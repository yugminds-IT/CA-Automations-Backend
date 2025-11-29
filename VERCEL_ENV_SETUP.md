# How to Add Environment Variables in Vercel

## Quick Steps

1. **Go to your Vercel project dashboard**
   - Visit [vercel.com](https://vercel.com)
   - Select your project: `ca-automations-backend`

2. **Navigate to Environment Variables**
   - Click on **Settings** (top menu)
   - Click on **Environment Variables** (left sidebar)

3. **Add Required Variables**

   Add these two **required** variables:

   ### DATABASE_URL
   - **Key:** `DATABASE_URL`
   - **Value:** Your PostgreSQL connection string
     - Format: `postgres://username:password@host:port/database?sslmode=require`
     - Get this from your database provider (Aiven, Supabase, etc.)
     - Example: `postgres://user:pass@host.example.com:5432/mydb?sslmode=require`
   - **Environments:** Select all (Production, Preview, Development)

   ### SECRET_KEY
   - **Key:** `SECRET_KEY`
   - **Value:** A strong random secret key for JWT signing
     - Generate one using: `openssl rand -hex 32`
     - Or use a long random string
   - **Environments:** Select all (Production, Preview, Development)

4. **Optional Variables** (have defaults, but you can set them):
   - `ALGORITHM` = `HS256` (default)
   - `ACCESS_TOKEN_EXPIRE_MINUTES` = `30` (default)
   - `REFRESH_TOKEN_EXPIRE_DAYS` = `7` (default)

5. **Redeploy**
   - After adding variables, go to **Deployments** tab
   - Click the **three dots** (⋯) on your latest deployment
   - Click **Redeploy**
   - Or push a new commit to trigger automatic deployment

## Visual Guide

```
Vercel Dashboard
  └─ Your Project (ca-automations-backend)
      └─ Settings
          └─ Environment Variables
              └─ Add New
                  ├─ Key: DATABASE_URL
                  ├─ Value: [your connection string]
                  └─ Environments: ☑ Production ☑ Preview ☑ Development
                  └─ Save
              
              └─ Add New
                  ├─ Key: SECRET_KEY
                  ├─ Value: [your secret key]
                  └─ Environments: ☑ Production ☑ Preview ☑ Development
                  └─ Save
```

## Important Notes

- **Never commit secrets to git** - They should only be in Vercel environment variables
- **Set for all environments** - Make sure to check Production, Preview, and Development
- **Redeploy after adding** - Environment variables are only available after redeployment
- **Test after deployment** - Visit `https://your-project.vercel.app/health` to verify it works

## Verify It's Working

After adding variables and redeploying:

1. Check the deployment logs - should not show validation errors
2. Visit `https://your-project.vercel.app/health` - should return `{"status": "healthy"}`
3. Visit `https://your-project.vercel.app/` - should return `{"message": "Backend CAA API"}`

## Troubleshooting

If it still doesn't work after adding variables:

1. **Double-check variable names** - Must be exactly `DATABASE_URL` and `SECRET_KEY` (case-sensitive)
2. **Verify all environments are selected** - Check Production, Preview, and Development
3. **Check for typos** - Copy-paste the variable names to avoid typos
4. **Redeploy** - Environment variables only apply to new deployments
5. **Check deployment logs** - Look for any other errors after the validation error is fixed

