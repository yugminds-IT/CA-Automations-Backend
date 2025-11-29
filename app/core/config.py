from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
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

