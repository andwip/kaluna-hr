#!/usr/bin/env bash
set -euo pipefail

SERVICE="kaluna-leave-email-watchdog.service"
TIMER="kaluna-leave-email-watchdog.timer"

echo "Stopping Kaluna watchdog timer/service..."

systemctl --user disable --now "$TIMER" 2>/dev/null || true
systemctl --user stop "$SERVICE" 2>/dev/null || true
systemctl --user reset-failed "$SERVICE" 2>/dev/null || true
systemctl --user daemon-reload

echo ""
echo "Timers:"
systemctl --user list-timers --all | grep kaluna || echo "No kaluna timer active."

echo ""
echo "Service status:"
systemctl --user status "$SERVICE" --no-pager || true

echo ""
echo "Done."
