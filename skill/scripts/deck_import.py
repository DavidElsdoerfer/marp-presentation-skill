#!/usr/bin/env python3
"""Adapter: bestehende PowerPoint-Präsentation → Marp-Deck (optional, über das Werkzeug `pptx2md`).

Übernommen werden Inhalte (Titel, Text, Listen, Tabellen, Bilder, Sprechernotizen), nicht das Layout: alle Folien erhalten
die Standard-Inhaltsklasse des gewählten Brands; Abschnitte, Spalten und Sonderlayouts ordnest du danach zu.

`pptx2md` (Fork mit Marp-Ausgabe, Apache-2.0) ist keine Abhängigkeit des Skills: Installation in einer eigenen
virtuellen Umgebung (siehe docs/import-workflow.md), Pfad per `--tool` oder Umgebungsvariable `PPTX2MD`.

Die Ausgabe des Werkzeugs wird nachbearbeitet: Frontmatter und CSS-Block ersetzt (inkl. Google-Fonts-@import, der beim
Öffnen Anfragen ins Internet senden würde), Titelfolie angepasst, Bilder nach assets/ verschoben.
"""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}

# Kleine, lokale Stilregeln für Konstrukte, die pptx2md erzeugt (Bildausrichtung per alt-Text, Spalten, Schriftstufen).
COMPAT_STYLE = """<style>
/* Kompatibilität zur Ausgabe von pptx2md (lokal, ohne externe Ressourcen) */
img[alt~="center"] { display: block; margin: 0 auto; }
img[alt~="left"] { float: left; margin: 0 1em 0.5em 0; }
img[alt~="right"] { float: right; margin: 0 0 0.5em 1em; }
.columns { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2em; }
.columns > div { overflow: hidden; }
.abs-pos { position: absolute; }
section.small { font-size: 0.9em; }
section.smaller { font-size: 0.8em; }
section.smallest { font-size: 0.72em; }
</style>
"""


class DeckImportError(Exception):
    pass


def find_tool(explicit=None):
    cand = explicit or os.environ.get("PPTX2MD") or shutil.which("pptx2md")
    if not cand or not Path(cand).exists() and not shutil.which(str(cand)):
        raise DeckImportError(
            "pptx2md nicht gefunden. Installation in einer eigenen Umgebung, z. B.:\n"
            "  python3 -m venv ~/.local/share/pptx2md && ~/.local/share/pptx2md/bin/pip install "
            "git+https://github.com/OscarPellicer/python-pptx.git git+https://github.com/OscarPellicer/pptx2marp.git\n"
            "dann --tool ~/.local/share/pptx2md/bin/pptx2md angeben (oder PPTX2MD setzen). "
            "Hinweis: braucht den python-pptx-Fork sowie numpy/scipy; das Projekt ist seit 2025-10 nicht mehr aktualisiert.")
    return str(cand)


def split_frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[4:end], text[end + 5:]
    return "", text


def strip_converter_header(body):
    """Entfernt CSS-Block(e) und den Anleitungskommentar am Anfang; liefert nur die Folien."""
    body = re.sub(r"\A\s*(<style>.*?</style>\s*)+", "", body, flags=re.S)
    body = re.sub(r"\A\s*<!--\s*MANUAL LAYOUT USAGE EXAMPLES:.*?-->\s*", "", body, flags=re.S)
    return body.lstrip("\n")


def retitle_first_slide(body):
    """Titelfolie: Klasse `title`, erste Überschrift bleibt `#`, die zweite (Untertitel) wird `##`."""
    parts = re.split(r"\n---\s*\n", body, maxsplit=1)
    first = parts[0]
    heads = list(re.finditer(r"^# (.*)$", first, flags=re.M))
    if not heads or "_class:" in first:
        return body, False
    if len(heads) >= 2:
        h = heads[1]
        first = first[:h.start()] + "## " + h.group(1) + first[h.end():]
    first = "<!-- _class: title -->\n\n" + first.lstrip("\n")
    return first + ("\n---\n" + parts[1] if len(parts) == 2 else ""), True


