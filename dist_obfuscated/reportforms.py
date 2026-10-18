import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import json
import base64
import tempfile
from database import FreemanDB
from cloud_service import CloudService, ask_cloud_credentials
from teacher_comments import build_subject_comment_indices, rating_to_comment as get_rating_comment
from cbc_engine import SUBJECT_TO_LEARNING_AREA
from cbc_report import (
    build_teacher_comments,
    build_subject_results,
    chart_marker_for_subject,
    group_rubric_records,
    normalize_level,
    pathway_recommendation,
)
import datetime


def ask_opening_closing_dates(parent):
    dialog = ctk.CTkToplevel(parent)
    dialog.title("School Dates")
    dialog.geometry("420x250")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.result = None

    ctk.CTkLabel(
        dialog,
        text="Include school opening and closing dates?",
        font=("Arial Bold", 16),
    ).pack(padx=24, pady=(24, 16))

    question_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    question_frame.pack(fill="x", padx=24)

    def finish_without_dates():
        dialog.result = {}
        dialog.destroy()

    def show_date_fields():
        question_frame.pack_forget()
        dialog.geometry("420x330")
        fields_frame.pack(fill="x", padx=24, pady=(8, 12))
        actions_frame.pack(fill="x", padx=24, pady=(0, 20))

    fields_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    opening_entry = ctk.CTkEntry(fields_frame, placeholder_text="e.g. 06/01/2027")
    closing_entry = ctk.CTkEntry(fields_frame, placeholder_text="e.g. 20/04/2027")
    for label_text, entry in (("Opening date", opening_entry), ("Closing date", closing_entry)):
        ctk.CTkLabel(fields_frame, text=label_text, anchor="w").pack(fill="x", pady=(8, 3))
        entry.pack(fill="x")

    actions_frame = ctk.CTkFrame(dialog, fg_color="transparent")

    def accept_dates():
        opening_date = opening_entry.get().strip()
        closing_date = closing_entry.get().strip()
        if not opening_date or not closing_date:
            messagebox.showwarning("Missing dates", "Enter both the opening and closing dates.", parent=dialog)
            return
        dialog.result = {"opening_date": opening_date, "closing_date": closing_date}
        dialog.destroy()

    ctk.CTkButton(
        question_frame, text="No", command=finish_without_dates,
        fg_color="#64748b", hover_color="#475569",
    ).pack(side="left", expand=True, padx=6)
    ctk.CTkButton(
        question_frame, text="Yes", command=show_date_fields,
        fg_color="#287a65", hover_color="#216451",
    ).pack(side="left", expand=True, padx=6)
    ctk.CTkButton(
        actions_frame, text="Cancel", command=dialog.destroy,
        fg_color="#64748b", hover_color="#475569",
    ).pack(side="left", expand=True, padx=6)
    ctk.CTkButton(
        actions_frame, text="Continue", command=accept_dates,
        fg_color="#287a65", hover_color="#216451",
    ).pack(side="left", expand=True, padx=6)

    parent.wait_window(dialog)
    return dialog.result


def ask_report_print_mode(parent):
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Choose Report Format")
    dialog.geometry("460x190")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.result = None
    ctk.CTkLabel(
        dialog, text="Which report should be printed?", font=("Arial Bold", 16),
    ).pack(padx=24, pady=(24, 18))
    actions = ctk.CTkFrame(dialog, fg_color="transparent")
    actions.pack(fill="x", padx=16, pady=(0, 20))
    for label, value, color in (
        ("One-page summary", "summary", "#287a65"),
        ("Full rubric", "full", "#1f538d"),
        ("Cancel", None, "#64748b"),
    ):
        def choose(selected=value):
            dialog.result = selected
            dialog.destroy()

        ctk.CTkButton(
            actions, text=label, command=choose, fg_color=color,
            hover_color="#216451" if value == "summary" else "#153d66" if value == "full" else "#475569",
        ).pack(side="left", expand=True, padx=5)
    parent.wait_window(dialog)
    return dialog.result


