# Test API Works in Postman but Not from Frontend (Production)

If the **test email API works in Postman** against the production URL but **does not work when called from the frontend**, use this checklist.

---

## 1. Check in the browser (is it frontend or backend?)

1. Open your **production frontend** in Chrome/Edge (e.g. `https://your-app.com`).
2. Open **DevTools** → **F12** or right‑click → Inspect.
3. Go to the **Network** tab.
4. Trigger the action that should call the test email API (e.g. “Send test email” or “Test scheduled email”).
5. In the list of requests, find the one that goes to your **API** (e.g. `test-email`, `test-scheduled-email`, or your backend domain).

Check the **Status** and **response**:

| What you see | Likely cause |
|--------------|--------------|
| **Status: (failed) or CORS error in Console** | Backend **CORS** not allowing your frontend origin. Fix: add frontend URL to `CORS_ORIGINS` in production. |
| **Status: 401 Unauthorized** | Frontend not sending the **Bearer token** (or wrong token). Fix: ensure frontend sends `Authorization: Bearer <access_token>` for that request. |
| **Status: 404** | Frontend calling **wrong URL** (e.g. path typo or still pointing to localhost). Fix: set frontend API base URL to production API URL. |
| **Status: 0 or no request at all** | Frontend **never calling** the API (wrong URL in code, or button not wired). Fix: check frontend env (e.g. `VITE_API_URL`, `NEXT_PUBLIC_API_URL`) and the code that triggers the request. |
| **Status: 200** | API is working from frontend; issue may be UI/feedback (e.g. success/error message not shown). |

Also open the **Console** tab and look for red errors (CORS, 401, or network errors).

---

## 2. Backend: CORS (most common when “Postman works, frontend doesn’t”)

In **production**, the backend only allows origins listed in **`CORS_ORIGINS`**.

- Your **.env** has: `CORS_ORIGINS=http://localhost:3001`
- If the **frontend in production** is on a different URL (e.g. `https://app.navedhana.com`), the browser will block the request and you’ll see a CORS error in the Console.

**Fix:** In the **production** environment (Coolify, Render, etc.), set:

```bash
CORS_ORIGINS=https://your-frontend-domain.com
```

If you have multiple frontend URLs (e.g. app + admin):

```bash
CORS_ORIGINS=https://app.navedhana.com,https://admin.navedhana.com
```

No spaces after commas. Restart the backend after changing.

---

## 3. Frontend: API base URL

The frontend must call the **production API URL**, not `http://localhost:8000`.

- Check how the frontend gets the API URL (e.g. `VITE_API_URL`, `NEXT_PUBLIC_API_URL`, `REACT_APP_API_URL`).
- In **production build/deploy**, that variable must be set to your production API (e.g. `https://api.navedhana.com`).
- In the Network tab, the request URL should be something like:  
  `https://api.navedhana.com/api/v1/test-email`  
  and **not** `http://localhost:8000/...`.

---

## 4. Frontend: Auth token

Postman works because you set **Authorization: Bearer &lt;token&gt;** manually.

- The frontend must send the same header for the test email (and test-scheduled-email) APIs.
- Check that the frontend stores the access token after login and attaches it to the request (e.g. axios/fetch interceptor or per-request header).
- In DevTools → Network → click the API request → **Headers** → Request Headers: you should see  
  `Authorization: Bearer eyJ...`  
  If it’s missing, the backend will return **401** and it will look like the API “doesn’t work” from the frontend.

---

## 5. Quick summary

| Check | Where | What to do |
|-------|--------|------------|
| CORS | Backend env (production) | Set `CORS_ORIGINS` to your frontend URL(s). Restart backend. |
| API URL | Frontend env / build | Set API base URL to production API (e.g. `https://api.navedhana.com`). |
| Token | Frontend code / Network tab | Send `Authorization: Bearer <access_token>` on the test-email request. |
| What actually fails | Browser DevTools → Network + Console | Use status code and error message to decide if it’s CORS, 401, 404, or no request. |

Once you see the **exact status code and any Console error** (e.g. CORS message), you can match it to the table above and fix the right place (backend CORS vs frontend URL vs frontend auth).
