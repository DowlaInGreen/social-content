#!/usr/bin/env python3
"""
VSS Digital — Media Generator (slike + reels)

Uzima .md objavu i generira:
  1. Brandiranu sliku (.png) — za LinkedIn, Facebook, Instagram feed
  2. Kratki reel (.mp4) — za Instagram Reels / Facebook Reels

Pokretanje:
  python scripts/generate_media.py content/approved/2026-06-01-01.md
  python scripts/generate_media.py                           # sve approved
"""

import re
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

# ── Imports ──────────────────────────────────────────────────────────────────
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from moviepy import (
        VideoClip, VideoFileClip, ImageClip, TextClip,
        CompositeVideoClip, concatenate_videoclips, ColorClip
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# ── CONSTANTS ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_APPROVED = REPO_ROOT / "content" / "approved"
CONTENT_PENDING = REPO_ROOT / "content" / "pending"
ASSETS_DIR = REPO_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = REPO_ROOT / "content" / "media"

# Brand colors
BG_DARK = (13, 13, 26)
BLUE = (79, 142, 247)
PURPLE = (155, 86, 182)
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 210)
GRADIENT_COLORS = [BLUE, PURPLE]

# Dimensions
IMG_SIZE = (1080, 1080)      # kvadratna slika za sve platforme
VIDEO_SIZE = (1080, 1920)     # 9:16 vertikalni reel

# ── FONT LOADING ─────────────────────────────────────────────────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Učitaj NotoSans font u zadanoj veličini."""
    font_path = FONTS_DIR / "NotoSans-Variable.ttf"
    if font_path.exists():
        # NotoSans-Variable podržava weight os — koristimo više weight za bold
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


# ── POST PARSING ─────────────────────────────────────────────────────────────
def parse_post(filepath: Path) -> dict:
    """Parsiraj .md file objave u strukturu (isti format kao post.py)."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    post = {
        "filepath": filepath,
        "topic": "",
        "linkedin": "",
        "facebook": "",
        "instagram": "",
        "image_suggestion": "",
    }
    current_section = None

    for line in lines:
        if line.startswith("# "):
            post["topic"] = line.replace("# ", "").strip()
        elif line.startswith("## LinkedIn"):
            current_section = "linkedin"
        elif line.startswith("## Facebook"):
            current_section = "facebook"
        elif line.startswith("## Instagram"):
            current_section = "instagram"
        elif line.startswith("## Prijedlog"):
            current_section = "image_suggestion"
        elif line.startswith("---"):
            continue
        elif current_section and line.strip():
            post[current_section] += line.strip() + " "

    for k in ("linkedin", "facebook", "instagram", "image_suggestion"):
        post[k] = post[k].strip()

    return post


# ── HELPERS ──────────────────────────────────────────────────────────────────
def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def darken_color(color: tuple, factor: float = 0.7) -> tuple:
    return tuple(int(c * factor) for c in color)


def lighter_color(color: tuple, factor: float = 0.3) -> tuple:
    return tuple(int(c + (255 - c) * factor) for c in color)


def wrap_text(text: str, max_chars: int = 35) -> list[str]:
    """Prekrij tekst u retke do max_chars znakova."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars and current:
            lines.append(current.strip())
            current = word
        else:
            current += " " + word
    if current:
        lines.append(current.strip())
    return lines


