#!/usr/bin/env bash
set -euo pipefail

echo "Stopping all Kaluna watchdog timers/services..."

for unit in $(systemctl --user list-unit-files | awk '/kaluna.*watchdog/ {print $1}'); do
  echo "Disabling/stopping $unit"
  systemctl --user disable --now "$unit" 2>/dev/null || true
  systemctl --user stop "$unit" 2>/dev/null || true
  systemctl --user reset-failed "$unit" 2>/dev/null || true
done

systemctl --user daemon-reload

echo ""
echo "Remaining Kaluna timers:"
systemctl --user list-timers --all | grep kaluna || echo "No Kaluna timers."

echo ""
echo "Remaining Kaluna watchdog units:"
systemctl --user list-units --all | grep 'kaluna.*watchdog' || echo "No active Kaluna watchdog units."

echo ""
echo "Done."
