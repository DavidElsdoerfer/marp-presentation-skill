#!/usr/bin/env bash
# Lauffähige Demo des Prototyps: synthetische Vorlage -> Brand-Import -> Marp-Modell -> PPTX -> (optional) Rendering mit LibreOffice.
#   PYTHON_PPTX=/pfad/zu/venv/bin/python ./run-demo.sh [ausgabeordner]
# Voraussetzungen: python-pptx im angegebenen Python, Node, marp-cli im npx-Cache (siehe doctor.py), optional LibreOffice + pdftocairo.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
out=${1:-$(mktemp -d)}
py=${PYTHON_PPTX:-python3}
"$py" -c "import pptx" 2>/dev/null || { echo "python-pptx fehlt: python3 -m venv v && v/bin/pip install python-pptx, dann PYTHON_PPTX=v/bin/python" >&2; exit 1; }
mkdir -p "$out"
python3 "$repo/tests/template_factory.py" "$out/vorlage.pptx" >/dev/null
MARP_BRANDS_DIR="$out/brands" python3 "$repo/skill/scripts/marp-deck" brand import "$out/vorlage.pptx" --name proto --no-render >/dev/null
node "$here/model.cjs" "$here/demo.md" > "$out/model.json"
"$py" "$here/build.py" "$out/model.json" "$out/brands/proto/brand.json" "$out/vorlage.pptx" "$out/ausgabe.pptx"
if command -v soffice >/dev/null && command -v pdftocairo >/dev/null; then
  soffice --headless --convert-to pdf --outdir "$out" "$out/ausgabe.pptx" >/dev/null 2>&1 </dev/null
  pdftocairo -png -scale-to-x 640 -scale-to-y 360 "$out/ausgabe.pdf" "$out/folie"
  echo "gerendert: $out/folie-*.png"
fi
echo "Ergebnis: $out/ausgabe.pptx"
