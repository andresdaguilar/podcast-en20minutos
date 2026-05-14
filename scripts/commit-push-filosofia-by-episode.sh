#!/usr/bin/env bash
# Wrapper for backwards compatibility — see commit-push-podcast-by-episode.sh
exec "$(cd "$(dirname "$0")" && pwd)/commit-push-podcast-by-episode.sh" Filosofia "$@"
