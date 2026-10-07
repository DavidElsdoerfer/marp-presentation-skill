# 0003 — Deck als Ordner, optional als `.deck` (ZIP)

Status: angenommen (2026-10-07)

Ein Deck ist ein selbstständiger Ordner mit Quelle, `marp.config.mjs`, `theme/` (Brand-Snapshot) und `assets/`. Ein bestehendes `.reveal`-Format wurde nicht gefunden; wir definieren `.deck` selbst als ZIP des Ordners (Python `zipfile`, Manifest, ohne `dist/`).

Snapshot statt gemeinsamem Pfad oder Symlink: portabel und rückwirkungsfrei. `brand-sync` aktualisiert gezielt.