class ReportFormsView(ctk.CTkToplevel):
    def __init__(self, parent_window, db):
        super().__init__(parent_window)
        
        self.parent_window = parent_window
        self.db = db
        self.current_class = None
        self.current_student = None
        
        # Initialize proper paths for executable environment
        if getattr(sys, 'frozen', False):
            # Running as executable
            self.USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
            os.makedirs(self.USER_DATA_DIR, exist_ok=True)
        else:
            # Running as script
            self.USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
        
        self.school_config = self.load_school_config()
        self.subject_comment_indices = build_subject_comment_indices(
            self.school_config.get("subjects", {})
        )
        
        # Window configuration
        self.title("Report Forms - Freeman Tech Solutions")
        self.geometry("1200x800")
        
        # Main layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Show class selection initially
        self.show_class_selection()
        
    def load_school_config(self):
        try:
            json_path = os.path.join(self.USER_DATA_DIR, 'school_config.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    return json.load(f)
            else:
                # If config doesn't exist in USER_DATA_DIR, copy from bundled location
                if getattr(sys, 'frozen', False):
                    bundled_config = os.path.join(sys._MEIPASS, "school_config.json")
                else:
                    bundled_config = os.path.join(os.path.dirname(os.path.realpath(__file__)), "school_config.json")
                if os.path.exists(bundled_config):
                    import shutil
                    shutil.copy2(bundled_config, json_path)
                    with open(json_path, 'r') as f:
                        return json.load(f)
        except Exception:
            pass
        return {}
    
    def clear_container(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
    
    def show_class_selection(self):
        self.clear_container()
        self.current_class = None
        
        # Header
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(header_frame, text="Report Forms - Class Selection", 
                                   font=("Arial Bold", 28))
        title_label.pack(side="left", padx=10)
        
        # Send all reports to portal button
        send_all_btn = ctk.CTkButton(header_frame, text="Send All Reports to Portal",
                                    fg_color="#3498db", hover_color="#2980b9",
                                    font=("Arial Bold", 14), height=40,
                                    command=self.send_all_reports_to_portal)
        send_all_btn.pack(side="right", padx=10)
        
        # Print all reports button
        print_all_btn = ctk.CTkButton(header_frame, text="Print All Reports",
                                     fg_color="#27ae60", hover_color="#1e8449",
                                     font=("Arial Bold", 14), height=40,
                                     command=self.print_all_reports)
        print_all_btn.pack(side="right", padx=10)
        
        # Back button
        back_btn = ctk.CTkButton(header_frame, text="← Back to Dashboard",
                                fg_color="#e74c3c", hover_color="#c0392b",
                                font=("Arial Bold", 14), height=40,
                                command=self.return_to_dashboard)
        back_btn.pack(side="right", padx=10)
        
        # Class selection frame
        class_frame = ctk.CTkFrame(self.main_container)
        class_frame.pack(fill="both", expand=True)
        
        # Get available classes
        classes = self.get_available_classes()
        
        # Create class buttons
        for i, class_name in enumerate(classes):
            btn = ctk.CTkButton(class_frame, text=class_name,
                               font=("Arial Bold", 18), height=50,
                               command=lambda c=class_name: self.show_student_list(c))
            btn.pack(fill="x", padx=20, pady=10)
    
    def get_available_classes(self):
        try:
            self.db.cursor().execute('SELECT DISTINCT grade FROM students ORDER BY grade')
            classes = [row[0] for row in self.db.cursor().fetchall()]
            return classes if classes else []
        except Exception as e:
            print(f"Error getting classes: {e}")
            return []
    
    def show_student_list(self, class_name):
        self.current_class = class_name
        self.clear_container()
        
        # Header
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(header_frame, text=f"Report Forms - {class_name}", 
                                   font=("Arial Bold", 28))
        title_label.pack(side="left", padx=10)
        
        # Send all reports for this class to portal button
        send_class_btn = ctk.CTkButton(header_frame, text="Send All Reports for This Class to Portal",
                                      fg_color="#3498db", hover_color="#2980b9",
                                      font=("Arial Bold", 14), height=40,
                                      command=self.send_class_reports_to_portal)
        send_class_btn.pack(side="right", padx=10)
        
        # Print reports for this class button
        print_class_btn = ctk.CTkButton(header_frame, text="Print Reports for This Class",
                                       fg_color="#27ae60", hover_color="#1e8449",
                                       font=("Arial Bold", 14), height=40,
                                       command=self.print_class_reports)
        print_class_btn.pack(side="right", padx=10)
        
        # Back button
        back_btn = ctk.CTkButton(header_frame, text="← Back to Class Selection",
                                fg_color="#e74c3c", hover_color="#c0392b",
                                font=("Arial Bold", 14), height=40,
                                command=self.show_class_selection)
        back_btn.pack(side="right", padx=10)
        
        # Student list frame
        student_frame = ctk.CTkScrollableFrame(self.main_container)
        student_frame.pack(fill="both", expand=True)
        
        # Get students in this class
        students = self.get_students_in_class(class_name)
        
        if not students:
            no_students_label = ctk.CTkLabel(student_frame, text="No students found in this class",
                                            font=("Arial", 16), text_color="gray")
            no_students_label.pack(pady=50)
            return
        
        # Create student rows
        for student in students:
            row_frame = ctk.CTkFrame(student_frame, height=60)
            row_frame.pack(fill="x", padx=20, pady=5)
            
            # Student info
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            name_label = ctk.CTkLabel(info_frame, text=student['name'],
                                      font=("Arial Bold", 16))
            name_label.pack(side="left", padx=10)
            
            adm_label = ctk.CTkLabel(info_frame, text=f"ADM: {student['adm_no']}",
                                     font=("Arial", 14), text_color="gray")
            adm_label.pack(side="left", padx=10)
            
            # View report button
            view_btn = ctk.CTkButton(row_frame, text="View Report",
                                    fg_color="#9b59b6", hover_color="#8e44ad",
                                    width=150, height=40,
                                    command=lambda s=student: self.show_report_form(s))
            view_btn.pack(side="right", padx=10, pady=10)
    
    def get_students_in_class(self, class_name):
        try:
            # Select all columns to see the actual structure
            self.db.cursor().execute('SELECT * FROM students WHERE grade = ? ORDER BY name',
                                   (class_name,))
            rows = self.db.cursor().fetchall()
            print(f"DEBUG get_students_in_class: Found {len(rows)} students for {class_name}")
            if rows:
                print(f"DEBUG get_students_in_class: First row has {len(rows[0])} columns")
                print(f"DEBUG get_students_in_class: Sample row: {rows[0]}")
            students = []
            for row in rows:
                student_data = {
                    'adm_no': row[0], 
                    'name': row[1], 
                    'grade': row[2], 
                    'stream': row[4] if len(row) > 4 and row[4] else 'none'
                }
                # Photo is at column 5 based on debug output
                if len(row) > 5 and row[5]:
                    student_data['photo'] = row[5]
                    print(f"DEBUG: Student {row[1]} has photo: {row[5][:50]}...")
                else:
                    student_data['photo'] = ''
                    print(f"DEBUG: Student {row[1]} has no photo")
                students.append(student_data)
            return students
        except Exception as e:
            print(f"Error getting students: {e}")
            return []
    
    def show_report_form(self, student):
        self.current_student = student
        self.clear_container()

        report_data = self.generate_report_data(student)
        if not report_data:
            messagebox.showinfo("No Report Data", "No assessment marks are available for this student.", parent=self)
            return

        report_window = ctk.CTkToplevel(self)
        report_window.title(f"Report Form - {student['name']}")
        report_window.geometry("1180x850")
        report_window.minsize(900, 650)

        report_container = ctk.CTkFrame(report_window, fg_color="transparent")
        report_container.pack(fill="both", expand=True, padx=16, pady=16)
        navigation = ctk.CTkScrollableFrame(report_container, height=56, orientation="horizontal")
        navigation.pack(fill="x", pady=(4, 8))
        self.create_school_header(report_container, student)
        self.create_student_info(report_container, student)
        page = ctk.CTkScrollableFrame(report_container)
        page.pack(fill="both", expand=True)

        page_specs = [("Summary", "summary", None)]
        page_specs.extend(
            (item["name"], "rubric", item)
            for item in report_data.get("rubric_subjects", [])
        )
        if report_data.get("pathway_recommendation"):
            page_specs.append(("Career Pathways", "pathway", None))

        self.report_page_specs = page_specs
        self.report_page_container = page
        self.report_page_buttons = []
        for index, (label, _kind, _data) in enumerate(page_specs):
            button = ctk.CTkButton(
                navigation,
                text=label,
                height=36,
                width=max(100, min(190, len(label) * 9)),
                command=lambda selected=index: self.show_report_page(selected, report_data),
            )
            button.pack(side="left", padx=4, pady=4)
            self.report_page_buttons.append(button)

        button_frame = ctk.CTkFrame(report_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=(8, 0))

        print_btn = ctk.CTkButton(
            button_frame, text="Print PDF", fg_color="#287a65", hover_color="#216451",
            height=40, width=150,
            command=lambda: self.print_individual_report(student),
        )
        print_btn.pack(side="left", padx=10)

        send_btn = ctk.CTkButton(
            button_frame, text="Send Full Report to Parent", fg_color="#1f538d",
            hover_color="#153d66", height=40, width=210,
            command=lambda: self.send_student_report_to_portal(student),
        )
        send_btn.pack(side="left", padx=10)

        close_btn = ctk.CTkButton(
            button_frame, text="Close", fg_color="#64748b", hover_color="#475569",
            height=40, width=120, command=report_window.destroy,
        )
        close_btn.pack(side="right", padx=10)

        self.show_report_page(0, report_data)

    def show_report_page(self, index, report_data):
        for widget in self.report_page_container.winfo_children():
            widget.destroy()
        for button_index, button in enumerate(self.report_page_buttons):
            button.configure(
                fg_color="#287a65" if button_index == index else "#e5e7eb",
                hover_color="#216451" if button_index == index else "#cbd5e1",
                text_color="white" if button_index == index else "#1f2937",
            )

        _label, kind, page_data = self.report_page_specs[index]
        if kind == "summary":
            self.create_cbc_summary_page(self.report_page_container, report_data)
        elif kind == "rubric":
            self.create_rubric_page(self.report_page_container, page_data)
        else:
            self.create_pathway_page(self.report_page_container, report_data)

    def create_cbc_summary_page(self, container, report_data):
        ctk.CTkLabel(
            container,
            text="Composite rating = 70% formative evidence + 30% summative assessment. "
            "Where no strand is marked, the summative assessment determines the rating.",
            anchor="w", justify="left", wraplength=1050, text_color="#475569",
        ).pack(fill="x", padx=12, pady=(4, 10))

        self.create_cbc_marks_table(container, report_data)
        self.create_subject_history_chart(container, report_data)

        comments = ctk.CTkFrame(
            container, fg_color="#ffffff", border_width=1, border_color="#94a3b8", corner_radius=6
        )
        comments.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(
            comments, text="Class Teacher Comment", font=("Arial Bold", 12), anchor="w", text_color="#111827"
        ).pack(
            fill="x", padx=12, pady=(8, 2)
        )
        teacher_comments = report_data.get("teacher_comments") or build_teacher_comments(
            report_data.get("subject_results", []), report_data.get("rubric_subjects", []),
            self.current_student.get("name", ""),
        )
        ctk.CTkLabel(
            comments, text=teacher_comments["class_teacher"], anchor="w", justify="left",
            wraplength=1000, text_color="#111827",
        ).pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(
            comments, text="Head Teacher Comment", font=("Arial Bold", 12), anchor="w", text_color="#111827"
        ).pack(
            fill="x", padx=12, pady=(4, 2)
        )
        ctk.CTkLabel(
            comments, text=teacher_comments["head_teacher"], anchor="w", justify="left",
            wraplength=1000, text_color="#111827",
        ).pack(fill="x", padx=12, pady=(0, 8))
        self.create_signature_section(container, self.current_student)

    def create_cbc_marks_table(self, container, report_data):
        table = ctk.CTkFrame(container, fg_color="white", border_width=1, border_color="#d1d5db")
        table.pack(fill="x", padx=12, pady=4)
        previous = list(reversed(report_data.get("previous_exams", [])[:2]))
        current_exam = report_data.get("exam_title", "Current Exam")
        widths = [190] + [105] * len(previous) + [120, 100, 125, 70, 110]
        for column, width in enumerate(widths):
            table.grid_columnconfigure(column, weight=width)

        learning_area_header = ctk.CTkLabel(
            table, text="Learning Area", width=widths[0], height=68, fg_color="#2e7d32",
            text_color="white", font=("Arial Bold", 10), wraplength=widths[0] - 8,
            border_width=1, border_color="#111827",
        )
        learning_area_header.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=1, pady=1)
        for index, exam in enumerate(previous, start=1):
            ctk.CTkLabel(
                table, text=exam.get("exam_name", "Previous"), width=widths[index], height=68, fg_color="#2e7d32",
                text_color="white", font=("Arial Bold", 10), wraplength=widths[index] - 8,
                border_width=1, border_color="#111827",
            ).grid(row=0, column=index, rowspan=2, sticky="nsew", padx=1, pady=1)

        current_start = 1 + len(previous)
        current_columns = ("Formative (70%)", "Summative (30%)", "Composite (Total)", "Level")
        ctk.CTkLabel(
            table, text=current_exam, height=32, fg_color="#1b5e20", text_color="white",
            font=("Arial Bold", 11), border_width=1, border_color="#111827",
        ).grid(row=0, column=current_start, columnspan=4, sticky="nsew", padx=1, pady=1)
        ctk.CTkLabel(
            table, text="Improvement", width=widths[-1], height=68, fg_color="#2e7d32",
            text_color="white", font=("Arial Bold", 10), wraplength=widths[-1] - 8,
            border_width=1, border_color="#111827",
        ).grid(row=0, column=current_start + 4, rowspan=2, sticky="nsew", padx=1, pady=1)
        for offset, heading in enumerate(current_columns):
            column = current_start + offset
            ctk.CTkLabel(
                table, text=heading, width=widths[column], height=34, fg_color="#2e7d32",
                text_color="white", font=("Arial Bold", 10), wraplength=widths[column] - 8,
                border_width=1, border_color="#111827",
            ).grid(row=1, column=column, sticky="nsew", padx=1, pady=1)

        latest_previous = report_data.get("previous_exams", [])
        latest_previous_marks = latest_previous[0].get("marks", {}) if latest_previous else {}
        for row_index, result in enumerate(report_data.get("subject_results", []), start=2):
            values = [result["subject"]]
            for exam in previous:
                values.append(self._previous_subject_score(exam.get("marks", {}), result["subject"]))
            current_score = result.get("composite_score")
            previous_score = self._previous_subject_score(latest_previous_marks, result["subject"])
            improvement = "-"
            if current_score is not None:
                try:
                    difference = int(round(float(current_score) - float(previous_score)))
                    improvement = f"+{difference}" if difference > 0 else str(difference)
                except (TypeError, ValueError):
                    pass
            values.extend((
                result.get("formative", "n/a"),
                result.get("summative", ""),
                "-" if current_score is None else str(current_score),
                result.get("rating", ""),
                improvement,
            ))
            background = "#f8fafc" if row_index % 2 else "white"
            for column, (value, width) in enumerate(zip(values, widths)):
                is_level = column == current_start + 3
                level = normalize_level(value) if is_level else ""
                ctk.CTkLabel(
                    table, text=str(value), width=width, height=34, fg_color=self._level_color(level) if level else background,
                    text_color="white" if level else "#1f2937", anchor="w" if column == 0 else "center",
                    wraplength=width - 8, border_width=1, border_color="#111827",
                ).grid(row=row_index, column=column, sticky="nsew", padx=1, pady=1)

    def create_subject_history_chart(self, container, report_data):
        section = ctk.CTkFrame(container, fg_color="transparent")
        section.pack(fill="x", padx=12, pady=(14, 4))
        ctk.CTkLabel(section, text="Subject Progress History", font=("Arial Bold", 16)).pack(
            anchor="w", pady=(0, 2)
        )
        ctk.CTkLabel(
            section, text="Composite score (%) across exams", text_color="#334155", anchor="w",
        ).pack(fill="x", pady=(0, 6))
        canvas = tk.Canvas(section, height=310, background="white", highlightthickness=1, highlightbackground="#d1d5db")
        canvas.pack(fill="x", expand=True)
        self._draw_subject_history(canvas, report_data)
        canvas.bind("<Configure>", lambda _event: self._draw_subject_history(canvas, report_data))

    def _draw_subject_history(self, canvas, report_data):
        canvas.delete("all")
        history = report_data.get("performance_history", [])
        if not history:
            canvas.create_text(24, 30, anchor="nw", text="No subject history is available yet.", fill="#475569")
            return
        width = max(canvas.winfo_width(), 850)
        left, right, top, bottom = 64, width - 245, 30, 250
        canvas.create_text(left + 2, top - 10, text="Composite (%)", anchor="sw", fill="#334155")
        for value in range(0, 101, 20):
            y = bottom - (bottom - top) * value / 100
            canvas.create_line(left, y, right, y, fill="#e2e8f0")
            canvas.create_text(left - 8, y, text=str(value), anchor="e", fill="#475569")
        canvas.create_line(left, top, left, bottom, fill="#475569")
        canvas.create_line(left, bottom, right, bottom, fill="#475569")

        palette = ["#166534", "#2563eb", "#c2410c", "#9333ea", "#0891b2", "#be123c", "#4d7c0f", "#0f766e", "#a16207"]
        subjects = report_data.get("subjects", [])
        subject_labels = report_data.get("subject_labels", {})
        for index, exam in enumerate(history):
            x = left + (right - left) * index / max(1, len(history) - 1)
            canvas.create_text(x, bottom + 12, text=exam.get("name", "Exam"), anchor="n", width=100, fill="#334155")
        for subject_index, subject in enumerate(subjects):
            display_subject = subject_labels.get(subject, subject)
            color = palette[subject_index % len(palette)]
            points = []
            for exam_index, exam in enumerate(history):
                score = exam.get("subjects", {}).get(subject)
                if score is None:
                    continue
                x = left + (right - left) * exam_index / max(1, len(history) - 1)
                y = bottom - (bottom - top) * max(0, min(100, float(score))) / 100
                points.append((x, y))
            for first, second in zip(points, points[1:]):
                canvas.create_line(*first, *second, fill=color, width=2)
            for marker_index, (x, y) in enumerate(points):
                if subject_index % 3 == 0:
                    canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="white")
                elif subject_index % 3 == 1:
                    canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4, fill=color, outline="white")
                else:
                    canvas.create_polygon(x, y - 5, x + 5, y + 4, x - 5, y + 4, fill=color, outline="white")
            if points:
                x, y = points[-1]
                canvas.create_text(
                    right + 10, y, text=display_subject, anchor="w", width=220,
                    fill=color, font=("Arial", 9, "bold"),
                )

    def create_rubric_page(self, container, subject):
        ctk.CTkLabel(
            container, text=subject["name"], font=("Arial Bold", 20), text_color="#2e7d32",
        ).pack(anchor="w", padx=12, pady=(12, 6))
        ctk.CTkLabel(
            container, text="Each X marks the learner's recorded level for a sub-strand.",
            text_color="#475569", anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))
        if not subject.get("strands"):
            ctk.CTkLabel(container, text="No strand ratings are available for this learning area and term.", text_color="#64748b").pack(pady=24)
            return

        colors = {"BE": "#b91c1c", "AE": "#c2410c", "ME": "#1d4ed8", "EE": "#15803d"}
        for strand in subject["strands"]:
            ctk.CTkLabel(
                container, text=strand["name"], font=("Arial Bold", 14),
                fg_color="#e8f5e9", text_color="#14532d", anchor="w",
            ).pack(fill="x", padx=12, pady=(8, 2))
            table = ctk.CTkFrame(container, fg_color="white", border_width=1, border_color="#d1d5db")
            table.pack(fill="x", padx=12, pady=(0, 4))
            headers = (("Sub-strand", 380), ("BE (1)", 86), ("AE (2)", 86), ("ME (3)", 86), ("EE (4)", 86))
            for col, (label, col_width) in enumerate(headers):
                ctk.CTkLabel(table, text=label, width=col_width, height=34, fg_color="#2e7d32", text_color="white", font=("Arial Bold", 10)).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)
            for row_index, row in enumerate(strand["sub_strands"], start=1):
                cells = [row["name"]]
                cells.extend("X" if row.get("level") == level else "" for level in ("BE", "AE", "ME", "EE"))
                for col, ((label, col_width), value) in enumerate(zip(headers, cells)):
                    level = row.get("level") if 1 <= col <= 4 else ""
                    ctk.CTkLabel(
                        table, text=value, width=col_width, height=32,
                        fg_color=colors.get(level, "#f8fafc" if row_index % 2 else "white"),
                        text_color="white" if level else "#334155",
                        anchor="w" if col == 0 else "center", wraplength=col_width - 8,
                    ).grid(row=row_index, column=col, sticky="nsew", padx=1, pady=1)
        recommendations = subject.get("recommendations", [])
        if recommendations:
            names = ", ".join(
                f"{item['name']} ({item['level']})" for item in recommendations
            )
            text = f"Revisit these sub-strands: {names}."
        else:
            text = "No specific revisit recommendation: the recorded levels do not show a lower-level variation."
        ctk.CTkLabel(
            container, text=text, fg_color="#fff7ed", text_color="#9a3412",
            anchor="w", justify="left", wraplength=1000,
        ).pack(fill="x", padx=12, pady=12)

    def create_pathway_page(self, container, report_data):
        recommendation = report_data.get("pathway_recommendation", {})
        ctk.CTkLabel(
            container, text="Junior Career Pathways", font=("Arial Bold", 20),
            text_color="#2e7d32",
        ).pack(anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            container,
            text=f"Indicative pathway: {recommendation.get('recommended') or 'Not enough ratings'}\n{recommendation.get('basis', '')}",
            anchor="w", justify="left", wraplength=1000, fg_color="#e8f5e9",
        ).pack(fill="x", padx=12, pady=8)
        score_lookup = {item["subject"]: item.get("composite_score") for item in report_data.get("subject_results", [])}
        aliases = {
            "MATH": "Mathematics", "MAT": "Mathematics", "ENG": "English",
            "KISW": "Kiswahili", "SCIE": "Science & Technology", "INT SCIE": "Integrated Science",
            "PRE-TECH": "Pre-Technical Studies", "AGRI": "Agriculture and Nutrition",
            "SST": "Social Studies", "C/A": "Creative Arts and Sports", "REL": "Religious Education",
            "CRE": "Religious Education", "RE": "Religious Education",
            "IRE": "Religious Education", "HRE": "Religious Education",
        }
        for pathway in recommendation.get("pathways", []):
            score = pathway.get("score")
            panel = ctk.CTkFrame(container, fg_color="#f8fafc", border_width=1, border_color="#cbd5e1", corner_radius=6)
            panel.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(panel, text=f"{pathway['name']}  |  {score if score is not None else 'No evidence'}%", font=("Arial Bold", 15), anchor="w").pack(fill="x", padx=12, pady=(8, 4))
            for subject in pathway["subjects"]:
                match = next((name for name in score_lookup if aliases.get(name, name) == subject), None)
                mark = score_lookup.get(match) if match else None
                ctk.CTkLabel(
                    panel, text=f"{subject}: {mark:g}%" if mark is not None else f"{subject}: no recorded composite",
                    anchor="w", text_color="#475569",
                ).pack(fill="x", padx=18, pady=1)
    
    def create_school_header(self, container, student):
        # Header frame matching portal layout with purple gradient
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        # Content frame with padding
        content_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=10)

        # School logo (left) with purple border
        logo_frame = ctk.CTkFrame(content_frame, width=100, height=100, 
                                  fg_color="#f5f7fa", border_width=3, border_color="#667eea",
                                  corner_radius=12)
        logo_frame.pack(side="left", padx=10)

        try:
            logo_path = self.school_config.get('logo', '')
            if logo_path and os.path.exists(logo_path):
                logo_photo = ctk.CTkImage(Image.open(logo_path), size=(80, 80))
                logo_label = ctk.CTkLabel(logo_frame, image=logo_photo, text="")
                logo_label.pack(pady=10)
            else:
                logo_label = ctk.CTkLabel(logo_frame, text="SCHOOL\nLOGO",
                                         font=("Arial Bold", 10), text_color="#666")
                logo_label.pack(pady=20)
        except:
            logo_label = ctk.CTkLabel(logo_frame, text="SCHOOL\nLOGO",
                                     font=("Arial Bold", 10), text_color="#666")
            logo_label.pack(pady=20)

        # School info (center) - matching portal centering
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10)

        school_name = self.school_config.get('school_name', 'School Name')
        school_name_label = ctk.CTkLabel(info_frame, text=school_name.upper(),
                                        font=("Arial Bold", 20), text_color="#667eea")
        school_name_label.pack(pady=2)

        address = self.school_config.get('address', '')
        if address:
            addr_label = ctk.CTkLabel(info_frame, text=address,
                                     font=("Arial", 13), text_color="#000000")
            addr_label.pack(pady=1)

        contacts = self.school_config.get('contacts', '')
        if contacts:
            contact_label = ctk.CTkLabel(info_frame, text=contacts,
                                        font=("Arial", 13), text_color="#000000")
            contact_label.pack(pady=1)

        # Student photo (right) with purple border
        photo_frame = ctk.CTkFrame(content_frame, width=100, height=120, 
                                   fg_color="#f5f7fa", border_width=3, border_color="#764ba2",
                                   corner_radius=12)
        photo_frame.pack(side="right", padx=10)

        student_photo = student.get('photo', '')
        if student_photo and os.path.exists(student_photo):
            try:
                photo_img = ctk.CTkImage(Image.open(student_photo), size=(80, 100))
                photo_label = ctk.CTkLabel(photo_frame, image=photo_img, text="")
                photo_label.pack(pady=10)
            except Exception as e:
                print(f"Error loading student photo: {e}")
                photo_label = ctk.CTkLabel(photo_frame, text="STUDENT\nPHOTO",
                                         font=("Arial Bold", 10), text_color="#666")
                photo_label.pack(pady=20)
        else:
            photo_label = ctk.CTkLabel(photo_frame, text="STUDENT\nPHOTO",
                                     font=("Arial Bold", 10), text_color="#666")
            photo_label.pack(pady=20)
    
    def create_student_info(self, container, student):
        # Student metadata frame matching portal styling with gradient background
        info_frame = ctk.CTkFrame(container, fg_color="#f5f7fa", corner_radius=12)
        info_frame.pack(fill="x", pady=(0, 10), padx=20)

        # Content frame with padding
        content_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=15)

        # Student details in horizontal row (matching portal metadata)
        details = [
            ("Name:", student.get('name', '')),
            ("Class:", student.get('grade', '')),
            ("Stream:", student.get('stream', 'none')),
        ]

        for i, (label, value) in enumerate(details):
            label_widget = ctk.CTkLabel(content_frame, text=label, font=("Arial Bold", 13), text_color="#667eea")
            label_widget.pack(side="left", padx=(0, 5))

            value_widget = ctk.CTkLabel(content_frame, text=value, font=("Arial", 13), text_color="#000000")
            value_widget.pack(side="left", padx=(0, 20))
    
    def get_class_teacher(self, class_name):
        try:
            # Get the first teacher from the teachers linked list for this class
            self.db.cursor().execute('SELECT teacher_name FROM teachers WHERE class_name = ? ORDER BY id ASC LIMIT 1',
                                   (class_name,))
            result = self.db.cursor().fetchone()
            return result[0] if result else ""
        except Exception as e:
            print(f"Error getting class teacher: {e}")
            return ""

    def get_teacher_assignments(self, class_name):
        """Get teacher assignments for all subjects in a class"""
        try:
            self.db.cursor().execute('SELECT subject, teacher_name FROM teachers WHERE class_name = ?',
                                   (class_name,))
            assignments = self.db.cursor().fetchall()
            # Create a dictionary mapping subject to teacher name
            teacher_map = {row[0]: row[1] for row in assignments}
            return teacher_map
        except Exception as e:
            print(f"Error getting teacher assignments: {e}")
            return {}

    def rating_to_comment(self, rating, subject=None):
        return get_rating_comment(rating, subject, self.subject_comment_indices)

    def get_class_teacher_comment(self, average_level):
        """Get class teacher comment based on average level"""
        normalized = normalize_level(average_level)
        if normalized:
            average_level = f"{normalized}1"
        comments = {
            "EE1": "Outstanding performance! You have shown a deep and advanced understanding of all subjects.",
            "EE2": "Excellent work! You are consistently performing at a very high level. Keep it up!",
            "ME1": "Good work! You have a solid grasp of the core concepts. Keep up the steady progress.",
            "ME2": "Good effort! You are making steady progress and engaging well with your lessons.",
            "AE1": "You are making progress. Focus on the finer details to reach full mastery.",
            "AE2": "A promising performance. Keep practicing to strengthen your understanding of these topics.",
            "BE1": "You are starting to grasp the basics. Let's keep working together to build your confidence.",
            "BE2": "A beginning step in your learning journey. Stay dedicated, and we will work on the fundamentals."
        }
        return comments.get(average_level, "No comment available.")

    def get_head_teacher_comment(self, average_level):
        """Get head teacher comment based on average level"""
        normalized = normalize_level(average_level)
        if normalized:
            average_level = f"{normalized}1"
        comments = {
            "EE1": "Excellent achievement. Continue to maintain this high standard of excellence.",
            "EE2": "A remarkable performance this term. Well done on your hard work.",
            "ME1": "You are meeting expectations well. Continue to be consistent in your studies.",
            "ME2": "You are performing well. Keep up the consistency as you prepare for the next term.",
            "AE1": "Good effort shown. With more focus, I am confident you will meet expectations soon.",
            "AE2": "You are close to the target level. Keep working hard and stay focused.",
            "BE1": "I see potential in your work. Let's strive to meet the expected goals next term.",
            "BE2": "There is potential for growth. We will provide the support needed to improve next term."
        }
        return comments.get(average_level, "No comment available.")
    
    def create_current_marks_section(self, container, student):
        # Get report data to include previous exams
        report_data = self.generate_report_data(student)
        if not report_data:
            return

        section_frame = ctk.CTkFrame(container, fg_color="#f8f9fa")
        section_frame.pack(fill="x", pady=(0, 10))

        # Create unified marks table matching PDF layout
        self.create_unified_marks_table(section_frame, report_data)

    def create_unified_marks_table(self, container, report_data):
        """Create a unified marks table matching PDF layout with current and previous exams"""
        current_marks = report_data.get('current_marks', {})
        previous_exams = report_data.get('previous_exams', [])
        exam_title = report_data.get('exam_title', 'CURRENT')
        grade = report_data.get('grade', '')

        # Get subjects for this grade
        subjects = self.get_subjects_for_grade(grade)

        def subject_token(value):
            return "".join(character for character in str(value).upper() if character.isalnum())

        current_subject_keys = {
            subject_token(key[:-2]): key[:-2]
            for key in current_marks
            if key.endswith('_s')
        }

        def current_subject_key(subject):
            return current_subject_keys.get(
                subject_token(subject),
                subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'),
            )

        def previous_subject_mark(exam_marks, subject, mark_type):
            if not isinstance(exam_marks, dict):
                return ''
            target = subject_token(subject)
            for key, mark in exam_marks.items():
                if subject_token(key) == target and isinstance(mark, dict):
                    return mark.get(mark_type, '')
            return ''

        def exam_total(exam_col):
            if exam_col['is_current']:
                suffix = '_p' if is_junior else '_s'
                total = 0
                for subject in subjects:
                    try:
                        total += float(current_marks.get(f"{current_subject_key(subject)}{suffix}") or 0)
                    except (TypeError, ValueError):
                        pass
                return total

            saved_total = exam_col.get('total_points')
            try:
                if saved_total not in (None, '', '-'):
                    return float(saved_total)
            except (TypeError, ValueError):
                pass

            mark_type = 'points' if is_junior else 'score'
            total = 0
            for subject in subjects:
                try:
                    total += float(previous_subject_mark(exam_col['marks'], subject, mark_type) or 0)
                except (TypeError, ValueError):
                    pass
            return total

        # Determine if junior (has points)
        is_junior = grade.lower() in ["grade 7", "grade 8", "grade 9"]

        # Prepare exam columns (previous + current)
        exam_cols = []
        if previous_exams and len(previous_exams) >= 2:
            exam_cols.append({**previous_exams[1], 'name': previous_exams[1].get('exam_name', ''), 'marks': previous_exams[1].get('marks', {}), 'total_points': previous_exams[1].get('total_points', ''), 'is_current': False})
        if previous_exams and len(previous_exams) >= 1:
            exam_cols.append({**previous_exams[0], 'name': previous_exams[0].get('exam_name', ''), 'marks': previous_exams[0].get('marks', {}), 'total_points': previous_exams[0].get('total_points', ''), 'is_current': False})
        exam_cols.append({'name': exam_title, 'marks': current_marks, 'total_points': None, 'is_current': True})

        # Table frame with portal styling
        table_frame = ctk.CTkFrame(container, fg_color="white", corner_radius=12)
        table_frame.pack(fill="x", padx=20, pady=10)

        # Calculate column widths for proper alignment
        subject_width = 90
        exam_width = 54
        rate_width = 40
        points_width = 40 if is_junior else 0
        improve_width = 56
        teacher_width = 75
        comment_width = 230
        teacher_map = self.get_teacher_assignments(grade)

        # Header row with portal purple gradient (simulated with solid color)
        header_line_count = max(
            1,
            *(len(str(exam_col['name'])) // max(1, (exam_width - 6) // 6) + 1 for exam_col in exam_cols),
        )
        header_frame = ctk.CTkFrame(
            table_frame,
            fg_color="#667eea",
            height=max(35, header_line_count * 15 + 10),
            corner_radius=12,
        )
        header_frame.pack(fill="x", padx=5, pady=5)
        header_frame.pack_propagate(False)

        # Header labels with fixed widths for alignment
        header_label = ctk.CTkLabel(header_frame, text="Learning Area", font=("Arial Bold", 10), text_color="#ffffff", width=subject_width, anchor="center")
        header_label.pack(side="left", padx=2)

        for exam_col in exam_cols:
            header_label = ctk.CTkLabel(
                header_frame,
                text=exam_col['name'],
                font=("Arial Bold", 10),
                text_color="#ffffff",
                width=exam_width,
                height=max(28, header_line_count * 14),
                anchor="center",
                wraplength=exam_width - 6,
            )
            header_label.pack(side="left", padx=2)

        header_label = ctk.CTkLabel(header_frame, text="Rate", font=("Arial Bold", 10), text_color="#ffffff", width=rate_width, anchor="center")
        header_label.pack(side="left", padx=2)

        if is_junior:
            header_label = ctk.CTkLabel(header_frame, text="Points", font=("Arial Bold", 10), text_color="#ffffff", width=points_width, anchor="center")
            header_label.pack(side="left", padx=2)

        header_label = ctk.CTkLabel(header_frame, text="Improve", font=("Arial Bold", 10), text_color="#ffffff", width=improve_width, anchor="center")
        header_label.pack(side="left", padx=2)

        header_label = ctk.CTkLabel(header_frame, text="Teacher", font=("Arial Bold", 10), text_color="#ffffff", width=teacher_width, anchor="center")
        header_label.pack(side="left", padx=2)

        header_label = ctk.CTkLabel(header_frame, text="Teachers Comments", font=("Arial Bold", 10), text_color="#ffffff", width=comment_width, anchor="center")
        header_label.pack(side="left", padx=2)

        # Data rows with alternating colors
        for i, subject in enumerate(subjects):
            row_bg = "#f9f9f9" if i % 2 == 0 else "white"
            row_frame = ctk.CTkFrame(table_frame, fg_color=row_bg)
            row_frame.pack(fill="x", pady=1)

            subject_key = current_subject_key(subject)
            current_score = current_marks.get(f'{subject_key}_s', '')
            current_rating = current_marks.get(f'{subject_key}_r', '')
            current_points = current_marks.get(f'{subject_key}_p', '')

            comment = self.rating_to_comment(current_rating, subject) if current_rating else 'No comment'
            comment_lines = max(1, len(comment) // max(1, comment_width // 7) + 1)
            row_height = max(32, comment_lines * 15 + 8)

            # Subject name
            subject_label = ctk.CTkLabel(row_frame, text=subject, font=("Arial", 9), width=subject_width, height=row_height, anchor="center", text_color="#000000", wraplength=subject_width - 8)
            subject_label.pack(side="left", padx=2)

            # Previous exam scores
            for exam_col in exam_cols:
                if not exam_col['is_current']:
                    exam_marks = exam_col['marks']
                    score = ""
                    if isinstance(exam_marks, dict):
                        score = previous_subject_mark(exam_marks, subject, 'score')
                    score_label = ctk.CTkLabel(row_frame, text=str(score), font=("Arial", 9), width=exam_width, height=row_height, anchor="center", text_color="#000000")
                    score_label.pack(side="left", padx=2)

            # Current exam score, rating, points
            score_label = ctk.CTkLabel(row_frame, text=str(current_score), font=("Arial", 9), width=exam_width, height=row_height, anchor="center", text_color="#000000")
            score_label.pack(side="left", padx=2)

            rating_label = ctk.CTkLabel(row_frame, text=str(current_rating), font=("Arial", 9), width=rate_width, height=row_height, anchor="center", text_color="#000000")
            rating_label.pack(side="left", padx=2)

            if is_junior:
                points_label = ctk.CTkLabel(row_frame, text=str(current_points), font=("Arial", 9), width=points_width, height=row_height, anchor="center", text_color="#000000")
                points_label.pack(side="left", padx=2)

            # Improvement
            improvement = "-"
            if previous_exams and len(previous_exams) > 0:
                latest_prev_marks = previous_exams[0].get('marks', {})
                prev_score = previous_subject_mark(latest_prev_marks, subject, 'score')
                try:
                    if current_score not in ('', None, '-') and prev_score not in ('', None, '-'):
                        diff = float(current_score) - float(prev_score)
                        improvement = f"+{diff:g}" if diff > 0 else (f"{diff:g}" if diff < 0 else '-')
                except (TypeError, ValueError):
                    pass

            improve_label = ctk.CTkLabel(row_frame, text=improvement, font=("Arial", 9), width=improve_width, height=row_height, anchor="center", text_color="#000000")
            improve_label.pack(side="left", padx=2)

            # Teacher name
            teacher_name = teacher_map.get(subject, 'N/A')
            teacher_label = ctk.CTkLabel(row_frame, text=teacher_name, font=("Arial", 9), width=teacher_width, height=row_height, anchor="center", text_color="#000000", wraplength=teacher_width - 8)
            teacher_label.pack(side="left", padx=2)

            # Teacher comment
            comment_label = ctk.CTkLabel(row_frame, text=comment, font=("Arial", 8), width=comment_width, height=row_height, anchor="w", justify="left", wraplength=comment_width - 10, text_color="#000000")
            comment_label.pack(side="left", padx=2)

        # Summary row with portal gradient styling
        summary_frame = ctk.CTkFrame(table_frame, fg_color="#f5f7fa", height=30, corner_radius=8)
        summary_frame.pack(fill="x", padx=5, pady=(10, 5))

        # Calculate totals
        current_total = exam_total(exam_cols[-1])
        total_label = "TOTAL POINTS" if is_junior else "TOTAL SCORES"

        avg_level = current_marks.get('average_points', '') or current_marks.get('average_level', '')

        total_label_widget = ctk.CTkLabel(summary_frame, text=total_label, font=("Arial Bold", 10), width=subject_width, anchor="center", text_color="#000000")
        total_label_widget.pack(side="left", padx=2)

        # Previous exam totals
        for exam_col in exam_cols:
            if not exam_col['is_current']:
                previous_total = exam_total(exam_col)
                total_label_widget = ctk.CTkLabel(
                    summary_frame,
                    text=f"{previous_total:g}" if previous_total else "-",
                    font=("Arial Bold", 10),
                    width=exam_width,
                    anchor="center",
                    text_color="#000000",
                )
                total_label_widget.pack(side="left", padx=2)

        # Current total
        current_total_label = ctk.CTkLabel(summary_frame, text=f"{current_total:g}" if current_total else "-", font=("Arial Bold", 10), width=exam_width, anchor="center", text_color="#000000")
        current_total_label.pack(side="left", padx=2)

        # Average level
        avg_label = ctk.CTkLabel(summary_frame, text=avg_level, font=("Arial Bold", 10), width=rate_width, anchor="center", text_color="#000000")
        avg_label.pack(side="left", padx=2)

        if is_junior:
            points_label = ctk.CTkLabel(summary_frame, text=f"{current_total:g}" if current_total else "-", font=("Arial Bold", 10), width=points_width, anchor="center", text_color="#000000")
            points_label.pack(side="left", padx=2)

        # Fill remaining cells with dashes
        for _ in range(3):  # Improve, Teacher, Comments
            dash_label = ctk.CTkLabel(summary_frame, text="-", font=("Arial", 10), width=improve_width if _ == 0 else (teacher_width if _ == 1 else comment_width), anchor="center", text_color="#000000")
            dash_label.pack(side="left", padx=2)

        # Performance History section
        history_section = ctk.CTkFrame(container, fg_color="transparent")
        history_section.pack(fill="x", padx=20, pady=10)

        history_title = ctk.CTkLabel(history_section, text="Performance History",
                                     font=("Arial Bold", 16), text_color="#667eea")
        history_title.pack(pady=(0, 10), anchor="w")

        # Simple performance chart (bar chart using frames)
        chart_frame = ctk.CTkFrame(history_section, fg_color="white", border_width=2, border_color="#667eea", corner_radius=12)
        chart_frame.pack(fill="x", pady=(0, 10))

        # Use the same subject score/points totals as the report table and PDF.
        performance_data = [
            {"name": exam_col["name"], "total": exam_total(exam_col)}
            for exam_col in exam_cols
        ]

        if performance_data:
            max_total = max((item["total"] for item in performance_data), default=0) or 1
            max_label_lines = max(
                1, max((len(item["name"]) + 19) // 20 for item in performance_data)
            )
            label_height = max(28, max_label_lines * 12)
            chart_content_height = max(190, 190 + label_height - 28)
            chart_content = ctk.CTkFrame(chart_frame, fg_color="transparent")
            chart_content.pack(fill="x", padx=15, pady=15)
            bar_container = ctk.CTkFrame(
                chart_content, fg_color="transparent", height=chart_content_height
            )
            bar_container.pack(fill="x")
            bar_container.pack_propagate(False)

            for data in performance_data:
                ratio = data["total"] / max_total
                bar_color = "#22c55e" if ratio >= 0.8 else "#eab308" if ratio >= 0.5 else "#ef4444"
                column = ctk.CTkFrame(
                    bar_container,
                    fg_color="transparent",
                    width=135,
                    height=chart_content_height,
                )
                column.pack(side="left", padx=8, fill="y")
                column.pack_propagate(False)

                total_label = ctk.CTkLabel(
                    column, text=f"{data['total']:g}", font=("Arial Bold", 10), text_color="#000000"
                )
                total_label.pack(side="top", pady=(0, 4))

                track = ctk.CTkFrame(column, fg_color="#e5e7eb", width=34, height=120, corner_radius=3)
                track.pack(side="top", expand=True)
                track.pack_propagate(False)
                ctk.CTkFrame(
                    track,
                    fg_color=bar_color,
                    width=34,
                    height=max(3, int(110 * ratio)) if data["total"] > 0 else 3,
                    corner_radius=3,
                ).place(relx=0.5, rely=1, anchor="s")

                exam_label = ctk.CTkLabel(
                    column,
                    text=data["name"],
                    font=("Arial", 9),
                    text_color="#000000",
                    width=125,
                    height=max(28, ((len(data["name"]) + 19) // 20) * 12),
                    wraplength=125,
                )
                exam_label.pack(side="bottom", pady=(4, 0))

        # Teacher and Administrator Comments section
        comments_section = ctk.CTkFrame(container, fg_color="transparent")
        comments_section.pack(fill="x", padx=20, pady=10)

        comments_title = ctk.CTkLabel(comments_section, text="Teacher and Administrator Comments",
                                     font=("Arial Bold", 16), text_color="#667eea")
        comments_title.pack(pady=(0, 10), anchor="w")

        # Get average level
        avg_level = current_marks.get('average_points', '') or current_marks.get('average_level', '')

        # Class Teacher Comment
        class_teacher_frame = ctk.CTkFrame(comments_section, fg_color="white", border_width=1, border_color="#000000", corner_radius=5)
        class_teacher_frame.pack(fill="x", pady=(0, 10))

        class_teacher_label = ctk.CTkLabel(class_teacher_frame, text="Class Teacher:", font=("Arial Bold", 12), text_color="#000000", anchor="w")
        class_teacher_label.pack(fill="x", padx=10, pady=(5, 2))

        class_teacher_comment = ctk.CTkLabel(class_teacher_frame, text=self.get_class_teacher_comment(avg_level),
                                            font=("Arial", 11), text_color="#000000", anchor="w", wraplength=800)
        class_teacher_comment.pack(fill="x", padx=10, pady=(0, 5))

        # Head Teacher Comment
        head_teacher_frame = ctk.CTkFrame(comments_section, fg_color="white", border_width=1, border_color="#000000", corner_radius=5)
        head_teacher_frame.pack(fill="x")

        head_teacher_label = ctk.CTkLabel(head_teacher_frame, text="Head Teacher:", font=("Arial Bold", 12), text_color="#000000", anchor="w")
        head_teacher_label.pack(fill="x", padx=10, pady=(5, 2))

        head_teacher_comment = ctk.CTkLabel(head_teacher_frame, text=self.get_head_teacher_comment(avg_level),
                                           font=("Arial", 11), text_color="#000000", anchor="w", wraplength=800)
        head_teacher_comment.pack(fill="x", padx=10, pady=(0, 5))

        # Signature block
        signature_section = ctk.CTkFrame(container, fg_color="transparent")
        signature_section.pack(fill="x", padx=20, pady=20)

        signature_frame = ctk.CTkFrame(signature_section, fg_color="transparent")
        signature_frame.pack(fill="x")

        school_administrator = self.school_config.get('school_administrator', 'School Administrator')

        sig_label = ctk.CTkLabel(signature_frame, text="School Administrator", font=("Arial Bold", 12), text_color="#667eea")
        sig_label.pack(anchor="w")

        name_label = ctk.CTkLabel(signature_frame, text=school_administrator, font=("Arial", 14), text_color="#000000")
        name_label.pack(anchor="w", pady=(0, 5))

        # Signature image
        signature_path = self.school_config.get('signatures', {}).get('headteacher', '')
        if signature_path and os.path.exists(signature_path):
            try:
                sig_img = Image.open(signature_path).resize((180, 80))
                sig_photo = ctk.CTkImage(sig_img)
                sig_image_label = ctk.CTkLabel(signature_frame, image=sig_photo, text="")
                sig_image_label.pack(anchor="w", pady=(0, 5))
            except Exception as e:
                print(f"Error loading signature: {e}")
                # Fallback to signature line
                sig_line = ctk.CTkFrame(signature_frame, fg_color="#667eea", height=2)
                sig_line.pack(fill="x", pady=(0, 5))
        else:
            # Fallback to signature line
            sig_line = ctk.CTkFrame(signature_frame, fg_color="#667eea", height=2)
            sig_line.pack(fill="x", pady=(0, 5))

        date_label = ctk.CTkLabel(signature_frame, text="Date: _______________", font=("Arial", 12), text_color="#667eea")
        date_label.pack(anchor="w")

    def create_previous_marks_section(self, container, student):
        section_frame = ctk.CTkFrame(container)
        section_frame.pack(fill="x", pady=(0, 20))
        
        # Section title with toggle button
        title_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=10)
        
        title_label = ctk.CTkLabel(title_frame, text="PREVIOUS EXAMINATION RESULTS",
                                   font=("Arial Bold", 18), text_color="#e67e22")
        title_label.pack(side="left", padx=10)
        
        # Get previous exams
        previous_exams = self.db.get_previous_exams(student['grade'])
        
        if previous_exams:
            # Create dropdown for previous exams
            exam_var = ctk.StringVar()
            exam_var.set(previous_exams[0][0])  # Default to most recent
            
            exam_menu = ctk.CTkOptionMenu(title_frame, variable=exam_var,
                                         values=[exam[0] for exam in previous_exams],
                                         command=lambda e: self.load_previous_exam(section_frame, e, student))
            exam_menu.pack(side="right", padx=10)
            
            # Load most recent exam
            self.load_previous_exam(section_frame, previous_exams[0][0], student)
        else:
            no_exams_label = ctk.CTkLabel(section_frame, text="No previous exams available",
                                         font=("Arial", 14), text_color="gray")
            no_exams_label.pack(pady=20)
    
    def load_previous_exam(self, container, exam_name, student):
        # Clear previous marks display
        for widget in container.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and widget != container.winfo_children()[0]:
                widget.destroy()

        # Get previous exam data
        marks_data, summary_data = self.db.get_previous_exam_data(exam_name, student['grade'])

        if marks_data:
            try:
                import json
                marks_data_parsed = json.loads(marks_data)

                print(f"DEBUG: Student adm_no: {student['adm_no']}")
                print(f"DEBUG: Student name: {student['name']}")
                print(f"DEBUG: Marks data type: {type(marks_data_parsed)}")
                print(f"DEBUG: Marks data: {marks_data_parsed}")

                # Handle both dictionary and list formats
                if isinstance(marks_data_parsed, dict):
                    student_marks = marks_data_parsed.get(student['adm_no'], {})
                    if not student_marks:
                        # Try with stripped/uppercase versions
                        for key in marks_data_parsed.keys():
                            if str(key).strip().upper() == str(student['adm_no']).strip().upper():
                                student_marks = marks_data_parsed[key]
                                break
                elif isinstance(marks_data_parsed, list):
                    # Handle list of lists format (flat data without adm_no)
                    if marks_data_parsed and isinstance(marks_data_parsed[0], list):
                        # This is a list of lists format: [['name', score1, rating1, ...]]
                        # Since there's no adm_no, we'll use the first item if only one student
                        # or try to match by name
                        if len(marks_data_parsed) == 1:
                            # Only one student, use it
                            student_marks = self.convert_list_to_dict(marks_data_parsed[0], student['grade'])
                        else:
                            # Try to match by student name
                            student_marks = {}
                            for item in marks_data_parsed:
                                if isinstance(item, list) and len(item) > 0:
                                    item_name = str(item[0]).strip().lower()
                                    student_name = str(student['name']).strip().lower()
                                    if item_name == student_name or item_name in student_name or student_name in item_name:
                                        student_marks = self.convert_list_to_dict(item, student['grade'])
                                        break
                    else:
                        # Handle list of dictionaries format
                        student_marks = {}
                        for item in marks_data_parsed:
                            if isinstance(item, dict):
                                item_adm = item.get('adm_no')
                                if item_adm:
                                    # Try exact match first
                                    if str(item_adm) == str(student['adm_no']):
                                        student_marks = item
                                        break
                                    # Try with stripped/uppercase versions
                                    elif str(item_adm).strip().upper() == str(student['adm_no']).strip().upper():
                                        student_marks = item
                                        break
                else:
                    student_marks = {}

                print(f"DEBUG: Student marks found: {bool(student_marks)}")

                if student_marks:
                    self.create_marks_table(container, student_marks, student['grade'], is_previous=True)
                else:
                    no_marks_label = ctk.CTkLabel(container, text="No marks found for this student in this exam",
                                                 font=("Arial", 14), text_color="gray")
                    no_marks_label.pack(pady=20)
            except Exception as e:
                print(f"Error loading previous exam: {e}")
                error_label = ctk.CTkLabel(container, text="Error loading previous exam data",
                                          font=("Arial", 14), text_color="gray")
                error_label.pack(pady=20)

    def convert_list_to_dict(self, marks_list, grade):
        """Convert a flat list of marks to a dictionary format"""
        # Get subjects for this grade
        subjects_config = self.school_config.get('subjects', {})
        grade_mapping = {
            'playgroup': 'playgroup',
            'pp1': 'pp1',
            'pp2': 'pp2',
            'Grade 1': 'lower',
            'Grade 2': 'lower',
            'Grade 3': 'lower',
            'Grade 4': 'primary',
            'Grade 5': 'primary',
            'Grade 6': 'primary',
            'Grade 7': 'jss',
            'Grade 8': 'jss',
            'Grade 9': 'jss',
        }
        key = grade_mapping.get(grade)
        subjects = subjects_config.get(key, [])

        marks_dict = {}
        
        # Determine format based on grade
        grade_lower = grade.lower()
        is_junior = grade_lower in ["grade 7", "grade 8", "grade 9"]
        
        # Skip the first element (name)
        idx = 1
        if is_junior:
            # Junior format: [name, score1, rating1, points1, score2, rating2, points2, ..., total, average_rating, average_points]
            print(f"DEBUG: convert_list_to_dict using junior format for {grade}")
            for subject in subjects:
                if idx + 2 < len(marks_list):
                    score = marks_list[idx]
                    rating = marks_list[idx + 1]
                    points = marks_list[idx + 2]
                    # For junior, use score as the display value (not points)
                    # Normalize subject name to use underscores (same as marksheet table)
                    clean_subject = "".join(char if char.isalnum() else "_" for char in subject).lower().strip("_")
                    marks_dict[f'{clean_subject}_s'] = score
                    marks_dict[f'{clean_subject}_r'] = rating
                    marks_dict[f'{clean_subject}_p'] = points
                    idx += 3
        else:
            # Playgroup/Primary format: [name, score1, rating1, score2, rating2, ..., total, average]
            print(f"DEBUG: convert_list_to_dict using standard format for {grade}")
            for subject in subjects:
                if idx + 1 < len(marks_list):
                    # Normalize subject name to use underscores (same as marksheet table)
                    clean_subject = "".join(char if char.isalnum() else "_" for char in subject).lower().strip("_")
                    marks_dict[f'{clean_subject}_s'] = marks_list[idx]
                    marks_dict[f'{clean_subject}_r'] = marks_list[idx + 1]
                    idx += 2

        # Add total and average if available
        if idx < len(marks_list):
            marks_dict['total_score'] = marks_list[idx]
        if idx + 1 < len(marks_list):
            marks_dict['average_level'] = marks_list[idx + 1]

        return marks_dict
    
    def get_student_current_marks(self, adm_no, grade):
        try:
            # Determine which table to use based on grade
            table_mapping = {
                'playgroup': 'playgroup_marks',
                'pp1': 'pp1_marks',
                'pp2': 'pp2_marks',
                'Grade 1': 'lower_marks',
                'Grade 2': 'lower_marks',
                'Grade 3': 'lower_marks',
                'Grade 4': 'primary_marks',
                'Grade 5': 'primary_marks',
                'Grade 6': 'primary_marks',
                'Grade 7': 'marksheet',
                'Grade 8': 'marksheet',
                'Grade 9': 'marksheet',
            }
            
            table = table_mapping.get(grade)
            print(f"DEBUG: get_student_current_marks - adm_no: {adm_no}, grade: {grade}, table: {table}")
            if not table:
                print(f"DEBUG: No table found for grade {grade}")
                return None
            
            self.db.cursor().execute(f'SELECT * FROM {table} WHERE adm_no = ?', (adm_no,))
            columns = [desc[0] for desc in self.db.cursor().description]
            row = self.db.cursor().fetchone()
            
            if row:
                result = dict(zip(columns, row))
                print(f"DEBUG: Found current marks for {adm_no}, keys: {list(result.keys())[:5]}")
                # Check if marks are empty (for junior grades)
                if table == 'marksheet':
                    # Check if any subject marks are non-empty
                    has_marks = any(result.get(col) for col in result.keys() if col.endswith('_s'))
                    if not has_marks:
                        print(f"DEBUG: Marksheet has no marks for {adm_no}, trying fallback to most recent exam")
                        # Fallback to most recent exam data
                        return self.get_student_current_marks_from_exam(adm_no, grade)
                return result
            
            print(f"DEBUG: No current marks found for {adm_no} in {table}")
            # Fallback to student_reports table for junior grades
            if table == 'marksheet':
                print(f"DEBUG: Trying fallback to student_reports for {adm_no}")
                return self.get_student_current_marks_from_reports(adm_no, grade)
            return None
        except Exception as e:
            print(f"Error getting current marks: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_student_current_marks_from_reports(self, adm_no, grade):
        """Fallback: Get current marks from student_reports table when marksheet is empty"""
        try:
            print(f"DEBUG: get_student_current_marks_from_reports - adm_no: {adm_no}, grade: {grade}")
            self.db.cursor().execute('SELECT marks_data FROM student_reports WHERE adm_no = ? AND grade = ?', (adm_no, grade))
            row = self.db.cursor().fetchone()
            
            if row:
                import json
                marks_data = json.loads(row[0])
                print(f"DEBUG: Found marks in student_reports for {adm_no}")
                
                # Convert dict format to marksheet format
                result = {'adm_no': adm_no}
                subjects = self.get_subjects_for_grade(grade)
                
                for subject in subjects:
                    subject_key = subject.upper().replace(' ', '').replace('-', '')
                    # Try different key formats
                    for key_format in [subject_key, subject_key.replace('-', ''), subject.upper().replace(' ', ''), subject.lower().replace(' ', '').replace('-', '')]:
                        if key_format in marks_data:
                            mark_data = marks_data[key_format]
                            if isinstance(mark_data, dict):
                                result[f'{subject.lower().replace(" ", "_").replace("-", "_")}_s'] = mark_data.get('score', '')
                                result[f'{subject.lower().replace(" ", "_").replace("-", "_")}_r'] = mark_data.get('rating', '')
                                result[f'{subject.lower().replace(" ", "_").replace("-", "_")}_p'] = mark_data.get('points', '')
                            else:
                                result[f'{subject.lower().replace(" ", "_").replace("-", "_")}_s'] = mark_data
                            break
                
                print(f"DEBUG: Converted marks from student_reports, keys: {list(result.keys())[:5]}")
                return result
            
            print(f"DEBUG: No marks found in student_reports for {adm_no}")
            return None
        except Exception as e:
            print(f"Error getting current marks from reports: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_student_current_marks_from_exam(self, adm_no, grade):
        """Fallback: Get current marks from the most recent exam when marksheet is empty"""
        try:
            print(f"DEBUG: get_student_current_marks_from_exam - adm_no: {adm_no}, grade: {grade}")
            # Get the most recent exam for this grade
            previous_exams = self.db.get_previous_exams(grade)
            if not previous_exams:
                print(f"DEBUG: No previous exams found for grade {grade}")
                return None
            
            # Get the most recent exam (first in list)
            most_recent_exam = previous_exams[0][0]
            print(f"DEBUG: Using most recent exam: {most_recent_exam}")
            
            # Get exam data
            marks_data, summary_data = self.db.get_previous_exam_data(most_recent_exam, grade)
            if not marks_data:
                print(f"DEBUG: No marks data found for exam {most_recent_exam}")
                return None
            
            # Parse marks data
            import json
            if isinstance(marks_data, str):
                marks_data = json.loads(marks_data)
            
            # Convert to marksheet format
            result = {'adm_no': adm_no}
            subjects = self.get_subjects_for_grade(grade)
            
            # Handle list format (junior grades)
            if isinstance(marks_data, list) and marks_data and isinstance(marks_data[0], list):
                # Find the student in the list
                student_marks = None
                for item in marks_data:
                    if item and len(item) > 0:
                        # Try to match by name (first item)
                        student_name = str(item[0]).strip()
                        # For now, if there's only one student or we can't match, use the first one
                        if len(marks_data) == 1:
                            student_marks = item
                            break
                
                if student_marks:
                    # Convert list to dict with _s, _r, _p columns
                    junior_grades = ['Grade 7', 'Grade 8', 'Grade 9']
                    is_junior = grade in junior_grades
                    
                    for i, subject in enumerate(subjects):
                        if is_junior:
                            # Junior format: score, rating, points
                            if i * 3 + 2 < len(student_marks):
                                score = student_marks[i * 3]
                                rating = student_marks[i * 3 + 1]
                                points = student_marks[i * 3 + 2]
                                subject_key = subject.lower().replace(' ', '_').replace('-', '_')
                                result[f'{subject_key}_s'] = score
                                result[f'{subject_key}_r'] = rating
                                result[f'{subject_key}_p'] = points
                        else:
                            # Primary format: score, rating
                            if i * 2 + 1 < len(student_marks):
                                score = student_marks[i * 2]
                                rating = student_marks[i * 2 + 1]
                                subject_key = subject.lower().replace(' ', '_').replace('-', '_')
                                result[f'{subject_key}_s'] = score
                                result[f'{subject_key}_r'] = rating
                    
                    # Extract total_points and average_level if present (last 2 items)
                    if len(student_marks) >= 2:
                        result['total_points'] = student_marks[-2]
                        result['average_level'] = student_marks[-1]
                    
                    print(f"DEBUG: Converted exam data to marksheet format, keys: {list(result.keys())[:5]}")
                    return result
            
            print(f"DEBUG: Could not convert exam data to marksheet format")
            return None
        except Exception as e:
            print(f"Error getting current marks from exam: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_marks_table(self, container, marks, grade, is_previous=False):
        # Get subjects for this grade
        subjects = self.get_subjects_for_grade(grade)

        if not subjects:
            return

        # Check if this is junior secondary (Grade 7, 8, 9) - these use points
        junior_grades = ['Grade 7', 'Grade 8', 'Grade 9']
        is_junior = grade in junior_grades

        # Create table frame with border
        table_frame = ctk.CTkFrame(container, border_width=2, border_color="#34495e")
        table_frame.pack(fill="x", padx=20, pady=10)

        # Header
        header_frame = ctk.CTkFrame(table_frame, fg_color="#34495e")
        header_frame.pack(fill="x")

        headers = ["Subject", "Score", "Rating"]
        if is_junior:
            headers.append("Points")

        for i, header in enumerate(headers):
            lbl = ctk.CTkLabel(header_frame, text=header, font=("Arial Bold", 13),
                              text_color="white", width=180)
            lbl.pack(side="left", padx=5, pady=8)

        # Extract subject keys from marks to preserve original column names
        subject_keys = {}
        for key in marks.keys():
            if key.endswith('_s') and key not in ['total_points', 'average_level', 'rank']:
                subject_name = key.replace('_s', '').replace('_', ' ').title()
                # Keep underscores in the key value to match database column names
                # Don't replace underscores in the value, only in the display name
                subject_keys[subject_name] = key.replace('_s', '')
        print(f"DEBUG: create_marks_table - subject_keys: {subject_keys}")
        print(f"DEBUG: create_marks_table - subjects from config: {subjects}")

        # Data rows with alternating colors
        for i, subject in enumerate(subjects):
            bg_color = "#ecf0f1" if i % 2 == 0 else "#ffffff"
            row_frame = ctk.CTkFrame(table_frame, fg_color=bg_color)
            row_frame.pack(fill="x", pady=0)

            # Subject name
            subj_label = ctk.CTkLabel(row_frame, text=subject, font=("Arial Bold", 12), width=180, anchor="w", text_color="#2c3e50")
            subj_label.pack(side="left", padx=5, pady=5)

            # Get score, rating, points for this subject using original column key
            # Normalize subject name to match database column naming (replace hyphens and slashes with underscores)
            # Use the same normalization as get_clean_col_name in ui_marksheet_junior.py
            clean_subject = "".join(char if char.isalnum() else "_" for char in subject).lower().strip("_")
            subject_key = subject_keys.get(subject, clean_subject)
            score = marks.get(f'{subject_key}_s', '')
            rating = marks.get(f'{subject_key}_r', '')
            points = marks.get(f'{subject_key}_p', '')
            print(f"DEBUG: Subject: {subject}, clean_subject: {clean_subject}, subject_key: {subject_key}, score: {score}")

            # Score
            score_label = ctk.CTkLabel(row_frame, text=str(score), font=("Arial", 12), width=180, text_color="#2c3e50")
            score_label.pack(side="left", padx=5, pady=5)

            # Rating
            rating_label = ctk.CTkLabel(row_frame, text=str(rating), font=("Arial", 12), width=180, text_color="#2c3e50")
            rating_label.pack(side="left", padx=5, pady=5)

            # Points (only for junior)
            if is_junior:
                points_label = ctk.CTkLabel(row_frame, text=str(points), font=("Arial Bold", 12), width=180, text_color="#2980b9")
                points_label.pack(side="left", padx=5, pady=5)

        # Total and average summary
        total = marks.get('total_points', '') or marks.get('total_score', '')
        avg = marks.get('average_points', '') or marks.get('average_level', '')

        summary_frame = ctk.CTkFrame(table_frame, fg_color="#2c3e50")
        summary_frame.pack(fill="x", pady=(10, 0))

        total_label_text = "TOTAL POINTS" if is_junior else "TOTAL SCORES"
        total_label = ctk.CTkLabel(summary_frame, text=f"{total_label_text}: {total}",
                                   font=("Arial Bold", 15), text_color="white")
        total_label.pack(side="left", padx=20, pady=12)

        avg_label = ctk.CTkLabel(summary_frame, text=f"AVERAGE LEVEL: {avg}",
                                 font=("Arial Bold", 15), text_color="#f1c40f")
        avg_label.pack(side="right", padx=20, pady=12)
    
    def get_subjects_for_grade(self, grade):
        subjects_config = self.school_config.get('subjects', {})
        
        grade_mapping = {
            'playgroup': 'playgroup',
            'pp1': 'pp1',
            'pp2': 'pp2',
            'Grade 1': 'lower',
            'Grade 2': 'lower',
            'Grade 3': 'lower',
            'Grade 4': 'primary',
            'Grade 5': 'primary',
            'Grade 6': 'primary',
            'Grade 7': 'jss',
            'Grade 8': 'jss',
            'Grade 9': 'jss',
        }
        
        key = grade_mapping.get(grade)
        print(f"DEBUG: get_subjects_for_grade - grade: {grade}, key: {key}, subjects: {subjects_config.get(key, [])}")
        return subjects_config.get(key, [])
    
    def create_signature_section(self, container, student):
        signature_frame = ctk.CTkFrame(container, fg_color="#f8f9fa")
        signature_frame.pack(fill="x", pady=(0, 20))

        # Section title
        title_label = ctk.CTkLabel(signature_frame, text="SIGNATURE",
                                   font=("Arial Bold", 16), text_color="#2c3e50")
        title_label.pack(pady=10)

        # Signature container
        sig_container = ctk.CTkFrame(signature_frame, fg_color="transparent")
        sig_container.pack(fill="x", padx=20, pady=10)

        # School administrator signature
        sig_frame = ctk.CTkFrame(sig_container, width=200, height=120)
        sig_frame.pack(side="right", padx=20, pady=10)

        # Get school administrator name from config
        school_administrator = self.school_config.get('school_administrator', 'School Administrator')

        try:
            signature_path = self.school_config.get('signatures', {}).get('headteacher', '')
            if signature_path and os.path.exists(signature_path):
                sig_img = Image.open(signature_path).resize((180, 80))
                sig_photo = ctk.CTkImage(sig_img)
                sig_label = ctk.CTkLabel(sig_frame, image=sig_photo, text="")
                sig_label.pack(pady=5)

                sig_name_label = ctk.CTkLabel(sig_frame, text=school_administrator,
                                             font=("Arial Bold", 12), text_color="#2c3e50")
                sig_name_label.pack(pady=2)
            else:
                sig_label = ctk.CTkLabel(sig_frame, text=f"{school_administrator.upper()}\nSIGNATURE",
                                        font=("Arial Bold", 10), text_color="gray")
                sig_label.pack(pady=20)
        except:
            sig_label = ctk.CTkLabel(sig_frame, text=f"{school_administrator.upper()}\nSIGNATURE",
                                    font=("Arial Bold", 10), text_color="gray")
            sig_label.pack(pady=20)

        # Date info
        info_frame = ctk.CTkFrame(sig_container, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        date_label = ctk.CTkLabel(info_frame, text="Date: _______________",
                                  font=("Arial", 13), text_color="#2c3e50")
        date_label.pack(pady=5, anchor="w")
        
        # Date
        date_label = ctk.CTkLabel(info_frame, text=f"Date: {datetime.datetime.now().strftime('%d/%m/%Y')}",
                                 font=("Arial", 13), text_color="#2c3e50")
        date_label.pack(pady=5, anchor="w")
    
    def ask_opening_closing_dates(self):
        return ask_opening_closing_dates(self)

    def print_individual_report(self, student):
        report_mode = ask_report_print_mode(self)
        if report_mode is None:
            return
        date_range = self.ask_opening_closing_dates()
        if date_range is None:
            return
        self.print_report_pdf(None, student, date_range=date_range, report_mode=report_mode)

    def _print_cbc_report_pdf(self, report, file_path, date_range, report_mode, show_messages):
        from fpdf import FPDF

        temporary_files = []

        def pdf_text(value):
            return str(value or "").encode("latin-1", "replace").decode("latin-1")

        def image_file(value):
            if not value:
                return ""
            value = str(value)
            if os.path.isfile(value):
                return value
            if value.startswith("data:image/"):
                try:
                    _, encoded = value.split(",", 1)
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as image:
                        image.write(base64.b64decode(encoded))
                        temporary_files.append(image.name)
                        return image.name
                except (ValueError, base64.binascii.Error):
                    return ""
            return ""

        dialog_parent = getattr(self, "parent_window", None)
        student_name = report.get("student_name", report.get("name", ""))
        grade = report.get("grade", "")
        exam_title = report.get("exam_title") or self.school_config.get("current_exam_title", "ASSESSMENT")
        output_path = file_path
        if not output_path:
            output_path = filedialog.asksaveasfilename(
                parent=dialog_parent,
                defaultextension=".pdf",
                initialfile=f"{str(student_name).replace(' ', '_')}_{str(exam_title).replace(' ', '_')}.pdf",
            )
        if not output_path:
            return False

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=12)
        school_name = self.school_config.get("school_name", "MY SCHOOL")
        address = self.school_config.get("address", "")
        contacts = self.school_config.get("contacts", "")
        logo = image_file(self.school_config.get("logo"))
        photo = image_file(report.get("photo"))
        green = (46, 125, 50)
        dark = (31, 41, 55)
        level_colors = {"BE": (185, 28, 28), "AE": (194, 65, 12), "ME": (29, 78, 216), "EE": (21, 128, 61)}

        def page_header(title):
            pdf.add_page()
            pdf.set_draw_color(*green)
            pdf.set_line_width(0.6)
            pdf.rect(5, 5, 287, 200)
            if logo:
                try:
                    pdf.image(logo, 10, 8, 22, 22)
                except Exception:
                    pass
            if photo:
                try:
                    pdf.image(photo, 265, 8, 20, 24)
                except Exception:
                    pass
            pdf.set_xy(36, 9)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(*green)
            pdf.cell(225, 7, pdf_text(str(school_name).upper()), align="C", ln=1)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*dark)
            pdf.cell(277, 4, pdf_text(address), align="C", ln=1)
            pdf.cell(277, 4, pdf_text(contacts), align="C", ln=1)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*dark)
            pdf.cell(277, 7, pdf_text(title), align="C", ln=1)
            pdf.set_fill_color(241, 245, 249)
            pdf.set_font("Helvetica", "B", 8)
            meta = (
                f"Learner: {student_name}    Class: {grade}    Stream: {report.get('stream', 'None')}    "
                f"Term: {report.get('term', '')}, {report.get('academic_year', '')}"
            )
            pdf.cell(277, 7, pdf_text(meta), border=0, ln=1, fill=True)
            pdf.ln(2)

        def section_title(text):
            pdf.set_fill_color(*green)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(277, 6, pdf_text(text), border=0, ln=1, fill=True)
            pdf.set_text_color(*dark)

        def draw_history_chart(y, height=36):
            history = report.get("performance_history", [])
            subjects = report.get("subjects", [])
            subject_labels = report.get("subject_labels", {})
            x_left, x_plot_right = 20, 205
            y_top, y_bottom = y + 9, y + 25
            pdf.set_draw_color(148, 163, 184)
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(10, y, 277, height, style="DF")
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*dark)
            pdf.text(13, y + 5, "SUBJECT PERFORMANCE HISTORY  |  Composite / exam score (%)")
            for value in (0, 50, 100):
                point_y = y_bottom - (y_bottom - y_top) * value / 100
                pdf.set_draw_color(218, 226, 232)
                pdf.line(x_left, point_y, x_plot_right, point_y)
                pdf.text(11, point_y + 1, str(value))
            if not history:
                return
            for exam_index, exam in enumerate(history):
                x = x_left + (x_plot_right - x_left) * exam_index / max(1, len(history) - 1)
                pdf.set_font("Helvetica", "", 6)
                pdf.text(x - 8, y_bottom + 4, pdf_text(str(exam.get("name", "Exam"))[:18]))

            def draw_marker(x, marker_y, marker, size):
                if marker == "circle":
                    pdf.ellipse(x - size, marker_y - size, size * 2, size * 2, style="F")
                elif marker == "square":
                    pdf.rect(x - size, marker_y - size, size * 2, size * 2, style="F")
                elif marker == "triangle":
                    pdf.line(x, marker_y - size, x - size, marker_y + size * 0.7)
                    pdf.line(x - size, marker_y + size * 0.7, x + size, marker_y + size * 0.7)
                    pdf.line(x + size, marker_y + size * 0.7, x, marker_y - size)
                elif marker == "cross":
                    pdf.line(x - size, marker_y, x + size, marker_y)
                    pdf.line(x, marker_y - size, x, marker_y + size)
                else:
                    pdf.line(x, marker_y - size, x + size, marker_y)
                    pdf.line(x + size, marker_y, x, marker_y + size)
                    pdf.line(x, marker_y + size, x - size, marker_y)
                    pdf.line(x - size, marker_y, x, marker_y - size)

            palette = [(22, 101, 52), (37, 99, 235), (194, 65, 12), (147, 51, 234), (8, 145, 178), (190, 18, 60), (77, 124, 15), (15, 118, 110), (161, 98, 7)]
            for subject_index, subject in enumerate(subjects):
                color = palette[subject_index % len(palette)]
                marker_shape = chart_marker_for_subject(subject_index)
                points = []
                for exam_index, exam in enumerate(history):
                    score = exam.get("subjects", {}).get(subject)
                    if score is None:
                        continue
                    x = x_left + (x_plot_right - x_left) * exam_index / max(1, len(history) - 1)
                    point_y = y_bottom - (y_bottom - y_top) * max(0, min(100, float(score))) / 100
                    points.append((x, point_y))
                pdf.set_draw_color(*color)
                pdf.set_fill_color(*color)
                pdf.set_line_width(0.2)
                for first, second in zip(points, points[1:]):
                    pdf.line(first[0], first[1], second[0], second[1])
                for x, point_y in points:
                    draw_marker(x, point_y, marker_shape, 1.2)
                legend_column = subject_index // 5
                legend_row = subject_index % 5
                legend_x = 212 + legend_column * 37
                legend_y = y + 9 + legend_row * 5
                pdf.set_draw_color(*color)
                pdf.set_fill_color(*color)
                pdf.line(legend_x, legend_y, legend_x + 5, legend_y)
                marker_position = (legend_x + 2.5, legend_y)
                draw_marker(marker_position[0], marker_position[1], marker_shape, 0.8)
                pdf.set_text_color(*dark)
                pdf.set_font("Helvetica", "", 5)
                label = pdf_text(subject_labels.get(subject, subject))[:24]
                pdf.text(legend_x + 7, legend_y + 1, label)
            pdf.set_text_color(*dark)

        try:
            page_header("LEARNER CBC SUMMARY")
            pdf.set_font("Helvetica", "", 7)
            pdf.multi_cell(
                277, 4,
                "Composite level uses 70% formative evidence and 30% summative assessment. "
                "If no formative strands are marked, the summative assessment determines the level. "
                "Previous exam columns retain their recorded score values.",
            )
            previous = list(reversed(report.get("previous_exams", [])[:2]))
            subject_results = report.get("subject_results", [])
            subject_width = 30
            previous_width = 17
            current_widths = [25, 20, 22, 12]
            improvement_width = 17
            teacher_width = 22
            comment_width = 277 - subject_width - previous_width * len(previous) - sum(current_widths) - improvement_width - teacher_width
            widths = [subject_width] + [previous_width] * len(previous) + current_widths + [improvement_width, teacher_width, comment_width]
            y = pdf.get_y()
            header_height = 10

            def header_cell(x, cell_y, cell_width, cell_height, label, color=green):
                pdf.set_fill_color(*color)
                pdf.set_draw_color(31, 41, 55)
                pdf.set_line_width(0.2)
                pdf.rect(x, cell_y, cell_width, cell_height, style="DF")
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 6)
                pdf.set_xy(x + 1, cell_y + max(0, (cell_height - 4) / 2))
                pdf.multi_cell(cell_width - 2, 4, pdf_text(label), align="C")

            x = 10
            header_cell(x, y, subject_width, header_height, "Learning Area")
            x += subject_width
            for exam, cell_width in zip(previous, widths[1:1 + len(previous)]):
                header_cell(x, y, cell_width, header_height, str(exam.get("exam_name", "Previous"))[:18])
                x += cell_width
            current_title = report.get("exam_title", "Current Exam")
            header_cell(x, y, sum(current_widths), 5, f"{current_title} (Current Exam)", color=(27, 94, 32))
            sub_x = x
            for label, cell_width in zip(("Formative 70%", "Summative 30%", "Composite Total", "Level"), current_widths):
                header_cell(sub_x, y + 5, cell_width, 5, label)
                sub_x += cell_width
            x += sum(current_widths)
            header_cell(x, y, improvement_width, header_height, "Improvement")
            x += improvement_width
            header_cell(x, y, teacher_width, header_height, "Teacher")
            x += teacher_width
            header_cell(x, y, comment_width, header_height, "Teacher Comment")
            y += header_height
            pdf.set_text_color(*dark)
            pdf.set_font("Helvetica", "", 6)
            teacher_map = self.get_teacher_assignments(grade)
            latest_previous = report.get("previous_exams", [])
            latest_previous_marks = latest_previous[0].get("marks", {}) if latest_previous else {}
            for row_index, item in enumerate(subject_results):
                subject = item["subject"]
                values = [subject]
                values.extend(self._previous_subject_score(exam.get("marks", {}), subject) for exam in previous)
                current_score = item.get("composite_score")
                previous_score = self._previous_subject_score(latest_previous_marks, subject)
                improvement = "-"
                if current_score is not None:
                    try:
                        difference = int(round(float(current_score) - float(previous_score)))
                        improvement = f"+{difference}" if difference > 0 else str(difference)
                    except (TypeError, ValueError):
                        pass
                values.extend((
                    item.get("formative", "n/a"), item.get("summative", ""),
                    "-" if current_score is None else str(current_score), item.get("rating", ""),
                    improvement,
                    teacher_map.get(subject, teacher_map.get(item.get("area"), "-")),
                    self.rating_to_comment({"EE": "EE1", "ME": "ME1", "AE": "AE1", "BE": "BE1"}.get(item.get("rating"), ""), subject),
                ))
                x = 10
                for column, (value, cell_width) in enumerate(zip(values, widths)):
                    row_color = (248, 250, 252) if row_index % 2 == 0 else (255, 255, 255)
                    pdf.set_fill_color(*level_colors.get(item.get("rating"), row_color) if column == 1 + len(previous) + 3 else row_color)
                    pdf.set_draw_color(31, 41, 55)
                    pdf.set_line_width(0.2)
                    pdf.rect(x, y, cell_width, 7, style="DF")
                    pdf.set_xy(x, y)
                    if column == 1 + len(previous) + 3:
                        pdf.set_text_color(255, 255, 255)
                    else:
                        pdf.set_text_color(*dark)
                    pdf.set_font("Helvetica", "", 6)
                    pdf.multi_cell(cell_width, 5, pdf_text(value), align="L" if column in (0, len(values) - 1, len(values) - 2) else "C")
                    x += cell_width
                y += 7
            pdf.set_y(y)
            chart_y = max(pdf.get_y() + 2, 128)
            draw_history_chart(chart_y, 36)
            teacher_comments = report.get("teacher_comments") or build_teacher_comments(
                report.get("subject_results", []), report.get("rubric_subjects", []), student_name
            )

            def draw_comment_frame(y, title, text, fill_color):
                line_count = max(1, (len(pdf_text(text)) + 149) // 150)
                frame_height = max(9, 4 + line_count * 3)
                pdf.set_fill_color(*fill_color)
                pdf.set_draw_color(*green)
                pdf.rect(10, y, 277, frame_height, style="DF")
                pdf.set_xy(14, y + 2)
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_text_color(*green)
                pdf.cell(48, 4, pdf_text(title))
                pdf.set_xy(62, y + 2)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*dark)
                pdf.multi_cell(220, 3, pdf_text(text))
                return y + frame_height + 1

            comment_y = chart_y + 37
            comment_y = draw_comment_frame(
                comment_y, "CLASS TEACHER", teacher_comments["class_teacher"], (240, 249, 244)
            )
            comment_y = draw_comment_frame(
                comment_y, "HEAD TEACHER", teacher_comments["head_teacher"], (239, 246, 255)
            )
            signature_y = comment_y + 1
            pdf.set_fill_color(241, 245, 249)
            pdf.set_draw_color(*green)
            pdf.rect(10, signature_y, 277, 12, style="DF")
            pdf.set_xy(14, signature_y + 2)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*dark)
            administrator = self.school_config.get("school_administrator", "School Administrator")
            pdf.cell(90, 4, pdf_text(f"HEADTEACHER: {administrator}"))
            pdf.set_xy(108, signature_y + 2)
            pdf.cell(75, 4, pdf_text("Signature: __________________"))
            pdf.set_xy(188, signature_y + 2)
            pdf.cell(45, 4, pdf_text("Date: __________"))
            if date_range and date_range.get("opening_date") and date_range.get("closing_date"):
                pdf.set_xy(14, signature_y + 7)
                pdf.set_font("Helvetica", "", 6)
                pdf.cell(270, 3, pdf_text(f"Term opening: {date_range['opening_date']}    Term closing: {date_range['closing_date']}"))

            if report_mode == "full":
                for subject in report.get("rubric_subjects", []):
                    page_header(f"LEARNER DETAILED PERFORMANCE RUBRIC - {subject['name']}")
                    section_title("SUB-STRAND PERFORMANCE")
                    if not subject.get("strands"):
                        pdf.set_font("Helvetica", "", 10)
                        pdf.multi_cell(277, 7, "No strand ratings are available for this learning area and term.")
                    else:
                        for strand in subject["strands"]:
                            if pdf.get_y() > 183:
                                page_header(f"{subject['name']} - CONTINUED")
                                section_title("SUB-STRAND PERFORMANCE")
                            pdf.set_fill_color(232, 245, 233)
                            pdf.set_text_color(20, 83, 45)
                            pdf.set_font("Helvetica", "B", 8)
                            pdf.cell(277, 6, pdf_text(strand["name"]), ln=1, fill=True)
                            pdf.set_text_color(*dark)
                            header = (("Sub-strand", 197), ("BE (1)", 20), ("AE (2)", 20), ("ME (3)", 20), ("EE (4)", 20))
                            pdf.set_font("Helvetica", "B", 7)
                            pdf.set_fill_color(*green)
                            pdf.set_text_color(255, 255, 255)
                            for label, cell_width in header:
                                pdf.cell(cell_width, 6, pdf_text(label), border=1, align="C", fill=True)
                            pdf.ln()
                            for row in strand["sub_strands"]:
                                if pdf.get_y() > 188:
                                    page_header(f"{subject['name']} - CONTINUED")
                                    section_title("SUB-STRAND PERFORMANCE")
                                    pdf.set_font("Helvetica", "B", 7)
                                    pdf.set_fill_color(*green)
                                    pdf.set_text_color(255, 255, 255)
                                    for label, cell_width in header:
                                        pdf.cell(cell_width, 6, pdf_text(label), border=1, align="C", fill=True)
                                    pdf.ln()
                                pdf.set_font("Helvetica", "", 7)
                                pdf.set_text_color(*dark)
                                pdf.set_fill_color(248, 250, 252)
                                pdf.cell(197, 6, pdf_text(row["name"]), border=1, fill=True)
                                for level in ("BE", "AE", "ME", "EE"):
                                    pdf.set_fill_color(*level_colors[level])
                                    pdf.set_text_color(255, 255, 255)
                                    pdf.cell(20, 6, "X" if row.get("level") == level else "", border=1, align="C", fill=True)
                                pdf.ln()
                    recommendations = subject.get("recommendations", [])
                    if pdf.get_y() > 183:
                        page_header(f"{subject['name']} - REVISIT FOCUS")
                    pdf.ln(4)
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(154, 52, 18)
                    if recommendations:
                        guidance = "Revisit these sub-strands: " + ", ".join(
                            f"{item['name']} ({item['level']})" for item in recommendations
                        ) + "."
                    else:
                        guidance = "No specific revisit recommendation: recorded levels do not show lower-level variation."
                    pdf.multi_cell(277, 5, pdf_text(guidance))
                    pdf.set_text_color(*dark)

                pathway = report.get("pathway_recommendation")
                if pathway:
                    page_header("JUNIOR CAREER PATHWAY GUIDANCE")
                    pdf.set_font("Helvetica", "", 8)
                    pdf.multi_cell(277, 5, pdf_text(pathway.get("basis", "")))
                    score_lookup = {item["subject"]: item.get("composite_score") for item in report.get("subject_results", [])}
                    aliases = {
                        "math": "mathematics", "mat": "mathematics", "eng": "english",
                        "kisw": "kiswahili", "scie": "science & technology", "int scie": "integrated science",
                        "pre-tech": "pre-technical studies", "agri": "agriculture and nutrition",
                        "sst": "social studies", "c/a": "creative arts and sports", "rel": "religious education",
                        "cre": "religious education", "re": "religious education",
                        "ire": "religious education", "hre": "religious education",
                    }
                    for item in pathway.get("pathways", []):
                        score = item.get("score")
                        is_recommended = item["name"] == pathway.get("recommended")
                        pdf.set_fill_color(*(232, 245, 233) if is_recommended else (241, 245, 249))
                        pdf.set_font("Helvetica", "B", 9)
                        label = f"{item['name']}  |  {score if score is not None else 'No evidence'}%"
                        if is_recommended:
                            label += "  |  INDICATIVE RECOMMENDATION"
                        pdf.cell(277, 7, pdf_text(label), ln=1, fill=True)
                        pdf.set_font("Helvetica", "", 7)
                        for subject_name in item["subjects"]:
                            match = next((name for name in score_lookup if aliases.get(name.casefold(), name.casefold()) == subject_name.casefold()), None)
                            mark = score_lookup.get(match) if match else None
                            value = f"{subject_name}: {mark:g}%" if mark is not None else f"{subject_name}: no recorded composite"
                            pdf.cell(277, 5, pdf_text("    " + value), ln=1)

            pdf.output(output_path)
            if show_messages:
                messagebox.showinfo("Success", "PDF generated successfully!", parent=dialog_parent)
            return True
        except Exception as error:
            if show_messages:
                messagebox.showerror("PDF Generation Failed", str(error), parent=dialog_parent)
            else:
                print(f"PDF Generation Failed: {error}")
            return False
        finally:
            for temporary_path in temporary_files:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)

    def print_report_pdf(self, container, student, file_path=None, date_range=None, report_mode="full"):
        from fpdf import FPDF
        import os
        from tkinter import filedialog
        show_messages = file_path is None

        # Check if student data is valid
        if not student:
            # Only show error message for individual printing (when file_path is not provided)
            if show_messages:
                messagebox.showerror("Error", "No student data provided")
            return False

        if not student.get("current_marks"):
            student = self.generate_report_data(student)
            if not student:
                if show_messages:
                    messagebox.showerror("No report data", "No marks were found for this student.")
                return False

        if student.get("subject_results") is not None:
            return self._print_cbc_report_pdf(student, file_path, date_range, report_mode, show_messages)

        # Get school configuration
        school_name = self.school_config.get("school_name", "MY SCHOOL")
        logo_path = self.school_config.get("logo")
        school_address = self.school_config.get("address", "")
        school_telephone = self.school_config.get("contacts", "")
        school_administrator = self.school_config.get("school_administrator", "School Administrator")
        signature_path = self.school_config.get("signatures", {}).get("headteacher", "")
        current_exam_title = self.school_config.get("current_exam_title", "PERFORMANCE REPORT")

        # Get student data from report_data (handle both student object and report_data)
        student_name = student.get("student_name", student.get("name", "")) if student else ""
        adm_no = student.get("adm_no", "") if student else ""
        stream = student.get("stream", "none") if student else "none"
        grade = student.get("grade", "") if student else ""
        # Use current_exam_title from school_config.json for consistency with cloud
        exam_title = current_exam_title
        current_marks = student.get("current_marks", {}) if student else {}
        previous_exams = student.get("previous_exams", []) if student else []
        
        # Debug: Check student data structure
        print(f"DEBUG PDF: Student data keys: {list(student.keys()) if student else 'None'}")
        print(f"DEBUG PDF: Student photo field: {'present' if student and student.get('photo') else 'not found'}")
        
        # Get class teacher (first teacher linked to this class)
        class_teacher = self.get_class_teacher(grade) if grade else ""

        # Ask for save location only if file_path is not provided
        if not file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=f"{student_name.replace(' ', '_')}_{exam_title.replace(' ', '_')}.pdf",
            )
        if not file_path:
            return False

        temporary_photo_path = None
        try:
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.add_page()

            # Page frame/border
            pdf.set_draw_color(0, 0, 0)
            pdf.set_line_width(0.5)
            pdf.rect(5, 5, 287, 200)  # Border around page with 5mm margin

            # Header - School logo (left), school info (center), student photo (right) - matching cloud layout
            # School logo
            if logo_path and os.path.exists(logo_path):
                try:
                    pdf.image(logo_path, 10, 8, 25)
                except:
                    pass
            
            # School info (center) - perfectly centered
            pdf.set_xy(10, 8)
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(277, 6, txt=school_name.upper(), border=0, ln=1, align="C")
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(277, 4, txt=school_address, border=0, ln=1, align="C")
            pdf.cell(277, 4, txt=school_telephone, border=0, ln=1, align="C")
            
            # Student photo (right) - matching cloud layout
            # Try multiple possible photo field names
            student_photo = student.get('photo', '') or student.get('student_photo', '') or student.get('image_path', '')
            student_photo_path = student_photo
            if isinstance(student_photo, str) and student_photo.startswith("data:image/"):
                try:
                    _, encoded_photo = student_photo.split(",", 1)
                    photo_bytes = base64.b64decode(encoded_photo)
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as photo_file:
                        photo_file.write(photo_bytes)
                        temporary_photo_path = photo_file.name
                    student_photo_path = temporary_photo_path
                except (ValueError, base64.binascii.Error) as e:
                    print(f"Error decoding student photo for PDF: {e}")
                    student_photo_path = None
            print(f"DEBUG PDF: Student photo source: {'data URI' if isinstance(student_photo, str) and student_photo.startswith('data:image/') else student_photo}")
            if student_photo_path and os.path.isfile(student_photo_path):
                try:
                    pdf.image(student_photo_path, 250, 8, 25)
                    print(f"DEBUG PDF: Student photo loaded successfully at (250, 8) size 25mm")
                except Exception as e:
                    print(f"Error loading student photo in PDF: {e}")
            else:
                print(f"DEBUG PDF: Student photo not found or path invalid")
            
            pdf.ln(8)  # Increased spacing to avoid cutting photo/logo
            
            # Student metadata - matching cloud layout with modern color
            pdf.set_fill_color(248, 250, 252)
            pdf.rect(10, pdf.get_y(), 277, 12, 'DF')
            
            pdf.set_xy(15, pdf.get_y() + 2)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(25, 6, txt="Name:", border=0, ln=0)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(50, 6, txt=student_name, border=0, ln=0)
            
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(15, 6, txt="Class:", border=0, ln=0)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(30, 6, txt=grade, border=0, ln=0)
            
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(20, 6, txt="Stream:", border=0, ln=0)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(30, 6, txt=stream, border=0, ln=0)
            
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(15, 6, txt="ADM:", border=0, ln=0)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(30, 6, txt=str(adm_no), border=0, ln=1)
            
            pdf.ln(5)

            # Extract subjects from current_marks for subject_keys, but use config subjects for display
            subject_keys = {}  # Store original column keys
            if current_marks:
                print(f"DEBUG: current_marks keys: {list(current_marks.keys())[:10]}")
                for key in current_marks.keys():
                    if key.endswith('_s') and key not in ['total_points', 'average_level', 'rank']:
                        subject_name = key.replace('_s', '').replace('_', ' ').title()
                        # Store the original key without _s for lookup
                        subject_keys[subject_name] = key.replace('_s', '')
                print(f"DEBUG: Subject keys: {subject_keys}")
            
            # Use subjects from configuration for display
            subjects = self.get_subjects_for_grade(grade)
            print(f"DEBUG: Subjects from config: {subjects}")

            # Data Table - Subjects as rows, exams as columns (matching cloud layout)
            if subjects:
                # Check if junior grade (has points)
                is_junior = grade in ['Grade 7', 'Grade 8', 'Grade 9']
                
                # Get teacher assignments for this class
                teacher_map = self.get_teacher_assignments(grade)
                
                # Prepare exam columns in order: second latest previous exam, latest previous exam, current exam
                exam_cols = []
                if previous_exams and len(previous_exams) >= 2:
                    exam_cols.append({
                        'name': previous_exams[1].get('exam_name', ''),
                        'marks': previous_exams[1].get('marks', {}),
                        'total_points': previous_exams[1].get('total_points', ''),
                        'is_current': False
                    })
                if previous_exams and len(previous_exams) >= 1:
                    exam_cols.append({
                        'name': previous_exams[0].get('exam_name', ''),
                        'marks': previous_exams[0].get('marks', {}),
                        'total_points': previous_exams[0].get('total_points', ''),
                        'is_current': False
                    })
                exam_cols.append({
                    'name': exam_title,
                    'marks': current_marks,
                    'total_points': '',
                    'is_current': True
                })
                
                # Calculate column widths to fit page exactly (277mm total width)
                # Total available width = 277mm (from 10mm left margin to 287mm right margin)
                num_prev_exams = len([e for e in exam_cols if not e['is_current']])
                subject_col_width = 30  # Subject name column
                exam_col_width = 20     # Each exam score column (increased for better readability)
                rating_col_width = 12   # Rating column
                points_col_width = 10   # Points column (junior only)
                teacher_col_width = 18  # Teacher name
                improvement_col_width = 12  # Improvement
                
                # Calculate longest teacher comment to determine comment column width
                max_comment_length = 0
                for subject in subjects:
                    normalized_subject = subject.replace('-', ' ').replace('/', ' ').title()
                    subject_key = subject_keys.get(normalized_subject, subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                    rating = current_marks.get(f'{subject_key}_r', '')
                    comment = self.rating_to_comment(rating, subject) if rating else 'No comment'
                    max_comment_length = max(max_comment_length, len(comment))
                
                # Estimate comment width based on longest comment (approx 3 chars per mm at 6pt font)
                estimated_comment_width = max(60, min(100, max_comment_length / 3))
                
                print(f"DEBUG PDF: Longest comment length: {max_comment_length} chars")
                print(f"DEBUG PDF: Estimated comment width: {estimated_comment_width}mm")
                
                # Target: align comment column left edge at 175mm
                # So comment column should start at 175mm, meaning it has 102mm width (277 - 175)
                target_comment_start = 175
                target_comment_width = 277 - target_comment_start
                
                # Calculate total width without comments
                total_fixed = subject_col_width + (num_prev_exams + 1) * exam_col_width + rating_col_width
                if is_junior:
                    total_fixed += points_col_width
                total_fixed += teacher_col_width + improvement_col_width
                
                # Set comment width to target (aligns with admission number)
                comment_col_width = target_comment_width
                
                # Calculate remaining space to distribute to exam columns
                remaining_space = 277 - total_fixed - comment_col_width
                
                # Distribute extra space to exam columns to fill gap
                if num_prev_exams + 1 > 0 and remaining_space > 0:
                    extra_per_exam = remaining_space / (num_prev_exams + 1)
                    exam_col_width += extra_per_exam
                    print(f"DEBUG PDF: Distributed {remaining_space}mm extra space to exam columns")
                
                # Recalculate total to ensure it's exactly 277mm
                total_width = subject_col_width + (num_prev_exams + 1) * exam_col_width + rating_col_width
                if is_junior:
                    total_width += points_col_width
                total_width += teacher_col_width + improvement_col_width + comment_col_width
                
                print(f"DEBUG PDF: Total table width calculated: {total_width}mm")
                print(f"DEBUG PDF: Comment column width: {comment_col_width}mm (aligns at {target_comment_start}mm)")
                print(f"DEBUG PDF: Exam column width: {exam_col_width}mm")
                
                # Header row - calculate max height needed for wrapping with modern gradient-like color
                pdf.set_fill_color(59, 130, 246)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 7)
                
                # Calculate how many lines each exam title needs
                max_lines = 1
                for exam_col in exam_cols:
                    title = exam_col['name']
                    # Approximate characters per line at 7pt font in 18mm width
                    chars_per_line = int(exam_col_width * 3)  # Rough estimate
                    lines_needed = max(1, (len(title) + chars_per_line - 1) // chars_per_line)
                    max_lines = max(max_lines, lines_needed)
                
                # Calculate header height based on max lines
                header_height = max_lines * 5  # 5mm per line
                print(f"DEBUG PDF: Header height calculated as {header_height}mm for {max_lines} lines")
                
                # Save current Y position
                current_y = pdf.get_y()
                print(f"DEBUG PDF: Header starts at Y={current_y}mm")
                
                # Draw header row with consistent height using manual positioning
                # Subject column
                pdf.set_xy(10, current_y)
                pdf.cell(subject_col_width, header_height, txt="Learning Area", border=1, ln=0, align="L", fill=True)
                
                # Previous exam columns - use cell with truncated text to prevent overflow
                x_pos = 10 + subject_col_width
                for exam_col in exam_cols:
                    if not exam_col['is_current']:
                        pdf.set_xy(x_pos, current_y)
                        pdf.set_xy(x_pos, current_y)
                        pdf.multi_cell(exam_col_width, 5, txt=exam_col['name'], border=1, align="C", fill=True)
                        x_pos += exam_col_width
                
                # Current exam column
                pdf.set_xy(x_pos, current_y)
                pdf.set_xy(x_pos, current_y)
                pdf.multi_cell(exam_col_width, 5, txt=exam_title, border=1, align="C", fill=True)
                x_pos += exam_col_width
                
                # Other columns
                pdf.set_xy(x_pos, current_y)
                pdf.cell(rating_col_width, header_height, txt="Rate", border=1, ln=0, align="C", fill=True)
                x_pos += rating_col_width
                
                if is_junior:
                    pdf.set_xy(x_pos, current_y)
                    pdf.cell(points_col_width, header_height, txt="Points", border=1, ln=0, align="C", fill=True)
                    x_pos += points_col_width
                
                pdf.set_xy(x_pos, current_y)
                pdf.cell(improvement_col_width, header_height, txt="Improve", border=1, ln=0, align="C", fill=True)
                x_pos += improvement_col_width
                
                pdf.set_xy(x_pos, current_y)
                pdf.cell(teacher_col_width, header_height, txt="Teacher", border=1, ln=0, align="C", fill=True)
                x_pos += teacher_col_width
                
                pdf.set_xy(x_pos, current_y)
                pdf.cell(comment_col_width, header_height, txt="Teachers Comments", border=1, ln=1, align="C", fill=True)
                
                # Reset Y position after header
                pdf.set_xy(10, current_y + header_height)
                print(f"DEBUG PDF: Header ends at Y={current_y + header_height}mm, data rows start here")
                
                # Data rows - Each subject as a row
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 6)
                
                print(f"DEBUG PDF: Starting data rows at Y={pdf.get_y()}mm")
                row_count = 0
                
                for subject in subjects:
                    row_count += 1
                    row_y = pdf.get_y()
                    print(f"DEBUG PDF: Row {row_count} ({subject}) starts at Y={row_y}mm")
                    
                    # Normalize subject name
                    normalized_subject = subject.replace('-', ' ').replace('/', ' ').title()
                    subject_key = subject_keys.get(normalized_subject, subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                    
                    # Subject name
                    pdf.cell(subject_col_width, 5, txt=subject[:18], border=1, ln=0, align="L")
                    
                    # Previous exam scores
                    for exam_col in exam_cols:
                        if not exam_col['is_current']:
                            exam_marks = exam_col['marks']
                            score = ""
                            if isinstance(exam_marks, dict):
                                subject_key_map = {
                                    'INT_SCIE': 'INTSCIE',
                                    'PRE_TECH': 'PRE-TECH',
                                    'C_A': 'C/A',
                                    'PRETECH': 'PRE-TECH',
                                    'CA': 'C/A'
                                }
                                subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                            pdf.cell(exam_col_width, 5, txt=str(score), border=1, ln=0, align="C")
                    
                    # Current exam score, rating, points
                    current_score = current_marks.get(f'{subject_key}_s', '')
                    current_rating = current_marks.get(f'{subject_key}_r', '')
                    current_points = current_marks.get(f'{subject_key}_p', '')
                    
                    pdf.cell(exam_col_width, 5, txt=str(current_score), border=1, ln=0, align="C")
                    pdf.cell(rating_col_width, 5, txt=str(current_rating), border=1, ln=0, align="C")
                    
                    if is_junior:
                        pdf.cell(points_col_width, 5, txt=str(current_points), border=1, ln=0, align="C")
                    
                    # Improvement - compare with latest previous exam
                    improvement = "-"
                    if previous_exams and len(previous_exams) > 0:
                        latest_prev_exam = previous_exams[0]
                        latest_prev_marks = latest_prev_exam.get('marks', {})
                        if isinstance(latest_prev_marks, dict):
                            subject_key_map = {
                                'INT_SCIE': 'INTSCIE',
                                'PRE_TECH': 'PRE-TECH',
                                'C_A': 'C/A',
                                'PRETECH': 'PRE-TECH',
                                'CA': 'C/A'
                            }
                            subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                            mapped_key = subject_key_map.get(subject_upper, subject_upper)
                            prev_score = latest_prev_marks.get(mapped_key, {}).get('score', '') if isinstance(latest_prev_marks.get(mapped_key, {}), dict) else ''
                            
                            if prev_score and current_score and prev_score not in ['', '-'] and current_score not in ['', '-']:
                                try:
                                    prev_num = float(prev_score)
                                    curr_num = float(current_score)
                                    diff = curr_num - prev_num
                                    if diff > 0:
                                        improvement = f"+{int(diff)}"
                                    elif diff < 0:
                                        improvement = f"{int(diff)}"
                                except:
                                    pass
                    
                    pdf.cell(improvement_col_width, 5, txt=improvement, border=1, ln=0, align="C")
                    
                    # Teacher name
                    teacher_name = teacher_map.get(subject, 'N/A')
                    pdf.cell(teacher_col_width, 5, txt=teacher_name[:15], border=1, ln=0, align="L")
                    
                    # Teacher comment - use multi_cell for wrapping
                    comment = self.rating_to_comment(current_rating, subject) if current_rating else 'No comment'
                    pdf.multi_cell(comment_col_width, 5, txt=comment, border=1, align="L")
                
                # Summary row - Total and Average with modern color
                pdf.set_fill_color(241, 245, 249)
                pdf.set_font("Helvetica", "B", 7)
                
                # Calculate totals
                current_total = 0
                if is_junior:
                    for subject in subjects:
                        subject_key = subject_keys.get(subject.replace('-', ' ').replace('/', ' ').title(), subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                        points = current_marks.get(f'{subject_key}_p', '')
                        if points and points not in ['', '-']:
                            try:
                                current_total += float(points)
                            except:
                                pass
                    total_label = "TOTAL POINTS"
                else:
                    for subject in subjects:
                        subject_key = subject_keys.get(subject.replace('-', ' ').replace('/', ' ').title(), subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                        score = current_marks.get(f'{subject_key}_s', '')
                        if score and score not in ['', '-']:
                            try:
                                current_total += float(score)
                            except:
                                pass
                    total_label = "TOTAL SCORES"
                
                avg_level = current_marks.get('average_points', '') or current_marks.get('average_level', '')
                
                pdf.cell(subject_col_width, 6, txt=total_label, border=1, ln=0, align="L", fill=True)
                
                # Previous exam totals - display total_points if available
                for exam_col in exam_cols:
                    if not exam_col['is_current']:
                        total_points = exam_col.get('total_points', '')
                        if total_points and total_points not in ['', '-']:
                            try:
                                pdf.cell(exam_col_width, 6, txt=str(int(total_points)), border=1, ln=0, align="C", fill=True)
                            except (ValueError, TypeError):
                                # If total_points is not numeric, show dash
                                pdf.cell(exam_col_width, 6, txt="-", border=1, ln=0, align="C", fill=True)
                        else:
                            pdf.cell(exam_col_width, 6, txt="-", border=1, ln=0, align="C", fill=True)
                
                pdf.cell(exam_col_width, 6, txt=str(int(current_total)) if current_total > 0 else "-", border=1, ln=0, align="C", fill=True)
                pdf.cell(rating_col_width, 6, txt=avg_level, border=1, ln=0, align="C", fill=True)
                
                if is_junior:
                    pdf.cell(points_col_width, 6, txt=str(int(current_total)) if current_total > 0 else "-", border=1, ln=0, align="C", fill=True)
                
                pdf.cell(improvement_col_width, 6, txt="-", border=1, ln=0, align="C", fill=True)
                pdf.cell(teacher_col_width, 6, txt="-", border=1, ln=0, align="C", fill=True)
                pdf.cell(comment_col_width, 6, txt="-", border=1, ln=1, align="C", fill=True)
                
                # Check if report fits on one page (A4 landscape height is 210mm)
                # Leave 40mm for footer section
                current_y = pdf.get_y()
                page_height = 210
                footer_space = 40
                max_y = page_height - footer_space
                
                print(f"DEBUG PDF: Current Y after table: {current_y}mm")
                print(f"DEBUG PDF: Max Y allowed for one page: {max_y}mm")
                
                # Performance History Chart - only if space available
                if current_y < max_y - 25:  # Need at least 25mm for chart (reduced height)
                    pdf.ln(8)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(0, 6, txt="Performance History", border=0, ln=1, align="L")
                    
                    # Draw simple bar chart for performance over exams
                    chart_x = 10
                    chart_y = pdf.get_y()
                    chart_width = 277  # Full width to touch right margin
                    chart_height = 20  # Reduced height to save space
                    
                    # Chart background with modern color
                    pdf.set_fill_color(248, 250, 252)
                    pdf.rect(chart_x, chart_y, chart_width, chart_height, 'DF')
                    
                    # Get performance data for chart
                    performance_data = []
                    for exam_col in exam_cols:
                        exam_name = exam_col['name']
                        exam_marks = exam_col['marks']
                        total = 0
                        if isinstance(exam_marks, dict):
                            for subject in subjects:
                                subject_key = subject_keys.get(subject.replace('-', ' ').replace('/', ' ').title(), subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                                if exam_col['is_current']:
                                    score = current_marks.get(f'{subject_key}_s', '')
                                    if is_junior:
                                        score = current_marks.get(f'{subject_key}_p', '')
                                else:
                                    subject_key_map = {
                                        'INT_SCIE': 'INTSCIE',
                                        'PRE_TECH': 'PRE-TECH',
                                        'C_A': 'C/A',
                                        'PRETECH': 'PRE-TECH',
                                        'CA': 'C/A'
                                    }
                                    subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                    mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                    score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                if score and score not in ['', '-']:
                                    try:
                                        total += float(score)
                                    except:
                                        pass
                        performance_data.append({'name': exam_name, 'total': total})
                    
                    # Draw bars
                    if performance_data:
                        max_total = max([d['total'] for d in performance_data]) if performance_data else 1
                        if max_total == 0:
                            max_total = 1
                        
                        # Calculate bar width to accommodate up to 8 exams
                        # Use 20mm total padding (10mm each side)
                        bar_width = (chart_width - 20) / len(performance_data)
                        bar_spacing = 5  # Spacing between bars
                        
                        for i, data in enumerate(performance_data):
                            bar_height = (data['total'] / max_total) * (chart_height - 15) if data['total'] > 0 else 0
                            bar_x = chart_x + 10 + i * bar_width
                            bar_y = chart_y + chart_height - 10 - bar_height
                            
                            # Bar color based on performance with modern vibrant colors
                            if data['total'] / max_total >= 0.8:
                                pdf.set_fill_color(34, 197, 94)  # Modern green
                            elif data['total'] / max_total >= 0.5:
                                pdf.set_fill_color(234, 179, 8)  # Modern yellow
                            else:
                                pdf.set_fill_color(239, 68, 68)  # Modern red
                            
                            pdf.rect(bar_x, bar_y, bar_width - bar_spacing, bar_height, 'F')
                            
                            # Exam name below bar
                            pdf.set_xy(bar_x, chart_y + chart_height - 8)
                            label_width = bar_width - bar_spacing
                            label_font_size = 6
                            pdf.set_font("Helvetica", "", label_font_size)
                            while label_font_size > 3 and pdf.get_string_width(data['name']) > label_width:
                                label_font_size -= 0.5
                                pdf.set_font("Helvetica", "", label_font_size)
                            pdf.cell(label_width, 5, txt=data['name'], border=0, ln=0, align="C")
                            
                            # Total above bar
                            if data['total'] > 0:
                                pdf.set_xy(bar_x, bar_y - 4)
                                pdf.set_font("Helvetica", "B", 6)
                                pdf.cell(bar_width - bar_spacing, 4, txt=str(int(data['total'])), border=0, ln=0, align="C")
                    
                    pdf.ln(5)
                    print(f"DEBUG PDF: Performance history chart added")
                else:
                    print(f"DEBUG PDF: Performance history chart skipped - not enough space (current_y={current_y}mm, max_y={max_y}mm)")
                
                pdf.ln(5)

            # Footer Sections - Comments and Signature
            pdf.ln(5)
            
            # Get average level for comments - use same logic as cloud
            average_level = current_marks.get('average_level', '')
            # Extract rating string if it's a tuple
            if isinstance(average_level, tuple):
                average_level = average_level[0]
            # Fallback: calculate average from marks if not provided
            if not average_level:
                scores = []
                for key in current_marks.keys():
                    if key.endswith('_s') and key not in ['total_points_s', 'average_level_s', 'rank_s']:
                        score = current_marks.get(key, '')
                        if score and score not in ['', '-']:
                            try:
                                scores.append(float(score))
                            except:
                                pass
                if scores:
                    avg_score = sum(scores) / len(scores)
                    # Convert to rating for junior grades
                    if is_junior:
                        from grading_logic import get_grade_7_8_rating
                        rating_result = get_grade_7_8_rating(avg_score)
                    else:
                        from grading_logic import get_grade_4_6_rating
                        rating_result = get_grade_4_6_rating(avg_score)
                    # Extract rating string if it's a tuple
                    if isinstance(rating_result, tuple):
                        average_level = rating_result[0]
                    else:
                        average_level = rating_result
                else:
                    average_level = 'BE2'
            
            # Comments Frame - reduced height to fit on page with modern color
            pdf.set_fill_color(241, 245, 249)
            frame_y = pdf.get_y()
            pdf.rect(10, frame_y, 277, 20, 'DF')  # Reduced from 30 to 20
            
            # Class Teacher Comment
            pdf.set_xy(15, frame_y + 3)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 5, txt="Class Teacher: " + self.get_class_teacher_comment(average_level), border=0, ln=1, align="L")
            
            # Head Teacher Comment
            pdf.set_xy(15, frame_y + 10)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 5, txt="Head Teacher: " + self.get_head_teacher_comment(average_level), border=0, ln=1, align="L")
            
            pdf.set_y(frame_y + 25)
            
            # School Administrator Signature - compact
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 5, txt=f"{school_administrator} (School Administrator)", border=0, ln=1)
            
            # Signature image or line - compact
            if signature_path and os.path.exists(signature_path):
                try:
                    signature_y = pdf.get_y()
                    pdf.image(signature_path, x=10, y=signature_y, h=20)
                    pdf.ln(25)
                except:
                    signature_y = pdf.get_y()
                    pdf.cell(0, 5, txt="_________________", border=0, ln=1)
                    pdf.ln(3)
            else:
                signature_y = pdf.get_y()
                pdf.cell(0, 5, txt="_________________", border=0, ln=1)
                pdf.ln(3)

            if date_range and date_range.get("opening_date") and date_range.get("closing_date"):
                date_box_x = 211
                date_box_y = signature_y - 2
                pdf.set_draw_color(40, 122, 101)
                pdf.set_fill_color(240, 249, 246)
                pdf.rect(date_box_x, date_box_y, 76, 25, "DF")
                pdf.set_xy(date_box_x + 4, date_box_y + 2)
                pdf.set_text_color(40, 122, 101)
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(68, 5, txt="SCHOOL DATES", border=0, ln=1, align="C")
                pdf.set_x(date_box_x + 5)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 7)
                pdf.cell(66, 6, txt=f"Opening: {date_range['opening_date']}", border=0, ln=1)
                pdf.set_x(date_box_x + 5)
                pdf.cell(66, 6, txt=f"Closing: {date_range['closing_date']}", border=0, ln=1)

            pdf.output(file_path)
            if temporary_photo_path and os.path.exists(temporary_photo_path):
                os.remove(temporary_photo_path)
                temporary_photo_path = None
            if show_messages:
                messagebox.showinfo("Success", "PDF generated successfully!")
            return True

        except Exception as e:
            # Only show error message for individual printing (when file_path is not provided)
            if show_messages:
                messagebox.showerror("Error", f"PDF Generation Failed: {e}")
            else:
                # For batch printing, just print to console
                print(f"PDF Generation Failed: {e}")
            return False
        finally:
            if temporary_photo_path and os.path.exists(temporary_photo_path):
                os.remove(temporary_photo_path)
    
    def send_student_report_to_portal(self, student):
        credentials = self.get_cloud_credentials()
        if not credentials:
            return
        
        # Generate report data
        report_data = self.generate_report_data(student)
        
        # Send to cloud
        service = CloudService()
        result = service.send_student_report(report_data, credentials)
        
        if result.get('success'):
            messagebox.showinfo("Success", f"Report for {student['name']} sent to portal successfully.")
        else:
            messagebox.showerror("Error", f"Failed to send report: {result.get('message')}")
    
    def send_class_reports_to_portal(self):
        if not self.current_class:
            return
        
        credentials = self.get_cloud_credentials()
        if not credentials:
            return
        
        students = self.get_students_in_class(self.current_class)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return
        
        service = CloudService()
        success_count = 0
        
        for student in students:
            report_data = self.generate_report_data(student)
            result = service.send_student_report(report_data, credentials)
            
            if result.get('success'):
                success_count += 1
        
        messagebox.showinfo("Success", f"Sent {success_count}/{len(students)} reports to portal.")
    
    def send_all_reports_to_portal(self):
        credentials = self.get_cloud_credentials()
        if not credentials:
            return
        
        classes = self.get_available_classes()
        if not classes:
            messagebox.showinfo("Info", "No classes found.")
            return
        
        service = CloudService()
        total_success = 0
        total_students = 0
        
        for class_name in classes:
            students = self.get_students_in_class(class_name)
            total_students += len(students)
            
            for student in students:
                report_data = self.generate_report_data(student)
                result = service.send_student_report(report_data, credentials)
                
                if result.get('success'):
                    total_success += 1
        
        messagebox.showinfo("Success", f"Sent {total_success}/{total_students} reports to portal.")
    
    def print_class_reports(self):
        if not self.current_class:
            return
        
        students = self.get_students_in_class(self.current_class)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return

        report_mode = ask_report_print_mode(self)
        if report_mode is None:
            return
        date_range = self.ask_opening_closing_dates()
        if date_range is None:
            return
        output_dir = filedialog.askdirectory(parent=self, title="Choose folder for class report PDFs")
        if not output_dir:
            return
        self._print_students_to_folder(students, output_dir, date_range, report_mode)
    
    def print_all_reports(self):
        classes = self.get_available_classes()
        if not classes:
            messagebox.showinfo("Info", "No classes found.")
            return
        
        students = [student for class_name in classes for student in self.get_students_in_class(class_name)]
        if not students:
            messagebox.showinfo("Info", "No students found.")
            return

        report_mode = ask_report_print_mode(self)
        if report_mode is None:
            return
        date_range = self.ask_opening_closing_dates()
        if date_range is None:
            return
        output_dir = filedialog.askdirectory(parent=self, title="Choose folder for all report PDFs")
        if not output_dir:
            return
        self._print_students_to_folder(students, output_dir, date_range, report_mode)

    def _print_students_to_folder(self, students, output_dir, date_range, report_mode):
        success_count = 0
        for student in students:
            report_data = self.generate_report_data(student)
            if not report_data:
                continue
            safe_name = "".join(
                character if character.isalnum() or character in "-_ " else "_"
                for character in student.get("name", "student")
            ).strip().replace(" ", "_")
            safe_adm = "".join(
                character if character.isalnum() or character in "-_" else "_"
                for character in str(student.get("adm_no", ""))
            )
            file_name = f"{safe_name}_{safe_adm or 'report'}.pdf"
            if self.print_report_pdf(
                None, report_data, os.path.join(output_dir, file_name), date_range, report_mode
            ):
                success_count += 1
        messagebox.showinfo(
            "Print complete",
            f"Created {success_count} of {len(students)} report PDFs in:\n{output_dir}",
        )
    
    def _photo_for_cloud(self, photo_value):
        """Return a web-displayable photo URL for cloud report payloads."""
        if not photo_value:
            return ""

        photo_value = str(photo_value).strip()
        if photo_value.startswith(("data:image/", "https://", "http://")):
            return photo_value
        if not os.path.isfile(photo_value):
            print(f"DEBUG: Student photo path is not a local file: {photo_value}")
            return ""

        try:
            import base64
            from io import BytesIO

            with Image.open(photo_value) as image:
                image.thumbnail((600, 800))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=78, optimize=True)

            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            print(f"DEBUG: Could not prepare student photo for cloud: {e}")
            return ""

    @staticmethod
    def _report_subject_token(value):
        return "".join(character for character in str(value or "").casefold() if character.isalnum())

    def _report_learning_area(self, subject, grade):
        area = SUBJECT_TO_LEARNING_AREA.get(str(subject).strip().upper())
        if area:
            return area
        area = {
            "INT SCI": "Integrated Science",
            "INT SCIE": "Integrated Science",
            "SCI": "Science & Technology",
            "SCIE": "Science & Technology",
            "CREAT": "Creative Arts and Sports",
            "ARTS": "Creative Arts and Sports",
            "REL": "Religious Education",
            "RE": "Religious Education",
        }.get(str(subject).strip().upper())
        if area:
            return area
        grade_type = self._grade_type_for_report(grade)
        configured_names = self.school_config.get("subject_names", {}).get(grade_type, {})
        if subject in configured_names:
            return configured_names[subject]
        token = self._report_subject_token(subject)
        for items in (self.school_config.get("subject_catalog") or {}).values():
            for item in items:
                if self._report_subject_token(item.get("short")) == token:
                    return str(item.get("name") or subject).strip()
        return str(subject).strip()

    @staticmethod
    def _grade_type_for_report(grade):
        return {
            "playgroup": "playgroup", "pp1": "pp1", "pp2": "pp2",
            "grade 1": "lower", "grade 2": "lower", "grade 3": "lower",
            "grade 4": "primary", "grade 5": "primary", "grade 6": "primary",
            "grade 7": "jss", "grade 8": "jss", "grade 9": "jss",
        }.get(str(grade).strip().casefold(), "")

    def _report_cbc_records(self, student, subjects, term, year):
        configured = self.school_config.get("cbc_levels", {}).get(student.get("grade"), {})
        if not configured:
            return []
        assessment_number = str(student.get("assessment_number") or "").strip()
        if not assessment_number:
            try:
                self.db.cursor().execute(
                    "SELECT assessment_number FROM students WHERE adm_no = ?",
                    (student.get("adm_no"),),
                )
                row = self.db.cursor().fetchone()
                assessment_number = str(row[0] or "").strip() if row else ""
            except Exception:
                assessment_number = ""
        learner_name = self._report_subject_token(student.get("name"))
        requested_areas = {self._report_learning_area(subject, student.get("grade")) for subject in subjects}
        aliases = {
            "Agriculture and Nutrition": ("Agriculture",),
            "Agriculture": ("Agriculture and Nutrition",),
            "Creative Arts and Sports": ("Creative Arts",),
            "Creative Arts": ("Creative Arts and Sports",),
        }
        matches = {}
        for area in requested_areas:
            for area_name in (area, *aliases.get(area, ())):
                by_term = configured.get(area_name, {})
                record = by_term.get(f"{year}|{term}") if year else None
                if record is None:
                    legacy = by_term.get(term)
                    if legacy and (not year or str(legacy.get("academic_year", year)) == str(year)):
                        record = legacy
                if not isinstance(record, dict):
                    continue
                for raw in record.get("records", []):
                    if len(raw) < 6:
                        continue
                    number, learner = str(raw[0] or "").strip(), str(raw[1] or "").strip()
                    if assessment_number and number:
                        belongs = number.casefold() == assessment_number.casefold()
                    else:
                        belongs = self._report_subject_token(learner) == learner_name
                    if belongs:
                        normalized = [raw[0], raw[1], area, *raw[3:]]
                        key = tuple(str(value or "") for value in normalized[:5])
                        matches[key] = normalized
        return list(matches.values())

    def _previous_subject_score(self, marks, subject):
        target = self._report_subject_token(subject)
        aliases = {
            "math": "mathematics", "mat": "mathematics", "eng": "english",
            "kisw": "kiswahili", "intsci": "integratedscience", "intscie": "integratedscience",
            "scie": "sciencetechnology",
            "pretech": "pretechnicalstudies", "agri": "agricultureandnutrition",
            "sst": "socialstudies", "ca": "creativeartsandsports", "rel": "religiouseducation",
        }
        target = aliases.get(target, target)
        if not isinstance(marks, dict):
            return "-"
        for key, value in marks.items():
            normalized = self._report_subject_token(key)
            normalized = aliases.get(normalized, normalized)
            if normalized != target:
                continue
            if isinstance(value, dict):
                value = value.get("score", "")
            return value if value not in (None, "") else "-"
        return "-"

    @staticmethod
    def _level_color(level):
        return {"BE": "#b91c1c", "AE": "#c2410c", "ME": "#1d4ed8", "EE": "#15803d"}.get(level, "#64748b")

    def _average_cbc_rating(self, report_data):
        values = {"BE": 1, "AE": 2, "ME": 3, "EE": 4}
        ratings = [values[item.get("rating")] for item in report_data.get("subject_results", []) if item.get("rating") in values]
        if not ratings:
            return ""
        average = sum(ratings) / len(ratings)
        return {1: "BE", 2: "AE", 3: "ME", 4: "EE"}[min(4, max(1, int(average + 0.5)))]

    def generate_report_data(self, student):
        if not hasattr(self, "subject_comment_indices"):
            self.subject_comment_indices = build_subject_comment_indices(
                self.school_config.get("subjects", {})
            )

        print(f"DEBUG: generate_report_data called for {student.get('name', 'Unknown')} in {student['grade']}")
        print(f"DEBUG: generate_report_data - Student keys: {list(student.keys())}")
        print(f"DEBUG: generate_report_data - Photo field: {student.get('photo', 'NOT FOUND')}")
        current_marks = self.get_student_current_marks(student['adm_no'], student['grade'])
        
        # If no current marks, return None - don't print report
        if not current_marks:
            print(f"DEBUG: No current marks found for {student.get('name', 'Unknown')} in {student['grade']}")
            return None
        print(f"DEBUG: Current marks found, proceeding with report generation")
        
        # Use current_exam_title for consistency with performance history graph
        exam_title = self.school_config.get("current_exam_title", "PERFORMANCE REPORT")
        
        # Fetch previous exams for this student
        previous_exams_data = []
        previous_exams_list = self.db.get_previous_exams(student['grade'])
        print(f"DEBUG: Found {len(previous_exams_list)} previous exams in database for grade {student['grade']}")
        for exam_name, exam_date in previous_exams_list:
            print(f"DEBUG: Previous exam: {exam_name} at {exam_date}")
        
        # Get subject names from school config instead of current marks
        # This ensures we use the correct subject names even if current marks are incomplete
        subject_names = self.get_subjects_for_grade(student['grade'])
        print(f"DEBUG: Subject names from config: {subject_names}")
        
        for exam_name, exam_date in previous_exams_list:  # Get all previous exams
            marks_data, summary_data = self.db.get_previous_exam_data(exam_name, student['grade'])
            print(f"DEBUG: Got marks_data for {exam_name}: {marks_data is not None}")
            if marks_data:
                # Parse the marks data to extract this student's marks
                try:
                    import json
                    # Handle both list and dict structures
                    if isinstance(marks_data, str):
                        marks_data = json.loads(marks_data)
                    
                    if isinstance(marks_data, list):
                        # List format: [[name, score1, rating1, score2, rating2, ...], ...]
                        # Junior format: [[name, score1, rating1, points1, score2, rating2, points2, ...], ...]
                        print(f"DEBUG: Marks data is a list with {len(marks_data)} students")
                        print(f"DEBUG: Student grade: {student['grade']}")
                        
                        # Detect if this is junior format (has 3 values per subject: score, rating, points)
                        # by checking if the data length suggests 3 values per subject
                        grade_lower = student['grade'].lower()
                        is_junior = grade_lower in ["grade 7", "grade 8", "grade 9"]
                        
                        for student_record in marks_data:
                            if len(student_record) > 0:
                                record_name = student_record[0]
                                record_key = "".join(record_name.split()).lower()
                                if record_key == "".join(student['name'].split()).lower():
                                    # Found the student, extract their marks
                                    # Convert list to dict format with subject names
                                    marks_dict = {}
                                    marks_list = student_record[1:]  # Skip name
                                    # Valid rating patterns
                                    rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
                                    
                                    # Determine format based on grade
                                    if is_junior:
                                        # Junior format: [score1, rating1, points1, score2, rating2, points2, ...]
                                        print(f"DEBUG: Using junior format (score, rating, points)")
                                        for i, subject_name in enumerate(subject_names):
                                            if i * 3 + 2 < len(marks_list):
                                                score = marks_list[i * 3]
                                                rating = marks_list[i * 3 + 1]
                                                points = marks_list[i * 3 + 2]
                                                
                                                # For junior, use score as the display value (not points)
                                                marks_dict[subject_name.upper().replace(' ', '')] = {
                                                    'score': score,
                                                    'rating': rating,
                                                    'points': points
                                                }
                                                print(f"DEBUG: Junior {subject_name}: score={score}, rating={rating}, points={points}")
                                    else:
                                        # Playgroup/Primary format: [score1, rating1, score2, rating2, ...]
                                        print(f"DEBUG: Using standard format (score, rating)")
                                        for i, subject_name in enumerate(subject_names):
                                            if i * 2 + 1 < len(marks_list):
                                                score = marks_list[i * 2]
                                                rating = marks_list[i * 2 + 1]
                                                
                                                marks_dict[subject_name.upper().replace(' ', '')] = {
                                                    'score': score,
                                                    'rating': rating
                                                }
                                    # Extract total_points and average_level if present (last 2 items after subjects)
                                    # Format: [name, score1, rating1, ..., total, average_level]
                                    total_points = None
                                    avg_level = None
                                    print(f"DEBUG: marks_list length: {len(marks_list)}, subject_names count: {len(subject_names)}")
                                    print(f"DEBUG: marks_list last 5 items: {marks_list[-5:]}")
                                    
                                    if is_junior:
                                        # Junior format: [name, score1, rating1, points1, ..., total_points, average_level]
                                        # Calculate expected length: 1 (name) + 3 * num_subjects + 2 (total, avg)
                                        expected_len = 1 + len(subject_names) * 3 + 2
                                        print(f"DEBUG: Junior expected_len={expected_len}, actual_len={len(marks_list)}")
                                        
                                        if len(marks_list) >= expected_len:
                                            avg_level = marks_list[-1]  # Last item is average_level
                                            total_points = marks_list[-2]  # Second to last item is total_points
                                            print(f"DEBUG: Junior total_points from end={total_points}, avg_level={avg_level}")
                                            # Validate that total_points is numeric
                                            try:
                                                int(total_points)
                                            except (ValueError, TypeError):
                                                print(f"DEBUG: total_points '{total_points}' is not numeric, calculating from subject points")
                                                total_points = 0
                                                for i, subject_name in enumerate(subject_names):
                                                    if i * 3 + 2 < len(marks_list):
                                                        points = marks_list[i * 3 + 2]
                                                        try:
                                                            total_points += int(points)
                                                        except:
                                                            pass
                                                print(f"DEBUG: Junior recalculated total_points={total_points} from subject points")
                                        else:
                                            # Try to calculate total from points if not present at end
                                            total_points = 0
                                            for i, subject_name in enumerate(subject_names):
                                                if i * 3 + 2 < len(marks_list):
                                                    points = marks_list[i * 3 + 2]
                                                    try:
                                                        total_points += int(points)
                                                    except:
                                                        pass
                                            print(f"DEBUG: Junior calculated total_points={total_points} from subject points (list too short)")
                                    else:
                                        # Standard format: [name, score1, rating1, ..., total_points, average_level]
                                        # Calculate expected length: 1 (name) + 2 * num_subjects + 2 (total, avg)
                                        expected_len = 1 + len(subject_names) * 2 + 2
                                        if len(marks_list) >= expected_len:
                                            avg_level = marks_list[-1]  # Last item is average_level
                                            total_points = marks_list[-2]  # Second to last item is total_points
                                            print(f"DEBUG: Standard total_points={total_points}, avg_level={avg_level}")
                                        else:
                                            # Try to calculate total from scores if not present at end
                                            total_points = 0
                                            for i, subject_name in enumerate(subject_names):
                                                if i * 2 < len(marks_list):
                                                    score = marks_list[i * 2]
                                                    try:
                                                        total_points += int(score)
                                                    except:
                                                        pass
                                            print(f"DEBUG: Standard calculated total_points={total_points} from subject scores")
                                    
                                    # Check if all marks are empty - if so, skip this exam
                                    has_data = False
                                    for subject, mark_data in marks_dict.items():
                                        score = mark_data.get('score', '')
                                        if score and str(score).strip():
                                            has_data = True
                                            break
                                    
                                    if not has_data:
                                        print(f"DEBUG: Skipping {exam_name} - all marks are empty for this student")
                                    else:
                                        previous_exams_data.append({
                                            'exam_name': exam_name,
                                            'exam_date': exam_date,
                                            'marks': marks_dict,
                                            'total_points': total_points,
                                            'average_level': avg_level
                                        })
                                        print(f"DEBUG: Added previous exam {exam_name} with mapped dict marks, total_points={total_points}, avg_level={avg_level}")
                                    print(f"DEBUG: marks_dict keys: {list(marks_dict.keys())}")
                                    print(f"DEBUG: marks_dict sample: {list(marks_dict.items())[:3]}")
                                    break
                    elif isinstance(marks_data, dict):
                        print(f"DEBUG: Marks dict keys: {list(marks_dict.keys())[:5]}")  # Show first 5 keys
                        # Find this student's marks
                        student_key = "".join(student['name'].split()).lower()
                        print(f"DEBUG: Looking for student key: {student_key} in marks_dict")
                        if student_key in marks_dict:
                            student_marks = marks_dict[student_key]
                            # Extract total_points and average_level if present
                            total_points = student_marks.get('total_points') if isinstance(student_marks, dict) else None
                            avg_level = student_marks.get('average_level') if isinstance(student_marks, dict) else None
                            
                            # Fix swapped score/rating fields in dict format
                            # Valid rating patterns
                            rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
                            if isinstance(student_marks, dict):
                                for subject, mark_data in student_marks.items():
                                    if isinstance(mark_data, dict):
                                        score = mark_data.get('score', '')
                                        rating = mark_data.get('rating', '')
                                        
                                        # Enhanced validation to fix corrupted score/rating fields
                                        score_str = str(score).strip()
                                        rating_str = str(rating).strip()
                                        
                                        # Case 1: score is a rating pattern and rating looks like a score/number
                                        if score_str in rating_patterns and rating_str.isdigit():
                                            print(f"DEBUG: Swapping score/rating for {subject}: score={score}, rating={rating}")
                                            mark_data['score'] = rating
                                            mark_data['rating'] = score
                                        # Case 2: score is a rating pattern and rating is also a rating (corrupted)
                                        elif score_str in rating_patterns and rating_str in rating_patterns:
                                            print(f"DEBUG: Both score and rating are ratings for {subject}: score={score}, rating={rating}")
                                            # Keep first rating as rating, set score to empty
                                            mark_data['rating'] = score_str
                                            mark_data['score'] = ''
                                        # Case 3: score is a point (1-8) and rating is a rating (swapped)
                                        elif score_str.isdigit() and 1 <= int(score_str) <= 8 and rating_str in rating_patterns:
                                            print(f"DEBUG: Score is point and rating is rating for {subject}: score={score}, rating={rating}")
                                            # This might be correct for playgroup, but for junior we want scores
                                            # For now, keep as is since points are valid for some grades
                                        # Case 4: score is a point (1-8) and rating is also a point (corrupted)
                                        elif score_str.isdigit() and rating_str.isdigit() and 1 <= int(score_str) <= 8 and 1 <= int(rating_str) <= 8:
                                            print(f"DEBUG: Both score and rating are points for {subject}: score={score}, rating={rating}")
                                            # Keep first point as score, set rating to empty
                                            mark_data['score'] = score_str
                                            mark_data['rating'] = ''
                            
                            # Check if all marks are empty - if so, skip this exam
                            has_data = False
                            if isinstance(student_marks, dict):
                                for subject, mark_data in student_marks.items():
                                    if isinstance(mark_data, dict):
                                        score = mark_data.get('score', '')
                                        if score and str(score).strip():
                                            has_data = True
                                            break
                            
                            if not has_data:
                                print(f"DEBUG: Skipping {exam_name} - all marks are empty for this student")
                            else:
                                previous_exams_data.append({
                                    'exam_name': exam_name,
                                    'exam_date': exam_date,
                                    'marks': student_marks,
                                    'total_points': total_points,
                                    'average_level': avg_level
                                })
                                print(f"DEBUG: Added previous exam {exam_name} with dict marks, total_points={total_points}, avg_level={avg_level}")
                        else:
                            print(f"DEBUG: Student key not found in marks_dict")
                except Exception as e:
                    print(f"DEBUG: Error parsing marks data: {e}")
                    import traceback
                    traceback.print_exc()
                    pass
        
        print(f"DEBUG: Total previous_exams_data: {len(previous_exams_data)}")

        subjects = self.get_subjects_for_grade(student["grade"])
        term = self.school_config.get("marksheet_term") or self.school_config.get("current_term") or "Term 1"
        year = self.school_config.get("academic_year")
        rubric_records = self._report_cbc_records(student, subjects, term, year)
        subject_areas = [
            (subject, self._report_learning_area(subject, student["grade"]))
            for subject in subjects
        ]
        subject_results = build_subject_results(subject_areas, current_marks, rubric_records)
        grouped_rubrics = {
            item["name"].casefold(): item for item in group_rubric_records(rubric_records)
        }
        rubric_subjects = []
        for subject, area in subject_areas:
            detail = grouped_rubrics.get(area.casefold()) or {
                "strands": [], "recommendations": []
            }
            rubric_subjects.append({"name": area, **detail})

        performance_history = []
        for exam in reversed(previous_exams_data):
            scores = {}
            for subject in subjects:
                value = self._previous_subject_score(exam.get("marks", {}), subject)
                try:
                    score = float(value)
                    if 0 <= score <= 100:
                        scores[subject] = score
                except (TypeError, ValueError):
                    continue
            performance_history.append({"name": exam.get("exam_name", "Previous"), "subjects": scores})
        current_scores = {
            item["subject"]: item["composite_score"]
            for item in subject_results
            if item.get("composite_score") is not None
        }
        performance_history.append({"name": exam_title, "subjects": current_scores})
        pathway = None
        if student["grade"] in ("Grade 7", "Grade 8", "Grade 9"):
            prior_scores = [item["subjects"] for item in performance_history[:-1]]
            pathway = pathway_recommendation(current_scores, prior_scores, term)
        teacher_comments = build_teacher_comments(
            subject_results, rubric_subjects, student.get("name", "")
        )

        return {
            'student_name': student['name'],
            'adm_no': student['adm_no'],
            'stream': student.get('stream', 'none'),
            'grade': student['grade'],
            'school_name': self.school_config.get('school_name', ''),
            'current_marks': current_marks,
            'term': term,
            'academic_year': year,
            'subjects': subjects,
            'subject_labels': {
                subject: self._report_learning_area(subject, student["grade"])
                for subject in subjects
            },
            'subject_results': subject_results,
            'average_rating': self._average_cbc_rating({'subject_results': subject_results}),
            'teacher_comments': teacher_comments,
            'rubric_subjects': rubric_subjects,
            'performance_history': performance_history,
            'pathway_recommendation': pathway,
            'class_teacher': self.get_class_teacher(student['grade']),
            'exam_title': exam_title,
            'previous_exams': previous_exams_data,
            'subject_comment_indices': self.subject_comment_indices,
            'generated_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'photo': self._photo_for_cloud(
                student.get('photo') or student.get('student_photo') or student.get('image_path')
            )
        }
    
    def get_cloud_credentials(self):
        cloud_config = self.school_config
        cloud_school_code = cloud_config.get('cloud_school_code', '').strip()
        cloud_teacher_username = cloud_config.get('cloud_teacher_username', '').strip()
        cloud_teacher_password = cloud_config.get('cloud_teacher_password', '').strip()
        
        if not cloud_school_code or not cloud_teacher_username:
            messagebox.showwarning("Cloud Not Configured", "Please configure cloud credentials in school settings.")
            return None
        
        if cloud_teacher_password:
            return {
                'school_code': cloud_school_code,
                'username': cloud_teacher_username,
                'password': cloud_teacher_password
            }
        else:
            return ask_cloud_credentials(self)
    
    def return_to_dashboard(self):
        self.destroy()
        self.parent_window.deiconify()


if __name__ == "__main__":
    app = ReportFormsView(None, FreemanDB())
    app.mainloop()
