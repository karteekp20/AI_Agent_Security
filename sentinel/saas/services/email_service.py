"""
Email Service - AWS SES and SMTP Integration
Handles sending transactional emails with Jinja2 templates
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

from pydantic import BaseModel, EmailStr
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


class EmailConfig(BaseModel):
    """Email service configuration"""
    provider: str = "smtp"  # "ses" or "smtp"

    # AWS SES Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    ses_from_email: str = "noreply@sentinel.ai"
    ses_from_name: str = "Sentinel Security"

    # SMTP Configuration (Development fallback)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    # Email Settings
    email_logo_url: str = "https://sentinel.ai/logo.png"
    email_support_email: str = "support@sentinel.ai"

    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Load configuration from environment variables"""
        return cls(
            provider=os.getenv("EMAIL_PROVIDER", "smtp"),
            aws_region=os.getenv("AWS_SES_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            ses_from_email=os.getenv("AWS_SES_FROM_EMAIL", "noreply@sentinel.ai"),
            ses_from_name=os.getenv("AWS_SES_FROM_NAME", "Sentinel Security"),
            smtp_host=os.getenv("SMTP_HOST", "localhost"),
            smtp_port=int(os.getenv("SMTP_PORT", "1025")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            email_logo_url=os.getenv("EMAIL_LOGO_URL", "https://sentinel.ai/logo.png"),
            email_support_email=os.getenv("EMAIL_SUPPORT_EMAIL", "support@sentinel.ai"),
        )


class EmailService:
    """Email service with AWS SES and SMTP support"""

    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Initialize email service

        Args:
            config: EmailConfig instance. If None, loads from environment
        """
        self.config = config or EmailConfig.from_env()

        # Initialize Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Initialize SES client if using SES
        self.ses_client = None
        if self.config.provider == "ses":
            try:
                import boto3
                self.ses_client = boto3.client(
                    'ses',
                    region_name=self.config.aws_region,
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                )
                logger.info("AWS SES client initialized successfully")
            except ImportError:
                logger.warning("boto3 not installed. Falling back to SMTP.")
                self.config.provider = "smtp"
            except Exception as e:
                logger.error(f"Failed to initialize SES client: {e}")
                logger.warning("Falling back to SMTP")
                self.config.provider = "smtp"

    def send_invitation_email(
        self,
        to_email: str,
        user_name: str,
        org_name: str,
        inviter_name: str,
        temporary_password: str,
        login_url: str,
        expires_hours: int = 24,
    ) -> bool:
        """
        Send user invitation email with temporary password

        Args:
            to_email: Recipient email address
            user_name: Name of invited user
            org_name: Organization name
            inviter_name: Name of person who sent invitation
            temporary_password: Temporary password for first login
            login_url: URL to login page
            expires_hours: Password expiration time in hours

        Returns:
            True if email sent successfully, False otherwise
        """
        context = {
            "user_name": user_name,
            "org_name": org_name,
            "inviter_name": inviter_name,
            "temporary_password": temporary_password,
            "login_url": login_url,
            "expires_hours": expires_hours,
            "support_email": self.config.email_support_email,
            "logo_url": self.config.email_logo_url,
            "year": datetime.now().year,
        }

        return self._send_template_email(
            to_email=to_email,
            subject=f"You've been invited to join {org_name} on Sentinel",
            template_name="invitation",
            context=context,
        )

    def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_url: str,
    ) -> bool:
        """
        Send email verification link

        Args:
            to_email: Recipient email address
            user_name: Name of user
            verification_url: URL with verification token

        Returns:
            True if email sent successfully, False otherwise
        """
        context = {
            "user_name": user_name,
            "verification_url": verification_url,
            "support_email": self.config.email_support_email,
            "logo_url": self.config.email_logo_url,
            "year": datetime.now().year,
        }

        return self._send_template_email(
            to_email=to_email,
            subject="Verify your Sentinel email address",
            template_name="verification",
            context=context,
        )

    def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_url: str,
        expires_minutes: int = 30,
    ) -> bool:
        """
        Send password reset link

        Args:
            to_email: Recipient email address
            user_name: Name of user
            reset_url: URL with reset token
            expires_minutes: Token expiration time in minutes

        Returns:
            True if email sent successfully, False otherwise
        """
        context = {
            "user_name": user_name,
            "reset_url": reset_url,
            "expires_minutes": expires_minutes,
            "support_email": self.config.email_support_email,
            "logo_url": self.config.email_logo_url,
            "year": datetime.now().year,
        }

        return self._send_template_email(
            to_email=to_email,
            subject="Reset your Sentinel password",
            template_name="password_reset",
            context=context,
        )

    def _send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        Send email using Jinja2 template

        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Template name (without extension)
            context: Template context variables

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Render HTML version
            html_body = self._render_template(f"{template_name}.html", context)

            # Render text version
            text_body = self._render_template(f"{template_name}.txt", context)

            # Send email
            if self.config.provider == "ses":
                return self._send_with_ses(to_email, subject, html_body, text_body)
            else:
                return self._send_with_smtp(to_email, subject, html_body, text_body)

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render Jinja2 template

        Args:
            template_name: Template filename
            context: Template context variables

        Returns:
            Rendered template string
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def _send_with_ses(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Send email using AWS SES

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            response = self.ses_client.send_email(
                Source=f"{self.config.ses_from_name} <{self.config.ses_from_email}>",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    }
                },
            )

            message_id = response.get('MessageId')
            logger.info(f"Email sent via SES to {to_email} (MessageId: {message_id})")
            return True

        except Exception as e:
            logger.error(f"SES send failed to {to_email}: {e}")
            return False

    def _send_with_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Send email using SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.ses_from_name} <{self.config.ses_from_email}>"
            msg['To'] = to_email

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Connect to SMTP server
            if self.config.smtp_use_tls:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)

            # Login if credentials provided
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)

            # Send email
            server.sendmail(self.config.ses_from_email, [to_email], msg.as_string())
            server.quit()

            logger.info(f"Email sent via SMTP to {to_email}")
            return True

        except Exception as e:
            logger.error(f"SMTP send failed to {to_email}: {e}")
            return False


def generate_verification_token(user_id: str, email: str) -> str:
    """
    Generate email verification token (JWT with 24h expiry)

    Args:
        user_id: User ID
        email: User email address

    Returns:
        JWT verification token
    """
    from datetime import timedelta
    from jose import jwt
    from ..auth.jwt import SECRET_KEY, ALGORITHM

    payload = {
        "user_id": str(user_id),
        "email": email,
        "token_type": "email_verification",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode email verification token

    Args:
        token: JWT verification token

    Returns:
        Token payload with user_id and email

    Raises:
        JWTError: If token is invalid or expired
    """
    from jose import jwt, JWTError
    from ..auth.jwt import SECRET_KEY, ALGORITHM

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("token_type") != "email_verification":
            raise ValueError("Invalid token type")

        return payload

    except JWTError as e:
        raise JWTError(f"Token verification failed: {str(e)}")
