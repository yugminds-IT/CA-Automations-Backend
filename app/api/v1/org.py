from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.db.models.organization import Organization
from pydantic import BaseModel

router = APIRouter()


class OrganizationCreate(BaseModel):
    name: str
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
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[OrganizationResponse], status_code=status.HTTP_200_OK)
def list_organizations(
    db: Session = Depends(get_db)
):
    """
    List all organizations with fields: id, name, city, state, country, pincode.
    """
    organizations = db.query(Organization).order_by(Organization.id).all()
    
    return [
        OrganizationResponse(
            id=org.id,
            name=org.name,
            city=org.city,
            state=org.state,
            country=org.country,
            pincode=org.pincode
        )
        for org in organizations
    ]


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization."""
    if not org.name or not org.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name is required"
        )
    
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
        pincode=db_org.pincode
    )

