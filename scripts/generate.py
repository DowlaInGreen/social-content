#!/usr/bin/env python3
"""
VSS Digital — AI Content Generator

Generira platformski optimiziran sadržaj za LinkedIn, Facebook i Instagram
koristeći Claude API. Brand DNA se učitava iz brand-dna.md i koristi
kao system prompt.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Spremi repo path
REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_PENDING = REPO_ROOT / "content" / "pending"
CONTENT_APPROVED = REPO_ROOT / "content" / "approved"
CONTENT_POSTED = REPO_ROOT / "content" / "posted"
BRAND_DNA_FILE = REPO_ROOT / "brand-dna.md"


def load_brand_dna() -> str:
    """Učitaj Brand DNA iz filea."""
    if BRAND_DNA_FILE.exists():
        return BRAND_DNA_FILE.read_text(encoding="utf-8")
    return "VSS Digital - digitalna agencija iz Novog Zagreba."


def generate_content(
    api_key: str,
    brand_dna: str,
    news_items: list[str],
    num_posts: int = 5,
) -> list[dict]:
    """
    Pozovi Claude API da generira N objava za tjedan.
    Svaka objava sadrži verzije za LinkedIn, Facebook i Instagram.
    """
    import requests

    news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "Nema konkretnih vijesti ovaj tjedan."

    prompt = f"""Generiraj {num_posts} objava za društvene mreže za VSS Digital.

BRAND IDENTITY (obavezno se drži ovoga):
{brand_dna}

VIJESTI / TEME ZA OVAJ TJEDAN:
{news_text}

Za SVAKU objavu napiši:
1. Jednu rečenicu o temi (topic)
2. LinkedIn verziju (200-400 znakova, edukativno-profesionalni ton)
3. Facebook verziju (150-300 znakova, topli lokalni ton, poziv na akciju)
4. Instagram verziju (80-150 znakova + max 10 hashtagova, vizualni stil)
5. Prijedlog za sliku (što bi na njoj trebalo biti)

PRAVILA:
- Piši isključivo na hrvatskom jeziku
- Ne koristi AI žargon — "digitalni asistent", "automatski sustav", "pametni booking"
- Fokus na UŠTEDU VREMENA — to je glavna vrijednost
- LinkedIn: završi s pitanjem za poticanje komentara
- Facebook: topao ton, kao da pišeš lokalnom poduzetniku
- Instagram: kratko, vizualno, do hashtagova

Vrati u JSON formatu:
{{"posts": [
  {{
    "date": "2026-06-01",
    "topic": "...",
    "linkedin": "...",
    "facebook": "...",
    "instagram": "...",
    "image_suggestion": "..."
  }}
]}}
"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": "Ti si content marketing stručnjak za lokalne biznise u Hrvatskoj. Specijaliziran si za pisanje objava za društvene mreže koje konvertiraju. Pišeš na čistom hrvatskom, bez anglicizama. Output uvijek u JSON formatu.",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")

    data = response.json()
    content_text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            content_text += block.get("text", "")

    # Parsiraj JSON iz odgovora
    # Prvo pokušaj naći JSON blok
    if "```json" in content_text:
        json_str = content_text.split("```json")[1].split("```")[0].strip()
    elif "```" in content_text:
        json_str = content_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = content_text.strip()

    # Ukloni leading/trailing non-JSON
    while json_str and not json_str.startswith("{"):
        json_str = json_str[1:]
    while json_str and not json_str.endswith("}"):
        json_str = json_str[:-1]

    result = json.loads(json_str)
    return result["posts"]


def save_posts(posts: list[dict]):
    """Spremi svaku objavu kao pojedinačni .md file u pending/."""
    CONTENT_PENDING.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, post in enumerate(posts):
        date_str = post.get("date", datetime.now().strftime("%Y-%m-%d"))
        filename = f"{date_str}-{i+1:02d}.md"
        filepath = CONTENT_PENDING / filename

        content = f"""# {post.get('topic', 'Objava')}

> Generirano: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Status: čeka odobrenje
> Platforme: LinkedIn | Facebook | Instagram

---

## LinkedIn (profesionalno)

{post.get('linkedin', '')}

---

## Facebook (toplo/lokalno)

{post.get('facebook', '')}

---

## Instagram (kratko/vizualno)

{post.get('instagram', '')}

---

## Prijedlog za sliku
{post.get('image_suggestion', '')}
"""
        filepath.write_text(content, encoding="utf-8")
        saved.append(str(filepath))
        print(f"  ✓ {filename}")

    return saved


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("❌ API ključ nije postavljen. Stavi ANTHROPIC_API_KEY u .env ili GitHub Secrets.")
        sys.exit(1)

    print("📰 VSS Digital — Content Generator")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Učitaj brand DNA
    brand_dna = load_brand_dna()
    print(f"✓ Brand DNA učitan ({len(brand_dna)} znakova)")

    # News items — mogu doći iz environment varijable ili filea
    news_input = os.environ.get("CONTENT_NEWS", "")
    news_items = [n.strip() for n in news_input.split("\n") if n.strip()]

    if news_items:
        print(f"✓ Vijesti: {len(news_items)} tema")
    else:
        print("ℹ Nema specificiranih vijesti — AI će generirati opći content")

    # Generiraj
    print("\n🤖 Generative AI radi...")
    posts = generate_content(api_key, brand_dna, news_items)
    print(f"✓ Generirano {len(posts)} objava")

    # Spremi
    print(f"\n💾 Spremam u content/pending/...")
    saved = save_posts(posts)

    print(f"\n✅ Gotovo! {len(saved)} objava čeka tvoj pregled u content/pending/")
    print(f"   Pregledaj, uredi ako treba, pa premjesti u content/approved/")


if __name__ == "__main__":
    main()
