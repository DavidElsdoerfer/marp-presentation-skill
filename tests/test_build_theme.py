"""Tests für build-theme.py (nur Standardbibliothek): python3 -m unittest discover tests"""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skill" / "scripts" / "build-theme.py"
TOKENS = (ROOT / "skill" / "brands" / "neutral" / "tokens.css").read_text()
LOGO = (ROOT / "skill" / "brands" / "neutral" / "assets" / "logo.svg").read_bytes()


def make_brand(base, name="testbrand", **extra):
    d = Path(base) / name
    (d / "assets").mkdir(parents=True)
    (d / "tokens.css").write_text(TOKENS)
    (d / "assets" / "logo.svg").write_bytes(LOGO)
    meta = {"name": name, "logo": "assets/logo.svg", **extra}
    (d / "brand.json").write_text(json.dumps(meta))
    return d


def run(*args, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=e, cwd=cwd)


class BuildTheme(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_neutral_builds_and_is_self_contained(self):
        out = self.t / "n.css"
        r = run("neutral", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        css = out.read_text()
        self.assertTrue(css.startswith("/* @theme neutral */"))
        self.assertIn("--logo: url('data:image/svg+xml;base64,", css)
        self.assertIn("section.title", css)
        self.assertNotIn("url('assets", css)

    def test_brand_store_via_env(self):
        store = self.t / "store"
        make_brand(store, "meinbrand")
        out = self.t / "m.css"
        r = run("meinbrand", out, env={"MARP_BRANDS_DIR": str(store)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(out.read_text().startswith("/* @theme meinbrand */"))

    def test_store_wins_over_builtin_order(self):
        store = self.t / "store"
        make_brand(store, "neutral", )
        r = run("--list", env={"MARP_BRANDS_DIR": str(store)})
        lines = [l for l in r.stdout.splitlines() if l.startswith("neutral")]
        self.assertEqual(len(lines), 2)  # Store und eingebaut
        self.assertIn(str(store), lines[0])  # Store zuerst

    def test_unknown_brand_fails(self):
        r = run("gibtsnicht", self.t / "x.css", env={"MARP_BRANDS_DIR": str(self.t)})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nicht gefunden", r.stderr)

    def test_logo_path_traversal_rejected(self):
        d = make_brand(self.t / "s", "evil")
        meta = json.loads((d / "brand.json").read_text())
        meta["logo"] = "../../../../etc/hostname"
        (d / "brand.json").write_text(json.dumps(meta))
        r = run(d, self.t / "e.css")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("außerhalb", r.stderr)
        self.assertFalse((self.t / "e.css").exists())

    def test_font_traversal_rejected(self):
        d = make_brand(self.t / "s", "evilfont", fonts=[{"family": "X", "file": "../../etc/hostname"}])
        r = run(d, self.t / "f.css")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("außerhalb", r.stderr)

    def test_fonts_embedded(self):
        d = make_brand(self.t / "s", "withfont", fonts=[{"family": "Test Sans", "file": "assets/t.woff2", "weight": 700}])
        (d / "assets" / "t.woff2").write_bytes(b"wOF2fake")
        out = self.t / "w.css"
        r = run(d, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        css = out.read_text()
        self.assertIn("@font-face { font-family: 'Test Sans'; font-weight: 700;", css)
        self.assertIn("data:font/woff2;base64,", css)
        self.assertLess(css.index("@font-face"), css.index(":root"))  # Fonts vor Tokens

    def test_unsupported_font_format_rejected(self):
        d = make_brand(self.t / "s", "badfont", fonts=[{"family": "X", "file": "assets/logo.svg"}])
        r = run(d, self.t / "b.css")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nicht unterstützt", r.stderr)

    def test_brand_layouts_css_appended(self):
        d = make_brand(self.t / "s", "withlayouts")
        (d / "layouts.css").write_text("section.kpi { color: red; }\n")
        out = self.t / "l.css"
        self.assertEqual(run(d, out).returncode, 0)
        css = out.read_text()
        self.assertIn("section.kpi", css)
        self.assertGreater(css.index("section.kpi"), css.index("section.closing"))  # nach Basis-Layouts

    def test_overrides_remove_base_blocks(self):
        d = make_brand(self.t / "s", "ov", overrides=["title", "chrome"])
        out = self.t / "o.css"
        self.assertEqual(run(d, out).returncode, 0)
        css = out.read_text()
        self.assertNotIn("section.title {", css)
        self.assertNotIn("\nsection::before {", css)       # chrome entfernt (nur das reine section::before)
        self.assertIn("\nsection.section::before {", css)  # Abschnittsfolie bleibt
        self.assertIn("section.section {", css)             # nicht überschriebene Blöcke bleiben
        self.assertIn("section.closing {", css)
        self.assertIn("h1, h2, h3, h4", css)                # Typografie bleibt

    def test_unknown_override_rejected(self):
        d = make_brand(self.t / "s", "badov", overrides=["gibtsnicht"])
        r = run(d, self.t / "b.css")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unbekannte overrides", r.stderr)

    def test_css_urls_inlined_and_traversal_rejected(self):
        d = make_brand(self.t / "s", "urls")
        (d / "assets" / "bg.png").write_bytes(b"\x89PNGfake")
        (d / "layouts.css").write_text('section.x { background: url("assets/bg.png") center / cover; }\n')
        out = self.t / "u.css"
        self.assertEqual(run(d, out).returncode, 0)
        css = out.read_text()
        self.assertIn("url('data:image/png;base64,", css)
        self.assertNotIn("assets/bg.png", css)
        (d / "layouts.css").write_text("section.x { background: url(../../../etc/hostname); }\n")
        r = run(d, self.t / "u2.css")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("außerhalb", r.stderr)

    def test_external_and_data_urls_untouched(self):
        d = make_brand(self.t / "s", "ext")
        (d / "layouts.css").write_text("a{background:url(https://example.org/x.png)}b{background:url(data:image/png;base64,AAAA)}\n")
        out = self.t / "e.css"
        self.assertEqual(run(d, out).returncode, 0)
        css = out.read_text()
        self.assertIn("url(https://example.org/x.png)", css)
        self.assertIn("url(data:image/png;base64,AAAA)", css)


if __name__ == "__main__":
    unittest.main()
