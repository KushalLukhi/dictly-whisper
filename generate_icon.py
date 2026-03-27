"""
generate_icon.py — Generates Dictly app icons for Windows (.ico) and macOS (.icns)
Run once: python generate_icon.py
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = Path(__file__).parent / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

# ── Design constants ────────────────────────────────────────────────────────
BG_COLOR       = (18, 18, 40)        # Deep navy
CIRCLE_COLOR   = (108, 75, 240)      # Purple
CIRCLE_GLOW    = (140, 100, 255, 80) # Soft glow
MIC_BODY       = (255, 255, 255)
MIC_STAND      = (200, 180, 255)
ARC_COLOR      = (200, 180, 255)


def draw_icon(size: int) -> Image.Image:
    scale = 4  # supersampling
    S = size * scale
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Background circle
    pad = int(S * 0.04)
    d.ellipse([pad, pad, S - pad, S - pad], fill=BG_COLOR)

    # Glow ring
    glow_pad = int(S * 0.08)
    d.ellipse([glow_pad, glow_pad, S - glow_pad, S - glow_pad],
              outline=(108, 75, 240, 60), width=int(S * 0.07))

    # Purple accent circle (top-left quadrant decoration)
    cx, cy = S // 2, S // 2
    r_accent = int(S * 0.36)
    d.ellipse([cx - r_accent, cy - r_accent, cx + r_accent, cy + r_accent],
              outline=CIRCLE_COLOR, width=int(S * 0.025))

    # ── Microphone body ──────────────────────────────────────────────────
    mic_w  = int(S * 0.18)
    mic_h  = int(S * 0.28)
    mic_r  = mic_w // 2
    mic_x  = cx - mic_w // 2
    mic_y  = int(S * 0.20)

    # Mic capsule (rounded rect)
    d.rounded_rectangle([mic_x, mic_y, mic_x + mic_w, mic_y + mic_h],
                         radius=mic_r, fill=MIC_BODY)

    # ── Mic stand arc ────────────────────────────────────────────────────
    arc_r   = int(S * 0.22)
    arc_cx  = cx
    arc_cy  = mic_y + mic_h - int(S * 0.02)
    arc_lw  = int(S * 0.04)
    bbox = [arc_cx - arc_r, arc_cy - arc_r, arc_cx + arc_r, arc_cy + arc_r]
    d.arc(bbox, start=200, end=340, fill=ARC_COLOR, width=arc_lw)

    # Stand vertical line
    stand_top_y  = arc_cy + arc_r - int(S * 0.06)
    stand_bot_y  = arc_cy + arc_r + int(S * 0.04)
    lw = arc_lw
    d.line([(cx, stand_top_y), (cx, stand_bot_y)], fill=ARC_COLOR, width=lw)

    # Stand base horizontal line
    base_w = int(S * 0.18)
    d.line([(cx - base_w // 2, stand_bot_y),
            (cx + base_w // 2, stand_bot_y)], fill=ARC_COLOR, width=lw)

    # Downsample back to target size (antialiasing)
    img = img.resize((size, size), Image.LANCZOS)
    return img


def save_ico(sizes=(16, 24, 32, 48, 64, 128, 256)):
    frames = [draw_icon(s) for s in sizes]
    path = ASSETS_DIR / "icon.ico"
    frames[0].save(path, format="ICO", sizes=[(s, s) for s in sizes],
                   append_images=frames[1:])
    print(f"  ✓ Saved {path}")
    return path


def save_png(size=512):
    img = draw_icon(size)
    path = ASSETS_DIR / "icon.png"
    img.save(path, format="PNG")
    print(f"  ✓ Saved {path}")
    return path


def save_icns():
    """macOS .icns — uses iconutil on Mac; on other platforms saves a placeholder."""
    import platform, subprocess, tempfile, shutil
    if platform.system() != "Darwin":
        # On non-Mac just save a 512px PNG as a stand-in
        img = draw_icon(512)
        path = ASSETS_DIR / "icon.icns"
        img.save(str(path).replace(".icns", ".png"))
        print(f"  ℹ  macOS .icns skipped (not on Mac) — icon.png saved instead")
        return
    iconset = Path(tempfile.mkdtemp()) / "icon.iconset"
    iconset.mkdir()
    for size in (16, 32, 64, 128, 256, 512):
        draw_icon(size).save(iconset / f"icon_{size}x{size}.png")
        draw_icon(size * 2).save(iconset / f"icon_{size}x{size}@2x.png")
    out = ASSETS_DIR / "icon.icns"
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)
    shutil.rmtree(iconset.parent)
    print(f"  ✓ Saved {out}")


if __name__ == "__main__":
    print("Generating Dictly icons…")
    save_ico()
    save_png()
    save_icns()
    print("Done! Icons saved to assets/")
