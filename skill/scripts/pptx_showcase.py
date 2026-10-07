#!/usr/bin/env python3
"""Erzeugt aus einer PPTX/POTX ein Showcase-Deck: eine leere Folie pro Layout (nur Standardbibliothek).

Eine leere Folie zeigt beim Export (PowerPoint, LibreOffice) nur die Grafiken von Layout und Master
(Logo, Linien, Verläufe, Hintergründe), keine Platzhalter. Daraus entstehen die Hintergründe des Brands.

  pptx_showcase.py <vorlage.pptx> <showcase.pptx> [--filled]

--filled setzt Beispieltext in die Textplatzhalter (Referenz für den Vergleich mit dem Marp-Ergebnis).
"""
import posixpath, re, sys, zipfile
from pathlib import Path

HDR = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
SLIDE = (HDR + f'<p:sld {NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
         '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
         '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
REL_T = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Beispieltexte der gefüllten Variante; der Brand-Vorschau-Deck nutzt dieselben Texte (Vergleich Original ↔ Marp).
SAMPLE = {
    "title": "Beispieltitel der Folie",
    "subtitle": "Untertitel mit etwas mehr Text",
    "body": ["Erster Punkt der Liste", "Zweiter Punkt mit etwas längerem Text", "Dritter Punkt"],
    "date": "01.01.2026",
    "footer": "Fußzeile",
}
PH_ROLE = {"title": "title", "ctrTitle": "title", "subTitle": "subtitle", "dt": "date", "ftr": "footer", "sldNum": "number",
           "body": "body", "obj": "body", None: "body"}
SKIP_TYPES = {"pic", "chart", "tbl", "media", "clipArt", "dgm"}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def filled_slide(layout_xml):
    """Folie mit Beispieltext in allen Textplatzhaltern des Layouts (Formatierung kommt aus dem Layout)."""
    import re as _re
    shapes, sid = [], 2
    for m in _re.finditer(r"<p:sp>.*?</p:sp>", layout_xml, flags=_re.S):
        ph = _re.search(r"<p:ph([^>]*)/?>", m.group(0))
        if not ph:
            continue
        typ = _re.search(r'type="([^"]+)"', ph.group(1))
        idx = _re.search(r'idx="([^"]+)"', ph.group(1))
        typ = typ.group(1) if typ else None
        if typ in SKIP_TYPES:
            continue
        role = PH_ROLE.get(typ, "body")
        attrs = (f' type="{typ}"' if typ else "") + (f' idx="{idx.group(1)}"' if idx else "")
        if role == "number":
            para = '<a:p><a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr lang="de-DE"/><a:t>‹#›</a:t></a:fld></a:p>'
        elif role == "body":
            para = "".join(f'<a:p><a:r><a:rPr lang="de-DE"/><a:t>{esc(t)}</a:t></a:r></a:p>' for t in SAMPLE["body"])
        else:
            para = f'<a:p><a:r><a:rPr lang="de-DE"/><a:t>{esc(SAMPLE[role])}</a:t></a:r></a:p>'
        shapes.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="ph{sid}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
                      f'<p:nvPr><p:ph{attrs}/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{para}</p:txBody></p:sp>')
        sid += 1
    return SLIDE.replace("</p:spTree>", "".join(shapes) + "</p:spTree>")


class ShowcaseError(Exception):
    pass


