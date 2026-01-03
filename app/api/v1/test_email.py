"""
Test endpoint for sending test emails.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from app.core.email_service import send_email, is_email_configured
from app.api.v1.client.dependencies import require_admin_or_employee

router = APIRouter()


class TestEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str = "Test Email from CAA Backend"
    message: str = "This is a test email to verify email configuration."


@router.post("/test-email")
async def send_test_email(
    request: TestEmailRequest,
    _: str = Depends(require_admin_or_employee)
):
    """
    Send a test email to verify email configuration.
    Requires admin or employee role.
    """
    if not is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured. Please set SMTP settings in environment variables."
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
            "to_email": request.to_email
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email to {request.to_email}. Check server logs for details."
        )

