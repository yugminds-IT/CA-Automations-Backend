# Postman Testing Guide for Backend CAA API

This guide will help you test all the authentication APIs in Postman.

## Base URL
```
http://localhost:8000
```

## Prerequisites
1. Make sure your FastAPI server is running:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Server should be accessible at `http://localhost:8000`

---

## API Endpoints to Test

### 1. Health Check (Optional - to verify server is running)

**Request:**
- **Method:** `GET`
- **URL:** `http://localhost:8000/health`
- **Headers:** None required

**Expected Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Signup API

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/v1/auth/signup`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "organization_name": "ABC Chartered Accountants",
    "admin_email": "admin@abcca.com",
    "admin_password": "SecurePass123",
    "admin_full_name": "John Doe",
    "admin_phone": "+1234567890"
  }
  ```

**Expected Response (201 Created):**
```json
{
  "organization": {
    "id": 1,
    "name": "ABC Chartered Accountants"
  },
  "admin": {
    "id": 1,
    "email": "admin@abcca.com",
    "full_name": "John Doe",
    "phone": "+1234567890",
    "org_id": 1,
    "role": "admin"
  },
  "message": "Organization and admin user created successfully"
}
```

**Password Requirements:**
- At least 8 characters long
- Contains at least one uppercase letter
- Contains at least one lowercase letter
- Contains at least one digit

---

### 3. Login API

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/v1/auth/login`
- **Headers:**
  ```
  Content-Type: application/x-www-form-urlencoded
  ```
- **Body (x-www-form-urlencoded):**
  | Key | Value |
  |-----|-------|
  | username | admin@abcca.com |
  | password | SecurePass123 |

  **OR use form-data:**
  - Select `Body` → `form-data`
  - Add:
    - Key: `username`, Value: `admin@abcca.com`
    - Key: `password`, Value: `SecurePass123`

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // 1000+ characters
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // 1000+ characters
  "token_type": "bearer"
}
```

**Note:** 
- Both tokens will be 1000+ characters long
- Save the `refresh_token` for testing the refresh endpoint
- Save the `access_token` for authenticated requests

---

### 4. Refresh Token API

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/v1/auth/refresh`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "refresh_token": "YOUR_REFRESH_TOKEN_FROM_LOGIN_RESPONSE"
  }
  ```

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // 1000+ characters
  "token_type": "bearer"
}
```

---

## Postman Collection Setup

### Creating a Postman Collection

1. **Create a new Collection:**
   - Click "New" → "Collection"
   - Name it "Backend CAA API"

2. **Add Environment Variables (Optional but Recommended):**
   - Click "Environments" → "Create Environment"
   - Name: "Local Development"
   - Add variables:
     | Variable | Initial Value | Current Value |
     |----------|---------------|---------------|
     | base_url | http://localhost:8000 | http://localhost:8000 |
     | access_token | | (will be set from login response) |
     | refresh_token | | (will be set from login response) |

3. **Create Requests:**

   **a. Health Check:**
   - Method: `GET`
   - URL: `{{base_url}}/health`

   **b. Signup:**
   - Method: `POST`
   - URL: `{{base_url}}/api/v1/auth/signup`
   - Headers: `Content-Type: application/json`
   - Body: Raw JSON (see example above)

   **c. Login:**
   - Method: `POST`
   - URL: `{{base_url}}/api/v1/auth/login`
   - Headers: `Content-Type: application/x-www-form-urlencoded`
   - Body: x-www-form-urlencoded (see example above)
   - **Tests Tab** (to auto-save tokens):
     ```javascript
     if (pm.response.code === 200) {
         var jsonData = pm.response.json();
         pm.environment.set("access_token", jsonData.access_token);
         pm.environment.set("refresh_token", jsonData.refresh_token);
     }
     ```

   **d. Refresh Token:**
   - Method: `POST`
   - URL: `{{base_url}}/api/v1/auth/refresh`
   - Headers: `Content-Type: application/json`
   - Body: Raw JSON:
     ```json
     {
       "refresh_token": "{{refresh_token}}"
     }
     ```
   - **Tests Tab** (to auto-update access token):
     ```javascript
     if (pm.response.code === 200) {
         var jsonData = pm.response.json();
         pm.environment.set("access_token", jsonData.access_token);
     }
     ```

---

## Step-by-Step Testing Flow

### Step 1: Test Health Check
- Send GET request to `/health`
- Should return `{"status": "healthy"}`

### Step 2: Create Organization & Admin (Signup)
- Send POST request to `/api/v1/auth/signup`
- Use the JSON body example above
- Note the `org_id` and `admin` details from response

### Step 3: Login
- Send POST request to `/api/v1/auth/login`
- Use `username` = email from signup
- Use `password` = password from signup
- Copy the `access_token` and `refresh_token` from response

### Step 4: Test Refresh Token
- Send POST request to `/api/v1/auth/refresh`
- Use the `refresh_token` from Step 3
- Should receive a new `access_token`

---

## Testing Error Cases

### 1. Signup with Invalid Password
**Request:**
```json
{
  "organization_name": "Test Org",
  "admin_email": "test@test.com",
  "admin_password": "weak",  // Too short
  "admin_full_name": "Test User"
}
```
**Expected:** 400 Bad Request with password validation error

### 2. Signup with Duplicate Email
- Try to signup with the same email twice
**Expected:** 400 Bad Request - "User with this email already exists"

### 3. Login with Wrong Password
**Request:**
- username: `admin@abcca.com`
- password: `WrongPassword123`
**Expected:** 401 Unauthorized - "Incorrect email or password"

### 4. Refresh with Invalid Token
**Request:**
```json
{
  "refresh_token": "invalid_token_here"
}
```
**Expected:** 401 Unauthorized - "Invalid or expired refresh token"

---

## Common Issues

1. **"Connection refused"**
   - Make sure the FastAPI server is running
   - Check if port 8000 is available

2. **"422 Unprocessable Entity"**
   - Check that request body matches the expected format
   - Verify Content-Type headers are correct

3. **"401 Unauthorized"**
   - Verify credentials are correct
   - Check if user exists in database

4. **Token errors**
   - Make sure tokens are copied completely (they're 1000+ characters)
   - Don't truncate the tokens

---

## Quick Test Scripts

### Using cURL (Alternative to Postman)

**Signup:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "ABC Chartered Accountants",
    "admin_email": "admin@abcca.com",
    "admin_password": "SecurePass123",
    "admin_full_name": "John Doe",
    "admin_phone": "+1234567890"
  }'
```

**Login:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@abcca.com&password=SecurePass123"
```

**Refresh Token:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN_HERE"}'
```

---

## Additional Resources

- **Interactive API Documentation:** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`

Both of these provide interactive testing interfaces similar to Postman!

