import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import cloud_portal_v2


class CloudHomeworkFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "homework.sqlite")
        self.db_path_patch = patch.object(cloud_portal_v2, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        cloud_portal_v2.init_db()
        connection = cloud_portal_v2.get_db()
        school = connection.execute(
            "INSERT INTO schools (school_name, school_code, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("Homework School", "homework-test", "unused", "2026-10-18"),
        )
        self.school_id = school.lastrowid
        connection.execute(
            "INSERT INTO teacher_assignments (school_id, class_name, subject, teacher_name, teacher_code) VALUES (?, ?, ?, ?, ?)",
            (self.school_id, "Grade 3", "Mathematics", "Teacher", "T003"),
        )
        connection.execute(
            "INSERT INTO students (school_id, grade, adm_no, student_name, gender, assessment_number) VALUES (?, ?, ?, ?, ?, ?)",
            (self.school_id, "Grade 3", "A003", "Learner", "F", "K0010203003"),
        )
        connection.execute(
            "INSERT INTO students (school_id, grade, adm_no, student_name, gender, assessment_number) VALUES (?, ?, ?, ?, ?, ?)",
            (self.school_id, "Grade 3", "A004", "Second Learner", "M", "K0010203004"),
        )
        connection.commit()
        connection.close()
        self.client = cloud_portal_v2.app.test_client()

    def tearDown(self):
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def test_publish_view_download_and_expiry(self):
        with self.client.session_transaction() as session:
            session["school_id"] = self.school_id
            session["teacher_code"] = "T003"
            session["role"] = "teacher"

        response = self.client.post(
            "/teacher/homework",
            data={
                "grade": "Grade 3",
                "title": "Fractions practice",
                "subject": "Mathematics",
                "instructions": "Complete the attached worksheet.",
                "due_date": "2099-12-31",
                "files": (io.BytesIO(b"worksheet bytes"), "worksheet.txt"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)

        connection = sqlite3.connect(self.db_path)
        homework_id = connection.execute(
            "SELECT id FROM homework_assignments WHERE title = ?",
            ("Fractions practice",),
        ).fetchone()[0]
        file_id = connection.execute(
            "SELECT id FROM homework_files WHERE homework_id = ?", (homework_id,)
        ).fetchone()[0]
        connection.close()

        with self.client.session_transaction() as session:
            session.clear()
            session["parent_student_id"] = 1
            session["parent_school_id"] = self.school_id
            session["parent_grade"] = "Grade 3"
            session["parent_student_name"] = "Learner"
            session["parent_school_name"] = "Homework School"

        landing = self.client.get("/parent/dashboard")
        self.assertEqual(landing.status_code, 200)
        self.assertIn(b"View Homework", landing.data)
        self.assertIn(b"1", landing.data)

        listing = self.client.get("/parent/homework")
        self.assertEqual(listing.status_code, 200)
        self.assertIn(b"Fractions practice", listing.data)
        detail = self.client.get(f"/parent/homework/{homework_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Answers cannot be submitted", detail.data)

        download = self.client.get(f"/parent/homework/file/{file_id}")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.data, b"worksheet bytes")

        teacher = self.client
        with teacher.session_transaction() as session:
            session.clear()
            session["school_id"] = self.school_id
            session["teacher_code"] = "T003"
            session["role"] = "teacher"
        overview = teacher.get("/teacher/homework?grade=Grade%203")
        self.assertIn(b"1 of 2 students checked", overview.data)
        self.assertIn(b"Opened (1)", overview.data)
        self.assertIn(b"Learner", overview.data)
        self.assertIn(b"Not opened (1)", overview.data)
        self.assertIn(b"Second Learner", overview.data)

        connection = sqlite3.connect(self.db_path)
        connection.execute(
            "UPDATE homework_assignments SET due_date = '2000-01-01' WHERE id = ?",
            (homework_id,),
        )
        connection.commit()
        connection.close()
        with self.client.session_transaction() as session:
            session.clear()
            session["parent_student_id"] = 1
            session["parent_school_id"] = self.school_id
            session["parent_grade"] = "Grade 3"
        expired_listing = self.client.get("/parent/homework")
        self.assertNotIn(b"Fractions practice", expired_listing.data)
        expired_download = self.client.get(f"/parent/homework/file/{file_id}")
        self.assertEqual(expired_download.status_code, 404)


if __name__ == "__main__":
    unittest.main()