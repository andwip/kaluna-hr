#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
  printf 'Usage: %s /api/path[?query]\n' "$0" >&2
  exit 64
fi

API_PATH="$1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.kaluna-api.curl"

if [[ "$API_PATH" != /api/* || "$API_PATH" == *$'\n'* || "$API_PATH" == *$'\r'* ]]; then
  printf 'Invalid API path\n' >&2
  exit 65
fi

exec curl --fail --show-error --silent --max-time 20 \
  --config "$CONFIG_FILE" \
  "http://localhost:3000${API_PATH}"
