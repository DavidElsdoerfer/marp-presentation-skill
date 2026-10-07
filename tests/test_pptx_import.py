"""Tests für PPTX-Extraktion, Showcase, Brand-Import und Vergleich (synthetische Vorlage aus template_factory)."""
import json, re, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(ROOT / "tests"))
import pptx_extract as px  # noqa: E402
import pptx_showcase as sc  # noqa: E402
import brand_import as bi  # noqa: E402
import brand_preview as bp  # noqa: E402
import template_factory as tf  # noqa: E402
from common import find_chrome  # noqa: E402

HAVE_RENDER = bool(shutil.which("soffice") and shutil.which("pdftocairo") and shutil.which("npx") and find_chrome())
CLI = SCRIPTS / "marp-deck"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.t = Path(cls.tmp.name)
        cls.pptx = tf.build(cls.t / "vorlage.pptx")
        cls.data = px.extract(cls.pptx)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class Extract(Base):
    def test_slide_theme_fonts(self):
        d = self.data
        self.assertEqual(d["slide"]["aspect"], 1.7778)
        self.assertEqual(d["theme"]["colors"]["accent1"], "#e4572e")
        self.assertEqual(d["theme"]["fonts"], {"major": "Georgia", "minor": "Verdana"})

    def test_layouts_and_types(self):
        names = [l["name"] for l in self.data["layouts"]]
        self.assertEqual(names, ["Titelfolie", "Titel und Inhalt", "Zwei Inhalte", "Abschnitt", "Nur Titel", "Zitat mit Bild"])
        self.assertEqual([l["type"] for l in self.data["layouts"]], ["title", "obj", "twoObj", "secHead", "titleOnly", "picTx"])

    def test_empty_placeholder_elements_recognized(self):
        """Regression: <p:ph/> ist ein leeres Element und gilt in ElementTree als falsch."""
        roles = [s["ph"]["role"] for s in self.data["layouts"][1]["shapes"] if s["kind"] == "placeholder"]
        self.assertEqual(roles, ["title", "body", "date", "footer", "number"])

    def test_geometry_inherited_from_master(self):
        title = next(s for s in self.data["layouts"][1]["shapes"] if s.get("ph", {}).get("role") == "title")
        self.assertTrue(title["xfrm_inherited"])
        f = px.to_fractions(self.data, title)
        self.assertAlmostEqual(f["x"], 0.06, places=3); self.assertAlmostEqual(f["w"], 0.70, places=3)

    def test_text_style_inheritance_and_theme_font_resolution(self):
        title = next(s for s in self.data["layouts"][1]["shapes"] if s.get("ph", {}).get("role") == "title")
        self.assertEqual(title["text_props"]["size_pt"], 32.0); self.assertTrue(title["text_props"]["bold"])
        self.assertEqual(title["text_props"]["font"], "Georgia")      # +mj-lt aufgelöst
        self.assertEqual(title["text_props"]["color"], "#0b3d5c")      # tx2 → dk2 über clrMap

    def test_anchor_inherited_per_key(self):
        """Regression: leeres <a:bodyPr/> darf den Anker des Masters nicht mit Standardwerten überschreiben."""
        title = next(s for s in self.data["layouts"][1]["shapes"] if s.get("ph", {}).get("role") == "title")
        self.assertEqual(title["body"]["anchor"], "ctr")

    def test_gradient_background(self):
        bg = self.data["layouts"][0]["bg"]
        self.assertEqual(bg["type"], "gradient"); self.assertEqual(bg["angle"], 45.0)
        self.assertEqual([s["hex"] for s in bg["stops"]], ["#0b3d5c", "#e4572e"])

    def test_group_transform_and_lummod(self):
        band = next(s for s in self.data["layouts"][5]["shapes"] if s.get("name") == "Zitatband")
        f = px.to_fractions(self.data, band)
        self.assertAlmostEqual(f["x"], 0.05, places=3); self.assertAlmostEqual(f["y"], 0.8, places=3)
        self.assertAlmostEqual(f["w"], 0.45, places=3)
        self.assertEqual(band["fill"]["hex"], "#fff4d0")               # accent3, lumMod 20 %, lumOff 80 %

    def test_picture_media(self):
        pics = [s for s in self.data["layouts"][0]["shapes"] if s["kind"] == "picture"]
        self.assertEqual(pics[0]["image"], "ppt/media/logo.png")

    def test_invalid_files_rejected(self):
        bad = self.t / "kaputt.pptx"; bad.write_bytes(b"kein zip")
        with self.assertRaises(px.PptxError):
            px.extract(bad)
        nopres = self.t / "leer.pptx"
        with zipfile.ZipFile(nopres, "w") as z:
            z.writestr("x.txt", "nichts")
        with self.assertRaises(px.PptxError):
            px.extract(nopres)

    def _with_presentation_xml(self, name, xml):
        evil = self.t / name
        with zipfile.ZipFile(self.pptx) as zin, zipfile.ZipFile(evil, "w") as zout:
            for n in zin.namelist():
                zout.writestr(n, xml if n == "ppt/presentation.xml" else zin.read(n))
        return evil

    def test_xml_bomb_rejected_cleanly(self):
        """Billion-Laughs: expat begrenzt die Erweiterung; der Fehler muss als PptxError (nicht als Traceback) ankommen."""
        ents = "".join(f'<!ENTITY lol{i} "' + (f"&lol{i - 1};" if i > 1 else "lol") * 10 + '">' for i in range(1, 10))
        bomb = (f'<?xml version="1.0"?><!DOCTYPE x [{ents}]><p:presentation xmlns:p="urn:p">&lol9;</p:presentation>')
        with self.assertRaises(px.PptxError):
            px.extract(self._with_presentation_xml("bombe.pptx", bomb))

    def test_external_entity_not_resolved(self):
        xxe = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/hostname">]><p:presentation xmlns:p="urn:p">&e;</p:presentation>'
        with self.assertRaises(px.PptxError):
            px.extract(self._with_presentation_xml("xxe.pptx", xxe))

    def test_unexpected_structure_is_a_clean_error(self):
        broken = ('<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                  '<p:sldMasterIdLst><p:sldMasterId id="1" r:id="rIdGibtsNicht"/></p:sldMasterIdLst></p:presentation>')
        with self.assertRaises(px.PptxError):
            px.extract(self._with_presentation_xml("kaputt-struktur.pptx", broken))

    def test_43_aspect(self):
        d = px.extract(tf.build(self.t / "v43.pptx", aspect="4:3"))
        self.assertAlmostEqual(d["slide"]["aspect"], 1.3333, places=3)


class Showcase(Base):
    def test_one_empty_slide_per_layout(self):
        out = self.t / "show.pptx"
        self.assertEqual(sc.build(self.pptx, out), 6)
        with zipfile.ZipFile(out) as z:
            self.assertIsNone(z.testzip())
            slides = sorted(n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))
            self.assertEqual(len(slides), 6)
            for n in slides:
                self.assertNotIn("<p:sp>", z.read(n).decode())            # leer: nur Layout/Master-Grafiken sichtbar
            rels = z.read("ppt/slides/_rels/slide3.xml.rels").decode()
            self.assertIn("slideLayout3.xml", rels)
        # Quelle bleibt gültig lesbar (Regression: writestr(ZipInfo) zerstörte die Offsets der Quelle)
        self.assertEqual(len(px.extract(out)["layouts"]), 6)

    def test_filled_has_sample_text_in_placeholders(self):
        out = self.t / "filled.pptx"
        sc.build(self.pptx, out, filled=True)
        with zipfile.ZipFile(out) as z:
            s2 = z.read("ppt/slides/slide2.xml").decode()
            s3 = z.read("ppt/slides/slide3.xml").decode()
        self.assertIn(sc.SAMPLE["title"], s2); self.assertIn(sc.SAMPLE["body"][0], s2)
        self.assertEqual(s3.count(sc.SAMPLE["body"][0]), 2)                # zwei Inhaltsfelder
        self.assertIn('type="slidenum"', s2)

    def test_sld_id_lst_after_notes_master(self):
        """Regression (echte Datei): sldIdLst muss NACH notesMasterIdLst stehen, sonst lädt LibreOffice die Datei nicht."""
        pres = ('<p:presentation xmlns:p="urn:p"><p:sldMasterIdLst><p:sldMasterId id="1" r:id="a" xmlns:r="urn:r"/></p:sldMasterIdLst>'
                '<p:notesMasterIdLst><p:notesMasterId r:id="b" xmlns:r="urn:r"/></p:notesMasterIdLst><p:sldSz cx="1" cy="1"/></p:presentation>')
        out = sc.insert_sld_id_lst(pres, [(256, "rId9")])
        self.assertLess(out.index("</p:notesMasterIdLst>"), out.index("<p:sldIdLst>"))
        self.assertLess(out.index("</p:sldIdLst>"), out.index("<p:sldSz"))
        with_handout = pres.replace("<p:sldSz", '<p:handoutMasterIdLst><p:handoutMasterId r:id="c" xmlns:r="urn:r"/></p:handoutMasterIdLst><p:sldSz')
        out = sc.insert_sld_id_lst(with_handout, [(256, "rId9")])
        self.assertLess(out.index("</p:handoutMasterIdLst>"), out.index("<p:sldIdLst>"))

    def test_sld_id_lst_valid_xml_when_r_declared_only_locally(self):
        """Regression (echte Datei): xmlns:r steht nur lokal an Elementen, nicht an der Wurzel → r:id braucht eigene Deklaration."""
        from xml.etree import ElementTree as ET
        pres = ('<p:presentation xmlns:p="urn:p"><p:sldMasterIdLst><p:sldMasterId id="1" r:id="a" xmlns:r="urn:r"/></p:sldMasterIdLst>'
                '<p:sldSz cx="1" cy="1"/></p:presentation>')
        root = ET.fromstring(sc.insert_sld_id_lst(pres, [(256, "rId9")]))     # wirft ParseError bei ungebundenem Präfix
        self.assertEqual(len(root.findall(".//{urn:p}sldId")), 1)

    def test_sld_id_lst_other_prefix(self):
        pres = ('<pr:presentation xmlns:pr="urn:p"><pr:sldMasterIdLst><pr:sldMasterId id="1"/></pr:sldMasterIdLst><pr:sldSz/></pr:presentation>')
        out = sc.insert_sld_id_lst(pres, [(256, "rId9")])
        self.assertIn("<pr:sldIdLst>", out); self.assertIn("</pr:sldIdLst>", out)

    def test_existing_slides_removed(self):
        out1 = self.t / "a.pptx"; sc.build(self.pptx, out1)
        out2 = self.t / "b.pptx"; self.assertEqual(sc.build(out1, out2), 6)    # Showcase eines Showcase: keine Doppelungen
        with zipfile.ZipFile(out2) as z:
            self.assertEqual(len([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)]), 6)


