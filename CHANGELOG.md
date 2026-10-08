# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).

## [Unveröffentlicht]

### Hinzugefügt
- `marp-deck suggest`: schlägt Zielordner und Namen für ein neues Deck vor (vorhandene Decks, Präsentationsordner, Namensschema, Datum-Präfix; schreibt nichts)
- `marp-deck new` (auch `import-deck`, `brand preview`) trägt neue Decks automatisch in die Projekt-Einstellungen ein, wenn dort schon Marp-Themes registriert sind
- Integration mit Marp for VS Code: jedes Deck bringt `.vscode/settings.json` mit; `marp-deck vscode` trägt Themes mehrerer Decks in Projekt-Einstellungen ein (`docs/vscode.md`, Entscheidung 0010, `tests/test_vscode.py`)
- `STATUS.md` (Stand, ungeprüfte Bereiche, Ablauf für den Firmenrechner); Entscheidungen vom 2026-10-08 in `docs/open-questions.md`
- MIT-Lizenz (`LICENSE`)
- `brand import --replace` (Neuimport mit Sicherung, übernimmt `custom.css`, `GUIDELINES.md`, Schriften), `repair-config`, `--trust-config`
- Sicherung von Handänderungen bei `brand sync` unter `.marp-deck/brand-backup-*`
- Regressionstests zu allen Review-Befunden (`tests/test_review_findings.py`), Entscheidung 0009
- `.deck`-Container: `marp-deck pack` / `unpack` (ZIP mit Manifest; prüft Zip-Slip, Symlinks, Größen, überschreibt nie)
- `marp-deck import-deck`: bestehende PowerPoint-Präsentation als Marp-Deck (optional über `pptx2md`); entfernt externe Google-Fonts-Importe
- Tests: Pack/Unpack inkl. manipulierter Archive, Adapter, „Brand-Import liest nie Folieninhalt“
- Entscheidung 0008
- CI-Import aus PowerPoint: `marp-deck brand showcase|import|preview|compare`, `pptx_extract.py`, `pptx_showcase.py`, `brand_import.py`, `brand_preview.py`
- Hintergründe pixelgenau über LibreOffice oder PDF-Export aus PowerPoint; ohne beides Rekonstruktion aus Grafiken
- Vergleich Original ↔ Marp mit Differenzbild und Abweichung in %; `reference/`-Renderings im Brand
- Brand-Format: `overrides` (Basis-Blöcke ersetzen), `size` (4:3/eigene Foliengröße), `custom.css`, `reference/`, `guidelines/`
- Abschaltbare Blöcke in `base/layouts.css` (`@block`/`@end`); `--font-heading`-Token
- 4:3-Vorlagen vollständig unterstützt (`@size`, `size:` im Frontmatter)
- Synthetische PPTX-Vorlage für Tests (`tests/template_factory.py`), Tests für Extraktion, Showcase, Import, Vergleich
- `docs/import-workflow.md`, Entscheidung 0007
- `marp-deck` (new, serve, export pdf|html|pptx, brand list|sync, doctor)
- Deck-Ordner mit Quelle, `marp.config.mjs`, Brand-Snapshot (`theme/`) und `assets/`
- Live-Vorschau mit Neuladen im Browser; Server nur auf `127.0.0.1` (Node-Preload)
- HTML-Export als eine portable Datei (lokale Bilder eingebettet), Presenter View aus `file://` geprüft
- Browser-Tests (puppeteer-core aus dem marp-cli-Cache): Live-Neuladen, Presenter View, Portabilität
- `SKILL.md` mit vollständigem Agent-Ablauf (Deck anlegen, Entwurf, Vorschau, parallele Bearbeitung, Export)
- Entscheidungen 0005 (HTML-Export) und 0006 (Server nur Loopback)
- Brand `neutral` (markenfrei, mit Platzhalter-Logo) als einziges eingebautes Brand
- Brand-Auflösung: Deck-Snapshot → `./.marp-brands/` → Brand-Store (`MARP_BRANDS_DIR`, `~/.config/marp-presentation/brands/`) → eingebaut; `build-theme.py --list`
- Schriften aus `brand.json` werden als `@font-face` per Data-URI eingebettet; optionale `layouts.css` je Brand
- Pfadprüfung in `brand.json` (Assets müssen im Brand-Ordner bleiben)
- `doctor.py` (Voraussetzungsprüfung), `common.py` (gepinnte marp-cli-Version, Chrome-Suche)
- Unit-Tests (`tests/test_build_theme.py`), Render-Test und Fixture-Deck mit allen Klassen und Komponenten (`skill/examples/all-classes.md`)
- `install.sh` mit `--all`, `--target`, `--uninstall`; Ziel `~/.agents/skills` für Copilot CLI
- `.gitignore` hält fremde Brands aus dem Repo
- `docs/requirements.md` (Anforderungskatalog) und `docs/decisions/0001–0004`
- Skill-Gerüst `skill/` mit `SKILL.md`
- `base/layouts.css` und `base/components.css` aus dem bisherigen `autarkit.css` herausgelöst
- Brand `autarkit` (`tokens.css`, `brand.json`, `assets/logo.svg`)
- `scripts/build-theme.py`
- `tests/compare-themes.sh`

