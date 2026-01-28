#!/usr/bin/env python3
"""
Test script to send a sample email using the email service.
Run this script to test your Hostinger SMTP configuration.
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.email_service import send_email, is_email_configured
from app.core.config import settings


async def test_send_email():
    """Test sending a sample email."""
    
    print("=" * 60)
    print("Email Configuration Test")
    print("=" * 60)
    
    # Check if email is configured
    if not is_email_configured():
        print("\n❌ Email is NOT configured!")
        print("\nMissing settings:")
        if not settings.SMTP_HOST:
            print("  - SMTP_HOST")
        if not settings.SMTP_USER:
            print("  - SMTP_USER")
        if not settings.SMTP_PASSWORD:
            print("  - SMTP_PASSWORD")
        if not settings.SMTP_FROM_EMAIL:
            print("  - SMTP_FROM_EMAIL")
        print("\nPlease set these in your .env file:")
        print("  SMTP_HOST=smtp.hostinger.com")
        print("  SMTP_PORT=465  # or 587")
        print("  SMTP_USER=your-email@yourdomain.com")
        print("  SMTP_PASSWORD=your-password")
        print("  SMTP_FROM_EMAIL=your-email@yourdomain.com")
        print("  SMTP_FROM_NAME=Your Organization")
        print("  SMTP_USE_TLS=True")
        print("  SMTP_TIMEOUT=60")
        return False
    
    print("\n✓ Email is configured")
    print(f"  SMTP Host: {settings.SMTP_HOST}")
    print(f"  SMTP Port: {settings.SMTP_PORT}")
    print(f"  SMTP User: {settings.SMTP_USER}")
    print(f"  From Email: {settings.SMTP_FROM_EMAIL}")
    print(f"  From Name: {settings.SMTP_FROM_NAME}")
    print(f"  Use TLS: {settings.SMTP_USE_TLS}")
    print(f"  Timeout: {settings.SMTP_TIMEOUT}s")
    
    # Get recipient email from command line or use default
    if len(sys.argv) > 1:
        recipient_email = sys.argv[1]
    else:
        recipient_email = input("\nEnter recipient email address: ").strip()
    
    if not recipient_email:
        print("❌ No email address provided")
        return False
    
    print(f"\n📧 Sending test email to: {recipient_email}")
    print("   Please wait...")
    
    # Sample HTML email body (using f-string to avoid CSS brace conflicts)
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    from_email = settings.SMTP_FROM_EMAIL
    from_name = settings.SMTP_FROM_NAME
    
    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Email</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background-color: #f5f5f5;
                line-height: 1.6;
            }}
            .email-container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .email-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .email-header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .email-body {{
                padding: 40px 30px;
                color: #333333;
            }}
            .email-body h2 {{
                color: #667eea;
                margin-top: 0;
            }}
            .email-body p {{
                margin: 16px 0;
                line-height: 1.8;
            }}
            .success-box {{
                background-color: #d4edda;
                border-left: 4px solid #28a745;
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 4px;
                color: #155724;
            }}
            .info-box {{
                background-color: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .email-footer {{
                background-color: #f8f9fa;
                padding: 30px;
                text-align: center;
                color: #666666;
                font-size: 14px;
                border-top: 1px solid #e5e5e5;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h1>✅ Test Email Successful!</h1>
            </div>
            
            <div class="email-body">
                <h2>Hello!</h2>
                
                <p>This is a test email from the CAA (Chartered Accountancy Automation) Backend system.</p>
                
                <div class="success-box">
                    <strong>✓ Email Configuration Working!</strong>
                    <p>If you received this email, your Hostinger SMTP configuration is working correctly.</p>
                </div>
                
                <div class="info-box">
                    <strong>Email Details:</strong>
                    <ul>
                        <li>SMTP Host: {smtp_host}</li>
                        <li>SMTP Port: {smtp_port}</li>
                        <li>From: {from_email}</li>
                        <li>From Name: {from_name}</li>
                    </ul>
                </div>
                
                <p>This email was sent to verify that the email service is properly configured and functioning.</p>
                
                <p>You can now use the email service to send:</p>
                <ul>
                    <li>Login credentials to users</li>
                    <li>Scheduled email templates</li>
                    <li>Notifications and reminders</li>
                </ul>
                
                <p>Best regards,<br>
                <strong>{from_name}</strong></p>
            </div>
            
            <div class="email-footer">
                <p><strong>{from_name}</strong></p>
                <p>This is an automated test email from the CAA Backend system.</p>
                <p>© 2024 CAA Platform. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send the email
    try:
        success = await send_email(
            to_email=recipient_email,
            subject="✅ Test Email - CAA Backend Email Configuration",
            html_body=html_body,
            from_name=settings.SMTP_FROM_NAME
        )
        
        if success:
            print("\n" + "=" * 60)
            print("✅ SUCCESS! Email sent successfully!")
            print("=" * 60)
            print(f"\nCheck the inbox of: {recipient_email}")
            print("\nIf you don't see the email:")
            print("  1. Check your spam/junk folder")
            print("  2. Wait a few minutes for delivery")
            print("  3. Verify the email address is correct")
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ FAILED! Email could not be sent")
            print("=" * 60)
            print("\nCheck the error messages above for details.")
            print("\nTroubleshooting:")
            print("  1. Verify SMTP credentials are correct")
            print("  2. Try using port 465 instead of 587")
            print("  3. Increase SMTP_TIMEOUT in .env")
            print("  4. Check firewall/network settings")
            return False
            
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR! Exception occurred")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        print("\nCheck the error details above.")
        return False


if __name__ == "__main__":
    print("\n🚀 Starting email test...\n")
    result = asyncio.run(test_send_email())
    sys.exit(0 if result else 1)
