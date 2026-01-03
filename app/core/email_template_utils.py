"""
Utility functions for email template variable replacement.
"""
import re
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
    
    # Convert newlines to HTML line breaks for HTML emails
    # Replace \n with <br> for HTML rendering
    body = body.replace('\n', '<br>')
    # Also handle \r\n (Windows line endings)
    body = body.replace('\r\n', '<br>')
    # Replace multiple consecutive <br> with single <br>
    import re
    body = re.sub(r'<br>\s*<br>', '<br>', body)
    
    # Wrap body in basic HTML structure if it's not already HTML
    # Check if body already contains HTML tags
    if not re.search(r'<[a-z][\s\S]*>', body, re.IGNORECASE):
        # Wrap in basic HTML structure
        body = f"""
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
    </style>
</head>
<body>
{body}
</body>
</html>
"""
    
    return subject, body


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