def extract_key_stat(text: str) -> str | None:
    """Pokušaj izvući ključnu brojku/stat iz teksta."""
    patterns = [
        r'(\d+\s*sati\s*tjedno)',
        r'(\d+\s*sati\s*mjesečno)',
        r'(\d+\s*[+-]?\s*poziva\s*dnevno)',
        r'(\d+[%]\s*)',
        r'(\d+\s*sati)',
        r'(\d+\s*dnevno)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def detect_template(post: dict) -> str:
    """Detektiraj koji vizualni template najbolje odgovara objavi."""
    linkedin = post.get("linkedin", "").lower()
    topic = post.get("topic", "").lower()
    full_text = linkedin + " " + topic

    # Quote template — ima citate, price, izjave (provjeri prije brojeva)
    if re.search(r'\".*?\"|\'\".*?\"\'\'|rekao|rekla|kaže|izjavio|priča', full_text):
        return "quote"

    # Feature template
    if re.search(r'novo|usluga|servis|ponuda|radimo', full_text):
        return "feature"

    # Brojčani template — ima brojke i usporedbe
    if re.search(r'\d+', full_text) or re.search(r'sati|mjesečno|dnevno|tjedno', full_text):
        return "stats"

    # Pitanje template
    if linkedin.startswith(("jeste li", "znate li", "koliko", "zašto", "kako", "imate li", "razmislite")):
        return "question"

    return "question"  # default


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def draw_gradient_bg(draw: ImageDraw, size: tuple):
    """Nacrtaj gradijent pozadinu #0d0d1a → plavo-ljubičasti accent."""
    w, h = size
    for y in range(h):
        ratio = y / h
        r = int(BG_DARK[0] + (BLUE[0] - BG_DARK[0]) * ratio * 0.3)
        g = int(BG_DARK[1] + (BLUE[1] - BG_DARK[1]) * ratio * 0.3)
        b = int(BG_DARK[2] + (PURPLE[2] - BG_DARK[2]) * ratio * 0.3)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def draw_accent_line(draw: ImageDraw, x: int, y: int, width: int, height: int = 4):
    """Nacrtaj gradient accent liniju."""
    for i in range(width):
        ratio = i / width
        r = int(BLUE[0] + (PURPLE[0] - BLUE[0]) * ratio)
        g = int(BLUE[1] + (PURPLE[1] - BLUE[1]) * ratio)
        b = int(BLUE[2] + (PURPLE[2] - BLUE[2]) * ratio)
        draw.point((x + i, y), fill=(r, g, b))
        if height > 1:
            for h in range(1, height):
                draw.point((x + i, y + h), fill=(r, g, b))


def draw_logo(draw: ImageDraw, x: int, y: int):
    """Nacrtaj VSS DIGITAL + REAL AUTOMATION logo."""
    font_logo = get_font(42)
    font_tagline = get_font(18)
    draw.text((x, y), "VSS DIGITAL", fill=WHITE, font=font_logo)
    draw.text((x, y + 48), "REAL AUTOMATION", fill=BLUE, font=font_tagline)
    # Mala linija ispod tagline
    draw_accent_line(draw, x, y + 78, 120, 2)


def draw_url(draw: ImageDraw, x: int, y: int):
    """Nacrtaj URL na dnu."""
    font_url = get_font(20)
    draw.text((x, y), "vssdigital.online", fill=LIGHT_GRAY, font=font_url)


def generate_image_stats(post: dict) -> Image.Image:
    """Template: veliki broj + ušteda."""
    img = Image.new("RGB", IMG_SIZE, BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(draw, IMG_SIZE)

    w, h = IMG_SIZE
    cx = w // 2

    # Logo
    draw_logo(draw, 60, 40)

    # Pokušaj izvući ključni broj
    number = "?"
    label = ""
    for text in [post.get("linkedin", ""), post.get("topic", ""), post.get("facebook", "")]:
        m = re.search(r'(\d+)\s*(sati|h|%|EUR|€)', text, re.IGNORECASE)
        if m:
            number = m.group(1)
            label = m.group(2).upper() if m.group(2) else ""
            break
        m2 = re.search(r'(\d+)[-–]\d+', text)
        if m2:
            number = m2.group(0)
            label = ""
            break

    # Veliki broj
    try:
        font_number = get_font(240)
        bbox = draw.textbbox((0, 0), number, font=font_number)
        nw = bbox[2] - bbox[0]
        draw.text((cx - nw // 2, 320), number, fill=BLUE, font=font_number)
    except Exception:
        font_number = get_font(180)
        draw.text((cx - 80, 340), number, fill=BLUE, font=font_number)

    # Label ispod broja
    if label:
        font_label = get_font(48)
        bbox = draw.textbbox((0, 0), label, font=font_label)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, 560), label, fill=PURPLE, font=font_label)

    # Accent linija
    draw_accent_line(draw, cx - 80, 640, 160, 3)

    # Key message ispod
    topic = post.get("topic", "")
    lines = wrap_text(topic, 30)
    font_msg = get_font(32)
    y_start = 680
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font_msg)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y_start), line, fill=WHITE, font=font_msg)
        y_start += 48

    # URL
    draw_url(draw, cx - 150, 1010)

    return img


