from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models.organization import Organization
from app.db.models.user import User
from app.api.v1.master_admin.dependencies import get_master_admin

router = APIRouter()


# Request/Response Schemas
class OrganizationCreate(BaseModel):
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int
    skip: int
    limit: int


@router.get("/", response_model=OrganizationListResponse, status_code=status.HTTP_200_OK)
def list_organizations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search term for name, city, state, country"),
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    List all organizations with pagination and optional search.
    Master admin only.
    """
    query = db.query(Organization)
    
    # Apply search filter if provided (handle empty string as None)
    if search and search.strip():
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Organization.name).like(search_term),
                func.lower(func.coalesce(Organization.city, "")).like(search_term),
                func.lower(func.coalesce(Organization.state, "")).like(search_term),
                func.lower(func.coalesce(Organization.country, "")).like(search_term),
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    organizations = query.order_by(Organization.id).offset(skip).limit(limit).all()
    
    # Format response
    org_list = [
        OrganizationResponse(
            id=org.id,
            name=org.name,
            city=org.city,
            state=org.state,
            country=org.country,
            pincode=org.pincode,
            created_at=org.created_at.isoformat() if org.created_at else None,
            updated_at=org.updated_at.isoformat() if org.updated_at else None
        )
        for org in organizations
    ]
    
    return OrganizationListResponse(
        organizations=org_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{org_id}", response_model=OrganizationResponse, status_code=status.HTTP_200_OK)
def get_organization(
    org_id: int,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """Get organization by ID. Master admin only."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {org_id} not found"
        )
    
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        city=organization.city,
        state=organization.state,
        country=organization.country,
        pincode=organization.pincode,
        created_at=organization.created_at.isoformat() if organization.created_at else None,
        updated_at=organization.updated_at.isoformat() if organization.updated_at else None
    )


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org: OrganizationCreate,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new organization.
    Master admin only.
    """
    # Validate required fields
    if not org.name or not org.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name is required"
        )
    
    # Check for duplicate organization name (case-insensitive)
    existing_org = db.query(Organization).filter(
        func.lower(Organization.name) == org.name.lower().strip()
    ).first()
    
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this name already exists"
        )
    
    # Create organization
    db_org = Organization(
        name=org.name.strip(),
        city=org.city.strip() if org.city else None,
        state=org.state.strip() if org.state else None,
        country=org.country.strip() if org.country else None,
        pincode=org.pincode.strip() if org.pincode else None
    )
    
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    
    return OrganizationResponse(
        id=db_org.id,
        name=db_org.name,
        city=db_org.city,
        state=db_org.state,
        country=db_org.country,
        pincode=db_org.pincode,
        created_at=db_org.created_at.isoformat() if db_org.created_at else None,
        updated_at=db_org.updated_at.isoformat() if db_org.updated_at else None
    )


@router.put("/{org_id}", response_model=OrganizationResponse, status_code=status.HTTP_200_OK)
def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Update an organization.
    Master admin only.
    """
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {org_id} not found"
        )
    
    # Update fields if provided
    if org_update.name is not None:
        if not org_update.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name cannot be empty"
            )
        # Check for duplicate name (excluding current organization)
        existing_org = db.query(Organization).filter(
            and_(
                func.lower(Organization.name) == org_update.name.lower().strip(),
                Organization.id != org_id
            )
        ).first()
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this name already exists"
            )
        organization.name = org_update.name.strip()
    
    if org_update.city is not None:
        organization.city = org_update.city.strip() if org_update.city else None
    if org_update.state is not None:
        organization.state = org_update.state.strip() if org_update.state else None
    if org_update.country is not None:
        organization.country = org_update.country.strip() if org_update.country else None
    if org_update.pincode is not None:
        organization.pincode = org_update.pincode.strip() if org_update.pincode else None
    
    db.commit()
    db.refresh(organization)
    
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        city=organization.city,
        state=organization.state,
        country=organization.country,
        pincode=organization.pincode,
        created_at=organization.created_at.isoformat() if organization.created_at else None,
        updated_at=organization.updated_at.isoformat() if organization.updated_at else None
    )


@router.delete("/{org_id}", status_code=status.HTTP_200_OK)
def delete_organization(
    org_id: int,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Delete an organization (soft delete by setting a flag, or hard delete if no users exist).
    Master admin only.
    
    Note: This is currently a hard delete. To implement soft delete, add a 'deleted_at' 
    or 'is_deleted' field to the Organization model.
    """
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {org_id} not found"
        )
    
    # Check if organization has users
    user_count = db.query(User).filter(User.org_id == org_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {user_count} user(s). Please remove or reassign users first."
        )
    
    # Delete organization
    db.delete(organization)
    db.commit()
    
    return {"detail": f"Organization {org_id} deleted successfully"}
