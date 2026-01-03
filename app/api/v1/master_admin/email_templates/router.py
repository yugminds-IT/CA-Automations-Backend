from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from pydantic import BaseModel, validator
from app.db.session import get_db
from app.db.models.email_template import EmailTemplate, EmailTemplateCategory, EmailTemplateType
from app.db.models.user import User
from app.api.v1.master_admin.dependencies import get_master_admin

router = APIRouter()


# Request/Response Schemas
class EmailTemplateCreate(BaseModel):
    name: str
    category: EmailTemplateCategory
    type: EmailTemplateType
    subject: str
    body: str
    variables: Optional[List[str]] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name is required')
        if len(v) > 255:
            raise ValueError('Name must be 255 characters or less')
        return v.strip()
    
    @validator('subject')
    def validate_subject(cls, v):
        if not v or not v.strip():
            raise ValueError('Subject is required')
        if len(v) > 500:
            raise ValueError('Subject must be 500 characters or less')
        return v.strip()
    
    @validator('body')
    def validate_body(cls, v):
        if not v or not v.strip():
            raise ValueError('Body is required')
        if len(v) > 10000:
            raise ValueError('Body must be 10000 characters or less')
        return v.strip()


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    variables: Optional[List[str]] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Name cannot be empty')
            if len(v) > 255:
                raise ValueError('Name must be 255 characters or less')
            return v.strip()
        return v
    
    @validator('subject')
    def validate_subject(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Subject cannot be empty')
            if len(v) > 500:
                raise ValueError('Subject must be 500 characters or less')
            return v.strip()
        return v
    
    @validator('body')
    def validate_body(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Body cannot be empty')
            if len(v) > 10000:
                raise ValueError('Body must be 10000 characters or less')
            return v.strip()
        return v


class EmailTemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    type: str
    subject: str
    body: str
    is_default: bool
    org_id: Optional[int] = None
    master_template_id: Optional[int] = None
    variables: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True


class EmailTemplateListResponse(BaseModel):
    templates: List[EmailTemplateResponse]
    total: int
    skip: int
    limit: int


@router.get("/", response_model=EmailTemplateListResponse, status_code=status.HTTP_200_OK)
def list_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    category: Optional[EmailTemplateCategory] = Query(None, description="Filter by category"),
    type: Optional[EmailTemplateType] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search term for name, subject"),
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    List all master email templates.
    Master admin only.
    """
    query = db.query(EmailTemplate).filter(
        EmailTemplate.is_default == True,
        EmailTemplate.org_id == None
    )
    
    # Filter by category if provided
    if category:
        query = query.filter(EmailTemplate.category == category)
    
    # Filter by type if provided
    if type:
        query = query.filter(EmailTemplate.type == type)
    
    # Apply search filter if provided
    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(EmailTemplate.name).like(search_term),
                func.lower(EmailTemplate.subject).like(search_term)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    templates = query.order_by(EmailTemplate.id).offset(skip).limit(limit).all()
    
    # Format response
    template_list = [
        EmailTemplateResponse(
            id=template.id,
            name=template.name,
            category=template.category.value,
            type=template.type.value,
            subject=template.subject,
            body=template.body,
            is_default=template.is_default,
            org_id=template.org_id,
            master_template_id=template.master_template_id,
            variables=template.variables,
            created_at=template.created_at.isoformat() if template.created_at else None,
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            created_by=template.created_by
        )
        for template in templates
    ]
    
    return EmailTemplateListResponse(
        templates=template_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{template_id}", response_model=EmailTemplateResponse, status_code=status.HTTP_200_OK)
def get_template(
    template_id: int,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """Get master email template by ID. Master admin only."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.is_default == True,
        EmailTemplate.org_id == None
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master template with id {template_id} not found"
        )
    
    return EmailTemplateResponse(
        id=template.id,
        name=template.name,
        category=template.category.value,
        type=template.type.value,
        subject=template.subject,
        body=template.body,
        is_default=template.is_default,
        org_id=template.org_id,
        master_template_id=template.master_template_id,
        variables=template.variables,
        created_at=template.created_at.isoformat() if template.created_at else None,
        updated_at=template.updated_at.isoformat() if template.updated_at else None,
        created_by=template.created_by
    )


@router.post("/", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: EmailTemplateCreate,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new master email template.
    Master admin only.
    """
    # Check for duplicate name in master templates
    existing_template = db.query(EmailTemplate).filter(
        EmailTemplate.name == template_data.name,
        EmailTemplate.is_default == True,
        EmailTemplate.org_id == None
    ).first()
    
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )
    
    # Create template
    db_template = EmailTemplate(
        name=template_data.name,
        category=template_data.category,
        type=template_data.type,
        subject=template_data.subject,
        body=template_data.body,
        is_default=True,
        org_id=None,
        master_template_id=None,
        variables=template_data.variables,
        created_by=current_user.id
    )
    
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    return EmailTemplateResponse(
        id=db_template.id,
        name=db_template.name,
        category=db_template.category.value,
        type=db_template.type.value,
        subject=db_template.subject,
        body=db_template.body,
        is_default=db_template.is_default,
        org_id=db_template.org_id,
        master_template_id=db_template.master_template_id,
        variables=db_template.variables,
        created_at=db_template.created_at.isoformat() if db_template.created_at else None,
        updated_at=db_template.updated_at.isoformat() if db_template.updated_at else None,
        created_by=db_template.created_by
    )


@router.put("/{template_id}", response_model=EmailTemplateResponse, status_code=status.HTTP_200_OK)
def update_template(
    template_id: int,
    template_update: EmailTemplateUpdate,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Update a master email template.
    Master admin only.
    Only updates templates where is_default=True and org_id=null.
    """
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.is_default == True,
        EmailTemplate.org_id == None
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master template with id {template_id} not found"
        )
    
    # Update fields if provided
    if template_update.name is not None:
        # Check for duplicate name (excluding current template)
        existing_template = db.query(EmailTemplate).filter(
            and_(
                EmailTemplate.name == template_update.name,
                EmailTemplate.is_default == True,
                EmailTemplate.org_id == None,
                EmailTemplate.id != template_id
            )
        ).first()
        if existing_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template with this name already exists"
            )
        template.name = template_update.name
    
    if template_update.subject is not None:
        template.subject = template_update.subject
    if template_update.body is not None:
        template.body = template_update.body
    if template_update.variables is not None:
        template.variables = template_update.variables
    
    db.commit()
    db.refresh(template)
    
    return EmailTemplateResponse(
        id=template.id,
        name=template.name,
        category=template.category.value,
        type=template.type.value,
        subject=template.subject,
        body=template.body,
        is_default=template.is_default,
        org_id=template.org_id,
        master_template_id=template.master_template_id,
        variables=template.variables,
        created_at=template.created_at.isoformat() if template.created_at else None,
        updated_at=template.updated_at.isoformat() if template.updated_at else None,
        created_by=template.created_by
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_master_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a master email template.
    Master admin only.
    Only deletes templates where is_default=True and org_id=null.
    Checks if any orgs have customized versions.
    """
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.is_default == True,
        EmailTemplate.org_id == None
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master template with id {template_id} not found"
        )
    
    # Check if any orgs have customized versions
    customized_count = db.query(EmailTemplate).filter(
        EmailTemplate.master_template_id == template_id
    ).count()
    
    if customized_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete master template. {customized_count} organization(s) have customized versions. Please notify them first."
        )
    
    # Delete template
    db.delete(template)
    db.commit()
    
    return None

