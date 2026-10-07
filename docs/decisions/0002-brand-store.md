# 0002 — Skill ohne CI, Brand-Store außerhalb

Status: angenommen (2026-10-07)

Das Repo liefert nur das Brand `neutral`. Brands liegen im Brand-Store, nicht im Skill-Verzeichnis (Updates dürfen Nutzerdaten nicht berühren; Firmenlogos und -schriften sind proprietär).

Suchreihenfolge: Deck-Snapshot (`theme/`) → `./.marp-brands/` → `~/.config/marp-presentation/brands/` (`MARP_BRANDS_DIR`) → eingebautes `neutral`.

Brand-Format siehe `brand-format.md`.
