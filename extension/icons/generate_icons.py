"""
Run this script once to generate the extension icons.
Requires: pip install Pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZES = [16, 32, 48, 128]
BG_COLOR = (108, 99, 255)
TEXT_COLOR = (255, 255, 255)

script_dir = os.path.dirname(os.path.abspath(__file__))

for size in SIZES:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    margin = max(1, size // 10)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 5,
        fill=BG_COLOR,
    )

    # Draw "R" letter
    font_size = max(8, int(size * 0.55))
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    out_path = os.path.join(script_dir, f"icon{size}.png")
    img.save(out_path, "PNG")
    print(f"Created {out_path}")

print("Done!")
