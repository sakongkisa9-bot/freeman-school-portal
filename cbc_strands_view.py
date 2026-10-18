from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from cbc_engine import SUBJECT_TO_LEARNING_AREA
from cloud_service import CloudService, ask_cloud_credentials

CHECK = "\u2713"
EMPTY = "\u25cb"


class CBCStrandsView(ctk.CTkFrame):
    def __init__(self, parent, grade, subjects, school_config, save_config,
                 back_callback, dashboard_callback, view_year=None):
        super().__init__(parent, fg_color="transparent")
        self.grade = grade
        self.subjects = subjects
        self.school_config = school_config
        self.save_config = save_config
        self.back_callback = back_callback
        self.dashboard_callback = dashboard_callback
        try:
            self.view_year = int(view_year or school_config.get("academic_year"))
        except (TypeError, ValueError):
            self.view_year = datetime.now().year
        try:
            self.current_year = int(school_config.get("academic_year"))
        except (TypeError, ValueError):
            self.current_year = datetime.now().year
        self.subject_var = ctk.StringVar(value=subjects[0] if subjects else "")
        self._build_widgets()
        self._render()

    @property
    def area_name(self):
        subject = self.subject_var.get().strip()
        return SUBJECT_TO_LEARNING_AREA.get(subject.upper(), subject)

    def _build_widgets(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 6))
        ctk.CTkLabel(header, text=f"{self.grade} Strands", font=("Arial Bold", 26)).pack(side="left")
        ctk.CTkButton(
            header, text="Dashboard", width=110, fg_color="#e74c3c", hover_color="#c0392b",
            command=self.dashboard_callback,
        ).pack(side="right")
        ctk.CTkButton(
            header, text="\u2190 Back", width=90, command=self.back_callback,
        ).pack(side="right", padx=8)

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=(4, 6))
        ctk.CTkLabel(controls, text="Subject").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            controls, values=self.subjects or ["No subjects"], variable=self.subject_var,
            command=lambda _: self._render(), width=200,
        ).pack(side="left")
        self.fetch_button = ctk.CTkButton(
            controls, text="Fetch Strands from Portal", height=36, command=self._fetch,
        )
        self.fetch_button.pack(side="left", padx=16)
        self.fetch_all_button = ctk.CTkButton(
            controls, text="Fetch All", height=36, command=self._fetch_all,
        )
        self.fetch_all_button.pack(side="left")
        if self.view_year != self.current_year:
            self.fetch_button.configure(state="disabled")
            self.fetch_all_button.configure(state="disabled")

        self.status = ctk.CTkLabel(self, text="", anchor="w", text_color="gray60")
        self.status.pack(fill="x", padx=26, pady=(0, 6))
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))

    def _saved_record(self):
        record = self.school_config.get("cbc_covered_strands", {}).get(self.grade, {}).get(self.area_name)
        if not isinstance(record, dict) or "strands" not in record:
            return None
        try:
            record_year = int(record.get("academic_year"))
        except (TypeError, ValueError):
            record_year = self.current_year
        return record if record_year == self.view_year else None

    def _fetch(self):
        if self.view_year != self.current_year:
            return
        if not self.subjects:
            messagebox.showwarning("Subject", "No subjects are configured for this class.", parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        try:
            year = int(self.school_config.get("academic_year"))
        except (TypeError, ValueError):
            year = datetime.now().year
        result = CloudService().fetch_cbc_covered_strands(self.grade, self.area_name, year, credentials)
        if not result.get("success"):
            messagebox.showerror(
                "Fetch Failed", result.get("message", "Could not fetch strands."), parent=self
            )
            return
        self._save_fetched_strands(self.area_name, year, result)
        self.save_config({"cbc_covered_strands": self.school_config["cbc_covered_strands"]})
        self._render()

    def _fetch_all(self):
        if self.view_year != self.current_year:
            return
        if not self.subjects:
            messagebox.showwarning("Subject", "No subjects are configured for this class.", parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        try:
            year = int(self.school_config.get("academic_year"))
        except (TypeError, ValueError):
            year = datetime.now().year

        areas = list(dict.fromkeys(
            SUBJECT_TO_LEARNING_AREA.get(subject.strip().upper(), subject.strip())
            for subject in self.subjects
        ))
        service = CloudService()
        failures = []
        fetched = 0
        for area in areas:
            result = service.fetch_cbc_covered_strands(self.grade, area, year, credentials)
            if not result.get("success"):
                failures.append(area)
                continue
            self._save_fetched_strands(area, year, result)
            fetched += 1
        if fetched:
            self.save_config({"cbc_covered_strands": self.school_config["cbc_covered_strands"]})
        self._render()
        if failures:
            messagebox.showwarning(
                "Fetch All", f"Fetched {fetched} of {len(areas)} subjects. Failed: {', '.join(failures)}.",
                parent=self,
            )
        else:
            messagebox.showinfo("Fetch All", f"Fetched strands for all {fetched} subjects.", parent=self)

    def _save_fetched_strands(self, area, year, result):
        record = {
            "academic_year": year,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "strands": result.get("strands", []),
        }
        by_grade = self.school_config.setdefault("cbc_covered_strands", {})
        grade_records = by_grade.get(self.grade)
        if not isinstance(grade_records, dict) or "areas" in grade_records:
            grade_records = {}
        grade_records[area] = record
        by_grade[self.grade] = grade_records

    def _render(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        record = self._saved_record()
        if not record:
            self.status.configure(text="")
            ctk.CTkLabel(
                self.list_frame,
                text="Nothing fetched for this subject yet. Click \"Fetch Strands from Portal\".",
                text_color="gray60",
            ).pack(pady=40)
            return

        strands = record["strands"]
        covered_total = sum(1 for strand in strands for sub in strand["sub_strands"] if sub["terms"])
        total = sum(len(strand["sub_strands"]) for strand in strands)
        self.status.configure(
            text=f"{self.area_name} \u00b7 {covered_total} of {total} sub-strands covered \u00b7 "
            f"fetched {record['fetched_at']} (year {record['academic_year']})"
        )
        for strand in strands:
            subs = strand["sub_strands"]
            covered = sum(1 for sub in subs if sub["terms"])
            done = bool(subs) and covered == len(subs)
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=(14, 2))
            ctk.CTkLabel(
                row,
                text=f"{CHECK + ' ' if done else ''}{strand['name']}",
                font=("Arial Bold", 17),
                text_color="#10b981" if done else None,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=f"{covered} of {len(subs)} covered", text_color="gray60"
            ).pack(side="right")
            for sub in subs:
                line = ctk.CTkFrame(self.list_frame, fg_color="transparent")
                line.pack(fill="x", padx=(32, 8), pady=1)
                is_covered = bool(sub["terms"])
                ctk.CTkLabel(
                    line,
                    text=f"{CHECK if is_covered else EMPTY}  {sub['name']}",
                    anchor="w",
                    text_color="#10b981" if is_covered else "gray60",
                ).pack(side="left")
                ctk.CTkLabel(
                    line,
                    text=", ".join(sub["terms"]) if is_covered else "Not covered yet",
                    text_color="gray60",
                ).pack(side="right")
