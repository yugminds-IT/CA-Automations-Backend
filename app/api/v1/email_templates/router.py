from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from pydantic import BaseModel, validator
from app.db.session import get_db
from app.db.models.email_template import EmailTemplate, EmailTemplateCategory, EmailTemplateType
from app.db.models.user import User
from app.api.v1.email_templates.dependencies import get_admin_user

router = APIRouter()


# Request/Response Schemas
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


class CustomizeTemplateRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    
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


class CreateTemplateRequest(BaseModel):
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


class UpdateTemplateRequest(BaseModel):
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


@router.get("/master/", response_model=EmailTemplateListResponse, status_code=status.HTTP_200_OK)
def list_master_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    category: Optional[EmailTemplateCategory] = Query(None, description="Filter by category"),
    type: Optional[EmailTemplateType] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search term for name, subject"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get all master admin templates (read-only for org admins).
    Returns only templates where is_default=True and org_id=null.
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


@router.get("/", response_model=EmailTemplateListResponse, status_code=status.HTTP_200_OK)
def list_org_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    category: Optional[EmailTemplateCategory] = Query(None, description="Filter by category"),
    type: Optional[EmailTemplateType] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search term for name, subject"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get org-specific email templates.
    Returns templates that belong to the current user's organization.
    """
    query = db.query(EmailTemplate).filter(
        EmailTemplate.org_id == current_user.org_id
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
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get single org template. Verifies template belongs to user's org."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.org_id == current_user.org_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found in your organization"
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


@router.post("/{master_template_id}/customize", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def customize_template(
    master_template_id: int,
    customize_data: CustomizeTemplateRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Customize a master template for the organization.
    If org already has customized version, updates it; otherwise creates new.
    """
    # Find master template
    master_template = db.query(EmailTemplate).filter(
        EmailTemplate.id == master_template_id,
        EmailTemplate.is_default == True,
        EmailTemplate.org_id == None
    ).first()
    
    if not master_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master template with id {master_template_id} not found"
        )
    
    # Check if org already has customized version
    existing_customized = db.query(EmailTemplate).filter(
        EmailTemplate.master_template_id == master_template_id,
        EmailTemplate.org_id == current_user.org_id
    ).first()
    
    if existing_customized:
        # Update existing customized template
        if customize_data.subject is not None:
            existing_customized.subject = customize_data.subject
        if customize_data.body is not None:
            existing_customized.body = customize_data.body
        
        db.commit()
        db.refresh(existing_customized)
        
        return EmailTemplateResponse(
            id=existing_customized.id,
            name=existing_customized.name,
            category=existing_customized.category.value,
            type=existing_customized.type.value,
            subject=existing_customized.subject,
            body=existing_customized.body,
            is_default=existing_customized.is_default,
            org_id=existing_customized.org_id,
            master_template_id=existing_customized.master_template_id,
            variables=existing_customized.variables,
            created_at=existing_customized.created_at.isoformat() if existing_customized.created_at else None,
            updated_at=existing_customized.updated_at.isoformat() if existing_customized.updated_at else None,
            created_by=existing_customized.created_by
        )
    else:
        # Create new customized template
        customized_template = EmailTemplate(
            name=master_template.name,
            category=master_template.category,
            type=master_template.type,
            subject=customize_data.subject if customize_data.subject else master_template.subject,
            body=customize_data.body if customize_data.body else master_template.body,
            is_default=False,
            org_id=current_user.org_id,
            master_template_id=master_template_id,
            variables=master_template.variables,
            created_by=current_user.id
        )
        
        db.add(customized_template)
        db.commit()
        db.refresh(customized_template)
        
        return EmailTemplateResponse(
            id=customized_template.id,
            name=customized_template.name,
            category=customized_template.category.value,
            type=customized_template.type.value,
            subject=customized_template.subject,
            body=customized_template.body,
            is_default=customized_template.is_default,
            org_id=customized_template.org_id,
            master_template_id=customized_template.master_template_id,
            variables=customized_template.variables,
            created_at=customized_template.created_at.isoformat() if customized_template.created_at else None,
            updated_at=customized_template.updated_at.isoformat() if customized_template.updated_at else None,
            created_by=customized_template.created_by
        )


@router.post("/", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: CreateTemplateRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a custom template for the organization.
    This is a custom template, not based on a master template.
    """
    # Check for duplicate name in org templates
    existing_template = db.query(EmailTemplate).filter(
        EmailTemplate.name == template_data.name,
        EmailTemplate.org_id == current_user.org_id
    ).first()
    
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists in your organization"
        )
    
    # Create template
    db_template = EmailTemplate(
        name=template_data.name,
        category=template_data.category,
        type=template_data.type,
        subject=template_data.subject,
        body=template_data.body,
        is_default=False,
        org_id=current_user.org_id,
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
    template_update: UpdateTemplateRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update an org-specific template. Verifies template belongs to user's org."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.org_id == current_user.org_id,
        EmailTemplate.is_default == False
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found or cannot be updated"
        )
    
    # Update fields if provided
    if template_update.name is not None:
        # Check for duplicate name (excluding current template)
        existing_template = db.query(EmailTemplate).filter(
            and_(
                EmailTemplate.name == template_update.name,
                EmailTemplate.org_id == current_user.org_id,
                EmailTemplate.id != template_id
            )
        ).first()
        if existing_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template with this name already exists in your organization"
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
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an org-specific template. Verifies template belongs to user's org and is_default=False."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.org_id == current_user.org_id,
        EmailTemplate.is_default == False
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found or cannot be deleted"
        )
    
    # Delete template
    db.delete(template)
    db.commit()
    
    return None

