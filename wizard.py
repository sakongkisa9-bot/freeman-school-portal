import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import os
from urllib.parse import urlparse

class SchoolSetupWizard(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        
        self.title("Global School Setup")
        self.geometry("500x700")
        self.db = db
        self.parent = parent
        self.attributes("-topmost", True)
        self.grab_set()
        
        # Determine correct directory for config files
        if getattr(__import__('sys'), 'frozen', False):
            # Running as executable
            self.BASE_DIR = __import__('sys')._MEIPASS
            self.USER_DATA_DIR = __import__('os').path.join(__import__('os').path.expanduser("~"), "FreemanSchoolPortal")
            __import__('os').makedirs(self.USER_DATA_DIR, exist_ok=True)
        else:
            # Running as script
            self.BASE_DIR = __import__('os').path.dirname(__import__('os').path.realpath(__file__))
            self.USER_DATA_DIR = self.BASE_DIR

        # Load existing config if available
        self.load_existing_config()
        
        # --- SCROLLABLE CONTAINER (In case we add many subjects) ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.scroll_frame, text="School Profile Setup", font=("Arial", 22, "bold")).pack(pady=10)

        # 1. School Name
        self.create_label("Official School Name:")
        self.name_entry = self.create_entry("e.g., SHINNERS ACADEMY")

        # 2. School Address
        self.create_label("Postal Address:")
        self.address_entry = self.create_entry("e.g., P.O. BOX 123, MATUNDA")

        # 3. Contacts
        self.create_label("School Contacts:")
        self.contact_entry = self.create_entry("e.g., 0712 345 678 / 0789 123 456")

        # 4. SUBJECT CONFIGURATION (The "Dynamic" part)
        ctk.CTkLabel(self.scroll_frame, text="Subject Setup (Comma Separated)", font=("Arial", 14, "bold"), text_color="#10b981").pack(pady=(20, 5))
        self.create_label("Playgroup subjects:")
        self.playgroup_subs = self.create_entry("LANG,MATH,CREAT...")
        # Pre-fill with your current defaults
        self.playgroup_subs.insert(0, "LANG, MATH, CREAT, ENV")

        self.create_label("PP1 Subjects:")
        self.pp1_subs = self.create_entry("LANG,MATH,ENV...")
        # Pre-fill with your current defaults
        self.pp1_subs.insert(0, "LANG, MATH, ENV, PSYCH, REL")

        self.create_label("PP2 Subjects:")
        self.pp2_subs = self.create_entry("LANG,MATH,ENV...")
        # Pre-fill with your current defaults
        self.pp2_subs.insert(0, "LANG, MATH, ENV, PSYCH, REL")

        self.create_label("lower Subjects (G1 - G3):")
        self.lower_subs = self.create_entry("Math, English, Kiswahili...")
        # Pre-fill with your current defaults
        self.lower_subs.insert(0, "ENG, KISW, MAT, ENV, LIT, CRE, ART, MOV")
        
        self.create_label("Primary Subjects (G4 - G6):")
        self.primary_subs = self.create_entry("Math, English, Kiswahili...")
        # Pre-fill with your current defaults
        self.primary_subs.insert(0, "ENG, KISW, MATH, SCIE, AGRI, SST, CRE, C/A, PHE")

        self.create_label("Junior Secondary Subjects (G7 - G9):")
        self.jss_subs = self.create_entry("Math, English, Pre-Tech...")
        self.jss_subs.insert(0, "MATH, ENG, KISW, INT SCIE, PRE-TECH, SST, CRE, AGRI, C/A")

        # 5. Cloud Portal Registration
        ctk.CTkLabel(self.scroll_frame, text="Cloud Portal Registration", font=("Arial", 14, "bold"), text_color="#10b981").pack(pady=(20, 5))
        self.create_label("Cloud Portal URL:")
        self.cloud_url_entry = self.create_entry("e.g., https://schoolportal.example.com or http://localhost:7000")
        ctk.CTkLabel(self.scroll_frame, text="Use a real reachable address, or localhost for a local cloud server.", font=("Arial", 10), text_color="gray").pack(padx=30, pady=(0, 10), anchor="w")
        self.create_label("Cloud School Code:")
        self.cloud_code_entry = self.create_entry("e.g., FREEMAN123")
        self.create_label("Cloud Teacher Username / Email:")
        self.cloud_teacher_entry = self.create_entry("e.g., teacher@example.com")
        self.create_label("Cloud Teacher Password:")
        self.cloud_password_entry = self.create_entry("Enter cloud portal password")

        # 6. Media (Logo/Signature)
        ctk.CTkLabel(self.scroll_frame, text="Branding Assets", font=("Arial", 14, "bold")).pack(pady=(20, 5))

        self.create_label("School Administrator Name:")
        self.admin_entry = self.create_entry("e.g., Mercy Chelimo (Headteacher) or Maxwell Kiptoo (Director)")

        # 7. System Security
        ctk.CTkLabel(self.scroll_frame, text="System Security", font=("Arial", 14, "bold"), text_color="#e74c3c").pack(pady=(20, 5))
        self.create_label("System Username:")
        self.system_username_entry = self.create_entry("e.g., admin")
        self.create_label("Administrator Password:")
        self.system_password_entry = self.create_entry("Enter administrator password")

        # 8. Payment Settings
        ctk.CTkLabel(self.scroll_frame, text="Payment & Licensing Settings", font=("Arial", 14, "bold"), text_color="#10b981").pack(pady=(20, 5))
        self.create_label("Installation Fee (KES):")
        self.installation_fee_entry = self.create_entry("e.g., 5000")
        self.installation_fee_entry.insert(0, "5000")
        
        self.create_label("Amount Per Student (KES):")
        self.amount_per_student_entry = self.create_entry("e.g., 100")
        self.amount_per_student_entry.insert(0, "100")
        
        self.create_label("Grace Period Days (to pay installation fee):")
        self.grace_period_entry = self.create_entry("e.g., 7")
        self.grace_period_entry.insert(0, "7")
        
        self.create_label("Free Trial Days (after installation fee paid):")
        self.trial_days_entry = self.create_entry("e.g., 30")
        self.trial_days_entry.insert(0, "30")
        
        self.create_label("Premium Period Days (after trial, per termly payment):")
        self.premium_days_entry = self.create_entry("e.g., 90")
        self.premium_days_entry.insert(0, "90")

        self.logo_path = ctk.StringVar()
        ctk.CTkButton(self.scroll_frame, text="📁 Browse Logo", command=lambda: self.pick_file(self.logo_path)).pack(pady=5)

        self.sig_path = ctk.StringVar()
        ctk.CTkButton(self.scroll_frame, text="✍️ Browse Signature", command=lambda: self.pick_file(self.sig_path)).pack(pady=5)

        # Save Button
        ctk.CTkButton(self, text="🚀 SAVE ALL SETTINGS", fg_color="#10b981", text_color="black",
                      font=("Arial Bold", 16), height=50, command=self.save_all).pack(fill="x", padx=20, pady=20)
        
        # Populate fields with existing configuration
        self.populate_fields_from_config()

    # --- HELPER UI METHODS ---
    def create_label(self, text):
        lbl = ctk.CTkLabel(self.scroll_frame, text=text, font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=30, pady=(10, 0))
        return lbl

    def create_entry(self, placeholder):
        ent = ctk.CTkEntry(self.scroll_frame, placeholder_text=placeholder, width=350)
        ent.pack(pady=5)
        return ent

    def pick_file(self, var):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            var.set(path)
            self.lift()

    def load_existing_config(self):
        """Load existing configuration and populate fields"""
        try:
            json_path = os.path.join(self.USER_DATA_DIR, 'school_config.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    config = json.load(f)
                
                # Store config to populate fields after they're created
                self.existing_config = config
        except Exception as e:
            print(f"Could not load existing config: {e}")
            self.existing_config = None
    
    def populate_fields_from_config(self):
        """Populate fields with existing configuration values"""
        if not hasattr(self, 'existing_config') or not self.existing_config:
            return
        
        config = self.existing_config
        
        # Populate school info
        if hasattr(self, 'name_entry') and config.get('school_name'):
            self.name_entry.delete(0, 'end')
            self.name_entry.insert(0, config['school_name'])
        
        if hasattr(self, 'address_entry') and config.get('address'):
            self.address_entry.delete(0, 'end')
            self.address_entry.insert(0, config['address'])
        
        if hasattr(self, 'contact_entry') and config.get('contacts'):
            self.contact_entry.delete(0, 'end')
            self.contact_entry.insert(0, config['contacts'])
        
        # Populate branding
        if hasattr(self, 'admin_entry') and config.get('school_administrator'):
            self.admin_entry.delete(0, 'end')
            self.admin_entry.insert(0, config['school_administrator'])
        
        if hasattr(self, 'logo_path') and config.get('logo'):
            self.logo_path.set(config['logo'])
        
        if hasattr(self, 'sig_path') and config.get('signatures', {}).get('headteacher'):
            self.sig_path.set(config['signatures']['headteacher'])
        
        # Populate cloud settings
        if hasattr(self, 'cloud_url_entry') and config.get('cloud_portal_url'):
            self.cloud_url_entry.delete(0, 'end')
            self.cloud_url_entry.insert(0, config['cloud_portal_url'])
        
        if hasattr(self, 'cloud_code_entry') and config.get('cloud_school_code'):
            self.cloud_code_entry.delete(0, 'end')
            self.cloud_code_entry.insert(0, config['cloud_school_code'])
        
        if hasattr(self, 'cloud_teacher_entry') and config.get('cloud_teacher_username'):
            self.cloud_teacher_entry.delete(0, 'end')
            self.cloud_teacher_entry.insert(0, config['cloud_teacher_username'])
        
        if hasattr(self, 'cloud_password_entry') and config.get('cloud_teacher_password'):
            self.cloud_password_entry.delete(0, 'end')
            self.cloud_password_entry.insert(0, config['cloud_teacher_password'])
        
        # Populate security settings
        if hasattr(self, 'system_username_entry') and config.get('system_username'):
            self.system_username_entry.delete(0, 'end')
            self.system_username_entry.insert(0, config['system_username'])
        
        if hasattr(self, 'system_password_entry') and config.get('system_password'):
            self.system_password_entry.delete(0, 'end')
            self.system_password_entry.insert(0, config['system_password'])
        
        # Populate payment settings
        if hasattr(self, 'installation_fee_entry') and config.get('installation_fee'):
            self.installation_fee_entry.delete(0, 'end')
            self.installation_fee_entry.insert(0, str(config['installation_fee']))
        
        if hasattr(self, 'amount_per_student_entry') and config.get('amount_per_student'):
            self.amount_per_student_entry.delete(0, 'end')
            self.amount_per_student_entry.insert(0, str(config['amount_per_student']))
        
        if hasattr(self, 'grace_period_entry') and config.get('grace_period_days'):
            self.grace_period_entry.delete(0, 'end')
            self.grace_period_entry.insert(0, str(config['grace_period_days']))
        
        if hasattr(self, 'trial_days_entry') and config.get('trial_days'):
            self.trial_days_entry.delete(0, 'end')
            self.trial_days_entry.insert(0, str(config['trial_days']))
        
        if hasattr(self, 'premium_days_entry') and config.get('premium_days'):
            self.premium_days_entry.delete(0, 'end')
            self.premium_days_entry.insert(0, str(config['premium_days']))
        
        # Populate subjects
        subjects = config.get('subjects', {})
        if hasattr(self, 'playgroup_subs') and subjects.get('playgroup'):
            self.playgroup_subs.delete(0, 'end')
            self.playgroup_subs.insert(0, ', '.join(subjects['playgroup']))
        
        if hasattr(self, 'pp1_subs') and subjects.get('pp1'):
            self.pp1_subs.delete(0, 'end')
            self.pp1_subs.insert(0, ', '.join(subjects['pp1']))
        
        if hasattr(self, 'pp2_subs') and subjects.get('pp2'):
            self.pp2_subs.delete(0, 'end')
            self.pp2_subs.insert(0, ', '.join(subjects['pp2']))
        
        if hasattr(self, 'lower_subs') and subjects.get('lower'):
            self.lower_subs.delete(0, 'end')
            self.lower_subs.insert(0, ', '.join(subjects['lower']))
        
        if hasattr(self, 'primary_subs') and subjects.get('primary'):
            self.primary_subs.delete(0, 'end')
            self.primary_subs.insert(0, ', '.join(subjects['primary']))
        
        if hasattr(self, 'jss_subs') and subjects.get('jss'):
            self.jss_subs.delete(0, 'end')
            self.jss_subs.insert(0, ', '.join(subjects['jss']))

    def normalize_cloud_url(self, url):
        url = (url or '').strip()
        if not url:
            return ''
        if '://' not in url:
            url = 'https://' + url
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('Enter a valid cloud portal URL starting with http:// or https://')
        return url.rstrip('/')

    def save_all(self):
        # Use USER_DATA_DIR for config files (works in both script and executable)
        json_path = os.path.join(self.USER_DATA_DIR, 'school_config.json')
            
        try:
            name = self.name_entry.get().upper()
            address = self.address_entry.get().upper()
            contacts = self.contact_entry.get()
            
            # FIX 2: Standardize subjects to UPPERCASE for DB compatibility
            # This prevents "Math" vs "MATH" issues in the database columns
            cloud_url = self.normalize_cloud_url(self.cloud_url_entry.get())
            grace_period_days = int(self.grace_period_entry.get())
            
            # Load existing config to preserve exam titles and other settings
            existing_config = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        existing_config = json.load(f)
                except:
                    pass
            
            config_data = {
                "school_name": name,
                "address": address,
                "contacts": contacts,
                "logo": self.logo_path.get(),
                "school_administrator": self.admin_entry.get().strip(),
                "signatures": {
                    "headteacher": self.sig_path.get()
                },
                "cloud_portal_url": cloud_url,
                "cloud_school_code": self.cloud_code_entry.get().strip(),
                "cloud_teacher_username": self.cloud_teacher_entry.get().strip(),
                "cloud_teacher_password": self.cloud_password_entry.get().strip(),
                # System Security Credentials
                "system_username": self.system_username_entry.get().strip(),
                "system_password": self.system_password_entry.get().strip(),
                # Payment & Licensing Settings
                "installation_fee": int(self.installation_fee_entry.get()),
                "amount_per_student": int(self.amount_per_student_entry.get()),
                "grace_period_days": grace_period_days,
                "trial_days": int(self.trial_days_entry.get()),
                "premium_days": int(self.premium_days_entry.get()),
                # Preserve existing exam titles or set defaults if they don't exist
                "playgroup_exam_title": existing_config.get("playgroup_exam_title", "PLAYGROUP ASSESSMENT REPORT"),
                "pp1_exam_title": existing_config.get("pp1_exam_title", "PP1 ASSESSMENT REPORT"),
                "pp2_exam_title": existing_config.get("pp2_exam_title", "PP2 ASSESSMENT REPORT"),
                "lower_exam_title": existing_config.get("lower_exam_title", "LOWER PRIMARY ASSESSMENT"),
                "primary_exam_title": existing_config.get("primary_exam_title", "PRIMARY SCHOOL MERIT LIST"),
                "jss_exam_title": existing_config.get("jss_exam_title", "JUNIOR SECONDARY ASSESSMENT"),
                "current_exam_title": existing_config.get("current_exam_title", "ASSESSMENT"),
                "portal_open": existing_config.get("portal_open", False),

                "subjects": {
                    "playgroup": [s.strip().upper() for s in self.playgroup_subs.get().split(',') if s.strip()],
                    "pp1": [s.strip().upper() for s in self.pp1_subs.get().split(',') if s.strip()],
                    "pp2": [s.strip().upper() for s in self.pp2_subs.get().split(',') if s.strip()],
                    "lower": [s.strip().upper() for s in self.lower_subs.get().split(',') if s.strip()],
                    "primary": [s.strip().upper() for s in self.primary_subs.get().split(',') if s.strip()],
                    "jss": [s.strip().upper() for s in self.jss_subs.get().split(',') if s.strip()]
                }
            }

            # Save the file
            with open(json_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            # Initialize license status in database
            try:
                self.db.initialize_license_status(grace_period_days)
                print("License status initialized with grace period")
            except Exception as db_error:
                print(f"Warning: Could not initialize license status: {db_error}")
            
            # DEBUG: Very helpful for you to see where it actually saved!
            print(f"SUCCESS: Config saved to: {os.path.abspath(json_path)}")

            messagebox.showinfo("Success", f"Settings saved to {json_path}\n\nLicense initialized with {grace_period_days} days grace period.")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")