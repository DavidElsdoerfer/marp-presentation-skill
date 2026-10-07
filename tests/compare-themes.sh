#!/usr/bin/env bash
# Rendert ein Deck mit zwei Themes als PNG und vergleicht byteweise.
# Aufruf: tests/compare-themes.sh <deck.md> <altes-theme.css> <neues-theme.css>
set -euo pipefail
[ $# -eq 3 ] || { echo "Aufruf: $0 <deck.md> <alt.css> <neu.css>"; exit 2; }
deck=$1; old=$2; new=$3
export CHROME_PATH=${CHROME_PATH:-/usr/bin/google-chrome}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/old" "$tmp/new"
for v in old new; do
  css=$([ $v = old ] && echo "$old" || echo "$new")
  npx -y @marp-team/marp-cli@4.1.2 --theme-set "$css" --allow-local-files --html \
    --images png -o "$tmp/$v/s.png" "$deck" >/dev/null 2>&1
done
n=0; bad=0
for f in "$tmp"/old/*.png; do
  n=$((n+1)); b=$(basename "$f")
  cmp -s "$f" "$tmp/new/$b" || { echo "DIFF $b"; bad=$((bad+1)); }
done
echo "$((n-bad)) von $n Folien identisch"
[ $bad -eq 0 ]
