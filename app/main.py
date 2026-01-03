from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.tenant_middleware import TenantMiddleware
from app.api.v1 import auth, org, user, uploads
from app.api.v1.client import client
from app.api.v1.master_admin import router as master_admin_router
from app.api.v1.email_templates import router as email_templates_router
from app.api.v1 import test_email
from app.core.email_scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="Backend CAA API", version="1.0.0")

# Add CORS middleware - allow everything for development
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
    """Start the email scheduler on application startup."""
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the email scheduler on application shutdown."""
    stop_scheduler()

