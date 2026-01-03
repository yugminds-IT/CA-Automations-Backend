from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List, Union
from pydantic import BaseModel, EmailStr
from app.db.session import get_db
from app.db.models.user import User, UserRole
from app.db.models.organization import Organization
from app.core.security import get_password_hash, validate_password
from app.api.v1.master_admin.dependencies import get_master_admin

router = APIRouter()


def empty_str_to_none(value: Union[str, int, None]) -> Optional[Union[str, int]]:
    """Convert empty strings to None for query parameters."""
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


# Request/Response Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    org_id: int
    role: Optional[str] = "employee"  # Default to employee


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    org_id: Optional[int] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    org_id: int
    role: str
    created_at: Optional[str] = None
    last_login: Optional[str] = None  # Note: User model doesn't have last_login field yet
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


def validate_role(role: str) -> UserRole:
    """Validate and convert role string to UserRole enum."""
    try:
        return UserRole(role.lower())
    except ValueError:
        valid_roles = [role.value for role in UserRole]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles are: {', '.join(valid_roles)}"
        )


@router.get("/", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    org_id: Optional[str] = Query(None, description="Filter by organization ID (integer)"),
    role: Optional[str] = Query(default=None, description="Filter by role"),
    search: Optional[str] = Query(default=None, description="Search term for email, full_name, phone"),
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    List all users across all organizations with pagination and optional filters.
    Master admin only.
    """
    # Handle empty strings in query parameters (convert to None)
    org_id_parsed = None
    if org_id and org_id.strip():
        try:
            org_id_parsed = int(org_id.strip())
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid org_id format. Must be an integer."
            )
    
    role_parsed = role.strip() if role and role.strip() else None
    search_parsed = search.strip() if search and search.strip() else None
    
    query = db.query(User)
    
    # Filter by organization if provided
    if org_id_parsed is not None:
        # Verify organization exists
        org = db.query(Organization).filter(Organization.id == org_id_parsed).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with id {org_id_parsed} not found"
            )
        query = query.filter(User.org_id == org_id_parsed)
    
    # Filter by role if provided
    if role_parsed:
        try:
            role_enum = validate_role(role_parsed)
            query = query.filter(User.role == role_enum)
        except HTTPException:
            raise
    
    # Apply search filter if provided
    if search_parsed:
        search_term = f"%{search_parsed.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.email).like(search_term),
                func.lower(func.coalesce(User.full_name, "")).like(search_term),
                func.lower(func.coalesce(User.phone, "")).like(search_term),
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.order_by(User.id).offset(skip).limit(limit).all()
    
    # Format response
    user_list = [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            org_id=user.org_id,
            role=user.role.value,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=None  # User model doesn't have last_login field yet
        )
        for user in users
    ]
    
    return UserListResponse(
        users=user_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID. Master admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        org_id=user.org_id,
        role=user.role.value,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=None  # User model doesn't have last_login field yet
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_create: UserCreate,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    Master admin only.
    """
    # Validate password
    is_valid, error_message = validate_password(user_create.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == user_create.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {user_create.org_id} not found"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Validate role
    try:
        user_role = validate_role(user_create.role)
    except HTTPException:
        raise
    
    # Create user
    db_user = User(
        email=user_create.email.lower().strip(),
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name.strip() if user_create.full_name else None,
        phone=user_create.phone.strip() if user_create.phone else None,
        org_id=user_create.org_id,
        role=user_role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        phone=db_user.phone,
        org_id=db_user.org_id,
        role=db_user.role.value,
        created_at=db_user.created_at.isoformat() if db_user.created_at else None,
        last_login=None
    )


@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Update a user.
    Master admin only.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Update email if provided
    if user_update.email is not None:
        # Check for duplicate email (excluding current user)
        existing_user = db.query(User).filter(
            and_(
                User.email == user_update.email.lower().strip(),
                User.id != user_id
            )
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        user.email = user_update.email.lower().strip()
    
    # Update full_name if provided
    if user_update.full_name is not None:
        user.full_name = user_update.full_name.strip() if user_update.full_name else None
    
    # Update phone if provided
    if user_update.phone is not None:
        user.phone = user_update.phone.strip() if user_update.phone else None
    
    # Update org_id if provided
    if user_update.org_id is not None:
        # Verify organization exists
        org = db.query(Organization).filter(Organization.id == user_update.org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with id {user_update.org_id} not found"
            )
        user.org_id = user_update.org_id
    
    # Update role if provided
    if user_update.role is not None:
        try:
            user_role = validate_role(user_update.role)
            user.role = user_role
        except HTTPException:
            raise
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        org_id=user.org_id,
        role=user.role.value,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=None
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user (soft delete by setting a flag, or hard delete).
    Master admin only.
    
    Note: This is currently a hard delete. To implement soft delete, add a 'deleted_at' 
    or 'is_deleted' field to the User model.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return {"detail": f"User {user_id} deleted successfully"}

