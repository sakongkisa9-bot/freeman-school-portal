import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import font as tkfont
import os
import json
import sqlite3
from datetime import datetime
from cloud_service import CloudService, ask_cloud_credentials


class NewsletterCreator(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        
        self.db = db
        self.parent = parent
        self.attachment_path = None
        
        # Window configuration
        self.title("Newsletter & Circular Creator")
        self.geometry("1200x800")
        
        # Make window full screen
        self.state('zoomed')
        
        # Center the window (fallback if zoomed doesn't work)
        self.update_idletasks()
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        x = 0
        y = 0
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        # Main container with scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="#f0f0f0")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#f0f0f0")
        self.main_frame.pack(fill="both", expand=True)
        
        # Close button in top right corner
        close_btn = ctk.CTkButton(
            self.main_frame,
            text="✕",
            width=40,
            height=40,
            command=self.destroy,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=("Arial", 18),
            corner_radius=20
        )
        close_btn.place(relx=1.0, rely=0.0, x=-15, y=15, anchor="ne")
        
        # Build the three sections
        self._build_audience_selector()
        self._build_wysiwyg_editor()
        self._build_attachment_channels()
        
        # Track active formatting for future typing
        self.active_formats = {"bold": False, "italic": False, "underline": False}
        
        # Initialize button states after a short delay
        self.after(100, self._update_button_states)
        
    def _build_audience_selector(self):
        """Top Section: Audience Selector with three dropdowns"""
        audience_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10)
        audience_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Title
        title_label = ctk.CTkLabel(
            audience_frame, 
            text="📋 Select Recipients", 
            font=("Arial Bold", 14),
            text_color="#2c3e50"
        )
        title_label.pack(pady=(10, 5))
        
        # Dropdowns container
        dropdowns_frame = ctk.CTkFrame(audience_frame, fg_color="transparent")
        dropdowns_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        dropdowns_frame.grid_columnconfigure(0, weight=1)
        dropdowns_frame.grid_columnconfigure(1, weight=1)
        dropdowns_frame.grid_columnconfigure(2, weight=1)
        
        # Dropdown 1: Target Type
        target_label = ctk.CTkLabel(
            dropdowns_frame, 
            text="Target Type", 
            font=("Arial", 11),
            text_color="#34495e"
        )
        target_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        self.target_type_var = ctk.StringVar(value="All School")
        self.target_type_dropdown = ctk.CTkOptionMenu(
            dropdowns_frame,
            variable=self.target_type_var,
            values=["All School", "By Class", "By Stream", "Individual Student"],
            command=self._on_target_type_change,
            fg_color="white",
            button_color="#3498db",
            button_hover_color="#2980b9",
            dropdown_fg_color="white",
            dropdown_text_color="#2c3e50"
        )
        self.target_type_dropdown.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Dropdown 2: Class Context
        class_label = ctk.CTkLabel(
            dropdowns_frame, 
            text="Class/Grade", 
            font=("Arial", 11),
            text_color="#34495e"
        )
        class_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        self.class_context_var = ctk.StringVar(value="All Classes")
        self.class_context_dropdown = ctk.CTkOptionMenu(
            dropdowns_frame,
            variable=self.class_context_var,
            values=self._get_class_options(),
            fg_color="white",
            button_color="#3498db",
            button_hover_color="#2980b9",
            dropdown_fg_color="white",
            dropdown_text_color="#2c3e50"
        )
        self.class_context_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Dropdown 3: Recipient Role (changes based on target type)
        role_label = ctk.CTkLabel(
            dropdowns_frame, 
            text="Send To", 
            font=("Arial", 11),
            text_color="#34495e"
        )
        role_label.grid(row=0, column=2, padx=5, pady=2, sticky="w")
        
        self.recipient_role_var = ctk.StringVar(value="Both Parents")
        self.recipient_role_dropdown = ctk.CTkOptionMenu(
            dropdowns_frame,
            variable=self.recipient_role_var,
            values=["Father", "Mother", "Both Parents"],
            fg_color="white",
            button_color="#3498db",
            button_hover_color="#2980b9",
            dropdown_fg_color="white",
            dropdown_text_color="#2c3e50"
        )
        self.recipient_role_dropdown.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
    def _build_wysiwyg_editor(self):
        """Middle Section: WYSIWYG Text Editor with formatting toolbar"""
        editor_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Editor title
        editor_title = ctk.CTkLabel(
            editor_frame, 
            text="✍️ Write Your Circular", 
            font=("Arial Bold", 14),
            text_color="#2c3e50"
        )
        editor_title.pack(pady=(10, 5))
        
        # Subject line
        subject_frame = ctk.CTkFrame(editor_frame, fg_color="transparent")
        subject_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        subject_label = ctk.CTkLabel(
            subject_frame, 
            text="Circular Title:", 
            font=("Arial Bold", 11),
            text_color="#2c3e50",
            width=100
        )
        subject_label.pack(side="left", padx=(0, 10))
        
        self.subject_entry = ctk.CTkEntry(
            subject_frame,
            placeholder_text="Enter the main title of your circular (e.g., 'Term 1 Exam Schedule')...",
            fg_color="white",
            border_color="#bdc3c7",
            border_width=1,
            text_color="#2c3e50",
            placeholder_text_color="#95a5a6",
            height=35
        )
        self.subject_entry.pack(side="left", fill="x", expand=True)
        
        # Formatting toolbar with horizontal scroll
        toolbar_scroll_frame = ctk.CTkScrollableFrame(editor_frame, fg_color="#ecf0f1", corner_radius=5, orientation="horizontal")
        toolbar_scroll_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        toolbar_frame = ctk.CTkFrame(toolbar_scroll_frame, fg_color="transparent")
        toolbar_frame.pack(fill="x")
        
        # Toolbar buttons - larger size
        btn_style = {
            "width": 45,
            "height": 45,
            "fg_color": "white",
            "hover_color": "#bdc3c7",
            "text_color": "#2c3e50",
            "font": ("Arial Bold", 14),
            "corner_radius": 8
        }
        
        self.bold_btn = ctk.CTkButton(toolbar_frame, text="B", command=lambda: [self._apply_format("bold"), self.after(10, self._update_button_states)], **btn_style)
        self.bold_btn.pack(side="left", padx=5, pady=5)
        
        self.italic_btn = ctk.CTkButton(toolbar_frame, text="I", command=lambda: [self._apply_format("italic"), self.after(10, self._update_button_states)], **btn_style)
        self.italic_btn.pack(side="left", padx=5, pady=5)
        
        self.underline_btn = ctk.CTkButton(toolbar_frame, text="U", command=lambda: [self._apply_format("underline"), self.after(10, self._update_button_states)], **btn_style)
        self.underline_btn.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator1 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator1.pack(side="left", padx=10, fill="y", pady=8)
        
        # Font family dropdown
        self.font_var = ctk.StringVar(value="Arial")
        font_dropdown = ctk.CTkOptionMenu(
            toolbar_frame,
            variable=self.font_var,
            values=["Arial", "Times New Roman", "Georgia", "Courier New"],
            command=self._apply_font,
            fg_color="white",
            button_color="#3498db",
            button_hover_color="#2980b9",
            dropdown_fg_color="white",
            dropdown_text_color="#2c3e50",
            width=120,
            height=45
        )
        font_dropdown.pack(side="left", padx=5, pady=5)
        
        # Text size
        self.text_size_var = ctk.StringVar(value="12")
        size_dropdown = ctk.CTkOptionMenu(
            toolbar_frame,
            variable=self.text_size_var,
            values=["10", "12", "14", "16", "18", "20"],
            command=self._apply_size,
            fg_color="white",
            button_color="#3498db",
            button_hover_color="#2980b9",
            dropdown_fg_color="white",
            dropdown_text_color="#2c3e50",
            width=70,
            height=45
        )
        size_dropdown.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator2 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator2.pack(side="left", padx=10, fill="y", pady=8)
        
        # Alignment buttons
        align_left_btn = ctk.CTkButton(toolbar_frame, text="⫷", command=lambda: self._apply_alignment("left"), **btn_style)
        align_left_btn.pack(side="left", padx=5, pady=5)
        
        align_center_btn = ctk.CTkButton(toolbar_frame, text="≡", command=lambda: self._apply_alignment("center"), **btn_style)
        align_center_btn.pack(side="left", padx=5, pady=5)
        
        align_right_btn = ctk.CTkButton(toolbar_frame, text="⫸", command=lambda: self._apply_alignment("right"), **btn_style)
        align_right_btn.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator3 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator3.pack(side="left", padx=10, fill="y", pady=8)
        
        # Heading styles
        self.heading_var = ctk.StringVar(value="Normal")
        heading_dropdown = ctk.CTkOptionMenu(
            toolbar_frame,
            variable=self.heading_var,
            values=["Normal", "Heading 1", "Heading 2", "Heading 3"],
            command=self._apply_heading,
            fg_color="white",
            button_color="#3498db",
            button_hover_color="#2980b9",
            dropdown_fg_color="white",
            dropdown_text_color="#2c3e50",
            width=100,
            height=45
        )
        heading_dropdown.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator4 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator4.pack(side="left", padx=10, fill="y", pady=8)
        
        # Text color
        color_btn = ctk.CTkButton(toolbar_frame, text="🎨", command=self._choose_text_color, **btn_style)
        color_btn.pack(side="left", padx=5, pady=5)
        
        # Highlight color
        highlight_btn = ctk.CTkButton(toolbar_frame, text="🖍️", command=self._choose_highlight_color, **btn_style)
        highlight_btn.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator5 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator5.pack(side="left", padx=10, fill="y", pady=8)
        
        # Strikethrough
        strike_btn = ctk.CTkButton(toolbar_frame, text="S̶", command=lambda: self._apply_format("strikethrough"), **btn_style)
        strike_btn.pack(side="left", padx=5, pady=5)
        
        # Subscript
        sub_btn = ctk.CTkButton(toolbar_frame, text="ₓ", command=lambda: self._apply_format("subscript"), **btn_style)
        sub_btn.pack(side="left", padx=5, pady=5)
        
        # Superscript
        sup_btn = ctk.CTkButton(toolbar_frame, text="ˣ", command=lambda: self._apply_format("superscript"), **btn_style)
        sup_btn.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator6 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator6.pack(side="left", padx=10, fill="y", pady=8)
        
        # Indentation
        indent_left_btn = ctk.CTkButton(toolbar_frame, text="⇤", command=self._decrease_indent, **btn_style)
        indent_left_btn.pack(side="left", padx=5, pady=5)
        
        indent_right_btn = ctk.CTkButton(toolbar_frame, text="⇥", command=self._increase_indent, **btn_style)
        indent_right_btn.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator7 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator7.pack(side="left", padx=10, fill="y", pady=8)
        
        # Undo/Redo
        undo_btn = ctk.CTkButton(toolbar_frame, text="↶", command=self._undo, **btn_style)
        undo_btn.pack(side="left", padx=5, pady=5)
        
        redo_btn = ctk.CTkButton(toolbar_frame, text="↷", command=self._redo, **btn_style)
        redo_btn.pack(side="left", padx=5, pady=5)
        
        # Separator
        separator8 = ctk.CTkFrame(toolbar_frame, fg_color="#bdc3c7", width=2)
        separator8.pack(side="left", padx=10, fill="y", pady=8)
        
        # List buttons
        bullet_btn = ctk.CTkButton(toolbar_frame, text="•", command=lambda: self._apply_format("bullet"), **btn_style)
        bullet_btn.pack(side="left", padx=5, pady=5)
        
        number_btn = ctk.CTkButton(toolbar_frame, text="1.", command=lambda: self._apply_format("number"), **btn_style)
        number_btn.pack(side="left", padx=5, pady=5)
        
        letter_btn = ctk.CTkButton(toolbar_frame, text="a.", command=lambda: self._apply_format("letter"), **btn_style)
        letter_btn.pack(side="left", padx=5, pady=5)
        
        roman_btn = ctk.CTkButton(toolbar_frame, text="i.", command=lambda: self._apply_format("roman"), **btn_style)
        roman_btn.pack(side="left", padx=5, pady=5)
        
        # Text editor area (white paper-like workspace) - larger height for multiple topics
        editor_container = ctk.CTkFrame(editor_frame, fg_color="white", border_color="#bdc3c7", border_width=1)
        editor_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Use tkinter Text widget for rich text editing
        from tkinter import Text
        self.text_editor = Text(
            editor_container,
            bg="white",
            fg="#2c3e50",
            font=("Arial", 12),
            wrap="word",
            padx=15,
            pady=15,
            relief="flat",
            borderwidth=0
        )
        self.text_editor.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bind Return key to handle list continuation
        self.text_editor.bind("<Return>", self._handle_return_key)
        
        # Bind keyboard shortcuts for formatting
        self.text_editor.bind("<Control-b>", lambda e: self._apply_format("bold"))
        self.text_editor.bind("<Control-i>", lambda e: self._apply_format("italic"))
        self.text_editor.bind("<Control-u>", lambda e: self._apply_format("underline"))
        self.text_editor.bind("<Control-l>", lambda e: self._apply_alignment("left"))
        self.text_editor.bind("<Control-e>", lambda e: self._apply_alignment("center"))
        self.text_editor.bind("<Control-r>", lambda e: self._apply_alignment("right"))
        
        # Bind selection change event to update button highlighting
        self.text_editor.bind("<KeyRelease>", self._update_button_states)
        self.text_editor.bind("<ButtonRelease-1>", self._update_button_states)
        self.text_editor.bind("<Button-1>", self._update_button_states)
        self.text_editor.bind("<B1-Motion>", self._update_button_states)
        
        # Bind key press to apply active formatting when typing
        self.text_editor.bind("<Key>", self._apply_active_formatting)
        
        # Configure text tags for formatting
        self.text_editor.tag_configure("bold", font=("Arial Bold", 12))
        self.text_editor.tag_configure("italic", font=("Arial Italic", 12))
        self.text_editor.tag_configure("underline", underline=True)
        self.text_editor.tag_configure("large", font=("Arial", 16))
        self.text_editor.tag_configure("center", justify="center")
        self.text_editor.tag_configure("right", justify="right")
        self.text_editor.tag_configure("strikethrough", overstrike=True)
        self.text_editor.tag_configure("subscript", offset=-5, font=("Arial", 9))
        self.text_editor.tag_configure("superscript", offset=5, font=("Arial", 9))
        self.text_editor.tag_configure("heading1", font=("Arial Bold", 24), spacing1=20, spacing3=20)
        self.text_editor.tag_configure("heading2", font=("Arial Bold", 20), spacing1=15, spacing3=15)
        self.text_editor.tag_configure("heading3", font=("Arial Bold", 16), spacing1=10, spacing3=10)
        
    def _build_attachment_channels(self):
        """Bottom Section: Attachment & Channels Bar"""
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=10)
        bottom_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Title
        bottom_title = ctk.CTkLabel(
            bottom_frame, 
            text="📎 Attachments & Delivery", 
            font=("Arial Bold", 14),
            text_color="#2c3e50"
        )
        bottom_title.pack(pady=(10, 5))
        
        # Content container
        content_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=0, minsize=500)
        
        # Left side: Attachment and checkboxes
        left_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w")
        
        # Attachment button
        attachment_frame = ctk.CTkFrame(left_frame, fg_color="#ecf0f1", corner_radius=5)
        attachment_frame.pack(side="left", padx=(0, 20))
        
        self.attachment_label = ctk.CTkLabel(
            attachment_frame, 
            text="📎 Attach Fee Structure / PDF / Image", 
            font=("Arial", 10),
            text_color="#2c3e50"
        )
        self.attachment_label.pack(side="left", padx=10, pady=8)
        
        attachment_btn = ctk.CTkButton(
            attachment_frame,
            text="Choose File",
            width=100,
            height=30,
            command=self._choose_attachment,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        attachment_btn.pack(side="left", padx=(0, 10), pady=8)
        
        # Checkboxes
        checkbox_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        checkbox_frame.pack(side="left")
        
        self.sms_var = ctk.BooleanVar(value=True)  # Default to True for mandatory SMS
        sms_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Send SMS Alert to Parent's Phone (Required)",
            variable=self.sms_var,
            fg_color="#3498db",
            hover_color="#2980b9",
            text_color="#2c3e50",
            font=("Arial", 10)
        )
        sms_checkbox.pack(anchor="w", pady=2)
        
        # Right side: Action buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")
        
        # Save Draft button
        save_draft_btn = ctk.CTkButton(
            button_frame,
            text="Save Draft",
            width=120,
            height=40,
            command=self._save_draft,
            fg_color="#95a5a6",
            hover_color="#7f8c8d",
            font=("Arial", 11)
        )
        save_draft_btn.pack(side="left", padx=5)
        
        # Print PDF Circular button (secondary action)
        print_pdf_btn = ctk.CTkButton(
            button_frame,
            text="🖨️ Print PDF Circular",
            width=160,
            height=40,
            command=self._print_pdf_circular,
            fg_color="#5dade2",
            hover_color="#3498db",
            font=("Arial", 11)
        )
        print_pdf_btn.pack(side="left", padx=5)
        
        # Publish to Parent Portal button (primary action)
        publish_btn = ctk.CTkButton(
            button_frame,
            text="🚀 Publish to Parent Portal & Notify",
            width=220,
            height=40,
            command=self._publish_to_portal,
            fg_color="#27ae60",
            hover_color="#229954",
            font=("Arial Bold", 11)
        )
        publish_btn.pack(side="left", padx=5)
        
    def _get_class_options(self):
        """Get available class/grade options from database"""
        try:
            self.db._cursor.execute("SELECT DISTINCT grade FROM students WHERE grade IS NOT NULL ORDER BY grade")
            classes = [row[0] for row in self.db._cursor.fetchall()]
            if classes:
                return ["All Classes"] + classes
            return ["All Classes"]
        except Exception as e:
            print(f"Error fetching classes: {e}")
            return ["All Classes"]
    
    def _on_target_type_change(self, value):
        """Handle target type dropdown change"""
        if value == "All School":
            self.class_context_dropdown.configure(state="disabled")
            self.class_context_var.set("All Classes")
            self.recipient_role_dropdown.configure(values=["All Parents"])
            self.recipient_role_dropdown.configure(state="disabled")
            self.recipient_role_var.set("All Parents")
        elif value == "Individual Student":
            self.class_context_dropdown.configure(state="normal")
            self.recipient_role_dropdown.configure(state="disabled")
            self.recipient_role_var.set("Select Student")
            # Update student dropdown when class changes
            self.class_context_dropdown.configure(command=self._on_class_change_for_student)
        elif value == "By Stream":
            self.class_context_dropdown.configure(state="normal")
            self.recipient_role_dropdown.configure(state="disabled")
            self.recipient_role_var.set("Select Stream")
            # Update stream dropdown when class changes
            self.class_context_dropdown.configure(command=self._on_class_change_for_stream)
        else:
            self.class_context_dropdown.configure(state="normal")
            self.recipient_role_dropdown.configure(values=["All Parents"])
            self.recipient_role_dropdown.configure(state="disabled")
            self.recipient_role_var.set("All Parents")
    
    def _on_class_change_for_student(self, value):
        """Handle class dropdown change when Individual Student is selected"""
        if self.target_type_var.get() == "Individual Student":
            # Get students for the selected class
            students = self._get_students_for_class(value)
            if students:
                self.recipient_role_dropdown.configure(values=students)
                self.recipient_role_dropdown.configure(state="normal")
                self.recipient_role_var.set(students[0] if students else "Select Student")
            else:
                self.recipient_role_dropdown.configure(values=["No Students"])
                self.recipient_role_var.set("No Students")
    
    def _get_students_for_class(self, class_name):
        """Get list of student names for a specific class"""
        try:
            self.db._cursor.execute(
                "SELECT name FROM students WHERE grade = ? ORDER BY name",
                (class_name,)
            )
            students = [row[0] for row in self.db._cursor.fetchall()]
            return students if students else []
        except Exception as e:
            print(f"Error fetching students for class {class_name}: {e}")
            return []
    
    def _on_class_change_for_stream(self, value):
        """Handle class dropdown change when By Stream is selected"""
        if self.target_type_var.get() == "By Stream":
            # Get streams for the selected class
            streams = self._get_streams_for_class(value)
            if streams:
                self.recipient_role_dropdown.configure(values=streams)
                self.recipient_role_dropdown.configure(state="normal")
                self.recipient_role_var.set(streams[0] if streams else "Select Stream")
            else:
                self.recipient_role_dropdown.configure(values=["No Streams"])
                self.recipient_role_var.set("No Streams")
    
    def _get_streams_for_class(self, class_name):
        """Get list of stream names for a specific class"""
        try:
            self.db._cursor.execute(
                "SELECT DISTINCT stream FROM students WHERE grade = ? AND stream IS NOT NULL AND stream != '' ORDER BY stream",
                (class_name,)
            )
            streams = [row[0] for row in self.db._cursor.fetchall()]
            return streams if streams else []
        except Exception as e:
            print(f"Error fetching streams for class {class_name}: {e}")
            return []
    
    def _apply_format(self, format_type):
        """Apply text formatting to selected text or toggle for future typing"""
        try:
            # Check if text is selected
            if self.text_editor.tag_ranges("sel"):
                # Text is selected - apply/remove formatting to selection
                if format_type == "bold":
                    current_tags = self.text_editor.tag_names("sel.first")
                    if "bold" in current_tags:
                        self.text_editor.tag_remove("bold", "sel.first", "sel.last")
                    else:
                        self.text_editor.tag_add("bold", "sel.first", "sel.last")
                elif format_type == "italic":
                    current_tags = self.text_editor.tag_names("sel.first")
                    if "italic" in current_tags:
                        self.text_editor.tag_remove("italic", "sel.first", "sel.last")
                    else:
                        self.text_editor.tag_add("italic", "sel.first", "sel.last")
                elif format_type == "underline":
                    current_tags = self.text_editor.tag_names("sel.first")
                    if "underline" in current_tags:
                        self.text_editor.tag_remove("underline", "sel.first", "sel.last")
                    else:
                        self.text_editor.tag_add("underline", "sel.first", "sel.last")
                elif format_type == "strikethrough":
                    current_tags = self.text_editor.tag_names("sel.first")
                    if "strikethrough" in current_tags:
                        self.text_editor.tag_remove("strikethrough", "sel.first", "sel.last")
                    else:
                        self.text_editor.tag_add("strikethrough", "sel.first", "sel.last")
                elif format_type == "subscript":
                    current_tags = self.text_editor.tag_names("sel.first")
                    if "subscript" in current_tags:
                        self.text_editor.tag_remove("subscript", "sel.first", "sel.last")
                    else:
                        self.text_editor.tag_add("subscript", "sel.first", "sel.last")
                elif format_type == "superscript":
                    current_tags = self.text_editor.tag_names("sel.first")
                    if "superscript" in current_tags:
                        self.text_editor.tag_remove("superscript", "sel.first", "sel.last")
                    else:
                        self.text_editor.tag_add("superscript", "sel.first", "sel.last")
            else:
                # No text selected - toggle formatting for future typing
                if format_type == "bold":
                    self.active_formats["bold"] = not self.active_formats["bold"]
                elif format_type == "italic":
                    self.active_formats["italic"] = not self.active_formats["italic"]
                elif format_type == "underline":
                    self.active_formats["underline"] = not self.active_formats["underline"]
                elif format_type == "strikethrough":
                    self.active_formats["strikethrough"] = not self.active_formats.get("strikethrough", False)
                elif format_type == "subscript":
                    self.active_formats["subscript"] = not self.active_formats.get("subscript", False)
                elif format_type == "superscript":
                    self.active_formats["superscript"] = not self.active_formats.get("superscript", False)
            
            if format_type in ["bullet", "number", "letter", "roman"]:
                if format_type == "bullet":
                    self._insert_list_item("• ")
                elif format_type == "number":
                    self._insert_numbered_list()
                elif format_type == "letter":
                    self._insert_lettered_list()
                elif format_type == "roman":
                    self._insert_roman_list()
            
            # Update button states immediately after applying format
            self._update_button_states()
        except Exception as e:
            print(f"Error applying format: {e}")
    
    def _apply_size(self, value):
        """Apply text size to selected text"""
        try:
            size = int(value)
            font_name = self.font_var.get()
            self.text_editor.tag_add(f"size_{value}", "sel.first", "sel.last")
            self.text_editor.tag_configure(f"size_{value}", font=(font_name, size))
        except:
            pass
    
    def _apply_font(self, font_name):
        """Apply font family to selected text"""
        try:
            size = int(self.text_size_var.get())
            self.text_editor.tag_add(f"font_{font_name}", "sel.first", "sel.last")
            self.text_editor.tag_configure(f"font_{font_name}", font=(font_name, size))
        except:
            pass
    
    def _apply_alignment(self, alignment):
        """Apply text alignment to selected text"""
        try:
            # Remove existing alignment tags
            for align in ["left", "center", "right"]:
                self.text_editor.tag_remove(align, "sel.first", "sel.last")
            # Add new alignment
            self.text_editor.tag_add(alignment, "sel.first", "sel.last")
        except:
            pass
    
    def _apply_heading(self, heading):
        """Apply heading style to selected text"""
        try:
            # Remove existing heading tags
            for h in ["heading1", "heading2", "heading3"]:
                self.text_editor.tag_remove(h, "sel.first", "sel.last")
            # Add new heading
            if heading == "Heading 1":
                self.text_editor.tag_add("heading1", "sel.first", "sel.last")
            elif heading == "Heading 2":
                self.text_editor.tag_add("heading2", "sel.first", "sel.last")
            elif heading == "Heading 3":
                self.text_editor.tag_add("heading3", "sel.first", "sel.last")
        except:
            pass
    
    def _choose_text_color(self):
        """Open color picker for text color"""
        from tkinter import colorchooser
        try:
            color = colorchooser.askcolor(title="Choose Text Color")[1]
            if color:
                self.text_editor.tag_add(f"color_{color}", "sel.first", "sel.last")
                self.text_editor.tag_configure(f"color_{color}", foreground=color)
        except:
            pass
    
    def _choose_highlight_color(self):
        """Open color picker for highlight/background color"""
        from tkinter import colorchooser
        try:
            color = colorchooser.askcolor(title="Choose Highlight Color")[1]
            if color:
                self.text_editor.tag_add(f"bg_{color}", "sel.first", "sel.last")
                self.text_editor.tag_configure(f"bg_{color}", background=color)
        except:
            pass
    
    def _decrease_indent(self):
        """Decrease indentation of current line"""
        try:
            current_line = self.text_editor.index("insert").split(".")[0]
            line_text = self.text_editor.get(f"{current_line}.0", f"{current_line}.end")
            if line_text.startswith("    "):
                self.text_editor.delete(f"{current_line}.0", f"{current_line}.4")
            elif line_text.startswith("   "):
                self.text_editor.delete(f"{current_line}.0", f"{current_line}.3")
            elif line_text.startswith("  "):
                self.text_editor.delete(f"{current_line}.0", f"{current_line}.2")
            elif line_text.startswith(" "):
                self.text_editor.delete(f"{current_line}.0", f"{current_line}.1")
        except:
            pass
    
    def _increase_indent(self):
        """Increase indentation of current line"""
        try:
            current_line = self.text_editor.index("insert").split(".")[0]
            self.text_editor.insert(f"{current_line}.0", "    ")
        except:
            pass
    
    def _undo(self):
        """Undo last action"""
        try:
            self.text_editor.edit_undo()
        except:
            pass
    
    def _redo(self):
        """Redo last undone action"""
        try:
            self.text_editor.edit_redo()
        except:
            pass
    
    def _insert_lettered_list(self):
        """Insert a lettered list item with auto-increment like a word processor"""
        try:
            # Get current line number
            current_line = int(self.text_editor.index("insert").split(".")[0])
            
            # Check if the previous line is a lettered list item
            if current_line > 1:
                prev_line_text = self.text_editor.get(f"{current_line-1}.0", f"{current_line-1}.end")
                # Check if previous line starts with a letter followed by ". "
                import re
                match = re.match(r'^([a-z])\.\s', prev_line_text.strip())
                if match:
                    # Increment the letter
                    prev_letter = match.group(1)
                    next_letter = chr(ord(prev_letter) + 1)
                    self.text_editor.insert("insert", f"{next_letter}. ")
                    return
            
            # If not continuing a list, start from 'a'
            self.text_editor.insert("insert", "a. ")
        except:
            pass
    
    def _insert_roman_list(self):
        """Insert a roman numeral list item with auto-increment like a word processor"""
        try:
            # Get current line number
            current_line = int(self.text_editor.index("insert").split(".")[0])
            
            # Check if the previous line is a roman numeral list item
            if current_line > 1:
                prev_line_text = self.text_editor.get(f"{current_line-1}.0", f"{current_line-1}.end")
                # Check if previous line starts with a roman numeral followed by ". "
                import re
                match = re.match(r'^([ivxlcdm]+)\.\s', prev_line_text.strip())
                if match:
                    # Convert roman numeral to number, increment, then convert back
                    prev_roman = match.group(1)
                    prev_num = self._roman_to_int(prev_roman)
                    next_num = prev_num + 1
                    next_roman = self._int_to_roman(next_num)
                    self.text_editor.insert("insert", f"{next_roman}. ")
                    return
            
            # If not continuing a list, start from 'i'
            self.text_editor.insert("insert", "i. ")
        except:
            pass
    
    def _roman_to_int(self, roman):
        """Convert roman numeral to integer"""
        roman = roman.lower()
        roman_dict = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
        total = 0
        prev_value = 0
        for char in reversed(roman):
            value = roman_dict[char]
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        return total
    
    def _int_to_roman(self, num):
        """Convert integer to roman numeral"""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syb = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num.lower()
    
    def _handle_return_key(self, event):
        """Handle Return key to continue numbered/lettered/roman lists"""
        try:
            # Get current line number
            current_line = int(self.text_editor.index("insert").split(".")[0])
            
            # Get current line text
            current_line_text = self.text_editor.get(f"{current_line}.0", f"{current_line}.end")
            
            # Check if current line is a list item
            import re
            
            # Check for numbered list (e.g., "1. ")
            num_match = re.match(r'^(\d+)\.\s', current_line_text.strip())
            if num_match:
                # Insert newline first
                self.text_editor.insert("insert", "\n")
                # Increment the number
                prev_num = int(num_match.group(1))
                next_num = prev_num + 1
                self.text_editor.insert("insert", f"{next_num}. ")
                return "break"  # Prevent default behavior
            
            # Check for lettered list (e.g., "a. ")
            letter_match = re.match(r'^([a-z])\.\s', current_line_text.strip())
            if letter_match:
                # Insert newline first
                self.text_editor.insert("insert", "\n")
                # Increment the letter
                prev_letter = letter_match.group(1)
                next_letter = chr(ord(prev_letter) + 1)
                self.text_editor.insert("insert", f"{next_letter}. ")
                return "break"  # Prevent default behavior
            
            # Check for roman numeral list (e.g., "i. ")
            roman_match = re.match(r'^([ivxlcdm]+)\.\s', current_line_text.strip())
            if roman_match:
                # Insert newline first
                self.text_editor.insert("insert", "\n")
                # Convert roman numeral to number, increment, then convert back
                prev_roman = roman_match.group(1)
                prev_num = self._roman_to_int(prev_roman)
                next_num = prev_num + 1
                next_roman = self._int_to_roman(next_num)
                self.text_editor.insert("insert", f"{next_roman}. ")
                return "break"  # Prevent default behavior
            
            # If not a list item, allow default behavior
            return None
        except:
            return None
    
    def _update_button_states(self, event=None):
        """Update button highlighting based on current formatting at cursor or active formats"""
        try:
            # Check if buttons exist
            if not hasattr(self, 'bold_btn') or not hasattr(self, 'italic_btn') or not hasattr(self, 'underline_btn'):
                return
            
            # Get current tags at cursor position
            try:
                if self.text_editor.tag_ranges("sel"):
                    # If text is selected, check tags at selection start
                    current_tags = self.text_editor.tag_names("sel.first")
                else:
                    # If no selection, check tags at cursor position
                    current_tags = self.text_editor.tag_names("insert")
            except Exception as e:
                current_tags = self.text_editor.tag_names("insert")
            
            # Update bold button - check both current tags and active formats
            if "bold" in current_tags or self.active_formats.get("bold", False):
                self.bold_btn.configure(fg_color="#3498db", text_color="white")
            else:
                self.bold_btn.configure(fg_color="white", text_color="#2c3e50")
            
            # Update italic button - check both current tags and active formats
            if "italic" in current_tags or self.active_formats.get("italic", False):
                self.italic_btn.configure(fg_color="#3498db", text_color="white")
            else:
                self.italic_btn.configure(fg_color="white", text_color="#2c3e50")
            
            # Update underline button - check both current tags and active formats
            if "underline" in current_tags or self.active_formats.get("underline", False):
                self.underline_btn.configure(fg_color="#3498db", text_color="white")
            else:
                self.underline_btn.configure(fg_color="white", text_color="#2c3e50")
        except Exception as e:
            pass
    
    def _apply_active_formatting(self, event):
        """Apply active formatting to newly typed text"""
        try:
            # Only apply formatting for regular character keys (not control keys)
            if event.keysym in ['Return', 'Tab', 'BackSpace', 'Delete', 'Escape', 'Control_L', 'Control_R', 
                               'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 
                               'F7', 'F8', 'F9', 'F10', 'F11', 'F12']:
                return None
            
            # Get the current insert position before the character is inserted
            insert_pos = self.text_editor.index("insert")
            
            # Schedule formatting application after the character is inserted
            def apply_after_insert():
                try:
                    # Get the position after the character was inserted
                    new_insert_pos = self.text_editor.index("insert")
                    # Apply tags to the newly inserted character
                    if self.active_formats.get("bold", False):
                        self.text_editor.tag_add("bold", insert_pos, new_insert_pos)
                    if self.active_formats.get("italic", False):
                        self.text_editor.tag_add("italic", insert_pos, new_insert_pos)
                    if self.active_formats.get("underline", False):
                        self.text_editor.tag_add("underline", insert_pos, new_insert_pos)
                    if self.active_formats.get("strikethrough", False):
                        self.text_editor.tag_add("strikethrough", insert_pos, new_insert_pos)
                    if self.active_formats.get("subscript", False):
                        self.text_editor.tag_add("subscript", insert_pos, new_insert_pos)
                    if self.active_formats.get("superscript", False):
                        self.text_editor.tag_add("superscript", insert_pos, new_insert_pos)
                except Exception as e:
                    print(f"Error in apply_after_insert: {e}")
            
            # Schedule the formatting application after the character is inserted
            self.after(1, apply_after_insert)
            
            return None
        except Exception as e:
            print(f"Error applying active formatting: {e}")
            return None
    
    def _insert_list_item(self, bullet):
        """Insert a bullet list item"""
        try:
            self.text_editor.insert("insert", bullet + " ")
        except:
            pass
    
    def _insert_numbered_list(self):
        """Insert a numbered list item with auto-increment like a word processor"""
        try:
            # Get current line number
            current_line = int(self.text_editor.index("insert").split(".")[0])
            
            # Check if the previous line is a numbered list item
            if current_line > 1:
                prev_line_text = self.text_editor.get(f"{current_line-1}.0", f"{current_line-1}.end")
                # Check if previous line starts with a number followed by ". "
                import re
                match = re.match(r'^(\d+)\.\s', prev_line_text.strip())
                if match:
                    # Increment the number
                    prev_num = int(match.group(1))
                    next_num = prev_num + 1
                    self.text_editor.insert("insert", f"{next_num}. ")
                    return
            
            # If not continuing a list, start from 1
            self.text_editor.insert("insert", "1. ")
        except:
            pass
    
    def _choose_attachment(self):
        """Open file dialog to choose attachment"""
        file_path = filedialog.askopenfilename(
            title="Select Attachment",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Image files", "*.png *.jpg *.jpeg *.gif"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.attachment_path = file_path
            filename = os.path.basename(file_path)
            self.attachment_label.configure(text=f"📎 {filename}")
    
    def _save_draft(self):
        """Save the circular as a draft"""
        subject = self.subject_entry.get()
        body = self.text_editor.get("1.0", "end-1c")
        
        if not subject and not body:
            messagebox.showwarning("Draft Warning", "Please add a subject or body before saving.")
            return
        
        try:
            # Save to database
            self._save_to_database(subject, body, draft=True)
            messagebox.showinfo("Draft Saved", "Circular saved as draft successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save draft: {e}")
    
    def _print_pdf_circular(self):
        """Generate and print PDF circular with school letterhead"""
        subject = self.subject_entry.get()
        body = self.text_editor.get("1.0", "end-1c")
        
        if not subject:
            messagebox.showwarning("Missing Subject", "Please enter a subject for the circular.")
            return
        
        if not body:
            messagebox.showwarning("Missing Body", "Please write the circular content.")
            return
        
        try:
            # Generate PDF
            pdf_path = self._generate_pdf(subject, body)
            
            # Open file dialog to save/print
            save_path = filedialog.asksaveasfilename(
                title="Save PDF Circular",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"circular_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            
            if save_path:
                import shutil
                shutil.copy2(pdf_path, save_path)
                messagebox.showinfo("PDF Generated", f"Circular PDF saved to:\n{save_path}")
                
                # Optionally open the PDF
                try:
                    os.startfile(save_path)
                except:
                    pass
            
            # Clean up temp file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not generate PDF: {e}")
    
    def _publish_to_portal(self):
        """Publish circular to parent portal and trigger notifications"""
        subject = self.subject_entry.get()
        body = self.text_editor.get("1.0", "end-1c")
        
        if not subject:
            messagebox.showwarning("Missing Subject", "Please enter a subject for the circular.")
            return
        
        if not body:
            messagebox.showwarning("Missing Body", "Please write the circular content.")
            return
        
        if not self.sms_var.get():
            messagebox.showwarning("Delivery Method", "SMS notification is required when sending to portal.")
            return
        
        try:
            # Save to newsletters table
            self._save_to_database(subject, body, draft=False)
            
            # Publish to portal_announcements table
            self._publish_to_portal_database(subject, body)
            
            # Trigger background SMS notification task
            if self.sms_var.get():
                self._queue_sms_notifications()
            
            # Sync to cloud
            self._sync_to_cloud(subject, body)
            
            messagebox.showinfo(
                "Published Successfully", 
                "Circular published to Parent Portal!\n\n"
                "Parents can now view it in their portal app.\n"
                "SMS notifications have been queued."
            )
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Publish Error", f"Could not publish to portal: {e}")
    
    def _sync_to_cloud(self, subject, body):
        """Sync newsletter to cloud portal"""
        try:
            # Get cloud credentials
            credentials = ask_cloud_credentials(self)
            if not credentials:
                print("Cloud sync cancelled - no credentials provided")
                return
            
            # Prepare newsletter data
            newsletter_data = {
                "subject": subject,
                "body": body,
                "target_type": self.target_type_var.get(),
                "class_context": self.class_context_var.get(),
                "recipient_role": self.recipient_role_var.get(),
                "attachment_path": self.attachment_path,
                "send_email": 0,  # Email is no longer supported
                "send_sms": 1 if self.sms_var.get() else 0
            }
            
            # Sync to cloud
            cloud_service = CloudService()
            result = cloud_service.sync_newsletter(newsletter_data, credentials)
            
            if result.get("success"):
                print(f"Newsletter synced to cloud successfully: {result.get('message')}")
            else:
                error_msg = result.get('message', 'Unknown error')
                print(f"Cloud sync failed: {error_msg}")
                # Show error to user if it's a credentials issue
                if "Invalid username or password" in error_msg or "School not found" in error_msg:
                    from tkinter import messagebox
                    messagebox.showerror("Cloud Sync Failed", f"Wrong cloud credentials!\n\n{error_msg}")
                else:
                    # Don't show other errors to user since local save succeeded
                    pass
                
        except Exception as e:
            print(f"Error syncing to cloud: {e}")
            # Don't show error to user since local save succeeded
    
    def _save_to_database(self, subject, body, draft=True):
        """Save circular to database"""
        try:
            # Create newsletters table if it doesn't exist
            self.db._cursor.execute("""
                CREATE TABLE IF NOT EXISTS newsletters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    target_type TEXT,
                    class_context TEXT,
                    recipient_role TEXT,
                    attachment_path TEXT,
                    send_email INTEGER DEFAULT 0,
                    send_sms INTEGER DEFAULT 0,
                    is_draft INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP
                )
            """)
            
            # Insert the newsletter
            self.db._cursor.execute("""
                INSERT INTO newsletters (
                    subject, body, target_type, class_context, recipient_role,
                    attachment_path, send_email, send_sms, is_draft, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subject,
                body,
                self.target_type_var.get(),
                self.class_context_var.get(),
                self.recipient_role_var.get(),
                self.attachment_path,
                0,  # Email is no longer supported
                1 if self.sms_var.get() else 0,
                1 if draft else 0,
                None if draft else "CURRENT_TIMESTAMP"
            ))
            
            self.db.conn.commit()
            
        except Exception as e:
            self.db.conn.rollback()
            raise e
    
    def _load_school_config(self):
        """Load school configuration for letterhead"""
        try:
            current_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(current_dir, "school_config.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading school config: {e}")
        return {}
    
    def _generate_pdf(self, subject, body):
        """Generate PDF with school letterhead using ReportLab"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Create temp PDF file
            temp_dir = os.path.dirname(os.path.realpath(__file__))
            pdf_path = os.path.join(temp_dir, f"temp_circular_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)
            
            story = []
            styles = getSampleStyleSheet()
            
            # Load school config
            school_config = self._load_school_config()
            school_name = school_config.get("school_name", "School Name")
            school_address = school_config.get("address", "School Address")
            school_phone = school_config.get("contacts", "")
            paybill = school_config.get("paybill", "")
            term_dates = school_config.get("term_dates", "")
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.darkblue,
                alignment=1,  # Center
                spaceAfter=12
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.black,
                alignment=1,  # Center
                spaceAfter=6
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                alignment=0,  # Left
                spaceAfter=12,
                leading=14
            )
            
            # School letterhead
            story.append(Paragraph(school_name.upper(), title_style))
            story.append(Paragraph(school_address, header_style))
            if school_phone:
                story.append(Paragraph(f"Tel: {school_phone}", header_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Date
            date_str = datetime.now().strftime("%d %B, %Y")
            story.append(Paragraph(f"<b>Date:</b> {date_str}", body_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Subject
            story.append(Paragraph(f"<b>SUBJECT:</b> {subject.upper()}", body_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Body text (convert newlines to <br/>)
            body_html = body.replace('\n', '<br/>')
            story.append(Paragraph(body_html, body_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Footer with school info
            if paybill or term_dates:
                footer_text = ""
                if paybill:
                    footer_text += f"<b>Paybill Number:</b> {paybill}<br/>"
                if term_dates:
                    footer_text += f"<b>Term Dates:</b> {term_dates}"
                
                story.append(Paragraph(footer_text, body_style))
            
            story.append(Spacer(1, 0.5*inch))
            
            # Signature block
            story.append(Paragraph("<b>_____________________</b>", body_style))
            story.append(Paragraph("<i>Principal / Head Teacher</i>", body_style))
            
            # Build PDF
            doc.build(story)
            
            return pdf_path
            
        except ImportError:
            # Fallback if ReportLab is not installed
            raise Exception("ReportLab library not installed. Please install it with: pip install reportlab")
        except Exception as e:
            raise e
    
    def _publish_to_portal_database(self, subject, body):
        """Insert circular into portal_announcements table"""
        try:
            # Create portal_announcements table if it doesn't exist
            self.db._cursor.execute("""
                CREATE TABLE IF NOT EXISTS portal_announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    newsletter_id INTEGER,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    target_type TEXT,
                    class_context TEXT,
                    recipient_role TEXT,
                    attachment_path TEXT,
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (newsletter_id) REFERENCES newsletters(id)
                )
            """)
            
            # Get the newsletter_id from the last insert
            self.db._cursor.execute("SELECT last_insert_rowid()")
            newsletter_id = self.db._cursor.fetchone()[0]
            
            # Get target class IDs based on selection
            target_class_ids = self._get_target_class_ids()
            
            # Insert into portal_announcements
            self.db._cursor.execute("""
                INSERT INTO portal_announcements (
                    newsletter_id, subject, body, target_type, 
                    class_context, recipient_role, attachment_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                newsletter_id,
                subject,
                body,
                self.target_type_var.get(),
                self.class_context_var.get(),
                self.recipient_role_var.get(),
                self.attachment_path
            ))
            
            # Get the portal_announcement_id
            self.db._cursor.execute("SELECT last_insert_rowid()")
            announcement_id = self.db._cursor.fetchone()[0]
            
            # Link announcement to target classes
            if target_class_ids:
                self._link_announcement_to_classes(announcement_id, target_class_ids)
            
            # Create notification entries for all students in target classes
            self._create_notification_entries(announcement_id, target_class_ids, 'newsletter')
            
            self.db.conn.commit()
            
        except Exception as e:
            self.db.conn.rollback()
            raise e
    
    def _get_target_class_ids(self):
        """Get class IDs based on audience selection"""
        try:
            target_type = self.target_type_var.get()
            class_context = self.class_context_var.get()
            
            if target_type == "All School" or class_context == "All Classes":
                # Return all class IDs
                self.db._cursor.execute("SELECT DISTINCT grade FROM students WHERE grade IS NOT NULL")
                return [row[0] for row in self.db._cursor.fetchall()]
            elif target_type == "Individual Student":
                # For individual student, return the class but we'll handle student filtering separately
                return [class_context]
            elif target_type == "By Stream":
                # For stream, return the class but we'll handle stream filtering separately
                return [class_context]
            else:
                # Return specific class ID
                return [class_context]
                
        except Exception as e:
            print(f"Error getting target class IDs: {e}")
            return []
    
    def _link_announcement_to_classes(self, announcement_id, class_ids):
        """Link announcement to target classes in junction table"""
        try:
            # Create junction table if it doesn't exist
            self.db._cursor.execute("""
                CREATE TABLE IF NOT EXISTS announcement_class_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    announcement_id INTEGER,
                    class_name TEXT,
                    FOREIGN KEY (announcement_id) REFERENCES portal_announcements(id)
                )
            """)
            
            # Insert links
            for class_name in class_ids:
                self.db._cursor.execute("""
                    INSERT INTO announcement_class_links (announcement_id, class_name)
                    VALUES (?, ?)
                """, (announcement_id, class_name))
                
        except Exception as e:
            print(f"Error linking announcement to classes: {e}")
    
    def _queue_email_notifications(self):
        """Queue email notifications for background processing"""
        try:
            # Create email_queue table if it doesn't exist
            self.db._cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    newsletter_id INTEGER,
                    recipient_email TEXT,
                    subject TEXT,
                    body TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (newsletter_id) REFERENCES newsletters(id)
                )
            """)
            
            # Get newsletter_id from last insert
            self.db._cursor.execute("SELECT last_insert_rowid()")
            newsletter_id = self.db._cursor.fetchone()[0]
            
            # Get recipient emails based on selection
            recipients = self._get_recipient_emails()
            subject = self.subject_entry.get()
            body = self.text_editor.get("1.0", "end-1c")
            
            # Queue emails
            for email in recipients:
                self.db._cursor.execute("""
                    INSERT INTO email_queue (newsletter_id, recipient_email, subject, body)
                    VALUES (?, ?, ?, ?)
                """, (newsletter_id, email, subject, body))
            
            self.db.conn.commit()
            print(f"Queued {len(recipients)} email notifications")
            
        except Exception as e:
            print(f"Error queuing email notifications: {e}")
    
    def _queue_sms_notifications(self):
        """Queue SMS notifications for background processing"""
        try:
            # Create sms_queue table if it doesn't exist
            self.db._cursor.execute("""
                CREATE TABLE IF NOT EXISTS sms_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    newsletter_id INTEGER,
                    recipient_phone TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (newsletter_id) REFERENCES newsletters(id)
                )
            """)
            
            # Get newsletter_id from last insert
            self.db._cursor.execute("SELECT last_insert_rowid()")
            newsletter_id = self.db._cursor.fetchone()[0]
            
            # Get recipient phone numbers based on selection
            recipients = self._get_recipient_phones()
            subject = self.subject_entry.get()
            body = self.text_editor.get("1.0", "end-1c")
            
            # Create SMS message (truncate if needed)
            sms_message = f"{subject}: {body[:100]}..." if len(body) > 100 else f"{subject}: {body}"
            
            # Queue SMS
            for phone in recipients:
                self.db._cursor.execute("""
                    INSERT INTO sms_queue (newsletter_id, recipient_phone, message)
                    VALUES (?, ?, ?)
                """, (newsletter_id, phone, sms_message))
            
            self.db.conn.commit()
            print(f"Queued {len(recipients)} SMS notifications")
            
        except Exception as e:
            print(f"Error queuing SMS notifications: {e}")
    
    def _get_recipient_emails(self):
        """Get recipient email addresses based on audience selection"""
        try:
            target_type = self.target_type_var.get()
            class_context = self.class_context_var.get()
            recipient_role = self.recipient_role_var.get()
            
            query = "SELECT DISTINCT phone FROM students WHERE phone IS NOT NULL AND phone != ''"
            params = []
            
            if target_type == "Individual Student":
                # Get phone for specific student
                query = "SELECT phone FROM students WHERE name = ? AND grade = ?"
                params = [recipient_role, class_context]
            elif target_type == "By Stream":
                # Get phones for students in specific stream
                query = "SELECT DISTINCT phone FROM students WHERE grade = ? AND stream = ? AND phone IS NOT NULL AND phone != ''"
                params = [class_context, recipient_role]
            elif target_type != "All School" and class_context != "All Classes":
                query += " AND grade = ?"
                params.append(class_context)
            
            self.db._cursor.execute(query, params)
            return [row[0] for row in self.db._cursor.fetchall() if row[0]]
            
        except Exception as e:
            print(f"Error getting recipient emails: {e}")
            return []
    
    def _get_recipient_phones(self):
        """Get recipient phone numbers based on audience selection"""
        try:
            target_type = self.target_type_var.get()
            class_context = self.class_context_var.get()
            recipient_role = self.recipient_role_var.get()
            
            query = "SELECT DISTINCT phone FROM students WHERE phone IS NOT NULL AND phone != ''"
            params = []
            
            if target_type == "Individual Student":
                # Get phone for specific student
                query = "SELECT phone FROM students WHERE name = ? AND grade = ?"
                params = [recipient_role, class_context]
            elif target_type == "By Stream":
                # Get phones for students in specific stream
                query = "SELECT DISTINCT phone FROM students WHERE grade = ? AND stream = ? AND phone IS NOT NULL AND phone != ''"
                params = [class_context, recipient_role]
            elif target_type != "All School" and class_context != "All Classes":
                query += " AND grade = ?"
                params.append(class_context)
            
            self.db._cursor.execute(query, params)
            return [row[0] for row in self.db._cursor.fetchall() if row[0]]
            
        except Exception as e:
            print(f"Error getting recipient phones: {e}")
            return []
    
    def _create_notification_entries(self, content_id, class_ids, content_type):
        """Create notification entries for all students in target classes"""
        try:
            # Create parent_view_status table if it doesn't exist
            self.db._cursor.execute("""
                CREATE TABLE IF NOT EXISTS parent_view_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    content_type TEXT NOT NULL,
                    content_id INTEGER NOT NULL,
                    has_viewed INTEGER DEFAULT 0,
                    viewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(student_id, content_type, content_id),
                    FOREIGN KEY(student_id) REFERENCES students(id)
                )
            """)
            
            # Handle individual student case
            if self.target_type_var.get() == "Individual Student":
                # Get the specific student ID
                student_name = self.recipient_role_var.get()
                class_context = self.class_context_var.get()
                
                self.db._cursor.execute(
                    "SELECT id FROM students WHERE name = ? AND grade = ?",
                    (student_name, class_context)
                )
                student_row = self.db._cursor.fetchone()
                
                if student_row:
                    student_ids = [student_row[0]]
                else:
                    student_ids = []
            elif self.target_type_var.get() == "By Stream":
                # Get students in specific stream
                stream_name = self.recipient_role_var.get()
                class_context = self.class_context_var.get()
                
                self.db._cursor.execute(
                    "SELECT id FROM students WHERE grade = ? AND stream = ?",
                    (class_context, stream_name)
                )
                student_ids = [row[0] for row in self.db._cursor.fetchall()]
            elif "All Classes" in class_ids or len(class_ids) == 0:
                # Get all students
                self.db._cursor.execute("SELECT id FROM students")
                student_ids = [row[0] for row in self.db._cursor.fetchall()]
            else:
                # Get students in specific classes
                student_ids = []
                for class_name in class_ids:
                    self.db._cursor.execute("SELECT id FROM students WHERE grade = ?", (class_name,))
                    student_ids.extend([row[0] for row in self.db._cursor.fetchall()])
            
            # Create notification entries for each student
            for student_id in student_ids:
                try:
                    self.db._cursor.execute("""
                        INSERT OR IGNORE INTO parent_view_status (student_id, content_type, content_id, has_viewed)
                        VALUES (?, ?, ?, 0)
                    """, (student_id, content_type, content_id))
                except Exception as e:
                    print(f"Error creating notification for student {student_id}: {e}")
            
            print(f"Created {len(student_ids)} notification entries for {content_type} {content_id}")
            
        except Exception as e:
            print(f"Error creating notification entries: {e}")
