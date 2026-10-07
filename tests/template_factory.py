"""Erzeugt eine synthetische, lizenzfreie PPTX-Vorlage für Tests (nur Standardbibliothek).

Sechs Layouts: Titelfolie (Verlauf, Master-Grafiken aus), Titel und Inhalt (alles geerbt),
Zwei Inhalte, Abschnitt, Nur Titel, Zitat mit Bild (Gruppe, Bildplatzhalter, lumMod-Farbe).
Farben und Schriften sind bewusst auffällig, damit Tests sie eindeutig wiedererkennen.
"""
import struct, zipfile, zlib
from pathlib import Path

COLORS = {"dk1": "1B1B1B", "lt1": "FFFFFF", "dk2": "0B3D5C", "lt2": "F3EFE6", "accent1": "E4572E",
          "accent2": "17BEBB", "accent3": "FFC914", "accent4": "76B041", "accent5": "2E282A", "accent6": "6A4C93",
          "hlink": "0563C1", "folHlink": "954F72"}
FONT_MAJOR, FONT_MINOR = "Georgia", "Verdana"

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
HDR = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def png(w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class Geo:
    def __init__(self, w=12192000, h=6858000):
        self.w, self.h = w, h

    def xfrm(self, x, y, cx, cy, tag="a:xfrm"):
        return (f'<{tag}><a:off x="{round(x * self.w)}" y="{round(y * self.h)}"/>'
                f'<a:ext cx="{round(cx * self.w)}" cy="{round(cy * self.h)}"/></{tag}>')


def scheme(val, mods=""):
    return f'<a:schemeClr val="{val}">{mods}</a:schemeClr>'


def lst(sz=None, bold=None, color=None, algn=None, caps=None):
    attrs = (f' sz="{sz}"' if sz else "") + (f' b="{int(bold)}"' if bold is not None else "") + (f' cap="{caps}"' if caps else "")
    fill = f"<a:solidFill>{color}</a:solidFill>" if color else ""
    al = f' algn="{algn}"' if algn else ""
    return f'<a:lstStyle><a:lvl1pPr{al}><a:defRPr{attrs}>{fill}</a:defRPr></a:lvl1pPr></a:lstStyle>'


def ph(id_, name, type_=None, idx=None, geo=None, box=None, style="<a:lstStyle/>", anchor=None, text="Text"):
    t = f' type="{type_}"' if type_ else ""
    i = f' idx="{idx}"' if idx is not None else ""
    sppr = f"<p:spPr>{geo.xfrm(*box)}</p:spPr>" if box else "<p:spPr/>"
    a = f' anchor="{anchor}"' if anchor else ""
    para = ('<a:p><a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr lang="de-DE"/><a:t>‹#›</a:t></a:fld></a:p>'
            if type_ == "sldNum" else f'<a:p><a:r><a:rPr lang="de-DE"/><a:t>{text}</a:t></a:r></a:p>')
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{id_}" name="{name}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
            f'<p:nvPr><p:ph{t}{i}/></p:nvPr></p:nvSpPr>{sppr}'
            f'<p:txBody><a:bodyPr{a}/>{style}{para}</p:txBody></p:sp>')


def rect(id_, name, geo, box, fill, prst="rect"):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{id_}" name="{name}"/><p:cNvSpPr/><p:nvPr userDrawn="1"/></p:nvSpPr>'
            f'<p:spPr>{geo.xfrm(*box)}<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>{fill}<a:ln><a:noFill/></a:ln></p:spPr></p:sp>')


