#!/usr/bin/env bash
# Commit and push each Filosofia episode folder separately (smaller pushes).
#
# If remote main already exists with unrelated history, push the current tip once:
#   git push -u origin main --force-with-lease
# then run this script (or set FIRST_FORCE=1 for the first push only — see below).
set -eu
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

REMOTE="${1:-origin}"
BRANCH="${2:-main}"
FIRST_FORCE="${FIRST_FORCE:-0}"

echo "Remote=$REMOTE branch=$BRANCH FIRST_FORCE=$FIRST_FORCE"

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git add .gitignore
  git commit -m "chore: gitignore (.claude and existing rules)"
  if [[ "$FIRST_FORCE" == "1" ]]; then
    git push -u --force-with-lease "$REMOTE" "HEAD:$BRANCH"
  else
    git push -u "$REMOTE" "HEAD:$BRANCH"
  fi
fi

LIST="$(mktemp)"
ls -1 Filosofia | grep -E '^[0-9]' | sort -V > "$LIST"
while IFS= read -r dir; do
  [[ -n "$dir" ]] || continue
  path="Filosofia/${dir}"
  if [[ ! -d "$path" ]]; then
    continue
  fi
  echo "=== $path ==="
  git add "$path/"
  if git diff --cached --quiet; then
    echo "(sin cambios nuevos, omitido)"
    continue
  fi
  git commit -m "Filosofia: ${dir}"
  git push "$REMOTE" "HEAD:$BRANCH"
done < "$LIST"
rm -f "$LIST"

py_count=0
for f in Filosofia/*.py; do
  [[ -f "$f" ]] || continue
  py_count=$((py_count + 1))
done
if [[ "$py_count" -gt 0 ]]; then
  echo "=== Filosofia Python scripts ==="
  git add Filosofia/*.py
  git commit -m "Filosofia: helper scripts (generate_blogs, etc.)"
  git push "$REMOTE" "HEAD:$BRANCH"
fi

echo "Done."
