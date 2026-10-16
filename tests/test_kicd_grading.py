import unittest

from kicd_grading import (
    formative_level,
    formative_raw,
    formative_weighted,
    index_levels,
    level_from_percent,
    levels_for,
    subject_result,
)


class KICDGradingTests(unittest.TestCase):
    def test_percentage_bands(self):
        cases = [(100, "EE"), (80, "EE"), (79, "ME"), (50, "ME"), (49, "AE"), (30, "AE"), (29, "BE"), (0, "BE")]
        for percent, level in cases:
            self.assertEqual(level_from_percent(percent), level)
        for invalid in (-1, 101, "AB", None):
            self.assertIsNone(level_from_percent(invalid))

    def test_formative_mean_and_weight(self):
        self.assertEqual(formative_raw(["EE", "ME"]), 3.5)
        self.assertEqual(formative_raw(["EE", "AB", "BE", None]), 2.5)
        self.assertIsNone(formative_raw(["AB", None]))
        self.assertEqual(formative_weighted(3.5), 61.25)
        self.assertEqual(
            [formative_level(value) for value in (4, 3.5, 3.0, 2.5, 2.0, 1.4)],
            ["EE", "EE", "ME", "ME", "AE", "BE"],
        )

    def test_matches_the_documented_example(self):
        result = subject_result(["EE", "ME"], 78)
        self.assertEqual((result["F"], result["S"], result["R"]), ("3.5 (EE)", "78%", "EE"))
        self.assertEqual(result["final_percent"], 84.65)

    def test_without_covered_sub_strands_the_exam_alone_decides(self):
        result = subject_result([], 45)
        self.assertEqual((result["F"], result["S"], result["R"]), ("n/a", "45%", "AE"))

    def test_absent_exam_is_ab(self):
        result = subject_result(["EE"], "AB")
        self.assertEqual((result["S"], result["R"]), ("AB", "AB"))

    def test_levels_are_matched_by_assessment_number_or_name(self):
        index = index_levels([
            ["K001", "Amina Wanjiku", "Mathematics", "Number", "Fractions", "EE"],
            ["K001", "Amina Wanjiku", "Mathematics", "Number", "Decimals", "ME"],
            ["K002", "Brian Otieno", "Mathematics", "Number", "Fractions", "BE"],
        ])
        self.assertEqual(levels_for(index, "K001", ""), ["EE", "ME"])
        self.assertEqual(levels_for(index, "", "brian  otieno"), ["BE"])
        self.assertEqual(levels_for(index, "K999", "Nobody"), [])

    def test_weighted_total_can_change_the_exam_level(self):
        # Strong formative lifts a 40% exam: 0.7*(2/4*100)... 2 points -> 35 + 12 = 47 AE
        self.assertEqual(subject_result(["AE"], 40)["R"], "AE")
        # 4 points -> 70 + 3 = 73 ME even with a weak exam.
        self.assertEqual(subject_result(["EE"], 10)["R"], "ME")


if __name__ == "__main__":
    unittest.main()
