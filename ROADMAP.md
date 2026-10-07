# Roadmap

Anforderungen: [docs/requirements.md](docs/requirements.md) · Entscheidungen: [docs/decisions/](docs/decisions/)

## M0 — Hygiene und CI-freier Skill
- [x] Theme in `base/layouts.css`, `base/components.css` und Brand-Tokens zerlegt
- [x] Hartcodierte Farben in Komponenten durch Tokens ersetzt
- [x] `build-theme.py` (Logo als Data-URI)
- [x] Pixelgleiche Regression gegen altes Theme (S1: 22, S6: 131 Folien)
- [ ] Brand `neutral` anlegen, `autarkit` aus dem Repo in den Brand-Store verschieben
- [ ] Brand-Auflösung (Deck → Projekt → User → eingebaut)
- [ ] Brand-Format erweitern: `layouts.css`, `GUIDELINES.md`, `fonts/`
- [ ] `doctor` (Node, marp-cli, Chrome, Schriften, optional LibreOffice, pdftocairo)
- [ ] Referenz-Deck `tests/fixtures/` mit allen Klassen
- [ ] `install.sh` verlinkt nach `~/.agents/skills` (Copilot CLI), optional `~/.claude/skills`, `~/.copilot/skills`

## M1 — Deck-Ordner, Vorschau, Export
- [ ] `new` (Deck-Skelett, Brand-Snapshot), `brand-sync`
- [ ] `serve`: `marp -s` im Hintergrund, URL melden
- [ ] `export pdf` (`--pdf-notes --pdf-outlines`)
- [ ] `export html` mit Presenter View (Bilder-Pfade, `file://` prüfen)
- [ ] marp-cli auf getestete Version pinnen
- [ ] S1 als Testfall migrieren

## M2 — Spike Layout-Treue
- [ ] Ein Firmenlayout (PPTX + Showcase-PDF + Screenshot), drei Layouts in Marp
- [ ] Slot-Modell klären (HTML-Divs mit Markdown)
- [ ] Hintergrund: Data-URI vs. Datei
- [ ] Abweichung per Differenzbild messen

## M3 — CI-Import
- [ ] Stufe A: Extraktion aus PPTX
- [ ] Hintergründe: LibreOffice → PDF/PNG-Export → Screenshots
- [ ] Stufe B: Agent-Mapping, `layouts.css`, `GUIDELINES.md`
- [ ] Korrekturschleife mit Differenzbild
- [ ] `brand preview`, Font-Warnung

## M4 — Container und Politur
- [ ] `pack`/`unpack` (`.deck`)
- [ ] Optionaler Adapter `import-deck` über `pptx2md --marp`
- [ ] `SKILL.md` vollständig, ersetzt Command `/presentation`
- [ ] Migration S6, Release v0.1.0

## Ideen (ungeplant)
- Eigener Browser-Editor (Text im Browser, Elemente verschieben); bewusst ausgeklammert, siehe 0001
- Editierbarer PPTX-Export
- Mehrsprachige Footer
