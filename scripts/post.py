#!/usr/bin/env python3
"""
VSS Digital — Social Media Publisher

Čita prvu neobjavljenu objavu iz content/approved/,
objavljuje na sve platforme, i premješta u content/posted/.
"""

import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_APPROVED = REPO_ROOT / "content" / "approved"
CONTENT_POSTED = REPO_ROOT / "content" / "posted"


def parse_post(filepath: Path) -> dict:
    """Parsiraj .md file objave u strukturu."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    topic = ""
    linkedin = ""
    facebook = ""
    instagram = ""
    image_suggestion = ""
    current_section = None

    for line in lines:
        if line.startswith("# "):
            topic = line.replace("# ", "").strip()
        elif line.startswith("## LinkedIn"):
            current_section = "linkedin"
        elif line.startswith("## Facebook"):
            current_section = "facebook"
        elif line.startswith("## Instagram"):
            current_section = "instagram"
        elif line.startswith("## Prijedlog"):
            current_section = "image"
        elif line.startswith("---"):
            continue
        elif current_section and line.strip():
            if current_section == "linkedin":
                linkedin += line.strip() + " "
            elif current_section == "facebook":
                facebook += line.strip() + " "
            elif current_section == "instagram":
                instagram += line.strip() + " "
            elif current_section == "image":
                image_suggestion += line.strip() + " "

    return {
        "filepath": filepath,
        "topic": topic,
        "linkedin": linkedin.strip(),
        "facebook": facebook.strip(),
        "instagram": instagram.strip(),
        "image_suggestion": image_suggestion.strip(),
    }


def get_next_post() -> Path | None:
    """Uzmi prvi file (po datumu) iz approved/."""
    if not CONTENT_APPROVED.exists():
        return None
    files = sorted(CONTENT_APPROVED.glob("*.md"))
    return files[0] if files else None


def archive_post(filepath: Path):
    """Premjesti objavljeni file u posted/."""
    CONTENT_POSTED.mkdir(parents=True, exist_ok=True)
    dest = CONTENT_POSTED / filepath.name
    shutil.move(str(filepath), str(dest))
    print(f"  → Arhivirano u content/posted/{filepath.name}")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")

    print("📤 VSS Digital — Publisher")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    post_file = get_next_post()
    if not post_file:
        print("ℹ Nema odobrenih objava u content/approved/")
        return

    post = parse_post(post_file)
    print(f"📄 Objava: {post['topic']}")
    print(f"   File: {post_file.name}")

    # 1. LinkedIn
    print("\n▶ LinkedIn...", end=" ", flush=True)
    try:
        from scripts.linkedin import post_to_linkedin
        result = post_to_linkedin(post["linkedin"])
        print(f"✓ (ID: {result['post_id']})")
    except Exception as e:
        print(f"✗ {e}")
        print("   Nastavljam s ostalima...")

    # 2. Facebook + Instagram
    print("▶ Facebook + IG...", end=" ", flush=True)
    try:
        from scripts.facebook import post_all
        results = post_all(post["facebook"])
        for r in results:
            print(f"✓ ({r['platform']}: {r['post_id']})", end=" ")
        print()
    except Exception as e:
        print(f"✗ {e}")

    # 3. Arhiviraj
    print("\n📦 Arhiviram...", end=" ", flush=True)
    archive_post(post_file)
    print("✓")

    print(f"\n✅ Objava \"{post['topic']}\" objavljena i arhivirana!")


if __name__ == "__main__":
    main()
