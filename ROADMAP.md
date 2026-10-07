# Roadmap

Anforderungen: [docs/requirements.md](docs/requirements.md) · Entscheidungen: [docs/decisions/](docs/decisions/)

## M0 — Hygiene und CI-freier Skill

**Fertig, wenn:** ein frischer Clone ohne private Daten ein `neutral`-Deck baut und der Regressionstest grün ist.

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

**Fertig, wenn:** eine Änderung der `.md` im Browser erscheint, PDF und HTML mit der Vorschau übereinstimmen und `P` im exportierten HTML die Presenter View öffnet.  
**Zu prüfen:** relative Bildpfade im HTML-Export (`dist/`), Presenter View über `file://`.

- [ ] `new` (Deck-Skelett, Brand-Snapshot), `brand-sync`
- [ ] `serve`: `marp -s` im Hintergrund, URL melden
- [ ] `export pdf` (`--pdf-notes --pdf-outlines`)
- [ ] `export html` mit Presenter View (Bilder-Pfade, `file://` prüfen)
- [ ] marp-cli auf getestete Version pinnen
- [ ] S1 als Testfall migrieren

## M2 — Spike Layout-Treue

**Fertig, wenn:** die gemessene Abweichung zum Original vorliegt und entschieden ist, ob Marp für die Layouts reicht. Offene Fragen: Slot-Modell, Hintergrund als Data-URI oder Datei, Treue mit XML-Werten plus Original-Hintergrund.

- [ ] Ein Firmenlayout (PPTX + Showcase-PDF + Screenshot), drei Layouts in Marp
- [ ] Slot-Modell klären (HTML-Divs mit Markdown)
- [ ] Hintergrund: Data-URI vs. Datei
- [ ] Abweichung per Differenzbild messen

## M3 — CI-Import

**Fertig, wenn:** eine Firmenvorlage ohne Handarbeit am CSS ein Brand ergibt, dessen Vorschau im Differenzbild unter der festgelegten Schwelle liegt.

- [ ] Stufe A: Extraktion aus PPTX
- [ ] Hintergründe: LibreOffice → PDF/PNG-Export → Screenshots
- [ ] Stufe B: Agent-Mapping, `layouts.css`, `GUIDELINES.md`
- [ ] Korrekturschleife mit Differenzbild
- [ ] `brand preview`, Font-Warnung

## M4 — Container und Politur

**Fertig, wenn:** ein Deck als `.deck` gepackt, auf einem anderen Rechner entpackt und ohne Anpassung gebaut werden kann.

- [ ] `pack`/`unpack` (`.deck`)
- [ ] Optionaler Adapter `import-deck` über `pptx2md --marp`
- [ ] `SKILL.md` vollständig, ersetzt Command `/presentation`
- [ ] Migration S6, Release v0.1.0

## Zuordnung Anforderung → Meilenstein

| Anforderung | Meilenstein |
|---|---|
| A1, A2 (Vorschau, parallele Dateibearbeitung) | M1 |
| B1 (Deck bringt Assets mit) | M1 |
| B2 (Repo, Agent-Skill) | M0, M4 |
| B3 (CI-frei, Brand-System) | M0 |
| C1 (PDF), C2 (HTML + Presenter View) | M1 |
| D1, D2 (PPTX-Import, Guidelines) | M2, M3 |
| E4 (portabler Ordner/Container) | M1, M4 |

## Arbeitsweise

- Pro Meilenstein ein Branch, Merge erst nach grünem Regressionstest, Tag pro Meilenstein.
- Vor jeder Theme-Änderung `tests/compare-themes.sh`.
- Nichts als „fertig“ markieren, was nicht gegen ein echtes Deck gerendert wurde.
- marp-cli bleibt auf eine getestete Version gepinnt; Updates bewusst und mit Regressionstest.

## Risiken

1. **Slots in Marp** (kein natives Modell) — Spike M2.
2. **Presenter View und Bilder im HTML-Export** sind ungeprüft — M1.
3. **Layout-Treue** hängt an der Vorlage; „recht gut, nicht perfekt“ ist realistisch.
4. **Schriften:** häufigste Abweichungsursache; nur meldbar, nicht lösbar.
5. **Marp-Updates** können das Rendering ändern.

## Ideen (ungeplant)
- Eigener Browser-Editor (Text im Browser, Elemente verschieben); bewusst ausgeklammert, siehe 0001
- Editierbarer PPTX-Export
- Mehrsprachige Footer
