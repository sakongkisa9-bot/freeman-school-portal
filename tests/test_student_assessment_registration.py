import sqlite3
import unittest

from database import FreemanDB


class StudentAssessmentRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.db = object.__new__(FreemanDB)
        self.db.conn = sqlite3.connect(":memory:")
        self.db._cursor = self.db.conn.cursor()
        self.db._cursor.execute(
            """
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adm_no TEXT UNIQUE,
                name TEXT,
                grade TEXT,
                gender TEXT,
                phone TEXT,
                photo TEXT,
                stream TEXT
            )
            """
        )

    def tearDown(self):
        self.db.conn.close()

    def test_migrates_old_table_and_saves_assessment_number(self):
        self.db.migration_1_0_2()

        saved = self.db.add_student(
            "007",
            "Amina Wanjiku",
            "Grade 5",
            "Female",
            "",
            check_footprint=False,
            assessment_number="00012345678",
        )

        self.db.cursor().execute(
            "SELECT assessment_number FROM students WHERE adm_no = ?", ("007",)
        )
        self.assertTrue(saved)
        self.assertEqual(self.db.cursor().fetchone()[0], "00012345678")
        self.assertEqual(self.db.next_admission_number(), "008")


if __name__ == "__main__":
    unittest.main()