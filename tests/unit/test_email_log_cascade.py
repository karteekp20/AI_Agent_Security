"""
Unit Tests for EmailLog Cascade Behavior
Tests foreign key cascade and deletion behavior for email logs
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime

from sentinel.saas.models import Base, Organization, User, EmailLog
from sentinel.saas.models.email_log import EmailStatus


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_organization(db_session):
    """Create sample organization for testing"""
    org = Organization(
        org_id=uuid4(),
        org_name="Test Organization",
        org_slug="test-org",
        subscription_tier="free",
        max_users=10,
        current_users=1,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def sample_user(db_session, sample_organization):
    """Create sample user for testing"""
    user = User(
        user_id=uuid4(),
        org_id=sample_organization.org_id,
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        role="member",
        is_active=True,
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# TEST CASES
# ============================================================================

class TestEmailLogCreation:
    """Test email log creation scenarios"""

    def test_email_log_creation_with_user(self, db_session, sample_organization, sample_user):
        """Test creating email log with valid user_id"""
        email_log = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=sample_user.user_id,
            template_name="invitation",
            to_email="recipient@example.com",
            subject="Welcome to Test Organization",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        db_session.add(email_log)
        db_session.commit()
        db_session.refresh(email_log)

        assert email_log.user_id == sample_user.user_id
        assert email_log.org_id == sample_organization.org_id
        assert email_log.template_name == "invitation"
        assert email_log.status == EmailStatus.SENT

    def test_email_log_creation_without_user(self, db_session, sample_organization):
        """Test creating email log with NULL user_id (system emails)"""
        email_log = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=None,  # System email, not tied to user
            template_name="system_alert",
            to_email="admin@example.com",
            subject="System Alert",
            status=EmailStatus.PENDING,
            provider="ses",
        )
        db_session.add(email_log)
        db_session.commit()
        db_session.refresh(email_log)

        assert email_log.user_id is None
        assert email_log.org_id == sample_organization.org_id
        assert email_log.template_name == "system_alert"


class TestUserDeletionCascade:
    """Test cascade behavior when users are deleted"""

    def test_user_deletion_sets_email_log_user_id_to_null(self, db_session, sample_organization, sample_user):
        """
        Test that deleting a user sets email_log.user_id to NULL

        This preserves the audit trail while marking that the user no longer exists.
        Email logs are compliance records and should not be deleted with users.
        """
        # Create email log for the user
        email_log = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=sample_user.user_id,
            template_name="verification",
            to_email=sample_user.email,
            subject="Verify your email",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        db_session.add(email_log)
        db_session.commit()

        email_log_id = email_log.email_log_id

        # Delete the user
        db_session.delete(sample_user)
        db_session.commit()

        # Verify email log still exists but user_id is NULL
        remaining_log = db_session.query(EmailLog).filter(
            EmailLog.email_log_id == email_log_id
        ).first()

        assert remaining_log is not None, "Email log should not be deleted"
        assert remaining_log.user_id is None, "user_id should be set to NULL"
        assert remaining_log.to_email == "user@example.com", "Email address preserved"
        assert remaining_log.template_name == "verification", "Template name preserved"

    def test_query_email_logs_after_user_deletion(self, db_session, sample_organization, sample_user):
        """Test that email logs can be queried after user is deleted"""
        # Create multiple email logs
        log_ids = []
        for i in range(3):
            email_log = EmailLog(
                email_log_id=uuid4(),
                org_id=sample_organization.org_id,
                user_id=sample_user.user_id,
                template_name=f"email_{i}",
                to_email=sample_user.email,
                subject=f"Test Email {i}",
                status=EmailStatus.SENT,
                provider="smtp",
            )
            db_session.add(email_log)
            log_ids.append(email_log.email_log_id)

        db_session.commit()

        # Delete user
        db_session.delete(sample_user)
        db_session.commit()

        # Query email logs by organization
        remaining_logs = db_session.query(EmailLog).filter(
            EmailLog.org_id == sample_organization.org_id
        ).all()

        assert len(remaining_logs) == 3, "All email logs should be preserved"
        for log in remaining_logs:
            assert log.user_id is None, "All user_ids should be NULL"
            assert log.email_log_id in log_ids, "Log IDs should match"


class TestOrganizationDeletionCascade:
    """Test cascade behavior when organizations are deleted"""

    def test_organization_deletion_cascades_to_email_logs(self, db_session, sample_organization, sample_user):
        """
        Test that deleting an organization CASCADE deletes all email logs

        This ensures complete tenant data removal for GDPR compliance.
        """
        # Create email logs
        email_log_1 = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=sample_user.user_id,
            template_name="invitation",
            to_email="user1@example.com",
            subject="Welcome",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        email_log_2 = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=None,  # System email
            template_name="system_alert",
            to_email="admin@example.com",
            subject="Alert",
            status=EmailStatus.SENT,
            provider="ses",
        )
        db_session.add_all([email_log_1, email_log_2])
        db_session.commit()

        # Delete organization (this should cascade to users and email_logs)
        db_session.delete(sample_organization)
        db_session.commit()

        # Verify all email logs are deleted
        remaining_logs = db_session.query(EmailLog).all()
        assert len(remaining_logs) == 0, "All email logs should be cascade deleted"

        # Verify user is also deleted (org -> user cascade)
        remaining_users = db_session.query(User).all()
        assert len(remaining_users) == 0, "Users should be cascade deleted with org"


class TestEmailLogRelationships:
    """Test relationships between EmailLog, User, and Organization"""

    def test_user_email_logs_relationship(self, db_session, sample_organization, sample_user):
        """Test accessing email logs through User relationship"""
        # Create email logs for user
        for i in range(2):
            email_log = EmailLog(
                email_log_id=uuid4(),
                org_id=sample_organization.org_id,
                user_id=sample_user.user_id,
                template_name=f"template_{i}",
                to_email=sample_user.email,
                subject=f"Subject {i}",
                status=EmailStatus.SENT,
                provider="smtp",
            )
            db_session.add(email_log)

        db_session.commit()
        db_session.refresh(sample_user)

        # Access through relationship
        assert len(sample_user.email_logs) == 2
        assert all(log.user_id == sample_user.user_id for log in sample_user.email_logs)

    def test_organization_email_logs_relationship(self, db_session, sample_organization, sample_user):
        """Test accessing email logs through Organization relationship"""
        # Create email logs for organization
        email_log_1 = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=sample_user.user_id,
            template_name="user_email",
            to_email="user@example.com",
            subject="User Email",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        email_log_2 = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=None,  # System email
            template_name="system_email",
            to_email="system@example.com",
            subject="System Email",
            status=EmailStatus.PENDING,
            provider="ses",
        )
        db_session.add_all([email_log_1, email_log_2])
        db_session.commit()
        db_session.refresh(sample_organization)

        # Access through relationship
        assert len(sample_organization.email_logs) == 2
        assert all(log.org_id == sample_organization.org_id for log in sample_organization.email_logs)


class TestMultipleDeletions:
    """Test complex deletion scenarios"""

    def test_multiple_users_with_email_logs(self, db_session, sample_organization):
        """Test deleting one user preserves other users' email logs"""
        # Create two users
        user1 = User(
            user_id=uuid4(),
            org_id=sample_organization.org_id,
            email="user1@example.com",
            role="member",
            is_active=True,
        )
        user2 = User(
            user_id=uuid4(),
            org_id=sample_organization.org_id,
            email="user2@example.com",
            role="member",
            is_active=True,
        )
        db_session.add_all([user1, user2])
        db_session.commit()

        # Create email logs for both users
        log1 = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=user1.user_id,
            template_name="email1",
            to_email=user1.email,
            subject="Email 1",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        log2 = EmailLog(
            email_log_id=uuid4(),
            org_id=sample_organization.org_id,
            user_id=user2.user_id,
            template_name="email2",
            to_email=user2.email,
            subject="Email 2",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        # Delete user1
        db_session.delete(user1)
        db_session.commit()

        # Verify user1's log has NULL user_id
        log1_after = db_session.query(EmailLog).filter(
            EmailLog.email_log_id == log1.email_log_id
        ).first()
        assert log1_after.user_id is None

        # Verify user2's log is unchanged
        log2_after = db_session.query(EmailLog).filter(
            EmailLog.email_log_id == log2.email_log_id
        ).first()
        assert log2_after.user_id == user2.user_id

        # Verify both logs still exist
        all_logs = db_session.query(EmailLog).all()
        assert len(all_logs) == 2
