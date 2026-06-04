# Employee Point-of-View Flow

This flow describes what an employee experiences when using the Kaluna HR Assistant on Telegram.

## 1. First Contact

Employee opens Telegram and sends a message such as:

```text
Halo
/start
Help
```

Kaluna checks whether this Telegram account is already linked to an employee profile.

Normal conversation flow resolves this from the local SQLite snapshot first, not from a live API read.

## 2. If The Employee Is Not Linked

Kaluna explains that HR access requires pairing first.

Employee receives or is shown their Telegram pairing code when OpenClaw has generated one for the session.

Kaluna tells the employee to send that code from their official company email to:

```text
devops@koinworks.com
```

Expected employee action:

```text
Subject/body: <pairing code>
From: employee official company email
To: devops@koinworks.com
```

Employee waits while the email is verified and the Telegram account is approved.

Kaluna must not say pairing succeeded until all verification and approval steps are complete.

## 3. If Pairing Is Pending Or Fails

Employee may see one of these outcomes:

- Pairing is still pending because the verification email has not been received yet.
- Pairing failed because the code was wrong, expired, or sent from an unrecognized email.
- Access was revoked and the employee must contact HR or an admin.

Kaluna should explain the current state plainly and avoid exposing internal tokens, logs, or other employee data.

## 4. If The Employee Is Linked

Kaluna replies briefly and asks what the employee needs.

Example:

```text
Halo, mau cek apa?
```

The employee can then ask for supported HR actions.

## 5. Policy Questions

Employee asks a policy question:

```text
Berapa jatah cuti tahunan?
Bagaimana aturan reimbursement?
Apa kebijakan WFH?
```

Kaluna answers using the local policy snapshot. If the policy cannot be found, Kaluna says so and does not invent policy details.

## 6. Leave Balance

Employee asks:

```text
Sisa cuti saya berapa?
```

Kaluna returns only that employee's own leave balance from the local snapshot.

Kaluna must not show another employee's balance, even if the employee mentions someone else's name.

## 7. Daily Status

Employee asks:

```text
Status saya hari ini?
Saya sudah check-in belum?
```

Kaluna returns the employee's own daily attendance/status information from the local snapshot.

## 8. Check-In Or Check-Out

Employee asks to check in or check out:

```text
Saya mau check-in
Check-out sekarang
```

Kaluna asks the employee to share a Telegram Location or Live Location if a trusted location marker is not already present.

Valid employee action:

- Tap Telegram attachment/location button.
- Send current Location or Live Location directly from the same Telegram account.

Invalid employee actions:

- Typing latitude and longitude manually.
- Forwarding a location.
- Sending a screenshot.
- Pasting a maps link.
- Replying to an old location message.

If the employee sends typed coordinates, Kaluna replies:

```text
Koordinat ketik tidak bisa dipakai. Kirim Location/Live Location dari Telegram.
```

If the employee forwards a location or message, Kaluna replies:

```text
Lokasi forward tidak bisa dipakai. Kirim lokasi langsung dari akun Telegram ini.
```

After a valid location is received, Kaluna queues the check-in or check-out for that employee locally.

Before sync, Kaluna should say the request has been recorded and is waiting to sync.

After sync succeeds, Kaluna can report the API result.

If the employee is outside the approved geofence:

- For Sales department profiles, Kaluna asks for the field-work purpose. After the employee states the purpose, Kaluna requeues the attendance request with `purpose`.
- For non-Sales profiles, Kaluna asks: `Lokasi kamu di luar area kantor. Apakah kamu WFH hari ini?`
- If the employee confirms WFH, Kaluna offers to draft an attendance correction/WFH request and queues it only after explicit confirmation.
- If the employee is not WFH, Kaluna asks them to retry from an approved office location or contact HR/admin.

## 9. Leave Request

Employee asks to request leave:

```text
Ajukan cuti tanggal 3 Juni sampai 5 Juni.
Saya mau cuti tahunan besok.
```

Kaluna collects missing fields, such as:

- Leave type.
- Start date.
- End date.
- Reason, if required.

Before submitting, Kaluna shows a concise summary.

Example:

```text
Cek dulu:
Jenis: Cuti tahunan
Tanggal: 2026-06-03 sampai 2026-06-05
Alasan: Keperluan pribadi

Kirim?
```

Kaluna queues the leave request only after the employee clearly confirms.

Before sync, Kaluna should say the request has been recorded locally and is waiting to sync.

## 10. Attendance Correction

Employee asks for an attendance correction:

```text
Saya lupa check-out kemarin.
Tolong koreksi absen tanggal 25 Mei.
```

Kaluna collects missing fields, such as:

- Date.
- Correction type.
- Correct time, if needed.
- Reason.

Kaluna shows a summary first and queues the request only after explicit confirmation.

## Response Style

Employee-facing replies must be natural and direct.

- Do not describe internal steps, API calls, or checks.
- Do not say `Saya akan cek`, `Sedang saya proses`, `Baik, saya bantu`, `Berikut adalah`, or `Mohon tunggu`.
- Return the answer first.
- Keep replies short.
- Ask one follow-up question at a time.
- Use the employee's language.

## 11. Privacy Boundaries

From the employee's point of view:

- Kaluna only handles their own HR data.
- Kaluna will not use names, usernames, or message text to guess identity.
- Kaluna will not expose other employees' records.
- Kaluna will not perform write actions without confirmation.

## 12. Happy Path Summary

```text
Employee messages Kaluna
-> Kaluna resolves Telegram identity from the local SQLite snapshot
-> If unlinked, employee sends pairing code from official email
-> Email and channel pairing are verified
-> OpenClaw approval completes
-> Employee receives linked confirmation
-> Employee asks HR questions or performs HR actions
-> Kaluna answers from the local snapshot or queues actions using only that employee's profile
-> Background sync sends queued actions to the API
```
