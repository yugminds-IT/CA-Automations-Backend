from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.tenant_middleware import TenantMiddleware
from app.api.v1 import auth, org, user

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


@app.get("/")
def root():
    return {"message": "Backend CAA API"}


@app.get("/health")
def health():
    return {"status": "healthy"}

