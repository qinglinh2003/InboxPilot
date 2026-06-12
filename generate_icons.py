#!/usr/bin/env python3
"""Generate MailPilot icons at 16, 32, 64, 80 px.

Design: Modern gradient background with a stylized paper-airplane-envelope
hybrid and subtle AI sparkle accents.  Renders at 4x then downscales for
crisp anti-aliasing.
"""

from PIL import Image, ImageDraw, ImageFilter
import os, math

SIZES = [16, 32, 64, 80]
OUT_DIR = "outlook-addin/src/taskpane/public/assets"
PREVIEW_DIR = "outlook-addin/src/taskpane/public/assets"

# ── Colour palette ──────────────────────────────────────────────
BG_TOP = (56, 97, 251)       # Vibrant blue
BG_BOT = (99, 54, 237)       # Rich purple
ACCENT = (0, 210, 180)       # Teal accent (AI / smart feel)
SPARKLE_MAIN = (255, 255, 255)
SPARKLE_SEC  = (0, 230, 200, 200)  # Semi-transparent teal sparkle
ENVELOPE_BODY = (255, 255, 255)
ENVELOPE_SHADOW = (40, 50, 120, 80)
FLAP_ACCENT = (220, 230, 255, 180)

SCALE = 4  # Supersampling factor


# ── Helpers ─────────────────────────────────────────────────────

def rounded_rect_mask(size, radius):
    """Anti-aliased rounded rectangle mask via supersampling."""
    big = size * SCALE
    r = radius * SCALE
    mask = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, big - 1, big - 1], radius=r, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def draw_gradient(img, top_color, bot_color):
    """Vertical linear gradient."""
    w, h = img.size
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b, 255)


def draw_sparkle(draw, cx, cy, r, fill="white", points=4):
    """Draw a multi-point sparkle/star."""
    pts = []
    n = points * 2
    for i in range(n):
        angle = math.radians(i * (360 / n) - 90)
        dist = r if i % 2 == 0 else r * 0.3
        pts.append((cx + dist * math.cos(angle), cy + dist * math.sin(angle)))
    draw.polygon(pts, fill=fill)


