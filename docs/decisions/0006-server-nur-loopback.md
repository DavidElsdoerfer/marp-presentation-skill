# 0006 — Vorschau-Server nur auf 127.0.0.1

Status: angenommen und getestet (2026-10-07)

`marp-cli -s` ruft `listen(port)` ohne Host auf und bindet damit an alle Netzwerkschnittstellen; eine Option dafür gibt es nicht. Auf Rechnern mit LAN/VPN wäre der Deck-Ordner im Netz lesbar.

**Entscheidung:** `marp-deck serve` startet den Server mit einem Node-Preload (`bind-localhost.cjs` via `NODE_OPTIONS=--require`), der `listen()` ohne Host auf `127.0.0.1` zwingt. Der Test prüft, dass der Port auf `127.0.0.1` und nicht auf `*` lauscht.

**Folgen:** Von anderen Geräten ist die Vorschau nicht erreichbar (gewollt). Server läuft als eigene Prozessgruppe; `serve --stop` beendet sie.
