#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "ERROR: deploy pushes are allowed only from main" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain=v1)" ]]; then
  echo "ERROR: commit or classify every local change before pushing" >&2
  git status --short
  exit 1
fi

git fetch --prune origin
read -r behind ahead < <(git rev-list --left-right --count origin/main...main)
if [[ "$behind" != "0" ]]; then
  echo "ERROR: local main is behind origin/main by $behind commit(s)" >&2
  exit 1
fi
if [[ "$ahead" == "0" ]]; then
  echo "main is already synchronized; no deployment push is needed"
  exit 0
fi

sha="$(git rev-parse HEAD)"
git push origin main
echo "Pushed $sha. Cloud Build Trigger owns build, candidate checks, and promotion."
