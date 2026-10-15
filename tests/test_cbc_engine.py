import unittest

from cbc_engine import (
    SUBJECT_TO_LEARNING_AREA,
    aggregate_competency,
    aggregate_term_competency,
    calculate_milestone_result,
    rating_from_percentage,
    reporting_bands_for_rating,
    validate_assessment_number,
    validate_curriculum,
    validate_rubric_rating,
)


class CBCEngineTests(unittest.TestCase):
    def test_percentage_bands_map_to_levels(self):
        cases = [(100, 4), (80, 4), (79, 3), (50, 3), (49, 2), (30, 2), (29, 1), (0, 1)]
        for percent, level in cases:
            self.assertEqual(rating_from_percentage(percent), level)
        for invalid in (-1, 101, "AB", None, ""):
            self.assertIsNone(rating_from_percentage(invalid))

    def test_primary_subject_codes_map_to_curriculum_learning_areas(self):
        self.assertEqual(SUBJECT_TO_LEARNING_AREA["AGRI"], "Agriculture")
        self.assertEqual(SUBJECT_TO_LEARNING_AREA["SCIE"], "Science & Technology")
        self.assertEqual(SUBJECT_TO_LEARNING_AREA["REL"], "Religious Education")

    def test_assessment_number_is_preserved_as_alphanumeric_text(self):
        self.assertEqual(validate_assessment_number(" K0010203002 "), "K0010203002")
        with self.assertRaises(ValueError):
            validate_assessment_number("KNEC 123")

    def test_junior_curriculum_has_nine_area_cap_and_hierarchy(self):
        curriculum = [
            {"name": f"Area {index}", "strands": [{"name": "Strand", "sub_strands": ["Topic"]}]}
            for index in range(9)
        ]
        self.assertEqual(len(validate_curriculum(curriculum, "Grade 9")), 9)
        with self.assertRaises(ValueError):
            validate_curriculum(curriculum + [curriculum[0]], "Grade 9")

    def test_mode_ignores_absence_and_ties_choose_lower_level(self):
        self.assertEqual(aggregate_competency([4, 3, 3, "AB"]), "ME")
        self.assertEqual(aggregate_competency([4, 3]), "ME")
        self.assertEqual(aggregate_competency(["AB"]), "AB")

    def test_weighted_mode_and_eight_point_reporting_band(self):
        self.assertEqual(aggregate_competency([4, 3], weights=[1, 2]), "ME")
        self.assertEqual(reporting_bands_for_rating(4), ("EE1", "EE2"))
        self.assertEqual(reporting_bands_for_rating(1), ("BE1", "BE2"))
        with self.assertRaises(ValueError):
            validate_rubric_rating(5)

    def test_term_aggregation_uses_category_weights_without_averages(self):
        self.assertEqual(aggregate_term_competency([4, 4, 3], [2]), "EE")
        self.assertEqual(aggregate_term_competency([4], [1, 1, 1]), "EE")
        self.assertEqual(aggregate_term_competency([4], []), "Pending")

    def test_milestone_weights_keep_components_separate(self):
        self.assertEqual(
            calculate_milestone_result(
                "Grade 9", 90, grade7_sba_percent=80, grade8_sba_percent=90
            ),
            88.0,
        )
        self.assertEqual(calculate_milestone_result("Grade 6", 90, sba_percent=80), 86.0)
        with self.assertRaises(ValueError):
            calculate_milestone_result("Grade 8", 80, 90)


if __name__ == "__main__":
    unittest.main()