"""
Test endpoint for sending test emails.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.client import Client
from app.db.models.email_template import EmailTemplate
from app.db.models.client_email_config import ScheduledEmail, ScheduledEmailStatus
from app.core.email_service import send_email, is_email_configured, get_missing_email_config
from app.core.config import settings
from app.api.v1.client.dependencies import require_admin_or_employee

router = APIRouter()


@router.get("/email-status")
async def email_status():
    """
    Lightweight email config status for production debugging. No auth.
    Returns configured vs missing SMTP vars only.
    """
    missing = get_missing_email_config()
    configured = is_email_configured()
    out = {"configured": configured, "missing": missing}
    if not configured and missing:
        out["hint"] = "Set these in your deployment platform's environment variables (e.g. Coolify, Render), not only in .env."
    return out


class TestEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str = "Test Email from CAA Backend"
    message: str = "This is a test email to verify email configuration."


@router.get("/test-email/config")
async def get_email_config(
    _: str = Depends(require_admin_or_employee)
):
    """
    Check email configuration status.
    Returns configuration details (without sensitive data).
    Requires admin or employee role.
    """
    config_status = {
        "configured": is_email_configured(),
        "smtp_host": settings.SMTP_HOST if settings.SMTP_HOST else None,
        "smtp_port": settings.SMTP_PORT,
        "smtp_user": settings.SMTP_USER if settings.SMTP_USER else None,
        "smtp_from_email": settings.SMTP_FROM_EMAIL if settings.SMTP_FROM_EMAIL else None,
        "smtp_from_name": settings.SMTP_FROM_NAME,
        "smtp_use_tls": settings.SMTP_USE_TLS,
        "smtp_timeout": settings.SMTP_TIMEOUT,
        "password_set": bool(settings.SMTP_PASSWORD),
    }
    
    if not config_status["configured"]:
        missing = get_missing_email_config()
        config_status["missing_settings"] = missing
        config_status["message"] = f"Email not configured. Missing: {', '.join(missing)}"
    else:
        config_status["message"] = "Email is configured and ready to use"
    
    return config_status


@router.post("/test-email")
async def send_test_email(
    request: TestEmailRequest,
    _: str = Depends(require_admin_or_employee)
):
    """
    Send a test email to verify email configuration.
    Requires admin or employee role.
    
    Troubleshooting:
    - If you get a timeout error, try using port 465 instead of 587
    - Increase SMTP_TIMEOUT in .env if connections are slow
    - Ensure SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM_EMAIL are set
    """
    if not is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured. Please set SMTP settings in environment variables. Use GET /api/v1/test-email/config to check configuration."
        )
    
    # Create HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 5px 5px;
            }}
            .test-message {{
                background-color: white;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                padding: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Test Email</h1>
        </div>
        <div class="content">
            <p>This is a test email from the CAA Backend system.</p>
            
            <div class="test-message">
                <p><strong>Test Message:</strong></p>
                <p>{request.message}</p>
            </div>
            
            <p>If you received this email, your email configuration is working correctly!</p>
            
            <p>Best regards,<br>
            CAA Backend System</p>
        </div>
    </body>
    </html>
    """
    
    success = await send_email(
        to_email=request.to_email,
        subject=request.subject,
        html_body=html_body
    )
    
    if success:
        return {
            "success": True,
            "message": f"Test email sent successfully to {request.to_email}",
            "to_email": request.to_email,
            "smtp_host": settings.SMTP_HOST,
            "smtp_port": settings.SMTP_PORT
        }
    else:
        error_detail = (
            f"Failed to send test email to {request.to_email}. "
            f"Check server logs for details. "
            f"Current SMTP settings: Host={settings.SMTP_HOST}, Port={settings.SMTP_PORT}. "
            f"Try using port 465 instead of 587 if you're experiencing timeout errors."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


class CreateScheduledEmailRequest(BaseModel):
    """Request body for creating a single scheduled email (for testing the scheduler)."""
    to_email: EmailStr = Field(..., description="Recipient email address")
    client_id: Optional[int] = Field(None, description="Client ID (uses first client in org if omitted)")
    template_id: Optional[int] = Field(None, description="Email template ID (uses first template in org if omitted)")
    send_in_seconds: int = Field(
        0,
        ge=0,
        le=86400,
        description="Seconds from now when the email should be due (0 = due now; scheduler picks it up within ~1 min)"
    )


@router.post("/test-scheduled-email")
def create_test_scheduled_email(
    request_body: CreateScheduledEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_employee)
):
    """
    Create one scheduled email for testing the email scheduler in Postman.

    - Uses your org (from token). If client_id/template_id are omitted, uses the first
      client and first template in your org.
    - Set send_in_seconds=0 so the email is due immediately; the scheduler runs every
      minute and will send it within about 1 minute.
    - Check logs for "EMAIL SCHEDULER" and "Processing scheduled email" to confirm send.
    """
    org_id = request.state.org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Valid access token with org_id is required."
        )

    # Resolve or validate client
    if request_body.client_id:
        client = db.query(Client).filter(
            Client.id == request_body.client_id,
            Client.org_id == org_id
        ).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {request_body.client_id} not found or not in your organization."
            )
    else:
        client = db.query(Client).filter(Client.org_id == org_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No client found in your organization. Create a client first or pass client_id."
            )

    # Resolve or validate template (org template or default/master)
    if request_body.template_id:
        template = db.query(EmailTemplate).filter(
            EmailTemplate.id == request_body.template_id
        ).filter(
            (EmailTemplate.org_id == org_id) | (EmailTemplate.org_id.is_(None))
        ).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {request_body.template_id} not found or not in your organization."
            )
    else:
        template = db.query(EmailTemplate).filter(
            (EmailTemplate.org_id == org_id) | (EmailTemplate.org_id.is_(None))
        ).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No email template found. Create a template or pass template_id."
            )

    # When should it be due (scheduler picks rows where scheduled_datetime <= now)
    if request_body.send_in_seconds == 0:
        # Due now so the next scheduler run (within ~1 min) picks it up
        scheduled_datetime = datetime.now() - timedelta(seconds=30)
    else:
        scheduled_datetime = datetime.now() + timedelta(seconds=request_body.send_in_seconds)
    scheduled_date = scheduled_datetime.date()
    scheduled_time = scheduled_datetime.time().replace(microsecond=0)

    scheduled_email = ScheduledEmail(
        client_id=client.id,
        template_id=template.id,
        recipient_emails=[request_body.to_email],
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        scheduled_datetime=scheduled_datetime,
        status=ScheduledEmailStatus.PENDING.value,
        is_recurring=False,
    )
    db.add(scheduled_email)
    db.commit()
    db.refresh(scheduled_email)

    return {
        "success": True,
        "message": "Scheduled email created. Scheduler runs every minute; check logs for send confirmation.",
        "scheduled_email_id": scheduled_email.id,
        "to_email": request_body.to_email,
        "client_id": client.id,
        "client_name": client.client_name,
        "template_id": template.id,
        "template_name": template.name,
        "scheduled_datetime": scheduled_datetime.isoformat(),
        "status": scheduled_email.status,
    }

