# 0009 — Unabhängiger Review und Härtung

Status: umgesetzt (2026-10-07)

Ein unabhängiger Review (lesend, jeder Befund reproduziert) fand Lücken im Vertrauensmodell für fremde Archive, Vorlagen
und Brands. Alle Befunde sind mit Regressionstests abgedeckt (`tests/test_review_findings.py`).

## Behoben
- **Code aus fremdem Archiv:** `marp.config.mjs` wird von marp-cli als JavaScript ausgeführt. `unpack` schreibt die Standard-Config
  neu; `serve`/`export` verweigern abweichende Configs (`--trust-config`, `repair-config`).
- **Strings aus der PPTX in CSS/Markdown:** Farben nur `[0-9a-f]{6}`, Schriftnamen und Layoutnamen bereinigt; Brand-CSS lehnt
  `@import` und externe URLs ab (Themes sind offline und in sich geschlossen).
- **Zustandsdatei aus Archiv (`serve.json`):** strikt validiert, URL aus validierten Zahlen, `--stop` nur für Prozesse, die wirklich
  unser marp-Server sind (cmdline und Prozessgruppe); `unpack` verwirft `.marp-deck/`, `.git/`, `dist/`, `node_modules/`.
- **Brand im Arbeitsordner überschrieb `neutral`:** Projektordner-Brands haben jetzt niedrigste Priorität; ein Verzeichnisname gilt nur
  als Pfad, wenn er ausdrücklich wie einer geschrieben ist; Auflösung auch über `brand.json:name`.
- **Symlinks im Brand:** der Snapshot folgt ihnen nicht mehr und entfernt sie; Ausschluss von `guidelines/`/`reference/` nur auf oberster Ebene.
- **Showcase enthielt Reste der Originalfolien** (Vorschaubild, Folientitel in `app.xml`, Kommentare, nur von Folien genutzte Medien):
  Erreichbarkeitsdurchlauf entfernt alles, was nicht mehr referenziert wird; Eintrags- und Größengrenzen.
- **Fehlerpfade:** keine halbfertigen Brands/Decks mehr nach Abbrüchen; Eingaben werden vor dem Schreiben geprüft; `--name`/`--slug` validiert.
- **`brand import --replace`** (Neuimport mit Sicherung, übernimmt `custom.css`); `brand sync` sichert Handänderungen im Snapshot.
- Weitere: `pack` mit mtime vor 1980, YAML-sichere Titel, `CLOSING_RE` mit Wortgrenzen, natürliche Sortierung auch bei `--reference`,
  Bildzuordnung im Adapter über Pfad statt Basisname (inkl. `%20`, gefährliche Schemata entfernt), LibreOffice mit eigenem Profil,
  `doctor` prüft `compare`, `install.sh --target` ohne Argument.

## Bewusst offen
- Decks rendern rohes HTML und lokale Dateien (`html: true`, `allowLocalFiles`): ein fremdes Deck kann beim Export lokale Dateien einbetten.
  Das ist für lokale Bilder nötig; Gegenmaßnahme ist Dokumentation (fremde Decks vor dem Export ansehen), keine technische Sperre.
- `npx -y @marp-team/marp-cli@<Version>` lädt aus dem Netz ohne Integritätsprüfung; die Version ist gepinnt, ein Lockfile fehlt.
- Mehrere Folienmaster: Tokens/Logo/Schriften nur vom ersten Master.
