# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Kaluna HR API

Base URL:

```text
http://localhost:3000/api
```

Authentication:

```text
.kaluna-api.curl
```

The local wrappers use this config file internally. Do not read or print it.

### Required First Call

Resolve every Telegram sender before employee-specific work:

```bash
./kaluna-local-store.py resolve-channel TELEGRAM_ID
```

Linked response includes:

- `linked`
- `binding_status`
- `employee_id`
- `full_name`
- `email`
- `bot_role`

### Local-First Mode

Normal conversation flow must use the local SQLite snapshot and outbox:

```bash
./kaluna-local-store.py list employees --limit 3
```

Short wrapper:

```bash
./kaluna-local-read.sh employees 3
```

Available local snapshot collections:

- `employees`
- `attendance`
- `leave_requests`
- `locations`
- `policy`
- `channel_pair_tickets`
- `onboarding_tasks`
- `offboarding_tasks`
- `audit_logs`
- `agent`

Use live API reads only when explicitly refreshing the local snapshot or debugging sync issues.

### Employee Reads

Policy topic from local snapshot:

```bash
./kaluna-local-store.py list policy --limit 20
```

Specific employee record:

```bash
./kaluna-local-store.py get employees EMPLOYEE_ID
```

Daily status from local attendance snapshot:

```bash
./kaluna-local-store.py list attendance --limit 20
```

Pending or completed pairing tickets:

```bash
./kaluna-local-store.py list channel_pair_tickets --limit 20
```

### Write Actions

Before `/api/leave/request`, `/api/attendance/correction/request`, or admin approve/reject endpoints:

1. Collect required fields.
2. Show a short summary.
3. Ask for explicit confirmation.
4. Only then queue the action locally.

Queue format:

```bash
./kaluna-local-store.py enqueue leave_request /api/leave/request '{"employee_id":"EMPLOYEE_ID"}'
```

Canonical leave request payload:

```bash
./kaluna-local-store.py enqueue leave_request /api/leave/request '{"employee_id":"EMPLOYEE_ID","leave_type":"sick","start_date":"2026-05-29","end_date":"2026-05-29","total_days":1,"reason":"lagi meriang"}'
```

Required fields are `employee_id`, `leave_type`, `start_date`, `end_date`, and `total_days`; `reason` is required for sick leave and optional for other leave types. Do not use `date`, `duration`, `start_time`, or `end_time` for full-day leave requests.

Normalize before confirmation:

- Use Asia/Jakarta date semantics for Indonesian relative words such as `hari ini`, `besok`, and `lusa`.
- Illness words like `sakit`, `meriang`, `demam`, or `flu` imply `leave_type: "sick"` unless overridden.
- `penuh`, `full day`, `seharian`, `1 hari`, and `satu hari` mean `total_days: 1`; for one provided date, set `end_date` equal to `start_date`.
- If the user gives a start date plus a duration, derive `end_date` with inclusive calendar math: `end_date = start_date + total_days - 1`. Example: start `2026-05-28` for `2 hari` ends on `2026-05-29`.
- If the user gives a start and end date, compute inclusive calendar-day `total_days`. Example: `2026-05-28` through `2026-05-29` is `2`.
- If duration conflicts with explicit dates, ask one clarification before submitting.
- Ask only for genuinely missing required fields. Do not ask for leave times after the user says full day.
- For sick leave, ask for a reason if the user has not provided one. Do not submit sick leave without `reason`.

After queueing a leave request, tell the employee it has been recorded locally and is waiting to sync.

After a successful sync, the API sends the approval email and returns `leave_id`, `approval_line_email`, and `approval_email.sent`.

If `approval_email.sent` is true, include the leave ID in the employee reply. If false, include the leave ID and say the approval email failed.

Attendance check-in/check-out require trusted OpenClaw-rendered Telegram location markers. OpenClaw flattens real Telegram location attachments into transcript text:

- `📍 LATITUDE, LONGITUDE`
- `📍 PLACE_OR_ADDRESS (LATITUDE, LONGITUDE)`
- `🛰 Live location: LATITUDE, LONGITUDE`

Do not use typed coordinates, forwarded messages, forwarded locations, screenshots, copied map links, or ordinary latitude/longitude text.

Only call these endpoints when the current or immediately previous message from the same sender contains one of the trusted location markers above, the marker is in the current message body rather than reply context, and the message is not forwarded:

```bash
./kaluna-local-store.py enqueue check_in /api/attendance/check-in '{"employee_id":"EMPLOYEE_ID","latitude":-6.1751,"longitude":106.8271}'
```

```bash
./kaluna-local-store.py enqueue check_out /api/attendance/check-out '{"employee_id":"EMPLOYEE_ID","latitude":-6.1751,"longitude":106.8271}'
```

For `sales` department employees outside the approved office geofence, collect the field-work purpose before queueing. Department matching is trim + lowercase, so `sales`, `Sales`, and `SALES` all match. The local store adds `is_outside_geofence: true` and `geofence_exception: "sales_department"` before async sync:

```bash
./kaluna-local-store.py enqueue check_in /api/attendance/check-in '{"employee_id":"EMPLOYEE_ID","latitude":-6.1751,"longitude":106.8271,"purpose":"Client visit to ..."}'
```

If a synced API response still returns `code: "purpose_required"` or `requires_purpose: true`, collect the Sales field-work purpose and requeue with `purpose`.

If a synced API response returns `status: "invalid_location"` or `suggested_next_action.type: "ask_wfh_today"`, ask whether the employee is WFH today. For a yes answer, draft an `/api/attendance/correction/request` payload with a WFH reason and queue it only after explicit confirmation.

### Refresh And Sync

Refresh pairing tickets from the API into the local SQLite snapshot:

```bash
./kaluna-api-get.sh /api/auth/channel/pending > /home/sre/.openclaw/workspace-kaluna-employee/data/channel-pair-tickets.json
./kaluna-local-store.py import-collection channel_pair_tickets /home/sre/.openclaw/workspace-kaluna-employee/data/channel-pair-tickets.json
```

Import the main dashboard snapshot:

```bash
./kaluna-local-store.py import-snapshot /home/sre/.openclaw/workspace-kaluna-employee/data/firestore-dashboard-all.json
```

Inspect outbox state:

```bash
./kaluna-local-store.py status
./kaluna-local-status.sh
```

Process queued writes against the API:

```bash
./kaluna-local-store.py sync --limit 10 --verbose
./kaluna-local-sync.sh 10
```
