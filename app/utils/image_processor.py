from PIL import Image
from io import BytesIO
import os

def process_uploaded_image(file_stream, output_path, size):
    """Crop and resize uploaded image"""
    try:
        img = Image.open(file_stream)
        
        # Crop to square
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        
        img = img.crop((left, top, right, bottom))
        img = img.resize(size, Image.ANTIALIAS)
        img.save(output_path, 'JPEG', quality=85)
        
        return True
    except Exception as e:
        print(f"Image processing error: {e}")
        return False