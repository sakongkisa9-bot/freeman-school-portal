import csv
import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import cloud_portal_v2
from werkzeug.security import generate_password_hash


class CBCCloudFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "cbc-test.sqlite")
        self.db_path_patch = patch.object(cloud_portal_v2, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        cloud_portal_v2.init_db()
        connection = cloud_portal_v2.get_db()
        school = connection.execute(
            "INSERT INTO schools (school_name, school_code, password_hash, created_at, portal_open) VALUES (?, ?, ?, ?, 1)",
            ("Test School", "cbc-test", generate_password_hash("pw"), "2026-10-14"),
        )
        self.school_id = school.lastrowid
        connection.execute(
            "INSERT INTO teacher_assignments (school_id, class_name, subject, teacher_name, teacher_code) VALUES (?, 'Grade 3', 'MATH', 'Teacher', 'T001')",
            (self.school_id,),
        )
        connection.execute(
            "INSERT INTO students (school_id, grade, adm_no, student_name, gender, assessment_number) VALUES (?, 'Grade 3', 'A001', 'A Learner', 'F', 'K0010203002')",
            (self.school_id,),
        )
        connection.commit()
        connection.close()
        self.client = cloud_portal_v2.app.test_client()
        with self.client.session_transaction() as session:
            session["school_id"] = self.school_id
            session["teacher_code"] = "T001"
            session["role"] = "admin"

    def tearDown(self):
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def _save_curriculum(self):
        return self.client.post(
            "/cbc/curriculum/Grade%203",
            data={
                "curriculum_json": '[{"name":"Mathematics","strands":[{"name":"Number","sub_strands":["Fractions"]}]}]'
            },
        )

    def test_curriculum_gradebook_and_csv_staging_use_assessment_number(self):
        curriculum_response = self._save_curriculum()
        self.assertEqual(curriculum_response.status_code, 200)
        with self.client.session_transaction() as session:
            session["role"] = "teacher"

        page = self.client.get(
            "/cbc/gradebook/Grade%203?area=Mathematics&term=Term%201&academic_year=2026"
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"K0010203002", page.data)

        connection = sqlite3.connect(self.db_path)
        student_id = connection.execute("SELECT id FROM students WHERE adm_no='A001'").fetchone()[0]
        sub_strand_id = connection.execute("SELECT id FROM cbc_sub_strands WHERE name='Fractions'").fetchone()[0]
        connection.close()
        for assessment_type, value in (("Formative", "4"), ("Localized Summative", "1")):
            response = self.client.post(
                "/cbc/gradebook/Grade%203?area=Mathematics&term=Term%201&academic_year=2026",
                data={
                    "assessment_type": assessment_type,
                    "rating_{}_{}".format(student_id, sub_strand_id): value,
                },
            )
            self.assertEqual(response.status_code, 302)

        progress = self.client.get(
            "/cbc/gradebook/Grade%203?area=Mathematics&term=Term%201&academic_year=2026&assessment_type=Formative"
        )
        self.assertIn(b"EE", progress.data)
        profile = self.client.get(
            "/cbc/profile/Grade%203/K0010203002?term=Term%201&academic_year=2026"
        )
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"Fractions", profile.data)
        self.assertIn(b"EE1 / EE2", profile.data)
        self.assertNotIn(b"Total Score", profile.data)
        self.assertNotIn(b"Rank", profile.data)
        connection = sqlite3.connect(self.db_path)
        ratings = connection.execute(
            "SELECT assessment_number, assessment_type, rating FROM cbc_rubric_scores ORDER BY assessment_type"
        ).fetchall()
        connection.execute(
            "INSERT INTO cba_term_task_configs (school_id, grade, subject, term, tasks_json, updated_at) VALUES (?, 'Grade 3', 'MATH', 'Term 1', ?, 'now')",
            (
                self.school_id,
                '[{"name":"Task 1","ranges":{"Level 1":{"min":0,"max":2},"Level 2":{"min":3,"max":5},"Level 3":{"min":6,"max":8},"Level 4":{"min":9,"max":10}}},{"name":"Task 2","ranges":{"Level 1":{"min":0,"max":2},"Level 2":{"min":3,"max":5},"Level 3":{"min":6,"max":8},"Level 4":{"min":9,"max":10}}}]',
            ),
        )
        connection.commit()
        connection.close()
        self.assertEqual(ratings, [("K0010203002", "Formative", "4"), ("K0010203002", "Localized Summative", "1")])

        staging = self.client.get("/cba/staging/Grade%203?subject=MATH&term=Term%201")
        self.assertEqual(staging.status_code, 200)
        download = self.client.get("/cba/staging/Grade%203/download?subject=MATH&term=Term%201")
        self.assertEqual(download.status_code, 200)
        rows = list(csv.reader(io.StringIO(download.data.decode("utf-8-sig"))))
        self.assertEqual(rows[0], ["Assessment Number", "Learner's Name", "Gender", "Task 1", "Task 2"])
        self.assertEqual(rows[1][:3], ["K0010203002", "A Learner", "F"])

    def test_csv_staging_blocks_missing_assessment_numbers(self):
        self._save_curriculum()
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            "INSERT INTO students (school_id, grade, adm_no, student_name, gender, assessment_number) VALUES (?, 'Grade 3', 'A002', 'Missing Number', 'M', '')",
            (self.school_id,),
        )
        connection.execute(
            "INSERT INTO cba_term_task_configs (school_id, grade, subject, term, tasks_json, updated_at) VALUES (?, 'Grade 3', 'MATH', 'Term 1', ?, 'now')",
            (self.school_id, '[{"name":"Task 1","ranges":{"Level 1":{"min":0,"max":2},"Level 2":{"min":3,"max":5},"Level 3":{"min":6,"max":8},"Level 4":{"min":9,"max":10}}}]'),
        )
        connection.commit()
        connection.close()
        with self.client.session_transaction() as session:
            session["role"] = "teacher"
        response = self.client.get("/cba/staging/Grade%203/download?subject=MATH&term=Term%201")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing Number", response.get_json()["missing_assessment_numbers"])

    def test_sync_api_uses_assessment_number_without_aggregate_total(self):
        tasks = [{
            "name": "Task 1",
            "ranges": {
                "Level 1": {"min": 0, "max": 2},
                "Level 2": {"min": 3, "max": 5},
                "Level 3": {"min": 6, "max": 8},
                "Level 4": {"min": 9, "max": 10},
            },
        }]
        publish = self.client.post(
            "/api/upload_cba_tasks",
            json={
                "school_code": "cbc-test",
                "username": "admin",
                "password": "pw",
                "grade": "Grade 3",
                "subject": "MATH",
                "term": "Term 1",
                "tasks": tasks,
            },
        )
        self.assertEqual(publish.status_code, 200)
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            "INSERT INTO cba_term_scores (school_id, grade, subject, term, adm_no, student_name, task_name, raw_score, teacher_code, updated_at) VALUES (?, 'Grade 3', 'MATH', 'Term 1', 'A001', 'A Learner', 'Task 1', '4', 'T001', 'now')",
            (self.school_id,),
        )
        connection.commit()
        connection.close()
        response = self.client.post(
            "/api/fetch_cba_results",
            json={
                "school_code": "cbc-test",
                "password": "pw",
                "grade": "Grade 3",
                "subject": "MATH",
                "term": "Term 1",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["columns"], ["Assessment Number", "Learner's Name", "Gender", "Task 1"])
        self.assertEqual(payload["records"][0], ["K0010203002", "A Learner", "F", 2])

    def test_mixed_level_and_max_tasks_export_levels_and_raw_scores(self):
        tasks = [
            {
                "name": "Task 1",
                "ranges": {
                    "Level 1": {"min": 0, "max": 2},
                    "Level 2": {"min": 3, "max": 5},
                    "Level 3": {"min": 6, "max": 8},
                    "Level 4": {"min": 9, "max": 10},
                },
            },
            {"name": "Task 2", "mode": "max", "max_score": 8},
        ]
        publish = self.client.post(
            "/api/upload_cba_tasks",
            json={
                "school_code": "cbc-test",
                "username": "admin",
                "password": "pw",
                "grade": "Grade 3",
                "subject": "MATH",
                "term": "Term 1",
                "tasks": tasks,
            },
        )
        self.assertEqual(publish.status_code, 200)
        with self.client.session_transaction() as session:
            session["role"] = "teacher"
        page = self.client.get("/cba/marks/Grade%203?subject=MATH&term=Term%201")
        self.assertIn(b'id="taskSelect"', page.data)
        self.assertIn(b"max 8", page.data)

        student_id = sqlite3.connect(self.db_path).execute(
            "SELECT id FROM students WHERE adm_no='A001'"
        ).fetchone()[0]
        too_high = self.client.post(
            "/cba/marks/Grade%203?subject=MATH&term=Term%201",
            data={f"score_{student_id}_0": "4", f"score_{student_id}_1": "9"},
        )
        self.assertEqual(too_high.status_code, 302)
        connection = sqlite3.connect(self.db_path)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM cba_term_scores").fetchone()[0], 0)
        connection.close()

        self.client.post(
            "/cba/marks/Grade%203?subject=MATH&term=Term%201",
            data={f"score_{student_id}_0": "4", f"score_{student_id}_1": "7"},
        )
        csv_response = self.client.get(
            "/cba/staging/Grade%203/download?subject=MATH&term=Term%201"
        )
        rows = list(csv.reader(io.StringIO(csv_response.data.decode("utf-8-sig"))))
        self.assertEqual(rows[1], ["K0010203002", "A Learner", "F", "2", "7"])

        excel = self.client.get("/cba/export/Grade%203/xlsx?subject=MATH&term=Term%201")
        from openpyxl import load_workbook

        sheet = load_workbook(io.BytesIO(excel.data), data_only=True).active
        self.assertEqual([sheet.cell(3, c).value for c in (4, 5)], [2, 7])

        fetched = self.client.post(
            "/api/fetch_cba_results",
            json={"school_code": "cbc-test", "password": "pw", "grade": "Grade 3", "subject": "MATH", "term": "Term 1"},
        )
        self.assertEqual(fetched.get_json()["records"][0][3:], [2, 7])

    def test_milestone_route_applies_requested_weighting(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            "INSERT INTO students (school_id, grade, adm_no, student_name, gender, assessment_number) VALUES (?, 'Grade 9', 'A009', 'A Learner', 'F', 'K0010203002')",
            (self.school_id,),
        )
        connection.commit()
        connection.close()
        response = self.client.post(
            "/api/cbc/milestone-results",
            json={
                "grade": "Grade 9",
                "assessment_number": "K0010203002",
                "academic_year": 2026,
                "grade7_sba_percent": 80,
                "grade8_sba_percent": 90,
                "national_percent": 90,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["weighted_result"], 88.0)


class CBCRubricSchemaUpgradeTests(unittest.TestCase):
    def test_legacy_ratings_are_preserved_as_formative(self):
        temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(temp_dir.name, "legacy-cbc.sqlite")
        patcher = patch.object(cloud_portal_v2, "DB_PATH", db_path)
        patcher.start()
        try:
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE cbc_learning_areas (id INTEGER PRIMARY KEY, school_id INTEGER, grade TEXT, name TEXT);
                CREATE TABLE cbc_strands (id INTEGER PRIMARY KEY, learning_area_id INTEGER, name TEXT);
                CREATE TABLE cbc_sub_strands (id INTEGER PRIMARY KEY, strand_id INTEGER, name TEXT);
                CREATE TABLE cbc_rubric_scores (
                    id INTEGER PRIMARY KEY, school_id INTEGER, grade TEXT, assessment_number TEXT,
                    academic_year INTEGER, term TEXT, sub_strand_id INTEGER, rating TEXT,
                    evidence TEXT, teacher_code TEXT, updated_at TEXT
                );
                INSERT INTO cbc_learning_areas VALUES (1, 1, 'Grade 3', 'Mathematics');
                INSERT INTO cbc_strands VALUES (1, 1, 'Number');
                INSERT INTO cbc_sub_strands VALUES (1, 1, 'Fractions');
                INSERT INTO cbc_rubric_scores VALUES (1, 1, 'Grade 3', 'K0010203002', 2026, 'Term 1', 1, '4', NULL, 'T001', 'now');
                """
            )
            connection.close()
            cloud_portal_v2.init_db()
            connection = sqlite3.connect(db_path)
            upgraded = connection.execute(
                "SELECT assessment_number, assessment_type, rating FROM cbc_rubric_scores"
            ).fetchone()
            connection.close()
            self.assertEqual(upgraded, ("K0010203002", "Formative", "4"))
        finally:
            patcher.stop()
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()