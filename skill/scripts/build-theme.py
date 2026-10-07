#!/usr/bin/env python3
"""Baut aus base/ + einem Brand ein einzelnes Marp-Theme.

Aufruf:
  build-theme.py <brand> <out.css> [--deck DIR]
  build-theme.py --list [--deck DIR]

<brand> ist ein Brand-Name oder ein Pfad zu einem Brand-Ordner (mit brand.json).
Suchreihenfolge für Namen:
  1. <deck>/theme/brand/          (Snapshot, nur mit --deck)
  2. ./.marp-brands/<name>/
  3. $MARP_BRANDS_DIR/<name>/  bzw.  ~/.config/marp-presentation/brands/<name>/
  4. <skill>/brands/<name>/       (eingebaut: neutral)

Ergebnis: /* @theme <name> */ + tokens.css + --logo (Data-URI) + layouts.css
          + components.css (+ optional brand/layouts.css)
"""
import argparse, base64, json, mimetypes, os, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BASE = SKILL / "base"


def search_dirs(deck):
    dirs = []
    if deck:
        dirs.append(Path(deck) / "theme" / "brand")
    dirs.append(Path.cwd() / ".marp-brands")
    store = os.environ.get("MARP_BRANDS_DIR")
    dirs.append(Path(store).expanduser() if store else Path.home() / ".config" / "marp-presentation" / "brands")
    dirs.append(SKILL / "brands")
    return dirs


def is_brand(path):
    return (path / "brand.json").is_file() and (path / "tokens.css").is_file()


def resolve(brand, deck):
    p = Path(brand).expanduser()
    if p.is_dir() and is_brand(p):
        return p.resolve()
    for d in search_dirs(deck):
        if d.name == "brand" and is_brand(d):  # Deck-Snapshot ist selbst der Brand-Ordner
            if json.loads((d / "brand.json").read_text())["name"] == brand:
                return d.resolve()
            continue
        cand = d / brand
        if cand.is_dir() and is_brand(cand):
            return cand.resolve()
    sys.exit(f"Brand '{brand}' nicht gefunden. Gesucht in: " + ", ".join(str(d) for d in search_dirs(deck)))


def list_brands(deck):
    for d in search_dirs(deck):
        if d.name == "brand" and is_brand(d):
            print(f"{json.loads((d / 'brand.json').read_text())['name']}\t{d}")
        elif d.is_dir():
            for c in sorted(d.iterdir()):
                if c.is_dir() and is_brand(c):
                    print(f"{c.name}\t{c}")


def safe_asset(brand_dir, rel):
    """Asset-Pfade müssen im Brand-Ordner bleiben (Brands können von Dritten stammen)."""
    path = (brand_dir / rel).resolve()
    if not path.is_relative_to(brand_dir):
        sys.exit(f"brand.json: Pfad '{rel}' liegt außerhalb des Brand-Ordners — abgebrochen")
    if not path.is_file():
        sys.exit(f"brand.json: Datei '{rel}' nicht gefunden")
    return path


FONT_MIME = {".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf"}
FONT_FORMAT = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}


def font_faces(brand_dir, meta):
    """@font-face-Regeln aus brand.json "fonts": [{family, file, weight?, style?}] mit Data-URI."""
    css = []
    for f in meta.get("fonts", []):
        path = safe_asset(brand_dir, f["file"])
        ext = path.suffix.lower()
        if ext not in FONT_MIME:
            sys.exit(f"brand.json: Schriftformat '{ext}' nicht unterstützt (woff2, woff, ttf, otf)")
        data = base64.b64encode(path.read_bytes()).decode()
        family = f["family"].replace("'", "")
        css.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {f.get('weight', 'normal')}; "
            f"font-style: {f.get('style', 'normal')}; "
            f"src: url('data:{FONT_MIME[ext]};base64,{data}') format('{FONT_FORMAT[ext]}'); }}\n"
        )
    return "".join(css)


def build(brand_dir, out):
    meta = json.loads((brand_dir / "brand.json").read_text())
    logo = safe_asset(brand_dir, meta["logo"])
    mime = mimetypes.guess_type(logo.name)[0] or "image/svg+xml"
    uri = f"data:{mime};base64," + base64.b64encode(logo.read_bytes()).decode()
    parts = [
        f"/* @theme {meta['name']} */\n",
        "/* GENERIERT von build-theme.py — nicht von Hand editieren (Quelle: Brand tokens.css + Skill base/) */\n",
        font_faces(brand_dir, meta),
        (brand_dir / "tokens.css").read_text(),
        f":root {{ --logo: url('{uri}'); }}\n",
        (BASE / "layouts.css").read_text(),
        (BASE / "components.css").read_text(),
    ]
    if (brand_dir / "layouts.css").is_file():
        parts.append((brand_dir / "layouts.css").read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts))
    print(f"{out} ({out.stat().st_size} Bytes, Brand '{meta['name']}' aus {brand_dir})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--deck")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        return list_brands(a.deck)
    if not (a.brand and a.out):
        ap.error("brand und out angeben (oder --list)")
    build(resolve(a.brand, a.deck), Path(a.out))


if __name__ == "__main__":
    main()
