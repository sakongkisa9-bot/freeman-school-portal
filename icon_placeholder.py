"""
Icon Creation Script for Freeman School Portal
Creates a simple icon as placeholder - replace with your actual designed icon
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_icon():
    """Create a placeholder icon for the executable"""
    
    # Create a 256x256 image (standard icon size)
    size = 256
    img = Image.new('RGBA', (size, size), (240, 240, 240, 255))  # Off-white background
    draw = ImageDraw.Draw(img)
    
    # Draw circular border
    border_color = (70, 130, 180, 255)  # Brushed blue
    border_width = 15
    draw.ellipse([border_width, border_width, size-border_width, size-border_width], 
                 outline=border_color, width=border_width)
    
    # Draw stylized 'F' shape
    f_color = (100, 149, 237, 255)  # Cornflower blue (metallic blue)
    
    # Vertical stem of F
    stem_x = 80
    stem_width = 30
    stem_top = 60
    stem_bottom = 200
    draw.rectangle([stem_x, stem_top, stem_x + stem_width, stem_bottom], 
                   fill=f_color)
    
    # Top horizontal bar
    top_bar_y = 70
    top_bar_height = 25
    top_bar_start = stem_x + stem_width
    top_bar_end = 180
    draw.rectangle([top_bar_start, top_bar_y, top_bar_end, top_bar_y + top_bar_height], 
                   fill=f_color)
    
    # Middle horizontal bar
    mid_bar_y = 130
    mid_bar_height = 25
    mid_bar_start = stem_x + stem_width
    mid_bar_end = 160
    draw.rectangle([mid_bar_start, mid_bar_y, mid_bar_end, mid_bar_y + mid_bar_height], 
                   fill=f_color)
    
    # Add circuit-like dots on the bars
    dot_color = (255, 215, 0, 255)  # Gold/yellow for glowing effect
    dot_radius = 6
    
    # Dots on top bar
    draw.ellipse([top_bar_end - 15, top_bar_y + 5, top_bar_end - 3, top_bar_y + 17], 
                 fill=dot_color)
    draw.ellipse([top_bar_end + 5, top_bar_y + 5, top_bar_end + 17, top_bar_y + 17], 
                 fill=dot_color)
    
    # Dots on middle bar
    draw.ellipse([mid_bar_end - 15, mid_bar_y + 5, mid_bar_end - 3, mid_bar_y + 17], 
                 fill=dot_color)
    
    # Simple lightbulb shape in the stem
    bulb_center_x = stem_x + stem_width // 2
    bulb_center_y = 165
    bulb_radius = 12
    draw.ellipse([bulb_center_x - bulb_radius, bulb_center_y - bulb_radius,
                  bulb_center_x + bulb_radius, bulb_center_y + bulb_radius],
                 fill=(255, 255, 0, 255))  # Yellow bulb
    
    # Add glow effect (simple circles)
    glow_color = (255, 255, 0, 100)
    draw.ellipse([bulb_center_x - bulb_radius - 5, bulb_center_y - bulb_radius - 5,
                  bulb_center_x + bulb_radius + 5, bulb_center_y + bulb_radius + 5],
                 fill=glow_color)
    
    # Save as PNG
    icon_path = "freeman_icon.png"
    img.save(icon_path, "PNG")
    print(f"Placeholder icon created: {icon_path}")
    print("Replace this with your actual designed icon for best results")
    
    return icon_path

def create_ico_from_png(png_path):
    """Convert PNG to ICO format for Windows executable"""
    try:
        img = Image.open(png_path)
        
        # Create different sizes for the ICO file
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img_sizes = []
        
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            img_sizes.append(resized)
        
        # Save as ICO
        ico_path = "freeman_icon.ico"
        img_sizes[0].save(ico_path, 
                         format='ICO',
                         sizes=[(img.width, img.height) for img in img_sizes])
        
        print(f"ICO file created: {ico_path}")
        return ico_path
        
    except Exception as e:
        print(f"Error creating ICO: {e}")
        return None

if __name__ == "__main__":
    print("Creating Freeman School Portal icon...")
    png_path = create_placeholder_icon()
    ico_path = create_ico_from_png(png_path)
    
    if ico_path:
        print(f"\nIcon files created successfully!")
        print(f"PNG: {png_path}")
        print(f"ICO: {ico_path}")
        print("\nFor production use, replace freeman_icon.png with your professionally designed icon.")
