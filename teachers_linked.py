import customtkinter as ctk
from tkinter import messagebox
from database import FreemanDB
import customtkinter as ctk

GRADE_SUBJECTS = {
    "playgroup": ["LANG", "MATH", "ENV", "CREAT"],
    "pp1": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "pp2": ["LANG", "MATH", "ENV", "PSYCH", "REL"],
    "Grade 1": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "Grade 2": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "Grade 3": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
    "Grade 4": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "Grade 5": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "Grade 6": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
    "Grade 7": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"],
    "Grade 8": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"],
    "Grade 9": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"],
}

class TeachersLinkedView(ctk.CTkFrame):
    def __init__(self, parent, db, class_name, return_callback):
        super().__init__(parent)
        self.db = db
        self.class_name = class_name
        self.return_callback = return_callback
        self.all_teacher_rows = []
        
        self.pack(fill="both", expand=True)
        self.setup_ui()
        self.load_teachers_from_db()
        
    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="gray20", height=80)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"Teachers Linked: {self.class_name.upper()}",
            font=("Arial Bold", 24),
            text_color="white"
        )
        title_label.pack(side="left", padx=20, pady=20)
        
        back_btn = ctk.CTkButton(
            header_frame,
            text="← Back to Dashboard",
            command=self.return_callback,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            width=150
        )
        back_btn.pack(side="right", padx=20, pady=20)
        
        # Main content area
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Table frame with scroll
        self.table_frame = ctk.CTkScrollableFrame(
            content_frame,
            fg_color="gray15",
            corner_radius=10,
            label_text="Subject-Teacher Assignments",
            label_font=("Arial Bold", 16)
        )
        self.table_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
        
        # Create table headers
        self.create_table_headers()
        
        # Control panel
        control_panel = ctk.CTkFrame(content_frame, width=200, fg_color="transparent")
        control_panel.pack(side="right", fill="y")
        
        btn_style = {"width": 160, "height": 40, "font": ("Arial Bold", 13)}
        
        self.btn_add = ctk.CTkButton(
            control_panel,
            text="Add Assignment",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            **btn_style,
            command=self.add_empty_row
        )
        self.btn_add.pack(pady=10)
        
        self.btn_edit = ctk.CTkButton(
            control_panel,
            text="Edit All",
            fg_color="#f39c12",
            hover_color="#d35400",
            **btn_style,
            command=self.mass_edit_all
        )
        self.btn_edit.pack(pady=10)
        
        spacer = ctk.CTkLabel(control_panel, text="")
        spacer.pack(expand=True)
        
    def create_table_headers(self):
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="gray25", corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 10))
        
        header_frame.grid_columnconfigure(0, weight=2)
        header_frame.grid_columnconfigure(1, weight=2)
        header_frame.grid_columnconfigure(2, weight=2)
        header_frame.grid_columnconfigure(3, weight=0, minsize=150)
        
        cols = ["SUBJECT", "TEACHER NAME", "TEACHER CODE", "ACTIONS"]
        for i, text in enumerate(cols):
            lbl = ctk.CTkLabel(header_frame, text=text, font=("Arial Bold", 12), text_color="white")
            lbl.grid(row=0, column=i, padx=10, pady=5, sticky="w")
    
    def add_empty_row(self):
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#2b2b2b", height=40)
        row_frame.pack(fill="x", pady=2, padx=5)
        self.all_teacher_rows.append(row_frame)
        
        row_frame.grid_columnconfigure(0, weight=2)
        row_frame.grid_columnconfigure(1, weight=2)
        row_frame.grid_columnconfigure(2, weight=2)
        row_frame.grid_columnconfigure(3, weight=0, minsize=150)
        
        # Subject dropdown
        subjects = GRADE_SUBJECTS.get(self.class_name, [])
        subject_var = ctk.StringVar(value=subjects[0] if subjects else "")
        subject_dropdown = ctk.CTkOptionMenu(
            row_frame,
            values=subjects,
            variable=subject_var,
            fg_color="white",
            text_color="black",
            button_color="white",
            button_hover_color="#e0e0e0"
        )
        subject_dropdown.grid(row=0, column=0, padx=2, pady=5, sticky="ew")
        
        # Teacher name entry
        teacher_name = ctk.CTkEntry(row_frame, placeholder_text="Teacher Name", fg_color="white", text_color="black", height=30)
        teacher_name.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        
        # Teacher code entry
        teacher_code = ctk.CTkEntry(row_frame, placeholder_text="Teacher Code", fg_color="white", text_color="black", height=30)
        teacher_code.grid(row=0, column=2, padx=2, pady=5, sticky="ew")
        
        # Actions frame
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=5)
        
        # Save button
        save_btn = ctk.CTkButton(
            actions_frame,
            text="✓",
            width=30,
            fg_color="green",
            command=lambda: self.save_to_db(subject_var, teacher_name, teacher_code, save_btn, row_frame)
        )
        save_btn.pack(side="left", padx=2)
        
        # Delete button
        del_btn = ctk.CTkButton(
            actions_frame,
            text="🗑",
            width=30,
            fg_color="#942727",
            command=lambda f=row_frame: self.confirm_delete(f)
        )
        del_btn.pack(side="left", padx=2)
    
    def save_to_db(self, subject_var, teacher_name_entry, teacher_code_entry, btn, row_frame):
        subject = subject_var.get()
        teacher_name = teacher_name_entry.get().strip()
        teacher_code = teacher_code_entry.get().strip()
        
        if not subject or not teacher_name or not teacher_code:
            messagebox.showwarning("Input Error", "Subject, Teacher Name, and Teacher Code are required!")
            return
        
        try:
            self.db.add_teacher_assignment(self.class_name, subject, teacher_name, teacher_code)
            
            # Lock the row
            for widget in row_frame.winfo_children():
                if isinstance(widget, ctk.CTkEntry):
                    widget.configure(state="disabled", fg_color="gray30", text_color="white")
                elif isinstance(widget, ctk.CTkOptionMenu):
                    widget.configure(state="disabled")
            
            btn.configure(text="Saved", state="disabled", fg_color="gray")
            print(f"Teacher assignment saved: {teacher_name} for {subject}")
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not save: {e}")
    
    def load_teachers_from_db(self):
        try:
            cursor = self.db.conn.cursor()
            query = "SELECT subject, teacher_name, teacher_code FROM teachers WHERE class_name = ?"
            cursor.execute(query, (self.class_name,))
            records = cursor.fetchall()
            
            for row_data in records:
                self.add_locked_row(row_data)
                
        except Exception as e:
            print(f"Error loading teachers: {e}")
    
    def add_locked_row(self, data):
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#1a1a1a")
        row_frame.pack(fill="x", pady=2, padx=5)
        self.all_teacher_rows.append(row_frame)
        
        row_frame.grid_columnconfigure(0, weight=2)
        row_frame.grid_columnconfigure(1, weight=2)
        row_frame.grid_columnconfigure(2, weight=2)
        row_frame.grid_columnconfigure(3, weight=0, minsize=150)
        
        # Subject (locked dropdown)
        subjects = GRADE_SUBJECTS.get(self.class_name, [])
        subject_var = ctk.StringVar(value=data[0])
        subject_dropdown = ctk.CTkOptionMenu(
            row_frame,
            values=subjects,
            variable=subject_var,
            fg_color="gray30",
            text_color="white",
            button_color="gray30",
            button_hover_color="gray40"
        )
        subject_dropdown.configure(state="disabled")
        subject_dropdown.grid(row=0, column=0, padx=2, pady=5, sticky="ew")
        
        # Teacher name (locked entry)
        teacher_name = ctk.CTkEntry(row_frame, fg_color="gray30", text_color="white", height=30)
        teacher_name.insert(0, data[1])
        teacher_name.configure(state="disabled")
        teacher_name.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        
        # Teacher code (locked entry)
        teacher_code = ctk.CTkEntry(row_frame, fg_color="gray30", text_color="white", height=30)
        teacher_code.insert(0, data[2])
        teacher_code.configure(state="disabled")
        teacher_code.grid(row=0, column=2, padx=2, pady=5, sticky="ew")
        
        # Actions frame
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=5)
        
        # Edit button
        edit_btn = ctk.CTkButton(
            actions_frame,
            text="✎",
            width=30,
            fg_color="#1f538d",
            command=lambda: self.unlock_row_for_edit(subject_var, teacher_name, teacher_code, actions_frame, row_frame)
        )
        edit_btn.pack(side="left", padx=2)
        
        # Delete button
        del_btn = ctk.CTkButton(
            actions_frame,
            text="🗑",
            width=30,
            fg_color="#942727",
            command=lambda f=row_frame, s=data[0]: self.confirm_delete_with_subject(f, s)
        )
        del_btn.pack(side="left", padx=2)
    
    def unlock_row_for_edit(self, subject_var, teacher_name, teacher_code, actions_frame, row_frame):
        # Unlock entries
        teacher_name.configure(state="normal", fg_color="white", text_color="black")
        teacher_code.configure(state="normal", fg_color="white", text_color="black")
        subject_var.set(subject_var.get())  # Keep current value
        subject_dropdown = None
        for widget in row_frame.winfo_children():
            if isinstance(widget, ctk.CTkOptionMenu):
                widget.configure(state="normal")
                subject_dropdown = widget
                break
        
        # Replace edit button with save button
        for widget in actions_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "✎":
                widget.destroy()
                break
        
        save_btn = ctk.CTkButton(
            actions_frame,
            text="✓",
            width=30,
            fg_color="green",
            command=lambda: self.update_in_db(subject_var, teacher_name, teacher_code, save_btn, actions_frame, row_frame, subject_dropdown)
        )
        save_btn.pack(side="left", padx=2)
    
    def update_in_db(self, subject_var, teacher_name_entry, teacher_code_entry, btn, actions_frame, row_frame, subject_dropdown):
        subject = subject_var.get()
        teacher_name = teacher_name_entry.get().strip()
        teacher_code = teacher_code_entry.get().strip()
        
        if not subject or not teacher_name or not teacher_code:
            messagebox.showwarning("Input Error", "All fields are required!")
            return
        
        try:
            # Get old subject from the first entry in the row
            old_subject = None
            for widget in row_frame.winfo_children():
                if isinstance(widget, ctk.CTkOptionMenu):
                    old_subject = widget.get()
                    break
            
            self.db.update_teacher_assignment(self.class_name, old_subject, subject, teacher_name, teacher_code)
            
            # Lock the row again
            teacher_name_entry.configure(state="disabled", fg_color="gray30", text_color="white")
            teacher_code_entry.configure(state="disabled", fg_color="gray30", text_color="white")
            subject_dropdown.configure(state="disabled")
            
            # Replace save button with edit button
            btn.destroy()
            edit_btn = ctk.CTkButton(
                actions_frame,
                text="✎",
                width=30,
                fg_color="#1f538d",
                command=lambda: self.unlock_row_for_edit(subject_var, teacher_name_entry, teacher_code_entry, actions_frame, row_frame)
            )
            edit_btn.pack(side="left", padx=2)
            
            print(f"Teacher assignment updated: {teacher_name} for {subject}")
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not update: {e}")
    
    def confirm_delete(self, frame):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this assignment?"):
            frame.destroy()
            if frame in self.all_teacher_rows:
                self.all_teacher_rows.remove(frame)
    
    def confirm_delete_with_subject(self, frame, subject):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the assignment for {subject}?"):
            try:
                self.db.delete_teacher_assignment(self.class_name, subject)
                frame.destroy()
                if frame in self.all_teacher_rows:
                    self.all_teacher_rows.remove(frame)
                print(f"Teacher assignment deleted for {subject}")
            except Exception as e:
                messagebox.showerror("Database Error", f"Could not delete: {e}")
    
    def mass_edit_all(self):
        """Unlocks all rows for editing"""
        for row in self.all_teacher_rows:
            subject_var = None
            teacher_name = None
            teacher_code = None
            actions_frame = None
            subject_dropdown = None
            
            for widget in row.winfo_children():
                if isinstance(widget, ctk.CTkOptionMenu):
                    subject_var = widget
                    subject_dropdown = widget
                elif isinstance(widget, ctk.CTkEntry):
                    if teacher_name is None:
                        teacher_name = widget
                    else:
                        teacher_code = widget
                elif isinstance(widget, ctk.CTkFrame):
                    actions_frame = widget
            
            if subject_var and teacher_name and teacher_code and actions_frame:
                # Unlock entries
                teacher_name.configure(state="normal", fg_color="white", text_color="black")
                teacher_code.configure(state="normal", fg_color="white", text_color="black")
                subject_dropdown.configure(state="normal")
                
                # Find and replace edit button with save button
                for widget in actions_frame.winfo_children():
                    if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "✎":
                        widget.destroy()
                        break
                
                save_btn = ctk.CTkButton(
                    actions_frame,
                    text="✓",
                    width=30,
                    fg_color="green",
                    command=lambda sv=subject_var, tn=teacher_name, tc=teacher_code, sb=save_btn, af=actions_frame, rf=row, sd=subject_dropdown: self.update_in_db(sv, tn, tc, sb, af, rf, sd)
                )
                save_btn.pack(side="left", padx=2)
        
        print("All teacher assignments unlocked for editing.")
