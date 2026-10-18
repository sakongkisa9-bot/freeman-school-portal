import os
import sys
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from fpdf import FPDF
from grading_logic import get_grade_4_6_rating, get_grade_7_8_rating
from marksheet_chooser import NEW_STYLE, OLD_STYLE
from kicd_grading import index_levels, levels_for, subject_result
from cbc_engine import SUBJECT_TO_LEARNING_AREA


def get_app_dir():
    """Get the application directory, handling both script and executable environments"""
    if getattr(sys, 'frozen', False):
        # Running as executable
        BASE_DIR = sys._MEIPASS
        USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    else:
        # Running as script
        BASE_DIR = os.path.dirname(os.path.realpath(__file__))
        USER_DATA_DIR = BASE_DIR
    return BASE_DIR, USER_DATA_DIR

LEVEL_ORDER = ["EE", "ME", "AE", "BE"]
LEVEL_POINTS = {"EE1": 8, "EE2": 7, "ME1": 6, "ME2": 5, "AE1": 4, "AE2": 3, "BE1": 2, "BE2": 1}
NEW_LEVEL_ORDER = ("EE", "ME", "AE", "BE")

DEFAULT_SUBJECTS = {
    "playgroup": ["MATH", "CREAT", "ENV"],
    "pp1": ["MATH", "ENV", "PSYCH", "REL"],
    "pp2": ["MATH", "ENV", "PSYCH", "REL"],
    "lower": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "primary": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "jss": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"]
}


def normalize_summary_level(level):
    value = str(level or "").strip().upper().replace(" ", "")
    if value in NEW_LEVEL_ORDER:
        return value
    if value in {"EE1", "EE2"}:
        return "EE"
    if value in {"ME1", "ME2"}:
        return "ME"
    if value in {"AE1", "AE2"}:
        return "AE"
    if value in {"BE1", "BE2"}:
        return "BE"
    return ""


class SummaryChooser(ctk.CTkFrame):
    def __init__(self, parent, class_name, load_config, save_config, on_open, on_back):
        super().__init__(parent, fg_color="transparent")
        self.class_name = class_name
        self.load_config = load_config
        self.save_config = save_config
        self.on_open = on_open
        config = load_config()
        saved_style = config.get("summary_style")
        self.style_var = ctk.StringVar(value=saved_style if saved_style in (NEW_STYLE, OLD_STYLE) else OLD_STYLE)

        box = ctk.CTkFrame(self, corner_radius=12)
        box.pack(expand=True)
        ctk.CTkLabel(box, text=f"{class_name} Student Marks Summary", font=("Arial Bold", 24)).pack(
            padx=50, pady=(30, 20)
        )
        ctk.CTkLabel(box, text="Summary style").pack()
        ctk.CTkSegmentedButton(
            box, values=[NEW_STYLE, OLD_STYLE], variable=self.style_var, width=300
        ).pack(pady=(4, 20))
        ctk.CTkButton(box, text="Open Summary", width=300, height=42, command=self._open).pack(pady=(0, 10))
        ctk.CTkButton(
            box, text="\u2B05 Back", width=300, fg_color="#942727", hover_color="#7a1f1f", command=on_back
        ).pack(pady=(0, 30))

    def _open(self):
        style = self.style_var.get()
        self.save_config({"summary_style": style})
        self.on_open(style)

