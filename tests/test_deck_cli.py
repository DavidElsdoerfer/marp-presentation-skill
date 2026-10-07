"""Tests für marp-deck: new, brand sync, export, serve, Browser-Verhalten.
Integrationstests brauchen Node (npx, marp-cli im Cache oder Netzwerk); Browser-Tests zusätzlich Chrome."""
import importlib.machinery, importlib.util, json, os, shutil, socket, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from common import find_chrome  # noqa: E402

CLI = SCRIPTS / "marp-deck"
loader = importlib.machinery.SourceFileLoader("marp_deck", str(CLI))
spec = importlib.util.spec_from_loader("marp_deck", loader)
md = importlib.util.module_from_spec(spec)
loader.exec_module(md)

HAVE_NODE = bool(shutil.which("npx"))
CHROME = find_chrome()
PPTR = next(iter(sorted(Path.home().glob(".npm/_npx/*/node_modules/puppeteer-core"))), None)
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0f01f0005000201a52fa9c80000000049454e44ae426082")


def deck_cli(*args, cwd=None, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True, cwd=cwd, env=e,
                          stdin=subprocess.DEVNULL, timeout=240)


class Slug(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(md.slugify("Größe & Wirkung: KI im Mittelstand!"), "größe-wirkung-ki-im-mittelstand")
        self.assertEqual(md.slugify("  Linux   vs  Windows "), "linux-vs-windows")
        self.assertEqual(md.slugify("a_b--c"), "a-b-c")
        self.assertEqual(md.slugify("!!!"), "")


class InlineAssets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        (self.d / "assets").mkdir(); (self.d / "assets" / "a b.png").write_bytes(PNG)
        (self.d.parent / "geheim.txt").write_text("nicht einbetten")

    def tearDown(self):
        self.tmp.cleanup()
        (self.d.parent / "geheim.txt").unlink(missing_ok=True)

    def test_inline_img_and_background(self):
        html = '<img src="assets/a%20b.png"><figure style="background-image:url(&quot;assets/a b.png&quot;)"></figure>'
        out, missing = md.inline_local_assets(html, self.d)
        self.assertEqual(missing, [])
        self.assertEqual(out.count("data:image/png;base64,"), 2)
        self.assertNotIn("assets/", out)

    def test_external_and_data_untouched(self):
        html = '<img src="https://example.org/x.png"><img src="data:image/png;base64,AAAA"><a href="#x">'
        out, missing = md.inline_local_assets(html, self.d)
        self.assertEqual(out, html); self.assertEqual(missing, [])

    def test_path_outside_deck_not_embedded(self):
        out, missing = md.inline_local_assets('<img src="../geheim.txt">', self.d)
        self.assertEqual(out, '<img src="../geheim.txt">'); self.assertEqual(missing, ["../geheim.txt"])

    def test_missing_file_reported(self):
        out, missing = md.inline_local_assets('<img src="assets/gibts-nicht.png">', self.d)
        self.assertEqual(missing, ["assets/gibts-nicht.png"])


class NewAndBrand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        self.env = {"MARP_BRANDS_DIR": str(self.t / "store")}

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_creates_self_contained_deck(self):
        r = deck_cli("new", "Mein Test-Deck", "--dir", self.t, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        deck = self.t / "mein-test-deck"
        for rel in ["mein-test-deck.md", "marp.config.mjs", "theme/theme.css", "theme/brand/brand.json",
                    "theme/brand/tokens.css", "assets", ".gitignore"]:
            self.assertTrue((deck / rel).exists(), rel)
        text = (deck / "mein-test-deck.md").read_text()
        self.assertIn("theme: neutral", text); self.assertIn("# Mein Test-Deck", text)
        self.assertIn("allowLocalFiles: true", (deck / "marp.config.mjs").read_text())
        self.assertIn("@theme neutral", (deck / "theme" / "theme.css").read_text())

    def test_new_refuses_existing(self):
        self.assertEqual(deck_cli("new", "X", "--dir", self.t, env=self.env).returncode, 0)
        r = deck_cli("new", "X", "--dir", self.t, env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertIn("existiert bereits", r.stderr)

    def test_new_unknown_brand_fails_without_leftovers(self):
        r = deck_cli("new", "Y", "--brand", "gibtsnicht", "--dir", self.t, env=self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.t / "y").exists())

    def test_brand_sync_picks_up_store_change(self):
        store = self.t / "store" / "eigen"; (store / "assets").mkdir(parents=True)
        shutil.copy(ROOT / "skill/brands/neutral/tokens.css", store / "tokens.css")
        shutil.copy(ROOT / "skill/brands/neutral/assets/logo.svg", store / "assets" / "logo.svg")
        (store / "brand.json").write_text(json.dumps({"name": "eigen", "logo": "assets/logo.svg"}))
        self.assertEqual(deck_cli("new", "D", "--brand", "eigen", "--dir", self.t, env=self.env).returncode, 0)
        deck = self.t / "d"
        self.assertIn("theme: eigen", (deck / "d.md").read_text())
        self.assertIn("unverändert", deck_cli("brand", "sync", deck, env=self.env).stdout)
        tok = (store / "tokens.css").read_text().replace("#2f5d8a", "#ff0000")
        (store / "tokens.css").write_text(tok)
        r = deck_cli("brand", "sync", deck, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("aktualisiert", r.stdout)
        self.assertIn("#ff0000", (deck / "theme" / "theme.css").read_text())

    def test_find_deck_errors(self):
        r = deck_cli("export", "html", self.t / "nix", env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertIn("kein Deck gefunden", r.stderr)


@unittest.skipUnless(HAVE_NODE, "npx nicht gefunden")
class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.t = Path(cls.tmp.name)
        cls.env = {"MARP_BRANDS_DIR": str(cls.t / "store")}
        assert deck_cli("new", "Integration", "--dir", cls.t, env=cls.env).returncode == 0
        cls.deck = cls.t / "integration"
        (cls.deck / "assets" / "p.png").write_bytes(PNG)
        with open(cls.deck / "integration.md", "a") as f:
            f.write("\n---\n\n# Bild\n\n![w:100](assets/p.png)\n\n---\n\n![bg right:30%](assets/p.png)\n\n# Hintergrund\n")

    @classmethod
    def tearDownClass(cls):
        deck_cli("serve", "--stop", cls.deck, env=cls.env)
        cls.tmp.cleanup()

    def test_1_export_html_is_single_file(self):
        r = deck_cli("export", "html", self.deck, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        html = (self.deck / "dist" / "integration.html").read_text()
        self.assertNotIn("assets/p.png", html)
        self.assertGreaterEqual(html.count("data:image/png;base64,"), 2)
        self.assertIn("presenter", html)

    @unittest.skipUnless(CHROME, "Chrome nicht gefunden")
    def test_2_export_pdf(self):
        r = deck_cli("export", "pdf", self.deck, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        pdf = (self.deck / "dist" / "integration.pdf").read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_3_serve_loopback_only_and_stop(self):
        port = 18400
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                self.skipTest("Testport belegt")
        r = deck_cli("serve", self.deck, "--port", port, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        try:
            self.assertIn(f"http://localhost:{port}/integration.md", r.stdout)
            ss = subprocess.run(["ss", "-ltn"], capture_output=True, text=True).stdout
            line = [l for l in ss.splitlines() if f":{port} " in l][0]
            self.assertIn(f"127.0.0.1:{port}", line)       # nicht 0.0.0.0 / *
            self.assertIn("läuft bereits", deck_cli("serve", self.deck, "--port", port, env=self.env).stdout)
        finally:
            self.assertIn("gestoppt", deck_cli("serve", self.deck, "--stop", env=self.env).stdout)
        with socket.socket() as s:
            self.assertNotEqual(s.connect_ex(("127.0.0.1", port)), 0)

    @unittest.skipUnless(CHROME and PPTR, "Chrome oder puppeteer-core nicht gefunden")
    def test_4_live_reload_in_browser(self):
        port = 18401
        r = deck_cli("serve", self.deck, "--port", port, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        try:
            url = json.loads((self.deck / ".marp-deck" / "serve.json").read_text())["url"]
            out = subprocess.run(["node", str(ROOT / "tests/e2e/browser-check.mjs"), str(PPTR), CHROME, "live",
                                  str(self.deck / "integration.md"), url, "# Integration", "# Neu geschrieben"],
                                 capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL)
            res = json.loads(out.stdout.strip().splitlines()[-1])
            self.assertEqual(res["before"], "Integration")
            self.assertEqual(res["after"], "Neu geschrieben")
        finally:
            deck_cli("serve", self.deck, "--stop", env=self.env)

    @unittest.skipUnless(CHROME and PPTR, "Chrome oder puppeteer-core nicht gefunden")
    def test_5_exported_html_portable_with_presenter_view(self):
        html = self.deck / "dist" / "integration.html"
        if not html.exists():
            self.skipTest("HTML-Export fehlt (test_1)")
        with tempfile.TemporaryDirectory() as lone:  # ohne Deck-Ordner öffnen
            shutil.copy(html, Path(lone) / "talk.html")
            out = subprocess.run(["node", str(ROOT / "tests/e2e/browser-check.mjs"), str(PPTR), CHROME, "html",
                                  str(Path(lone) / "talk.html")], capture_output=True, text=True, timeout=90,
                                 stdin=subprocess.DEVNULL)
        res = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(res["imagesLoaded"]); self.assertEqual(res["failedRequests"], [])
        self.assertIn("view=presenter", res["presenterUrl"]); self.assertIn("Presenter view", res["presenterTitle"])


if __name__ == "__main__":
    unittest.main()
