# Vercel Deployment Troubleshooting

## Common Error: 500 INTERNAL_SERVER_ERROR / FUNCTION_INVOCATION_FAILED

### 1. Check Environment Variables

The most common cause is missing environment variables. Ensure these are set in your Vercel project:

**Required:**
- `DATABASE_URL` - Your PostgreSQL connection string
- `SECRET_KEY` - Your JWT secret key

**Optional (have defaults):**
- `ALGORITHM` - Default: HS256
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Default: 30
- `REFRESH_TOKEN_EXPIRE_DAYS` - Default: 7

**How to set:**
1. Go to your Vercel project dashboard
2. Navigate to Settings → Environment Variables
3. Add each variable for Production, Preview, and Development environments
4. Redeploy after adding variables

### 2. Check Database Connection

Your database must be:
- Accessible from the internet (not localhost)
- Allowing connections from Vercel's IP ranges
- Using SSL if required (include `?sslmode=require` in DATABASE_URL)

**Test your DATABASE_URL format:**
```
postgres://username:password@host:port/database?sslmode=require
```

### 3. Check Vercel Logs

1. Go to your Vercel project dashboard
2. Click on the deployment that failed
3. Check the "Functions" tab for detailed error logs
4. Look for Python tracebacks or import errors

### 4. Verify Python Version

The `vercel.json` specifies Python 3.11. Ensure your dependencies are compatible.

### 5. Check Import Paths

The `api/index.py` file should correctly import from `app.main`. If you see import errors:
- Verify the project structure matches what's in the repository
- Check that all `__init__.py` files exist in the app directories

### 6. Database Connection Pooling

For serverless functions, connection pooling is handled automatically. The code uses `pool_pre_ping=True` to handle stale connections.

### 7. Test Locally with Vercel CLI

Test your function locally before deploying:

```bash
# Install Vercel CLI
npm install -g vercel

# Run locally
vercel dev
```

This will help identify issues before deploying.

### 8. Common Error Messages and Solutions

**"DATABASE_URL not set"**
- Solution: Add `DATABASE_URL` environment variable in Vercel dashboard

**"SECRET_KEY not set"**
- Solution: Add `SECRET_KEY` environment variable in Vercel dashboard

**"ModuleNotFoundError: No module named 'app'"**
- Solution: Check that `api/index.py` has correct path setup

**"Connection refused" or database connection errors**
- Solution: Verify DATABASE_URL is correct and database is accessible from internet

**"ImportError" or missing dependencies**
- Solution: Ensure all packages in `requirements.txt` are compatible with Python 3.11

### 9. Quick Health Check

After deployment, test these endpoints:
- `GET /health` - Should return `{"status": "healthy"}` without database
- `GET /` - Should return `{"message": "Backend CAA API"}`
- `GET /docs` - Should show Swagger UI

If `/health` works but other endpoints fail, it's likely a database connection issue.

### 10. Force Redeploy

Sometimes a simple redeploy fixes issues:
1. Go to Vercel dashboard
2. Click "Redeploy" on your latest deployment
3. Or push a new commit to trigger a new deployment

## Getting More Help

If issues persist:
1. Check Vercel function logs (most important)
2. Share the specific error message from logs
3. Verify all environment variables are set correctly
4. Test database connection separately using a PostgreSQL client

