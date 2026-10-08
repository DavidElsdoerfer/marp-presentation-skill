# STATUS — Stand des Projekts

Stand: 2026-10-08. **Lies diese Datei zuerst**, wenn du (Agent oder Mensch) auf einem anderen Rechner weiterarbeitest.
Regeln für Änderungen: `AGENTS.md`. Ziele: `docs/requirements.md`. Entscheidungen: `docs/decisions/`.

## Was fertig und geprüft ist

| Bereich | Stand | Geprüft durch |
|---|---|---|
| Deck-Ordner anlegen, Live-Vorschau (nur localhost), PDF, HTML mit Presenter View | fertig | Tests inkl. echtem Browser (Live-Reload, Presenter View, Portabilität) |
| Brand-System (neutral eingebaut, eigene Brands im Brand-Store) | fertig | Unit-Tests |
| CI-Import aus PowerPoint (`brand import/showcase/preview/compare`) | fertig, **nur mit synthetischer und LibreOffice-Vorlagen geprüft** | Tests, Vergleich Original ↔ Marp (≈ 5 % = Textglättung) |
| `.deck`-Container (`pack`/`unpack`) | fertig | Tests inkl. manipulierter Archive |
| Übernahme alter PPTX-Decks (`import-deck`, optional über `pptx2md`) | fertig | Tests mit echtem Werkzeug |
| Härtung nach unabhängigem Review | fertig | `tests/test_review_findings.py`, `docs/decisions/0009-review-haertung.md` |

Tests: `python3 -m unittest discover tests` (Render-/Browser-Tests brauchen Chrome und Node, sonst übersprungen).

## Was ausdrücklich NICHT geprüft ist (hier liegt die Arbeit auf dem Firmenrechner)

1. **Echte, in PowerPoint erstellte Firmenvorlage.** Bisher nur eine synthetische Vorlage und LibreOffice-Beispiele. Offen: echte Platzhalter-
   und Layoutvielfalt, mehrere Folienmaster (Tokens/Logo kommen nur vom ersten), Aufzählungszeichen, Absatzabstände, Datumsfeld.
2. **PDF-Export leerer Platzhalter in PowerPoint.** Mit LibreOffice bestätigt, mit PowerPoint selbst nicht. Davon hängt der Weg
   „nur PowerPoint, kein LibreOffice“ ab (`docs/import-workflow.md`, Pfad B).
3. **Copilot CLI.** `install.sh` verlinkt nach `~/.agents/skills` (laut Drittquelle der Pfad für Copilot CLI); nie mit Copilot CLI ausprobiert.

### So testest du auf dem Firmenrechner (Ablauf)

```bash
./install.sh && python3 skill/scripts/doctor.py           # Voraussetzungen
marp-deck brand showcase firma.pptx --out showcase/        # nur nötig ohne LibreOffice: zwei PPTX → in PowerPoint als PDF exportieren
marp-deck brand import firma.pptx --name firma [--backgrounds leer.pdf --reference gefuellt.pdf] [--guidelines richtlinie.pdf] [--fonts ordner/]
marp-deck brand compare firma                              # Bilder ansehen: Hintergründe deckungsgleich? nur Glyphenrauschen im Differenzbild?
marp-deck brand preview firma && marp-deck serve firma-vorschau
```
Ergebnis festhalten (Abweichungen, was falsch zugeordnet wurde, Warnungen) und hier eintragen: Fehler als Test mit synthetischer
Vorlage nachstellen (`tests/template_factory.py`), dann beheben. **Firmenvorlagen, Logos, Schriften, Richtlinien nie ins Repo** (öffentlich).

## Entscheidungen des Autors (2026-10-08)

- Spuren im öffentlichen Git-Verlauf (frühes autarkit-Logo, Firmenname im Kommentar): **so lassen**, kein History-Rewrite.
- S6-Schulungsreihe: **ignorieren**, wird bei Bedarf mit dem Skill neu aufgebaut. S1 liegt als Deck-Ordner vor (Testfall).
- Alter globaler Command `/presentation`: **entfernt** (Sicherung außerhalb des Repos).
- Release v0.1.0: **offen** (nach dem Test mit einer echten Firmenvorlage).
- Lizenz: MIT.
- Live-Bearbeiten im Browser: **nicht gewünscht** (Vorschau lädt nur nach). Marp bleibt die Basis (`docs/decisions/0001-marp-als-basis.md`).

## Bekannte, bewusst akzeptierte Grenzen

- Decks rendern rohes HTML und lokale Dateien; ein fremdes Deck kann beim Export lokale Dateien einbetten. Fremde Decks vor dem Export ansehen.
- `npx` lädt die gepinnte marp-cli-Version ohne Integritätsprüfung (kein Lockfile).
- Layout-Treue: Textposition ±1–2 px, Zeilenumbrüche können abweichen; bei großer Schrift zeigt `brand compare` bis ~15 % (Glyphenkanten).
- Diagramme, SmartArt, Animationen werden nicht übernommen.

## Nächste Schritte

Siehe `ROADMAP.md`. Aktuell in Arbeit: Integration mit der VS-Code-Erweiterung „Marp for VS Code“ (`docs/vscode.md`).
