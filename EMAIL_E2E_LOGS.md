# Email end-to-end logs

All mail-related events are logged with the prefix **`[MAIL E2E]`** so you can trace the full flow in the terminal.

**Grep in logs:** `[MAIL E2E]`

---

## Log sequence (order of events)

### 1. Scheduled (created)

When email config is saved (PUT `/api/v1/client/{id}/email-config`) or test-scheduled-email is called:

```
[MAIL E2E] SCHEDULED client_id=X created=N ids=[...] first_at=YYYY-MM-DDTHH:MM:SS
[MAIL E2E] SCHEDULED (test) id=X client_id=Y to=email@example.com due=...
```

- **SCHEDULED** = new scheduled emails were created (pending).
- **SCHEDULED (test)** = one test scheduled email was created via `/api/v1/test-scheduled-email`.

### 2. Cancelled (config saved again)

When the same client’s email config is saved again, all pending scheduled emails for that client are cancelled:

```
[MAIL E2E] CANCELLED client_id=X count=N (config saved again)
```

### 3. Scheduler run (due emails picked up)

Every minute the scheduler looks for pending emails that are due:

```
[MAIL E2E] SCHEDULER_RUN due_now=N ids=[...] at=YYYY-MM-DD HH:MM:SS
```

Then for each email:

- **SEND_START** = starting to send this scheduled email.
- **SKIPPED** = row was no longer pending (e.g. cancelled before send).

```
[MAIL E2E] SEND_START id=X client_id=Y to=[...] due=...
[MAIL E2E] SKIPPED id=X status=cancelled (no longer pending)
```

### 4. SMTP send (actual send)

Inside the send flow, when the SMTP call is made:

```
[MAIL E2E] SMTP_SENT to=email@example.com subject=...
[MAIL E2E] SMTP_FAILED to=email@example.com error=...
```

### 5. Final status (scheduler)

After sending (or failing) for that scheduled email:

```
[MAIL E2E] SENT id=X client_id=Y to=[...] sent_at=...
[MAIL E2E] FAILED id=X client_id=Y to=[...] error=...
```

---

## Example full flow (one email)

```
[MAIL E2E] SCHEDULED client_id=1 created=1 ids=[41] first_at=2026-01-29T12:13:00
...
[MAIL E2E] SCHEDULER_RUN due_now=1 ids=[41] at=2026-01-29 12:13:05
[MAIL E2E] SEND_START id=41 client_id=1 to=['user@example.com'] due=2026-01-29 12:13:00
[MAIL E2E] SMTP_SENT to=user@example.com subject=...
[MAIL E2E] SENT id=41 client_id=1 to=['user@example.com'] sent_at=2026-01-29T12:13:06
```

---

## Quick reference

| Log prefix | Meaning |
|------------|--------|
| `[MAIL E2E] SCHEDULED` | New scheduled emails created (config save or test API). |
| `[MAIL E2E] CANCELLED` | Pending emails cancelled (config saved again). |
| `[MAIL E2E] SCHEDULER_RUN` | Scheduler found N due emails (ids listed). |
| `[MAIL E2E] SEND_START` | Scheduler started sending one scheduled email. |
| `[MAIL E2E] SKIPPED` | Row no longer pending (e.g. cancelled). |
| `[MAIL E2E] SMTP_SENT` | SMTP send succeeded. |
| `[MAIL E2E] SMTP_FAILED` | SMTP send failed (error in log). |
| `[MAIL E2E] SENT` | Scheduled email marked SENT (success). |
| `[MAIL E2E] FAILED` | Scheduled email marked FAILED (all recipients failed). |

Use `grep "[MAIL E2E]"` (or your platform’s log search) to see the full trail for any run.
