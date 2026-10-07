---
marp: true
theme: neutral
paginate: true
html: true
footer: "Fixture · alle Klassen"
---

<!-- _class: title -->

# Alle Layouts
## Referenz-Deck für Regressionstests

<div class="title-meta">
  <span>Oktober 2026</span>
  <span>marp-presentation-skill</span>
</div>

---

# Standard-Inhaltsfolie

Fließtext mit **Hervorhebung**, *Metainfo* und `Code`.

- Erster Punkt
- Zweiter Punkt mit [Link](https://example.org)

> Infobox: Hinweis im Blockquote.

| Spalte A | Spalte B | Spalte C |
|---|---|---|
| eins | zwei | drei |
| vier | fünf | sechs |

---

<!-- _class: section -->

# Abschnittstrenner
## 1

---

<!-- _class: cols -->

# Zweispaltig

<div>

### Links
- Punkt A
- Punkt B

</div>
<div>

### Rechts
- Punkt C
- Punkt D

</div>

---

# Agenda-Komponente

<div class="agenda-item"><div><p class="agenda-headline">Erstes Kapitel</p><p class="agenda-subline">Mit Subline</p></div><div class="agenda-number">01</div></div>
<hr class="agenda-divider">
<div class="agenda-item"><div><p class="agenda-headline">Zweites Kapitel</p><p class="agenda-subline">Noch eine Subline</p></div><div class="agenda-number">02</div></div>
<hr class="agenda-divider">
<div class="agenda-item"><div><p class="agenda-headline">Drittes Kapitel</p></div><div class="agenda-number">03</div></div>

---

# Agenda kompakt

<div class="agenda-compact">
<div class="agenda-item"><p class="agenda-headline">Kapitel eins</p><div class="agenda-number">01</div></div>
<div class="agenda-item"><p class="agenda-headline">Kapitel zwei</p><div class="agenda-number">02</div></div>
<div class="agenda-item"><p class="agenda-headline">Kapitel drei</p><div class="agenda-number">03</div></div>
<div class="agenda-item"><p class="agenda-headline">Kapitel vier</p><div class="agenda-number">04</div></div>
</div>

---

# Drei Spalten mit Box-Mustern

<div class="columns-3">
<div><div class="box-header">Definition</div><div class="box-body"><ul><li>Punkt eins</li><li>Punkt zwei</li></ul></div></div>
<div><div class="box-header">Beispiel</div><div class="box-body"><ul><li>Punkt eins</li><li>Punkt zwei</li></ul></div></div>
<div><div class="box-header">Hinweis</div><div class="box-body"><ul><li>Punkt eins</li><li>Punkt zwei</li></ul></div></div>
</div>

<div class="info-callout" style="margin-top:1rem">Info-Callout unter den Spalten.</div>

---

# Vier Spalten

<div class="columns-4">
<div><div class="box-header">A</div><div class="box-body">Text</div></div>
<div><div class="box-header">B</div><div class="box-body">Text</div></div>
<div><div class="box-header">C</div><div class="box-body">Text</div></div>
<div><div class="box-header">D</div><div class="box-body">Text</div></div>
</div>

---

# Flow horizontal (3 Schritte)

<div class="flow-3">
<div><div class="flow-header">01 · Denken</div><div class="flow-body">Aufgabe verstehen</div></div>
<div class="flow-arrow"></div>
<div><div class="flow-header-outline">02 · Werkzeug</div><div class="flow-body">Werkzeug wählen</div></div>
<div class="flow-arrow"></div>
<div><div class="flow-header">03 · Auswerten</div><div class="flow-body">Ergebnis prüfen</div></div>
</div>
<div class="flow-loop-3" data-label="wiederholen"></div>

---

# Flow 2 und 4

<div class="flow-2">
<div><div class="flow-header">Vorher</div><div class="flow-body">Text</div></div>
<div class="flow-arrow"></div>
<div><div class="flow-header">Nachher</div><div class="flow-body">Text</div></div>
</div>

<div class="flow-4">
<div><div class="flow-header-outline">1</div><div class="flow-body">a</div></div><div class="flow-arrow"></div>
<div><div class="flow-header-outline">2</div><div class="flow-body">b</div></div><div class="flow-arrow"></div>
<div><div class="flow-header">3</div><div class="flow-body">c</div></div><div class="flow-arrow"></div>
<div><div class="flow-header">4</div><div class="flow-body">d</div></div>
</div>

---

<!-- _class: cols -->

# Vertikaler Flow und Loop

<div class="flow-vertical">
<div class="flow-vertical-step"><div class="flow-header">Schritt 1</div><div class="flow-body">Text</div></div>
<div class="flow-vertical-arrow"></div>
<div class="flow-vertical-step"><div class="flow-header-outline">Schritt 2</div><div class="flow-body">Text</div></div>
<div class="flow-vertical-return">nein → zurück</div>
</div>

<div class="flow-loop-vertical">
<div class="flow-loop-vertical-steps">
<div><div class="flow-header">01 · Denken</div><div class="flow-body">Text</div></div>
<div class="flow-vertical-arrow"></div>
<div><div class="flow-header">02 · Werkzeug</div><div class="flow-body">Text</div></div>
<div class="flow-vertical-arrow"></div>
<div><div class="flow-header">03 · Auswerten</div><div class="flow-body">Text</div></div>
</div>
<div class="flow-loop-vertical-bow"></div>
</div>

---

# Swimlane

<div class="columns-3">
<div class="swimlane-step"><div class="flow-header-arrow">Planen</div><div class="swimlane-body">Inhalt</div><div class="flow-footer">Footer</div></div>
<div class="swimlane-step"><div class="flow-header-arrow">Umsetzen</div><div class="swimlane-body">Inhalt</div><div class="flow-footer">Footer</div></div>
<div class="swimlane-step"><div class="flow-header-arrow">Prüfen</div><div class="swimlane-body">Inhalt</div><div class="flow-footer">Footer</div></div>
</div>

---

# Icon-Matrix

<div class="icon-matrix">
<div><div class="box-header">Karte 1</div><div class="icon-matrix-body"><div class="icon-matrix-item"><div class="icon-matrix-icon-box">A</div>Eins</div><div class="icon-matrix-item"><div class="icon-matrix-icon-box">B</div>Zwei</div></div></div>
<div><div class="box-header">Karte 2</div><div class="icon-matrix-body"><div class="icon-matrix-item"><div class="icon-matrix-icon-box">A</div>Eins</div><div class="icon-matrix-item"><div class="icon-matrix-icon-box">B</div>Zwei</div></div></div>
</div>

---

# Accordion-Layout

<div class="accordion-layout">
<div class="accordion-layout-header">Überschrift</div>
<div class="accordion-layout-body">
<div class="accordion-row"><div class="accordion-label">Zeile 1</div><div class="accordion-mid has-arrow">Mitte</div><div class="accordion-right"><span>Links</span><span>Rechts</span></div></div>
<div class="accordion-row"><div class="accordion-label">Zeile 2</div><div class="accordion-mid has-arrow">Mitte</div><div class="accordion-right"><span>Links</span><span>Rechts</span></div></div>
<div class="accordion-row"><div class="accordion-label">Zeile 3</div><div class="accordion-mid">Mitte</div><div class="accordion-right"><span>Links</span><span>Rechts</span></div></div>
</div>
</div>

---

# Tabelle ohne Zebra

<div class="table-plain">

| A | B |
|---|---|
| eins | zwei |
| drei | vier |

</div>

---

<!-- _class: closing -->

# Danke

## kontakt@example.org

Beispielstraße 1 · 12345 Beispielstadt
