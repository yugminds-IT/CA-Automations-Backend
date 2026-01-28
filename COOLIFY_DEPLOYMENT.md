# Coolify Deployment Guide

## Prerequisites

1. Coolify instance running
2. PostgreSQL database (can be created in Coolify or external)
3. Domain name (optional, for custom domain)

## Step 1: Create New Resource in Coolify

1. Go to your Coolify dashboard
2. Click "New Resource" → "Application"
3. Connect your Git repository or upload code

## Step 2: Configure Build Settings

### Build Pack: Docker
- Coolify will automatically detect the Dockerfile

### Build Command (if needed):
```bash
docker build -t backend-caa .
```

### Start Command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

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

### Database Connection Pool (for 100+ concurrent requests)

```env
# Production settings for high traffic
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_CONNECT_TIMEOUT=10
DB_STATEMENT_TIMEOUT=30
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

After deployment, run database migrations:

```bash
# SSH into your Coolify container or use Coolify's terminal
alembic upgrade head
```

Or add a startup script that runs migrations automatically.

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

### For Production:
```env
ENVIRONMENT=production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### For Staging:
```env
ENVIRONMENT=staging
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
```

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is correct
- Check database firewall rules
- Ensure database is accessible from Coolify server

### Port Issues
- Ensure port 8000 is exposed in Dockerfile
- Check Coolify port mapping

### Migration Issues
- Run migrations manually: `alembic upgrade head`
- Check database permissions

### Email Not Sending
- Verify SMTP credentials
- Check SMTP port (587 for TLS, 465 for SSL)
- Test with a test email endpoint

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
