"""
Utility functions for email template variable replacement.
"""
import re
import html
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple
from app.db.models.client import Client
from app.db.models.organization import Organization
from app.db.models.email_template import EmailTemplate


def replace_template_variables(
    template: EmailTemplate,
    client: Client,
    organization: Organization,
    scheduled_date: Optional[date] = None,
    deadline_date: Optional[date] = None,
    login_email: Optional[str] = None,
    login_password: Optional[str] = None,
    login_url: Optional[str] = None,
    service_description: Optional[str] = None,
    amount: Optional[str] = None,
    document_name: Optional[str] = None
) -> Tuple[str, str]:
    """
    Replace template variables in email template subject and body.
    
    Variables supported:
    Client variables:
    - {{client_name}} → client.client_name
    - {{company_name}} → client.company_name
    - {{client_email}} → client.email
    - {{client_phone}} → client.phone_number
    
    Organization variables:
    - {{org_name}} → organization.name
    - {{org_email}} → organization admin email (from first admin user)
    - {{org_phone}} → organization admin phone (from first admin user)
    - {{org_city}} → organization.city
    - {{org_state}} → organization.state
    - {{org_country}} → organization.country
    - {{org_pincode}} → organization.pincode
    
    Service variables:
    - {{service_name}} → template.name
    - {{service_description}} → service description (if provided)
    
    Date variables:
    - {{current_date}} → current date (YYYY-MM-DD format)
    - {{date}} → current date (YYYY-MM-DD format, alias for current_date)
    - {{today}} → current date (YYYY-MM-DD format, alias for current_date)
    - {{current_datetime}} → current datetime
    - {{scheduled_date}} → scheduled_date (YYYY-MM-DD format)
    - {{deadline_date}} → deadline_date (YYYY-MM-DD format)
    - {{follow_up_date}} → client.follow_date (YYYY-MM-DD format)
    
    Login variables:
    - {{login_email}} → login email
    - {{login_password}} → login password (if provided)
    - {{login_url}} → login URL
    
    Other variables:
    - {{amount}} → amount (if provided)
    - {{document_name}} → document name (if provided)
    - {{additional_notes}} → client.additional_notes
    
    Args:
        template: EmailTemplate instance
        client: Client instance
        organization: Organization instance
        scheduled_date: Optional scheduled date for the email
        deadline_date: Optional deadline date
        login_email: Optional login email
        login_password: Optional login password
        login_url: Optional login URL
        service_description: Optional service description
        amount: Optional amount/payment amount
        document_name: Optional document name
        
    Returns:
        Tuple of (subject, body) with variables replaced
    """
    # Get login email from client's user account if available
    client_login_email = ""
    if client.user_id and client.user:
        client_login_email = client.user.email or ""
    
    # Get organization email and phone from first admin user
    org_email = ""
    org_phone = ""
    if organization.users:
        admin_user = next((u for u in organization.users if u.role.value == "admin"), None)
        if admin_user:
            org_email = admin_user.email or ""
            org_phone = admin_user.phone or ""
    
    # Build variable map
    variables: Dict[str, Any] = {
        # Client variables
        "client_name": client.client_name or "",
        "company_name": client.company_name or "",
        "client_email": client.email or "",
        "client_phone": client.phone_number or "",
        
        # Organization variables
        "org_name": organization.name or "",
        "org_email": org_email,
        "org_phone": org_phone,
        "org_city": organization.city or "",
        "org_state": organization.state or "",
        "org_country": organization.country or "",
        "org_pincode": organization.pincode or "",
        
        # Service variables
        "service_name": template.name or "",
        "service_description": service_description or "",
        
        # Date variables
        "current_date": date.today().strftime("%Y-%m-%d"),
        "date": date.today().strftime("%Y-%m-%d"),  # Alias for current_date
        "today": date.today().strftime("%Y-%m-%d"),  # Alias for current_date
        "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # Login credentials
        "login_email": login_email or client_login_email or "",
        "login_password": login_password or "[Password not available. Please use password reset or contact administrator.]",  # Note: Plain password cannot be retrieved from database
        "login_url": login_url or "[Login URL not configured. Please contact administrator.]",  # Frontend login URL
        
        # Other variables
        "amount": amount or "",
        "document_name": document_name or "",
        "additional_notes": client.additional_notes or "",
    }
    
    # Scheduled date
    if scheduled_date:
        variables["scheduled_date"] = scheduled_date.strftime("%Y-%m-%d")
    else:
        variables["scheduled_date"] = ""
    
    # Deadline date
    if deadline_date:
        variables["deadline_date"] = deadline_date.strftime("%Y-%m-%d")
    else:
        variables["deadline_date"] = scheduled_date.strftime("%Y-%m-%d") if scheduled_date else ""
    
    # Follow-up date (from client)
    if client.follow_date:
        variables["follow_up_date"] = client.follow_date.strftime("%Y-%m-%d")
    else:
        variables["follow_up_date"] = ""
    
    # Replace variables in subject and body
    subject = replace_variables_in_text(template.subject, variables)
    body = replace_variables_in_text(template.body, variables)
    
    # Wrap body in professional HTML email template with organization name
    body = wrap_email_in_html_template(body, organization_name=organization.name or "Navedhana Private Limited")
    
    return subject, body


