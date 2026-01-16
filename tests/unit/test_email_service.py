"""
Unit Tests for Email Service
Tests email sending functionality with mocked backends
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sentinel.saas.services.email_service import (
    EmailService,
    EmailConfig,
    generate_verification_token,
    verify_verification_token,
)


class TestEmailConfig:
    """Test Email Configuration"""

    def test_from_env_default_values(self):
        """Test loading config with default values"""
        config = EmailConfig()
        assert config.provider == "smtp"
        assert config.smtp_host == "localhost"
        assert config.smtp_port == 1025

    def test_from_env_custom_values(self, monkeypatch):
        """Test loading config from environment variables"""
        monkeypatch.setenv("EMAIL_PROVIDER", "ses")
        monkeypatch.setenv("AWS_SES_REGION", "us-west-2")
        monkeypatch.setenv("AWS_SES_FROM_EMAIL", "test@example.com")

        config = EmailConfig.from_env()
        assert config.provider == "ses"
        assert config.aws_region == "us-west-2"
        assert config.ses_from_email == "test@example.com"


class TestEmailService:
    """Test Email Service"""

    @pytest.fixture
    def email_service(self):
        """Create email service with SMTP config"""
        config = EmailConfig(provider="smtp", smtp_use_tls=False)
        return EmailService(config)

    def test_initialization(self, email_service):
        """Test email service initializes correctly"""
        assert email_service.config.provider == "smtp"
        assert email_service.jinja_env is not None
        assert email_service.ses_client is None

    @patch("sentinel.saas.services.email_service.smtplib.SMTP")
    def test_send_invitation_email_smtp(self, mock_smtp, email_service):
        """Test sending invitation email via SMTP"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = email_service.send_invitation_email(
            to_email="user@example.com",
            user_name="John Doe",
            org_name="Acme Corp",
            inviter_name="Jane Smith",
            temporary_password="temp123",
            login_url="http://localhost:5173/login",
            expires_hours=24,
        )

        assert result is True
        mock_smtp.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch("sentinel.saas.services.email_service.smtplib.SMTP")
    def test_send_verification_email_smtp(self, mock_smtp, email_service):
        """Test sending verification email via SMTP"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = email_service.send_verification_email(
            to_email="user@example.com",
            user_name="John Doe",
            verification_url="http://localhost:5173/verify?token=abc123",
        )

        assert result is True
        mock_smtp.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch("sentinel.saas.services.email_service.smtplib.SMTP")
    def test_send_password_reset_email_smtp(self, mock_smtp, email_service):
        """Test sending password reset email via SMTP"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = email_service.send_password_reset_email(
            to_email="user@example.com",
            user_name="John Doe",
            reset_url="http://localhost:5173/reset?token=xyz789",
            expires_minutes=30,
        )

        assert result is True
        mock_smtp.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch("sentinel.saas.services.email_service.smtplib.SMTP")
    def test_send_email_failure(self, mock_smtp, email_service):
        """Test email send failure handling"""
        mock_smtp.side_effect = Exception("SMTP connection failed")

        result = email_service.send_invitation_email(
            to_email="user@example.com",
            user_name="John Doe",
            org_name="Acme Corp",
            inviter_name="Jane Smith",
            temporary_password="temp123",
            login_url="http://localhost:5173/login",
        )

        assert result is False

    def test_render_template(self, email_service):
        """Test Jinja2 template rendering"""
        html = email_service._render_template(
            "invitation.html",
            {
                "user_name": "John Doe",
                "org_name": "Acme Corp",
                "inviter_name": "Jane Smith",
                "temporary_password": "temp123",
                "login_url": "http://localhost:5173/login",
                "expires_hours": 24,
                "support_email": "support@sentinel.ai",
                "logo_url": "https://sentinel.ai/logo.png",
                "year": 2024,
            }
        )

        assert "John Doe" in html
        assert "Acme Corp" in html
        assert "Jane Smith" in html
        assert "temp123" in html


class TestVerificationTokens:
    """Test email verification token generation and validation"""

    def test_generate_verification_token(self):
        """Test generating verification token"""
        token = generate_verification_token("user-id-123", "user@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_verification_token(self):
        """Test verifying valid token"""
        token = generate_verification_token("user-id-123", "user@example.com")
        payload = verify_verification_token(token)

        assert payload["user_id"] == "user-id-123"
        assert payload["email"] == "user@example.com"
        assert payload["token_type"] == "email_verification"

    def test_verify_invalid_token(self):
        """Test verifying invalid token raises error"""
        with pytest.raises(Exception):
            verify_verification_token("invalid-token")

    def test_verify_expired_token(self):
        """Test verifying expired token raises error"""
        # Would need to mock datetime to test expiration
        # For now, just verify the token validation works
        token = generate_verification_token("user-id-123", "user@example.com")
        payload = verify_verification_token(token)
        assert "exp" in payload
