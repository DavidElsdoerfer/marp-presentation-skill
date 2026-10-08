# Offene Fragen an den Autor

Diese Punkte brauchen eine Entscheidung und werden nicht automatisch erledigt.

## Lizenz
Erledigt: MIT (2026-10-08), siehe `LICENSE`.

## autarkit-Brand im Git-Verlauf
Der erste Commit enthält `skill/brands/autarkit/` (Logo-SVG und Farb-Tokens). Aus dem aktuellen Stand ist es entfernt, im Verlauf bleibt es sichtbar (auch in Klonen und Forks). Es sind keine Zugangsdaten oder Kundendaten, nur das Marken-Logo. Entfernen aus dem Verlauf ginge nur per History-Rewrite und Force-Push; das ist bei einem öffentlichen Repo nur begrenzt wirksam (Caches, Forks). Entscheidung: so lassen oder umschreiben.

## Weitere Spuren im öffentlichen Verlauf (bitte prüfen)
Der Verlauf (Commits `c73920f` bis `5460744`) enthält noch:
- in `skill/base/layouts.css` den Kommentar „analog AUMOVIO-Pattern“ (ein Firmenname; falls das dein Arbeitgeber ist, ggf. unerwünscht),
- in `skill/base/components.css` Verweise auf `wiki/assets/themes/projekt.css (S6-CLI-Agent-Frameworks-Schulungsmaterial)`, auf „autarkit-Palette“ und auf Folien einer nicht benannten PPTX-Vorlage („Folie 7/8/9/10“, Layoutnamen).

Aus dem aktuellen Stand sind diese Kommentare entfernt (Commit „Kommentare neutralisiert“), im Verlauf bleiben sie sichtbar. Entscheidung wie beim autarkit-Brand: so lassen oder Verlauf neu schreiben (Force-Push; bei öffentlichem Repo nur begrenzt wirksam, Klone/Forks/Caches bleiben).

## Git-Identität
Auf dem Rechner ist keine globale Git-Identität gesetzt; im Repo ist lokal `David Elsdoerfer <david.elsdoerfer@gmail.com>` eingetragen. Die Adresse steht damit in jedem öffentlichen Commit.
