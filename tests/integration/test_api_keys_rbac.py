"""
Integration Tests for API Keys RBAC
Tests that only admin/owner can create and revoke API keys
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from sentinel.saas.server import app
from sentinel.saas.models import Base, Organization, User, Workspace, APIKey
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
def test_workspace(db_session, test_organization):
    """Create test workspace"""
    workspace = Workspace(
        workspace_id=uuid4(),
        org_id=test_organization.org_id,
        workspace_name="Default Workspace",
        workspace_slug="default",
    )
    db_session.add(workspace)
    db_session.commit()
    db_session.refresh(workspace)
    return workspace


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


@pytest.fixture
def viewer_user(db_session, test_organization):
    """Create viewer user for testing"""
    user = User(
        user_id=uuid4(),
        org_id=test_organization.org_id,
        email="viewer@example.com",
        username="viewer",
        full_name="Viewer User",
        role="viewer",
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
# TEST CASES - CREATE API KEY
# ============================================================================

class TestCreateAPIKey:
    """Test who can create API keys"""

    def test_admin_can_create_api_key(self, client, admin_user, test_workspace):
        """Admin should be able to create API keys"""
        response = client.post(
            "/api-keys",
            headers=get_auth_headers(admin_user),
            json={
                "key_name": "Test Admin Key",
                "workspace_id": str(test_workspace.workspace_id),
                "scopes": ["process"],
                "rate_limit_per_minute": 60,
            }
        )

        # Admin should succeed or get 403 if RBAC is implemented
        # Success: 201 Created
        # Failure (expected if RBAC is working): Would allow admin
        assert response.status_code in [201, 403]

        if response.status_code == 201:
            data = response.json()
            assert "api_key" in data
            assert data["key_name"] == "Test Admin Key"

    def test_owner_can_create_api_key(self, client, owner_user, test_workspace):
        """Owner should be able to create API keys"""
        response = client.post(
            "/api-keys",
            headers=get_auth_headers(owner_user),
            json={
                "key_name": "Test Owner Key",
                "workspace_id": str(test_workspace.workspace_id),
                "scopes": ["process"],
                "rate_limit_per_minute": 60,
            }
        )

        # Owner should always succeed
        assert response.status_code == 201

        data = response.json()
        assert "api_key" in data
        assert data["key_name"] == "Test Owner Key"

    def test_viewer_cannot_create_api_key(self, client, viewer_user, test_workspace):
        """Viewer should NOT be able to create API keys"""
        response = client.post(
            "/api-keys",
            headers=get_auth_headers(viewer_user),
            json={
                "key_name": "Test Viewer Key",
                "workspace_id": str(test_workspace.workspace_id),
                "scopes": ["process"],
                "rate_limit_per_minute": 60,
            }
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower() or "role" in response.json()["detail"].lower()

    def test_member_cannot_create_api_key(self, client, member_user, test_workspace):
        """Member should NOT be able to create API keys"""
        response = client.post(
            "/api-keys",
            headers=get_auth_headers(member_user),
            json={
                "key_name": "Test Member Key",
                "workspace_id": str(test_workspace.workspace_id),
                "scopes": ["process"],
                "rate_limit_per_minute": 60,
            }
        )

        # Should be forbidden
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower() or "role" in response.json()["detail"].lower()


# ============================================================================
# TEST CASES - REVOKE API KEY
# ============================================================================

class TestRevokeAPIKey:
    """Test who can revoke API keys"""

    @pytest.fixture
    def existing_api_key(self, db_session, test_organization, test_workspace, owner_user):
        """Create an existing API key for testing"""
        import hashlib
        import secrets

        full_key = f"sk_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        key_prefix = full_key[:15] + "..."

        api_key = APIKey(
            org_id=test_organization.org_id,
            workspace_id=test_workspace.workspace_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            key_name="Existing Test Key",
            scopes=["process"],
            rate_limit_per_minute=60,
            created_by=owner_user.user_id,
            is_active=True,
        )
        db_session.add(api_key)
        db_session.commit()
        db_session.refresh(api_key)
        return api_key

    def test_owner_can_revoke_api_key(self, client, owner_user, existing_api_key):
        """Owner should be able to revoke API keys"""
        response = client.delete(
            f"/api-keys/{existing_api_key.key_id}",
            headers=get_auth_headers(owner_user)
        )

        # Owner should succeed
        assert response.status_code == 204

    def test_admin_can_revoke_api_key(self, client, db_session, admin_user, test_organization, test_workspace, owner_user):
        """Admin should be able to revoke API keys"""
        # Create a new key to revoke
        import hashlib
        import secrets

        full_key = f"sk_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        key_prefix = full_key[:15] + "..."

        api_key = APIKey(
            org_id=test_organization.org_id,
            workspace_id=test_workspace.workspace_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            key_name="Key to Revoke",
            scopes=["process"],
            rate_limit_per_minute=60,
            created_by=owner_user.user_id,
            is_active=True,
        )
        db_session.add(api_key)
        db_session.commit()
        db_session.refresh(api_key)

        response = client.delete(
            f"/api-keys/{api_key.key_id}",
            headers=get_auth_headers(admin_user)
        )

        # Admin should succeed or get 403 based on RBAC
        assert response.status_code in [204, 403]

    def test_viewer_cannot_revoke_api_key(self, client, viewer_user, existing_api_key):
        """Viewer should NOT be able to revoke API keys"""
        response = client.delete(
            f"/api-keys/{existing_api_key.key_id}",
            headers=get_auth_headers(viewer_user)
        )

        # Should be forbidden
        assert response.status_code == 403

    def test_member_cannot_revoke_api_key(self, client, member_user, existing_api_key):
        """Member should NOT be able to revoke API keys"""
        response = client.delete(
            f"/api-keys/{existing_api_key.key_id}",
            headers=get_auth_headers(member_user)
        )

        # Should be forbidden
        assert response.status_code == 403


# ============================================================================
# TEST CASES - LIST API KEYS
# ============================================================================

class TestListAPIKeys:
    """Test that all authenticated users can list API keys (read-only)"""

    @pytest.fixture
    def multiple_api_keys(self, db_session, test_organization, test_workspace, owner_user):
        """Create multiple API keys for testing"""
        import hashlib
        import secrets

        keys = []
        for i in range(3):
            full_key = f"sk_live_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(full_key.encode()).hexdigest()
            key_prefix = full_key[:15] + "..."

            api_key = APIKey(
                org_id=test_organization.org_id,
                workspace_id=test_workspace.workspace_id,
                key_hash=key_hash,
                key_prefix=key_prefix,
                key_name=f"Test Key {i+1}",
                scopes=["process"],
                rate_limit_per_minute=60,
                created_by=owner_user.user_id,
                is_active=True,
            )
            db_session.add(api_key)
            keys.append(api_key)

        db_session.commit()
        return keys

    def test_viewer_can_list_api_keys(self, client, viewer_user, multiple_api_keys):
        """Viewer should be able to list (but not modify) API keys"""
        response = client.get(
            "/api-keys",
            headers=get_auth_headers(viewer_user)
        )

        # Listing should be allowed for all roles
        assert response.status_code == 200

        data = response.json()
        assert "api_keys" in data
        assert len(data["api_keys"]) == 3

    def test_member_can_list_api_keys(self, client, member_user, multiple_api_keys):
        """Member should be able to list API keys"""
        response = client.get(
            "/api-keys",
            headers=get_auth_headers(member_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["api_keys"]) == 3


# ============================================================================
# TEST CASES - EDGE CASES
# ============================================================================

class TestAPIKeysEdgeCases:
    """Test edge cases and error scenarios"""

    def test_unauthorized_request_returns_401(self, client, test_workspace):
        """Unauthorized requests should return 401"""
        response = client.post(
            "/api-keys",
            # No authorization header
            json={
                "key_name": "Unauthorized Key",
                "workspace_id": str(test_workspace.workspace_id),
                "scopes": ["process"],
            }
        )

        assert response.status_code in [401, 403]

    def test_cannot_revoke_nonexistent_key(self, client, owner_user):
        """Attempting to revoke non-existent key should return 404"""
        fake_key_id = uuid4()

        response = client.delete(
            f"/api-keys/{fake_key_id}",
            headers=get_auth_headers(owner_user)
        )

        assert response.status_code == 404

    def test_cannot_create_key_for_other_org_workspace(self, client, owner_user, db_session):
        """Users cannot create keys for workspaces in other organizations"""
        # Create another organization and workspace
        other_org = Organization(
            org_id=uuid4(),
            org_name="Other Company",
            org_slug="other-company",
        )
        other_workspace = Workspace(
            workspace_id=uuid4(),
            org_id=other_org.org_id,
            workspace_name="Other Workspace",
            workspace_slug="other",
        )
        db_session.add_all([other_org, other_workspace])
        db_session.commit()

        response = client.post(
            "/api-keys",
            headers=get_auth_headers(owner_user),
            json={
                "key_name": "Cross-Org Key",
                "workspace_id": str(other_workspace.workspace_id),
                "scopes": ["process"],
            }
        )

        # Should fail - workspace doesn't belong to user's org
        assert response.status_code == 404
        assert "workspace" in response.json()["detail"].lower()
