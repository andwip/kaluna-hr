#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 8 ]]; then
  printf 'Usage: %s to_email leave_id employee_name employee_id leave_type start_date end_date total_days\n' "$0" >&2
  exit 64
fi

TO_EMAIL="$1"
LEAVE_ID="$2"
EMPLOYEE_NAME="$3"
EMPLOYEE_ID="$4"
LEAVE_TYPE="$5"
START_DATE="$6"
END_DATE="$7"
TOTAL_DAYS="$8"

if [[ "$TO_EMAIL" != *@*.* || "$TO_EMAIL" == *$'\n'* || "$TO_EMAIL" == *$'\r'* ]]; then
  printf 'Invalid approval line email\n' >&2
  exit 65
fi

if [[ ! "$LEAVE_ID" =~ ^LEAVE_[A-Za-z0-9_-]+$ ]]; then
  printf 'Invalid leave id\n' >&2
  exit 65
fi

set -a
. /home/sre/.openclaw/google/gogcli.env
set +a

BODY=$(printf '%s\n' \
  "Leave approval is required for ${EMPLOYEE_NAME}." \
  "" \
  "Leave ID: ${LEAVE_ID}" \
  "Employee ID: ${EMPLOYEE_ID}" \
  "Type: ${LEAVE_TYPE}" \
  "Dates: ${START_DATE} to ${END_DATE}" \
  "Total days: ${TOTAL_DAYS}" \
  "" \
  "Reply to this email with approve, approved, setuju, ok, or similar approval text to approve the leave automatically." \
  "The Kaluna agent will process the reply from the kaluna-labeled devops inbox.")

exec /home/sre/.openclaw/bin/gog \
  --home /home/sre/.openclaw/google/gogcli \
  gmail send \
  --account devops@koinworks.com \
  --from devops@koinworks.com \
  --to "$TO_EMAIL" \
  --cc kaluna@koinworks.com \
  --subject "[Kaluna Leave Approval] ${LEAVE_ID} - ${EMPLOYEE_NAME}" \
  --body "$BODY" \
  --json \
  --no-input
