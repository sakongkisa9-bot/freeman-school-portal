from tkinter import messagebox

import customtkinter as ctk

from cloud_service import CloudService, ask_cloud_credentials

TERMS = ("Term 1", "Term 2", "Term 3")
CLASSES = (
    "playgroup", "pp1", "pp2", "Grade 1", "Grade 2", "Grade 3", "Grade 4",
    "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9",
)


class CreateExamDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_created=None):
        super().__init__(parent)
        self.on_created = on_created
        self.title("Create Exam")
        self.geometry("460x650")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Create Exam", font=("Arial Bold", 22)).pack(pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Uploading a new exam replaces the current portal exam and removes its marks.",
            wraplength=400,
        ).pack(pady=(0, 12))

        self.title_entry = ctk.CTkEntry(self, placeholder_text="Exam title, e.g. TERM 2 EXAM 2026", width=380)
        self.title_entry.pack(pady=8)

        term_row = ctk.CTkFrame(self, fg_color="transparent")
        term_row.pack(pady=4)
        ctk.CTkLabel(term_row, text="Term").pack(side="left", padx=(0, 8))
        self.term_menu = ctk.CTkOptionMenu(term_row, values=list(TERMS), width=120)
        self.term_menu.pack(side="left")

        self.scope_var = ctk.StringVar(value="All school")
        ctk.CTkSegmentedButton(
            self,
            values=["All school", "Selected classes"],
            variable=self.scope_var,
            command=lambda _: self._update_scope(),
        ).pack(pady=10)

        self.class_frame = ctk.CTkScrollableFrame(self, width=360, height=250)
        self.class_frame.pack(pady=6)
        self.class_vars = {}
        for name in CLASSES:
            variable = ctk.BooleanVar(value=False)
            self.class_vars[name] = variable
            ctk.CTkCheckBox(self.class_frame, text=name, variable=variable).pack(anchor="w", pady=3)
        self._update_scope()

        self.upload_button = ctk.CTkButton(self, text="Upload to Portal", height=40, command=self._upload)
        self.upload_button.pack(pady=16)

    def _update_scope(self):
        state = "normal" if self.scope_var.get() == "Selected classes" else "disabled"
        for child in self.class_frame.winfo_children():
            child.configure(state=state)

    def _upload(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Exam Title", "Enter the exam title.", parent=self)
            return
        all_classes = self.scope_var.get() == "All school"
        classes = [name for name, variable in self.class_vars.items() if variable.get()]
        if not all_classes and not classes:
            messagebox.showwarning("Classes", "Select at least one class.", parent=self)
            return
        if not messagebox.askyesno(
            "Replace Current Exam",
            "This replaces the current portal exam and removes its marks from the portal. Continue?",
            parent=self,
        ):
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        result = CloudService().create_exam(title, all_classes, classes, credentials)
        if not result.get("success"):
            messagebox.showerror(
                "Upload Failed", result.get("message", "Could not upload the exam."), parent=self
            )
            return
        messagebox.showinfo("Exam Uploaded", result.get("message", "Exam uploaded."), parent=self)
        term = self.term_menu.get()
        callback = self.on_created
        self.destroy()
        if callback:
            callback(title, term, all_classes, classes)
