# Marp for VS Code

Die Erweiterung [Marp for VS Code](https://github.com/marp-team/marp-vscode) zeigt Marp-Markdown direkt in VS Code als Vorschau und
exportiert PDF/HTML/PPTX. Dieser Skill ist mit ihr kompatibel: **ein Deck-Ordner in VS Code öffnen, fertig** — ohne eine CSS-Datei
pro Projekt anzulegen, zu benennen und der Erweiterung beizubringen.

## Wie die Erweiterung arbeitet (am Quellcode 3.6.1 geprüft)

- Eigene Themes kommen **nur** aus der Einstellung `markdown.marp.themes`: Liste von URLs oder Pfaden. Pfade gelten **relativ zum
  Workspace-Ordner** (dem in VS Code geöffneten Ordner), **müssen darin liegen** (`..` und absolute Pfade werden verworfen), **Globs gibt es nicht**.
- Das Theme wird über `/* @theme name */` benannt; im Deck wählt `theme: name`. Registriert wird mit `themeSet.add(css)`:
  **bei gleichem Namen gewinnt still das zuletzt registrierte** (deshalb mussten Dateien bisher eindeutig heißen).
- Eine `marp.config.mjs`/`.marprc` liest die Erweiterung **nicht** (Export nutzt eine selbst erzeugte Konfiguration aus den Einstellungen).
- Ohne `markdown.marp.html: "all"` lässt die Vorschau nur eine Allowlist zu: unsere `<div>`-Komponenten (Slots, Flow, Boxen, `title-meta`)
  würden als Text angezeigt. Im nicht vertrauenswürdigen Workspace ist HTML immer aus, ebenso eigene Themes (Schild-Symbol in den Einstellungen).

## Was der Skill daraus macht

1. **Jedes Deck bringt `.vscode/settings.json` mit** (`marp-deck new`, `import-deck`, `brand preview`):
   ```json
   { "markdown.marp.themes": ["theme/theme.css"], "markdown.marp.html": "all",
     "markdown.marp.pdf.noteAnnotations": true, "markdown.marp.pdf.outlines": "both" }
   ```
   Das Theme liegt im Deck (`theme/theme.css`), der Pfad ist relativ zum Deck. Deck-Ordner öffnen, dem Workspace vertrauen: Vorschau und Export laufen.
   Die Datei ist Teil des Decks und reist im `.deck`-Archiv mit.
2. **Decks in einem größeren Projekt** (z. B. `Projekt/Präsentationen/2026-10-05-Workshop/`): Ist nicht das Deck, sondern der Projektordner der Workspace,
   greifen die Einstellungen im Deck nicht. **Einmalig** `marp-deck vscode <projekt>` ausführen; danach trägt `marp-deck new` (auch `import-deck`, `brand preview`) jedes neue Deck
   darunter **automatisch** ein (Bedingung: der nächste Ordner oberhalb, dessen `.vscode/settings.json` schon Marp-Themes listet; bei Kommentaren in der Datei nur ein Hinweis).
   Ohne frühere Registrierung legt `new` nie Dateien im Projekt an, es gibt nur einen Hinweis. `marp-deck vscode [PROJEKT]` findet alle Decks darunter (Tiefe 4, ohne `dist/`, `node_modules/`, `.git/`) und trägt ihre Themes in
   `<projekt>/.vscode/settings.json` ein:
   - nur ergänzen, nichts löschen (tote Einträge werden gemeldet); Nutzerwerte wie `pdf.outlines` bleiben, `markdown.marp.html` wird auf `"all"` gesetzt (nötig)
   - Sicherung `settings.json.bak-<zeit>` bei jeder Änderung, `--dry-run` zeigt nur an
   - enthält die Datei Kommentare, wird sie **nicht umgeschrieben**; die Zeilen zum Einfügen werden ausgegeben (Exit-Code 3)
   - **gleichnamige Themes mit unterschiedlichem Inhalt** (z. B. nach `brand sync` in nur einem Deck) werden gemeldet; Abhilfe: `marp-deck brand sync` in allen Decks
3. **Fremde `.deck`-Archive:** `unpack` schreibt `.vscode/settings.json` aus der Standardvorlage neu und verwirft `tasks.json`, `launch.json` u. ä. Workspace-Dateien können Programme
   starten (z. B. Aufgaben mit `runOn: folderOpen`); sie werden nie aus einem Archiv übernommen.

## Vorschau in VS Code oder im Browser?

| | Marp for VS Code | `marp-deck serve` |
|---|---|---|
| Vorschau | im Editor neben dem Markdown | im Browser, lädt bei jeder Dateiänderung nach |
| Einrichtung | Ordner öffnen, Workspace vertrauen | keine |
| Export | Befehl „Export Slide Deck“ (braucht Chrome/Edge/Firefox) | `marp-deck export pdf|html` |
| HTML-Export | Erweiterung: normales HTML (Bilder nicht eingebettet) | **eine Datei** mit eingebetteten Bildern und Presenter View |

Beides nebeneinander ist möglich; für die Weitergabe als einzelne HTML-Datei bleibt `marp-deck export html` der bessere Weg.

## Grenzen

- Die Einstellungen greifen nur im **vertrauenswürdigen** Workspace. Beim ersten Öffnen fragt VS Code danach.
- Der Skill ändert keine **Benutzer**-Einstellungen von VS Code (nur `.vscode/` im Ordner).
- Das Plugin nutzt für 4:3-Decks `size: 4:3` aus dem Theme (`@size`-Angabe wird mitgeliefert).
- Nicht getestet: die Erweiterung selbst (hier ohne VS Code). Geprüft ist `themeSet.add` und die HTML-Allowlist mit `marp-core`, derselben Bibliothek wie in der Erweiterung (`tests/test_vscode.py`).
