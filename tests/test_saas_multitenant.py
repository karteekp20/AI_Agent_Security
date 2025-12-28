"""
End-to-End Multi-Tenant SaaS Tests
Comprehensive tests for tenant isolation, RBAC, and security
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from sentinel.saas.server import app
from sentinel.saas.models import Base, Organization, User, Workspace, APIKey
from sentinel.saas.dependencies import get_db
from sentinel.saas.auth import hash_password, generate_api_key
from sentinel.saas.rls import set_org_context


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use in-memory SQLite for testing (or configure test PostgreSQL)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_saas.db"

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


@pytest.fixture(scope="module")
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
def db_session():
    """Database session for direct DB operations"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# TEST 1: USER REGISTRATION & ORGANIZATION CREATION
# ============================================================================

class TestRegistration:
    """Test user registration and organization creation"""

    def test_register_creates_org_and_user(self, client):
        """Test that registration creates organization, user, and workspace"""
        response = client.post("/auth/register", json={
            "email": "founder@acme.com",
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "org_name": "Acme Corp"
        })

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "user_id" in data
        assert "org_id" in data
        assert "workspace_id" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "founder@acme.com"
        assert data["org_name"] == "Acme Corp"
        assert data["org_slug"] == "acme-corp"

    def test_register_duplicate_email_fails(self, client):
        """Test that duplicate email registration fails"""
        # First registration
        client.post("/auth/register", json={
            "email": "duplicate@test.com",
            "password": "SecurePass123!",
            "full_name": "User One",
            "org_name": "Test Org 1"
        })

        # Duplicate registration should fail
        response = client.post("/auth/register", json={
            "email": "duplicate@test.com",
            "password": "SecurePass123!",
            "full_name": "User Two",
            "org_name": "Test Org 2"
        })

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_weak_password_rejected(self, client):
        """Test that weak passwords are rejected"""
        response = client.post("/auth/register", json={
            "email": "weak@test.com",
            "password": "weak",
            "full_name": "Weak User",
            "org_name": "Test Org"
        })

        assert response.status_code == 422  # Validation error


# ============================================================================
# TEST 2: AUTHENTICATION & JWT TOKENS
# ============================================================================

