"""
API endpoints for client email configuration and scheduling.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import and_, or_
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime, time, timedelta
from app.db.session import get_db
from app.db.models.client import Client
from app.db.models.email_template import EmailTemplate
from app.db.models.organization import Organization
from app.db.models.client_email_config import ClientEmailConfig, ScheduledEmail, ScheduledEmailStatus
from app.api.v1.client.dependencies import require_admin_or_employee
from app.core.email_template_utils import replace_template_variables
from app.core.email_service import send_email

router = APIRouter()


# Pydantic Schemas
class EmailTemplateConfig(BaseModel):
    email: EmailStr
    selectedTemplates: List[int]


class ServiceConfig(BaseModel):
    enabled: bool
    templateId: int
    templateName: str
    dateType: str = Field(..., description="single, range, or all")
    scheduledDate: Optional[date] = None
    scheduledDateFrom: Optional[date] = None
    scheduledDateTo: Optional[date] = None
    scheduledTimes: List[str] = Field(..., description="List of times in HH:mm format")
    
    @field_validator('dateType')
    @classmethod
    def validate_date_type(cls, v):
        if v not in ['single', 'range', 'all']:
            raise ValueError("dateType must be 'single', 'range', or 'all'")
        return v
    
    @field_validator('scheduledTimes')
    @classmethod
    def validate_times(cls, v):
        for time_str in v:
            try:
                time.fromisoformat(time_str)
            except ValueError:
                raise ValueError(f"Invalid time format: {time_str}. Use HH:mm format (24-hour).")
        return v


class EmailConfigRequest(BaseModel):
    emails: List[EmailStr]
    emailTemplates: Dict[str, EmailTemplateConfig]
    services: Dict[str, ServiceConfig]


class EmailConfigResponse(BaseModel):
    client_id: int
    emails: List[str]
    emailTemplates: Dict[str, Dict[str, Any]]
    services: Dict[str, Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScheduledEmailResponse(BaseModel):
    id: int
    template_id: Optional[int]
    template_name: Optional[str]
    recipient_emails: List[str]
    scheduled_date: date
    scheduled_time: str
    scheduled_datetime: datetime
    status: str
    is_recurring: bool
    recurrence_end_date: Optional[date] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScheduledEmailsListResponse(BaseModel):
    scheduled_emails: List[ScheduledEmailResponse]
    total: int


# Schemas for individual email management
class EmailCreate(BaseModel):
    email: EmailStr
    selectedTemplates: List[int] = Field(default_factory=list, description="List of template IDs to associate with this email")


class EmailUpdate(BaseModel):
    selectedTemplates: List[int] = Field(..., description="List of template IDs to associate with this email")


class EmailResponse(BaseModel):
    email: str
    selectedTemplates: List[int]


class EmailListResponse(BaseModel):
    emails: List[EmailResponse]
    total: int


# Helper Functions
def get_email_config_from_db(client_id: int, org_id: int, db: Session) -> ClientEmailConfig:
    """Helper function to get and validate email config from database."""
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get config
    db_config = db.query(ClientEmailConfig).filter(
        ClientEmailConfig.client_id == client_id
    ).first()
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found"
        )
    
    return db_config


def validate_email_config(
    config: EmailConfigRequest,
    org_id: int,
    db: Session
) -> None:
    """Validate email configuration data."""
    errors = {}
    
    # Validate email format (already validated by Pydantic EmailStr)
    # Validate template IDs exist and belong to organization (or are master templates)
    all_template_ids = set()
    for email_config in config.emailTemplates.values():
        all_template_ids.update(email_config.selectedTemplates)
    
    for service_config in config.services.values():
        if service_config.enabled:
            all_template_ids.add(service_config.templateId)
    
    if all_template_ids:
        templates = db.query(EmailTemplate).filter(
            EmailTemplate.id.in_(all_template_ids)
        ).all()
        found_template_ids = {t.id for t in templates}
        
        # Check if all templates belong to org or are master templates (is_default=True and org_id is None)
        invalid_templates = []
        for template_id in all_template_ids:
            if template_id not in found_template_ids:
                invalid_templates.append(template_id)
            else:
                template = next(t for t in templates if t.id == template_id)
                # Allow if template belongs to org or is a master template
                if template.org_id and template.org_id != org_id:
                    invalid_templates.append(template_id)
        
        if invalid_templates:
            errors["templates"] = [f"Template IDs not found or not accessible: {invalid_templates}"]
    
    # Validate service configurations
    for service_id, service_config in config.services.items():
        if not service_config.enabled:
            continue
        
        service_errors = []
        
        if service_config.dateType == "single":
            if not service_config.scheduledDate:
                service_errors.append("scheduledDate is required for dateType 'single'")
            else:
                # Allow today and future dates only (reject past dates)
                # Use <= comparison to explicitly allow today: reject only if scheduledDate < today
                today = date.today()
                if service_config.scheduledDate < today:
                    service_errors.append("scheduledDate cannot be in the past (must be today or later)")
            if service_config.scheduledDateFrom or service_config.scheduledDateTo:
                service_errors.append("scheduledDateFrom and scheduledDateTo must be null for dateType 'single'")
        
        elif service_config.dateType == "range":
            if not service_config.scheduledDateFrom or not service_config.scheduledDateTo:
                service_errors.append("scheduledDateFrom and scheduledDateTo are required for dateType 'range'")
            elif service_config.scheduledDateFrom >= service_config.scheduledDateTo:
                service_errors.append("scheduledDateTo must be after scheduledDateFrom")
            else:
                # Allow today and future dates only (reject past dates)
                today = date.today()
                if service_config.scheduledDateFrom < today:
                    service_errors.append("scheduledDateFrom cannot be in the past (must be today or later)")
            if service_config.scheduledDate:
                service_errors.append("scheduledDate must be null for dateType 'range'")
        
        elif service_config.dateType == "all":
            if service_config.scheduledDate or service_config.scheduledDateFrom or service_config.scheduledDateTo:
                service_errors.append("All date fields must be null for dateType 'all'")
        
        if not service_config.scheduledTimes:
            service_errors.append("At least one scheduled time must be specified")
        
        if service_errors:
            errors[f"services.{service_id}"] = service_errors
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "Validation error", "errors": errors}
        )


def create_scheduled_emails(
    config: EmailConfigRequest,
    client_id: int,
    template_id: int,
    service_config: ServiceConfig,
    db: Session
) -> List[ScheduledEmail]:
    """Create scheduled email records based on service configuration."""
    scheduled_emails = []
    
    # Get recipient emails for this template
    recipient_emails = [
        email for email, email_config in config.emailTemplates.items()
        if template_id in email_config.selectedTemplates
    ]
    
    if not recipient_emails:
        return scheduled_emails
    
    if service_config.dateType == "single":
        # Create jobs for the single date at each time
        for time_str in service_config.scheduledTimes:
            t = time.fromisoformat(time_str)
            scheduled_datetime = datetime.combine(service_config.scheduledDate, t)
            
            scheduled_email = ScheduledEmail(
                client_id=client_id,
                template_id=template_id,
                recipient_emails=recipient_emails,
                scheduled_date=service_config.scheduledDate,
                scheduled_time=t,
                scheduled_datetime=scheduled_datetime,
                status=ScheduledEmailStatus.PENDING.value,
                is_recurring=False
            )
            scheduled_emails.append(scheduled_email)
    
    elif service_config.dateType == "range":
        # Create jobs for each day in the range at each time
        current_date = service_config.scheduledDateFrom
        while current_date <= service_config.scheduledDateTo:
            for time_str in service_config.scheduledTimes:
                t = time.fromisoformat(time_str)
                scheduled_datetime = datetime.combine(current_date, t)
                
                scheduled_email = ScheduledEmail(
                    client_id=client_id,
                    template_id=template_id,
                    recipient_emails=recipient_emails,
                    scheduled_date=current_date,
                    scheduled_time=t,
                    scheduled_datetime=scheduled_datetime,
                    status=ScheduledEmailStatus.PENDING.value,
                    is_recurring=False,
                    recurrence_end_date=service_config.scheduledDateTo
                )
                scheduled_emails.append(scheduled_email)
            
            # Move to next day
            current_date += timedelta(days=1)
    
    elif service_config.dateType == "all":
        # For "all", create one record per time for tomorrow (recurring)
        tomorrow = date.today() + timedelta(days=1)
        for time_str in service_config.scheduledTimes:
            t = time.fromisoformat(time_str)
            scheduled_datetime = datetime.combine(tomorrow, t)
            
            scheduled_email = ScheduledEmail(
                client_id=client_id,
                template_id=template_id,
                recipient_emails=recipient_emails,
                scheduled_date=tomorrow,
                scheduled_time=t,
                scheduled_datetime=scheduled_datetime,
                status=ScheduledEmailStatus.PENDING.value,
                is_recurring=True,
                recurrence_end_date=None  # No end date for "all"
            )
            scheduled_emails.append(scheduled_email)
    
    return scheduled_emails


# API Endpoints
@router.post("/{client_id}/email-config", response_model=EmailConfigResponse, status_code=status.HTTP_201_CREATED)
def create_email_config(
    client_id: int,
    config: EmailConfigRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Create email configuration for a client."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check if config already exists
    existing_config = db.query(ClientEmailConfig).filter(
        ClientEmailConfig.client_id == client_id
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email configuration already exists. Use PUT to update."
        )
    
    # Validate configuration
    validate_email_config(config, org_id, db)
    
    # Convert config to dict for storage (mode='json' converts dates to strings)
    config_dict = config.model_dump(mode='json')
    
    # Create email config record
    db_config = ClientEmailConfig(
        client_id=client_id,
        config_data=config_dict
    )
    db.add(db_config)
    db.flush()
    
    # Create scheduled emails
    for service_id, service_config in config.services.items():
        if service_config.enabled:
            scheduled_emails = create_scheduled_emails(
                config, client_id, service_config.templateId, service_config, db
            )
            db.add_all(scheduled_emails)
    
    db.commit()
    db.refresh(db_config)
    
    # Build response
    return EmailConfigResponse(
        client_id=client_id,
        emails=config_dict["emails"],
        emailTemplates=config_dict["emailTemplates"],
        services=config_dict["services"],
        created_at=db_config.created_at,
        updated_at=db_config.updated_at
    )


@router.put("/{client_id}/email-config", response_model=EmailConfigResponse)
def update_email_config(
    client_id: int,
    config: EmailConfigRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Update email configuration for a client."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get existing config (upsert behavior - create if not exists)
    db_config = db.query(ClientEmailConfig).filter(
        ClientEmailConfig.client_id == client_id
    ).first()
    
    # Validate configuration
    validate_email_config(config, org_id, db)
    
    # Cancel all pending scheduled emails for this client (if config exists)
    if db_config:
        db.query(ScheduledEmail).filter(
            ScheduledEmail.client_id == client_id,
            ScheduledEmail.status == ScheduledEmailStatus.PENDING.value
        ).update({"status": ScheduledEmailStatus.CANCELLED.value})
    
    # Convert config to dict for storage (mode='json' converts dates to strings)
    config_dict = config.model_dump(mode='json')
    
    if db_config:
        # Update existing config - use flag_modified to ensure SQLAlchemy detects JSON column change
        db_config.config_data = config_dict
        flag_modified(db_config, "config_data")
    else:
        # Create new config (upsert behavior)
        db_config = ClientEmailConfig(
            client_id=client_id,
            config_data=config_dict
        )
        db.add(db_config)
    
    db.flush()
    
    # Create new scheduled emails
    for service_id, service_config in config.services.items():
        if service_config.enabled:
            scheduled_emails = create_scheduled_emails(
                config, client_id, service_config.templateId, service_config, db
            )
            db.add_all(scheduled_emails)
    
    db.commit()
    db.refresh(db_config)
    
    # Build response
    return EmailConfigResponse(
        client_id=client_id,
        emails=config_dict["emails"],
        emailTemplates=config_dict["emailTemplates"],
        services=config_dict["services"],
        created_at=db_config.created_at,
        updated_at=db_config.updated_at
    )


@router.get("/{client_id}/email-config", response_model=EmailConfigResponse)
def get_email_config(
    client_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Get email configuration for a client."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get config
    db_config = db.query(ClientEmailConfig).filter(
        ClientEmailConfig.client_id == client_id
    ).first()
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found"
        )
    
    config_dict = db_config.config_data
    
    return EmailConfigResponse(
        client_id=client_id,
        emails=config_dict.get("emails", []),
        emailTemplates=config_dict.get("emailTemplates", {}),
        services=config_dict.get("services", {}),
        created_at=db_config.created_at,
        updated_at=db_config.updated_at
    )


@router.delete("/{client_id}/email-config", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_config(
    client_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Delete email configuration for a client and cancel all scheduled emails."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Cancel all pending scheduled emails
    db.query(ScheduledEmail).filter(
        ScheduledEmail.client_id == client_id,
        ScheduledEmail.status == ScheduledEmailStatus.PENDING.value
    ).update({"status": ScheduledEmailStatus.CANCELLED.value})
    
    # Delete config
    db_config = db.query(ClientEmailConfig).filter(
        ClientEmailConfig.client_id == client_id
    ).first()
    
    if db_config:
        db.delete(db_config)
    
    db.commit()
    return None


@router.get("/{client_id}/scheduled-emails", response_model=ScheduledEmailsListResponse)
def get_scheduled_emails(
    client_id: int,
    request: Request,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, sent, failed, cancelled"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Get scheduled emails for a client."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Build query
    query = db.query(ScheduledEmail).filter(ScheduledEmail.client_id == client_id)
    
    if status_filter:
        query = query.filter(ScheduledEmail.status == status_filter)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    scheduled_emails = query.order_by(ScheduledEmail.scheduled_datetime.desc()).offset(skip).limit(limit).all()
    
    # Build response
    email_responses = []
    for email in scheduled_emails:
        template_name = None
        if email.template:
            template_name = email.template.name
        
        email_responses.append(ScheduledEmailResponse(
            id=email.id,
            template_id=email.template_id,
            template_name=template_name,
            recipient_emails=email.recipient_emails,
            scheduled_date=email.scheduled_date,
            scheduled_time=email.scheduled_time.strftime("%H:%M"),
            scheduled_datetime=email.scheduled_datetime,
            status=email.status,
            is_recurring=email.is_recurring,
            recurrence_end_date=email.recurrence_end_date,
            error_message=email.error_message,
            sent_at=email.sent_at
        ))
    
    return ScheduledEmailsListResponse(
        scheduled_emails=email_responses,
        total=total
    )


@router.delete("/{client_id}/scheduled-emails/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_scheduled_email(
    client_id: int,
    email_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Cancel a specific scheduled email."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get scheduled email
    scheduled_email = db.query(ScheduledEmail).filter(
        ScheduledEmail.id == email_id,
        ScheduledEmail.client_id == client_id
    ).first()
    
    if not scheduled_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled email not found"
        )
    
    # Cancel if still pending
    if scheduled_email.status == ScheduledEmailStatus.PENDING.value:
        scheduled_email.status = ScheduledEmailStatus.CANCELLED.value
        db.commit()
    
    return None


@router.post("/{client_id}/scheduled-emails/{email_id}/retry", status_code=status.HTTP_200_OK)
def retry_scheduled_email(
    client_id: int,
    email_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Retry a failed scheduled email."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify client exists and belongs to organization
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == org_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get scheduled email
    scheduled_email = db.query(ScheduledEmail).filter(
        ScheduledEmail.id == email_id,
        ScheduledEmail.client_id == client_id
    ).first()
    
    if not scheduled_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled email not found"
        )
    
    if scheduled_email.status != ScheduledEmailStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed emails"
        )
    
    # Reset to pending
    scheduled_email.status = ScheduledEmailStatus.PENDING.value
    scheduled_email.error_message = None
    db.commit()
    
    return {"message": "Email scheduled for retry"}


# Individual Email Management Endpoints
@router.get("/{client_id}/email-config/emails", response_model=EmailListResponse)
def list_emails(
    client_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Get all emails in the email configuration."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    db_config = get_email_config_from_db(client_id, org_id, db)
    config_dict = db_config.config_data
    
    emails_list = []
    email_templates = config_dict.get("emailTemplates", {})
    
    # Build response from emailTemplates dict
    for email_addr, email_config in email_templates.items():
        emails_list.append(EmailResponse(
            email=email_addr,
            selectedTemplates=email_config.get("selectedTemplates", [])
        ))
    
    return EmailListResponse(
        emails=emails_list,
        total=len(emails_list)
    )


@router.get("/{client_id}/email-config/emails/{email}", response_model=EmailResponse)
def get_email(
    client_id: int,
    email: EmailStr,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Get configuration for a specific email."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    db_config = get_email_config_from_db(client_id, org_id, db)
    config_dict = db_config.config_data
    
    email_str = str(email)
    email_templates = config_dict.get("emailTemplates", {})
    
    if email_str not in email_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email '{email_str}' not found in configuration"
        )
    
    email_config = email_templates[email_str]
    return EmailResponse(
        email=email_str,
        selectedTemplates=email_config.get("selectedTemplates", [])
    )


@router.post("/{client_id}/email-config/emails", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)
def create_email(
    client_id: int,
    email_data: EmailCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Add a new email to the email configuration."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    db_config = get_email_config_from_db(client_id, org_id, db)
    config_dict = db_config.config_data.copy()
    
    email_str = str(email_data.email)
    email_templates = config_dict.get("emailTemplates", {})
    emails_list = config_dict.get("emails", [])
    
    # Check if email already exists
    if email_str in email_templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{email_str}' already exists in configuration"
        )
    
    # Validate template IDs if provided
    if email_data.selectedTemplates:
        templates = db.query(EmailTemplate).filter(
            EmailTemplate.id.in_(email_data.selectedTemplates)
        ).all()
        found_template_ids = {t.id for t in templates}
        invalid_templates = [tid for tid in email_data.selectedTemplates if tid not in found_template_ids]
        
        if invalid_templates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template IDs: {invalid_templates}"
            )
        
        # Check if templates belong to org or are master templates
        for template in templates:
            if template.org_id and template.org_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Template ID {template.id} does not belong to your organization"
                )
    
    # Add email to emails list if not already present
    if email_str not in emails_list:
        emails_list.append(email_str)
    
    # Add email configuration
    email_templates[email_str] = {
        "email": email_str,
        "selectedTemplates": email_data.selectedTemplates
    }
    
    config_dict["emails"] = emails_list
    config_dict["emailTemplates"] = email_templates
    
    # Update database - use flag_modified to ensure SQLAlchemy detects JSON column change
    db_config.config_data = config_dict
    flag_modified(db_config, "config_data")
    db.commit()
    db.refresh(db_config)
    
    return EmailResponse(
        email=email_str,
        selectedTemplates=email_data.selectedTemplates
    )


@router.put("/{client_id}/email-config/emails/{email}", response_model=EmailResponse)
def update_email(
    client_id: int,
    email: EmailStr,
    email_data: EmailUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Update (replace) configuration for a specific email."""
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    db_config = get_email_config_from_db(client_id, org_id, db)
    config_dict = db_config.config_data.copy()
    
    email_str = str(email)
    email_templates = config_dict.get("emailTemplates", {})
    
    if email_str not in email_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email '{email_str}' not found in configuration"
        )
    
    # Validate template IDs if provided
    if email_data.selectedTemplates:
        templates = db.query(EmailTemplate).filter(
            EmailTemplate.id.in_(email_data.selectedTemplates)
        ).all()
        found_template_ids = {t.id for t in templates}
        invalid_templates = [tid for tid in email_data.selectedTemplates if tid not in found_template_ids]
        
        if invalid_templates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template IDs: {invalid_templates}"
            )
        
        # Check if templates belong to org or are master templates
        for template in templates:
            if template.org_id and template.org_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Template ID {template.id} does not belong to your organization"
                )
    
    # Update email configuration (replace)
    email_templates[email_str] = {
        "email": email_str,
        "selectedTemplates": email_data.selectedTemplates
    }
    
    config_dict["emailTemplates"] = email_templates
    
    # Update database - use flag_modified to ensure SQLAlchemy detects JSON column change
    db_config.config_data = config_dict
    flag_modified(db_config, "config_data")
    db.commit()
    db.refresh(db_config)
    
    return EmailResponse(
        email=email_str,
        selectedTemplates=email_data.selectedTemplates
    )


