from fastapi import APIRouter, Depends
from app.api.v1.master_admin import organizations, users, auth
from app.api.v1.master_admin.email_templates import router as email_templates_router
from app.api.v1.master_admin.dependencies import get_master_admin

router = APIRouter()

# Include auth router (signup and login) - no auth required for these endpoints
router.include_router(
    auth.router,
    prefix="/auth",
    tags=["master-admin-auth"]
)

# Include organization and user routers - all endpoints require master admin authentication
# Router-level dependency ensures ALL endpoints in these routers require master admin role
router.include_router(
    organizations.router,
    prefix="/org",
    tags=["master-admin-organizations"],
    dependencies=[Depends(get_master_admin)]
)

router.include_router(
    users.router,
    prefix="/user",
    tags=["master-admin-users"],
    dependencies=[Depends(get_master_admin)]
)

router.include_router(
    email_templates_router,
    prefix="/email-templates",
    tags=["master-admin-email-templates"],
    dependencies=[Depends(get_master_admin)]
)

