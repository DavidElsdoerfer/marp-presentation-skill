# Anforderungskatalog

Stand 2026-10-07. A–D sind fix, E ist bestätigt oder angepasst.

## Fix
- **A1** Nutzer und Agent bearbeiten dieselbe Präsentation parallel (Datei-basiert: Agent und Editor ändern die `.md`).
- **A2** Live-Vorschau im Browser über localhost, ohne zusätzliche Anwendung. Die Vorschau lädt bei Dateiänderung neu. Direktes Bearbeiten im Browser ist **nicht** gefordert (siehe Entscheidung 0001).
- **B1** Jede Präsentation bringt Assets und Stylesheets selbst mit.
- **B2** Skill für Claude Code, opencode und GitHub Copilot CLI in eigenem Git-Repo (AGENTS.md, Roadmap, Changelog).
- **B3** Skill kommt ohne eigene CI. Nutzer bringen ihre CI mit (Brand-System).
- **C1** Sauberer PDF-Export.
- **C2** HTML-Export zum Halten der Präsentation, mit Presenter View.
- **D1** Import von PPTX-Folienmastern (Layouts, Farben, Schriften, Logos).
- **D2** Quellen: Design-Guidelines und mehrere PPTX-Vorlagen mit verschiedenen Layouts.

## Abgeleitet / bestätigt
- **E1** Quelle darf auch ein anderes Format als Markdown sein, solange A–D erfüllt sind (Markdown ist Vorgabe der Wahl).
- **E2** Versionierbarkeit in Git darf anders gelöst werden, solange A–D erfüllt sind.
- **E3** Läuft lokal und offline.
- **E4** Selbstständige, verschiebbare Ordner. Optional ZIP-Container (`.deck`).
- **E5** Übernahme bestehender Decks: nicht gefordert (optionaler Adapter möglich).
- **E6** CI-Exaktheit vor Pixelgenauigkeit der Textumbrüche; Ziel: möglichst exakte CI.
- **E7** Geringe Hürde, wenig Abhängigkeiten.
- **E8** PPTX als Ausgabe nicht nötig. PPTX als Import-Quelle für neue Layouts wichtig.
- **E9** Nur der Autor bearbeitet sein Deck; andere Nutzer des Skills müssen Decks aber portabel weitergeben können.