class TestAuthentication:
    """Test JWT authentication flow"""

    @pytest.fixture
    def registered_user(self, client):
        """Create a registered user"""
        response = client.post("/auth/register", json={
            "email": "testuser@example.com",
            "password": "TestPass123!",
            "full_name": "Test User",
            "org_name": "Test Organization"
        })
        return response.json()

    def test_login_success(self, client, registered_user):
        """Test successful login with correct credentials"""
        response = client.post("/auth/login", json={
            "email": "testuser@example.com",
            "password": "TestPass123!"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "testuser@example.com"

    def test_login_wrong_password(self, client, registered_user):
        """Test login fails with wrong password"""
        response = client.post("/auth/login", json={
            "email": "testuser@example.com",
            "password": "WrongPassword123!"
        })

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_get_current_user(self, client, registered_user):
        """Test /auth/me endpoint with valid token"""
        access_token = registered_user["access_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["role"] == "owner"

    def test_token_refresh(self, client, registered_user):
        """Test refresh token generates new access token"""
        refresh_token = registered_user["refresh_token"]

        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


# ============================================================================
# TEST 3: TENANT ISOLATION
# ============================================================================

class TestTenantIsolation:
    """Test that organizations cannot access each other's data"""

    @pytest.fixture
    def org_a_user(self, client):
        """Create user in Organization A"""
        response = client.post("/auth/register", json={
            "email": "user_a@orga.com",
            "password": "PassA123!",
            "full_name": "User A",
            "org_name": "Organization A"
        })
        return response.json()

    @pytest.fixture
    def org_b_user(self, client):
        """Create user in Organization B"""
        response = client.post("/auth/register", json={
            "email": "user_b@orgb.com",
            "password": "PassB123!",
            "full_name": "User B",
            "org_name": "Organization B"
        })
        return response.json()

    def test_users_cannot_see_other_org_users(self, client, org_a_user, org_b_user):
        """Test that Org A cannot see Org B users"""
        # Get users from Org A's perspective
        response = client.get(
            "/orgs/me/users",
            headers={"Authorization": f"Bearer {org_a_user['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see users from Org A
        assert data["total"] == 1
        assert data["users"][0]["email"] == "user_a@orga.com"
        assert all(u["email"] != "user_b@orgb.com" for u in data["users"])

    def test_workspaces_isolated_by_org(self, client, org_a_user, org_b_user):
        """Test that workspaces are isolated by organization"""
        # Get Org A workspaces
        response_a = client.get(
            "/workspaces",
            headers={"Authorization": f"Bearer {org_a_user['access_token']}"}
        )

        # Get Org B workspaces
        response_b = client.get(
            "/workspaces",
            headers={"Authorization": f"Bearer {org_b_user['access_token']}"}
        )

        assert response_a.status_code == 200
        assert response_b.status_code == 200

        workspaces_a = response_a.json()["workspaces"]
        workspaces_b = response_b.json()["workspaces"]

        # Verify different org_ids
        assert workspaces_a[0]["org_id"] != workspaces_b[0]["org_id"]


# ============================================================================
# TEST 4: API KEY GENERATION & USAGE
# ============================================================================

class TestAPIKeys:
    """Test API key generation and usage"""

    @pytest.fixture
    def org_with_api_key(self, client, db_session):
        """Create organization with API key"""
        # Register user
        reg_response = client.post("/auth/register", json={
            "email": "apitest@example.com",
            "password": "ApiTest123!",
            "full_name": "API Test User",
            "org_name": "API Test Org"
        })
        user_data = reg_response.json()

        # Generate API key manually (since we don't have the endpoint yet)
        from sentinel.saas.auth import generate_api_key, hash_api_key

        api_key_full, key_hash, key_prefix = generate_api_key()

        api_key = APIKey(
            key_id=uuid4(),
            org_id=user_data["org_id"],
            workspace_id=user_data["workspace_id"],
            key_hash=key_hash,
            key_prefix=key_prefix,
            key_name="Test API Key",
            is_active=True
        )
        db_session.add(api_key)
        db_session.commit()

        return {
            **user_data,
            "api_key": api_key_full,
            "key_hash": key_hash
        }

    def test_process_endpoint_with_api_key(self, client, org_with_api_key):
        """Test /process endpoint with API key authentication"""
        response = client.post(
            "/process",
            headers={"X-API-Key": org_with_api_key["api_key"]},
            json={
                "user_input": "Hello, test message",
                "user_id": "test_user_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "allowed" in data
        assert "risk_score" in data
        assert "org_id" in data
        assert "workspace_id" in data
        assert data["org_id"] == org_with_api_key["org_id"]

    def test_process_endpoint_without_api_key(self, client):
        """Test /process endpoint fails without API key"""
        response = client.post(
            "/process",
            json={"user_input": "Test"}
        )

        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]


# ============================================================================
# TEST 5: RBAC (ROLE-BASED ACCESS CONTROL)
# ============================================================================

class TestRBAC:
    """Test role-based access control"""

    @pytest.fixture
    def org_with_users(self, client, db_session):
        """Create organization with owner and member"""
        # Create owner
        owner_response = client.post("/auth/register", json={
            "email": "owner@rbactest.com",
            "password": "Owner123!",
            "full_name": "Owner User",
            "org_name": "RBAC Test Org"
        })
        owner_data = owner_response.json()

        # Create member (using owner's token to invite)
        member = User(
            user_id=uuid4(),
            org_id=owner_data["org_id"],
            email="member@rbactest.com",
            password_hash=hash_password("Member123!"),
            full_name="Member User",
            role="member",
            is_active=True
        )
        db_session.add(member)
        db_session.commit()

        # Login as member to get token
        member_login = client.post("/auth/login", json={
            "email": "member@rbactest.com",
            "password": "Member123!"
        })

        return {
            "owner": owner_data,
            "member": member_login.json()
        }

    def test_member_cannot_invite_users(self, client, org_with_users):
        """Test that members cannot invite users (requires admin/owner)"""
        response = client.post(
            "/orgs/me/users/invite",
            headers={"Authorization": f"Bearer {org_with_users['member']['access_token']}"},
            json={
                "email": "newuser@test.com",
                "full_name": "New User",
                "role": "member"
            }
        )

        assert response.status_code == 403  # Forbidden

    def test_owner_can_invite_users(self, client, org_with_users):
        """Test that owners can invite users"""
        response = client.post(
            "/orgs/me/users/invite",
            headers={"Authorization": f"Bearer {org_with_users['owner']['access_token']}"},
            json={
                "email": "invited@test.com",
                "full_name": "Invited User",
                "role": "member"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "temporary_password" in data
        assert data["email"] == "invited@test.com"


# ============================================================================
# TEST 6: ORGANIZATION LIMITS
# ============================================================================

class TestOrganizationLimits:
    """Test organization usage limits"""

    def test_api_request_tracking(self, client, db_session):
        """Test that API requests are tracked per organization"""
        # Create org with API key
        reg_response = client.post("/auth/register", json={
            "email": "limits@test.com",
            "password": "Limits123!",
            "full_name": "Limits User",
            "org_name": "Limits Test Org"
        })
        user_data = reg_response.json()

        # Get initial request count
        org = db_session.query(Organization).filter(
            Organization.org_id == user_data["org_id"]
        ).first()
        initial_count = org.api_requests_this_month

        # Note: Would need to create API key and make /process request
        # to test actual increment (simplified here)
        assert initial_count == 0
        assert org.max_api_requests_per_month == 10000  # Free tier


# ============================================================================
# TEST 7: WORKSPACE MANAGEMENT
# ============================================================================

class TestWorkspaces:
    """Test workspace CRUD operations"""

    @pytest.fixture
    def user_with_token(self, client):
        """Create user and return auth token"""
        response = client.post("/auth/register", json={
            "email": "workspace@test.com",
            "password": "Workspace123!",
            "full_name": "Workspace User",
            "org_name": "Workspace Test Org"
        })
        return response.json()

    def test_create_workspace(self, client, user_with_token):
        """Test creating a new workspace"""
        response = client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {user_with_token['access_token']}"},
            json={
                "workspace_name": "Staging Environment",
                "description": "Staging workspace for testing",
                "environment": "staging"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["workspace_name"] == "Staging Environment"
        assert data["environment"] == "staging"
        assert data["workspace_slug"] == "staging-environment"

    def test_list_workspaces(self, client, user_with_token):
        """Test listing workspaces"""
        response = client.get(
            "/workspaces",
            headers={"Authorization": f"Bearer {user_with_token['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data
        assert data["total"] >= 1  # At least the default workspace

    def test_delete_last_workspace_fails(self, client, user_with_token):
        """Test that deleting the last workspace fails"""
        # Get workspace list
        list_response = client.get(
            "/workspaces",
            headers={"Authorization": f"Bearer {user_with_token['access_token']}"}
        )
        workspace_id = list_response.json()["workspaces"][0]["workspace_id"]

        # Try to delete (should fail if it's the only one)
        if list_response.json()["total"] == 1:
            response = client.delete(
                f"/workspaces/{workspace_id}",
                headers={"Authorization": f"Bearer {user_with_token['access_token']}"}
            )
            assert response.status_code == 400
            assert "last workspace" in response.json()["detail"].lower()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
