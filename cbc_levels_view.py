from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from cbc_engine import SUBJECT_TO_LEARNING_AREA
from cloud_service import CloudService, ask_cloud_credentials

TERMS = ("Term 1", "Term 2", "Term 3")
LEVELS = ("EE", "ME", "AE", "BE", "AB")


class CBCLevelsView(ctk.CTkFrame):
    """Shows each learner's level per strand and sub-strand, as entered on the portal."""

    def __init__(self, parent, grade, subjects, school_config, save_config,
                 back_callback, dashboard_callback):
        super().__init__(parent, fg_color="transparent")
        self.grade = grade
        self.subjects = subjects
        self.school_config = school_config
        self.save_config = save_config
        self.back_callback = back_callback
        self.dashboard_callback = dashboard_callback
        self.subject_var = ctk.StringVar(value=subjects[0] if subjects else "")
        current_term = school_config.get("current_term")
        self.term_var = ctk.StringVar(value=current_term if current_term in TERMS else TERMS[0])
        self.current_year = self._int_or_none(school_config.get("academic_year")) or datetime.now().year
        self.year_var = ctk.StringVar(value=str(self.current_year))
        self._build_widgets()
        self._render()

    @staticmethod
    def _int_or_none(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _year_options(self):
        years = {self.current_year}
        for areas in self.school_config.get("cbc_levels", {}).get(self.grade, {}).values():
            for record in areas.values():
                year = self._int_or_none(record.get("academic_year"))
                if year:
                    years.add(year)
        return [str(year) for year in sorted(years, reverse=True)]

    @property
    def area_name(self):
        subject = self.subject_var.get().strip()
        return SUBJECT_TO_LEARNING_AREA.get(subject.upper(), subject)

    def _build_widgets(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 6))
        ctk.CTkLabel(header, text=f"{self.grade} Marked Strands", font=("Arial Bold", 26)).pack(side="left")
        ctk.CTkButton(
            header, text="Dashboard", width=110, fg_color="#e74c3c", hover_color="#c0392b",
            command=self.dashboard_callback,
        ).pack(side="right")
        ctk.CTkButton(header, text="\u2190 Back", width=90, command=self.back_callback).pack(
            side="right", padx=8
        )

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=(4, 6))
        ctk.CTkLabel(controls, text="Subject").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            controls, values=self.subjects or ["No subjects"], variable=self.subject_var,
            command=lambda _: self._render(), width=180,
        ).pack(side="left")
        ctk.CTkLabel(controls, text="Term").pack(side="left", padx=(16, 8))
        ctk.CTkOptionMenu(
            controls, values=list(TERMS), variable=self.term_var,
            command=lambda _: self._render(), width=110,
        ).pack(side="left")
        ctk.CTkLabel(controls, text="Year").pack(side="left", padx=(16, 8))
        ctk.CTkOptionMenu(
            controls, values=self._year_options(), variable=self.year_var,
            command=lambda _: self._render(), width=90,
        ).pack(side="left")
        ctk.CTkButton(
            controls, text="Fetch Marked Strands from Portal", height=36, command=self._fetch,
        ).pack(side="left", padx=16)

        self.status = ctk.CTkLabel(self, text="", anchor="w", text_color="gray60")
        self.status.pack(fill="x", padx=26, pady=(0, 6))

        table = ctk.CTkFrame(self)
        table.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)
        style = ttk.Style()
        style.configure("Levels.Treeview", rowheight=28, font=("Segoe UI", 11))
        style.configure("Levels.Treeview.Heading", font=("Segoe UI", 11, "bold"))
        self.tree = ttk.Treeview(
            table, columns=("number", "level"), style="Levels.Treeview", selectmode="browse"
        )
        self.tree.heading("#0", text="Strand / Sub-strand / Learner")
        self.tree.heading("number", text="Assessment Number")
        self.tree.heading("level", text="Level")
        self.tree.column("#0", width=520, stretch=True)
        self.tree.column("number", width=170, anchor="w")
        self.tree.column("level", width=200, anchor="center")
        self.tree.tag_configure("strand", font=("Segoe UI", 12, "bold"))
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vertical.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")

    def _record(self):
        by_area = self.school_config.get("cbc_levels", {}).get(self.grade, {}).get(self.area_name, {})
        record = by_area.get(f"{self.year_var.get()}|{self.term_var.get()}")
        if record is None:
            # Records fetched before years were tracked are stored under the term alone.
            legacy = by_area.get(self.term_var.get())
            if legacy and str(legacy.get("academic_year")) == self.year_var.get():
                return legacy
        return record

    def _fetch(self):
        if not self.subjects:
            messagebox.showwarning("Subject", "No subjects are configured for this class.", parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        year = int(self.year_var.get())
        result = CloudService().fetch_cbc_ratings(
            self.grade, self.area_name, self.term_var.get(), year, credentials
        )
        if not result.get("success"):
            messagebox.showerror(
                "Fetch Failed", result.get("message", "Could not fetch marked strands."), parent=self
            )
            return
        levels = self.school_config.setdefault("cbc_levels", {})
        by_area = levels.setdefault(self.grade, {}).setdefault(self.area_name, {})
        by_area[f"{year}|{self.term_var.get()}"] = {
            "academic_year": year,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "records": result.get("records", []),
        }
        self.save_config({"cbc_levels": levels})
        self._render()

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        record = self._record()
        if not record:
            self.status.configure(
                text="Nothing fetched for this subject and term yet. Click \"Fetch Marked Strands from Portal\"."
            )
            return
        # Records: assessment number, learner, area, strand, sub-strand, level.
        strands = {}
        for number, learner, _area, strand, sub_strand, level in record["records"]:
            strands.setdefault(strand, {}).setdefault(sub_strand, []).append((learner, number, level))
        self.status.configure(
            text=f"{self.area_name} \u00b7 {self.term_var.get()} \u00b7 fetched {record['fetched_at']} "
            f"(year {record['academic_year']})"
        )
        if not strands:
            self.status.configure(text=self.status.cget("text") + " \u00b7 no levels entered yet")
        for strand_name, sub_strands in strands.items():
            strand_id = self.tree.insert("", "end", text=strand_name, open=True, tags=("strand",))
            for sub_name, learners in sub_strands.items():
                counts = {level: sum(1 for _, _, value in learners if value == level) for level in LEVELS}
                summary = "  ".join(f"{level} {count}" for level, count in counts.items() if count)
                sub_id = self.tree.insert(
                    strand_id, "end", text=sub_name, values=("", summary), open=False
                )
                for learner, number, level in sorted(learners, key=lambda item: item[0].casefold()):
                    self.tree.insert(sub_id, "end", text=learner, values=(number, level))
