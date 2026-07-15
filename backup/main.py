# main.py
import customtkinter as ctk
from PIL import Image
import security
import os
import random
import sys
import json
from license_manager import check_and_activate_license

# LICENSE CHECK - Must pass before application can start
def check_license_before_start():
    """Check license validity before allowing application to start"""
    is_allowed, message = check_and_activate_license()
    
    if not is_allowed:
        # Show error dialog and exit
        root = ctk.CTk()
        root.title("License Error")
        root.geometry("600x400")
        
        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (600 // 2)
        y = (screen_height // 2) - (400 // 2)
        root.geometry(f"600x400+{x}+{y}")
        root.resizable(False, False)
        
        # Error message frame
        frame = ctk.CTkFrame(root)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Error icon/text
        ctk.CTkLabel(frame, text="⚠️ LICENSE ERROR", font=("Arial Bold", 24), 
                   text_color="#e74c3c").pack(pady=(20, 10))
        
        # Error message
        msg_label = ctk.CTkLabel(frame, text=message, font=("Arial", 12), 
                                wraplength=500, justify="center")
        msg_label.pack(pady=20)
        
        # Exit button
        ctk.CTkButton(frame, text="Exit", command=root.destroy, 
                     width=150, height=40, fg_color="#e74c3c").pack(pady=20)
        
        root.mainloop()
        sys.exit(1)
    
    return True


def check_terms_agreement():
    """Check if user has agreed to Terms of Use"""
    try:
        # Handle both development and executable environments
        if getattr(sys, 'frozen', False):
            USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        else:
            USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
        
        config_path = os.path.join(USER_DATA_DIR, "school_config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                # Check if terms have been accepted and version matches
                current_terms_version = "1.0"
                accepted_version = config.get("terms_accepted_version", "")
                if accepted_version == current_terms_version:
                    return True
    except:
        pass
    
    return False


def show_terms_dialog():
    """Show Terms of Use agreement dialog"""
    dialog = ctk.CTk()
    dialog.title("Terms of Use Agreement")
    dialog.geometry("800x600")
    
    # Center the window
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    x = (screen_width // 2) - (800 // 2)
    y = (screen_height // 2) - (600 // 2)
    dialog.geometry(f"800x600+{x}+{y}")
    dialog.resizable(False, False)
    
    # Main frame
    main_frame = ctk.CTkFrame(dialog)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Title
    ctk.CTkLabel(main_frame, text="TERMS OF USE", font=("Arial Bold", 24), 
                text_color="#2c3e50").pack(pady=(10, 20))
    
    # Scrollable text area for terms
    from customtkinter import CTkScrollableFrame
    scroll_frame = CTkScrollableFrame(main_frame, width=700, height=350)
    scroll_frame.pack(fill="both", expand=True, pady=(0, 20))
    
    terms_text = """
1. OWNERSHIP AND INTELLECTUAL PROPERTY
This software (the "School management system") is the sole and exclusive property of Freeman-Tech Solutions. The School acknowledges that it is being granted a limited, non-exclusive, non-transferable, and revocable license to use the System for its internal academic management purposes. The School does not acquire any ownership interest, title, or rights in the System.

2. RESTRICTIONS AND PROHIBITED USE
The School shall not, and shall not permit any third party to:
• Decompile, disassemble, reverse-engineer, or attempt to derive the source code or underlying logic of the System.
• Modify, adapt, or create derivative works based on the System.
• Rent, lease, sublicense, or distribute the System to any other school or entity. Any attempt to bypass security features, license keys, or update mechanisms will result in the immediate termination of this license.

3. TRIAL PERIOD AND LICENSING
• Trial Period: A School may be granted a Free Trial period. If the System is installed during an academic term, the Free Trial shall remain active until the conclusion of that current academic term.
• Transition to Premium: Upon the conclusion of the Trial Period, the School must pay the agreed-upon Premium License Fee to maintain access to the System.
• Renewal: Failure to remit payment within 14 days of the start of the following term will result in the suspension of all system features, including cloud synchronization, report generation, and data export capabilities.

4. UPDATES, MAINTENANCE, AND SUPPORT
• Automatic Updates: The System may periodically connect to Freeman-Tech Solutions' servers to check for and apply updates, security patches, or feature enhancements. The School consents to these automatic updates to ensure continued functionality.
• Support Services: Basic support for system errors is included during the active license period. Major feature requests or personalized customizations outside the standard scope of the System are subject to separate negotiation and additional fees.
• Disclaimer: Freeman-Tech Solutions provides the System on an "as-is" basis and does not guarantee that access will be 100% uninterrupted.

5. LIMITATION OF LIABILITY
Freeman-Tech Solutions shall not be held liable for any data loss, administrative errors, or hardware issues resulting from the use of the System. The School is responsible for maintaining its own periodic backups of all academic data.

6. TERMINATION
This license remains in effect until terminated. Freeman-Tech Solutions reserves the right to terminate this license if the School fails to comply with any terms herein, specifically regarding payment or unauthorized redistribution. Upon termination, the School must cease all use of the System immediately.
"""
    
    terms_label = ctk.CTkLabel(scroll_frame, text=terms_text, font=("Arial", 11), 
                               justify="left", wraplength=650)
    terms_label.pack(pady=10, padx=10, anchor="w")
    
    # Checkbox for agreement
    agree_var = ctk.BooleanVar(value=False)
    checkbox = ctk.CTkCheckBox(main_frame, text="I have read and agree to the Terms of Use", 
                             variable=agree_var, font=("Arial", 12))
    checkbox.pack(pady=(0, 20))
    
    # Buttons
    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x")
    
    def on_agree():
        if agree_var.get():
            # Save agreement to config
            try:
                if getattr(sys, 'frozen', False):
                    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
                else:
                    USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
                
                config_path = os.path.join(USER_DATA_DIR, "school_config.json")
                
                config = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                
                config["terms_accepted_version"] = "1.0"
                config["terms_accepted_date"] = "2026-06-17"
                
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
            except:
                pass
            
            dialog.destroy()
        else:
            ctk.CTkMessageBox.show_warning("Agreement Required", 
                                         "You must agree to the Terms of Use to continue.")
    
    def on_decline():
        ctk.CTkMessageBox.showinfo("Exit", "You must agree to the Terms of Use to use this software.")
        sys.exit(1)
    
    agree_btn = ctk.CTkButton(button_frame, text="I Agree", command=on_agree, 
                              width=150, height=40, fg_color="#27ae60", hover_color="#219150")
    agree_btn.pack(side="right", padx=5)
    
    decline_btn = ctk.CTkButton(button_frame, text="Decline", command=on_decline, 
                                width=150, height=40, fg_color="#e74c3c", hover_color="#c0392b")
    decline_btn.pack(side="right", padx=5)
    
    dialog.mainloop()

class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Window Setup
        self.overrideredirect(True)
        width, height = 600, 450 # Increased height slightly for the bar
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}")
# --- NEW: Bottom Frame for Text and Bar ---
        # Change 'fg_color' to any color you want (e.g., "#2b2b2b", "gray10", or "blue")
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#a232a8", corner_radius=0)
        self.bottom_frame.pack(fill="x", side="bottom")


        # 2. Assets & Status Messages
        self.assets_path = os.path.join(os.path.dirname(__file__), "assets")
        self.images = ["splash1.jpg", "splash2.jpg", "splash3.jpg"]
        self.status_messages = [
            "Initializing Freeman Engine...",
            "Loading Database...",
            "Checking Security Protocols...",
            "Syncing Grade Rubrics...",
            "Optimizing Dashboard...",
            "Finalizing Startup..."
        ]
        self.current_img_idx = 0
        self.progress_val = 0

        # 3. UI Elements
        # Image Display (Top Part)
        self.img_label = ctk.CTkLabel(self, text="")
        self.img_label.pack(expand=True, fill="both")

        # Status Text (Now inside bottom_frame)
        self.status_label = ctk.CTkLabel(self.bottom_frame, text="Starting...", font=("Arial", 14))
        self.status_label.pack(pady=(15, 5))

        # Loading Bar (Now inside bottom_frame)
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, width=400, progress_color="#1f6aa5")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

        # Percentage Label (Now inside bottom_frame)
        self.percentage_label = ctk.CTkLabel(self.bottom_frame, text="0%", font=("Arial Bold", 12))
        self.percentage_label.pack(pady=(0, 15))
        
        # 4. Start the logic
        self.update_slideshow()
        self.update_progress()

    def update_slideshow(self):
        """Switches images every 3 seconds"""
        if self.current_img_idx < len(self.images):
            img_path = os.path.join(self.assets_path, self.images[self.current_img_idx])
            try:
                raw_img = Image.open(img_path)
                ctk_img = ctk.CTkImage(raw_img, size=(600, 350))
                self.img_label.configure(image=ctk_img)
                self.current_img_idx += 1
                self.after(3000, self.update_slideshow)
            except:
                self.current_img_idx += 1
                self.after(3000, self.update_slideshow)

    def update_progress(self):
        """Handles the 1% to 100% logic and status text"""
        if self.progress_val <= 1.0:
            # Update the bar and percentage text
            self.progress_bar.set(self.progress_val)
            self.percentage_label.configure(text=f"{int(self.progress_val * 100)}%")
            
            # Change status text randomly to look like it's "thinking"
            if int(self.progress_val * 100) % 20 == 0:
                self.status_label.configure(text=random.choice(self.status_messages))
            
            # Increment progress (0.01 = 1%)
            # It will take about 9 seconds total (matches 3 images x 3 seconds)
            self.progress_val += 0.01
            self.after(90, self.update_progress) 
        else:
            self.finish_splash()

    def finish_splash(self):
        self.destroy()
        # Note: security.show_login() doesn't exist, this splash screen is not used in the main flow

import customtkinter as ctk
from security import LoginPage   # Assuming you saved the login class here
from splash import SplashScreen2 # Assuming you saved the splash class here
from ui_dashboard import Dashboard     # Your beautiful registry GUI

def run_freeman_os():
    # Check license before starting application
    check_license_before_start()
    
    # Check Terms of Use agreement
    if not check_terms_agreement():
        show_terms_dialog()

    # STEP 1: OPEN LOGIN
    login = LoginPage()
    login.mainloop() 
    
    if login.success:
    # The code PAUSES here until login.destroy() is called inside the Login class
    
    # STEP 2: IF LOGIN SUCCESSFUL, SHOW ANIMATED SPLASH
    # (In your Login class, ensure you only call self.destroy() if credentials are correct)
       splash = SplashScreen2()
       splash.mainloop()

    # STEP 3: LAUNCH THE HOMEPAGE
       app = Dashboard()
       app.mainloop()
    else:
        # If they hit "X" or failed, the script just ends here
        print("Login cancelled or failed. System shutting down.")

if __name__ == "__main__":
    # Show initial splash screen
    app = SplashScreen()
    app.mainloop()
    
    # Then run the main application (login → splashscreen2 → dashboard)
    run_freeman_os()




