# Coolify Deployment Guide

## Prerequisites

1. Coolify instance running
2. PostgreSQL database (can be created in Coolify or external)
3. Domain name (optional, for custom domain)
4. GitHub repo cloned/connected — **you've done this ✓**

### Quick checklist (order of operations)

1. **General & Build** — Fill the form (Step 1 below).
2. **Environment variables** — Add required env vars (Step 3).
3. **PostgreSQL** — Create a DB in Coolify or use an external one; set `DATABASE_URL`.
4. **Port** — Set port **8000** in the application settings.
5. **Deploy** — Trigger deployment and run migrations (handled by `start.sh`).

---

## Step 1: Coolify UI — General & Build (form-by-form)

After adding your GitHub repo as a new **Application**, use these values in the Coolify form.

### General

| Field | Value |
|-------|--------|
| **Name** | `ca-backend` |
| **Description** | e.g. `CAA Backend API` (optional) |
| **Build Pack** | **Dockerfile** *(not Nixpacks)* — the project has a `Dockerfile` |
| **Is it a static site?** | No |
| **Domains** | `https://ca-api.navedhana.com` |
| **Generate Domain** | Use if you want Coolify to suggest a domain |
| **Direction** | Allow www & non-www (or your preference) |
| **Docker Registry** | Leave empty unless you push to a registry |
| **Docker Image** | Empty |
| **Docker Image Tag** | Empty |

### Build

| Field | Value |
|-------|--------|
| **Install Command** | *(leave empty)* — Docker handles install |
| **Build Command** | *(leave empty)* — Dockerfile defines build |
| **Start Command** | *(leave empty)* — `Dockerfile` `CMD` uses `start.sh` |
| **Base Directory** | `/` |
| **Publish Directory** | `/` |
| **Watch Paths** | *(leave empty)* |

**Important:** With **Build Pack = Dockerfile**, Coolify builds from the repo `Dockerfile`. Install/build/start are defined there; you don't need to set them in the form.

### Port

- Set **Port** to **8000** (FastAPI runs on 8000; Coolify will map the domain to it).

---

## Step 2: Configure Build Settings (reference)

### Build Pack: Dockerfile
- Coolify uses the `Dockerfile` in the repo root.
- The image runs `start.sh`, which runs migrations then `uvicorn`.

### What the Dockerfile does
- Builds a Python 3.12 image, installs deps, copies app code.
- `start.sh`: **wait for DB** → **migrations with retries** → `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Exposes port **8000**. Healthcheck hits `/health` (120s start-period to allow DB wait + migrations).

## Step 3: Environment Variables

Set these environment variables in Coolify's environment section:

### Required Variables

```env
# Environment
ENVIRONMENT=production

# Database (Coolify will provide this if using Coolify's PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# Security (GENERATE THESE - DO NOT USE DEFAULTS!)
SECRET_KEY=your-very-long-random-secret-key-min-32-characters
ENCRYPTION_KEY=your-fernet-encryption-key-base64-encoded

# JWT Settings
ACCESS_TOKEN_EXPIRE_MINUTES=7200
REFRESH_TOKEN_EXPIRE_DAYS=30
ALGORITHM=HS256
```

### Database connection pool (optional)

Defaults (10+5) are suitable for most deployments. Override for high traffic:

```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_CONNECT_TIMEOUT=15
DB_STATEMENT_TIMEOUT=60
```

For 100+ concurrent requests: `DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=10`.

### Startup tuning (optional)

If the app restarts while the DB is still coming up, increase wait/retry:

```env
DB_WAIT_MAX_ATTEMPTS=30
DB_WAIT_DELAY_SECONDS=2
DB_WAIT_CONNECT_TIMEOUT=5
MIGRATION_MAX_ATTEMPTS=5
MIGRATION_RETRY_DELAY_SECONDS=5
```

### Email Configuration

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Company Name
SMTP_USE_TLS=true
FRONTEND_URL=https://your-frontend-domain.com
```

## Step 4: Generate Security Keys

### Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Generate ENCRYPTION_KEY:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Step 5: Database Setup

### Option A: Use Coolify's PostgreSQL
1. Create a PostgreSQL resource in Coolify
2. Coolify will automatically provide `DATABASE_URL` environment variable
3. The connection string will be in format: `postgresql://user:pass@host:5432/dbname`

