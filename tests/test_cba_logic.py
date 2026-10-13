import unittest

from cba_logic import convert_raw_score, describe_criterion, task_score_bounds, validate_tasks


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

    def test_supports_exact_word_count_and_above_threshold(self):
        task = {
            "name": "Reading Comprehension",
            "unit": "words",
            "ranges": {
                "Level 1": {"type": "range", "min": 0, "max": 44},
                "Level 2": {"type": "range", "min": 45, "max": 89},
                "Level 3": {"type": "exact", "value": 90},
                "Level 4": {"type": "above", "value": 90},
            },
        }
        normalized = validate_tasks([task])[0]

        self.assertEqual(convert_raw_score(normalized, "90"), {"level": "Level 3", "points": 3})
        self.assertEqual(convert_raw_score(normalized, "91"), {"level": "Level 4", "points": 4})
        self.assertEqual(describe_criterion(normalized["ranges"]["Level 4"], "words"), "Above 90 words")
        self.assertEqual(task_score_bounds(normalized), (0, None))

    def test_supports_inclusive_at_least_rule(self):
        task = {
            "name": "Single Threshold",
            "ranges": {
                "Level 1": {"type": "range", "min": 0, "max": 4},
                "Level 2": {"type": "range", "min": 5, "max": 8},
                "Level 3": {"type": "range", "min": 9, "max": 12},
                "Level 4": {"type": "at_least", "value": 13},
            },
        }
        self.assertEqual(
            convert_raw_score(validate_tasks([task])[0], "13"),
            {"level": "Level 4", "points": 4},
        )


if __name__ == "__main__":
    unittest.main()