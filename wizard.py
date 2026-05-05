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
        
        self.logo_path = ctk.StringVar()
        ctk.CTkButton(self.scroll_frame, text="📁 Browse Logo", command=lambda: self.pick_file(self.logo_path)).pack(pady=5)
        
        self.sig_path = ctk.StringVar()
        ctk.CTkButton(self.scroll_frame, text="✍️ Browse Signature", command=lambda: self.pick_file(self.sig_path)).pack(pady=5)

        # Save Button
        ctk.CTkButton(self, text="🚀 SAVE ALL SETTINGS", fg_color="#10b981", text_color="black",
                      font=("Arial Bold", 16), height=50, command=self.save_all).pack(fill="x", padx=20, pady=20)

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
        # FIX 1: Use a reliable path. 
        # If your script is in a subfolder, use .. to go up to the root project folder
        project_dir = os.path.dirname(os.path.realpath(__file__))
        json_path = os.path.join(project_dir, 'school_config.json')
            
        try:
            name = self.name_entry.get().upper()
            address = self.address_entry.get().upper()
            contacts = self.contact_entry.get()
            
            # FIX 2: Standardize subjects to UPPERCASE for DB compatibility
            # This prevents "Math" vs "MATH" issues in the database columns
            cloud_url = self.normalize_cloud_url(self.cloud_url_entry.get())
            config_data = {
                "school_name": name,
                "address": address,
                "contacts": contacts,
                "logo": self.logo_path.get(),
                "signatures": {
                    "headteacher": self.sig_path.get()
                },
                "cloud_portal_url": cloud_url,
                "cloud_school_code": self.cloud_code_entry.get().strip(),
                "cloud_teacher_username": self.cloud_teacher_entry.get().strip(),
                "cloud_teacher_password": self.cloud_password_entry.get().strip(),
                # Added Exam Titles so the Playgroup view knows what to display
                "playgroup_exam_title": "PLAYGROUP ASSESSMENT REPORT",
                "primary_exam_title": "PRIMARY SCHOOL MERIT LIST",
                "jss_exam_title": "JUNIOR SECONDARY ASSESSMENT",
                
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
            
            # DEBUG: Very helpful for you to see where it actually saved!
            print(f"SUCCESS: Config saved to: {os.path.abspath(json_path)}")

            messagebox.showinfo("Success", f"Settings saved to {json_path}")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")