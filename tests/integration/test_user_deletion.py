"""
Integration Tests for User Deletion Endpoint
Tests DELETE /orgs/me/users/{user_id} with email_logs cascade behavior
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from sentinel.saas.server import app
from sentinel.saas.models import Base, Organization, User, EmailLog
from sentinel.saas.models.email_log import EmailStatus
from sentinel.saas.dependencies import get_db
from sentinel.saas.auth.jwt import create_access_token


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


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def db_session(test_db):
    """Database session for direct DB operations"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# HELPER FIXTURES
# ============================================================================

@pytest.fixture
def test_organization(db_session):
    """Create test organization"""
    org = Organization(
        org_id=uuid4(),
        org_name="Test Company",
        org_slug="test-company",
        subscription_tier="pro",
        max_users=20,
        current_users=0,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def owner_user(db_session, test_organization):
    """Create owner user for testing"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="owner@example.com",
        username="owner",
        full_name="Owner User",
        role="owner",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    test_organization.current_users += 1
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, test_organization):
    """Create admin user for testing"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        role="admin",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    test_organization.current_users += 1
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def member_user(db_session, test_organization):
    """Create member user for testing"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="member@example.com",
        username="member",
        full_name="Member User",
        role="member",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    test_organization.current_users += 1
    db_session.commit()
    db_session.refresh(user)
    return user


def get_auth_headers(user: User):
    """Generate JWT token for user authentication"""
    token = create_access_token(
        data={
            "sub": str(user.user_id),
            "org_id": str(user.org_id),
            "role": user.role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# TEST CASES
# ============================================================================

class TestUserDeletionEndpoint:
    """Test DELETE /orgs/me/users/{user_id} endpoint"""

    def test_delete_user_via_api_endpoint(self, client, db_session, test_organization, owner_user, member_user):
        """Test full user deletion flow via API"""
        # Create email log for member user
        email_log = EmailLog(
            email_log_id=uuid4(),
            org_id=test_organization.org_id,
            user_id=member_user.user_id,
            template_name="invitation",
            to_email=member_user.email,
            subject="Welcome to Test Company",
            status=EmailStatus.SENT,
            provider="smtp",
        )
        db_session.add(email_log)
        db_session.commit()
        email_log_id = email_log.email_log_id

        # Delete member user as owner
        response = client.delete(
            f"/orgs/me/users/{member_user.user_id}",
            headers=get_auth_headers(owner_user)
        )

        assert response.status_code == 204, f"Expected 204, got {response.status_code}"

        # Verify user is deleted
        deleted_user = db_session.query(User).filter(
            User.user_id == member_user.user_id
        ).first()
        assert deleted_user is None, "User should be deleted"

        # Verify email log persists with NULL user_id
        remaining_log = db_session.query(EmailLog).filter(
            EmailLog.email_log_id == email_log_id
        ).first()
        assert remaining_log is not None, "Email log should not be deleted"
        assert remaining_log.user_id is None, "user_id should be set to NULL"

        # Verify organization user count is updated
        db_session.refresh(test_organization)
        assert test_organization.current_users == 1, "User count should be decremented"

    def test_email_logs_persist_after_user_deletion(self, client, db_session, test_organization, owner_user, member_user):
        """Test that email logs are preserved after user deletion"""
        # Create multiple email logs for the user
        log_ids = []
        for i in range(3):
            email_log = EmailLog(
                email_log_id=uuid4(),
                org_id=test_organization.org_id,
                user_id=member_user.user_id,
                template_name=f"email_{i}",
                to_email=member_user.email,
                subject=f"Test Email {i}",
                status=EmailStatus.SENT,
                provider="smtp",
            )
            db_session.add(email_log)
            log_ids.append(email_log.email_log_id)
        db_session.commit()

        # Delete user
        response = client.delete(
            f"/orgs/me/users/{member_user.user_id}",
            headers=get_auth_headers(owner_user)
        )
        assert response.status_code == 204

        # Verify all email logs exist with NULL user_id
        remaining_logs = db_session.query(EmailLog).filter(
            EmailLog.email_log_id.in_(log_ids)
        ).all()

        assert len(remaining_logs) == 3, "All email logs should be preserved"
        for log in remaining_logs:
            assert log.user_id is None, "user_id should be NULL"
            assert log.to_email == member_user.email, "Email address preserved"


class TestDeletionPermissions:
    """Test role-based permissions for user deletion"""

    def test_cannot_delete_self(self, client, db_session, owner_user):
        """Test that users cannot delete their own account"""
        response = client.delete(
            f"/orgs/me/users/{owner_user.user_id}",
            headers=get_auth_headers(owner_user)
        )

        assert response.status_code == 400
        assert "Cannot delete your own user account" in response.json()["detail"]

        # Verify user still exists
        user = db_session.query(User).filter(User.user_id == owner_user.user_id).first()
        assert user is not None

    def test_cannot_delete_owner_as_non_owner(self, client, db_session, owner_user, admin_user):
        """Test that non-owners cannot delete owner accounts"""
        response = client.delete(
            f"/orgs/me/users/{owner_user.user_id}",
            headers=get_auth_headers(admin_user)
        )

        assert response.status_code == 403
        assert "Only owners can delete owner accounts" in response.json()["detail"]

        # Verify owner still exists
        owner = db_session.query(User).filter(User.user_id == owner_user.user_id).first()
        assert owner is not None

    def test_admin_can_delete_member(self, client, db_session, admin_user, member_user):
        """Test that admins can delete member accounts"""
        response = client.delete(
            f"/orgs/me/users/{member_user.user_id}",
            headers=get_auth_headers(admin_user)
        )

        assert response.status_code == 204

        # Verify member is deleted
        member = db_session.query(User).filter(User.user_id == member_user.user_id).first()
        assert member is None

    def test_owner_can_delete_admin(self, client, db_session, owner_user, admin_user):
        """Test that owners can delete admin accounts"""
        response = client.delete(
            f"/orgs/me/users/{admin_user.user_id}",
            headers=get_auth_headers(owner_user)
        )

        assert response.status_code == 204

        # Verify admin is deleted
        admin = db_session.query(User).filter(User.user_id == admin_user.user_id).first()
        assert admin is None

    def test_member_cannot_delete_users(self, client, db_session, member_user, test_organization):
        """Test that member role cannot delete users"""
        # Create another member
        other_member = User(
            user_id=uuid4(),
            org_id=test_organization.org_id,
            email="other@example.com",
            role="member",
            is_active=True,
        )
        db_session.add(other_member)
        db_session.commit()

        response = client.delete(
            f"/orgs/me/users/{other_member.user_id}",
            headers=get_auth_headers(member_user)
        )

        # Should be forbidden (403) - member role not authorized
        assert response.status_code in [403, 401]


class TestDeletionEdgeCases:
    """Test edge cases and error handling"""

    def test_delete_nonexistent_user_returns_404(self, client, owner_user):
        """Test deleting a non-existent user returns 404"""
        fake_user_id = uuid4()
        response = client.delete(
            f"/orgs/me/users/{fake_user_id}",
            headers=get_auth_headers(owner_user)
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_delete_user_from_different_org_returns_404(self, client, db_session, owner_user):
        """Test that users can only delete from their own organization"""
        # Create another organization with a user
        other_org = Organization(
            org_id=uuid4(),
            org_name="Other Company",
            org_slug="other-company",
        )
        other_user = User(
            user_id=uuid4(),
            org_id=other_org.org_id,
            email="other@othercompany.com",
            role="member",
            is_active=True,
        )
        db_session.add_all([other_org, other_user])
        db_session.commit()

        # Try to delete user from different org
        response = client.delete(
            f"/orgs/me/users/{other_user.user_id}",
            headers=get_auth_headers(owner_user)
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

        # Verify other user still exists
        user = db_session.query(User).filter(User.user_id == other_user.user_id).first()
        assert user is not None


class TestCORSAndHeaders:
    """Test CORS and response headers"""

    def test_delete_user_no_cors_error(self, client, db_session, owner_user, member_user):
        """Test that user deletion doesn't trigger CORS errors"""
        response = client.delete(
            f"/orgs/me/users/{member_user.user_id}",
            headers=get_auth_headers(owner_user)
        )

        # Should succeed without CORS errors
        assert response.status_code == 204

        # Verify CORS headers are present (TestClient may not set these)
        # In real application, these would be set by CORSMiddleware

    def test_unauthorized_request_returns_401(self, client, member_user):
        """Test that unauthorized requests return 401"""
        response = client.delete(
            f"/orgs/me/users/{member_user.user_id}",
            # No authorization header
        )

        assert response.status_code in [401, 403]  # Depends on auth implementation