class ClassSummaryView(ctk.CTkFrame):
    def __init__(self, parent, db_connection, class_name, stream=None, style=OLD_STYLE):
        super().__init__(parent, fg_color="transparent")
        self.db = db_connection
        self.class_name = class_name
        self.stream = stream
        self.style = style
        # Initialize proper paths for executable environment
        self.BASE_DIR, self.USER_DATA_DIR = get_app_dir()
        self.grade_type, self.table_name = self.resolve_class_metadata(class_name)
        self.school_config = self.load_school_config()
        self.subjects = self.get_subjects_from_json(
            self.grade_type, selected_only=self.style == NEW_STYLE
        )
        self.current_exam_title = self.school_config.get(f"{self.grade_type}_exam_title", f"{class_name.upper()} SUMMARY")
        self.summary = self.load_summary_data()

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.body_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body_frame.grid(row=0, column=0, sticky="nsew")

        self.create_header()
        self.create_summary_cards()
        if self.style == NEW_STYLE:
            self.create_new_style_section()
        else:
            self.create_details_section()
        self.create_bottom_controls()

    def get_json_path(self):
        # Use USER_DATA_DIR for config file (works in both script and executable)
        return os.path.join(self.USER_DATA_DIR, 'school_config.json')

    def load_school_config(self):
        try:
            json_path = self.get_json_path()
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    return json.load(f)
            else:
                # If config doesn't exist in USER_DATA_DIR, copy from bundled location
                bundled_config = os.path.join(self.BASE_DIR, "school_config.json")
                if os.path.exists(bundled_config):
                    import shutil
                    shutil.copy2(bundled_config, json_path)
                    with open(json_path, 'r') as f:
                        return json.load(f)
        except Exception:
            pass
        return {}

    def resolve_class_metadata(self, class_name):
        lower = class_name.lower()
        if "play" in lower:
            return "playgroup", "playgroup_marks"
        if "pre-primary 1" in lower or "pp1" in lower:
            return "pp1", "pp1_marks"
        if "pre-primary 2" in lower or "pp2" in lower:
            return "pp2", "pp2_marks"
        if any(g in lower for g in ["grade 1", "grade 2", "grade 3"]):
            return "lower", "lower_marks"
        if any(g in lower for g in ["grade 4", "grade 5", "grade 6"]):
            return "primary", "primary_marks"
        return "jss", "marksheet"

    def get_subjects_from_json(self, section, selected_only=False):
        try:
            catalog = self.school_config.get("subject_catalog", {}).get(section)
            if selected_only and isinstance(catalog, list):
                return [
                    item["short"].strip()
                    for item in catalog
                    if isinstance(item, dict) and item.get("selected") and item.get("short", "").strip()
                ]
            subjects = self.school_config.get("subjects", {}).get(section)
            if subjects and isinstance(subjects, list):
                return subjects
        except Exception:
            pass
        return DEFAULT_SUBJECTS.get(section, [])

    def clean_column_name(self, subject):
        return subject.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()

    def ensure_marks_table(self):
        try:
            if self.table_name == "marksheet":
                self.db.cursor().execute("CREATE TABLE IF NOT EXISTS marksheet (adm_no TEXT PRIMARY KEY, total_points INTEGER, average_points TEXT, rank INTEGER)")
            else:
                self.db.cursor().execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} (adm_no TEXT PRIMARY KEY, total_points INTEGER, average_level TEXT)")

            self.db.cursor().execute(f"PRAGMA table_info({self.table_name})")
            existing_cols = [row[1].lower() for row in self.db.cursor().fetchall()]

            for subject in self.subjects:
                base = self.clean_column_name(subject)
                score_col = f"{base}_s"
                remark_col = f"{base}_r"
                if score_col not in existing_cols:
                    self.db.cursor().execute(f"ALTER TABLE {self.table_name} ADD COLUMN {score_col} INTEGER")
                if remark_col not in existing_cols:
                    self.db.cursor().execute(f"ALTER TABLE {self.table_name} ADD COLUMN {remark_col} TEXT")
                if self.table_name == "marksheet":
                    point_col = f"{base}_p"
                    if point_col not in existing_cols:
                        self.db.cursor().execute(f"ALTER TABLE marksheet ADD COLUMN {point_col} INTEGER")

            self.db.conn.commit()
        except Exception:
            pass

    def _learning_area_for_subject(self, subject):
        normalized = subject.strip().upper()
        area = SUBJECT_TO_LEARNING_AREA.get(normalized)
        if area:
            return area
        names = self.school_config.get("subject_names", {}).get(self.grade_type, {})
        if subject in names:
            return names[subject]
        for items in (self.school_config.get("subject_catalog") or {}).values():
            for item in items:
                if item.get("short", "").strip().upper() == normalized:
                    return item.get("name", subject).strip()
        return subject.strip()

    def _load_new_style_level_indexes(self):
        config_levels = self.school_config.get("cbc_levels", {}).get(self.class_name, {})
        term = self.school_config.get("marksheet_term") or self.school_config.get("current_term") or "Term 1"
        year = str(self.school_config.get("academic_year") or "")
        indexes = {}
        for subject in self.subjects:
            area = self._learning_area_for_subject(subject)
            area_names = [area]
            if area == "Agriculture and Nutrition":
                area_names.append("Agriculture")
            record = None
            for area_name in area_names:
                by_area = config_levels.get(area_name, {})
                record = by_area.get(f"{year}|{term}") if year else None
                if record is None:
                    record = by_area.get(term)
                if record is not None:
                    break
            indexes[subject] = index_levels(record.get("records", [])) if isinstance(record, dict) else {}
        return indexes

    def load_summary_data(self):
        self.ensure_marks_table()
        subject_select = []
        subject_points = []
        for subject in self.subjects:
            base = self.clean_column_name(subject)
            subject_select.append(f"m.{base}_s")
            subject_select.append(f"m.{base}_r")
            if self.table_name == "marksheet":
                subject_select.append(f"m.{base}_p")
                subject_points.append((subject, f"m.{base}_p"))
            else:
                subject_points.append((subject, f"m.{base}_s"))

        average_field = "m.average_points" if self.table_name == "marksheet" else "m.average_level"
        if self.style == NEW_STYLE:
            score_columns = [f"m.{self.clean_column_name(subject)}_s" for subject in self.subjects]
            select_columns = ["s.adm_no", "s.name", "s.gender", "s.assessment_number"] + score_columns
            level_indexes = self._load_new_style_level_indexes()
        else:
            select_columns = ["s.adm_no", "s.name", "s.gender"] + subject_select + ["m.total_points", average_field]
            level_indexes = {}
        column_clause = ", ".join(select_columns)
        query = f"SELECT {column_clause} FROM students s LEFT JOIN {self.table_name} m ON s.adm_no = m.adm_no WHERE UPPER(s.grade) = UPPER(?)"
        params = [self.class_name]
        if self.stream:
            query += " AND UPPER(TRIM(s.stream)) = UPPER(?)"
            params.append(self.stream)

        try:
            self.db.cursor().execute(query, params)
            rows = self.db.cursor().fetchall()
        except Exception:
            rows = []

        distribution = {level: 0 for level in LEVEL_ORDER}
        subject_level_counts = {
            subject: {level: 0 for level in NEW_LEVEL_ORDER} for subject in self.subjects
        }
        gender_counts = {"male": 0, "female": 0, "other": 0}
        gender_totals = {"male": 0, "female": 0, "other": 0}
        subject_totals = {subject: 0.0 for subject in self.subjects}
        subject_counts = {subject: 0 for subject in self.subjects}
        total_students = 0

        for row in rows:
            if not row:
                continue
            total_students += 1
            gender_raw = str(row[2]).strip().lower() if row[2] else "other"

            # Map gender values to standard categories
            if gender_raw in ["m", "male", "boy"]:
                gender = "male"
            elif gender_raw in ["f", "female", "girl"]:
                gender = "female"
            else:
                gender = "other"

            gender_counts[gender] += 1

            if self.style == NEW_STYLE:
                assessment_number = row[3]
                start_idx = 4
                total_points = 0
            else:
                average_value = row[-1] if len(row) > 0 else None
                normalized_level = normalize_summary_level(average_value)
                if normalized_level:
                    distribution[normalized_level] += 1
                total_points = row[-2] if len(row) > 1 and isinstance(row[-2], (int, float)) else 0
                start_idx = 3

            if isinstance(total_points, (int, float)):
                gender_totals[gender] += total_points

            for subject in self.subjects:
                if self.style == NEW_STYLE:
                    score = row[start_idx]
                    start_idx += 1
                    rating = subject_result(
                        levels_for(level_indexes.get(subject, {}), assessment_number, row[1]), score
                    )["R"]
                    if rating in subject_level_counts[subject]:
                        subject_level_counts[subject][rating] += 1
                elif self.table_name == "marksheet":
                    score = row[start_idx]
                    start_idx += 3
                else:
                    score = row[start_idx]
                    start_idx += 2

                score_value = 0.0
                if isinstance(score, (int, float)):
                    score_value = float(score)
                elif isinstance(score, str):
                    try:
                        score_value = float(score.strip())
                    except Exception:
                        score_value = 0.0

                if self.style != NEW_STYLE or (
                    score is not None and str(score).strip() and str(score).strip().upper() != "AB"
                ):
                    subject_totals[subject] += score_value
                    subject_counts[subject] += 1

        subject_averages = []
        for subject in self.subjects:
            count = subject_counts[subject]
            mean_value = round(subject_totals[subject] / count if count else 0.0, 2)
            subject_averages.append((subject, mean_value))

        subject_averages.sort(key=lambda pair: pair[1], reverse=True)

        # Check for previous exam
        has_history = False
        trend_text = "No previous exam"
        try:
            self.db.cursor().execute(
                "SELECT exam_name FROM previous_exams WHERE class_name = ? ORDER BY exam_date DESC LIMIT 1",
                (self.class_name,)
            )
            previous_exam = self.db.cursor().fetchone()
            if previous_exam:
                has_history = True
                trend_text = f"Previous: {previous_exam[0]}"
        except Exception:
            pass

        return {
            "total_students": total_students,
            "distribution": distribution,
            "gender_counts": gender_counts,
            "gender_totals": gender_totals,
            "subject_averages": subject_averages,
            "subject_level_counts": subject_level_counts,
            "has_history": has_history,
            "trend_text": trend_text,
        }

    def map_primary_score_to_point(self, score):
        try:
            score = int(score)
            rating = get_grade_4_6_rating(score)
            return LEVEL_POINTS.get(rating, 0)
        except Exception:
            return 0

    def map_jss_score_to_point(self, score):
        try:
            score = int(score)
            rating, points = get_grade_7_8_rating(score)
            return float(points)
        except Exception:
            return 0

    def create_header(self):
        school = self.school_config.get("school_name", "Freeman Tech Solutions").upper()
        exam_label = self.current_exam_title.upper()
        header_text = f"{school}\n{self.class_name.upper()} - {exam_label}"
        self.header_label = ctk.CTkLabel(self.body_frame, text=header_text, font=("Arial Bold", 20), fg_color="#1f538d", text_color="white", corner_radius=12, height=80)
        self.header_label.pack(fill="x", padx=20, pady=15)

    def create_summary_cards(self):
        top_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(0, 10))

        cards = [
            ("Total Students", str(self.summary["total_students"]), "#10b981"),
            ("Male Students", str(self.summary["gender_counts"]["male"]), "#3b82f6"),
            ("Female Students", str(self.summary["gender_counts"]["female"]), "#ec4899"),
            ("Previous Exam", self.summary["trend_text"], "#fbbf24")
        ]

        for text, value, color in cards:
            card = ctk.CTkFrame(top_frame, fg_color="#20232a", corner_radius=10)
            card.pack(side="left", expand=True, fill="both", padx=5)
            ctk.CTkLabel(card, text=text, font=("Arial", 10), text_color="#d1d5db").pack(anchor="w", padx=12, pady=(12, 3))
            ctk.CTkLabel(card, text=value, font=("Arial Bold", 18), text_color=color).pack(anchor="w", padx=12, pady=(0, 12))

    def create_details_section(self):
        detail_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        detail_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Create a 2x2 grid layout
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(1, weight=1)
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        # Top-left: Distribution
        dist_frame = ctk.CTkFrame(detail_frame, fg_color="#20232a", corner_radius=10)
        dist_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.render_distribution_compact(dist_frame)

        # Top-right: Subject Ranking
        rank_frame = ctk.CTkFrame(detail_frame, fg_color="#20232a", corner_radius=10)
        rank_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.render_subject_ranking_compact(rank_frame)

        # Bottom-left: Gender Comparison
        gender_frame = ctk.CTkFrame(detail_frame, fg_color="#20232a", corner_radius=10)
        gender_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.render_gender_comparison_compact(gender_frame)

        # Bottom-right: Subject Chart
        chart_frame = ctk.CTkFrame(detail_frame, fg_color="#20232a", corner_radius=10)
        chart_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.render_subject_chart_compact(chart_frame)

    def create_new_style_section(self):
        chart_panel = ctk.CTkFrame(self.body_frame, fg_color="#20232a", corner_radius=8)
        chart_panel.pack(fill="x", expand=True, padx=20, pady=(0, 10))
        ctk.CTkLabel(
            chart_panel, text="Subject Average and Rank", font=("Arial Bold", 14)
        ).pack(anchor="w", padx=14, pady=(12, 8))

        canvas_frame = ctk.CTkFrame(chart_panel, fg_color="#111827", corner_radius=6)
        canvas_frame.pack(fill="x", padx=12, pady=(0, 12))
        chart_width = max(620, 54 + len(self.subjects) * 78)
        chart_canvas = ctk.CTkCanvas(
            canvas_frame, width=620, height=230, bg="#111827", highlightthickness=0
        )
        chart_canvas.pack(fill="x", expand=True, padx=5, pady=(5, 0))
        scrollbar = ctk.CTkScrollbar(canvas_frame, orientation="horizontal", command=chart_canvas.xview)
        scrollbar.pack(fill="x", padx=5, pady=(0, 5))
        chart_canvas.configure(xscrollcommand=scrollbar.set, scrollregion=(0, 0, chart_width, 230))
        chart_canvas.create_line(35, 180, chart_width - 10, 180, fill="#64748b")
        for value in (25, 50, 75, 100):
            y = 180 - value * 1.35
            chart_canvas.create_line(35, y, chart_width - 10, y, fill="#273449")
            chart_canvas.create_text(28, y, text=str(value), fill="#9ca3af", font=("Arial", 8), anchor="e")
        for rank, (subject, average) in enumerate(self.summary["subject_averages"], start=1):
            x = 48 + (rank - 1) * 78
            height = max(0, min(135, average * 1.35))
            chart_canvas.create_rectangle(
                x, 180 - height, x + 38, 180, fill="#38bdf8", outline=""
            )
            chart_canvas.create_text(
                x + 19, 174 - height, text=f"{average:.1f}", fill="#f8fafc", font=("Arial", 8)
            )
            chart_canvas.create_text(
                x + 19, 190, text=f"#{rank} {subject[:8]}", fill="#d1d5db", font=("Arial", 8)
            )

        table_panel = ctk.CTkFrame(self.body_frame, fg_color="#20232a", corner_radius=8)
        table_panel.pack(fill="x", expand=True, padx=20, pady=(0, 16))
        ctk.CTkLabel(
            table_panel, text="Students by Subject and Level", font=("Arial Bold", 14)
        ).pack(anchor="w", padx=14, pady=(12, 8))
        table = ctk.CTkFrame(table_panel, fg_color="transparent")
        table.pack(fill="x", padx=12, pady=(0, 12))
        table.grid_columnconfigure(0, weight=3)
        for column in range(1, len(NEW_LEVEL_ORDER) + 1):
            table.grid_columnconfigure(column, weight=1, uniform="level-count")
        headings = ["Subject", *NEW_LEVEL_ORDER]
        for column, heading in enumerate(headings):
            ctk.CTkLabel(
                table, text=heading, font=("Arial Bold", 11), text_color="#bae6fd"
            ).grid(row=0, column=column, sticky="ew", padx=4, pady=5)
        for row_index, subject in enumerate(self.subjects, start=1):
            background = "#111827" if row_index % 2 else "#1f2937"
            ctk.CTkLabel(
                table, text=subject, anchor="w", fg_color=background, corner_radius=4
            ).grid(row=row_index, column=0, sticky="ew", padx=2, pady=2, ipady=5)
            for column, level in enumerate(NEW_LEVEL_ORDER, start=1):
                ctk.CTkLabel(
                    table,
                    text=str(self.summary["subject_level_counts"][subject][level]),
                    fg_color=background,
                    corner_radius=4,
                ).grid(row=row_index, column=column, sticky="ew", padx=2, pady=2, ipady=5)

    def render_distribution_compact(self, parent):
        ctk.CTkLabel(parent, text="Class Level Distribution", font=("Arial Bold", 12)).pack(anchor="w", padx=12, pady=(12, 8))
        
        # Use a frame with grid layout instead of scrollable
        grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(2, weight=1)
        grid_frame.grid_columnconfigure(3, weight=1)
        
        for index, level in enumerate(LEVEL_ORDER):
            row = index // 4
            col = index % 4
            bg = "#081c15" if index % 2 == 0 else "#102f1f"
            cell = ctk.CTkFrame(grid_frame, fg_color=bg, corner_radius=8)
            cell.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            ctk.CTkLabel(cell, text=level, font=("Arial Bold", 10)).pack(pady=(8, 2))
            ctk.CTkLabel(cell, text=str(self.summary["distribution"][level]), font=("Arial Bold", 14), text_color="#f8fafc").pack(pady=(0, 8))

    def render_subject_ranking_compact(self, parent):
        ctk.CTkLabel(parent, text="Subject Mean Ranking", font=("Arial Bold", 12)).pack(anchor="w", padx=12, pady=(12, 8))
        
        ranking_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ranking_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        for rank, (subject, mean_value) in enumerate(self.summary["subject_averages"], start=1):
            bg = "#1f2937" if rank % 2 == 1 else "#111827"
            row = ctk.CTkFrame(ranking_frame, fg_color=bg, corner_radius=6)
            row.pack(fill="x", padx=2, pady=2)
            ctk.CTkLabel(row, text=f"{rank}. {subject}", font=("Arial", 10)).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=f"{mean_value:.2f}", font=("Arial Bold", 10), text_color="#60a5fa").pack(side="right", padx=8, pady=6)

    def render_gender_comparison_compact(self, parent):
        stats = self.summary["gender_counts"]
        total = max(1, self.summary["total_students"])
        ratio_text = f"M: {stats['male']} | F: {stats['female']} | O: {stats['other']}"
        ctk.CTkLabel(parent, text="Gender Performance", font=("Arial Bold", 12)).pack(anchor="w", padx=12, pady=(12, 8))
        ctk.CTkLabel(parent, text=ratio_text, font=("Arial", 9), text_color="#d1d5db").pack(anchor="w", padx=12)

        male_pct = max(0, min(100, int(stats["male"] / total * 100)))
        female_pct = max(0, min(100, int(stats["female"] / total * 100)))
        other_pct = max(0, 100 - male_pct - female_pct)
        
        progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        progress_frame.pack(fill="x", padx=12, pady=(8, 0))
        
        progress = ctk.CTkProgressBar(progress_frame, width=200, progress_color="#3b82f6", corner_radius=8)
        progress.pack(fill="x")
        progress.set(male_pct / 100)

        ctk.CTkLabel(parent, text=f"Male {male_pct}%  ·  Female {female_pct}%  ·  Other {other_pct}%", font=("Arial", 9), text_color="#9ca3af").pack(anchor="w", padx=12, pady=(5, 12))

    def render_subject_chart_compact(self, parent):
        ctk.CTkLabel(parent, text="Subject Performance", font=("Arial Bold", 12)).pack(anchor="w", padx=12, pady=(12, 8))

        canvas_container = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=8)
        canvas_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        chart_canvas = ctk.CTkCanvas(canvas_container, width=280, height=140, bg="#111827", highlightthickness=0)
        chart_canvas.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        subject_data = self.summary["subject_averages"]
        max_value = max((value for _, value in subject_data), default=1)
        max_value = max(max_value, 1)  # Ensure max_value is at least 1 to avoid division by zero
        bar_width = 25
        spacing = 10
        base_y = 110
        x_start = 15
        total_width = max(280, x_start + len(subject_data) * (bar_width + spacing) + 20)

        for index, (subject, value) in enumerate(subject_data):
            x0 = x_start + index * (bar_width + spacing)
            x1 = x0 + bar_width
            height = int((value / max_value) * 80) if max_value > 0 else 0
            chart_canvas.create_rectangle(x0, base_y - height, x1, base_y, fill="#38bdf8", outline="")
            chart_canvas.create_text((x0 + x1) / 2, base_y - height - 8, text=f"{value:.1f}", fill="#f8fafc", font=("Arial", 7))
            chart_canvas.create_text((x0 + x1) / 2, base_y + 8, text=subject[:6], fill="#d1d5db", font=("Arial", 7), anchor="n")

        chart_canvas.configure(scrollregion=(0, 0, total_width, 140))

    def normalize_pdf_text(self, text):
        if text is None:
            return ""
        return str(text).replace("—", "-").replace("–", "-").replace("…", "...")

    def create_bottom_controls(self):
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkButton(bottom_bar, text="🖨 Print PDF", fg_color="#f59e0b", text_color="black", command=self.generate_pdf_report).pack(side="left", padx=5)

        # Find the return_to_home method by traversing up the widget hierarchy
        def find_return_to_home(widget):
            current = widget
            while current:
                if hasattr(current, 'return_to_home') and callable(getattr(current, 'return_to_home')):
                    return current.return_to_home
                current = getattr(current, 'master', None)
            return None

        back_callback = find_return_to_home(self)
        if back_callback is None:
            back_callback = lambda: print("Back button clicked - no return_to_home method found")

        ctk.CTkButton(bottom_bar, text="⬅ Back to Dashboard", fg_color="#ef4444", command=back_callback).pack(side="right", padx=5)

    def generate_new_style_pdf(self, file_path):
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.graphics.shapes import Drawing, Line, Rect, String
        from reportlab.platypus import KeepInFrame, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape

        page_width, page_height = landscape(A4)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="SummaryTitle", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, alignment=TA_CENTER, textColor=colors.HexColor("#17324d"),
        ))
        styles.add(ParagraphStyle(
            name="SummarySubTitle", parent=styles["Normal"], fontSize=10,
            alignment=TA_CENTER, textColor=colors.HexColor("#475569"),
        ))
        subject_data = self.summary["subject_averages"]
        chart = Drawing(page_width - 48, 155)
        plot_left, plot_bottom, plot_height = 38, 25, 105
        plot_width = page_width - 110
        chart.add(Line(plot_left, plot_bottom, plot_left + plot_width, plot_bottom, strokeColor=colors.grey))
        for mark in (0, 25, 50, 75, 100):
            y = plot_bottom + mark / 100 * plot_height
            chart.add(Line(plot_left, y, plot_left + plot_width, y, strokeColor=colors.HexColor("#e2e8f0")))
            chart.add(String(3, y - 3, str(mark), fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#475569")))
        slot_width = plot_width / max(1, len(subject_data))
        bar_width = min(38, slot_width * 0.55)
        for rank, (subject, average) in enumerate(subject_data, start=1):
            center_x = plot_left + slot_width * (rank - 0.5)
            bar_height = max(0, min(100, average)) / 100 * plot_height
            chart.add(Rect(
                center_x - bar_width / 2, plot_bottom, bar_width, bar_height,
                fillColor=colors.HexColor("#168aad"), strokeColor=None,
            ))
            chart.add(String(
                center_x, plot_bottom + bar_height + 3, f"{average:.1f}",
                fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#17324d"),
            ))
            chart.add(String(
                center_x, 8, f"#{rank} {subject[:8]}",
                fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#334155"),
            ))

        header = Paragraph(
            f"{escape(str(self.school_config.get('school_name', 'Freeman Tech Solutions')).upper())}",
            styles["SummaryTitle"],
        )
        subtitle = Paragraph(
            f"{escape(self.class_name.upper())} STUDENT MARKS SUMMARY | {escape(self.current_exam_title)}",
            styles["SummarySubTitle"],
        )
        metrics = [
            ["Total Students", "Male", "Female", "Other"],
            [
                str(self.summary["total_students"]),
                str(self.summary["gender_counts"]["male"]),
                str(self.summary["gender_counts"]["female"]),
                str(self.summary["gender_counts"]["other"]),
            ],
        ]
        metric_table = Table(metrics, colWidths=[(page_width - 48) / 4] * 4)
        metric_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1f5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324d")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        levels = [["Subject", *NEW_LEVEL_ORDER]] + [
            [subject, *[str(self.summary["subject_level_counts"][subject][level]) for level in NEW_LEVEL_ORDER]]
            for subject in self.subjects
        ]
        level_table = Table(levels, colWidths=[page_width - 48 - 4 * 90, 90, 90, 90, 90], repeatRows=1)
        table_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
        level_table.setStyle(table_style)

        def draw_footer(canvas, document):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
            canvas.line(24, 24, page_width - 24, 24)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawString(24, 12, "Student Marks Summary")
            canvas.drawRightString(page_width - 24, 12, f"Page {document.page}")
            canvas.restoreState()

        document = SimpleDocTemplate(
            file_path, pagesize=landscape(A4), leftMargin=24, rightMargin=24,
            topMargin=24, bottomMargin=32, title=f"{self.class_name} Student Marks Summary",
        )
        content = [header, subtitle, Spacer(1, 6), metric_table, Spacer(1, 8)]
        content.extend([Paragraph("Subject Average and Rank", styles["Heading2"]), chart, Spacer(1, 4)])
        content.extend([Paragraph("Students by Subject and Level", styles["Heading2"]), level_table])
        page_content = KeepInFrame(
            page_width - 48, page_height - 56, content, mode="shrink"
        )
        document.build([page_content], onFirstPage=draw_footer, onLaterPages=draw_footer)
        messagebox.showinfo("Report Saved", f"PDF exported to {os.path.basename(file_path)}", parent=self)

    def generate_pdf_report(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{self.class_name}_SUMMARY.pdf")
        if not file_path:
            return

        if self.style == NEW_STYLE:
            try:
                self.generate_new_style_pdf(file_path)
            except Exception as exc:
                messagebox.showerror("PDF Error", f"Could not create PDF: {exc}", parent=self)
            return

        school = self.school_config.get("school_name", "Freeman Tech Solutions").upper()
        logo_path = self.school_config.get("logo", "")
        signature_path = self.school_config.get("signatures", {}).get("headteacher", "")
        exam_title = self.current_exam_title

        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=False)

            # Page border
            pdf.set_draw_color(15, 23, 42)
            pdf.set_line_width(1.5)
            pdf.rect(8, 8, 194, 280)

            # Header area and logo
            pdf.set_fill_color(15, 23, 42)
            pdf.rect(10, 10, 190, 24, 'F')
            pdf.set_font("Helvetica", 'B', 18)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(12, 14)
            pdf.cell(0, 8, txt=self.normalize_pdf_text(school), ln=0, align='L')
            if logo_path and os.path.exists(logo_path):
                try:
                    pdf.image(logo_path, x=170, y=12, w=25)
                except Exception:
                    pass
            pdf.set_font("Helvetica", 'B', 11)
            pdf.set_xy(12, 22)
            pdf.cell(0, 6, txt=self.normalize_pdf_text(f"{self.class_name.upper()} SUMMARY - {exam_title}"), ln=0, align='L')
            pdf.ln(16)

            overall_count = self.summary['total_students'] if self.summary['total_students'] else 0
            overall_totals = sum(self.summary['gender_totals'].values())
            overall_avg_point = overall_totals / overall_count if overall_count else 0

            # Summary badge area
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_text_color(15, 23, 42)
            pdf.set_fill_color(224, 242, 254)
            pdf.cell(0, 9, txt="Summary at a Glance", ln=1, fill=True)
            pdf.set_font("Helvetica", '', 10)
            pdf.set_fill_color(249, 250, 251)
            pdf.cell(0, 6, txt=self.normalize_pdf_text(f"Total Students: {overall_count}"), ln=1, fill=True)
            pdf.cell(0, 6, txt=self.normalize_pdf_text(f"Male: {self.summary['gender_counts']['male']}   Female: {self.summary['gender_counts']['female']}   Other: {self.summary['gender_counts']['other']}"), ln=1, fill=True)
            pdf.cell(0, 6, txt=self.normalize_pdf_text(f"Overall Avg points: {overall_avg_point:.1f}"), ln=1, fill=True)
            pdf.cell(0, 6, txt=self.normalize_pdf_text(f"Previous Exam Status: {self.summary['trend_text']}"), ln=1, fill=True)
            pdf.ln(5)

            # Separator line
            pdf.set_draw_color(59, 130, 246)
            pdf.set_line_width(0.6)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            # Subject performance chart
            subject_data = self.summary['subject_averages']
            max_value = max((value for _, value in subject_data), default=1)
            max_value = max(max_value, 1)  # Ensure max_value is at least 1 to avoid division by zero
            chart_height = 38
            chart_width = 180
            chart_x = 15
            chart_y = pdf.get_y()
            num_subjects = max(1, len(subject_data))
            spacing = 4 if num_subjects > 10 else 6
            bar_width = max(5, min(12, int((chart_width - (num_subjects + 1) * spacing) / num_subjects)))
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_xy(10, chart_y)
            pdf.cell(0, 8, txt="Subject Performance Chart", ln=1)
            chart_y = pdf.get_y()

            for index, (subject, value) in enumerate(subject_data):
                bar_x = chart_x + spacing + index * (bar_width + spacing)
                bar_h = int((value / max_value) * chart_height) if max_value > 0 else 0
                pdf.set_fill_color(59, 130, 246)
                pdf.rect(bar_x, chart_y + chart_height - bar_h, bar_width, bar_h, 'F')
                pdf.set_xy(bar_x - 0.5, chart_y + chart_height + 1)
                pdf.set_font("Helvetica", '', 7)
                pdf.multi_cell(bar_width + 1, 3.5, self.normalize_pdf_text(subject[:4]), align='C')
                pdf.set_xy(bar_x - 0.5, chart_y + chart_height - bar_h - 4)
                pdf.set_font("Helvetica", '', 7)
                pdf.cell(bar_width + 1, 3.5, txt=f"{value:.1f}", align='C')

            pdf.set_xy(10, chart_y + chart_height + 16)
            pdf.ln(2)

            # Distribution summary table
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, txt="Class Level Distribution", ln=1)
            pdf.set_font("Helvetica", '', 9)
            for index, level in enumerate(LEVEL_ORDER):
                if index % 2 == 0:
                    pdf.set_fill_color(241, 245, 249)
                    pdf.cell(0, 5.5, txt=self.normalize_pdf_text(f"{level}: {self.summary['distribution'][level]}"), ln=1, fill=True)
                else:
                    pdf.cell(0, 5.5, txt=self.normalize_pdf_text(f"{level}: {self.summary['distribution'][level]}"), ln=1)
            pdf.ln(4)

            # Gender averages
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, txt="Gender Point Averages", ln=1)
            pdf.set_font("Helvetica", '', 9)
            for gender in ["male", "female", "other"]:
                count = self.summary['gender_counts'][gender]
                avg_points = self.summary['gender_totals'][gender] / count if count else 0
                pdf.cell(0, 5.5, txt=self.normalize_pdf_text(f"{gender.title()}: {count} student(s), Avg points {avg_points:.1f}"), ln=1)
            pdf.ln(4)

            # Subject ranking in two columns for compact one-page layout
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(0, 8, txt="Subject Ranking", ln=1)
            pdf.set_font("Helvetica", '', 9)
            rank_list = self.summary['subject_averages']
            half = (len(rank_list) + 1) // 2
            left_col = rank_list[:half]
            right_col = rank_list[half:]
            left_x = 10
            right_x = 105
            start_y = pdf.get_y()
            line_height = 5.5

            for index in range(max(len(left_col), len(right_col))):
                if index < len(left_col):
                    pdf.set_xy(left_x, start_y + index * line_height)
                    pdf.cell(90, line_height, txt=self.normalize_pdf_text(f"{index + 1}. {left_col[index][0][:20]} - {left_col[index][1]:.1f}"), ln=0)
                if index < len(right_col):
                    pdf.set_xy(right_x, start_y + index * line_height)
                    pdf.cell(90, line_height, txt=self.normalize_pdf_text(f"{index + half + 1}. {right_col[index][0][:20]} - {right_col[index][1]:.1f}"), ln=0)
            pdf.set_y(start_y + max(len(left_col), len(right_col)) * line_height + 4)

            if signature_path and os.path.exists(signature_path):
                try:
                    pdf.image(signature_path, x=150, y=250, w=45)
                    pdf.set_xy(150, 295)
                    pdf.set_font("Helvetica", '', 10)
                    pdf.cell(45, 6, txt="Headteacher", align='C')
                except Exception:
                    pass

            # Footer with page numbering
            pdf.set_xy(10, 290)
            pdf.set_font("Helvetica", '', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, txt=f"Generated on {self.normalize_pdf_text(self.current_exam_title)} | Page 1", ln=1, align='C')

            pdf.output(file_path)
            messagebox.showinfo("Report Saved", f"PDF exported to {os.path.basename(file_path)}")
        except Exception as exc:
            messagebox.showerror("PDF Error", f"Could not create PDF: {exc}")
