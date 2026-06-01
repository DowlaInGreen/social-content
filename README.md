# VSS Digital — Social Media Content Automation

Automatsko generiranje i objavljivanje sadržaja za društvene mreže (LinkedIn, Facebook, Instagram) za VSS Digital.
Sada s **automatskim generiranjem brandiranih slika i kratkih reelsova**!

## Kako radi

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  AI generira │ ──→ │ Ti pregledaš │ ──→ │ Auto-objava  │
│  content +   │     │ i odobriš    │     │ svaki dan    │
│  mediji      │     │              │     │ sa slikom    │
└─────────────┘     └──────────────┘     └──────────────┘
```

## Tjedni flow

1. **Ponedjeljak 08:00** — GitHub Action pokrene AI, generira 5-7 objava za tjedan
2. **Automatski se generiraju** brandirane slike (.png) i kratki reels (.mp4)
3. **Ti otvoriš PR** ili pregledaš `.md` fileove u `content/pending/`
4. **Premjestiš odobrene** u `content/approved/` (ili odobriš kroz PR)
5. **Svaki dan u 12:00** — objavi se jedna odobrena objava na sve platforme
   - LinkedIn: tekst + slika
   - Facebook: tekst + slika
   - Instagram: slika (ili reel za veći engagement)

## Medijski templateovi

`scripts/generate_media.py` automatski detektira koji vizualni template odgovara objavi:

| Template | Kad se koristi | Primjer |
|----------|---------------|---------|
| **📊 Stats** | Objave s brojkama | "10 sati tjedno", "40 sati mjesečno" |
| **💬 Quote** | Priče/citati klijenata | "Prije sam stalno prekidala posao..." |
| **❓ Question** | Pitanja za engagement | "Jeste li znali da..." |
| **🛠️ Feature** | Usluge i servisi | "Novo u ponudi..." |

Slike: 1080×1080px (kvadratne)
Reels: 1080×1920px (9:16 vertikalni, ~17 sekundi)

## Mape

```
content/
├── pending/     # AI generirani draftovi, čekaju tvoj pregled
├── approved/    # Ti odobrio, čekaju red za objavu
├── posted/      # Objavljen content (arhiva)
└── media/       # Automatski generirane slike (.png) i reels (.mp4)
```

## Postavljanje

### 1. Forkaj / kloniraj repo

```bash
git clone https://github.com/DowlaInGreen/social-content.git
```

### 2. Dodaj API ključeve u GitHub Secrets

| Secret | Opis |
|--------|------|
| `ANTHROPIC_API_KEY` | Za generiranje contenta (Claude) |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn API token |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Meta (FB/IG) token |

### 3. Brand DNA

Brand identitet se definira u `brand-dna.md` — ton, publika, platformski stilovi. AI model koristi ovo kao system prompt.

### 4. Pokreni lokalno (opcionalno)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/generate.py
```

### 5. Generiraj medije zasebno

```bash
python scripts/generate_media.py                    # sve approved objave
python scripts/generate_media.py content/approved/2026-06-01-01.md  # jedna objava
python scripts/generate_media.py --no-video          # samo slike (brže)
```
