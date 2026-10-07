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


def build(src, dst, filled=False):
    src, dst = Path(src), Path(dst)
    with zipfile.ZipFile(src) as zin:
        layouts = layout_order(zin)
        if not layouts:
            raise ShowcaseError("keine Layouts gefunden")
        names = [i.filename for i in zin.infolist()]
        drop = {n for n in names if n.startswith(("ppt/slides/", "ppt/notesSlides/"))}
        pres = zin.read("ppt/presentation.xml").decode("utf-8")
        prels = zin.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
        ctypes = zin.read("[Content_Types].xml").decode("utf-8")

        # vorhandene Folien (und deren Notizen) entfernen
        prels = re.sub(r'<Relationship [^>]*Type="[^"]*/relationships/slide"[^>]*/>', "", prels)
        ctypes = re.sub(r'<Override [^>]*PartName="/ppt/(slides|notesSlides)/[^"]*"[^>]*/>', "", ctypes)
        pres = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>|<p:sldIdLst/>", "", pres, flags=re.S)

        used = {int(i) for i in re.findall(r'Id="rId(\d+)"', prels)}
        nxt = max(used | {0}) + 1
        ids, new_rels, new_ct = [], [], []
        for k, lay in enumerate(layouts, start=1):
            rid = f"rId{nxt}"; nxt += 1
            ids.append((255 + k, rid))
            new_rels.append(f'<Relationship Id="{rid}" Type="{REL_T}/slide" Target="slides/slide{k}.xml"/>')
            new_ct.append(f'<Override PartName="/ppt/slides/slide{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
        pres = insert_sld_id_lst(pres, ids)
        prels = prels.replace("</Relationships>", "".join(new_rels) + "</Relationships>")
        ctypes = ctypes.replace("</Types>", "".join(new_ct) + "</Types>")

        dst.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                n = info.filename
                if n in drop or re.match(r"ppt/(slides|notesSlides)/_rels/", n):
                    continue
                data = zin.read(n)
                if n == "ppt/presentation.xml":
                    data = pres.encode("utf-8")
                elif n == "ppt/_rels/presentation.xml.rels":
                    data = prels.encode("utf-8")
                elif n == "[Content_Types].xml":
                    data = ctypes.encode("utf-8")
                # Name statt ZipInfo: writestr(info, …) würde den Header-Offset des Quell-Eintrags überschreiben.
                zout.writestr(n, data)
            for k, lay in enumerate(layouts, start=1):
                zout.writestr(f"ppt/slides/slide{k}.xml", filled_slide(zin.read(lay).decode("utf-8")) if filled else SLIDE)
                target = posixpath.relpath(lay, "ppt/slides")
                zout.writestr(f"ppt/slides/_rels/slide{k}.xml.rels", HDR +
                              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                              f'<Relationship Id="rId1" Type="{REL_T}/slideLayout" Target="{target}"/></Relationships>')
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
