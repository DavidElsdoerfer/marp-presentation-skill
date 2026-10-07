# 0001 — Marp als Basis, keine Live-Bearbeitung im Browser

Status: angenommen (2026-10-07)

## Entscheidung
Marp (marp-cli, gepinnt) bleibt die Render-Basis. Der Browser zeigt eine Live-Vorschau (`marp -s`), bearbeitet wird in Dateien (durch Nutzer im Editor oder durch den Agenten).

## Verworfene Alternativen
- **Slidev:** Slots und `dragPos` passen gut zu PPTX-Platzhaltern und Drag-Editing, aber schwere Node-Toolchain (E7), kein PPTX-Theme-Import.
- **reveal.js / Quarto:** gute Präsentationsansicht, Markdown ohne Slots; Quarto-brand.yml für pptx unvollständig.
- **Typst + Touying:** beste PDF-Typografie, aber kein HTML-Export mit Presenter View (C2).
- **PPTX-nativ (python-pptx, Pandoc reference-doc):** exakte CI, aber keine Browser-Vorschau und kein HTML (A2, C2).

## Folgen
- Kein WYSIWYG-Editor im Browser. Eine eigene Editor-Anwendung (Text im Browser, Elemente verschieben) wäre ein eigenes Teilprojekt und steht nur als Idee auf der Roadmap.
- Marp hat keine Slots; Layout-Treue für mehrere Platzhalter wird im Spike (M2) geprüft.
- `pptx2marp` wurde geprüft (nur Inhalts-Konverter, liest keine Master); höchstens als optionaler Adapter.