def wrap_email_in_html_template(body_content: str, organization_name: str = "Navedhana Private Limited") -> str:
    """
    Wrap email body in professional HTML template.
    
    This function:
    1. Checks if content already has HTML tags
    2. If plain text, converts to HTML paragraphs
    3. Wraps everything in a professional HTML email template
    
    Args:
        body_content: Email body content (plain text or HTML)
        organization_name: Name of the organization sending the email (default: "Navedhana Private Limited")
        
    Returns:
        Complete HTML email with professional formatting
    """
    if not body_content:
        body_content = ""
    
    # Check if content already has HTML tags
    has_html = bool(re.search(r'<[a-z][\s\S]*>', body_content, re.IGNORECASE))
    
    if has_html:
        # Content already has HTML, use it as-is
        formatted_content = body_content
    else:
        # Convert plain text to HTML paragraphs
        # Split by newlines and create paragraphs
        lines = [line.strip() for line in body_content.split('\n') if line.strip()]
        
        if not lines:
            formatted_content = "<p style=\"margin: 0 0 16px 0; line-height: 1.6; color: #333333;\"></p>"
        else:
            formatted_content = ''.join([
                f'<p style="margin: 0 0 16px 0; line-height: 1.6; color: #333333;">{html.escape(line)}</p>'
                for line in lines
            ])
    
    # Wrap in professional HTML email template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Email</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; line-height: 1.6;">
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5; padding: 40px 0;">
    <tr>
      <td align="center" style="padding: 0;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
          <tr>
            <td style="padding: 40px 40px 30px 40px; background-color: #ffffff; border-radius: 8px 8px 0 0;">
              <div style="text-align: center;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #1a1a1a; letter-spacing: -0.5px;">{html.escape(organization_name)}</h1>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding: 0 40px 40px 40px; background-color: #ffffff;">
              <div style="color: #333333; font-size: 16px; line-height: 1.6;">
                {formatted_content}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding: 30px 40px; background-color: #f9f9f9; border-radius: 0 0 8px 8px; border-top: 1px solid #e5e5e5;">
              <div style="text-align: center; color: #666666; font-size: 14px; line-height: 1.5;">
                <p style="margin: 0 0 8px 0;">Best regards,</p>
                <p style="margin: 0; font-weight: 500; color: #333333;">{html.escape(organization_name)}</p>
                <p style="margin: 12px 0 0 0; font-size: 12px; color: #999999;">
                  This is an automated email. Please do not reply directly to this message.
                </p>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    
    return html_template


def replace_variables_in_text(text: str, variables: Dict[str, Any]) -> str:
    """
    Replace {{variable_name}} patterns in text with values from variables dict.
    
    Args:
        text: Text containing variable placeholders
        variables: Dictionary mapping variable names to values
        
    Returns:
        Text with variables replaced
    """
    if not text:
        return text
    
    result = text
    # Find all {{variable_name}} patterns
    pattern = r'\{\{(\w+)\}\}'
    
    def replace_match(match):
        var_name = match.group(1)
        value = variables.get(var_name, "")
        # Convert value to string, handle None
        return str(value) if value is not None else ""
    
    result = re.sub(pattern, replace_match, result)
    
    return result

