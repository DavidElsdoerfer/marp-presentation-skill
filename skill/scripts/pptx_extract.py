#!/usr/bin/env python3
"""Liest Folienmaster, Layouts und Theme aus einer .pptx/.potx (nur Standardbibliothek).

Es werden nur Master, Layouts und Theme gelesen, nie Folieninhalt (Vorlagen enthalten oft
vertrauliche Beispieltexte). Ergebnis: ein JSON-fähiges dict, siehe extract().

CLI:  pptx_extract.py <datei.pptx> [--json]
"""
import colorsys, json, posixpath, re, sys, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
R_EMBED = "{%s}embed" % NS["r"]
EMU_PER_PT = 12700
MAX_XML = 8 * 1024 * 1024      # Schutz gegen übergroße XML-Teile
MAX_ENTRIES = 5000             # Schutz gegen Zip-Bomben (Anzahl Einträge)
MAX_MEDIA = 64 * 1024 * 1024   # Gesamtgröße eingelesener Medien

PRST_COLORS = {"black": "000000", "white": "ffffff", "red": "ff0000", "green": "008000", "blue": "0000ff",
               "yellow": "ffff00", "gray": "808080", "grey": "808080", "orange": "ffa500"}
SCHEME_FALLBACK = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}


class PptxError(Exception):
    pass


HEX6 = re.compile(r"^[0-9a-fA-F]{6}$")
FONT_BAD = re.compile(r"[^\w .+\-]", re.UNICODE)
NAME_BAD = re.compile(r"[\x00-\x1f\x7f<>&\"'`*/\\\[\]{}()$#@|]")


def safe_hex(val, default="000000"):
    """Farbwerte aus der Datei: nur genau sechs Hexziffern (sonst landet Fremdtext in tokens.css)."""
    return val if isinstance(val, str) and HEX6.match(val) else default


def safe_font(name):
    """Schriftnamen: nur Buchstaben, Ziffern, Leerzeichen, . + - (sonst CSS-Injektion über font-family)."""
    if not isinstance(name, str):
        return None
    cleaned = FONT_BAD.sub("", name).strip()[:80]
    return cleaned or None


def safe_text(name, fallback="Layout"):
    """Namen aus der Datei für Markdown/CSS-Kommentare/Doku: Steuer- und Markup-Zeichen entfernen."""
    cleaned = NAME_BAD.sub("", re.sub(r"\s+", " ", name or "")).strip()[:80]
    return cleaned or fallback


def q(tag):
    pfx, name = tag.split(":")
    return "{%s}%s" % (NS[pfx], name)


def find(el, path):
    return el.find(path, NS) if el is not None else None


def findall(el, path):
    return el.findall(path, NS) if el is not None else []


def find_first(el, *paths):
    """Erstes vorhandenes Element. Nicht `a or b` nutzen: leere Elemente (z. B. <p:ph/>) gelten als falsch."""
    for path in paths:
        r = find(el, path)
        if r is not None:
            return r
    return None


class Package:
    """Dünner, abgesicherter Zugriff auf das ZIP-Paket."""

    def __init__(self, path):
        try:
            self.z = zipfile.ZipFile(path)
        except zipfile.BadZipFile as e:
            raise PptxError(f"{path}: keine gültige PPTX/ZIP-Datei") from e
        infos = self.z.infolist()
        if len(infos) > MAX_ENTRIES:
            raise PptxError("zu viele Einträge im Paket")
        self.names = {i.filename for i in infos}
        self.media_bytes = 0

    def xml(self, name):
        name = name.lstrip("/")
        if name not in self.names:
            return None
        info = self.z.getinfo(name)
        if info.file_size > MAX_XML:
            raise PptxError(f"{name}: XML zu groß")
        # defusedxml ist nicht in der Standardbibliothek; Pythons expat löst keine externen Entitäten auf und begrenzt die
        # Erweiterung interner Entitäten (XML-Bomben). Fehler werden hier in eine verständliche Meldung übersetzt.
        try:
            return ET.fromstring(self.z.read(name))
        except ET.ParseError as e:
            raise PptxError(f"{name}: kein gültiges XML ({e})") from e

    def read(self, name):
        name = name.lstrip("/")
        info = self.z.getinfo(name)
        self.media_bytes += info.file_size
        if self.media_bytes > MAX_MEDIA:
            raise PptxError("Medien zu groß")
        return self.z.read(name)

    def rels(self, part):
        """Relationen eines Teils: {rId: absoluter Zielpfad im Paket}."""
        d, f = posixpath.split(part.lstrip("/"))
        relname = posixpath.join(d, "_rels", f + ".rels")
        root = self.xml(relname)
        out = {}
        for r in findall(root, "rel:Relationship"):
            if r.get("TargetMode") == "External":
                continue
            target = r.get("Target")
            tgt = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(d, target))
            out[r.get("Id")] = (tgt, r.get("Type", "").rsplit("/", 1)[-1])
        return out