def generate_image_question(post: dict) -> Image.Image:
    """Template: pitanje + ključna poruka."""
    img = Image.new("RGB", IMG_SIZE, BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(draw, IMG_SIZE)

    w, h = IMG_SIZE
    cx = w // 2

    draw_logo(draw, 60, 40)

    # Question mark icon
    font_qm = get_font(100)
    draw.text((cx - 40, 220), "?", fill=BLUE, font=font_qm)

    # Topic kao naslov
    topic = post.get("topic", "")
    lines = wrap_text(topic, 28)
    font_title = get_font(44)
    y_start = 360
    for line in lines[:4]:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y_start), line, fill=WHITE, font=font_title)
        y_start += 56

    # Accent line
    draw_accent_line(draw, cx - 60, y_start + 20, 120, 3)

    # Kratki opis
    linkedin = post.get("linkedin", "")
    if len(linkedin) > 100:
        body = linkedin[:100] + "..."
    else:
        body = linkedin

    body_lines = wrap_text(body, 32)
    y_start += 60
    font_body = get_font(28)
    for line in body_lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y_start), line, fill=LIGHT_GRAY, font=font_body)
        y_start += 40

    # URL
    draw_url(draw, cx - 150, 1010)

    return img


def generate_image_quote(post: dict) -> Image.Image:
    """Template: citat / customer story."""
    img = Image.new("RGB", IMG_SIZE, BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(draw, IMG_SIZE)

    w, h = IMG_SIZE
    cx = w // 2

    draw_logo(draw, 60, 40)

    # Veliki navodnici
    font_quote = get_font(120)
    draw.text((80, 260), '"', fill=BLUE, font=font_quote)

    # Izvući citat iz teksta
    linkedin = post.get("linkedin", "")
    quote_match = re.search(r'"([^"]+)"', linkedin)
    if quote_match:
        quote_text = quote_match.group(1)
    else:
        quote_text = linkedin[:200]

    lines = wrap_text(quote_text, 30)
    font_body = get_font(34)
    y_start = 360
    for line in lines[:5]:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y_start), line, fill=WHITE, font=font_body)
        y_start += 48

    # Closing quote
    draw.text((cx + 60, y_start + 10), '"', fill=PURPLE, font=font_quote)

    # Accent line
    draw_accent_line(draw, cx - 60, y_start + 80, 120, 3)

    # Topic
    font_topic = get_font(26)
    topic = post.get("topic", "")
    bbox = draw.textbbox((0, 0), topic[:60], font=font_topic)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, y_start + 100), topic[:60], fill=LIGHT_GRAY, font=font_topic)

    # URL
    draw_url(draw, cx - 150, 1010)

    return img


def generate_image_feature(post: dict) -> Image.Image:
    """Template: feature / usluga."""
    img = Image.new("RGB", IMG_SIZE, BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(draw, IMG_SIZE)

    w, h = IMG_SIZE
    cx = w // 2

    draw_logo(draw, 60, 40)

    # Topic
    topic = post.get("topic", "")
    lines = wrap_text(topic, 28)
    font_title = get_font(46)
    y_start = 300
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y_start), line, fill=WHITE, font=font_title)
        y_start += 58

    # Accent
    draw_accent_line(draw, cx - 80, y_start + 20, 160, 3)

    # Feature bullets
    linkedin = post.get("linkedin", "")
    # Izvući key points
    points = []
    for line in linkedin.split("."):
        line = line.strip()
        if line and len(line) > 20:
            points.append(line[:80])

    y_start += 60
    font_bullet = get_font(28)
    for point in points[:4]:
        short = point[:70] + ("..." if len(point) > 70 else "")
        bbox = draw.textbbox((0, 0), short, font=font_bullet)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y_start), short, fill=LIGHT_GRAY, font=font_bullet)
        y_start += 40

    # URL
    draw_url(draw, cx - 150, 1010)

    return img


