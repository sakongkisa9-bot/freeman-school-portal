import customtkinter as ctk
from PIL import Image
import os
import json

class LoginPage(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.success = False
        
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
        
        # --- 1. WINDOW CONFIGURATION & CENTERING ---
        self.title("Freeman Tech Solutions - Login")
        
        window_width = 800
        window_height = 450
        
        # Calculate coordinates to center the window on the screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.resizable(False, False)

        # --- 2. ASSET PATHS ---
        # Getting the folder where this script is saved
        current_dir = os.path.dirname(os.path.realpath(__file__))
        
        # Logo path
        logo_path = os.path.join(current_dir, "assets", "splash2.jpg")
        # Icon paths
        user_icon_path = os.path.join(current_dir, "icons", "user.png")
        lock_icon_path = os.path.join(current_dir, "icons", "locked-computer.png")

        # --- 3. CREATE UI ELEMENTS ---
        # Left side for Logo, Right side for Login
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- LEFT PANEL (Logo) ---
        try:
            logo_img = ctk.CTkImage(Image.open(logo_path), size=(280, 280))
            self.logo_label = ctk.CTkLabel(self, image=logo_img, text="")
            self.logo_label.grid(row=0, column=0, padx=20, pady=20)
        except Exception as e:
            print(f"Error loading logo: {e}")
            self.logo_label = ctk.CTkLabel(self, text="LOGO MISSING")
            self.logo_label.grid(row=0, column=0)

        # --- RIGHT PANEL (Form) ---
        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.grid(row=0, column=1, padx=40, sticky="nsew")

        self.title_label = ctk.CTkLabel(self.form_frame, text="LOG IN PAGE", font=("Arial Bold", 28))
        self.title_label.pack(pady=(60, 30))

        # Username Input (with Icon logic)
        try:
            u_icon = ctk.CTkImage(Image.open(user_icon_path), size=(20, 20))
            self.user_entry = ctk.CTkEntry(self.form_frame, placeholder_text="Username", 
                                           width=280, height=35)
        except:
            self.user_entry = ctk.CTkEntry(self.form_frame, placeholder_text="Username", 
                                           width=280, height=35)
        self.user_entry.pack(pady=10)

        # Password Input
        self.pass_entry = ctk.CTkEntry(self.form_frame, placeholder_text="Password", 
                                       show="*", width=280, height=35)
        self.pass_entry.pack(pady=10)

        # Login Button
        self.login_btn = ctk.CTkButton(self.form_frame, text="Login", 
                                       command=self.handle_login, width=150, height=40)
        self.login_btn.pack(pady=30)

        # --- FOOTER SLOGAN ---
        self.slogan = ctk.CTkLabel(self, 
                                   text="Freeman Tech Solutions: Transforming Schools to Modern Technology", 
                                   font=("Arial Italic", 11), text_color="gray")
        self.slogan.place(relx=0.5, rely=0.95, anchor="center")

    def handle_login(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        
        # Load credentials from school_config.json
        try:
            # Use USER_DATA_DIR for config files (works in both script and executable)
            json_path = os.path.join(self.USER_DATA_DIR, 'school_config.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    config = json.load(f)
                    config_username = config.get('system_username', 'admin')
                    config_password = config.get('system_password', '1234')
            else:
                # Fallback to default credentials if config doesn't exist
                config_username = 'admin'
                config_password = '1234'
        except Exception as e:
            print(f"Error loading config: {e}")
            # Fallback to default credentials
            config_username = 'admin'
            config_password = '1234'
        
        # Check credentials
        if username == config_username and password == config_password:
            self.success = True
            print("Login Successful!")
            self.destroy() # This will close the login and let main.py continue
        else:
            print("invalid credentials")

