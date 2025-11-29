# Vercel Deployment Guide

This guide will help you deploy your FastAPI backend to Vercel.

## Prerequisites

1. A Vercel account (sign up at [vercel.com](https://vercel.com))
2. Vercel CLI installed (optional, for CLI deployment)
3. Your database URL and environment variables ready

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Push your code to GitHub/GitLab/Bitbucket**
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   git push origin main
   ```

2. **Import Project to Vercel**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Click "Import Git Repository"
   - Select your repository
   - Vercel will auto-detect the Python/FastAPI setup

3. **Configure Environment Variables**
   - In the Vercel project settings, go to "Environment Variables"
   - Add the following variables:
     - `DATABASE_URL` - Your PostgreSQL connection string
     - `SECRET_KEY` - Your JWT secret key
     - `ALGORITHM` - (Optional) Default: HS256
     - `ACCESS_TOKEN_EXPIRE_MINUTES` - (Optional) Default: 30
     - `REFRESH_TOKEN_EXPIRE_DAYS` - (Optional) Default: 7

4. **Deploy**
   - Click "Deploy"
   - Wait for the build to complete
   - Your API will be available at `https://your-project.vercel.app`

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel
   ```
   - Follow the prompts
   - When asked about environment variables, you can add them now or later in the dashboard

4. **Deploy to Production**
   ```bash
   vercel --prod
   ```

## Important Notes

### Database Migrations

Vercel serverless functions are stateless, so you **cannot run Alembic migrations directly on Vercel**. You have two options:

1. **Run migrations locally or from another environment** before deploying:
   ```bash
   alembic upgrade head
   ```

2. **Use a migration service** or run migrations from a CI/CD pipeline

### Database Connection

- Make sure your database is accessible from the internet (not just localhost)
- Use connection pooling for better performance
- Consider using a managed database service like:
  - Vercel Postgres
  - Supabase
  - Neon
  - Railway
  - Render

### Environment Variables

All environment variables must be set in the Vercel dashboard:
- Go to your project → Settings → Environment Variables
- Add each variable for the appropriate environments (Production, Preview, Development)

### API Routes

Your API will be available at:
- Production: `https://your-project.vercel.app/api/v1/...`
- All routes from your FastAPI app will work as expected

### Testing the Deployment

After deployment, test your endpoints:
- Health check: `https://your-project.vercel.app/health`
- API docs: `https://your-project.vercel.app/docs`
- Login: `POST https://your-project.vercel.app/api/v1/auth/login`

## Troubleshooting

### Build Errors

If you encounter build errors:
1. Check that all dependencies in `requirements.txt` are compatible
2. Ensure Python version is 3.11 (configured in `vercel.json`)
3. Check Vercel build logs for specific error messages

### Database Connection Issues

- Verify your `DATABASE_URL` is correct and accessible
- Check if your database allows connections from Vercel's IP ranges
- Ensure SSL is properly configured if required

### Cold Start Performance

Serverless functions have cold starts. To minimize:
- Use Vercel Pro plan for better performance
- Consider using Vercel Edge Functions for specific routes if applicable

## Project Structure for Vercel

```
backend-caa/
├── api/
│   └── index.py          # Serverless function entry point
├── app/                   # Your FastAPI application
├── vercel.json           # Vercel configuration
├── .vercelignore         # Files to exclude from deployment
└── requirements.txt      # Python dependencies
```

## Additional Resources

- [Vercel Python Documentation](https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python)
- [FastAPI on Vercel](https://vercel.com/guides/deploying-fastapi-with-vercel)
- [Mangum Documentation](https://mangum.io/)

