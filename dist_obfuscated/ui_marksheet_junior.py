import customtkinter as ctk
from tkinter import messagebox
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import sys
import json
from tkinter import filedialog, messagebox
from cloud_service import (
    CloudService,
    ask_cloud_credentials,
    apply_cloud_records_to_table,
)
from debug_console import debug_log


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


def calculate_junior_grade(score):
    """Junior School (CBC) Grading Logic"""
    try:
        score = int(score)
        if score >= 90:
            return "EE1", 8
        elif score >= 75:
            return "EE2", 7
        elif score >= 58:
            return "ME1", 6
        elif score >= 41:
            return "ME2", 5
        elif score >= 31:
            return "AE1", 4
        elif score >= 21:
            return "AE2", 3
        elif score >= 11:
            return "BE1", 2
        else:
            return "BE2", 1
    except ValueError:
        return "", 0


def get_clean_col_name(subject_name):
    """Sanitizes subject names for SQLite compatibility"""
    # Replace anything that isn't a letter or number with an underscore
    clean = "".join(char if char.isalnum() else "_" for char in subject_name)
    return clean.lower().strip("_")


def sync_database_columns(db, subjects):
    db._cursor.execute("PRAGMA table_info(marksheet)")
    existing_cols = [row[1] for row in db._cursor.fetchall()]

    for sub in subjects:
        base = get_clean_col_name(sub)
        for suffix in ["_s", "_r", "_p"]:
            col = f"{base}{suffix}"
            if col not in existing_cols:
                print(f"Adding column: {col}")
                db._cursor.execute(f"ALTER TABLE marksheet ADD COLUMN {col} TEXT")
    db.conn.commit()


