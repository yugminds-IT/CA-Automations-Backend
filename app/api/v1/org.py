from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.organization import Organization
from pydantic import BaseModel

router = APIRouter()


class OrganizationCreate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a dummy organization."""
    db_org = Organization(name=org.name)
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

