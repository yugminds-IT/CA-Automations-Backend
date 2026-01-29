from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Required settings
    DATABASE_URL: str
    SECRET_KEY: str
    
    # JWT settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 7200   # Default: 7200 minutes (5 days) - set in .env to override
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # Default: 30 days - set in .env to override
    
    # Database connection pool settings (for production scalability)
    DB_POOL_SIZE: int = 10  # Base pool size (override via env for high traffic)
    DB_MAX_OVERFLOW: int = 5  # Extra connections under load (override via env)
    DB_POOL_TIMEOUT: int = 30  # Seconds to wait for connection from pool
    DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    DB_CONNECT_TIMEOUT: int = 15  # Connection timeout (generous for cold start)
    DB_STATEMENT_TIMEOUT: int = 60  # Statement timeout in seconds
    
    # Email settings (optional - email sending will be disabled if not configured)
    # Use these env vars only:
    #   SMTP_FROM=ca-services@navedhana.com
    #   SMTP_HOST=smtp.hostinger.com
    #   SMTP_PASS=your-password
    #   SMTP_PORT=465
    #   SMTP_SECURE=true
    #   SMTP_USER=contact@navedhana.com
    SMTP_FROM: Optional[str] = None  # Sender email address
    SMTP_HOST: Optional[str] = None
    SMTP_PASS: Optional[str] = None  # SMTP password
    SMTP_PORT: Optional[int] = 465  # 465 = SSL, 587 = STARTTLS
    SMTP_SECURE: bool = True  # true for port 465 (SSL), false for 587 (STARTTLS)
    SMTP_USER: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = "Navedhana"  # Optional sender name (not in your env; default used)
    SMTP_TIMEOUT: int = 30  # Connection timeout (seconds)
    SMTP_RETRY_ATTEMPTS: int = 3  # Retries for failed emails
    SMTP_EMAIL_DELAY: float = 1.0  # Delay between multiple emails (seconds)
    
    # Frontend URL for login links in emails
    FRONTEND_URL: Optional[str] = None
    
    # Encryption key for storing plain passwords (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ENCRYPTION_KEY: Optional[str] = None
    
    # Environment detection
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # CORS settings (for production security)
    CORS_ORIGINS: Optional[str] = None  # Comma-separated list of allowed origins (e.g., "https://app1.com,https://app2.com")
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # File storage settings
    FILE_STORAGE_BACKEND: str = "local"  # "local" or "s3"
    
    # S3 settings (required if FILE_STORAGE_BACKEND="s3")
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET_NAME: Optional[str] = None
    AWS_S3_ENDPOINT_URL: Optional[str] = None  # For S3-compatible services (e.g., DigitalOcean Spaces, MinIO)
    
    class Config:
        env_file = ".env"  # Optional: only used if file exists
        env_file_encoding = "utf-8"
        case_sensitive = True


# Initialize settings with better error handling
try:
    settings = Settings()
except Exception as e:
    # Provide helpful error message for missing environment variables
    missing_vars = []
    if not os.getenv("DATABASE_URL"):
        missing_vars.append("DATABASE_URL")
    if not os.getenv("SECRET_KEY"):
        missing_vars.append("SECRET_KEY")
    
    if missing_vars:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            "Please set these in your deployment platform's environment variables."
        )
        raise ValueError(error_msg) from e
    raise

