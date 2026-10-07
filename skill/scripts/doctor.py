#!/usr/bin/env python3
"""Prüft die Voraussetzungen des Skills. Exit-Code 1, wenn Pflicht-Voraussetzungen fehlen."""
import re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MARP_CLI_VERSION, find_chrome

rows = []  # (status, name, detail)


def add(status, name, detail):
    rows.append((status, name, detail))


def version(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL).stdout.strip().splitlines()[0]
    except Exception:
        return None


if sys.version_info >= (3, 9):
    add("ok", "python", sys.version.split()[0])
else:
    add("FEHLT", "python", f"{sys.version.split()[0]} — mindestens 3.9 nötig")

node = shutil.which("node")
if node:
    v = version([node, "--version"]) or "?"
    major = int(re.sub(r"\D.*", "", v.lstrip("v")) or 0)
    add("ok" if major >= 18 else "FEHLT", "node", f"{v}" + ("" if major >= 18 else " — mindestens 18 nötig"))
else:
    add("FEHLT", "node", "nicht installiert (für npx @marp-team/marp-cli)")
add("ok" if shutil.which("npx") else "FEHLT", "npx", shutil.which("npx") or "nicht gefunden")

cache = list(Path.home().glob(".npm/_npx/*/node_modules/@marp-team/marp-cli/package.json"))
cached = [p for p in cache if f'"version": "{MARP_CLI_VERSION}"' in p.read_text()]
add("ok" if cached else "warn", f"marp-cli {MARP_CLI_VERSION}",
    "im npx-Cache" if cached else "noch nicht geladen — wird beim ersten Aufruf per npx installiert (Netzwerk nötig)")

chrome = find_chrome()
add("ok" if chrome else "FEHLT", "chrome/chromium", chrome or "nicht gefunden — PDF/PNG-Export unmöglich (CHROME_PATH setzen)")

for tool, why in [("soffice", "LibreOffice: PPTX-Layouts als Hintergrund rendern (CI-Import, optional)"),
                  ("pdftocairo", "PDF → SVG/PNG für CI-Import (optional)"),
                  ("montage", "ImageMagick: Kontaktbögen/Differenzbilder (optional)"),
                  ("fc-list", "Schriftprüfung (optional)")]:
    p = shutil.which(tool)
    add("ok" if p else "warn", tool, p or f"nicht gefunden — {why}")

w = max(len(r[1]) for r in rows)
for status, name, detail in rows:
    print(f"[{status:5}] {name:<{w}}  {detail}")
fail = [r for r in rows if r[0] == "FEHLT"]
print("\nPflicht-Voraussetzungen erfüllt." if not fail else f"\n{len(fail)} Pflicht-Voraussetzung(en) fehlen.")
sys.exit(1 if fail else 0)
