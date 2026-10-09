import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import json
import logging
from database import FreemanDB
from cloud_service import CloudService, ask_cloud_credentials
from grading_logic import get_grade_7_8_rating, get_grade_4_6_rating
from fpdf import FPDF
import datetime

# Log when reportforms is imported
logging.info("=" * 60)
logging.info("REPORTFORMS.PY - MODULE IMPORTED")
logging.info("=" * 60)
logging.info(f"ReportForms imported from: {__file__}")
logging.info(f"sys.frozen: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    logging.info(f"sys._MEIPASS: {sys._MEIPASS}")
logging.info("=" * 60)


class ReportFormsView(ctk.CTkToplevel):
    def __init__(self, parent_window, db):
        super().__init__(parent_window)

        logging.info("=" * 60)
        logging.info("REPORTFORMS VIEW - INITIALIZING")
        logging.info("=" * 60)

        self.parent_window = parent_window
        self.db = db
        self.current_class = None
        self.current_student = None
        self.current_report_window = None  # Track the current report window for dialog parenting

        # Initialize proper paths for executable environment
        if getattr(sys, 'frozen', False):
            # Running as executable
            self.BASE_DIR = sys._MEIPASS
            self.USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
            os.makedirs(self.USER_DATA_DIR, exist_ok=True)
            logging.info(f"Running in EXECUTABLE mode")
            logging.info(f"  BASE_DIR: {self.BASE_DIR}")
            logging.info(f"  USER_DATA_DIR: {self.USER_DATA_DIR}")
        else:
            # Running as script
            self.BASE_DIR = os.path.dirname(os.path.realpath(__file__))
            self.USER_DATA_DIR = self.BASE_DIR
            logging.info(f"Running in SCRIPT mode")
            logging.info(f"  BASE_DIR: {self.BASE_DIR}")
            logging.info(f"  USER_DATA_DIR: {self.USER_DATA_DIR}")

        logging.info("Loading school config...")
        self.school_config = self.load_school_config()
        logging.info(f"School config loaded: {len(self.school_config)} keys")
        logging.info("=" * 60)
        
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

        # Debug: Check if student has photo
        print(f"DEBUG show_report_form: Student keys: {list(student.keys())}")
        print(f"DEBUG show_report_form: Photo field: {student.get('photo', 'NOT FOUND')}")

        # Create report form window
        report_window = ctk.CTkToplevel(self)
        report_window.title(f"Report Form - {student['name']}")
        report_window.geometry("1000x800")
        self.current_report_window = report_window  # Store reference for dialog parenting
        
        # Main container
        report_container = ctk.CTkScrollableFrame(report_window)
        report_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # School header
        self.create_school_header(report_container, student)
        
        # Student info
        self.create_student_info(report_container, student)
        
        # Current marks section
        self.create_current_marks_section(report_container, student)
        
        # Previous marks section
        self.create_previous_marks_section(report_container, student)
        
        # Signature section
        self.create_signature_section(report_container, student)
        
        # Action buttons
        button_frame = ctk.CTkFrame(report_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=30)
        
        # Print PDF button
        print_btn = ctk.CTkButton(button_frame, text="📄 Print as PDF",
                                 fg_color="#27ae60", hover_color="#1e8449",
                                 font=("Arial Bold", 14), height=45, width=200,
                                 command=lambda: self.print_report_pdf(report_container, student, opening_date=None, closing_date=None))
        print_btn.pack(side="left", padx=10)
        
        # Send to parent button
        send_btn = ctk.CTkButton(button_frame, text="📤 Send Report to Parent",
                                fg_color="#3498db", hover_color="#2980b9",
                                font=("Arial Bold", 14), height=45, width=200,
                                command=lambda: self.send_student_report_to_portal(student))
        send_btn.pack(side="left", padx=10)
        
        # Close button
        close_btn = ctk.CTkButton(button_frame, text="✕ Close",
                                 fg_color="#e74c3c", hover_color="#c0392b",
                                 font=("Arial Bold", 14), height=45, width=150,
                                 command=report_window.destroy)
        close_btn.pack(side="right", padx=10)
    
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
                try:
                    logo_photo = ctk.CTkImage(Image.open(logo_path), size=(80, 80))
                    logo_label = ctk.CTkLabel(logo_frame, image=logo_photo, text="")
                    logo_label.pack(pady=10)
                except Exception as img_error:
                    print(f"Error loading logo: {img_error}")
                    logo_label = ctk.CTkLabel(logo_frame, text="SCHOOL\nLOGO",
                                             font=("Arial Bold", 10), text_color="#666")
                    logo_label.pack(pady=20)
            else:
                logo_label = ctk.CTkLabel(logo_frame, text="SCHOOL\nLOGO",
                                         font=("Arial Bold", 10), text_color="#666")
                logo_label.pack(pady=20)
        except Exception as e:
            print(f"Error in logo display: {e}")
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
            except Exception as img_error:
                print(f"Error loading student photo: {img_error}")
                photo_label = ctk.CTkLabel(photo_frame, text="STUDENT\nPHOTO",
                                         font=("Arial Bold", 10), text_color="#666")
                photo_label.pack(pady=20)
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

    def rating_to_comment(self, rating):
        """Convert rating to teacher comment based on performance level"""
        rating_comments = {
            "BE1": "A starting point. Focus on understanding the basic concepts, and I am here to help you practice.",
            "BE2": "You are showing effort, but need more practice on the fundamentals to reach the expected level.",
            "AE1": "You are approaching the expected level. With more practice, you will master this.",
            "AE2": "Good effort shown. Keep working on the basics to build a stronger foundation.",
            "ME1": "Good progress. You are grasping the core ideas; continue practicing to gain more confidence.",
            "ME2": "Well done! You are very close to mastering this. Pay close attention to the finer details.",
            "EE1": "Great work! You have successfully demonstrated this competency. Keep up the consistent performance.",
            "EE2": "Outstanding! You have mastered the task and shown deep understanding. Keep challenging yourself.",
        }
        return rating_comments.get(rating, "No comment available.")

    def get_class_teacher_comment(self, average_level):
        """Get class teacher comment based on average level"""
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
        subject_keys = {}
        for subject in subjects:
            normalized = subject.replace('-', ' ').replace('/', ' ').title()
            key = subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_')
            subject_keys[normalized] = key

        # Determine if junior (has points)
        is_junior = grade.lower() in ["grade 7", "grade 8", "grade 9"]

        # Prepare exam columns (previous + current)
        exam_cols = []
        if previous_exams and len(previous_exams) >= 2:
            exam_cols.append({'name': previous_exams[1].get('exam_name', ''), 'marks': previous_exams[1].get('marks', {}), 'is_current': False})
        if previous_exams and len(previous_exams) >= 1:
            exam_cols.append({'name': previous_exams[0].get('exam_name', ''), 'marks': previous_exams[0].get('marks', {}), 'is_current': False})
        exam_cols.append({'name': exam_title, 'marks': current_marks, 'is_current': True})

        # Table frame with portal styling
        table_frame = ctk.CTkFrame(container, fg_color="white", corner_radius=12)
        table_frame.pack(fill="x", padx=20, pady=10)

        # Calculate column widths for proper alignment
        subject_width = 100
        exam_width = 60
        rate_width = 40
        points_width = 40 if is_junior else 0
        improve_width = 60
        teacher_width = 80
        comment_width = 200

        total_width = subject_width + (len(exam_cols) * exam_width) + rate_width + points_width + improve_width + teacher_width + comment_width

        # Header row with portal purple gradient (simulated with solid color)
        header_frame = ctk.CTkFrame(table_frame, fg_color="#667eea", height=35, corner_radius=12)
        header_frame.pack(fill="x", padx=5, pady=5)

        # Header labels with fixed widths for alignment
        header_label = ctk.CTkLabel(header_frame, text="Learning Area", font=("Arial Bold", 10), text_color="#ffffff", width=subject_width, anchor="center")
        header_label.pack(side="left", padx=2)

        for exam_col in exam_cols:
            header_label = ctk.CTkLabel(header_frame, text=exam_col['name'][:8], font=("Arial Bold", 10), text_color="#ffffff", width=exam_width, anchor="center")
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

            normalized_subject = subject.replace('-', ' ').replace('/', ' ').title()
            subject_key = subject_keys.get(normalized_subject, subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))

            # Subject name
            subject_label = ctk.CTkLabel(row_frame, text=subject[:18], font=("Arial", 9), width=subject_width, anchor="center", text_color="#000000")
            subject_label.pack(side="left", padx=2)

            # Previous exam scores
            for exam_col in exam_cols:
                if not exam_col['is_current']:
                    exam_marks = exam_col['marks']
                    score = ""
                    if isinstance(exam_marks, dict):
                        subject_key_map = {
                            'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                            'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                        }
                        subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                        mapped_key = subject_key_map.get(subject_upper, subject_upper)
                        score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                    score_label = ctk.CTkLabel(row_frame, text=str(score), font=("Arial", 9), width=exam_width, anchor="center", text_color="#000000")
                    score_label.pack(side="left", padx=2)

            # Current exam score, rating, points
            current_score = current_marks.get(f'{subject_key}_s', '')
            current_rating = current_marks.get(f'{subject_key}_r', '')
            current_points = current_marks.get(f'{subject_key}_p', '')

            score_label = ctk.CTkLabel(row_frame, text=str(current_score), font=("Arial", 9), width=exam_width, anchor="center", text_color="#000000")
            score_label.pack(side="left", padx=2)

            rating_label = ctk.CTkLabel(row_frame, text=str(current_rating), font=("Arial", 9), width=rate_width, anchor="center", text_color="#000000")
            rating_label.pack(side="left", padx=2)

            if is_junior:
                points_label = ctk.CTkLabel(row_frame, text=str(current_points), font=("Arial", 9), width=points_width, anchor="center", text_color="#000000")
                points_label.pack(side="left", padx=2)

            # Improvement
            improvement = "-"
            if previous_exams and len(previous_exams) > 0:
                latest_prev_exam = previous_exams[0]
                latest_prev_marks = latest_prev_exam.get('marks', {})
                if isinstance(latest_prev_marks, dict):
                    subject_key_map = {
                        'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                        'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                    }
                    subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                    mapped_key = subject_key_map.get(subject_upper, subject_upper)
                    prev_score = latest_prev_marks.get(mapped_key, {}).get('score', '') if isinstance(latest_prev_marks.get(mapped_key, {}), dict) else ''
                    try:
                        if current_score and prev_score:
                            diff = int(current_score) - int(prev_score)
                            improvement = f"+{diff}" if diff > 0 else str(diff)
                    except:
                        pass

            improve_label = ctk.CTkLabel(row_frame, text=improvement, font=("Arial", 9), width=improve_width, anchor="center", text_color="#000000")
            improve_label.pack(side="left", padx=2)

            # Teacher name
            teacher_map = self.get_teacher_assignments(grade)
            teacher_name = teacher_map.get(subject, 'N/A')
            teacher_label = ctk.CTkLabel(row_frame, text=teacher_name[:15], font=("Arial", 9), width=teacher_width, anchor="center", text_color="#000000")
            teacher_label.pack(side="left", padx=2)

            # Teacher comment
            comment = self.rating_to_comment(current_rating) if current_rating else 'No comment'
            comment_label = ctk.CTkLabel(row_frame, text=comment, font=("Arial", 8), width=comment_width, anchor="w", text_color="#000000", wraplength=comment_width - 10)
            comment_label.pack(side="left", padx=2)

        # Summary row with portal gradient styling
        summary_frame = ctk.CTkFrame(table_frame, fg_color="#f5f7fa", height=30, corner_radius=8)
        summary_frame.pack(fill="x", padx=5, pady=(10, 5))

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

        total_label_widget = ctk.CTkLabel(summary_frame, text=total_label, font=("Arial Bold", 10), width=subject_width, anchor="center", text_color="#000000")
        total_label_widget.pack(side="left", padx=2)

        # Previous exam totals
        for exam_col in exam_cols:
            if not exam_col['is_current']:
                total_points = exam_col.get('total_points', '')
                if total_points and total_points not in ['', '-']:
                    # Check if total_points is a rating string (ME1, EE2, etc.) instead of numeric
                    rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
                    if str(total_points).strip() in rating_patterns:
                        # It's a rating, calculate from marks instead
                        exam_marks = exam_col.get('marks', {})
                        calc_total = 0
                        if isinstance(exam_marks, dict):
                            for subject in subjects:
                                # Use the same subject key mapping as in the data retrieval
                                subject_key_map = {
                                    'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                    'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                }
                                subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                if is_junior:
                                    points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                    if points and points not in ['', '-']:
                                        try:
                                            calc_total += float(points)
                                        except:
                                            pass
                                else:
                                    score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                    if score and score not in ['', '-']:
                                        try:
                                            calc_total += float(score)
                                        except:
                                            pass
                        total_label_widget = ctk.CTkLabel(summary_frame, text=str(int(calc_total)) if calc_total > 0 else "-", font=("Arial Bold", 10), width=exam_width, anchor="center", text_color="#000000")
                    else:
                        try:
                            total_label_widget = ctk.CTkLabel(summary_frame, text=str(int(float(total_points))), font=("Arial Bold", 10), width=exam_width, anchor="center", text_color="#000000")
                        except (ValueError, TypeError):
                            # Fallback: calculate from marks if total_points is invalid
                            exam_marks = exam_col.get('marks', {})
                            calc_total = 0
                            if isinstance(exam_marks, dict):
                                for subject in subjects:
                                    # Use the same subject key mapping as in the data retrieval
                                    subject_key_map = {
                                        'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                        'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                    }
                                    subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                    mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                    if is_junior:
                                        points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                        if points and points not in ['', '-']:
                                            try:
                                                calc_total += float(points)
                                            except:
                                                pass
                                    else:
                                        score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                        if score and score not in ['', '-']:
                                            try:
                                                calc_total += float(score)
                                            except:
                                                pass
                            total_label_widget = ctk.CTkLabel(summary_frame, text=str(int(calc_total)) if calc_total > 0 else "-", font=("Arial Bold", 10), width=exam_width, anchor="center", text_color="#000000")
                else:
                    # Fallback: calculate from marks if total_points is missing
                    exam_marks = exam_col.get('marks', {})
                    calc_total = 0
                    if isinstance(exam_marks, dict):
                        for subject in subjects:
                            # Use the same subject key mapping as in the data retrieval
                            subject_key_map = {
                                'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                            }
                            subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                            mapped_key = subject_key_map.get(subject_upper, subject_upper)
                            if is_junior:
                                points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                if points and points not in ['', '-']:
                                    try:
                                        calc_total += float(points)
                                    except:
                                        pass
                            else:
                                score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                if score and score not in ['', '-']:
                                    try:
                                        calc_total += float(score)
                                    except:
                                        pass
                    total_label_widget = ctk.CTkLabel(summary_frame, text=str(int(calc_total)) if calc_total > 0 else "-", font=("Arial Bold", 10), width=exam_width, anchor="center", text_color="#000000")
                total_label_widget.pack(side="left", padx=2)

        # Current total
        current_total_label = ctk.CTkLabel(summary_frame, text=str(int(current_total)) if current_total > 0 else "-", font=("Arial Bold", 10), width=exam_width, anchor="center", text_color="#000000")
        current_total_label.pack(side="left", padx=2)

        # Average level
        avg_label = ctk.CTkLabel(summary_frame, text=avg_level, font=("Arial Bold", 10), width=rate_width, anchor="center", text_color="#000000")
        avg_label.pack(side="left", padx=2)

        if is_junior:
            points_label = ctk.CTkLabel(summary_frame, text=str(int(current_total)) if current_total > 0 else "-", font=("Arial Bold", 10), width=points_width, anchor="center", text_color="#000000")
            points_label.pack(side="left", padx=2)

        # Fill remaining cells with dashes
        for _ in range(3):  # Improve, Teacher, Comments
            dash_label = ctk.CTkLabel(summary_frame, text="-", font=("Arial", 10), width=improve_width if _ == 0 else (teacher_width if _ == 1 else comment_width), anchor="center", text_color="#000000")
            dash_label.pack(side="left", padx=2)

        # Performance Summary section (matching portal)
        summary_section = ctk.CTkFrame(container, fg_color="#667eea", corner_radius=12)
        summary_section.pack(fill="x", padx=20, pady=10)

        summary_title = ctk.CTkLabel(summary_section, text="Summary for Parents: Understanding Your Child's Progress",
                                     font=("Arial Bold", 16), text_color="#ffffff")
        summary_title.pack(pady=(15, 10), padx=15)

        summary_text = ctk.CTkLabel(summary_section,
                                    text="We use a Competency-Based Curriculum (CBC) assessment scale to track your child's growth. "
                                        "This scale measures how well your child has mastered specific skills throughout the term.",
                                    font=("Arial", 12), text_color="#ffffff", wraplength=800)
        summary_text.pack(pady=(0, 10), padx=15)

        # Rating explanations
        rating_frame = ctk.CTkFrame(summary_section, fg_color="transparent")
        rating_frame.pack(fill="x", padx=15, pady=(0, 15))

        ratings = [
            ("EE1 & EE2 (Exceeding Expectations):", "Your child has demonstrated a deep and outstanding understanding of the material."),
            ("ME1 & ME2 (Meeting Expectations):", "Your child is making good progress and is successfully grasping the core concepts."),
            ("AE1 & AE2 (Approaching Expectations):", "Your child is working toward meeting the expected outcomes."),
            ("BE1 & BE2 (Below Expectations):", "Your child is in the early stages of learning these concepts.")
        ]

        for rating_title, rating_desc in ratings:
            rating_row = ctk.CTkFrame(rating_frame, fg_color="transparent")
            rating_row.pack(fill="x", pady=2)

            title_label = ctk.CTkLabel(rating_row, text=rating_title, font=("Arial Bold", 11), text_color="#ffffff", anchor="w")
            title_label.pack(fill="x")

            desc_label = ctk.CTkLabel(rating_row, text=rating_desc, font=("Arial", 10), text_color="#ffffff", anchor="w")
            desc_label.pack(fill="x", padx=(0, 0))

        # Performance History section
        history_section = ctk.CTkFrame(container, fg_color="transparent")
        history_section.pack(fill="x", padx=20, pady=10)

        history_title = ctk.CTkLabel(history_section, text="Performance History",
                                     font=("Arial Bold", 16), text_color="#667eea")
        history_title.pack(pady=(0, 10), anchor="w")

        # Simple performance chart (bar chart using frames)
        chart_frame = ctk.CTkFrame(history_section, fg_color="white", border_width=2, border_color="#667eea", corner_radius=12)
        chart_frame.pack(fill="x", pady=(0, 10))

        # Prepare performance data
        performance_data = []
        for exam_col in exam_cols:
            exam_name = exam_col['name'][:8]
            exam_marks = exam_col['marks']
            total = 0

            # Use pre-calculated total_points if available (more accurate)
            if not exam_col['is_current']:
                total_points = exam_col.get('total_points', '')
                if total_points and total_points not in ['', '-']:
                    # Check if total_points is a rating string (ME1, EE2, etc.) instead of numeric
                    rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
                    if str(total_points).strip() in rating_patterns:
                        # It's a rating, calculate from marks instead
                        if isinstance(exam_marks, dict):
                            for subject in subjects:
                                # Use the same subject key mapping as in the data retrieval
                                subject_key_map = {
                                    'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                    'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                }
                                subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                if is_junior:
                                    points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                    if points and points not in ['', '-']:
                                        try:
                                            total += float(points)
                                        except:
                                            pass
                                else:
                                    score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                    if score and score not in ['', '-']:
                                        try:
                                            total += float(score)
                                        except:
                                            pass
                    else:
                        try:
                            total = float(total_points)
                        except (ValueError, TypeError):
                            total = 0
                            # Fallback to calculating from marks if total_points is invalid
                            if isinstance(exam_marks, dict):
                                for subject in subjects:
                                    # Use the same subject key mapping as in the data retrieval
                                    subject_key_map = {
                                        'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                        'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                    }
                                    subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                    mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                    if is_junior:
                                        points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                        if points and points not in ['', '-']:
                                            try:
                                                total += float(points)
                                            except:
                                                pass
                                    else:
                                        score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                        if score and score not in ['', '-']:
                                            try:
                                                total += float(score)
                                            except:
                                                pass
            else:
                # For current exam, calculate from marks
                if isinstance(exam_marks, dict):
                    for subject in subjects:
                        subject_key = subject_keys.get(subject.replace('-', ' ').replace('/', ' ').title(), subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                        if is_junior:
                            points = exam_marks.get(f'{subject_key}_p', '')
                            if points and points not in ['', '-']:
                                try:
                                    total += float(points)
                                except:
                                    pass
                        else:
                            score = exam_marks.get(f'{subject_key}_s', '')
                            if score and score not in ['', '-']:
                                try:
                                    total += float(score)
                                except:
                                    pass

            performance_data.append({'name': exam_name, 'total': total})

        if performance_data:
            max_total = max(d['total'] for d in performance_data) if performance_data else 1
            if max_total == 0:
                max_total = 1

            chart_content = ctk.CTkFrame(chart_frame, fg_color="transparent")
            chart_content.pack(fill="x", padx=15, pady=15)

            # Draw bars
            bar_width = 100
            bar_spacing = 20
            total_chart_width = len(performance_data) * (bar_width + bar_spacing)

            bar_container = ctk.CTkFrame(chart_content, fg_color="transparent")
            bar_container.pack(fill="x")

            for i, data in enumerate(performance_data):
                bar_height = (data['total'] / max_total) * 150 if data['total'] > 0 else 0

                # Bar color based on performance
                if data['total'] / max_total >= 0.8:
                    bar_color = "#22c55e"  # Green
                elif data['total'] / max_total >= 0.5:
                    bar_color = "#eab308"  # Yellow
                else:
                    bar_color = "#ef4444"  # Red

                bar_frame = ctk.CTkFrame(bar_container, fg_color=bar_color, width=bar_width, corner_radius=5)
                bar_frame.pack(side="left", padx=bar_spacing//2)
                bar_frame.pack_propagate(False)  # Prevent shrinking

                # Bar height
                if bar_height > 0:
                    height_frame = ctk.CTkFrame(bar_frame, fg_color=bar_color)
                    height_frame.pack(side="bottom", fill="x")
                    height_frame.pack_propagate(False)
                    height_frame.configure(height=int(bar_height))

                # Exam name
                exam_label = ctk.CTkLabel(bar_frame, text=data['name'], font=("Arial", 9), text_color="#000000")
                exam_label.pack(side="bottom", pady=5)

                # Total score
                if data['total'] > 0:
                    total_label = ctk.CTkLabel(bar_frame, text=str(int(data['total'])), font=("Arial Bold", 10), text_color="#000000")
                    total_label.pack(side="bottom", pady=2)

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
    
    def print_report_pdf(self, container, student, file_path=None, opening_date=None, closing_date=None):
        import os
        from tkinter import filedialog, simpledialog, messagebox

        # Check if student data is valid
        if not student:
            # Only show error message for individual printing (when file_path is not provided)
            if not file_path:
                messagebox.showerror("Error", "No student data provided")
            return

        # Dates are no longer required - will be integrated later
        opening_date = None
        closing_date = None

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
        print(f"DEBUG PDF: Student photo field: {student.get('photo', 'NOT FOUND') if student else 'NO STUDENT'}")
        
        # Get class teacher (first teacher linked to this class)
        class_teacher = self.get_class_teacher(grade) if grade else ""

        # Ask for save location only if file_path is not provided
        if not file_path:
            print(f"DEBUG PDF: Opening file dialog...")
            # For executable, default to user's Documents folder
            if getattr(sys, 'frozen', False):
                initial_dir = os.path.join(os.path.expanduser("~"), "Documents")
                if not os.path.exists(initial_dir):
                    initial_dir = os.path.expanduser("~")
            else:
                initial_dir = os.getcwd()

            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=f"{student_name.replace(' ', '_')}_{exam_title.replace(' ', '_')}.pdf",
                initialdir=initial_dir,
            )
            print(f"DEBUG PDF: File dialog returned: {file_path}")
        if not file_path:
            print(f"DEBUG PDF: No file path selected, aborting")
            return

        # Check if the directory is writable
        try:
            import os
            file_dir = os.path.dirname(file_path) or os.getcwd()
            if not os.path.exists(file_dir):
                os.makedirs(file_dir, exist_ok=True)
            test_file = os.path.join(file_dir, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print(f"DEBUG PDF: Directory is writable: {file_dir}")
        except Exception as e:
            print(f"ERROR PDF: Directory not writable: {e}")
            if not file_path:
                messagebox.showerror("Error", f"Cannot write to selected location: {e}")
            return

        # Convert to absolute path to avoid relative path issues
        file_path = os.path.abspath(file_path)
        print(f"DEBUG PDF: Absolute file path: {file_path}")

        try:
            print(f"DEBUG PDF: Creating FPDF object...")
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            print(f"DEBUG PDF: Adding page...")
            pdf.add_page()
            print(f"DEBUG PDF: Page added successfully")

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
            print(f"DEBUG PDF: Student photo path: {student_photo}")
            if student_photo and os.path.exists(student_photo):
                try:
                    pdf.image(student_photo, 250, 8, 25)
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
                    comment = self.rating_to_comment(rating) if rating else 'No comment'
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
                        # Truncate exam name to fit in column (approx 8 chars at 7pt font)
                        exam_name = exam_col['name'][:8] if len(exam_col['name']) > 8 else exam_col['name']
                        pdf.cell(exam_col_width, header_height, txt=exam_name, border=1, ln=0, align="C", fill=True)
                        x_pos += exam_col_width
                
                # Current exam column
                pdf.set_xy(x_pos, current_y)
                current_exam_name = exam_title[:8] if len(exam_title) > 8 else exam_title
                pdf.cell(exam_col_width, header_height, txt=current_exam_name, border=1, ln=0, align="C", fill=True)
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
                    comment = self.rating_to_comment(current_rating) if current_rating else 'No comment'
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
                            # Check if total_points is a rating string (ME1, EE2, etc.) instead of numeric
                            rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
                            if str(total_points).strip() in rating_patterns:
                                # It's a rating, calculate from marks instead
                                exam_marks = exam_col.get('marks', {})
                                calc_total = 0
                                if isinstance(exam_marks, dict):
                                    for subject in subjects:
                                        # Use the same subject key mapping as in the data retrieval
                                        subject_key_map = {
                                            'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                            'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                        }
                                        subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                        mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                        if is_junior:
                                            points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                            if points and points not in ['', '-']:
                                                try:
                                                    calc_total += float(points)
                                                except:
                                                    pass
                                        else:
                                            score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                            if score and score not in ['', '-']:
                                                try:
                                                    calc_total += float(score)
                                                except:
                                                    pass
                                pdf.cell(exam_col_width, 6, txt=str(int(calc_total)) if calc_total > 0 else "-", border=1, ln=0, align="C", fill=True)
                            else:
                                try:
                                    pdf.cell(exam_col_width, 6, txt=str(int(float(total_points))), border=1, ln=0, align="C", fill=True)
                                except (ValueError, TypeError):
                                    # Fallback: calculate from marks if total_points is invalid
                                    exam_marks = exam_col.get('marks', {})
                                    calc_total = 0
                                    if isinstance(exam_marks, dict):
                                        for subject in subjects:
                                            # Use the same subject key mapping as in the data retrieval
                                            subject_key_map = {
                                                'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                                'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                            }
                                            subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                            mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                            if is_junior:
                                                points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                                if points and points not in ['', '-']:
                                                    try:
                                                        calc_total += float(points)
                                                    except:
                                                        pass
                                            else:
                                                score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                                if score and score not in ['', '-']:
                                                    try:
                                                        calc_total += float(score)
                                                    except:
                                                        pass
                                    pdf.cell(exam_col_width, 6, txt=str(int(calc_total)) if calc_total > 0 else "-", border=1, ln=0, align="C", fill=True)
                        else:
                            # Fallback: calculate from marks if total_points is missing
                            exam_marks = exam_col.get('marks', {})
                            calc_total = 0
                            if isinstance(exam_marks, dict):
                                for subject in subjects:
                                    # Use the same subject key mapping as in the data retrieval
                                    subject_key_map = {
                                        'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                        'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                    }
                                    subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                    mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                    if is_junior:
                                        points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                        if points and points not in ['', '-']:
                                            try:
                                                calc_total += float(points)
                                            except:
                                                pass
                                    else:
                                        score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                        if score and score not in ['', '-']:
                                            try:
                                                calc_total += float(score)
                                            except:
                                                pass
                            pdf.cell(exam_col_width, 6, txt=str(int(calc_total)) if calc_total > 0 else "-", border=1, ln=0, align="C", fill=True)
                
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
                        exam_name = exam_col['name'][:8]
                        exam_marks = exam_col['marks']
                        total = 0

                        # Use pre-calculated total_points if available (more accurate)
                        if not exam_col['is_current']:
                            total_points = exam_col.get('total_points', '')
                            if total_points and total_points not in ['', '-']:
                                # Check if total_points is a rating string (ME1, EE2, etc.) instead of numeric
                                rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
                                if str(total_points).strip() in rating_patterns:
                                    # It's a rating, calculate from marks instead
                                    if isinstance(exam_marks, dict):
                                        for subject in subjects:
                                            # Use the same subject key mapping as in the data retrieval
                                            subject_key_map = {
                                                'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                                'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                            }
                                            subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                            mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                            if is_junior:
                                                # For junior, check for points
                                                points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                                if points and points not in ['', '-']:
                                                    try:
                                                        total += float(points)
                                                    except:
                                                        pass
                                            else:
                                                # For other grades, check for score
                                                score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                                if score and score not in ['', '-']:
                                                    try:
                                                        total += float(score)
                                                    except:
                                                        pass
                                else:
                                    try:
                                        total = float(total_points)
                                    except (ValueError, TypeError):
                                        total = 0
                                        # Fallback to calculating from marks if total_points is invalid
                                        if isinstance(exam_marks, dict):
                                            for subject in subjects:
                                                # Use the same subject key mapping as in the data retrieval
                                                subject_key_map = {
                                                    'INT_SCIE': 'INTSCIE', 'PRE_TECH': 'PRE-TECH', 'C_A': 'C/A',
                                                    'PRETECH': 'PRE-TECH', 'CA': 'C/A'
                                                }
                                                subject_upper = subject.upper().replace(' ', '_').replace('-', '_').replace('/', '_')
                                                mapped_key = subject_key_map.get(subject_upper, subject_upper)
                                                if is_junior:
                                                    # For junior, check for points
                                                    points = exam_marks.get(mapped_key, {}).get('points', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                                    if points and points not in ['', '-']:
                                                        try:
                                                            total += float(points)
                                                        except:
                                                            pass
                                                else:
                                                    # For other grades, check for score
                                                    score = exam_marks.get(mapped_key, {}).get('score', '') if isinstance(exam_marks.get(mapped_key, {}), dict) else ''
                                                    if score and score not in ['', '-']:
                                                        try:
                                                            total += float(score)
                                                        except:
                                                            pass
                        else:
                            # For current exam, calculate from marks
                            if isinstance(exam_marks, dict):
                                for subject in subjects:
                                    subject_key = subject_keys.get(subject.replace('-', ' ').replace('/', ' ').title(), subject.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
                                    if is_junior:
                                        points = current_marks.get(f'{subject_key}_p', '')
                                        if points and points not in ['', '-']:
                                            try:
                                                total += float(points)
                                            except:
                                                pass
                                    else:
                                        score = current_marks.get(f'{subject_key}_s', '')
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
                            pdf.set_font("Helvetica", "", 6)
                            pdf.cell(bar_width - bar_spacing, 5, txt=data['name'], border=0, ln=0, align="C")
                            
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
                        rating_result = get_grade_7_8_rating(avg_score)
                    else:
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
                    pdf.image(signature_path, x=10, y=pdf.get_y(), h=20)
                    pdf.ln(25)
                except:
                    pdf.cell(0, 5, txt="_________________", border=0, ln=1)
                    pdf.ln(3)
            else:
                pdf.cell(0, 5, txt="_________________", border=0, ln=1)
                pdf.ln(3)
            
            # Add opening and closing dates to the right of signature if provided
            if opening_date and closing_date:
                pdf.set_xy(150, pdf.get_y() - 28)  # Position to the right of signature
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 5, txt=f"Opening Date: {opening_date}", border=0, ln=1, align="L")
                pdf.set_xy(150, pdf.get_y() + 5)
                pdf.cell(0, 5, txt=f"Closing Date: {closing_date}", border=0, ln=1, align="L")

            print(f"DEBUG PDF: Attempting to write PDF to: {file_path}")
            pdf.output(file_path)
            print(f"DEBUG PDF: PDF written successfully")

            # Verify file was actually created
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"DEBUG PDF: File verified - Size: {file_size} bytes")
                if file_size < 1000:
                    print(f"WARNING PDF: File size suspiciously small ({file_size} bytes)")
            else:
                print(f"ERROR PDF: File was not created at {file_path}")

            # Only show success message for individual printing (when file_path is not provided)
            if not file_path:
                messagebox.showinfo("Success", f"PDF generated successfully!\nLocation: {file_path}")

        except Exception as e:
            print(f"ERROR PDF: PDF Generation Failed: {e}")
            import traceback
            traceback.print_exc()
            # Only show error message for individual printing (when file_path is not provided)
            if not file_path:
                messagebox.showerror("Error", f"PDF Generation Failed: {e}")
            else:
                # For batch printing, just print to console
                print(f"PDF Generation Failed: {e}")
    
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
        
        messagebox.showinfo("Print", f"Would print {len(students)} reports for {self.current_class}.")
        
        students = self.get_students_in_class(self.current_class)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return
        
        print(f"=== Found {len(students)} students in {self.current_class} ===")

        # Dates are no longer required - will be integrated later
        opening_date = None
        closing_date = None

        # Ask for save directory
        from tkinter import filedialog
        # For executable, default to user's Documents folder
        if getattr(sys, 'frozen', False):
            initial_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.exists(initial_dir):
                initial_dir = os.path.expanduser("~")
        else:
            initial_dir = os.getcwd()

        save_dir = filedialog.askdirectory(title="Select directory to save PDFs", initialdir=initial_dir)
        if not save_dir:
            return

        # Convert to absolute path
        save_dir = os.path.abspath(save_dir)
        print(f"DEBUG PDF: Batch save directory: {save_dir}")
        
        # Print reports for all students in the class
        success_count = 0
        for student in students:
            # Generate report data for this student
            report_data = self.generate_report_data(student)
            if not report_data:
                continue
            
            # Merge student basic info with report data
            report_data['name'] = student.get('name', '')
            report_data['adm_no'] = student.get('adm_no', '')
            report_data['grade'] = student.get('grade', '')
            report_data['stream'] = student.get('stream', 'none')
            report_data['photo'] = student.get('photo', '')
            
            # Create file path
            file_path = os.path.join(save_dir, f"{student['name'].replace(' ', '_')}_report.pdf")
            
            # Print the report
            try:
                self.print_report_pdf(None, report_data, file_path=file_path, 
                                    opening_date=opening_date, closing_date=closing_date)
                success_count += 1
            except Exception as e:
                print(f"Error printing report for {student['name']}: {e}")
        
        messagebox.showinfo("Success", f"Printed {success_count}/{len(students)} reports for {self.current_class}.")
    
    def print_all_reports(self):
        classes = self.get_available_classes()
        if not classes:
            messagebox.showinfo("Info", "No classes found.")
            return
        
        total_students = sum(len(self.get_students_in_class(cls)) for cls in classes)
        messagebox.showinfo("Print", f"Would print {total_students} reports for all classes.")
        
        print(f"=== Found {len(classes)} classes ===")

        # Dates are no longer required - will be integrated later
        opening_date = None
        closing_date = None

        # Ask for save directory
        from tkinter import filedialog
        # For executable, default to user's Documents folder
        if getattr(sys, 'frozen', False):
            initial_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.exists(initial_dir):
                initial_dir = os.path.expanduser("~")
        else:
            initial_dir = os.getcwd()

        save_dir = filedialog.askdirectory(title="Select directory to save PDFs", initialdir=initial_dir)
        if not save_dir:
            return

        # Convert to absolute path
        save_dir = os.path.abspath(save_dir)
        print(f"DEBUG PDF: Batch save directory: {save_dir}")
        
        # Print reports for all students in all classes
        total_success = 0
        total_students = 0
        
        for class_name in classes:
            students = self.get_students_in_class(class_name)
            total_students += len(students)
            
            for student in students:
                # Generate report data for this student
                report_data = self.generate_report_data(student)
                if not report_data:
                    continue
                
                # Merge student basic info with report data
                report_data['name'] = student.get('name', '')
                report_data['adm_no'] = student.get('adm_no', '')
                report_data['grade'] = student.get('grade', '')
                report_data['stream'] = student.get('stream', 'none')
                report_data['photo'] = student.get('photo', '')
                
                # Create file path
                file_path = os.path.join(save_dir, f"{student['name'].replace(' ', '_')}_{class_name}_report.pdf")
                
                # Print the report
                try:
                    self.print_report_pdf(None, report_data, file_path=file_path, 
                                        opening_date=opening_date, closing_date=closing_date)
                    total_success += 1
                except Exception as e:
                    print(f"Error printing report for {student['name']}: {e}")
        
        messagebox.showinfo("Success", f"Printed {total_success}/{total_students} reports for all classes.")
    
    def generate_report_data(self, student):
        print(f"DEBUG: generate_report_data called for {student.get('name', 'Unknown')} in {student['grade']}")
        print(f"DEBUG: generate_report_data - Student keys: {list(student.keys())}")
        print(f"DEBUG: generate_report_data - Photo field: {student.get('photo', 'NOT FOUND')}")
        
        current_marks = self.get_student_current_marks(student['adm_no'], student['grade'])
        if not current_marks:
            print(f"DEBUG: No current marks found for {student.get('name', 'Unknown')} in {student['grade']}")
            return None
        
        print(f"DEBUG: Current marks found, proceeding with report generation")
        exam_title = self.school_config.get("current_exam_title", "PERFORMANCE REPORT")
        
        previous_exams_data = []
        previous_exams_list = self.db.get_previous_exams(student['grade'])
        print(f"DEBUG: Found {len(previous_exams_list)} previous exams in database for grade {student['grade']}")
        
        subject_names = self.get_subjects_for_grade(student['grade'])
        print(f"DEBUG: Subject names from config: {subject_names}")
        
        rating_patterns = ['BE1', 'BE2', 'AE1', 'AE2', 'ME1', 'ME2', 'EE1', 'EE2']
        grade_lower = student['grade'].lower()
        is_junior = grade_lower in ["grade 7", "grade 8", "grade 9"]
        
        for exam_name, exam_date in previous_exams_list:
            marks_data, summary_data = self.db.get_previous_exam_data(exam_name, student['grade'])
            print(f"DEBUG: Got marks_data for {exam_name}: {marks_data is not None}")
            
            if marks_data:
                try:
                    import json
                    if isinstance(marks_data, str):
                        marks_data = json.loads(marks_data)
                    
                    if isinstance(marks_data, list):
                        print(f"DEBUG: Marks data is a list with {len(marks_data)} students")
                        for student_record in marks_data:
                            if student_record and student_record[0].strip().lower() == student['name'].strip().lower():
                                marks_dict = {}
                                marks_list = student_record[1:]
                                
                                if is_junior:
                                    print(f"DEBUG: Using junior format (score, rating, points)")
                                    for i, subject_name in enumerate(subject_names):
                                        if i * 3 + 2 < len(marks_list):
                                            marks_dict[subject_name.upper().replace(' ', '')] = {
                                                'score': marks_list[i * 3],
                                                'rating': marks_list[i * 3 + 1],
                                                'points': marks_list[i * 3 + 2]
                                            }
                                else:
                                    print(f"DEBUG: Using standard format (score, rating)")
                                    for i, subject_name in enumerate(subject_names):
                                        if i * 2 + 1 < len(marks_list):
                                            marks_dict[subject_name.upper().replace(' ', '')] = {
                                                'score': marks_list[i * 2],
                                                'rating': marks_list[i * 2 + 1]
                                            }
                                
                                total_points, avg_level = None, 'BE2'
                                for offset in range(-3, 0):
                                    try:
                                        pt = int(marks_list[offset])
                                        if 0 < pt < 1000:
                                            total_points = pt
                                            break
                                    except (ValueError, TypeError):
                                        continue
                                        
                                if total_points is None and len(marks_list) >= 2:
                                    try:
                                        total_points = int(marks_list[-2])
                                    except:
                                        total_points = 0
                                        
                                for val in marks_list[-3:]:
                                    if str(val).strip() in rating_patterns:
                                        avg_level = str(val).strip()
                                        break

                                has_data = any(m.get('score', '') for m in marks_dict.values() if isinstance(m, dict))
                                if has_data:
                                    previous_exams_data.append({
                                        'exam_name': exam_name,
                                        'exam_date': exam_date,
                                        'marks': marks_dict,
                                        'total_points': total_points,
                                        'average_level': avg_level
                                    })
                                    print(f"DEBUG: Added previous exam {exam_name}, total={total_points}, avg={avg_level}")
                                break
                                
                    elif isinstance(marks_data, dict):
                        student_key = "".join(student['name'].split()).lower()
                        if student_key in marks_data:
                            student_marks = marks_data[student_key]
                            total_points = student_marks.get('total_points') if isinstance(student_marks, dict) else None
                            avg_level = student_marks.get('average_level') if isinstance(student_marks, dict) else 'BE2'
                            
                            previous_exams_data.append({
                                'exam_name': exam_name,
                                'exam_date': exam_date,
                                'marks': student_marks,
                                'total_points': total_points,
                                'average_level': avg_level if avg_level in rating_patterns else 'BE2'
                            })
                except Exception as e:
                    print(f"DEBUG: Error parsing marks data: {e}")
                    
        print(f"DEBUG: Total previous_exams_data: {len(previous_exams_data)}")
        
        # Base64 photo encoding
        import base64
        photo_path = student.get('photo', '')
        encoded_photo = ''
        if photo_path and os.path.exists(photo_path):
            try:
                with open(photo_path, "rb") as image_file:
                    file_bytes = image_file.read()
                    encoded_string = base64.b64encode(file_bytes).decode('utf-8')
                    ext = photo_path.split('.')[-1].lower()
                    mime_type = 'image/png' if ext == 'png' else 'image/jpeg'
                    encoded_photo = f"data:{mime_type};base64,{encoded_string}"
            except Exception as e:
                print(f"DEBUG: Error encoding student photo to base64: {e}")
                
        return {
            'student_name': student['name'],
            'adm_no': student['adm_no'],
            'stream': student.get('stream', 'none'),
            'grade': student['grade'],
            'school_name': self.school_config.get('school_name', ''),
            'current_marks': current_marks,
            'class_teacher': self.get_class_teacher(student['grade']),
            'exam_title': exam_title,
            'previous_exams': previous_exams_data,
            'generated_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'photo': encoded_photo,
            'student_photo': encoded_photo
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
