"""Render-Test: Fixture-Deck mit neutral bauen und als PNG rendern. Überspringt ohne Chrome/Node."""
import re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skill" / "scripts"))
from common import find_chrome, run_marp  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "all-classes.md"


def expected_slides(md):
    body = md.split("---", 2)[2]  # Frontmatter abtrennen
    return len(re.findall(r"^---\s*$", body, flags=re.M)) + 1


@unittest.skipUnless(find_chrome(), "Chrome/Chromium nicht gefunden")
class RenderFixture(unittest.TestCase):
    def test_all_slides_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            subprocess.run([sys.executable, str(ROOT / "skill/scripts/build-theme.py"), "neutral", str(tmp / "t.css")], check=True)
            run_marp(["--allow-local-files", "--html", "--theme-set", str(tmp / "t.css"), "--images", "png",
                      "-o", str(tmp / "s.png"), str(FIXTURE)], capture=True)
            pngs = sorted(tmp.glob("s.*.png"))
            self.assertEqual(len(pngs), expected_slides(FIXTURE.read_text()))
            self.assertTrue(all(p.stat().st_size > 2000 for p in pngs))


if __name__ == "__main__":
    unittest.main()
