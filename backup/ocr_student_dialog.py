import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
from ocr_service import OCRService
from database import FreemanDB

class OCRStudentDialog(ctk.CTkToplevel):
    """Dialog for OCR-based student registration"""
    
    def __init__(self, parent, callback=None, db=None):
        super().__init__(parent)
        
        self.parent = parent
        self.callback = callback
        self.ocr_service = OCRService()
        # Use the passed database instance if provided, otherwise create a new one
        self.db = db if db else FreemanDB()
        
        self.extracted_students = []
        self.image_path = None
        
        self.setup_window()
        self.create_widgets()
        
    def setup_window(self):
        """Setup window properties"""
        self.title("OCR Student Registration")
        self.geometry("900x700")
        
        # Center the window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (900 // 2)
        y = (screen_height // 2) - (700 // 2)
        self.geometry(f"900x700+{x}+{y}")
        
        self.resizable(True, True)
        
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Register Students from Image", 
            font=("Arial Bold", 20)
        )
        title_label.pack(pady=(0, 20))
        
        # Image upload section
        image_frame = ctk.CTkFrame(main_frame)
        image_frame.pack(fill="x", pady=(0, 20))
        
        # Upload button
        self.upload_btn = ctk.CTkButton(
            image_frame,
            text="📷 Select Image",
            command=self.select_image,
            width=200,
            height=40,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.upload_btn.pack(side="left", padx=(0, 10))
        
        # Process button
        self.process_btn = ctk.CTkButton(
            image_frame,
            text="🔍 Extract Students",
            command=self.process_image,
            width=200,
            height=40,
            fg_color="#27ae60",
            hover_color="#219150",
            state="disabled"
        )
        self.process_btn.pack(side="left", padx=(0, 10))
        
        # Image path label
        self.image_path_label = ctk.CTkLabel(
            image_frame,
            text="No image selected",
            font=("Arial", 11)
        )
        self.image_path_label.pack(side="left", padx=10)
        
        # Image preview
        self.image_preview_frame = ctk.CTkFrame(main_frame, height=200)
        self.image_preview_frame.pack(fill="x", pady=(0, 20))
        
        self.image_preview_label = ctk.CTkLabel(
            self.image_preview_frame,
            text="Image preview will appear here",
            font=("Arial", 12),
            text_color="gray"
        )
        self.image_preview_label.pack(expand=True)
        
        # Students table section
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        table_title = ctk.CTkLabel(
            table_frame,
            text="Extracted Students",
            font=("Arial Bold", 14)
        )
        table_title.pack(pady=(10, 5))
        
        # Create scrollable frame for student list
        from customtkinter import CTkScrollableFrame
        self.students_scroll = CTkScrollableFrame(
            table_frame,
            height=300,
            width=850
        )
        self.students_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Action buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        self.add_student_btn = ctk.CTkButton(
            button_frame,
            text="➕ Add Student",
            command=self.add_manual_student,
            width=150,
            height=40,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.add_student_btn.pack(side="right", padx=5)

        self.register_btn = ctk.CTkButton(
            button_frame,
            text="✅ Register All Students",
            command=self.register_students,
            width=200,
            height=40,
            fg_color="#27ae60",
            hover_color="#219150",
            state="disabled"
        )
        self.register_btn.pack(side="right", padx=5)
        
        self.clear_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ Clear All",
            command=self.clear_all,
            width=150,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled"
        )
        self.clear_btn.pack(side="right", padx=5)
        
        # Instructions
        instructions = """
        Instructions:
        1. Click 'Select Image' to choose an image containing a student list
        2. Click 'Extract Students' to process the image with OCR
        3. Review and edit the extracted student data
        4. Click 'Add Student' to manually add students if OCR missed any
        5. Click 'Register All Students' to add them to the system
        
        For best results:
        - Use clear, high-resolution images
        - Ensure text is well-lit and readable
        - Use images with tabular or list format
        - If OCR fails, use 'Add Student' to enter manually
        """
        
        instructions_label = ctk.CTkLabel(
            main_frame,
            text=instructions,
            font=("Arial", 10),
            justify="left",
            text_color="gray"
        )
        instructions_label.pack(pady=10)
        
    def select_image(self):
        """Select an image file"""
        file_path = filedialog.askopenfilename(
            title="Select Student List Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.image_path = file_path
            self.image_path_label.configure(text=os.path.basename(file_path))
            self.process_btn.configure(state="normal")
            
            # Show image preview
            self.show_image_preview(file_path)
            
    def show_image_preview(self, image_path):
        """Show preview of selected image"""
        try:
            # Load and resize image for preview
            img = Image.open(image_path)
            
            # Calculate aspect ratio
            img_width, img_height = img.size
            max_width = 850
            max_height = 200
            
            if img_width > max_width or img_height > max_height:
                ratio = min(max_width/img_width, max_height/img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to CTkImage
            ctk_img = ctk.CTkImage(img, size=img.size)
            
            # Update preview
            self.image_preview_label.configure(image=ctk_img, text="")
            self.image_preview_label.image = ctk_img
            
        except Exception as e:
            self.image_preview_label.configure(text=f"Error loading image: {str(e)}")
            
    def process_image(self):
        """Process the selected image with OCR"""
        if not self.image_path:
            messagebox.showerror("Error", "Please select an image first")
            return
        
        try:
            # Show processing message
            self.process_btn.configure(state="disabled", text="Processing...")
            self.update()
            
            # Process image with OCR
            students, message = self.ocr_service.process_student_list_image(self.image_path)
            
            if not students:
                messagebox.showwarning("No Results", message)
                self.process_btn.configure(state="normal", text="🔍 Extract Students")
                return
            
            # Store extracted students
            self.extracted_students = students
            
            # Display students in the UI
            self.display_students(students)
            
            # Enable register button
            self.register_btn.configure(state="normal")
            self.clear_btn.configure(state="normal")
            
            # Show success message
            messagebox.showinfo("Success", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process image: {str(e)}")
        finally:
            self.process_btn.configure(state="normal", text="🔍 Extract Students")
            
    def display_students(self, students):
        """Display extracted students in the UI"""
        # Clear existing widgets
        for widget in self.students_scroll.winfo_children():
            widget.destroy()
        
        # Create header row
        header_frame = ctk.CTkFrame(self.students_scroll)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        headers = ["ADM No", "Name", "Grade", "Gender", "Phone", "Actions"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                header_frame,
                text=header,
                font=("Arial Bold", 11),
                width=130 if i < 5 else 100
            )
            label.pack(side="left", padx=5)
        
        # Create student rows
        self.student_entries = []
        
        for i, student in enumerate(students):
            row_frame = ctk.CTkFrame(self.students_scroll)
            row_frame.pack(fill="x", padx=5, pady=2)
            
            # Create entry widgets for each field
            entries = {}
            
            # ADM No
            adm_var = ctk.StringVar(value=student.get('adm_no', ''))
            adm_entry = ctk.CTkEntry(row_frame, textvariable=adm_var, width=130)
            adm_entry.pack(side="left", padx=5)
            entries['adm_no'] = adm_var
            
            # Name
            name_var = ctk.StringVar(value=student.get('name', ''))
            name_entry = ctk.CTkEntry(row_frame, textvariable=name_var, width=200)
            name_entry.pack(side="left", padx=5)
            entries['name'] = name_var
            
            # Grade
            grade_var = ctk.StringVar(value=student.get('grade', ''))
            grade_entry = ctk.CTkEntry(row_frame, textvariable=grade_var, width=100)
            grade_entry.pack(side="left", padx=5)
            entries['grade'] = grade_var
            
            # Gender
            gender_var = ctk.StringVar(value=student.get('gender', ''))
            gender_menu = ctk.CTkOptionMenu(
                row_frame,
                values=["", "M", "F"],
                variable=gender_var,
                width=80
            )
            gender_menu.pack(side="left", padx=5)
            entries['gender'] = gender_var
            
            # Phone
            phone_var = ctk.StringVar(value=student.get('phone', ''))
            phone_entry = ctk.CTkEntry(row_frame, textvariable=phone_var, width=130)
            phone_entry.pack(side="left", padx=5)
            entries['phone'] = phone_var
            
            # Remove button
            remove_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=30,
                height=28,
                fg_color="#e74c3c",
                hover_color="#c0392b",
                command=lambda idx=i: self.remove_student(idx)
            )
            remove_btn.pack(side="left", padx=5)
            
            self.student_entries.append(entries)
            
    def remove_student(self, index):
        """Remove a student from the list"""
        if 0 <= index < len(self.extracted_students):
            del self.extracted_students[index]
            del self.student_entries[index]
            self.display_students(self.extracted_students)
            
            if not self.extracted_students:
                self.register_btn.configure(state="disabled")
                self.clear_btn.configure(state="disabled")
                
    def add_manual_student(self):
        """Add a new empty student row for manual entry"""
        new_student = {
            'adm_no': '',
            'name': '',
            'grade': '',
            'gender': '',
            'phone': ''
        }
        self.extracted_students.append(new_student)
        self.display_students(self.extracted_students)
        
        # Enable register and clear buttons
        self.register_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")

    def clear_all(self):
        """Clear all extracted students"""
        self.extracted_students = []
        self.student_entries = []
        
        # Clear the display
        for widget in self.students_scroll.winfo_children():
            widget.destroy()
        
        self.register_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        
    def register_students(self):
        """Register all extracted students to the database"""
        if not self.student_entries:
            messagebox.showerror("Error", "No students to register")
            return
        
        # Collect data from entry widgets
        students_to_register = []
        for entries in self.student_entries:
            student = {
                'adm_no': entries['adm_no'].get().strip(),
                'name': entries['name'].get().strip(),
                'grade': entries['grade'].get().strip(),
                'gender': entries['gender'].get().strip(),
                'phone': entries['phone'].get().strip()
            }
            
            # Validate required fields
            if not student['adm_no'] or not student['name']:
                messagebox.showerror("Error", "ADM No and Name are required for all students")
                return
            
            students_to_register.append(student)
        
        # Confirm registration
        result = messagebox.askyesno(
            "Confirm Registration",
            f"Register {len(students_to_register)} students to the database?"
        )
        
        if not result:
            return
        
        # Register students
        success_count = 0
        failed_students = []
        
        for student in students_to_register:
            try:
                # Validate and clean data
                cleaned = self.ocr_service.validate_student_data(student)
                
                # Add to database
                success = self.db.add_student(
                    adm=cleaned.get('adm_no', ''),
                    name=cleaned.get('name', ''),
                    grade=cleaned.get('grade', ''),
                    gender=cleaned.get('gender', ''),
                    phone=cleaned.get('phone', ''),
                    check_footprint=True
                )
                
                if success:
                    success_count += 1
                else:
                    failed_students.append(student['name'])
                    
            except Exception as e:
                failed_students.append(f"{student['name']} ({str(e)})")
        
        # Show results
        if success_count > 0:
            message = f"Successfully registered {success_count} students"
            if failed_students:
                message += f"\n\nFailed to register {len(failed_students)} students:\n"
                message += "\n".join(failed_students[:5])  # Show first 5 failures
                if len(failed_students) > 5:
                    message += f"\n... and {len(failed_students) - 5} more"
            
            messagebox.showinfo("Registration Complete", message)
            
            # Clear the dialog
            self.clear_all()
            
            # Refresh parent if callback provided
            if self.callback:
                self.callback()
                
            # Close dialog
            self.destroy()
        else:
            messagebox.showerror("Registration Failed", "Failed to register any students")

def show_ocr_dialog(parent, callback=None, db=None):
    """Show the OCR student registration dialog"""
    dialog = OCRStudentDialog(parent, callback, db)
    dialog.grab_set()  # Make dialog modal
    return dialog

if __name__ == "__main__":
    # Test the dialog
    root = ctk.CTk()
    root.geometry("400x300")
    
    def on_callback():
        print("Students registered successfully!")
    
    btn = ctk.CTkButton(root, text="Open OCR Dialog", command=lambda: show_ocr_dialog(root, on_callback))
    btn.pack(expand=True)
    
    root.mainloop()
