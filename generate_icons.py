#!/usr/bin/env python3
"""Generate MailPilot icons — minimalist geometric design.

Creates PNG icons at 16, 32, 64, 80 px.
Design: rounded indigo background + white envelope + small paper-plane accent.
"""

from PIL import Image, ImageDraw
import math
import os

SIZES = [16, 32, 64, 80]
OUT_DIR = "outlook-addin/src/taskpane/public/assets"

# Colors
BG_TOP = (79, 70, 229)       # indigo-600
BG_BOT = (99, 102, 241)      # indigo-500
ENVELOPE = (255, 255, 255)    # white
FOLD = (79, 70, 229)         # indigo-600 (envelope fold line)
PLANE = (165, 180, 252)       # indigo-300 (subtle accent)


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_rounded_rect(draw, xy, radius, fill):
    """Draw a filled rounded rectangle."""
    x0, y0, x1, y1 = xy
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    # Four corners
    draw.pieslice([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=fill)
    # Fill rectangles
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)


def generate_icon(size):
    """Generate a single icon at the given size."""
    # Work at 4x resolution for anti-aliasing, then downscale
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- Background: rounded rectangle with gradient ---
    corner_r = s // 5
    # Draw gradient by horizontal lines
    for y in range(s):
        t = y / s
        color = lerp_color(BG_TOP, BG_BOT, t)
        draw.line([(0, y), (s - 1, y)], fill=color)

    # Apply rounded corner mask
    mask = Image.new("L", (s, s), 0)
    mask_draw = ImageDraw.Draw(mask)
    draw_rounded_rect(mask_draw, [0, 0, s, s], corner_r, fill=255)
    img.putalpha(mask)

    # Re-create draw after alpha change
    draw = ImageDraw.Draw(img)

    # --- Envelope body ---
    margin = s * 0.18
    env_top = s * 0.30
    env_bot = s * 0.72
    env_left = margin
    env_right = s - margin

    # Envelope rectangle (white, slightly rounded)
    envelope_coords = [env_left, env_top, env_right, env_bot]
    env_r = s * 0.04
    draw_rounded_rect(draw, envelope_coords, int(env_r), fill=ENVELOPE)

    # --- Envelope flap (V shape on top) ---
    flap_tip_y = s * 0.48  # V goes down to here
    mid_x = s / 2

    # Draw filled triangle for the flap
    flap_points = [
        (env_left, env_top),
        (mid_x, flap_tip_y),
        (env_right, env_top),
    ]
    draw.polygon(flap_points, fill=ENVELOPE)

    # Draw the V fold lines
    line_w = max(1, int(s * 0.02))
    draw.line([(env_left, env_top), (mid_x, flap_tip_y)], fill=FOLD, width=line_w)
    draw.line([(env_right, env_top), (mid_x, flap_tip_y)], fill=FOLD, width=line_w)

    # Bottom fold lines (from bottom corners to center)
    bottom_tip_y = s * 0.55
    draw.line([(env_left, env_bot), (mid_x, bottom_tip_y)],
              fill=(*FOLD, 80), width=line_w)
    draw.line([(env_right, env_bot), (mid_x, bottom_tip_y)],
              fill=(*FOLD, 80), width=line_w)

    # --- Paper plane accent (top-right, small) ---
    plane_cx = s * 0.72
    plane_cy = s * 0.28
    plane_size = s * 0.13

    # Simple arrow/plane shape pointing upper-right
    p1 = (plane_cx + plane_size, plane_cy - plane_size)  # tip
    p2 = (plane_cx - plane_size * 0.3, plane_cy + plane_size * 0.1)  # bottom-left
    p3 = (plane_cx + plane_size * 0.1, plane_cy - plane_size * 0.3)  # top edge
    p4 = (plane_cx - plane_size * 0.1, plane_cy + plane_size * 0.6)  # tail

    # Main triangle
    draw.polygon([p1, p2, p3], fill=(*PLANE, 220))
    # Tail
    draw.polygon([p1, p2, p4], fill=(*PLANE, 150))

    # --- Downscale with high-quality resampling ---
    img = img.resize((size, size), Image.LANCZOS)

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for size in SIZES:
        icon = generate_icon(size)
        path = os.path.join(OUT_DIR, f"icon-{size}.png")
        icon.save(path, "PNG", optimize=True)
        file_size = os.path.getsize(path)
        print(f"  ✓ {path}  ({size}×{size}, {file_size:,} bytes)")

    # Also generate a preview HTML
    preview = """<!DOCTYPE html>
<html><head><title>MailPilot Icon Preview</title>
<style>
  body { font-family: system-ui; background: #1a1a2e; color: #fff;
         display: flex; flex-direction: column; align-items: center;
         padding: 40px; gap: 30px; }
  .row { display: flex; gap: 30px; align-items: center; }
  .icon-box { text-align: center; }
  .icon-box img { image-rendering: pixelated; border: 1px solid #333; }
  .label { font-size: 12px; color: #888; margin-top: 6px; }
  h1 { margin: 0; }
  .light { background: #f5f5f5; padding: 20px; border-radius: 12px; }
</style></head><body>
<h1>MailPilot Icons</h1>
<h3>Dark background (actual size)</h3>
<div class="row">
"""
    for sz in SIZES:
        preview += f'  <div class="icon-box"><img src="icon-{sz}.png" width="{sz}" height="{sz}"><div class="label">{sz}×{sz}</div></div>\n'

    preview += '</div>\n<h3>Dark background (4× zoom)</h3>\n<div class="row">\n'
    for sz in SIZES:
        preview += f'  <div class="icon-box"><img src="icon-{sz}.png" width="{sz*4}" height="{sz*4}"><div class="label">{sz}×{sz} @ 4×</div></div>\n'

    preview += '</div>\n<h3>Light background (4× zoom)</h3>\n<div class="row light">\n'
    for sz in SIZES:
        preview += f'  <div class="icon-box"><img src="icon-{sz}.png" width="{sz*4}" height="{sz*4}"><div class="label">{sz}×{sz} @ 4×</div></div>\n'

    preview += "</div>\n</body></html>"

    preview_path = os.path.join(OUT_DIR, "icon-preview.html")
    with open(preview_path, "w") as f:
        f.write(preview)
    print(f"  ✓ {preview_path}")
    print(f"\nOpen {preview_path} in a browser to preview.")


if __name__ == "__main__":
    main()
