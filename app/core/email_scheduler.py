"""
Background scheduler service for sending scheduled emails.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.db.session import get_session_local
from app.db.models.client_email_config import ScheduledEmail, ScheduledEmailStatus
from app.db.models.client import Client
from app.db.models.email_template import EmailTemplate
from app.db.models.organization import Organization
from app.core.email_template_utils import replace_template_variables
from app.core.email_service import send_email
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler():
    """Start the email scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        # Schedule job to run every minute
        scheduler.add_job(
            process_scheduled_emails,
            trigger=CronTrigger(second=0),  # Run at the start of every minute
            id='process_scheduled_emails',
            name='Process scheduled emails',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Email scheduler started")


def stop_scheduler():
    """Stop the email scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Email scheduler stopped")


def process_scheduled_emails():
    """
    Process scheduled emails that are due to be sent.
    This function runs every minute to check for emails to send.
    """
    SessionLocal = get_session_local()
    db: Session = None
    
    try:
        db = SessionLocal()
        current_datetime = datetime.now()
        current_date = current_datetime.date()
        
        # Find emails to send:
        # - status == 'pending'
        # - scheduled_datetime <= current_datetime
        # - (is_recurring == false) OR (is_recurring == true AND (recurrence_end_date is None OR recurrence_end_date >= current_date))
        
        query = db.query(ScheduledEmail).filter(
            ScheduledEmail.status == ScheduledEmailStatus.PENDING.value,
            ScheduledEmail.scheduled_datetime <= current_datetime
        )
        
        # Filter recurring emails
        recurring_filter = (
            (ScheduledEmail.is_recurring == False) |
            (
                (ScheduledEmail.is_recurring == True) &
                (
                    (ScheduledEmail.recurrence_end_date.is_(None)) |
                    (ScheduledEmail.recurrence_end_date >= current_date)
                )
            )
        )
        
        query = query.filter(recurring_filter)
        
        scheduled_emails = query.all()
        
        # Only log when there are emails to process (reduce log noise)
        if len(scheduled_emails) > 0:
            logger.info("="*80)
            logger.info(f"📧 EMAIL SCHEDULER - Checking for scheduled emails at {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*80)
            logger.info(f"🔍 Found {len(scheduled_emails)} scheduled email(s) to process")
            logger.info(f"\n📬 Processing {len(scheduled_emails)} email(s):\n")
        # Only log "no emails" at DEBUG level to reduce console noise
        else:
            logger.debug(f"Email scheduler checked at {current_datetime.strftime('%Y-%m-%d %H:%M:%S')} - no emails to send")

        for idx, scheduled_email in enumerate(scheduled_emails, 1):
            try:
                logger.info(f"[{idx}/{len(scheduled_emails)}] Processing scheduled email ID: {scheduled_email.id}")
                send_scheduled_email(db, scheduled_email)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error processing scheduled email {scheduled_email.id}: {error_msg}", exc_info=True)
                # Update status to failed
                try:
                    scheduled_email.status = ScheduledEmailStatus.FAILED.value
                    scheduled_email.error_message = error_msg[:500]  # Limit error message length
                    db.commit()
                except Exception as db_error:
                    logger.error(f"❌ Failed to update scheduled email {scheduled_email.id} status: {str(db_error)}")
                    db.rollback()
        
        db.commit()
        if len(scheduled_emails) > 0:
            logger.info("="*80)
            logger.info("✅ Email scheduler job completed")
            logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Error in process_scheduled_emails: {str(e)}", exc_info=True)
        if db:
            try:
                db.rollback()
            except Exception:
                pass  # Ignore rollback errors during shutdown
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass  # Ignore close errors during shutdown


def send_scheduled_email(db: Session, scheduled_email: ScheduledEmail):
    """
    Send a single scheduled email.
    
    Args:
        db: Database session
        scheduled_email: ScheduledEmail instance to send
    """
    logger.info(f"Starting email send process for scheduled email ID: {scheduled_email.id}")
    logger.info(f"Client ID: {scheduled_email.client_id}, Template ID: {scheduled_email.template_id}")
    logger.info(f"Scheduled for: {scheduled_email.scheduled_date} at {scheduled_email.scheduled_time}")
    logger.info(f"Recipients: {', '.join(scheduled_email.recipient_emails)}")
    
    # Get client with user and services relationships loaded
    from sqlalchemy.orm import joinedload
    logger.debug("Fetching client data...")
    client = db.query(Client).options(
        joinedload(Client.user),
        joinedload(Client.services)
    ).filter(Client.id == scheduled_email.client_id).first()
    if not client:
        error_msg = f"Client {scheduled_email.client_id} not found"
        logger.error(f"Client {scheduled_email.client_id} not found for scheduled email {scheduled_email.id}")
        scheduled_email.status = ScheduledEmailStatus.FAILED.value
        scheduled_email.error_message = "Client not found"
        return
    logger.info(f"Client found: {client.client_name} ({client.company_name})")
    
    logger.debug("Fetching email template...")
    template = None
    if scheduled_email.template_id:
        template = db.query(EmailTemplate).filter(EmailTemplate.id == scheduled_email.template_id).first()
        if not template:
            error_msg = f"Template {scheduled_email.template_id} not found"
            logger.error(f"Template {scheduled_email.template_id} not found for scheduled email {scheduled_email.id}")
            scheduled_email.status = ScheduledEmailStatus.FAILED.value
            scheduled_email.error_message = "Template not found"
            return
        logger.info(f"Template found: '{template.name}' (ID: {template.id})")
        # Log template details for debugging
        logger.info(f"Using template ID {template.id}: '{template.name}' - Subject: '{template.subject[:50]}...', Body length: {len(template.body) if template.body else 0}")
    
    logger.debug("Fetching organization data...")
    from sqlalchemy.orm import joinedload
    organization = db.query(Organization).options(joinedload(Organization.users)).filter(Organization.id == client.org_id).first()
    if not organization:
        error_msg = f"Organization {client.org_id} not found"
        logger.error(f"Organization {client.org_id} not found for scheduled email {scheduled_email.id}")
        scheduled_email.status = ScheduledEmailStatus.FAILED.value
        scheduled_email.error_message = "Organization not found"
        return
    logger.info(f"Organization found: {organization.name}")
    
    # Get admin's full name for email sender
    admin_full_name = None
    if organization.users:
        admin_user = next((u for u in organization.users if u.role.value == "admin"), None)
        if admin_user:
            admin_full_name = admin_user.full_name
    logger.info(f"Admin sender: {admin_full_name or 'CAA System'}")
    
    if not template:
        error_msg = "No template specified"
        logger.error(f"No template specified for scheduled email {scheduled_email.id}")
        scheduled_email.status = ScheduledEmailStatus.FAILED.value
        scheduled_email.error_message = "Template not specified"
        return
    
    # Get login email and password from client's user account
    login_email = None
    login_password = None
    if client.user_id and client.user:
        login_email = client.user.email
        # Try to decrypt the stored plain password if available
        from app.core.security import decrypt_password
        if client.user.encrypted_plain_password:
            login_password = decrypt_password(client.user.encrypted_plain_password)
        # If decryption fails or password not stored, login_password will remain None
        # and the template will use the default message
    
    # Construct login URL from frontend URL configuration
    from app.core.config import settings
    if settings.FRONTEND_URL:
        # Remove trailing slash if present
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        login_url = f"{frontend_url}/login"
    else:
        # Log warning if FRONTEND_URL is not configured
        logger.warning(f"FRONTEND_URL not configured. login_url will be empty for scheduled email {scheduled_email.id}")
        login_url = ""  # Empty if not configured
    
    # Replace template variables
    logger.debug("Replacing template variables...")
    try:
        logger.info(f"Replacing template variables for scheduled email {scheduled_email.id}")
        logger.info(f"Template ID: {template.id}, Name: '{template.name}'")
        logger.info(f"Template subject (raw): '{template.subject}'")
        logger.info(f"Template body (raw, first 500 chars): {template.body[:500] if template.body else 'None'}")
        logger.info(f"Template body length: {len(template.body) if template.body else 0}")
        logger.debug(f"Full template body: {template.body}")
        
        # Get service description if client has services
        service_description = ""
        if client.services:
            # Get first service description if available
            first_service = client.services[0]
            if hasattr(first_service, 'description'):
                service_description = first_service.description or ""
        
        subject, body = replace_template_variables(
            template=template,
            client=client,
            organization=organization,
            scheduled_date=scheduled_email.scheduled_date,
            deadline_date=scheduled_email.scheduled_date,
            login_email=login_email,
            login_password=login_password,  # Decrypted password if available
            login_url=login_url,
            service_description=service_description,
            amount=None,  # Can be passed if available in future
            document_name=None  # Can be passed if available in future
        )
        
        logger.info(f"Variables replaced - Subject: '{subject[:60]}...'")
        logger.info(f"Body length: {len(body)} characters")
        logger.debug(f"Template body preview (first 300 chars): {body[:300]}")
        logger.info(f"Template variables replaced. Subject: '{subject[:50]}...', Body length: {len(body)}")
        logger.info(f"Template body after replacement (first 500 chars): {body[:500]}")
        logger.debug(f"Full template body: {body}")
    except Exception as e:
        error_msg = f"Template variable replacement error: {str(e)}"
        logger.error(f"Error replacing template variables for scheduled email {scheduled_email.id}: {str(e)}", exc_info=True)
        scheduled_email.status = ScheduledEmailStatus.FAILED.value
        scheduled_email.error_message = error_msg
        return
    
    # Send email to each recipient
    logger.info(f"Sending email to {len(scheduled_email.recipient_emails)} recipient(s)...")
    success_count = 0
    error_messages = []
    
    import asyncio
    import time
    
    async def send_email_with_retry(to_email: str, subject: str, html_body: str, from_name: str, max_retries: int = None):
        """
        Send email with retry logic to handle transient failures.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: Email HTML body
            from_name: Sender name
            max_retries: Maximum number of retry attempts (defaults to SMTP_RETRY_ATTEMPTS from settings)
            
        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        if max_retries is None:
            max_retries = settings.SMTP_RETRY_ATTEMPTS
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt}/{max_retries} to send email to {to_email}")
                success = await send_email(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    from_name=from_name
                )
                
                if success:
                    logger.info(f"✓ Successfully sent email to {to_email} (attempt {attempt})")
                    return True, None
                else:
                    error_msg = f"send_email returned False (attempt {attempt})"
                    logger.warning(f"⚠ {error_msg} for {to_email}")
                    
                    # If not the last attempt, wait before retrying
                    if attempt < max_retries:
                        wait_time = attempt * 2  # Exponential backoff: 2s, 4s, 6s
                        logger.info(f"Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                    
            except Exception as e:
                error_msg = str(e)
                error_lower = error_msg.lower()
                
                # Check if it's a retryable error
                is_retryable = any(keyword in error_lower for keyword in [
                    "timeout", "timed out", "connection", "network", "temporary"
                ])
                
                if is_retryable and attempt < max_retries:
                    wait_time = attempt * 2  # Exponential backoff
                    logger.warning(f"⚠ Retryable error on attempt {attempt} for {to_email}: {error_msg}")
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to send email to {to_email} (attempt {attempt}): {error_msg}")
                    return False, error_msg
        
        # All retries exhausted
        final_error = f"Failed after {max_retries} attempts"
        logger.error(f"❌ All retries exhausted for {to_email}: {final_error}")
        return False, final_error
    
    async def send_all_emails():
        """Send all emails with retry logic and rate limiting."""
        nonlocal success_count, error_messages
        
        # Send emails sequentially with small delays to avoid rate limiting
        # This is more reliable than sending all at once
        for idx, recipient_email in enumerate(scheduled_email.recipient_emails):
            logger.info(f"[{idx + 1}/{len(scheduled_email.recipient_emails)}] Sending to: {recipient_email}")
            
            # Add small delay between emails to avoid overwhelming SMTP server
            if idx > 0:
                delay = settings.SMTP_EMAIL_DELAY
                logger.debug(f"Waiting {delay}s before next email (rate limiting)...")
                await asyncio.sleep(delay)
            
            success, error_msg = await send_email_with_retry(
                to_email=recipient_email,
                subject=subject,
                html_body=body,
                from_name=admin_full_name
            )
            
            if success:
                success_count += 1
            else:
                error_message = f"Error sending to {recipient_email}: {error_msg or 'Unknown error'}"
                logger.error(error_message)
                error_messages.append(error_message)
    
    # Run async function
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        logger.info("Starting async email send process...")
        loop.run_until_complete(send_all_emails())
        logger.info(f"Async email send process completed. Success: {success_count}/{len(scheduled_email.recipient_emails)}")
    except Exception as e:
        error_msg = f"Error in async email sending: {str(e)}"
        logger.error(error_msg, exc_info=True)
        error_messages.append(error_msg)
        success_count = 0  # Mark as failed if async execution fails
    
    # Update status
    try:
        if success_count > 0:
            # At least one email was sent successfully
            scheduled_email.status = ScheduledEmailStatus.SENT.value
            scheduled_email.sent_at = datetime.now()
            if error_messages:
                # Limit error message length to avoid database issues
                error_msg_combined = "; ".join(error_messages)
                scheduled_email.error_message = error_msg_combined[:1000]  # Limit to 1000 chars
            
            logger.info(f"✅ Status: SENT ({success_count}/{len(scheduled_email.recipient_emails)} successful)")
            if error_messages:
                logger.warning(f"⚠️  Partial success - some recipients failed: {len(error_messages)} failed")
                for err in error_messages:
                    logger.warning(f"  - {err}")
            
            # If this is a recurring email, create next occurrence
            if scheduled_email.is_recurring:
                try:
                    create_next_recurring_email(db, scheduled_email)
                    logger.info("✅ Created next recurring email")
                except Exception as recur_error:
                    logger.error(f"❌ Failed to create next recurring email: {str(recur_error)}", exc_info=True)
            
            logger.info("✅ Email send process completed successfully")
        else:
            # All emails failed
            scheduled_email.status = ScheduledEmailStatus.FAILED.value
            error_msg_combined = "; ".join(error_messages) if error_messages else "Failed to send all emails"
            scheduled_email.error_message = error_msg_combined[:1000]  # Limit to 1000 chars
            logger.error(f"❌ FAILED: All recipients failed to receive email ({len(scheduled_email.recipient_emails)} recipients)")
            logger.error(f"   Error details: {scheduled_email.error_message}")
        
        db.commit()
        logger.debug("Database commit successful")
    except Exception as commit_error:
        logger.error(f"❌ Failed to commit scheduled email status: {str(commit_error)}", exc_info=True)
        db.rollback()
        raise


def create_next_recurring_email(db: Session, scheduled_email: ScheduledEmail):
    """
    Create the next occurrence of a recurring email.
    
    Args:
        db: Database session
        scheduled_email: The scheduled email that was just sent (recurring)
    """
    current_date = scheduled_email.scheduled_date
    recurrence_end_date = scheduled_email.recurrence_end_date
    
    # Check if we should create next occurrence
    if recurrence_end_date and current_date >= recurrence_end_date:
        # Recurrence has ended
        return
    
    # Calculate next date (tomorrow)
    next_date = current_date + timedelta(days=1)
    
    # If there's an end date and next_date exceeds it, don't create
    if recurrence_end_date and next_date > recurrence_end_date:
        return
    
    # Create next scheduled email
    next_datetime = datetime.combine(next_date, scheduled_email.scheduled_time)
    
    next_scheduled_email = ScheduledEmail(
        client_id=scheduled_email.client_id,
        template_id=scheduled_email.template_id,
        recipient_emails=scheduled_email.recipient_emails,
        scheduled_date=next_date,
        scheduled_time=scheduled_email.scheduled_time,
        scheduled_datetime=next_datetime,
        status=ScheduledEmailStatus.PENDING.value,
        is_recurring=True,
        recurrence_end_date=recurrence_end_date
    )
    
    db.add(next_scheduled_email)
    db.flush()
    logger.info(f"Created next recurring email (ID: {next_scheduled_email.id}) for scheduled_email {scheduled_email.id}")