@router.patch("/{client_id}/email-config/emails/{email}", response_model=EmailResponse)
def patch_email(
    client_id: int,
    email: EmailStr,
    email_data: EmailUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """Partially update configuration for a specific email (same as PUT for now, but kept for RESTful consistency)."""
    # For email config, PATCH is the same as PUT since we're only updating selectedTemplates
    return update_email(client_id, email, email_data, request, db, _)


@router.delete("/{client_id}/email-config/emails/{email}", status_code=status.HTTP_200_OK)
def delete_email(
    client_id: int,
    email: EmailStr,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """
    Remove an email from the email configuration.
    
    Removes the email from:
    - emails array
    - emailTemplates object
    - Updates scheduled emails (removes from recipients or cancels if no recipients left)
    """
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    db_config = get_email_config_from_db(client_id, org_id, db)
    config_dict = db_config.config_data.copy()
    
    email_str = str(email)
    email_templates = config_dict.get("emailTemplates", {})
    emails_list = config_dict.get("emails", [])
    
    if email_str not in email_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email '{email_str}' not found in configuration"
        )
    
    # Remove email from emailTemplates
    del email_templates[email_str]
    
    # Remove email from emails list
    if email_str in emails_list:
        emails_list.remove(email_str)
    
    config_dict["emailTemplates"] = email_templates
    config_dict["emails"] = emails_list
    
    # Cancel all pending scheduled emails that include this email
    pending_emails = db.query(ScheduledEmail).filter(
        ScheduledEmail.client_id == client_id,
        ScheduledEmail.status == ScheduledEmailStatus.PENDING.value
    ).all()
    
    for scheduled_email in pending_emails:
        if email_str in scheduled_email.recipient_emails:
            # Remove email from recipient list or cancel if it's the only recipient
            updated_recipients = [e for e in scheduled_email.recipient_emails if e != email_str]
            if updated_recipients:
                scheduled_email.recipient_emails = updated_recipients
                flag_modified(scheduled_email, "recipient_emails")  # Flag JSON column as modified
            else:
                # No recipients left, cancel the email
                scheduled_email.status = ScheduledEmailStatus.CANCELLED.value
    
    # Update database - use flag_modified to ensure SQLAlchemy detects JSON column change
    db_config.config_data = config_dict
    flag_modified(db_config, "config_data")
    db.commit()
    
    return {"message": f"Email '{email_str}' successfully removed from configuration"}

