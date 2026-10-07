# 0005 — HTML-Export als eine einzige Datei

Status: angenommen und getestet (2026-10-07)

`marp-cli` lässt lokale Bilder im HTML-Export als relative Pfade stehen (`assets/x.png`). Aus `dist/` heraus zeigen sie ins Leere; eine HTML-Datei ließe sich nicht allein weitergeben.

**Entscheidung:** `marp-deck export html` bettet lokale Bilder und Hintergründe nach dem Export als Data-URI ein (nur Dateien innerhalb des Deck-Ordners; fehlende oder externe Pfade bleiben stehen und werden gemeldet). Ergebnis: eine portable Datei, Presenter View (Taste `P`) funktioniert aus `file://` (im Browser geprüft: Popup `?view=presenter`).

**Grenze:** Videos und `<link href>` auf lokale Dateien werden nicht eingebettet; Dateigröße wächst mit den Bildern.
