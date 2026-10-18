import json
import sqlite3
import unittest
from types import SimpleNamespace

from database import FreemanDB
from historical_report_forms import ArchivedReportFormsView
from ui_summary import ClassSummaryView


class HistoricalSummaryTests(unittest.TestCase):
    def test_summary_uses_archived_rows_and_does_not_invent_gender(self):
        view = SimpleNamespace(
            subjects=["Math", "English"],
            grade_type="primary",
            archive_term="Term 2",
            archive_year=2025,
        )
        summary = ClassSummaryView.load_archived_summary_data(
            view,
            (json.dumps([["Amina", 80, "EE", 70, "ME", 150, "EE"]]), "{}"),
        )

        self.assertEqual(summary["total_students"], 1)
        self.assertEqual(summary["subject_averages"], [("Math", 80.0), ("English", 70.0)])
        self.assertEqual(summary["distribution"], {"EE": 1, "ME": 1, "AE": 0, "BE": 0})
        self.assertFalse(summary["gender_data_available"])


class ArchivedYearLookupTests(unittest.TestCase):
    def test_year_lookup_can_be_limited_to_class(self):
        database = FreemanDB.__new__(FreemanDB)
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        database._cursor = connection.cursor()
        database._cursor.execute(
            "CREATE TABLE previous_exams (class_name TEXT, year INTEGER, exam_name TEXT, exam_date TEXT)"
        )
        database._cursor.executemany(
            "INSERT INTO previous_exams VALUES (?, ?, ?, ?)",
            [
                ("Grade 4", 2025, "Term 1 Exam", "2025-03-01"),
                ("Grade 4", 2024, "Term 3 Exam", "2024-10-01"),
                ("Grade 5", 2023, "Term 2 Exam", "2023-06-01"),
            ],
        )

        self.assertEqual(database.get_previous_exam_years("Grade 4"), [2025, 2024])
        self.assertEqual(database.get_previous_exam_years(), [2025, 2024, 2023])
        self.assertEqual(database.get_previous_exams("Grade 4", 2025), [("Term 1 Exam", "2025-03-01")])


class HistoricalReportTests(unittest.TestCase):
    def test_archived_report_row_is_parsed_without_live_student_data(self):
        view = SimpleNamespace(subjects=["Math"], stride=3)
        report = ArchivedReportFormsView._student_subjects(
            view, ["Amina", 82, "ME", 6, 82, "ME", 6]
        )

        self.assertEqual(report, [("Math", 82, "ME", 6)])


if __name__ == "__main__":
    unittest.main()