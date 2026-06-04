#!/usr/bin/env bash
set -Eeuo pipefail

LIMIT="${1:-10}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

exec "$SCRIPT_DIR/kaluna-local-store.py" sync --limit "$LIMIT" --verbose
