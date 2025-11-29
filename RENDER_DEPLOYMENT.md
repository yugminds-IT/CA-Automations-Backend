# Render Deployment Guide

This guide will help you deploy your FastAPI backend to Render.

## Prerequisites

1. A Render account (sign up at [render.com](https://render.com))
2. Your database URL and environment variables ready
3. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### Option 1: Deploy via Render Dashboard (Recommended)

1. **Push your code to GitHub/GitLab/Bitbucket**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create a New Web Service**
   - Go to [render.com/dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your Git repository
   - Select your repository

3. **Configure the Service**
   - **Name:** `backend-caa` (or your preferred name)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Choose Free or Starter (Free tier is suitable for development)

4. **Configure Environment Variables**
   - Scroll down to "Environment Variables"
   - Click "Add Environment Variable"
   - Add the following variables:
     - `DATABASE_URL` - Your PostgreSQL connection string
     - `SECRET_KEY` - Your JWT secret key
     - `ALGORITHM` - (Optional) Default: HS256
     - `ACCESS_TOKEN_EXPIRE_MINUTES` - (Optional) Default: 30
     - `REFRESH_TOKEN_EXPIRE_DAYS` - (Optional) Default: 7

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your application
   - Your API will be available at `https://your-service-name.onrender.com`

### Option 2: Deploy using render.yaml

If you have a `render.yaml` file in your repository:

1. **Push your code** (including `render.yaml`)
2. **Go to Render Dashboard**
3. **Click "New +" → "Blueprint"**
4. **Connect your repository**
5. **Render will automatically detect and use `render.yaml`**

## Database Setup

### Using Render PostgreSQL (Recommended)

1. **Create a PostgreSQL Database**
   - In Render dashboard, click "New +" → "PostgreSQL"
   - Choose a name and plan
   - Click "Create Database"
   - Copy the "Internal Database URL" or "External Database URL"

2. **Use the Database URL**
   - Add it as `DATABASE_URL` environment variable in your web service
   - The internal URL is faster and free, but only works within Render
   - The external URL works from anywhere but may have connection limits

### Using External Database

If you're using an external PostgreSQL database (like Aiven, Supabase, etc.):
- Use the connection string as `DATABASE_URL`
- Make sure the database allows connections from Render's IP ranges
- Include SSL parameters if required: `?sslmode=require`

## Database Migrations

Render web services can run migrations. You have two options:

### Option 1: Run migrations as part of the build

Add to your `render.yaml`:
```yaml
buildCommand: pip install -r requirements.txt && alembic upgrade head
```

### Option 2: Run migrations manually via Render Shell

1. Go to your service in Render dashboard
2. Click "Shell" tab
3. Run: `alembic upgrade head`

### Option 3: Run migrations locally before deployment

```bash
# Set DATABASE_URL to your production database
export DATABASE_URL="your-production-database-url"
alembic upgrade head
```

## Environment Variables

All environment variables must be set in the Render dashboard:
- Go to your service → Environment
- Add each variable
- Click "Save Changes" (this will trigger a new deployment)

### Required Variables

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key

### Optional Variables (have defaults)

- `ALGORITHM` - Default: HS256
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Default: 30
- `REFRESH_TOKEN_EXPIRE_DAYS` - Default: 7

## API Routes

Your API will be available at:
- Production: `https://your-service-name.onrender.com/api/v1/...`
- All routes from your FastAPI app will work as expected

## Testing the Deployment

After deployment, test your endpoints:
- Health check: `https://your-service-name.onrender.com/health`
- API docs: `https://your-service-name.onrender.com/docs`
- Root: `https://your-service-name.onrender.com/`
- Login: `POST https://your-service-name.onrender.com/api/v1/auth/login`

## Troubleshooting

### Build Errors

If you encounter build errors:
1. Check that all dependencies in `requirements.txt` are compatible
2. Ensure Python version is 3.11+ (Render auto-detects from your code)
3. Check Render build logs for specific error messages

### Database Connection Issues

- Verify your `DATABASE_URL` is correct and accessible
- Check if your database allows connections from Render's IP ranges
- Ensure SSL is properly configured if required
- For Render PostgreSQL, use the "Internal Database URL" for better performance

### Application Crashes

1. Check Render service logs
2. Verify all environment variables are set correctly
3. Test the application locally with the same environment variables

### Cold Starts

Render free tier services spin down after 15 minutes of inactivity. The first request after spin-down may take longer. Consider:
- Using Render's Starter plan for always-on services
- Setting up a health check ping service to keep it warm

## Project Structure for Render

```
backend-caa/
├── app/                   # Your FastAPI application
│   └── main.py           # Application entry point
├── render.yaml           # Render configuration (optional)
├── requirements.txt      # Python dependencies
└── README.md
```

## Additional Resources

- [Render Python Documentation](https://render.com/docs/deploy-python)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

