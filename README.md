# VSS Digital — Social Media Content Automation

Automatsko generiranje i objavljivanje sadržaja za društvene mreže (LinkedIn, Facebook, Instagram) za VSS Digital.

## Kako radi

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  AI generira │ ──→ │ Ti pregledaš │ ──→ │ Auto-objava  │
│  content     │     │ i odobriš    │     │ svaki dan    │
└─────────────┘     └──────────────┘     └──────────────┘
```

## Tjedni flow

1. **Ponedjeljak 08:00** — GitHub Action pokrene AI, generira 5-7 objava za tjedan
2. **Ti otvoriš PR** ili pregledaš `.md` fileove u `content/pending/`
3. **Premjestiš odobrene** u `content/approved/` (ili odobriš kroz PR)
4. **Svaki dan u 12:00** — objavi se jedna odobrena objava na sve platforme

## Mape

```
content/
├── pending/     # AI generirani draftovi, čekaju tvoj pregled
├── approved/    # Ti odobrio, čekaju red za objavu
└── posted/      # Objavljen content (arhiva)
```

## Postavljanje

### 1. Forkaj / kloniraj repo

```bash
git clone https://github.com/vssdigital/social-content.git
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
