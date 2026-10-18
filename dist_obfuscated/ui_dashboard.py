from ui_marksheet_junior import JuniorMarkSheetView  # Import the new workshop file
from ui_marksheet_primary import PrimaryMarkSheetView  # For Grade 4-6
from ui_marksheet_playgroup import PlaygroupMarkSheetView
from ui_marksheet_pp1 import PP1MarkSheetView
from ui_marksheet_pp2 import PP2MarkSheetView
from ui_marksheet_lower import LowerMarkSheetView
from ui_summary import ClassSummaryView, SummaryChooser
from teachers_linked import TeachersLinkedView, get_subjects_for_class
from cba_task_manager import CBATaskManager
from cba_results_view import CBAResultsView
from cbc_levels_view import CBCLevelsView
from ui_marksheet_kicd import KICDMarkSheetView
from marksheet_chooser import MarksheetChooser, OLD_STYLE
from teachers_linked import map_class_name_to_config_key
from cbc_strands_view import CBCStrandsView
from create_exam_dialog import CreateExamDialog
from reportforms import ReportFormsView, ask_opening_closing_dates, ask_report_print_mode
from ocr_student_dialog import show_ocr_dialog
from excel_student_import import read_student_rows
import os
import sys
import json
import webbrowser
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import messagebox
from database import FreemanDB  # Ensure database.py is in the same folder
from PIL import Image
from wizard import SchoolSetupWizard
import network_manager
from cloud_service import CloudService, ask_cloud_credentials
import io
import contextlib
import subprocess

PERIOD_TERMS = ("Term 1", "Term 2", "Term 3")

# Classes that share one marksheet (and so one current exam) by group
MARKSHEET_CLASS_TYPES = [
    ("playgroup", "playgroup"),
    ("pp1", "pp1"),
    ("pp2", "pp2"),
    ("Grade 1", "lower"),
    ("Grade 2", "lower"),
    ("Grade 3", "lower"),
    ("Grade 4", "primary"),
    ("Grade 5", "primary"),
    ("Grade 6", "primary"),
    ("Grade 7", "jss"),
    ("Grade 8", "jss"),
    ("Grade 9", "jss"),
]


# Handle both development and executable environments
def get_app_dir():
    """Get the application directory, handling both script and executable environments"""
    if getattr(sys, "frozen", False):
        # Running as executable
        BASE_DIR = sys._MEIPASS
        USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    else:
        # Running as script
        BASE_DIR = os.path.dirname(os.path.realpath(__file__))
        USER_DATA_DIR = BASE_DIR
    return BASE_DIR, USER_DATA_DIR


