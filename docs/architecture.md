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
