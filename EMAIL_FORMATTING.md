# Email Formatting Guide

## ⚠️🚨 CRITICAL ISSUE: Backend Implementation Required 🚨⚠️

### Problem
**The preview in the frontend shows HTML-formatted emails, but emails are currently being sent as plain text.**

**Users are receiving unformatted plain text emails instead of the professional HTML format shown in the preview.**

### Root Cause
The backend email sending function is sending emails as plain text instead of HTML. The template body needs to be wrapped in an HTML email template before sending.

### Solution (URGENT)
**The backend MUST wrap email bodies in HTML when sending emails.** This is a critical fix needed immediately.

## Overview
Email templates can now be created with HTML formatting for professional-looking emails. The frontend provides tools to preview and format emails properly. However, **the backend must implement HTML wrapping** for emails to be sent in the professional format shown in the preview.

## Frontend Features

### 1. HTML Email Template Wrapper
Location: `lib/utils/email-template.ts`

The `wrapEmailInHTMLTemplate()` function wraps email body content in a professional HTML email template with:
- Professional fonts (system font stack)
- Proper spacing and padding
- Responsive design (max-width: 600px)
- Company header
- Professional footer
- Proper line heights and colors

### 2. Template Editor
- **Edit Mode**: Write HTML or plain text
- **Preview Mode**: See how the email will look with professional formatting
- **Variable Support**: Insert template variables like `{{client_name}}`, `{{company_name}}`, etc.

## Backend Integration

### ⚠️ CRITICAL: Email Sending Implementation Required

**PROBLEM:** Emails are currently being sent as plain text, but the preview shows HTML formatting. Recipients receive unformatted emails.

**SOLUTION:** When sending emails from the backend, you **MUST** wrap the template body in HTML using the `wrapEmailInHTMLTemplate()` function or equivalent backend implementation.

**Where to implement:** In the backend function that sends scheduled emails (likely in the email sending service/celery task).

### Current Issue ⚠️
**Emails are currently being sent as plain text**, which is why recipients see unformatted emails instead of the professional HTML format shown in the preview.

### Solution (REQUIRED)
The backend email sending function **MUST**:

1. **Get the template body** from the database
2. **Replace variables** with actual values
3. **Wrap in HTML template** using the wrapper function
4. **Send as HTML email** (not plain text)

### Example Backend Implementation (Python)

```python
def wrap_email_in_html_template(body_content: str) -> str:
    """Wrap email body in professional HTML template"""
    # Check if content already has HTML
    has_html = bool(re.search(r'<[a-z][\s\S]*>', body_content, re.IGNORECASE))
    
    if has_html:
        formatted_content = body_content
    else:
        # Convert plain text to HTML paragraphs
        lines = [line.strip() for line in body_content.split('\n') if line.strip()]
        formatted_content = ''.join([
            f'<p style="margin: 0 0 16px 0; line-height: 1.6; color: #333333;">{html.escape(line)}</p>'
            for line in lines
        ])
    
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
                <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #1a1a1a; letter-spacing: -0.5px;">Navedhana Private Limited</h1>
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
                <p style="margin: 0; font-weight: 500; color: #333333;">Navedhana Private Limited</p>
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

# When sending email:
def send_email(template_body: str, recipient: str, subject: str):
    # Replace variables in template body
    body_with_variables = replace_template_variables(template_body, data)
    
    # Wrap in HTML template
    html_body = wrap_email_in_html_template(body_with_variables)
    
    # Send as HTML email
    send_html_email(
        to=recipient,
        subject=subject,
        html_body=html_body
    )
```

## Template Body Format

Templates can be saved as:
- **Plain text**: Will be automatically converted to HTML paragraphs
- **HTML**: Will be preserved and wrapped in the email template

### Example Plain Text Template:
```
Dear {{client_name}},

Thank you for choosing our services.

Your login credentials are:
Email: {{email}}
Password: {{password}}

Please login at: {{login_url}}
```

### Example HTML Template:
```
<p>Dear <strong>{{client_name}}</strong>,</p>

<p>Thank you for choosing our services.</p>

<p>Your login credentials are:<br>
Email: <strong>{{email}}</strong><br>
Password: <strong>{{password}}</strong></p>

<p>Please login at: <a href="{{login_url}}">{{login_url}}</a></p>
```

Both will be wrapped in the professional HTML email template when sent.

## Implementation Checklist

### Backend Team - Required Actions:

- [ ] **Locate the email sending function** (likely in email service or scheduled email task)
- [ ] **Import or implement** the `wrapEmailInHTMLTemplate()` function (see example above)
- [ ] **Modify email sending** to:
  1. Get template body from database
  2. Replace template variables with actual values
  3. **Wrap body in HTML** using `wrapEmailInHTMLTemplate()`
  4. Send as **HTML email** (not plain text) - ensure email client is configured for HTML
- [ ] **Test** by sending a test email and verifying it matches the preview format
- [ ] **Verify** emails are sent with `Content-Type: text/html` header

### Current Email Sending Flow (WRONG):
```
Template Body → Replace Variables → Send as Plain Text ❌
```

### Required Email Sending Flow (CORRECT):
```
Template Body → Replace Variables → Wrap in HTML Template → Send as HTML Email ✅
```

## Testing

After implementation:
1. Create/edit an email template in the frontend
2. Use the preview to see the expected format
3. Schedule or send the email
4. Check the received email - it should match the preview format
5. If emails are still plain text, verify:
   - HTML wrapper function is being called
   - Email is sent with `Content-Type: text/html`
   - Email client/library supports HTML emails
