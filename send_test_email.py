#!/usr/bin/env python3
"""
Script to send a test email from the terminal.
Usage: python send_test_email.py <recipient_email>
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.email_service import send_email, is_email_configured
from app.core.config import settings


async def main():
    """Send a test email."""
    # Get recipient email from command line argument
    if len(sys.argv) < 2:
        print("Usage: python send_test_email.py <recipient_email>")
        print("Example: python send_test_email.py your-email@gmail.com")
        sys.exit(1)
    
    recipient_email = sys.argv[1]
    
    # Check if email is configured
    if not is_email_configured():
        print("❌ Email service is not configured!")
        print("\nPlease set the following environment variables in your .env file:")
        print("  SMTP_HOST=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USER=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-app-password")
        print("  SMTP_FROM_EMAIL=your-email@gmail.com")
        print("  SMTP_USE_TLS=true")
        print("\nSee GMAIL_SETUP.md for detailed instructions.")
        sys.exit(1)
    
    print(f"📧 Sending test email to: {recipient_email}")
    print(f"📤 From: {settings.SMTP_FROM_EMAIL}")
    print(f"🔗 SMTP Server: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    print()
    
    # Create test email HTML body
    html_body = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background-color: #4CAF50;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }
            .content {
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 5px 5px;
            }
            .test-message {
                background-color: white;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                padding: 20px;
                margin: 20px 0;
            }
            .success {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
                color: #155724;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✅ Test Email Successful!</h1>
        </div>
        <div class="content">
            <p>This is a test email from the CAA Backend system.</p>
            
            <div class="test-message">
                <p><strong>Test Details:</strong></p>
                <ul>
                    <li>Email service is configured correctly</li>
                    <li>SMTP connection is working</li>
                    <li>Email sending functionality is operational</li>
                </ul>
            </div>
            
            <div class="success">
                <strong>✓ Success!</strong> If you received this email, your email configuration is working perfectly!
            </div>
            
            <p>You can now use the email scheduling features in the CAA Backend system.</p>
            
            <p>Best regards,<br>
            CAA Backend System</p>
        </div>
    </body>
    </html>
    """
    
    subject = "Test Email from CAA Backend - Email Configuration Test"
    
    try:
        print("⏳ Sending email...")
        success = await send_email(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body
        )
        
        if success:
            print("✅ Test email sent successfully!")
            print(f"📬 Check your inbox at: {recipient_email}")
            print("\nIf you don't see the email:")
            print("  - Check your spam/junk folder")
            print("  - Wait a few seconds (email delivery can take time)")
            print("  - Verify your SMTP settings are correct")
        else:
            print("❌ Failed to send test email.")
            print("Check the error messages above for details.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Verify your SMTP settings in .env file")
        print("  2. Check that your Gmail App Password is correct")
        print("  3. Ensure 2-Step Verification is enabled on Gmail")
        print("  4. See GMAIL_SETUP.md for detailed setup instructions")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

