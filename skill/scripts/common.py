"""Gemeinsame Hilfen der Skill-Skripte (nur Standardbibliothek)."""
import os, shutil, subprocess, sys
from pathlib import Path

# Einzige Stelle für die gepinnte, getestete marp-cli-Version.
MARP_CLI_VERSION = "4.1.2"

SKILL = Path(__file__).resolve().parent.parent

# Ordner- und Dateinamen sind reines ASCII (weltweit tätige Konzerne, Dateisysteme, Werkzeuge): Umlaute werden umschrieben.
TRANSLIT = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss", "ẞ": "SS", "æ": "ae", "Æ": "Ae",
            "œ": "oe", "Œ": "Oe", "ø": "o", "Ø": "O", "å": "a", "Å": "A", "đ": "d", "Đ": "D", "ł": "l", "Ł": "L", "þ": "th", "Þ": "Th"}


def ascii_fold(text):
    """Umlaute und Akzente in ASCII umschreiben (ä→ae, ß→ss, é→e); nicht umschreibbare Zeichen (z. B. CJK) entfallen."""
    import unicodedata
    for src, dst in TRANSLIT.items():
        text = text.replace(src, dst)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

CHROME_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]


def find_chrome():
    """Pfad zu Chrome/Chromium oder None. CHROME_PATH überschreibt die Suche."""
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for name in CHROME_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    for p in sorted(Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux*/chrome")):
        return str(p)
    return None


def marp_cmd():
    """Kommando-Präfix für das gepinnte marp-cli."""
    return ["npx", "-y", f"@marp-team/marp-cli@{MARP_CLI_VERSION}", "--no-stdin"]


def marp_env():
    env = dict(os.environ)
    chrome = find_chrome()
    if chrome:
        env["CHROME_PATH"] = chrome
    return env


def run_marp(args, cwd=None, check=True, capture=False):
    """Führt marp-cli aus. stdin ist geschlossen (sonst wartet marp-cli ggf. auf Eingabe)."""
    return subprocess.run(
        marp_cmd() + list(args), cwd=cwd, env=marp_env(), check=check,
        stdin=subprocess.DEVNULL, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
