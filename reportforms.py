import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
import os
import json
from database import FreemanDB
from cloud_service import CloudService, ask_cloud_credentials
import datetime


class ReportFormsView(ctk.CTkToplevel):
    def __init__(self, parent_window, db):
        super().__init__(parent_window)
        
        self.parent_window = parent_window
        self.db = db
        self.current_class = None
        self.current_student = None
        self.school_config = self.load_school_config()
        
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
            current_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(current_dir, 'school_config.json')
            if os.path.exists(json_path):
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
            self.db._cursor.execute('SELECT DISTINCT grade FROM students ORDER BY grade')
            classes = [row[0] for row in self.db._cursor.fetchall()]
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
            self.db._cursor.execute('SELECT adm_no, name, grade FROM students WHERE grade = ? ORDER BY name',
                                   (class_name,))
            students = [{'adm_no': row[0], 'name': row[1], 'grade': row[2]} 
                       for row in self.db._cursor.fetchall()]
            return students
        except Exception as e:
            print(f"Error getting students: {e}")
            return []
    
    def show_report_form(self, student):
        self.current_student = student
        self.clear_container()
        
        # Create report form window
        report_window = ctk.CTkToplevel(self)
        report_window.title(f"Report Form - {student['name']}")
        report_window.geometry("1000x800")
        
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
                                 command=lambda: self.print_report_pdf(report_container, student))
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
        header_frame = ctk.CTkFrame(container, height=220)
        header_frame.pack(fill="x", pady=(0, 20))

        # School logo (placeholder)
        logo_frame = ctk.CTkFrame(header_frame, width=200, height=200)
        logo_frame.pack(side="left", padx=20, pady=15)

        try:
            logo_path = self.school_config.get('logo', '')
            if logo_path and os.path.exists(logo_path):
                logo_photo = ctk.CTkImage(Image.open(logo_path), size=(180, 180))
                logo_label = ctk.CTkLabel(logo_frame, image=logo_photo, text="")
                logo_label.pack()
            else:
                logo_label = ctk.CTkLabel(logo_frame, text="SCHOOL\nLOGO",
                                         font=("Arial Bold", 14), text_color="gray")
                logo_label.pack(pady=40)
        except:
            logo_label = ctk.CTkLabel(logo_frame, text="SCHOOL\nLOGO",
                                     font=("Arial Bold", 14), text_color="gray")
            logo_label.pack(pady=40)

        # School info
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=15)

        school_name = self.school_config.get('school_name', 'School Name')
        school_name_label = ctk.CTkLabel(info_frame, text=school_name.upper(),
                                        font=("Arial Bold", 28))
        school_name_label.pack(pady=5)

        address = self.school_config.get('address', '')
        if address:
            addr_label = ctk.CTkLabel(info_frame, text=address,
                                     font=("Arial", 13))
            addr_label.pack(pady=2)

        contacts = self.school_config.get('contacts', '')
        if contacts:
            contact_label = ctk.CTkLabel(info_frame, text=f"Contact: {contacts}",
                                        font=("Arial Bold", 13), text_color="#e74c3c")
            contact_label.pack(pady=2)

        # Report title
        report_title = ctk.CTkLabel(info_frame, text="COMPETENCY BASED CURRICULUM (CBC) REPORT CARD",
                                    font=("Arial Bold", 16), text_color="#3498db")
        report_title.pack(pady=10)
    
    def create_student_info(self, container, student):
        info_frame = ctk.CTkFrame(container, fg_color="#f8f9fa")
        info_frame.pack(fill="x", pady=(0, 20))

        # Section title
        title_label = ctk.CTkLabel(info_frame, text="STUDENT INFORMATION",
                                   font=("Arial Bold", 16), text_color="#2c3e50")
        title_label.pack(pady=10)

        # Student details in a grid layout
        details_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        details_frame.pack(fill="x", padx=20, pady=10)

        details = [
            ("Student Name:", student['name']),
            ("Admission Number:", student['adm_no']),
            ("Class/Grade:", student['grade']),
        ]

        # Add class teacher
        class_teacher = self.get_class_teacher(student['grade'])
        if class_teacher:
            details.append(("Class Teacher:", class_teacher))

        # Create two columns
        for i, (label, value) in enumerate(details):
            row = i // 2
            col = i % 2

            row_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            row_frame.grid(row=row, column=col, sticky="w", padx=10, pady=5)

            lbl = ctk.CTkLabel(row_frame, text=label, font=("Arial Bold", 13), width=180, anchor="w", text_color="#2c3e50")
            lbl.pack(side="left", padx=5)

            val = ctk.CTkLabel(row_frame, text=value, font=("Arial", 13), text_color="#2c3e50")
            val.pack(side="left", padx=5)
    
    def get_class_teacher(self, class_name):
        try:
            # Get the first teacher from the teachers linked list for this class
            self.db._cursor.execute('SELECT teacher_name FROM teachers WHERE class_name = ? ORDER BY id ASC LIMIT 1',
                                   (class_name,))
            result = self.db._cursor.fetchone()
            return result[0] if result else ""
        except Exception as e:
            print(f"Error getting class teacher: {e}")
            return ""
    
    def create_current_marks_section(self, container, student):
        section_frame = ctk.CTkFrame(container, fg_color="#f8f9fa")
        section_frame.pack(fill="x", pady=(0, 20))

        # Section title
        title_label = ctk.CTkLabel(section_frame, text="CURRENT TERM PERFORMANCE",
                                   font=("Arial Bold", 18), text_color="#27ae60")
        title_label.pack(pady=10)

        # Get current marks
        current_marks = self.get_student_current_marks(student['adm_no'], student['grade'])

        if current_marks:
            # Create marks table
            self.create_marks_table(section_frame, current_marks, student['grade'])
        else:
            no_marks_label = ctk.CTkLabel(section_frame, text="No current marks available",
                                         font=("Arial", 14), text_color="gray")
            no_marks_label.pack(pady=20)
    
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
        }
        key = grade_mapping.get(grade)
        subjects = subjects_config.get(key, [])

        marks_dict = {}
        # marks_list format: [name, score1, rating1, score2, rating2, ..., total, average]
        # Skip the first element (name)
        idx = 1
        for subject in subjects:
            if idx + 1 < len(marks_list):
                marks_dict[f'{subject.lower()}_s'] = marks_list[idx]
                marks_dict[f'{subject.lower()}_r'] = marks_list[idx + 1]
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
            }
            
            table = table_mapping.get(grade)
            if not table:
                return None
            
            self.db._cursor.execute(f'SELECT * FROM {table} WHERE adm_no = ?', (adm_no,))
            columns = [desc[0] for desc in self.db._cursor.description]
            row = self.db._cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            
            return None
        except Exception as e:
            print(f"Error getting current marks: {e}")
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

        # Data rows with alternating colors
        for i, subject in enumerate(subjects):
            bg_color = "#ecf0f1" if i % 2 == 0 else "#ffffff"
            row_frame = ctk.CTkFrame(table_frame, fg_color=bg_color)
            row_frame.pack(fill="x", pady=0)

            # Subject name
            subj_label = ctk.CTkLabel(row_frame, text=subject, font=("Arial Bold", 12), width=180, anchor="w", text_color="#2c3e50")
            subj_label.pack(side="left", padx=5, pady=5)

            # Get score, rating, points for this subject
            score = marks.get(f'{subject.lower()}_s', '') or marks.get(f'{subject}_s', '')
            rating = marks.get(f'{subject.lower()}_r', '') or marks.get(f'{subject}_r', '')
            points = marks.get(f'{subject.lower()}_p', '') or marks.get(f'{subject}_p', '')

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
        avg = marks.get('average_level', '')

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
        }
        
        key = grade_mapping.get(grade)
        return subjects_config.get(key, [])
    
    def create_signature_section(self, container, student):
        signature_frame = ctk.CTkFrame(container, fg_color="#f8f9fa")
        signature_frame.pack(fill="x", pady=(0, 20))
        
        # Section title
        title_label = ctk.CTkLabel(signature_frame, text="SIGNATURES",
                                   font=("Arial Bold", 16), text_color="#2c3e50")
        title_label.pack(pady=10)
        
        # Signature container
        sig_container = ctk.CTkFrame(signature_frame, fg_color="transparent")
        sig_container.pack(fill="x", padx=20, pady=10)
        
        # Headteacher signature
        sig_frame = ctk.CTkFrame(sig_container, width=200, height=120)
        sig_frame.pack(side="right", padx=20, pady=10)
        
        try:
            signature_path = self.school_config.get('signatures', {}).get('headteacher', '')
            if signature_path and os.path.exists(signature_path):
                sig_img = Image.open(signature_path).resize((180, 80))
                sig_photo = ctk.CTkImage(sig_img)
                sig_label = ctk.CTkLabel(sig_frame, image=sig_photo, text="")
                sig_label.pack(pady=5)
                
                sig_name_label = ctk.CTkLabel(sig_frame, text="Headteacher",
                                             font=("Arial Bold", 12), text_color="#2c3e50")
                sig_name_label.pack(pady=2)
            else:
                sig_label = ctk.CTkLabel(sig_frame, text="HEADTEACHER\nSIGNATURE",
                                        font=("Arial Bold", 10), text_color="gray")
                sig_label.pack(pady=20)
        except:
            sig_label = ctk.CTkLabel(sig_frame, text="HEADTEACHER\nSIGNATURE",
                                    font=("Arial Bold", 10), text_color="gray")
            sig_label.pack(pady=20)
        
        # Date and class teacher info
        info_frame = ctk.CTkFrame(sig_container, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        
        # Get class teacher
        class_teacher = self.get_class_teacher(student['grade'])
        if class_teacher:
            teacher_label = ctk.CTkLabel(info_frame, text=f"Class Teacher: {class_teacher}",
                                        font=("Arial", 13), text_color="#2c3e50")
            teacher_label.pack(pady=5, anchor="w")
        
        # Date
        date_label = ctk.CTkLabel(info_frame, text=f"Date: {datetime.datetime.now().strftime('%d/%m/%Y')}",
                                 font=("Arial", 13), text_color="#2c3e50")
        date_label.pack(pady=5, anchor="w")
    
    def print_report_pdf(self, container, student):
        # Placeholder for PDF generation
        messagebox.showinfo("Print PDF", "PDF generation will be implemented with a PDF library like ReportLab.")
    
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
    
    def print_all_reports(self):
        classes = self.get_available_classes()
        if not classes:
            messagebox.showinfo("Info", "No classes found.")
            return
        
        total_students = sum(len(self.get_students_in_class(cls)) for cls in classes)
        messagebox.showinfo("Print", f"Would print {total_students} reports for all classes.")
    
    def generate_report_data(self, student):
        current_marks = self.get_student_current_marks(student['adm_no'], student['grade'])
        
        # Determine exam title based on grade
        grade = student['grade']
        grade_lower = grade.lower()
        if grade_lower in ["playgroup", "pp1", "pp2"]:
            exam_title = self.school_config.get("playgroup_exam_title", "TERM ASSESSMENT")
        elif grade_lower in ["grade 1", "grade 2", "grade 3", "grade 4", "grade 5", "grade 6"]:
            exam_title = self.school_config.get("primary_exam_title", "PRIMARY EXAM")
        elif grade_lower in ["grade 7", "grade 8", "grade 9"]:
            exam_title = self.school_config.get("jss_exam_title", "JSS ASSESSMENT")
        else:
            exam_title = "TERM ASSESSMENT"
        
        # Fetch previous exams for this student
        previous_exams_data = []
        previous_exams_list = self.db.get_previous_exams(student['grade'])
        print(f"DEBUG: Found {len(previous_exams_list)} previous exams in database for grade {student['grade']}")
        for exam_name, exam_date in previous_exams_list:
            print(f"DEBUG: Previous exam: {exam_name} at {exam_date}")
        
        for exam_name, exam_date in previous_exams_list[:2]:  # Get up to 2 previous exams
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
                        print(f"DEBUG: Marks data is a list with {len(marks_data)} students")
                        for student_record in marks_data:
                            if len(student_record) > 0:
                                record_name = student_record[0]
                                record_key = "".join(record_name.split()).lower()
                                if record_key == "".join(student['name'].split()).lower():
                                    # Found the student, extract their marks
                                    # Convert list to dict format similar to current_marks
                                    marks_dict = {}
                                    # Assuming format: [name, score1, rating1, score2, rating2, ...]
                                    # We need to know the subject names to map correctly
                                    # For now, store as raw list
                                    previous_exams_data.append({
                                        'exam_name': exam_name,
                                        'exam_date': exam_date,
                                        'marks': student_record[1:]  # Skip name, keep marks
                                    })
                                    print(f"DEBUG: Added previous exam {exam_name} with list marks")
                                    break
                    elif isinstance(marks_data, dict):
                        print(f"DEBUG: Marks dict keys: {list(marks_dict.keys())[:5]}")  # Show first 5 keys
                        # Find this student's marks
                        student_key = "".join(student['name'].split()).lower()
                        print(f"DEBUG: Looking for student key: {student_key} in marks_dict")
                        if student_key in marks_dict:
                            previous_exams_data.append({
                                'exam_name': exam_name,
                                'exam_date': exam_date,
                                'marks': marks_dict[student_key]
                            })
                            print(f"DEBUG: Added previous exam {exam_name} with dict marks")
                        else:
                            print(f"DEBUG: Student key not found in marks_dict")
                except Exception as e:
                    print(f"DEBUG: Error parsing marks data: {e}")
                    import traceback
                    traceback.print_exc()
                    pass
        
        print(f"DEBUG: Total previous_exams_data: {len(previous_exams_data)}")
        
        return {
            'student_name': student['name'],
            'adm_no': student['adm_no'],
            'grade': student['grade'],
            'school_name': self.school_config.get('school_name', ''),
            'current_marks': current_marks,
            'class_teacher': self.get_class_teacher(student['grade']),
            'exam_title': exam_title,
            'previous_exams': previous_exams_data,
            'generated_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