def layout_order(z):
    """Layouts in der Reihenfolge, in der pptx_extract sie liefert (Master für Master)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pptx_extract as px
    pkg = px.Package.__new__(px.Package)
    pkg.z, pkg.names, pkg.media_bytes = z, {i.filename for i in z.infolist()}, 0
    pres = pkg.xml("ppt/presentation.xml")
    pres_rels = pkg.rels("ppt/presentation.xml")
    out = []
    for m in px.findall(pres, "p:sldMasterIdLst/p:sldMasterId"):
        mf = pres_rels[m.get("{%s}id" % px.NS["r"])][0]
        mrels = pkg.rels(mf)
        mroot = pkg.xml(mf)
        for lid in px.findall(mroot, "p:sldLayoutIdLst/p:sldLayoutId"):
            out.append(mrels[lid.get("{%s}id" % px.NS["r"])][0])
    return out


def insert_sld_id_lst(pres, ids):
    """Fügt <sldIdLst> an der schemakonformen Stelle ein. ids: Liste von (id, rId).

    Reihenfolge laut Schema: sldMasterIdLst, notesMasterIdLst, handoutMasterIdLst, sldIdLst, sldSz.
    Maßgeblich ist das LETZTE der vorangehenden Elemente (nicht das erste Treffer-Tag im Text).
    Das Namensraum-Präfix wird aus dem Dokument übernommen, und r: wird an den neuen Elementen selbst
    deklariert (manche Generatoren deklarieren xmlns:r nur lokal an einzelnen Elementen).
    """
    pm = re.search(r"<((?:[A-Za-z_][\w.-]*:)?)sldMasterIdLst[\s>/]", pres)
    if not pm:
        raise ShowcaseError("presentation.xml: sldMasterIdLst fehlt")
    pfx = pm.group(1)
    ends = [m.end() for tag in ("handoutMasterIdLst", "notesMasterIdLst", "sldMasterIdLst")
            for m in re.finditer(rf"</{re.escape(pfx)}{tag}>", pres)]
    if not ends:
        raise ShowcaseError("presentation.xml: sldMasterIdLst nicht geschlossen")
    body = "".join(f'<{pfx}sldId id="{i}" r:id="{rid}" xmlns:r="{REL_T}"/>' for i, rid in ids)
    at = max(ends)
    return pres[:at] + f"<{pfx}sldIdLst>{body}</{pfx}sldIdLst>" + pres[at:]


MAX_ENTRIES = 5000
MAX_BYTES = 256 * 1024 * 1024
DROP_PREFIXES = ("ppt/slides/", "ppt/notesSlides/", "ppt/comments/", "ppt/commentAuthors", "ppt/authors", "docProps/thumbnail")
DROP_REL_TYPE = re.compile(r'<Relationship [^>]*Type="[^"]*/(slide|commentAuthors|authors|thumbnail)"[^>]*/>')


def rel_targets(part, rels_xml):
    """Interne Ziele einer .rels-Datei als absolute Paketpfade."""
    base = posixpath.dirname(part)
    out = []
    for m in re.finditer(r"<Relationship\s[^>]*>", rels_xml):
        tag = m.group(0)
        if re.search(r'TargetMode="External"', tag):
            continue
        t = re.search(r'Target="([^"]*)"', tag)
        if not t:
            continue
        target = t.group(1)
        out.append(target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(base, target)))
    return out


def rels_name(part):
    d, f = posixpath.split(part)
    return posixpath.join(d, "_rels", f + ".rels")


def source_of(rels):
    """Teil, zu dem eine .rels-Datei gehört ('_rels/.rels' → Paketstamm '')."""
    d, f = posixpath.split(rels)
    return "" if f == ".rels" else posixpath.join(posixpath.dirname(d), f[:-5])


def reachable(parts):
    """Alle Teile, die vom Paketstamm (_rels/.rels) aus erreichbar sind. Alles andere (Medien, Einbettungen, Diagramme,
    die nur von entfernten Folien genutzt wurden) fällt weg."""
    keep, queue = {"[Content_Types].xml", "_rels/.rels"}, ["_rels/.rels"]
    while queue:
        rels = queue.pop()
        for target in rel_targets(source_of(rels), parts[rels].decode("utf-8", "replace")):
            if target in parts and target not in keep:
                keep.add(target)
                r = rels_name(target)
                if r in parts and r not in keep:
                    keep.add(r)
                    queue.append(r)
    return keep


def build(src, dst, filled=False):
    src, dst = Path(src), Path(dst)
    with zipfile.ZipFile(src) as zin:
        infos = [i for i in zin.infolist() if not i.is_dir()]
        if len(infos) > MAX_ENTRIES:
            raise ShowcaseError(f"zu viele Einträge im Paket ({len(infos)} > {MAX_ENTRIES})")
        if sum(i.file_size for i in infos) > MAX_BYTES:
            raise ShowcaseError("Paket ist entpackt zu groß")
        layouts = layout_order(zin)
        if not layouts:
            raise ShowcaseError("keine Layouts gefunden")
        parts = {i.filename: zin.read(i.filename) for i in infos}

    # Folien, Notizen, Kommentare, Vorschaubild und die zugehörigen Beziehungen entfernen
    parts = {n: d for n, d in parts.items()
             if not n.startswith(DROP_PREFIXES) and not re.match(r"ppt/(slides|notesSlides|comments)/_rels/", n)}
    for n in ("ppt/_rels/presentation.xml.rels", "_rels/.rels"):
        if n in parts:
            parts[n] = DROP_REL_TYPE.sub("", parts[n].decode("utf-8")).encode("utf-8")
    if "docProps/app.xml" in parts:      # enthält die Folientitel (TitlesOfParts)
        app = parts["docProps/app.xml"].decode("utf-8")
        app = re.sub(r"<(?:\w+:)?HeadingPairs>.*?</(?:\w+:)?HeadingPairs>|<(?:\w+:)?TitlesOfParts>.*?</(?:\w+:)?TitlesOfParts>", "", app, flags=re.S)
        parts["docProps/app.xml"] = app.encode("utf-8")

    pres = parts["ppt/presentation.xml"].decode("utf-8")
    prels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    ctypes = parts["[Content_Types].xml"].decode("utf-8")
    pres = re.sub(r"<(?:\w+:)?sldIdLst>.*?</(?:\w+:)?sldIdLst>|<(?:\w+:)?sldIdLst/>", "", pres, flags=re.S)
    used = {int(i) for i in re.findall(r'Id="rId(\d+)"', prels)}
    nxt = max(used | {0}) + 1
    ids, new_rels, new_ct = [], [], []
    for k, lay in enumerate(layouts, start=1):
        rid = f"rId{nxt}"; nxt += 1
        ids.append((255 + k, rid))
        new_rels.append(f'<Relationship Id="{rid}" Type="{REL_T}/slide" Target="slides/slide{k}.xml"/>')
        new_ct.append(f'<Override PartName="/ppt/slides/slide{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
        parts[f"ppt/slides/slide{k}.xml"] = (filled_slide(parts[lay].decode("utf-8")) if filled else SLIDE).encode("utf-8")
        parts[f"ppt/slides/_rels/slide{k}.xml.rels"] = (HDR + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                                        f'<Relationship Id="rId1" Type="{REL_T}/slideLayout" Target="{posixpath.relpath(lay, "ppt/slides")}"/>'
                                                        '</Relationships>').encode("utf-8")
    parts["ppt/presentation.xml"] = insert_sld_id_lst(pres, ids).encode("utf-8")
    parts["ppt/_rels/presentation.xml.rels"] = prels.replace("</Relationships>", "".join(new_rels) + "</Relationships>").encode("utf-8")
    ctypes = re.sub(r'<Override [^>]*PartName="/(?:ppt/(?:slides|notesSlides|comments)/|ppt/commentAuthors|ppt/authors|docProps/thumbnail)[^"]*"[^>]*/>', "", ctypes)
    parts["[Content_Types].xml"] = ctypes.replace("</Types>", "".join(new_ct) + "</Types>").encode("utf-8")

    # Alles entfernen, was vom Paketstamm aus nicht mehr erreichbar ist (verwaiste Medien, Einbettungen, Diagramme …)
    keep = reachable(parts)
    parts = {n: d for n, d in parts.items() if n in keep}
    ct = parts["[Content_Types].xml"].decode("utf-8")
    ct = re.sub(r'<Override [^>]*PartName="/([^"]+)"[^>]*/>', lambda m: m.group(0) if m.group(1) in parts else "", ct)
    parts["[Content_Types].xml"] = ct.encode("utf-8")

    dst.parent.mkdir(parents=True, exist_ok=True)
    order = ["[Content_Types].xml"] + [n for n in parts if n != "[Content_Types].xml"]
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in order:
            zout.writestr(n, parts[n])
    return len(layouts)


def main():
    args = [a for a in sys.argv[1:] if a != "--filled"]
    if len(args) != 2:
        sys.exit(__doc__)
    try:
        n = build(args[0], args[1], filled="--filled" in sys.argv)
    except (ShowcaseError, KeyError, zipfile.BadZipFile) as e:
        sys.exit(f"pptx_showcase: {e}")
    print(f"{args[1]}: {n} Folien (eine pro Layout)")


if __name__ == "__main__":
    main()