def pic(id_, name, geo, box, rid="rId2"):
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="{id_}" name="{name}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
            f'<p:nvPr userDrawn="1"/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr>{geo.xfrm(*box)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def sptree(inner):
    return ('<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            f'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{inner}</p:spTree>')


def solid(color):
    return f"<a:solidFill>{color}</a:solidFill>"


def theme_xml():
    cs = "".join(f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k, v in COLORS.items())
    fills = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3
    lns = '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>' * 3
    return (HDR + f'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Testvorlage"><a:themeElements>'
            f'<a:clrScheme name="Test">{cs}</a:clrScheme>'
            f'<a:fontScheme name="Test"><a:majorFont><a:latin typeface="{FONT_MAJOR}"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
            f'<a:minorFont><a:latin typeface="{FONT_MINOR}"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
            f'<a:fmtScheme name="Test"><a:fillStyleLst>{fills}</a:fillStyleLst><a:lnStyleLst>{lns}</a:lnStyleLst>'
            f'<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>'
            f'<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst>{fills}</a:bgFillStyleLst></a:fmtScheme>'
            f'</a:themeElements></a:theme>')


def build(path, aspect="16:9"):
    geo = Geo(12192000, 6858000) if aspect == "16:9" else Geo(9144000, 6858000)
    bg1, tx2, acc1 = scheme("bg1"), scheme("tx2"), scheme("accent1")

    footers = (ph(20, "Datum", "dt", 10, style=lst(sz=1200, color=scheme("tx1", '<a:lumMod val="60000"/><a:lumOff val="40000"/>')))
               + ph(21, "Fusszeile", "ftr", 11) + ph(22, "Foliennummer", "sldNum", 12))

    master = (HDR + f'<p:sldMaster {NS}><p:cSld><p:bg><p:bgRef idx="1001">{bg1}</p:bgRef></p:bg>' + sptree(
        ph(2, "Titel", "title", geo=geo, box=(0.06, 0.06, 0.70, 0.14), anchor="ctr", text="Titel")
        + ph(3, "Inhalt", "body", 1, geo=geo, box=(0.06, 0.24, 0.88, 0.62), text="Inhalt")
        + ph(4, "Datum", "dt", 10, geo=geo, box=(0.06, 0.92, 0.2, 0.05), text="")
        + ph(5, "Fusszeile", "ftr", 11, geo=geo, box=(0.30, 0.92, 0.4, 0.05), text="")
        + ph(6, "Foliennummer", "sldNum", 12, geo=geo, box=(0.84, 0.92, 0.10, 0.05), text="")
        + pic(7, "Logo", geo, (0.84, 0.04, 0.10, 0.03))
        + rect(8, "Balken", geo, (0, 0.985, 1, 0.015), solid(acc1)))
        + '</p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
        'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst>' + "".join(f'<p:sldLayoutId id="{2147483649 + i}" r:id="rId{i + 3}"/>' for i in range(6)) + '</p:sldLayoutIdLst>'
        '<p:txStyles><p:titleStyle><a:lvl1pPr algn="l"><a:defRPr sz="3200" b="1"><a:solidFill>' + tx2 + '</a:solidFill>'
        '<a:latin typeface="+mj-lt"/></a:defRPr></a:lvl1pPr></p:titleStyle>'
        '<p:bodyStyle><a:lvl1pPr algn="l"><a:defRPr sz="2000"><a:solidFill>' + scheme("tx1") + '</a:solidFill>'
        '<a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></p:bodyStyle>'
        '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1200"/></a:lvl1pPr></p:otherStyle></p:txStyles></p:sldMaster>')

    def layout(name, type_, shapes, bg="", show_master=True):
        sm = "" if show_master else ' showMasterSp="0"'
        return (HDR + f'<p:sldLayout {NS} type="{type_}" preserve="1"{sm}><p:cSld name="{name}">{bg}{sptree(shapes)}</p:cSld>'
                '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')

    grad = (f'<p:bg><p:bgPr><a:gradFill><a:gsLst><a:gs pos="0">{scheme("tx2")}</a:gs><a:gs pos="100000">{acc1}</a:gs></a:gsLst>'
            '<a:lin ang="2700000" scaled="0"/></a:gradFill><a:effectLst/></p:bgPr></p:bg>')
    sec_bg = f'<p:bg><p:bgPr>{solid(scheme("accent2"))}<a:effectLst/></p:bgPr></p:bg>'
    layouts = [
        layout("Titelfolie", "title",
               pic(2, "Logo", geo, (0.06, 0.08, 0.20, 0.06))
               + ph(3, "Titel", "ctrTitle", geo=geo, box=(0.06, 0.35, 0.80, 0.20), anchor="b",
                    style=lst(sz=5400, bold=1, color=bg1, algn="l"), text="Titel")
               + rect(4, "Akzent", geo, (0.06, 0.565, 0.10, 0.006), solid(scheme("accent3")))
               + ph(5, "Untertitel", "subTitle", 1, geo=geo, box=(0.06, 0.58, 0.80, 0.10),
                    style=lst(sz=2400, color=scheme("accent3"), algn="l"), text="Untertitel"), bg=grad, show_master=False),
        layout("Titel und Inhalt", "obj", ph(2, "Titel", "title", text="Titel") + ph(3, "Inhalt", None, 1, text="Inhalt") + footers),
        layout("Zwei Inhalte", "twoObj",
               ph(2, "Titel", "title", text="Titel")
               + ph(3, "Links", None, 1, geo=geo, box=(0.06, 0.24, 0.43, 0.62), text="Links")
               + ph(4, "Rechts", None, 2, geo=geo, box=(0.51, 0.24, 0.43, 0.62), text="Rechts") + footers),
        layout("Abschnitt", "secHead",
               ph(2, "Titel", "title", geo=geo, box=(0.08, 0.38, 0.70, 0.20), anchor="b",
                  style=lst(sz=4400, color=bg1, caps="all"), text="Abschnitt")
               + ph(3, "Text", "body", 1, geo=geo, box=(0.08, 0.58, 0.70, 0.08), style=lst(sz=2000, color=scheme("bg2")), text="Nummer"),
               bg=sec_bg, show_master=False),
        layout("Nur Titel", "titleOnly", ph(2, "Titel", "title", text="Titel") + footers),
        layout("Zitat mit Bild", "picTx",
               '<p:grpSp><p:nvGrpSpPr><p:cNvPr id="9" name="Gruppe"/><p:cNvGrpSpPr/><p:nvPr userDrawn="1"/></p:nvGrpSpPr>'
               '<p:grpSpPr><a:xfrm><a:off x="609600" y="5486400"/><a:ext cx="5486400" cy="609600"/>'
               '<a:chOff x="0" y="0"/><a:chExt cx="1000" cy="1000"/></a:xfrm></p:grpSpPr>'
               + rect(10, "Zitatband", Geo(1000, 1000), (0, 0, 1, 1), solid(scheme("accent3", '<a:lumMod val="20000"/><a:lumOff val="80000"/>')))
               + '</p:grpSp>'
               + ph(2, "Titel", "title", geo=geo, box=(0.06, 0.20, 0.45, 0.30), text="Titel")
               + ph(3, "Zitat", None, 2, geo=geo, box=(0.06, 0.50, 0.45, 0.30), text="Zitat")
               + ph(4, "Bild", "pic", 1, geo=geo, box=(0.55, 0.20, 0.40, 0.60), text="")
               + footers),
    ]

    ct = (HDR + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          + "".join(f'<Override PartName="/ppt/slideLayouts/slideLayout{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>' for i in range(6))
          + '</Types>')
    rels = lambda items: (HDR + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(
        f'<Relationship Id="{i}" Type="{REL}/{t}" Target="{tg}"/>' for i, t, tg in items) + '</Relationships>')
    pres = (HDR + f'<p:presentation {NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            f'<p:sldSz cx="{geo.w}" cy="{geo.h}"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels([("rId1", "officeDocument", "ppt/presentation.xml")]))
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", rels([("rId1", "slideMaster", "slideMasters/slideMaster1.xml")]))
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels(
            [("rId1", "theme", "../theme/theme1.xml"), ("rId2", "image", "../media/logo.png")]
            + [(f"rId{i + 3}", "slideLayout", f"../slideLayouts/slideLayout{i + 1}.xml") for i in range(6)]))
        z.writestr("ppt/media/logo.png", png(300, 90, (23, 190, 187)))
        for i, xml in enumerate(layouts):
            z.writestr(f"ppt/slideLayouts/slideLayout{i + 1}.xml", xml)
            items = [("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")]
            if i in (0, 5) or "Logo" in xml:
                items.append(("rId2", "image", "../media/logo.png"))
            z.writestr(f"ppt/slideLayouts/_rels/slideLayout{i + 1}.xml.rels", rels(items))
    return path


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1] if len(sys.argv) > 1 else "testvorlage.pptx"))
