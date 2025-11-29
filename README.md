# Backend CAA API

A FastAPI backend boilerplate with JWT authentication, PostgreSQL database, and tenant middleware.

## Features

- FastAPI framework
- JWT authentication
- PostgreSQL database with SQLAlchemy
- Tenant middleware for multi-tenant support
- Alembic for database migrations
- Render deployment support

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- pip

### Installation

1. Clone the repository and navigate to the project directory:
```bash
cd backend-caa
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

**For macOS users:** If you encounter errors installing `psycopg2-binary`, first install libpq:
```bash
brew install libpq
```

Then install Python dependencies with the proper environment variables:
```bash
export LDFLAGS="-L$(brew --prefix libpq)/lib"
export CPPFLAGS="-I$(brew --prefix libpq)/include"
pip install -r requirements.txt
```

**For other systems:**
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env .env.local  # Optional: create a local copy
# Edit .env with your database credentials and secret key
```

5. Start PostgreSQL:
```bash
# Make sure PostgreSQL is running and create the database
createdb backend_caa
```

6. Run database migrations:
```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

7. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Deployment

This project is configured for deployment on Render. See `RENDER_DEPLOYMENT.md` for detailed deployment instructions.

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login and get JWT token

### Organizations
- `POST /api/v1/org/` - Create a new organization

### Users
- `POST /api/v1/user/` - Create a new user

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Secret key for JWT token signing
- `ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time in minutes (default: 30)

## Project Structure

```
backend-caa/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── org.py
│   │       └── user.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── tenant_middleware.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── organization.py
│   │       └── user.py
│   └── main.py
├── alembic/
├── alembic.ini
├── requirements.txt
├── runtime.txt
├── render.yaml
└── README.md
```

## Development

To run in development mode with auto-reload:

```bash
uvicorn app.main:app --reload
```

## License

MIT

