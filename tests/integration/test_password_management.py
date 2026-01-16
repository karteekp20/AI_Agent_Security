"""
Integration Tests for Password Management
Tests password change flows, temp password handling, and forced password changes
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime, timedelta

from sentinel.saas.server import app
from sentinel.saas.models import Base, Organization, User
from sentinel.saas.dependencies import get_db
from sentinel.saas.auth.jwt import create_access_token
from sentinel.saas.auth.password import hash_password, verify_password


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
def normal_user(db_session, test_organization):
    """Create normal user with no password change required"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="normal@example.com",
        username="normal",
        full_name="Normal User",
        role="member",
        password_hash=hash_password("SecurePass123!"),
        password_must_change=False,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    test_organization.current_users += 1
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def temp_password_user(db_session, test_organization):
    """Create user with temporary password that must be changed"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="temppass@example.com",
        username="temppass",
        full_name="Temp Password User",
        role="member",
        password_hash=hash_password("TempPass123!"),
        password_must_change=True,
        password_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    test_organization.current_users += 1
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def expired_password_user(db_session, test_organization):
    """Create user with expired temporary password"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="expired@example.com",
        username="expired",
        full_name="Expired Password User",
        role="member",
        password_hash=hash_password("ExpiredPass123!"),
        password_must_change=True,
        password_expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
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
# TEST CASES - CHANGE PASSWORD ENDPOINT
# ============================================================================

