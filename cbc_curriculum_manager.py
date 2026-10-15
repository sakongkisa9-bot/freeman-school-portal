import copy
from tkinter import filedialog, messagebox

import customtkinter as ctk

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
        self.title(f"Strands - {grade}")
        self.geometry("900x700")
        self.minsize(760, 560)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.subject_var = ctk.StringVar(value=subjects[0] if subjects else "")
        self.strands = []
        self.strand_entries = []
        self._build_widgets()
        self._load_area()
        self.after(150, self.focus_force)

    def _build_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=f"{self.grade} Strands",
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
            text="Edit the strand and sub-strand names, add or remove entries, then save or publish.",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.editor = ctk.CTkScrollableFrame(self)
        self.editor.grid(row=2, column=0, sticky="nsew", padx=20, pady=8)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=20, pady=(8, 18))
        ctk.CTkButton(actions, text="Save on This Computer", command=self._save_local).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Publish Curriculum to Portal", command=self._publish).pack(side="left", padx=8)
        ctk.CTkButton(
            actions, text="Close", width=100, fg_color="#e74c3c", hover_color="#c0392b",
            command=self._close,
        ).pack(side="right")

    @property
    def area_name(self):
        subject = self.subject_var.get().strip()
        return SUBJECT_TO_LEARNING_AREA.get(subject.upper(), subject)

    def _load_area(self):
        areas = (
            self.school_config.get("cbc_curriculum", {})
            .get(self.grade, {})
            .get(self.area_name, [])
        )
        self.strands = copy.deepcopy(areas[0]["strands"]) if areas else []
        self._render_editor()

    def _render_editor(self):
        for widget in self.editor.winfo_children():
            widget.destroy()
        self.strand_entries = []
        if not self.strands:
            ctk.CTkLabel(
                self.editor,
                text="No strands yet. Import a curriculum PDF or add a strand.",
                text_color="gray60",
            ).pack(pady=24)
        for strand in self.strands:
            card = ctk.CTkFrame(self.editor)
            card.pack(fill="x", padx=6, pady=8)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(10, 4))
            name_entry = ctk.CTkEntry(top, font=("Arial Bold", 14), placeholder_text="Strand name")
            name_entry.insert(0, strand["name"])
            name_entry.pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                top, text="Remove Strand", width=120, fg_color="#c0392b", hover_color="#962d22",
                command=lambda item=strand: self._remove_strand(item),
            ).pack(side="left", padx=(8, 0))
            sub_entries = []
            for index, sub_strand in enumerate(strand["sub_strands"]):
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=(34, 10), pady=2)
                entry = ctk.CTkEntry(row, placeholder_text="Sub-strand name")
                entry.insert(0, sub_strand)
                entry.pack(side="left", fill="x", expand=True)
                ctk.CTkButton(
                    row, text="Remove", width=80, fg_color="#7f8c8d", hover_color="#626c6d",
                    command=lambda item=strand, position=index: self._remove_sub_strand(item, position),
                ).pack(side="left", padx=(8, 0))
                sub_entries.append(entry)
            ctk.CTkButton(
                card, text="+ Add Sub-strand", width=140,
                command=lambda item=strand: self._add_sub_strand(item),
            ).pack(anchor="w", padx=34, pady=(6, 10))
            self.strand_entries.append((strand, name_entry, sub_entries))
        ctk.CTkButton(self.editor, text="+ Add Strand", command=self._add_strand).pack(
            anchor="w", padx=6, pady=12
        )

    def _collect(self):
        for strand, name_entry, sub_entries in self.strand_entries:
            strand["name"] = name_entry.get().strip()
            strand["sub_strands"] = [entry.get().strip() for entry in sub_entries]

    def _remove_strand(self, strand):
        self._collect()
        self.strands = [item for item in self.strands if item is not strand]
        self._render_editor()

    def _remove_sub_strand(self, strand, position):
        self._collect()
        del strand["sub_strands"][position]
        self._render_editor()

    def _add_strand(self):
        self._collect()
        self.strands.append({"name": "", "sub_strands": [""]})
        self._render_editor()

    def _add_sub_strand(self, strand):
        self._collect()
        strand["sub_strands"].append("")
        self._render_editor()

    def _read_area(self):
        self._collect()
        strands = []
        for strand in self.strands:
            sub_strands = [name for name in strand["sub_strands"] if name]
            if strand["name"] or sub_strands:
                strands.append({"name": strand["name"], "sub_strands": sub_strands})
        try:
            return validate_curriculum(
                [{"name": self.area_name, "strands": strands}], self.grade
            )
        except ValueError as error:
            raise ValueError(f"Check the strands: {error}") from error

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
        self.strands = [
            {"name": strand["name"], "sub_strands": list(strand["sub_strands"])}
            for strand in strands
        ]
        self._render_editor()
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

    def _close(self):
        self.destroy()
        if self.on_close:
            self.on_close()