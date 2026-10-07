# CI aus PowerPoint übernehmen

Aus einer PowerPoint-Vorlage (`.pptx`, `.potx`) wird ein Brand: Farben, Schriften, Logo, Hintergründe und die
Position von Titel, Inhalt, Fußzeile und Seitenzahl je Layout. Gelesen werden nur **Folienmaster, Layouts und Theme**,
nie der Inhalt von Folien.

## Voraussetzungen

| Werkzeug | wofür | Pflicht? |
|---|---|---|
| Python 3.9+ | Import (nur Standardbibliothek) | ja |
| LibreOffice (`soffice`) + `pdftocairo` | Hintergründe und Vergleichsbilder automatisch rendern | nein (siehe Pfad B) |
| ImageMagick (`compare`, `montage`) | Abweichung messen, Vergleichsbilder | nein |

`marp-deck doctor` zeigt, was vorhanden ist.

## Pfad A — mit LibreOffice (alles automatisch)

```bash
marp-deck brand import firma.pptx --name firma --guidelines design-richtlinie.pdf --fonts ~/fonts/firma/
marp-deck brand preview firma        # Deck mit allen Layouts anlegen, dann: marp-deck serve firma-vorschau
marp-deck brand compare firma        # Original | Marp | Differenz je Layout, mit Abweichung in %
```

Der Brand landet im Brand-Store (`~/.config/marp-presentation/brands/firma/`), nicht im Skill-Repo.

## Pfad B — nur PowerPoint (ein manueller Schritt)

```bash
marp-deck brand showcase firma.pptx --out showcase/
```
erzeugt zwei Dateien: `…-showcase-leer.pptx` (eine **leere** Folie je Layout: zeigt nur Logo, Linien, Verläufe, Hintergründe)
und `…-showcase-gefuellt.pptx` (Beispieltext in den Platzhaltern). Beide in PowerPoint als PDF exportieren
(Datei → Exportieren → PDF), dann:

```bash
marp-deck brand import firma.pptx --name firma --backgrounds leer.pdf --reference gefuellt.pdf
```

> Ungetestet: Ob PowerPoint beim PDF-Export leere Platzhalter wirklich weglässt, ist mit LibreOffice bestätigt,
> mit PowerPoint selbst nicht. Zeigt das PDF Platzhaltertext („Titel durch Klicken hinzufügen“), melde das bitte.

Ohne PDFs (und ohne LibreOffice) rekonstruiert der Import die Hintergründe aus den Grafiken der Vorlage
(Farbflächen, Verläufe, Bilder als Ebenen). Das ist angenähert: Sonderformen (Freiformen, Muster) fehlen.

## Pfad C — nur Screenshots

Ohne die PPTX-Datei gibt es keinen automatischen Import. Ein Agent kann anhand von Screenshots und der
Design-Richtlinie ein Brand von Hand aufbauen (Tokens, `custom.css`); das ist ungenauer (Positionen, Farben, Schriften
sind geschätzt). Die Kombination aus PPTX und Screenshots ist besser: Werte aus der PPTX, Screenshot als Abnahme.

## Ergebnis

```
<brand>/
├── brand.json     Name, Logo, overrides, Layout-Zuordnung, Schriften, Palette, Foliengröße
├── tokens.css     Farben, Schriften (aus dem Theme der Vorlage)
├── layouts.css    GENERIERT: Hintergründe und Positionen je Layout
├── custom.css     optional, von Hand: bleibt bei Neuimport erhalten
├── layouts.md     welche Markdown-Struktur welches Layout füllt
├── GUIDELINES.md  Regeln aus den Design-Guidelines (vom Agenten auszuwerten)
├── reference/     Original-Renderings der Layouts mit Beispieltext (für brand compare)
└── assets/        bg/ (Hintergründe), media/ (Logo, Bilder), fonts/
```

### Layout-Zuordnung
`title`, `section`, `closing`, `cols` und die Standard-Inhaltsfolie werden aus Layouttyp und -namen erkannt; alle
anderen Layouts werden zu `layout-<name>`. Falsch erkannt? `--map klasse="Layoutname"` (mehrfach möglich), z. B.
`--map closing="Danke"`. Gibt es kein Abschluss-Layout, nutzt `closing` die Titelfolie.

### Slots
Marp kennt keine Platzhalter. Layouts mit mehreren Inhaltsbereichen füllst du mit je einem `<div>` pro Bereich, in
Leserichtung (Leerzeile nach dem öffnenden Tag). Bild-Bereiche nehmen ein Bild (`![](assets/x.png)`).
`layouts.md` zeigt es je Layout.

### Handanpassung und Neuimport
`layouts.css` nicht bearbeiten (wird bei Neuimport überschrieben), sondern `custom.css` anlegen. Ein Neuimport mit `--replace` sichert den alten Brand (`<name>.bak-<zeit>`) und übernimmt `custom.css`, `GUIDELINES.md` und mitgelieferte Schriften; ohne `--replace` lehnt der Import einen vorhandenen Brand ab. `custom.css` und alle Brand-CSS dürfen keine externen Ressourcen (`@import`, `http(s):`) enthalten. Farben und Schriften
in `tokens.css` dürfen angepasst werden. Danach Decks mit `marp-deck brand sync <deck>` aktualisieren.

