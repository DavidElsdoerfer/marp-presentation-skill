# Architektur

## Schichten
- `skill/base/` — Layouts und Komponenten, markenneutral, nutzen nur CSS-Variablen.
- `skill/brands/<name>/` — `tokens.css` (`:root`-Variablen), `brand.json` (`name`, `logo`), `assets/`.
- `scripts/build-theme.py` — fügt zusammen: `/* @theme <name> */` + Tokens + `--logo` (Data-URI) + Layouts + Komponenten.

## Deck-Ordner (geplant)
```
<slug>/
├── <slug>.md
├── marp.config.mjs
├── theme/theme.css   generiert, Snapshot des Brands
└── assets/
```
Snapshot statt gemeinsamer Pfad/Symlink: Decks bleiben portabel und ändern sich nicht rückwirkend.

## Export
PDF und PNG über Chromium; HTML (Bespoke) mit Presenter View (Taste `P`). Live-Bearbeiten über `marp -s`.

## CLI (geplant, ab M1)

Ein Einstieg `marp-deck` (Python-Standardbibliothek, ruft gepinntes `marp-cli`):

| Befehl | Zweck |
|---|---|
| `new` | Deck-Ordner mit Brand-Snapshot anlegen |
| `serve` | `marp -s` im Hintergrund, URL melden |
| `export pdf\|html` | PDF bzw. HTML mit Presenter View |
| `brand list\|import\|preview\|sync` | Brands verwalten, PPTX importieren |
| `pack` / `unpack` | `.deck` (ZIP) erzeugen/entpacken |
| `doctor` | Voraussetzungen prüfen |
