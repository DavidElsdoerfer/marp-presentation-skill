# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).

## [Unveröffentlicht]

### Hinzugefügt
- Brand `neutral` (markenfrei, mit Platzhalter-Logo) als einziges eingebautes Brand
- Brand-Auflösung: Deck-Snapshot → `./.marp-brands/` → Brand-Store (`MARP_BRANDS_DIR`, `~/.config/marp-presentation/brands/`) → eingebaut; `build-theme.py --list`
- Schriften aus `brand.json` werden als `@font-face` per Data-URI eingebettet; optionale `layouts.css` je Brand
- Pfadprüfung in `brand.json` (Assets müssen im Brand-Ordner bleiben)
- `doctor.py` (Voraussetzungsprüfung), `common.py` (gepinnte marp-cli-Version, Chrome-Suche)
- Unit-Tests (`tests/test_build_theme.py`), Render-Test und Fixture-Deck mit allen Klassen und Komponenten (`tests/fixtures/all-classes.md`)
- `install.sh` mit `--all`, `--target`, `--uninstall`; Ziel `~/.agents/skills` für Copilot CLI
- `.gitignore` hält fremde Brands aus dem Repo
- `docs/requirements.md` (Anforderungskatalog) und `docs/decisions/0001–0004`
- Skill-Gerüst `skill/` mit `SKILL.md`
- `base/layouts.css` und `base/components.css` aus dem bisherigen `autarkit.css` herausgelöst
- Brand `autarkit` (`tokens.css`, `brand.json`, `assets/logo.svg`)
- `scripts/build-theme.py`
- `tests/compare-themes.sh`

### Geändert
- Brand `autarkit` aus dem Repo entfernt (liegt im Brand-Store; im Git-Verlauf bleibt der erste Commit)
- Alle 40 Komponentenklassen visuell geprüft (Fixture); `neutral`: `--primary-lt` aufgehellt
- Hartcodierte Farben in Komponenten durch Tokens ersetzt (`--grey-label`, `--grey-mid`, `--callout`, `--light`, `--border`, `--white`)
- Logo als Data-URI beim Build eingesetzt statt im CSS gepflegt
