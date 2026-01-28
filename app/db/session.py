from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# Lazy initialization for serverless environments
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine with environment-optimized connection pooling."""
    global _engine
    if _engine is None:
        # Convert postgres:// or postgresql:// to postgresql+psycopg:// for psycopg3
        database_url = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
        
        # Detect environment type
        is_serverless = os.getenv("VERCEL") is not None or os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if is_serverless:
            # Serverless-optimized connection pool settings
            # Small pool to prevent connection exhaustion
            pool_size = int(os.getenv("DB_POOL_SIZE", "2"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "0"))
            pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
            pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        elif environment == "production":
            # Production settings - use config values (can be overridden via env vars)
            pool_size = settings.DB_POOL_SIZE
            max_overflow = settings.DB_MAX_OVERFLOW
            pool_timeout = settings.DB_POOL_TIMEOUT
            pool_recycle = settings.DB_POOL_RECYCLE
        else:
            # Local development settings - smaller pool for dev
            pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "5"))
            pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
            pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        
        connect_args = {
            "connect_timeout": settings.DB_CONNECT_TIMEOUT,
        }
        # statement_timeout via options (skip if using PgBouncer; set in DB otherwise)
        if settings.DB_STATEMENT_TIMEOUT > 0:
            connect_args["options"] = f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT * 1000}"

        _engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=False,
            connect_args=connect_args,
        )
    return _engine


def get_session_local():
    """Get or create session maker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    """Dependency to get database session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

