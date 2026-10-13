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
        self.rule_menus = {}
        self.first_value_entries = {}
        self.second_value_entries = {}

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

        ctk.CTkLabel(editor, text="Unit (optional)").grid(
            row=1, column=0, sticky="w", padx=14, pady=8
        )
        self.unit_entry = ctk.CTkEntry(editor, placeholder_text="e.g. words")
        self.unit_entry.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=8)

        ctk.CTkLabel(editor, text="Level").grid(row=2, column=0, padx=10, pady=8)
        ctk.CTkLabel(editor, text="Rule").grid(row=2, column=1, padx=8, pady=8)
        ctk.CTkLabel(editor, text="Value / minimum").grid(row=2, column=2, padx=8, pady=8)
        ctk.CTkLabel(editor, text="Maximum").grid(row=2, column=3, padx=8, pady=8)
        editor.grid_columnconfigure(2, weight=1)
        editor.grid_columnconfigure(3, weight=1)

        for row_number, level in enumerate(reversed(LEVEL_NAMES), start=3):
            ctk.CTkLabel(editor, text=level).grid(
                row=row_number, column=0, sticky="w", padx=10, pady=8
            )
            mode = ctk.CTkOptionMenu(
                editor,
                values=["Range", "Single number", "Above", "At least"],
                command=lambda value, item=level: self._update_rule_fields(item, value),
                width=130,
            )
            mode.set("Range")
            mode.grid(row=row_number, column=1, sticky="ew", padx=6, pady=8)
            first_value = ctk.CTkEntry(editor, placeholder_text="Min", width=110)
            first_value.grid(row=row_number, column=2, sticky="ew", padx=6, pady=8)
            second_value = ctk.CTkEntry(editor, placeholder_text="Max", width=110)
            second_value.grid(row=row_number, column=3, sticky="ew", padx=(6, 14), pady=8)
            self.rule_menus[level] = mode
            self.first_value_entries[level] = first_value
            self.second_value_entries[level] = second_value

        actions = ctk.CTkFrame(editor, fg_color="transparent")
        actions.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=18)
        ctk.CTkButton(
            actions, text="Add Task", command=self._add_task
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions,
            text="Save Task",
            fg_color="#247a74",
            hover_color="#1d625d",
            command=self._save_task,
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
            mode = self.rule_menus[level].get()
            first_value = self.first_value_entries[level].get().strip()
            if mode == "Range":
                ranges[level] = {
                    "type": "range",
                    "min": first_value,
                    "max": self.second_value_entries[level].get().strip(),
                }
            else:
                rule_type = {
                    "Single number": "exact",
                    "Above": "above",
                    "At least": "at_least",
                }[mode]
                ranges[level] = {"type": rule_type, "value": first_value}
        return {
            "name": self.name_entry.get().strip(),
            "unit": self.unit_entry.get().strip(),
            "ranges": ranges,
        }

    def _add_task(self):
        self._clear_form()
        self.name_entry.focus_set()

    def _save_task(self):
        updated = list(self.tasks)
        task = self._task_from_form()
        if self.selected_index is None:
            updated.append(task)
        else:
            updated[self.selected_index] = task
        try:
            self.tasks = validate_tasks(updated)
        except ValueError as error:
            messagebox.showerror("Invalid Task", str(error), parent=self)
            return
        self._refresh_task_list()
        self._clear_form()

    def _select_task(self, index):
        self.selected_index = index
        task = self.tasks[index]
        self._clear_form()
        self.selected_index = index
        self.name_entry.insert(0, task["name"])
        self.unit_entry.insert(0, task.get("unit", ""))
        for level, criterion in task["ranges"].items():
            rule_type = criterion.get("type", "range")
            mode = {
                "range": "Range",
                "exact": "Single number",
                "above": "Above",
                "at_least": "At least",
            }[rule_type]
            self.rule_menus[level].set(mode)
            if rule_type == "range":
                self.first_value_entries[level].insert(0, str(criterion["min"]))
                self.second_value_entries[level].insert(0, str(criterion["max"]))
            else:
                self.first_value_entries[level].insert(0, str(criterion["value"]))
            self._update_rule_fields(level, mode)

    def _delete_task(self, index):
        del self.tasks[index]
        if self.selected_index == index:
            self._clear_form()
        elif self.selected_index is not None and self.selected_index > index:
            self.selected_index -= 1
        self._refresh_task_list()

    def _update_rule_fields(self, level, mode):
        first_entry = self.first_value_entries[level]
        second_entry = self.second_value_entries[level]
        first_entry.configure(
            placeholder_text="Min" if mode == "Range" else "Score"
        )
        if mode == "Range":
            second_entry.configure(state="normal", placeholder_text="Max")
        else:
            second_entry.delete(0, "end")
            second_entry.configure(state="disabled", placeholder_text="Not used")

    def _clear_form(self):
        self.selected_index = None
        self.name_entry.delete(0, "end")
        self.unit_entry.delete(0, "end")
        for level in LEVEL_NAMES:
            self.rule_menus[level].set("Range")
            self.first_value_entries[level].delete(0, "end")
            self.second_value_entries[level].configure(state="normal")
            self.second_value_entries[level].delete(0, "end")
            self._update_rule_fields(level, "Range")

    def _refresh_task_list(self):
        for child in self.task_list.winfo_children():
            child.destroy()
        for index, task in enumerate(self.tasks):
            task_row = ctk.CTkFrame(self.task_list)
            task_row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(
                task_row,
                text=f"{task['name']}" + (f" ({task['unit']})" if task.get("unit") else ""),
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=8, pady=8)
            ctk.CTkButton(
                task_row,
                text="Edit",
                width=58,
                command=lambda item=index: self._select_task(item),
            ).pack(side="right", padx=4, pady=4)
            ctk.CTkButton(
                task_row,
                text="Delete",
                width=62,
                fg_color="#9d3939",
                hover_color="#7e2c2c",
                command=lambda item=index: self._delete_task(item),
            ).pack(side="right", padx=4, pady=4)

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
            error_message = result.get("message", "Could not publish task configuration.")
            if "Status: 404" in error_message:
                error_message = (
                    "The live cloud portal has not been updated with KNEC CBA yet. "
                    "Deploy the latest cloud_portal_v2.py to Railway, then try publishing again."
                )
            messagebox.showerror(
                "CBA Publish Failed",
                error_message,
                parent=self,
            )
            return
        if self.on_publish:
            self.on_publish(tasks)
        messagebox.showinfo("KNEC CBA", "Task configuration published to the cloud.", parent=self)