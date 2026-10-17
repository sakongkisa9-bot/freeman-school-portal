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

    def test_class_streams_are_saved_and_cleared_per_class(self):
        self.db.create_class_streams_table()

        saved = self.db.set_class_streams("Playgroup", ["A", "B", "a"])

        self.assertEqual(saved, ["A", "B"])
        self.assertEqual(self.db.get_class_streams("playgroup"), ["A", "B"])
        self.assertEqual(self.db.set_class_streams("Playgroup", []), [])
        self.assertEqual(self.db.get_class_streams("Playgroup"), [])

    def test_cannot_remove_stream_with_assigned_students(self):
        self.db.create_class_streams_table()
        self.db.set_class_streams("Playgroup", ["A", "B"])
        self.db.cursor().execute(
            "INSERT INTO students (adm_no, name, grade, stream) VALUES (?, ?, ?, ?)",
            ("001", "Amina", "Playgroup", "B"),
        )

        with self.assertRaisesRegex(ValueError, "students are assigned"):
            self.db.set_class_streams("Playgroup", ["A"])

        self.assertEqual(self.db.get_class_streams("Playgroup"), ["A", "B"])


if __name__ == "__main__":
    unittest.main()