## Wie gut ist das Ergebnis?

`brand compare` rendert dieselben Beispieltexte in der Vorlage (LibreOffice/PowerPoint) und in Marp und misst die Abweichung.
**Hintergründe stimmen pixelgenau** (sie sind das gerenderte Original). Die Restabweichung ist Textglättung zwischen
den Renderern (Glyphenkanten, 1–2 px Versatz); sie wächst mit der Schriftgröße: bei 20-pt-Text etwa 5 %, bei 32-pt-Text
10–15 %. Ein echter Layoutfehler zeigt sich als verschobener Block im Differenzbild, nicht als Kantenrauschen.

## Grenzen

- Positionen von Text sind auf etwa 1–2 px genau, Zeilenumbrüche können abweichen (Marp fließt, PowerPoint nicht).
- Schriften: PPTX enthält nur Namen. Die Dateien müssen mitgeliefert werden (`--fonts`), sonst Ersatzschrift. Der
  Import meldet fehlende Schriften.
- Diagramme, SmartArt, Animationen, Übergänge werden nicht übernommen. Gedrehte Textfelder werden gedreht, gedrehte
  Fließtextbereiche nicht.
- Datumsplatzhalter wird nicht abgebildet (Marp hat keinen).
- 16:9 und 4:3 sind unterstützt; andere Seitenverhältnisse wenig getestet.
- Bei Vorlagen mit **mehreren Folienmastern** stammen Farben, Schriften und Logo vom ersten Master (nicht getestet).
- Strings aus der Datei (Farben, Schriftnamen, Layoutnamen) werden bereinigt, bevor sie in CSS oder Markdown landen: Farben nur als sechs Hexziffern, Schriftnamen nur Buchstaben/Ziffern/Leerzeichen/`.+-`, Layoutnamen ohne Markup.
- Nur mit LibreOffice-Dateien und einer synthetischen Vorlage geprüft, nicht mit einer echten Firmenvorlage aus PowerPoint.

## Vertraulichkeit

PPTX-Vorlagen, Logos, Schriften und Richtlinien einer Firma gehören **nicht** in ein öffentliches Repo. Der Brand-Store
liegt außerhalb des Skill-Repos; `reference/` und `assets/` enthalten die Grafiken der CI und bleiben dort.

---

# Bestehende Präsentation übernehmen (`import-deck`)

Optional, über das Werkzeug [`pptx2md`](https://github.com/OscarPellicer/pptx2marp) (Fork mit Marp-Ausgabe, Apache-2.0).
Es ist keine Abhängigkeit des Skills und braucht einen `python-pptx`-Fork sowie numpy/scipy; das Projekt wird seit
2025-10 nicht mehr aktualisiert. Installation in einer eigenen Umgebung:

```bash
python3 -m venv ~/.local/share/pptx2md
~/.local/share/pptx2md/bin/pip install git+https://github.com/OscarPellicer/python-pptx.git git+https://github.com/OscarPellicer/pptx2marp.git
export PPTX2MD=~/.local/share/pptx2md/bin/pptx2md
marp-deck import-deck alter-vortrag.pptx --brand firma --title "Alter Vortrag"
```

Übernommen werden Titel, Text, Listen, Tabellen, Bilder (nach `assets/`) und Sprechernotizen (als `<!-- … -->`). **Nicht**
übernommen werden Layout, Diagramme, SmartArt, Animationen. Der Adapter ersetzt die Frontmatter, entfernt den mitgelieferten
CSS-Block (inklusive eines Google-Fonts-`@import`, der beim Öffnen Anfragen ins Internet senden würde) und macht aus der
ersten Folie eine Titelfolie. Alle weiteren Folien erhalten die Standard-Inhaltsklasse; Abschnitte, Spalten und Abschluss
ordnest du danach zu.

# Decks weitergeben (`pack` / `unpack`)

```bash
marp-deck pack mein-vortrag            # → mein-vortrag.deck (ZIP)
marp-deck unpack mein-vortrag.deck --dir ~/Vorträge
```

Ein `.deck` aus fremder Quelle gilt als nicht vertrauenswürdig: `unpack` übernimmt `marp.config.mjs` nie aus dem Archiv (ausführbarer Code), sondern schreibt die Standardfassung neu, und verwirft `.marp-deck/`, `.git/`, `dist/`, `node_modules/`. Ein Deck rendert rohes HTML und lokale Dateien; fremde Decks vor dem Export ansehen.

Ein `.deck` ist ein ZIP mit `manifest.json` (Format, Version, Name, Brand) und dem Deck-Ordner (Quelle, Config,
Theme-Snapshot, Assets). `dist/`, `.marp-deck/` und Symlinks bleiben draußen. Der Brand-Snapshot enthält weder
Original-Richtlinien (`guidelines/`) noch Referenzbilder (`reference/`). `unpack` prüft das Archiv vollständig, bevor es
etwas schreibt: Pfade mit `..` oder absolute Pfade, Symlinks, Einträge außerhalb des Deck-Ordners, zu große oder zu viele
Dateien und neuere Formatversionen werden abgelehnt; ein vorhandener Zielordner wird nie überschrieben.
