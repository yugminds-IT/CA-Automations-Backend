from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.session import get_db
from app.db.models.user import User, UserRole
from app.db.models.organization import Organization
from app.db.models.refresh_token import RefreshToken
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    validate_password
)
from datetime import timedelta, datetime
from app.core.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/master-admin/auth/login")


# Request/Response Schemas
class MasterAdminSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    org_id: Optional[int] = None  # Optional: if not provided, will use or create system org


class OrganizationResponse(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    org_id: int
    role: str
    
    class Config:
        from_attributes = True


class MasterAdminSignupResponse(BaseModel):
    user: UserResponse
    organization: OrganizationResponse
    message: str


class MasterAdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration time in seconds
    user: UserResponse
    organization: OrganizationResponse
    role: str  # Explicitly include role for frontend routing


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration time in seconds


def get_or_create_system_organization(db: Session) -> Organization:
    """
    Get or create a system organization for master admins.
    This organization is used when master admins don't specify an org_id.
    """
    system_org = db.query(Organization).filter(
        Organization.name == "System Administration"
    ).first()
    
    if not system_org:
        system_org = Organization(
            name="System Administration",
            city=None,
            state=None,
            country=None,
            pincode=None
        )
        db.add(system_org)
        db.commit()
        db.refresh(system_org)
    
    return system_org


@router.post("/signup", response_model=MasterAdminSignupResponse, status_code=status.HTTP_201_CREATED)
async def master_admin_signup(
    signup_data: MasterAdminSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Signup endpoint for creating a master admin user.
    
    This endpoint creates a master admin user. If org_id is not provided,
    it will use or create a special "System Administration" organization.
    
    Note: Master admin signup should typically be restricted in production
    (e.g., require a special secret key or admin approval).
    """
    # Validate password strength
    is_valid, error_message = validate_password(signup_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == signup_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Determine organization
    if signup_data.org_id:
        # Use provided organization
        organization = db.query(Organization).filter(
            Organization.id == signup_data.org_id
        ).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with id {signup_data.org_id} not found"
            )
    else:
        # Use or create system organization
        organization = get_or_create_system_organization(db)
    
    # Create master admin user
    master_admin_user = User(
        email=signup_data.email.lower().strip(),
        hashed_password=get_password_hash(signup_data.password),
        full_name=signup_data.full_name.strip() if signup_data.full_name else None,
        phone=signup_data.phone.strip() if signup_data.phone else None,
        org_id=organization.id,
        role=UserRole.MASTER_ADMIN
    )
    db.add(master_admin_user)
    db.commit()
    db.refresh(master_admin_user)
    db.refresh(organization)
    
    return MasterAdminSignupResponse(
        user=UserResponse(
            id=master_admin_user.id,
            email=master_admin_user.email,
            full_name=master_admin_user.full_name,
            phone=master_admin_user.phone,
            org_id=master_admin_user.org_id,
            role=master_admin_user.role.value
        ),
        organization=OrganizationResponse(
            id=organization.id,
            name=organization.name,
            city=organization.city,
            state=organization.state,
            country=organization.country,
            pincode=organization.pincode
        ),
        message="Master admin user created successfully"
    )


@router.post("/login", response_model=MasterAdminLoginResponse)
async def master_admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint for master admin users.
    Only users with MASTER_ADMIN role can use this endpoint.
    Returns both access token and refresh token (1000+ characters each).
    """
    # Find user by email (OAuth2PasswordRequestForm uses 'username' field)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user is a master admin
    if user.role != UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This endpoint is for master admin users only."
        )
    
    # Revoke all existing refresh tokens for this user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    
    # Create access token with org_id and role (1000+ characters)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "org_id": user.org_id,
            "role": user.role.value,
            "user_id": user.id
        },
        expires_delta=access_token_expires,
        min_length=1000
    )
    
    # Create refresh token (1000+ characters)
    refresh_token = create_refresh_token(user_id=user.id, min_length=1000)
    
    # Store refresh token in database
    refresh_token_expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_refresh_token = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=refresh_token_expires,
        is_revoked=False
    )
    db.add(db_refresh_token)
    db.commit()
    
    # Refresh user and organization to get latest data
    db.refresh(user)
    organization = db.query(Organization).filter(Organization.id == user.org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Calculate expiration time in seconds
    expires_in_seconds = int(access_token_expires.total_seconds())
    
    return MasterAdminLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            org_id=user.org_id,
            role=user.role.value  # Should be "master_admin"
        ),
        organization=OrganizationResponse(
            id=organization.id,
            name=organization.name,
            city=organization.city,
            state=organization.state,
            country=organization.country,
            pincode=organization.pincode
        ),
        role=user.role.value  # Explicitly include role at top level for frontend
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def master_admin_refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token for master admin using a valid refresh token.
    Returns a new access token (1000+ characters).
    Only works for master admin users.
    """
    # Decode the refresh token
    payload = decode_refresh_token(refresh_data.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if refresh token exists in database and is not revoked
    db_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_data.refresh_token,
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).first()
    
    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )
    
    # Check if token has expired
    if db_refresh_token.expires_at < datetime.utcnow():
        # Mark as revoked
        db_refresh_token.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    
    # Get user and verify they are master admin
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.role != UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Master admin role required."
        )
    
    # Create new access token (1000+ characters)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "org_id": user.org_id,
            "role": user.role.value,
            "user_id": user.id
        },
        expires_delta=access_token_expires,
        min_length=1000
    )
    
    # Calculate expiration time in seconds
    expires_in_seconds = int(access_token_expires.total_seconds())
    
    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds
    )

