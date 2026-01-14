#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate PWA icons for Mobile GCS
Creates icon-192.png and icon-512.png
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_icon(size: int, output_path: str):
    """Create a PWA icon with SC2 Zerg theme"""
    # Create image with dark background
    img = Image.new('RGB', (size, size), color='#16213e')
    draw = ImageDraw.Draw(img)
    
    # Draw Zerg symbol (simplified - green circle with Z)
    center = size // 2
    radius = size // 3
    
    # Outer circle (green)
    draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill='#00ff00',
        outline='#00cc00',
        width=max(2, size // 64)
    )
    
    # Inner circle (darker green)
    inner_radius = radius * 0.7
    draw.ellipse(
        [center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius],
        fill='#16213e',
        outline='#00ff00',
        width=max(1, size // 128)
    )
    
    # Draw "Z" letter (Zerg symbol)
    try:
        # Try to use a font if available
        font_size = size // 4
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Draw "Z" in the center
        text = "Z"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = center - text_width // 2
        text_y = center - text_height // 2
        
        draw.text(
            (text_x, text_y),
            text,
            fill='#00ff00',
            font=font
        )
    except Exception as e:
        # Fallback: draw simple "Z" shape with lines
        line_width = max(3, size // 64)
        # Top horizontal line
        draw.line(
            [center - radius * 0.5, center - radius * 0.3, center + radius * 0.5, center - radius * 0.3],
            fill='#00ff00',
            width=line_width
        )
        # Diagonal line
        draw.line(
            [center + radius * 0.5, center - radius * 0.3, center - radius * 0.5, center + radius * 0.3],
            fill='#00ff00',
            width=line_width
        )
        # Bottom horizontal line
        draw.line(
            [center - radius * 0.5, center + radius * 0.3, center + radius * 0.5, center + radius * 0.3],
            fill='#00ff00',
            width=line_width
        )
    
    # Save image
    img.save(output_path, 'PNG')
    print(f"Created icon: {output_path} ({size}x{size})")

def main():
    """Generate PWA icons"""
    # Get script directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    static_dir = project_root / "monitoring" / "static"
    
    # Create static directory if it doesn't exist
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate icons
    create_icon(192, str(static_dir / "icon-192.png"))
    create_icon(512, str(static_dir / "icon-512.png"))
    
    print("\n? PWA icons generated successfully!")
    print(f"Location: {static_dir}")
    print("\nNext steps:")
    print("1. Start the dashboard server: python monitoring/dashboard.py")
    print("2. Open http://localhost:8000 in your mobile browser")
    print("3. Add to Home Screen (Android) or Share > Add to Home Screen (iOS)")

if __name__ == "__main__":
    try:
        from PIL import Image, ImageDraw, ImageFont
        main()
    except ImportError:
        print("? PIL/Pillow is required. Install it with:")
        print("   pip install Pillow")
        print("\nAlternatively, you can use online icon generators:")
        print("   - https://www.pwabuilder.com/imageGenerator")
        print("   - https://realfavicongenerator.net/")
