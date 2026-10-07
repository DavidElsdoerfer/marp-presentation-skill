#!/usr/bin/env python3
"""Baut aus base/ + einem Brand ein einzelnes Marp-Theme.

Aufruf: build-theme.py <brand-dir> <out.css>
Ergebnis: /* @theme <name> */ + tokens.css + --logo (Data-URI) + layouts.css + components.css
"""
import base64, json, mimetypes, sys
from pathlib import Path

base = Path(__file__).resolve().parent.parent / "base"
brand = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
meta = json.loads((brand / "brand.json").read_text())

logo = brand / meta["logo"]
mime = mimetypes.guess_type(logo.name)[0] or "image/svg+xml"
uri = f"data:{mime};base64," + base64.b64encode(logo.read_bytes()).decode()

parts = [
    f"/* @theme {meta['name']} */\n",
    "/* GENERIERT von build-theme.py — nicht von Hand editieren (Quelle: brand/tokens.css + Skill base/) */\n",
    (brand / "tokens.css").read_text(),
    f":root {{ --logo: url('{uri}'); }}\n",
    (base / "layouts.css").read_text(),
    (base / "components.css").read_text(),
]
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(parts))
print(f"{out} ({out.stat().st_size} Bytes, Theme '{meta['name']}')")