class TestChangePasswordEndpoint:
    """Test the /auth/change-password endpoint"""

    def test_user_changes_password_successfully(self, client, db_session, normal_user):
        """User should be able to change their password"""
        response = client.post(
            "/auth/change-password",
            headers=get_auth_headers(normal_user),
            json={
                "current_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "success" in data["message"].lower()

        # Verify password was changed in database
        db_session.refresh(normal_user)
        assert verify_password("NewSecurePass456!", normal_user.password_hash)
        assert not verify_password("SecurePass123!", normal_user.password_hash)

        # Verify password_changed_at was set
        assert normal_user.password_changed_at is not None

    def test_cannot_login_with_old_password(self, client, db_session, normal_user):
        """After password change, old password should not work"""
        # Change password
        client.post(
            "/auth/change-password",
            headers=get_auth_headers(normal_user),
            json={
                "current_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        # Try to login with old password
        response = client.post(
            "/auth/login",
            json={
                "email": "normal@example.com",
                "password": "SecurePass123!",  # Old password
            }
        )

        assert response.status_code == 401

    def test_can_login_with_new_password(self, client, db_session, normal_user):
        """After password change, new password should work"""
        # Change password
        client.post(
            "/auth/change-password",
            headers=get_auth_headers(normal_user),
            json={
                "current_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        # Try to login with new password
        response = client.post(
            "/auth/login",
            json={
                "email": "normal@example.com",
                "password": "NewSecurePass456!",  # New password
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_incorrect_current_password_fails(self, client, normal_user):
        """Change password should fail if current password is wrong"""
        response = client.post(
            "/auth/change-password",
            headers=get_auth_headers(normal_user),
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_new_password_cannot_be_same_as_current(self, client, normal_user):
        """New password must be different from current password"""
        response = client.post(
            "/auth/change-password",
            headers=get_auth_headers(normal_user),
            json={
                "current_password": "SecurePass123!",
                "new_password": "SecurePass123!",  # Same as current
                "confirm_password": "SecurePass123!",
            }
        )

        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()


# ============================================================================
# TEST CASES - FORCED PASSWORD CHANGE ON LOGIN
# ============================================================================

class TestForcedPasswordChange:
    """Test forced password change flow for users with temp passwords"""

    def test_temp_password_forces_change_on_login(self, client, temp_password_user):
        """Login with temp password should return password_change_required=true"""
        response = client.post(
            "/auth/login",
            json={
                "email": "temppass@example.com",
                "password": "TempPass123!",
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should have access token but with password_change_required flag
        assert "access_token" in data
        assert data["password_change_required"] is True

    def test_password_must_change_flag_cleared_after_change(
        self,
        client,
        db_session,
        temp_password_user
    ):
        """password_must_change flag should be cleared after changing password"""
        # Verify flag is set initially
        assert temp_password_user.password_must_change is True

        # Change password
        response = client.post(
            "/auth/change-password",
            headers=get_auth_headers(temp_password_user),
            json={
                "current_password": "TempPass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        assert response.status_code == 200

        # Verify flag is cleared
        db_session.refresh(temp_password_user)
        assert temp_password_user.password_must_change is False
        assert temp_password_user.password_expires_at is None

    def test_subsequent_login_does_not_require_password_change(
        self,
        client,
        db_session,
        temp_password_user
    ):
        """After changing password, subsequent logins should not require change"""
        # Change password
        client.post(
            "/auth/change-password",
            headers=get_auth_headers(temp_password_user),
            json={
                "current_password": "TempPass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        # Login again with new password
        response = client.post(
            "/auth/login",
            json={
                "email": "temppass@example.com",
                "password": "NewSecurePass456!",
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should NOT require password change anymore
        assert data.get("password_change_required") is False


# ============================================================================
# TEST CASES - TEMP PASSWORD EXPIRATION
# ============================================================================

class TestTempPasswordExpiration:
    """Test temporary password expiration"""

    def test_expired_temp_password_requires_change(self, client, expired_password_user):
        """Login with expired temp password should require password change"""
        response = client.post(
            "/auth/login",
            json={
                "email": "expired@example.com",
                "password": "ExpiredPass123!",
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should indicate password change is required
        assert data["password_change_required"] is True


# ============================================================================
# TEST CASES - USER INVITATION SETS TEMP PASSWORD FLAG
# ============================================================================

class TestUserInvitation:
    """Test that user invitation sets temporary password flags"""

    @pytest.fixture
    def owner_user(self, db_session, test_organization):
        """Create owner user who can invite others"""
        user = User(
            user_id=uuid4(),
            org_id=test_organization.org_id,
            email="owner@example.com",
            username="owner",
            full_name="Owner User",
            role="owner",
            password_hash=hash_password("OwnerPass123!"),
            is_active=True,
            email_verified=True,
        )
        db_session.add(user)
        test_organization.current_users += 1
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_user_invitation_sets_temp_password_flag(
        self,
        client,
        db_session,
        owner_user,
        test_organization
    ):
        """Inviting a user should set password_must_change=True"""
        response = client.post(
            "/orgs/me/users",
            headers=get_auth_headers(owner_user),
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "role": "member",
            }
        )

        # Should create user successfully
        assert response.status_code in [200, 201]

        # Find the newly created user
        new_user = db_session.query(User).filter(
            User.email == "newuser@example.com"
        ).first()

        assert new_user is not None
        assert new_user.password_must_change is True
        assert new_user.password_expires_at is not None

        # Verify expiration is ~7 days from now
        time_diff = new_user.password_expires_at - datetime.utcnow()
        assert 6.9 <= time_diff.days <= 7.1  # Allow small variance

    def test_invited_user_forced_to_change_password(
        self,
        client,
        db_session,
        owner_user
    ):
        """Invited user should be forced to change password on first login"""
        # Invite user
        response = client.post(
            "/orgs/me/users",
            headers=get_auth_headers(owner_user),
            json={
                "email": "invited@example.com",
                "full_name": "Invited User",
                "role": "member",
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()

        # Get temp password from response
        temp_password = data.get("temporary_password")
        if not temp_password:
            # If temp password not in response, skip this test
            pytest.skip("Temporary password not returned in invitation response")

        # Try to login with temp password
        login_response = client.post(
            "/auth/login",
            json={
                "email": "invited@example.com",
                "password": temp_password,
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.json()

        # Should require password change
        assert login_data["password_change_required"] is True


# ============================================================================
# TEST CASES - EDGE CASES
# ============================================================================

class TestPasswordEdgeCases:
    """Test edge cases and error scenarios"""

    def test_unauthenticated_cannot_change_password(self, client):
        """Unauthenticated requests should be rejected"""
        response = client.post(
            "/auth/change-password",
            # No authentication header
            json={
                "current_password": "OldPass123!",
                "new_password": "NewPass456!",
                "confirm_password": "NewPass456!",
            }
        )

        assert response.status_code in [401, 403]

    def test_password_changed_at_timestamp_updated(self, client, db_session, normal_user):
        """password_changed_at should be updated to current time"""
        # Record time before change
        time_before = datetime.utcnow()

        # Change password
        response = client.post(
            "/auth/change-password",
            headers=get_auth_headers(normal_user),
            json={
                "current_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!",
            }
        )

        assert response.status_code == 200

        # Verify timestamp was updated
        db_session.refresh(normal_user)
        assert normal_user.password_changed_at is not None
        assert normal_user.password_changed_at >= time_before

        # Verify it's recent (within 5 seconds)
        time_diff = datetime.utcnow() - normal_user.password_changed_at
        assert time_diff.total_seconds() < 5