class Import(Base):
    def run_import(self, name="testbrand", **kw):
        out = self.t / f"brand-{name}"
        res = bi.import_brand(self.pptx, name, out, render=False, **kw)
        return out, res

    def test_classification(self):
        _, res = self.run_import("klass")
        self.assertEqual(res["semantic"]["title"], "Titelfolie"); self.assertEqual(res["semantic"]["section"], "Abschnitt")
        self.assertEqual(res["semantic"]["cols"], "Zwei Inhalte"); self.assertEqual(res["semantic"]["content"], "Titel und Inhalt")
        self.assertIn("wie Titelfolie", res["semantic"]["closing"])
        self.assertIn("layout-nur-titel", sum(res["classes"].values(), []))

    def test_files_and_tokens(self):
        out, _ = self.run_import("dateien")
        for f in ("brand.json", "tokens.css", "layouts.css", "layouts.md"):
            self.assertTrue((out / f).is_file(), f)
        tok = (out / "tokens.css").read_text()
        self.assertIn("--primary: #e4572e", tok); self.assertIn('"Verdana"', tok); self.assertIn('"Georgia", serif', tok)
        meta = json.loads((out / "brand.json").read_text())
        self.assertEqual(meta["background_mode"], "layers")
        self.assertEqual(set(meta["overrides"]), {"chrome", "title", "section", "closing", "cols"})
        self.assertTrue((out / meta["logo"]).is_file())

    def test_layers_mode_reconstructs_background_from_graphics(self):
        out, _ = self.run_import("layers")
        css = (out / "layouts.css").read_text()
        self.assertIn("linear-gradient(135deg", css)                    # 45° OOXML → 135° CSS
        self.assertIn("url('assets/media/logo.png')", css)
        self.assertNotIn("assets/bg/", css)

    def test_geometry_in_css(self):
        out, _ = self.run_import("geo")
        css = (out / "layouts.css").read_text()
        # Titel und Inhalt: Titelfeld x=0.06 → 76.8 px, Breite 0.70 → 896 px
        m = re.search(r"section h1 \{[^}]*left: ([\d.]+)px;[^}]*width: ([\d.]+)px", css, re.S)
        self.assertEqual((m.group(1), m.group(2)), ("76.8", "896"))
        self.assertIn("section.cols > div:nth-of-type(2)", css)         # zwei Slots
        self.assertIn("font-family: var(--font)", css)                  # Regression: Textschrift explizit
        self.assertIn("section.title::after { display: none; }", css)   # Regression: Marpit verwirft content auf ::after

    def test_built_theme_renders_with_overrides(self):
        out, _ = self.run_import("build")
        css = self.t / "b.css"
        r = subprocess.run([sys.executable, str(SCRIPTS / "build-theme.py"), str(out), str(css)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = css.read_text()
        self.assertNotIn("section.title::before {\n  top: 35px", text)   # Basis-Titelblock ersetzt
        self.assertIn("/* @theme build */", text)

    def test_existing_dir_not_overwritten(self):
        out = self.t / "belegt"; out.mkdir(); (out / "x.txt").write_text("bleibt")
        with self.assertRaises(bi.ImportError_):
            bi.import_brand(self.pptx, "belegt", out, render=False)
        self.assertEqual((out / "x.txt").read_text(), "bleibt")

    def test_deck_snapshot_excludes_originals(self):
        """Ein weitergegebenes Deck darf die Original-Richtlinien und Referenzbilder nicht enthalten."""
        g = self.t / "richtlinie-geheim.pdf"; g.write_bytes(b"%PDF vertraulich")
        store = self.t / "store-snap"
        env = {**__import__("os").environ, "MARP_BRANDS_DIR": str(store)}
        out = store / "snap"
        bi.import_brand(self.pptx, "snap", out, render=False, guidelines=[g])
        (out / "reference").mkdir(exist_ok=True); (out / "reference" / "01.png").write_bytes(b"png")
        r = subprocess.run([sys.executable, str(CLI), "new", "Snap Deck", "--brand", "snap", "--dir", str(self.t)], capture_output=True,
                           text=True, env=env, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stderr)
        snap = self.t / "snap-deck" / "theme" / "brand"
        self.assertFalse((snap / "guidelines").exists()); self.assertFalse((snap / "reference").exists())
        self.assertTrue((snap / "GUIDELINES.md").is_file())            # die verdichteten Regeln bleiben
        self.assertTrue((snap / "layouts.css").is_file())

    def test_cli_failed_import_keeps_existing_brand(self):
        store = self.t / "store"; (store / "belegt").mkdir(parents=True); (store / "belegt" / "x.txt").write_text("bleibt")
        r = subprocess.run([sys.executable, str(CLI), "brand", "import", str(self.pptx), "--name", "belegt", "--no-render"],
                           capture_output=True, text=True, env={**__import__("os").environ, "MARP_BRANDS_DIR": str(store)}, stdin=subprocess.DEVNULL)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((store / "belegt" / "x.txt").read_text(), "bleibt")   # Regression: Fehlerpfad löschte vorhandene Brand

    def test_map_override_and_unknown_layout(self):
        _, res = self.run_import("map", mapping={"closing": "Nur Titel"})
        self.assertEqual(res["semantic"]["closing"], "Nur Titel")
        with self.assertRaises(bi.ImportError_):
            bi.import_brand(self.pptx, "x", self.t / "map2", render=False, mapping={"closing": "Gibts nicht"})

    def test_guidelines_copied(self):
        g = self.t / "richtlinie.txt"; g.write_text("Logo braucht Abstand.")
        out, res = self.run_import("gl", guidelines=[g])
        self.assertTrue((out / "guidelines" / "richtlinie.txt").is_file())
        self.assertIn("Quellen", (out / "GUIDELINES.md").read_text())

    def test_43_template_is_first_class(self):
        p43 = tf.build(self.t / "v43.pptx", aspect="4:3")
        out = self.t / "b43"
        res = bi.import_brand(p43, "b43", out, render=False)
        self.assertEqual(res["warnings"], [])
        meta = json.loads((out / "brand.json").read_text())
        self.assertEqual(meta["size"], {"name": "4:3", "w": 960, "h": 720})
        css = self.t / "b43.css"
        subprocess.run([sys.executable, str(SCRIPTS / "build-theme.py"), str(out), str(css)], check=True, capture_output=True)
        self.assertIn("/* @size 4:3 960px 720px */", css.read_text())
        # Titelfeld x=0.06 → 0.06 × 960 px (nicht × 1280)
        self.assertRegex((out / "layouts.css").read_text(), r"section h1 \{[^}]*left: 57\.6px")
        self.assertIn("size: 4:3", bp.preview_markdown(meta))
        env = {**__import__("os").environ, "MARP_BRANDS_DIR": str(self.t)}
        r = subprocess.run([sys.executable, str(CLI), "new", "Vier zu Drei", "--brand", str(out), "--dir", str(self.t)],
                           capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("size: 4:3", (self.t / "vier-zu-drei" / "vier-zu-drei.md").read_text())

    def test_sample_run_style_used_as_fallback(self):
        """Regression (LibreOffice-Dateien): Größen stehen in der Beispielzeile statt in lstStyle/txStyles."""
        sp = ('<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
              '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr algn="ctr"/><a:r><a:rPr sz="4400" b="1"><a:latin typeface="Arial"/></a:rPr><a:t>x</a:t></a:r></a:p></p:txBody></p:sp>')
        from xml.etree import ElementTree as ET
        tx = px.find(ET.fromstring(sp), "p:txBody")
        props = px.para_props(tx, px.Theme(ET.Element("x")), {})
        self.assertEqual((props["size_pt"], props["bold"], props["font"]), (44.0, True, "Arial"))
        self.assertNotIn("align", props)                  # Ausrichtung der Beispielzeile ist unzuverlässig

    def test_end_para_props_ignored_and_defaults_applied(self):
        """Regression (LibreOffice): endParaRPr formatiert nur das Absatzende und ist kein Textstil; fehlende Größen → Office-Standard."""
        sp = ('<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
              '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr sz="1800" b="1"/></a:p></p:txBody></p:sp>')
        from xml.etree import ElementTree as ET
        tx = px.find(ET.fromstring(sp), "p:txBody")
        self.assertEqual(px.para_props(tx, px.Theme(ET.Element("x")), {}), {})
        self.assertEqual(px.DEFAULT_STYLE["title"]["size_pt"], 44.0)

    def test_rotation_and_negative_padding(self):
        out, _ = self.run_import("rot")
        # synthetische Vorlage: nichts rotiert → keine transform-Zeile
        self.assertNotIn("transform: rotate", (out / "layouts.css").read_text())
        s = {"xfrm": {"rot": 351.85}}
        self.assertEqual(bi.rotation_css(s)[0], "transform: rotate(-8.1deg)")      # 351.85° ≡ −8.15°
        self.assertEqual(bi.rotation_css({"xfrm": {"rot": 0.0}}), [])
        self.assertNotIn("-", re.search(r"padding: ([^;]*);", (out / "layouts.css").read_text()).group(1).split()[0])

    def test_preview_markdown(self):
        out, _ = self.run_import("pv")
        meta = bp.load_meta(out)
        md = bp.preview_markdown(meta)
        self.assertIn("theme: pv", md); self.assertIn("<!-- _class: cols -->", md); 
        self.assertEqual(md.count("<div>\n\n- "), 3)                 # cols: 2 Textslots, Zitat-Layout: 1 Textslot
        self.assertIn("picture: hier einfügen", md)                 # Bildplatz im Zitat-Layout
        cmp_md = bp.preview_markdown(meta, "compare")
        self.assertIn(sc.SAMPLE["title"], cmp_md); self.assertNotIn("title-meta", cmp_md)


@unittest.skipUnless(HAVE_RENDER, "LibreOffice, pdftocairo, Chrome oder Node fehlen")
class RenderAndCompare(Base):
    def test_render_mode_and_comparison_within_text_noise(self):
        out = self.t / "rb"
        res = bi.import_brand(self.pptx, "rb", out)
        self.assertEqual(res["mode"], "render")
        self.assertEqual(len(list((out / "assets" / "bg").glob("*.png"))), 6)
        self.assertEqual(len(list((out / "reference").glob("*.png"))), 6)
        if not shutil.which("compare"):
            self.skipTest("ImageMagick fehlt")
        rows = bp.compare(out, self.t / "cmp")
        self.assertEqual(len(rows), 7)                                    # 6 Layouts + closing-Alias
        for r in rows:
            self.assertLess(r["abweichung"], 0.12, f"{r['class']}: {r['abweichung']}")   # Textglättung ≈ 5 %, Layoutfehler > 10 %
        self.assertTrue((self.t / "cmp" / "01-title-vergleich.png").is_file())

    def test_end_to_end_deck_with_imported_brand(self):
        store = self.t / "store2"
        env = {**__import__("os").environ, "MARP_BRANDS_DIR": str(store)}
        r = subprocess.run([sys.executable, str(CLI), "brand", "import", str(self.pptx), "--name", "e2e"], capture_output=True, text=True,
                           env=env, stdin=subprocess.DEVNULL, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, str(CLI), "new", "E2E Deck", "--brand", "e2e", "--dir", str(self.t)], capture_output=True, text=True,
                           env=env, stdin=subprocess.DEVNULL, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        deck = self.t / "e2e-deck"
        r = subprocess.run([sys.executable, str(CLI), "export", "pdf", str(deck)], capture_output=True, text=True, env=env,
                           stdin=subprocess.DEVNULL, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((deck / "dist" / "e2e-deck.pdf").read_bytes().startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
