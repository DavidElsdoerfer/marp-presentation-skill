"""Tests für die Integration mit Marp for VS Code (Einstellungen, Aggregation, Archivsicherheit, Plugin-Verhalten)."""
import importlib.machinery, importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
CLI = SCRIPTS / "marp-deck"
loader = importlib.machinery.SourceFileLoader("marp_deck_vs", str(CLI))
spec = importlib.util.spec_from_loader("marp_deck_vs", loader)
md = importlib.util.module_from_spec(spec); loader.exec_module(md)

CORE = next(iter(sorted(Path.home().glob(".npm/_npx/*/node_modules/@marp-team/marp-core"))), None)


def cli(*args, env=None, cwd=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True, env=e, cwd=cwd,
                          stdin=subprocess.DEVNULL, timeout=240)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        self.env = {"MARP_BRANDS_DIR": str(self.t / "store")}
        self.proj = self.t / "projekt"; self.proj.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def deck(self, title, where=None, brand="neutral"):
        r = cli("new", title, "--dir", where or self.proj, "--brand", brand, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return (where or self.proj) / md.slugify(title)

    def settings(self, folder):
        return json.loads((folder / ".vscode" / "settings.json").read_text())


class DeckSettings(Base):
    def test_new_deck_brings_own_settings(self):
        d = self.deck("Eins")
        s = self.settings(d)
        self.assertEqual(s["markdown.marp.themes"], ["theme/theme.css"])
        self.assertEqual(s["markdown.marp.html"], "all")              # sonst zeigt die Vorschau <div>-Komponenten als Text
        self.assertTrue(s["markdown.marp.pdf.noteAnnotations"]); self.assertEqual(s["markdown.marp.pdf.outlines"], "both")
        self.assertTrue((d / "theme" / "theme.css").is_file())        # der Pfad zeigt auf eine vorhandene Datei im Deck

    def test_pack_unpack_keeps_settings_but_never_takes_them_from_archive(self):
        d = self.deck("Zwei")
        cli("pack", d, env=self.env)
        arc = self.proj / "zwei.deck"
        self.assertIn("zwei/.vscode/settings.json", zipfile.ZipFile(arc).namelist())
        evil = self.t / "evil.deck"
        with zipfile.ZipFile(arc) as zin, zipfile.ZipFile(evil, "w") as zout:
            for n in zin.namelist():
                zout.writestr(n, '{"terminal.integrated.shell.linux": "/tmp/x", "python.defaultInterpreterPath": "/tmp/evil"}' if n.endswith(".vscode/settings.json") else zin.read(n))
            zout.writestr("zwei/.vscode/tasks.json", '{"version":"2.0.0","tasks":[{"label":"x","type":"shell","command":"touch PWNED","runOptions":{"runOn":"folderOpen"}}]}')
            zout.writestr("zwei/.vscode/launch.json", "{}")
        out = self.t / "out"; out.mkdir()
        self.assertEqual(cli("unpack", evil, "--dir", out, env=self.env).returncode, 0)
        v = out / "zwei" / ".vscode"
        self.assertEqual(sorted(p.name for p in v.iterdir()), ["settings.json"])
        self.assertEqual((v / "settings.json").read_text(), md.VSCODE_SETTINGS)


class Aggregate(Base):
    def test_nested_decks_registered_in_project_settings(self):
        a = self.deck("Alpha", self.proj / "vortraege")
        b = self.deck("Beta", self.proj / "vortraege" / "unter")
        r = cli("vscode", self.proj, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.settings(self.proj)
        self.assertEqual(sorted(s["markdown.marp.themes"]), ["vortraege/alpha/theme/theme.css", "vortraege/unter/beta/theme/theme.css"])
        self.assertEqual(s["markdown.marp.html"], "all")
        for p in s["markdown.marp.themes"]:
            self.assertTrue((self.proj / p).is_file(), p)
        before = (self.proj / ".vscode" / "settings.json").read_text()
        r = cli("vscode", self.proj, env=self.env)                     # idempotent
        self.assertIn("bereits aktuell", r.stdout)
        self.assertEqual((self.proj / ".vscode" / "settings.json").read_text(), before)
        self.assertEqual(list((self.proj / ".vscode").glob("*.bak-*")), [])   # nichts geändert → keine Sicherung

    def test_preserves_existing_keys_and_makes_backup(self):
        self.deck("Gamma")
        (self.proj / ".vscode").mkdir()
        (self.proj / ".vscode" / "settings.json").write_text(json.dumps({
            "editor.fontSize": 15, "markdown.marp.html": "default", "markdown.marp.pdf.outlines": "pages",
            "markdown.marp.themes": ["extern/mein.css", "https://example.org/t.css"], "url": "https://x//y", "trick": "a,]"}))
        r = cli("vscode", self.proj, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.settings(self.proj)
        self.assertEqual(s["editor.fontSize"], 15); self.assertEqual(s["url"], "https://x//y"); self.assertEqual(s["trick"], "a,]")
        self.assertEqual(s["markdown.marp.pdf.outlines"], "pages")       # Nutzerwahl bleibt
        self.assertEqual(s["markdown.marp.html"], "all")                 # nötig → gesetzt und gemeldet
        self.assertEqual(s["markdown.marp.themes"][:2], ["extern/mein.css", "https://example.org/t.css"])
        self.assertIn("gamma/theme/theme.css", s["markdown.marp.themes"])
        self.assertIn("fehlende Datei: extern/mein.css", r.stderr)       # tote Einträge werden gemeldet, nicht gelöscht
        self.assertEqual(len(list((self.proj / ".vscode").glob("settings.json.bak-*"))), 1)

    def test_jsonc_with_comments_is_not_rewritten(self):
        self.deck("Delta")
        f = self.proj / ".vscode" / "settings.json"; f.parent.mkdir()
        original = '{\n  // meine Notiz\n  "editor.fontSize": 14,\n}\n'
        f.write_text(original)
        r = cli("vscode", self.proj, env=self.env)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(f.read_text(), original)                        # unverändert
        self.assertIn("delta/theme/theme.css", r.stdout)                 # Zeilen zum Einfügen werden ausgegeben

    def test_trailing_commas_without_comments_are_accepted(self):
        self.deck("Epsilon")
        f = self.proj / ".vscode" / "settings.json"; f.parent.mkdir()
        f.write_text('{"a": [1, 2,], "b": {"c": 1,},}\n')
        self.assertEqual(cli("vscode", self.proj, env=self.env).returncode, 0)
        self.assertEqual(self.settings(self.proj)["a"], [1, 2])

    def test_unparsable_settings_untouched(self):
        self.deck("Zeta")
        f = self.proj / ".vscode" / "settings.json"; f.parent.mkdir()
        f.write_text("{kaputt")
        r = cli("vscode", self.proj, env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertEqual(f.read_text(), "{kaputt")

    def test_same_theme_name_different_content_warns(self):
        a = self.deck("Eta", self.proj / "a"); b = self.deck("Theta", self.proj / "b")
        css = b / "theme" / "theme.css"; css.write_text(css.read_text() + "\n/* abweichender Stand */\n")
        r = cli("vscode", self.proj, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unterschiedlichem Inhalt", r.stderr); self.assertIn("brand sync", r.stderr)

    def test_dry_run_changes_nothing(self):
        self.deck("Iota")
        r = cli("vscode", self.proj, "--dry-run", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("Probelauf", r.stdout)
        self.assertFalse((self.proj / ".vscode").exists())

    def test_project_that_is_itself_a_deck(self):
        d = self.deck("Kappa")
        (d / ".vscode" / "settings.json").unlink()                        # älteres Deck ohne Einstellungen
        r = cli("vscode", d, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.settings(d)["markdown.marp.themes"], ["theme/theme.css"])

    def test_no_decks_is_an_error(self):
        r = cli("vscode", self.proj, env=self.env)
        self.assertNotEqual(r.returncode, 0); self.assertIn("keine Decks", r.stderr)

    def test_ignores_build_and_state_dirs(self):
        d = self.deck("Lambda")
        shutil.copytree(d, self.proj / "dist" / "kopie")
        shutil.copytree(d, self.proj / "node_modules" / "x")
        r = cli("vscode", self.proj, env=self.env)
        self.assertEqual(self.settings(self.proj)["markdown.marp.themes"], ["lambda/theme/theme.css"])


class Jsonc(unittest.TestCase):
    def test_parser(self):
        obj, had = md.parse_jsonc('{"a": "http://x//y", /* c */ "b": [1,2,], // z\n "c": "// kein Kommentar"}')
        self.assertEqual(obj, {"a": "http://x//y", "b": [1, 2], "c": "// kein Kommentar"}); self.assertTrue(had)
        obj, had = md.parse_jsonc('{"a": "x,}", "b": "y,]"}')
        self.assertEqual(obj, {"a": "x,}", "b": "y,]"}); self.assertFalse(had)
        with self.assertRaises(ValueError):
            md.parse_jsonc("{nope")


@unittest.skipUnless(CORE and shutil.which("node"), "marp-core (npx-Cache) oder Node fehlen")
class PluginBehaviour(Base):
    """Stellt nach, wie die Erweiterung Themes registriert (themeSet.add) und HTML filtert — so bleibt die Annahme prüfbar."""

    def run_node(self, css, md_text, html):
        js = f"""
const {{ Marp }} = require({json.dumps(str(CORE))});
const marp = new Marp({{ html: {str(html).lower()} }});
marp.themeSet.add({json.dumps(css)});
const out = marp.render({json.dumps(md_text)});
console.log(JSON.stringify({{ known: !!marp.themeSet.get('neutral'), components: (out.html.match(/<div class="box-header"/g)||[]).length,
  escaped: (out.html.match(/&lt;div class=/g)||[]).length, size: marp.themeSet.getThemeMeta('neutral', 'size') }}));
"""
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_theme_registers_and_html_all_is_required(self):
        d = self.deck("Plugin")
        css = (d / "theme" / "theme.css").read_text()
        text = '---\nmarp: true\ntheme: neutral\n---\n\n# T\n\n<div class="box-header">A</div>\n'
        default = self.run_node(css, text, html=False)       # Standard der Erweiterung (Allowlist)
        self.assertTrue(default["known"]); self.assertEqual(default["components"], 0); self.assertGreater(default["escaped"], 0)
        allhtml = self.run_node(css, text, html=True)         # markdown.marp.html = "all"
        self.assertEqual(allhtml["components"], 1); self.assertEqual(allhtml["escaped"], 0)

    def test_last_theme_with_same_name_wins(self):
        js = f"""
const {{ Marp }} = require({json.dumps(str(CORE))});
const m = new Marp(); m.themeSet.add('/* @theme x */ section{{color:red}}'); m.themeSet.add('/* @theme x */ section{{color:blue}}');
console.log(/color:\\s*blue/.test(m.render('---\\ntheme: x\\n---\\n# a').css));
"""
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.stdout.strip(), "true")


if __name__ == "__main__":
    unittest.main()
