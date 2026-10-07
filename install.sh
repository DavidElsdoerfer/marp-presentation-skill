#!/usr/bin/env bash
# Verlinkt skill/ als "marp-presentation" in die Skill-Verzeichnisse der Agenten.
#
#   ./install.sh                 ~/.agents/skills (Copilot CLI, andere) + ~/.claude/skills, wenn vorhanden
#   ./install.sh --all           zusätzlich ~/.copilot/skills
#   ./install.sh --target DIR    nur nach DIR/marp-presentation
#   ./install.sh --uninstall     entfernt die Links wieder (nur Symlinks auf dieses Repo)
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
src="$here/skill"
name=marp-presentation
targets=()
mode=install
all=0

while [ $# -gt 0 ]; do
  case "$1" in
    --all) all=1 ;;
    --target) shift; targets+=("$1") ;;
    --uninstall) mode=uninstall ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ ${#targets[@]} -eq 0 ]; then
  targets+=("$HOME/.agents/skills")
  [ -d "$HOME/.claude" ] && targets+=("$HOME/.claude/skills")
  [ $all -eq 1 ] && targets+=("$HOME/.copilot/skills")
fi

for t in "${targets[@]}"; do
  dest="$t/$name"
  if [ "$mode" = uninstall ]; then
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then rm "$dest"; echo "entfernt: $dest"
    else echo "übersprungen (kein Link auf dieses Repo): $dest"; fi
    continue
  fi
  mkdir -p "$t"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "$dest existiert und ist kein Symlink — übersprungen" >&2; continue
  fi
  ln -sfn "$src" "$dest"
  echo "verlinkt: $dest -> $src"
done
