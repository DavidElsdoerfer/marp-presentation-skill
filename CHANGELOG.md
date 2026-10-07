# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).

## [Unveröffentlicht]

### Hinzugefügt
- `docs/requirements.md` (Anforderungskatalog) und `docs/decisions/0001–0004`
- Skill-Gerüst `skill/` mit `SKILL.md`
- `base/layouts.css` und `base/components.css` aus dem bisherigen `autarkit.css` herausgelöst
- Brand `autarkit` (`tokens.css`, `brand.json`, `assets/logo.svg`)
- `scripts/build-theme.py`
- `tests/compare-themes.sh`

### Geändert
- Hartcodierte Farben in Komponenten durch Tokens ersetzt (`--grey-label`, `--grey-mid`, `--callout`, `--light`, `--border`, `--white`)
- Logo als Data-URI beim Build eingesetzt statt im CSS gepflegt
