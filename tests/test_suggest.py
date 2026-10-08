"""Tests für `marp-deck suggest` (Zielordner und Name vorschlagen; schreibt nichts)."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "skill" / "scripts" / "marp-deck"


def cli(*args, env=None, cwd=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True, env=e, cwd=cwd,
                          stdin=subprocess.DEVNULL, timeout=120)


class Suggest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.t = Path(self.tmp.name)
        self.proj = self.t / "Projekt"; (self.proj / ".git").mkdir(parents=True)
        self.env = {"MARP_BRANDS_DIR": str(self.t / "store")}

    def tearDown(self):
        self.tmp.cleanup()

    def mkdeck(self, name, where):
        r = cli("new", "x", "--slug", name, "--dir", where, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def sg(self, title, *extra, cwd=None):
        r = cli("suggest", title, "--json", *extra, cwd=cwd or self.proj, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_follows_existing_decks_and_naming(self):
        base = self.proj / "Präsentationen"
        self.mkdeck("2026-10-05-Workshop", base); self.mkdeck("2026-10-19-Workshop", base)
        res = self.sg("Agentic AI Einstieg", "--date", "2026-12-01")
        self.assertEqual(Path(res["dir"]), base)
        self.assertEqual(res["slug"], "2026-12-01-Agentic-AI-Einstieg")       # Datum-Präfix und Großschreibung wie vorhandene Decks
        self.assertFalse(res["creates_dir"])
        self.assertTrue(any("vorhandene" in r for r in res["reasons"]))

    def test_lowercase_names_stay_lowercase_without_date(self):
        base = self.proj / "folien"
        self.mkdeck("intro", base); self.mkdeck("deep-dive", base)
        res = self.sg("Noch Ein Vortrag")
        self.assertEqual(res["slug"], "noch-ein-vortrag")

    def test_most_used_folder_wins(self):
        a, b = self.proj / "a", self.proj / "b"
        self.mkdeck("eins", a); self.mkdeck("zwei", a); self.mkdeck("drei", b)
        res = self.sg("Neu")
        self.assertEqual(Path(res["dir"]), a)
        self.assertEqual([Path(p) for p in res["alternatives"]], [b])

    def test_existing_presentation_folder_without_decks(self):
        (self.proj / "docs" / "Präsentationen").mkdir(parents=True)
        res = self.sg("Erster")
        self.assertEqual(Path(res["dir"]), self.proj / "docs" / "Präsentationen")
        self.assertIn("passt zum Zweck", " ".join(res["reasons"]))

    def test_fallback_creates_new_folder_only_in_proposal(self):
        res = self.sg("Allererster")
        self.assertEqual(Path(res["dir"]), self.proj / "presentations")
        self.assertTrue(res["creates_dir"])
        self.assertFalse((self.proj / "presentations").exists())              # schreibt nichts

    def test_no_collision_with_existing_slug(self):
        base = self.proj / "talks"
        self.mkdeck("2026-12-01-Gleich", base); self.mkdeck("2026-11-01-Alt", base)
        res = self.sg("Gleich", "--date", "2026-12-01")
        self.assertEqual(res["slug"], "2026-12-01-Gleich-2")

    def test_works_from_subfolder_and_finds_project_root(self):
        base = self.proj / "Präsentationen"; self.mkdeck("2026-10-05-Workshop", base)
        res = self.sg("Aus Unterordner", "--date", "2026-12-01", cwd=base / "2026-10-05-Workshop")
        self.assertEqual(Path(res["project"]), self.proj)
        self.assertEqual(Path(res["dir"]), base)

    def test_proposed_command_creates_exactly_that_deck(self):
        base = self.proj / "Präsentationen"; self.mkdeck("2026-10-05-Workshop", base)
        res = self.sg("Genau So", "--date", "2026-12-01")
        r = cli("new", "Genau So", "--dir", res["dir"], "--slug", res["slug"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((Path(res["path"]) / f"{res['slug']}.md").is_file())

    def test_text_output_and_bad_input(self):
        r = cli("suggest", "Text Ausgabe", "--date", "2026-12-01", cwd=self.proj, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Vorschlag:", r.stdout); self.assertIn("Anlegen mit:", r.stdout)
        self.assertNotEqual(cli("suggest", "X", "--date", "morgen", cwd=self.proj, env=self.env).returncode, 0)
        self.assertNotEqual(cli("suggest", env=self.env).returncode, 0)

    def test_ignores_decks_in_build_and_dependency_dirs(self):
        self.mkdeck("kopie", self.proj / "node_modules" / "x"); self.mkdeck("kopie2", self.proj / "dist")
        res = self.sg("Neu")
        self.assertEqual(Path(res["dir"]), self.proj / "presentations")


if __name__ == "__main__":
    unittest.main()
