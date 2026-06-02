from ui_marksheet_junior import JuniorMarkSheetView # Import the new workshop file
from ui_marksheet_primary import PrimaryMarkSheetView # For Grade 4-6
from ui_marksheet_playgroup import PlaygroupMarkSheetView
from ui_marksheet_pp1 import PP1MarkSheetView
from ui_marksheet_pp2 import PP2MarkSheetView
from ui_marksheet_lower import LowerMarkSheetView
from ui_summary import ClassSummaryView
from teachers_linked import TeachersLinkedView
from reportforms import ReportFormsView
import os
import sys
import json
import webbrowser
import customtkinter as ctk
from tkinter import messagebox
from database import FreemanDB  # Ensure database.py is in the same folder
from PIL import Image
from wizard import SchoolSetupWizard
import network_manager
from cloud_service import CloudService, ask_cloud_credentials

class Dashboard(ctk.CTk):
    def __init__(self, school_name_placeholder="Freeman Tech Solutions (Demo)"):
        super().__init__()

        self.db = FreemanDB()

        # --- ADD THESE TWO LINES HERE ---
        self.search_var = ctk.StringVar()
        self.all_student_rows = []
        self.portal_open = self.load_portal_state()  # Track portal state from config
        # --------------------------------

        self.overrideredirect(True)

        screen_width = self.winfo_screenwidth()
        
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # --- 1. WINDOW CONFIGURATION & CENTERING ---
        self.title("Freeman Tech Solutions - Home Page")
        
        # Dashboard is usually bigger (like 1100x700). We will center it.
        window_width = 1100
        window_height = 700
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        # This makes the window take up the entire screen
    
        # --- 1. ASSET PATHS ---
        current_dir = os.path.dirname(os.path.realpath(__file__))
        bg_image_path = os.path.join(current_dir, "assets", "dashboard_bg.jpg")

       # --- THE BACKGROUND IMAGE WITH DIAGONAL WATERMARK ---
        try:
            # This gets the actual width and height of the laptop screen
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            bg_raw = Image.open(bg_image_path).resize((screen_width, screen_height))
            
            # Add diagonal watermark text
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(bg_raw)
            watermark_text = "FREEMAN TECH SOLUTIONS"
            try:
                # Try to use a larger bold font if available
                font = ImageFont.truetype("arial.ttf", 120)
            except:
                font = ImageFont.load_default()
            
            # Draw diagonal text (45 degrees)
            text_color = (100, 100, 100, 80)  # Semi-transparent gray
            draw.text((screen_width // 3, screen_height // 2 - 100), watermark_text, 
                     fill=(100, 100, 100), font=font)
            
            # Rotate the watermark for diagonal effect
            watermark = Image.new('RGBA', (screen_width, screen_height), (0, 0, 0, 0))
            watermark_draw = ImageDraw.Draw(watermark)
            watermark_draw.text((50, screen_height // 2), watermark_text, 
                               fill=(100, 100, 100, 60), font=font)
            watermark_rotated = watermark.rotate(-45, expand=False)
            bg_raw.paste(watermark_rotated, (0, 0), watermark_rotated)
            
            bg_img = ctk.CTkImage(bg_raw, size=(screen_width, screen_height))
            
            self.bg_label = ctk.CTkLabel(self, image=bg_img, text="")
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Background image error: {e}")

# Optional: If you want to allow the user to exit fullscreen with the 'Esc' key
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # Use the name passed from the login (or default placeholder for now)
        self.dynamic_school_name = school_name_placeholder

        # --- 2. LAYOUT DESIGN ---
        # Column 0: Vertical Button Menu (Left Side)
        # Column 1: Main Content Area (Right Side, for future dynamic content)
        self.grid_columnconfigure(0, weight=0, minsize=250) # Menu stays fixed size
        self.grid_columnconfigure(1, weight=1) # Content area expands
        self.grid_rowconfigure(0, weight=1)

        # --- 3. MENU PANEL (Vertical Buttons) ---
        # This matches the boxes you drew on the left
        self.menu_panel = ctk.CTkFrame(self, corner_radius=0,border_width=1,border_color="grey")
        self.menu_panel.grid(row=0, column=0, sticky="nsew")


        # Top Title/Brand in Menu
        self.brand_label = ctk.CTkLabel(self.menu_panel, text="Freeman OS", font=("Arial Bold", 20))
        self.brand_label.pack(pady=(30, 20))

        # --- CREATE BUTTONS FROM YOUR DRAWING ---
        btn_width = 155 # Standardizing button size for neatness
        btn_height = 40
        btn_pady = 8 # Space between them

        # Placeholder text, to be replaced by icons later
        self.btn_register = ctk.CTkButton(self.menu_panel, text="Register Students", width=btn_width, height=btn_height, command=lambda: self.show_class_selection("Registration", self.btn_register))
        self.btn_register.pack(pady=btn_pady)

        self.btn_mark_sheets = ctk.CTkButton(self.menu_panel, text="View Mark Sheets", width=btn_width, height=btn_height, command=lambda: self.show_class_selection("Mark Sheets", self.btn_mark_sheets))
        self.btn_mark_sheets.pack(pady=btn_pady)

        self.btn_previous_exams = ctk.CTkButton(self.menu_panel, text="Previous Exams", width=btn_width, height=btn_height, command=lambda: self.show_class_selection("Previous Exams", self.btn_previous_exams))
        self.btn_previous_exams.pack(pady=btn_pady)

        self.btn_summary = ctk.CTkButton(self.menu_panel, text="Student Marks Summary", width=btn_width, height=btn_height, command=lambda: self.show_class_selection("Summary", self.btn_summary))
        self.btn_summary.pack(pady=btn_pady)

        self.btn_teachers = ctk.CTkButton(self.menu_panel, text="Teachers Linked", width=btn_width, height=btn_height, command=lambda: self.show_class_selection("Teachers", self.btn_teachers))
        self.btn_teachers.pack(pady=btn_pady)

        self.btn_report_forms = ctk.CTkButton(self.menu_panel, text="View Report Forms", width=btn_width, height=btn_height, command=self.open_report_forms)
        self.btn_report_forms.pack(pady=btn_pady)

        # Spacer/Fill (This pushes the Exit button to the bottom)
        self.menu_spacer = ctk.CTkLabel(self.menu_panel, text="")
        self.menu_spacer.pack(expand=True, fill="y")

        # For the Register button:
        self.btn_register.configure(
             command=lambda: self.show_class_selection("Registering", self.btn_register)
               )

# For the Mark Sheets button:
        self.btn_mark_sheets.configure(
             command=lambda: self.show_class_selection("Viewing Marks", self.btn_mark_sheets)
             )

        # Add this at the end of your __init__ section
        self.sidebar_buttons = [
        self.btn_register,
        self.btn_mark_sheets,
        self.btn_previous_exams,
        self.btn_summary,
        self.btn_teachers,
        self.btn_report_forms
        ]
        # Inside your Home/Dashboard Class
        self.setup_btn = ctk.CTkButton(
            self.menu_panel, 
            text="⚙️ Setup School Branding", 
            command=self.open_wizard,
            fg_color="#34495e",
            hover_color="#2c3e50",
            height=45,
            font=("Arial Bold", 14)
        )
        self.setup_btn.pack(pady=(0, 30))
        self.btn_portal = ctk.CTkButton(
            self.menu_panel,
            text="📡 Launch Teacher Portal",
            command=self.handle_portal_button,
            fg_color="green",
            width=btn_width,
            height=btn_height
        )
        self.btn_portal.pack(pady=10)
        self.update_portal_button()  # Set initial button state based on loaded config

        self.btn_cloud_sync = ctk.CTkButton(
            self.menu_panel,
            text="🔄 Sync Students Cloud",
            command=self.handle_cloud_sync_button,
            fg_color="#1f538d",
            hover_color="#153d66",
            width=btn_width,
            height=btn_height
        )
        self.btn_cloud_sync.pack(pady=10)

        # Exit Button at the bottom
        self.btn_exit = ctk.CTkButton(self.menu_panel, text="Exit", width=btn_width, height=btn_height, 
                                      fg_color="#e74c3c", hover_color="#c0392b", # Red for Exit
                                      command=self.exit_app)
        self.btn_exit.pack(pady=(0, 30))


        # --- 4. MAIN CONTENT PANEL ---
        self.content_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.content_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)


        # Row 0 of Content: Top Header (School Name / Homepage Title)
        # matches the top-right corner of your drawing
        self.header_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(10, 20))
        
        # School Name [DYNAMIC]
        self.school_title_label = ctk.CTkLabel(self.header_frame, text=self.dynamic_school_name, font=("Arial Bold", 26))
        self.school_title_label.pack(side="left", padx=10)
        
        # "Homepage" title
        self.page_title_label = ctk.CTkLabel(self.header_frame, text="/ HOMEPAGE", font=("Arial Italic", 14), text_color="gray")
        self.page_title_label.pack(side="left", anchor="sw", padx=(0, 20), pady=(0, 5))

       

        # Row 1 of Content: Future Workspace (Currently blank, can be used for summary stats later)
        self.work_area_label = ctk.CTkLabel(self.content_panel, text="Dashboard Workspace initialized.\nClick a menu button on the left to begin.", 
                                              font=("Arial", 16), text_color="gray60")
        self.work_area_label.pack(expand=True)


        # --- 5. THE THEME/MODE TOGGLE (Bottom right of content) ---
        # Dark mode | Light mode toggle buttons from your drawing
        self.theme_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        self.theme_frame.pack(side="bottom", anchor="se", pady=(20, 0))

        # We will use a segmented button for a clean 'switch' look
        self.theme_toggle = ctk.CTkSegmentedButton(self.theme_frame, 
                                                   values=["Light Mode", "Dark Mode"],
                                                   command=self.change_theme_event)
        
        # Match current system setting (usually Dark)
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Light":
            self.theme_toggle.set("Light Mode")
        else:
            self.theme_toggle.set("Dark Mode")
            
        self.theme_toggle.pack()
        # --- ADD THIS INSIDE YOUR DashboardApp CLASS ---

        self.all_student_rows = []
    
    def open_wizard(self):
    # This calls the class we created in the previous step
         SchoolSetupWizard(self, self.db)

    def open_report_forms(self):
        # Use the existing class selection method
        self.show_class_selection("Report Forms", self.btn_report_forms)
    def load_school_name(self):
        try:
            current_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(current_dir, 'school_config.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    config = json.load(f)
                    name = config.get('school_name', '')
                    return name.strip() if isinstance(name, str) and name.strip() else 'Freeman'
        except Exception:
            pass
        return 'Freeman'

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

    def load_portal_state(self):
        """Load portal state from config file"""
        try:
            config = self.load_school_config()
            return config.get('portal_open', False)
        except Exception:
            return False

    def save_portal_state(self, state):
        """Save portal state to config file"""
        try:
            self.save_school_config({'portal_open': state})
        except Exception as e:
            print(f'Unable to save portal state: {e}')

    def save_school_config(self, updates):
        try:
            current_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(current_dir, 'school_config.json')
            config = self.load_school_config()
            config.update(updates)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f'Unable to save school config: {e}')

    def get_local_student_list(self):
        try:
            self.db._cursor.execute('SELECT adm_no, name, grade, gender, phone, photo, stream FROM students ORDER BY grade, adm_no')
            rows = self.db._cursor.fetchall()
            return [
                {
                    'adm_no': row[0] or '',
                    'name': row[1] or '',
                    'grade': row[2] or '',
                    'gender': row[3] or '',
                    'phone': row[4] or '',
                    'photo': row[5] if len(row) > 5 else None,
                    'stream': row[6] if len(row) > 6 else 'None'
                }
                for row in rows if row[0] and row[1]
            ]
        except Exception as e:
            print(f'Error reading local students: {e}')
            return []

    def get_local_teacher_list(self):
        try:
            teachers = self.db.get_all_teachers()
            return [
                {
                    'class_name': row[0] or '',
                    'subject': row[1] or '',
                    'teacher_name': row[2] or '',
                    'teacher_code': row[3] or ''
                }
                for row in teachers if row[0] and row[1] and row[2] and row[3]
            ]
        except Exception as e:
            print(f'Error reading local teachers: {e}')
            return []

    def sync_students_to_cloud(self, credentials):
        students = self.get_local_student_list()
        if not students:
            messagebox.showinfo('Cloud Sync', 'No local students found to sync.')
            return False

        # Load school details from config
        school_details = {}
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    logo_path = config.get("logo", "")
                    # Convert logo to base64 if it's a local file
                    school_logo = self.image_to_base64(logo_path) if logo_path else ""
                    school_details = {
                        "school_name": config.get("school_name", ""),
                        "school_address": config.get("address", ""),
                        "school_telephone": config.get("contacts", ""),
                        "school_logo": school_logo
                    }
        except Exception as e:
            print(f"Error loading school config: {e}")

        # Convert student photos to base64 if they are local files
        for student in students:
            if student.get('photo'):
                student['photo'] = self.image_to_base64(student['photo'])

        service = CloudService()
        result = service.sync_students(students, credentials, school_details)
        if not result.get('success'):
            messagebox.showerror('Cloud Sync Failed', result.get('message', 'Could not sync students to cloud.'))
            return False

        messagebox.showinfo('Cloud Sync', f"Uploaded {len(students)} local students to cloud portal.")
        return True

    def image_to_base64(self, image_path):
        """Convert an image file to base64 string with data URI prefix"""
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            with open(image_path, "rb") as image_file:
                import base64
                # Get file extension to determine MIME type
                ext = os.path.splitext(image_path)[1].lower()
                mime_type = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp'
                }.get(ext, 'image/png')
                
                base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None

    def sync_teachers_to_cloud(self, credentials):
        teachers = self.get_local_teacher_list()
        if not teachers:
            messagebox.showinfo('Cloud Sync', 'No local teachers found to sync.')
            return False

        service = CloudService()
        result = service.sync_teachers(teachers, credentials)
        if not result.get('success'):
            messagebox.showerror('Cloud Sync Failed', result.get('message', 'Could not sync teachers to cloud.'))
            return False

        messagebox.showinfo('Cloud Sync', f"Uploaded {len(teachers)} local teachers to cloud portal.")
        return True

    def handle_portal_button(self):
        cloud_config = self.load_school_config()
        cloud_url = cloud_config.get('cloud_portal_url', '').strip()
        cloud_school_code = cloud_config.get('cloud_school_code', '').strip()
        cloud_teacher_username = cloud_config.get('cloud_teacher_username', '').strip()

        # Toggle portal state
        if not self.portal_open:
            # Launch portal
            school = self.load_school_name()
            success, message = network_manager.launch_sync_portal(school)

            if success:
                portal_text = []
                if message.startswith('HOTSPOT|'):
                    _, ssid, password, server_url = message.split('|', 3)
                    portal_text.append(f"WiFi Name: {ssid}")
                    portal_text.append(f"Password: {password}")
                    portal_text.append(f"Offline Portal: {server_url}")
                elif message.startswith('SERVER_ONLY|'):
                    _, server_url, error_message = message.split('|', 2)
                    portal_text.append(f"Offline Portal: {server_url}")
                    portal_text.append(f"Hotspot error: {error_message}")
                    portal_text.append("Enable Windows Mobile Hotspot manually if you want a local Wi-Fi network.")
                else:
                    portal_text.append(f"Offline Portal: {message}")

                if cloud_url:
                    portal_text.append(f"Cloud Portal: {cloud_url}")

                messagebox.showinfo("Portal Active", "\n".join(portal_text))

                # Toggle cloud portal if configured
                if cloud_school_code and cloud_teacher_username and cloud_url:
                    cloud_teacher_password = cloud_config.get('cloud_teacher_password', '').strip()
                    if cloud_teacher_password:
                        credentials = {
                            'school_code': cloud_school_code,
                            'username': cloud_teacher_username,
                            'password': cloud_teacher_password
                        }
                    else:
                        credentials = ask_cloud_credentials(self)
                        if not credentials:
                            # Still update local state even if cloud auth fails
                            self.portal_open = True
                            self.update_portal_button()
                            return

                    # Toggle cloud portal to open
                    service = CloudService()
                    result = service.toggle_portal(credentials)
                    if result.get('success'):
                        print(f"Cloud portal opened: {result.get('message')}")
                    else:
                        print(f"Failed to open cloud portal: {result.get('message')}")

                    self.sync_students_to_cloud(credentials)
                    self.sync_teachers_to_cloud(credentials)
                    try:
                        webbrowser.open(cloud_url)
                    except Exception:
                        pass
                elif cloud_url and not cloud_school_code:
                    if messagebox.askyesno('Cloud Portal', 'Open the cloud portal in the browser?'):
                        try:
                            webbrowser.open(cloud_url)
                        except Exception:
                            pass

                # Update state and button
                self.portal_open = True
                self.save_portal_state(True)
                self.update_portal_button()
            else:
                messagebox.showerror("Portal Error", f"Failed to start: {message}")
        else:
            # Close portal
            cloud_close_success = True
            if cloud_school_code and cloud_teacher_username and cloud_url:
                cloud_teacher_password = cloud_config.get('cloud_teacher_password', '').strip()
                if cloud_teacher_password:
                    credentials = {
                        'school_code': cloud_school_code,
                        'username': cloud_teacher_username,
                        'password': cloud_teacher_password
                    }
                else:
                    credentials = ask_cloud_credentials(self)
                    if not credentials:
                        # Still close locally even if user cancels cloud auth
                        cloud_close_success = False

                # Toggle cloud portal to close
                if credentials:
                    service = CloudService()
                    result = service.toggle_portal(credentials)
                    if result.get('success'):
                        messagebox.showinfo("Portal Closed", "Teachers portal has been closed. Teachers can no longer enter marks.")
                    else:
                        messagebox.showerror("Portal Error", f"Failed to close cloud portal: {result.get('message')}")
                        cloud_close_success = False
            else:
                messagebox.showinfo("Portal Closed", "Teachers portal has been closed. Teachers can no longer enter marks.")

            # Always update local state and button regardless of cloud status
            self.portal_open = False
            self.save_portal_state(False)
            self.update_portal_button()

    def update_portal_button(self):
        """Update portal button text and color based on state"""
        if self.portal_open:
            self.btn_portal.configure(text="🔒 Close Teacher Portal", fg_color="#e74c3c")
        else:
            self.btn_portal.configure(text="📡 Launch Teacher Portal", fg_color="green")

    def handle_cloud_sync_button(self):
        config = self.load_school_config()
        cloud_url = config.get('cloud_portal_url', '').strip()
        cloud_school_code = config.get('cloud_school_code', '').strip()
        cloud_teacher_username = config.get('cloud_teacher_username', '').strip()
        cloud_teacher_password = config.get('cloud_teacher_password', '').strip()

        if not cloud_url or not cloud_school_code or not cloud_teacher_username:
            messagebox.showwarning('Cloud Sync', 'Cloud portal is not fully configured. Please register the school or add cloud portal settings in school_config.json.')
            return

        if cloud_teacher_password:
            credentials = {
                'school_code': cloud_school_code,
                'username': cloud_teacher_username,
                'password': cloud_teacher_password
            }
        else:
            credentials = ask_cloud_credentials(self)
            if not credentials:
                return

        success = self.sync_students_to_cloud(credentials)
        if success:
            self.sync_teachers_to_cloud(credentials)
            if messagebox.askyesno('Cloud Portal', 'Students and teachers synced successfully. Open the cloud portal now?'):
                try:
                    webbrowser.open(cloud_url)
                except Exception:
                    pass

    def add_empty_row(self):
        # 1. Create the Row Frame with a slightly lighter dark color
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#2b2b2b", height=40)
        row_frame.pack(fill="x", pady=2, padx=5)

        self.all_student_rows.append(row_frame)

        # Configure grid columns for 7 columns (5 entries + photo + stream + actions)
        for i in range(7):
            row_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        row_frame.grid_columnconfigure(7, weight=0, minsize=150)

        # 3. Entry Boxes (White Background & Black Text for Clarity)
        entry_style = {"fg_color": "white", "text_color": "black", "height": 30}

        adm = ctk.CTkEntry(row_frame, placeholder_text="ADM", **entry_style)
        adm.grid(row=0, column=0, padx=2, pady=5, sticky="ew")

        name = ctk.CTkEntry(row_frame, placeholder_text="Full Name", **entry_style)
        name.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        grade = ctk.CTkEntry(row_frame, placeholder_text="Grade", **entry_style)
        grade.grid(row=0, column=2, padx=2, pady=5, sticky="ew")

        gender = ctk.CTkEntry(row_frame, placeholder_text="Gender", **entry_style)
        gender.grid(row=0, column=3, padx=2, pady=5, sticky="ew")

        phone = ctk.CTkEntry(row_frame, placeholder_text="Phone", **entry_style)
        phone.grid(row=0, column=4, padx=2, pady=5, sticky="ew")

        # Stream field
        stream = ctk.CTkEntry(row_frame, placeholder_text="Stream", **entry_style)
        stream.grid(row=0, column=5, padx=2, pady=5, sticky="ew")

        # Photo upload button
        photo_path = ctk.StringVar()
        photo_btn = ctk.CTkButton(row_frame, text="📷 Photo", width=80, height=30,
                                   command=lambda: self.upload_student_photo(photo_path, photo_btn))
        photo_btn.grid(row=0, column=6, padx=2, pady=5, sticky="ew")

        # 4. The Button Actions Frame (This holds Save, Edit, Delete together)
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=7, padx=5)

        # SAVE (Green)
        save_btn = ctk.CTkButton(actions_frame, text="✓", width=30, fg_color="green",
                                 command=lambda: self.save_to_db(adm, name, grade, gender, phone, stream, photo_path, save_btn))
        save_btn.pack(side="left", padx=2)

       # EDIT (Blue)
        # We pass ALL entries and the save button to a new helper function
        edit_btn = ctk.CTkButton(actions_frame, text="✎", width=30, fg_color="#1f538d",
                                 command=lambda e=[adm, name, grade, gender, phone, stream, photo_path], b=save_btn, pb=photo_btn: self.unlock_row_for_edit(e, b, pb))
        edit_btn.pack(side="left", padx=2)

       # DELETE (Red)
        # Use 'adm' (the variable name for your first Entry box)
        del_btn = ctk.CTkButton(actions_frame, text="🗑", width=30, fg_color="#942727",
                                command=lambda f=row_frame, a=adm: self.confirm_delete(f, a))
        del_btn.pack(side="left", padx=2)

    def upload_student_photo(self, photo_path_var, photo_btn):
        """Open file dialog to select student photo"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Student Photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            photo_path_var.set(file_path)
            photo_btn.configure(text="✓ Photo")

    def unlock_row_for_edit(self, entries, save_button, photo_btn=None):
        """Unlocks a row and RE-LINKS the save button to the database function"""
        # Unlock all entry fields (first 6 are CTkEntry, last is StringVar for photo)
        for i, entry in enumerate(entries):
            if i < 6 and isinstance(entry, ctk.CTkEntry):
                entry.configure(state="normal", fg_color="white", text_color="black")

        # Enable photo button if it exists
        if photo_btn:
            photo_btn.configure(state="normal", fg_color="#1f538d",
                                command=lambda: self.upload_student_photo(entries[6], photo_btn))

        # We must re-configure the command so it knows to save again when clicked
        save_button.configure(
            state="normal",
            text="✓",
            fg_color="green",
            command=lambda: self.save_to_db(entries[0], entries[1], entries[2], entries[3], entries[4], entries[5], entries[6], save_button)
        )

    def save_to_db(self, adm_entry, name_entry, grade_entry, gender_entry, phone_entry, stream_entry, photo_path_var, btn):
        adm = adm_entry.get()
        name = name_entry.get()
        gender = gender_entry.get()
        phone = phone_entry.get()
        stream = stream_entry.get() if stream_entry else "None"
        photo = photo_path_var.get() if photo_path_var else None

        # --- THE CRITICAL FIX ---
        # This pulls the actual text from your title label
        # so it matches the database perfectly.
        raw_title = self.registry_title.cget("text") # Result: "Student Registry: playgroup"
        current_class = raw_title.replace("Student Registry: ", "").strip()

        # Normalize grade names to match database format
        grade_mapping = {
            "Play group": "playgroup",
            "Pre-Primary 1": "pp1",
            "Pre-Primary 2": "pp2",
        }
        grade = grade_mapping.get(current_class, current_class)

        if not adm or not name:
            messagebox.showwarning("Input Error", "ADM and Name are required!")
            return

        try:
            # 1. Save to Database
            self.db.add_student(adm, name, grade, gender, phone, photo, stream)

            # 2. Lock the Row visually
            for entry in [adm_entry, name_entry, grade_entry, gender_entry, phone_entry, stream_entry]:
                if entry:
                    entry.configure(state="disabled", fg_color="gray30", text_color="white")

            # 3. Update Button
            btn.configure(text="Saved", state="disabled", fg_color="gray")

            # 4. Success Message in Terminal
            print(f"Verified Save: {name} added to {grade}")

        except Exception as e:
            messagebox.showerror("Database Error", f"Could not save: {e}")

    def mass_edit_all(self):
        """Unlocks every row currently visible in the table"""
        if not self.all_student_rows:
            print("No rows to edit!")
            return

        for row in self.all_student_rows:
            # 1. Find all Entry boxes in this row and unlock them
            row_entries = []
            photo_btn = None
            save_btn = None

            # We look through all children of the row
            for widget in row.winfo_children():
                if isinstance(widget, ctk.CTkEntry):
                    widget.configure(state="normal", fg_color="white", text_color="black")
                    row_entries.append(widget)

                # Find photo button
                if isinstance(widget, ctk.CTkButton) and "Photo" in widget.cget("text"):
                    photo_btn = widget

                # The Save button is hidden inside the actions frame
                if isinstance(widget, ctk.CTkFrame):
                    for sub_widget in widget.winfo_children():
                        if isinstance(sub_widget, ctk.CTkButton):
                            # Identify the Save/Saved button by its text
                            if sub_widget.cget("text") in ["Saved", "✓"]:
                                save_btn = sub_widget

            # 2. Re-link the Save button so it works after being unlocked
            if save_btn and len(row_entries) >= 6:
                # Create a StringVar for photo path if not exists
                photo_path = ctk.StringVar()
                save_btn.configure(
                    state="normal",
                    text="✓",
                    fg_color="green",
                    command=lambda r=row_entries, p=photo_path, pb=photo_btn, b=save_btn: self.save_to_db(r[0], r[1], r[2], r[3], r[4], r[5], p, b)
                )
        print("All rows unlocked for editing.")

    def remove_specific_row(self, frame_to_remove):
        """Removes the row from the screen and the tracker"""
        frame_to_remove.destroy()
        if frame_to_remove in self.all_student_rows:
            self.all_student_rows.remove(frame_to_remove)
    def edit_row(self, entries, save_btn):
        """Unlocks the boxes so the teacher can fix a typo"""
        for entry in entries:
            entry.configure(state="normal", text_color="white", fg_color="gray25")
        
        # Change the button back to the Tick so they can save again
        save_btn.configure(text="✓", state="normal", fg_color="#2ecc71")
    def clear_all_students(self):
        """Permanently deletes all students currently visible on the screen from the DB"""
        if not self.all_student_rows:
            messagebox.showinfo("Info", "There are no rows to remove.")
            return
            
        # 1. Ask for confirmation (Crucial since this is permanent!)
        confirm = messagebox.askyesno("Confirm Mass Delete", 
                                     "WARNING: This will PERMANENTLY delete all students shown below from the database. \n\nContinue?")
        
        if confirm:
            try:
                for row in self.all_student_rows:
                    # 2. Find the ADM NO entry box in this row
                    # We look for the first CTkEntry widget
                    adm_no = None
                    for widget in row.winfo_children():
                        if isinstance(widget, ctk.CTkEntry):
                            adm_no = widget.get()
                            break # Found the first box (ADM NO), move on
                    
                    # 3. If there is an ADM NO, delete it from the database
                    if adm_no:
                        self.db.delete_student(adm_no)
                    
                    # 4. Remove the row from the UI
                    row.destroy()
                
                # 5. Reset the tracker list
                self.all_student_rows = []
                messagebox.showinfo("Success", "All records have been permanently deleted.")
                print("Mass deletion complete.")
                
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during mass deletion: {e}")
                
    def lock_and_save(self, entries, button):
        """Disables typing and changes the button appearance"""
        
        # Check if Name is empty before locking
        if entries[1].get() == "":
            print("Error: Name is required!")
            return

        # Disable all entry boxes in this row
        for entry in entries:
            entry.configure(state="disabled", text_color="white",fg_color="gray10",border_width=0)
        
        # Change the Tick to a "Locked" icon or just hide it
        button.configure(text="Saved", state="disabled", fg_color="#34495e")
        
        print(f"Data for {entries[1].get()} has been locked in the registry.")

    def add_filled_row_from_db(self, data):
        """Creates a row that is already populated and locked"""
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#2b2b2b", height=40)
        row_frame.pack(fill="x", pady=2, padx=5)
        self.all_student_rows.append(row_frame)

        # Configure grid columns for 7 columns + actions
        for i in range(7):
            row_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        row_frame.grid_columnconfigure(7, weight=0, minsize=150)

        # Create entries and insert the data from 'student' tuple
        entries = []
        # Create 5 main entry fields (adm, name, grade, gender, phone)
        # Handle old records that might not have all columns
        for i in range(5):
            e = ctk.CTkEntry(row_frame, fg_color="gray30", text_color="white", state="normal")
            value = str(data[i]) if i < len(data) and data[i] is not None else ""
            e.insert(0, value) # Put the DB info (ADM, Name, etc) into the box
            e.configure(state="disabled") # Lock it immediately
            e.grid(row=0, column=i, padx=2, pady=5, sticky="ew")
            entries.append(e)

        # Stream field (column 5)
        stream_value = str(data[6]) if len(data) > 6 and data[6] is not None else "None"
        stream = ctk.CTkEntry(row_frame, fg_color="gray30", text_color="white", state="normal")
        stream.insert(0, stream_value)
        stream.configure(state="disabled")
        stream.grid(row=0, column=5, padx=2, pady=5, sticky="ew")
        entries.append(stream)

        # Photo field (column 6)
        photo_value = data[5] if len(data) > 5 else None
        photo_path = ctk.StringVar(value=photo_value or "")
        photo_btn = ctk.CTkButton(row_frame, text="✓ Photo" if photo_value else "📷 Photo", width=80, height=30,
                                   state="disabled", fg_color="gray")
        photo_btn.grid(row=0, column=6, padx=2, pady=5, sticky="ew")
        entries.append(photo_path)  # Store the StringVar in entries list

        # Add the action buttons (Save, Edit, Delete)
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=7, padx=5)

        # The Save button starts as "Saved"
        save_btn = ctk.CTkButton(actions_frame, text="Saved", width=40, fg_color="gray", state="disabled",
                                 command=lambda: self.save_to_db(entries[0], entries[1], entries[2], entries[3], entries[4], entries[5], entries[6], save_btn))
        save_btn.pack(side="left", padx=2)

        edit_btn = ctk.CTkButton(actions_frame, text="✎", width=30, fg_color="#1f538d",
                                 command=lambda e=entries, b=save_btn, pb=photo_btn: self.unlock_row_for_edit(e, b, pb))
        edit_btn.pack(side="left", padx=2)

        # DELETE (Red)
        # We use entries[0] because that's the ADM NO box we just created in the loop above
        del_btn = ctk.CTkButton(actions_frame, text="🗑", width=30, fg_color="#942727",
                                command=lambda f=row_frame, a=entries[0]: self.confirm_delete(f, a))
        del_btn.pack(side="left", padx=2)
    def create_table_headers(self):
        """Creates the header row inside the table_frame"""
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="gray25", corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 10)) # pady adds space before the first student

        # Match the column logic of your rows (7 columns + actions)
        for i in range(7):
            header_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        header_frame.grid_columnconfigure(7, weight=0, minsize=150)

        cols = ["ADM NO", "STUDENT NAME", "GRADE", "GENDER", "PHONE", "STREAM", "PHOTO", "ACTIONS"]
        for i, text in enumerate(cols):
            lbl = ctk.CTkLabel(header_frame, text=text, font=("Arial Bold", 12), text_color="white")
            if i < 7:
                lbl.grid(row=0, column=i, padx=10, pady=5, sticky="w")
            else:
                lbl.grid(row=0, column=7, padx=10, pady=5)
    
    def show_student_registry(self, class_name):
        # 1. Layout: Hide sidebar and expand content
        self.menu_panel.grid_forget()
        self.grid_columnconfigure(0, weight=0, minsize=0)
        self.grid_columnconfigure(1, weight=1)
        self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
        
        # 2. Clear previous widgets
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

            # --- MOVE THIS UP HERE ---
        # 2. Create the Title FIRST so save_to_db can always find it
        self.registry_title = ctk.CTkLabel(self.content_panel, 
                                          text=f"Student Registry: {class_name}", 
                                          font=("Arial Bold", 24))
        self.registry_title.pack(pady=20)
        # -------------------------
        
        # 3. Create the Main Container and THE TABLE FRAME (Must happen FIRST)
        self.registry_container = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        self.registry_container.pack(fill="both", expand=True, padx=20)

        # --- 1. Create the Scrollable Frame FIRST ---
        self.table_frame = ctk.CTkScrollableFrame(self.registry_container, 
                                                 fg_color="gray15", 
                                                 corner_radius=10)
        self.table_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # --- 2. Call the Header Function ---
        # This puts the header INSIDE the scrollable frame at the very top
        self.create_table_headers()

        # 4. Now that table_frame exists, we can use these functions:
        self.all_student_rows = []
        self.load_students_from_db(class_name)
        
        # 5. Add blank rows
        for _ in range(3):
            self.add_empty_row()
        
        self.search_entry = ctk.CTkEntry(self.content_panel, placeholder_text="🔍 Search...", 
                                         width=300, textvariable=self.search_var)
        self.search_var.trace_add("write", self.filter_students)
        self.search_entry.pack(pady=10)

        # 7. Right Side Control Panel
        self.control_panel = ctk.CTkFrame(self.registry_container, width=200, fg_color="transparent")
        self.control_panel.pack(side="right", fill="y")
        
        # ... (rest of your button code) ...
        btn_style = {"width": 160, "height": 40, "font": ("Arial Bold", 13)}
        
        self.btn_add = ctk.CTkButton(self.control_panel, text="Add Student", 
                                     fg_color="#2ecc71", hover_color="#27ae60", **btn_style, command=self.add_empty_row)
        self.btn_add.pack(pady=10)

        self.btn_remove = ctk.CTkButton(self.control_panel, text="Remove all Students", 
                                        fg_color="#e74c3c", hover_color="#c0392b", **btn_style)
        self.btn_remove.pack(pady=10)

        self.btn_edit = ctk.CTkButton(self.control_panel, text="Edit all Students", 
                                      fg_color="#f39c12", hover_color="#d35400", **btn_style,command=self.mass_edit_all)
        self.btn_edit.pack(pady=10)

        self.spacer = ctk.CTkLabel(self.control_panel, text="")
        self.spacer.pack(expand=True)

        self.btn_home = ctk.CTkButton(self.control_panel, text="Home", 
                                      command=self.return_to_home, **btn_style)
        self.btn_home.pack(pady=10)

        self.btn_remove.configure(command=self.clear_all_students)

    def load_students_from_db(self, class_name):
        try:
            # Check if the DB tool is broken
            if not hasattr(self.db.conn, 'cursor'):
                 print("Database connection issue.")
                 return

            # Use the connection directly to be safe
            cursor = self.db.conn.cursor()

            query = "SELECT adm_no, name, grade, gender, phone, photo, stream FROM students WHERE grade = ?"
            cursor.execute(query, (class_name,))

            records = cursor.fetchall()

            # Clear current list tracker before adding new ones
            self.all_student_rows = []

            for row_data in records:
                self.add_locked_row(row_data)

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")

    def add_locked_row(self, data):
        """Creates a row that is already saved and disabled with perfect alignment"""
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#1a1a1a")
        row_frame.pack(fill="x", pady=2, padx=5)
        self.all_student_rows.append(row_frame)

        # --- THE ALIGNMENT FIX ---
        # Force the first 7 columns to be exactly equal in size (5 entries + stream + photo)
        for i in range(7):
            row_frame.grid_columnconfigure(i, weight=1, uniform="column_group")
        # Keep the actions column fixed
        row_frame.grid_columnconfigure(7, weight=0, minsize=150)

        entries = []
        # Create 5 main entry fields (adm, name, grade, gender, phone)
        # Handle old records that might not have all columns
        for i in range(5):
            # Use sticky="ew" so the entry stretches to fill the uniform column
            e = ctk.CTkEntry(row_frame, fg_color="gray20", text_color="white", height=30)
            value = str(data[i]) if i < len(data) and data[i] is not None else ""
            e.insert(0, value)
            e.configure(state="disabled")
            e.grid(row=0, column=i, padx=2, pady=5, sticky="ew")
            entries.append(e)

        # Stream field (column 5)
        stream_value = str(data[6]) if len(data) > 6 and data[6] is not None else "None"
        stream = ctk.CTkEntry(row_frame, fg_color="gray20", text_color="white", height=30)
        stream.insert(0, stream_value)
        stream.configure(state="disabled")
        stream.grid(row=0, column=5, padx=2, pady=5, sticky="ew")
        entries.append(stream)

        # Photo field (column 6)
        photo_value = data[5] if len(data) > 5 else None
        photo_path = ctk.StringVar(value=photo_value or "")
        photo_btn = ctk.CTkButton(row_frame, text="✓ Photo" if photo_value else "📷 Photo", width=80, height=30,
                                   state="disabled", fg_color="gray")
        photo_btn.grid(row=0, column=6, padx=2, pady=5, sticky="ew")
        entries.append(photo_path)  # Store the StringVar in entries list

        actions = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions.grid(row=0, column=7, padx=5)

       # DELETE (Red)
        # We use entries[0] because that's the ADM NO box we just created in the loop above
        del_btn = ctk.CTkButton(actions, text="🗑", width=30, fg_color="#942727",
                                command=lambda f=row_frame, a=entries[0]: self.confirm_delete(f, a))
        del_btn.pack(side="left", padx=2)

        save_btn = ctk.CTkButton(actions, text="Saved", width=40, state="disabled", fg_color="gray")
        save_btn.pack(side="left", padx=2)

        edit_btn = ctk.CTkButton(actions, text="✎", width=30,
                                 command=lambda e=entries, b=save_btn, pb=photo_btn: self.unlock_row_for_edit(e, b, pb))
        edit_btn.pack(side="left", padx=2)
        
    def confirm_delete(self, frame, adm_entry):
        adm_no = adm_entry.get()
        if not adm_no:
            frame.destroy() # Just a blank row, safe to just close
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete ADM: {adm_no} permanently?"):
            self.db.delete_student(adm_no) # Delete from DB
            frame.destroy()               # Remove from UI
   
    def filter_students(self, *args):
        """Hides rows that don't match the search query"""
        search_query = self.search_var.get().lower()

        for row_frame in self.all_student_rows:
            # We need to look at the ADM (index 0) and Name (index 1) entries
            # We find them inside the row_frame
            row_widgets = [child for child in row_frame.winfo_children() if isinstance(child, ctk.CTkEntry)]
            
            if row_widgets:
                adm_text = row_widgets[0].get().lower()
                name_text = row_widgets[1].get().lower()

                # If the search matches either the ADM or the Name, show the row
                if search_query in adm_text or search_query in name_text:
                    row_frame.pack(fill="x", pady=1, padx=5) # Show
                else:
                    row_frame.pack_forget() # Hide

    def show_dashboard_workspace(self):
        """Resets the layout so the sidebar is visible again"""
        
        # 1. BRING BACK THE SIDEBAR (Column 0)
        self.grid_columnconfigure(0, weight=0, minsize=250) 
        self.grid_columnconfigure(1, weight=1)
        self.menu_panel.grid(row=0, column=0, sticky="nsew")
        
        # 2. PUT CONTENT BACK IN COLUMN 1 (Don't let it span both columns)
        self.content_panel.grid(row=0, column=1, columnspan=1, sticky="nsew")

        # 3. Clear the workspace
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # 4. Show the Welcome Message
        self.work_area_label = ctk.CTkLabel(
            self.content_panel, 
            text="Welcome to Freeman Tech Solutions\nSelect a task from the sidebar to begin.", 
            font=("Arial", 18), text_color="gray60"
        )
        self.work_area_label.pack(expand=True)
    
        # 5. Reset button highlights
        for btn in self.sidebar_buttons:
            btn.configure(fg_color="transparent", text_color="gray", border_width=0, font=("Arial", 13))
    def return_to_home(self):
        """Brings back the sidebar and resets the layout"""
        
        # Remove marksheet toolbar if exists
        if hasattr(self, 'marksheet_toolbar'):
            self.marksheet_toolbar.destroy()
        
        # 1. BRING BACK SIDEBAR
        self.menu_panel.grid(row=0, column=0, sticky="nsew")
        
        # 2. PUSH CONTENT BACK TO COLUMN 1
        self.content_panel.grid(row=0, column=1, sticky="nsew")

        # 3. Show the original welcome screen
        self.show_dashboard_workspace()
   
    def highlight_button(self, active_button):
        """Resets all sidebar buttons to ghost-style and makes the active one pop out"""
        for btn in self.sidebar_buttons:
            # RESET: Non-selected buttons become semi-transparent/ghost
            btn.configure(
                fg_color="transparent", 
                text_color="gray", 
                font=("Arial", 13),
                border_width=0
            )
        
        # ACTIVE: The selected button gets the 'Freeman Glow'
        active_button.configure(
            fg_color="#1f6aa5",     # Solid Vibrant Blue
            text_color="white",     # Crisp White Text
            font=("Arial Bold", 14), # Bigger and Bolder
            border_width=2,         # Thin border to make it sharp
            border_color="#5dade2"  # Lighter blue border
        )

        
    def show_class_selection(self, action_type, button_object):
            # Trigger the visual highlight first
                self.highlight_button(button_object)

            # Clear the workspace (keep header/theme toggle)
                for widget in self.content_panel.winfo_children():
                    if widget != self.header_frame and widget != self.theme_frame:
                        widget.destroy()

            # Create the Scrollable Class Menu
                self.class_frame = ctk.CTkScrollableFrame(
                    self.content_panel, 
                    label_text=f"SELECT CLASS FOR: {action_type.upper()}",
                    label_font=("Arial Bold", 20),
                    fg_color="gray10", # Darker background for the class list
                    width=400, height=500
                    )
                self.class_frame.pack(pady=40, expand=True)

                # Add Create New Exam button at the top if viewing marks
                if action_type == "Viewing Marks":
                    create_exam_btn = ctk.CTkButton(
                        self.class_frame,
                        text="🆕 Create New Exam (All Classes)",
                        fg_color="#10b981",
                        text_color="white",
                        width=300,
                        height=45,
                        command=self.create_new_exam_all_classes
                    )
                    create_exam_btn.pack(pady=(0, 20))

                # Add Send All Reports to Portal and Print All Reports buttons for Report Forms
                if action_type == "Report Forms":
                    send_all_btn = ctk.CTkButton(
                        self.class_frame,
                        text="📤 Send All Reports to Portal",
                        fg_color="#3498db",
                        text_color="white",
                        width=300,
                        height=45,
                        command=self.send_all_reports_to_portal
                    )
                    send_all_btn.pack(pady=(0, 10))

                    print_all_btn = ctk.CTkButton(
                        self.class_frame,
                        text="📄 Print All Reports",
                        fg_color="#27ae60",
                        text_color="white",
                        width=300,
                        height=45,
                        command=self.print_all_reports
                    )
                    print_all_btn.pack(pady=(0, 10))

                    # Back to Dashboard button
                    back_btn = ctk.CTkButton(
                        self.class_frame,
                        text="← Back to Dashboard",
                        fg_color="#e74c3c",
                        text_color="white",
                        width=300,
                        height=45,
                        command=self.return_to_home
                    )
                    back_btn.pack(pady=(0, 20))

                classes = [
                    "playgroup", "pp1", "pp2",
                    "Grade 1", "Grade 2", "Grade 3", "Grade 4",
                    "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9"
                    ]
                for class_name in classes:
                    btn = ctk.CTkButton(
                        self.class_frame, 
                        text=class_name, 
                        width=300, height=45,
                        hover_color="#2ecc71", # Glow green when hovering over a class
                        command=lambda c=class_name: self.open_class_action(c, action_type)
                        )
                    btn.pack(pady=10)
    def open_class_action(self, class_selected, action_type):
        # 1. Clear the old view completely (Class Selection Menu)
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        print(f"Action: {action_type} | Target: {class_selected}")

        # 2. DECIDE: Which screen are we opening?
        
        # This handles the new Marksheet file
        if action_type == "Viewing Marks":
            # --- FULL SCREEN MODE ---
            self.menu_panel.grid_forget() # Hide the left sidebar
            self.grid_columnconfigure(0, weight=0, minsize=0) # Shrink sidebar space to zero
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew") # Content takes all columns

            # 1. Clean up the class name for easier comparison
            name_upper = class_selected.upper().strip()

            # 2. Route to the correct view based on the name
            if "PLAYGROUP" in name_upper or "PLAY GROUP" in name_upper:
                self.current_view = PlaygroupMarkSheetView(self.content_panel, self.db, class_selected)

            elif "PP1" in name_upper or "PRE-PRIMARY 1" in name_upper:
                self.current_view = PP1MarkSheetView(self.content_panel, self.db, class_selected)

            elif "PP2" in name_upper or "PRE-PRIMARY 2" in name_upper:
                self.current_view = PP2MarkSheetView(self.content_panel, self.db, class_selected)
                
            elif any(g in name_upper for g in ["GRADE 1", "GRADE 2", "GRADE 3"]):
                self.current_view = LowerMarkSheetView(self.content_panel, self.db, class_selected)
                
            elif any(g in name_upper for g in ["GRADE 4", "GRADE 5", "GRADE 6"]):
                from ui_marksheet_primary import PrimaryMarkSheetView
                self.current_view = PrimaryMarkSheetView(self.content_panel, self.db, class_selected)
                
            else:
                # Fallback for Junior Secondary or others
                from ui_marksheet_junior import JuniorMarkSheetView
                self.current_view = JuniorMarkSheetView(self.content_panel, self.db, class_selected)

            # Final UI placement
            self.current_view.pack(fill="both", expand=True)

        elif action_type == "Summary":
            # --- FULL SCREEN SUMMARY ---
            self.menu_panel.grid_forget()
            self.grid_columnconfigure(0, weight=0, minsize=0)
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.current_view = ClassSummaryView(self.content_panel, self.db, class_selected)
            self.current_view.pack(fill="both", expand=True)

        # This handles the Register button
        elif action_type == "Registering" or action_type == "Registration":
            # We call the function that is already inside this Dashboard class
            self.show_student_registry(class_selected)

        # This handles the Previous Exams button
        elif action_type == "Previous Exams":
            self.show_previous_exams_selection(class_selected)

        # This handles the Teachers Linked button
        elif action_type == "Teachers":
            # --- FULL SCREEN MODE ---
            self.menu_panel.grid_forget() # Hide the left sidebar
            self.grid_columnconfigure(0, weight=0, minsize=0) # Shrink sidebar space to zero
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.current_view = TeachersLinkedView(self.content_panel, self.db, class_selected, self.show_dashboard_workspace)
            self.current_view.pack(fill="both", expand=True)

        # This handles the Report Forms button
        elif action_type == "Report Forms":
            # --- FULL SCREEN MODE ---
            self.menu_panel.grid_forget() # Hide the left sidebar
            self.grid_columnconfigure(0, weight=0, minsize=0) # Shrink sidebar space to zero
            self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.show_report_forms_class_view(class_selected)

    def show_report_forms_class_view(self, class_name):
        # Clear the old view completely
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # Header frame with title and action buttons
        header_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        # Title
        title_label = ctk.CTkLabel(header_frame, text=f"Report Forms - {class_name}",
                                   font=("Arial Bold", 28))
        title_label.pack(side="left", padx=10)

        # Send all reports for this class to portal button
        send_class_btn = ctk.CTkButton(header_frame, text="Send All Reports for This Class to Portal",
                                      fg_color="#3498db", hover_color="#2980b9",
                                      font=("Arial Bold", 14), height=40,
                                      command=lambda: self.send_class_reports_to_portal(class_name))
        send_class_btn.pack(side="right", padx=10)

        # Print reports for this class button
        print_class_btn = ctk.CTkButton(header_frame, text="Print Reports for This Class",
                                       fg_color="#27ae60", hover_color="#1e8449",
                                       font=("Arial Bold", 14), height=40,
                                       command=lambda: self.print_class_reports(class_name))
        print_class_btn.pack(side="right", padx=10)

        # Back button
        back_btn = ctk.CTkButton(header_frame, text="← Back to Class Selection",
                                fg_color="#e74c3c", hover_color="#c0392b",
                                font=("Arial Bold", 14), height=40,
                                command=self.open_report_forms)
        back_btn.pack(side="right", padx=10)

        # Student list frame
        student_frame = ctk.CTkScrollableFrame(self.content_panel)
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
                                    command=lambda s=student: self.show_student_report_form(s))
            view_btn.pack(side="right", padx=10, pady=10)

    def get_students_in_class(self, class_name):
        try:
            self.db._cursor.execute('SELECT adm_no, name, grade, stream FROM students WHERE grade = ? ORDER BY name',
                                   (class_name,))
            students = [{'adm_no': row[0], 'name': row[1], 'grade': row[2], 'stream': row[3] if row[3] else 'none'}
                       for row in self.db._cursor.fetchall()]
            return students
        except Exception as e:
            print(f"Error getting students: {e}")
            return []

    def show_student_report_form(self, student):
        # Create a new toplevel window for the report form
        report_window = ctk.CTkToplevel(self)
        report_window.title(f"Report Form - {student['name']}")
        report_window.geometry("1000x800")

        # Main container
        report_container = ctk.CTkScrollableFrame(report_window)
        report_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Import report forms functionality
        from reportforms import ReportFormsView
        # Create a temporary report forms instance to use its methods
        temp_report = ReportFormsView.__new__(ReportFormsView)
        temp_report.parent_window = self
        temp_report.db = self.db
        temp_report.current_student = student
        temp_report.current_class = student['grade']
        temp_report.school_config = self.load_school_config()

        # Create school header
        temp_report.create_school_header(report_container, student)
        # Create student info
        temp_report.create_student_info(report_container, student)
        # Create current marks section
        temp_report.create_current_marks_section(report_container, student)
        # Create previous marks section
        temp_report.create_previous_marks_section(report_container, student)

        # Action buttons
        button_frame = ctk.CTkFrame(report_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=30)

        # Print PDF button
        print_btn = ctk.CTkButton(button_frame, text="📄 Print as PDF",
                                 fg_color="#27ae60", hover_color="#1e8449",
                                 font=("Arial Bold", 14), height=45, width=200,
                                 command=lambda: temp_report.print_report_pdf(None, temp_report.generate_report_data(student)))
        print_btn.pack(side="left", padx=10)

        # Send to parent button
        send_btn = ctk.CTkButton(button_frame, text="📤 Send Report to Parent",
                                fg_color="#3498db", hover_color="#2980b9",
                                font=("Arial Bold", 14), height=45, width=200,
                                command=lambda: temp_report.send_student_report_to_portal(student))
        send_btn.pack(side="left", padx=10)

        # Close button
        close_btn = ctk.CTkButton(button_frame, text="✕ Close",
                                 fg_color="#e74c3c", hover_color="#c0392b",
                                 font=("Arial Bold", 14), height=45, width=150,
                                 command=report_window.destroy)
        close_btn.pack(side="right", padx=10)

        # Store reference to prevent garbage collection
        if not hasattr(self, 'report_windows'):
            self.report_windows = []
        self.report_windows.append(report_window)

        # Bring window to front after a short delay
        report_window.after(100, report_window.lift)
        report_window.after(100, report_window.focus_force)

    def send_class_reports_to_portal(self, class_name):
        credentials = self.get_cloud_credentials()
        if not credentials:
            return

        students = self.get_students_in_class(class_name)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return

        from cloud_service import CloudService
        service = CloudService()
        success_count = 0

        for student in students:
            report_data = self.generate_report_data(student)
            result = service.send_student_report(report_data, credentials)

            if result.get('success'):
                success_count += 1

        messagebox.showinfo("Success", f"Sent {success_count}/{len(students)} reports to portal.")

    def print_class_reports(self, class_name):
        students = self.get_students_in_class(class_name)
        if not students:
            messagebox.showinfo("Info", "No students in this class.")
            return

        from tkinter import filedialog
        from reportforms import ReportFormsView

        # Ask for directory to save PDFs
        save_dir = filedialog.askdirectory(title=f"Select folder to save {class_name} reports")
        if not save_dir:
            return

        success_count = 0
        for student in students:
            try:
                # Create temporary report object
                temp_report = ReportFormsView.__new__(ReportFormsView)
                temp_report.db = self.db
                temp_report.school_config = self.load_school_config()

                # Generate report data for this student
                report_data = temp_report.generate_report_data(student)
                
                if not report_data:
                    print(f"Warning: No report data generated for {student.get('name', 'Unknown')}")
                    continue

                # Generate PDF
                student_name = student.get("name", "")
                exam_title = report_data.get("exam_title", "PERFORMANCE REPORT")
                file_path = f"{save_dir}/{student_name.replace(' ', '_')}_{exam_title.replace(' ', '_')}.pdf"

                # Call the print function with file_path
                temp_report.print_report_pdf(None, report_data, file_path)
                success_count += 1

            except Exception as e:
                print(f"Error generating PDF for {student.get('name', 'Unknown')}: {e}")
                import traceback
                traceback.print_exc()

        messagebox.showinfo("Success", f"Generated {success_count}/{len(students)} PDF reports for {class_name}.")

    def generate_report_data(self, student):
        from reportforms import ReportFormsView
        temp_report = ReportFormsView.__new__(ReportFormsView)
        temp_report.db = self.db
        temp_report.school_config = self.load_school_config()
        return temp_report.generate_report_data(student)

    def get_cloud_credentials(self):
        from cloud_service import ask_cloud_credentials
        cloud_config = self.load_school_config()
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

    def send_all_reports_to_portal(self):
        credentials = self.get_cloud_credentials()
        if not credentials:
            return

        classes = [
            "playgroup", "pp1", "pp2",
            "Grade 1", "Grade 2", "Grade 3", "Grade 4",
            "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9"
        ]

        from cloud_service import CloudService
        service = CloudService()
        total_success = 0
        total_students = 0

        for class_name in classes:
            students = self.get_students_in_class(class_name)
            total_students += len(students)

            for student in students:
                report_data = self.generate_report_data(student)
                if report_data is None:
                    print(f"Skipping {student.get('name', 'Unknown')} - no marks found")
                    continue
                result = service.send_student_report(report_data, credentials)

                if result.get('success'):
                    total_success += 1

        messagebox.showinfo("Success", f"Sent {total_success}/{total_students} reports to portal.")

    def print_all_reports(self):
        classes = [
            "playgroup", "pp1", "pp2",
            "Grade 1", "Grade 2", "Grade 3", "Grade 4",
            "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9"
        ]

        from tkinter import filedialog
        from reportforms import ReportFormsView

        # Ask for directory to save PDFs
        save_dir = filedialog.askdirectory(title="Select folder to save all reports")
        if not save_dir:
            return

        total_success = 0
        total_students = 0

        for class_name in classes:
            students = self.get_students_in_class(class_name)
            if not students:
                continue

            total_students += len(students)

            for student in students:
                try:
                    # Create temporary report object
                    temp_report = ReportFormsView.__new__(ReportFormsView)
                    temp_report.db = self.db
                    temp_report.school_config = self.load_school_config()

                    # Generate report data for this student
                    report_data = temp_report.generate_report_data(student)
                    
                    if not report_data:
                        print(f"Warning: No report data generated for {student.get('name', 'Unknown')} in {class_name}")
                        continue

                    # Generate PDF
                    student_name = student.get("name", "")
                    exam_title = report_data.get("exam_title", "PERFORMANCE REPORT")
                    file_path = f"{save_dir}/{class_name}_{student_name.replace(' ', '_')}_{exam_title.replace(' ', '_')}.pdf"

                    # Call the print function with file_path
                    temp_report.print_report_pdf(None, report_data, file_path)
                    total_success += 1

                except Exception as e:
                    print(f"Error generating PDF for {student.get('name', 'Unknown')} in {class_name}: {e}")
                    import traceback
                    traceback.print_exc()

        messagebox.showinfo("Success", f"Generated {total_success}/{total_students} PDF reports for all classes.")

    def show_previous_exams_selection(self, class_selected):
        # Clear the old view completely (Class Selection Menu)
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # Get previous exams for this class
        previous_exams = self.db.get_previous_exams(class_selected)

        if not previous_exams:
            # No previous exams found
            no_exams_label = ctk.CTkLabel(
                self.content_panel,
                text=f"No previous exams found for {class_selected}",
                font=("Arial", 18),
                text_color="gray"
            )
            no_exams_label.pack(pady=50)

            back_btn = ctk.CTkButton(
                self.content_panel,
                text="Back",
                command=self.return_to_home,
                width=150
            )
            back_btn.pack(pady=20)
            return

        # Create the exam selection UI
        exam_frame = ctk.CTkScrollableFrame(
            self.content_panel,
            label_text=f"PREVIOUS EXAMS FOR: {class_selected.upper()}",
            label_font=("Arial Bold", 20),
            fg_color="gray10",
            width=600,
            height=500
        )
        exam_frame.pack(pady=40, expand=True)

        for exam_name, exam_date in previous_exams:
            row_frame = ctk.CTkFrame(exam_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=5)

            view_btn = ctk.CTkButton(
                row_frame,
                text=f"{exam_name} ({exam_date})",
                width=400,
                height=45,
                hover_color="#2ecc71",
                command=lambda e=exam_name, c=class_selected: self.open_previous_exam_marksheet(e, c)
            )
            view_btn.pack(side="left", padx=5)

            delete_btn = ctk.CTkButton(
                row_frame,
                text="🗑 Delete",
                width=100,
                height=45,
                fg_color="#e74c3c",
                hover_color="#c0392b",
                command=lambda e=exam_name, c=class_selected: self.delete_previous_exam(e, c)
            )
            delete_btn.pack(side="left", padx=5)

        back_btn = ctk.CTkButton(
            self.content_panel,
            text="Back",
            command=self.return_to_home,
            width=150
        )
        back_btn.pack(pady=20)

    def open_previous_exam_marksheet(self, exam_name, class_name):
        # Clear the old view completely
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # Full screen mode
        self.menu_panel.grid_forget()
        self.grid_columnconfigure(0, weight=0, minsize=0)
        self.content_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # Get the exam data
        marks_data, summary_data = self.db.get_previous_exam_data(exam_name, class_name)

        # Determine the correct marksheet view based on class
        name_upper = class_name.upper().strip()

        if "PLAYGROUP" in name_upper or "PLAY GROUP" in name_upper:
            from ui_marksheet_playgroup import PlaygroupMarkSheetView
            self.current_view = PlaygroupMarkSheetView(self.content_panel, self.db, class_name, read_only=True, exam_name=exam_name, marks_data=marks_data, summary_data=summary_data)
        elif "PP1" in name_upper or "PRE-PRIMARY 1" in name_upper:
            from ui_marksheet_pp1 import PP1MarkSheetView
            self.current_view = PP1MarkSheetView(self.content_panel, self.db, class_name, read_only=True, exam_name=exam_name, marks_data=marks_data, summary_data=summary_data)
        elif "PP2" in name_upper or "PRE-PRIMARY 2" in name_upper:
            from ui_marksheet_pp2 import PP2MarkSheetView
            self.current_view = PP2MarkSheetView(self.content_panel, self.db, class_name, read_only=True, exam_name=exam_name, marks_data=marks_data, summary_data=summary_data)
        elif any(g in name_upper for g in ["GRADE 1", "GRADE 2", "GRADE 3"]):
            from ui_marksheet_lower import LowerMarkSheetView
            self.current_view = LowerMarkSheetView(self.content_panel, self.db, class_name, read_only=True, exam_name=exam_name, marks_data=marks_data, summary_data=summary_data)
        elif any(g in name_upper for g in ["GRADE 4", "GRADE 5", "GRADE 6"]):
            from ui_marksheet_primary import PrimaryMarkSheetView
            self.current_view = PrimaryMarkSheetView(self.content_panel, self.db, class_name, read_only=True, exam_name=exam_name, marks_data=marks_data, summary_data=summary_data)
        else:
            from ui_marksheet_junior import JuniorMarkSheetView
            self.current_view = JuniorMarkSheetView(self.content_panel, self.db, class_name, read_only=True, exam_name=exam_name, marks_data=marks_data, summary_data=summary_data)

        self.current_view.pack(fill="both", expand=True)

    def delete_previous_exam(self, exam_name, class_name):
        """Delete a previous exam"""
        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the exam '{exam_name}' for {class_name}? This action cannot be undone."
        ):
            self.db.delete_previous_exam(exam_name, class_name)
            messagebox.showinfo("Success", f"Exam '{exam_name}' has been deleted.")
            # Refresh the exam list
            self.show_previous_exams_selection(class_name)

    def show_marksheet_view(self, class_name):
        # 1. Clear the main panel
        for widget in self.content_panel.winfo_children():
            if widget != self.header_frame and widget != self.theme_frame:
                widget.destroy()

        # 2. Call the new MarkSheet class
        # This replaces all the manual code you would have written!
        self.marksheet = JuniorMarkSheetView(self.content_panel, self.db, class_name)
        self.marksheet.pack(fill="both", expand=True)

    # --- EVENTS / LOGIC ---
    def exit_app(self):
        """Cleanly closes the dashboard and the entire Python application"""
        self.destroy() # Closes the Window
        sys.exit()     # Tells Python to stop entirely

    def change_theme_event(self, selected_mode):
        """Handles the user changing the theme via the button from the drawing"""
        if selected_mode == "Light Mode":
            ctk.set_appearance_mode("Light")
            print("Switched to Light Mode")
        else:
            ctk.set_appearance_mode("Dark")
            print("Switched to Dark Mode")

    def dummy_event(self):
        """Temporary function so the buttons have commands without crashing"""
        print("Button Clicked - Feature coming soon!")

    def create_new_exam_all_classes(self):
        """Create a new exam for all marksheet types at once"""
        import json
        from datetime import datetime
        
        dialog = ctk.CTkInputDialog(
            text="Enter New Exam Title (for all classes):",
            title="Create New Exam - All Classes"
        )
        exam_title = dialog.get_input()
        
        if not exam_title:
            return
        
        exam_title = exam_title.strip()
        if not exam_title:
            messagebox.showwarning("Invalid Title", "Please enter a valid exam title.")
            return
        
        # Load school config
        school_config = self.load_school_config()
        
        # Store OLD exam titles before updating (to save as previous exams)
        grade_types = ["playgroup", "pp1", "pp2", "lower", "primary", "jss"]
        old_exam_titles = {}
        for grade_type in grade_types:
            old_exam_titles[grade_type] = school_config.get(f"{grade_type}_exam_title", "")
        
        # Update exam titles for all grade types in school_config.json
        for grade_type in grade_types:
            school_config[f"{grade_type}_exam_title"] = exam_title
        
        # Also update current_exam_title for junior marksheet
        old_exam_titles["current"] = school_config.get("current_exam_title", "")
        school_config["current_exam_title"] = exam_title
        
        # Save updated school config
        try:
            json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'school_config.json')
            with open(json_path, 'w') as f:
                json.dump(school_config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update school config: {e}")
            return
        
        # List of all marksheet types (use lowercase to match database)
        class_types = [
            ("playgroup", "playgroup"),
            ("pp1", "pp1"),
            ("pp2", "pp2"),
            ("Grade 1", "lower"),
            ("Grade 2", "lower"),
            ("Grade 3", "lower"),
            ("Grade 4", "primary"),
            ("Grade 5", "primary"),
            ("Grade 6", "primary"),
            ("Grade 7", "jss"),
            ("Grade 8", "jss"),
            ("Grade 9", "jss")
        ]
        
        success_count = 0
        failed_classes = []
        
        for class_name, grade_type in class_types:
            try:
                # Always get current marks from the marks table (don't skip if previous exists)
                table_name = self.get_table_name_for_grade(grade_type)
                marks_data = self.get_current_marks_for_class(class_name, table_name, grade_type)
                summary_data = json.dumps({"total_students": 0, "distribution": {}, "gender_counts": {}, "gender_totals": {}, "subject_averages": [], "has_history": False, "trend_text": "First Exam"})
                
                # Save to previous_exams table using the OLD exam title (not the new one)
                old_exam_title = old_exam_titles.get(grade_type, "")
                if old_exam_title:  # Only save if there was an old exam title
                    exam_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.db._cursor.execute(
                        "INSERT OR REPLACE INTO previous_exams (exam_name, class_name, exam_date, marks_data, summary_data) VALUES (?, ?, ?, ?, ?)",
                        (old_exam_title, class_name, exam_date, marks_data, summary_data)
                    )
                    self.db.conn.commit()
                
                # Clear current marks table for this class to start fresh with new exam
                try:
                    # Get admission numbers for students in this class
                    self.db._cursor.execute("SELECT adm_no FROM students WHERE grade = ?", (class_name,))
                    adm_nos = [row[0] for row in self.db._cursor.fetchall()]
                    
                    # Delete marks for these students
                    for adm_no in adm_nos:
                        self.db._cursor.execute(f"DELETE FROM {table_name} WHERE adm_no = ?", (adm_no,))
                    self.db.conn.commit()
                except Exception as e:
                    print(f"Error clearing marks for {class_name}: {e}")
                
                success_count += 1
                
            except Exception as e:
                failed_classes.append(f"{class_name}: {str(e)}")
                print(f"Error creating exam for {class_name}: {e}")
        
        # Show result
        if success_count > 0:
            message = f"Successfully created new exam '{exam_title}' for {success_count} classes.\nExam titles have been updated in school configuration."
            if failed_classes:
                message += f"\n\nFailed for:\n" + "\n".join(failed_classes[:5])
                if len(failed_classes) > 5:
                    message += f"\n... and {len(failed_classes) - 5} more"
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", f"Failed to create exam for all classes:\n" + "\n".join(failed_classes))

    def get_table_name_for_grade(self, grade_type):
        """Get the table name for a given grade type"""
        table_mapping = {
            "playgroup": "playgroup_marks",
            "pp1": "pp1_marks",
            "pp2": "pp2_marks",
            "lower": "lower_marks",
            "primary": "primary_marks",
            "jss": "marksheet"
        }
        return table_mapping.get(grade_type, "marksheet")

    def get_current_marks_for_class(self, class_name, table_name, grade_type):
        """Get current marks data for a class"""
        import json
        
        try:
            # Get subjects for this grade type
            school_config = self.load_school_config()
            subjects = school_config.get("subjects", {}).get(grade_type, [])
            
            if not subjects:
                # Default subjects if not in config
                default_subjects = {
                    "playgroup": ["MATH", "CREAT", "ENV"],
                    "pp1": ["MATH", "ENV", "PSYCH", "REL"],
                    "pp2": ["MATH", "ENV", "PSYCH", "REL"],
                    "lower": ["ENG", "KISW", "MAT", "ENV", "LIT", "CRE", "ART", "MOV"],
                    "primary": ["ENG", "KISW", "MATH", "SCIE", "AGRI", "SST", "CRE", "C/A", "PHE"],
                    "jss": ["MATH", "ENG", "KISW", "INT SCIE", "PRE-TECH", "SST", "CRE", "AGRI", "C/A"]
                }
                subjects = default_subjects.get(grade_type, [])
            
            # Build query - different structure for junior (marksheet table)
            if table_name == "marksheet":
                select_cols = ["s.name"]
                for subject in subjects:
                    clean = subject.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                    select_cols.append(f"m.{clean}_s")
                    select_cols.append(f"m.{clean}_r")
                    select_cols.append(f"m.{clean}_p")
                select_cols.append("m.total_points")
                select_cols.append("m.average_points")
                select_cols.append("m.rank")
            else:
                select_cols = ["s.name"]
                for subject in subjects:
                    clean = subject.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                    select_cols.append(f"m.{clean}_s")
                    select_cols.append(f"m.{clean}_r")
                select_cols.append("m.total_points")
                select_cols.append("m.average_level")
            
            col_str = ", ".join(select_cols)
            query = f"SELECT {col_str} FROM students s LEFT JOIN {table_name} m ON s.adm_no = m.adm_no WHERE s.grade = ?"
            
            self.db._cursor.execute(query, (class_name,))
            rows = self.db._cursor.fetchall()
            
            # Convert to JSON
            records = []
            for row in rows:
                record = list(row)
                records.append(record)
            
            return json.dumps(records)
            
        except Exception as e:
            print(f"Error getting current marks for {class_name}: {e}")
            return json.dumps([])

    def load_school_config(self):
        """Load school configuration from JSON"""
        try:
            json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'school_config.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

def show_dashboard(school_name="Freeman Tech Solutions"):
    # This allows you to test just this screen from ui_dashboard.py
    # Change the name here to see the top label update
    dashboard = Dashboard(school_name)
    dashboard.mainloop()

if __name__ == "__main__":
    show_dashboard()