def move_images(body, search_roots, assets):
    """Kopiert referenzierte Bilder nach assets/ und schreibt die Pfade im Markdown um.

    Zuordnung über den relativen Pfad unterhalb der Suchwurzeln (Basisname nur, wenn eindeutig). URL-kodierte Pfade
    (%20) werden dekodiert. Gefährliche Schemata (file:, javascript: …) werden entfernt und gemeldet.
    """
    from urllib.parse import unquote
    assets.mkdir(parents=True, exist_ok=True)
    roots = [Path(r).resolve() for r in search_roots]
    by_rel, by_name = {}, {}
    for r in roots:
        for p in sorted(r.rglob("*")):
            if p.is_file() and not p.is_symlink() and p.suffix.lower() in IMAGE_EXT:
                by_rel.setdefault(p.relative_to(r).as_posix(), p)
                by_name.setdefault(p.name, []).append(p)
    used, missing, blocked = {}, [], []

    def lookup(ref):
        norm = posixpath_norm(unquote(ref))
        if norm in by_rel:
            return by_rel[norm]
        # relative Angabe, die mit dem Pfad unterhalb der Wurzel endet (oder umgekehrt) — nur wenn eindeutig
        hits = [p for rel, p in by_rel.items() if rel.endswith("/" + norm) or norm.endswith("/" + rel)]
        if len(hits) == 1:
            return hits[0]
        if hits:
            return None
        cands = by_name.get(Path(norm).name, [])
        return cands[0] if len(cands) == 1 else None

    def target_for(ref):
        src = lookup(ref)
        if src is None:
            missing.append(ref)
            return None
        key = str(src)
        if key not in used:
            name = src.name
            dst = assets / name
            n = 1
            while dst.exists():                       # nie ein vorhandenes Bild überschreiben
                dst = assets / f"{Path(name).stem}-{n}{Path(name).suffix}"
                n += 1
            shutil.copy(src, dst)
            used[key] = f"assets/{dst.name}"
        return used[key]

    def sub(m):
        ref = m.group("p")
        if re.match(r"^(https?:|data:|assets/)", ref):
            return m.group(0)
        if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", ref):       # file:, javascript:, ftp: …
            blocked.append(ref)
            return f"{m.group('pre')}about:blank{m.group('post')}"
        new = target_for(ref)
        return m.group(0) if new is None else f"{m.group('pre')}{new}{m.group('post')}"

    body = re.sub(r"(?P<pre>!\[[^\]]*\]\()(?P<p>[^)\s]+)(?P<post>[^)]*\))", sub, body)
    body = re.sub(r"""(?P<pre>\bsrc=["'])(?P<p>[^"']+)(?P<post>["'])""", sub, body)
    return body, sorted(set(missing)), sorted(set(blocked))


def posixpath_norm(ref):
    import posixpath
    ref = ref.replace("\\", "/")
    while ref.startswith("./"):
        ref = ref[2:]
    return posixpath.normpath(ref) if ref else ref


def build_markdown(raw, frontmatter, search_roots, assets):
    _, body = split_frontmatter(raw)
    body = strip_converter_header(body)
    body, titled = retitle_first_slide(body)
    body, missing, blocked = move_images(body, search_roots, assets)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    slides = len(re.split(r"\n---\s*\n", body))
    return f"---\n{frontmatter}---\n\n{COMPAT_STYLE}\n{body}", {"slides": slides, "title_slide": titled, "missing_images": missing, "blocked_refs": blocked}


def convert(pptx, tool, workdir):
    """Ruft pptx2md auf; liefert (Markdown-Datei, Bildordner)."""
    out, imgs = Path(workdir) / "out", Path(workdir) / "imgs"
    out.mkdir(parents=True); imgs.mkdir()
    # cwd = Arbeitsordner: pptx2md legt Bildordner sonst relativ zum aktuellen Verzeichnis an
    r = subprocess.run([tool, str(Path(pptx).resolve()), "--marp", "-o", str(out), "-i", str(imgs), "--disable-color", "--min-block-size", "1"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600, cwd=workdir)
    mds = sorted(out.glob("*.md"))
    if r.returncode != 0 or not mds:
        raise DeckImportError(f"pptx2md fehlgeschlagen (Exit {r.returncode}): {(r.stderr or r.stdout).strip()[-400:]}")
    return mds[0], [out, imgs, Path(workdir)]


def main():
    sys.exit("Aufruf über: marp-deck import-deck <datei.pptx> --brand NAME")


if __name__ == "__main__":
    main()
