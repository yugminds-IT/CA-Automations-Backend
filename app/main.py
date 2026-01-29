from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.tenant_middleware import TenantMiddleware
from app.api.v1 import auth, org, user, uploads
from app.api.v1.client import client
from app.api.v1.master_admin import router as master_admin_router
from app.api.v1.email_templates import router as email_templates_router
from app.api.v1 import test_email
from app.core.email_scheduler import start_scheduler, stop_scheduler
from app.core.config import settings

app = FastAPI(title="Backend CAA API", version="1.0.0")

# Configure CORS based on environment
if settings.ENVIRONMENT == "production" and settings.CORS_ORIGINS:
    # Production: Use specific origins from config
    allowed_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Development/Staging: Allow all origins (less secure, but convenient for dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add tenant middleware
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(org.router, prefix="/api/v1/org", tags=["organizations"])
app.include_router(user.router, prefix="/api/v1/user", tags=["users"])
app.include_router(client.router, prefix="/api/v1/client", tags=["clients"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["uploads"])
# Org admin email templates endpoints
app.include_router(email_templates_router.router, prefix="/api/v1/email-templates", tags=["email-templates"])
# Master admin endpoints
app.include_router(master_admin_router.router, prefix="/api/v1/master-admin", tags=["master-admin"])
# Test endpoints
app.include_router(test_email.router, prefix="/api/v1", tags=["test"])


@app.get("/")
def root():
    return {"message": "Backend CAA API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Start the email scheduler on application startup. Non-fatal if it fails."""
    import logging
    from app.core.email_service import is_email_configured, get_missing_email_config

    log = logging.getLogger("uvicorn.error")
    if is_email_configured():
        log.info("Email configured (SMTP). Sending enabled.")
    else:
        log.warning(
            "Email NOT configured. Missing: %s. Set these in your deployment platform's environment variables (not only in .env).",
            ", ".join(get_missing_email_config()),
        )
    try:
        start_scheduler()
    except Exception as e:
        log.warning("Email scheduler failed to start (scheduled emails disabled): %s", e)


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the email scheduler on application shutdown."""
    stop_scheduler()

