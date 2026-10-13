import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import cloud_portal_v2
from werkzeug.security import generate_password_hash


class CBACloudFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "cba-test.sqlite")
        self.db_path_patch = patch.object(cloud_portal_v2, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        cloud_portal_v2.init_db()

        connection = cloud_portal_v2.get_db()
        cursor = connection.execute(
            """
            INSERT INTO schools (school_name, school_code, password_hash, created_at, portal_open)
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                "Test School",
                "test-school",
                generate_password_hash("school-password"),
                "2026-10-13",
            ),
        )
        self.school_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO teacher_assignments
                (school_id, class_name, subject, teacher_name, teacher_code)
            VALUES (?, 'Grade 3', 'ENG', 'Teacher One', 'T001')
            """,
            (self.school_id,),
        )
        connection.execute(
            """
            INSERT INTO students (school_id, grade, adm_no, student_name)
            VALUES (?, 'Grade 3', 'A001', 'Amina Wanjiku')
            """,
            (self.school_id,),
        )
        connection.execute(
            """
            INSERT INTO students (school_id, grade, adm_no, student_name)
            VALUES (?, 'Grade 3', 'A002', 'Brian Otieno')
            """,
            (self.school_id,),
        )
        connection.commit()
        connection.close()
        self.client = cloud_portal_v2.app.test_client()
        with self.client.session_transaction() as session:
            session["school_id"] = self.school_id
            session["teacher_code"] = "T001"

    def tearDown(self):
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def test_publish_save_convert_and_download_cba_results(self):
        tasks = [
            {
                "name": "Task 1",
                "unit": "words",
                "ranges": {
                    "Level 1": {"type": "range", "min": 0, "max": 44},
                    "Level 2": {"type": "range", "min": 45, "max": 89},
                    "Level 3": {"type": "exact", "value": 90},
                    "Level 4": {"type": "above", "value": 90},
                },
            }
        ]
        publish_response = self.client.post(
            "/api/upload_cba_tasks",
            json={
                "school_code": "test-school",
                "username": "admin",
                "password": "school-password",
                "grade": "Grade 3",
                "subject": "ENG",
                "tasks": tasks,
            },
        )
        self.assertEqual(publish_response.status_code, 200)

        subject_response = self.client.get("/cba/select_subject/Grade%203")
        self.assertEqual(subject_response.status_code, 200)
        self.assertIn(b"ENG", subject_response.data)
        self.assertIn(b"/cba/marks/Grade%203?subject=ENG", subject_response.data)

        page_response = self.client.get("/cba/marks/Grade%203?subject=ENG")
        self.assertEqual(page_response.status_code, 200)
        self.assertIn(b"Task 1", page_response.data)
        self.assertIn(b"Above 90 words", page_response.data)

        save_response = self.client.post(
            "/cba/marks/Grade%203?subject=ENG",
            data={"score_1_0": "4", "score_2_0": "90"},
            follow_redirects=True,
        )
        self.assertEqual(save_response.status_code, 200)

        connection = sqlite3.connect(self.db_path)
        raw_score = connection.execute(
            "SELECT raw_score FROM cba_scores WHERE adm_no = 'A001' AND task_name = 'Task 1'"
        ).fetchone()[0]
        percentage_count = connection.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
        connection.close()
        self.assertEqual(raw_score, 4)
        self.assertEqual(percentage_count, 0)

        invalid_response = self.client.post(
            "/cba/marks/Grade%203?subject=ENG",
            data={"score_1_0": "-1"},
            follow_redirects=True,
        )
        self.assertEqual(invalid_response.status_code, 200)
        connection = sqlite3.connect(self.db_path)
        preserved_score = connection.execute(
            "SELECT raw_score FROM cba_scores WHERE adm_no = 'A001' AND task_name = 'Task 1'"
        ).fetchone()[0]
        connection.close()
        self.assertEqual(preserved_score, 4)

        excel_response = self.client.get(
            "/cba/export/Grade%203/xlsx?subject=ENG"
        )
        self.assertEqual(excel_response.status_code, 200)
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(excel_response.data), data_only=True)
        worksheet = workbook.active
        self.assertEqual(worksheet.cell(4, 3).value, 4)
        self.assertEqual(worksheet.cell(4, 4).value, "Level 1")
        self.assertEqual(worksheet.cell(4, 5).value, 1)
        self.assertEqual(worksheet.cell(5, 3).value, 90)
        self.assertEqual(worksheet.cell(5, 4).value, "Level 3")
        self.assertEqual(worksheet.cell(5, 5).value, 3)

        pdf_response = self.client.get("/cba/export/Grade%203/pdf?subject=ENG")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()