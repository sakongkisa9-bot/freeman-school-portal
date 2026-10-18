import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from marksheet_chooser import NEW_STYLE, OLD_STYLE
from ui_summary import ClassSummaryView, normalize_summary_level


class SummaryDatabase:
    def __init__(self, average_level="EE2"):
        self.conn = sqlite3.connect(":memory:")
        self._cursor = self.conn.cursor()
        self._cursor.execute(
            "CREATE TABLE students (adm_no TEXT, name TEXT, gender TEXT, grade TEXT, assessment_number TEXT, stream TEXT)"
        )
        self._cursor.execute(
            "INSERT INTO students VALUES ('A1', 'Amina Wanjiku', 'F', 'Grade 4', 'K001', 'A')"
        )
        self._cursor.execute(
            "INSERT INTO students VALUES ('A2', 'Brian Otieno', 'M', 'Grade 4', 'K002', 'A')"
        )
        self._cursor.execute(
            "CREATE TABLE primary_marks (adm_no TEXT PRIMARY KEY, total_points INTEGER, average_level TEXT, "
            "eng_s INTEGER, eng_r TEXT, eng_p INTEGER)"
        )
        self._cursor.execute(
            "INSERT INTO primary_marks VALUES ('A1', 8, ?, 78, 'ME', 3)", (average_level,)
        )
        self._cursor.execute(
            "INSERT INTO primary_marks VALUES ('A2', 0, 'Y', 'AB', 'AB', 0)"
        )
        self.conn.commit()

    def cursor(self):
        return self._cursor


def summary_view(style, db, config):
    view = ClassSummaryView.__new__(ClassSummaryView)
    view.db = db
    view.class_name = "Grade 4"
    view.stream = None
    view.style = style
    view.grade_type = "primary"
    view.table_name = "primary_marks"
    view.subjects = ["ENG"]
    view.school_config = config
    return view


class SummaryDataTests(unittest.TestCase):
    def test_new_style_uses_selected_catalog_without_changing_old_source(self):
        view = ClassSummaryView.__new__(ClassSummaryView)
        view.school_config = {
            "subjects": {"primary": ["STALE"]},
            "subject_catalog": {
                "primary": [
                    {"short": "ENG", "selected": True},
                    {"short": "STALE", "selected": False},
                ]
            },
        }
        self.assertEqual(view.get_subjects_from_json("primary", selected_only=True), ["ENG"])
        self.assertEqual(view.get_subjects_from_json("primary"), ["STALE"])

    def test_legacy_levels_collapse_to_four_reporting_bands(self):
        self.assertEqual(
            [normalize_summary_level(level) for level in ("EE1", "EE2", "ME1", "ME2", "AE1", "AE2", "BE1", "BE2")],
            ["EE", "EE", "ME", "ME", "AE", "AE", "BE", "BE"],
        )

    def test_new_style_counts_final_subject_rating_and_averages_marks(self):
        config = {
            "academic_year": 2026,
            "marksheet_term": "Term 1",
            "cbc_levels": {
                "Grade 4": {
                    "English": {
                        "2026|Term 1": {
                            "records": [["K001", "Amina Wanjiku", "English", "Strand", "Sub-strand", "EE"]]
                        }
                    }
                }
            },
        }
        db = SummaryDatabase()
        self.addCleanup(db.conn.close)
        summary = summary_view(NEW_STYLE, db, config).load_summary_data()
        self.assertEqual(summary["subject_averages"], [("ENG", 78.0)])
        self.assertEqual(summary["subject_level_counts"]["ENG"], {"EE": 1, "ME": 0, "AE": 0, "BE": 0})

    def test_new_style_pdf_is_generated(self):
        db = SummaryDatabase()
        self.addCleanup(db.conn.close)
        view = summary_view(NEW_STYLE, db, {})
        view.subjects = [f"SUBJECT{index}" for index in range(1, 13)]
        view.summary = {
            "total_students": 1,
            "gender_counts": {"male": 0, "female": 1, "other": 0},
            "subject_averages": [(subject, 78.0) for subject in view.subjects],
            "subject_level_counts": {
                subject: {"EE": 1, "ME": 0, "AE": 0, "BE": 0}
                for subject in view.subjects
            },
        }
        view.school_config = {"school_name": "Test School"}
        view.current_exam_title = "Term Assessment"
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "summary.pdf")
            with patch("ui_summary.messagebox.showinfo"):
                view.generate_new_style_pdf(path)
            with open(path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            self.assertTrue(pdf_data.startswith(b"%PDF-"))
            self.assertIn(b"/Count 1", pdf_data)


if __name__ == "__main__":
    unittest.main()