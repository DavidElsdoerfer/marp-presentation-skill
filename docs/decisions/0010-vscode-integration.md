# 0010 — Integration mit Marp for VS Code

Status: umgesetzt (2026-10-08)

## Problem
Pro Projekt musste eine CSS-Datei angelegt, eindeutig benannt und in `markdown.marp.themes` eingetragen werden. Grund: Pfade gelten relativ zum
Workspace und müssen darin liegen; gleichnamige Themes überschreiben sich still (letzter gewinnt); `marp.config.*` wird nicht gelesen.

## Entscheidung
Das Theme liegt im Deck (`theme/theme.css`, schon vorher so). Jedes Deck bringt eine `.vscode/settings.json` mit Pfad `theme/theme.css`, `html: "all"` und PDF-Optionen;
`marp-deck vscode` trägt Themes mehrerer Decks in die Projekt-Einstellungen ein (ergänzend, mit Sicherung, ohne Kommentare zu zerstören).

## Verworfen
- **Theme inline im Markdown (`<style>`):** würde ohne Konfiguration überall laufen, bläht aber jedes Deck um das ganze Theme auf (mit Logo/Hintergründen als Data-URI mehrere MB),
  macht Diffs und Agentenarbeit unhandlich und kann `@size`/4:3 nicht abbilden.
- **Absolute Pfade oder Benutzer-Einstellungen:** werden von der Erweiterung verworfen (Pfade müssen im Workspace liegen).
- **Eindeutige Theme-Namen pro Deck (Hash im Namen):** würde das `theme:` im Markdown bei jedem Brand-Update ändern; stattdessen meldet `marp-deck vscode` Konflikte.

## Sicherheit
Workspace-Dateien (`.vscode/settings.json`, `tasks.json`, `launch.json`) können Programme starten. `unpack` übernimmt sie nie aus Archiven: Einstellungen neu aus der Vorlage,
alles andere verworfen (wie bei `marp.config.mjs`, 0009).

## Prüfung
`tests/test_vscode.py`: Einstellungen, Aggregation (idempotent, Sicherung, Kommentare, Konflikte, tote Einträge), Archivsicherheit und Plugin-Verhalten
(`themeSet.add`, HTML-Allowlist, „letzter Name gewinnt“) mit `marp-core`.
