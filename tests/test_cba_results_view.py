import unittest

from cba_results_view import CBAResultsView


class CBAResultsViewTests(unittest.TestCase):
    def test_level_column_is_not_treated_as_optional_total(self):
        view = object.__new__(CBAResultsView)
        view.columns = ["Learner", "Level"]
        view.records = [["A Learner", "EE"]]
        view.has_total_score = False
        self.assertEqual(
            view._print_data(False),
            (["Learner", "Level"], [["A Learner", "EE"]]),
        )

    def test_only_total_score_column_can_be_omitted(self):
        view = object.__new__(CBAResultsView)
        view.columns = ["Learner", "Task 1", "Total Score"]
        view.records = [["A Learner", 4, 4]]
        view.has_total_score = True
        self.assertEqual(
            view._print_data(False),
            (["Learner", "Task 1"], [["A Learner", 4]]),
        )


if __name__ == "__main__":
    unittest.main()