# main.py
import customtkinter as ctk
from PIL import Image
import security
import os
import random

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
        security.show_login()

if __name__ == "__main__":
    app = SplashScreen()
    app.mainloop()

    
import customtkinter as ctk
from security import LoginPage   # Assuming you saved the login class here
from splash import SplashScreen2 # Assuming you saved the splash class here
from ui_dashboard import Dashboard     # Your beautiful registry GUI

def run_freeman_os():

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
    run_freeman_os()