# ── Farben ─────────────────────────────────────────────────────────────────

def clamp(v):
    return max(0.0, min(1.0, v))


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(clamp(c) * 255):02x}" for c in rgb)


def apply_mods(hexcolor, node):
    """Wendet die gängigen Farbmodifikatoren (lumMod, lumOff, tint, shade, alpha) an. -> (hex, alpha|None)"""
    rgb = hex_to_rgb(hexcolor)
    alpha = None
    for m in list(node):
        tag = m.tag.split("}")[1]
        val = m.get("val")
        if val is None:
            continue
        v = int(val) / 100000
        if tag in ("lumMod", "lumOff"):
            h, l, s = colorsys.rgb_to_hls(*rgb)
            l = clamp(l * v) if tag == "lumMod" else clamp(l + v)
            rgb = colorsys.hls_to_rgb(h, l, s)
        elif tag == "tint":      # Richtung Weiß
            rgb = tuple(clamp(c * v + (1 - v)) for c in rgb)
        elif tag == "shade":     # Richtung Schwarz
            rgb = tuple(clamp(c * v) for c in rgb)
        elif tag == "alpha":
            alpha = v
    return rgb_to_hex(rgb), alpha


class Theme:
    def __init__(self, root):
        self.colors, self.fonts = {}, {}
        cs = find(root, "a:themeElements/a:clrScheme")
        for el in list(cs) if cs is not None else []:
            name = el.tag.split("}")[1]
            child = list(el)[0] if len(el) else None
            if child is None:
                continue
            if child.tag.endswith("srgbClr"):
                self.colors[name] = "#" + safe_hex(child.get("val")).lower()
            elif child.tag.endswith("sysClr"):
                self.colors[name] = "#" + safe_hex(child.get("lastClr")).lower()
        fs = find(root, "a:themeElements/a:fontScheme")
        for kind in ("major", "minor"):
            latin = find(fs, f"a:{kind}Font/a:latin")
            self.fonts[kind] = safe_font(latin.get("typeface")) if latin is not None else None
        self.fmt_bg = [list(e) for e in findall(root, "a:themeElements/a:fmtScheme/a:bgFillStyleLst")]


def color_of(el, theme, clrmap):
    """Löst ein Farb-Element (srgbClr/schemeClr/sysClr/prstClr) auf. -> {"hex", "alpha"} oder None"""
    if el is None:
        return None
    tag = el.tag.split("}")[1]
    hexc = None
    if tag == "srgbClr":
        hexc = "#" + safe_hex(el.get("val")).lower()
    elif tag == "sysClr":
        hexc = "#" + safe_hex(el.get("lastClr")).lower()
    elif tag == "prstClr":
        hexc = "#" + PRST_COLORS.get(el.get("val", ""), "000000")
    elif tag == "schemeClr":
        name = el.get("val")
        mapped = clrmap.get(name, name) if clrmap else name
        mapped = SCHEME_FALLBACK.get(mapped, mapped)
        hexc = theme.colors.get(mapped) or theme.colors.get(SCHEME_FALLBACK.get(name, name))
        if name == "phClr":
            return {"hex": None, "alpha": None, "placeholder_color": True}
    if hexc is None:
        return None
    hexc, alpha = apply_mods(hexc, el)
    return {"hex": hexc, "alpha": alpha}


