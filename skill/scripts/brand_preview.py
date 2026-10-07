#!/usr/bin/env python3
"""Vorschau-Deck und Vergleich Original ↔ Marp für einen importierten Brand.

  brand_preview.py preview <brand-dir>            Markdown eines Decks, das jede Layout-Klasse zeigt
  brand_preview.py compare <brand-dir> <out-dir>  rendert Marp, legt Original (reference/) daneben, misst die Abweichung
"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import run_marp  # noqa: E402
from pptx_showcase import SAMPLE  # noqa: E402


def md_safe(text):
    """Layoutnamen (aus fremden Dateien) dürfen im Vorschau-Deck kein Markup/HTML erzeugen."""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f<>&\"'`*/\\\[\]{}()$#@|]", "", text or "")).strip()[:80] or "Layout"


def lines_html(lines):
    return "<br>".join(lines)


def entry_markdown(e, mode):
    cls = e["class"]
    out = []
    if cls != "content":
        out.append(f"<!-- _class: {cls} -->\n")
    compare = mode == "compare"
    if e["title"]:
        out.append(f"# {SAMPLE['title'] if compare else 'Beispieltitel: ' + md_safe(e['layout'])}\n")
    if e["subtitle"]:
        if e["sub_role"] == "body":
            out.append(f"## {lines_html(SAMPLE['body']) if compare else '1'}\n")
        else:
            out.append(f"## {SAMPLE['subtitle'] if compare else 'Untertitel mit etwas mehr Text'}\n")
    if e["slots"]:
        for n in range(1, e["slots"] + 1):
            role = (e.get("slot_roles") or ["body"] * e["slots"])[n - 1]
            if role != "body":    # Bild/Diagramm/Tabelle: im Vergleich leer (das Original zeigt dort ebenfalls nichts)
                out.append("<div></div>\n" if compare else f"<div>\n\n_{role}: hier einfügen_\n\n</div>\n")
                continue
            body = lines_html(SAMPLE["body"]) if compare else "\n".join(f"- {t}" for t in SAMPLE["body"])
            out.append(f"<div>\n\n{body}\n\n</div>\n")
    elif e["flow_body"]:
        out.append((lines_html(SAMPLE["body"]) if compare else "\n".join(f"- {t}" for t in SAMPLE["body"])) + "\n")
    if e["meta"] and not compare:
        out.append('<div class="title-meta"><span>Oktober 2026</span><span>Autor · Ort</span></div>\n')
    return "\n".join(out)


def preview_markdown(meta, mode="preview"):
    size = f"size: {meta['size']['name']}\n" if meta.get("size") else ""
    head = (f"---\nmarp: true\ntheme: {meta['name']}\n{size}paginate: true\nhtml: true\nfooter: \"{SAMPLE['footer']}\"\n---\n\n")
    return head + "\n---\n\n".join(entry_markdown(e, mode) for e in meta["preview"])


def load_meta(brand_dir):
    return json.loads((Path(brand_dir) / "brand.json").read_text())


def im(*args):
    exe = shutil.which("compare")
    if not exe:
        return None
    return subprocess.run([exe, *map(str, args)], capture_output=True, text=True, stdin=subprocess.DEVNULL)


def compare(brand_dir, out_dir):
    brand_dir, out_dir = Path(brand_dir), Path(out_dir)
    meta = load_meta(brand_dir)
    refs = sorted((brand_dir / "reference").glob("*.png"))
    if not refs:
        raise SystemExit("brand compare: keine Referenzbilder (reference/) — beim Import --reference angeben oder LibreOffice nutzen")
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        theme = tmp / "theme.css"
        subprocess.run([sys.executable, str(HERE / "build-theme.py"), str(brand_dir), str(theme)], check=True, capture_output=True)
        md = tmp / "compare.md"
        md.write_text(preview_markdown(meta, "compare"))
        run_marp(["--allow-local-files", "--html", "--theme-set", str(theme), "--images", "png", "-o", str(tmp / "m.png"), str(md)],
                 capture=True)
        marp = sorted(tmp.glob("m.*.png"))
        rows = []
        for j, e in enumerate(meta["preview"]):
            if j >= len(marp):
                break
            ref = refs[e["index"]]
            name = f"{j + 1:02d}-{e['class']}"
            shutil.copy(marp[j], out_dir / f"{name}-marp.png")
            shutil.copy(ref, out_dir / f"{name}-original.png")
            r = im("-metric", "RMSE", "-compose", "src", out_dir / f"{name}-original.png", out_dir / f"{name}-marp.png", out_dir / f"{name}-diff.png")
            m = re.search(r"\(([\d.eE+-]+)\)", (r.stderr or r.stdout) if r else "")
            diff = float(m.group(1)) if m else None
            rows.append({"class": e["class"], "layout": e["layout"], "files": name, "abweichung": diff})
            if shutil.which("montage"):
                subprocess.run(["montage", "-label", "Original", out_dir / f"{name}-original.png", "-label", "Marp", out_dir / f"{name}-marp.png",
                                "-label", "Differenz", out_dir / f"{name}-diff.png", "-tile", "3x1", "-geometry", "640x360+4+4",
                                out_dir / f"{name}-vergleich.png"], check=False, capture_output=True, stdin=subprocess.DEVNULL)
    (out_dir / "vergleich.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    return rows


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, brand = sys.argv[1], sys.argv[2]
    if cmd == "preview":
        print(preview_markdown(load_meta(brand)))
    elif cmd == "compare" and len(sys.argv) == 4:
        for r in compare(brand, sys.argv[3]):
            ab = "n/a" if r["abweichung"] is None else f"{r['abweichung'] * 100:.1f} %"
            print(f"{r['class']:<24} {r['layout']:<24} Abweichung {ab}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
