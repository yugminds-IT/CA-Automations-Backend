# Production Email Troubleshooting

If **emails are not sending in production** (but work locally), use this checklist.

## Why it works locally but not in production

- **Local:** The app reads SMTP settings from your `.env` file. All vars are present.
- **Production:** The app reads settings from the **deployment platform’s environment** (Coolify, Render, Railway, etc.). The `.env` file is usually **not** deployed (e.g. it’s in `.gitignore`), so if you never set `SMTP_HOST`, `SMTP_PASSWORD`, etc. in the platform’s UI or config, they are **missing** in prod and email is disabled.

**Fix:** Set every required SMTP variable in your **deployment platform’s environment variables**, not only in `.env`.

## 1. Check config status

**`GET /api/v1/email-status`** (no auth) returns:

```json
{ "configured": true, "missing": [] }
```

or, when not configured:

```json
{ "configured": false, "missing": ["SMTP_HOST", "SMTP_PASSWORD", ...], "hint": "Set these in your deployment platform's environment variables (e.g. Coolify, Render), not only in .env." }
```

- If `configured` is `false`, set the missing env vars in your **deployment platform** (Coolify, Render, Railway, etc.) — same names as in `.env`, e.g. `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`.

## 2. Required SMTP env vars

Set these in your **production environment** (not only in `.env` locally):

| Variable | Example | Notes |
|----------|---------|--------|
| `SMTP_HOST` | `smtp.gmail.com` or `smtp.hostinger.com` | Your provider’s SMTP host |
| `SMTP_PORT` | `587` or `465` | 587 = STARTTLS, 465 = SSL |
| `SMTP_USER` | `you@example.com` | Usually your email |
| `SMTP_PASSWORD` | app password or email password | **Gmail: use App Password, not account password** |
| `SMTP_FROM_EMAIL` | `noreply@example.com` | Sender address |
| `SMTP_FROM_NAME` | `Your App` | Optional |

## 3. Common fixes

- **Env vars in production:** Set all SMTP vars in the platform’s “Environment” / “Env vars” (not only in `.env`). Restart the app after adding them.
- **Gmail**: Use an [App Password](https://support.google.com/accounts/answer/185833), not your normal password. `SMTP_USER` = your Gmail address.
- **Timeouts**: Set `SMTP_TIMEOUT=60` (default 30). Try `SMTP_PORT=465` if 587 times out.
- **Firewall**: Production host must allow **outbound** SMTP (ports 587 and/or 465). Some platforms block 587; if so, use `SMTP_PORT=465` and `SMTP_USE_TLS=false`.
- **STARTTLS**: For port 587 use `SMTP_USE_TLS=true` (default). For 465 use `SMTP_USE_TLS=false`.

## 4. Logs

On startup the app logs either:

- `Email configured (SMTP). Sending enabled.`
- `Email NOT configured. Missing: SMTP_HOST, ...`

When sending, it logs `Attempting to send email to ... via HOST:PORT` and then either success or an error with hints. Check your deployment logs for these messages.

## 5. Test endpoint

**`POST /api/v1/test-email`** (requires auth) sends a test email. Use it after fixing config to verify sending works.

**`GET /api/v1/test-email/config`** (requires auth) returns full config status (including which vars are set, but not secrets).

---

## 6. Scheduled emails not sending

If **test email works** but **scheduled emails never send**:

- **Event loop fix:** The scheduler runs in a background thread. It now uses `asyncio.run()` so async email sending uses a dedicated event loop. Deploy the latest code.
- **Logs:** On startup you should see `Email scheduler started`. Every minute the job runs; when there are pending emails you’ll see `📧 EMAIL SCHEDULER - Checking for scheduled emails` and processing logs. Check deployment logs for errors (e.g. "Error in async email sending").
- **Multiple workers:** If you run **multiple app workers** (e.g. Gunicorn with `workers=4`), each process starts its own scheduler and the job runs in every worker. That can cause duplicate sends or odd behavior. For scheduled emails to run once per minute, either run **one worker** or use an external cron that calls a dedicated “process scheduled emails” endpoint (if you add one).
- **Pending emails:** Scheduled emails are sent only when `scheduled_datetime <= now` and `status == 'pending'`. Confirm in the DB or via your API that there are pending rows and that `scheduled_datetime` is in the past (or now).
