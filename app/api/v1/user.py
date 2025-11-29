from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User, UserRole
from app.db.models.organization import Organization
from app.core.security import get_password_hash
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    org_id: int


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    org_id: int
    role: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a dummy user."""
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create user (defaults to EMPLOYEE role - admins create employees)
    db_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        phone=user.phone,
        org_id=user.org_id,
        role=UserRole.EMPLOYEE
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
        role=db_user.role.value
    )