class JuniorMarkSheetView(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        db_connection,
        class_name,
        read_only=False,
        exam_name=None,
        marks_data=None,
        summary_data=None,
    ):
        super().__init__(parent, fg_color="transparent")
        self.db = db_connection
        self.class_name = class_name
        self.read_only = read_only
        self.exam_name = exam_name
        self.marks_data = marks_data
        self.summary_data = summary_data

        # Initialize proper paths for executable environment
        self.BASE_DIR, self.USER_DATA_DIR = get_app_dir()

        # FIX: Load subjects from JSON immediately
        self.subjects = self.get_subjects_from_json()
        if self.read_only and self.exam_name:
            self.current_exam_title = self.exam_name
        else:
            self.current_exam_title = "PERFORMANCE RECORD"
            try:
                json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")
                if os.path.exists(json_path):
                    with open(json_path, "r") as f:
                        config = json.load(f)
                        # This line sets the title you wrote last time
                        self.current_exam_title = config.get(
                            "current_exam_title", "PERFORMANCE RECORD"
                        )
            except:
                pass

        self.create_header_section()
        self.create_bottom_controls()

        # Container for both header canvas and content canvas
        self.scroll_container = ctk.CTkFrame(self, fg_color="gray15")
        self.scroll_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Header canvas (horizontal scroll only, fixed at top)
        self.header_canvas = ctk.CTkCanvas(
            self.scroll_container, bg="#242424", highlightthickness=0, height=90
        )
        self.header_canvas.pack(side="top", fill="x")

        # Content canvas (both horizontal and vertical scroll)
        self.canvas = ctk.CTkCanvas(
            self.scroll_container, bg="#242424", highlightthickness=0
        )
        self.h_scroll = ctk.CTkScrollbar(
            self.scroll_container,
            orientation="horizontal",
            command=self._on_horizontal_scroll,
        )
        self.v_scroll = ctk.CTkScrollbar(
            self.scroll_container, orientation="vertical", command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=self._update_h_scroll, yscrollcommand=self.v_scroll.set
        )
        self.header_canvas.configure(xscrollcommand=self._update_h_scroll)
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Create header frame inside header canvas at (0, 0)
        self.header_frame = ctk.CTkFrame(self.header_canvas, fg_color="gray15")
        self.header_canvas.create_window((0, 0), window=self.header_frame, anchor="nw")

        # Table inner frame inside content canvas at (0, 0)
        self.table_inner_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas.create_window((0, 0), window=self.table_inner_frame, anchor="nw")

        # Add mouse wheel bindings for proper scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

        self.load_students_from_registry()

    def _on_horizontal_scroll(self, *args):
        """Sync horizontal scrolling between header and content canvases"""
        self.canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _update_h_scroll(self, first, last):
        """Update horizontal scrollbar position from both canvases"""
        self.h_scroll.set(first, last)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        try:
            if event.num == 4 or event.delta > 0:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                self.canvas.yview_scroll(1, "units")
        except Exception:
            pass

    def _update_scrollregion(self):
        """Update scrollregion ensuring top starts at 0 to prevent gap"""
        try:
            self.canvas.update_idletasks()
            self.header_canvas.update_idletasks()

            # Force the canvas window to stay at (0, 0)
            self.canvas.coords(self.canvas.find_withtag("all")[0], 0, 0)

            # Update content canvas scrollregion
            bbox = self.canvas.bbox("all")
            if bbox:
                content_width = bbox[2]
                content_height = bbox[3]
            else:
                req_width = self.table_inner_frame.winfo_reqwidth()
                req_height = self.table_inner_frame.winfo_reqheight()
                # Ensure minimum height to prevent gap when there's only one student
                min_height = max(req_height, 100)
                content_width = req_width
                content_height = min_height

            # Get header width
            header_bbox = self.header_canvas.bbox("all")
            if header_bbox:
                header_width = header_bbox[2]
            else:
                header_width = self.header_frame.winfo_reqwidth()

            # Use the maximum width to ensure all content is visible
            max_width = max(content_width, header_width)

            self.canvas.configure(scrollregion=(0, 0, max_width, content_height))
            self.canvas.yview_moveto(0)

            # Update header canvas scrollregion (horizontal only)
            # Use the same width as content canvas to ensure synchronization
            if header_bbox:
                self.header_canvas.configure(
                    scrollregion=(0, 0, max_width, header_bbox[3])
                )
            else:
                self.header_canvas.configure(scrollregion=(0, 0, max_width, 90))
        except Exception:
            pass

    def create_header_section(self):
        self.header_label = ctk.CTkLabel(
            self,
            text="Loading School Name...",
            font=("Arial Bold", 22),
            fg_color="#2e7d32",
            text_color="white",
            corner_radius=8,
            height=70,
        )
        self.header_label.pack(fill="x", padx=10, pady=10)

    def create_table_headers(self):
        # Clear existing headers from both frames
        for child in self.header_frame.winfo_children():
            child.destroy()

        # FIXED DIMENSIONS
        NAME_W = 180
        BOX_SIZE = 45
        TOT_W = 65

        # Configure columns on BOTH header_frame and table_inner_frame to keep them synchronized
        self.header_frame.grid_columnconfigure(0, weight=0, minsize=NAME_W)
        self.table_inner_frame.grid_columnconfigure(0, weight=0, minsize=NAME_W)

        # Header: Name (Use width=NAME_W to prevent expansion)
        ctk.CTkLabel(
            self.header_frame,
            text="STUDENT NAME",
            font=("Arial Bold", 12),
            width=NAME_W,
            fg_color="gray25",
            corner_radius=0,
        ).grid(row=0, column=0, rowspan=2, sticky="nsew", padx=1, pady=0)

        for i, sub in enumerate(self.subjects):
            col_start = 1 + (i * 3)
            self.header_frame.grid_columnconfigure(
                (col_start, col_start + 1, col_start + 2),
                weight=0,
                minsize=BOX_SIZE,
                uniform="subs",
            )
            self.table_inner_frame.grid_columnconfigure(
                (col_start, col_start + 1, col_start + 2),
                weight=0,
                minsize=BOX_SIZE,
                uniform="subs",
            )

            # Subject Heading (Locked width)
            display_name = sub.upper()[:6]
            ctk.CTkLabel(
                self.header_frame,
                text=display_name,
                fg_color="gray30",
                corner_radius=0,
                width=BOX_SIZE * 3,
                font=("Arial Bold", 10),
            ).grid(
                row=0,
                column=col_start,
                columnspan=3,
                sticky="nsew",
                padx=1,
                pady=(1, 0),
            )

            # S, R, P Labels
            labels = [("S", "#1a1a1a"), ("R", "#2c3e50"), ("P", "#1e3a24")]
            for j, (txt, color) in enumerate(labels):
                ctk.CTkLabel(
                    self.header_frame,
                    text=txt,
                    fg_color=color,
                    corner_radius=0,
                    width=BOX_SIZE,
                    height=BOX_SIZE,
                    font=("Arial Bold", 10),
                ).grid(row=1, column=col_start + j, sticky="nsew", padx=1, pady=0)

        # Totals
        total_start = 1 + (len(self.subjects) * 3)
        self.header_frame.grid_columnconfigure(
            (total_start, total_start + 1, total_start + 2), weight=0, minsize=TOT_W
        )
        self.table_inner_frame.grid_columnconfigure(
            (total_start, total_start + 1, total_start + 2), weight=0, minsize=TOT_W
        )

        for j, txt in enumerate(["TOT", "AVG", "RANK"]):
            ctk.CTkLabel(
                self.header_frame,
                text=txt,
                font=("Arial Bold", 11),
                width=TOT_W,
                fg_color="gray20",
                corner_radius=0,
            ).grid(
                row=0, column=total_start + j, rowspan=2, sticky="nsew", padx=1, pady=0
            )

    def add_student_row(self, student_data, row_index, read_only=False):
        # Create a frame for this row to hold all widgets
        row_frame = ctk.CTkFrame(self.table_inner_frame, fg_color="transparent")
        # Calculate total columns: name (1) + subjects*3 + totals*3
        total_columns = 1 + (len(self.subjects) * 3) + 3
        # Use sticky="ew" to expand horizontally only; height is determined by content
        row_frame.grid(
            row=row_index,
            column=0,
            columnspan=total_columns,
            sticky="ew",
            padx=0,
            pady=0,
        )

        # Configure this row to NOT expand vertically (weight=0) and set fixed height
        self.table_inner_frame.grid_rowconfigure(row_index, weight=0, minsize=47)

        # Configure columns in the row_frame
        NAME_W = 180
        BOX_SIZE = 45
        TOT_W = 65

        # Column 0: Name label
        row_frame.grid_columnconfigure(0, weight=0, minsize=NAME_W)

        # Subjects: each subject has three columns (score, rating, points)
        num_subjects = len(self.subjects)
        for i in range(num_subjects):
            col_start = 1 + (i * 3)
            row_frame.grid_columnconfigure(col_start, weight=0, minsize=BOX_SIZE)
            row_frame.grid_columnconfigure(col_start + 1, weight=0, minsize=BOX_SIZE)
            row_frame.grid_columnconfigure(col_start + 2, weight=0, minsize=BOX_SIZE)

        # Totals: three columns (total, average, rank)
        total_start = 1 + (num_subjects * 3)
        row_frame.grid_columnconfigure(total_start, weight=0, minsize=TOT_W)
        row_frame.grid_columnconfigure(total_start + 1, weight=0, minsize=TOT_W)
        row_frame.grid_columnconfigure(total_start + 2, weight=0, minsize=TOT_W)

        # 1. Name Label (column 0, row 0 of row_frame)
        ctk.CTkLabel(
            row_frame,
            text=student_data[0],
            anchor="w",
            padx=10,
            width=NAME_W,
            font=("Arial", 12),
            fg_color="transparent",
        ).grid(row=0, column=0, sticky="w", padx=1, pady=0)

        # 2. Subject Entry Boxes (Square)
        for i in range(num_subjects):
            col_start = 1 + (i * 3)
            # Score column (editable or read-only)
            score_col = col_start
            score_entry = ctk.CTkEntry(
                row_frame,
                width=BOX_SIZE,
                height=BOX_SIZE,
                font=("Arial Bold", 12),
                fg_color="#1a1a1a" if not read_only else "gray30",
                border_width=0,
                corner_radius=0,
                justify="center",
            )
            score_entry.grid(row=0, column=score_col, sticky="ew", padx=1, pady=0)
            if len(student_data) > score_col and student_data[score_col] is not None:
                score_entry.insert(0, str(student_data[score_col]))
            if read_only:
                score_entry.configure(state="disabled")
            else:
                # Bind focusout to auto_fill_results, passing the row_frame
                score_entry.bind(
                    "<FocusOut>",
                    lambda event, ent=score_entry, col=score_col, r_frame=row_frame: self.auto_fill_results(
                        ent, col, r_frame
                    ),
                )

            # Rating column (disabled)
            rating_col = col_start + 1
            rating_entry = ctk.CTkEntry(
                row_frame,
                width=BOX_SIZE,
                height=BOX_SIZE,
                font=("Arial Bold", 12),
                fg_color="#2c3e50",
                border_width=0,
                corner_radius=0,
                justify="center",
            )
            rating_entry.grid(row=0, column=rating_col, sticky="ew", padx=1, pady=0)
            if len(student_data) > rating_col and student_data[rating_col] is not None:
                rating_entry.insert(0, str(student_data[rating_col]))
            rating_entry.configure(state="disabled")

            # Points column (disabled)
            points_col = col_start + 2
            points_entry = ctk.CTkEntry(
                row_frame,
                width=BOX_SIZE,
                height=BOX_SIZE,
                font=("Arial Bold", 12),
                fg_color="#1e3a24",
                border_width=0,
                corner_radius=0,
                justify="center",
            )
            points_entry.grid(row=0, column=points_col, sticky="ew", padx=1, pady=0)
            if len(student_data) > points_col and student_data[points_col] is not None:
                points_entry.insert(0, str(student_data[points_col]))
            points_entry.configure(state="disabled")

        # 3. Totals Boxes
        total_start = 1 + (num_subjects * 3)
        summary_colors = ["gray30", "#1f538d", "#4a1515"]
        for j in range(3):
            col_idx = total_start + j
            val = student_data[col_idx] if len(student_data) > col_idx else ""
            box = ctk.CTkEntry(
                row_frame,
                width=65,
                height=BOX_SIZE,
                fg_color=summary_colors[j],
                font=("Arial Bold", 12),
                border_width=0,
                corner_radius=0,
                justify="center",
            )
            box.grid(row=0, column=col_idx, sticky="ew", padx=1, pady=0)
            box.insert(0, str(val))
            box.configure(state="disabled")

    def auto_fill_results(self, score_entry, col, row_frame):
        # 1. Get the score
        score_val = score_entry.get()

        # 2. Calculate the Grade (Remark) and Points
        rating_val, points_val = calculate_junior_grade(score_val)

        # 3. Find the Remark (R) and Point (P) widgets in the same row_frame
        try:
            # Get all widgets in the row_frame
            r_entry = [w for w in row_frame.grid_slaves(row=0, column=col + 1)][0]
            p_entry = [w for w in row_frame.grid_slaves(row=0, column=col + 2)][0]

            # 4. Update the widgets
            for ent, val in [(r_entry, rating_val), (p_entry, str(points_val))]:
                ent.configure(state="normal")
                ent.delete(0, "end")
                ent.insert(0, val)
                ent.configure(state="disabled")

            # 5. Trigger the totals update for this specific row
            # Get the row index from the row_frame's grid info
            row_index = row_frame.grid_info()["row"]
            self.update_totals(row_index)

        except IndexError:
            # This prevents a crash if the grid isn't fully rendered yet
            pass

    def update_totals(self, row_index):
        total_points_sum = 0
        num_subjects = len(self.subjects)

        # Get the row_frame first (it's at column 0, spanning all columns)
        row_frames = self.table_inner_frame.grid_slaves(row=row_index, column=0)
        if not row_frames:
            return
        row_frame = row_frames[0]

        # 1. Sum up the Points (P) columns
        # Points are in columns 3, 6, 9... (multiples of 3)
        for sub_idx in range(1, num_subjects + 1):
            p_col = sub_idx * 3
            try:
                # Look inside the row_frame for the point widget
                widgets = row_frame.grid_slaves(row=0, column=p_col)
                if widgets:
                    val = widgets[0].get()
                    if val.isdigit():
                        total_points_sum += int(val)
            except Exception:
                continue

        # 2. Find the Summary Boxes
        # Total Box is at (subjects * 3) + 1
        total_box_col = (num_subjects * 3) + 1

        try:
            # Update Total Points Box (inside row_frame)
            total_widgets = row_frame.grid_slaves(row=0, column=total_box_col)
            if total_widgets:
                total_box = total_widgets[0]
                total_box.configure(state="normal")
                total_box.delete(0, "end")
                total_box.insert(0, str(total_points_sum))
                total_box.configure(state="disabled")

            # 3. Calculate Average Grade using dynamic thresholds based on number of subjects
            # Scale thresholds: EE1=90% of max points, EE2=75%, ME1=58%, ME2=41%, AE1=31%, AE2=21%, BE1=11%
            max_points_per_subject = 8  # Maximum points per subject (EE1)
            max_total_points = num_subjects * max_points_per_subject

            if max_total_points > 0:
                # Calculate thresholds dynamically based on percentage of maximum possible points
                thresholds = [
                    (int(max_total_points * 0.90), "EE1"),  # 90% or higher
                    (int(max_total_points * 0.75), "EE2"),  # 75% or higher
                    (int(max_total_points * 0.58), "ME1"),  # 58% or higher
                    (int(max_total_points * 0.41), "ME2"),  # 41% or higher
                    (int(max_total_points * 0.31), "AE1"),  # 31% or higher
                    (int(max_total_points * 0.21), "AE2"),  # 21% or higher
                    (int(max_total_points * 0.11), "BE1"),  # 11% or higher
                ]
                avg_grade = next(
                    (g for t, g in thresholds if total_points_sum >= t), "BE2"
                )
            else:
                avg_grade = "BE2"

            # Update Average Level Box (inside row_frame)
            avg_widgets = row_frame.grid_slaves(row=0, column=total_box_col + 1)
            if avg_widgets:
                avg_box = avg_widgets[0]
                avg_box.configure(state="normal")
                avg_box.delete(0, "end")
                avg_box.insert(0, avg_grade)
                avg_box.configure(state="disabled")

        except Exception as e:
            print(f"Error updating totals: {e}")

    def load_students_from_registry(self):
        self.update_header_text(self.current_exam_title)
        self.subjects = self.get_subjects_from_json()
        sync_database_columns(self.db, self.subjects)

        try:
            # If in read-only mode with marks_data, load from JSON data instead of database
            if self.read_only and self.marks_data:
                import json

                records = json.loads(self.marks_data)
            else:
                subject_cols = []
                for sub in self.subjects:
                    base = get_clean_col_name(sub)
                    subject_cols.append(f"m.{base}_s")
                    subject_cols.append(f"m.{base}_r")
                    subject_cols.append(f"m.{base}_p")

                cols_string = ", ".join(subject_cols)

                # The query remains the same (Correctly sorts by Rank)
                query = (
                    f"SELECT s.name, {cols_string}, m.total_points, m.average_points, m.rank "
                    f"FROM students s LEFT JOIN marksheet m ON s.adm_no = m.adm_no "
                    f"WHERE UPPER(s.grade) = UPPER(?) "
                    f"ORDER BY CASE WHEN m.rank IS NULL THEN 1 ELSE 0 END, m.rank ASC"
                )

                self.db.cursor().execute(query, (self.class_name,))
                records = self.db.cursor().fetchall()
                print(
                    f"DEBUG: Loaded {len(records)} students for grade '{self.class_name}' from database"
                )

            # 1. Clear the UI
            for child in self.table_inner_frame.winfo_children():
                child.destroy()

            # 2. Build the Headers (in separate header_frame, not in scrollable area)
            self.create_table_headers()

            # 3. Add Student Rows (Starting from Row 0 in table_inner_frame, since headers are separate)
            # 'idx' will tell 'add_student_row' exactly where to sit vertically
            for idx, student in enumerate(records, start=0):
                self.add_student_row(student, idx, read_only=self.read_only)

            # Update scrollregion after all rows are added
            self.canvas.after(100, lambda: self._update_scrollregion())

        except Exception as e:
            print(f"Dynamic Load Error: {e}")

    def create_bottom_controls(self):
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_bar.pack(fill="x", side="bottom", padx=20, pady=10)

        if self.read_only:
            # Read-only mode: only Print and View Summary buttons
            ctk.CTkButton(
                self.bottom_bar,
                text="🖨 Print PDF",
                fg_color="#f57c00",
                text_color="black",
                command=self.print_to_pdf,
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                self.bottom_bar,
                text="📊 View Summary",
                fg_color="#1f538d",
                command=self.view_summary,
            ).pack(side="left", padx=5)
        else:
            # Normal mode: all editing buttons
            ctk.CTkButton(
                self.bottom_bar,
                text="💾 Save Marks",
                fg_color="#2e7d32",
                width=120,
                command=self.save_all_marks,
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                self.bottom_bar,
                text="☁ Fetch from Cloud",
                fg_color="#1f538d",
                hover_color="#153d66",
                command=self.fetch_cloud_data,
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                self.bottom_bar,
                text="🖨 Print PDF",
                fg_color="#f57c00",
                text_color="black",
                command=self.print_to_pdf,
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                self.bottom_bar,
                text="🆕 New Exam",
                fg_color="#e67e22",
                command=self.create_new_exam,
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                self.bottom_bar,
                text="🔄 Refresh",
                fg_color="#34495e",
                command=self.load_students_from_registry,
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.bottom_bar,
            text="⬅ Back",
            fg_color="#942727",
            command=self.master.master.return_to_home,
        ).pack(side="right", padx=5)

    def fetch_cloud_data(self):
        # 1. Get login details
        credentials = ask_cloud_credentials(self)
        if not credentials:
            return

        service = CloudService()

        # 2. Call the cloud API
        # Ensure this method in cloud_service.py uses the '/api/get_marks' endpoint
        result = service.fetch_marks(self.class_name, credentials)

        # DEBUG: Print the full result
        print(f"DEBUG JUNIOR: Cloud fetch result: {result}")

        # 3. Handle the response
        if result.get("success"):
            # The cloud sends data in the "marks" key
            marks_data = result.get("marks", [])
            print(f"DEBUG JUNIOR: Marks data received: {len(marks_data)} records")
            if marks_data:
                print(f"DEBUG JUNIOR: First record sample: {marks_data[0]}")

            if not marks_data:
                messagebox.showinfo(
                    "Cloud Fetch", "No marks found on the cloud for this class."
                )
                return

            # Get subjects to align columns correctly
            subjects = self.get_subjects_from_json()
            print(f"DEBUG JUNIOR: Subjects: {subjects}")

            # 4. Fill the table (Junior uses 3 columns per subject)
            apply_cloud_records_to_table(
                self.table_inner_frame, marks_data, subjects, columns_per_subject=3
            )
            self.update_idletasks()

            # 5. Save the fetched marks to database (skip reload to preserve cloud values)
            self.save_all_marks(skip_reload=True)

            # 6. Consume marks from cloud (delete them after successful fetch)
            service.consume_marks(self.class_name, credentials)

            # 7. Success Message
            messagebox.showinfo(
                "Cloud Fetch",
                f"Successfully synchronized {len(marks_data)} student records. Marks have been removed from cloud.",
            )

        else:
            # If result['success'] is False
            print(f"DEBUG JUNIOR: Cloud fetch failed: {result.get('message')}")
            messagebox.showerror(
                "Cloud Fetch Failed",
                result.get("message", "Could not fetch cloud marks."),
            )

    def get_subjects_from_json(self):
        default_subjects = [
            "ENG",
            "KISW",
            "MATHS",
            "INT SCIE",
            "AGRI",
            "SST",
            "CRE",
            "C/A",
            "PRE-TECH",
        ]

        # Use USER_DATA_DIR for config file (works in both script and executable)
        json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")

        try:
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config = json.load(f)
                    # Use the nested structure we found earlier
                    subjects_dict = config.get("subjects", {})
                    return subjects_dict.get("jss", default_subjects)
            return default_subjects
        except Exception as e:
            return default_subjects

    def print_to_pdf(self):
        from fpdf import FPDF
        import os

        # 1. Use USER_DATA_DIR for config file (works in both script and executable)
        json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")

        # 2. Fetch Dynamic Data from JSON (Priority)
        school_name = "MY SCHOOL"
        logo_path = None
        subjects = self.get_subjects_from_json()

        try:
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config = json.load(f)
                    school_name = config.get("school_name", "MY SCHOOL")
                    logo_path = config.get("logo")
        except Exception as e:
            print(f"PDF JSON Load Error: {e}")

        num_subs = len(subjects)
        exam_name = getattr(self, "current_exam_title", "PERFORMANCE RECORD")

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"{self.class_name}_{exam_name.replace(' ', '_')}.pdf",
        )
        if not file_path:
            return

        try:
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.add_page()

            # --- 3. HEADER: Logo & School Name ---
            if logo_path and os.path.exists(logo_path):
                try:
                    pdf.image(logo_path, 10, 8, 25)
                except:
                    print("Could not embed logo image.")

            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 10, txt=school_name.upper(), border=0, ln=1, align="C")
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(
                0,
                7,
                txt=f"JUNIOR SCHOOL REPORT: {self.class_name.upper()} - {exam_name}",
                border=0,
                ln=1,
                align="C",
            )
            pdf.ln(10)

            # --- 4. Table Column Math ---
            name_w = 40
            totals_section_w = 35
            usable_w = 277 - name_w - totals_section_w
            sub_col_w = usable_w / max(1, (num_subs * 3))

            # --- 5. Main Table Headers ---
            pdf.set_fill_color(30, 80, 40)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)

            pdf.cell(
                name_w, 12, txt="STUDENT NAME", border=1, ln=0, align="C", fill=True
            )
            for sub in subjects:
                pdf.cell(
                    sub_col_w * 3, 6, txt=sub[:8], border=1, ln=0, align="C", fill=True
                )

            pdf.cell(10, 12, txt="TOT", border=1, ln=0, align="C", fill=True)
            pdf.cell(15, 12, txt="AVG", border=1, ln=0, align="C", fill=True)
            pdf.cell(10, 12, txt="POS", border=1, ln=1, align="C", fill=True)

            # S | R | P Row logic
            current_y = pdf.get_y()
            pdf.set_xy(10 + name_w, current_y - 6)
            pdf.set_font("Helvetica", "B", 6)
            for _ in subjects:
                pdf.cell(sub_col_w, 6, txt="S", border=1, ln=0, align="C", fill=True)
                pdf.cell(sub_col_w, 6, txt="R", border=1, ln=0, align="C", fill=True)
                pdf.cell(sub_col_w, 6, txt="P", border=1, ln=0, align="C", fill=True)
            pdf.set_y(current_y)

            # --- 6. DATA ROWS ---
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=7)

            all_widgets = self.table_inner_frame.grid_slaves()
            if not all_widgets:
                return
            max_grid_row = max(w.grid_info()["row"] for w in all_widgets)

            for r in range(2, max_grid_row + 1):
                try:
                    name_widgets = self.table_inner_frame.grid_slaves(row=r, column=0)
                    if not name_widgets:
                        continue
                    # The name is in a CTkLabel inside the row_frame
                    row_frame = name_widgets[0]
                    label_widgets = row_frame.grid_slaves(row=0, column=0)
                    if not label_widgets:
                        continue
                    name_text = label_widgets[0].cget("text")

                    if not name_text or name_text.upper() == "STUDENT NAME":
                        continue

                    pdf.cell(name_w, 7, txt=name_text[:22], border=1)

                    for i in range(1, (num_subs * 3) + 1):
                        cell_widgets = row_frame.grid_slaves(row=0, column=i)
                        val = (
                            cell_widgets[0].get()
                            if cell_widgets and hasattr(cell_widgets[0], "get")
                            else ""
                        )
                        pdf.cell(sub_col_w, 7, txt=str(val), border=1, ln=0, align="C")

                    total_col_idx = (num_subs * 3) + 1
                    for j in range(3):
                        t_widgets = row_frame.grid_slaves(
                            row=0, column=total_col_idx + j
                        )
                        t_val = (
                            t_widgets[0].get()
                            if t_widgets and hasattr(t_widgets[0], "get")
                            else ""
                        )
                        w_val = 15 if j == 1 else 10
                        ln_val = 1 if j == 2 else 0
                        pdf.cell(
                            w_val, 7, txt=str(t_val), border=1, ln=ln_val, align="C"
                        )

                except Exception as row_err:
                    print(f"Skipping PDF row {r}: {row_err}")

            pdf.output(file_path)
            messagebox.showinfo("Success", "PDF generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"PDF Generation Failed: {e}")

    def save_all_marks(self, skip_reload=False):
        # Force focus away from any entry widget to commit values
        self.table_inner_frame.focus_set()

        debug_log("DEBUG: save_all_marks called")
        success_count = 0
        subjects = self.get_subjects_from_json()
        num_subs = len(subjects)
        debug_log(f"DEBUG: Found {num_subs} subjects: {subjects}")

        # 1. Get all row indices currently in the grid
        # Junior marksheet has headers in separate header_frame, student rows start from row 0
        all_widgets = self.table_inner_frame.grid_slaves()
        debug_log(f"DEBUG: Found {len(all_widgets)} total widgets in table_inner_frame")
        if not all_widgets:
            debug_log("DEBUG: No widgets found, returning")
            return

        # Find the highest row index to know how many students we have
        max_row = max(w.grid_info()["row"] for w in all_widgets)
        debug_log(f"DEBUG: Max row index: {max_row}")

        for r in range(0, max_row + 1):
            try:
                debug_log(f"DEBUG: Processing row {r}")
                # 2. Find the Student Name Label in this row
                row_frames = self.table_inner_frame.grid_slaves(row=r, column=0)
                debug_log(f"DEBUG: Row {r} column 0 has {len(row_frames)} frames")
                if not row_frames:
                    debug_log(f"DEBUG: No row frames found for row {r}")
                    continue

                # Junior marksheet uses row_frame structure - get name label from inside the frame
                row_frame = row_frames[0]
                if hasattr(row_frame, "winfo_children"):
                    # Get the name label at column 0 inside the row_frame
                    name_widgets = row_frame.grid_slaves(row=0, column=0)
                    print(f"DEBUG: Row {r} has {len(name_widgets)} name widgets")
                    if not name_widgets:
                        debug_log(f"DEBUG: No name widgets found for row {r}")
                        continue
                    student_name = name_widgets[0].cget("text")
                    debug_log(f"DEBUG: Student name: {student_name}")
                else:
                    print(f"DEBUG: Row frame has no winfo_children")
                    continue

                # 3. Get Admission Number from database
                self.db.cursor().execute(
                    "SELECT adm_no FROM students WHERE name = ?", (student_name,)
                )
                result = self.db.cursor().fetchone()
                if not result:
                    debug_log(f"DEBUG: No adm_no found for student {student_name}")
                    continue
                adm_no = result[0]
                debug_log(f"DEBUG: adm_no: {adm_no}")

                # 4. Collect Marks for each subject
                update_parts = []
                values = []
                # Replace the manual logic in save_all_marks with this:
                for i, sub in enumerate(subjects):
                    col_start = 1 + (i * 3)
                    # CLEANER & SAFER: Use the existing helper function
                    base = get_clean_col_name(sub)
                    debug_log(
                        f"DEBUG: Subject {i}: {sub}, base: {base}, col_start: {col_start}"
                    )

                    # Get values from grid (inside the row_frame)
                    s_widgets = row_frame.grid_slaves(row=0, column=col_start)
                    r_widgets = row_frame.grid_slaves(row=0, column=col_start + 1)
                    p_widgets = row_frame.grid_slaves(row=0, column=col_start + 2)

                    debug_log(
                        f"DEBUG: s_widgets: {len(s_widgets)}, r_widgets: {len(r_widgets)}, p_widgets: {len(p_widgets)}"
                    )

                    s_val = s_widgets[0].get() if s_widgets else "0"
                    debug_log(f"DEBUG: s_val: {s_val}")

                    # Temporarily enable disabled widgets to read their values
                    r_val = "BE2"
                    if r_widgets:
                        orig_state = r_widgets[0].cget("state")
                        r_widgets[0].configure(state="normal")
                        r_val = r_widgets[0].get()
                        r_widgets[0].configure(state=orig_state)
                    debug_log(f"DEBUG: r_val: {r_val}")

                    p_val = "0"
                    if p_widgets:
                        orig_state = p_widgets[0].cget("state")
                        p_widgets[0].configure(state="normal")
                        p_val = p_widgets[0].get()
                        p_widgets[0].configure(state=orig_state)
                    debug_log(f"DEBUG: p_val: {p_val}")

                    update_parts.extend([f"{base}_s=?", f"{base}_r=?", f"{base}_p=?"])
                    values.extend([s_val, r_val, p_val])

                # 5. Get total_points and average_points from UI
                total_start = 1 + (num_subs * 3)
                debug_log(f"DEBUG: total_start: {total_start}")
                total_widgets = row_frame.grid_slaves(row=0, column=total_start)
                avg_widgets = row_frame.grid_slaves(row=0, column=total_start + 1)

                debug_log(
                    f"DEBUG: total_widgets: {len(total_widgets)}, avg_widgets: {len(avg_widgets)}"
                )

                total_val = "0"
                if total_widgets:
                    orig_state = total_widgets[0].cget("state")
                    total_widgets[0].configure(state="normal")
                    total_val = total_widgets[0].get()
                    total_widgets[0].configure(state=orig_state)
                debug_log(f"DEBUG: total_val: {total_val}")

                avg_val = ""
                if avg_widgets:
                    orig_state = avg_widgets[0].cget("state")
                    avg_widgets[0].configure(state="normal")
                    avg_val = avg_widgets[0].get()
                    avg_widgets[0].configure(state=orig_state)
                debug_log(f"DEBUG: avg_val: {avg_val}")

                update_parts.extend(["total_points=?", "average_points=?"])
                values.extend([total_val, avg_val])

                # 6. Execute Update
                values.append(adm_no)
                sql = f"UPDATE marksheet SET {', '.join(update_parts)} WHERE adm_no=?"
                debug_log(f"DEBUG: SQL: {sql}")
                debug_log(f"DEBUG: Values: {values}")

                # Ensure record exists
                self.db.cursor().execute(
                    "SELECT 1 FROM marksheet WHERE adm_no=?", (adm_no,)
                )
                if not self.db.cursor().fetchone():
                    debug_log(
                        f"DEBUG: No existing record for adm_no {adm_no}, inserting"
                    )
                    self.db.cursor().execute(
                        "INSERT INTO marksheet (adm_no) VALUES (?)", (adm_no,)
                    )
                else:
                    debug_log(f"DEBUG: Existing record found for adm_no {adm_no}")

                self.db.cursor().execute(sql, values)
                success_count += 1
                debug_log(
                    f"DEBUG: Successfully saved row {r}, success_count: {success_count}"
                )

            except Exception as e:
                debug_log(f"Error saving row {r}: {e}")
                import traceback

                traceback.print_exc()
                continue

        self.db.conn.commit()
        debug_log(f"DEBUG: Committed to database, success_count: {success_count}")
        self.calculate_rankings()
        messagebox.showinfo("Success", f"Saved {success_count} students.")
        if not skip_reload:
            debug_log("DEBUG: Reloading students from registry")
            self.load_students_from_registry()

    def calculate_rankings(self):
        subjects = self.get_subjects_from_json()

        # Use the cleaning function here too!
        point_cols = [f"{get_clean_col_name(s)}_p" for s in subjects]

        # Use COALESCE to treat empty/null marks as 0, otherwise the sum becomes NULL
        sum_query = " + ".join([f"COALESCE({col}, 0)" for col in point_cols])

        self.db.cursor().execute(f"UPDATE marksheet SET total_points = ({sum_query})")

        # Calculate average_points based on total_points
        self.db.cursor().execute(f"""
            UPDATE marksheet 
            SET average_points = CASE 
                WHEN total_points > 0 THEN (
                    CASE 
                        WHEN total_points / {len(subjects)} >= 7.5 THEN 'EE1'
                        WHEN total_points / {len(subjects)} >= 6.5 THEN 'EE2'
                        WHEN total_points / {len(subjects)} >= 5.5 THEN 'ME1'
                        WHEN total_points / {len(subjects)} >= 4.5 THEN 'ME2'
                        WHEN total_points / {len(subjects)} >= 3.5 THEN 'AE1'
                        WHEN total_points / {len(subjects)} >= 2.5 THEN 'AE2'
                        WHEN total_points / {len(subjects)} >= 1.5 THEN 'BE1'
                        ELSE 'BE2'
                    END
                )
                ELSE ''
            END
        """)

        # Get all students for this class sorted by total_points descending
        self.db.cursor().execute(
            """
            SELECT m.adm_no 
            FROM marksheet m
            JOIN students s ON m.adm_no = s.adm_no
            WHERE UPPER(s.grade) = UPPER(?)
            ORDER BY m.total_points DESC
            """,
            (self.class_name,),
        )
        ranked_students = self.db.cursor().fetchall()

        # Update the 'rank' column with their position (starting from 1)
        current_rank = 0
        prev_score = None

        for i, (adm,) in enumerate(ranked_students, start=1):
            # Get the score for this student
            self.db.cursor().execute(
                "SELECT total_points FROM marksheet WHERE adm_no = ?", (adm,)
            )
            result = self.db.cursor().fetchone()
            score = result[0] if result else 0

            # Assign rank (handle ties)
            if score != prev_score:
                current_rank = i
                prev_score = score

            self.db.cursor().execute(
                "UPDATE marksheet SET rank = ? WHERE adm_no = ?", (current_rank, adm)
            )

        self.db.conn.commit()

    def create_new_exam(self):
        dialog = ctk.CTkInputDialog(text="Enter Exam Title:", title="New Exam")
        new_title = dialog.get_input()

        if new_title and messagebox.askyesno(
            "Confirm", f"Reset marks for {self.class_name} and start '{new_title}'?"
        ):
            # 1. Save the current exam as a previous exam with its summary
            self.save_current_exam_as_previous()

            # 2. Clear the marks in the DB
            self.db.cursor().execute(
                "DELETE FROM marksheet WHERE adm_no IN (SELECT adm_no FROM students WHERE UPPER(grade) = UPPER(?))",
                (self.class_name,),
            )
            self.db.conn.commit()

            # 3. Update the variable in the app
            self.current_exam_title = new_title.upper()

            # 4. Save this title to school_config.json permanently
            try:
                import json
                import os

                json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")

                config = {}
                if os.path.exists(json_path):
                    with open(json_path, "r") as f:
                        config = json.load(f)

                # Update the specific key for the exam title
                config["current_exam_title"] = self.current_exam_title

                with open(json_path, "w") as f:
                    json.dump(config, f, indent=4)
            except Exception as e:
                print(f"Error saving exam title to JSON: {e}")

            # 5. Refresh the UI
            self.load_students_from_registry()

    def save_current_exam_as_previous(self):
        """Save the current exam data as a previous exam with summary"""
        import json

        # Get current exam title
        current_exam_name = self.current_exam_title

        # Get marks data
        subject_cols = []
        for sub in self.subjects:
            base = get_clean_col_name(sub)
            subject_cols.append(f"m.{base}_s")
            subject_cols.append(f"m.{base}_r")
            subject_cols.append(f"m.{base}_p")

        cols_string = ", ".join(subject_cols)

        query = (
            f"SELECT s.name, {cols_string}, m.total_points, m.average_points, m.rank "
            f"FROM students s LEFT JOIN marksheet m ON s.adm_no = m.adm_no "
            f"WHERE UPPER(s.grade) = UPPER(?) "
            f"ORDER BY CASE WHEN m.rank IS NULL THEN 1 ELSE 0 END, m.rank ASC"
        )

        self.db.cursor().execute(query, (self.class_name,))
        records = self.db.cursor().fetchall()

        # Convert to JSON-serializable format
        marks_data = json.dumps([list(record) for record in records])

        # Get summary data
        summary_data = self.generate_summary_data()
        summary_json = json.dumps(summary_data)

        # Save to database
        self.db.save_previous_exam(
            current_exam_name, self.class_name, summary_json, marks_data
        )

        print(f"Saved previous exam: {current_exam_name} for {self.class_name}")

    def generate_summary_data(self):
        """Generate summary data for the current exam matching ClassSummaryView format"""
        LEVEL_ORDER = ["EE1", "EE2", "ME1", "ME2", "AE1", "AE2", "BE1", "BE2"]

        # Get subjects from JSON
        subjects = self.get_subjects_from_json()

        # Initialize data structures
        distribution = {level: 0 for level in LEVEL_ORDER}
        gender_counts = {"male": 0, "female": 0, "other": 0}
        gender_totals = {"male": 0, "female": 0, "other": 0}
        subject_totals = {subject: 0.0 for subject in subjects}
        subject_counts = {subject: 0 for subject in subjects}
        total_students = 0

        # Query student data with marks
        query = """
            SELECT s.name, s.gender, m.total_points, m.average_points
            FROM students s
            LEFT JOIN marksheet m ON s.adm_no = m.adm_no
            WHERE UPPER(s.grade) = UPPER(?)
        """
        self.db.cursor().execute(query, (self.class_name,))
        rows = self.db.cursor().fetchall()

        for row in rows:
            if not row:
                continue
            total_students += 1

            name, gender, total_points, average_points = row

            # Map gender values to standard categories
            gender_raw = str(gender).strip().lower() if gender else "other"
            if gender_raw in ["m", "male", "boy"]:
                gender = "male"
            elif gender_raw in ["f", "female", "girl"]:
                gender = "female"
            else:
                gender = "other"

            gender_counts[gender] += 1

            # Track distribution based on average_points
            if average_points is not None:
                average_label = str(average_points).strip().upper().replace(" ", "")
                if average_label in distribution:
                    distribution[average_label] += 1

            # Track gender totals
            if isinstance(total_points, (int, float)):
                gender_totals[gender] += total_points

        # Calculate subject averages
        # For junior marks, we need to get subject scores
        for subject in subjects:
            clean_name = (
                subject.strip()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
                .lower()
            )
            score_col = f"{clean_name}_s"
            points_col = f"{clean_name}_p"

            query = f"""
                SELECT m.{score_col}, m.{points_col}
                FROM marksheet m
                JOIN students s ON m.adm_no = s.adm_no
                WHERE UPPER(s.grade) = UPPER(?)
            """
            self.db.cursor().execute(query, (self.class_name,))
            subject_rows = self.db.cursor().fetchall()

            for score_row in subject_rows:
                score, points = score_row
                # Use points if available, otherwise use score
                value = points if points is not None else score
                if value is not None:
                    try:
                        score_value = float(value)
                        subject_totals[subject] += score_value
                        subject_counts[subject] += 1
                    except (ValueError, TypeError):
                        pass

        # Calculate subject averages
        subject_averages = []
        for subject in subjects:
            count = subject_counts[subject]
            mean_value = round(subject_totals[subject] / count if count else 0.0, 2)
            subject_averages.append((subject, mean_value))

        subject_averages.sort(key=lambda pair: pair[1], reverse=True)

        return {
            "total_students": total_students,
            "distribution": distribution,
            "gender_counts": gender_counts,
            "gender_totals": gender_totals,
            "subject_averages": subject_averages,
            "has_history": False,
            "trend_text": "No previous exam",
        }

    def view_summary(self):
        """View the summary for a previous exam"""
        if self.summary_data:
            # Show the summary in a new window
            self.summary_window = ctk.CTkToplevel(self)
            self.summary_window.title(f"Summary - {self.exam_name}")
            self.summary_window.geometry("900x700")
            self.summary_window.protocol(
                "WM_DELETE_WINDOW", self.on_summary_window_close
            )
            self.summary_window.transient(self)
            self.summary_window.grab_set()

            summary_frame = ctk.CTkScrollableFrame(
                self.summary_window, fg_color="gray15"
            )
            summary_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Parse and display the summary data
            import json

            try:
                summary = json.loads(self.summary_data)

                # Debug: print the summary data
                print(f"Summary data: {summary}")

                # Header
                header = ctk.CTkLabel(
                    summary_frame,
                    text=f"Summary - {self.exam_name}",
                    font=("Arial Bold", 20),
                    fg_color="#1f538d",
                    text_color="white",
                    corner_radius=10,
                    height=60,
                )
                header.pack(fill="x", padx=10, pady=10)

                # Handle both old and new data formats
                # Old format: {'Total Students': 21, 'Students with Marks': 20, 'Average Total Points': 6.35, 'Grade Distribution': {'BE1': 1, 'BE2': 19}}
                # New format: {'total_students': 21, 'gender_counts': {...}, 'distribution': {...}, 'subject_averages': [...], ...}

                # Check if it's the old format
                if "Total Students" in summary or "Students with Marks" in summary:
                    # Old format - display as key-value pairs
                    info_frame = ctk.CTkFrame(
                        summary_frame, fg_color="#20232a", corner_radius=12
                    )
                    info_frame.pack(fill="x", padx=10, pady=10)

                    for key, value in summary.items():
                        if isinstance(value, dict):
                            # Handle nested dict like Grade Distribution
                            ctk.CTkLabel(
                                info_frame,
                                text=key,
                                font=("Arial Bold", 14),
                                text_color="#10b981",
                            ).pack(anchor="w", padx=15, pady=(10, 5))
                            for sub_key, sub_value in value.items():
                                ctk.CTkLabel(
                                    info_frame,
                                    text=f"  {sub_key}: {sub_value}",
                                    font=("Arial", 12),
                                    text_color="#d1d5db",
                                ).pack(anchor="w", padx=20, pady=2)
                        else:
                            ctk.CTkLabel(
                                info_frame,
                                text=f"{key}: {value}",
                                font=("Arial", 12),
                                text_color="#d1d5db",
                            ).pack(anchor="w", padx=15, pady=5)
                else:
                    # New format - display with cards and structured layout
                    # Summary cards
                    cards_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
                    cards_frame.pack(fill="x", padx=10, pady=10)

                    cards = [
                        (
                            "Total Students",
                            str(summary.get("total_students", 0)),
                            "#10b981",
                        ),
                        (
                            "Male Students",
                            str(summary.get("gender_counts", {}).get("male", 0)),
                            "#3b82f6",
                        ),
                        (
                            "Female Students",
                            str(summary.get("gender_counts", {}).get("female", 0)),
                            "#ec4899",
                        ),
                        (
                            "Previous Exam",
                            summary.get("trend_text", "No previous exam"),
                            "#fbbf24",
                        ),
                    ]

                    for text, value, color in cards:
                        card = ctk.CTkFrame(
                            cards_frame, fg_color="#20232a", corner_radius=12
                        )
                        card.pack(side="left", expand=True, fill="both", padx=5)
                        ctk.CTkLabel(
                            card, text=text, font=("Arial", 10), text_color="#d1d5db"
                        ).pack(anchor="w", padx=10, pady=(10, 5))
                        ctk.CTkLabel(
                            card, text=value, font=("Arial Bold", 18), text_color=color
                        ).pack(anchor="w", padx=10, pady=(0, 10))

                    # Distribution
                    dist_frame = ctk.CTkFrame(
                        summary_frame, fg_color="#20232a", corner_radius=12
                    )
                    dist_frame.pack(fill="x", padx=10, pady=10)
                    ctk.CTkLabel(
                        dist_frame,
                        text="Class Level Distribution",
                        font=("Arial Bold", 14),
                    ).pack(anchor="w", padx=15, pady=(15, 10))

                    dist_grid = ctk.CTkFrame(dist_frame, fg_color="transparent")
                    dist_grid.pack(fill="x", padx=15, pady=(0, 15))

                    distribution = summary.get("distribution", {})
                    levels = ["EE1", "EE2", "ME1", "ME2", "AE1", "AE2", "BE1", "BE2"]
                    for i, level in enumerate(levels):
                        if i % 4 == 0:
                            row_frame = ctk.CTkFrame(dist_grid, fg_color="transparent")
                            row_frame.pack(fill="x", pady=2)
                        cell = ctk.CTkFrame(
                            row_frame, fg_color="#1f2937", corner_radius=8
                        )
                        cell.pack(side="left", expand=True, fill="both", padx=2)
                        ctk.CTkLabel(
                            cell,
                            text=f"{level}: {distribution.get(level, 0)}",
                            font=("Arial", 11),
                        ).pack(pady=8)

                    # Subject averages
                    subj_frame = ctk.CTkFrame(
                        summary_frame, fg_color="#20232a", corner_radius=12
                    )
                    subj_frame.pack(fill="x", padx=10, pady=10)
                    ctk.CTkLabel(
                        subj_frame, text="Subject Mean Ranking", font=("Arial Bold", 14)
                    ).pack(anchor="w", padx=15, pady=(15, 10))

                    subj_grid = ctk.CTkFrame(subj_frame, fg_color="transparent")
                    subj_grid.pack(fill="x", padx=15, pady=(0, 15))

                    subject_averages = summary.get("subject_averages", [])
                    for rank, (subject, mean_value) in enumerate(
                        subject_averages, start=1
                    ):
                        row = ctk.CTkFrame(
                            subj_grid,
                            fg_color="#1f2937" if rank % 2 == 1 else "#111827",
                            corner_radius=8,
                        )
                        row.pack(fill="x", pady=2)
                        ctk.CTkLabel(
                            row, text=f"{rank}. {subject}", font=("Arial", 11)
                        ).pack(side="left", padx=10, pady=8)
                        ctk.CTkLabel(
                            row,
                            text=f"{mean_value:.2f}",
                            font=("Arial Bold", 11),
                            text_color="#60a5fa",
                        ).pack(side="right", padx=10, pady=8)

            except Exception as e:
                error_label = ctk.CTkLabel(
                    summary_frame,
                    text=f"Error loading summary: {e}",
                    font=("Arial", 14),
                    text_color="red",
                )
                error_label.pack(pady=10)
        else:
            messagebox.showinfo("Summary", "No summary data available for this exam.")

    def on_summary_window_close(self):
        """Handle summary window close event"""
        if hasattr(self, "summary_window"):
            self.summary_window.destroy()
            delattr(self, "summary_window")

    def update_header_text(self, exam_title):
        json_path = os.path.join(self.USER_DATA_DIR, "school_config.json")

        school = "MY SCHOOL"  # Default

        # 1. Try JSON First (Since Wizard saves here)
        try:
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config = json.load(f)
                    school = config.get("school_name", "MY SCHOOL")
        except:
            pass

        header_text = f"{school.upper()}\n{self.class_name.upper()} - {exam_title}"
        self.header_label.configure(text=header_text)
