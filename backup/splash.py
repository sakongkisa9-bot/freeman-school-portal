import customtkinter as ctk
import time
from PIL import Image, ImageDraw, ImageFont

class SplashScreen2(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.overrideredirect(True) # Professional "No-Bar" look
        self.geometry("600x400+400+200") 
        self.configure(fg_color="#0d1117") # Deep GitHub-style dark blue/black

        # Create diagonal watermark using PIL
        watermark_img = Image.new('RGBA', (600, 400), (13, 17, 23, 0))
        watermark_draw = ImageDraw.Draw(watermark_img)
        try:
            font = ImageFont.truetype("arial.ttf", 100)
        except:
            font = ImageFont.load_default()
        watermark_draw.text((50, 150), "FREEMAN", fill=(26, 58, 74, 80), font=font)
        watermark_rotated = watermark_img.rotate(-45, expand=False)
        self.watermark_photo = ctk.CTkImage(watermark_rotated, size=(600, 400))
        self.watermark_label = ctk.CTkLabel(self, image=self.watermark_photo, text="")
        self.watermark_label.place(x=0, y=0)

        # 1. THE LOGO / BRANDING
        self.brand_label = ctk.CTkLabel(self, text="FREEMAN TECH SOLUTIONS", 
                                        font=("Orbitron", 28, "bold"), 
                                        text_color="#3498db")
        self.brand_label.pack(pady=(100, 5))
        
        self.tagline = ctk.CTkLabel(self, text="Innovating Education Management", 
                                    font=("Arial", 12), text_color="gray")
        self.tagline.pack(pady=(0, 40))

        # 2. THE STATUS TEXT (Updates during loading)
        self.status_label = ctk.CTkLabel(self, text="System Booting...", 
                                         font=("Arial", 11), text_color="#58a6ff")
        self.status_label.pack(pady=(20, 5))

        # 3. THE PROGRESS BAR
        self.progress = ctk.CTkProgressBar(self, width=400, height=12, 
                                           progress_color="#3498db", 
                                           fg_color="#21262d",
                                           corner_radius=10)
        self.progress.set(0)
        self.progress.pack(pady=10)

        # Start the "Fake" Loading Sequence
        self.after(500, self.run_loading_animation)

    def run_loading_animation(self):
        """Creates a smooth, realistic loading experience"""
        steps = [
            (0.15, "Initializing Core Modules..."),
            (0.35, "Connecting to Freeman Secure Server..."),
            (0.60, "Loading Class Registries..."),
            (0.85, "Optimizing UI Layout..."),
            (1.0, "Ready to Launch!")
        ]

        for val, msg in steps:
            self.status_label.configure(text=msg)
            self.progress.set(val)
            self.update() # Refreshes the screen so the teacher sees the bar move
            time.sleep(0.6) # Controls the speed of the splash

        self.after(600, self.enter_app)

    def enter_app(self):
        self.destroy()
        print("Splash Complete. Entering Freeman OS...")
        # Your next line will be: self.app = Dashboard()
if __name__ == "__main__":
    app = SplashScreen2()
    app.mainloop()