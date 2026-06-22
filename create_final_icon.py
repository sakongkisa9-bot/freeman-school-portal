"""
Create a proper Windows icon file for the executable
This creates a high-quality icon that will actually work
"""

from PIL import Image, ImageDraw
import os

def create_proper_icon():
    """Create a proper Windows icon with multiple sizes"""
    
    print("Creating proper Windows icon...")
    
    # Create icon at different sizes
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # Create image
        img = Image.new('RGBA', (size, size), (240, 240, 240, 255))
        draw = ImageDraw.Draw(img)
        
        # Scale dimensions based on size
        scale = size / 256.0
        border_width = max(1, int(15 * scale))
            
        # Draw circular border
        margin = border_width
        draw.ellipse([margin, margin, size-margin, size-margin], 
                     outline=(70, 130, 180, 255), width=border_width)
        
        # Draw stylized 'F' shape
        f_color = (100, 149, 237, 255)
        
        # Vertical stem
        stem_x = int(80 * scale)
        stem_width = max(2, int(30 * scale))
        stem_top = int(60 * scale)
        stem_bottom = int(200 * scale)
        draw.rectangle([stem_x, stem_top, stem_x + stem_width, stem_bottom], 
                       fill=f_color)
        
        # Top horizontal bar
        top_bar_y = int(70 * scale)
        top_bar_height = max(2, int(25 * scale))
        top_bar_start = stem_x + stem_width
        top_bar_end = int(180 * scale)
        draw.rectangle([top_bar_start, top_bar_y, top_bar_end, top_bar_y + top_bar_height], 
                       fill=f_color)
        
        # Middle horizontal bar
        mid_bar_y = int(130 * scale)
        mid_bar_height = max(2, int(25 * scale))
        mid_bar_start = stem_x + stem_width
        mid_bar_end = int(160 * scale)
        draw.rectangle([mid_bar_start, mid_bar_y, mid_bar_end, mid_bar_y + mid_bar_height], 
                       fill=f_color)
        
        # Add circuit dots (only on larger sizes)
        if size >= 32:
            dot_color = (255, 215, 0, 255)
            dot_radius = max(1, int(6 * scale))
            
            # Dots on top bar
            draw.ellipse([top_bar_end - dot_radius*2, top_bar_y + dot_radius, 
                          top_bar_end, top_bar_y + dot_radius*3], fill=dot_color)
            
            # Dots on middle bar  
            draw.ellipse([mid_bar_end - dot_radius*2, mid_bar_y + dot_radius,
                          mid_bar_end, mid_bar_y + dot_radius*3], fill=dot_color)
        
        # Lightbulb (only on larger sizes)
        if size >= 48:
            bulb_center_x = stem_x + stem_width // 2
            bulb_center_y = int(165 * scale)
            bulb_radius = max(2, int(12 * scale))
            draw.ellipse([bulb_center_x - bulb_radius, bulb_center_y - bulb_radius,
                          bulb_center_x + bulb_radius, bulb_center_y + bulb_radius],
                         fill=(255, 255, 0, 255))
        
        images.append(img)
    
    # Save as ICO with all sizes using PIL's ICO format
    ico_path = "freeman_icon.ico"
    
    # Use the largest image as the base and save with all sizes
    images[-1].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in images])
    
    # Check file size
    file_size = os.path.getsize(ico_path)
    print(f"Icon created: {ico_path}")
    print(f"File size: {file_size} bytes")
    print(f"Includes sizes: {sizes}")
    
    if file_size < 1000:
        print("WARNING: Icon file is too small. Trying alternative method...")
        # Try saving each size individually
        images[0].save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
        file_size = os.path.getsize(ico_path)
        print(f"Alternative icon size: {file_size} bytes")
    
    return ico_path

if __name__ == "__main__":
    create_proper_icon()
