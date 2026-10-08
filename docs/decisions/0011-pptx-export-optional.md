# 0011 — Editierbarer PPTX-Export: optional, niedrige Priorität

Status: zurückgestellt (2026-10-08). Priorität des Autors: Marp (Vorschau, PDF, HTML, VS Code, CI-Import) muss zuerst sauber laufen.

## Ausgangslage
`marp-deck export pptx` und marp-cli erzeugen nur **Bilder** der Folien (nicht editierbar). `marp-cli --pptx-editable` ist experimentell und kennt keine Folienmaster.
Gewünscht wäre ein PPTX auf Basis der Original-Vorlage, in dem man in PowerPoint finalisieren kann.

## Konzept (am Prototyp geprüft)
1. Marp zerlegt das Markdown (marp-core, `markdown.parse`): Folien, Direktiven (`_class`), Überschriften, verschachtelte Listen, Tabellen, Bilder,
   Notizen, `<div>`-Slots. Ergebnis: JSON-Modell. (Notizen und Direktiven kommen so exakt wie in der Vorschau.)
2. `python-pptx` lädt die **bereinigte Vorlage** des Brands, entfernt vorhandene Folien und erzeugt je Folie eine neue auf dem zugeordneten Layout. Master, Theme und Layouts bleiben.
3. Zuordnung über unsere Klassen (`title`, `section`, `cols`, `closing`, `layout-…`) auf Layouts; Slots → Inhaltsplatzhalter in Leserichtung.

Prototyp (synthetische Vorlage, 7 Folien, mit LibreOffice gerendert): Titel/Abschnitt/Abschluss mit Verlauf, Logo und Linien aus dem Master; Text in echten Platzhaltern;
Fett/Kursiv/Code/Links, Listenebenen, zwei Spalten, native Tabelle und Notizen funktionieren. Nicht abgebildet: HTML-Komponenten (Flow, Boxen, Accordion, Agenda).

## Entwurfsentscheidungen
- **Stufe 1:** Platzhalter, native Tabellen, Bilder; **nicht abbildbare Folien als Bild der Marp-Folie** (vollständig, nicht editierbar; die Zusammenfassung nennt sie).
- **Stufe 2:** bekannte Komponenten als einzelne PowerPoint-Formen mit festen Positionen (Referenzfläche 1280×720, Geometrie aus dem gerenderten Browser-DOM).
  Diese Formen sind editierbar, aber nicht mit dem Master verknüpft (Master-/Theme-Änderungen wirken dort nicht). Ein vergleichbarer Weg wird in einem bestehenden
  Exporter (strukturiertes Modell → `python-pptx` + feste Vorlage) so umgesetzt.
- **Layout-Suche per Name, Index als Rückfall, harter Abbruch bei fehlendem Layout** (stilles Ausweichen verdeckt Fehler).
- **Eigene Platzhalter** (z. B. Autor, Datum, Organisationseinheit auf der Titelfolie) über den Platzhalter-Index auf Frontmatter-Felder abbilden; Standardwerte im Brand-Store.
- **Vorlage im Brand:** bereinigte Kopie (ohne Folien, Kommentare, Vorschaubild, eingebettete Schriften); sie reist im Deck mit. Firmenspezifische Layoutnamen, Indizes und Standardwerte gehören in die Brand-Konfiguration im Brand-Store, **nie ins öffentliche Repo**.
- **Abhängigkeit:** `python-pptx` nur für diesen Export, optional (Hinweis zur Installation in eigener Umgebung). Eigenes PPTX-XML wäre in PowerPoint riskanter (Reparaturmeldungen), nur LibreOffice steht zum Testen bereit.

## Grenzen (gelten für jeden Weg HTML/Markdown → PPTX)
- Zeilenumbrüche rechnet PowerPoint selbst neu; in festen Formen kann der Umbruch abweichen.
- Der Rückweg PPTX → Marp ist verlustbehaftet (`import-deck`); die PPTX ist ein Endpunkt: erst inhaltlich in Marp fertigstellen, dann exportieren und in PowerPoint finalisieren.
- Ob erzeugte Dateien in PowerPoint ohne Reparaturmeldung öffnen, ist nur auf einem Rechner mit PowerPoint prüfbar.
- Recherche: reveal.js und Marp/Slidev exportieren PPTX nicht editierbar (nur Bilder); Pandoc/Quarto wählen Layouts nach Inhalt, nicht pro Folie.

## Technisches Wissen und Prototyp
Lauffähiger Prototyp und die gesammelten technischen Erkenntnisse (Marp-Tokens, python-pptx-Fallstricke, Layout-Zuordnung, Vorlagenvorbereitung, Bild-Rückfall, Komponenten als Formen, Testplan): [`docs/prototypes/pptx-export/`](../prototypes/pptx-export/README.md).
