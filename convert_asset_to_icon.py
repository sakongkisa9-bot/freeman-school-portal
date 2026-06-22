"""
Convert an existing asset image to icon format
"""

from PIL import Image
import os

def convert_asset_to_icon():
    """Convert splash1.png to icon format"""
    
    asset_path = "assets/splash1.png"
    if not os.path.exists(asset_path):
        print(f"Asset not found: {asset_path}")
        return None
    
    # Open the image
    img = Image.open(asset_path)
    
    # Create square icon by cropping to center
    min_dim = min(img.size)
    left = (img.size[0] - min_dim) // 2
    top = (img.size[1] - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    
    img_cropped = img.crop((left, top, right, bottom))
    
    # Resize to standard icon sizes
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        resized = img_cropped.resize((size, size), Image.Resampling.LANCZOS)
        images.append(resized)
    
    # Save as ICO
    ico_path = "freeman_icon.ico"
    images[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in images])
    
    file_size = os.path.getsize(ico_path)
    print(f"Icon created from asset: {ico_path}")
    print(f"File size: {file_size} bytes")
    
    return ico_path

if __name__ == "__main__":
    convert_asset_to_icon()
