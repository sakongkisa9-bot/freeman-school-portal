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


class LowerMarkSheetView(ctk.CTkFrame):
    def get_json_path(self):
        import os

        # This automatically finds the folder where the script is running
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "school_config.json"
        )

    def __init__(self, parent, db_connection, class_name):
        super().__init__(parent, fg_color="transparent")
        self.db = db_connection
        self.class_name = class_name

        # 1. Load Title & School Name from JSON immediately
        self.current_exam_title = "LOWER PRIMARY ASSESSMENT 2026"
        try:
            import json
            import os

            path = self.get_json_path()
            if os.path.exists(path):
                with open(path, "r") as f:
                    config = json.load(f)
                    # We use a specific key for primary titles
                    self.current_exam_title = config.get(
                        "lower_exam_title", "LOWER PRIMARY ASSESSMENT 2026"
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

                # Navigate the nested dictionary: subjects -> lower
                if "subjects" in config and "lower" in config["subjects"]:
                    return config["subjects"]["lower"]

                # Fallback for old flat JSON format
                if "lower_subjects" in config:
                    return config["lower_subjects"]

        except Exception as e:
            print(f"Warning: Could not read JSON: {e}")

        # Default fallback if file is missing or broken
        return ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"]

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

        self.btn_save = ctk.CTkButton(
            self.bottom_bar,
            text="💾 Save Marks",
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            width=120,
            command=self.save_lower_marks,
        )
        self.btn_save.pack(side="left", padx=10, pady=15)

        self.btn_cloud = ctk.CTkButton(
            self.bottom_bar,
            text="☁ Fetch from Cloud",
            fg_color="#1f538d",
            hover_color="#153d66",
            command=self.fetch_cloud_data,
        )
        self.btn_cloud.pack(side="left", padx=10, pady=15)
        self.btn_refresh = ctk.CTkButton(
            self.bottom_bar,
            text="refresh",
            fg_color="#87f500",
            text_color="black",
            hover_color="#00f529",
            command=self.refresh_local_data,
        )
        self.btn_refresh.pack(side="left", padx=15, pady=15)

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
            fg_color="#1f538d",
            hover_color="#153d66",
            command=self.handle_new_exam,  # Logic below
        )
        self.btn_new_exam.pack(side="left", padx=10, pady=15)

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

            # 5. Success Message
            messagebox.showinfo(
                "Cloud Fetch",
                f"Successfully synchronized {len(marks_data)} student records.",
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

    def create_scrollable_table_area(self):
        self.container = ctk.CTkFrame(self, fg_color="gray15")
        self.container.pack(fill="both", expand=True, padx=10, pady=5)

        self.canvas = ctk.CTkCanvas(self.container, bg="#242424", highlightthickness=0)
        self.h_scroll = ctk.CTkScrollbar(
            self.container, orientation="horizontal", command=self.canvas.xview
        )
        self.v_scroll = ctk.CTkScrollbar(
            self.container, orientation="vertical", command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set
        )
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.table_inner = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas.create_window((0, 0), window=self.table_inner, anchor="nw")
        self.table_inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.create_table_headers()

    def create_table_headers(self):
        h_frame = ctk.CTkFrame(self.table_inner, fg_color="gray25", corner_radius=0)
        h_frame.pack(fill="x")
        h_frame.grid_columnconfigure(0, weight=0, minsize=180, uniform="primary_col")

        subjects = self.get_subjects_from_json()
        num_subs = len(subjects)

        ctk.CTkLabel(h_frame, text="STUDENT NAME", font=("Arial Bold", 11)).grid(
            row=0, column=0, rowspan=2
        )

        for i, sub in enumerate(subjects):
            col_start = 1 + (i * 2)
            h_frame.grid_columnconfigure(
                (col_start, col_start + 1), weight=0, minsize=24, uniform="primary_col"
            )

            ctk.CTkLabel(
                h_frame, text=sub[:8], fg_color="gray30", font=("Arial Bold", 10)
            ).grid(row=0, column=col_start, columnspan=2, sticky="nsew", padx=1, pady=1)
            ctk.CTkLabel(
                h_frame, text="Score", font=("Arial", 9), fg_color="#1a1a1a"
            ).grid(row=1, column=col_start, sticky="nsew")
            ctk.CTkLabel(
                h_frame, text="Rate", font=("Arial", 9), fg_color="#2c3e50"
            ).grid(row=1, column=col_start + 1, sticky="nsew")

        t_idx = 1 + (num_subs * 2)
        h_frame.grid_columnconfigure(
            (t_idx, t_idx + 1, t_idx + 2), weight=0, minsize=65, uniform="primary_col"
        )
        ctk.CTkLabel(h_frame, text="TOTAL SCORES", font=("Arial Bold", 9)).grid(
            row=0, column=t_idx, rowspan=2, sticky="nsew"
        )
        ctk.CTkLabel(h_frame, text="AVERAGE LEVEL", font=("Arial Bold", 9)).grid(
            row=0, column=t_idx + 1, rowspan=2, sticky="nsew"
        )
        ctk.CTkLabel(h_frame, text="POS", font=("Arial Bold", 9)).grid(
            row=0, column=t_idx + 2, rowspan=2, sticky="nsew"
        )

    def add_student_row_with_data(self, row_data, rank):
        subjects = self.get_subjects_from_json()
        num_subs = len(subjects)

        row_frame = ctk.CTkFrame(self.table_inner, fg_color="transparent")
        row_frame.pack(fill="x", pady=1)
        row_frame.grid_columnconfigure(0, weight=0, minsize=180, uniform="primary_col")
        ctk.CTkLabel(
            row_frame, text=row_data[0], anchor="w", padx=5, font=("Arial", 10)
        ).grid(row=0, column=0)

        for i in range(num_subs * 2):
            col_idx = i + 1
            row_frame.grid_columnconfigure(
                col_idx, weight=0, minsize=24, uniform="primary_col"
            )
            color = "#1a1a1a" if i % 2 == 0 else "#2c3e50"
            e = ctk.CTkEntry(
                row_frame,
                width=24,
                height=24,
                fg_color=color,
                border_width=1,
                corner_radius=0,
                justify="center",
            )
            e.grid(row=0, column=col_idx, sticky="nsew")

            val = row_data[col_idx]
            if val is not None:
                e.insert(0, str(val))

            if i % 2 == 0:
                e.bind(
                    "<FocusOut>",
                    lambda event, ent=e, idx=i: self.auto_calculate(
                        ent, idx, row_frame
                    ),
                )
            else:
                e.configure(state="disabled")

        t_idx = 1 + (num_subs * 2)
        row_frame.grid_columnconfigure(
            (t_idx, t_idx + 1, t_idx + 2), weight=0, minsize=65, uniform="primary_col"
        )

        t_box = ctk.CTkEntry(
            row_frame, height=24, fg_color="gray30", corner_radius=0, justify="center"
        )
        if row_data[t_idx] is not None:
            t_box.insert(0, str(row_data[t_idx]))
        t_box.configure(state="disabled")
        t_box.grid(row=0, column=t_idx, sticky="nsew")

        l_box = ctk.CTkEntry(
            row_frame, height=24, fg_color="#1f538d", corner_radius=0, justify="center"
        )
        if row_data[t_idx + 1] is not None:
            l_box.insert(0, str(row_data[t_idx + 1]))
        l_box.configure(state="disabled")
        l_box.grid(row=0, column=t_idx + 1, sticky="nsew")

        p_box = ctk.CTkEntry(
            row_frame,
            height=24,
            fg_color="#455a64",
            text_color="white",
            corner_radius=0,
            justify="center",
            font=("Arial Bold", 10),
        )
        p_box.insert(0, str(rank))
        p_box.configure(state="disabled")
        p_box.grid(row=0, column=t_idx + 2, sticky="nsew")

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
        self.refresh_totals(row_frame)

    def refresh_totals(self, row_frame):
        import grading_logic as gl  # Ensure your file is imported

        subjects = self.get_subjects_from_json()
        num_subs = len(subjects)
        total_score = 0

        widgets = row_frame.grid_slaves(row=0)
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

            # 1. Ensure base table exists
            self.db._cursor.execute(
                "CREATE TABLE IF NOT EXISTS lower_marks (adm_no TEXT PRIMARY KEY)"
            )

            # 2. Get currently existing columns
            self.db._cursor.execute("PRAGMA table_info(lower_marks)")
            existing_cols = [row[1].lower() for row in self.db._cursor.fetchall()]

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
                    print(f"DEBUG: Adding missing column [{s_col}] to lower_marks...")
                    self.db._cursor.execute(
                        f"ALTER TABLE lower_marks ADD COLUMN {s_col} INTEGER"
                    )

                # Check Rate Column
                if r_col not in existing_cols:
                    print(f"DEBUG: Adding missing column [{r_col}] to lower_marks...")
                    self.db._cursor.execute(
                        f"ALTER TABLE lower_marks ADD COLUMN {r_col} TEXT"
                    )

            # 4. Final check for Totals/Level
            if "total_points" not in existing_cols:
                self.db._cursor.execute(
                    "ALTER TABLE lower_marks ADD COLUMN total_points INTEGER"
                )
            if "average_level" not in existing_cols:
                self.db._cursor.execute(
                    "ALTER TABLE lower_marks ADD COLUMN average_level TEXT"
                )

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
                LEFT JOIN lower_marks m ON s.adm_no = m.adm_no
                WHERE s.grade = ?
            """
            # 1. Fetch data
            # ... (Your existing SQL SELECT query logic here) ...
            self.db._cursor.execute(query, (self.class_name,))
            records = self.db._cursor.fetchall()

            # 2. Rank calculation
            total_idx = 1 + (num_subs * 2)
            scored_students = []
            for row in records:
                score = row[total_idx] if row[total_idx] is not None else -1
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
            final_list.sort(key=lambda x: (x[1] == "-", x[1] if x[1] != "-" else 999))

            # 4. Draw rows in the sorted order
            for row_data, pos in final_list:
                self.add_student_row_with_data(row_data, pos)

        except Exception as e:
            print(f"Loading/Sorting Error: {e}")

    def save_lower_marks(self):
        success_count = 0
        subjects = self.get_subjects_from_json()
        num_subs = len(subjects)

        try:
            for row_frame in self.table_inner.winfo_children():
                if not isinstance(row_frame, ctk.CTkFrame):
                    continue

                # Get Student Name
                widgets = row_frame.grid_slaves(row=0)
                # Sort widgets by column to ensure we read them in order
                widgets.sort(key=lambda w: int(w.grid_info()["column"]))

                if not widgets or widgets[0].cget("text") == "STUDENT NAME":
                    continue
                student_name = widgets[0].cget("text")

                # Get Admission Number
                self.db._cursor.execute(
                    "SELECT adm_no FROM students WHERE name = ?", (student_name,)
                )
                res = self.db._cursor.fetchone()
                if not res:
                    continue
                adm_no = res[0]

                # 1. Collect dynamic marks from Entry boxes
                # We skip index 0 (Name) and take the next (num_subs * 2) widgets
                marks_data = []
                for i in range(1, (num_subs * 2) + 1):
                    val = widgets[i].get()
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

                query = f"INSERT OR REPLACE INTO lower_marks ({', '.join(col_names)}) VALUES ({placeholders})"
                final_data = [adm_no] + marks_data + [total_val, lvl_val]

                self.db._cursor.execute(query, final_data)
                success_count += 1

            self.db.conn.commit()
            messagebox.showinfo("Success", f"Saved marks for {success_count} students.")
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
            title="Save Lower Marksheet",
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
                    subjects = config.get("subjects", {}).get("lower", [])

            if not subjects:
                subjects = ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"]

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
            for row_frame in self.table_inner.winfo_children():
                # Get name from the first widget in the row
                widgets = row_frame.grid_slaves(row=0)
                # Sort widgets by column index because grid_slaves returns them in reverse
                widgets.sort(key=lambda w: int(w.grid_info()["column"]))

                if not widgets or widgets[0].cget("text") == "STUDENT NAME":
                    continue

                # Print Name
                pdf.cell(name_w, 8, widgets[0].cget("text")[:22], 1)

                # Print Subjects (S and R)
                num_sub_widgets = len(subjects) * 2
                for i in range(1, num_sub_widgets + 1):
                    val = widgets[i].get() if hasattr(widgets[i], "get") else ""
                    pdf.cell(sub_col_w, 8, str(val), 1, 0, "C")

                # Print Totals (The last 3 widgets)
                pdf.cell(tot_w, 8, str(widgets[-3].get()), 1, 0, "C")
                pdf.cell(lvl_w, 8, str(widgets[-2].get()), 1, 0, "C")
                pdf.cell(pos_w, 8, str(widgets[-1].get()), 1, 1, "C")

            pdf.output(file_path)
            messagebox.showinfo(
                "Success", f"Report saved to {os.path.basename(file_path)}"
            )

        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate report: {e}")

    def handle_new_exam(self):
        self.save_lower_marks()
        dialog = ctk.CTkInputDialog(
            text="Enter New Exam Title:", title="New Performance Record"
        )
        new_title = dialog.get_input()

        if new_title:
            if messagebox.askyesno(
                "Confirm Reset", f"Clear marks and start {new_title}?"
            ):
                try:
                    # Clear DB marks
                    self.db._cursor.execute(
                        "DELETE FROM lower_marks WHERE adm_no IN (SELECT adm_no FROM students WHERE grade = ?)",
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

                    config["lower_exam_title"] = self.current_exam_title

                    with open(path, "w") as f:
                        json.dump(config, f, indent=4)

                    self.update_header_display()
                    self.load_students_from_registry()
                    messagebox.showinfo("Success", "Exam title saved!")
                except Exception as e:
                    messagebox.showerror("Error", f"Save failed: {e}")
