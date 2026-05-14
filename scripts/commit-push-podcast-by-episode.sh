#!/usr/bin/env bash
# Commit and push each episode folder under a podcast root separately (smaller pushes).
#
# Usage:
#   bash scripts/commit-push-podcast-by-episode.sh Historia [remote] [branch]
#   bash scripts/commit-push-podcast-by-episode.sh Libros
#   bash scripts/commit-push-podcast-by-episode.sh Mitologia
#
# If the repo has no commits yet, seeds .gitignore first. If the first push is rejected,
# use FIRST_FORCE=1 (same as the Filosofía helper) or push with --force-with-lease once.
set -eu
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PODCAST="${1:?Usage: $0 <Filosofia|Historia|Libros|Mitologia> [remote] [branch]}"
REMOTE="${2:-origin}"
BRANCH="${3:-main}"
FIRST_FORCE="${FIRST_FORCE:-0}"

case "$PODCAST" in
  Filosofia|Historia|Libros|Mitologia) ;;
  *)
    echo "Unknown podcast folder: $PODCAST" >&2
    exit 1
    ;;
esac

if [[ ! -d "$PODCAST" ]]; then
  echo "Missing directory: $PODCAST" >&2
  exit 1
fi

echo "Podcast=$PODCAST remote=$REMOTE branch=$BRANCH FIRST_FORCE=$FIRST_FORCE"

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
ls -1 "$PODCAST" | grep -E '^[0-9]' | sort -V > "$LIST"
while IFS= read -r dir; do
  [[ -n "$dir" ]] || continue
  path="${PODCAST}/${dir}"
  if [[ ! -d "$path" ]]; then
    continue
  fi
  echo "=== $path ==="
  git add "$path/"
  if git diff --cached --quiet; then
    echo "(sin cambios nuevos, omitido)"
    continue
  fi
  git commit -m "${PODCAST}: ${dir}"
  git push "$REMOTE" "HEAD:$BRANCH"
done < "$LIST"
rm -f "$LIST"

py_count=0
for f in "$PODCAST"/*.py; do
  [[ -f "$f" ]] || continue
  py_count=$((py_count + 1))
done
if [[ "$py_count" -gt 0 ]]; then
  echo "=== ${PODCAST} Python scripts ==="
  git add "$PODCAST"/*.py
  git commit -m "${PODCAST}: helper scripts"
  git push "$REMOTE" "HEAD:$BRANCH"
fi

echo "Done ($PODCAST)."
