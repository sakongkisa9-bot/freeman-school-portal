import unittest
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from cbc_report import (
    build_teacher_comments,
    build_subject_results,
    chart_marker_for_subject,
    group_rubric_records,
    normalize_level,
    pathway_recommendation,
    recommend_substrands,
)
from jinja2 import DictLoader, Environment


class CBCReportTests(unittest.TestCase):
    def test_normalizes_current_and_legacy_levels(self):
        self.assertEqual(
            [normalize_level(value) for value in ("4", "ME", "BE1", "EE2", "AB", "unknown")],
            ["EE", "ME", "BE", "EE", "AB", ""],
        )

    def test_chart_subject_marker_order_includes_diamond(self):
        self.assertEqual(
            [chart_marker_for_subject(index) for index in range(5)],
            ["circle", "square", "triangle", "cross", "diamond"],
        )

    def test_groups_substrands_and_recommends_weakest_variable_levels(self):
        subjects = group_rubric_records(
            [
                ["K1", "Learner", "Mathematics", "Number", "Fractions", "EE", "Accurate work"],
                ["K1", "Learner", "Mathematics", "Number", "Decimals", "ME"],
                ["K1", "Learner", "Mathematics", "Measurement", "Length", "AE"],
                ["K1", "Learner", "Mathematics", "Measurement", "Area", "BE"],
            ]
        )
        self.assertEqual(subjects[0]["name"], "Mathematics")
        self.assertEqual(len(subjects[0]["strands"]), 2)
        self.assertEqual(subjects[0]["strands"][0]["sub_strands"][0]["evidence"], "Accurate work")
        self.assertEqual(
            [item["name"] for item in subjects[0]["recommendations"]],
            ["Length", "Area"],
        )

    def test_uniform_levels_need_no_recommendation(self):
        self.assertEqual(
            recommend_substrands(
                [{"name": "Fractions", "level": "BE"}, {"name": "Decimals", "level": "BE"}]
            ),
            [],
        )

    def test_teacher_comments_use_student_specific_strengths_and_focus(self):
        comments = build_teacher_comments(
            [
                {"area": "Mathematics", "rating": "EE"},
                {"area": "English", "rating": "AE"},
            ],
            [{"name": "English", "recommendations": [{"name": "Comprehension"}]}],
            "Morgan Kibet",
        )
        self.assertIn("Mathematics", comments["class_teacher"])
        self.assertIn("Morgan Kibet", comments["class_teacher"])
        self.assertIn("English (Comprehension)", comments["class_teacher"])
        self.assertNotEqual(comments["class_teacher"], comments["head_teacher"])

    def test_teacher_comments_report_missing_evidence_without_generic_rating(self):
        comments = build_teacher_comments([{"area": "Math", "rating": ""}], student_name="Morgan")
        self.assertIn("More assessment evidence", comments["class_teacher"])

    def test_low_level_outlier_is_recommended_without_flagging_majority(self):
        result = recommend_substrands(
            [
                {"name": "A", "level": "AE"},
                {"name": "B", "level": "AE"},
                {"name": "C", "level": "AE"},
                {"name": "D", "level": "BE"},
            ]
        )
        self.assertEqual([item["name"] for item in result], ["D"])

    def test_pathway_recommendation_requires_repeated_evidence_for_consistency(self):
        current = {"Mathematics": 90, "Integrated Science": 85, "English": 60}
        history = [current, current]
        recommendation = pathway_recommendation(current, history, "Term 2")
        self.assertEqual(recommendation["recommended"], "STEM")
        self.assertTrue(recommendation["consistent"])

    def test_school_subject_abbreviations_feed_pathway_scores(self):
        recommendation = pathway_recommendation(
            {"MATH": 90, "INT SCI": 80, "PRE-TECH": 85, "AGRI": 75, "ENG": 60}
        )
        stem = next(item for item in recommendation["pathways"] if item["name"] == "STEM")
        self.assertEqual(stem["score"], 82.5)
        math = next(item for item in stem["subject_scores"] if item["name"] == "Mathematics")
        self.assertEqual(math["score"], 90)

    def test_single_exam_is_labeled_indicative(self):
        recommendation = pathway_recommendation({"Mathematics": 80}, term="Term 1")
        self.assertFalse(recommendation["consistent"])
        self.assertIn("only", recommendation["basis"])

    def test_parent_template_renders_cbc_pages_without_legacy_totals(self):
        template_path = Path(__file__).parents[1] / "templates" / "cloud_parent_dashboard.html"
        env = Environment(loader=DictLoader({"cloud_base.html": "{% block content %}{% endblock %}"}))
        env.filters["rating_to_comment"] = lambda rating, subject, _indices: f"{rating} {subject}"
        env.filters["get_class_teacher_comment"] = lambda rating: f"Class {rating}"
        env.filters["get_head_teacher_comment"] = lambda rating: f"Head {rating}"
        report = {
            "subjects": ["MATH"],
            "subject_labels": {"MATH": "Mathematics"},
            "exam_title": "Term 3 Exam",
            "performance_history": [
                {"name": "Term 2 Exam", "subjects": {"MATH": 60}},
                {"name": "Term 3 Exam", "subjects": {"MATH": 82}},
            ],
            "subject_results": [{
                "subject": "MATH", "area": "Mathematics", "formative": "4.0 (EE)",
                "summative": "40%", "composite_score": 82.0, "rating": "EE",
            }],
            "rubric_subjects": [{
                "name": "Mathematics",
                "strands": [{"name": "Number", "sub_strands": [{
                    "name": "Fractions", "level": "EE", "evidence": "Accurate work",
                }]}],
                "recommendations": [],
            }],
            "pathway_recommendation": {
                "recommended": "STEM", "basis": "Indicative match.",
                "pathways": [{
                    "name": "STEM", "score": 82.0,
                    "subject_scores": [{"name": "Mathematics", "score": 82.0}],
                }],
            },
            "subject_comment_indices": {}, "average_rating": "EE", "current_marks": {},
        }
        html = env.from_string(template_path.read_text(encoding="utf-8")).render(
            report=report, previous_exams=[], student_name="Learner", grade="Grade 7",
            student_stream="East", school_name="School", school_address="",
            school_telephone="", school_logo="", student_photo="", teacher_map={},
            school_administrator="Head Teacher", school_signature="", session={},
        )
        for expected in (
            "Subject Progress History", "Mathematics: Detailed Performance Rubric",
            "Junior Career Pathway Guidance", "Term 3 Exam (Current Exam)",
            "Formative (70%)", "Composite (Total)", "Improvement", "+22",
            "EE (4)",
        ):
            self.assertIn(expected, html)
        self.assertNotIn("Teacher Note", html)
        self.assertNotIn("TOTAL SCORES", html)
        self.assertNotIn("EE1 &amp; EE2", html)

    def test_pdf_modes_generate_one_summary_page_or_full_pages(self):
        from reportforms import ReportFormsView

        class Harness:
            school_config = {"school_name": "Test School", "school_administrator": "Head Teacher"}
            _average_cbc_rating = staticmethod(lambda _report: "EE")
            get_class_teacher_comment = staticmethod(lambda _level: "Good progress.")
            get_head_teacher_comment = staticmethod(lambda _level: "Continue learning.")
            get_teacher_assignments = staticmethod(lambda _grade: {})
            rating_to_comment = staticmethod(lambda _rating, _subject: "Strong work.")
            _previous_subject_score = staticmethod(lambda _marks, _subject: "-")

        report = {
            "student_name": "Learner", "grade": "Grade 7", "term": "Term 3",
            "academic_year": 2026, "exam_title": "Term 3 Assessment", "stream": "East",
            "subjects": ["MATH"], "subject_results": [{
                "subject": "MATH", "area": "Mathematics", "formative": "4.0 (EE)",
                "summative": "40%", "composite_score": 82.0, "rating": "EE",
            }],
            "performance_history": [{"name": "Term 3", "subjects": {"MATH": 82.0}}],
            "rubric_subjects": [{
                "name": "Mathematics",
                "strands": [{"name": "Number", "sub_strands": [{
                    "name": "Fractions", "level": "EE", "evidence": "Accurate work",
                }]}],
                "recommendations": [],
            }],
            "pathway_recommendation": {
                "recommended": "STEM", "basis": "Indicative match.",
                "pathways": [{"name": "STEM", "score": 82.0, "subjects": ["Mathematics"]}],
            },
        }
        with TemporaryDirectory() as directory:
            counts = []
            for mode in ("summary", "full"):
                output = Path(directory) / f"{mode}.pdf"
                success = ReportFormsView._print_cbc_report_pdf(
                    Harness(), report, str(output), None, mode, False,
                )
                self.assertTrue(success)
                counts.append(len(re.findall(rb"/Type /Page\b", output.read_bytes())))
        self.assertEqual(counts, [1, 3])

    def test_subject_composite_uses_formative_and_summative_weights(self):
        results = build_subject_results(
            [("MATH", "Mathematics")],
            {"math_s": 40},
            [["K1", "Learner", "Mathematics", "Number", "Fractions", "EE"]],
        )
        self.assertEqual(results[0]["formative"], "4.0 (EE)")
        self.assertEqual(results[0]["summative"], "40%")
        self.assertEqual(results[0]["rating"], "EE")
        self.assertEqual(results[0]["composite_score"], 82.0)

    def test_report_composite_is_rounded_to_a_whole_percent(self):
        result = build_subject_results(
            [("MATH", "Mathematics")],
            {"math_s": 78},
            [
                ["K1", "Learner", "Mathematics", "Number", "Fractions", "EE"],
                ["K1", "Learner", "Mathematics", "Number", "Decimals", "ME"],
            ],
        )[0]
        self.assertEqual(result["composite_score"], 85)
        self.assertIsInstance(result["composite_score"], int)

    def test_subject_without_strand_records_uses_exam_alone(self):
        result = build_subject_results(
            [("MATH", "Mathematics")], {"math_s": 45}, []
        )[0]
        self.assertEqual(result["formative"], "n/a")
        self.assertEqual(result["rating"], "AE")
        self.assertEqual(result["composite_score"], 45.0)


if __name__ == "__main__":
    unittest.main()