def fill_of(sppr, theme, clrmap, rels=None):
    """Füllung eines spPr/bgPr: solid, gradient, image, none."""
    if sppr is None:
        return None
    if find(sppr, "a:noFill") is not None:
        return {"type": "none"}
    sf = find(sppr, "a:solidFill")
    if sf is not None and len(sf):
        c = color_of(list(sf)[0], theme, clrmap)
        return {"type": "solid", **c} if c else None
    gf = find(sppr, "a:gradFill")
    if gf is not None:
        stops = []
        for gs in findall(gf, "a:gsLst/a:gs"):
            c = color_of(list(gs)[0], theme, clrmap) if len(gs) else None
            if c and c.get("hex"):
                stops.append({"pos": int(gs.get("pos", "0")) / 100000, **c})
        lin = find(gf, "a:lin")
        angle = int(lin.get("ang", "0")) / 60000 if lin is not None else 90.0
        return {"type": "gradient", "stops": stops, "angle": angle,
                "kind": "radial" if find(gf, "a:path") is not None else "linear"}
    bf = find(sppr, "a:blipFill")
    if bf is not None:
        blip = find(bf, "a:blip")
        rid = blip.get(R_EMBED) if blip is not None else None
        target = rels.get(rid, (None,))[0] if rels and rid else None
        return {"type": "image", "image": target, "tile": find(bf, "a:tile") is not None}
    return None


# ── Geometrie, Text ────────────────────────────────────────────────────────

class Slide:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def frac(self, x, y, cx, cy):
        return {"x": x / self.w, "y": y / self.h, "w": cx / self.w, "h": cy / self.h}


def xfrm_of(sppr):
    xf = find(sppr, "a:xfrm")
    if xf is None:
        return None
    off, ext = find(xf, "a:off"), find(xf, "a:ext")
    if off is None or ext is None:
        return None
    return {"x": int(off.get("x", 0)), "y": int(off.get("y", 0)), "cx": int(ext.get("cx", 0)),
            "cy": int(ext.get("cy", 0)), "rot": int(xf.get("rot", 0)) / 60000,
            "flipH": xf.get("flipH") == "1", "flipV": xf.get("flipV") == "1"}


def font_name(face, theme):
    """Löst Theme-Verweise (+mj-lt, +mn-lt, +mj-ea …) in Schriftnamen auf."""
    if face and face.startswith("+mj"):
        return theme.fonts.get("major")
    if face and face.startswith("+mn"):
        return theme.fonts.get("minor")
    return safe_font(face)


def lvl1_props(lststyle, theme, clrmap):
    """Schrift/Absatz von Ebene 1 aus einem lstStyle-Element."""
    lv = find(lststyle, "a:lvl1pPr")
    if lv is None:
        return {}
    out = {}
    if lv.get("algn"):
        out["align"] = lv.get("algn")
    d = find(lv, "a:defRPr")
    if d is not None:
        if d.get("sz"):
            out["size_pt"] = int(d.get("sz")) / 100
        if d.get("b") is not None:
            out["bold"] = d.get("b") == "1"
        if d.get("i") is not None:
            out["italic"] = d.get("i") == "1"
        if d.get("cap"):
            out["caps"] = d.get("cap")
        sf = find(d, "a:solidFill")
        if sf is not None and len(sf):
            c = color_of(list(sf)[0], theme, clrmap)
            if c and c.get("hex"):
                out["color"] = c["hex"]
        lat = find(d, "a:latin")
        if lat is not None and lat.get("typeface"):
            out["font"] = font_name(lat.get("typeface"), theme)
    return out


def first_run_props(txbody, theme, clrmap):
    """Schrift aus den Runs/Absätzen eines Textkörpers (für statische Textfelder)."""
    out = {}
    for rpr in findall(txbody, ".//a:rPr"):
        if rpr.get("sz"):
            out["size_pt"] = int(rpr.get("sz")) / 100
        if rpr.get("b") is not None:
            out["bold"] = rpr.get("b") == "1"
        sf = find(rpr, "a:solidFill")
        if sf is not None and len(sf):
            c = color_of(list(sf)[0], theme, clrmap)
            if c and c.get("hex"):
                out["color"] = c["hex"]
        lat = find(rpr, "a:latin")
        if lat is not None and lat.get("typeface"):
            out["font"] = font_name(lat.get("typeface"), theme)
        break
    return out


