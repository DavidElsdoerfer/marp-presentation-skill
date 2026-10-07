#!/usr/bin/env python3
"""Erzeugt aus einer PPTX/POTX ein Marp-Brand (Stufe A des CI-Imports; nur Standardbibliothek + optional LibreOffice).

Ergebnis im Brand-Ordner:
  brand.json   Name, Logo, overrides, Layout-Zuordnung, Schriften, Palette
  tokens.css   Farben und Schriften aus dem Theme
  layouts.css  generierte Layouts (Hintergrund, Position/Größe von Titel, Inhalt, Fuß, Nummer)
  layouts.md   Doku: welche Markdown-Struktur füllt welches Layout
  assets/      bg/ (Hintergründe je Layout), media/ (Logo, Bilder), fonts/ (optional)

Hintergründe nach Qualität: gerenderte Layouts (LibreOffice oder vom Nutzer gelieferte PDF/PNG) →
sonst Rekonstruktion aus Master/Layout-Grafiken (Ebenen aus Farbflächen, Verläufen und Bildern).
"""
import colorsys, json, re, shutil, subprocess, sys, tempfile, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pptx_extract as px  # noqa: E402
import pptx_showcase as sc  # noqa: E402

SLIDE_W, SLIDE_H = 1280, 720
SERIF = ("georgia", "times", "cambria", "garamond", "palatino", "book antiqua", "constantia", "baskerville", "minion")
CLOSING_RE = re.compile(r"(clos|end|thank|danke|abschluss|schluss|ende|kontakt|contact|fragen|questions)", re.I)


class ImportError_(Exception):
    pass


# ── Hilfen ─────────────────────────────────────────────────────────────────

def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "layout"


def mix(h1, h2, t):
    a, b = px.hex_to_rgb(h1), px.hex_to_rgb(h2)
    return px.rgb_to_hex(tuple(a[i] * (1 - t) + b[i] * t for i in range(3)))


def lightness(h):
    return colorsys.rgb_to_hls(*px.hex_to_rgb(h))[1]


def darker(h, f):
    r, l, s = colorsys.rgb_to_hls(*px.hex_to_rgb(h))
    return px.rgb_to_hex(colorsys.hls_to_rgb(r, max(0, l * f), s))