class Dashboard(ctk.CTk):
    def __init__(self, school_name_placeholder="Freeman Tech Solutions (Demo)"):
        super().__init__()

        self.db = FreemanDB()
        self.BASE_DIR, self.USER_DATA_DIR = get_app_dir()

        theme_config = self.load_school_config()
        self.dashboard_appearance = theme_config.get("dashboard_appearance", "Dark")
        if self.dashboard_appearance not in ("Light", "Dark"):
            self.dashboard_appearance = "Dark"
        self.dashboard_accent = theme_config.get("dashboard_accent", "#1f6aa5")
        if (
            not isinstance(self.dashboard_accent, str)
            or len(self.dashboard_accent) != 7
            or not self.dashboard_accent.startswith("#")
            or not all(char in "0123456789abcdefABCDEF" for char in self.dashboard_accent[1:])
        ):
            self.dashboard_accent = "#1f6aa5"
        self.dashboard_background = theme_config.get("dashboard_background", "")
        self.dashboard_background_url = theme_config.get(
            "dashboard_background_url", ""
        )
        self.dashboard_particles_enabled = bool(
            theme_config.get("dashboard_particles_enabled", True)
        )
        self.dashboard_particles = []
        self.dashboard_particle_lines = []
        self.dashboard_particle_after_id = None
        self.dashboard_particle_canvas_size = (0, 0)
        self.bing_wallpaper_enabled = bool(
            theme_config.get("bing_wallpaper_enabled", False)
        )
        self.bing_wallpaper_last_refresh = theme_config.get(
            "bing_wallpaper_last_refresh", ""
        )
        self.bing_wallpaper_credit = theme_config.get("bing_wallpaper_credit", "")
        try:
            self.bing_wallpaper_interval_hours = int(
                theme_config.get("bing_wallpaper_interval_hours", 24)
            )
        except (TypeError, ValueError):
            self.bing_wallpaper_interval_hours = 24
        if self.bing_wallpaper_interval_hours not in (1, 3, 6, 12, 24, 48, 72):
            self.bing_wallpaper_interval_hours = 24
        self.bing_refresh_after_id = None
        self.control_drag_state = None
        self.dashboard_control_positions = theme_config.get(
            "dashboard_control_positions", {}
        )
        if not isinstance(self.dashboard_control_positions, dict):
            self.dashboard_control_positions = {}
        ctk.set_appearance_mode(self.dashboard_appearance)

        # --- ADD THESE TWO LINES HERE ---
        self.search_var = ctk.StringVar()
        self.all_student_rows = []
        self.portal_open = self.load_portal_state()  # Track portal state from config
        # --------------------------------

        self.overrideredirect(True)

        screen_width = self.winfo_screenwidth()

        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        # --- 1. WINDOW CONFIGURATION & CENTERING ---
        self.title("Freeman Tech Solutions - Home Page")

        # Dashboard is usually bigger (like 1100x700). We will center it.
        window_width = 1100
        window_height = 700

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        # This makes the window take up the entire screen

        # --- 1. ASSET PATHS ---
        default_bg_path = os.path.join(self.BASE_DIR, "assets", "dashboard_bg.jpg")
        bg_image_path = self.dashboard_background
        bing_cache_missing = self.bing_wallpaper_enabled and (
            not bg_image_path or not os.path.isfile(bg_image_path)
        )
        if not bg_image_path or not os.path.isfile(bg_image_path):
            bg_image_path = default_bg_path

        # --- THE BACKGROUND IMAGE WITH DIAGONAL WATERMARK ---
        try:
            self.set_dashboard_background(bg_image_path)
        except Exception as e:
            print(f"Background image error: {e}")

        # Optional: If you want to allow the user to exit fullscreen with the 'Esc' key
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # Use the name passed from the login (or default placeholder for now)
        self.dynamic_school_name = school_name_placeholder

        # --- 2. LAYOUT DESIGN ---
        # Column 0: Vertical Button Menu (Left Side)
        # Column 1: Main Content Area (Right Side, for future dynamic content)
        self.grid_columnconfigure(0, weight=0, minsize=250)  # Menu stays fixed size
        self.grid_columnconfigure(1, weight=1)  # Content area expands
        self.grid_rowconfigure(0, weight=1)

        # --- 3. MENU PANEL (Vertical Buttons) ---
        # This matches the boxes you drew on the left
        self.menu_panel = ctk.CTkScrollableFrame(
            self, corner_radius=0, border_width=1, border_color="grey"
        )
        self.menu_panel.grid(row=0, column=0, sticky="nsew")

        # Top Title/Brand in Menu
        self.brand_label = ctk.CTkLabel(
            self.menu_panel, text="Freeman OS", font=("Arial Bold", 20)
        )
        self.brand_label.pack(pady=(30, 20))

        # --- CREATE BUTTONS FROM YOUR DRAWING ---
        btn_width = 155  # Standardizing button size for neatness
        btn_height = 40
        btn_pady = 8  # Space between them

        # Placeholder text, to be replaced by icons later
        self.btn_register = ctk.CTkButton(
            self.menu_panel,
            text="Register Students",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(
                lambda: self.show_class_selection("Registration", self.btn_register)
            ),
        )
        self.btn_register.pack(pady=btn_pady)

        self.btn_mark_sheets = ctk.CTkButton(
            self.menu_panel,
            text="View Mark Sheets",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(
                lambda: self.show_class_selection("Mark Sheets", self.btn_mark_sheets)
            ),
        )
        self.btn_mark_sheets.pack(pady=btn_pady)

        self.btn_knec_cba = ctk.CTkButton(
            self.menu_panel,
            text="KNEC CBA",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(self.open_cba_menu),
        )
        self.btn_knec_cba.pack(pady=btn_pady)

        self.btn_competency_gradebook = ctk.CTkButton(
            self.menu_panel,
            text="Strands",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(self.open_competency_gradebook),
        )
        self.btn_competency_gradebook.pack(pady=btn_pady)

        self.btn_performance_dashboard = ctk.CTkButton(
            self.menu_panel,
            text="Performance\nDashboard",
            width=btn_width,
            height=btn_height + 8,
            command=lambda: self.require_auth(self.open_performance_dashboard),
        )
        self.btn_performance_dashboard.pack(pady=btn_pady)

        self.btn_summary = ctk.CTkButton(
            self.menu_panel,
            text="Student Marks Summary",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(
                lambda: self.show_class_selection("Summary", self.btn_summary)
            ),
        )
        self.btn_summary.pack(pady=btn_pady)

        self.btn_teachers = ctk.CTkButton(
            self.menu_panel,
            text="Teachers Linked",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(
                lambda: self.show_class_selection("Teachers", self.btn_teachers)
            ),
        )
        self.btn_teachers.pack(pady=btn_pady)

        self.btn_report_forms = ctk.CTkButton(
            self.menu_panel,
            text="View Report Forms",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(self.open_report_forms),
        )
        self.btn_report_forms.pack(pady=btn_pady)

        self.btn_newsletter = ctk.CTkButton(
            self.menu_panel,
            text="Newsletter & Circular",
            width=btn_width,
            height=btn_height,
            command=lambda: self.require_auth(self.open_newsletter),
        )
        self.btn_newsletter.pack(pady=btn_pady)

        # Spacer/Fill (This pushes the Exit button to the bottom)
        self.menu_spacer = ctk.CTkLabel(self.menu_panel, text="")
        self.menu_spacer.pack(expand=True, fill="y", pady=10)

        # For the Register button:
        self.btn_register.configure(
            command=lambda: self.require_auth(
                lambda: self.show_class_selection("Registering", self.btn_register)
            )
        )

        # For the Mark Sheets button:
        self.btn_mark_sheets.configure(
            command=lambda: self.require_auth(
                lambda: self.show_class_selection("Viewing Marks", self.btn_mark_sheets)
            )
        )

        # Add this at the end of your __init__ section
        self.sidebar_buttons = [
            self.btn_register,
            self.btn_mark_sheets,
            self.btn_knec_cba,
            self.btn_competency_gradebook,
            self.btn_performance_dashboard,
            self.btn_summary,
            self.btn_teachers,
            self.btn_report_forms,
            self.btn_newsletter,
        ]
        self.btn_portal = ctk.CTkButton(
            self.menu_panel,
            text="📡 Launch Teacher Portal",
            command=lambda: self.require_auth(self.handle_portal_button),
            fg_color="green",
            width=btn_width,
            height=btn_height,
        )
        self.btn_portal.pack(pady=10)
        self.update_portal_button()  # Set initial button state based on loaded config

        self.btn_cloud_sync = ctk.CTkButton(
            self.menu_panel,
            text="🔄 Sync Students Cloud",
            command=lambda: self.require_auth(self.handle_cloud_sync_button),
            fg_color="#1f538d",
            hover_color="#153d66",
            width=btn_width,
            height=btn_height,
        )
        self.btn_cloud_sync.pack(pady=10)

        # Exit Button at the bottom
        self.btn_exit = ctk.CTkButton(
            self.menu_panel,
            text="Exit",
            width=btn_width,
            height=btn_height,
            fg_color="#e74c3c",
            hover_color="#c0392b",  # Red for Exit
            command=self.exit_app,
        )
        self.btn_exit.pack(pady=(0, 30))

        # --- 4. MAIN CONTENT PANEL ---
        self.content_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.content_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.create_content_background()

        self.header_frame = ctk.CTkFrame(
            self.content_panel, width=1, height=1, fg_color="transparent"
        )
        self.header_frame.place_forget()
        self.create_home_header_controls()
        self.update_countdown_timer()
        self.check_pending_alerts_on_startup()
        self.check_for_updates_on_startup()

        # Row 1 of Content: Future Workspace (Currently blank, can be used for summary stats later)
        self.work_area_label = ctk.CTkLabel(
            self.content_panel,
            text="Dashboard Workspace initialized.\nClick a menu button on the left to begin.",
            font=("Arial", 16),
            text_color="gray60",
        )
        self.work_area_label.pack(expand=True)

        # --- 5. THE THEME/MODE TOGGLE (Bottom right of content) ---
        # Dark mode | Light mode toggle buttons from your drawing
        self.theme_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        self.theme_frame.place_forget()
        self.create_theme_controls()
        self.apply_dashboard_theme()
        # --- ADD THIS INSIDE YOUR DashboardApp CLASS ---

        self.all_student_rows = []
        if self.bing_wallpaper_enabled:
            self.after(
                1200,
                lambda: self.refresh_bing_wallpaper_if_due(
                    force=bing_cache_missing
                ),
            )
        elif self.dashboard_background_url:
            self.after(1200, self.refresh_online_dashboard_background)

    def open_wizard(self):
        # This calls the class we created in the previous step
        SchoolSetupWizard(self, self.db)

    def create_home_header_controls(self):
        self.countdown_label = ctk.CTkLabel(
            self.content_panel,
            text="⏳ -- days",
            font=("Arial Bold", 16),
            text_color="#10b981",
        )
        self.countdown_label.place(relx=1, rely=0, anchor="ne", x=-12, y=12)
        self.period_label = ctk.CTkLabel(
            self.content_panel, text="", font=("Arial Bold", 16), text_color="#10b981"
        )
        self.period_label.place(x=12, y=12)
        self.period_button = ctk.CTkButton(
            self.content_panel,
            text="Year & Term",
            width=120,
            height=30,
            command=lambda: self.require_auth(self.open_period_dialog),
        )
        self.period_button.place(x=12, y=44)
        self.refresh_period_label()
        self.btn_system_settings = ctk.CTkButton(
            self.content_panel,
            text="⚙️ System Settings",
            command=lambda: self.run_draggable_button_command(
                "dashboard_system_settings_button",
                lambda: self.require_auth(self.open_system_settings),
            ),
            fg_color="#34495e",
            hover_color="#2c3e50",
            height=35,
            font=("Arial Bold", 12),
        )
        self.btn_create_exam = ctk.CTkButton(
            self.content_panel,
            text="📝 Create Exam",
            command=lambda: self.run_draggable_button_command(
                "dashboard_create_exam_button",
                lambda: self.require_auth(self.open_create_exam_dialog),
            ),
            fg_color="#8e44ad",
            hover_color="#732d91",
            height=35,
            font=("Arial Bold", 12),
        )
        self.btn_check_updates = ctk.CTkButton(
            self.content_panel,
            text="🔄 Update Available",
            command=lambda: self.require_auth(self.check_for_updates),
            fg_color="#3498db",
            hover_color="#2980b9",
            height=40,
            font=("Arial Bold", 13),
            corner_radius=8,
            border_width=2,
            border_color="#2980b9",
        )
        self.bind_control_drag_events(
            self.btn_system_settings, "dashboard_system_settings_button"
        )
        self.layout_dashboard_control_group("dashboard_system_settings_button")
        self.bind_control_drag_events(self.btn_create_exam, "dashboard_create_exam_button")
        self.layout_dashboard_control_group("dashboard_create_exam_button")
        self.btn_check_updates.place(relx=1, rely=0, anchor="ne", x=-12, y=204)
        self.btn_check_updates.lift()

    def get_academic_year(self):
        try:
            return int(self.load_school_config().get("academic_year"))
        except (TypeError, ValueError):
            return None

    def get_current_term(self):
        term = self.load_school_config().get("current_term")
        return term if term in PERIOD_TERMS else PERIOD_TERMS[0]

    def refresh_period_label(self):
        label = getattr(self, "period_label", None)
        if label is None or not label.winfo_exists():
            return
        year = self.get_academic_year()
        label.configure(
            text=f"{self.get_current_term()} \u00b7 {year}" if year else "Set the year and term"
        )

    def open_period_dialog(self):
        year = self.get_academic_year()
        term = self.get_current_term()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Year & Term")
        dialog.geometry("460x430")
        dialog.transient(self)
        dialog.grab_set()

        if year is None:
            ctk.CTkLabel(dialog, text="Set the current year", font=("Arial Bold", 20)).pack(pady=(24, 6))
            ctk.CTkLabel(
                dialog,
                text="Type the current year once. After this the year can only move forward.",
                wraplength=380,
                text_color="gray",
            ).pack(pady=(0, 10))
            year_entry = ctk.CTkEntry(dialog, width=160, placeholder_text="e.g. 2026")
            year_entry.pack(pady=6)
            term_menu = ctk.CTkOptionMenu(dialog, values=list(PERIOD_TERMS), width=160)
            term_menu.set(term)
            term_menu.pack(pady=6)

            def save_first():
                text = year_entry.get().strip()
                if not text.isdigit() or not 2000 <= int(text) <= datetime.now().year + 1:
                    messagebox.showerror("Year", "Enter a valid current year.", parent=dialog)
                    return
                self.set_period(int(text), term_menu.get())
                dialog.destroy()

            ctk.CTkButton(dialog, text="Save", height=38, command=save_first).pack(pady=16)
            return

        ctk.CTkLabel(dialog, text=f"Year {year}", font=("Arial Bold", 22)).pack(pady=(24, 6))
        ctk.CTkLabel(dialog, text="Term").pack()
        # A term can be kept or moved forward, never back.
        term_menu = ctk.CTkOptionMenu(
            dialog, values=list(PERIOD_TERMS[PERIOD_TERMS.index(term):]), width=160
        )
        term_menu.set(term)
        term_menu.pack(pady=6)

        def set_term():
            chosen = term_menu.get()
            if chosen != term and not messagebox.askyesno(
                "Change Term",
                f"Move to {chosen}? The current exam is saved as read-only {term} history "
                f"and {chosen} starts with no exam.",
                parent=dialog,
            ):
                return
            self.set_period(year, chosen)
            dialog.destroy()

        def reflect():
            dialog.destroy()
            self.reflect_period_to_portal()

        def next_year():
            dialog.destroy()
            self.start_next_year()

        ctk.CTkButton(dialog, text="Set Term", height=36, command=set_term).pack(pady=(10, 4))
        ctk.CTkButton(
            dialog, text="Reflect to Portal", height=36, fg_color="#10b981", text_color="black",
            command=reflect,
        ).pack(pady=4)
        ctk.CTkLabel(dialog, text="New school year", font=("Arial Bold", 14)).pack(pady=(24, 2))
        ctk.CTkLabel(
            dialog,
            text=f"Starts {year + 1}: promotes every learner and makes {year} read-only.",
            wraplength=380,
            text_color="gray",
        ).pack()
        ctk.CTkButton(
            dialog, text=f"Start {year + 1}", height=36, fg_color="#e67e22", hover_color="#d35400",
            command=next_year,
        ).pack(pady=8)

    def set_period(self, year, term):
        old_year = self.get_academic_year()
        if old_year is None:
            self.db.backfill_previous_exam_year(year)
        elif term != self.get_current_term():
            self.snapshot_exams()
        self.save_school_config({"academic_year": year, "current_term": term})
        self.refresh_period_label()

    def snapshot_exams(self):
        """Store every class's running exam as read-only history under the current term and year."""
        config = self.load_school_config()
        cleared = {"current_exam_title": ""}
        for class_name, grade_type in MARKSHEET_CLASS_TYPES:
            if config.get(f"{grade_type}_exam_title"):
                self.store_class_exam(class_name, grade_type, config)
            cleared[f"{grade_type}_exam_title"] = ""
            cleared[f"{grade_type}_exam_term"] = ""
        self.save_school_config(cleared)

    def start_next_year(self):
        year = self.get_academic_year()
        if not year:
            return
        new_year = year + 1
        portal_rollover = messagebox.askyesnocancel(
            "Start New Year",
            f"Start {new_year}?\n\n"
            f"- Every learner moves to the next class.\n"
            f"- {year} exams are kept read-only.\n"
            f"- Yes: copy portal marks to this computer and clear the portal.\n"
            f"- No: start this computer only.\n\nThis cannot be undone.",
        )
        if portal_rollover is None:
            return
        if portal_rollover:
            credentials = ask_cloud_credentials(self)
            if not credentials:
                return
            archived, error = self.archive_portal_marks(year, self.get_current_term(), credentials)
            if not archived:
                messagebox.showerror("Portal Archive Failed", error)
                return
            result = CloudService().start_new_year(new_year, PERIOD_TERMS[0], credentials)
            if not result.get("success"):
                messagebox.showerror(
                    "Portal Reset Failed",
                    result.get("message", "Portal marks were downloaded, but the portal could not be reset."),
                )
                return
        self.snapshot_exams()
        # Marks are keyed by admission number, so they must not follow learners into the new class.
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%\\_marks' ESCAPE '\\'")
        for (table_name,) in cursor.fetchall():
            cursor.execute(f"DELETE FROM {table_name}")
        self.db.conn.commit()
        self.execute_student_promotion()
        self.save_school_config({"academic_year": new_year, "current_term": PERIOD_TERMS[0]})
        self.refresh_period_label()
        if portal_rollover:
            messagebox.showinfo(
                "New Year Started",
                f"{new_year} started. Previous portal marks are saved on this computer, and the portal is ready for the new year.",
            )

    def archive_portal_marks(self, year, term, credentials):
        service = CloudService()
        config = self.load_school_config()
        archived_records = []
        for class_name, grade_type in MARKSHEET_CLASS_TYPES:
            result = service.fetch_marks(class_name, credentials)
            if not result.get("success"):
                return False, result.get("message", f"Could not fetch portal marks for {class_name}.")
            records = result.get("marks", [])
            if records:
                archived_records.append((class_name, grade_type, records))

        summary = json.dumps({
            "total_students": 0,
            "distribution": {},
            "gender_counts": {},
            "gender_totals": {},
            "subject_averages": [],
            "has_history": False,
            "trend_text": "Portal archive",
        })
        for class_name, grade_type, records in archived_records:
            subjects = config.get("subjects", {}).get(grade_type, [])
            if not subjects:
                subjects = {
                    "playgroup": ["MATH", "CREAT", "ENV"],
                    "pp1": ["MATH", "ENV", "PSYCH", "REL"],
                    "pp2": ["MATH", "ENV", "PSYCH", "REL"],
                    "lower": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
                    "primary": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
                    "jss": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"],
                }.get(grade_type, [])
            by_exam = {}
            for record in records:
                exam_title = str(record.get("exam_title") or config.get(f"{grade_type}_exam_title") or f"Portal Marks {year}")
                scores = record.get("scores") or {}
                row = [record.get("student_name", "")]
                for subject in subjects:
                    normalized = subject.strip().lower()
                    key = next(
                        (name for name in scores if name.strip().lower() == normalized),
                        next((name for name in scores if normalized in name.strip().lower() or name.strip().lower() in normalized), None),
                    )
                    entry = scores.get(key, {}) if key else {}
                    if not isinstance(entry, dict):
                        entry = {"score": entry}
                    row.extend([entry.get("score", entry.get("raw", "")), entry.get("rating", "")])
                    if grade_type == "jss":
                        row.append(entry.get("points", ""))
                if grade_type == "jss":
                    row.extend([record.get("total_points", ""), "", "-"])
                else:
                    row.extend([record.get("total_scores", ""), ""])
                by_exam.setdefault(exam_title, []).append(row)

            for exam_title, rows in by_exam.items():
                existing, _ = self.db.get_previous_exam_data(exam_title, class_name, year)
                current_title = config.get(f"{grade_type}_exam_title", "")
                if grade_type == "jss":
                    current_title = current_title or config.get("current_exam_title", "")
                saved_title = f"{exam_title} (Portal)" if existing or current_title == exam_title else exam_title
                try:
                    self.db.save_previous_exam(
                        saved_title,
                        class_name,
                        summary,
                        json.dumps(rows),
                        term=term,
                        year=year,
                    )
                except Exception as error:
                    return False, f"Could not save portal marks for {class_name}: {error}"
        return True, ""

    def reflect_period_to_portal(self):
        year = self.get_academic_year()
        if not year:
            messagebox.showwarning("Year & Term", "Set the year and term first.")
            return
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return
        result = CloudService().set_period(year, self.get_current_term(), credentials)
        if result.get("success"):
            messagebox.showinfo("Portal", result.get("message", "Portal updated."))
        else:
            messagebox.showerror("Portal", result.get("message", "Could not update the portal."))

    def bind_control_drag_events(self, widget, group_name):
        widget.bind(
            "<ButtonPress-1>",
            lambda event, name=group_name: self.begin_control_drag(event, name),
            add="+",
        )
        widget.bind(
            "<B1-Motion>",
            lambda event, name=group_name: self.move_control_drag(event, name),
            add="+",
        )
        widget.bind(
            "<ButtonRelease-1>",
            lambda event, name=group_name: self.finish_control_drag(name),
            add="+",
        )
        for child in widget.winfo_children():
            self.bind_control_drag_events(child, group_name)

    def run_draggable_button_command(self, group_name, command):
        drag_state = self.control_drag_state
        if drag_state and drag_state["group"] == group_name and drag_state["moved"]:
            return
        command()

    def get_control_position(self, group_name):
        defaults = {
            "dashboard_system_settings_button": {"x": -12, "y": 108},
            "dashboard_create_exam_button": {"x": -12, "y": 152},
        }
        position = self.dashboard_control_positions.get(
            group_name, defaults[group_name]
        )
        try:
            return int(position.get("x", defaults[group_name]["x"])), int(
                position.get("y", defaults[group_name]["y"])
            )
        except (AttributeError, TypeError, ValueError):
            return defaults[group_name]["x"], defaults[group_name]["y"]

    def layout_dashboard_control_group(self, group_name):
        x, y = self.get_control_position(group_name)
        if group_name == "dashboard_system_settings_button":
            button = self.btn_system_settings
        elif group_name == "dashboard_create_exam_button":
            button = self.btn_create_exam
        else:
            return

        button.place(relx=1, rely=0, anchor="ne", x=x, y=y)
        button.lift()

    def begin_control_drag(self, event, group_name):
        x, y = self.get_control_position(group_name)
        self.control_drag_state = {
            "group": group_name,
            "root_x": event.x_root,
            "root_y": event.y_root,
            "x": x,
            "y": y,
            "moved": False,
        }

    def move_control_drag(self, event, group_name):
        state = self.control_drag_state
        if not state or state["group"] != group_name:
            return

        parent_width = max(1, self.content_panel.winfo_width())
        parent_height = max(1, self.content_panel.winfo_height())
        group_width, group_height = 380, 42
        minimum_y, maximum_y = 0, max(0, parent_height - group_height)

        x = state["x"] + event.x_root - state["root_x"]
        y = state["y"] + event.y_root - state["root_y"]
        if abs(x - state["x"]) + abs(y - state["y"]) >= 3:
            state["moved"] = True
        if not state["moved"]:
            return
        x = min(0, max(-parent_width + group_width, x))
        y = min(maximum_y, max(minimum_y, y))
        self.dashboard_control_positions[group_name] = {"x": x, "y": y}
        self.layout_dashboard_control_group(group_name)

    def finish_control_drag(self, group_name):
        if not self.control_drag_state or self.control_drag_state["group"] != group_name:
            return
        position = self.dashboard_control_positions.get(group_name)
        if position and self.control_drag_state["moved"]:
            self.save_school_config(
                {"dashboard_control_positions": self.dashboard_control_positions}
            )
        self.control_drag_state = None

    def create_theme_controls(self):
        self.theme_toggle = ctk.CTkSegmentedButton(
            self.content_panel,
            values=["Light Mode", "Dark Mode"],
            command=self.change_theme_event,
        )
        self.theme_toggle.set(f"{self.dashboard_appearance} Mode")

        self.theme_settings_button = ctk.CTkButton(
            self.content_panel,
            text="Customize Theme",
            width=130,
            command=self.open_theme_settings,
        )
        self.subjects_button = ctk.CTkButton(
            self.content_panel,
            text="Subjects",
            width=100,
            command=lambda: self.require_auth(self.open_subjects_dialog),
        )
        self.theme_toggle.place(relx=1, rely=1, anchor="se", x=-150, y=-12)
        self.theme_settings_button.place(
            relx=1, rely=1, anchor="se", x=-12, y=-12
        )
        toggle_width = max(self.theme_toggle.winfo_reqwidth(), 200)
        self.subjects_button.place(
            relx=1, rely=1, anchor="se", x=-(150 + toggle_width + 10), y=-12
        )
        self.theme_toggle.lift()
        self.theme_settings_button.lift()
        self.subjects_button.lift()

    def open_subjects_dialog(self):
        from subject_catalog import (
            CATALOG_GROUPS,
            build_catalog,
            config_updates,
        )

        catalog = build_catalog(self.load_school_config())
        dialog = ctk.CTkToplevel(self)
        dialog.title("School Subjects")
        dialog.geometry("760x640")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Tick the subjects your school teaches", font=("Arial Bold", 18)
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            dialog,
            text="The short form is used on marksheets; teachers see the full name. Short forms are editable.",
            text_color="gray",
        ).pack(pady=(0, 8))

        tabs = ctk.CTkTabview(dialog)
        tabs.pack(fill="both", expand=True, padx=14, pady=4)
        rows = {key: [] for key, _, _, _ in CATALOG_GROUPS}
        limits = {key: limit for key, _, _, limit in CATALOG_GROUPS}

        def add_row(key, frame, item):
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=2)
            var = ctk.BooleanVar(value=item["selected"])
            ctk.CTkCheckBox(row, text="", variable=var, width=24).pack(side="left")
            if item["custom"]:
                name_widget = ctk.CTkEntry(row, width=330)
                name_widget.insert(0, item["name"])
            else:
                name_widget = ctk.CTkLabel(row, text=item["name"], width=330, anchor="w")
            name_widget.pack(side="left", padx=(4, 8))
            short = ctk.CTkEntry(row, width=120)
            short.insert(0, item["short"])
            short.pack(side="left")
            record = {"var": var, "name": name_widget, "short": short,
                      "custom": item["custom"], "base": item["name"], "row": row}
            if item["custom"]:
                def remove(rec=record, k=key):
                    rec["row"].destroy()
                    rows[k].remove(rec)
                ctk.CTkButton(row, text="Remove", width=70, fg_color="#942727",
                              hover_color="#7a1f1f", command=remove).pack(side="left", padx=8)
            rows[key].append(record)

        for key, title, _, limit in CATALOG_GROUPS:
            tab = tabs.add(title.split(" (")[0])
            ctk.CTkLabel(tab, text=f"{title} - up to {limit} subjects", text_color="gray").pack(anchor="w", padx=6)
            frame = ctk.CTkScrollableFrame(tab, height=360)
            frame.pack(fill="both", expand=True, pady=4)
            for item in catalog[key]:
                add_row(key, frame, item)

            add_bar = ctk.CTkFrame(tab, fg_color="transparent")
            add_bar.pack(fill="x")
            name_entry = ctk.CTkEntry(add_bar, width=300, placeholder_text="New subject (full name)")
            name_entry.pack(side="left", padx=4)
            short_entry = ctk.CTkEntry(add_bar, width=110, placeholder_text="Short form")
            short_entry.pack(side="left", padx=4)

            def add_custom(k=key, f=frame, n=name_entry, s=short_entry):
                full = n.get().strip()
                short_form = s.get().strip().upper()
                if not full or not short_form:
                    messagebox.showwarning("Subjects", "Enter both the full name and the short form.", parent=dialog)
                    return
                add_row(k, f, {"name": full, "short": short_form, "selected": True, "custom": True})
                n.delete(0, "end")
                s.delete(0, "end")

            ctk.CTkButton(add_bar, text="Add subject", width=100, command=add_custom).pack(side="left", padx=4)

        def save():
            result = {}
            for key, records in rows.items():
                items, shorts = [], set()
                for rec in records:
                    short = rec["short"].get().strip().upper()
                    name = rec["name"].get().strip() if rec["custom"] else rec["base"]
                    selected = bool(rec["var"].get())
                    if selected and (not short or not name):
                        messagebox.showwarning("Subjects", "Every ticked subject needs a name and a short form.", parent=dialog)
                        return
                    if selected and short in shorts:
                        messagebox.showwarning("Subjects", f"Short form {short} is used twice in the same level.", parent=dialog)
                        return
                    if selected:
                        shorts.add(short)
                    items.append({"name": name, "short": short, "selected": selected, "custom": rec["custom"]})
                if len(shorts) > limits[key]:
                    messagebox.showwarning("Subjects", f"At most {limits[key]} subjects fit this level's marksheet.", parent=dialog)
                    return
                result[key] = items
            self.save_school_config(config_updates(result))
            messagebox.showinfo(
                "Subjects",
                "Subjects saved. Sync with the cloud portal to update teachers.",
                parent=dialog,
            )
            dialog.destroy()

        ctk.CTkButton(
            dialog, text="Save Subjects", fg_color="#10b981", text_color="black",
            height=40, command=save,
        ).pack(fill="x", padx=14, pady=10)

    def open_theme_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Customize Dashboard Theme")
        dialog.geometry("460x590")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Dashboard accent color", font=("Arial Bold", 18)
        ).pack(pady=(24, 16))

        swatches = ctk.CTkFrame(dialog, fg_color="transparent")
        swatches.pack(pady=8)
        accent_presets = {
            "Ocean": "#1f6aa5",
            "Forest": "#25855a",
            "Coral": "#c65d3a",
            "Teal": "#168c8c",
        }
        for name, color in accent_presets.items():
            ctk.CTkButton(
                swatches,
                text=name,
                width=82,
                fg_color=color,
                hover_color=self.get_hover_color(color),
                command=lambda selected=color: self.set_dashboard_accent(selected),
            ).pack(side="left", padx=4)

        ctk.CTkButton(
            dialog,
            text="Choose custom color...",
            command=self.choose_dashboard_accent,
        ).pack(pady=16)

        ctk.CTkLabel(
            dialog, text="Dashboard picture", font=("Arial Bold", 18)
        ).pack(pady=(12, 8))
        ctk.CTkButton(
            dialog,
            text="Choose picture from this computer...",
            command=self.choose_dashboard_background,
        ).pack(pady=5)
        ctk.CTkButton(
            dialog,
            text="Download picture from a URL...",
            command=self.download_dashboard_background,
        ).pack(pady=5)
        ctk.CTkButton(
            dialog,
            text="Restore default picture",
            command=self.restore_default_dashboard_background,
        ).pack(pady=5)

        self.bing_wallpaper_var = ctk.BooleanVar(
            value=self.bing_wallpaper_enabled
        )
        self.bing_wallpaper_switch = ctk.CTkSwitch(
            dialog,
            text="Daily Bing travel pictures",
            variable=self.bing_wallpaper_var,
            command=lambda: self.set_bing_wallpaper_enabled(
                self.bing_wallpaper_var.get()
            ),
            onvalue=True,
            offvalue=False,
        )
        self.bing_wallpaper_switch.pack(pady=(12, 4))

        ctk.CTkLabel(dialog, text="Check for a new picture every:").pack(pady=(8, 2))
        self.bing_interval_menu = ctk.CTkOptionMenu(
            dialog,
            values=["1 hour", "3 hours", "6 hours", "12 hours", "24 hours", "48 hours", "72 hours"],
            command=self.set_bing_wallpaper_interval,
        )
        self.bing_interval_menu.set(
            f"{self.bing_wallpaper_interval_hours} hours"
            if self.bing_wallpaper_interval_hours != 1
            else "1 hour"
        )
        self.bing_interval_menu.pack(pady=(2, 8))

        ctk.CTkLabel(
            dialog,
            text="Bing may publish a new image daily. Internet is needed to check; the cached picture stays available offline.",
            text_color="gray",
            wraplength=400,
        ).pack(pady=(4, 8))
        if self.bing_wallpaper_credit:
            ctk.CTkLabel(
                dialog,
                text=self.bing_wallpaper_credit,
                text_color="gray",
                wraplength=400,
            ).pack(pady=(0, 8))

        self.dashboard_particles_var = ctk.BooleanVar(
            value=self.dashboard_particles_enabled
        )
        ctk.CTkSwitch(
            dialog,
            text="Portal-style moving particles",
            variable=self.dashboard_particles_var,
            command=lambda: self.set_dashboard_particles_enabled(
                self.dashboard_particles_var.get()
            ),
        ).pack(pady=(4, 12))

        ctk.CTkButton(dialog, text="Done", command=dialog.destroy, width=100).pack()

    def set_dashboard_background(self, image_path):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        background = Image.open(image_path).convert("RGB")
        background = background.resize((screen_width, screen_height))

        self.bg_image = ctk.CTkImage(
            background, size=(screen_width, screen_height)
        )
        self.content_background_source = background.copy()
        if hasattr(self, "bg_label") and self.bg_label.winfo_exists():
            self.bg_label.configure(image=self.bg_image)
        else:
            self.bg_label = ctk.CTkLabel(self, image=self.bg_image, text="")
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_label.lower()
        self.create_content_background()

    def create_content_background(self):
        if not hasattr(self, "content_panel") or not hasattr(self, "bg_image"):
            return
        if not self.content_panel.winfo_exists():
            return
        canvas = self.content_panel._canvas
        if not hasattr(self, "content_background_item"):
            self.content_background_item = canvas.create_image(
                0, 0, anchor="nw", tags=("dashboard_wallpaper",)
            )
            self.content_panel.bind(
                "<Configure>", self.resize_content_background, add="+"
            )
        self.resize_content_background()

    def resize_content_background(self, event=None):
        if not hasattr(self, "content_background_item"):
            return
        width = max(1, self.content_panel.winfo_width())
        height = max(1, self.content_panel.winfo_height())
        scale = max(0.1, float(self.content_panel._get_widget_scaling()))
        root_x = round(
            (self.content_panel.winfo_rootx() - self.winfo_rootx()) / scale
        )
        root_y = round(
            (self.content_panel.winfo_rooty() - self.winfo_rooty()) / scale
        )
        source_canvas_width = max(1, round(width / scale))
        source_canvas_height = max(1, round(height / scale))
        source_width, source_height = self.content_background_source.size
        left = max(0, min(source_width - 1, root_x))
        top = max(0, min(source_height - 1, root_y))
        right = max(
            left + 1, min(source_width, root_x + source_canvas_width)
        )
        bottom = max(
            top + 1, min(source_height, root_y + source_canvas_height)
        )
        background = self.content_background_source.crop((left, top, right, bottom))
        if background.size != (width, height):
            background = background.resize((width, height))
        from PIL import ImageTk

        self.content_background_photo = ImageTk.PhotoImage(background)
        canvas = self.content_panel._canvas
        canvas.itemconfigure(
            self.content_background_item,
            image=self.content_background_photo,
        )
        canvas.coords(self.content_background_item, 0, 0)
        canvas.tag_raise(self.content_background_item)
        self.resize_dashboard_particles(width, height)

    def set_dashboard_particles_enabled(self, enabled):
        self.dashboard_particles_enabled = bool(enabled)
        self.save_school_config(
            {"dashboard_particles_enabled": self.dashboard_particles_enabled}
        )
        canvas = getattr(getattr(self, "content_panel", None), "_canvas", None)
        if not canvas:
            return
        if enabled:
            self.resize_content_background()
            self.start_dashboard_particles()
        else:
            if self.dashboard_particle_after_id:
                self.after_cancel(self.dashboard_particle_after_id)
                self.dashboard_particle_after_id = None
            canvas.delete("dashboard_particle_line")
            canvas.delete("dashboard_particle_dot")
            self.dashboard_particles = []
            self.dashboard_particle_lines = []

    def resize_dashboard_particles(self, width, height):
        if not self.dashboard_particles_enabled:
            return
        old_width, old_height = self.dashboard_particle_canvas_size
        if width < 10 or height < 10:
            return
        if not self.dashboard_particles:
            import random

            particle_count = 65
            self.dashboard_particles = [
                {
                    "x": random.uniform(0, width),
                    "y": random.uniform(0, height),
                    "vx": random.uniform(-0.7, 0.7),
                    "vy": random.uniform(-0.7, 0.7),
                    "size": 2.5,
                    "item": self.content_panel._canvas.create_oval(
                        0,
                        0,
                        0,
                        0,
                        fill="#10b981",
                        outline="",
                        tags=("dashboard_particle_dot",),
                    ),
                }
                for _ in range(particle_count)
            ]
            self.dashboard_particle_lines = [
                (
                    first,
                    second,
                    self.content_panel._canvas.create_line(
                        0,
                        0,
                        0,
                        0,
                        fill="#187b6b",
                        width=1,
                        state="hidden",
                        tags=("dashboard_particle_line",),
                    ),
                )
                for first in range(particle_count)
                for second in range(first + 1, particle_count)
            ]
        elif old_width and old_height and (old_width, old_height) != (width, height):
            scale_x = width / old_width
            scale_y = height / old_height
            for particle in self.dashboard_particles:
                particle["x"] *= scale_x
                particle["y"] *= scale_y
        self.dashboard_particle_canvas_size = (width, height)
        self.start_dashboard_particles()

    def start_dashboard_particles(self):
        if (
            not self.dashboard_particles_enabled
            or not self.dashboard_particles
            or self.dashboard_particle_after_id
        ):
            return
        self.animate_dashboard_particles()

    def animate_dashboard_particles(self):
        if not self.dashboard_particles_enabled or not self.content_panel.winfo_exists():
            self.dashboard_particle_after_id = None
            return

        canvas = self.content_panel._canvas
        width, height = self.dashboard_particle_canvas_size
        for particle in self.dashboard_particles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            if particle["x"] < 0 or particle["x"] > width:
                particle["vx"] *= -1
            if particle["y"] < 0 or particle["y"] > height:
                particle["vy"] *= -1
            size = particle["size"]
            canvas.coords(
                particle["item"],
                particle["x"] - size,
                particle["y"] - size,
                particle["x"] + size,
                particle["y"] + size,
            )

        for first, second, line_id in self.dashboard_particle_lines:
            particle_a = self.dashboard_particles[first]
            particle_b = self.dashboard_particles[second]
            distance = (
                (particle_a["x"] - particle_b["x"]) ** 2
                + (particle_a["y"] - particle_b["y"]) ** 2
            ) ** 0.5
            if distance < 120:
                canvas.coords(
                    line_id,
                    particle_a["x"],
                    particle_a["y"],
                    particle_b["x"],
                    particle_b["y"],
                )
                canvas.itemconfigure(line_id, state="normal")
            else:
                canvas.itemconfigure(line_id, state="hidden")

        canvas.tag_raise("dashboard_wallpaper")
        canvas.tag_raise("dashboard_particle_line")
        canvas.tag_raise("dashboard_particle_dot")
        self.dashboard_particle_after_id = self.after(
            40, self.animate_dashboard_particles
        )

    def choose_dashboard_background(self):
        from tkinter import filedialog
        import shutil

        source_path = filedialog.askopenfilename(
            parent=self,
            title="Choose Dashboard Picture",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not source_path:
            return

        try:
            background_dir = os.path.join(
                self.USER_DATA_DIR, "dashboard_backgrounds"
            )
            os.makedirs(background_dir, exist_ok=True)
            extension = os.path.splitext(source_path)[1].lower()
            destination = os.path.join(background_dir, f"dashboard_wallpaper{extension}")
            if os.path.abspath(source_path) != os.path.abspath(destination):
                shutil.copy2(source_path, destination)
            self.set_dashboard_background(destination)
            self.dashboard_background = destination
            self.dashboard_background_url = ""
            self.bing_wallpaper_enabled = False
            if hasattr(self, "bing_wallpaper_var"):
                self.bing_wallpaper_var.set(False)
            self.save_school_config(
                {
                    "dashboard_background": destination,
                    "dashboard_background_url": "",
                    "bing_wallpaper_enabled": False,
                }
            )
        except Exception as error:
            messagebox.showerror("Picture Error", f"Could not use this picture: {error}")

    def download_dashboard_background(self):
        from urllib.parse import urlparse

        dialog = ctk.CTkInputDialog(
            text="Enter a direct HTTPS or HTTP image URL:",
            title="Download Dashboard Picture",
        )
        image_url = dialog.get_input()
        if not image_url:
            return
        image_url = image_url.strip()
        parsed_url = urlparse(image_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            messagebox.showerror("Invalid URL", "Enter a valid HTTP or HTTPS URL.")
            return

        try:
            destination = self.fetch_dashboard_background(image_url)
            self.set_dashboard_background(destination)
            self.dashboard_background = destination
            self.dashboard_background_url = image_url
            self.bing_wallpaper_enabled = False
            if hasattr(self, "bing_wallpaper_var"):
                self.bing_wallpaper_var.set(False)
            self.save_school_config(
                {
                    "dashboard_background": destination,
                    "dashboard_background_url": image_url,
                    "bing_wallpaper_enabled": False,
                }
            )
        except Exception as error:
            messagebox.showerror(
                "Download Error", f"Could not download this picture: {error}"
            )

    def fetch_dashboard_background(self, image_url, filename_prefix="downloaded_wallpaper"):
        from urllib.parse import urlparse
        from urllib.request import Request, urlopen

        parsed_url = urlparse(image_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise ValueError("Enter a valid HTTP or HTTPS image URL.")

        request = Request(image_url, headers={"User-Agent": "FreemanSchoolPortal"})
        with urlopen(request, timeout=15) as response:
            image_bytes = response.read(10 * 1024 * 1024 + 1)
        if len(image_bytes) > 10 * 1024 * 1024:
            raise ValueError("The picture must be 10 MB or smaller.")

        image = Image.open(io.BytesIO(image_bytes))
        extensions = {
            "JPEG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp",
            "BMP": ".bmp",
        }
        if image.format not in extensions:
            raise ValueError("Use a JPEG, PNG, WebP, or BMP image.")
        image.verify()

        background_dir = os.path.join(self.USER_DATA_DIR, "dashboard_backgrounds")
        os.makedirs(background_dir, exist_ok=True)
        destination = os.path.join(
            background_dir, f"{filename_prefix}{extensions[image.format]}"
        )
        with open(destination, "wb") as image_file:
            image_file.write(image_bytes)
        return destination

    def refresh_online_dashboard_background(self):
        import threading

        image_url = self.dashboard_background_url

        def refresh():
            try:
                destination = self.fetch_dashboard_background(image_url)
                self.after(
                    0,
                    lambda: self.apply_online_dashboard_background(
                        image_url, destination
                    ),
                )
            except Exception as error:
                print(f"Online dashboard picture refresh failed: {error}")

        threading.Thread(target=refresh, daemon=True).start()

    def apply_online_dashboard_background(self, image_url, image_path):
        if self.dashboard_background_url != image_url:
            return
        try:
            self.set_dashboard_background(image_path)
            self.dashboard_background = image_path
            self.save_school_config({"dashboard_background": image_path})
        except Exception as error:
            print(f"Could not apply online dashboard picture: {error}")

    def set_bing_wallpaper_enabled(self, enabled):
        self.bing_wallpaper_enabled = bool(enabled)
        self.dashboard_background_url = "" if enabled else self.dashboard_background_url
        self.save_school_config(
            {
                "bing_wallpaper_enabled": self.bing_wallpaper_enabled,
                "dashboard_background_url": self.dashboard_background_url,
            }
        )
        if enabled:
            self.refresh_bing_wallpaper_if_due(force=True)
        elif self.bing_refresh_after_id:
            self.after_cancel(self.bing_refresh_after_id)
            self.bing_refresh_after_id = None

    def set_bing_wallpaper_interval(self, selected_interval):
        try:
            interval_hours = int(selected_interval.split()[0])
        except (AttributeError, ValueError):
            return
        if interval_hours not in (1, 3, 6, 12, 24, 48, 72):
            return
        self.bing_wallpaper_interval_hours = interval_hours
        self.save_school_config({"bing_wallpaper_interval_hours": interval_hours})
        if self.bing_wallpaper_enabled:
            self.schedule_bing_wallpaper_check()

    def refresh_bing_wallpaper_if_due(self, force=False):
        if not self.bing_wallpaper_enabled:
            return

        now = datetime.now()
        refresh_time = now.isoformat(timespec="seconds")
        if not force and self.bing_wallpaper_last_refresh:
            try:
                last_refresh = datetime.fromisoformat(
                    self.bing_wallpaper_last_refresh
                )
            except ValueError:
                last_refresh = datetime.min
            if now - last_refresh < timedelta(
                hours=self.bing_wallpaper_interval_hours
            ):
                self.schedule_bing_wallpaper_check()
                return

        import threading
        from urllib.request import Request, urlopen

        def refresh():
            try:
                request = Request(
                    "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US",
                    headers={"User-Agent": "FreemanSchoolPortal"},
                )
                with urlopen(request, timeout=15) as response:
                    archive = json.loads(response.read(1024 * 1024).decode("utf-8"))
                image_info = archive["images"][0]
                image_url = image_info.get("url") or image_info.get("urlbase")
                if not image_url:
                    raise ValueError("Bing did not return a wallpaper URL.")
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                elif image_url.startswith("/"):
                    image_url = "https://www.bing.com" + image_url
                destination = self.fetch_dashboard_background(
                    image_url, filename_prefix="bing_wallpaper"
                )
                credit = image_info.get("copyright", "Bing daily image")
                self.after(
                    0,
                    lambda: self.apply_bing_wallpaper(
                        refresh_time, destination, credit
                    ),
                )
            except Exception as error:
                print(f"Bing wallpaper refresh failed: {error}")
                self.after(0, lambda: self.schedule_bing_wallpaper_retry())

        threading.Thread(target=refresh, daemon=True).start()

    def apply_bing_wallpaper(self, refresh_date, image_path, credit):
        if not self.bing_wallpaper_enabled:
            return
        try:
            self.set_dashboard_background(image_path)
            self.dashboard_background = image_path
            self.bing_wallpaper_last_refresh = refresh_date
            self.bing_wallpaper_credit = credit
            self.save_school_config(
                {
                    "dashboard_background": image_path,
                    "dashboard_background_url": "",
                    "bing_wallpaper_enabled": True,
                    "bing_wallpaper_last_refresh": refresh_date,
                    "bing_wallpaper_credit": credit,
                }
            )
            self.schedule_bing_wallpaper_check()
        except Exception as error:
            print(f"Could not apply Bing wallpaper: {error}")
            self.schedule_bing_wallpaper_retry()

    def schedule_bing_wallpaper_check(self):
        if not self.bing_wallpaper_enabled:
            return
        if self.bing_refresh_after_id:
            self.after_cancel(self.bing_refresh_after_id)
        try:
            last_refresh = datetime.fromisoformat(self.bing_wallpaper_last_refresh)
            seconds_until_refresh = (
                last_refresh
                + timedelta(hours=self.bing_wallpaper_interval_hours)
                - datetime.now()
            ).total_seconds()
        except (TypeError, ValueError):
            seconds_until_refresh = 60
        delay_seconds = max(
            60,
            min(seconds_until_refresh, self.bing_wallpaper_interval_hours * 3600),
        )
        self.bing_refresh_after_id = self.after(
            int(delay_seconds * 1000), self.refresh_bing_wallpaper_if_due
        )

    def schedule_bing_wallpaper_retry(self):
        if self.bing_wallpaper_enabled:
            if self.bing_refresh_after_id:
                self.after_cancel(self.bing_refresh_after_id)
            self.bing_refresh_after_id = self.after(
                30 * 60 * 1000, self.refresh_bing_wallpaper_if_due
            )

    def restore_default_dashboard_background(self):
        default_path = os.path.join(self.BASE_DIR, "assets", "dashboard_bg.jpg")
        try:
            self.set_dashboard_background(default_path)
            self.dashboard_background = ""
            self.dashboard_background_url = ""
            self.bing_wallpaper_enabled = False
            self.bing_wallpaper_last_refresh = ""
            self.bing_wallpaper_credit = ""
            if hasattr(self, "bing_wallpaper_var"):
                self.bing_wallpaper_var.set(False)
            self.save_school_config(
                {
                    "dashboard_background": "",
                    "dashboard_background_url": "",
                    "bing_wallpaper_enabled": False,
                    "bing_wallpaper_last_refresh": "",
                    "bing_wallpaper_credit": "",
                }
            )
        except Exception as error:
            messagebox.showerror(
                "Picture Error", f"Could not restore the default picture: {error}"
            )

    def choose_dashboard_accent(self):
        from tkinter import colorchooser

        selected_color = colorchooser.askcolor(
            color=self.dashboard_accent, parent=self
        )[1]
        if selected_color:
            self.set_dashboard_accent(selected_color)

    def set_dashboard_accent(self, color):
        self.dashboard_accent = color
        self.save_school_config({"dashboard_accent": color})
        self.apply_dashboard_theme()

    @staticmethod
    def get_hover_color(color):
        red = max(0, int(color[1:3], 16) - 24)
        green = max(0, int(color[3:5], 16) - 24)
        blue = max(0, int(color[5:7], 16) - 24)
        return f"#{red:02x}{green:02x}{blue:02x}"

    def apply_dashboard_theme(self):
        hover_color = self.get_hover_color(self.dashboard_accent)
        if hasattr(self, "menu_panel"):
            self.menu_panel.configure(border_color=self.dashboard_accent)
        if hasattr(self, "brand_label"):
            self.brand_label.configure(text_color=self.dashboard_accent)
        if hasattr(self, "theme_toggle") and self.theme_toggle.winfo_exists():
            self.theme_toggle.configure(
                selected_color=self.dashboard_accent,
                selected_hover_color=hover_color,
            )
        active_button = getattr(self, "active_sidebar_button", None)
        if active_button is not None and active_button.winfo_exists():
            active_button.configure(
                fg_color=self.dashboard_accent,
                border_color=hover_color,
            )
        for button in getattr(self, "class_selection_buttons", []):
            if button.winfo_exists():
                button.configure(
                    fg_color=self.dashboard_accent,
                    hover_color=hover_color,
                )

    def verify_admin_password(self):
        """Prompt for admin password and verify against school_config.json"""
        try:
            config = self.load_school_config()
            admin_password = config.get("system_password", "1234")
        except:
            admin_password = "1234"

        # Create password prompt dialog
        password_dialog = ctk.CTkToplevel(self)
        password_dialog.title("Admin Authentication Required")
        password_dialog.geometry("400x200")
        password_dialog.attributes("-topmost", True)
        password_dialog.grab_set()

        ctk.CTkLabel(
            password_dialog,
            text="Enter Administrator Password:",
            font=("Arial", 14, "bold"),
        ).pack(pady=20)

        password_entry = ctk.CTkEntry(password_dialog, show="*", width=250)
        password_entry.pack(pady=10)
        password_entry.focus()

        result = {"verified": False}

        def verify():
            if password_entry.get() == admin_password:
                result["verified"] = True
                password_dialog.destroy()
            else:
                messagebox.showerror("Authentication Failed", "Incorrect password!")
                password_entry.delete(0, "end")

        ctk.CTkButton(password_dialog, text="Verify", command=verify, width=100).pack(
            pady=20
        )

        password_dialog.wait_window()
        return result["verified"]

    def require_auth(self, action):
        """Require admin password before executing action"""
        if self.verify_admin_password():
            action()

    def verify_developer_password(self):
        """Prompt for developer password and verify against hardcoded credentials"""
        developer_password = "16592@FREE man"

        # Create password prompt dialog
        password_dialog = ctk.CTkToplevel(self)
        password_dialog.title("Developer Authentication Required")
        password_dialog.geometry("400x200")
        password_dialog.attributes("-topmost", True)
        password_dialog.grab_set()

        ctk.CTkLabel(
            password_dialog,
            text="Enter Developer Password:",
            font=("Arial", 14, "bold"),
        ).pack(pady=20)

        password_entry = ctk.CTkEntry(password_dialog, show="*", width=250)
        password_entry.pack(pady=10)
        password_entry.focus()

        result = {"verified": False}

        def verify():
            if password_entry.get() == developer_password:
                result["verified"] = True
                password_dialog.destroy()
            else:
                messagebox.showerror(
                    "Authentication Failed", "Incorrect developer password!"
                )
                password_entry.delete(0, "end")

        ctk.CTkButton(password_dialog, text="Verify", command=verify, width=100).pack(
            pady=20
        )

        password_dialog.wait_window()
        return result["verified"]

    def require_developer_auth(self, action):
        """Require developer password before executing action"""
        if self.verify_developer_password():
            action()

    def execute_student_promotion(self):
        """Move every learner to the next class; called when a new year starts."""
        try:
            print("[PROMOTION] Starting student promotion")

            # Define promotion mapping
            promotion_map = {
                "Playgroup": "PP1",
                "PP1": "PP2",
                "PP2": "Grade 1",
                "Grade 1": "Grade 2",
                "Grade 2": "Grade 3",
                "Grade 3": "Grade 4",
                "Grade 4": "Grade 5",
                "Grade 5": "Grade 6",
                "Grade 6": "Grade 7",
                "Grade 7": "Grade 8",
                "Grade 8": "Grade 9",
                "Grade 9": "Grade 10",
                "Grade 10": "Grade 11",
                "Grade 11": "Grade 12",
            }

            print(f"[PROMOTION] Promotion map: {promotion_map}")

            # Get all students
            print("[PROMOTION] Fetching all students from database...")
            self.db.cursor().execute(
                "SELECT adm_no, name, grade, gender, phone, photo, stream FROM students"
            )
            students = self.db.cursor().fetchall()
            print(f"[PROMOTION] Found {len(students)} students")

            promoted_count = 0

            for student in students:
                adm_no, name, current_grade, gender, phone, photo, stream = student
                print(
                    f"[PROMOTION] Processing student: {name} (ADM: {adm_no}, Grade: {current_grade})"
                )

                # Handle case-insensitive grade matching
                current_grade_normalized = (
                    current_grade.strip().title() if current_grade else ""
                )
                if current_grade_normalized == "Playgroup":
                    current_grade_normalized = "Playgroup"
                elif current_grade_normalized.lower() == "pp1":
                    current_grade_normalized = "PP1"
                elif current_grade_normalized.lower() == "pp2":
                    current_grade_normalized = "PP2"

                if current_grade_normalized in promotion_map:
                    new_grade = promotion_map[current_grade_normalized]
                    print(
                        f"[PROMOTION] Student {name} will move from {current_grade} ({current_grade_normalized}) to {new_grade}"
                    )

                    print(f"[PROMOTION] Promoting student {name} to {new_grade}")
                    self.db.cursor().execute(
                        "UPDATE students SET grade = ? WHERE adm_no = ?",
                        (new_grade, adm_no),
                    )
                    promoted_count += 1
                else:
                    print(
                        f"[PROMOTION] WARNING: Student {name} has unrecognized grade: {current_grade} (normalized: {current_grade_normalized})"
                    )

            print(f"[PROMOTION] Committing database changes...")
            self.db.conn.commit()
            print(f"[PROMOTION] Database commit successful")

            messagebox.showinfo(
                "Promotion Complete",
                f"Student promotion completed successfully!\n\n"
                f"Promoted: {promoted_count} students\n"
                f"Grade 12 learners were retained in the system.",
            )

            # Sync students to cloud after promotion
            print("[PROMOTION] Starting cloud sync after promotion...")
            config = self.load_school_config()
            cloud_url = config.get("cloud_portal_url", "").strip()
            cloud_school_code = config.get("cloud_school_code", "").strip()
            cloud_teacher_username = config.get("cloud_teacher_username", "").strip()
            cloud_teacher_password = config.get("cloud_teacher_password", "").strip()

            if not cloud_url or not cloud_school_code or not cloud_teacher_username:
                print("[PROMOTION] Cloud portal not configured, skipping sync")
            else:
                if cloud_teacher_password:
                    credentials = {
                        "school_code": cloud_school_code,
                        "username": cloud_teacher_username,
                        "password": cloud_teacher_password,
                    }
                    try:
                        self.sync_students_to_cloud(credentials)
                        print("[PROMOTION] Cloud sync completed successfully")
                    except Exception as sync_error:
                        print(f"[PROMOTION] Cloud sync error: {sync_error}")
                        messagebox.showwarning(
                            "Cloud Sync",
                            f"Promotion completed but cloud sync failed: {sync_error}",
                        )

        except Exception as e:
            print(f"[PROMOTION ERROR] An error occurred during promotion: {e}")
            import traceback

            traceback.print_exc()
            messagebox.showerror(
                "Promotion Failed", f"An error occurred during promotion: {e}"
            )

    def open_system_settings(self):
        """Open the system settings dialog"""
        self.reset_sidebar_highlights()

        # Clear content panel
        for widget in self.content_panel.winfo_children():
            widget.destroy()

        # Create header
        header_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 20))

        ctk.CTkLabel(
            header_frame, text=self.dynamic_school_name, font=("Arial Bold", 26)
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            header_frame,
            text="/ SYSTEM SETTINGS",
            font=("Arial Italic", 14),
            text_color="gray",
        ).pack(side="left", anchor="sw")

        # Create settings frame
        settings_frame = ctk.CTkFrame(self.content_panel)
        settings_frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(
            settings_frame, text="System Settings", font=("Arial Bold", 24)
        ).pack(pady=20)

        # Setup School Branding option
        setup_branding_btn = ctk.CTkButton(
            settings_frame,
            text="⚙️ Setup School Branding",
            width=300,
            height=50,
            font=("Arial Bold", 14),
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=lambda: self.require_developer_auth(self.open_wizard),
        )
        setup_branding_btn.pack(pady=10)

        # Change Password/Username option
        change_creds_btn = ctk.CTkButton(
            settings_frame,
            text="🔐 Change Password/Username",
            width=300,
            height=50,
            font=("Arial Bold", 14),
            fg_color="#3498db",
            hover_color="#2980b9",
            command=self.open_change_credentials,
        )
        change_creds_btn.pack(pady=10)

        # Back button
        back_btn = ctk.CTkButton(
            settings_frame,
            text="Back to Dashboard",
            width=300,
            height=40,
            command=self.restore_dashboard,
        )
        back_btn.pack(pady=20)

    def open_change_credentials(self):
        """Open the change password/username dialog"""
        # Clear content panel
        for widget in self.content_panel.winfo_children():
            widget.destroy()

        # Create header
        header_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 20))

        ctk.CTkLabel(
            header_frame, text=self.dynamic_school_name, font=("Arial Bold", 26)
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            header_frame,
            text="/ SYSTEM SETTINGS / CHANGE CREDENTIALS",
            font=("Arial Italic", 14),
            text_color="gray",
        ).pack(side="left", anchor="sw")

        # Create credentials frame
        creds_frame = ctk.CTkFrame(self.content_panel)
        creds_frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(
            creds_frame, text="Change Password/Username", font=("Arial Bold", 24)
        ).pack(pady=20)

        # Load current credentials
        config = self.load_school_config()
        current_username = config.get("system_username", "admin")

        # Old password field
        ctk.CTkLabel(creds_frame, text="Old Password:", font=("Arial", 14)).pack(
            pady=(10, 5)
        )
        old_password_entry = ctk.CTkEntry(creds_frame, width=300, show="*")
        old_password_entry.pack(pady=5)

        # New username field
        ctk.CTkLabel(
            creds_frame,
            text="New Username (leave blank to keep current):",
            font=("Arial", 14),
        ).pack(pady=(10, 5))
        new_username_entry = ctk.CTkEntry(creds_frame, width=300)
        new_username_entry.pack(pady=5)
        new_username_entry.insert(0, current_username)

        # New password field
        ctk.CTkLabel(creds_frame, text="New Password:", font=("Arial", 14)).pack(
            pady=(10, 5)
        )
        new_password_entry = ctk.CTkEntry(creds_frame, width=300, show="*")
        new_password_entry.pack(pady=5)

        # Confirm new password field
        ctk.CTkLabel(
            creds_frame, text="Confirm New Password:", font=("Arial", 14)
        ).pack(pady=(10, 5))
        confirm_password_entry = ctk.CTkEntry(creds_frame, width=300, show="*")
        confirm_password_entry.pack(pady=5)

        # Save button
        save_btn = ctk.CTkButton(
            creds_frame,
            text="Save Changes",
            width=300,
            height=50,
            font=("Arial Bold", 14),
            fg_color="#27ae60",
            hover_color="#229954",
            command=lambda: self.save_credentials(
                old_password_entry.get(),
                new_username_entry.get(),
                new_password_entry.get(),
                confirm_password_entry.get(),
            ),
        )
        save_btn.pack(pady=20)

        # Back button
        back_btn = ctk.CTkButton(
            creds_frame,
            text="Back to System Settings",
            width=300,
            height=40,
            command=self.open_system_settings,
        )
        back_btn.pack(pady=10)

    def save_credentials(
        self, old_password, new_username, new_password, confirm_password
    ):
        """Save the new credentials to school_config.json"""
        import os
        import json

        # Load current config
        config = self.load_school_config()
        current_password = config.get("system_password", "1234")
        current_username = config.get("system_username", "admin")

        # Validate old password
        if old_password != current_password:
            messagebox.showerror("Error", "Old password is incorrect.")
            return

        # Validate new password match
        if new_password != confirm_password:
            messagebox.showerror("Error", "New passwords do not match.")
            return

        # If username is blank, keep current
        if not new_username.strip():
            new_username = current_username

        # If password is blank, keep current
        if not new_password.strip():
            new_password = current_password

        # Update config
        config["system_username"] = new_username
        config["system_password"] = new_password

        # Save to school_config.json
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            with open(json_path, "w") as f:
                json.dump(config, f, indent=4)

            messagebox.showinfo("Success", "Credentials updated successfully!")
            self.open_system_settings()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {e}")

    def restore_dashboard(self):
        """Restore the dashboard view"""
        self.return_to_home()

    def open_report_forms(self):
        # Use the existing class selection method
        self.show_class_selection("Report Forms", self.btn_report_forms)

    def open_newsletter(self):
        from newsletter import NewsletterCreator

        NewsletterCreator(self, self.db)

    def load_school_name(self):
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config = json.load(f)
                    name = config.get("school_name", "")
                    return (
                        name.strip()
                        if isinstance(name, str) and name.strip()
                        else "Freeman"
                    )
        except Exception:
            pass
        return "Freeman"

    def load_school_config(self):
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    return json.load(f)
            else:
                # If config doesn't exist in USER_DATA_DIR, copy from bundled location
                bundled_config = os.path.join(self.BASE_DIR, "school_config.json")
                if os.path.exists(bundled_config):
                    import shutil

                    shutil.copy2(bundled_config, json_path)
                    with open(json_path, "r") as f:
                        return json.load(f)
        except Exception:
            pass
        return {}

    def load_portal_state(self):
        """Load portal state from config file"""
        try:
            config = self.load_school_config()
            return config.get("portal_open", False)
        except Exception:
            return False

    def save_portal_state(self, state):
        """Save portal state to config file"""
        try:
            self.save_school_config({"portal_open": state})
        except Exception as e:
            print(f"Unable to save portal state: {e}")

    def save_school_config(self, updates):
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            config = self.load_school_config()
            config.update(updates)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Unable to save school config: {e}")

    def get_local_student_list(self):
        try:
            self.db.cursor().execute(
                "SELECT adm_no, name, grade, gender, phone, photo, stream, assessment_number FROM students ORDER BY grade, adm_no"
            )
            rows = self.db.cursor().fetchall()
            return [
                {
                    "adm_no": row[0] or "",
                    "name": row[1] or "",
                    "grade": row[2] or "",
                    "gender": row[3] or "",
                    "phone": row[4] or "",
                    "photo": row[5] if len(row) > 5 else None,
                    "stream": row[6] if len(row) > 6 else "None",
                    "assessment_number": row[7] if len(row) > 7 else "",
                }
                for row in rows
                if row[0] and row[1]
            ]
        except Exception as e:
            print(f"Error reading local students: {e}")
            return []

    def get_local_teacher_list(self):
        try:
            teachers = self.db.get_all_teachers()
            return [
                {
                    "class_name": row[0] or "",
                    "subject": row[1] or "",
                    "teacher_name": row[2] or "",
                    "teacher_code": row[3] or "",
                }
                for row in teachers
                if row[0] and row[1] and row[2] and row[3]
            ]
        except Exception as e:
            print(f"Error reading local teachers: {e}")
            return []

    def sync_students_to_cloud(self, credentials):
        students = self.get_local_student_list()
        if not students:
            messagebox.showinfo("Cloud Sync", "No local students found to sync.")
            return False

        # Load school details from config
        school_details = {}
        try:
            config_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    logo_path = config.get("logo", "")
                    # Convert logo to base64 if it's a local file
                    school_logo = self.image_to_base64(logo_path) if logo_path else ""
                    school_details = {
                        "school_name": config.get("school_name", ""),
                        "school_address": config.get("address", ""),
                        "school_telephone": config.get("contacts", ""),
                        "school_logo": school_logo,
                        "subjects": {
                            **config.get("subjects", {}),
                            "_names": config.get("subject_names", {}),
                            "_custom": {
                                key: [i["name"] for i in items if i.get("custom") and i.get("selected")]
                                for key, items in (config.get("subject_catalog") or {}).items()
                            },
                        },
                    }
        except Exception as e:
            print(f"Error loading school config: {e}")

        # Convert student photos to base64 if they are local files
        for student in students:
            if student.get("photo"):
                student["photo"] = self.image_to_base64(student["photo"])

        service = CloudService()
        result = service.sync_students(students, credentials, school_details)
        if not result.get("success"):
            messagebox.showerror(
                "Cloud Sync Failed",
                result.get("message", "Could not sync students to cloud."),
            )
            return False

        messagebox.showinfo(
            "Cloud Sync", f"Uploaded {len(students)} local students to cloud portal."
        )
        return True

    def image_to_base64(self, image_path):
        """Convert an image file to base64 string with data URI prefix"""
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            with open(image_path, "rb") as image_file:
                import base64

                # Get file extension to determine MIME type
                ext = os.path.splitext(image_path)[1].lower()
                mime_type = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                }.get(ext, "image/png")

                base64_data = base64.b64encode(image_file.read()).decode("utf-8")
                return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None

    def sync_teachers_to_cloud(self, credentials):
        teachers = self.get_local_teacher_list()
        if not teachers:
            messagebox.showinfo("Cloud Sync", "No local teachers found to sync.")
            return False

        service = CloudService()
        result = service.sync_teachers(teachers, credentials)
        if not result.get("success"):
            messagebox.showerror(
                "Cloud Sync Failed",
                result.get("message", "Could not sync teachers to cloud."),
            )
            return False

        messagebox.showinfo(
            "Cloud Sync", f"Uploaded {len(teachers)} local teachers to cloud portal."
        )
        return True

    def handle_portal_button(self):
        cloud_config = self.load_school_config()
        cloud_url = cloud_config.get("cloud_portal_url", "").strip()
        cloud_school_code = cloud_config.get("cloud_school_code", "").strip()
        cloud_teacher_username = cloud_config.get("cloud_teacher_username", "").strip()

        # Toggle portal state
        if not self.portal_open:
            # Launch portal
            school = self.load_school_name()
            success, message = network_manager.launch_sync_portal(school)

            if success:
                portal_text = []
                if message.startswith("HOTSPOT|"):
                    _, ssid, password, server_url = message.split("|", 3)
                    portal_text.append(f"WiFi Name: {ssid}")
                    portal_text.append(f"Password: {password}")
                    portal_text.append(f"Offline Portal: {server_url}")
                elif message.startswith("SERVER_ONLY|"):
                    _, server_url, error_message = message.split("|", 2)
                    portal_text.append(f"Offline Portal: {server_url}")
                    portal_text.append(f"Hotspot error: {error_message}")
                    portal_text.append(
                        "Enable Windows Mobile Hotspot manually if you want a local Wi-Fi network."
                    )
                else:
                    portal_text.append(f"Offline Portal: {message}")

                if cloud_url:
                    portal_text.append(f"Cloud Portal: {cloud_url}")

                messagebox.showinfo("Portal Active", "\n".join(portal_text))

                # Toggle cloud portal if configured
                if cloud_school_code and cloud_teacher_username and cloud_url:
                    cloud_teacher_password = cloud_config.get(
                        "cloud_teacher_password", ""
                    ).strip()
                    if cloud_teacher_password:
                        credentials = {
                            "school_code": cloud_school_code,
                            "username": cloud_teacher_username,
                            "password": cloud_teacher_password,
                        }
                    else:
                        credentials = ask_cloud_credentials(self)
                        if not credentials:
                            # Still update local state even if cloud auth fails
                            self.portal_open = True
                            self.update_portal_button()
                            return

                    # Toggle cloud portal to open
                    service = CloudService()
                    result = service.toggle_portal(credentials)
                    if result.get("success"):
                        print(f"Cloud portal opened: {result.get('message')}")
                    else:
                        print(f"Failed to open cloud portal: {result.get('message')}")

                    self.sync_students_to_cloud(credentials)
                    self.sync_teachers_to_cloud(credentials)
                    # Commented out to prevent Chrome redirection
                    # try:
                    #     webbrowser.open(cloud_url)
                    # except Exception:
                    #     pass
                elif cloud_url and not cloud_school_code:
                    if messagebox.askyesno(
                        "Cloud Portal", "Open the cloud portal in the browser?"
                    ):
                        # Commented out to prevent Chrome redirection
                        # try:
                        #     webbrowser.open(cloud_url)
                        # except Exception:
                        #     pass
                        pass

                # Update state and button
                self.portal_open = True
                self.save_portal_state(True)
                self.update_portal_button()
            else:
                messagebox.showerror("Portal Error", f"Failed to start: {message}")
        else:
            # Close portal
            cloud_close_success = True
            if cloud_school_code and cloud_teacher_username and cloud_url:
                cloud_teacher_password = cloud_config.get(
                    "cloud_teacher_password", ""
                ).strip()
                if cloud_teacher_password:
                    credentials = {
                        "school_code": cloud_school_code,
                        "username": cloud_teacher_username,
                        "password": cloud_teacher_password,
                    }
                else:
                    credentials = ask_cloud_credentials(self)
                    if not credentials:
                        # Still close locally even if user cancels cloud auth
                        cloud_close_success = False

                # Toggle cloud portal to close
                if credentials:
                    service = CloudService()
                    result = service.toggle_portal(credentials)
                    if result.get("success"):
                        messagebox.showinfo(
                            "Portal Closed",
                            "Teachers portal has been closed. Teachers can no longer enter marks.",
                        )
                    else:
                        messagebox.showerror(
                            "Portal Error",
                            f"Failed to close cloud portal: {result.get('message')}",
                        )
                        cloud_close_success = False
            else:
                messagebox.showinfo(
                    "Portal Closed",
                    "Teachers portal has been closed. Teachers can no longer enter marks.",
                )

            # Only update local state and button if close operation succeeded
            if cloud_close_success:
                self.portal_open = False
                self.save_portal_state(False)
                self.update_portal_button()

    def update_portal_button(self):
        """Update portal button text and color based on state"""
        if self.portal_open:
            self.btn_portal.configure(
                text="🔒 Close Teacher Portal", fg_color="#e74c3c"
            )
        else:
            self.btn_portal.configure(text="📡 Launch Teacher Portal", fg_color="green")

    def handle_cloud_sync_button(self):
        config = self.load_school_config()
        cloud_url = config.get("cloud_portal_url", "").strip()
        cloud_school_code = config.get("cloud_school_code", "").strip()
        cloud_teacher_username = config.get("cloud_teacher_username", "").strip()
        cloud_teacher_password = config.get("cloud_teacher_password", "").strip()

        if not cloud_url or not cloud_school_code or not cloud_teacher_username:
            messagebox.showwarning(
                "Cloud Sync",
                "Cloud portal is not fully configured. Please register the school or add cloud portal settings in school_config.json.",
            )
            return

        if cloud_teacher_password:
            credentials = {
                "school_code": cloud_school_code,
                "username": cloud_teacher_username,
                "password": cloud_teacher_password,
            }
        else:
            credentials = ask_cloud_credentials(self)
            if not credentials:
                return

        success = self.sync_students_to_cloud(credentials)
        if success:
            self.sync_teachers_to_cloud(credentials)
            if messagebox.askyesno(
                "Cloud Portal",
                "Students and teachers synced successfully. Open the cloud portal now?",
            ):
                # Commented out to prevent Chrome redirection
                # try:
                #     webbrowser.open(cloud_url)
                # except Exception:
                #     pass
                pass

    def add_empty_row(self):
        # 1. Create the Row Frame with a slightly lighter dark color
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#2b2b2b", height=40)
        row_frame.pack(fill="x", pady=2, padx=5)

        self.all_student_rows.append(row_frame)

        # Configure columns for student details, photo, and actions
        for i in range(8):
            row_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        row_frame.grid_columnconfigure(8, weight=0, minsize=150)

        # 3. Entry Boxes (White Background & Black Text for Clarity)
        entry_style = {"fg_color": "white", "text_color": "black", "height": 30}

        adm = ctk.CTkEntry(row_frame, placeholder_text="ADM", **entry_style)
        adm.grid(row=0, column=0, padx=2, pady=5, sticky="ew")

        assessment_number = ctk.CTkEntry(
            row_frame, placeholder_text="Assessment No.", **entry_style
        )
        assessment_number.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        name = ctk.CTkEntry(row_frame, placeholder_text="Full Name", **entry_style)
        name.grid(row=0, column=2, padx=2, pady=5, sticky="ew")

        grade = ctk.CTkEntry(row_frame, placeholder_text="Grade", **entry_style)
        grade.grid(row=0, column=3, padx=2, pady=5, sticky="ew")

        gender = ctk.CTkEntry(row_frame, placeholder_text="Gender", **entry_style)
        gender.grid(row=0, column=4, padx=2, pady=5, sticky="ew")

        phone = ctk.CTkEntry(row_frame, placeholder_text="Phone", **entry_style)
        phone.grid(row=0, column=5, padx=2, pady=5, sticky="ew")

        # Stream field
        stream = ctk.CTkEntry(row_frame, placeholder_text="Stream", **entry_style)
        if getattr(self, "registry_streams", []) and self.registry_stream != "None":
            stream.insert(0, self.registry_stream)
        stream.grid(row=0, column=6, padx=2, pady=5, sticky="ew")

        # Photo upload button
        photo_path = ctk.StringVar()
        photo_btn = ctk.CTkButton(
            row_frame,
            text="📷 Photo",
            width=80,
            height=30,
            command=lambda: self.upload_student_photo(photo_path, photo_btn),
        )
        photo_btn.grid(row=0, column=7, padx=2, pady=5, sticky="ew")

        # 4. The Button Actions Frame (This holds Save, Edit, Delete together)
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=8, padx=5)

        # SAVE (Green)
        save_btn = ctk.CTkButton(
            actions_frame,
            text="✓",
            width=30,
            fg_color="green",
            command=lambda: self.save_to_db(
                adm, name, grade, gender, phone, stream, photo_path, save_btn,
                assessment_number,
            ),
        )
        save_btn.pack(side="left", padx=2)

        # EDIT (Blue)
        # We pass ALL entries and the save button to a new helper function
        edit_btn = ctk.CTkButton(
            actions_frame,
            text="✎",
            width=30,
            fg_color="#1f538d",
            command=lambda e=[
                adm,
                assessment_number,
                name,
                grade,
                gender,
                phone,
                stream,
                photo_path,
            ], b=save_btn, pb=photo_btn: self.unlock_row_for_edit(e, b, pb),
        )
        edit_btn.pack(side="left", padx=2)

        # DELETE (Red)
        # Use 'adm' (the variable name for your first Entry box)
        del_btn = ctk.CTkButton(
            actions_frame,
            text="🗑",
            width=30,
            fg_color="#942727",
            command=lambda f=row_frame, a=adm: self.confirm_delete(f, a),
        )
        del_btn.pack(side="left", padx=2)

    def upload_student_photo(self, photo_path_var, photo_btn):
        """Open file dialog to select student photo"""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Student Photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")],
        )
        if file_path:
            photo_path_var.set(file_path)
            photo_btn.configure(text="✓ Photo")

    def unlock_row_for_edit(self, entries, save_button, photo_btn=None):
        """Unlocks a row and RE-LINKS the save button to the database function"""
        # Unlock all entry fields; the final item is the photo-path variable.
        for i, entry in enumerate(entries):
            if i < 7 and isinstance(entry, ctk.CTkEntry):
                entry.configure(state="normal", fg_color="white", text_color="black")

        # Enable photo button if it exists
        if photo_btn:
            photo_btn.configure(
                state="normal",
                fg_color="#1f538d",
                command=lambda: self.upload_student_photo(entries[7], photo_btn),
            )

        # We must re-configure the command so it knows to save again when clicked
        save_button.configure(
            state="normal",
            text="✓",
            fg_color="green",
            command=lambda: self.save_to_db(
                entries[0],
                entries[2],
                entries[3],
                entries[4],
                entries[5],
                entries[6],
                entries[7],
                save_button,
                entries[1],
            ),
        )

    def save_to_db(
        self,
        adm_entry,
        name_entry,
        grade_entry,
        gender_entry,
        phone_entry,
        stream_entry,
        photo_path_var,
        btn,
        assessment_entry=None,
    ):
        adm = adm_entry.get()
        name = name_entry.get()
        assessment_number = assessment_entry.get() if assessment_entry else ""
        gender = gender_entry.get()
        phone = phone_entry.get()
        stream = stream_entry.get().strip() if stream_entry else "None"
        if getattr(self, "registry_streams", []):
            configured = {
                configured_stream.casefold(): configured_stream
                for configured_stream in self.registry_streams
            }
            if stream.casefold() not in configured:
                messagebox.showwarning(
                    "Invalid Stream",
                    "Choose one of this class's configured streams before saving.",
                )
                return
            stream = configured[stream.casefold()]
        photo = photo_path_var.get() if photo_path_var else None

        # --- THE CRITICAL FIX ---
        # This pulls the actual text from your title label
        # so it matches the database perfectly.
        raw_title = self.registry_title.cget(
            "text"
        )  # Result: "Student Registry: playgroup"
        current_class = self.registry_class

        # Normalize grade names to match database format
        grade_mapping = {
            "Play group": "playgroup",
            "Pre-Primary 1": "pp1",
            "Pre-Primary 2": "pp2",
        }
        grade = grade_mapping.get(current_class, current_class)

        if not adm:
            adm = self.next_registry_admission_number()
            adm_entry.delete(0, "end")
            adm_entry.insert(0, adm)

        if not name:
            messagebox.showwarning("Input Error", "Student name is required!")
            return

        try:
            # 1. Save to Database
            saved = self.db.add_student(
                adm,
                name,
                grade,
                gender,
                phone,
                photo,
                stream,
                check_footprint=True,
                assessment_number=assessment_number,
            )
            if not saved:
                messagebox.showerror("Database Error", "The student could not be saved.")
                return

            # 2. Lock the Row visually
            for entry in [
                adm_entry,
                name_entry,
                grade_entry,
                gender_entry,
                phone_entry,
                stream_entry,
                assessment_entry,
            ]:
                if entry:
                    entry.configure(
                        state="disabled", fg_color="gray30", text_color="white"
                    )

            # 3. Update Button
            btn.configure(text="Saved", state="disabled", fg_color="gray")

            # 4. Success Message in Terminal
            print(f"Verified Save: {name} added to {grade}")

        except Exception as e:
            messagebox.showerror("Database Error", f"Could not save: {e}")

    def mass_edit_all(self):
        """Unlocks every row currently visible in the table"""
        if not self.all_student_rows:
            print("No rows to edit!")
            return

        for row in self.all_student_rows:
            # 1. Find all Entry boxes in this row and unlock them
            row_entries = []
            photo_btn = None
            save_btn = None

            # We look through all children of the row
            for widget in row.winfo_children():
                if isinstance(widget, ctk.CTkEntry):
                    widget.configure(
                        state="normal", fg_color="white", text_color="black"
                    )
                    row_entries.append(widget)

                # Find photo button
                if isinstance(widget, ctk.CTkButton) and "Photo" in widget.cget("text"):
                    photo_btn = widget

                # The Save button is hidden inside the actions frame
                if isinstance(widget, ctk.CTkFrame):
                    for sub_widget in widget.winfo_children():
                        if isinstance(sub_widget, ctk.CTkButton):
                            # Identify the Save/Saved button by its text
                            if sub_widget.cget("text") in ["Saved", "✓"]:
                                save_btn = sub_widget

            # 2. Re-link the Save button so it works after being unlocked
            if save_btn and len(row_entries) >= 7:
                # Create a StringVar for photo path if not exists
                photo_path = ctk.StringVar()
                save_btn.configure(
                    state="normal",
                    text="✓",
                    fg_color="green",
                    command=lambda r=row_entries, p=photo_path, pb=photo_btn, b=save_btn: self.save_to_db(
                        r[0], r[2], r[3], r[4], r[5], r[6], p, b, r[1]
                    ),
                )
        print("All rows unlocked for editing.")

    def remove_specific_row(self, frame_to_remove):
        """Removes the row from the screen and the tracker"""
        frame_to_remove.destroy()
        if frame_to_remove in self.all_student_rows:
            self.all_student_rows.remove(frame_to_remove)

    def edit_row(self, entries, save_btn):
        """Unlocks the boxes so the teacher can fix a typo"""
        for entry in entries:
            entry.configure(state="normal", text_color="white", fg_color="gray25")

        # Change the button back to the Tick so they can save again
        save_btn.configure(text="✓", state="normal", fg_color="#2ecc71")

    def clear_all_students(self):
        """Permanently deletes all students currently visible on the screen from the DB"""
        if not self.all_student_rows:
            messagebox.showinfo("Info", "There are no rows to remove.")
            return

        # 1. Ask for confirmation (Crucial since this is permanent!)
        confirm = messagebox.askyesno(
            "Confirm Mass Delete",
            "WARNING: This will PERMANENTLY delete all students shown below from the database. \n\nContinue?",
        )

        if confirm:
            try:
                for row in self.all_student_rows:
                    # 2. Find the ADM NO entry box in this row
                    # We look for the first CTkEntry widget
                    adm_no = None
                    for widget in row.winfo_children():
                        if isinstance(widget, ctk.CTkEntry):
                            adm_no = widget.get()
                            break  # Found the first box (ADM NO), move on

                    # 3. If there is an ADM NO, delete it from the database
                    if adm_no:
                        self.db.delete_student(adm_no)

                    # 4. Remove the row from the UI
                    row.destroy()

                # 5. Reset the tracker list
                self.all_student_rows = []
                messagebox.showinfo(
                    "Success", "All records have been permanently deleted."
                )
                print("Mass deletion complete.")

            except Exception as e:
                messagebox.showerror(
                    "Error", f"An error occurred during mass deletion: {e}"
                )

    def lock_and_save(self, entries, button):
        """Disables typing and changes the button appearance"""

        # Check if Name is empty before locking
        if entries[1].get() == "":
            print("Error: Name is required!")
            return

        # Disable all entry boxes in this row
        for entry in entries:
            entry.configure(
                state="disabled", text_color="white", fg_color="gray10", border_width=0
            )

        # Change the Tick to a "Locked" icon or just hide it
        button.configure(text="Saved", state="disabled", fg_color="#34495e")

        print(f"Data for {entries[1].get()} has been locked in the registry.")

    def add_filled_row_from_db(self, data):
        """Creates a row that is already populated and locked"""
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#2b2b2b", height=40)
        row_frame.pack(fill="x", pady=2, padx=5)
        self.all_student_rows.append(row_frame)

        # Configure grid columns for 7 columns + actions
        for i in range(7):
            row_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        row_frame.grid_columnconfigure(7, weight=0, minsize=150)

        # Create entries and insert the data from 'student' tuple
        entries = []
        # Create 5 main entry fields (adm, name, grade, gender, phone)
        # Handle old records that might not have all columns
        for i in range(5):
            e = ctk.CTkEntry(
                row_frame, fg_color="gray30", text_color="white", state="normal"
            )
            value = str(data[i]) if i < len(data) and data[i] is not None else ""
            e.insert(0, value)  # Put the DB info (ADM, Name, etc) into the box
            e.configure(state="disabled")  # Lock it immediately
            e.grid(row=0, column=i, padx=2, pady=5, sticky="ew")
            entries.append(e)

        # Stream field (column 5)
        stream_value = str(data[6]) if len(data) > 6 and data[6] is not None else "None"
        stream = ctk.CTkEntry(
            row_frame, fg_color="gray30", text_color="white", state="normal"
        )
        stream.insert(0, stream_value)
        stream.configure(state="disabled")
        stream.grid(row=0, column=5, padx=2, pady=5, sticky="ew")
        entries.append(stream)

        # Photo field (column 6)
        photo_value = data[5] if len(data) > 5 else None
        photo_path = ctk.StringVar(value=photo_value or "")
        photo_btn = ctk.CTkButton(
            row_frame,
            text="✓ Photo" if photo_value else "📷 Photo",
            width=80,
            height=30,
            state="disabled",
            fg_color="gray",
        )
        photo_btn.grid(row=0, column=6, padx=2, pady=5, sticky="ew")
        entries.append(photo_path)  # Store the StringVar in entries list

        # Add the action buttons (Save, Edit, Delete)
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=7, padx=5)

        # The Save button starts as "Saved"
        save_btn = ctk.CTkButton(
            actions_frame,
            text="Saved",
            width=40,
            fg_color="gray",
            state="disabled",
            command=lambda: self.save_to_db(
                entries[0],
                entries[1],
                entries[2],
                entries[3],
                entries[4],
                entries[5],
                entries[6],
                save_btn,
            ),
        )
        save_btn.pack(side="left", padx=2)

        edit_btn = ctk.CTkButton(
            actions_frame,
            text="✎",
            width=30,
            fg_color="#1f538d",
            command=lambda e=entries, b=save_btn, pb=photo_btn: self.unlock_row_for_edit(
                e, b, pb
            ),
        )
        edit_btn.pack(side="left", padx=2)

        # DELETE (Red)
        # We use entries[0] because that's the ADM NO box we just created in the loop above
        del_btn = ctk.CTkButton(
            actions_frame,
            text="🗑",
            width=30,
            fg_color="#942727",
            command=lambda f=row_frame, a=entries[0]: self.confirm_delete(f, a),
        )
        del_btn.pack(side="left", padx=2)

    def create_table_headers(self):
        """Creates the header row inside the table_frame"""
        header_frame = ctk.CTkFrame(
            self.table_frame, fg_color="gray25", corner_radius=5
        )
        header_frame.pack(
            fill="x", pady=(0, 10)
        )  # pady adds space before the first student

        # Match the column logic of your rows (8 columns + actions)
        for i in range(8):
            header_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        header_frame.grid_columnconfigure(8, weight=0, minsize=150)

        cols = [
            "ADM NO",
            "ASSESSMENT NO",
            "STUDENT NAME",
            "GRADE",
            "GENDER",
            "PHONE",
            "STREAM",
            "PHOTO",
            "ACTIONS",
        ]
        for i, text in enumerate(cols):
            lbl = ctk.CTkLabel(
                header_frame, text=text, font=("Arial Bold", 12), text_color="white"
            )
            if i < 8:
                lbl.grid(row=0, column=i, padx=10, pady=5, sticky="w")
            else:
                lbl.grid(row=0, column=8, padx=10, pady=5)

    def show_student_registry(self, class_name, stream=None):
        # 1. Layout: Hide sidebar and expand content
        self.menu_panel.grid_forget()
        self.grid_columnconfigure(0, weight=0, minsize=0)
        self.grid_columnconfigure(1, weight=1)
        self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # 2. Clear previous widgets
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

            # --- MOVE THIS UP HERE ---
        # 2. Create the Title FIRST so save_to_db can always find it
        self.registry_title = ctk.CTkLabel(
            self.content_panel,
            text=f"Student Registry: {class_name}",
            font=("Arial Bold", 24),
        )
        self.registry_title.pack(pady=20)
        # -------------------------

        self.registry_class = class_name
        self.registry_streams = self.db.get_class_streams(class_name)
        self.registry_stream = stream or (
            self.registry_streams[0] if self.registry_streams else "None"
        )
        stream_bar = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        stream_bar.pack(fill="x", padx=24, pady=(0, 14))
        ctk.CTkButton(
            stream_bar,
            text="Configure Streams",
            width=150,
            command=lambda: self.configure_class_streams(class_name),
        ).pack(side="left")
        ctk.CTkLabel(stream_bar, text="Registry stream:").pack(side="left", padx=(20, 8))
        stream_values = self.registry_streams or ["None"]
        if self.registry_stream not in stream_values:
            self.registry_stream = stream_values[0]
        self.registry_stream_var = ctk.StringVar(value=self.registry_stream)
        ctk.CTkOptionMenu(
            stream_bar,
            values=stream_values,
            variable=self.registry_stream_var,
            command=lambda value: self.show_student_registry(class_name, value),
            width=180,
        ).pack(side="left")

        # 3. Create the Main Container and THE TABLE FRAME (Must happen FIRST)
        self.registry_container = ctk.CTkFrame(
            self.content_panel, fg_color="transparent"
        )
        self.registry_container.pack(fill="both", expand=True, padx=20)

        # --- 1. Create the Scrollable Frame FIRST ---
        self.table_frame = ctk.CTkScrollableFrame(
            self.registry_container, fg_color="gray15", corner_radius=10
        )
        self.table_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # --- 2. Call the Header Function ---
        # This puts the header INSIDE the scrollable frame at the very top
        self.create_table_headers()

        # 4. Now that table_frame exists, we can use these functions:
        self.all_student_rows = []
        self.load_students_from_db(class_name)

        # 5. Add blank rows
        for _ in range(3):
            self.add_empty_row()

        self.search_entry = ctk.CTkEntry(
            self.content_panel,
            placeholder_text="🔍 Search...",
            width=300,
            textvariable=self.search_var,
        )
        self.search_var.trace_add("write", self.filter_students)
        self.search_entry.pack(pady=10)

        # 7. Right Side Control Panel
        self.control_panel = ctk.CTkFrame(
            self.registry_container, width=200, fg_color="transparent"
        )
        self.control_panel.pack(side="right", fill="y")

        # ... (rest of your button code) ...
        btn_style = {"width": 160, "height": 40, "font": ("Arial Bold", 13)}

        self.btn_add = ctk.CTkButton(
            self.control_panel,
            text="Add Student",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            **btn_style,
            command=self.add_empty_row,
        )
        self.btn_add.pack(pady=10)

        self.btn_import_excel = ctk.CTkButton(
            self.control_panel,
            text="Import from Excel",
            fg_color="#247a74",
            hover_color="#1d625d",
            **btn_style,
            command=lambda: self.import_students_from_excel(class_name),
        )
        self.btn_import_excel.pack(pady=10)

        self.btn_ocr = ctk.CTkButton(
            self.control_panel,
            text="📷 OCR Register",
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            **btn_style,
            command=lambda: self.open_ocr_dialog(class_name),
        )
        self.btn_ocr.pack(pady=10)

        self.btn_remove = ctk.CTkButton(
            self.control_panel,
            text="Remove all Students",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            **btn_style,
        )
        self.btn_remove.pack(pady=10)

        self.btn_edit = ctk.CTkButton(
            self.control_panel,
            text="Edit all Students",
            fg_color="#f39c12",
            hover_color="#d35400",
            **btn_style,
            command=self.mass_edit_all,
        )
        self.btn_edit.pack(pady=10)

        self.spacer = ctk.CTkLabel(self.control_panel, text="")
        self.spacer.pack(expand=True)

        self.btn_home = ctk.CTkButton(
            self.control_panel, text="Home", command=self.return_to_home, **btn_style
        )
        self.btn_home.pack(pady=10)

        self.btn_remove.configure(command=self.clear_all_students)

    def configure_class_streams(self, class_name):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Configure {class_name} Streams")
        dialog.geometry("420x520")
        dialog.transient(self)
        dialog.grab_set()

        existing = self.db.get_class_streams(class_name)
        ctk.CTkLabel(dialog, text=f"Streams for {class_name}", font=("Arial Bold", 20)).pack(pady=(20, 8))
        ctk.CTkLabel(dialog, text="Choose 0 for no streams, or enter a name for each stream.").pack(pady=(0, 12))
        count_var = ctk.StringVar(value=str(len(existing)))
        count_menu = ctk.CTkOptionMenu(dialog, values=[str(count) for count in range(13)], variable=count_var)
        count_menu.pack(pady=(0, 12))
        names_frame = ctk.CTkScrollableFrame(dialog, height=300)
        names_frame.pack(fill="both", expand=True, padx=20, pady=8)
        name_entries = []

        def rebuild_name_entries(_value=None):
            for child in names_frame.winfo_children():
                child.destroy()
            name_entries.clear()
            for index in range(int(count_var.get())):
                entry = ctk.CTkEntry(names_frame, placeholder_text=f"Stream {index + 1}")
                entry.pack(fill="x", pady=5)
                if index < len(existing):
                    entry.insert(0, existing[index])
                name_entries.append(entry)

        count_menu.configure(command=rebuild_name_entries)
        rebuild_name_entries()

        def save_streams():
            try:
                self.db.set_class_streams(class_name, [entry.get() for entry in name_entries])
                dialog.destroy()
                self.show_student_registry(class_name)
            except ValueError as error:
                messagebox.showerror("Invalid Streams", str(error), parent=dialog)

        ctk.CTkButton(dialog, text="Save Streams", command=save_streams).pack(pady=16)

    def next_registry_admission_number(self):
        """Allocate an admission number after saved and currently staged rows."""
        next_admission_text = self.db.next_admission_number()
        next_admission = int(next_admission_text)
        pending_admissions = []
        self.prune_dead_student_rows()
        for row_frame in self.all_student_rows:
            for widget in row_frame.winfo_children():
                if not isinstance(widget, ctk.CTkEntry):
                    continue
                try:
                    column = int(widget.grid_info().get("column", -1))
                except (TypeError, ValueError):
                    continue
                value = widget.get().strip()
                if column == 0 and value.isdigit():
                    pending_admissions.append(int(value))
        if pending_admissions:
            next_admission = max(next_admission, max(pending_admissions) + 1)
        width = max(len(str(next_admission)), len(next_admission_text))
        return str(next_admission).zfill(width)

    def prune_dead_student_rows(self):
        """Forget row frames whose Tk widgets were destroyed."""
        live_rows = []
        for row in self.all_student_rows:
            try:
                if row.winfo_exists():
                    live_rows.append(row)
            except Exception:
                pass
        self.all_student_rows = live_rows

    def import_students_from_excel(self, class_name):
        """Load KNEC nominal-roll rows into the editable student registry."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select KNEC Nominal Roll",
            filetypes=[("Excel workbooks", "*.xlsx *.xlsm")],
        )
        if not file_path:
            return

        try:
            imported_students = read_student_rows(file_path)
            self.prune_dead_student_rows()
            self.db.cursor().execute(
                "SELECT assessment_number FROM students WHERE assessment_number IS NOT NULL"
            )
            seen_assessment_numbers = {
                str(row[0]).strip() for row in self.db.cursor().fetchall() if row[0]
            }
            for row_frame in self.all_student_rows:
                for widget in row_frame.winfo_children():
                    if not isinstance(widget, ctk.CTkEntry):
                        continue
                    try:
                        column = int(widget.grid_info().get("column", -1))
                    except (TypeError, ValueError):
                        continue
                    if column == 1 and widget.get().strip():
                        seen_assessment_numbers.add(widget.get().strip())

            students_to_add = []
            skipped_duplicates = 0
            for student in imported_students:
                assessment_number = student["assessment_number"].strip()
                if assessment_number in seen_assessment_numbers:
                    skipped_duplicates += 1
                    continue
                seen_assessment_numbers.add(assessment_number)
                students_to_add.append(student)

            if not students_to_add:
                messagebox.showinfo(
                    "Excel Import",
                    "No new students were found. Existing assessment numbers were skipped.",
                )
                return

            grade_mapping = {
                "Play group": "playgroup",
                "Pre-Primary 1": "pp1",
                "Pre-Primary 2": "pp2",
            }
            grade = grade_mapping.get(class_name, class_name)
            has_stream_column = bool(imported_students) and all(
                "stream" in student for student in imported_students
            )

            if self.registry_streams and not has_stream_column:
                self.assign_import_streams(
                    class_name, grade, students_to_add, skipped_duplicates
                )
                return

            if self.registry_streams:
                selected_stream = self.registry_stream.casefold()
                assigned_students = [
                    (student, self.registry_stream)
                    for student in students_to_add
                    if student.get("stream", "").strip().casefold() == selected_stream
                ]
                skipped_other_streams = len(students_to_add) - len(assigned_students)
            else:
                assigned_students = [
                    (student, student.get("stream") or "None")
                    for student in students_to_add
                ]
                skipped_other_streams = 0

            if not assigned_students:
                messagebox.showinfo(
                    "Excel Import",
                    f"No new Excel rows matched stream '{self.registry_stream}'.",
                )
                return

            self.stage_imported_students(
                class_name,
                grade,
                assigned_students,
                skipped_duplicates,
                skipped_other_streams,
            )
        except Exception as error:
            messagebox.showerror("Excel Import", f"Could not read this workbook:\n{error}")

    def assign_import_streams(self, class_name, grade, students, skipped_duplicates):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Assign Excel Students to Streams")
        dialog.geometry("1200x650")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(
            dialog,
            text="Select one stream for each student",
            font=("Arial Bold", 20),
        ).pack(pady=(16, 10))

        grid = ctk.CTkScrollableFrame(dialog)
        grid.pack(fill="both", expand=True, padx=16, pady=8)
        grid.grid_columnconfigure(0, weight=2, minsize=220)
        grid.grid_columnconfigure(1, weight=1, minsize=130)
        ctk.CTkLabel(grid, text="STUDENT", font=("Arial Bold", 11)).grid(
            row=0, column=0, padx=6, pady=6, sticky="w"
        )
        ctk.CTkLabel(grid, text="ASSESSMENT NO.", font=("Arial Bold", 11)).grid(
            row=0, column=1, padx=6, pady=6
        )
        for column, stream_name in enumerate(self.registry_streams, start=2):
            grid.grid_columnconfigure(column, weight=0, minsize=68)
            ctk.CTkLabel(
                grid,
                text=stream_name,
                font=("Arial Bold", 10),
                wraplength=64,
            ).grid(row=0, column=column, padx=2, pady=6)

        assignments = []
        for row_index, student in enumerate(students, start=1):
            ctk.CTkLabel(grid, text=student["name"], anchor="w").grid(
                row=row_index, column=0, padx=6, pady=4, sticky="ew"
            )
            ctk.CTkLabel(grid, text=student["assessment_number"]).grid(
                row=row_index, column=1, padx=6, pady=4
            )
            row_vars = {}
            assignments.append(row_vars)

            def select_only(stream_name, variables=row_vars):
                if variables[stream_name].get():
                    for other_name, variable in variables.items():
                        if other_name != stream_name:
                            variable.set(False)

            for column, stream_name in enumerate(self.registry_streams, start=2):
                variable = ctk.BooleanVar(value=False)
                row_vars[stream_name] = variable
                ctk.CTkCheckBox(
                    grid,
                    text="",
                    width=24,
                    variable=variable,
                    command=lambda name=stream_name, vars_for_row=row_vars: select_only(
                        name, vars_for_row
                    ),
                ).grid(row=row_index, column=column, padx=10, pady=4)

        def confirm_assignments():
            assigned = []
            for student, row_vars in zip(students, assignments):
                selected = [name for name, variable in row_vars.items() if variable.get()]
                if len(selected) != 1:
                    messagebox.showwarning(
                        "Stream Required",
                        f"Select exactly one stream for {student['name']}.",
                        parent=dialog,
                    )
                    return
                assigned.append((student, selected[0]))
            dialog.destroy()
            self.stage_imported_students(
                class_name, grade, assigned, skipped_duplicates, 0
            )

        ctk.CTkButton(
            dialog, text="Add to Registry", command=confirm_assignments
        ).pack(pady=12)

    def stage_imported_students(
        self, class_name, grade, assigned_students, skipped_duplicates, skipped_streams
    ):
        for student, stream_name in assigned_students:
            self.add_empty_row()
            row_frame = self.all_student_rows[-1]
            entries = {
                int(widget.grid_info()["column"]): widget
                for widget in row_frame.winfo_children()
                if isinstance(widget, ctk.CTkEntry)
            }
            values = {
                0: self.next_registry_admission_number(),
                1: student["assessment_number"],
                2: student["name"],
                3: grade,
                4: student.get("gender", ""),
                5: student.get("phone", ""),
                6: stream_name,
            }
            for column, value in values.items():
                entries[column].delete(0, "end")
                entries[column].insert(0, value)

        messagebox.showinfo(
            "Excel Import",
            f"Loaded {len(assigned_students)} students for review. "
            f"{skipped_duplicates} duplicate assessment number(s) skipped. "
            f"{skipped_streams} row(s) from other streams skipped. "
            "Save each row to register it.",
        )

    def open_ocr_dialog(self, class_name):
        """Open the OCR student registration dialog"""

        def refresh_registry():
            # Refresh the student registry after OCR registration
            self.show_student_registry(class_name, self.registry_stream)

        stream = self.registry_stream if self.registry_stream != "None" else None
        show_ocr_dialog(self, refresh_registry, self.db, class_name, stream)

    def open_cba_menu(self):
        self.highlight_button(self.btn_knec_cba)
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        menu = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        menu.pack(expand=True)
        ctk.CTkLabel(menu, text="KNEC CBA", font=("Arial Bold", 26)).pack(pady=20)
        ctk.CTkButton(
            menu,
            text="Add Tasks",
            width=260,
            height=48,
            command=lambda: self.show_class_selection(
                "KNEC CBA Tasks", self.btn_knec_cba
            ),
        ).pack(pady=10)
        ctk.CTkButton(
            menu,
            text="Add Tasks for Several Classes",
            width=260,
            height=48,
            command=self.show_cba_bulk_class_selection,
        ).pack(pady=10)
        ctk.CTkButton(
            menu,
            text="Fetch Converted CBA",
            width=260,
            height=48,
            command=lambda: self.show_class_selection(
                "KNEC CBA Fetch", self.btn_knec_cba
            ),
        ).pack(pady=10)

    def open_create_exam_dialog(self):
        if not self.get_academic_year():
            messagebox.showwarning("Year & Term", "Set the academic year and term first (top left of the dashboard).")
            return
        CreateExamDialog(self, on_created=self.on_exam_created, term=self.get_current_term())

    def classes_sharing_exam(self, class_names):
        """A marksheet group switches exam together, so include the whole group."""
        group_types = {kind for name, kind in MARKSHEET_CLASS_TYPES if name in class_names}
        return [name for name, kind in MARKSHEET_CLASS_TYPES if kind in group_types]

    def on_exam_created(self, title, term, all_classes, classes):
        chosen = [name for name, _kind in MARKSHEET_CLASS_TYPES] if all_classes else classes
        affected = self.classes_sharing_exam(chosen)
        if not affected:
            return
        message = (
            f"Start '{title}' ({term}) on this computer for: {', '.join(affected)}.\n\n"
            "The current marks are first saved as read-only history, then cleared."
        )
        extra = [name for name in affected if name not in chosen]
        if extra:
            message += f"\n\nIncluded because they share a marksheet: {', '.join(extra)}."
        if messagebox.askyesno("Start Exam on This Computer", message):
            self.rotate_local_exam(title, term, affected)
            messagebox.showinfo("Exam Started", f"'{title}' is now the current exam ({term}).")

    def rotate_local_exam(self, exam_title, term, class_names):
        config = self.load_school_config()
        updates = {}
        for class_name, grade_type in MARKSHEET_CLASS_TYPES:
            if class_name not in class_names:
                continue
            self.store_class_exam(class_name, grade_type, config)
            updates[f"{grade_type}_exam_title"] = exam_title
            updates[f"{grade_type}_exam_term"] = term
            if grade_type == "jss":
                updates["current_exam_title"] = exam_title
        self.save_school_config(updates)

    def store_class_exam(self, class_name, grade_type, config):
        """Save the class's current exam as read-only history for its term and year, then clear its marks."""
        old_title = config.get(f"{grade_type}_exam_title", "")
        table_name = self.get_table_name_for_grade(grade_type)
        if old_title:
            empty_summary = json.dumps(
                {
                    "total_students": 0,
                    "distribution": {},
                    "gender_counts": {},
                    "gender_totals": {},
                    "subject_averages": [],
                    "has_history": False,
                    "trend_text": "First Exam",
                }
            )
            streams = self.db.get_class_streams(class_name)
            archive_streams = [*streams, "None"] if streams else [None]
            for stream in archive_streams:
                history_class = f"{class_name} [{stream}]" if stream and stream != "None" else class_name
                marks_data = self.get_current_marks_for_class(
                    class_name, table_name, grade_type,
                    stream=stream if streams else None,
                )
                self.db.save_previous_exam(
                    old_title, history_class, empty_summary, marks_data,
                    term=config.get(f"{grade_type}_exam_term") or config.get("current_term") or None,
                    year=self.get_academic_year(),
                )
        try:
            self.db.cursor().execute(
                f"DELETE FROM {table_name} WHERE adm_no IN (SELECT adm_no FROM students WHERE grade = ?)",
                (class_name,),
            )
            self.db.conn.commit()
        except Exception as error:
            print(f"Error clearing marks for {class_name}: {error}")

    def open_competency_gradebook(self):
        self.show_class_selection(
            "Strands", self.btn_competency_gradebook
        )

    def return_to_strands(self):
        self.show_dashboard_workspace()
        self.open_competency_gradebook()

    def open_performance_dashboard(self):
        self.show_class_selection(
            "Performance Dashboard", self.btn_performance_dashboard
        )

    def return_to_performance(self):
        self.show_dashboard_workspace()
        self.open_performance_dashboard()

    def show_cba_bulk_class_selection(self):
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        frame = ctk.CTkScrollableFrame(
            self.content_panel,
            label_text="SELECT CLASSES FOR SHARED TASKS",
            label_font=("Arial Bold", 20),
            width=520,
            height=520,
        )
        frame.pack(expand=True, fill="both", padx=30, pady=30)
        classes = [
            "playgroup", "pp1", "pp2", "Grade 1", "Grade 2", "Grade 3",
            "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9",
        ]
        self.cba_class_vars = {}
        for class_name in classes:
            selected = ctk.BooleanVar(value=False)
            self.cba_class_vars[class_name] = selected
            ctk.CTkCheckBox(frame, text=class_name, variable=selected).pack(
                anchor="w", padx=12, pady=5
            )
        ctk.CTkButton(
            frame,
            text="OK",
            command=self.show_cba_bulk_subject_selection,
        ).pack(pady=16)

    def show_cba_bulk_subject_selection(self):
        selected_classes = [
            class_name
            for class_name, variable in self.cba_class_vars.items()
            if variable.get()
        ]
        if not selected_classes:
            messagebox.showwarning("Select Classes", "Select at least one class.")
            return

        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()
        frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        frame.pack(expand=True)
        ctk.CTkLabel(
            frame,
            text=f"Shared tasks for {len(selected_classes)} selected class(es)",
            font=("Arial Bold", 20),
        ).pack(pady=14)

        subject_sets = [set(get_subjects_for_class(name)) for name in selected_classes]
        common_subjects = sorted(set.intersection(*subject_sets)) if subject_sets else []
        subject_mode = ctk.StringVar(value="Same subject")
        mode = ctk.CTkSegmentedButton(
            frame,
            values=["Same subject", "All subjects"],
            variable=subject_mode,
            command=lambda _: update_subject_control(),
        )
        mode.pack(pady=12)

        if not common_subjects:
            mode.configure(values=["All subjects"])
            subject_mode.set("All subjects")
        subject_menu = ctk.CTkOptionMenu(
            frame,
            values=common_subjects or ["No common subject"],
            width=250,
        )
        subject_menu.pack(pady=12)

        def update_subject_control():
            if subject_mode.get() == "Same subject" and common_subjects:
                subject_menu.configure(state="normal")
            else:
                subject_menu.configure(state="disabled")

        def open_shared_editor():
            if subject_mode.get() == "Same subject":
                subject = subject_menu.get()
                targets = [(class_name, subject) for class_name in selected_classes]
            else:
                targets = [
                    (class_name, subject)
                    for class_name in selected_classes
                    for subject in get_subjects_for_class(class_name)
                ]
            if not targets:
                messagebox.showwarning(
                    "No Subjects", "No configured subjects were found for the selected classes."
                )
                return
            first_class, first_subject = targets[0]
            self.open_cba_task_manager(
                first_class, first_subject, targets=targets
            )

        ctk.CTkButton(frame, text="OK", command=open_shared_editor).pack(pady=16)
        ctk.CTkButton(
            frame,
            text="Back to Classes",
            command=self.show_cba_bulk_class_selection,
        ).pack(pady=5)

    def show_cba_fetch_subject_selection(self, class_name):
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        subjects = get_subjects_for_class(class_name)
        if not subjects:
            messagebox.showwarning("No Subjects", f"No subjects are configured for {class_name}.")
            return

        frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        frame.pack(expand=True)
        ctk.CTkLabel(
            frame,
            text=f"Fetch converted CBA results · {class_name}",
            font=("Arial Bold", 21),
        ).pack(pady=14)

        subject_menu = ctk.CTkOptionMenu(frame, values=subjects, width=260)
        subject_menu.pack(pady=10)
        term_menu = ctk.CTkOptionMenu(
            frame, values=["Term 1", "Term 2", "Term 3"], width=180
        )
        term_menu.pack(pady=10)

        def update_terms(selected_subject):
            class_tasks = (
                self.load_school_config()
                .get("cba_tasks", {})
                .get(class_name, {})
                .get(selected_subject, {})
            )
            available_terms = (
                list(class_tasks.keys())
                if isinstance(class_tasks, dict)
                else ["Term 1"]
            )
            if not available_terms:
                available_terms = ["Term 1", "Term 2", "Term 3"]
            term_menu.configure(values=available_terms)
            active_term = (
                self.load_school_config()
                .get("cba_active_terms", {})
                .get(class_name, {})
                .get(selected_subject)
            )
            term_menu.set(active_term if active_term in available_terms else available_terms[0])

        subject_menu.configure(command=update_terms)
        update_terms(subject_menu.get())

        def fetch_results():
            credentials = ask_cloud_credentials(self)
            if not credentials:
                return
            result = CloudService().fetch_cba_results(
                class_name, subject_menu.get(), term_menu.get(), credentials
            )
            if not result.get("success"):
                messagebox.showerror(
                    "CBA Fetch Failed",
                    result.get("message", "Could not fetch converted CBA results."),
                )
                return
            for widget in self.content_panel.winfo_children():
                if widget != self.header_frame and widget != self.theme_frame:
                    widget.destroy()
            self.current_view = CBAResultsView(
                self.content_panel,
                result,
                return_callback=lambda: self.show_cba_fetch_subject_selection(class_name),
            )
            self.current_view.pack(fill="both", expand=True)

        ctk.CTkButton(
            frame,
            text="Fetch Converted CBA",
            width=240,
            height=44,
            command=fetch_results,
        ).pack(pady=18)

        ctk.CTkButton(
            frame,
            text="Back to Classes",
            command=lambda: self.show_class_selection(
                "KNEC CBA Fetch", self.btn_knec_cba
            ),
        ).pack(pady=6)

    def show_cba_subject_selection(self, class_name):
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        frame = ctk.CTkScrollableFrame(
            self.content_panel,
            label_text=f"SELECT SUBJECT FOR: {class_name.upper()}",
            label_font=("Arial Bold", 20),
            width=520,
            height=520,
        )
        frame.pack(expand=True, fill="both", padx=30, pady=30)
        subjects = get_subjects_for_class(class_name)
        if not subjects:
            ctk.CTkLabel(frame, text="No subjects are configured for this class.").pack(
                pady=20
            )
        for subject in subjects:
            ctk.CTkButton(
                frame,
                text=subject,
                width=300,
                height=42,
                command=lambda selected=subject: self.open_cba_task_manager(
                    class_name, selected
                ),
            ).pack(pady=7)
        ctk.CTkButton(
            frame,
            text="Back to Classes",
            command=lambda: self.show_class_selection(
                "KNEC CBA Tasks", self.btn_knec_cba
            ),
        ).pack(pady=18)

    def open_cba_task_manager(self, class_name, subject, targets=None):
        targets = targets or [(class_name, subject)]
        config = self.load_school_config()
        subject_tasks = (
            config.get("cba_tasks", {}).get(class_name, {}).get(subject, {})
        )
        if isinstance(subject_tasks, list):
            tasks_by_term = {"Term 1": subject_tasks}
        elif isinstance(subject_tasks, dict):
            tasks_by_term = subject_tasks
        else:
            tasks_by_term = {}
        active_term = (
            config.get("cba_active_terms", {}).get(class_name, {}).get(subject)
        )
        if active_term not in ("Term 1", "Term 2", "Term 3"):
            active_term = next(
                (
                    term
                    for term in reversed(("Term 1", "Term 2", "Term 3"))
                    if tasks_by_term.get(term)
                ),
                "Term 1",
            )

        def save_tasks_for_term(term, saved_tasks):
            current_config = self.load_school_config()
            cba_tasks = current_config.get("cba_tasks", {})
            active_terms = current_config.get("cba_active_terms", {})
            for target_class, target_subject in targets:
                class_tasks = cba_tasks.setdefault(target_class, {})
                current = class_tasks.get(target_subject, {})
                if isinstance(current, list):
                    current = {"Term 1": current}
                current[term] = saved_tasks
                class_tasks[target_subject] = current
                active_terms.setdefault(target_class, {})[target_subject] = term
            self.save_school_config(
                {"cba_tasks": cba_tasks, "cba_active_terms": active_terms}
            )

        CBATaskManager(
            self,
            class_name,
            subject,
            tasks_by_term=tasks_by_term,
            term=active_term,
            targets=targets,
            on_change=save_tasks_for_term,
        )

    def load_students_from_db(self, class_name):
        try:
            # Use the public cursor method for consistency with case-insensitive grade matching
            print(f"DEBUG: Loading students for class_name='{class_name}'")
            print(f"DEBUG: Database connection: {self.db.conn}")
            print(f"DEBUG: Database connection ID: {id(self.db.conn)}")
            print(
                f"DEBUG: Database path: {self.db.conn.execute('PRAGMA database_list').fetchall()}"
            )

            # Check if we're using the same connection as the dashboard
            print(f"DEBUG: Dashboard DB connection ID: {id(self.db.conn)}")

            # First, let's check what grades exist in the database
            print(f"DEBUG: Executing SELECT DISTINCT grade FROM students...")
            self.db.cursor().execute("SELECT DISTINCT grade FROM students")
            all_grades = self.db.cursor().fetchall()
            print(f"DEBUG: All grades in database: {all_grades}")

            # Check total student count
            self.db.cursor().execute("SELECT COUNT(*) FROM students")
            total_count = self.db.cursor().fetchone()[0]
            print(f"DEBUG: Total students in database: {total_count}")

            query = (
                "SELECT adm_no, assessment_number, name, grade, gender, phone, photo, stream "
                "FROM students WHERE UPPER(grade) = UPPER(?)"
            )
            params = [class_name]
            if self.registry_streams:
                if self.registry_stream == "None":
                    query += " AND (stream IS NULL OR TRIM(stream) = '' OR UPPER(stream) = 'NONE')"
                else:
                    query += " AND UPPER(TRIM(stream)) = UPPER(?)"
                    params.append(self.registry_stream)
            self.db.cursor().execute(query, params)
            records = self.db.cursor().fetchall()
            print(
                f"DEBUG: Loaded {len(records)} students for grade '{class_name}' from database"
            )
            print(f"DEBUG: Student records: {records}")

            # Clear current list tracker before adding new ones
            self.all_student_rows = []

            for row_data in records:
                self.add_locked_row(row_data)

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            import traceback

            traceback.print_exc()

    def add_locked_row(self, data):
        """Creates a row that is already saved and disabled with perfect alignment"""
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#1a1a1a")
        row_frame.pack(fill="x", pady=2, padx=5)
        self.all_student_rows.append(row_frame)

        # --- THE ALIGNMENT FIX ---
        # Keep all student fields aligned with the registry headers.
        for i in range(8):
            row_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        # Keep the actions column fixed
        row_frame.grid_columnconfigure(8, weight=0, minsize=150)

        entries = []
        values = [
            data[0] if len(data) > 0 else "",
            data[1] if len(data) > 1 else "",
            data[2] if len(data) > 2 else "",
            data[3] if len(data) > 3 else "",
            data[4] if len(data) > 4 else "",
            data[5] if len(data) > 5 else "",
            data[7] if len(data) > 7 else "None",
        ]
        for column, value in enumerate(values):
            entry = ctk.CTkEntry(
                row_frame, fg_color="gray20", text_color="white", height=30
            )
            if value is not None:
                entry.insert(0, str(value))
            entry.configure(state="disabled")
            entry.grid(row=0, column=column, padx=2, pady=5, sticky="ew")
            entries.append(entry)

        # Photo field (column 7)
        photo_value = data[6] if len(data) > 6 else None
        photo_path = ctk.StringVar(value=photo_value or "")
        photo_btn = ctk.CTkButton(
            row_frame,
            text="✓ Photo" if photo_value else "📷 Photo",
            width=80,
            height=30,
            state="disabled",
            fg_color="gray",
        )
        photo_btn.grid(row=0, column=7, padx=2, pady=5, sticky="ew")
        entries.append(photo_path)  # Store the StringVar in entries list

        actions = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions.grid(row=0, column=8, padx=5)

        # DELETE (Red)
        # We use entries[0] because that's the ADM NO box we just created in the loop above
        del_btn = ctk.CTkButton(
            actions,
            text="🗑",
            width=30,
            fg_color="#942727",
            command=lambda f=row_frame, a=entries[0]: self.confirm_delete(f, a),
        )
        del_btn.pack(side="left", padx=2)

        save_btn = ctk.CTkButton(
            actions,
            text="Saved",
            width=40,
            state="disabled",
            fg_color="gray",
            command=lambda: self.save_to_db(
                entries[0], entries[2], entries[3], entries[4], entries[5],
                entries[6], entries[7], save_btn, entries[1]
            ),
        )
        save_btn.pack(side="left", padx=2)

        edit_btn = ctk.CTkButton(
            actions,
            text="✎",
            width=30,
            command=lambda e=entries, b=save_btn, pb=photo_btn: self.unlock_row_for_edit(
                e, b, pb
            ),
        )
        edit_btn.pack(side="left", padx=2)

    def confirm_delete(self, frame, adm_entry):
        adm_no = adm_entry.get()
        if not adm_no:
            frame.destroy()  # Just a blank row, safe to just close
            return

        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete ADM: {adm_no} permanently?",
        ):
            self.db.delete_student(adm_no)  # Delete from DB
            frame.destroy()  # Remove from UI

    def filter_students(self, *args):
        """Hides rows that don't match the search query"""
        search_query = self.search_var.get().lower()

        for row_frame in self.all_student_rows:
            # We need to look at the ADM (index 0) and Name (index 1) entries
            # We find them inside the row_frame
            row_widgets = [
                child
                for child in row_frame.winfo_children()
                if isinstance(child, ctk.CTkEntry)
            ]

            if row_widgets:
                adm_text = row_widgets[0].get().lower()
                name_text = row_widgets[2].get().lower()

                # If the search matches either the ADM or the Name, show the row
                if search_query in adm_text or search_query in name_text:
                    row_frame.pack(fill="x", pady=1, padx=5)  # Show
                else:
                    row_frame.pack_forget()  # Hide

    def show_dashboard_workspace(self):
        """Resets the layout so the sidebar is visible again"""
        self.grid_columnconfigure(0, weight=0, minsize=250)
        self.grid_columnconfigure(1, weight=1)
        self.menu_panel.grid(row=0, column=0, sticky="nsew")
        self.content_panel.grid(row=0, column=1, columnspan=1, sticky="nsew")

        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        if not hasattr(self, "header_frame") or not self.header_frame.winfo_exists():
            self.header_frame = ctk.CTkFrame(
                self.content_panel, width=1, height=1, fg_color="transparent"
            )
            self.header_frame.place_forget()
        if not hasattr(self, "theme_frame") or not self.theme_frame.winfo_exists():
            self.theme_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
            self.theme_frame.place_forget()

        self.create_home_header_controls()
        self.create_theme_controls()

        self.work_area_label = ctk.CTkLabel(
            self.content_panel,
            text="Select a task from the sidebar to begin.",
            font=("Arial", 18),
            text_color="gray60",
        )
        self.work_area_label.pack(expand=True)

        self.update_countdown_timer()
        self.reset_sidebar_highlights()
        self.apply_dashboard_theme()

    def return_to_home(self):
        """Brings back the sidebar and resets the layout"""

        # Remove marksheet toolbar if exists
        if hasattr(self, "marksheet_toolbar"):
            self.marksheet_toolbar.destroy()

        # 1. BRING BACK SIDEBAR
        self.menu_panel.grid(row=0, column=0, sticky="nsew")

        # 2. PUSH CONTENT BACK TO COLUMN 1
        self.content_panel.grid(row=0, column=1, sticky="nsew")

        # 3. Show the original welcome screen
        self.show_dashboard_workspace()

    def highlight_button(self, active_button):
        """Resets all sidebar buttons to ghost-style and makes the active one pop out"""
        self.reset_sidebar_highlights()
        self.active_sidebar_button = active_button

        # ACTIVE: The selected button gets the 'Freeman Glow'
        active_button.configure(
            fg_color=self.dashboard_accent,
            text_color="white",  # Crisp White Text
            font=("Arial Bold", 14),  # Bigger and Bolder
            border_width=2,  # Thin border to make it sharp
            border_color=self.get_hover_color(self.dashboard_accent),
        )

    def reset_sidebar_highlights(self):
        self.active_sidebar_button = None
        for button in getattr(self, "sidebar_buttons", []):
            if button.winfo_exists():
                button.configure(
                    fg_color="transparent",
                    text_color="gray",
                    font=("Arial", 13),
                    border_width=0,
                )

    def show_class_selection(self, action_type, button_object):
        # Trigger the visual highlight first
        self.highlight_button(button_object)

        # Clear the workspace (keep header/theme toggle)
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # Create the Scrollable Class Menu
        self.class_frame = ctk.CTkScrollableFrame(
            self.content_panel,
            label_text=f"SELECT CLASS FOR: {action_type.upper()}",
            label_font=("Arial Bold", 20),
            fg_color="gray10",  # Darker background for the class list
            width=400,
            height=500,
        )
        self.class_frame.pack(pady=40, expand=True)
        self.class_selection_buttons = []

        if action_type in ("Strands", "Performance Dashboard"):
            ctk.CTkButton(
                self.class_frame,
                text="← Back to Dashboard",
                fg_color="#e74c3c",
                hover_color="#c0392b",
                text_color="white",
                width=300,
                height=45,
                command=self.show_dashboard_workspace,
            ).pack(pady=(0, 20))

        # Add Send All Reports to Portal and Print All Reports buttons for Report Forms
        if action_type == "Report Forms":
            send_all_btn = ctk.CTkButton(
                self.class_frame,
                text="📤 Send All Reports to Portal",
                fg_color="#3498db",
                text_color="white",
                width=300,
                height=45,
                command=self.send_all_reports_to_portal,
            )
            send_all_btn.pack(pady=(0, 10))

            print_all_btn = ctk.CTkButton(
                self.class_frame,
                text="📄 Print All Reports",
                fg_color="#27ae60",
                text_color="white",
                width=300,
                height=45,
                command=self.print_all_reports,
            )
            print_all_btn.pack(pady=(0, 10))

            # Back to Dashboard button
            back_btn = ctk.CTkButton(
                self.class_frame,
                text="← Back to Dashboard",
                fg_color="#e74c3c",
                text_color="white",
                width=300,
                height=45,
                command=self.return_to_home,
            )
            back_btn.pack(pady=(0, 20))

        classes = [
            "playgroup",
            "pp1",
            "pp2",
            "Grade 1",
            "Grade 2",
            "Grade 3",
            "Grade 4",
            "Grade 5",
            "Grade 6",
            "Grade 7",
            "Grade 8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
        ]
        for class_name in classes:
            btn = ctk.CTkButton(
                self.class_frame,
                text=class_name,
                width=300,
                height=45,
                fg_color=self.dashboard_accent,
                hover_color=self.get_hover_color(self.dashboard_accent),
                command=lambda c=class_name: self.open_class_action(c, action_type),
            )
            btn.pack(pady=10)
            self.class_selection_buttons.append(btn)

    def open_class_action(self, class_selected, action_type, stream=None):
        configured_streams = self.db.get_class_streams(class_selected)
        if action_type not in ("Registration", "Registering") and configured_streams and stream is None:
            self.show_stream_selection(class_selected, action_type, configured_streams)
            return

        # 1. Clear the old view completely (Class Selection Menu)
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        print(f"Action: {action_type} | Target: {class_selected} | Stream: {stream or 'None'}")
        self.selected_stream = stream

        # 2. DECIDE: Which screen are we opening?

        # This handles the new Marksheet file
        if action_type == "Viewing Marks":
            # --- FULL SCREEN MODE ---
            self.menu_panel.grid_forget()  # Hide the left sidebar
            self.grid_columnconfigure(
                0, weight=0, minsize=0
            )  # Shrink sidebar space to zero
            self.content_panel.grid(
                row=0, column=0, columnspan=2, sticky="nsew"
            )  # Content takes all columns
            try:
                self.current_view = MarksheetChooser(
                    self.content_panel,
                    self.db,
                    class_selected,
                    self.load_school_config,
                    self.save_school_config,
                    lambda style, term, exam, is_current, year=None: self.open_chosen_marksheet(
                        class_selected, style, term, exam, is_current, year, stream
                    ),
                    self.return_to_home,
                    stream=stream,
                )
                self.current_view.pack(fill="both", expand=True)
            except Exception as error:
                import logging

                logging.exception("Unable to open the marksheet chooser")
                self.return_to_home()
                messagebox.showerror(
                    "Marksheet unavailable",
                    f"The marksheet could not be opened.\n\n{error}",
                    parent=self,
                )

        elif action_type == "Summary":
            # --- FULL SCREEN SUMMARY STYLE SELECTION ---
            self.menu_panel.grid_forget()
            self.grid_columnconfigure(0, weight=0, minsize=0)
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.current_view = SummaryChooser(
                self.content_panel,
                class_selected,
                self.load_school_config,
                self.save_school_config,
                lambda style: self.open_class_summary(class_selected, style, stream),
                self.return_to_home,
            )
            self.current_view.pack(fill="both", expand=True)

        elif action_type == "KNEC CBA Tasks":
            self.show_cba_subject_selection(class_selected)

        elif action_type == "KNEC CBA Fetch":
            self.show_cba_fetch_subject_selection(class_selected)

        elif action_type == "Performance Dashboard":
            self.menu_panel.grid_forget()
            self.grid_columnconfigure(0, weight=0, minsize=0)
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.current_view = CBCLevelsView(
                self.content_panel,
                class_selected,
                get_subjects_for_class(class_selected),
                self.load_school_config(),
                self.save_school_config,
                self.return_to_performance,
                self.show_dashboard_workspace,
            )
            self.current_view.pack(fill="both", expand=True)

        elif action_type == "Strands":
            self.menu_panel.grid_forget()
            self.grid_columnconfigure(0, weight=0, minsize=0)
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.current_view = CBCStrandsView(
                self.content_panel,
                class_selected,
                get_subjects_for_class(class_selected),
                self.load_school_config(),
                self.save_school_config,
                self.return_to_strands,
                self.show_dashboard_workspace,
            )
            self.current_view.pack(fill="both", expand=True)

        # This handles the Register button
        elif action_type == "Registering" or action_type == "Registration":
            # We call the function that is already inside this Dashboard class
            self.show_student_registry(class_selected)

        # This handles the Teachers Linked button
        elif action_type == "Teachers":
            # --- FULL SCREEN MODE ---
            self.menu_panel.grid_forget()  # Hide the left sidebar
            self.grid_columnconfigure(
                0, weight=0, minsize=0
            )  # Shrink sidebar space to zero
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.current_view = TeachersLinkedView(
                self.content_panel,
                self.db,
                class_selected,
                self.show_dashboard_workspace,
                stream=stream,
            )
            self.current_view.pack(fill="both", expand=True)

        # This handles the Report Forms button
        elif action_type == "Report Forms":
            # --- FULL SCREEN MODE ---
            self.menu_panel.grid_forget()  # Hide the left sidebar
            self.grid_columnconfigure(
                0, weight=0, minsize=0
            )  # Shrink sidebar space to zero
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.show_report_forms_class_view(class_selected, stream)

    def show_stream_selection(self, class_name, action_type, streams):
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        frame = ctk.CTkScrollableFrame(
            self.content_panel,
            label_text=f"SELECT STREAM FOR {class_name.upper()}: {action_type.upper()}",
            label_font=("Arial Bold", 20),
            fg_color="gray10",
            width=400,
            height=500,
        )
        frame.pack(pady=40, expand=True)
        ctk.CTkButton(
            frame,
            text="Back to Classes",
            width=300,
            height=40,
            command=lambda: self.show_class_selection(
                action_type, self.active_sidebar_button
            ),
        ).pack(pady=(0, 16))
        for stream in streams:
            ctk.CTkButton(
                frame,
                text=stream,
                width=300,
                height=45,
                fg_color=self.dashboard_accent,
                hover_color=self.get_hover_color(self.dashboard_accent),
                command=lambda selected=stream: self.open_class_action(
                    class_name, action_type, selected
                ),
            ).pack(pady=10)

    def show_report_forms_class_view(self, class_name, stream=None):
        # Clear the old view completely
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # Header frame with title and action buttons
        header_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"Report Forms - {class_name}" + (f" / {stream}" if stream else ""),
            font=("Arial Bold", 28),
        )
        title_label.pack(side="left", padx=10)

        # Send all reports for this class to portal button
        send_class_btn = ctk.CTkButton(
            header_frame,
            text="Send All Reports for This Class to Portal",
            fg_color="#3498db",
            hover_color="#2980b9",
            font=("Arial Bold", 14),
            height=40,
            command=lambda: self.send_class_reports_to_portal(class_name, stream),
        )
        send_class_btn.pack(side="right", padx=10)

        # Print reports for this class button
        print_class_btn = ctk.CTkButton(
            header_frame,
            text="Print Reports for This Class",
            fg_color="#27ae60",
            hover_color="#1e8449",
            font=("Arial Bold", 14),
            height=40,
            command=lambda: self.print_class_reports(class_name, stream),
        )
        print_class_btn.pack(side="right", padx=10)

        # Back button
        back_btn = ctk.CTkButton(
            header_frame,
            text="← Back to Class Selection",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=("Arial Bold", 14),
            height=40,
            command=self.open_report_forms,
        )
        back_btn.pack(side="right", padx=10)

        # Student list frame
        student_frame = ctk.CTkScrollableFrame(self.content_panel)
        student_frame.pack(fill="both", expand=True)

        # Get students in this class
        students = self.get_students_in_class(class_name, stream)

        if not students:
            no_students_label = ctk.CTkLabel(
                student_frame,
                text="No students found in this class",
                font=("Arial", 16),
                text_color="gray",
            )
            no_students_label.pack(pady=50)
            return

        # Create student rows
        for student in students:
            row_frame = ctk.CTkFrame(student_frame, height=60)
            row_frame.pack(fill="x", padx=20, pady=5)

            # Student info
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

            name_label = ctk.CTkLabel(
                info_frame, text=student["name"], font=("Arial Bold", 16)
            )
            name_label.pack(side="left", padx=10)

            adm_label = ctk.CTkLabel(
                info_frame,
                text=f"ADM: {student['adm_no']}",
                font=("Arial", 14),
                text_color="gray",
            )
            adm_label.pack(side="left", padx=10)

            # View report button
            view_btn = ctk.CTkButton(
                row_frame,
                text="View Report",
                fg_color="#9b59b6",
                hover_color="#8e44ad",
                width=150,
                height=40,
                command=lambda s=student: self.show_student_report_form(s),
            )
            view_btn.pack(side="right", padx=10, pady=10)

    def get_students_in_class(self, class_name, stream=None):
        try:
            query = "SELECT adm_no, name, grade, stream, photo FROM students WHERE UPPER(grade) = UPPER(?)"
            params = [class_name]
            if stream:
                query += " AND UPPER(TRIM(stream)) = UPPER(?)"
                params.append(stream)
            query += " ORDER BY name"
            self.db.cursor().execute(query, params)
            students = []
            for row in self.db.cursor().fetchall():
                student_data = {
                    "adm_no": row[0],
                    "name": row[1],
                    "grade": row[2],
                    "stream": row[3] if row[3] else "none",
                }
                if len(row) > 4 and row[4]:
                    student_data["photo"] = row[4]
                else:
                    student_data["photo"] = ""
                students.append(student_data)
            return students
        except Exception as e:
            print(f"Error getting students: {e}")
            return []

    def show_student_report_form(self, student):
        # Create a new toplevel window for the report form
        report_window = ctk.CTkToplevel(self)
        report_window.title(f"Report Form - {student['name']}")
        report_window.geometry("1400x900")
        report_window.state('zoomed')  # Full screen by default

        # Main container with portal gradient background
        report_container = ctk.CTkFrame(report_window, fg_color="#f0f2f5")
        report_container.pack(fill="both", expand=True, padx=0, pady=0)

        # Import report forms functionality
        from reportforms import ReportFormsView
        from teacher_comments import build_subject_comment_indices

        # Create a temporary report forms instance to use its methods
        temp_report = ReportFormsView.__new__(ReportFormsView)
        temp_report.parent_window = self
        temp_report.db = self.db
        temp_report.current_student = student
        temp_report.current_class = student["grade"]
        temp_report.school_config = self.load_school_config()
        temp_report.subject_comment_indices = build_subject_comment_indices(
            temp_report.school_config.get("subjects", {})
        )

        report_data = temp_report.generate_report_data(student)
        if not report_data:
            report_window.destroy()
            messagebox.showinfo("No Report Data", "No assessment marks are available for this student.", parent=self)
            return

        navigation = ctk.CTkFrame(report_container, fg_color="transparent")
        navigation.pack(fill="x", padx=12, pady=(8, 4))

        # Create school header
        temp_report.create_school_header(report_container, student)
        temp_report.create_student_info(report_container, student)

        page = ctk.CTkScrollableFrame(report_container, fg_color="transparent")
        page.pack(fill="both", expand=True, padx=8, pady=4)
        page_specs = [("Summary", "summary", None)]
        page_specs.extend(
            (item["name"], "rubric", item)
            for item in report_data.get("rubric_subjects", [])
        )
        if report_data.get("pathway_recommendation"):
            page_specs.append(("Career Pathways", "pathway", None))
        temp_report.report_page_specs = page_specs
        temp_report.report_page_container = page
        temp_report.report_page_buttons = []
        navigation_columns = 5
        for column in range(navigation_columns):
            navigation.grid_columnconfigure(column, weight=1, uniform="report_navigation")
        for index, (label, _kind, _data) in enumerate(page_specs):
            button = ctk.CTkButton(
                navigation,
                text=label,
                height=40,
                width=0,
                command=lambda selected=index: temp_report.show_report_page(selected, report_data),
            )
            button.grid(
                row=index // navigation_columns,
                column=index % navigation_columns,
                sticky="ew",
                padx=4,
                pady=4,
            )
            temp_report.report_page_buttons.append(button)
        temp_report.show_report_page(0, report_data)

        # Action buttons
        button_frame = ctk.CTkFrame(report_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=30)

        # Print PDF button
        print_btn = ctk.CTkButton(
            button_frame,
            text="📄 Print as PDF",
            fg_color="#27ae60",
            hover_color="#1e8449",
            font=("Arial Bold", 14),
            height=45,
            width=200,
            command=lambda: self.print_individual_report(temp_report, student),
        )
        print_btn.pack(side="left", padx=10)

        # Send to parent button
        send_btn = ctk.CTkButton(
            button_frame,
            text="📤 Send Report to Parent",
            fg_color="#3498db",
            hover_color="#2980b9",
            font=("Arial Bold", 14),
            height=45,
            width=200,
            command=lambda: temp_report.send_student_report_to_portal(student),
        )
        send_btn.pack(side="left", padx=10)

        # Close button
        close_btn = ctk.CTkButton(
            button_frame,
            text="✕ Close",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=("Arial Bold", 14),
            height=45,
            width=150,
            command=report_window.destroy,
        )
        close_btn.pack(side="right", padx=10)

        # Store reference to prevent garbage collection
        if not hasattr(self, "report_windows"):
            self.report_windows = []
        self.report_windows.append(report_window)

        # Bring window to front after a short delay
        report_window.after(100, report_window.lift)
        report_window.after(100, report_window.focus_force)

    def print_individual_report(self, report_view, student):
        report_mode = ask_report_print_mode(self)
        if report_mode is None:
            return
        date_range = ask_opening_closing_dates(self)
        if date_range is None:
            return
        report_data = report_view.generate_report_data(student)
        if report_data:
            report_view.print_report_pdf(
                None, report_data, date_range=date_range, report_mode=report_mode
            )

    def send_class_reports_to_portal(self, class_name, stream=None):
        credentials = self.get_cloud_credentials()
        if not credentials:
            return

        students = self.get_students_in_class(class_name, stream)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return

        from cloud_service import CloudService

        service = CloudService()
        success_count = 0

        for student in students:
            report_data = self.generate_report_data(student)
            result = service.send_student_report(report_data, credentials)

            if result.get("success"):
                success_count += 1

        messagebox.showinfo(
            "Success", f"Sent {success_count}/{len(students)} reports to portal."
        )

    def print_class_reports(self, class_name, stream=None):
        students = self.get_students_in_class(class_name, stream)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return

        report_mode = ask_report_print_mode(self)
        if report_mode is None:
            return
        date_range = ask_opening_closing_dates(self)
        if date_range is None:
            return

        from tkinter import filedialog
        from reportforms import ReportFormsView

        # Ask for directory to save PDFs
        save_dir = filedialog.askdirectory(
            title=f"Select folder to save {class_name} reports"
        )
        if not save_dir:
            return

        success_count = 0
        for student in students:
            try:
                # Create temporary report object
                temp_report = ReportFormsView.__new__(ReportFormsView)
                temp_report.db = self.db
                temp_report.school_config = self.load_school_config()

                # Generate report data for this student
                report_data = temp_report.generate_report_data(student)

                if not report_data:
                    print(
                        f"Warning: No report data generated for {student.get('name', 'Unknown')}"
                    )
                    continue

                # Generate PDF
                student_name = student.get("name", "")
                exam_title = report_data.get("exam_title", "PERFORMANCE REPORT")
                file_path = f"{save_dir}/{student_name.replace(' ', '_')}_{exam_title.replace(' ', '_')}.pdf"

                # Call the print function with file_path
                if temp_report.print_report_pdf(
                    None, report_data, file_path, date_range=date_range,
                    report_mode=report_mode,
                ):
                    success_count += 1

            except Exception as e:
                print(f"Error generating PDF for {student.get('name', 'Unknown')}: {e}")
                import traceback

                traceback.print_exc()

        messagebox.showinfo(
            "Success",
            f"Generated {success_count}/{len(students)} PDF reports for {class_name}.",
        )

    def generate_report_data(self, student):
        from reportforms import ReportFormsView

        temp_report = ReportFormsView.__new__(ReportFormsView)
        temp_report.db = self.db
        temp_report.school_config = self.load_school_config()
        return temp_report.generate_report_data(student)

    def get_cloud_credentials(self):
        from cloud_service import ask_cloud_credentials

        cloud_config = self.load_school_config()
        cloud_school_code = cloud_config.get("cloud_school_code", "").strip()
        cloud_teacher_username = cloud_config.get("cloud_teacher_username", "").strip()
        cloud_teacher_password = cloud_config.get("cloud_teacher_password", "").strip()

        if not cloud_school_code or not cloud_teacher_username:
            messagebox.showwarning(
                "Cloud Not Configured",
                "Please configure cloud credentials in school settings.",
            )
            return None

        if cloud_teacher_password:
            return {
                "school_code": cloud_school_code,
                "username": cloud_teacher_username,
                "password": cloud_teacher_password,
            }
        else:
            return ask_cloud_credentials(self)

    def send_all_reports_to_portal(self):
        credentials = self.get_cloud_credentials()
        if not credentials:
            return

        classes = [
            "playgroup",
            "pp1",
            "pp2",
            "Grade 1",
            "Grade 2",
            "Grade 3",
            "Grade 4",
            "Grade 5",
            "Grade 6",
            "Grade 7",
            "Grade 8",
            "Grade 9",
        ]

        from cloud_service import CloudService

        service = CloudService()
        total_success = 0
        total_students = 0

        for class_name in classes:
            students = self.get_students_in_class(class_name)
            total_students += len(students)

            for student in students:
                report_data = self.generate_report_data(student)
                if report_data is None:
                    print(f"Skipping {student.get('name', 'Unknown')} - no marks found")
                    continue
                result = service.send_student_report(report_data, credentials)

                if result.get("success"):
                    total_success += 1

        messagebox.showinfo(
            "Success", f"Sent {total_success}/{total_students} reports to portal."
        )

    def print_all_reports(self):
        classes = [
            "playgroup",
            "pp1",
            "pp2",
            "Grade 1",
            "Grade 2",
            "Grade 3",
            "Grade 4",
            "Grade 5",
            "Grade 6",
            "Grade 7",
            "Grade 8",
            "Grade 9",
        ]

        report_mode = ask_report_print_mode(self)
        if report_mode is None:
            return
        date_range = ask_opening_closing_dates(self)
        if date_range is None:
            return

        from tkinter import filedialog
        from reportforms import ReportFormsView

        # Ask for directory to save PDFs
        save_dir = filedialog.askdirectory(title="Select folder to save all reports")
        if not save_dir:
            return

        total_success = 0
        total_students = 0

        for class_name in classes:
            students = self.get_students_in_class(class_name)
            if not students:
                continue

            total_students += len(students)
            class_dir = os.path.join(save_dir, class_name)
            os.makedirs(class_dir, exist_ok=True)

            for student in students:
                try:
                    # Create temporary report object
                    temp_report = ReportFormsView.__new__(ReportFormsView)
                    temp_report.db = self.db
                    temp_report.school_config = self.load_school_config()

                    # Generate report data for this student
                    report_data = temp_report.generate_report_data(student)

                    if not report_data:
                        print(
                            f"Warning: No report data generated for {student.get('name', 'Unknown')} in {class_name}"
                        )
                        continue

                    # Generate PDF
                    student_name = student.get("name", "")
                    exam_title = report_data.get("exam_title", "PERFORMANCE REPORT")
                    file_path = os.path.join(
                        class_dir,
                        f"{student_name.replace(' ', '_')}_{exam_title.replace(' ', '_')}.pdf",
                    )

                    # Call the print function with file_path
                    if temp_report.print_report_pdf(
                        None, report_data, file_path, date_range=date_range,
                        report_mode=report_mode,
                    ):
                        total_success += 1

                except Exception as e:
                    print(
                        f"Error generating PDF for {student.get('name', 'Unknown')} in {class_name}: {e}"
                    )
                    import traceback

                    traceback.print_exc()

        messagebox.showinfo(
            "Success",
            f"Generated {total_success}/{total_students} PDF reports for all classes.",
        )

    def open_class_summary(self, class_name, style, stream=None):
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()
        self.menu_panel.grid_forget()
        self.grid_columnconfigure(0, weight=0, minsize=0)
        self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.current_view = ClassSummaryView(
            self.content_panel, self.db, class_name, stream=stream, style=style
        )
        self.current_view.pack(fill="both", expand=True)

    def open_chosen_marksheet(self, class_name, style, term, exam_name, is_current, year=None, stream=None):
        if exam_name is None:
            messagebox.showinfo(
                "No Exam", f"No exam for {term}. Create one with the Create Exam button on the dashboard."
            )
            return
        old_views = {
            "playgroup": PlaygroupMarkSheetView,
            "pp1": PP1MarkSheetView,
            "pp2": PP2MarkSheetView,
            "lower": LowerMarkSheetView,
            "primary": PrimaryMarkSheetView,
            "jss": JuniorMarkSheetView,
        }
        grade_type = dict(MARKSHEET_CLASS_TYPES).get(class_name) or map_class_name_to_config_key(class_name)
        if not is_current:
            if style != OLD_STYLE:
                messagebox.showinfo(
                    "Previous Exam",
                    "Previous exams open in the old style (read-only). Their saved ratings use the old layout.",
                )
            self.open_previous_exam_marksheet(exam_name, class_name, year, stream)
            return
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()
        if style == OLD_STYLE:
            self.current_view = old_views.get(grade_type, JuniorMarkSheetView)(
                self.content_panel, self.db, class_name, stream=stream
            )
        else:
            self.current_view = KICDMarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                self.return_to_home,
                self.load_school_config,
                self.save_school_config,
                initial_term=term,
                stream=stream,
            )
        self.current_view.pack(fill="both", expand=True)

    def open_previous_exam_marksheet(self, exam_name, class_name, year=None, stream=None):
        # Clear the old view completely
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # Full screen mode
        self.menu_panel.grid_forget()
        self.grid_columnconfigure(0, weight=0, minsize=0)
        self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # Get the exam data
        history_class = f"{class_name} [{stream}]" if stream else class_name
        marks_data, summary_data = self.db.get_previous_exam_data(exam_name, history_class, year)

        # Determine the correct marksheet view based on class
        name_upper = class_name.upper().strip()

        if "PLAYGROUP" in name_upper or "PLAY GROUP" in name_upper:
            from ui_marksheet_playgroup import PlaygroupMarkSheetView

            self.current_view = PlaygroupMarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                read_only=True,
                exam_name=exam_name,
                marks_data=marks_data,
                summary_data=summary_data,
                stream=stream,
            )
        elif "PP1" in name_upper or "PRE-PRIMARY 1" in name_upper:
            from ui_marksheet_pp1 import PP1MarkSheetView

            self.current_view = PP1MarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                read_only=True,
                exam_name=exam_name,
                marks_data=marks_data,
                summary_data=summary_data,
                stream=stream,
            )
        elif "PP2" in name_upper or "PRE-PRIMARY 2" in name_upper:
            from ui_marksheet_pp2 import PP2MarkSheetView

            self.current_view = PP2MarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                read_only=True,
                exam_name=exam_name,
                marks_data=marks_data,
                summary_data=summary_data,
                stream=stream,
            )
        elif any(g in name_upper for g in ["GRADE 1", "GRADE 2", "GRADE 3"]):
            from ui_marksheet_lower import LowerMarkSheetView

            self.current_view = LowerMarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                read_only=True,
                exam_name=exam_name,
                marks_data=marks_data,
                summary_data=summary_data,
                stream=stream,
            )
        elif any(g in name_upper for g in ["GRADE 4", "GRADE 5", "GRADE 6"]):
            from ui_marksheet_primary import PrimaryMarkSheetView

            self.current_view = PrimaryMarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                read_only=True,
                exam_name=exam_name,
                marks_data=marks_data,
                summary_data=summary_data,
                stream=stream,
            )
        else:
            from ui_marksheet_junior import JuniorMarkSheetView

            self.current_view = JuniorMarkSheetView(
                self.content_panel,
                self.db,
                class_name,
                read_only=True,
                exam_name=exam_name,
                marks_data=marks_data,
                summary_data=summary_data,
                stream=stream,
            )

        self.current_view.pack(fill="both", expand=True)

    def show_marksheet_view(self, class_name):
        # 1. Clear the main panel
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # 2. Call the new MarkSheet class
        # This replaces all the manual code you would have written!
        self.marksheet = JuniorMarkSheetView(self.content_panel, self.db, class_name)
        self.marksheet.pack(fill="both", expand=True)

    # --- EVENTS / LOGIC ---
    def exit_app(self):
        """Cleanly closes the dashboard and the entire Python application"""
        self.destroy()  # Closes the Window
        sys.exit()  # Tells Python to stop entirely

    def change_theme_event(self, selected_mode):
        """Apply and persist the selected dashboard appearance mode."""
        self.dashboard_appearance = "Light" if selected_mode == "Light Mode" else "Dark"
        ctk.set_appearance_mode(self.dashboard_appearance)
        self.save_school_config({"dashboard_appearance": self.dashboard_appearance})
        self.apply_dashboard_theme()

    def dummy_event(self):
        """Temporary function so the buttons have commands without crashing"""
        print("Button Clicked - Feature coming soon!")

    def create_new_exam_all_classes(self):
        """Create a new exam for all marksheet types at once"""
        import json
        from datetime import datetime, timedelta

        dialog = ctk.CTkInputDialog(
            text="Enter New Exam Title (for all classes):",
            title="Create New Exam - All Classes",
        )
        exam_title = dialog.get_input()

        if not exam_title:
            return

        exam_title = exam_title.strip()
        if not exam_title:
            messagebox.showwarning("Invalid Title", "Please enter a valid exam title.")
            return

        # Load school config
        school_config = self.load_school_config()

        # Store OLD exam titles before updating (to save as previous exams)
        grade_types = ["playgroup", "pp1", "pp2", "lower", "primary", "jss"]
        old_exam_titles = {}
        for grade_type in grade_types:
            old_exam_titles[grade_type] = school_config.get(
                f"{grade_type}_exam_title", ""
            )

        # Update exam titles for all grade types in school_config.json
        for grade_type in grade_types:
            school_config[f"{grade_type}_exam_title"] = exam_title

        # Also update current_exam_title for junior marksheet
        old_exam_titles["current"] = school_config.get("current_exam_title", "")
        school_config["current_exam_title"] = exam_title

        # Save updated school config
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            with open(json_path, "w") as f:
                json.dump(school_config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update school config: {e}")
            return

        # List of all marksheet types (use lowercase to match database)
        class_types = [
            ("playgroup", "playgroup"),
            ("pp1", "pp1"),
            ("pp2", "pp2"),
            ("Grade 1", "lower"),
            ("Grade 2", "lower"),
            ("Grade 3", "lower"),
            ("Grade 4", "primary"),
            ("Grade 5", "primary"),
            ("Grade 6", "primary"),
            ("Grade 7", "jss"),
            ("Grade 8", "jss"),
            ("Grade 9", "jss"),
        ]

        success_count = 0
        failed_classes = []

        for class_name, grade_type in class_types:
            try:
                # Always get current marks from the marks table (don't skip if previous exists)
                table_name = self.get_table_name_for_grade(grade_type)
                summary_data = json.dumps(
                    {
                        "total_students": 0,
                        "distribution": {},
                        "gender_counts": {},
                        "gender_totals": {},
                        "subject_averages": [],
                        "has_history": False,
                        "trend_text": "First Exam",
                    }
                )

                # Save to previous_exams table using the OLD exam title (not the new one)
                old_exam_title = old_exam_titles.get(grade_type, "")
                if old_exam_title:  # Only save if there was an old exam title
                    exam_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    streams = self.db.get_class_streams(class_name)
                    archive_streams = [*streams, "None"] if streams else [None]
                    for stream in archive_streams:
                        history_class = f"{class_name} [{stream}]" if stream and stream != "None" else class_name
                        marks_data = self.get_current_marks_for_class(
                            class_name, table_name, grade_type,
                            stream=stream if streams else None,
                        )
                        self.db.cursor().execute(
                            "INSERT OR REPLACE INTO previous_exams (exam_name, class_name, exam_date, marks_data, summary_data) VALUES (?, ?, ?, ?, ?)",
                            (
                                old_exam_title,
                                history_class,
                                exam_date,
                                marks_data,
                                summary_data,
                            ),
                        )
                    self.db.conn.commit()

                # Clear current marks table for this class to start fresh with new exam
                try:
                    # Get admission numbers for students in this class
                    self.db.cursor().execute(
                        "SELECT adm_no FROM students WHERE grade = ?", (class_name,)
                    )
                    adm_nos = [row[0] for row in self.db.cursor().fetchall()]

                    # Delete marks for these students
                    for adm_no in adm_nos:
                        self.db.cursor().execute(
                            f"DELETE FROM {table_name} WHERE adm_no = ?", (adm_no,)
                        )
                    self.db.conn.commit()
                except Exception as e:
                    print(f"Error clearing marks for {class_name}: {e}")

                success_count += 1

            except Exception as e:
                failed_classes.append(f"{class_name}: {str(e)}")
                print(f"Error creating exam for {class_name}: {e}")

        # Show result
        if success_count > 0:
            message = f"Successfully created new exam '{exam_title}' for {success_count} classes.\nExam titles have been updated in school configuration."
            if failed_classes:
                message += f"\n\nFailed for:\n" + "\n".join(failed_classes[:5])
                if len(failed_classes) > 5:
                    message += f"\n... and {len(failed_classes) - 5} more"
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror(
                "Error",
                f"Failed to create exam for all classes:\n" + "\n".join(failed_classes),
            )

    def get_table_name_for_grade(self, grade_type):
        """Get the table name for a given grade type"""
        table_mapping = {
            "playgroup": "playgroup_marks",
            "pp1": "pp1_marks",
            "pp2": "pp2_marks",
            "lower": "lower_marks",
            "primary": "primary_marks",
            "jss": "marksheet",
        }
        return table_mapping.get(grade_type, "marksheet")

    def get_current_marks_for_class(self, class_name, table_name, grade_type, stream=None):
        """Get current marks data for a class"""
        import json

        try:
            # Get subjects for this grade type
            school_config = self.load_school_config()
            subjects = school_config.get("subjects", {}).get(grade_type, [])

            if not subjects:
                # Default subjects if not in config
                default_subjects = {
                    "playgroup": ["MATH", "CREAT", "ENV"],
                    "pp1": ["MATH", "ENV", "PSYCH", "REL"],
                    "pp2": ["MATH", "ENV", "PSYCH", "REL"],
                    "lower": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
                    "primary": [
                        "ENG",
                        "KISW",
                        "MATH",
                        "SCIE",
                        "AGRI",
                        "SST",
                        "CRE",
                        "C/A",
                        "PHE",
                    ],
                    "jss": [
                        "MATH",
                        "ENG",
                        "KISW",
                        "INT SCIE",
                        "PRE-TECH",
                        "SST",
                        "CRE",
                        "AGRI",
                        "C/A",
                    ],
                }
                subjects = default_subjects.get(grade_type, [])

            # Build query - different structure for junior (marksheet table)
            if table_name == "marksheet":
                select_cols = ["s.name"]
                for subject in subjects:
                    clean = (
                        subject.strip()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace("/", "_")
                        .lower()
                    )
                    select_cols.append(f"m.{clean}_s")
                    select_cols.append(f"m.{clean}_r")
                    select_cols.append(f"m.{clean}_p")
                select_cols.append("m.total_points")
                select_cols.append("m.average_points")
                select_cols.append("m.rank")
            else:
                select_cols = ["s.name"]
                for subject in subjects:
                    clean = (
                        subject.strip()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace("/", "_")
                        .lower()
                    )
                    select_cols.append(f"m.{clean}_s")
                    select_cols.append(f"m.{clean}_r")
                select_cols.append("m.total_points")
                select_cols.append("m.average_level")

            col_str = ", ".join(select_cols)
            query = f"SELECT {col_str} FROM students s LEFT JOIN {table_name} m ON s.adm_no = m.adm_no WHERE UPPER(s.grade) = UPPER(?)"
            params = [class_name]
            if stream == "None":
                query += " AND (s.stream IS NULL OR TRIM(s.stream) = '' OR UPPER(s.stream) = 'NONE')"
            elif stream:
                query += " AND UPPER(TRIM(s.stream)) = UPPER(?)"
                params.append(stream)
            self.db.cursor().execute(query, params)
            rows = self.db.cursor().fetchall()

            # Convert to JSON
            records = []
            for row in rows:
                record = list(row)
                records.append(record)

            return json.dumps(records)

        except Exception as e:
            print(f"Error getting current marks for {class_name}: {e}")
            return json.dumps([])

    def load_school_config(self):
        """Load school configuration from JSON"""
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    return json.load(f)
            else:
                # If config doesn't exist in USER_DATA_DIR, copy from bundled location
                bundled_config = os.path.join(self.BASE_DIR, "school_config.json")
                if os.path.exists(bundled_config):
                    import shutil

                    shutil.copy2(bundled_config, json_path)
                    with open(json_path, "r") as f:
                        return json.load(f)
        except Exception:
            pass
        return {}

    def load_mpesa_config(self):
        """Load M-Pesa configuration from separate config file"""
        try:
            json_path = os.path.join(self.USER_DATA_DIR, "mpesa_config.json")

            # First check if config exists in user data directory
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    return json.load(f)

            # If not in user data directory, check bundled location (for executable)
            bundled_config = os.path.join(self.BASE_DIR, "mpesa_config.json")
            if os.path.exists(bundled_config):
                # Copy bundled config to user data directory
                import shutil

                shutil.copy2(bundled_config, json_path)
                with open(json_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def check_pending_alerts_on_startup(self):
        """Check for pending alerts older than 3 days on startup"""
        try:
            # First, try to send all pending alerts
            self.send_pending_alerts()

            # Then check if there are still pending alerts older than 3 days
            pending_alerts = self.db.get_pending_alerts(
                max_age_hours=72
            )  # 3 days = 72 hours

            if pending_alerts:
                # Alerts are older than 3 days and still pending - block system
                self.show_alert_blocking_message(pending_alerts)

        except Exception as e:
            print(f"Error checking pending alerts: {e}")

    def send_pending_alerts(self):
        """Send all pending alerts that haven't been sent yet"""
        try:
            from notification_service import NotificationService

            notification_service = NotificationService()

            # Get all pending alerts (not just old ones)
            pending_alerts = self.db.get_all_pending_alerts()

            for alert in pending_alerts:
                alert_id = alert[0]
                alert_type = alert[1]
                message = alert[2]

                # Try to send the alert
                results = notification_service.send_alert(message)

                # Check if any alert was sent successfully
                sent_successfully = any(result[1] for result in results)

                if sent_successfully:
                    self.db.mark_alert_sent(alert_id)
                    print(f"Alert {alert_id} sent successfully")
                else:
                    print(f"Failed to send alert {alert_id}: {results}")

        except Exception as e:
            print(f"Error sending pending alerts: {e}")

    def show_alert_blocking_message(self, pending_alerts):
        """Show blocking message when alerts are older than 3 days"""
        # Disable all buttons
        self.disable_system_buttons()

        # Create blocking message frame
        if hasattr(self, "alert_blocking_frame") and self.alert_blocking_frame:
            return

        self.alert_blocking_frame = ctk.CTkFrame(
            self, fg_color="#8b0000", corner_radius=10
        )
        self.alert_blocking_frame.place(
            relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.4
        )
        self.alert_blocking_frame.lift()

        ctk.CTkLabel(
            self.alert_blocking_frame,
            text="⚠️ SYSTEM BLOCKED - ALERTS NOT SENT",
            font=("Arial Bold", 20),
            text_color="white",
        ).pack(pady=20)

        ctk.CTkLabel(
            self.alert_blocking_frame,
            text=f"{len(pending_alerts)} alert(s) have been pending for more than 3 days.\n\nPlease connect to the internet and restart the system.\nIf the problem persists, contact the developer.",
            font=("Arial", 14),
            text_color="white",
            wraplength=400,
        ).pack(pady=10)

        ctk.CTkButton(
            self.alert_blocking_frame,
            text="🔄 Retry Connection",
            fg_color="#10b981",
            text_color="black",
            font=("Arial Bold", 14),
            height=40,
            command=self.retry_alert_connection,
        ).pack(pady=20)

    def retry_alert_connection(self):
        """Retry sending alerts when user clicks retry"""
        try:
            # Try to send pending alerts
            self.send_pending_alerts()

            # Check if there are still old alerts
            pending_alerts = self.db.get_pending_alerts(max_age_hours=72)  # 3 days

            if not pending_alerts:
                # All alerts sent - unblock system
                if hasattr(self, "alert_blocking_frame") and self.alert_blocking_frame:
                    self.alert_blocking_frame.destroy()
                    self.alert_blocking_frame = None
                self.enable_system_buttons()
                messagebox.showinfo(
                    "Success", "All alerts have been sent successfully!"
                )
            else:
                messagebox.showerror(
                    "Still Blocked",
                    "Some alerts still cannot be sent. Please check your internet connection.",
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to send alerts: {e}")

    def check_for_updates_on_startup(self):
        """Check for updates in background on startup"""

        def check_updates():
            try:
                from update_manager import UpdateManager

                update_manager = UpdateManager()
                has_update, update_info = update_manager.check_for_updates()

                print(
                    f"Update check result: has_update={has_update}, info={update_info}"
                )

                if has_update:
                    # Show update button
                    self.after(0, self.show_update_button)
                    print("Update button should appear")
                else:
                    # Hide update button
                    self.after(0, self.hide_update_button)
                    print("No update available")

            except Exception as e:
                print(f"Error checking for updates on startup: {e}")

        # Run in background thread to not block startup
        import threading

        thread = threading.Thread(target=check_updates)
        thread.daemon = True
        thread.start()

    def show_update_button(self):
        """Show the update button when updates are available"""
        if (
            hasattr(self, "btn_check_updates")
            and self.btn_check_updates.winfo_exists()
            and not self.btn_check_updates.winfo_ismapped()
        ):
            self.btn_check_updates.place(
                relx=1, rely=0, anchor="ne", x=-12, y=160
            )
            self.btn_check_updates.lift()

    def hide_update_button(self):
        """Hide the update button when no updates are available"""
        if (
            hasattr(self, "btn_check_updates")
            and self.btn_check_updates.winfo_exists()
            and self.btn_check_updates.winfo_ismapped()
        ):
            self.btn_check_updates.place_forget()

    def check_for_updates(self):
        """Check for system updates (manual check)"""
        try:
            from update_manager import UpdateManager

            update_manager = UpdateManager()
            has_update, update_info = update_manager.check_for_updates()

            if has_update:
                # Show update available dialog
                self.show_update_dialog(update_info)
            else:
                messagebox.showinfo("Update Check", update_info)

        except Exception as e:
            messagebox.showerror(
                "Update Error", f"Error checking for updates: {str(e)}"
            )

    def show_update_dialog(self, update_info):
        """Show update available dialog"""
        # Create update dialog
        update_dialog = ctk.CTkToplevel(self)
        update_dialog.title("Update Available")
        update_dialog.geometry("500x450")

        ctk.CTkLabel(
            update_dialog,
            text="🔄 Update Available",
            font=("Arial Bold", 18),
            text_color="#10b981",
        ).pack(pady=20)

        ctk.CTkLabel(
            update_dialog,
            text=f"Current Version: {update_info['current_version']}",
            font=("Arial", 12),
        ).pack(pady=5)

        ctk.CTkLabel(
            update_dialog,
            text=f"New Version: {update_info['new_version']}",
            font=("Arial Bold", 14),
            text_color="#10b981",
        ).pack(pady=5)

        ctk.CTkLabel(update_dialog, text="Changelog:", font=("Arial Bold", 12)).pack(
            pady=(10, 5)
        )

        ctk.CTkLabel(
            update_dialog,
            text=update_info.get("changelog", "No changelog available"),
            font=("Arial", 10),
            wraplength=450,
        ).pack(pady=5)

        # Check if download URL is available
        has_download_url = bool(update_info.get("download_url")) and update_info[
            "download_url"
        ].endswith(".zip")

        if not has_download_url:
            ctk.CTkLabel(
                update_dialog,
                text="⚠️ Update package not yet available.\nContact developer for manual update.",
                font=("Arial", 11),
                text_color="#f39c12",
                wraplength=450,
            ).pack(pady=10)

        def download_and_install():
            try:
                from update_manager import UpdateManager

                update_manager = UpdateManager()

                # Show progress
                progress_label = ctk.CTkLabel(
                    update_dialog, text="Downloading update..."
                )
                progress_label.pack(pady=10)

                progress_bar = ctk.CTkProgressBar(update_dialog, width=400)
                progress_bar.pack(pady=5)
                progress_bar.set(0)

                def progress_callback(percent):
                    progress_bar.set(percent / 100)
                    update_dialog.update()

                success, result = update_manager.download_update(
                    update_info["download_url"], progress_callback
                )

                if success:
                    progress_label.configure(text="Installing update...")
                    update_dialog.update()

                    success, result = update_manager.install_update(result)

                    if success:
                        messagebox.showinfo(
                            "Success",
                            "Update installed successfully! Please restart the application.",
                        )
                        update_dialog.destroy()
                    else:
                        messagebox.showerror(
                            "Error", f"Failed to install update: {result}"
                        )
                        progress_label.configure(text="Installation failed")
                else:
                    messagebox.showerror(
                        "Error", f"Failed to download update: {result}"
                    )
                    progress_label.configure(text="Download failed")

            except Exception as e:
                messagebox.showerror("Error", f"Error during update: {str(e)}")

        if has_download_url:
            ctk.CTkButton(
                update_dialog,
                text="Download and Install",
                fg_color="#10b981",
                hover_color="#059669",
                height=40,
                font=("Arial Bold", 12),
                command=download_and_install,
            ).pack(pady=20)
        else:
            ctk.CTkButton(
                update_dialog,
                text="Close",
                fg_color="#3498db",
                hover_color="#2980b9",
                height=40,
                font=("Arial Bold", 12),
                command=update_dialog.destroy,
            ).pack(pady=20)

        ctk.CTkButton(
            update_dialog,
            text="Cancel",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=35,
            font=("Arial Bold", 12),
            command=update_dialog.destroy,
        ).pack(pady=5)

    def update_countdown_timer(self):
        """Update countdown timer with color coding"""
        try:
            # Check if countdown_label still exists
            if (
                not hasattr(self, "countdown_label")
                or not self.countdown_label.winfo_exists()
            ):
                return

            license_status = self.db.get_license_status()
            config = self.load_school_config()

            if not license_status:
                # No license status yet - show grace period countdown
                # Calculate days from installation
                self.countdown_label.configure(
                    text="⏳ Setup Required", text_color="#f39c12"
                )
                return

            end_date_str = license_status[3]  # end_date is at index 3
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
            current_date = datetime.now()

            # Calculate remaining time
            time_remaining = end_date - current_date
            remaining_days = time_remaining.days

            # Check if license has expired (end_date is in the past)
            if time_remaining.total_seconds() <= 0:
                # System closed - initialize payment settings
                self.countdown_label.configure(
                    text="⚠️ SYSTEM CLOSED", text_color="#e74c3c"
                )
                self.disable_system_buttons()
                self.show_payment_message()
                
                # Initialize payment settings with default values if not already set
                payment_settings = self.db.get_payment_settings()
                if not payment_settings:
                    self.db.save_payment_settings(
                        full_payment_amount=2500,
                        payment_percentage=70.0,
                        payment_option='partial',
                        system_locked=1
                    )
            else:
                # Update countdown with color coding
                if remaining_days > 10:
                    color = "#10b981"  # Green
                elif remaining_days > 5:
                    color = "#f39c12"  # Orange
                else:
                    color = "#e74c3c"  # Red

                self.countdown_label.configure(
                    text=f"⏳ {remaining_days} days", text_color=color
                )
                self.enable_system_buttons()
                self.hide_payment_message()

        except Exception as e:
            print(f"Error updating countdown timer: {e}")
            # Only try to configure if label exists
            if hasattr(self, "countdown_label") and self.countdown_label.winfo_exists():
                self.countdown_label.configure(text="⏳ -- days", text_color="#10b981")

        # Update every minute
        self.after(60000, self.update_countdown_timer)

    def disable_system_buttons(self):
        """Disable all buttons except exit"""
        buttons_to_disable = [
            "btn_performance_dashboard",
            "btn_competency_gradebook",
            "btn_create_exam",
            "btn_register",
            "btn_mark_sheets",
            "btn_summary",
            "btn_teachers",
            "btn_report_forms",
            "btn_newsletter",
            "btn_portal",
            "btn_cloud_sync",
            "period_button",
            "btn_system_settings",
            "btn_check_updates",
        ]
        for btn_name in buttons_to_disable:
            try:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    btn.configure(state="disabled")
            except:
                pass

    def enable_system_buttons(self):
        """Enable all system buttons"""
        buttons_to_enable = [
            "btn_performance_dashboard",
            "btn_competency_gradebook",
            "btn_create_exam",
            "btn_register",
            "btn_mark_sheets",
            "btn_summary",
            "btn_teachers",
            "btn_report_forms",
            "btn_newsletter",
            "btn_portal",
            "btn_cloud_sync",
            "period_button",
            "btn_system_settings",
            "btn_check_updates",
        ]
        for btn_name in buttons_to_enable:
            try:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    btn.configure(state="normal")
            except:
                pass

    def show_payment_message(self):
        """Show payment message and button when system is closed"""
        # Check if payment message already exists
        if hasattr(self, "payment_message_frame") and self.payment_message_frame:
            return

        # Create payment message frame with higher z-index
        self.payment_message_frame = ctk.CTkFrame(
            self, fg_color="#2c3e50", corner_radius=10
        )
        self.payment_message_frame.place(
            relx=0.5, rely=0.5, anchor="center", relwidth=0.5, relheight=0.4
        )
        self.payment_message_frame.lift()  # Bring to front

        ctk.CTkLabel(
            self.payment_message_frame,
            text="⚠️ SYSTEM CLOSED - PAYMENT REQUIRED",
            font=("Arial Bold", 20),
            text_color="#e74c3c",
        ).pack(pady=20)

        ctk.CTkLabel(
            self.payment_message_frame,
            text="Your license has expired. Please make a payment to continue using the system.",
            font=("Arial", 14),
            text_color="white",
        ).pack(pady=10)

        self.btn_pay_now = ctk.CTkButton(
            self.payment_message_frame,
            text="💳 PAY NOW",
            fg_color="#10b981",
            text_color="black",
            font=("Arial Bold", 16),
            height=50,
            command=self.initiate_payment,
        )
        self.btn_pay_now.pack(pady=20)

    def hide_payment_message(self):
        """Hide payment message when system is open"""
        if hasattr(self, "payment_message_frame") and self.payment_message_frame:
            self.payment_message_frame.destroy()
            self.payment_message_frame = None

    def initiate_payment(self):
        """Initiate M-Pesa payment for license renewal"""
        try:
            config = self.load_school_config()
            mpesa_config = self.load_mpesa_config()
            license_status = self.db.get_license_status()

            # Calculate payment amount based on license type and student count
            total_students = self.db.get_total_students()
            amount_per_student = config.get("amount_per_student", 100)
            payment_amount = total_students * amount_per_student

            if (
                license_status and license_status[5] == 0
            ):  # installation_fee_paid = 0 (index 5)
                # Installation fee payment
                payment_type = "installation_fee"
                amount = config.get("installation_fee", 5000)
                message = f"Installation Fee: KES {amount}"
            else:
                # Termly payment
                payment_type = "termly"
                amount = payment_amount
                message = f"Termly Payment for {total_students} students: KES {amount}"

            # Show payment dialog
            from tkinter import simpledialog

            phone_number = simpledialog.askstring(
                "M-Pesa Payment",
                f"{message}\n\nEnter your M-Pesa phone number (format: 254XXXXXXXXX):",
                parent=self,
            )

            if phone_number:
                # Import M-Pesa service
                try:
                    from mpesa_service import MpesaService, format_phone_number

                    # Get M-Pesa credentials from separate config
                    consumer_key = mpesa_config.get("consumer_key", "")
                    consumer_secret = mpesa_config.get("consumer_secret", "")
                    passkey = mpesa_config.get("passkey", "")
                    shortcode = mpesa_config.get("shortcode", "")
                    environment = mpesa_config.get("environment", "sandbox")

                    if not all([consumer_key, consumer_secret, passkey, shortcode]):
                        messagebox.showerror(
                            "M-Pesa Configuration Error",
                            "M-Pesa credentials not configured. Please configure them in mpesa_config.json",
                        )
                        return

                    # For testing, simulate payment without actual M-Pesa call
                    # In production, you would use ngrok or a public server for callbacks
                    if environment == "sandbox":
                        # Simulate successful payment for testing
                        self.db.save_payment(
                            payment_type=payment_type,
                            amount=amount,
                            status="completed",
                            mpesa_receipt="TEST_"
                            + str(int(datetime.now().timestamp())),
                            transaction_date=datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            result_code=0,
                            result_desc="Success",
                        )

                        # Update license status
                        if payment_type == "installation_fee":
                            license_status = self.db.get_license_status()
                            if license_status:
                                # Extend license by trial period from NOW
                                trial_days = config.get("trial_days", 30)
                                new_end = datetime.now() + timedelta(days=trial_days)
                                self.db.save_license_status(
                                    license_type="trial",
                                    start_date=license_status[2],
                                    end_date=new_end.strftime("%Y-%m-%d %H:%M:%S"),
                                    installation_fee_paid=1,
                                    trial_started=1,
                                    premium_started=license_status[7],
                                )
                        else:
                            # Extend license by premium period from NOW
                            license_status = self.db.get_license_status()
                            if license_status:
                                premium_days = config.get("premium_days", 90)
                                new_end = datetime.now() + timedelta(days=premium_days)
                                self.db.save_license_status(
                                    license_type="premium",
                                    start_date=license_status[2],
                                    end_date=new_end.strftime("%Y-%m-%d %H:%M:%S"),
                                    installation_fee_paid=license_status[5],
                                    trial_started=license_status[6],
                                    premium_started=1,
                                )

                        messagebox.showinfo(
                            "Payment Successful",
                            f"Payment of KES {amount} completed successfully!\n\nSystem will now reopen.",
                        )
                        self.hide_payment_message()
                        self.enable_system_buttons()
                        self.update_countdown_timer()
                        return

                    # Initialize M-Pesa service
                    mpesa = MpesaService(
                        consumer_key=consumer_key,
                        consumer_secret=consumer_secret,
                        passkey=passkey,
                        shortcode=shortcode,
                        environment=environment,
                    )

                    # Format phone number
                    formatted_phone = format_phone_number(phone_number)

                    # For desktop app, we'll use a local callback handler
                    # In production, you'd need a public URL for callbacks
                    callback_url = "http://localhost:5000/mpesa/callback"

                    # Initiate STK Push
                    success, result = mpesa.initiate_stk_push(
                        phone_number=formatted_phone,
                        amount=amount,
                        callback_url=callback_url,
                        account_reference=f"License-{payment_type}",
                        transaction_desc=f"Freeman School Portal - {payment_type}",
                    )

                    if success:
                        # Save payment record with M-Pesa details
                        merchant_request_id = result.get("MerchantRequestID")
                        checkout_request_id = result.get("CheckoutRequestID")
                        response_desc = result.get("ResponseDescription")

                        self.db.save_payment(
                            payment_type=payment_type,
                            amount=amount,
                            merchant_request_id=merchant_request_id,
                            checkout_request_id=checkout_request_id,
                            result_desc=response_desc,
                            status="pending",
                        )

                        messagebox.showinfo(
                            "Payment Initiated",
                            f"STK Push request sent to {formatted_phone}\n\n"
                            f"Merchant Request ID: {merchant_request_id}\n"
                            f"Please check your phone for the M-Pesa prompt.",
                        )
                    else:
                        messagebox.showerror(
                            "Payment Failed",
                            f"Failed to initiate STK Push: {result.get('error', 'Unknown error')}",
                        )

                except ImportError:
                    # M-Pesa service not available - show manual payment option
                    messagebox.showinfo(
                        "Payment Initiated",
                        f"Payment request for KES {amount}\n\n"
                        f"Please make a manual M-Pesa payment to shortcode:\n"
                        f"Account Reference: License-{payment_type}\n\n"
                        f"After payment, contact support to activate your license.",
                    )

                    # Save payment record as manual
                    self.db.save_payment(
                        payment_type=payment_type,
                        amount=amount,
                        status="manual_pending",
                    )

        except Exception as e:
            messagebox.showerror("Payment Error", f"Error initiating payment: {e}")


def show_dashboard(school_name="Freeman Tech Solutions"):
    # This allows you to test just this screen from ui_dashboard.py
    # Change the name here to see the top label update
    dashboard = Dashboard(school_name)
    dashboard.mainloop()


if __name__ == "__main__":
    show_dashboard()