def para_props(txbody, theme, clrmap):
    """Stil der ersten Beispielzeile eines Platzhalters (Ausrichtung, Schrift, Größe).

    PowerPoint legt Stile in lstStyle/txStyles ab; manche Generatoren (z. B. LibreOffice) schreiben sie
    stattdessen in die Beispielzeile (rPr, endParaRPr). Dient daher nur als Rückfall mit niedriger Priorität.
    """
    para = find(txbody, "a:p")
    if para is None:
        return {}
    out = {}
    ppr = find(para, "a:pPr")
    # Ausrichtung (pPr@algn) bleibt außen vor: LibreOffice schreibt sie in Beispielzeilen, rendert aber anders;
    # maßgeblich ist lstStyle/txStyles.
    # endParaRPr bleibt bewusst außen vor: es formatiert nur das Absatzende leerer Absätze, keinen Text.
    rpr = find_first(para, "a:r/a:rPr")
    if rpr is None:
        rpr = find(ppr, "a:defRPr")
    if rpr is None:
        return out
    if rpr.get("sz"):
        out["size_pt"] = int(rpr.get("sz")) / 100
    if rpr.get("b") is not None:
        out["bold"] = rpr.get("b") == "1"
    if rpr.get("i") is not None:
        out["italic"] = rpr.get("i") == "1"
    if rpr.get("cap") and rpr.get("cap") != "none":
        out["caps"] = rpr.get("cap")
    sf = find(rpr, "a:solidFill")
    if sf is not None and len(sf):
        c = color_of(list(sf)[0], theme, clrmap)
        if c and c.get("hex"):
            out["color"] = c["hex"]
    lat = find(rpr, "a:latin")
    if lat is not None and lat.get("typeface"):
        out["font"] = font_name(lat.get("typeface"), theme)
    return out


def text_of(txbody):
    paras = []
    for p in findall(txbody, "a:p"):
        s = "".join((t.text or "") for t in findall(p, "a:r/a:t"))
        paras.append(s)
    return "\n".join(paras).strip()


def body_props(txbody):
    """Nur explizit gesetzte Eigenschaften (Anker, Innenabstände); alles andere wird geerbt bzw. hat Standardwerte."""
    bp = find(txbody, "a:bodyPr")
    out = {}
    if bp is None:
        return out
    if bp.get("anchor"):
        out["anchor"] = bp.get("anchor")
    ins = {k: int(bp.get(k)) / EMU_PER_PT for k in ("lIns", "tIns", "rIns", "bIns") if bp.get(k) is not None}
    if ins:
        out["insets"] = ins
    return out


# Office-Standardgrößen, wenn weder lstStyle noch txStyles etwas festlegen
DEFAULT_STYLE = {"title": {"size_pt": 44.0}, "subtitle": {"size_pt": 32.0}, "body": {"size_pt": 32.0},
                 "date": {"size_pt": 12.0}, "footer": {"size_pt": 12.0}, "number": {"size_pt": 12.0}}

PH_CLASS = {"title": "title", "ctrTitle": "title", "subTitle": "subtitle", "body": "body", "obj": "body",
            "dt": "date", "ftr": "footer", "sldNum": "number", "pic": "picture", "chart": "chart", "tbl": "table",
            "media": "media", "clipArt": "picture", "dgm": "diagram"}


def ph_role(ph):
    t = ph.get("type")
    if t is None:
        return "body"
    return PH_CLASS.get(t, t)


