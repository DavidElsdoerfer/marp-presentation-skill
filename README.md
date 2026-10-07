# marp-presentation-skill

Claude-Code-/opencode-Skill für Marp-Präsentationen mit austauschbarer Brand (CI).

**Ziele**
- Mensch und Agent bearbeiten dasselbe Markdown-Deck parallel, Live-Vorschau im Browser (`marp -s`), keine Zusatzanwendung.
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
  scripts/             build-theme.py, (geplant: new, serve, export, import-brand)
docs/                  Architektur, Brand-Format
tests/                 Regressionstest für Theme-Änderungen
```

## Installation

```bash
./install.sh     # verlinkt skill/ nach ~/.claude/skills/marp-presentation
```

## Theme bauen

```bash
python3 skill/scripts/build-theme.py skill/brands/autarkit out/autarkit.css
```

## Voraussetzungen

Node (für `npx @marp-team/marp-cli`), Chrome/Chromium (PDF, PNG), Python 3.
