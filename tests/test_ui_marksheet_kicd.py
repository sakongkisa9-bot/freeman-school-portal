import sqlite3
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import ui_marksheet_kicd
import teachers_linked
from ui_marksheet_kicd import KICDMarkSheetView, normalize_score


class StubDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self._cursor = self.conn.cursor()
        self._cursor.execute(
            "CREATE TABLE students (adm_no TEXT PRIMARY KEY, name TEXT, grade TEXT, assessment_number TEXT, stream TEXT)"
        )
        self._cursor.executemany(
            "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
            [("A1", "Amina Wanjiku", "Grade 4", "K001", "A"), ("A2", "Brian Otieno", "Grade 4", "K002", "B")],
        )
        self.conn.commit()

    def cursor(self):
        return self._cursor


class KICDMarkSheetTests(unittest.TestCase):
    def setUp(self):
        import customtkinter as ctk

        try:
            self.root = ctk.CTk()
        except Exception as error:
            self.skipTest(f"No display available: {error}")
        self.root.withdraw()
        self.db = StubDB()
        self.config = {
            "school_name": "Test School",
            "academic_year": 2026,
            "cbc_levels": {
                "Grade 4": {
                    "Agriculture": {
                        "Term 1": {
                            "records": [
                                ["K001", "Amina Wanjiku", "Agriculture", "1.0", "1.1", "EE"],
                                ["K001", "Amina Wanjiku", "Agriculture", "1.0", "1.2", "ME"],
                            ]
                        }
                    }
                }
            },
        }
        patcher = patch.object(ui_marksheet_kicd, "get_subjects_for_class", lambda _name: ["AGRI", "ENG"])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.root.destroy)

    def _view(self, stream=None):
        return KICDMarkSheetView(
            self.root, self.db, "Grade 4", lambda: None, lambda: self.config,
            lambda updates: self.config.update(updates), stream=stream,
        )

    def test_normalize_score(self):
        self.assertEqual(normalize_score(None), "")
        self.assertEqual(normalize_score("ab"), "AB")
        self.assertEqual(normalize_score(78.0), "78")
        self.assertEqual(normalize_score("abc"), "")
        self.assertEqual(normalize_score(120), "")

    def test_columns_show_formative_summative_and_final_without_rank(self):
        view = self._view()
        self.assertNotIn("RANK", " ".join(str(view.tree.heading(c, "text")) for c in view.columns))
        amina, brian = view.rows
        amina["scores"]["AGRI"] = "78"
        brian["scores"]["AGRI"] = "45"
        self.assertEqual(view._cells(amina)[:4], ["Amina Wanjiku", "3.5 (EE)", "78%", "EE"])
        self.assertEqual(view._cells(brian)[1:4], ["n/a", "45%", "AE"])

    def test_save_writes_scores_ratings_and_points(self):
        view = self._view()
        amina, brian = view.rows
        amina["scores"]["AGRI"] = "78"
        brian["scores"]["ENG"] = "AB"
        view.save_marks(notify=False)
        cursor = self.db.cursor()
        cursor.execute("SELECT agri_s, agri_r, agri_p FROM primary_marks WHERE adm_no = 'A1'")
        self.assertEqual(cursor.fetchone(), (78, "ME", 3))
        cursor.execute("SELECT eng_s, eng_r, eng_p FROM primary_marks WHERE adm_no = 'A2'")
        self.assertEqual(cursor.fetchone(), ("AB", "AB", 0))

        reopened = self._view()
        self.assertEqual(reopened.rows[0]["scores"]["AGRI"], "78")
        self.assertEqual(reopened.rows[1]["scores"]["ENG"], "AB")

    def test_stream_selection_loads_only_that_stream(self):
        view = self._view("A")

        self.assertEqual([row["adm_no"] for row in view.rows], ["A1"])

    def test_term_without_strands_falls_back_to_exam_score(self):
        view = self._view()
        view.term_var.set("Term 2")
        view._term_changed("Term 2")
        amina = view.rows[0]
        amina["scores"]["AGRI"] = "85"
        self.assertEqual(view._cells(amina)[1:4], ["n/a", "85%", "EE"])
        self.assertEqual(self.config["marksheet_term"], "Term 2")

    def test_cloud_fetch_refreshes_term_ratings_without_marks(self):
        class CloudStub:
            def fetch_marks(self, _grade, _credentials):
                return {"success": True, "marks": []}

            def fetch_cbc_covered_strands(self, _grade, area, year, _credentials):
                return {
                    "success": True,
                    "strands": [{
                        "name": "Current Strand",
                        "sub_strands": [{"name": "Current Sub-strand", "terms": []}],
                    }],
                }

            def fetch_cbc_ratings(self, grade, area, term, year, _credentials):
                return {
                    "success": True,
                    "records": [["K001", "Amina Wanjiku", area, "Strand", "Sub-strand", "EE"]],
                }

        view = self._view()
        with (
            patch.object(ui_marksheet_kicd, "ask_cloud_credentials", return_value={"school_code": "s"}),
            patch.object(ui_marksheet_kicd, "CloudService", return_value=CloudStub()),
            patch.object(ui_marksheet_kicd.messagebox, "showinfo"),
        ):
            view.fetch_cloud_data()

        record = self.config["cbc_levels"]["Grade 4"]["Agriculture and Nutrition"]["2026|Term 1"]
        self.assertEqual(len(record["records"]), 1)
        strands = self.config["cbc_covered_strands"]["Grade 4"]["Agriculture and Nutrition"]["strands"]
        self.assertEqual(strands[0]["name"], "Current Strand")
        self.assertEqual(view._cells(view.rows[0])[1], "4.0 (EE)")


class SubjectSourceTests(unittest.TestCase):
    def test_subjects_come_from_selected_catalog_not_fallback_lists(self):
        config = {
            "subjects": {"primary": ["STALE"]},
            "subject_catalog": {
                "primary": [
                    {"short": "AGRI", "selected": True},
                    {"short": "STALE", "selected": False},
                ]
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "school_config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(config, handle)
            with patch.object(teachers_linked, "get_json_path", return_value=path):
                self.assertEqual(teachers_linked.get_subjects_for_class("Grade 4"), ["AGRI"])

    def test_missing_subject_configuration_returns_no_guessed_subjects(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "school_config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)
            with patch.object(teachers_linked, "get_json_path", return_value=path):
                self.assertEqual(teachers_linked.get_subjects_for_class("Grade 4"), [])


if __name__ == "__main__":
    unittest.main()
