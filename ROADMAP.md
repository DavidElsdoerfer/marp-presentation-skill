# Roadmap

Anforderungen: [docs/requirements.md](docs/requirements.md) · Entscheidungen: [docs/decisions/](docs/decisions/)

## M0 — Hygiene und CI-freier Skill

**Fertig, wenn:** ein frischer Clone ohne private Daten ein `neutral`-Deck baut und der Regressionstest grün ist.

- [x] Theme in `base/layouts.css`, `base/components.css` und Brand-Tokens zerlegt
- [x] Hartcodierte Farben in Komponenten durch Tokens ersetzt
- [x] `build-theme.py` (Logo als Data-URI)
- [x] Pixelgleiche Regression gegen altes Theme (S1: 22, S6: 131 Folien)
- [x] Brand `neutral` anlegen, `autarkit` aus dem Repo in den Brand-Store verschieben
- [x] Brand-Auflösung (Deck → Projekt → User → eingebaut)
- [x] Brand-Format erweitern: `layouts.css`, `GUIDELINES.md`, `fonts/`
- [x] `doctor` (Node, marp-cli, Chrome, Schriften, optional LibreOffice, pdftocairo)
- [x] Referenz-Deck `skill/examples/all-classes.md` mit allen Klassen (damit sind alle Komponenten visuell geprüft)
- [x] `install.sh` verlinkt nach `~/.agents/skills` (Copilot CLI), optional `~/.claude/skills`, `~/.copilot/skills`
- [ ] Offen für den Autor: Lizenz wählen; autarkit-Logo/-Tokens stehen noch im öffentlichen Git-Verlauf (siehe `docs/open-questions.md`)

## M1 — Deck-Ordner, Vorschau, Export

**Fertig, wenn:** eine Änderung der `.md` im Browser erscheint, PDF und HTML mit der Vorschau übereinstimmen und `P` im exportierten HTML die Presenter View öffnet.  
**Geprüft:** Bildpfade im HTML-Export (jetzt eingebettet, Entscheidung 0005), Presenter View über `file://` (funktioniert), Server nur auf localhost (0006).

- [x] `new` (Deck-Skelett, Brand-Snapshot), `brand-sync`
- [x] `serve`: `marp -s` im Hintergrund, URL melden
- [x] `export pdf` (`--pdf-notes --pdf-outlines`)
- [x] `export html` mit Presenter View (Bilder-Pfade, `file://` prüfen)
- [x] marp-cli auf getestete Version pinnen
- [x] S1 als Testfall migrieren (neuer Ordner neben den alten Dateien; 22/22 Folien pixelgleich)

## M2 — Spike Layout-Treue

**Fertig, wenn:** die gemessene Abweichung zum Original vorliegt und entschieden ist, ob Marp für die Layouts reicht. Offene Fragen: Slot-Modell, Hintergrund als Data-URI oder Datei, Treue mit XML-Werten plus Original-Hintergrund.

- [x] Spike mit synthetischer Vorlage (6 Layouts) und LibreOffice-Vorlagen statt Firmenlayout: Abweichung 4,7–6,7 % (nur Textglättung)
- [x] Slot-Modell klären (HTML-Divs mit Markdown)
- [x] Hintergrund: Data-URI vs. Datei
- [x] Abweichung per Differenzbild messen

## M3 — CI-Import

**Fertig, wenn:** eine Firmenvorlage ohne Handarbeit am CSS ein Brand ergibt, dessen Vorschau im Differenzbild nur Textglättung zeigt. **Stand:** mit synthetischer und LibreOffice-Vorlagen erreicht; mit einer echten PowerPoint-Firmenvorlage noch zu prüfen.

- [x] Stufe A: Extraktion aus PPTX
- [x] Hintergründe: LibreOffice → PDF/PNG-Export aus PowerPoint → Rekonstruktion aus Grafiken (nur Screenshots: Agent von Hand, siehe import-workflow.md)
- [x] Stufe B: Agent-Mapping, `layouts.css`, `GUIDELINES.md`
- [x] Korrekturschleife mit Differenzbild
- [x] `brand preview`, Font-Warnung

## M4 — Container und Politur

**Fertig, wenn:** ein Deck als `.deck` gepackt, auf einem anderen Rechner entpackt und ohne Anpassung gebaut werden kann.

- [x] `pack`/`unpack` (`.deck`)
- [x] Optionaler Adapter `import-deck` über `pptx2md --marp`
- [x] `SKILL.md` vollständig
- [ ] globalen Command `/presentation` ablösen (liegt außerhalb des Repos, Entscheidung des Autors)
- [ ] Migration S6 (Entscheidung offen: ein Deck pro Session, geteilte Assets)
- [ ] Release v0.1.0 (nach Test mit echter PowerPoint-Firmenvorlage)

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
