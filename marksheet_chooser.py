import customtkinter as ctk

from academic_periods import TERMS, available_terms
from teachers_linked import map_class_name_to_config_key

NEW_STYLE = "New style"
OLD_STYLE = "Old style"


class MarksheetChooser(ctk.CTkFrame):
    """Pick style (new / old), term and exam before opening a marksheet.

    on_open(style, term, exam_name, is_current) is called when the user presses Open.
    """

    def __init__(self, parent, db, class_name, load_config, save_config, on_open, on_back,
                 stream=None, view_year=None):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.class_name = class_name
        self.stream = stream
        self.history_class_name = f"{class_name} [{stream}]" if stream else class_name
        self.load_config = load_config
        self.save_config = save_config
        self.on_open = on_open
        self.view_year = view_year
        self.grade_type = map_class_name_to_config_key(class_name)
        config = load_config()

        saved_style = config.get("marksheet_style")
        self.style_var = ctk.StringVar(value=saved_style if saved_style in (NEW_STYLE, OLD_STYLE) else NEW_STYLE)
        term_default = config.get("current_term") or config.get(f"{self.grade_type}_exam_term") or config.get("marksheet_term")
        self.term_var = ctk.StringVar(value=term_default if term_default in TERMS else TERMS[0])
        current_year = config.get("academic_year")
        years = {str(year) for year in [current_year, *db.get_previous_exam_years(self.history_class_name)] if year}
        if self.view_year is not None:
            years = {str(self.view_year)}
        self.years = sorted(years, key=lambda year: int(year), reverse=True) or ["-"]
        self.year_var = ctk.StringVar(value=str(current_year) if current_year else self.years[0])
        self.exam_var = ctk.StringVar()
        self.exam_labels = {}

        box = ctk.CTkFrame(self, corner_radius=12)
        box.pack(expand=True)
        ctk.CTkLabel(box, text=f"{class_name} Marksheet", font=("Arial Bold", 24)).pack(padx=60, pady=(30, 20))

        ctk.CTkLabel(box, text="Marksheet style").pack()
        ctk.CTkSegmentedButton(box, values=[NEW_STYLE, OLD_STYLE], variable=self.style_var, width=300).pack(pady=(4, 16))

        ctk.CTkLabel(box, text="Year").pack()
        self.year_menu = ctk.CTkOptionMenu(
            box, values=self.years, variable=self.year_var, width=300, command=self._year_changed
        )
        self.year_menu.pack(pady=(4, 16))
        if self.view_year is not None:
            self.year_menu.configure(state="disabled")

        ctk.CTkLabel(box, text="Term").pack()
        self.term_menu = ctk.CTkSegmentedButton(
            box, values=list(TERMS), variable=self.term_var, width=300, command=self._term_changed
        )
        self.term_menu.pack(pady=(4, 16))

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

    def _available_terms(self):
        config = self.load_config()
        return available_terms(
            self.year_var.get(), config.get("academic_year"), config.get("current_term") or TERMS[0]
        )

    def _year_changed(self, _year):
        terms = self._available_terms()
        self.term_menu.configure(values=list(terms))
        if self.term_var.get() not in terms:
            self.term_var.set(terms[-1])
        self._refresh_exams()

    def _term_changed(self, _term):
        self._refresh_exams()

    def _current_title(self):
        config = self.load_config()
        if self.grade_type == "jss":
            return config.get("current_exam_title") or config.get("jss_exam_title") or ""
        return config.get(f"{self.grade_type}_exam_title", "")

    def _refresh_exams(self):
        terms = self._available_terms()
        self.term_menu.configure(values=list(terms))
        if self.term_var.get() not in terms:
            self.term_var.set(terms[-1])
        term = self.term_var.get()
        config = self.load_config()
        current = self._current_title()
        current_term = config.get("current_term") or config.get(f"{self.grade_type}_exam_term")
        year_text = self.year_var.get()
        is_this_year = year_text == str(config.get("academic_year") or "")
        year = int(year_text) if year_text.isdigit() else None
        self.exam_labels = {}
        if current and is_this_year and (not current_term or current_term == term):
            self.exam_labels[f"{current} (current)"] = (current, True)
        for exam_name, _date in self.db.get_previous_exams_for_term(self.history_class_name, term, year):
            if not (is_this_year and exam_name == current):
                self.exam_labels[exam_name] = (exam_name, False)
        if not self.exam_labels:
            self.exam_labels[f"No exam in {term} {year_text}"] = (None, False)
        labels = list(self.exam_labels)
        self.exam_menu.configure(values=labels)
        self.exam_var.set(labels[0])
        if not is_this_year:
            note = "Past years are read-only."
        else:
            note = "" if len(labels) > 1 else "Exams are created from the Create Exam button on the dashboard."
        self.note.configure(text=note)

    def _open(self):
        exam_name, is_current = self.exam_labels.get(self.exam_var.get(), (None, False))
        style = self.style_var.get()
        term = self.term_var.get()
        year_text = self.year_var.get()
        self.save_config({"marksheet_style": style, "marksheet_term": term})
        self.on_open(style, term, exam_name, is_current, int(year_text) if year_text.isdigit() else None)