def r1(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


class Scale:
    """Rechnet Bruchteile und Punkt in Marp-Pixel (Folie 1280 × 720 bei 16:9) um."""

    def __init__(self, slide):
        self.aspect = slide["w_emu"] / slide["h_emu"]
        self.h = SLIDE_H
        if abs(self.aspect - 16 / 9) < 0.01:
            self.w, self.size_name = SLIDE_W, None                   # Marp-Standard, keine Größenangabe nötig
        elif abs(self.aspect - 4 / 3) < 0.01:
            self.w, self.size_name = 960, "4:3"
        else:
            self.w, self.size_name = round(SLIDE_H * self.aspect), "brand"
        self.pt = self.w / slide["w_pt"]

    def x(self, f): return f * self.w
    def y(self, f): return f * self.h
    def size(self, pt): return pt * self.pt


def font_stack(face, generic=None):
    if not face:
        return None
    generic = generic or ("serif" if any(s in face.lower() for s in SERIF) else "sans-serif")
    return f'"{face}", {generic}'


def rgba(color):
    h, a = color["hex"], color.get("alpha")
    if a is None or a >= 0.999:
        return h
    r, g, b = (round(c * 255) for c in px.hex_to_rgb(h))
    return f"rgba({r}, {g}, {b}, {a:.3g})"


# ── Hintergründe ───────────────────────────────────────────────────────────

def grad_css(f):
    stops = ", ".join(f"{rgba(s)} {s['pos'] * 100:.0f}%" for s in f["stops"]) or "transparent, transparent"
    if f.get("kind") == "radial":
        return f"radial-gradient(circle at center, {stops})"
    return f"linear-gradient({(f['angle'] + 90) % 360:.0f}deg, {stops})"


def layer_for(shape, sc_, media_url, warnings):
    """CSS-Hintergrundebene für eine Grafik (Bild, Farbfläche, Linie) oder None."""
    xf = shape.get("xfrm")
    if not xf:
        return None
    x, y, w, h = sc_.x(xf["x"] / sc_.src_w), sc_.y(xf["y"] / sc_.src_h), sc_.x(xf["cx"] / sc_.src_w), sc_.y(xf["cy"] / sc_.src_h)
    pos = f"{r1(x)}px {r1(y)}px / {r1(w)}px {r1(h)}px no-repeat"
    kind = shape["kind"]
    if kind == "picture" and shape.get("image"):
        url = media_url(shape["image"])
        return f"url('{url}') {pos}" if url else None
    if kind == "line":
        ln = shape.get("line")
        if not ln:
            return None
        t = max(sc_.size(ln["w_pt"]), 1)
        if h < 1:  # waagerecht
            return f"linear-gradient({ln['hex']}, {ln['hex']}) {r1(x)}px {r1(y - t / 2)}px / {r1(w)}px {r1(t)}px no-repeat"
        return f"linear-gradient({ln['hex']}, {ln['hex']}) {r1(x - t / 2)}px {r1(y)}px / {r1(t)}px {r1(h)}px no-repeat"
    fill = shape.get("fill")
    if kind != "shape" or not fill or fill.get("type") == "none":
        return None
    geom = shape.get("geom")
    if geom not in (None, "rect", "roundRect", "ellipse", "flowChartProcess"):
        warnings.append(f"Form '{shape.get('name')}' ({geom}) wird nur als Rechteck angenähert")
    if fill["type"] == "solid" and fill.get("hex"):
        c = rgba(fill)
        if geom == "ellipse":
            return f"radial-gradient(ellipse closest-side, {c} 99%, transparent 100%) {pos}"
        return f"linear-gradient({c}, {c}) {pos}"
    if fill["type"] == "gradient":
        return f"{grad_css(fill)} {pos}"
    if fill["type"] == "image":
        url = media_url(fill.get("image"))
        return f"url('{url}') {pos}" if url else None
    return None


def layered_background(data, layout, sc_, media_url, warnings):
    """Rekonstruktion ohne Rendering: Hintergrundfüllung + Grafiken aus Master und Layout (oberste Ebene zuerst)."""
    master = data["masters"][layout["master"]]
    layers, base = [], "#ffffff"
    bg = layout.get("bg") or master.get("bg")
    if bg and bg.get("type") == "solid" and bg.get("hex"):
        base = bg["hex"]
    elif bg and bg.get("type") == "gradient":
        layers.append(grad_css(bg))
    elif bg and bg.get("type") == "image":
        url = media_url(bg.get("image"))
        if url:
            layers.append(f"url('{url}') center / 100% 100% no-repeat")
    shapes = []
    if layout.get("show_master_shapes", True):
        shapes += [s for s in master["shapes"] if s["kind"] != "placeholder"]
    shapes += [s for s in layout["shapes"] if s["kind"] != "placeholder"]
    top_first = []
    for s in reversed(shapes):  # spätere Formen liegen oben; CSS listet die oberste Ebene zuerst
        l = layer_for(s, sc_, media_url, warnings)
        if l:
            top_first.append(l)
    return ", ".join(top_first + layers) if (top_first or layers) else "none", base


# ── Layout-Zuordnung ───────────────────────────────────────────────────────

def classify(data, overrides=None):
    """Ordnet Layouts den semantischen Klassen title/section/closing/cols/content zu; Rest = layout-<slug>."""
    layouts = data["layouts"]
    taken = {}
    ov = overrides or {}

    def pick(cls, pred):
        if cls in ov:
            for i, l in enumerate(layouts):
                if l["name"].lower() == ov[cls].lower():
                    taken[cls] = i
                    return
            raise ImportError_(f"--map {cls}={ov[cls]}: Layout nicht gefunden (vorhanden: {[l['name'] for l in layouts]})")
        for i, l in enumerate(layouts):
            if i not in taken.values() and pred(l):
                taken[cls] = i
                return

    roles = lambda l: [s["ph"]["role"] for s in l["shapes"] if s["kind"] == "placeholder"]
    pick("title", lambda l: l["type"] == "title" or "ctrTitle" in [s["ph"]["type"] for s in l["shapes"] if s["kind"] == "placeholder"])
    pick("section", lambda l: l["type"] == "secHead")
    pick("closing", lambda l: bool(CLOSING_RE.search(l["name"])) and l["type"] in (None, "title", "secHead", "blank", "titleOnly", "cust"))
    pick("cols", lambda l: l["type"] in ("twoObj", "twoTxTwoObj") or roles(l).count("body") == 2)
    pick("content", lambda l: l["type"] in ("obj", "tx") or (roles(l).count("body") == 1 and "title" in roles(l)))
    classes = {}  # layout index -> [Klassen]
    for cls, i in taken.items():
        classes.setdefault(i, []).append(cls)
    slugs, used = {}, set()
    for i, l in enumerate(layouts):
        if i in classes:
            continue
        if l["type"] == "blank" and not any(s["kind"] != "placeholder" for s in l["shapes"]):
            continue  # leeres Layout nicht als Klasse anbieten
        s = f"layout-{slugify(l['name'])}"
        n, base = 2, s
        while s in used:
            s = f"{base}-{n}"; n += 1
        used.add(s)
        classes[i] = [s]
    return classes


# ── CSS-Erzeugung ──────────────────────────────────────────────────────────

def ph_list(layout, *roles):
    return [s for s in layout["shapes"] if s["kind"] == "placeholder" and s["ph"]["role"] in roles and s.get("xfrm")]


def reading_order(shapes):
    return sorted(shapes, key=lambda s: (round(s["xfrm"]["y"] / 300000), s["xfrm"]["x"]))


def text_css(tp, sc_, theme_fonts, *, default_color=None, heading=False):
    out = []
    if "size_pt" in tp:
        out.append(f"font-size: {r1(sc_.size(tp['size_pt']))}px")
    out.append(f"font-weight: {700 if tp.get('bold') else 400}")
    if tp.get("italic"):
        out.append("font-style: italic")
    if tp.get("caps") == "all":
        out.append("text-transform: uppercase")
    col = tp.get("color") or default_color
    if col:
        out.append(f"color: {col}")
    if tp.get("align"):
        out.append("text-align: " + {"l": "left", "r": "right", "ctr": "center", "just": "justify"}.get(tp["align"], "left"))
    face = tp.get("font")
    major, minor = theme_fonts.get("major"), theme_fonts.get("minor")
    wanted = major if heading else minor
    if face and face != wanted:
        out.append(f"font-family: {font_stack(face)}")
    else:  # explizit setzen: die Basis-Typografie nutzt für h1–h4 sonst die Überschriftenschrift
        out.append("font-family: var(--font-heading, var(--font))" if heading else "font-family: var(--font)")
    return out


def box_css(s, sc_):
    xf = s["xfrm"]
    f = px.Slide(sc_.src_w, sc_.src_h).frac(xf["x"], xf["y"], xf["cx"], xf["cy"])
    return [f"left: {r1(sc_.x(f['x']))}px", f"top: {r1(sc_.y(f['y']))}px", f"width: {r1(sc_.x(f['w']))}px", f"height: {r1(sc_.y(f['h']))}px"], f


def insets_of(s):
    """Innenabstände eines Platzhalters in pt (PowerPoint-Standard, wenn nichts gesetzt ist)."""
    return {"lIns": 7.2, "tIns": 3.6, "rIns": 7.2, "bIns": 3.6, **(s.get("body") or {}).get("insets", {})}


def anchor_css(s):
    a = (s.get("body") or {}).get("anchor", "t")
    return {"t": "flex-start", "ctr": "center", "b": "flex-end"}.get(a, "flex-start")


def rotation_css(s):
    rot = (s.get("xfrm") or {}).get("rot", 0.0) % 360
    if abs(rot) < 0.05 or abs(rot - 360) < 0.05:
        return []
    return [f"transform: rotate({r1(rot - 360 if rot > 180 else rot)}deg)", "transform-origin: center"]


def abs_text_block(sel, s, sc_, theme_fonts, heading):
    box, _ = box_css(s, sc_)
    ins = insets_of(s)
    decl = ["position: absolute", *box, "margin: 0", "border: 0", "box-sizing: border-box",
            f"padding: {r1(sc_.size(ins['tIns']))}px {r1(sc_.size(ins['rIns']))}px {r1(sc_.size(ins['bIns']))}px {r1(sc_.size(ins['lIns']))}px",
            "display: flex", "flex-direction: column", f"justify-content: {anchor_css(s)}", "line-height: 1.2", "overflow: visible",
            "letter-spacing: normal", *rotation_css(s), *text_css(s.get("text_props", {}), sc_, theme_fonts, heading=heading)]
    return f"{sel} {{\n  " + ";\n  ".join(decl) + ";\n}\n"


def plan(layout, mode):
    """Welche Platzhalter wofür genutzt werden (gemeinsame Grundlage für CSS und Vorschau-Deck)."""
    titles = ph_list(layout, "title")
    subs = ph_list(layout, "subtitle")
    bodies = reading_order(ph_list(layout, "body", "picture", "chart", "table", "media", "diagram"))
    texts = [b for b in bodies if b["ph"]["role"] == "body"]
    secondary = None
    if mode != "content" and subs:
        secondary = subs[0]
    elif mode == "special" and texts:       # z. B. Abschnittsnummer im Textfeld des Abschnittslayouts
        secondary = texts[0]
        bodies = [b for b in bodies if b is not secondary]
    only_flow_body = len(bodies) == 1 and bodies[0]["ph"]["role"] == "body" and mode != "special"
    use_slots = (len(bodies) >= 2 or (len(bodies) == 1 and not only_flow_body)) and mode != "special"
    body_tp = (bodies[0].get("text_props") if bodies else (secondary or {}).get("text_props")) or {}
    return {"titles": titles, "secondary": secondary, "bodies": bodies, "only_flow_body": only_flow_body, "use_slots": use_slots,
            "body_tp": body_tp, "foot": ph_list(layout, "footer"), "num": ph_list(layout, "number")}


def layout_css(data, layout, selectors, bg, base_color, sc_, mode):
    """CSS-Block für ein Layout. mode: 'content' (Standardfolie), 'special' (title/section/closing), 'cols', 'custom'."""
    sel = ", ".join(f"section.{c}" if c != "content" else "section" for c in selectors)
    pre = lambda suffix: ", ".join((f"section.{c}" if c != "content" else "section") + suffix for c in selectors)
    fonts = data["theme"]["fonts"]
    pl = plan(layout, mode)
    titles, secondary, bodies = pl["titles"], pl["secondary"], pl["bodies"]
    foot, num, only_flow_body, use_slots, body_tp = pl["foot"], pl["num"], pl["only_flow_body"], pl["use_slots"], pl["body_tp"]
    out = [f"/* ── {layout['name']} → {', '.join(selectors)} ── */\n"]

    # Folienfläche
    pad = "0"
    if only_flow_body:
        _, f = box_css(bodies[0], sc_)
        ins = insets_of(bodies[0])
        # Felder dürfen über den Folienrand ragen → Abstände nie negativ (sonst verwirft CSS die ganze Zeile)
        pad = (f"{r1(max(0, sc_.y(f['y']) + sc_.size(ins['tIns'])))}px {r1(max(0, sc_.x(1 - f['x'] - f['w']) + sc_.size(ins['rIns'])))}px "
               f"{r1(max(0, sc_.y(1 - f['y'] - f['h']) + sc_.size(ins['bIns'])))}px {r1(max(0, sc_.x(f['x']) + sc_.size(ins['lIns'])))}px")
    base_size = r1(sc_.size(body_tp["size_pt"])) + "px" if "size_pt" in body_tp else "24px"
    decl = [f"background: {bg}" if bg != "none" else "background: none", f"background-color: {base_color}",
            "border: 0", "box-sizing: border-box", "position: relative", "display: block", f"padding: {pad}",
            f"font-family: var(--font)", f"font-size: {base_size}", "line-height: 1.2",
            f"color: {body_tp.get('color') or 'var(--text)'}"]
    out.append(f"{sel} {{\n  " + ";\n  ".join(d for d in decl if d) + ";\n}\n")
    out.append(f"{pre('::before')} {{ display: none; }}\n")

    # Titel
    if titles:
        out.append(abs_text_block(pre(" h1"), titles[0], sc_, fonts, heading=True))
        out.append(f"{pre(' h1::after')} {{ display: none; }}\n")
    else:
        out.append(f"{pre(' h1')} {{ display: none; }}\n")
    # erstes Fluss-Element direkt am oberen Rand des Inhaltsbereichs (Browser geben ihm sonst 1em Außenabstand)
    out.append(f"{pre(' > h1 + *')} {{ margin-top: 0; }}\n")
    if secondary is not None and mode != "content":
        out.append(f"{pre(' > h1 + h2 + *')} {{ margin-top: 0; }}\n")
    # Untertitel/zweiter Text → h2
    if secondary is not None and mode != "content":
        out.append(abs_text_block(pre(" h2"), secondary, sc_, fonts, heading=False))
        # Absätze unter dem zweiten Text (Kontakt, Hinweise)
        box, f = box_css(secondary, sc_)
        top = sc_.y(f["y"] + f["h"]) + 8
        small = secondary.get("text_props", {}).get("size_pt", 20) * 0.6
        out.append(f"{pre(' > p')} {{\n  position: absolute; left: {box[0].split(': ')[1]}; top: {r1(top)}px; width: {box[2].split(': ')[1]};\n"
                   f"  margin: 0 0 4px 0; font-size: {r1(sc_.size(small))}px; color: {secondary.get('text_props', {}).get('color') or 'inherit'};\n}}\n")

    # Meta-Zeile der Titelfolie
    if "title" in selectors or "closing" in selectors:
        left = box_css(titles[0], sc_)[0][0] if titles else "left: 64px"
        out.append(f"{pre(' .title-meta')} {{\n  position: absolute; {left}; bottom: {r1(sc_.y(0.06))}px; width: {r1(sc_.x(0.88))}px;\n"
                   f"  display: flex; justify-content: space-between; margin: 0; font-size: {r1(sc_.size(14))}px;\n"
                   f"  opacity: 0.85; border-top: 1px solid currentColor; padding-top: 8px;\n}}\n")

    # Inhalts-Slots (n-tes <div> = n-ter Platzhalter in Leserichtung)
    if use_slots:
        for n, b in enumerate(bodies, start=1):
            box, _ = box_css(b, sc_)
            ins = insets_of(b)
            slot = pre(f" > div:nth-of-type({n})")
            out.append(f"{slot} {{\n  position: absolute; " + "; ".join(box) +
                       f"; box-sizing: border-box; margin: 0;\n  padding: {r1(sc_.size(ins['tIns']))}px {r1(sc_.size(ins['rIns']))}px "
                       f"{r1(sc_.size(ins['bIns']))}px {r1(sc_.size(ins['lIns']))}px;\n  " +
                       ";\n  ".join(text_css(b.get("text_props", {}), sc_, fonts, default_color="var(--text)")) + ";\n}\n")
            out.append(f"{pre(f' > div:nth-of-type({n}) > :first-child')} {{ margin-top: 0; }}\n")
            if b["ph"]["role"] != "body":   # Bild-, Diagramm-, Tabellen-Platzhalter: Inhalt füllt die Fläche
                out.append(f"{pre(f' > div:nth-of-type({n}) img')} {{ width: 100%; height: 100%; object-fit: cover; display: block; }}\n")

    # Fußzeile und Seitenzahl
    if foot:
        out.append(abs_text_block(pre(" footer"), foot[0], sc_, fonts, heading=False))
    else:
        out.append(f"{pre(' footer')} {{ display: none; }}\n")
    if num:
        box, _ = box_css(num[0], sc_)
        tp = text_css(num[0].get("text_props", {}), sc_, fonts)
        # Hinweis: Marpit setzt content auf section::after selbst (Seitenzahl) und verwirft eigene Werte.
        out.append(f"{pre('::after')} {{\n  position: absolute; " + "; ".join(box) +
                   ";\n  padding: 0; display: flex; align-items: center; justify-content: flex-end;\n  " + ";\n  ".join(tp) + ";\n}\n")
    else:
        out.append(f"{pre('::after')} {{ display: none; }}\n")
    return "\n".join(out) + "\n"


# ── Tokens ─────────────────────────────────────────────────────────────────

def derive_tokens(data):
    c = data["theme"]["colors"]
    g = lambda k, d: c.get(k, d)
    dk1, lt1, dk2, lt2 = g("dk1", "#1f2933"), g("lt1", "#ffffff"), g("dk2", "#1f2933"), g("lt2", "#f0f0f0")
    prim = g("accent1", "#2f5d8a")
    dark = dk2 if lightness(dk2) < 0.35 else dk1
    light = lt2 if lightness(lt2) > 0.8 else "#f0f0f0"
    tokens = {
        "--primary": prim, "--primary-dk": darker(prim, 0.78), "--primary-lt": mix(prim, "#ffffff", 0.35),
        "--primary-xl": mix(prim, "#ffffff", 0.90), "--dark": dark, "--text": dk1, "--muted": mix(dk1, lt1, 0.55),
        "--border": mix(dk1, lt1, 0.88), "--light": light, "--white": lt1, "--grey-label": mix(dk1, lt1, 0.62),
        "--grey-mid": mix(dk1, lt1, 0.82), "--callout": mix(prim, "#ffffff", 0.72)}
    fonts = data["theme"]["fonts"]
    minor, major = fonts.get("minor"), fonts.get("major")
    tokens["--font"] = font_stack(minor, "sans-serif") + ', system-ui, "Segoe UI", Helvetica, Arial, sans-serif' if minor else \
        '-apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
    if major and major != minor:
        tokens["--font-heading"] = font_stack(major)
    return tokens


def tokens_css(tokens, source):
    body = "\n".join(f"  {k}: {v};" for k, v in tokens.items())
    return f"/* Brand-Tokens — generiert aus {source} (Theme-Farben/-Schriften). Anpassen erlaubt. */\n:root {{\n{body}\n}}\n"


# ── Rendern ────────────────────────────────────────────────────────────────

def pdf_to_pngs(pdf, outdir, width=SLIDE_W, height=SLIDE_H):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    if not shutil.which("pdftocairo"):
        raise ImportError_("pdftocairo fehlt (poppler-utils) — PDF kann nicht in Bilder umgewandelt werden")
    # Exakte Zielgröße (nicht -scale-to-y -1): PDF-Seitengrößen runden sonst auf 721 px und strecken Hintergründe um 1 px.
    subprocess.run(["pdftocairo", "-png", "-scale-to-x", str(width), "-scale-to-y", str(height), str(pdf), str(Path(outdir) / "bg")],
                   check=True, stdin=subprocess.DEVNULL, capture_output=True)
    files = sorted(Path(outdir).glob("bg-*.png"), key=lambda p: int(re.search(r"(\d+)\.png$", p.name).group(1)))
    return files


def render_with_libreoffice(pptx, tmp, filled=False):
    soffice = shutil.which("soffice")
    if not soffice:
        return None
    Path(tmp).mkdir(parents=True, exist_ok=True)
    show = Path(tmp) / "showcase.pptx"
    sc.build(pptx, show, filled=filled)
    r = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(show)],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    pdf = Path(tmp) / "showcase.pdf"
    return pdf if pdf.is_file() else None