def parse_shapes(tree, ctx, group_tf=None):
    """Flache Liste der Formen eines spTree; Gruppen werden mit ihrer Transformation aufgelöst."""
    shapes = []
    for el in list(tree):
        tag = el.tag.split("}")[1]
        if tag == "grpSp":
            gp = find(el, "p:grpSpPr")
            xf = find(gp, "a:xfrm")
            tf = None
            if xf is not None and find(xf, "a:off") is not None and find(xf, "a:chOff") is not None:
                off, ext = find(xf, "a:off"), find(xf, "a:ext")
                co, ce = find(xf, "a:chOff"), find(xf, "a:chExt")
                cw, ch = int(ce.get("cx")) or 1, int(ce.get("cy")) or 1
                tf = {"ox": int(off.get("x")), "oy": int(off.get("y")), "sx": int(ext.get("cx")) / cw,
                      "sy": int(ext.get("cy")) / ch, "cx": int(co.get("x")), "cy": int(co.get("y"))}
            shapes += parse_shapes(el, ctx, compose(group_tf, tf))
            continue
        if tag not in ("sp", "pic", "cxnSp"):
            continue
        sppr = find(el, "p:spPr")
        nv = find_first(el, "p:nvSpPr/p:cNvPr", "p:nvPicPr/p:cNvPr", "p:nvCxnSpPr/p:cNvPr")
        ph = find_first(el, "p:nvSpPr/p:nvPr/p:ph", "p:nvPicPr/p:nvPr/p:ph")
        xf = xfrm_of(sppr)
        if xf and group_tf:
            xf = apply_group(xf, group_tf)
        shape = {"kind": {"sp": "shape", "pic": "picture", "cxnSp": "line"}[tag],
                 "name": nv.get("name") if nv is not None else "", "xfrm": xf}
        if ph is not None:
            shape["kind"] = "placeholder"
            shape["ph"] = {"type": ph.get("type"), "idx": ph.get("idx"), "role": ph_role(ph)}
        if tag == "pic":
            blip = find(el, "p:blipFill/a:blip")
            rid = blip.get(R_EMBED) if blip is not None else None
            shape["image"] = ctx["rels"].get(rid, (None,))[0] if rid else None
        else:
            f = fill_of(sppr, ctx["theme"], ctx["clrmap"], ctx["rels"])
            if f:
                shape["fill"] = f
            geom = find(sppr, "a:prstGeom")
            shape["geom"] = geom.get("prst") if geom is not None else ("custom" if find(sppr, "a:custGeom") is not None else None)
        ln = find(sppr, "a:ln")
        if ln is not None:
            lf = fill_of(ln, ctx["theme"], ctx["clrmap"])
            if lf and lf.get("type") == "solid":
                shape["line"] = {"hex": lf["hex"], "w_pt": int(ln.get("w", 12700)) / EMU_PER_PT}
        tx = find(el, "p:txBody")
        if tx is not None:
            props = {}
            props.update(lvl1_props(find(tx, "a:lstStyle"), ctx["theme"], ctx["clrmap"]))
            if shape["kind"] != "placeholder":
                props.update(first_run_props(tx, ctx["theme"], ctx["clrmap"]))
            shape["text_props"] = props
            if shape["kind"] == "placeholder":
                shape["sample_props"] = para_props(tx, ctx["theme"], ctx["clrmap"])
                shape["sample_present"] = find(tx, "a:p") is not None
            shape["body"] = body_props(tx)
            if shape["kind"] != "placeholder":
                t = text_of(tx)
                if t:
                    shape["text"] = t
        shapes.append(shape)
    return shapes


def compose(outer, inner):
    if inner is None:
        return outer
    if outer is None:
        return inner
    # verschachtelte Gruppen: innere Transformation in den Raum der äußeren abbilden
    return {"ox": outer["ox"] + (inner["ox"] - outer["cx"]) * outer["sx"], "oy": outer["oy"] + (inner["oy"] - outer["cy"]) * outer["sy"],
            "sx": inner["sx"] * outer["sx"], "sy": inner["sy"] * outer["sy"], "cx": inner["cx"], "cy": inner["cy"]}


def apply_group(xf, tf):
    return {**xf, "x": round(tf["ox"] + (xf["x"] - tf["cx"]) * tf["sx"]), "y": round(tf["oy"] + (xf["y"] - tf["cy"]) * tf["sy"]),
            "cx": round(xf["cx"] * tf["sx"]), "cy": round(xf["cy"] * tf["sy"])}


