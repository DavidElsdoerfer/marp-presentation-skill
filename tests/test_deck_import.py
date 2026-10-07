"""Tests für den Adapter import-deck (pptx2md) und für die Zusage 'Brand-Import liest nie Folieninhalt'."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(ROOT / "tests"))
import brand_import as bi  # noqa: E402
import deck_import as di  # noqa: E402
import pptx_extract as px  # noqa: E402
import template_factory as tf  # noqa: E402

CLI = SCRIPTS / "marp-deck"
TOOL = os.environ.get("PPTX2MD") or shutil.which("pptx2md")

# Gekürzte, aber strukturgleiche Ausgabe von `pptx2md --marp` (inkl. Google-Fonts-@import, Anleitungskommentar, Bild, Notiz).
RAW = '''---
marp: true
theme: default
paginate: true
html: true
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Cabin&display=swap');
section { font-family: 'Open Sans', sans-serif; }
</style>

<!--
  MANUAL LAYOUT USAGE EXAMPLES:
  <div class="columns"></div>
-->

# Mein Vortrag

# Untertitel hier


---

# Erste Inhaltsfolie

* Punkt eins
<!--
Das sage ich dazu.
-->


---

# Bild

![left Picture 2 w:384px](beispiel_img/slide3_shape3.png)
'''
FRONT = 'marp: true\ntheme: neutral\npaginate: true\nhtml: true\nfooter: "T"\n'


class SlideContentNeverRead(unittest.TestCase):
    def test_brand_import_ignores_slide_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pptx = tf.build(t / "mit-folien.pptx", slides=True)
            self.assertIn(tf.SECRET, __import__("zipfile").ZipFile(pptx).read("ppt/slides/slide2.xml").decode())   # Text ist wirklich drin
            data = px.extract(pptx)
            self.assertNotIn(tf.SECRET, json.dumps(data, ensure_ascii=False))
            out = t / "brand"
            bi.import_brand(pptx, "geheim", out, render=False)
            for f in out.rglob("*"):
                if f.is_file():
                    self.assertNotIn(tf.SECRET.encode(), f.read_bytes(), f"{f.name} enthält Folientext")
            sc = __import__("pptx_showcase")
            show = t / "show.pptx"; sc.build(pptx, show)
            self.assertNotIn(tf.SECRET.encode(), b"".join(__import__("zipfile").ZipFile(show).read(n) for n in __import__("zipfile").ZipFile(show).namelist()))


class Postprocess(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        (self.t / "work" / "beispiel_img").mkdir(parents=True)
        (self.t / "work" / "beispiel_img" / "slide3_shape3.png").write_bytes(b"\x89PNGdata")
        self.assets = self.t / "deck" / "assets"

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, raw=RAW):
        return di.build_markdown(raw, FRONT, [self.t / "work"], self.assets)

    def test_external_import_and_style_block_removed(self):
        text, _ = self.build()
        self.assertNotIn("googleapis", text); self.assertNotIn("http", text)          # keine externen Ressourcen
        self.assertNotIn("MANUAL LAYOUT", text); self.assertNotIn("Open Sans", text)
        self.assertEqual(text.count("<style>"), 1)                       # nur die lokale Kompatibilitäts-CSS
        self.assertIn("theme: neutral", text); self.assertNotIn("theme: default", text)

    def test_title_slide(self):
        text, info = self.build()
        self.assertTrue(info["title_slide"])
        self.assertIn("<!-- _class: title -->\n\n# Mein Vortrag\n\n## Untertitel hier", text)

    def test_notes_kept_as_comments(self):
        text, _ = self.build()
        self.assertIn("<!--\nDas sage ich dazu.\n-->", text)

    def test_slide_count(self):
        _, info = self.build()
        self.assertEqual(info["slides"], 3)

    def test_images_moved_and_paths_rewritten(self):
        text, info = self.build()
        self.assertIn("![left Picture 2 w:384px](assets/slide3_shape3.png)", text)
        self.assertEqual((self.assets / "slide3_shape3.png").read_bytes(), b"\x89PNGdata")
        self.assertEqual(info["missing_images"], [])

    def test_missing_image_reported_and_path_kept(self):
        text, info = self.build(RAW.replace("slide3_shape3.png", "fehlt.png"))
        self.assertEqual(info["missing_images"], ["beispiel_img/fehlt.png"])
        self.assertIn("beispiel_img/fehlt.png", text)

    def test_existing_asset_not_overwritten(self):
        self.assets.mkdir(parents=True); (self.assets / "slide3_shape3.png").write_bytes(b"MEINS")
        text, _ = self.build()
        self.assertEqual((self.assets / "slide3_shape3.png").read_bytes(), b"MEINS")
        self.assertIn("assets/slide3_shape3-1.png", text)

    def test_path_traversal_reference_only_resolves_by_name_inside_roots(self):
        (self.t / "geheim.png").write_bytes(b"AUSSERHALB")
        text, info = self.build(RAW.replace("beispiel_img/slide3_shape3.png", "../../geheim.png"))
        self.assertFalse((self.assets / "geheim.png").exists())           # liegt nicht unter den Suchwurzeln
        self.assertEqual(info["missing_images"], ["../../geheim.png"])

    def test_first_slide_variants(self):
        one = "---\nmarp: true\n---\n\n# Nur ein Titel\n\n---\n\n# Zwei\n"
        text, info = di.build_markdown(one, FRONT, [self.t / "work"], self.assets)
        self.assertIn("<!-- _class: title -->\n\n# Nur ein Titel", text); self.assertNotIn("## ", text)
        noh = "---\nmarp: true\n---\n\nnur Text\n\n---\n\n# Zwei\n"
        _, info = di.build_markdown(noh, FRONT, [self.t / "work"], self.assets)
        self.assertFalse(info["title_slide"])

    def test_find_tool_error_has_install_hint(self):
        old = os.environ.pop("PPTX2MD", None)
        try:
            with self.assertRaises(di.DeckImportError) as cm:
                di.find_tool("/gibt/es/nicht")
            self.assertIn("python3 -m venv", str(cm.exception))
        finally:
            if old:
                os.environ["PPTX2MD"] = old


@unittest.skipUnless(TOOL, "pptx2md nicht installiert (PPTX2MD setzen)")
class EndToEnd(unittest.TestCase):
    def test_import_deck_with_real_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pptx = tf.build(t / "mit-folien.pptx", slides=True)
            env = {**os.environ, "MARP_BRANDS_DIR": str(t / "store")}
            r = subprocess.run([sys.executable, str(CLI), "import-deck", str(pptx), "--tool", TOOL, "--dir", str(t)],
                               capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=300)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            md = (t / "mit-folien" / "mit-folien.md").read_text()
            self.assertIn("<!-- _class: title -->", md); self.assertIn("# Mein Vortrag", md); self.assertIn("## Untertitel hier", md)
            self.assertIn(tf.SECRET, md)                                  # eigene Folien: Inhalt wird übernommen
            self.assertNotIn("googleapis", md)

    def test_tool_failure_leaves_no_deck(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            bad = t / "kaputt.pptx"; bad.write_bytes(b"kein pptx")
            env = {**os.environ, "MARP_BRANDS_DIR": str(t / "store")}
            r = subprocess.run([sys.executable, str(CLI), "import-deck", str(bad), "--tool", TOOL, "--dir", str(t)],
                               capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=300)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((t / "kaputt").exists())


if __name__ == "__main__":
    unittest.main()
