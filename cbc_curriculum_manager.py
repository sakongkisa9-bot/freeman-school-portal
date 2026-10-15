import json
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from cba_results_view import CBAResultsView
from cbc_curriculum_import import extract_curriculum_pdf
from cbc_engine import SUBJECT_TO_LEARNING_AREA, validate_curriculum
from cloud_service import CloudService, ask_cloud_credentials


class CBCCurriculumManager(ctk.CTkToplevel):
    def __init__(self, parent, grade, subjects, school_config, save_config, on_close=None):
        super().__init__(parent)
        self.grade = grade
        self.subjects = subjects
        self.school_config = school_config
        self.save_config = save_config
        self.on_close = on_close
        self.title(f"Competency Gradebook - {grade}")
        self.geometry("900x700")
        self.minsize(760, 560)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._close)

        current_year = datetime.now().year
        self.subject_var = ctk.StringVar(value=subjects[0] if subjects else "")
        self.term_var = ctk.StringVar(value="Term 1")
        self.type_var = ctk.StringVar(value="All")
        self.year_var = ctk.StringVar(value=str(current_year))
        self._build_widgets()
        self._load_area()

    def _build_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=f"{self.grade} Competency Gradebook",
            font=("Arial Bold", 22),
        ).grid(row=0, column=0, sticky="w")
        self.subject_menu = ctk.CTkOptionMenu(
            header, values=self.subjects or ["No subjects"],
            variable=self.subject_var, command=lambda _: self._load_area(), width=190,
        )
        self.subject_menu.grid(row=0, column=1, padx=8)
        ctk.CTkButton(
            header, text="Import Curriculum PDF", command=self._import_pdf
        ).grid(row=0, column=2)

        ctk.CTkLabel(
            self,
            text="Review the extracted strand and sub-strand names below before saving or publishing.",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.editor = ctk.CTkTextbox(self, wrap="none", font=("Consolas", 12))
        self.editor.grid(row=2, column=0, sticky="nsew", padx=20, pady=8)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        ctk.CTkButton(actions, text="Save on This Computer", command=self._save_local).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Publish Curriculum to Portal", command=self._publish).pack(side="left", padx=8)

        fetch = ctk.CTkFrame(self, fg_color="transparent")
        fetch.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 18))
        ctk.CTkLabel(fetch, text="Term").pack(side="left", padx=(0, 5))
        ctk.CTkOptionMenu(fetch, values=["Term 1", "Term 2", "Term 3"], variable=self.term_var, width=110).pack(side="left", padx=5)
        ctk.CTkLabel(fetch, text="Assessment").pack(side="left", padx=(10, 5))
        ctk.CTkOptionMenu(fetch, values=["All", "Formative", "Localized Summative"], variable=self.type_var, width=180).pack(side="left", padx=5)
        ctk.CTkLabel(fetch, text="Year").pack(side="left", padx=(10, 5))
        ctk.CTkEntry(fetch, textvariable=self.year_var, width=90).pack(side="left", padx=5)
        ctk.CTkButton(fetch, text="Fetch Portal Ratings", command=self._fetch_ratings).pack(side="right")

    @property
    def area_name(self):
        subject = self.subject_var.get().strip()
        return SUBJECT_TO_LEARNING_AREA.get(subject.upper(), subject)

    def _load_area(self):
        self.editor.delete("1.0", "end")
        areas = (
            self.school_config.get("cbc_curriculum", {})
            .get(self.grade, {})
            .get(self.area_name, [])
        )
        if not areas:
            areas = [{"name": self.area_name, "strands": []}]
        self.editor.insert("1.0", json.dumps(areas, indent=2, ensure_ascii=True))

    def _read_area(self):
        try:
            submitted = json.loads(self.editor.get("1.0", "end").strip())
            areas = validate_curriculum(submitted, self.grade)
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            raise ValueError(f"Check the curriculum JSON: {error}") from error
        if len(areas) != 1 or areas[0]["name"].casefold() != self.area_name.casefold():
            raise ValueError(f"This editor must contain one learning area named {self.area_name}.")
        return areas

    def _import_pdf(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose a KNEC curriculum design PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        try:
            strands = extract_curriculum_pdf(path)
        except Exception as error:
            messagebox.showerror("Curriculum Import Failed", str(error), parent=self)
            return
        area = [{"name": self.area_name, "strands": strands}]
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", json.dumps(area, indent=2, ensure_ascii=True))
        sub_strand_count = sum(len(strand["sub_strands"]) for strand in strands)
        messagebox.showinfo(
            "Review Imported Curriculum",
            f"Found {len(strands)} strands and {sub_strand_count} sub-strands. Review the names before publishing.",
            parent=self,
        )

    def _save_local(self):
        try:
            areas = self._read_area()
        except ValueError as error:
            messagebox.showerror("Invalid Curriculum", str(error), parent=self)
            return
        curriculum = self.school_config.setdefault("cbc_curriculum", {})
        curriculum.setdefault(self.grade, {})[self.area_name] = areas
        self.save_config({"cbc_curriculum": curriculum})
        messagebox.showinfo("Saved", "Curriculum saved on this computer.", parent=self)

    def _publish(self):
        try:
            areas = self._read_area()
        except ValueError as error:
            messagebox.showerror("Invalid Curriculum", str(error), parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        result = CloudService().upload_cbc_curriculum(self.grade, areas, credentials)
        if not result.get("success"):
            messagebox.showerror(
                "Publish Failed", result.get("message", "Could not publish curriculum."), parent=self
            )
            return
        curriculum = self.school_config.setdefault("cbc_curriculum", {})
        curriculum.setdefault(self.grade, {})[self.area_name] = areas
        self.save_config({"cbc_curriculum": curriculum})
        messagebox.showinfo("Published", result.get("message", "Curriculum published."), parent=self)

    def _fetch_ratings(self):
        try:
            academic_year = int(self.year_var.get())
            if not 2000 <= academic_year <= 2200:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Year", "Enter a year from 2000 to 2200.", parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        assessment_type = "" if self.type_var.get() == "All" else self.type_var.get()
        result = CloudService().fetch_cbc_ratings(
            self.grade,
            self.area_name,
            self.term_var.get(),
            academic_year,
            credentials,
            assessment_type,
        )
        if not result.get("success"):
            messagebox.showerror(
                "Fetch Failed", result.get("message", "Could not fetch competency ratings."), parent=self
            )
            return
        result.update(
            {
                "subject": self.area_name,
                "report_title": "Competency Ratings",
                "filename_suffix": "competency_ratings",
            }
        )
        result_window = ctk.CTkToplevel(self)
        result_window.title(f"{self.grade} {self.area_name} Ratings")
        result_window.geometry("1100x620")
        CBAResultsView(result_window, result).pack(fill="both", expand=True)

    def _close(self):
        self.destroy()
        if self.on_close:
            self.on_close()