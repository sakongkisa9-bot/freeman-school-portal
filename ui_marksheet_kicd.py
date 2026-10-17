import json
import os
from datetime import datetime
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

    def __init__(self, parent, db, class_name, return_callback, load_config, save_config, initial_term=None, stream=None):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.class_name = class_name
        self.stream = stream
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
        params = [self.class_name]
        if self.stream:
            query = query.replace(
                "ORDER BY s.name COLLATE NOCASE",
                "AND UPPER(TRIM(s.stream)) = UPPER(?) ORDER BY s.name COLLATE NOCASE",
            )
            params.append(self.stream)
        cursor.execute(query, params)
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
        year = str(config.get("academic_year") or "")
        self.level_index = {}
        for subject in self.subjects:
            area = self._learning_area(subject, config)
            area_names = [area]
            if area == "Agriculture and Nutrition":
                area_names.append("Agriculture")
            record = None
            for area_name in area_names:
                by_area = config.get("cbc_levels", {}).get(self.class_name, {}).get(area_name, {})
                record = by_area.get(f"{year}|{term}") if year else None
                if record is None:
                    record = by_area.get(term)
                if record is not None:
                    break
            if isinstance(record, dict):
                self.level_index[subject] = index_levels(record.get("records", []))

    def _learning_area(self, subject, config):
        normalized = subject.strip().upper()
        area = SUBJECT_TO_LEARNING_AREA.get(normalized)
        if area:
            return area
        names = config.get("subject_names", {}).get(self.grade_type, {})
        if subject in names:
            return names[subject]
        for items in (config.get("subject_catalog") or {}).values():
            for item in items:
                if item.get("short", "").strip().upper() == normalized:
                    return item.get("name", subject).strip()
        return subject.strip()

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
            + "."
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
        service = CloudService()
        result = service.fetch_marks(self.class_name, credentials)
        if not result.get("success"):
            messagebox.showerror(
                "Cloud Fetch Failed", result.get("message", "Could not fetch cloud marks."), parent=self
            )
            return
        records = result.get("marks", [])
        config = self.load_config()
        try:
            year = int(config.get("academic_year"))
        except (TypeError, ValueError):
            year = datetime.now().year
        term = self.term_var.get()
        levels = config.setdefault("cbc_levels", {})
        by_area = levels.setdefault(self.class_name, {})
        covered_by_grade = config.setdefault("cbc_covered_strands", {})
        covered_by_area = covered_by_grade.setdefault(self.class_name, {})
        ratings_synced = []
        ratings_failed = []
        strands_synced = []
        strands_failed = []
        for subject in self.subjects:
            area = self._learning_area(subject, config)
            strands_result = service.fetch_cbc_covered_strands(
                self.class_name, area, year, credentials
            )
            if strands_result.get("success"):
                covered_by_area[area] = {
                    "academic_year": year,
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "strands": strands_result.get("strands", []),
                }
                strands_synced.append(subject)
            else:
                strands_failed.append(subject)
            rating_result = service.fetch_cbc_ratings(
                self.class_name, area, term, year, credentials
            )
            if rating_result.get("success"):
                by_area.setdefault(area, {})[f"{year}|{term}"] = {
                    "academic_year": year,
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "records": rating_result.get("records", []),
                }
                ratings_synced.append(subject)
            else:
                ratings_failed.append(subject)
        self.save_config({"cbc_levels": levels, "cbc_covered_strands": covered_by_grade})
        self._load_levels()

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
            subject_names = config.get("subject_names", {}).get(self.grade_type, {})
            for subject in self.subjects:
                aliases = {subject.strip().casefold()}
                full_name = subject_names.get(subject)
                if full_name:
                    aliases.add(full_name.strip().casefold())
                key = next((name for name in scores if str(name).strip().casefold() in aliases), None)
                if key is None:
                    continue
                entry = scores[key]
                value = entry.get("score", "") if isinstance(entry, dict) else entry
                row["scores"][subject] = normalize_score(value)
            self.tree.item(row["item"], values=self._cells(row))
        if records:
            self.save_marks(notify=False)
        self._render()
        details = [f"Synchronized {matched} student records."] if records else [
            "No marks found on the cloud for this class."
        ]
        if ratings_synced:
            details.append(f"Refreshed strand ratings for {len(ratings_synced)} subjects.")
        if ratings_failed:
            details.append("Could not refresh strands for: " + ", ".join(ratings_failed) + ".")
        if strands_synced:
            details.append(f"Updated strand lists for {len(strands_synced)} subjects.")
        if strands_failed:
            details.append("Could not update strand lists for: " + ", ".join(strands_failed) + ".")
        messagebox.showinfo("Cloud Fetch", "\n".join(details), parent=self)

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
