# 0008 — `.deck`-Container und Adapter für bestehende Decks

Status: umgesetzt (2026-10-07), ergänzt 0003 und die Anforderung E4

## Container
`.deck` = ZIP mit `manifest.json` (Format `marp-deck`, Version 1) als erstem Eintrag und dem Deck-Ordner darunter.
Ein bestehendes `.reveal`-Format wurde nicht gefunden (siehe 0003); das Format ist unser eigenes und bewusst schlicht.
`unpack` validiert vor dem Schreiben (Zip-Slip, absolute Pfade, Symlinks, Größen- und Anzahlgrenzen, Manifest, Namen)
und überschreibt nie.

## Brand-Snapshot ohne Originale
`new` kopierte zunächst den ganzen Brand-Ordner ins Deck, also auch `guidelines/` (Original-Richtlinien) und
`reference/` (Referenzbilder). Ein weitergegebenes Deck hätte beides mitgenommen. Jetzt bleiben beide im Brand-Store.

## Adapter `import-deck`
Optional über `pptx2md --marp`. Erkenntnisse beim Test mit dem echten Werkzeug:
- Die Ausgabe enthält einen CSS-Block mit **Google-Fonts-`@import`** (externe Anfrage beim Öffnen): wird entfernt.
- Titelfolien erhalten zwei `#`: Adapter macht `title`-Klasse + `##` daraus.
- `-o` erwartet einen Ordner; Bilder landen relativ zum Arbeitsverzeichnis: Aufruf mit eigenem Arbeitsordner.
- Notizen kommen als HTML-Kommentare und passen zur Presenter View.
Inhalte werden übernommen, das Layout nicht. Keine Abhängigkeit des Skills (Fork von `python-pptx`, numpy/scipy,
seit 2025-10 nicht mehr aktualisiert).

## Zusage und Test
Der Brand-Import liest nie Folieninhalt; ein Test mit Geheimtext auf einer Folie prüft, dass er weder im Extrakt, im Brand
noch im Showcase auftaucht.
