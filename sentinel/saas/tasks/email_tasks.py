"""
Email Celery Tasks - Async email sending with retry logic
"""

from celery import Task
from typing import Dict, Any
from datetime import datetime
import logging

from ..celery_app import celery_app
from ..services.email_service import EmailService, EmailConfig
from ..database import SessionLocal
from ..models.email_log import EmailLog, EmailStatus
import uuid

logger = logging.getLogger(__name__)


class EmailTask(Task):
    """
    Base email task with retry logic and error handling

    Retry strategy:
    - Max 3 retries
    - Exponential backoff: 5min, 15min, 45min
    """
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 2700  # 45 minutes
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=EmailTask,
    name="send_email_task",
    default_retry_delay=300,  # 5 minutes
)
def send_email_task(
    self,
    template_name: str,
    to_email: str,
    context: Dict[str, Any],
    org_id: str = None,
    user_id: str = None,
) -> Dict[str, Any]:
    """
    Send email asynchronously with retry logic

    Args:
        template_name: Template name (e.g., "invitation", "verification")
        to_email: Recipient email address
        context: Template context variables
        org_id: Organization ID (for logging)
        user_id: User ID (for logging)

    Returns:
        Dictionary with success status and details

    Raises:
        Exception: If email sending fails after all retries
    """
    db = SessionLocal()
    email_log = None

    try:
        # Create email log entry
        if org_id:
            email_log = EmailLog(
                email_log_id=uuid.uuid4(),
                org_id=uuid.UUID(org_id) if org_id else None,
                user_id=uuid.UUID(user_id) if user_id else None,
                template_name=template_name,
                to_email=to_email,
                subject=_get_subject_for_template(template_name, context),
                status=EmailStatus.PENDING,
                provider=EmailConfig.from_env().provider,
                created_at=datetime.utcnow(),
            )
            db.add(email_log)
            db.commit()
            db.refresh(email_log)

        # Initialize email service
        email_service = EmailService()

        # Send email based on template
        success = False
        if template_name == "invitation":
            success = email_service.send_invitation_email(
                to_email=to_email,
                user_name=context.get("user_name", ""),
                org_name=context.get("org_name", ""),
                inviter_name=context.get("inviter_name", ""),
                temporary_password=context.get("temporary_password", ""),
                login_url=context.get("login_url", ""),
                expires_hours=context.get("expires_hours", 24),
            )
        elif template_name == "verification":
            success = email_service.send_verification_email(
                to_email=to_email,
                user_name=context.get("user_name", ""),
                verification_url=context.get("verification_url", ""),
            )
        elif template_name == "password_reset":
            success = email_service.send_password_reset_email(
                to_email=to_email,
                user_name=context.get("user_name", ""),
                reset_url=context.get("reset_url", ""),
                expires_minutes=context.get("expires_minutes", 30),
            )
        else:
            raise ValueError(f"Unknown template: {template_name}")

        # Update email log if successful
        if success and email_log:
            email_log.status = EmailStatus.SENT
            email_log.sent_at = datetime.utcnow()
            db.commit()

            logger.info(
                f"Email sent successfully: {template_name} to {to_email} "
                f"(log_id: {email_log.email_log_id})"
            )

            return {
                "success": True,
                "email_log_id": str(email_log.email_log_id),
                "to_email": to_email,
                "template": template_name,
                "sent_at": email_log.sent_at.isoformat(),
            }
        elif not success:
            raise Exception(f"Failed to send {template_name} email to {to_email}")

    except Exception as e:
        logger.error(f"Error sending {template_name} email to {to_email}: {e}")

        # Update email log if it exists
        if email_log:
            email_log.status = EmailStatus.FAILED
            email_log.error_message = str(e)
            db.commit()

        # Retry the task
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(name="send_bulk_email_task")
def send_bulk_email_task(
    template_name: str,
    recipients: list,
    context_template: Dict[str, Any],
    org_id: str = None,
) -> Dict[str, Any]:
    """
    Send bulk emails asynchronously

    Args:
        template_name: Template name
        recipients: List of recipient dictionaries with email and context overrides
        context_template: Base context template
        org_id: Organization ID

    Returns:
        Dictionary with success count and failed emails

    Example:
        send_bulk_email_task.delay(
            template_name="invitation",
            recipients=[
                {"email": "user1@example.com", "user_name": "User 1"},
                {"email": "user2@example.com", "user_name": "User 2"},
            ],
            context_template={"org_name": "Acme Corp", ...},
            org_id="..."
        )
    """
    success_count = 0
    failed_emails = []

    for recipient_data in recipients:
        to_email = recipient_data.pop("email")

        # Merge context
        context = {**context_template, **recipient_data}

        try:
            # Queue individual email task
            send_email_task.delay(
                template_name=template_name,
                to_email=to_email,
                context=context,
                org_id=org_id,
                user_id=recipient_data.get("user_id"),
            )
            success_count += 1

        except Exception as e:
            logger.error(f"Failed to queue email for {to_email}: {e}")
            failed_emails.append({"email": to_email, "error": str(e)})

    logger.info(
        f"Bulk email task completed: {success_count} queued, "
        f"{len(failed_emails)} failed"
    )

    return {
        "success_count": success_count,
        "failed_count": len(failed_emails),
        "failed_emails": failed_emails,
    }


def _get_subject_for_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    Generate email subject based on template and context

    Args:
        template_name: Template name
        context: Template context

    Returns:
        Email subject string
    """
    subjects = {
        "invitation": f"You've been invited to join {context.get('org_name', 'Sentinel')}",
        "verification": "Verify your Sentinel email address",
        "password_reset": "Reset your Sentinel password",
    }

    return subjects.get(template_name, "Notification from Sentinel")
