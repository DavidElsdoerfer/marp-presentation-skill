# 0004 — CI-Import in zwei Stufen mit Fallback-Kette

Status: angenommen (2026-10-07), Umsetzung nach Spike M2

**Stufe A (Skript, Standardbibliothek):** Farben, Schriften, Logos/Medien, Layoutnamen und Platzhaltergeometrie aus der PPTX. Nur Master und Layouts, nie Folieninhalt.

**Hintergründe nach Qualität:** (1) LibreOffice rendert Layouts ohne Text; (2) vom Nutzer aus PowerPoint exportiertes PDF/PNG (eine Folie pro Layout, leere Platzhalter); (3) nur Screenshots → approximativ, so gekennzeichnet.

**Stufe B (Agent):** Mapping auf Klassen, `layouts.css`/`layouts.md`, `GUIDELINES.md` aus den Design-Guidelines; Korrekturschleife mit Differenzbild gegen die Referenz; `brand preview` zeigt alle Layouts.

**Grenzen:** keine Pixelgenauigkeit bei Textumbruch, Schriften nur als Namen, Diagramme/SmartArt/Animationen nicht übernommen.