def generate_image(post: dict) -> Path:
    """Glavna funkcija — generiraj sliku za objavu."""
    template = detect_template(post)
    print(f"  🎨 Template: {template}")

    if template == "stats":
        img = generate_image_stats(post)
    elif template == "quote":
        img = generate_image_quote(post)
    elif template == "feature":
        img = generate_image_feature(post)
    else:
        img = generate_image_question(post)

    # Spremi
    stem = post["filepath"].stem
    output_path = OUTPUT_DIR / f"{stem}.png"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", optimize=True)
    print(f"  🖼  Slika: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO (REEL) GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def pil_to_np(pil_img: Image.Image, force_rgb: bool = False) -> 'np.ndarray':
    """Pretvori PIL Image u numpy array za MoviePy.
    Ako force_rgb=True, uklanja alpha kanal (za standalone slike)."""
    import numpy as np
    if force_rgb and pil_img.mode == "RGBA":
        pil_img = pil_img.convert("RGB")
    return np.array(pil_img)


def make_text_frame(text: str, font_size: int = 60, fg_color: str = "#FFFFFF",
                    max_width: int = 950):
    """Napravi numpy frame s tekstom na prozirnoj pozadini."""
    font = get_font(font_size)
    lines = wrap_text(text, 35)

    # Izračunaj dimenzije
    line_heights = []
    total_h = 0
    max_line_w = 0
    for line in lines[:6]:
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_heights.append((lw, lh))
        max_line_w = max(max_line_w, lw)
        total_h += lh + 12  # spacing

    total_h = max(total_h, 100)
    max_line_w = min(max_line_w + 40, max_width)

    img = Image.new("RGBA", (max_line_w + 80, total_h + 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = 30
    for i, line in enumerate(lines[:6]):
        if i < len(line_heights):
            lw, lh = line_heights[i]
        else:
            bbox = font.getbbox(line)
            lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (img.width - lw) // 2
        try:
            draw.text((x, y), line, fill=fg_color, font=font)
        except Exception:
            pass
        y += lh + 12

    return pil_to_np(img)


def make_scene(title: str, body: str, duration: float = 5.0,
               scene_type: str = "hook") -> VideoClip:
    """Napravi jednu scenu za reel (tekst na tamnoj pozadini)."""
    w, h = VIDEO_SIZE

    # Background frames - animate gradient
    def make_frame(t):
        import numpy as np
        ratio = t / duration if duration > 0 else 0
        arr = np.zeros((h, w, 3), dtype=np.uint8)

        # Gradient background
        for y in range(h):
            y_ratio = y / h
            r = int(BG_DARK[0] + (BLUE[0] - BG_DARK[0]) * y_ratio * 0.3)
            g = int(BG_DARK[1] + (BLUE[1] - BG_DARK[1]) * y_ratio * 0.3)
            b = int(BG_DARK[2] + (PURPLE[2] - BG_DARK[2]) * y_ratio * 0.3)

            # Subtle animation - pulsing accent
            pulse = int(20 * abs((t / 3) % 2 - 1))
            r = min(255, r + pulse)
            g = min(255, g + pulse)
            b = min(255, b + pulse)

            arr[y, :] = [r, g, b]

        return arr

    bg_clip = VideoClip(make_frame, duration=duration)

    # Overlay tekst
    clips = [bg_clip]

    # Logo - top
    logo_img = Image.new("RGBA", (300, 120), (0, 0, 0, 0))
    logo_draw = ImageDraw.Draw(logo_img)
    font_logo = get_font(36)
    font_tag = get_font(16)
    logo_draw.text((20, 10), "VSS DIGITAL", fill=WHITE, font=font_logo)
    logo_draw.text((20, 52), "REAL AUTOMATION", fill=BLUE, font=font_tag)
    logo_np = pil_to_np(logo_img)
    logo_clip = ImageClip(logo_np, duration=duration).with_position((40, 40))
    clips.append(logo_clip)

    # Title (big)
    if scene_type == "hook":
        # Veliko pitanje/stat
        title_img = make_text_frame(title, font_size=72, fg_color="#4F8EF7")
        title_clip = ImageClip(title_img, duration=duration).with_position(("center", 300))
        clips.append(title_clip)

        # Body manji
        body_img = make_text_frame(body, font_size=44, fg_color="#C8C8D2")
        body_clip = ImageClip(body_img, duration=duration).with_position(("center", 650))
        clips.append(body_clip)

    elif scene_type == "body":
        # Key message
        body_img = make_text_frame(body, font_size=52, fg_color="#FFFFFF")
        body_clip = ImageClip(body_img, duration=duration).with_position(("center", 400))
        clips.append(body_clip)

    elif scene_type == "cta":
        # CTA
        cta_img = make_text_frame(title, font_size=64, fg_color="#4F8EF7")
        cta_clip = ImageClip(cta_img, duration=duration).with_position(("center", 380))
        clips.append(cta_clip)

        # URL
        url_img = make_text_frame("vssdigital.online", font_size=36, fg_color="#C8C8D2")
        url_clip = ImageClip(url_img, duration=duration).with_position(("center", 700))
        clips.append(url_clip)

    return CompositeVideoClip(clips, size=VIDEO_SIZE)


def generate_video(post: dict) -> Path | None:
    """Glavna funkcija — generiraj reel (15-20s) za objavu."""
    if not MOVIEPY_AVAILABLE:
        print("  ⚠  moviepy nije instaliran — preskačem video")
        return None

    linkedin = post.get("linkedin", "")
    topic = post.get("topic", "")

    # Izvuci hook (prva rečenica)
    sentences = linkedin.split(".")
    hook = sentences[0].strip() if sentences else topic
    body_text = ". ".join(sentences[1:4]).strip() if len(sentences) > 1 else linkedin[:150]

    try:
        print(f"  🎬 Generiram reel (3 scene)...")

        # Scene 1: Hook
        scene1 = make_scene(hook, "", duration=6.0, scene_type="hook")

        # Scene 2: Key message
        scene2 = make_scene("", body_text, duration=6.0, scene_type="body")

        # Scene 3: CTA
        cta_text = "Javite se za demonstraciju!"
        scene3 = make_scene(cta_text, "", duration=5.0, scene_type="cta")

        # Spoj
        final = concatenate_videoclips([scene1, scene2, scene3], method="compose")

        # Spremi
        stem = post["filepath"].stem
        output_path = OUTPUT_DIR / f"{stem}.mp4"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        final.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio=False,
            preset="fast",
            threads=2,
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            logger=None,
        )
        size_kb = output_path.stat().st_size // 1024
        print(f"  🎞  Reel: {output_path.name} ({size_kb} KB, ~17s)")

        # Cleanup
        final.close()
        for c in [scene1, scene2, scene3]:
            c.close()

        return output_path

    except Exception as e:
        print(f"  ❌ Video error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def process_post(filepath: Path, skip_video: bool = False) -> dict:
    """Procesiraj jednu objavu: generiraj sliku + opcionalno reel."""
    print(f"\n📄 {filepath.name}")
    post = parse_post(filepath)
    print(f"   Tema: {post['topic'][:60]}...")
    print(f"   Template: {detect_template(post)}")

    result = {"file": filepath.name, "image": None, "video": None}

    # Slika
    try:
        img_path = generate_image(post)
        result["image"] = str(img_path)
    except Exception as e:
        print(f"  ❌ Greška kod slike: {e}")
        import traceback
        traceback.print_exc()

    # Video
    if not skip_video:
        try:
            vid_path = generate_video(post)
            result["video"] = str(vid_path) if vid_path else None
        except Exception as e:
            print(f"  ❌ Greška kod videa: {e}")

    print(f"  ✅ {filepath.name} obrađen")
    return result


def main():
    print("🎬 VSS Digital — Media Generator")
    print("══════════════════════════════════\n")

    skip_video = "--no-video" in sys.argv

    # Ako je zadan konkretan file
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        files = [Path(a) for a in args if Path(a).exists()]
    else:
        # Sve approved + pending
        files = sorted(CONTENT_APPROVED.glob("*.md")) + sorted(CONTENT_PENDING.glob("*.md"))

    if not files:
        print("ℹ Nema .md fileova za obradu.")
        print("   Usage: python scripts/generate_media.py [file.md]")
        return

    print(f"📁 {len(files)} objava za obradu\n")

    results = []
    for f in files:
        r = process_post(f, skip_video=skip_video)
        results.append(r)

    # Summary
    print("\n" + "=" * 50)
    print("📊 SAŽETAK")
    print("=" * 50)
    images_ok = sum(1 for r in results if r["image"])
    videos_ok = sum(1 for r in results if r["video"])
    print(f"🖼  Slika: {images_ok}/{len(results)}")
    print(f"🎞  Reel:  {videos_ok}/{len(results)}")
    print(f"📁 Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
