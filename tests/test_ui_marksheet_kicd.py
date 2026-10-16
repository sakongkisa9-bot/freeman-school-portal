import sqlite3
import unittest
from unittest.mock import patch

import ui_marksheet_kicd
from ui_marksheet_kicd import KICDMarkSheetView, normalize_score


class StubDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self._cursor = self.conn.cursor()
        self._cursor.execute(
            "CREATE TABLE students (adm_no TEXT PRIMARY KEY, name TEXT, grade TEXT, assessment_number TEXT)"
        )
        self._cursor.executemany(
            "INSERT INTO students VALUES (?, ?, ?, ?)",
            [("A1", "Amina Wanjiku", "Grade 4", "K001"), ("A2", "Brian Otieno", "Grade 4", "K002")],
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

    def _view(self):
        return KICDMarkSheetView(
            self.root, self.db, "Grade 4", lambda: None, lambda: self.config,
            lambda updates: self.config.update(updates),
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

    def test_term_without_strands_falls_back_to_exam_score(self):
        view = self._view()
        view.term_var.set("Term 2")
        view._term_changed("Term 2")
        amina = view.rows[0]
        amina["scores"]["AGRI"] = "85"
        self.assertEqual(view._cells(amina)[1:4], ["n/a", "85%", "EE"])
        self.assertEqual(self.config["marksheet_term"], "Term 2")


if __name__ == "__main__":
    unittest.main()
