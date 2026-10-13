import customtkinter as ctk
from tkinter import messagebox

from cba_logic import LEVEL_NAMES, validate_tasks
from cloud_service import CloudService, ask_cloud_credentials


class CBATaskManager(ctk.CTkToplevel):
    def __init__(self, parent, grade, subject, tasks=None, on_publish=None):
        super().__init__(parent)
        self.grade = grade
        self.subject = subject
        self.on_publish = on_publish
        try:
            self.tasks = validate_tasks(tasks) if tasks else []
        except ValueError:
            self.tasks = []
        self.selected_index = None
        self.minimum_entries = {}
        self.maximum_entries = {}

        self.title(f"KNEC CBA Tasks - {grade} / {subject}")
        self.geometry("1040x680")
        self.minsize(900, 600)
        self.transient(parent)
        self.grab_set()
        self._build_widgets()
        self._refresh_task_list()

    def _build_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self,
            text=f"{self.grade}  /  {self.subject}",
            font=("Arial Bold", 22),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 12))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1, minsize=260)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self.task_list = ctk.CTkScrollableFrame(body, label_text="Tasks")
        self.task_list.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        editor = ctk.CTkFrame(body)
        editor.grid(row=0, column=1, sticky="nsew")
        editor.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(editor, text="Task name").grid(
            row=0, column=0, sticky="w", padx=14, pady=(16, 8)
        )
        self.name_entry = ctk.CTkEntry(editor, placeholder_text="e.g. Task 1")
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=(16, 8))

        ctk.CTkLabel(editor, text="Level").grid(row=1, column=0, padx=14, pady=8)
        ctk.CTkLabel(editor, text="Minimum raw score").grid(row=1, column=1, padx=8, pady=8)
        ctk.CTkLabel(editor, text="Maximum raw score").grid(row=1, column=2, padx=14, pady=8)
        editor.grid_columnconfigure(2, weight=1)

        for row_number, level in enumerate(reversed(LEVEL_NAMES), start=2):
            ctk.CTkLabel(editor, text=level).grid(
                row=row_number, column=0, sticky="w", padx=14, pady=8
            )
            minimum = ctk.CTkEntry(editor, placeholder_text="Min", width=130)
            minimum.grid(row=row_number, column=1, sticky="ew", padx=8, pady=8)
            maximum = ctk.CTkEntry(editor, placeholder_text="Max", width=130)
            maximum.grid(row=row_number, column=2, sticky="ew", padx=(8, 14), pady=8)
            self.minimum_entries[level] = minimum
            self.maximum_entries[level] = maximum

        actions = ctk.CTkFrame(editor, fg_color="transparent")
        actions.grid(row=6, column=0, columnspan=3, sticky="ew", padx=10, pady=18)
        ctk.CTkButton(actions, text="Add Task", command=self._add_task).pack(
            side="left", padx=4
        )
        ctk.CTkButton(actions, text="Edit Task", command=self._edit_task).pack(
            side="left", padx=4
        )
        ctk.CTkButton(
            actions,
            text="Remove Task",
            fg_color="#9d3939",
            hover_color="#7e2c2c",
            command=self._remove_task,
        ).pack(side="left", padx=4)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))
        ctk.CTkButton(
            footer,
            text="Publish Tasks to Cloud",
            fg_color="#247a74",
            hover_color="#1d625d",
            command=self._publish,
        ).pack(side="right")

    def _task_from_form(self):
        ranges = {}
        for level in LEVEL_NAMES:
            ranges[level] = {
                "min": self.minimum_entries[level].get().strip(),
                "max": self.maximum_entries[level].get().strip(),
            }
        return {"name": self.name_entry.get().strip(), "ranges": ranges}

    def _add_task(self):
        try:
            self.tasks = validate_tasks(self.tasks + [self._task_from_form()])
        except ValueError as error:
            messagebox.showerror("Invalid Task", str(error), parent=self)
            return
        self._refresh_task_list()
        self._clear_form()

    def _edit_task(self):
        if self.selected_index is None:
            messagebox.showinfo("Select Task", "Select a task to edit.", parent=self)
            return
        updated = list(self.tasks)
        updated[self.selected_index] = self._task_from_form()
        try:
            self.tasks = validate_tasks(updated)
        except ValueError as error:
            messagebox.showerror("Invalid Task", str(error), parent=self)
            return
        self._refresh_task_list()

    def _remove_task(self):
        if self.selected_index is None:
            messagebox.showinfo("Select Task", "Select a task to remove.", parent=self)
            return
        del self.tasks[self.selected_index]
        self.selected_index = None
        self._refresh_task_list()
        self._clear_form()

    def _select_task(self, index):
        self.selected_index = index
        task = self.tasks[index]
        self._clear_form()
        self.name_entry.insert(0, task["name"])
        for level, score_range in task["ranges"].items():
            self.minimum_entries[level].insert(0, str(score_range["min"]))
            self.maximum_entries[level].insert(0, str(score_range["max"]))

    def _clear_form(self):
        self.selected_index = None
        self.name_entry.delete(0, "end")
        for entry in (*self.minimum_entries.values(), *self.maximum_entries.values()):
            entry.delete(0, "end")

    def _refresh_task_list(self):
        for child in self.task_list.winfo_children():
            child.destroy()
        for index, task in enumerate(self.tasks):
            ctk.CTkButton(
                self.task_list,
                text=task["name"],
                anchor="w",
                command=lambda item=index: self._select_task(item),
            ).pack(fill="x", padx=6, pady=4)

    def _publish(self):
        try:
            tasks = validate_tasks(self.tasks)
        except ValueError as error:
            messagebox.showerror("Cannot Publish", str(error), parent=self)
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        result = CloudService().upload_cba_tasks(
            self.grade, self.subject, tasks, credentials
        )
        if not result.get("success"):
            messagebox.showerror(
                "CBA Publish Failed",
                result.get("message", "Could not publish task configuration."),
                parent=self,
            )
            return
        if self.on_publish:
            self.on_publish(tasks)
        messagebox.showinfo("KNEC CBA", "Task configuration published to the cloud.", parent=self)