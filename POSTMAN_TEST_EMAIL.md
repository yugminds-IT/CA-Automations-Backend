# Test Email in Postman – Step by Step

Use these steps to send a test email from Postman.

---

## Prerequisites

- Backend running (e.g. `http://localhost:8000` or your production URL).
- An **admin or employee** user (org login). Master admin cannot use the org login; use org admin/employee for test-email.

---

## Step 1: Check if email is configured (no auth)

1. In Postman, create a new request.
2. Set **Method** to **GET**.
3. Set **URL** to:
   ```text
   http://localhost:8000/api/v1/email-status
   ```
   (Replace with your production URL if testing prod.)
4. Click **Send**.
5. Check the response:
   - `"configured": true` → You can send test email (go to Step 2).
   - `"configured": false` and `"missing": [...]` → Set those env vars (e.g. in `.env` or deployment), then try again.

---

## Step 2: Get access token (login)

1. Create a new request.
2. Set **Method** to **POST**.
3. Set **URL** to:
   ```text
   http://localhost:8000/api/v1/auth/login
   ```
4. Open the **Body** tab.
5. Select **x-www-form-urlencoded**.
6. Add these key-value pairs:

   | Key      | Value              |
   |----------|--------------------|
   | username | your-admin@email.com |
   | password | your-password      |

   Use the **email** as `username` (not a separate username field).
7. Click **Send**.
8. In the response JSON, copy the **`access_token`** value (long string). You will use it in the next step.

---

## Step 3: Send test email

1. Create a new request.
2. Set **Method** to **POST**.
3. Set **URL** to:
   ```text
   http://localhost:8000/api/v1/test-email
   ```
4. **Authorization:**
   - Go to the **Authorization** tab.
   - Type: **Bearer Token**.
   - In **Token**, paste the `access_token` you copied in Step 2.
5. **Body:**
   - Go to the **Body** tab.
   - Select **raw** and **JSON**.
   - Use:

   ```json
   {
     "to_email": "recipient@example.com",
     "subject": "Test Email from Postman",
     "message": "This is a test message."
   }
   ```

   Replace `recipient@example.com` with the inbox you want to use for the test.
6. Click **Send**.
7. You should get a success response and the email at `to_email`.

---

## Optional: Check email config (with auth)

1. **Method:** GET  
2. **URL:** `http://localhost:8000/api/v1/test-email/config`  
3. **Authorization:** Bearer Token → same `access_token` as in Step 3.  
4. **Send** → response shows whether email is configured and which settings are set (no secrets).

---

## Test scheduled email (scheduler)

Creates **one** scheduled email so the background scheduler will send it (within ~1 minute). Use this to verify that scheduled emails work.

**Prerequisites:** Same token as Step 2 (admin/employee). Your org must have at least one **client** and one **email template**.

1. **Method:** POST  
2. **URL:** `http://localhost:8000/api/v1/test-scheduled-email`  
3. **Authorization:** Bearer Token → same `access_token` as in Step 2.  
4. **Body** → **raw** → **JSON**:

   ```json
   {
     "to_email": "your-inbox@example.com",
     "client_id": null,
     "template_id": null,
     "send_in_seconds": 0
   }
   ```

   - **to_email** (required): Where to send the email.  
   - **client_id** (optional): Omit or `null` to use the first client in your org.  
   - **template_id** (optional): Omit or `null` to use the first template in your org.  
   - **send_in_seconds**: `0` = due now (scheduler will send it within ~1 min). Use e.g. `60` to make it due in 1 minute.

5. **Send.**  
6. Response includes `scheduled_email_id`, `scheduled_datetime`, `status: "pending"`.  
7. Wait up to ~1 minute and check the inbox for `to_email`. Check server logs for `📧 EMAIL SCHEDULER` and `Processing scheduled email` to confirm the job ran.

---

## Quick reference

| Step | Method | URL | Auth | Body |
|------|--------|-----|------|------|
| 1 – Email status | GET | `/api/v1/email-status` | None | — |
| 2 – Login | POST | `/api/v1/auth/login` | None | x-www-form-urlencoded: `username`, `password` |
| 3 – Send test email | POST | `/api/v1/test-email` | Bearer \<token\> | JSON: `to_email`, `subject`, `message` |
| Optional – Email config | GET | `/api/v1/test-email/config` | Bearer \<token\> | — |
| **Scheduled email** | **POST** | **`/api/v1/test-scheduled-email`** | **Bearer \<token\>** | **JSON: `to_email`, optional `client_id`, `template_id`, `send_in_seconds`** |

Use **localhost:8000** (or your server URL) as the base for all URLs above.
