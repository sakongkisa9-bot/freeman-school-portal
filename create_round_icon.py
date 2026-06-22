from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def create_round_icon():
    """Create a high-quality round icon from scratch at high resolution"""
    
    # Create ultra-high resolution base image
    base_size = 1024  # Ultra-high resolution for crisp rendering
    img = Image.new('RGBA', (base_size, base_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Create circular background with gradient effect
    margin = 20
    center = base_size // 2
    radius = (base_size // 2) - margin
    
    # Draw main circle with blue gradient (simulated with concentric circles)
    for i in range(radius, 0, -2):
        alpha = int(255 * (i / radius))
        color = (52, 152, 219, alpha)  # Blue gradient
        draw.ellipse([center - i, center - i, center + i, center + i], fill=color)
    
    # Add darker border
    draw.ellipse([center - radius, center - radius, center + radius, center + radius], 
                 outline=(41, 128, 185, 255), width=8)
    
    # Add "F" letter in center
    try:
        # Try to use a larger bold font
        font_size = 500
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 500)
        except:
            font = ImageFont.load_default()
    
    text = "F"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = center - (text_width // 2)
    y = center - (text_height // 2) - 30
    
    # Draw text with shadow for depth
    draw.text((x + 4, y + 4), text, font=font, fill=(0, 0, 0, 80))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Add "FREEMAN" text at bottom
    try:
        small_font = ImageFont.truetype("arialbd.ttf", 80)
    except:
        try:
            small_font = ImageFont.truetype("arial.ttf", 80)
        except:
            small_font = ImageFont.load_default()
    
    school_text = "FREEMAN"
    bbox = draw.textbbox((0, 0), school_text, font=small_font)
    text_width = bbox[2] - bbox[0]
    x = center - (text_width // 2)
    y = center + 200
    draw.text((x, y), school_text, font=small_font, fill=(255, 255, 255, 255))
    
    # Apply slight sharpening for crispness
    img = img.filter(ImageFilter.SHARPEN)
    
    # Save as PNG first
    png_path = "freeman_icon_round.png"
    img.save(png_path, "PNG", optimize=True)
    print(f"Created round icon PNG: {png_path}")
    
    # Create multi-size ICO file with high-quality resampling
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256), (512, 512)]
    icon_images = []
    
    for icon_size in icon_sizes:
        # Resize image for this size with high-quality resampling
        resized = img.resize(icon_size, Image.Resampling.LANCZOS)
        # Apply slight sharpening to smaller sizes to maintain clarity
        if icon_size[0] < 128:
            resized = resized.filter(ImageFilter.SHARPEN)
        icon_images.append(resized)
    
    # Save as ICO with proper format using PIL's ICO saving
    ico_path = "freeman_icon_round.ico"
    # Use the largest image as the base and embed other sizes
    icon_images[-1].save(
        ico_path, 
        format='ICO',
        sizes=icon_sizes,
        append_images=icon_images[:-1]
    )
    print(f"Created round icon ICO: {ico_path} with sizes: {icon_sizes}")
    
    return ico_path

if __name__ == "__main__":
    create_round_icon()
    print("\nRound icon created successfully!")
    print("Files created:")
    print("  - freeman_icon_round.png (for preview)")
    print("  - freeman_icon_round.ico (for executable)")
    print("\nCreated from scratch at 1024px resolution for maximum clarity.")
