# Production Email Troubleshooting

If **emails are not sending in production**, use this checklist.

## 1. Check config status

**`GET /api/v1/email-status`** (no auth) returns:

```json
{ "configured": true, "missing": [] }
```

or, when not configured:

```json
{ "configured": false, "missing": ["SMTP_HOST", "SMTP_PASSWORD", ...] }
```

- If `configured` is `false`, set the missing env vars in your deployment (Coolify, Render, etc.).

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

- **Gmail**: Use an [App Password](https://support.google.com/accounts/answer/185833), not your normal password. `SMTP_USER` = your Gmail address.
- **Timeouts**: Set `SMTP_TIMEOUT=60` (default 30). Try `SMTP_PORT=465` if 587 times out.
- **Firewall**: Production host must allow **outbound** SMTP (ports 587 and/or 465). Some platforms block them.
- **STARTTLS**: For port 587 use `SMTP_USE_TLS=true` (default). For 465 use `SMTP_USE_TLS=false`.

## 4. Logs

On startup the app logs either:

- `Email configured (SMTP). Sending enabled.`
- `Email NOT configured. Missing: SMTP_HOST, ...`

When sending, it logs `Attempting to send email to ... via HOST:PORT` and then either success or an error with hints. Check your deployment logs for these messages.

## 5. Test endpoint

**`POST /api/v1/test-email`** (requires auth) sends a test email. Use it after fixing config to verify sending works.

**`GET /api/v1/test-email/config`** (requires auth) returns full config status (including which vars are set, but not secrets).
