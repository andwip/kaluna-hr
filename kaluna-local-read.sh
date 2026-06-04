#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -lt 1 || "$#" -gt 2 ]]; then
  printf 'Usage: %s COLLECTION [LIMIT]\n' "$0" >&2
  exit 64
fi

COLLECTION="$1"
LIMIT="${2:-20}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

exec "$SCRIPT_DIR/kaluna-local-store.py" list "$COLLECTION" --limit "$LIMIT"
