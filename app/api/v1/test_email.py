"""
Test endpoint for sending test emails.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
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
    return {"configured": is_email_configured(), "missing": missing}


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