def bg_of(root, ctx):
    bg = find(root, "p:cSld/p:bg")
    if bg is None:
        return None
    pr = find(bg, "p:bgPr")
    if pr is not None:
        return fill_of(pr, ctx["theme"], ctx["clrmap"], ctx["rels"])
    ref = find(bg, "p:bgRef")
    if ref is not None and len(ref):
        c = color_of(list(ref)[0], ctx["theme"], ctx["clrmap"])
        if c and c.get("hex"):
            return {"type": "solid", **c, "from_theme_ref": True}
    return None


def clrmap_of(master_root):
    cm = find(master_root, "p:clrMap")
    return dict(cm.attrib) if cm is not None else {}


def text_styles(master_root, theme, clrmap):
    out = {}
    for key, name in (("title", "titleStyle"), ("body", "bodyStyle"), ("other", "otherStyle")):
        out[key] = lvl1_props(find(master_root, f"p:txStyles/p:{name}"), theme, clrmap)
    return out


# ── Hauptfunktion ──────────────────────────────────────────────────────────

def extract(path):
    try:
        return _extract(path)
    except (KeyError, ValueError, AttributeError, IndexError, TypeError) as e:
        raise PptxError(f"Datei hat eine unerwartete Struktur ({type(e).__name__}: {e}) — keine gültige Vorlage?") from e


def _extract(path):
    pkg = Package(path)
    pres = pkg.xml("ppt/presentation.xml")
    if pres is None:
        raise PptxError("ppt/presentation.xml fehlt — keine PowerPoint-Datei")
    sz = find(pres, "p:sldSz")
    w, h = int(sz.get("cx")), int(sz.get("cy"))
    if w <= 0 or h <= 0:
        raise PptxError("ungültige Foliengröße (sldSz)")
    slide = Slide(w, h)
    pres_rels = pkg.rels("ppt/presentation.xml")

    masters, layouts, themes = [], [], {}
    master_files = []
    for m in findall(pres, "p:sldMasterIdLst/p:sldMasterId"):
        tgt = pres_rels.get(m.get("{%s}id" % NS["r"]))
        if tgt:
            master_files.append(tgt[0])
    if not master_files:
        raise PptxError("kein Folienmaster gefunden")

    for mf in master_files:
        mroot = pkg.xml(mf)
        mrels = pkg.rels(mf)
        theme_file = next((t for t, kind in mrels.values() if kind == "theme"), None)
        if theme_file not in themes:
            themes[theme_file] = Theme(pkg.xml(theme_file)) if theme_file else Theme(ET.Element("x"))
        theme = themes[theme_file]
        clrmap = clrmap_of(mroot)
        ctx = {"theme": theme, "clrmap": clrmap, "rels": mrels}
        tree = find(mroot, "p:cSld/p:spTree")
        master = {"file": mf, "theme_file": theme_file, "clrmap": clrmap, "bg": bg_of(mroot, ctx),
                  "shapes": parse_shapes(tree, ctx), "text_styles": text_styles(mroot, theme, clrmap)}
        masters.append(master)
        for lid in findall(mroot, "p:sldLayoutIdLst/p:sldLayoutId"):
            tgt = mrels.get(lid.get("{%s}id" % NS["r"]))
            if not tgt:
                continue
            lf = tgt[0]
            lroot = pkg.xml(lf)
            lrels = pkg.rels(lf)
            lctx = {"theme": theme, "clrmap": clrmap, "rels": lrels}
            cm_over = find(lroot, "p:clrMapOvr/a:overrideClrMapping")
            if cm_over is not None:
                lctx["clrmap"] = dict(cm_over.attrib)
            ltree = find(lroot, "p:cSld/p:spTree")
            layouts.append({
                "file": lf, "name": safe_text(find(lroot, "p:cSld").get("name") or posixpath.basename(lf)),
                "type": lroot.get("type"), "master": len(masters) - 1,
                "show_master_shapes": lroot.get("showMasterSp") != "0",
                "bg": bg_of(lroot, lctx), "shapes": parse_shapes(ltree, lctx)})

    # Geometrie von Platzhaltern aus dem Master erben
    for lay in layouts:
        master = masters[lay["master"]]
        for s in lay["shapes"]:
            if s["kind"] == "placeholder":
                inherit(s, master)
    fonts = themes[masters[0]["theme_file"]].fonts
    colors = themes[masters[0]["theme_file"]].colors
    media = sorted(n for n in pkg.names if n.startswith("ppt/media/"))
    return {"source": Path(path).name, "slide": {"w_emu": w, "h_emu": h, "w_pt": w / EMU_PER_PT, "h_pt": h / EMU_PER_PT,
                                                  "aspect": round(w / h, 4)},
            "theme": {"colors": colors, "fonts": fonts}, "masters": masters, "layouts": layouts, "media": media}