def draw_envelope_modern(draw, cx, cy, w, h):
    """Draw a clean, modern envelope with subtle depth."""
    left = cx - w // 2
    top = cy - h // 2
    right = cx + w // 2
    bottom = cy + h // 2
    corner_r = max(2, w // 10)

    # Main body
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=corner_r,
        fill=ENVELOPE_BODY,
    )

    # Flap (V-shape from top corners meeting at center)
    flap_depth = int(h * 0.50)
    # Darker accent line for the fold
    draw.polygon(
        [(left, top), (cx, top + flap_depth), (right, top)],
        fill=(200, 210, 240),
    )
    # Inner flap highlight
    inset = max(1, w // 14)
    draw.polygon(
        [(left + inset, top + inset),
         (cx, top + flap_depth - inset),
         (right - inset, top + inset)],
        fill=FLAP_ACCENT,
    )

    # Bottom-left accent line (simulates paper fold)
    line_y = top + int(h * 0.65)
    line_w = max(1, w // 20)
    draw.line(
        [(left + corner_r, line_y), (cx - w // 6, line_y)],
        fill=(180, 190, 220, 120),
        width=line_w,
    )


def draw_paper_airplane_hint(draw, cx, cy, size):
    """Draw a tiny paper airplane motif (the 'Pilot' in MailPilot)."""
    s = size * 0.12
    # Simple paper airplane shape
    pts = [
        (cx + s * 1.2, cy - s * 0.3),   # nose (right)
        (cx - s * 0.8, cy - s * 1.0),   # top wing
        (cx - s * 0.2, cy),              # body center
        (cx - s * 0.8, cy + s * 1.0),   # bottom wing
    ]
    draw.polygon(pts, fill=ACCENT)
    # Wing fold line
    draw.line(
        [(cx - s * 0.2, cy), (cx + s * 1.2, cy - s * 0.3)],
        fill=(0, 180, 160),
        width=max(1, int(s * 0.15)),
    )


# ── Main icon generator ────────────────────────────────────────

def generate_icon(target_size):
    """Generate one icon, rendered at SCALE then downscaled."""
    size = target_size * SCALE

    # Transparent canvas
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Gradient background
    bg = Image.new("RGBA", (size, size))
    draw_gradient(bg, BG_TOP, BG_BOT)

    # Round the corners
    radius = max(2, target_size // 4) * SCALE
    mask_big = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask_big).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255,
    )
    img.paste(bg, (0, 0), mask_big)

    # Add a subtle radial glow in the center-top
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    glow_r = int(size * 0.35)
    glow_cx, glow_cy = size // 2, int(size * 0.3)
    gd.ellipse(
        [glow_cx - glow_r, glow_cy - glow_r,
         glow_cx + glow_r, glow_cy + glow_r],
        fill=(100, 180, 255, 40),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size // 6))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    if target_size <= 16:
        # ── 16px: Minimal — just a clean envelope ──
        ew = int(size * 0.60)
        eh = int(size * 0.40)
        draw_envelope_modern(draw, cx, cy + size // 16, ew, eh)

    elif target_size <= 32:
        # ── 32px: Envelope + single sparkle ──
        ew = int(size * 0.55)
        eh = int(size * 0.38)
        ecx = cx - size // 14
        ecy = cy + size // 14
        draw_envelope_modern(draw, ecx, ecy, ew, eh)

        # Sparkle top-right
        sr = size * 0.08
        draw_sparkle(draw, cx + size // 4, cy - size // 5, sr, SPARKLE_MAIN)

    else:
        # ── 64px, 80px: Full detail ──
        ew = int(size * 0.50)
        eh = int(size * 0.35)
        ecx = cx - size // 12
        ecy = cy + size // 10
        draw_envelope_modern(draw, ecx, ecy, ew, eh)

        # Paper airplane accent (top-right of envelope)
        draw_paper_airplane_hint(draw, cx + size // 5, cy - size // 8, size)

        # Main sparkle
        sr = size * 0.065
        sx = cx + size * 0.32
        sy = cy - size * 0.28
        draw_sparkle(draw, sx, sy, sr, SPARKLE_MAIN)

        # Secondary smaller sparkle
        sr2 = size * 0.035
        draw_sparkle(draw, sx + size * 0.08, sy + size * 0.12, sr2, SPARKLE_SEC)

        # Tiny dot accent
        dr = max(1, int(size * 0.012))
        draw.ellipse(
            [sx - size * 0.12 - dr, sy + size * 0.05 - dr,
             sx - size * 0.12 + dr, sy + size * 0.05 + dr],
            fill=(255, 255, 255, 140),
        )

    # Downscale with high-quality resampling
    final = img.resize((target_size, target_size), Image.LANCZOS)
    return final


# ── Preview HTML generator ──────────────────────────────────────

def generate_preview_html(out_dir):
    """Create a simple HTML page to preview all icon sizes."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MailPilot Icon Preview</title>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #1a1a2e;
    color: #eee;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px;
    gap: 32px;
  }
  h1 { color: #7c9dff; margin-bottom: 8px; }
  .grid {
    display: flex;
    gap: 40px;
    align-items: end;
    flex-wrap: wrap;
    justify-content: center;
  }
  .icon-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    background: #252540;
    padding: 24px 20px 16px;
    border-radius: 12px;
  }
  .icon-card img { image-rendering: auto; }
  .label { font-size: 13px; color: #999; }
  .zoom-row {
    display: flex;
    gap: 24px;
    align-items: center;
    background: #252540;
    padding: 20px 32px;
    border-radius: 12px;
  }
  .zoom-row img { image-rendering: pixelated; }
  .section-title {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #666;
    margin-top: 16px;
  }
  .bg-white { background: #fff; padding: 24px; border-radius: 12px; }
  .bg-dark  { background: #1a1a2e; padding: 24px; border-radius: 12px; }
</style>
</head>
<body>
  <h1>MailPilot Icons</h1>

  <p class="section-title">Actual Size</p>
  <div class="grid">
"""
    for s in SIZES:
        html += f"""    <div class="icon-card">
      <img src="icon-{s}.png" width="{s}" height="{s}" alt="icon-{s}">
      <span class="label">{s}x{s}</span>
    </div>\n"""

    html += """  </div>

  <p class="section-title">4x Zoom (on dark)</p>
  <div class="zoom-row bg-dark">
"""
    for s in SIZES:
        z = s * 4
        html += f'    <img src="icon-{s}.png" width="{z}" height="{z}" alt="icon-{s} zoomed">\n'

    html += """  </div>

  <p class="section-title">4x Zoom (on white)</p>
  <div class="zoom-row bg-white">
"""
    for s in SIZES:
        z = s * 4
        html += f'    <img src="icon-{s}.png" width="{z}" height="{z}" alt="icon-{s} zoomed">\n'

    html += """  </div>
</body>
</html>"""

    path = os.path.join(out_dir, "icon-preview.html")
    with open(path, "w") as f:
        f.write(html)
    print(f"  ✔ {path} (preview page)")


# ── Main ────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for size in SIZES:
        img = generate_icon(size)
        path = os.path.join(OUT_DIR, f"icon-{size}.png")
        img.save(path, "PNG", optimize=True)
        fsize = os.path.getsize(path)
        print(f"  ✔ {path} ({size}x{size}, {fsize} bytes)")

    generate_preview_html(OUT_DIR)
    print(f"\nDone! Open {OUT_DIR}/icon-preview.html in a browser to preview.")


if __name__ == "__main__":
    main()
