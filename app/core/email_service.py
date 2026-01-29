"""
Email service for sending emails to users.
Supports sending login credentials to admins, employees, and clients.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_missing() -> List[str]:
    missing = []
    if not (settings.SMTP_HOST or "").strip():
        missing.append("SMTP_HOST")
    if not (settings.SMTP_USER or "").strip():
        missing.append("SMTP_USER")
    if not (settings.SMTP_PASSWORD or "").strip():
        missing.append("SMTP_PASSWORD")
    if not (settings.SMTP_FROM_EMAIL or "").strip():
        missing.append("SMTP_FROM_EMAIL")
    return missing


def is_email_configured() -> bool:
    """Check if email is properly configured."""
    return len(_get_missing()) == 0


def get_missing_email_config() -> List[str]:
    """Return list of missing SMTP env var names. Use for logging/diagnostics."""
    return _get_missing()


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
    from_name: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        plain_body: Plain text email body (optional, auto-generated from HTML if not provided)
        from_name: Sender name (optional, defaults to SMTP_FROM_NAME from settings)
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    if not is_email_configured():
        missing = get_missing_email_config()
        logger.warning(
            "Email not configured. Skipping send. Missing: %s. Set these in production env.",
            ", ".join(missing),
        )
        return False

    try:
        logger.info(
            "Attempting to send email to %s via %s:%s (subject: %s...)",
            to_email,
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            (subject or "")[:50],
        )
        
        # Use provided from_name or fall back to settings
        sender_name = from_name or settings.SMTP_FROM_NAME
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{sender_name} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        
        # Create plain text version if not provided
        if not plain_body:
            # Simple HTML to text conversion (remove tags)
            import re
            plain_body = re.sub(r'<[^>]+>', '', html_body)
            plain_body = plain_body.replace('&nbsp;', ' ').strip()
        
        # Add both plain and HTML versions
        part1 = MIMEText(plain_body, "plain")
        part2 = MIMEText(html_body, "html")
        
        message.attach(part1)
        message.attach(part2)
        
        # Send email using aiosmtplib with explicit STARTTLS handling
        # Hostinger/Gmail port 587 requires STARTTLS (plain connection, then upgrade to TLS)
        # Hostinger/Gmail port 465 requires SSL from the start
        # Use configurable timeout (default 30 seconds, increase if experiencing timeouts)
        smtp_timeout = settings.SMTP_TIMEOUT
        import ssl
        
        # Try to connect based on port
        if settings.SMTP_PORT == 465:
            # Port 465: SSL/TLS from the start (SMTPS)
            # Create SSL context with relaxed settings for some SMTP servers
            context = ssl.create_default_context()
            # Some SMTP servers need these settings
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            try:
                smtp = aiosmtplib.SMTP(
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    use_tls=True,
                    tls_context=context,
                    timeout=smtp_timeout,
                )
                await smtp.connect()
                logger.info("SMTP connected to %s:%s (SSL)", settings.SMTP_HOST, settings.SMTP_PORT)
            except Exception as e:
                error_msg = str(e).lower()
                if "timeout" in error_msg or "timed out" in error_msg:
                    logger.warning(f"Port 465 connection timed out. Trying port 587 as fallback...")
                    # Fallback to port 587
                    smtp = aiosmtplib.SMTP(
                        hostname=settings.SMTP_HOST,
                        port=587,
                        timeout=smtp_timeout,
                    )
                    await smtp.connect()
                    if settings.SMTP_USE_TLS:
                        await smtp.starttls()
                    logger.info("SMTP connected to %s:587 STARTTLS (fallback from 465)", settings.SMTP_HOST)
                else:
                    raise
        else:
            # Port 587: Plain connection first, then STARTTLS
            smtp = aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                timeout=smtp_timeout,
            )
            await smtp.connect()
            
            # For port 587, use STARTTLS to upgrade plain connection to TLS
            if settings.SMTP_USE_TLS:
                # starttls() will raise an error if already using TLS - catch and continue
                try:
                    await smtp.starttls()
                except Exception as tls_error:
                    em = str(tls_error).lower()
                    if "already" in em and "tls" in em:
                        logger.info("SMTP already using TLS, continuing")
                    else:
                        raise
        
        await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        await smtp.send_message(message)
        await smtp.quit()
        
        logger.info("Email sent successfully to %s", to_email)
        return True

    except Exception as e:
        err = str(e)
        err_lower = err.lower()
        logger.error("Failed to send email to %s: %s", to_email, err, exc_info=True)

        if "timeout" in err_lower or "timed out" in err_lower:
            logger.error(
                "SMTP timeout. Try: SMTP_PORT=465 or increase SMTP_TIMEOUT; ensure outbound %s allowed.",
                settings.SMTP_PORT,
            )
        elif "connection" in err_lower or "refused" in err_lower:
            logger.error(
                "SMTP connection refused. Check SMTP_HOST/SMTP_PORT and firewall for outbound %s.",
                settings.SMTP_PORT,
            )
        elif "authentication" in err_lower or "login" in err_lower:
            logger.error(
                "SMTP auth failed. Check SMTP_USER and SMTP_PASSWORD (use app password for Gmail)."
            )
        return False


async def send_login_credentials_email(
    recipient_email: str,
    recipient_name: str,
    login_email: str,
    password: str,
    role: str,
    organization_name: Optional[str] = None,
    from_name: Optional[str] = None
) -> bool:
    """
    Send login credentials email to a user.
    
    Args:
        recipient_email: Email address to send to
        recipient_name: Name of the recipient
        login_email: Email used for login
        password: Plain text password
        role: User role (admin, employee, client)
        organization_name: Optional organization name
        from_name: Sender name (optional, defaults to SMTP_FROM_NAME from settings)
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    # Determine role-specific messaging
    role_messages = {
        "admin": {
            "title": "Welcome! Your Admin Account Has Been Created",
            "description": "Your admin account has been created. You can now manage your organization and users."
        },
        "employee": {
            "title": "Welcome! Your Employee Account Has Been Created",
            "description": "Your employee account has been created. You can now access the system."
        },
        "client": {
            "title": "Welcome! Your Client Portal Access Has Been Created",
            "description": "Your client portal account has been created. You can now access your account information."
        }
    }
    
    role_info = role_messages.get(role.lower(), {
        "title": "Welcome! Your Account Has Been Created",
        "description": "Your account has been created. You can now access the system."
    })
    
    # Build HTML email body
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
            .credentials {{
                background-color: white;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                padding: 20px;
                margin: 20px 0;
            }}
            .credential-item {{
                margin: 10px 0;
                padding: 10px;
                background-color: #f5f5f5;
                border-left: 4px solid #4CAF50;
            }}
            .label {{
                font-weight: bold;
                color: #666;
                display: inline-block;
                width: 120px;
            }}
            .value {{
                color: #333;
                font-family: monospace;
            }}
            .warning {{
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
                color: #856404;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{role_info['title']}</h1>
        </div>
        <div class="content">
            <p>Dear {recipient_name},</p>
            
            <p>{role_info['description']}</p>
    """
    
    if organization_name:
        html_body += f'<p><strong>Organization:</strong> {organization_name}</p>'
    
    html_body += f"""
            <div class="credentials">
                <h3 style="margin-top: 0;">Your Login Credentials:</h3>
                <div class="credential-item">
                    <span class="label">Email:</span>
                    <span class="value">{login_email}</span>
                </div>
                <div class="credential-item">
                    <span class="label">Password:</span>
                    <span class="value">{password}</span>
                </div>
            </div>
            
            <div class="warning">
                <strong>⚠️ Security Notice:</strong> Please change your password after your first login for security purposes.
            </div>
            
            <p>You can now log in to the system using the credentials above.</p>
            
            <p>If you have any questions or need assistance, please contact your administrator.</p>
            
            <p>Best regards,<br>
            {from_name or settings.SMTP_FROM_NAME}</p>
        </div>
        <div class="footer">
            <p>This is an automated email. Please do not reply to this message.</p>
        </div>
    </body>
    </html>
    """
    
    subject = role_info['title']
    
    return await send_email(
        to_email=recipient_email,
        subject=subject,
        html_body=html_body,
        from_name=from_name
    )