def inherit(shape, master):
    """Fehlende Geometrie und Textstil eines Layout-Platzhalters aus dem Master-Platzhalter übernehmen."""
    ph = shape["ph"]
    cand = [m for m in master["shapes"] if m["kind"] == "placeholder"]
    match = next((m for m in cand if ph["idx"] is not None and m["ph"]["idx"] == ph["idx"] and m["ph"]["role"] == ph["role"]), None)
    if match is None:
        match = next((m for m in cand if m["ph"]["role"] == ph["role"]), None)
    if match is None and ph["role"] == "subtitle":
        match = next((m for m in cand if m["ph"]["role"] == "body"), None)
    if match is None:
        return
    if shape.get("xfrm") is None and match.get("xfrm"):
        shape["xfrm"] = dict(match["xfrm"]); shape["xfrm_inherited"] = True
    kind = "title" if ph["role"] == "title" else "body" if ph["role"] in ("body", "subtitle") else "other"
    merged = dict(master["text_styles"].get(kind, {}))     # niedrigste Priorität: Master-txStyles
    if not shape.get("sample_present"):                    # Beispielzeile nur von EINER Ebene (Layout, sonst Master):
        merged.update(match.get("sample_props", {}))       # sie ist ein Rückfall für Generatoren ohne lstStyle (LibreOffice)
    merged.update(match.get("text_props", {}))             # lstStyle des Master-Platzhalters
    merged.update(shape.get("sample_props", {}))           # Beispielzeile des Layout-Platzhalters
    merged.update(shape.get("text_props", {}))             # lstStyle des Layout-Platzhalters (höchste Priorität)
    for key, val in DEFAULT_STYLE.get(ph["role"], {}).items():   # Office-Standardwerte, wenn die Datei nichts festlegt
        merged.setdefault(key, val)
    shape["text_props"] = merged
    mb, sb = match.get("body") or {}, shape.get("body") or {}
    if mb or sb:
        shape["body"] = {**mb, **sb, **({"insets": {**mb.get("insets", {}), **sb.get("insets", {})}} if (mb.get("insets") or sb.get("insets")) else {})}


def to_fractions(data, shape):
    """Position einer Form als Bruchteile der Folie (0..1)."""
    xf = shape.get("xfrm")
    if not xf:
        return None
    s = Slide(data["slide"]["w_emu"], data["slide"]["h_emu"])
    return s.frac(xf["x"], xf["y"], xf["cx"], xf["cy"])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        data = extract(sys.argv[1])
    except PptxError as e:
        sys.exit(f"pptx_extract: {e}")
    if "--json" in sys.argv:
        print(json.dumps(data, indent=1, ensure_ascii=False))
        return
    print(f"{data['source']}: {data['slide']['w_pt']:.0f}×{data['slide']['h_pt']:.0f} pt (Seitenverhältnis {data['slide']['aspect']})")
    print("Schriften:", data["theme"]["fonts"])
    print("Farben:", ", ".join(f"{k} {v}" for k, v in data["theme"]["colors"].items()))
    print(f"{len(data['masters'])} Master, {len(data['layouts'])} Layouts, {len(data['media'])} Mediendateien")
    for i, l in enumerate(data["layouts"]):
        phs = [f"{s['ph']['role']}" for s in l["shapes"] if s["kind"] == "placeholder"]
        extra = [s["kind"] for s in l["shapes"] if s["kind"] != "placeholder"]
        print(f"  [{i}] {l['name']!r} type={l['type']} Platzhalter={phs} Grafiken={len(extra)}")


if __name__ == "__main__":
    main()