# ── Hauptfunktion ──────────────────────────────────────────────────────────

def import_brand(pptx, name, out_dir, backgrounds=None, render=True, mapping=None, guidelines=(), fonts_dir=None, reference=None):
    pptx, out_dir = Path(pptx), Path(out_dir)
    data = px.extract(pptx)
    warnings = []
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ImportError_(f"{out_dir} existiert und ist nicht leer")
    sc_ = Scale(data["slide"])
    sc_.src_w, sc_.src_h = data["slide"]["w_emu"], data["slide"]["h_emu"]
    if sc_.size_name == "brand":
        warnings.append(f"Seitenverhältnis {sc_.aspect:.2f} (weder 16:9 noch 4:3): eigene Foliengröße {sc_.w}×{sc_.h} px — wenig getestet")

    classes = classify(data, mapping)
    layouts = data["layouts"]

    # Hintergründe beschaffen
    bg_files, bg_mode = {}, "layers"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        files = None
        if backgrounds:
            b = Path(backgrounds)
            if b.suffix.lower() == ".pdf":
                files = pdf_to_pngs(b, tmp, sc_.w)
            elif b.is_dir():
                files = sorted([p for p in b.iterdir() if p.suffix.lower() == ".png"],
                               key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)])
            else:
                raise ImportError_(f"--backgrounds: {b} ist weder PDF noch Ordner mit PNGs")
        elif render:
            pdf = render_with_libreoffice(pptx, tmp)
            if pdf:
                files = pdf_to_pngs(pdf, tmp, sc_.w)
            else:
                warnings.append("LibreOffice nicht verfügbar oder Rendering fehlgeschlagen — Hintergründe werden aus den Grafiken rekonstruiert")
        ref_files = None
        if reference:
            r = Path(reference)
            ref_files = pdf_to_pngs(r, tmp / "ref", sc_.w) if r.suffix.lower() == ".pdf" else sorted(r.glob("*.png"))
        elif render and not backgrounds:
            pdf = render_with_libreoffice(pptx, tmp / "ref", filled=True)
            ref_files = pdf_to_pngs(pdf, tmp / "ref", sc_.w) if pdf else None
        if ref_files is not None and len(ref_files) == len(layouts):
            (out_dir / "reference").mkdir(parents=True)
            for i, f in enumerate(ref_files):
                shutil.copy(f, out_dir / "reference" / f"{i + 1:02d}-{slugify(layouts[i]['name'])}.png")
        elif ref_files is not None:
            warnings.append(f"{len(ref_files)} Referenzbilder für {len(layouts)} Layouts — Vergleich nicht möglich")
        if files is not None:
            if len(files) != len(layouts):
                warnings.append(f"{len(files)} Hintergrundbilder für {len(layouts)} Layouts — Zuordnung unmöglich, Rekonstruktion aus Grafiken")
            else:
                bg_files = {i: p for i, p in enumerate(files)}
                bg_mode = "render"

        # Ausgabeordner
        (out_dir / "assets" / "bg").mkdir(parents=True)
        (out_dir / "assets" / "media").mkdir(parents=True)
        media_map = {}

        def media_url(target):
            if not target:
                return None
            if target not in media_map:
                pkg = px.Package(pptx)
                dst = out_dir / "assets" / "media" / Path(target).name
                dst.write_bytes(pkg.read(target))
                media_map[target] = f"assets/media/{dst.name}"
            return media_map[target]

        bg_css = {}
        for i, l in enumerate(layouts):
            if i not in classes:
                continue
            if bg_mode == "render":
                slug = f"{i + 1:02d}-{slugify(l['name'])}"
                shutil.copy(bg_files[i], out_dir / "assets" / "bg" / f"{slug}.png")
                bg_css[i] = (f"url('assets/bg/{slug}.png') center / 100% 100% no-repeat", "#ffffff")
            else:
                bg_css[i] = layered_background(data, l, sc_, media_url, warnings)

        # Logo: größtes Bild im Master, sonst im Titellayout, sonst Platzhalter
        logo = None
        cands = [s for s in data["masters"][0]["shapes"] if s["kind"] == "picture" and s.get("image")]
        for i in classes:
            cands += [s for s in layouts[i]["shapes"] if s["kind"] == "picture" and s.get("image")]
        if cands:
            best = max(cands, key=lambda s: (s["xfrm"] or {}).get("cx", 0) * (s["xfrm"] or {}).get("cy", 0))
            logo = media_url(best["image"])
        if not logo:
            shutil.copy(HERE.parent / "brands" / "neutral" / "assets" / "logo.svg", out_dir / "assets" / "logo.svg")
            logo = "assets/logo.svg"
            warnings.append("kein Logo in der Vorlage gefunden — Platzhalter-Logo eingesetzt (assets/logo.svg ersetzen)")

        # layouts.css
        overrides = []
        css = [f"/* Brand-Layouts — GENERIERT von brand_import.py aus {pptx.name}.\n"
               "   Für Handarbeit lieber custom.css anlegen (wird nach dieser Datei eingebunden und bleibt bei Neuimport erhalten). */\n"]
        used_semantic, preview = {}, []
        for i, cls_list in sorted(classes.items()):
            l = layouts[i]
            sem = [c for c in cls_list if c in ("title", "section", "closing", "cols", "content")]
            for c in sem:
                used_semantic[c] = l["name"]
            bg, base = bg_css[i]
            mode = "content" if "content" in cls_list else "special" if any(c in cls_list for c in ("title", "section", "closing")) \
                else "cols" if "cols" in cls_list else "custom"
            css.append(layout_css(data, l, cls_list, bg, base, sc_, mode))
            pl = plan(l, mode)
            for c in cls_list:
                preview.append(preview_entry(c, l, i, pl, mode))
        # closing ohne eigenes Layout → wie Titelfolie
        if "closing" not in used_semantic and "title" in used_semantic:
            ti = classes_index(classes, "title")
            css.append(layout_css(data, layouts[ti], ["closing"], *bg_css[ti], sc_, "special"))
            preview.append(preview_entry("closing", layouts[ti], ti, plan(layouts[ti], "special"), "special"))
            used_semantic["closing"] = f"{used_semantic['title']} (wie Titelfolie)"
        for blk, cls in (("chrome", "content"), ("title", "title"), ("section", "section"), ("closing", "closing"), ("cols", "cols")):
            if cls in used_semantic:
                overrides.append(blk)
        (out_dir / "layouts.css").write_text("\n".join(css))

        # Tokens, Schriften
        tokens = derive_tokens(data)
        (out_dir / "tokens.css").write_text(tokens_css(tokens, pptx.name))
        font_info = register_fonts(data, out_dir, fonts_dir, warnings)

        meta = {"name": name, "logo": logo, "overrides": overrides, "source": pptx.name, "background_mode": bg_mode,
                "layouts": {c: n for c, n in used_semantic.items()},
                "custom_layouts": {c: layouts[i]["name"] for i, cl in classes.items() for c in cl if c.startswith("layout-")},
                **({"size": {"name": sc_.size_name, "w": sc_.w, "h": sc_.h}} if sc_.size_name else {}),
                "preview": preview, "slide": {"w_pt": data["slide"]["w_pt"], "h_pt": data["slide"]["h_pt"], "aspect": data["slide"]["aspect"]},
                "palette": data["theme"]["colors"], "theme_fonts": data["theme"]["fonts"]}
        if font_info["fonts"]:
            meta["fonts"] = font_info["fonts"]
        if font_info["missing"]:
            meta["fonts_missing"] = font_info["missing"]
        (out_dir / "brand.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        (out_dir / "layouts.md").write_text(layouts_doc(data, classes, used_semantic, name))

        if guidelines:
            gd = out_dir / "guidelines"
            gd.mkdir()
            for g in guidelines:
                shutil.copy(g, gd / Path(g).name)
            (out_dir / "GUIDELINES.md").write_text(
                f"# Gestaltungsregeln {name}\n\n"
                "<!-- Der Agent verdichtet hier die Regeln aus den Originaldokumenten in guidelines/ zu kurzen,\n"
                "     prüfbaren Aussagen (Logo-Abstand, Farbeinsatz, Schriftgrößen, Tonalität, Verbote). -->\n\n"
                "Quellen: " + ", ".join(f"`guidelines/{Path(g).name}`" for g in guidelines) + "\n\n## Regeln\n\n_(noch nicht ausgewertet)_\n")

    return {"name": name, "dir": str(out_dir), "mode": bg_mode, "classes": {data["layouts"][i]["name"]: c for i, c in classes.items()},
            "semantic": used_semantic, "fonts_missing": font_info["missing"], "warnings": sorted(set(warnings)),
            "guidelines": [Path(g).name for g in guidelines]}


def preview_entry(cls, layout, index, pl, mode):
    return {"class": cls, "layout": layout["name"], "index": index, "title": bool(pl["titles"]),
            "subtitle": pl["secondary"] is not None and mode != "content",
            "slots": len(pl["bodies"]) if pl["use_slots"] else 0, "slot_roles": [b["ph"]["role"] for b in pl["bodies"]] if pl["use_slots"] else [],
            "flow_body": pl["only_flow_body"],
            "sub_role": pl["secondary"]["ph"]["role"] if pl["secondary"] and mode != "content" else None,
            "meta": cls in ("title", "closing")}


def classes_index(classes, cls):
    return next(i for i, cl in classes.items() if cls in cl)


def installed(family):
    if not shutil.which("fc-list"):
        return None
    r = subprocess.run(["fc-list", family, "family"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return bool(r.stdout.strip())


def register_fonts(data, out_dir, fonts_dir, warnings):
    """Schriftnamen melden; mitgelieferte Dateien einbetten (woff2/woff/ttf/otf)."""
    needed = sorted({f for f in data["theme"]["fonts"].values() if f})
    for l in data["layouts"]:
        for s in l["shapes"]:
            f = (s.get("text_props") or {}).get("font")
            if f and not f.startswith("+"):
                needed.append(f)
    needed = sorted(set(needed))
    fonts, found = [], set()
    if fonts_dir:
        fd = Path(fonts_dir)
        (out_dir / "fonts").mkdir(exist_ok=True)
        for p in sorted(fd.iterdir()):
            if p.suffix.lower() not in (".woff2", ".woff", ".ttf", ".otf"):
                continue
            fam, weight, style = font_identity(p)
            match = next((n for n in needed if slugify(n) == slugify(fam) or slugify(n) in slugify(p.stem)), None)
            if match:
                shutil.copy(p, out_dir / "fonts" / p.name)
                fonts.append({"family": match, "file": f"fonts/{p.name}", "weight": weight, "style": style})
                found.add(match)
    missing = [n for n in needed if n not in found and installed(n) is False]
    if missing:
        warnings.append("Schriften nicht installiert und nicht mitgeliefert: " + ", ".join(missing) +
                        " — PDF/HTML nutzen sonst Ersatzschriften (--fonts ORDNER angeben)")
    return {"fonts": fonts, "missing": missing}


def font_identity(path):
    """Familie, Gewicht, Stil einer Schriftdatei (fc-scan, sonst aus dem Dateinamen geraten)."""
    stem = path.stem
    if shutil.which("fc-scan"):
        r = subprocess.run(["fc-scan", "--format", "%{family[0]}|%{weight}|%{slant}", str(path)], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        if r.returncode == 0 and "|" in r.stdout:
            fam, w, sl = (r.stdout.strip().split("|") + ["", "", ""])[:3]
            try:
                weight = {80: 400, 100: 500, 180: 600, 200: 700, 205: 800, 210: 900, 0: 100, 40: 300}.get(int(float(w)), 400)
            except ValueError:
                weight = 400
            return fam, weight, "italic" if sl.strip() not in ("0", "") else "normal"
    low = stem.lower()
    return re.sub(r"[-_ ](bold|italic|regular|light|medium|black).*$", "", stem, flags=re.I), (700 if "bold" in low else 400), ("italic" if "italic" in low else "normal")


def layouts_doc(data, classes, semantic, name):
    lines = [f"# Layouts von {name}\n", f"Quelle: `{data['source']}`. Klasse pro Folie: `<!-- _class: <klasse> -->`.\n",
             "**Slots:** Layouts mit mehreren Inhaltsbereichen füllst du mit je einem `<div>` pro Bereich, in Leserichtung "
             "(Leerzeile nach dem öffnenden Tag, damit Markdown darin gilt).\n"]
    for i, cls_list in sorted(classes.items()):
        l = data["layouts"][i]
        roles = [s["ph"]["role"] for s in l["shapes"] if s["kind"] == "placeholder" and s["ph"]["role"] not in ("date", "footer", "number")]
        bodies = reading_order(ph_list(l, "body", "picture", "chart", "table", "media", "diagram"))
        lines.append(f"## `{'`, `'.join(cls_list)}` — {l['name']}\n")
        parts = []
        if "title" in roles:
            parts.append("`# Titel`")
        if "subtitle" in roles:
            parts.append("`## Untertitel`")
        if len(bodies) == 1 and bodies[0]["ph"]["role"] == "body":
            parts.append("Inhalt als normales Markdown darunter")
        elif bodies:
            parts.append(f"{len(bodies)} Slots als `<div>` (" + ", ".join(b["ph"]["role"] for b in bodies) + ")")
        if any(c in cls_list for c in ("title", "closing")):
            parts.append("Meta-Zeile `<div class=\"title-meta\"><span>…</span><span>…</span></div>`")
        lines.append("- " + "\n- ".join(parts or ["(nur Grafik)"]) + "\n")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx"); ap.add_argument("out"); ap.add_argument("--name", required=True)
    ap.add_argument("--backgrounds"); ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--map", action="append", default=[], help="klasse=Layoutname, z. B. closing=Danke")
    ap.add_argument("--guidelines", action="append", default=[]); ap.add_argument("--fonts"); ap.add_argument("--reference")
    a = ap.parse_args()
    mapping = dict(m.split("=", 1) for m in a.map)
    try:
        res = import_brand(a.pptx, a.name, a.out, a.backgrounds, not a.no_render, mapping, a.guidelines, a.fonts, a.reference)
    except (ImportError_, px.PptxError, sc.ShowcaseError) as e:
        sys.exit(f"brand_import: {e}")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
