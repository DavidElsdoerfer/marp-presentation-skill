"""Regressionstests zu den Befunden des unabhängigen Reviews (Sicherheit, Fehlerpfade, Doku-Zusagen)."""
import json, os, re, shutil, signal, subprocess, sys, tempfile, time, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(ROOT / "tests"))
import brand_import as bi  # noqa: E402
import brand_preview as bp  # noqa: E402
import deck_import as di  # noqa: E402
import pptx_extract as px  # noqa: E402
import template_factory as tf  # noqa: E402
import importlib.machinery, importlib.util  # noqa: E402

CLI = SCRIPTS / "marp-deck"
loader = importlib.machinery.SourceFileLoader("marp_deck_rev", str(CLI))
spec = importlib.util.spec_from_loader("marp_deck_rev", loader)
md = importlib.util.module_from_spec(spec); loader.exec_module(md)


def cli(*args, env=None, cwd=None, timeout=240):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True, env=e, cwd=cwd,
                          stdin=subprocess.DEVNULL, timeout=timeout)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        self.env = {"MARP_BRANDS_DIR": str(self.t / "store")}

    def tearDown(self):
        self.tmp.cleanup()

    def new_deck(self, title="Review Deck"):
        r = cli("new", title, "--dir", self.t, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.t / md.slugify(title)


class ConfigIsCode(Base):
    """Befund 1: marp.config.mjs wird von marp-cli als JavaScript ausgeführt."""

    def test_unpack_never_takes_config_from_archive(self):
        deck = self.new_deck()
        cli("pack", deck, env=self.env)
        arc = self.t / "review-deck.deck"
        evil = self.t / "evil.deck"
        with zipfile.ZipFile(arc) as zin, zipfile.ZipFile(evil, "w") as zout:
            for n in zin.namelist():
                zout.writestr(n, "import {writeFileSync} from 'fs'; writeFileSync('PWNED','x'); export default {};" if n.endswith("marp.config.mjs") else zin.read(n))
        out = self.t / "out"; out.mkdir()
        self.assertEqual(cli("unpack", evil, "--dir", out, env=self.env).returncode, 0)
        self.assertEqual((out / "review-deck" / "marp.config.mjs").read_text(), md.CONFIG)

    def test_modified_config_refused_for_export_and_serve(self):
        deck = self.new_deck()
        (deck / "marp.config.mjs").write_text("export default {}; // geändert\n")
        for sub in (["export", "html"], ["serve"]):
            r = cli(*sub, deck, env=self.env)
            self.assertNotEqual(r.returncode, 0, sub)
            self.assertIn("Standard-Config", r.stderr)
            self.assertIn("--trust-config", r.stderr)
        self.assertFalse((self.t / "PWNED").exists())

    def test_repair_config(self):
        deck = self.new_deck()
        (deck / "marp.config.mjs").write_text("böse")
        self.assertEqual(cli("repair-config", deck, env=self.env).returncode, 0)
        self.assertEqual((deck / "marp.config.mjs").read_text(), md.CONFIG)


class UnpackState(Base):
    """Befunde 3 und 18: Zustands- und Build-Verzeichnisse aus Archiven."""

    def test_unpack_drops_state_build_and_git(self):
        deck = self.new_deck()
        cli("pack", deck, env=self.env)
        arc = self.t / "review-deck.deck"
        evil = self.t / "evil2.deck"
        with zipfile.ZipFile(arc) as zin, zipfile.ZipFile(evil, "w") as zout:
            for n in zin.namelist():
                zout.writestr(n, zin.read(n))
            zout.writestr("review-deck/.marp-deck/serve.json", json.dumps({"pid": 1234, "port": "1@evil.example:80/x#"}))
            zout.writestr("review-deck/.git/config", "[core]\n fsmonitor = touch PWNED\n")
            zout.writestr("review-deck/dist/x.html", "<script></script>")
            zout.writestr("review-deck/node_modules/x/index.js", "x")
        out = self.t / "out2"; out.mkdir()
        self.assertEqual(cli("unpack", evil, "--dir", out, env=self.env).returncode, 0)
        d = out / "review-deck"
        for gone in (".marp-deck", ".git", "dist", "node_modules"):
            self.assertFalse((d / gone).exists(), gone)

    def test_read_state_validates(self):
        deck = self.new_deck()
        state = deck / ".marp-deck"; state.mkdir()
        for bad in ({"pid": 1, "port": 8080}, {"pid": 0, "port": 8080}, {"pid": "12", "port": 8080}, {"pid": 99999, "port": "1@x:80/#"},
                    {"pid": 99999, "port": 0}, {"pid": 99999, "port": 70000}, {"pid": True, "port": 80}, {"pid": 5}, [1, 2], "x"):
            (state / "serve.json").write_text(json.dumps(bad))
            self.assertIsNone(md.read_state(deck), bad)
        (state / "serve.json").write_text("kein json")
        self.assertIsNone(md.read_state(deck))
        (state / "serve.json").write_text(json.dumps({"pid": 4242, "port": 8123}))
        st = md.read_state(deck)
        self.assertEqual((st["pid"], st["port"]), (4242, 8123))
        self.assertTrue(st["url"].startswith("http://localhost:8123/"))       # URL aus validierten Zahlen, nie aus der Datei

    def test_stop_does_not_kill_foreign_process(self):
        """Eine PID aus der Zustandsdatei, die nicht zu unserem marp-Server gehört, darf nie beendet werden."""
        deck = self.new_deck()
        victim = subprocess.Popen(["sleep", "300"], start_new_session=True)
        try:
            (deck / ".marp-deck").mkdir()
            (deck / ".marp-deck" / "serve.json").write_text(json.dumps({"pid": victim.pid, "port": 8999}))
            r = cli("serve", deck, "--stop", env=self.env)
            self.assertEqual(r.returncode, 0, r.stderr)
            time.sleep(0.3)
            self.assertIsNone(victim.poll(), "fremder Prozess wurde beendet")
            self.assertIn("ignoriert", r.stdout)
        finally:
            os.killpg(victim.pid, signal.SIGKILL); victim.wait()


class PptxStringsAreData(Base):
    """Befund 4 und 2: Farben, Schriften und Namen aus der PPTX dürfen kein CSS/Markdown/HTML einschleusen."""

    def evil_pptx(self):
        src = tf.build(self.t / "ok.pptx")
        out = self.t / "evil.pptx"
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
            for n in zin.namelist():
                d = zin.read(n)
                if n == "ppt/theme/theme1.xml":
                    d = d.decode().replace('<a:dk1><a:srgbClr val="1B1B1B"/>', '<a:dk1><a:srgbClr val="1B1B1B; } @import url(https://evil.example/x.css); :root { --x: 1"/>') \
                        .replace('typeface="Verdana"', 'typeface="x&quot;; } body{background:url(https://evil.example/b.png)} :root{--y:&quot;"').encode()
                if n == "ppt/slideLayouts/slideLayout2.xml":
                    d = d.decode().replace('name="Titel und Inhalt"', 'name="Nur Titel */ body{background:red} /*&lt;iframe src=&quot;file:///etc/hostname&quot;&gt;"').encode()
                zout.writestr(n, d)
        return out

    def test_extract_sanitizes(self):
        data = px.extract(self.evil_pptx())
        self.assertNotIn(";", data["theme"]["colors"]["dk1"]); self.assertRegex(data["theme"]["colors"]["dk1"], r"^#[0-9a-f]{6}$")
        font = data["theme"]["fonts"]["minor"]
        self.assertNotRegex(font, r"[\"';{}()]")
        name = data["layouts"][1]["name"]
        for bad in ("<", ">", "*/", "/*", '"', "{", "("):
            self.assertNotIn(bad, name)

    def test_import_output_is_inert(self):
        out = self.t / "evil-brand"
        bi.import_brand(self.evil_pptx(), "evil", out, render=False)
        css = self.t / "evil.css"
        r = subprocess.run([sys.executable, str(SCRIPTS / "build-theme.py"), str(out), str(css)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = css.read_text()
        self.assertNotIn("https://", text); self.assertNotIn("@import", text); self.assertNotIn("body{background:red}", text); self.assertNotIn("body {background:red}", text)
        self.assertNotIn("<iframe", text); self.assertNotIn("file:///", text); self.assertNotIn("url(http", text)
        for line in text.splitlines():                       # Layoutnamen stehen nur in Kommentaren, die nicht vorzeitig enden
            if line.startswith("/* ── ") and " → " in line:
                self.assertEqual(line.count("*/"), 1, line)
        font_line = next(l for l in text.splitlines() if l.strip().startswith("--font:"))
        self.assertRegex(font_line, r'^\s*--font:\s*"[\w .+\-]+", sans-serif', "Schriftname bleibt ein einziger, harmloser Textwert")
        self.assertRegex(next(l for l in text.splitlines() if l.strip().startswith("--text:")), r"--text: #[0-9a-f]{6};")
        self.assertNotIn("<iframe", (out / "layouts.md").read_text()); self.assertNotIn("file:///", (out / "layouts.md").read_text())
        meta = bp.load_meta(out)
        pm = bp.preview_markdown(meta); self.assertNotIn("<iframe", pm); self.assertNotIn("file:///", pm)

    def test_preview_escapes_old_brands_too(self):
        meta = {"name": "x", "preview": [{"class": "content", "layout": 'A <iframe src="file:///etc/hostname"> *b* `c`', "index": 0,
                                          "title": True, "subtitle": False, "slots": 0, "flow_body": True, "meta": False}]}
        md_text = bp.preview_markdown(meta)
        self.assertNotIn("<iframe", md_text); self.assertNotIn("file:///", md_text)

    def test_font_and_color_helpers(self):
        self.assertEqual(px.safe_font('Arial"; }'), "Arial")
        self.assertEqual(px.safe_font("Calibri Light"), "Calibri Light")
        self.assertEqual(px.safe_hex("zzzzzz"), "000000"); self.assertEqual(px.safe_hex("AbC123"), "AbC123")
        self.assertEqual(px.safe_text("a\nb\x00 <c>"), "a b c")

    def test_invalid_slide_size(self):
        src = tf.build(self.t / "ok2.pptx")
        out = self.t / "cy0.pptx"
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
            for n in zin.namelist():
                d = zin.read(n)
                zout.writestr(n, d.decode().replace('cy="6858000"/><p:notesSz', 'cy="0"/><p:notesSz').encode() if n == "ppt/presentation.xml" else d)
        with self.assertRaises(px.PptxError):
            px.extract(out)


class BrandResolution(Base):
    def test_snapshot_does_not_follow_symlinks(self):
        """Befund 9: Symlinks im Brand dürfen Ziele nicht ins Deck (und .deck) kopieren."""
        secret = self.t / "geheim.txt"; secret.write_text("TOPSECRET")
        brand = self.t / "store" / "sym"; shutil.copytree(ROOT / "skill/brands/neutral", brand)
        os.symlink(secret, brand / "assets" / "notes.txt")
        r = cli("new", "Sym", "--brand", "sym", "--dir", self.t, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        deck = self.t / "sym"
        self.assertFalse((deck / "theme" / "brand" / "assets" / "notes.txt").exists())
        cli("pack", deck, env=self.env)
        self.assertNotIn(b"TOPSECRET", b"".join(zipfile.ZipFile(self.t / "sym.deck").read(n) for n in zipfile.ZipFile(self.t / "sym.deck").namelist()))

    def test_exclude_only_top_level(self):
        """Befund 24: assets/reference/ o. ä. darf nicht aus dem Snapshot fallen."""
        brand = self.t / "store" / "tl"; shutil.copytree(ROOT / "skill/brands/neutral", brand)
        (brand / "assets" / "reference").mkdir(); (brand / "assets" / "reference" / "bild.png").write_bytes(b"x")
        (brand / "reference").mkdir(); (brand / "reference" / "o.png").write_bytes(b"x")
        self.assertEqual(cli("new", "Tl", "--brand", "tl", "--dir", self.t, env=self.env).returncode, 0)
        snap = self.t / "tl" / "theme" / "brand"
        self.assertTrue((snap / "assets" / "reference" / "bild.png").is_file())
        self.assertFalse((snap / "reference").exists())

    def test_names_validated(self):
        for bad in ("../x", "a/b", ".", "..", "x y/z", "-rf"):
            r = cli("new", "T", "--slug", bad, "--dir", self.t, env=self.env)
            self.assertNotEqual(r.returncode, 0, bad)
        pptx = tf.build(self.t / "v.pptx")
        for bad in ("../escaped", "a/b", ".."):
            r = cli("brand", "import", pptx, "--name", bad, "--no-render", env=self.env)
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertFalse((self.t / "escaped").exists())
            self.assertFalse((self.t / "store" / ".." / "escaped").exists())

    def test_title_with_backslash_and_newline(self):
        deck = self.new_deck("Pfad C:\\temp\\neu")
        text = (deck / f"{deck.name}.md").read_text()
        head = text.split("---")[1]
        self.assertIn('footer: "Pfad C:\\\\temp\\\\neu"', head)           # gültiges YAML (Backslash maskiert)
        deck2 = self.t / "x"
        r = cli("new", "Zeile eins\nZeile zwei", "--slug", "zwei", "--dir", self.t, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('footer: "Zeile eins Zeile zwei"', (self.t / "zwei" / "zwei.md").read_text())

    def test_failed_new_leaves_no_deck(self):
        brand = self.t / "store" / "nolog"; shutil.copytree(ROOT / "skill/brands/neutral", brand)
        (brand / "assets" / "logo.svg").unlink()
        r = cli("new", "Kaputt", "--brand", "nolog", "--dir", self.t, env=self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.t / "kaputt").exists())
        (brand / "assets" / "logo.svg").write_bytes((ROOT / "skill/brands/neutral/assets/logo.svg").read_bytes())
        self.assertEqual(cli("new", "Kaputt", "--brand", "nolog", "--dir", self.t, env=self.env).returncode, 0)   # Retry möglich


class ImportErrorsAndReplace(Base):
    def setUp(self):
        super().setUp()
        self.pptx = tf.build(self.t / "v.pptx")

    def test_missing_guideline_leaves_nothing(self):
        r = cli("brand", "import", self.pptx, "--name", "gl", "--guidelines", self.t / "gibtsnicht.pdf", "--no-render", env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertIn("nicht gefunden", r.stderr)
        self.assertFalse((self.t / "store" / "gl").exists())
        self.assertNotIn("Traceback", r.stderr)

    def test_missing_media_is_a_warning_not_a_crash(self):
        nomedia = self.t / "nomedia.pptx"
        with zipfile.ZipFile(self.pptx) as zin, zipfile.ZipFile(nomedia, "w") as zout:
            for n in zin.namelist():
                if n != "ppt/media/logo.png":
                    zout.writestr(n, zin.read(n))
        res = bi.import_brand(nomedia, "nm", self.t / "nm", render=False)
        self.assertTrue(any("fehlt im Paket" in w for w in res["warnings"]))

    def test_unexpected_error_cleans_up(self):
        broken = self.t / "broken.pptx"
        with zipfile.ZipFile(self.pptx) as zin, zipfile.ZipFile(broken, "w") as zout:
            for n in zin.namelist():
                zout.writestr(n, b"<kein xml" if n == "ppt/slideMasters/slideMaster1.xml" else zin.read(n))
        r = cli("brand", "import", broken, "--name", "br", "--no-render", env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertNotIn("Traceback", r.stderr)
        self.assertFalse((self.t / "store" / "br").exists())

    def test_replace_keeps_handwork_and_backs_up(self):
        self.assertEqual(cli("brand", "import", self.pptx, "--name", "rp", "--no-render", env=self.env).returncode, 0)
        brand = self.t / "store" / "rp"
        (brand / "custom.css").write_text("section.x { color: red; }\n")
        (brand / "GUIDELINES.md").write_text("# Regeln\n- Logo braucht Abstand\n")
        r = cli("brand", "import", self.pptx, "--name", "rp", "--no-render", env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertIn("--replace", r.stderr)
        self.assertEqual((brand / "custom.css").read_text(), "section.x { color: red; }\n")   # unangetastet
        r = cli("brand", "import", self.pptx, "--name", "rp", "--no-render", "--replace", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((brand / "custom.css").read_text(), "section.x { color: red; }\n")
        self.assertIn("Logo braucht Abstand", (brand / "GUIDELINES.md").read_text())
        backups = [p for p in (self.t / "store").iterdir() if ".bak-" in p.name]
        self.assertEqual(len(backups), 1)
        self.assertEqual([p for p in (self.t / "store").iterdir() if ".neu-" in p.name], [])

    def test_failed_replace_keeps_old_brand(self):
        self.assertEqual(cli("brand", "import", self.pptx, "--name", "rf", "--no-render", env=self.env).returncode, 0)
        brand = self.t / "store" / "rf"; (brand / "custom.css").write_text("ALT")
        r = cli("brand", "import", self.t / "nix.pptx", "--name", "rf", "--no-render", "--replace", env=self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((brand / "custom.css").read_text(), "ALT")
        self.assertEqual([p.name for p in (self.t / "store").iterdir()], ["rf"])


class Classification(Base):
    def test_closing_needs_whole_word(self):
        for name in ("Agenda", "Calendar", "Trend", "Vendor", "Attendees", "Weekend plan"):
            self.assertIsNone(bi.CLOSING_RE.search(name), name)
        for name in ("Closing", "End", "Danke", "Thank you", "Abschluss", "Fragen?", "Kontakt", "THE END"):
            self.assertIsNotNone(bi.CLOSING_RE.search(name), name)

    def test_agenda_custom_layout_does_not_become_closing(self):
        src = tf.build(self.t / "k.pptx")
        out = self.t / "k2.pptx"
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
            for n in zin.namelist():
                d = zin.read(n)
                if n == "ppt/slideLayouts/slideLayout3.xml":
                    d = d.decode().replace('name="Zwei Inhalte"', 'name="Agenda"').replace('type="twoObj"', 'type="cust"').encode()
                zout.writestr(n, d)
        res = bi.import_brand(out, "k", self.t / "kb", render=False)
        self.assertNotEqual(res["semantic"].get("closing", "").split(" ")[0], "Agenda")

    def test_reference_folder_sorted_naturally(self):
        names = [Path(f"{i}.png") for i in (10, 2, 1, 12, 3)]
        self.assertEqual([p.name for p in bi.natural_sorted(names)], ["1.png", "2.png", "3.png", "10.png", "12.png"])


class DeckImportMapping(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        (self.t / "w" / "a").mkdir(parents=True); (self.t / "w" / "b").mkdir()
        (self.t / "w" / "a" / "img.png").write_bytes(b"A"); (self.t / "w" / "b" / "img.png").write_bytes(b"B")
        (self.t / "w" / "my pic.png").write_bytes(b"P")
        self.assets = self.t / "deck" / "assets"

    def tearDown(self):
        self.tmp.cleanup()

    def run_md(self, body):
        return di.move_images(body, [self.t / "w"], self.assets)

    def test_same_basename_in_two_folders_not_merged(self):
        out, missing, _ = self.run_md("![](a/img.png)\n![](b/img.png)\n")
        self.assertEqual(missing, [])
        refs = re.findall(r"\]\((assets/[^)]+)\)", out)
        self.assertEqual(len(set(refs)), 2)
        self.assertEqual(sorted((self.t / "deck" / r).read_bytes() for r in refs), [b"A", b"B"])

    def test_url_encoded_and_html_variants(self):
        out, missing, _ = self.run_md('![](my%20pic.png)\n<img src="my pic.png">\n')
        self.assertEqual(missing, [])
        self.assertEqual(out.count("assets/my pic.png"), 2)

    def test_dangerous_schemes_blocked(self):
        out, missing, blocked = self.run_md('![](file:///etc/hostname)\n<img src="javascript:alert(1)">\n![](ftp://x/y.png)\n')
        self.assertNotIn("file:///", out); self.assertNotIn("javascript:", out)
        self.assertEqual(len(blocked), 3)

    def test_ambiguous_basename_reported_missing(self):
        _, missing, _ = self.run_md("![](img.png)\n")
        self.assertEqual(missing, ["img.png"])


class PackEdgeCases(Base):
    def test_pack_with_pre_1980_mtime(self):
        deck = self.new_deck("Alt")
        old = deck / "assets" / "alt.md"; old.write_text("x"); os.utime(old, (0, 0))
        r = cli("pack", deck, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.t / "alt.deck.tmp").exists())


class SnapshotBackup(Base):
    def test_sync_backs_up_hand_changes(self):
        brand = self.t / "store" / "sb"; shutil.copytree(ROOT / "skill/brands/neutral", brand)
        json_p = brand / "brand.json"; meta = json.loads(json_p.read_text()); meta["name"] = "sb"; json_p.write_text(json.dumps(meta))
        self.assertEqual(cli("new", "Sb", "--brand", "sb", "--dir", self.t, env=self.env).returncode, 0)
        deck = self.t / "sb"
        (deck / "theme" / "brand" / "custom.css").write_text("section { color: red; }\n")     # Handänderung im Deck
        r = cli("brand", "sync", deck, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Sicherung", r.stderr)
        backups = list((deck / ".marp-deck").glob("brand-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "custom.css").read_text(), "section { color: red; }\n")
        r = cli("brand", "sync", deck, env=self.env)                          # ohne Änderung keine weitere Sicherung
        self.assertEqual(len(list((deck / ".marp-deck").glob("brand-backup-*"))), 1)


if __name__ == "__main__":
    unittest.main()
