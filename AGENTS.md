# AGENTS.md — marp-presentation-skill

Gilt für Claude Code, opencode und andere Agenten. `CLAUDE.md` verweist hierher.

## Zweck
Marp-Skill mit Brand-System. Ziel und Stand: `README.md`, `ROADMAP.md`.

## Architektur-Regeln
- **Zwei Schichten:** `skill/base/` (Layouts, markenneutral) und `skill/brands/<name>/` (nur Tokens + Assets). Marken-Werte gehören nie in `base/`. Hartcodierte Farben in `base/` sind Fehler → Token anlegen.
- **Theme-Datei ist generiert:** `scripts/build-theme.py` baut `theme.css`. Nie von Hand editieren.
- **Deck = selbstständiger Ordner.** Keine Pfade, die aus dem Deck hinausführen.
- **Logo als Data-URI** (Obsidian-Sandbox, HTML-Export).
- Klassennamen (`title`, `section`, `cols`, `closing`, Komponenten) nicht umbenennen — bestehende Decks hängen daran.

## Vor jeder Theme-Änderung
`tests/compare-themes.sh` ausführen (rendert ein Deck mit altem und neuem Theme als PNG und vergleicht byteweise). Unerwartete Diffs = Regression.

## Konventionen
- Commits: Conventional Commits, deutscher Text (`feat: …`, `fix: …`, `docs: …`).
- Sprache in Doku und Kommentaren: Deutsch, Umlaute korrekt.
- Änderungen im `CHANGELOG.md` (Abschnitt *Unveröffentlicht*) festhalten, Roadmap-Haken setzen.
- Keine Features als „fertig" melden, die nicht gegen ein echtes Deck gerendert wurden.

## Bekannte Fallen
- `section::after { padding: 0 }` ist nötig (Marp-Scaffold vererbt padding), sonst rutscht die Seitenzahl.
- Auf `title` genau ein `#`, auf `section` nur eine Zahl in `##`.
- PPTX-Schriften sind meist nicht eingebettet; Font-Dateien müssen separat geliefert werden.
