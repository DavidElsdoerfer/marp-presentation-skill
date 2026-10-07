# 0007 — CI-Import: Umsetzung und Erkenntnisse

Status: umgesetzt (2026-10-07), Ergänzung zu 0004

## Umsetzung
- `pptx_extract.py` liest Master, Layouts, Theme (nur Standardbibliothek, Größenlimits, nie Folieninhalt).
- `pptx_showcase.py` erzeugt aus der Vorlage ein Deck mit je einer **leeren** Folie pro Layout (zeigt nur Grafiken) und
  eine **gefüllte** Variante (Beispieltext in den Platzhaltern) als Referenz.
- `brand_import.py` erzeugt Tokens, `layouts.css`, `layouts.md`, `brand.json`. Hintergründe: gerendert (LibreOffice oder
  vom Nutzer exportiertes PDF) → pixelgenau; sonst aus Grafiken rekonstruiert (angenähert).
- `brand_preview.py` baut Vorschau-Deck und Vergleich (Original | Marp | Differenz, Abweichung in %).
- Basis-Blöcke in `layouts.css` sind per `/* @block … */` markiert; ein Brand ersetzt sie über `overrides`.
- Slots: n-tes `<div>` = n-ter Inhaltsplatzhalter in Leserichtung; Einzelbereich als Fluss mit Padding.

## Ergebnis des Spikes (M2)
Marp reicht für die Layouts. Mit einer synthetischen, PowerPoint-artigen Vorlage liegt die Abweichung zum Original bei
4,7–6,7 % (reine Textglättung, Hintergründe pixelgleich). Mit LibreOffice-Vorlagen (32-pt-Text) 3–15 %.

## Erkenntnisse (Fallstricke)
- Marpit verwirft `content` auf `section::after`/`::before` (Seitenzahl): Seitenzahl ausblenden per `display: none`.
- Browser geben dem ersten Absatz 1em Außenabstand: `section > h1 + *` und erstes Kind je Slot auf `margin-top: 0`.
- Felder dürfen über den Folienrand ragen: Padding nie negativ (CSS verwirft sonst die ganze Zeile).
- Leere XML-Elemente (`<p:ph/>`) sind in ElementTree „falsch“: nie `a or b` mit Elementen.
- `ZipFile.writestr(ZipInfo, …)` ändert das Info-Objekt der Quelle: mit dem Namen schreiben.
- Manche Generatoren deklarieren `xmlns:r` nur lokal: eingefügte Elemente deklarieren ihr Präfix selbst; `sldIdLst` steht
  nach dem **letzten** der Master-Listen.
- `bodyPr` nur mit explizit gesetzten Eigenschaften übernehmen, sonst überschreibt es geerbte Werte.
- LibreOffice legt Stile in `endParaRPr`/Beispielzeilen ab, die nichts bedeuten: nicht als Textstil nutzen; fehlende
  Größen → Office-Standard (Titel 44, Untertitel/Inhalt 32, Fuß 12 pt).
- PDF-Seitengrößen runden: PNGs exakt auf Zielgröße rendern (sonst 721 px statt 720 und 1 px Verzug).

## Offen
- Mit einer echten, in PowerPoint erstellten Firmenvorlage prüfen (bisher: synthetisch und LibreOffice-Beispiele).
- PowerPoint-PDF-Export leerer Platzhalter prüfen (nur mit LibreOffice bestätigt).
- Datumsplatzhalter, Aufzählungszeichen und Absatzabstände der Vorlage werden nicht übernommen.
