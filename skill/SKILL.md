---
name: marp-presentation
description: Marp-Präsentationen mit austauschbarer Brand (CI) bauen, live im Browser bearbeiten und als PDF/HTML exportieren. Aufrufen bei Folien, Slide-Decks, Präsentationen auf Markdown-Basis. STATUS - in Entwicklung, nur Theme-Build verfügbar (siehe ROADMAP.md im Repo).
---

# marp-presentation

Marp-Skill mit zwei Schichten: stabile Layouts (`base/`) und austauschbare Brands (`brands/<name>/`).

## Stand

Verfügbar:
- `scripts/build-theme.py <brand-dir> <out.css>` baut ein einzelnes, selbstständiges Marp-Theme (Brand-Tokens + Logo als Data-URI + Layouts + Komponenten).

Noch nicht verfügbar (siehe `ROADMAP.md`): Deck-Ordner anlegen, Live-Server, PDF/HTML-Export mit Presenter View, PPTX-CI-Import.

## Folienklassen

`title` (1× `#`, `##`, `<div class="title-meta">`), `section` (`# Titel`, `## N` — nur Zahl), `cols`, `closing`, leer = Inhaltsfolie. Komponenten: siehe `base/components.css`.

## Regeln

- Layouts nicht pro Deck ändern, nur Brand-Tokens.
- `theme.css` im Deck ist generiert, nicht von Hand editieren.
- Frontmatter: `marp: true`, `theme: <brand-name>`, `paginate: true`, `html: true`, `footer`.
