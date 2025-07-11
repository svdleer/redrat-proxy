import os
import logging

# Try to import PIL, but provide fallback if it's not available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Setup logging
try:
    from app.utils.logger import logger
except ImportError:
    logger = logging.getLogger("redrat")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

def process_image(file_stream, output_path, size=(200, 200)):
    """Process an uploaded image (resize, crop, etc.)"""
    if not PIL_AVAILABLE:
        logger.warning("PIL not available, cannot process image")
        return False
        
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
        # Use LANCZOS instead of ANTIALIAS which is deprecated in newer PIL/Pillow
        resize_method = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', Image.BICUBIC))
        img = img.resize(size, resize_method)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        img.save(output_path, 'JPEG', quality=85)
        logger.info(f"Image processed and saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return False

def allowed_file(filename, allowed_extensions=None):
    """Check if a file is allowed based on extension"""
    if allowed_extensions is None:
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions