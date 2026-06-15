#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 2 ]]; then
  printf 'Usage: %s /api/path json-body\n' "$0" >&2
  exit 64
fi

API_PATH="$1"
JSON_BODY="$2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.kaluna-api.curl"

if [[ "$API_PATH" != /api/* || "$API_PATH" == *'?'* || "$API_PATH" == *$'\n'* || "$API_PATH" == *$'\r'* ]]; then
  printf 'Invalid API path\n' >&2
  exit 65
fi

exec curl --fail --show-error --silent --max-time 20 \
  --request POST "http://localhost:3000${API_PATH}" \
  --config "$CONFIG_FILE" \
  --header "Content-Type: application/json" \
  --data-raw "$JSON_BODY"
