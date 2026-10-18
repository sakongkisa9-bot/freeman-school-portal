from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from academic_periods import TERMS, available_terms
from cbc_engine import SUBJECT_TO_LEARNING_AREA
from cloud_service import CloudService, ask_cloud_credentials

LEVELS = ("EE", "ME", "AE", "BE", "AB")


class CBCLevelsView(ctk.CTkFrame):
    """Shows each learner's level per strand and sub-strand, as entered on the portal."""

    def __init__(self, parent, grade, subjects, school_config, save_config,
                 back_callback, dashboard_callback, view_year=None):
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
        selected_year = self._int_or_none(view_year) or self.current_year
        self.dashboard_view_year = self._int_or_none(view_year)
        self.year_var = ctk.StringVar(value=str(selected_year))
        self.fetch_buttons = []
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

    def _year_changed(self, _year):
        self._sync_period_controls()
        self._render()

    def _sync_period_controls(self):
        terms = available_terms(
            self.year_var.get(), self.current_year, self.school_config.get("current_term") or TERMS[0]
        )
        self.term_menu.configure(values=list(terms))
        if self.term_var.get() not in terms:
            self.term_var.set(terms[-1])
        state = "disabled" if self.year_var.get() != str(self.current_year) else "normal"
        for button in self.fetch_buttons:
            button.configure(state=state)

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
        self.term_menu = ctk.CTkOptionMenu(
            controls, values=list(TERMS), variable=self.term_var,
            command=lambda _: self._render(), width=110,
        )
        self.term_menu.pack(side="left")
        ctk.CTkLabel(controls, text="Year").pack(side="left", padx=(16, 8))
        self.year_menu = ctk.CTkOptionMenu(
            controls, values=self._year_options(), variable=self.year_var,
            command=self._year_changed, width=90,
        )
        self.year_menu.pack(side="left")
        if self.dashboard_view_year is not None:
            self.year_menu.configure(state="disabled")
        self.fetch_buttons.append(ctk.CTkButton(
            controls, text="Fetch Marked Strands from Portal", height=36, command=self._fetch,
        ))
        self.fetch_buttons[-1].pack(side="left", padx=16)
        self.fetch_buttons.append(ctk.CTkButton(
            controls, text="Fetch All", height=36, command=self._fetch_all,
        ))
        self.fetch_buttons[-1].pack(side="left")

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
        success, error = self._fetch_area(self.area_name, self.term_var.get(), year, credentials)
        if not success:
            messagebox.showerror("Fetch Failed", error, parent=self)
            return
        self.save_config({"cbc_levels": self.school_config["cbc_levels"]})
        self._render()

    def _fetch_all(self):
        if not self.subjects:
            messagebox.showwarning("Subject", "No subjects are configured for this class.", parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        year = int(self.year_var.get())
        term = self.term_var.get()
        areas = list(dict.fromkeys(
            SUBJECT_TO_LEARNING_AREA.get(subject.strip().upper(), subject.strip())
            for subject in self.subjects
        ))
        failures = []
        fetched = 0
        for area in areas:
            success, _error = self._fetch_area(area, term, year, credentials)
            if success:
                fetched += 1
            else:
                failures.append(area)
        if fetched:
            self.save_config({"cbc_levels": self.school_config["cbc_levels"]})
        self._render()
        if failures:
            messagebox.showwarning(
                "Fetch All", f"Fetched {fetched} of {len(areas)} subjects. Failed: {', '.join(failures)}.",
                parent=self,
            )
        else:
            messagebox.showinfo("Fetch All", f"Fetched marked strands for all {fetched} subjects.", parent=self)

    def _fetch_area(self, area, term, year, credentials):
        result = CloudService().fetch_cbc_ratings(
            self.grade, area, term, year, credentials
        )
        if not result.get("success"):
            return False, result.get("message", "Could not fetch marked strands.")
        evidence_by_key = {
            (str(row[0]), str(row[3]), str(row[4])): row[6]
            for row in result.get("evidence_records", [])
            if len(row) > 6
        }
        records = [
            [*row, evidence_by_key.get((str(row[0]), str(row[3]), str(row[4])), "")]
            for row in result.get("records", [])
        ]
        levels = self.school_config.setdefault("cbc_levels", {})
        by_area = levels.setdefault(self.grade, {}).setdefault(area, {})
        by_area[f"{year}|{term}"] = {
            "academic_year": year,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "records": records,
        }
        return True, None

    def _render(self):
        self._sync_period_controls()
        self.tree.delete(*self.tree.get_children())
        record = self._record()
        if not record:
            note = "Past years are read-only. " if self.year_var.get() != str(self.current_year) else ""
            self.status.configure(
                text=note + "Nothing fetched for this subject and term yet."
            )
            return
        # Records: assessment number, learner, area, strand, sub-strand, level.
        strands = {}
        for row in record["records"]:
            if len(row) < 6:
                continue
            number, learner, _area, strand, sub_strand, level = row[:6]
            strands.setdefault(strand, {}).setdefault(sub_strand, []).append((learner, number, level))
        self.status.configure(
            text=f"{self.area_name} \u00b7 {self.term_var.get()} \u00b7 fetched {record['fetched_at']} "
            f"(year {record['academic_year']})"
            + (" \u00b7 read-only" if self.year_var.get() != str(self.current_year) else "")
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
