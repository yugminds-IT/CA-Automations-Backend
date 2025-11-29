# Postman Collection Import Guide

## Quick Start

### Step 1: Import Collection
1. Open **Postman**
2. Click **Import** button (top left)
3. Click **Upload Files**
4. Select: `Backend_CAA_API.postman_collection.json`
5. Click **Import**

### Step 2: Import Environment (Optional but Recommended)
1. Click **Import** again
2. Select: `Postman_Environment.postman_environment.json`
3. Click **Import**
4. Select the environment from dropdown (top right): **"Backend CAA - Local Development"**

### Step 3: Start Your Server
```bash
uvicorn app.main:app --reload
```

### Step 4: Test the APIs
Run requests in this order:

1. **Health Check** → Verify server is running
2. **Signup** → Create organization and admin user (auto-saves `org_id` and `admin_email`)
3. **Login** → Get tokens (auto-saves `access_token` and `refresh_token`)
4. **Refresh Token** → Get new access token
5. **Create Organization** → (Optional) Create another organization
6. **Create User** → Create employee user (uses saved `org_id`)

---

## Collection Structure

### 📁 Health & Status
- **Root** - `GET /`
- **Health Check** - `GET /health`

### 🔐 Authentication
- **Signup** - `POST /api/v1/auth/signup`
  - Creates organization + admin user
  - Auto-saves: `org_id`, `admin_email`
  
- **Login** - `POST /api/v1/auth/login`
  - Gets access token + refresh token (1000+ chars each)
  - Auto-saves: `access_token`, `refresh_token`
  
- **Refresh Token** - `POST /api/v1/auth/refresh`
  - Gets new access token
  - Auto-updates: `access_token`

### 🏢 Organizations
- **Create Organization** - `POST /api/v1/org/`

### 👥 Users
- **Create User (Employee)** - `POST /api/v1/user/`
  - Creates employee user (uses `org_id` from environment)

---

## Features

✅ **Auto-save tokens** - Login automatically saves tokens to environment variables  
✅ **Auto-update tokens** - Refresh token automatically updates access token  
✅ **Variable usage** - All requests use environment variables  
✅ **Organized folders** - Endpoints grouped logically  
✅ **Console logging** - See token lengths and IDs in console  
✅ **Ready to use** - All requests pre-configured with examples  

---

## Environment Variables

The collection uses these variables (auto-populated after first requests):

| Variable | Description | Auto-set by |
|----------|-------------|-------------|
| `base_url` | API base URL | Manual (default: http://localhost:8000) |
| `admin_email` | Admin email | Signup request |
| `org_id` | Organization ID | Signup request |
| `access_token` | JWT access token | Login/Refresh requests |
| `refresh_token` | JWT refresh token | Login request |

---

## Testing Flow

### Complete Flow Example:

1. **Health Check**
   - Should return: `{"status": "healthy"}`

2. **Signup**
   ```json
   {
     "organization_name": "ABC Chartered Accountants",
     "admin_email": "admin@abcca.com",
     "admin_password": "SecurePass123",
     "admin_full_name": "John Doe",
     "admin_phone": "+1234567890"
   }
   ```
   - ✅ Saves `org_id` and `admin_email` automatically

3. **Login**
   - Uses saved `admin_email` from environment
   - ✅ Saves `access_token` and `refresh_token` automatically
   - Check console: Should show tokens are 1000+ characters

4. **Refresh Token**
   - Uses saved `refresh_token` from environment
   - ✅ Updates `access_token` automatically

5. **Create User (Employee)**
   - Uses saved `org_id` from environment
   - Creates employee with default role

---

## Troubleshooting

### Variables not updating?
- Make sure environment is selected (top right dropdown)
- Check if test scripts ran (View → Show Postman Console)

### Server not responding?
- Verify server is running: `http://localhost:8000/health`
- Check port 8000 is not in use

### Import errors?
- Ensure JSON files are valid
- Try importing collection and environment separately

---

## Alternative: FastAPI Docs

You can also test directly in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

