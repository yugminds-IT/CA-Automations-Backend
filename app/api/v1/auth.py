from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# Pydantic schemas for signup
class SignupRequest(BaseModel):
    organization_name: str
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str
    admin_phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    pincode: Optional[str]
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    org_id: int
    role: str
    
    class Config:
        from_attributes = True


class SignupResponse(BaseModel):
    organization: OrganizationResponse
    admin: UserResponse
    message: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration time in seconds
    user: UserResponse
    organization: OrganizationResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration time in seconds


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    signup_data: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Signup endpoint for creating a new organization with an admin user.
    
    This endpoint creates:
    1. A new organization
    2. An admin user for that organization
    
    The admin user can later create employee accounts for their organization.
    """
    # Validate password strength
    is_valid, error_message = validate_password(signup_data.admin_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == signup_data.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create organization with address details
    new_org = Organization(
        name=signup_data.organization_name,
        city=signup_data.city,
        state=signup_data.state,
        country=signup_data.country,
        pincode=signup_data.pincode
    )
    db.add(new_org)
    db.flush()  # Flush to get the org_id without committing
    
    # Create admin user
    admin_user = User(
        email=signup_data.admin_email,
        hashed_password=get_password_hash(signup_data.admin_password),
        full_name=signup_data.admin_full_name,
        phone=signup_data.admin_phone,
        org_id=new_org.id,
        role=UserRole.ADMIN
    )
    db.add(admin_user)
    
    # Commit both organization and user
    db.commit()
    db.refresh(new_org)
    db.refresh(admin_user)
    
    # Send login credentials email to admin (in background)
    from app.core.email_service import send_login_credentials_email
    background_tasks.add_task(
        send_login_credentials_email,
        recipient_email=signup_data.admin_email,
        recipient_name=signup_data.admin_full_name or "Admin",
        login_email=signup_data.admin_email,
        password=signup_data.admin_password,
        role="admin",
        organization_name=signup_data.organization_name
    )
    
    return SignupResponse(
        organization=OrganizationResponse(
            id=new_org.id,
            name=new_org.name,
            city=new_org.city,
            state=new_org.state,
            country=new_org.country,
            pincode=new_org.pincode
        ),
        admin=UserResponse(
            id=admin_user.id,
            email=admin_user.email,
            full_name=admin_user.full_name,
            phone=admin_user.phone,
            org_id=admin_user.org_id,
            role=admin_user.role.value
        ),
        message="Organization and admin user created successfully"
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint that returns both access token and refresh token.
    Both tokens are guaranteed to be 1000+ characters long.
    
    Note: Master admin users should use /api/v1/master-admin/auth/login instead.
    """
    # Find user by email (OAuth2PasswordRequestForm uses 'username' field)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Prevent master admin from using regular login endpoint
    # Master admins must use the dedicated master admin login endpoint
    if user.role == UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Master admin users must use /api/v1/master-admin/auth/login endpoint"
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
    
    return LoginResponse(
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
            role=user.role.value
        ),
        organization=OrganizationResponse(
            id=organization.id,
            name=organization.name,
            city=organization.city,
            state=organization.state,
            country=organization.country,
            pincode=organization.pincode
        )
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    Returns a new access token (1000+ characters).
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
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
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

