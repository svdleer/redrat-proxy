#!/usr/bin/env python3
"""
Convert SVG logo to PNG
This script converts the SVG logo to a proper PNG file
"""

import os
import sys

try:
    import cairosvg
except ImportError:
    print("CairoSVG not installed. Installing...")
    os.system("pip install cairosvg pillow")
    try:
        import cairosvg
    except ImportError:
        print("Failed to install CairoSVG. Please install it manually:")
        print("pip install cairosvg pillow")
        sys.exit(1)

def convert_svg_to_png():
    """Convert the SVG logo to PNG format"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(base_dir, 'app', 'static', 'images', 'logo.svg')
    png_path = os.path.join(base_dir, 'app', 'static', 'images', 'logo.png')
    
    if not os.path.exists(svg_path):
        print(f"Error: SVG file not found at {svg_path}")
        return False
    
    try:
        print(f"Converting {svg_path} to {png_path}...")
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=400, output_height=400)
        print("✅ Conversion successful!")
        return True
    except Exception as e:
        print(f"❌ Error converting SVG to PNG: {e}")
        return False

if __name__ == "__main__":
    convert_svg_to_png()
