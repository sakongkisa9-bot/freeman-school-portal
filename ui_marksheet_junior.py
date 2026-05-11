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
import json
from tkinter import filedialog, messagebox
from cloud_service import (
    CloudService,
    ask_cloud_credentials,
    apply_cloud_records_to_table,
)


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
    def __init__(self, parent, db_connection, class_name):
        super().__init__(parent, fg_color="transparent")
        self.db = db_connection
        self.class_name = class_name

        # FIX: Load subjects from JSON immediately
        self.subjects = self.get_subjects_from_json()
        self.current_exam_title = "PERFORMANCE RECORD"
        try:
            import json
            import os

            project_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(project_dir, "school_config.json")
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

        # Canvas for scrolling
        self.canvas_container = ctk.CTkFrame(self, fg_color="gray15")
        self.canvas_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.canvas = ctk.CTkCanvas(
            self.canvas_container, bg="#242424", highlightthickness=0
        )
        self.h_scroll = ctk.CTkScrollbar(
            self.canvas_container, orientation="horizontal", command=self.canvas.xview
        )
        self.v_scroll = ctk.CTkScrollbar(
            self.canvas_container, orientation="vertical", command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set
        )
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.table_inner_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas.create_window((0, 0), window=self.table_inner_frame, anchor="nw")
        self.table_inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.load_students_from_registry()

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
        for child in self.table_inner_frame.winfo_children():
            child.destroy()

        # FIXED DIMENSIONS
        NAME_W = 180
        BOX_SIZE = 45
        TOT_W = 65

        # 1. LOCK THE COLUMNS
        self.table_inner_frame.grid_columnconfigure(0, weight=0, minsize=NAME_W)

        # Header: Name (Use width=NAME_W to prevent expansion)
        ctk.CTkLabel(
            self.table_inner_frame,
            text="STUDENT NAME",
            font=("Arial Bold", 12),
            width=NAME_W,
            fg_color="gray25",
            corner_radius=0,
        ).grid(row=0, column=0, rowspan=2, sticky="nsew", padx=1, pady=1)

        for i, sub in enumerate(self.subjects):
            col_start = 1 + (i * 3)
            self.table_inner_frame.grid_columnconfigure(
                (col_start, col_start + 1, col_start + 2),
                weight=0,
                minsize=BOX_SIZE,
                uniform="subs",
            )

            # Subject Heading (Locked width)
            display_name = sub.upper()[:6]
            ctk.CTkLabel(
                self.table_inner_frame,
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
                    self.table_inner_frame,
                    text=txt,
                    fg_color=color,
                    corner_radius=0,
                    width=BOX_SIZE,
                    height=BOX_SIZE,
                    font=("Arial Bold", 10),
                ).grid(row=1, column=col_start + j, sticky="nsew", padx=1, pady=1)

        # Totals
        total_start = 1 + (len(self.subjects) * 3)
        self.table_inner_frame.grid_columnconfigure(
            (total_start, total_start + 1, total_start + 2), weight=0, minsize=TOT_W
        )

        for j, txt in enumerate(["TOT", "AVG", "RANK"]):
            ctk.CTkLabel(
                self.table_inner_frame,
                text=txt,
                font=("Arial Bold", 11),
                width=TOT_W,
                fg_color="gray20",
                corner_radius=0,
            ).grid(
                row=0, column=total_start + j, rowspan=2, sticky="nsew", padx=1, pady=1
            )

    def add_student_row(self, student_data, row_index):
        grid_row = row_index + 2
        NAME_W = 180
        BOX_SIZE = 45

        # 1. Name Label - CRITICAL: width=NAME_W and anchor="w"
        # This stops long names from pushing the squares to the right
        ctk.CTkLabel(
            self.table_inner_frame,
            text=student_data[0],
            anchor="w",
            padx=10,
            width=NAME_W,
            font=("Arial", 12),
            fg_color="transparent",
        ).grid(row=grid_row, column=0, sticky="nsew", padx=1, pady=1)

        # 2. Subject Entry Boxes (Square)
        num_subjects = len(self.subjects)
        for i in range(1, (num_subjects * 3) + 1):
            color = ["#1a1a1a", "#2c3e50", "#1e3a24"][(i - 1) % 3]

            # Added width=BOX_SIZE here
            e = ctk.CTkEntry(
                self.table_inner_frame,
                width=BOX_SIZE,
                height=BOX_SIZE,
                font=("Arial Bold", 12),
                fg_color=color,
                border_width=0,
                corner_radius=0,
                justify="center",
            )
            e.grid(row=grid_row, column=i, sticky="nsew", padx=1, pady=1)

            if len(student_data) > i and student_data[i] is not None:
                e.insert(0, str(student_data[i]))
                if i % 3 != 1:
                    e.configure(state="disabled")

            if i % 3 == 1:
                e.bind(
                    "<FocusOut>",
                    lambda event, ent=e, col=i, r=grid_row: self.auto_fill_results(
                        ent, col, r
                    ),
                )

        # 3. Totals Boxes
        total_start = 1 + (num_subjects * 3)
        summary_colors = ["gray30", "#1f538d", "#4a1515"]
        for j in range(3):
            col_idx = total_start + j
            val = student_data[col_idx] if len(student_data) > col_idx else ""

            # Added width=65 here
            box = ctk.CTkEntry(
                self.table_inner_frame,
                width=65,
                height=BOX_SIZE,
                fg_color=summary_colors[j],
                font=("Arial Bold", 12),
                border_width=0,
                corner_radius=0,
                justify="center",
            )
            box.insert(0, str(val))
            box.configure(state="disabled")
            box.grid(row=grid_row, column=col_idx, sticky="nsew", padx=1, pady=1)

    def auto_fill_results(self, score_entry, col, row_index):
        # 1. Get the score
        score_val = score_entry.get()

        # 2. Calculate the Grade (Remark) and Points
        # (Assuming your calculate_junior_grade function is available)
        rating_val, points_val = calculate_junior_grade(score_val)

        # 3. Find the Remark (R) and Point (P) widgets
        # We look in the MASTER frame using the absolute row_index and column
        try:
            r_entry = [
                w
                for w in self.table_inner_frame.grid_slaves(
                    row=row_index, column=col + 1
                )
            ][0]
            p_entry = [
                w
                for w in self.table_inner_frame.grid_slaves(
                    row=row_index, column=col + 2
                )
            ][0]

            # 4. Update the widgets
            for ent, val in [(r_entry, rating_val), (p_entry, str(points_val))]:
                ent.configure(state="normal")
                ent.delete(0, "end")
                ent.insert(0, val)
                ent.configure(state="disabled")

            # 5. Trigger the totals update for this specific row
            self.update_totals(row_index)

        except IndexError:
            # This prevents a crash if the grid isn't fully rendered yet
            pass

    def update_totals(self, row_index):
        total_points_sum = 0
        num_subjects = len(self.subjects)

        # 1. Sum up the Points (P) columns
        # Points are in columns 3, 6, 9... (multiples of 3)
        for sub_idx in range(1, num_subjects + 1):
            p_col = sub_idx * 3
            try:
                # We look in the master frame (self.table_inner_frame) using row_index
                widgets = self.table_inner_frame.grid_slaves(
                    row=row_index, column=p_col
                )
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
            # Update Total Points Box
            total_widgets = self.table_inner_frame.grid_slaves(
                row=row_index, column=total_box_col
            )
            if total_widgets:
                total_box = total_widgets[0]
                total_box.configure(state="normal")
                total_box.delete(0, "end")
                total_box.insert(0, str(total_points_sum))
                total_box.configure(state="disabled")

            # 3. Calculate Average Grade
            mean_points = total_points_sum / num_subjects if total_points_sum > 0 else 0
            # Use the same level codes expected by summary distribution
            grades = [
                (7.5, "EE1"),
                (6.5, "EE2"),
                (5.5, "ME1"),
                (4.5, "ME2"),
                (3.5, "AE1"),
                (2.5, "AE2"),
                (1.5, "BE1"),
            ]
            avg_grade = next((g for p, g in grades if mean_points >= p), "BE2")

            # Update Average Level Box (total_box_col + 1)
            avg_widgets = self.table_inner_frame.grid_slaves(
                row=row_index, column=total_box_col + 1
            )
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
                f"WHERE s.grade = ? "
                f"ORDER BY CASE WHEN m.rank IS NULL THEN 1 ELSE 0 END, m.rank ASC"
            )

            self.db._cursor.execute(query, (self.class_name,))
            records = self.db._cursor.fetchall()

            # 1. Clear the UI
            for child in self.table_inner_frame.winfo_children():
                child.destroy()

            # 2. Build the Headers (Occupies Row 0 and Row 1)
            self.create_table_headers()

            # 3. Add Student Rows (Starting from Row 2)
            # 'idx' will tell 'add_student_row' exactly where to sit vertically
            for idx, student in enumerate(records, start=2):
                self.add_student_row(student, idx)

        except Exception as e:
            print(f"Dynamic Load Error: {e}")

    def create_bottom_controls(self):
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_bar.pack(fill="x", side="bottom", padx=20, pady=10)

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
                self.table_inner_frame, marks_data, subjects, columns_per_subject=3
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

        # Force the path to the project folder
        project_dir = os.path.dirname(os.path.realpath(__file__))
        json_path = os.path.join(project_dir, "school_config.json")

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

        # 1. Force the correct Project Directory paths
        project_dir = os.path.dirname(os.path.realpath(__file__))
        json_path = os.path.join(project_dir, "school_config.json")

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
            pdf.cell(0, 10, school_name.upper(), ln=True, align="C")
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(
                0,
                7,
                f"JUNIOR SCHOOL REPORT: {self.class_name.upper()} - {exam_name}",
                ln=True,
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

            pdf.cell(name_w, 12, "STUDENT NAME", 1, 0, "C", True)
            for sub in subjects:
                pdf.cell(sub_col_w * 3, 6, sub[:8], 1, 0, "C", True)

            pdf.cell(10, 12, "TOT", 1, 0, "C", True)
            pdf.cell(15, 12, "AVG", 1, 0, "C", True)
            pdf.cell(10, 12, "POS", 1, 1, "C", True)

            # S | R | P Row logic
            current_y = pdf.get_y()
            pdf.set_xy(10 + name_w, current_y - 6)
            pdf.set_font("Helvetica", "B", 6)
            for _ in subjects:
                pdf.cell(sub_col_w, 6, "S", 1, 0, "C", True)
                pdf.cell(sub_col_w, 6, "R", 1, 0, "C", True)
                pdf.cell(sub_col_w, 6, "P", 1, 0, "C", True)
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
                    name_text = name_widgets[0].cget("text")

                    if not name_text or name_text.upper() == "STUDENT NAME":
                        continue

                    pdf.cell(name_w, 7, name_text[:22], 1)

                    for i in range(1, (num_subs * 3) + 1):
                        cell_widgets = self.table_inner_frame.grid_slaves(
                            row=r, column=i
                        )
                        val = (
                            cell_widgets[0].get()
                            if cell_widgets and hasattr(cell_widgets[0], "get")
                            else ""
                        )
                        pdf.cell(sub_col_w, 7, str(val), 1, 0, "C")

                    total_col_idx = (num_subs * 3) + 1
                    for j in range(3):
                        t_widgets = self.table_inner_frame.grid_slaves(
                            row=r, column=total_col_idx + j
                        )
                        t_val = (
                            t_widgets[0].get()
                            if t_widgets and hasattr(t_widgets[0], "get")
                            else ""
                        )
                        w_val = 15 if j == 1 else 10
                        ln_val = 1 if j == 2 else 0
                        pdf.cell(w_val, 7, str(t_val), 1, ln_val, "C")

                except Exception as row_err:
                    print(f"Skipping PDF row {r}: {row_err}")

            pdf.output(file_path)
            messagebox.showinfo("Success", "PDF generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"PDF Generation Failed: {e}")

    def save_all_marks(self):
        success_count = 0
        subjects = self.get_subjects_from_json()
        num_subs = len(subjects)

        # 1. Get all row indices currently in the grid
        # We start from row 2 because rows 0 and 1 are headers
        all_widgets = self.table_inner_frame.grid_slaves()
        if not all_widgets:
            return

        # Find the highest row index to know how many students we have
        max_row = max(w.grid_info()["row"] for w in all_widgets)

        for r in range(2, max_row + 1):
            try:
                # 2. Find the Student Name Label in this row
                name_widgets = self.table_inner_frame.grid_slaves(row=r, column=0)
                if not name_widgets:
                    continue
                student_name = name_widgets[0].cget("text")

                # 3. Get Admission Number from database
                self.db._cursor.execute(
                    "SELECT adm_no FROM students WHERE name = ?", (student_name,)
                )
                result = self.db._cursor.fetchone()
                if not result:
                    continue
                adm_no = result[0]

                # 4. Collect Marks for each subject
                update_parts = []
                values = []

                for i, sub in enumerate(subjects):
                    col_start = 1 + (i * 3)
                    # Clean the subject name for database column names
                    b = (
                        sub.replace(" ", "_")
                        .replace("-", "_")
                        .lower()
                        .replace("/", "_")
                    )

                    # Get Score(s), Remark(r), and Points(p) from the grid cells
                    s_val = (
                        self.table_inner_frame.grid_slaves(row=r, column=col_start)[
                            0
                        ].get()
                        or "0"
                    )
                    r_val = (
                        self.table_inner_frame.grid_slaves(row=r, column=col_start + 1)[
                            0
                        ].get()
                        or "BE2"
                    )
                    p_val = (
                        self.table_inner_frame.grid_slaves(row=r, column=col_start + 2)[
                            0
                        ].get()
                        or "0"
                    )

                    update_parts.extend([f"{b}_s=?", f"{b}_r=?", f"{b}_p=?"])
                    values.extend([s_val, r_val, p_val])

                # 5. Add the 'total_points' and 'avg_level' for storage (Optional but good)
                total_col = 1 + (num_subs * 3)
                total_points = (
                    self.table_inner_frame.grid_slaves(row=r, column=total_col)[0].get()
                    or "0"
                )
                average_points = (
                    self.table_inner_frame.grid_slaves(row=r, column=total_col + 1)[
                        0
                    ].get()
                    or ""
                )

                update_parts.extend(["total_points=?", "average_points=?"])
                values.extend([total_points, average_points])

                # 6. Execute Update
                values.append(adm_no)
                sql = f"UPDATE marksheet SET {', '.join(update_parts)} WHERE adm_no=?"

                # Ensure record exists
                self.db._cursor.execute(
                    "SELECT 1 FROM marksheet WHERE adm_no=?", (adm_no,)
                )
                if not self.db._cursor.fetchone():
                    self.db._cursor.execute(
                        "INSERT INTO marksheet (adm_no) VALUES (?)", (adm_no,)
                    )

                self.db._cursor.execute(sql, values)
                success_count += 1

            except Exception as e:
                print(f"Error saving row {r}: {e}")
                continue

        self.db.conn.commit()
        self.calculate_rankings()
        messagebox.showinfo("Success", f"Saved {success_count} students.")
        self.load_students_from_registry()

    def calculate_rankings(self):
        """Calculates totals and assigns numerical rank 1, 2, 3..."""
        subjects = self.get_subjects_from_json()

        # Build the sum string for all point columns (e.g., maths_p + eng_p + ...)
        point_cols = [
            f"{s.replace(' ', '_').replace('-', '_').lower().replace('/', '_')}_p"
            for s in subjects
        ]
        sum_query = " + ".join(point_cols)

        # 1. Update total_points for everyone
        self.db._cursor.execute(f"UPDATE marksheet SET total_points = ({sum_query})")

        # 2. Get all students sorted by total_points descending
        self.db._cursor.execute(
            "SELECT adm_no FROM marksheet ORDER BY total_points DESC"
        )
        ranked_students = self.db._cursor.fetchall()

        # 3. Update the 'rank' column with their position
        for i, (adm,) in enumerate(ranked_students, start=1):
            self.db._cursor.execute(
                "UPDATE marksheet SET rank = ? WHERE adm_no = ?", (i, adm)
            )

        self.db.conn.commit()

    def create_new_exam(self):
        dialog = ctk.CTkInputDialog(text="Enter Exam Title:", title="New Exam")
        new_title = dialog.get_input()

        if new_title and messagebox.askyesno(
            "Confirm", f"Reset marks for {self.class_name} and start '{new_title}'?"
        ):
            # 1. Clear the marks in the DB
            self.db._cursor.execute(
                "DELETE FROM marksheet WHERE adm_no IN (SELECT adm_no FROM students WHERE grade = ?)",
                (self.class_name,),
            )
            self.db.conn.commit()

            # 2. Update the variable in the app
            self.current_exam_title = new_title.upper()

            # 3. Save this title to school_config.json permanently
            try:
                import json
                import os

                project_dir = os.path.dirname(os.path.realpath(__file__))
                json_path = os.path.join(project_dir, "school_config.json")

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

            # 4. Refresh the UI
            self.load_students_from_registry()

    def update_header_text(self, exam_title):
        project_dir = os.path.dirname(os.path.realpath(__file__))
        json_path = os.path.join(project_dir, "school_config.json")

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
