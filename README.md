# marp-presentation-skill

Claude-Code-/opencode-Skill für Marp-Präsentationen mit austauschbarer Brand (CI).

**Ziele**
- Mensch und Agent bearbeiten dasselbe Markdown-Deck parallel; Live-Vorschau im Browser (`marp -s`) lädt bei jeder Änderung nach, keine Zusatzanwendung. Bearbeitet wird in Dateien, nicht im Browser.
- Jedes Deck ist ein selbstständiger Ordner (Theme, Assets, Config) und braucht keine kopierten Dateien von außen.
- Sauberer PDF-Export und HTML-Export mit Presenter View.
- Brands aus PPTX-Folienmastern importieren (Farben, Schriften, Logos, Layouts).

**Status:** in Entwicklung. Siehe [ROADMAP.md](ROADMAP.md) und [CHANGELOG.md](CHANGELOG.md).

## Aufbau

```
skill/                 das eigentliche Skill-Verzeichnis (wird nach ~/.claude/skills/ gelinkt)
  SKILL.md
  base/                layouts.css, components.css — markenneutral
  brands/<name>/       tokens.css, brand.json, assets/
  scripts/             marp-deck (CLI), build-theme.py, pptx_extract.py, pptx_showcase.py, brand_import.py, brand_preview.py, doctor.py
docs/                  Architektur, Brand-Format
tests/                 Unit- und Render-Tests, Fixture-Deck, Theme-Vergleich
```

## Installation

```bash
./install.sh            # verlinkt skill/ nach ~/.agents/skills und ~/.claude/skills (falls vorhanden)
./install.sh --all      # zusätzlich ~/.copilot/skills
./install.sh --uninstall
python3 skill/scripts/doctor.py   # Voraussetzungen prüfen
```

## Theme bauen

```bash
python3 skill/scripts/build-theme.py neutral out/neutral.css
python3 skill/scripts/build-theme.py --list          # verfügbare Brands
```

Eigene Brands liegen im Brand-Store `~/.config/marp-presentation/brands/<name>/`, siehe [docs/brand-format.md](docs/brand-format.md).

## Benutzung

```bash
skill/scripts/marp-deck new "Mein Titel" --brand neutral   # Deck-Ordner mit Quelle, Config, Theme-Snapshot
skill/scripts/marp-deck serve mein-titel                   # Live-Vorschau im Browser (nur localhost)
skill/scripts/marp-deck export pdf mein-titel              # dist/mein-titel.pdf (mit Notizen, Gliederung)
skill/scripts/marp-deck export html mein-titel             # dist/mein-titel.html: eine Datei, Presenter View mit Taste P
skill/scripts/marp-deck brand sync mein-titel              # Brand-Snapshot aktualisieren
skill/scripts/marp-deck serve mein-titel --stop
```

In einem Agent (Claude Code, opencode, Copilot CLI) genügt: „Mach mir eine Präsentation zu …“ — der Agent liest `skill/SKILL.md`.

## Decks weitergeben und übernehmen

```bash
skill/scripts/marp-deck pack mein-titel                 # → mein-titel.deck (ZIP), ohne dist/ und ohne Original-Richtlinien
skill/scripts/marp-deck unpack mein-titel.deck --dir ~/Vorträge
skill/scripts/marp-deck import-deck alter-vortrag.pptx --brand firma   # optional, braucht pptx2md
```

## CI aus PowerPoint übernehmen

```bash
skill/scripts/marp-deck brand import firma.pptx --name firma --guidelines richtlinie.pdf --fonts ~/fonts/firma/
skill/scripts/marp-deck brand compare firma     # Original | Marp | Differenz je Layout
skill/scripts/marp-deck new "Mein Titel" --brand firma
```

Siehe [docs/import-workflow.md](docs/import-workflow.md) (auch für Rechner ohne LibreOffice).

## Voraussetzungen

Node (für `npx @marp-team/marp-cli`), Chrome/Chromium (PDF, PNG), Python 3. Optional für den CI-Import: LibreOffice, `pdftocairo`, ImageMagick.

## Tests

```bash
python3 -m unittest discover tests      # Unit-Tests + Render-Test (braucht Chrome, sonst übersprungen)
tests/compare-themes.sh deck.md alt.css neu.css   # Pixelvergleich bei Theme-Änderungen
```
