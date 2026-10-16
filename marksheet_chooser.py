import customtkinter as ctk

from teachers_linked import map_class_name_to_config_key

TERMS = ("Term 1", "Term 2", "Term 3")
NEW_STYLE = "New style"
OLD_STYLE = "Old style"


class MarksheetChooser(ctk.CTkFrame):
    """Pick style (new / old), term and exam before opening a marksheet.

    on_open(style, term, exam_name, is_current) is called when the user presses Open.
    """

    def __init__(self, parent, db, class_name, load_config, save_config, on_open, on_back):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.class_name = class_name
        self.load_config = load_config
        self.save_config = save_config
        self.on_open = on_open
        self.grade_type = map_class_name_to_config_key(class_name)
        config = load_config()

        saved_style = config.get("marksheet_style")
        self.style_var = ctk.StringVar(value=saved_style if saved_style in (NEW_STYLE, OLD_STYLE) else NEW_STYLE)
        term_default = config.get(f"{self.grade_type}_exam_term") or config.get("marksheet_term")
        self.term_var = ctk.StringVar(value=term_default if term_default in TERMS else TERMS[0])
        self.exam_var = ctk.StringVar()
        self.exam_labels = {}

        box = ctk.CTkFrame(self, corner_radius=12)
        box.pack(expand=True)
        ctk.CTkLabel(box, text=f"{class_name} Marksheet", font=("Arial Bold", 24)).pack(padx=60, pady=(30, 20))

        ctk.CTkLabel(box, text="Marksheet style").pack()
        ctk.CTkSegmentedButton(box, values=[NEW_STYLE, OLD_STYLE], variable=self.style_var, width=300).pack(pady=(4, 16))

        ctk.CTkLabel(box, text="Term").pack()
        ctk.CTkSegmentedButton(
            box, values=list(TERMS), variable=self.term_var, width=300, command=lambda _v: self._refresh_exams()
        ).pack(pady=(4, 16))

        ctk.CTkLabel(box, text="Exam").pack()
        self.exam_menu = ctk.CTkOptionMenu(box, values=["-"], variable=self.exam_var, width=300)
        self.exam_menu.pack(pady=(4, 6))
        self.note = ctk.CTkLabel(box, text="", text_color="gray60", wraplength=300)
        self.note.pack(pady=(0, 16))

        ctk.CTkButton(box, text="Open Mark Sheet", width=300, height=42, command=self._open).pack(pady=(0, 10))
        ctk.CTkButton(
            box, text="\u2B05 Back", width=300, fg_color="#942727", hover_color="#7a1f1f", command=on_back
        ).pack(pady=(0, 30))
        self._refresh_exams()

    def _current_title(self):
        config = self.load_config()
        if self.grade_type == "jss":
            return config.get("current_exam_title") or config.get("jss_exam_title") or ""
        return config.get(f"{self.grade_type}_exam_title", "")

    def _refresh_exams(self):
        term = self.term_var.get()
        config = self.load_config()
        current = self._current_title()
        current_term = config.get(f"{self.grade_type}_exam_term")
        self.exam_labels = {}
        if current and (not current_term or current_term == term):
            self.exam_labels[f"{current} (current)"] = (current, True)
        for exam_name, _date in self.db.get_previous_exams_for_term(self.class_name, term):
            if exam_name != current:
                self.exam_labels[exam_name] = (exam_name, False)
        if not self.exam_labels:
            self.exam_labels[f"No exam in {term}"] = (None, False)
        labels = list(self.exam_labels)
        self.exam_menu.configure(values=labels)
        self.exam_var.set(labels[0])
        self.note.configure(
            text="" if len(labels) > 1 else "Exams are created from the Create Exam button on the dashboard."
        )

    def _open(self):
        exam_name, is_current = self.exam_labels.get(self.exam_var.get(), (None, False))
        style = self.style_var.get()
        term = self.term_var.get()
        self.save_config({"marksheet_style": style, "marksheet_term": term})
        self.on_open(style, term, exam_name, is_current)
