import json
import os
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from cbc_engine import SUBJECT_TO_LEARNING_AREA
from cloud_service import CloudService, ask_cloud_credentials
from kicd_grading import ABSENT, LEVEL_POINTS, index_levels, level_from_percent, levels_for, subject_result
from teachers_linked import get_subjects_for_class, map_class_name_to_config_key

TABLES = {
    "playgroup": "playgroup_marks",
    "pp1": "pp1_marks",
    "pp2": "pp2_marks",
    "lower": "lower_marks",
    "primary": "primary_marks",
    "jss": "marksheet",
}
TERMS = ("Term 1", "Term 2", "Term 3")


def _column_base(subject, grade_type):
    if grade_type == "jss":
        return "".join(char if char.isalnum() else "_" for char in subject).lower().strip("_")
    return subject.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()


def normalize_score(value):
    """Return '' for none, 'AB' for absent, otherwise the whole-number score as text."""
    text = str(value if value is not None else "").strip()
    if text.upper() == ABSENT:
        return ABSENT
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if 0 <= number <= 100 else ""


class KICDMarkSheetView(ctk.CTkFrame):
    """Marksheet with Formative (70%), Summative exam and Final rating per subject, no ranking."""

    def __init__(self, parent, db, class_name, return_callback, load_config, save_config, initial_term=None):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.class_name = class_name
        self.return_callback = return_callback
        self.load_config = load_config
        self.save_config = save_config
        self.grade_type = map_class_name_to_config_key(class_name)
        self.table = TABLES.get(self.grade_type, "marksheet")
        self.subjects = get_subjects_for_class(class_name)
        config = load_config()
        saved_term = initial_term or config.get("marksheet_term")
        self.term_var = ctk.StringVar(value=saved_term if saved_term in TERMS else TERMS[0])
        self.rows = []
        self.level_index = {}
        self.editor = None
        self._ensure_columns()
        self._build_widgets()
        self._load_students()

    # ---- database -------------------------------------------------------
    def _base(self, subject):
        return _column_base(subject, self.grade_type)

    def _ensure_columns(self):
        cursor = self.db.cursor()
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table} (adm_no TEXT PRIMARY KEY)")
        cursor.execute(f"PRAGMA table_info({self.table})")
        existing = {row[1].lower() for row in cursor.fetchall()}
        for subject in self.subjects:
            base = self._base(subject)
            for suffix, kind in (("_s", "INTEGER"), ("_r", "TEXT"), ("_p", "INTEGER")):
                if f"{base}{suffix}" not in existing:
                    cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN {base}{suffix} {kind}")
        self.db.conn.commit()

    def _load_students(self):
        select = ", ".join(f"m.{self._base(subject)}_s" for subject in self.subjects)
        query = (
            f"SELECT s.adm_no, s.name, s.assessment_number{', ' + select if select else ''} "
            f"FROM students s LEFT JOIN {self.table} m ON s.adm_no = m.adm_no "
            "WHERE UPPER(s.grade) = UPPER(?) ORDER BY s.name COLLATE NOCASE"
        )
        cursor = self.db.cursor()
        cursor.execute(query, (self.class_name,))
        self.rows = [
            {
                "adm_no": record[0],
                "name": record[1] or "",
                "assessment_number": record[2] or "",
                "scores": {
                    subject: normalize_score(record[3 + index])
                    for index, subject in enumerate(self.subjects)
                },
            }
            for record in cursor.fetchall()
        ]
        self._load_levels()
        self._render()

    def _load_levels(self):
        config = self.load_config()
        term = self.term_var.get()
        self.level_index = {}
        for subject in self.subjects:
            area = SUBJECT_TO_LEARNING_AREA.get(subject.strip().upper(), subject.strip())
            record = config.get("cbc_levels", {}).get(self.class_name, {}).get(area, {}).get(term)
            if isinstance(record, dict):
                self.level_index[subject] = index_levels(record.get("records", []))

    # ---- widgets --------------------------------------------------------
    def _config_text(self):
        config = self.load_config()
        school = str(config.get("school_name", "")).upper()
        key = "current_exam_title" if self.grade_type == "jss" else f"{self.grade_type}_exam_title"
        exam = config.get(key) or config.get("current_exam_title") or "ASSESSMENT"
        return school, exam

    def _build_widgets(self):
        school, exam = self._config_text()
        self.exam_title = exam
        self.school_name = school
        self.header_label = ctk.CTkLabel(
            self,
            text=f"{school}  |  {self.class_name.upper()}  |  {exam}",
            font=("Arial Bold", 22), fg_color="#2e7d32", text_color="white",
            corner_radius=8, height=64,
        )
        self.header_label.pack(fill="x", padx=10, pady=10)

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=14)
        ctk.CTkLabel(controls, text="Formative term").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            controls, values=list(TERMS), variable=self.term_var, width=110,
            command=self._term_changed,
        ).pack(side="left")
        self.status = ctk.CTkLabel(controls, text="", text_color="gray60", anchor="w")
        self.status.pack(side="left", padx=16)

        ctk.CTkLabel(
            self,
            text="F = formative from strands (70%) · S = exam score · R = final rating. "
            "Double-click an S cell to edit it: leave blank for none, type AB for absent.",
            text_color="gray60", anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 0))

        table = ctk.CTkFrame(self)
        table.pack(fill="both", expand=True, padx=10, pady=8)
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)
        style = ttk.Style()
        style.configure("KICD.Treeview", rowheight=30, font=("Segoe UI", 11))
        style.configure("KICD.Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.columns = ["name"] + [
            f"{index}_{part}" for index in range(len(self.subjects)) for part in ("F", "S", "R")
        ]
        self.tree = ttk.Treeview(
            table, columns=self.columns, show="headings", style="KICD.Treeview", selectmode="browse"
        )
        self.tree.heading("name", text="STUDENT NAME")
        self.tree.column("name", width=230, minwidth=160, stretch=False, anchor="w")
        for index, subject in enumerate(self.subjects):
            label = subject.upper()[:8]
            for part, width in (("F", 92), ("S", 62), ("R", 52)):
                column = f"{index}_{part}"
                self.tree.heading(column, text=f"{label} {part}")
                self.tree.column(column, width=width, minwidth=46, stretch=False, anchor="center")
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", self._begin_edit)

        bar = ctk.CTkFrame(self, fg_color="gray20", height=60)
        bar.pack(side="bottom", fill="x")
        for text, color, command in (
            ("\U0001F4BE Save Marks", "#2e7d32", lambda: self.save_marks()),
            ("\u2601 Fetch from Cloud", "#1f538d", self.fetch_cloud_data),
            ("\U0001F5A8 Print PDF", "#f57c00", self.print_pdf),
            ("\U0001F504 Refresh", "#34495e", self._refresh),
        ):
            ctk.CTkButton(bar, text=text, fg_color=color, command=command).pack(
                side="left", padx=5, pady=15
            )
        ctk.CTkButton(
            bar, text="\u2B05 Back to Dashboard", fg_color="#942727", hover_color="#7a1f1f",
            command=self.return_callback,
        ).pack(side="right", padx=20, pady=15)

    # ---- display --------------------------------------------------------
    def _cells(self, row):
        values = [row["name"]]
        for subject in self.subjects:
            levels = levels_for(
                self.level_index.get(subject, {}), row["assessment_number"], row["name"]
            )
            result = subject_result(levels, row["scores"].get(subject, ""))
            values.extend([result["F"], result["S"], result["R"]])
        return values

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(self.rows):
            row["item"] = self.tree.insert("", "end", iid=str(index), values=self._cells(row))
        covered = [subject for subject in self.subjects if subject in self.level_index]
        self.status.configure(
            text="Strands loaded for: " + (", ".join(covered) if covered else "none (F shows n/a)")
            + ". Fetch them on the Performance Dashboard first."
        )

    def _term_changed(self, term):
        self.save_config({"marksheet_term": term})
        self._load_levels()
        self._render()

    def _refresh(self):
        self._load_students()

    # ---- editing --------------------------------------------------------
    def _begin_edit(self, event):
        self._end_edit(commit=False)
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        item = self.tree.identify_row(event.y)
        column_id = self.columns[int(self.tree.identify_column(event.x)[1:]) - 1]
        if not item or not column_id.endswith("_S"):
            return
        subject = self.subjects[int(column_id.split("_")[0])]
        row = self.rows[int(item)]
        x, y, width, height = self.tree.bbox(item, column_id)
        entry = ttk.Entry(self.tree, justify="center")
        entry.insert(0, row["scores"].get(subject, ""))
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.select_range(0, "end")
        entry.bind("<Return>", lambda _e: self._end_edit(commit=True))
        entry.bind("<Escape>", lambda _e: self._end_edit(commit=False))
        entry.bind("<FocusOut>", lambda _e: self._end_edit(commit=True))
        self.editor = (entry, row, subject)

    def _end_edit(self, commit):
        if not self.editor:
            return
        entry, row, subject = self.editor
        self.editor = None
        text = entry.get().strip()
        entry.destroy()
        if not commit:
            return
        if text and text.upper() != ABSENT and not (text.isdigit() and 0 <= int(text) <= 100):
            messagebox.showwarning(
                "Invalid Score", "Enter a score from 0 to 100, AB for absent, or leave it blank.",
                parent=self,
            )
            return
        row["scores"][subject] = ABSENT if text.upper() == ABSENT else text
        self.tree.item(row["item"], values=self._cells(row))

    # ---- saving ---------------------------------------------------------
    def save_marks(self, notify=True):
        self._end_edit(commit=True)
        cursor = self.db.cursor()
        for row in self.rows:
            cursor.execute(f"SELECT 1 FROM {self.table} WHERE adm_no = ?", (row["adm_no"],))
            if not cursor.fetchone():
                cursor.execute(f"INSERT INTO {self.table} (adm_no) VALUES (?)", (row["adm_no"],))
            assignments, values = [], []
            for subject in self.subjects:
                score = row["scores"].get(subject, "")
                # Stored rating is the exam-only level so the classic marksheets read the same data
                rating = ABSENT if score == ABSENT else (level_from_percent(float(score)) if score else None)
                base = self._base(subject)
                assignments += [f"{base}_s = ?", f"{base}_r = ?", f"{base}_p = ?"]
                values += [
                    ABSENT if score == ABSENT else (int(score) if score else None),
                    rating,
                    LEVEL_POINTS.get(rating, 0),
                ]
            if assignments:
                cursor.execute(
                    f"UPDATE {self.table} SET {', '.join(assignments)} WHERE adm_no = ?",
                    (*values, row["adm_no"]),
                )
        self.db.conn.commit()
        if notify:
            messagebox.showinfo("Saved", "Marks saved.", parent=self)

    def fetch_cloud_data(self):
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        result = CloudService().fetch_marks(self.class_name, credentials)
        if not result.get("success"):
            messagebox.showerror(
                "Cloud Fetch Failed", result.get("message", "Could not fetch cloud marks."), parent=self
            )
            return
        records = result.get("marks", [])
        if not records:
            messagebox.showinfo("Cloud Fetch", "No marks found on the cloud for this class.", parent=self)
            return
        by_adm = {str(record.get("adm_no", "")).strip(): record for record in records}
        by_name = {"".join(str(record.get("student_name", "")).split()).lower(): record for record in records}
        matched = 0
        for row in self.rows:
            record = by_adm.get(str(row["adm_no"]).strip()) or by_name.get(
                "".join(row["name"].split()).lower()
            )
            if not record:
                continue
            matched += 1
            scores = record.get("scores", {})
            for subject in self.subjects:
                key = next(
                    (name for name in scores if subject.strip().lower() in name.lower()
                     or name.lower() in subject.strip().lower()),
                    None,
                )
                if key is None:
                    continue
                entry = scores[key]
                value = entry.get("score", "") if isinstance(entry, dict) else entry
                row["scores"][subject] = normalize_score(value)
            self.tree.item(row["item"], values=self._cells(row))
        self.save_marks(notify=False)
        messagebox.showinfo("Cloud Fetch", f"Synchronized {matched} student records.", parent=self)

    # ---- printing -------------------------------------------------------
    def print_pdf(self):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self.class_name}_marksheet.pdf".replace(" ", "_"),
        )
        if not path:
            return
        top = [""] + [subject.upper() for subject in self.subjects for _ in range(3)]
        sub = ["STUDENT NAME"] + ["F", "S", "R"] * len(self.subjects)
        body = [self._cells(row) for row in self.rows]
        table = Table([top, sub, *body], repeatRows=2)
        style = [
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#2e7d32")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]
        for index in range(len(self.subjects)):
            start = 1 + index * 3
            style.append(("SPAN", (start, 0), (start + 2, 0)))
        table.setStyle(TableStyle(style))
        styles = getSampleStyleSheet()
        title = f"{self.school_name} | {self.class_name.upper()} | {self.exam_title} | {self.term_var.get()}"
        SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=18, rightMargin=18).build(
            [Paragraph(title, styles["Heading3"]), Spacer(1, 6), table]
        )
        messagebox.showinfo("Print PDF", "Marksheet PDF saved.", parent=self)
        if os.name == "nt":
            os.startfile(path)
