import json
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from fpdf import FPDF

from academic_periods import TERMS


class ArchivedReportFormsView(ctk.CTkFrame):
    def __init__(self, parent, db, class_name, year, school_config, back_callback, stream=None):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.class_name = class_name
        self.year = int(year)
        self.stream = stream
        self.history_class = f"{class_name} [{stream}]" if stream else class_name
        self.school_config = school_config or {}
        self.back_callback = back_callback
        self.selected_report = None
        self.grade_type = self._grade_type(class_name)
        default_subjects = {
            "playgroup": ["MATH", "CREAT", "ENV"],
            "pp1": ["MATH", "ENV", "PSYCH", "REL"],
            "pp2": ["MATH", "ENV", "PSYCH", "REL"],
            "lower": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
            "primary": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
            "jss": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"],
        }
        self.subjects = self.school_config.get("subjects", {}).get(self.grade_type) or default_subjects[self.grade_type]
        self.stride = 3 if self.grade_type == "jss" else 2

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(18, 8))
        ctk.CTkLabel(
            header,
            text=f"{class_name} Report Forms | {self.year} | READ-ONLY",
            font=("Arial Bold", 22),
        ).pack(side="left")
        ctk.CTkButton(header, text="Back", width=90, command=back_callback).pack(side="right")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(controls, text="Term").pack(side="left", padx=(0, 8))
        self.term_var = ctk.StringVar(value=TERMS[0])
        ctk.CTkOptionMenu(
            controls,
            values=list(TERMS),
            variable=self.term_var,
            command=lambda _value: self._refresh_exams(),
            width=130,
        ).pack(side="left")
        ctk.CTkLabel(controls, text="Exam").pack(side="left", padx=(16, 8))
        self.exam_menu = ctk.CTkOptionMenu(
            controls, values=["-"], command=lambda _value: self._load_exam(), width=260
        )
        self.exam_menu.pack(side="left")
        self.status = ctk.CTkLabel(controls, text="", text_color="gray60")
        self.status.pack(side="left", padx=16)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=(8, 20))
        content.grid_columnconfigure(0, weight=1, uniform="historical-report")
        content.grid_columnconfigure(1, weight=2, uniform="historical-report")
        content.grid_rowconfigure(0, weight=1)
        self.student_panel = ctk.CTkScrollableFrame(content, label_text="Archived students")
        self.student_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.detail_panel = ctk.CTkScrollableFrame(content, label_text="Report form")
        self.detail_panel.grid(row=0, column=1, sticky="nsew")
        self._refresh_exams()

    @staticmethod
    def _grade_type(class_name):
        normalized = class_name.strip().lower()
        if "play" in normalized:
            return "playgroup"
        if "pp1" in normalized or "pre-primary 1" in normalized:
            return "pp1"
        if "pp2" in normalized or "pre-primary 2" in normalized:
            return "pp2"
        if any(f"grade {number}" in normalized for number in (1, 2, 3)):
            return "lower"
        if any(f"grade {number}" in normalized for number in (4, 5, 6)):
            return "primary"
        return "jss"

    @staticmethod
    def _pdf_text(value):
        return str(value or "").encode("latin-1", "replace").decode("latin-1")

    def _refresh_exams(self):
        records = self.db.get_previous_exams_for_term(
            self.history_class, self.term_var.get(), self.year
        )
        self.exam_names = [name for name, _date in records]
        labels = self.exam_names or [f"No archived exam in {self.term_var.get()}"]
        self.exam_menu.configure(values=labels)
        self.exam_menu.set(labels[0])
        self._load_exam()

    def _load_exam(self):
        for child in self.student_panel.winfo_children():
            child.destroy()
        for child in self.detail_panel.winfo_children():
            child.destroy()
        exam_name = self.exam_menu.get()
        if exam_name not in getattr(self, "exam_names", []):
            self.status.configure(text="No archived report data for this term.")
            return
        marks_data, _summary = self.db.get_previous_exam_data(
            exam_name, self.history_class, self.year
        )
        try:
            rows = json.loads(marks_data) if isinstance(marks_data, str) else marks_data
        except (TypeError, ValueError):
            rows = []
        self.records = [row for row in rows if isinstance(row, (list, tuple)) and row] \
            if isinstance(rows, list) else []
        self.exam_name = exam_name
        self.status.configure(
            text="Archived marks only; comments and roster details were not saved."
        )
        for index, row in enumerate(self.records):
            ctk.CTkButton(
                self.student_panel,
                text=str(row[0]),
                anchor="w",
                command=lambda selected=index: self._show_student(selected),
            ).pack(fill="x", padx=4, pady=3)
        if self.records:
            self._show_student(0)

    def _student_subjects(self, row):
        parsed = []
        for index, subject in enumerate(self.subjects):
            score_index = 1 + index * self.stride
            rating_index = score_index + 1
            points_index = score_index + 2
            score = row[score_index] if score_index < len(row) else ""
            rating = row[rating_index] if rating_index < len(row) else ""
            points = row[points_index] if self.stride == 3 and points_index < len(row) else ""
            parsed.append((subject, score, rating, points))
        return parsed

    def _show_student(self, index):
        row = self.records[index]
        parsed = self._student_subjects(row)
        self.selected_report = (str(row[0]), parsed, row)
        for child in self.detail_panel.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.detail_panel, text=str(row[0]), font=("Arial Bold", 20)
        ).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            self.detail_panel,
            text=f"{self.class_name} | {self.exam_name} | {self.term_var.get()} {self.year}",
            text_color="gray60",
        ).pack(anchor="w", padx=14, pady=(0, 12))
        for subject, score, rating, points in parsed:
            text = f"{subject}:  {score}   {rating}"
            if self.stride == 3:
                text += f"   {points} points"
            ctk.CTkLabel(self.detail_panel, text=text, anchor="w").pack(
                fill="x", padx=14, pady=4
            )
        total_index = 1 + len(self.subjects) * self.stride
        total = row[total_index] if total_index < len(row) else ""
        average = row[total_index + 1] if total_index + 1 < len(row) else ""
        ctk.CTkLabel(
            self.detail_panel,
            text=f"Total: {total}    Average: {average}",
            font=("Arial Bold", 14),
        ).pack(anchor="w", padx=14, pady=12)
        ctk.CTkButton(
            self.detail_panel, text="Print Report Form", command=self._print_selected
        ).pack(anchor="w", padx=14, pady=(4, 16))

    def _print_selected(self):
        if not self.selected_report:
            return
        student_name, subjects, row = self.selected_report
        initial_name = f"{student_name.replace(' ', '_')}_{self.year}_{self.term_var.get().replace(' ', '_')}.pdf"
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".pdf",
            initialfile=initial_name,
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, self._pdf_text(self.school_config.get("school_name", "School")), ln=1, align="C")
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 9, "HISTORICAL REPORT FORM", ln=1, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Learner: {self._pdf_text(student_name)}", ln=1)
        pdf.cell(0, 8, f"Class: {self._pdf_text(self.class_name)}    Exam: {self._pdf_text(self.exam_name)}", ln=1)
        pdf.cell(0, 8, f"Term: {self.term_var.get()}    Academic year: {self.year}", ln=1)
        pdf.ln(4)
        headers = ["Subject", "Score", "Rating"] + (["Points"] if self.stride == 3 else [])
        widths = [80, 35, 35] + ([35] if self.stride == 3 else [])
        pdf.set_font("Arial", "B", 10)
        for heading, width in zip(headers, widths):
            pdf.cell(width, 8, heading, border=1)
        pdf.ln()
        pdf.set_font("Arial", "", 10)
        for subject, score, rating, points in subjects:
            values = [subject, score, rating] + ([points] if self.stride == 3 else [])
            for value, width in zip(values, widths):
                pdf.cell(width, 8, self._pdf_text(value)[:32], border=1)
            pdf.ln()
        total_index = 1 + len(self.subjects) * self.stride
        total = row[total_index] if total_index < len(row) else ""
        average = row[total_index + 1] if total_index + 1 < len(row) else ""
        pdf.ln(4)
        pdf.cell(0, 8, f"Total: {self._pdf_text(total)}    Average: {self._pdf_text(average)}", ln=1)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(0, 5, "Generated from the archived marks snapshot. Comments and historical roster details were not archived.")
        pdf.output(path)
        messagebox.showinfo("Report Saved", f"PDF exported to {os.path.basename(path)}", parent=self)