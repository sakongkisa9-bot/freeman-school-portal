import customtkinter as ctk

from tkinter import messagebox

from grading_logic import get_grade_4_6_rating, calculate_final_level

from fpdf import FPDF

from reportlab.lib.pagesizes import landscape, A4

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from reportlab.lib.styles import getSampleStyleSheet

from reportlab.lib.units import inch

from reportlab.lib import colors

from reportlab.platypus import Image

from cloud_service import (
    CloudService,
    ask_cloud_credentials,
    apply_cloud_records_to_table,
)

import os


class PlaygroupMarkSheetView(ctk.CTkFrame):

    def get_json_path(self):

        import os

        # This automatically finds the folder where the script is running

        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "school_config.json"
        )

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

        # Normalize class name to match database format

        grade_mapping = {
            "Play group": "playgroup",
            "Pre-Primary 1": "pp1",
            "Pre-Primary 2": "pp2",
        }

        self.class_name = grade_mapping.get(class_name, class_name)

        self.read_only = read_only

        self.exam_name = exam_name

        self.marks_data = marks_data

        self.summary_data = summary_data

        # 1. Load Title & School Name from JSON immediately

        if self.read_only and self.exam_name:

            self.current_exam_title = self.exam_name

        else:

            self.current_exam_title = "PLAYGROUP ASSESSMENT 2026"

            try:

                import json

                import os

                path = self.get_json_path()

                if os.path.exists(path):

                    with open(path, "r") as f:

                        config = json.load(f)

                        # We use a specific key for primary titles

                        self.current_exam_title = config.get(
                            "playgroup_exam_title", "PLAYGROUP ASSESSMENT 2026"
                        )

            except Exception as e:

                print(f"Init JSON Load Error: {e}")

        # 2. Build UI (Make sure these are called in this order)

        self.ensure_table_exists()

        self.create_header_section()  # This creates self.header_label

        self.create_bottom_controls()

        self.create_scrollable_table_area()

        # 3. Final Refresh

        self.update_header_display()

        self.load_students_from_registry()

    def get_subjects_from_json(self):

        import json

        try:

            json_path = self.get_json_path()

            with open(json_path, "r") as f:

                config = json.load(f)

                # Navigate the nested dictionary: subjects -> playgroup

                if "subjects" in config and "playgroup" in config["subjects"]:

                    return config["subjects"]["playgroup"]

                # Fallback for old flat JSON format

                if "playgroup_subjects" in config:

                    return config["playgroup_subjects"]

        except Exception as e:

            print(f"Warning: Could not read JSON: {e}")

        # Default fallback if file is missing or broken

        return ["LANG", "MATH", "CREAT", "ENV"]

    def create_header_section(self):

        header_text = (
            f"SHINNERS SCHOOL MATISI {self.class_name.upper()}\n2026 PERFORMANCE RECORD"
        )

        # We store this as an instance variable 'self.header_label'

        self.header_label = ctk.CTkLabel(
            self,
            text=header_text,
            font=("Arial Bold", 22),
            fg_color="#2e7d32",
            text_color="white",
            corner_radius=8,
            height=70,
        )

        self.header_label.pack(fill="x", padx=10, pady=10)

    def update_header_display(self):
        """Updates the header to match the Junior style: SCHOOL NAME | GRADE | EXAM TITLE"""

        import json

        # 1. Default values

        school_name = "SHINNERS SCHOOL"

        # 2. Try to get the real school name from JSON

        try:

            json_path = self.get_json_path()

            with open(json_path, "r") as f:

                config = json.load(f)

                school_name = config.get("school_name", "SHINNERS SCHOOL").upper()

        except:

            pass

        # 3. Construct the full string

        display_text = (
            f"{school_name}  |  {self.class_name.upper()}  |  {self.current_exam_title}"
        )

        # 4. Update the label (using your existing header_label)

        if hasattr(self, "header_label"):

            self.header_label.configure(
                text=display_text,
                text_color="#f39c12",  # Matches the Junior orange highlight
            )

    def create_bottom_controls(self):

        self.bottom_bar = ctk.CTkFrame(self, fg_color="gray20", height=60)

        self.bottom_bar.pack(side="bottom", fill="x")

        if self.read_only:

            # Read-only mode: only Print and View Summary buttons

            ctk.CTkButton(
                self.bottom_bar,
                text="🖨 Print PDF",
                fg_color="#f57c00",
                text_color="black",
                hover_color="#e64a19",
                command=self.generate_pdf_report,
            ).pack(side="left", padx=5, pady=15)

            ctk.CTkButton(
                self.bottom_bar,
                text="📊 View Summary",
                fg_color="#1f538d",
                hover_color="#153d66",
                command=self.view_summary,
            ).pack(side="left", padx=5, pady=15)

        else:

            # Normal mode: all editing buttons

            self.btn_save = ctk.CTkButton(
                self.bottom_bar,
                text="💾 Save Marks",
                fg_color="#2e7d32",
                hover_color="#1b5e20",
                width=120,
                command=self.save_playgroup_marks,
            )

            self.btn_save.pack(side="left", padx=5, pady=15)

            self.btn_cloud = ctk.CTkButton(
                self.bottom_bar,
                text="☁ Fetch from Cloud",
                fg_color="#1f538d",
                hover_color="#153d66",
                command=self.fetch_cloud_data,
            )

            self.btn_cloud.pack(side="left", padx=5, pady=15)

            self.btn_pdf = ctk.CTkButton(
                self.bottom_bar,
                text="🖨 Print PDF",
                fg_color="#f57c00",
                text_color="black",
                hover_color="#e64a19",
                command=self.generate_pdf_report,
            )

            self.btn_pdf.pack(side="left", padx=5, pady=15)

            self.btn_new_exam = ctk.CTkButton(
                self.bottom_bar,
                text="🆕 New Exam",
                fg_color="#e67e22",
                hover_color="#d35400",
                command=self.handle_new_exam,
            )

            self.btn_new_exam.pack(side="left", padx=5, pady=15)

            self.btn_refresh = ctk.CTkButton(
                self.bottom_bar,
                text="🔄 Refresh",
                fg_color="#34495e",
                hover_color="#2c3e50",
                command=self.refresh_local_data,
            )

            self.btn_refresh.pack(side="left", padx=5, pady=15)

        self.btn_back = ctk.CTkButton(
            self.bottom_bar,
            text="⬅ Back to Dashboard",
            fg_color="#942727",
            hover_color="#7a1f1f",
            command=self.master.master.return_to_home,
        )

        self.btn_back.pack(side="right", padx=20, pady=15)

    def fetch_cloud_data(self):

        # 1. Get login details

        credentials = ask_cloud_credentials(self)

        if not credentials:

            return

        service = CloudService()

        # 2. Call the cloud API

        # Ensure this method in cloud_service.py uses the '/api/get_marks' endpoint

        result = service.fetch_marks(self.class_name, credentials)

        # 3. Handle the response

        if result.get("success"):

            # The cloud sends data in the "marks" key

            marks_data = result.get("marks", [])

            if not marks_data:

                messagebox.showinfo(
                    "Cloud Fetch", "No marks found on the cloud for this class."
                )

                return

            # Get subjects to align columns correctly

            subjects = self.get_subjects_from_json()

            # 4. Fill the table (Junior uses 3 columns per subject)

            apply_cloud_records_to_table(
                self.table_inner, marks_data, subjects, columns_per_subject=2
            )

            self.update_idletasks()

            # 5. Save the fetched marks to database (skip reload to preserve cloud values)

            self.save_playgroup_marks(skip_reload=True)

            # 6. Consume marks from cloud (delete them after successful fetch)

            service.consume_marks(self.class_name, credentials)

            # 7. Success Message

            messagebox.showinfo(
                "Cloud Fetch",
                f"Successfully synchronized {len(marks_data)} student records. Marks have been removed from cloud.",
            )

        else:

            # If result['success'] is False

            messagebox.showerror(
                "Cloud Fetch Failed",
                result.get("message", "Could not fetch cloud marks."),
            )

    def refresh_local_data(self):

        # Simply reload the students and marks from the local sqlite db

        self.load_students_from_registry()

        messagebox.showinfo("Refresh", "Table updated with latest local entries!")

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

                if "Total Students" in summary or "Students with Marks" in summary:

                    # Old format - display as key-value pairs

                    info_frame = ctk.CTkFrame(
                        summary_frame, fg_color="#20232a", corner_radius=12
                    )

                    info_frame.pack(fill="x", padx=10, pady=10)

                    for key, value in summary.items():

                        if isinstance(value, dict):

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

    def create_scrollable_table_area(self):

        self.container = ctk.CTkFrame(self, fg_color="gray15")

        self.container.pack(fill="both", expand=True, padx=10, pady=5)

        # Container for both header canvas and content canvas
        self.scroll_container = ctk.CTkFrame(self.container, fg_color="gray15")
        self.scroll_container.pack(fill="both", expand=True)

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
            self.scroll_container, orientation="horizontal", command=self._on_horizontal_scroll
        )

        self.v_scroll = ctk.CTkScrollbar(
            self.scroll_container, orientation="vertical", command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=self._update_h_scroll, yscrollcommand=self.v_scroll.set
        )
        self.header_canvas.configure(
            xscrollcommand=self._update_h_scroll
        )

        self.h_scroll.pack(side="bottom", fill="x")

        self.v_scroll.pack(side="right", fill="y")

        self.canvas.pack(side="left", fill="both", expand=True)

        # Create header frame inside header canvas at (0, 0)
        self.header_frame = ctk.CTkFrame(self.header_canvas, fg_color="gray15")
        self.header_canvas.create_window((0, 0), window=self.header_frame, anchor="nw")

        # Table inner frame inside content canvas at (0, 0)
        self.table_inner = ctk.CTkFrame(self.canvas, fg_color="transparent")

        self.canvas.create_window((0, 0), window=self.table_inner, anchor="nw")

        # Add mouse wheel bindings for proper scrolling

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        self.canvas.bind("<Button-4>", self._on_mousewheel)

        self.canvas.bind("<Button-5>", self._on_mousewheel)

        self.create_table_headers()

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
                req_width = self.table_inner.winfo_reqwidth()
                req_height = self.table_inner.winfo_reqheight()
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
                self.header_canvas.configure(scrollregion=(0, 0, max_width, header_bbox[3]))
            else:
                self.header_canvas.configure(scrollregion=(0, 0, max_width, 90))
        except Exception:
            pass


    def create_table_headers(self):

        # FIXED DIMENSIONS

        NAME_W = 180

        BOX_SIZE = 45

        TOT_W = 65

        # Configure columns on BOTH header_frame and table_inner to keep them synchronized
        self.header_frame.grid_columnconfigure(0, weight=0, minsize=NAME_W)

        self.table_inner.grid_columnconfigure(0, weight=0, minsize=NAME_W)

        subjects = self.get_subjects_from_json()

        num_subs = len(subjects)

        # Header: Name (Use width=NAME_W to prevent expansion)

        ctk.CTkLabel(
            self.header_frame,
            text="STUDENT NAME",
            font=("Arial Bold", 12),
            width=NAME_W,
            fg_color="gray25",
            corner_radius=0,
        ).grid(row=0, column=0, rowspan=2, sticky="nsew", padx=1, pady=0)

        for i, sub in enumerate(subjects):

            col_start = 1 + (i * 2)

            self.header_frame.grid_columnconfigure(
                (col_start, col_start + 1),
                weight=0,
                minsize=BOX_SIZE,
                uniform="subs",
            )

            self.table_inner.grid_columnconfigure(
                (col_start, col_start + 1),
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
                width=BOX_SIZE * 2,
                font=("Arial Bold", 10),
            ).grid(
                row=0,
                column=col_start,
                columnspan=2,
                sticky="nsew",
                padx=1,
                pady=(1, 0),
            )

            # Score, Rate Labels

            labels = [("Score", "#1a1a1a"), ("Rate", "#2c3e50")]

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

        total_start = 1 + (num_subs * 2)

        self.header_frame.grid_columnconfigure(
            (total_start, total_start + 1, total_start + 2), weight=0, minsize=TOT_W
        )

        self.table_inner.grid_columnconfigure(
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

    def add_student_row_with_data(self, row_data, rank, read_only=False):

        subjects = self.get_subjects_from_json()

        num_subs = len(subjects)

        # FIXED DIMENSIONS (matching header)

        NAME_W = 180

        BOX_SIZE = 45

        TOT_W = 65

        # Calculate row index based on existing rows in table_inner

        # Headers are now separate, so student rows start at row 0

        row_index = len(self.table_inner.grid_slaves()) // (1 + num_subs * 2 + 3)

        # Configure this row to NOT expand vertically (weight=0) and set fixed height
        self.table_inner.grid_rowconfigure(row_index, weight=0, minsize=47)

        # Name label (column 0)

        ctk.CTkLabel(
            self.table_inner,
            text=row_data[0],
            anchor="w",
            padx=10,
            font=("Arial", 12),
            width=NAME_W,
            fg_color="transparent",
        ).grid(row=row_index, column=0, sticky="w", padx=1, pady=0)

        for i in range(num_subs * 2):

            col_idx = i + 1

            color = "#1a1a1a" if i % 2 == 0 else "#2c3e50"

            if read_only and i % 2 == 0:

                color = "gray30"

            e = ctk.CTkEntry(
                self.table_inner,
                width=BOX_SIZE,
                height=BOX_SIZE,
                fg_color=color,
                border_width=0,
                corner_radius=0,
                justify="center",
                font=("Arial Bold", 12),
            )

            e.grid(row=row_index, column=col_idx, sticky="ew", padx=1, pady=0)

            val = row_data[col_idx]

            if val is not None:

                e.insert(0, str(val))

            if read_only:

                e.configure(state="disabled")

            elif i % 2 == 0:

                e.bind(
                    "<FocusOut>",
                    lambda event, ent=e, idx=i: self.auto_calculate(
                        ent, idx, self.table_inner
                    ),
                )

            else:

                e.configure(state="disabled")

        t_idx = 1 + (num_subs * 2)

        summary_colors = ["gray30", "#1f538d", "#4a1515"]

        for j in range(3):

            col_idx = t_idx + j

            val = row_data[col_idx] if len(row_data) > col_idx else ""

            if j == 2:

                val = str(rank)

            box = ctk.CTkEntry(
                self.table_inner,
                width=TOT_W,
                height=BOX_SIZE,
                fg_color=summary_colors[j],
                font=("Arial Bold", 12),
                border_width=0,
                corner_radius=0,
                justify="center",
            )

            box.grid(row=row_index, column=col_idx, sticky="ew", padx=1, pady=0)

            box.insert(0, str(val))

            box.configure(state="disabled")

    def auto_calculate(self, entry_widget, col_index, row_frame):
        """Validates the input and triggers the dynamic total calculation."""

        val = entry_widget.get().strip()

        # 1. Validate input (make sure they actually typed a number)

        if val:

            try:

                score = int(val)

                # Optional: Prevent them from entering numbers over 100

                if score > 100 or score < 0:

                    from tkinter import messagebox

                    messagebox.showwarning(
                        "Invalid Score", "Please enter a score between 0 and 100."
                    )

                    entry_widget.delete(0, "end")

                    return

            except ValueError:

                # If they typed letters instead of numbers, clear the box

                entry_widget.delete(0, "end")

                return

        # 2. If the input is good, tell the row to recalculate!

        # Get the row index from the entry widget

        row_idx = entry_widget.grid_info()["row"]

        self.refresh_totals(row_frame, row_idx)

    def refresh_totals(self, row_frame, row_idx):

        import grading_logic as gl  # Ensure your file is imported

        subjects = self.get_subjects_from_json()

        num_subs = len(subjects)

        total_score = 0

        widgets = row_frame.grid_slaves(row=row_idx)

        widgets.sort(key=lambda w: int(w.grid_info()["column"]))

        # 1. Calculate Subject Ratings using get_grade_4_6_rating

        for i in range(num_subs):

            score_idx = 1 + (i * 2)

            rate_idx = score_idx + 1

            try:

                score_val = widgets[score_idx].get().strip()

                if score_val.isdigit():

                    s = int(score_val)

                    total_score += s

                    # USE YOUR SPECIFIC PRIMARY LOGIC

                    rate = gl.get_grade_4_6_rating(s)

                    widgets[rate_idx].configure(state="normal")

                    widgets[rate_idx].delete(0, "end")

                    widgets[rate_idx].insert(0, rate)

                    widgets[rate_idx].configure(state="disabled")

            except:

                continue

        # 2. Update Total Score Box

        t_idx = 1 + (num_subs * 2)

        widgets[t_idx].configure(state="normal")

        widgets[t_idx].delete(0, "end")

        widgets[t_idx].insert(0, str(total_score))

        widgets[t_idx].configure(state="disabled")

        # 3. Calculate Final Level using your calculate_final_level (is_primary=True)

        avg_lvl = gl.calculate_final_level(total_score, is_primary=True)

        l_box = widgets[t_idx + 1]

        l_box.configure(state="normal")

        l_box.delete(0, "end")

        l_box.insert(0, avg_lvl)

        l_box.configure(state="disabled")

    def ensure_table_exists(self):
        """Syncs database columns with JSON subjects and prints every action."""

        try:

            subjects = self.get_subjects_from_json()

            # 1. Ensure base table exists (created in database.py)

            self.db.cursor().execute(
                "CREATE TABLE IF NOT EXISTS playgroup_marks (adm_no TEXT PRIMARY KEY)"
            )

            # 2. Get currently existing columns

            self.db.cursor().execute("PRAGMA table_info(playgroup_marks)")

            existing_cols = [row[1].lower() for row in self.db.cursor().fetchall()]

            # 3. Check every subject from JSON

            for sub in subjects:

                # Use this logic everywhere you handle subject columns:

                clean_name = (
                    sub.strip()
                    .replace(" ", "_")
                    .replace("-", "_")
                    .replace("/", "_")
                    .lower()
                )

                s_col = f"{clean_name}_s"

                r_col = f"{clean_name}_r"

                # Check Score Column

                if s_col not in existing_cols:

                    print(
                        f"DEBUG: Adding missing column [{s_col}] to playgroup_marks..."
                    )

                    try:
                        self.db.cursor().execute(
                            f"ALTER TABLE playgroup_marks ADD COLUMN {s_col} INTEGER"
                        )
                    except Exception as e:
                        if "duplicate column" in str(e).lower():
                            print(f"DEBUG: Column [{s_col}] already exists, skipping...")
                        else:
                            raise

                # Check Rate Column

                if r_col not in existing_cols:

                    print(
                        f"DEBUG: Adding missing column [{r_col}] to playgroup_marks..."
                    )

                    try:
                        self.db.cursor().execute(
                            f"ALTER TABLE playgroup_marks ADD COLUMN {r_col} TEXT"
                        )
                    except Exception as e:
                        if "duplicate column" in str(e).lower():
                            print(f"DEBUG: Column [{r_col}] already exists, skipping...")
                        else:
                            raise

            # 4. Final check for Totals/Level

            if "total_points" not in existing_cols:

                try:
                    self.db.cursor().execute(
                        "ALTER TABLE playgroup_marks ADD COLUMN total_points INTEGER"
                    )
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print("DEBUG: Column [total_points] already exists, skipping...")
                    else:
                        raise

            if "average_level" not in existing_cols:

                try:
                    self.db.cursor().execute(
                        "ALTER TABLE playgroup_marks ADD COLUMN average_level TEXT"
                    )
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print("DEBUG: Column [average_level] already exists, skipping...")
                    else:
                        raise

            self.db.conn.commit()

            print(">>> Database Sync Complete: All columns verified.")

        except Exception as e:

            print(f"!!! Database Migration Error: {e}")

    def load_students_from_registry(self):

        # Clear UI

        for child in self.table_inner.winfo_children():

            child.destroy()

        self.create_table_headers()

        subjects = self.get_subjects_from_json()

        num_subs = len(subjects)

        try:

            # If in read-only mode with marks_data, load from JSON data instead of database

            if self.read_only and self.marks_data:

                import json

                records = json.loads(self.marks_data)

                # Recalculate rank from total scores (rank is not saved in JSON)

                total_idx = 1 + (num_subs * 2)

                scored_students = []

                for row_data in records:

                    try:

                        score = (
                            int(row_data[total_idx])
                            if row_data[total_idx] is not None
                            else -1
                        )

                    except (ValueError, TypeError):

                        score = -1

                    scored_students.append({"data": row_data, "score": score})

                # Sort by total points (Highest first)

                scored_students.sort(key=lambda x: x["score"], reverse=True)

                # Assign positions

                final_list = []

                current_pos = 0

                for i, item in enumerate(scored_students):

                    if item["score"] == -1:

                        pos = "-"

                    else:

                        if i > 0 and item["score"] == scored_students[i - 1]["score"]:

                            pos = current_pos  # Tie

                        else:

                            current_pos = i + 1

                            pos = current_pos

                    final_list.append((item["data"], pos))

                # Sort by position: Numbers 1, 2, 3... then the "-" students at the bottom

                final_list.sort(
                    key=lambda x: (x[1] == "-", x[1] if x[1] != "-" else 999)
                )

                # Draw rows in the sorted order

                for row_data, pos in final_list:

                    self.add_student_row_with_data(row_data, pos, read_only=self.read_only)

            else:

                # Inside load_students_from_registry...

                subjects = self.get_subjects_from_json()

                select_cols = []

                for sub in subjects:

                    # Use .strip() to handle "MAT " vs "MAT"

                    clean_name = (
                        sub.strip()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace("/", "_")
                        .lower()
                    )

                    select_cols.extend([f"m.{clean_name}_s", f"m.{clean_name}_r"])

                col_str = ", ".join(select_cols) if select_cols else "m.total_points"

                query = f"""

                    SELECT s.name, {col_str}, m.total_points, m.average_level

                    FROM students s

                    LEFT JOIN playgroup_marks m ON s.adm_no = m.adm_no

                    WHERE UPPER(s.grade) = UPPER(?)

                """

                # 1. Fetch data

                # ... (Your existing SQL SELECT query logic here) ...

                self.db.cursor().execute(query, (self.class_name,))

                records = self.db.cursor().fetchall()

                print(f"DEBUG: Loaded {len(records)} students for grade '{self.class_name}' from database")

                # 2. Rank calculation

                total_idx = 1 + (num_subs * 2)

                scored_students = []

                for row in records:

                    try:

                        score = (
                            int(row[total_idx]) if row[total_idx] is not None else -1
                        )

                    except (ValueError, TypeError):

                        score = -1

                    scored_students.append({"data": row, "score": score})

                # Sort by total points (Highest first)

                scored_students.sort(key=lambda x: x["score"], reverse=True)

                # 3. Assign positions and Sort for UI

                final_list = []

                current_pos = 0

                for i, item in enumerate(scored_students):

                    if item["score"] == -1:

                        pos = "-"

                    else:

                        if i > 0 and item["score"] == scored_students[i - 1]["score"]:

                            pos = current_pos  # Tie

                        else:

                            current_pos = i + 1

                            pos = current_pos

                    final_list.append((item["data"], pos))

                # SORT THE LIST BY POSITION: Numbers 1, 2, 3... then the "-" students at the bottom

                final_list.sort(
                    key=lambda x: (x[1] == "-", x[1] if x[1] != "-" else 999)
                )

                # 4. Draw rows in the sorted order

                for row_data, pos in final_list:

                    self.add_student_row_with_data(row_data, pos)

            # Update scrollregion after all rows are added

            self.canvas.after(
                100, lambda: self._update_scrollregion()
            )


        except Exception as e:

            print(f"Loading/Sorting Error: {e}")

    def save_playgroup_marks(self, skip_reload=False):
        # Force focus away from any entry widget to commit values
        self.table_inner.focus_set()
        
        success_count = 0

        subjects = self.get_subjects_from_json()

        num_subs = len(subjects)

        try:

            # Playgroup marksheet uses direct grid layout, not row frames

            # Get all widgets and group them by row

            all_widgets = self.table_inner.grid_slaves()

            if not all_widgets:

                return

            # Group widgets by row

            rows = {}

            for w in all_widgets:

                row = w.grid_info()["row"]

                if row not in rows:

                    rows[row] = []

                rows[row].append(w)

            for row_idx in sorted(rows.keys()):

                widgets = rows[row_idx]

                # Sort widgets by column

                widgets.sort(key=lambda w: int(w.grid_info()["column"]))

                if not widgets:

                    continue

                # Get Student Name (column 0)

                name_widget = widgets[0]

                if not hasattr(name_widget, "cget"):

                    continue

                student_name = name_widget.cget("text")

                if student_name == "STUDENT NAME":

                    continue

                # Get Admission Number

                self.db.cursor().execute(
                    "SELECT adm_no FROM students WHERE name = ?", (student_name,)
                )

                res = self.db.cursor().fetchone()

                if not res:

                    continue

                adm_no = res[0]

                # 1. Collect dynamic marks from Entry boxes using the grouped widgets list

                marks_data = []

                for i in range(1, (num_subs * 2) + 1):
                    widget = widgets[i]
                    val = widget.get() if hasattr(widget, 'get') else None
                    marks_data.append(val if val != "" else None)

                # 2. Collect Totals and Level (The last 3 widgets are Total, Level, Pos)

                # Position is not saved in the marks table, only Total and Level

                total_val = widgets[-3].get()
                lvl_val = widgets[-2].get()

                # 3. DYNAMIC SQL QUERY

                # Total columns = adm_no (1) + subjects (num_subs * 2) + total (1) + level (1)

                total_columns_needed = 1 + (num_subs * 2) + 2

                placeholders = ", ".join(["?"] * total_columns_needed)

                # Build column names dynamically to ensure order matches placeholders

                col_names = ["adm_no"]

                for sub in subjects:

                    clean = (
                        sub.strip()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace("/", "_")
                        .lower()
                    )

                    col_names.extend([f"{clean}_s", f"{clean}_r"])

                col_names.extend(["total_points", "average_level"])

                query = f"INSERT OR REPLACE INTO playgroup_marks ({', '.join(col_names)}) VALUES ({placeholders})"

                final_data = [adm_no] + marks_data + [total_val, lvl_val]

                self.db.cursor().execute(query, final_data)

                success_count += 1

            self.db.conn.commit()

            messagebox.showinfo("Success", f"Saved marks for {success_count} students.")

            if not skip_reload:

                self.load_students_from_registry()  # Refresh to update rankings

        except Exception as e:

            messagebox.showerror("Database Error", f"Could not save: {e}")

    def generate_pdf_report(self):

        from tkinter import filedialog, messagebox

        import os

        import json

        # 1. Setup File Path

        exam_name = getattr(self, "current_exam_title", "EXAM_REPORT")

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"{self.class_name}_{exam_name.replace(' ', '_')}.pdf",
            title="Save Playgroup Marksheet",
        )

        if not file_path:

            return

        try:

            # 2. Fetch School Data and Subjects from JSON (The "Kabianga" Source)

            school_name = "SHINNERS SCHOOL"

            logo_path = ""

            subjects = []

            json_path = self.get_json_path()

            if os.path.exists(json_path):

                with open(json_path, "r") as f:

                    config = json.load(f)

                    school_name = config.get("school_name", "SHINNERS SCHOOL").upper()

                    logo_path = config.get("logo", "")

                    # Get subjects from the nested structure we fixed earlier

                    subjects = config.get("subjects", {}).get("playgroup", [])

            if not subjects:

                subjects = ["LANG", "MATH", "CREAT", "ENV"]

            # 3. Initialize PDF

            pdf = FPDF(orientation="L", unit="mm", format="A4")

            pdf.add_page()

            # Draw Logo if exists

            if logo_path and os.path.exists(logo_path):

                pdf.image(logo_path, 10, 8, 20)

            # Header: School Name

            pdf.set_font("Helvetica", "B", 18)

            pdf.cell(0, 10, school_name, ln=True, align="C")

            # Sub-Header: Grade and Exam Title

            pdf.set_font("Helvetica", "B", 12)

            pdf.cell(
                0,
                8,
                f"GRADE: {self.class_name.upper()}  |  RECORD: {exam_name}",
                ln=True,
                align="C",
            )

            pdf.ln(5)

            # --- DYNAMIC COLUMN CALCULATION ---

            name_w = 45  # Slightly wider for long names

            tot_w = 12

            lvl_w = 25

            pos_w = 12

            totals_section_w = tot_w + lvl_w + pos_w

            # A4 Landscape is 297mm. Margin is 10mm each side = 277mm usable.

            usable_w = 277 - name_w - totals_section_w

            sub_col_w = usable_w / max(1, (len(subjects) * 2))

            # --- Row 1: Main Headers ---

            pdf.set_font("Helvetica", "B", 9)

            pdf.set_fill_color(240, 240, 240)

            pdf.cell(name_w, 14, "STUDENT NAME", 1, 0, "C", True)

            for sub in subjects:

                pdf.cell(sub_col_w * 2, 7, sub[:8], 1, 0, "C", True)

            pdf.cell(tot_w, 14, "TOT", 1, 0, "C", True)

            pdf.cell(lvl_w, 14, "LEVEL", 1, 0, "C", True)

            pdf.cell(pos_w, 14, "POS", 1, 1, "C", True)

            # --- Row 2: Score/Rate Labels ---

            # Move back up to draw S/R under the subjects

            current_y = pdf.get_y()

            pdf.set_xy(10 + name_w, current_y - 7)

            pdf.set_font("Helvetica", "B", 7)

            for _ in subjects:

                pdf.cell(sub_col_w, 7, "S", 1, 0, "C", True)

                pdf.cell(sub_col_w, 7, "R", 1, 0, "C", True)

            pdf.ln(7)

            # --- Data Rows ---

            pdf.set_font("Helvetica", size=8)

            # Get all widgets and group them by row

            all_widgets = self.table_inner.grid_slaves()

            if not all_widgets:

                return

            # Group widgets by row

            rows = {}

            for widget in all_widgets:

                grid_info = widget.grid_info()

                row = int(grid_info["row"])

                col = int(grid_info["column"])

                if row not in rows:

                    rows[row] = {}

                rows[row][col] = widget

            for row in sorted(rows.keys()):
                row_widgets = rows[row]

                if not row_widgets:

                    continue

                # Get name from column 0

                if 0 not in row_widgets:

                    continue

                name_widget = row_widgets[0]

                if not hasattr(name_widget, "cget"):

                    continue

                name_text = name_widget.cget("text")

                if not name_text or name_text == "STUDENT NAME":

                    continue

                # Print Name

                pdf.cell(name_w, 8, txt=name_text[:22], border=1)

                # Print Subjects (S and R)

                num_sub_widgets = len(subjects) * 2

                for i in range(1, min(num_sub_widgets + 1, len(row_widgets))):

                    if i in row_widgets:

                        val = (
                            row_widgets[i].get()
                            if hasattr(row_widgets[i], "get")
                            else ""
                        )

                        pdf.cell(sub_col_w, 8, txt=str(val), border=1, ln=0, align="C")

                # Print Totals (The last 3 widgets) - only if they exist

                t_idx = 1 + (len(subjects) * 2)

                for j in range(3):

                    col_idx = t_idx + j

                    if col_idx in row_widgets:

                        val = (
                            row_widgets[col_idx].get()
                            if hasattr(row_widgets[col_idx], "get")
                            else ""
                        )

                        if j == 0:

                            pdf.cell(tot_w, 8, txt=str(val), border=1, ln=0, align="C")

                        elif j == 1:

                            pdf.cell(lvl_w, 8, txt=str(val), border=1, ln=0, align="C")

                        else:

                            pdf.cell(pos_w, 8, txt=str(val), border=1, ln=1, align="C")

            pdf.output(file_path)

            messagebox.showinfo(
                "Success", f"Report saved to {os.path.basename(file_path)}"
            )

        except Exception as e:

            messagebox.showerror("PDF Error", f"Failed to generate report: {e}")

    def handle_new_exam(self):

        self.save_playgroup_marks()

        dialog = ctk.CTkInputDialog(
            text="Enter New Exam Title:", title="New Performance Record"
        )

        new_title = dialog.get_input()

        if new_title:

            if messagebox.askyesno(
                "Confirm Reset", f"Clear marks and start {new_title}?"
            ):

                try:

                    # Save current exam as previous exam before clearing

                    self.save_current_exam_as_previous()

                    # Clear DB marks

                    self.db.cursor().execute(
                        "DELETE FROM playgroup_marks WHERE adm_no IN (SELECT adm_no FROM students WHERE UPPER(grade) = UPPER(?))",
                        (self.class_name,),
                    )

                    self.db.conn.commit()

                    # Update local title

                    self.current_exam_title = new_title.upper()

                    # SAVE TO JSON PERMANENTLY

                    import json

                    import os

                    path = self.get_json_path()

                    config = {}

                    if os.path.exists(path):

                        with open(path, "r") as f:

                            config = json.load(f)

                    config["playgroup_exam_title"] = self.current_exam_title

                    with open(path, "w") as f:

                        json.dump(config, f, indent=4)

                    self.update_header_display()

                    self.load_students_from_registry()

                    messagebox.showinfo("Success", "Exam title saved!")

                except Exception as e:

                    messagebox.showerror("Error", f"Save failed: {e}")

    def save_current_exam_as_previous(self):
        """Save the current exam as a previous exam with summary"""

        import json

        # Get current exam title

        current_exam_name = self.current_exam_title

        # Get all marks data

        subjects = self.get_subjects_from_json()

        select_cols = []

        for sub in subjects:

            clean_name = (
                sub.strip()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
                .lower()
            )

            select_cols.extend([f"m.{clean_name}_s", f"m.{clean_name}_r"])

        col_str = ", ".join(select_cols) if select_cols else "m.total_points"

        query = f"""

            SELECT s.name, {col_str}, m.total_points, m.average_level

            FROM students s

            LEFT JOIN playgroup_marks m ON s.adm_no = m.adm_no

            WHERE UPPER(s.grade) = UPPER(?)

        """

        self.db.cursor().execute(query, (self.class_name,))

        records = self.db.cursor().fetchall()

        # Convert to JSON

        marks_data = json.dumps(records)

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

            SELECT s.name, s.gender, m.total_points, m.average_level

            FROM students s

            LEFT JOIN playgroup_marks m ON s.adm_no = m.adm_no

            WHERE UPPER(s.grade) = UPPER(?)

        """

        self.db.cursor().execute(query, (self.class_name,))

        rows = self.db.cursor().fetchall()

        for row in rows:

            if not row:

                continue

            total_students += 1

            name, gender, total_points, average_level = row

            # Map gender values to standard categories

            gender_raw = str(gender).strip().lower() if gender else "other"

            if gender_raw in ["m", "male", "boy"]:

                gender = "male"

            elif gender_raw in ["f", "female", "girl"]:

                gender = "female"

            else:

                gender = "other"

            gender_counts[gender] += 1

            # Track distribution based on average_level

            if average_level is not None:

                average_label = str(average_level).strip().upper().replace(" ", "")

                if average_label in distribution:

                    distribution[average_label] += 1

            # Track gender totals

            if isinstance(total_points, (int, float)):

                gender_totals[gender] += total_points

        # Calculate subject averages

        for subject in subjects:

            clean_name = (
                subject.strip()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
                .lower()
            )

            score_col = f"{clean_name}_s"

            query = f"""

                SELECT m.{score_col}

                FROM playgroup_marks m

                JOIN students s ON m.adm_no = s.adm_no

                WHERE UPPER(s.grade) = UPPER(?)

            """

            self.db.cursor().execute(query, (self.class_name,))

            subject_rows = self.db.cursor().fetchall()

            for score_row in subject_rows:

                score = score_row[0]

                if score is not None:

                    try:

                        score_value = float(score)

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