### Option B: External PostgreSQL
1. Use your own PostgreSQL instance
2. Set `DATABASE_URL` manually in environment variables

### Run Migrations

Migrations run automatically on every container start via `start.sh` (after waiting for the DB and with retries). No manual step needed.

## Step 6: Configure Port

- **Port**: `8000` (default, already configured in Dockerfile)
- Coolify will automatically map this to your domain

## Step 7: Health Check

The Dockerfile includes a health check. Coolify will use this to monitor your application.

## Step 8: Persistent Storage

### Uploads Directory

If you need persistent storage for file uploads:

1. In Coolify, go to your application settings
2. Add a volume mount:
   - **Host Path**: `/app/uploads`
   - **Container Path**: `/app/uploads`

Or configure to use cloud storage (S3, etc.) in the future.

## Step 9: Resource Limits (Recommended)

Set appropriate resource limits in Coolify:

- **CPU**: 1-2 cores (increase for high traffic)
- **Memory**: 512MB - 1GB (increase for high traffic)
- **Storage**: 10GB+ (depending on file uploads)

## Step 10: Domain Configuration

1. In Coolify, go to your application
2. Add a domain (e.g., `api.yourdomain.com`)
3. Coolify will automatically configure SSL with Let's Encrypt

## Step 11: Environment-Specific Settings

### For production
```env
ENVIRONMENT=production
```
Override `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` only if you need more connections.

### For staging
```env
ENVIRONMENT=staging
```

## Troubleshooting

### Continuous restarts / "No server available"

Usually the app exits before it can serve traffic (often DB-related). The image is now optimized for this:

1. **Check logs** in Coolify (Deployments → view log). Look for:
   - `wait_for_db: ... failed` → DB not reachable. Verify `DATABASE_URL`, DB running, and network/firewall.
   - `Migrations failed after N attempts` → DB reachable but migrations failing. Check DB user permissions, disk space, or run `alembic upgrade head` manually in a one-off container to see the error.
   - `Missing required environment variables` → Set `DATABASE_URL` and `SECRET_KEY` in Coolify env.

2. **Ensure DB is up first.** If the app and Postgres start together, the app waits for the DB (see `DB_WAIT_*` env vars). If the DB takes longer than ~60s, increase `DB_WAIT_MAX_ATTEMPTS` and/or `DB_WAIT_DELAY_SECONDS`.

3. **Port**: Coolify must use **8000** as the application port. The container exposes 8000 and the healthcheck uses it.

4. **Healthcheck**: The container has a 120s start-period. If startup (DB wait + migrations) regularly exceeds that, increase `MIGRATION_RETRY_DELAY_SECONDS` or fix migration slowness.

### Database connection issues
- Verify `DATABASE_URL` is correct (include `postgresql://` or `postgres://`, and that the host is the **internal** DB hostname/IP Coolify uses, not `localhost`, unless DB runs in same stack).
- Check database firewall rules and that the DB is reachable from the app container.
- For Coolify Postgres: use the `DATABASE_URL` (or equivalent) that Coolify provides for the linked DB.

### Port issues
- Ensure port **8000** is set in Coolify for this application.
- The Dockerfile exposes 8000; the app binds `0.0.0.0:8000`.

### Migration issues
- Migrations run automatically on startup. If they keep failing, run them manually: open a shell in the container (or a one-off) and run `alembic upgrade head` to see the traceback.
- Check DB user permissions (CREATE, ALTER, etc.) and that the schema exists.

### Email not sending
- Verify SMTP credentials and that they’re set in env.
- Check SMTP port (587 for TLS, 465 for SSL).
- Scheduler startup failures are non-fatal; the API still runs. Check logs for scheduler warnings.

## Monitoring

Monitor these in Coolify:
- Application logs
- Resource usage (CPU, Memory)
- Health check status
- Database connection pool usage

## Scaling

For high traffic:
1. Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
2. Increase CPU/Memory limits
3. Consider horizontal scaling (multiple instances)
4. Use a load balancer

## Backup

1. Set up database backups in Coolify
2. Backup uploads directory if using local storage
3. Export environment variables for disaster recovery
