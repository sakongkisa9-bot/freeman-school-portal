import unittest

from cba_logic import convert_raw_score, validate_tasks


class CBALogicTests(unittest.TestCase):
    def setUp(self):
        self.task = {
            "name": "Task 1",
            "ranges": {
                "Level 1": {"min": 1, "max": 4},
                "Level 2": {"min": 5, "max": 8},
                "Level 3": {"min": 9, "max": 12},
                "Level 4": {"min": 13, "max": 16},
            },
        }

    def test_converts_inclusive_level_boundaries_to_points(self):
        self.assertEqual(convert_raw_score(self.task, "4"), {"level": "Level 1", "points": 1})
        self.assertEqual(convert_raw_score(self.task, "13"), {"level": "Level 4", "points": 4})

    def test_rejects_score_outside_all_configured_ranges(self):
        with self.assertRaises(ValueError):
            convert_raw_score(self.task, "17")

    def test_rejects_overlapping_ranges(self):
        self.task["ranges"]["Level 2"]["min"] = 4
        with self.assertRaises(ValueError):
            validate_tasks([self.task])


if __name__ == "__main__":
    unittest.main()