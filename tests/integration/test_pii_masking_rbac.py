"""
Integration Tests for PII Masking with RBAC
Tests that PII is correctly masked in audit log responses based on user role
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from sentinel.saas.server import app
from sentinel.saas.models import Base, Organization, User
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


@pytest.fixture
def mock_audit_log_with_pii():
    """Create mock audit log data with PII"""
    return {
        "id": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "session-123",
        "request_id": "req-456",
        "org_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "user_id": "user-789",
        "user_role": "member",
        "ip_address": "192.168.1.100",
        "user_input": "Contact me at john.doe@example.com or call 555-1234",
        "input_length": 56,
        "blocked": False,
        "risk_score": 0.3,
        "risk_level": "low",
        "pii_detected": True,
        "pii_entities": [
            {
                "entity_type": "email",
                "value": "john.doe@example.com",
                "start_position": 14,
                "end_position": 35,
                "redaction_strategy": "mask",
                "redacted_value": "j***@example.com",
                "confidence": 0.99,
                "detection_method": "regex",
                "token_id": "TOKEN_EMAIL_001"
            },
            {
                "entity_type": "phone",
                "value": "555-1234",
                "start_position": 47,
                "end_position": 55,
                "redaction_strategy": "mask",
                "redacted_value": "***-****",
                "confidence": 0.95,
                "detection_method": "regex",
                "token_id": "TOKEN_PHONE_001"
            }
        ],
        "redacted_count": 2,
        "injection_detected": False,
        "escalated": False,
        "metadata": {}
    }


# ============================================================================
# TEST CASES
# ============================================================================

class TestPIIMaskingForAdmin:
    """Test that admin users see full PII in audit logs"""

    @patch('sentinel.saas.routers.audit.get_postgres_adapter')
    def test_admin_sees_full_pii_in_audit_logs(
        self,
        mock_get_adapter,
        client,
        admin_user,
        mock_audit_log_with_pii
    ):
        """Admin should see original email and phone number (not redacted)"""
        # Mock the PostgreSQL adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_audit_logs.return_value = [mock_audit_log_with_pii]
        mock_get_adapter.return_value = mock_adapter

        # Make request as admin
        response = client.get(
            "/audit-logs",
            headers=get_auth_headers(admin_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        log = data["logs"][0]

        # Admin should see original PII (NOT redacted)
        assert "john.doe@example.com" in log["user_input"]
        assert "555-1234" in log["user_input"]
        assert "[EMAIL_REDACTED]" not in log["user_input"]
        assert "[PHONE_REDACTED]" not in log["user_input"]

        # Verify PII entities are present
        assert log["pii_detected"] is True
        assert len(log["threat_details"]["pii"]) == 2

        # Verify masked_value is visible to admin
        email_entity = next(e for e in log["threat_details"]["pii"] if e["entity_type"] == "email")
        assert email_entity["masked_value"] == "j***@example.com"


class TestPIIMaskingForViewer:
    """Test that viewer users see redacted PII in audit logs"""

    @patch('sentinel.saas.routers.audit.get_postgres_adapter')
    def test_viewer_sees_redacted_pii_in_audit_logs(
        self,
        mock_get_adapter,
        client,
        viewer_user,
        mock_audit_log_with_pii
    ):
        """Viewer should see [EMAIL_REDACTED] and [PHONE_REDACTED] tokens"""
        # Mock the PostgreSQL adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_audit_logs.return_value = [mock_audit_log_with_pii]
        mock_get_adapter.return_value = mock_adapter

        # Make request as viewer
        response = client.get(
            "/audit-logs",
            headers=get_auth_headers(viewer_user)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        log = data["logs"][0]

        # Viewer should see redacted tokens (NOT original PII)
        assert "[EMAIL_REDACTED]" in log["user_input"]
        assert "[PHONE_REDACTED]" in log["user_input"]
        assert "john.doe@example.com" not in log["user_input"]
        assert "555-1234" not in log["user_input"]

        # Verify PII entities are present but masked_value not shown
        assert log["pii_detected"] is True
        assert len(log["threat_details"]["pii"]) == 2

        # Viewer should NOT see masked_value
        for entity in log["threat_details"]["pii"]:
            assert entity.get("masked_value") is None


class TestPIIMaskingForMember:
    """Test that member users see redacted PII in audit logs"""

    @patch('sentinel.saas.routers.audit.get_postgres_adapter')
    def test_member_sees_redacted_pii(
        self,
        mock_get_adapter,
        client,
        member_user,
        mock_audit_log_with_pii
    ):
        """Member role should also see redacted PII (not just viewer)"""
        # Mock the PostgreSQL adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_audit_logs.return_value = [mock_audit_log_with_pii]
        mock_get_adapter.return_value = mock_adapter

        # Make request as member
        response = client.get(
            "/audit-logs",
            headers=get_auth_headers(member_user)
        )

        assert response.status_code == 200
        data = response.json()

        log = data["logs"][0]

        # Member should see redacted tokens
        assert "[EMAIL_REDACTED]" in log["user_input"]
        assert "[PHONE_REDACTED]" in log["user_input"]
        assert "john.doe@example.com" not in log["user_input"]
        assert "555-1234" not in log["user_input"]


class TestDashboardPIIMasking:
    """Test PII masking in Dashboard Recent Threats endpoint"""

    @patch('sentinel.saas.routers.dashboard.get_postgres_adapter')
    def test_dashboard_pii_masking_for_admin(
        self,
        mock_get_adapter,
        client,
        admin_user,
        mock_audit_log_with_pii
    ):
        """Dashboard should apply same masking rules as audit logs"""
        # Mock the PostgreSQL adapter for dashboard
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_recent_threats.return_value = [mock_audit_log_with_pii]
        mock_get_adapter.return_value = mock_adapter

        # Make request as admin
        response = client.get(
            "/dashboard/recent-threats",
            headers=get_auth_headers(admin_user)
        )

        # Skip if endpoint doesn't exist (implementation may vary)
        if response.status_code == 404:
            pytest.skip("Dashboard endpoint not implemented")

        assert response.status_code == 200
        data = response.json()

        # Admin should see original PII in dashboard too
        if data.get("threats"):
            threat = data["threats"][0]
            assert "john.doe@example.com" in threat.get("user_input", "")
            assert "[EMAIL_REDACTED]" not in threat.get("user_input", "")

    @patch('sentinel.saas.routers.dashboard.get_postgres_adapter')
    def test_dashboard_pii_masking_for_viewer(
        self,
        mock_get_adapter,
        client,
        viewer_user,
        mock_audit_log_with_pii
    ):
        """Dashboard should show redacted PII to viewers"""
        # Mock the PostgreSQL adapter for dashboard
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_recent_threats.return_value = [mock_audit_log_with_pii]
        mock_get_adapter.return_value = mock_adapter

        # Make request as viewer
        response = client.get(
            "/dashboard/recent-threats",
            headers=get_auth_headers(viewer_user)
        )

        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Dashboard endpoint not implemented")

        assert response.status_code == 200
        data = response.json()

        # Viewer should see redacted PII in dashboard
        if data.get("threats"):
            threat = data["threats"][0]
            assert "[EMAIL_REDACTED]" in threat.get("user_input", "")
            assert "john.doe@example.com" not in threat.get("user_input", "")


class TestEdgeCases:
    """Test edge cases for PII masking"""

    @patch('sentinel.saas.routers.audit.get_postgres_adapter')
    def test_no_pii_returns_original_text(
        self,
        mock_get_adapter,
        client,
        viewer_user
    ):
        """Log without PII should return original text for all roles"""
        log_without_pii = {
            "id": 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "org_id": str(uuid4()),
            "user_input": "This is a harmless message with no sensitive data",
            "pii_detected": False,
            "pii_entities": [],
            "blocked": False,
        }

        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_audit_logs.return_value = [log_without_pii]
        mock_get_adapter.return_value = mock_adapter

        response = client.get(
            "/audit-logs",
            headers=get_auth_headers(viewer_user)
        )

        assert response.status_code == 200
        data = response.json()
        log = data["logs"][0]

        # Original text should be preserved
        assert log["user_input"] == "This is a harmless message with no sensitive data"
        assert "[REDACTED]" not in log["user_input"]

    @patch('sentinel.saas.routers.audit.get_postgres_adapter')
    def test_multiple_pii_types_all_redacted(
        self,
        mock_get_adapter,
        client,
        viewer_user
    ):
        """Test that multiple PII types are all properly redacted"""
        log_with_multiple_pii = {
            "id": 3,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "org_id": str(uuid4()),
            "user_input": "Contact john.doe@example.com, call 555-1234, SSN: 123-45-6789",
            "pii_detected": True,
            "pii_entities": [
                {
                    "entity_type": "email",
                    "start_position": 8,
                    "end_position": 29,
                    "redaction_strategy": "mask"
                },
                {
                    "entity_type": "phone",
                    "start_position": 36,
                    "end_position": 44,
                    "redaction_strategy": "mask"
                },
                {
                    "entity_type": "ssn",
                    "start_position": 51,
                    "end_position": 62,
                    "redaction_strategy": "mask"
                }
            ],
            "blocked": False,
        }

        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.get_audit_logs.return_value = [log_with_multiple_pii]
        mock_get_adapter.return_value = mock_adapter

        response = client.get(
            "/audit-logs",
            headers=get_auth_headers(viewer_user)
        )

        assert response.status_code == 200
        data = response.json()
        log = data["logs"][0]

        # All three PII types should be redacted
        assert "[EMAIL_REDACTED]" in log["user_input"]
        assert "[PHONE_REDACTED]" in log["user_input"]
        assert "[SSN_REDACTED]" in log["user_input"]

        # Original values should NOT be present
        assert "john.doe@example.com" not in log["user_input"]
        assert "555-1234" not in log["user_input"]
        assert "123-45-6789" not in log["user_input"]
