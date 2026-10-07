# Roadmap

## Meilenstein 1 — Theme-Fundament
- [x] Theme in `base/layouts.css`, `base/components.css` und Brand-Tokens zerlegt
- [x] Hartcodierte Farben in Komponenten durch Tokens ersetzt
- [x] `build-theme.py` (Logo als Data-URI, ein Theme, eine Datei)
- [x] Pixelgleiche Regression gegen altes Theme (S1: 22, S6: 131 Folien)
- [ ] Ungenutzte Komponenten (29 von 40) visuell testen oder entfernen
- [ ] Referenz-Deck `tests/fixtures/` mit allen Klassen

## Meilenstein 2 — Deck-Ordner und Export
- [ ] Deck-Skelett: `<slug>/<slug>.md`, `marp.config.mjs`, `theme/`, `assets/`
- [ ] `new` legt Deck mit Brand-Snapshot an, `brand-sync` aktualisiert
- [ ] `serve`: `marp -s` im Hintergrund, URL melden (paralleles Arbeiten Mensch + Agent)
- [ ] `export pdf` (`--pdf-notes --pdf-outlines`)
- [ ] `export html` mit Presenter View (relative Bilder prüfen, ggf. `dist/` + ZIP)
- [ ] S1 als Testfall migrieren

## Meilenstein 3 — CI-Import
- [ ] `import-brand <datei.pptx>`: Farben (`a:clrScheme`), Schriften (`a:fontScheme`), Logos/Medien, Layoutnamen → `brands/<name>/`
- [ ] Mapping Layouts → `title`/`section`/`cols`/`closing`
- [ ] Meldung bei fehlenden Font-Dateien
- [ ] Test mit echter Kunden-Vorlage

## Meilenstein 4 — Skill fertig
- [ ] `SKILL.md` mit allen Befehlen, ersetzt globalen Command `/presentation`
- [ ] Migration S6

## Ideen (ungeplant)
- Editierbarer PPTX-Export
- Brand-Vorschau-Deck, das alle Layouts zeigt
- Mehrsprachige Footer