### Geändert
- Namen aus Titeln höchstens 60 Zeichen (an Wortgrenze gekürzt); `SKILL.md` verlangt einen kurzen Themen-Titel statt des ganzen Nutzersatzes
- **Ordner- und Dateinamen sind reines ASCII:** Titel werden umgeschrieben (ä→ae, ö→oe, ü→ue, ß→ss, Akzente entfallen); `--slug`/`--name` mit Nicht-ASCII-Zeichen werden mit Vorschlag abgelehnt; gleiche Umschrift für Layout-Klassen im Brand-Import
- `suggest` erkennt Datum-Präfixe in drei Formen (JJJJ-MM-TT, JJJJMMTT, JJJJ-MM); neutralere Liste möglicher Präsentationsordner
- `SKILL.md`: Ablauf an den Anwenderablauf angepasst (gebündelte Rückfragen inkl. Zielordner, Übergabe an VS Code als Standard, Export durch den Nutzer mit dem Plugin, Hinweis auf Unterschiede beim HTML-Export)
- `unpack` übernimmt `.vscode/settings.json` nie aus Archiven (Standardvorlage statt Archivinhalt) und verwirft weitere `.vscode/*`-Dateien
- **Sicherheit (Review):** `unpack` übernimmt `marp.config.mjs` nie aus dem Archiv; `serve`/`export` verweigern abweichende Configs;
  Strings aus der PPTX werden bereinigt; Brand-CSS ohne `@import`/externe URLs; `serve.json` strikt validiert; Symlinks im Brand nicht gefolgt;
  Showcase ohne Reste der Originalfolien (Vorschaubild, Titel, Kommentare, verwaiste Medien), mit Größen- und Eintragsgrenzen
- Brand-Suche: Projektordner-Brands zuletzt (überschreiben `neutral` nicht mehr)
- Fehlerpfade hinterlassen keine halbfertigen Brands/Decks
- Brand-Snapshot im Deck enthält keine Original-Richtlinien (`guidelines/`) und keine Referenzbilder (`reference/`) mehr
- Brand `autarkit` aus dem Repo entfernt (liegt im Brand-Store; im Git-Verlauf bleibt der erste Commit)
- Alle 40 Komponentenklassen visuell geprüft (Fixture); `neutral`: `--primary-lt` aufgehellt
- Hartcodierte Farben in Komponenten durch Tokens ersetzt (`--grey-label`, `--grey-mid`, `--callout`, `--light`, `--border`, `--white`)
- Logo als Data-URI beim Build eingesetzt statt im CSS gepflegt
