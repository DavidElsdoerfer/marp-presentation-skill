#!/usr/bin/env bash
# Verlinkt skill/ nach ~/.claude/skills/marp-presentation
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
dest=${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/marp-presentation
mkdir -p "$(dirname "$dest")"
if [ -e "$dest" ] && [ ! -L "$dest" ]; then
  echo "$dest existiert und ist kein Symlink — abgebrochen" >&2; exit 1
fi
ln -sfn "$here/skill" "$dest"
echo "verlinkt: $dest -> $here/skill"
