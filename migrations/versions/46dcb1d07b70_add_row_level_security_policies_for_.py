"""Add Row-Level Security policies for multi-tenant isolation

Revision ID: 46dcb1d07b70
Revises: 900dc3026ec6
Create Date: 2025-12-27 22:23:20.572947

Row-Level Security (RLS) ensures that users can only access data belonging to their organization.
This is enforced at the database level, providing defense-in-depth security.

Usage:
Before executing queries, set the current organization ID:
    SET app.current_org_id = '<org_id>';

For application connections, set it once per session or transaction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46dcb1d07b70'
down_revision: Union[str, None] = '900dc3026ec6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enable Row-Level Security on all multi-tenant tables

    Creates policies that filter rows based on current_setting('app.current_org_id').
    This ensures automatic tenant isolation at the database level.
    """

    # =========================================================================
    # USERS TABLE - RLS
    # =========================================================================

    # Enable RLS
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # Policy: Users can only see users in their organization
    op.execute("""
        CREATE POLICY users_isolation_policy ON users
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # Policy: Users can only insert users into their organization
    op.execute("""
        CREATE POLICY users_insert_policy ON users
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # =========================================================================
    # WORKSPACES TABLE - RLS
    # =========================================================================

    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY workspaces_isolation_policy ON workspaces
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    op.execute("""
        CREATE POLICY workspaces_insert_policy ON workspaces
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # =========================================================================
    # API_KEYS TABLE - RLS
    # =========================================================================

    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY api_keys_isolation_policy ON api_keys
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    op.execute("""
        CREATE POLICY api_keys_insert_policy ON api_keys
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # =========================================================================
    # POLICIES TABLE - RLS
    # =========================================================================

    op.execute("ALTER TABLE policies ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY policies_isolation_policy ON policies
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    op.execute("""
        CREATE POLICY policies_insert_policy ON policies
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # =========================================================================
    # REPORTS TABLE - RLS
    # =========================================================================

    op.execute("ALTER TABLE reports ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY reports_isolation_policy ON reports
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    op.execute("""
        CREATE POLICY reports_insert_policy ON reports
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # =========================================================================
    # SUBSCRIPTIONS TABLE - RLS
    # =========================================================================

    op.execute("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY subscriptions_isolation_policy ON subscriptions
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    op.execute("""
        CREATE POLICY subscriptions_insert_policy ON subscriptions
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # =========================================================================
    # ORGANIZATIONS TABLE - Special Case
    # =========================================================================

    # Organizations table has different RLS:
    # Users can only see their own organization
    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY organizations_isolation_policy ON organizations
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # Note: INSERT policy is not needed for organizations as they are created
    # during registration before org_id is set in session

    # =========================================================================
    # CREATE HELPER FUNCTION
    # =========================================================================

    # Function to set organization context for a session
    op.execute("""
        CREATE OR REPLACE FUNCTION set_org_context(p_org_id UUID)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_org_id', p_org_id::text, FALSE);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # Function to clear organization context
    op.execute("""
        CREATE OR REPLACE FUNCTION clear_org_context()
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_org_id', '', FALSE);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)


def downgrade() -> None:
    """
    Remove Row-Level Security policies

    WARNING: This removes tenant isolation at the database level.
    Only use in development or when migrating away from RLS.
    """

    # Drop helper functions
    op.execute("DROP FUNCTION IF EXISTS set_org_context(UUID)")
    op.execute("DROP FUNCTION IF EXISTS clear_org_context()")

    # Drop all policies and disable RLS
    tables = ['users', 'workspaces', 'api_keys', 'policies', 'reports', 'subscriptions', 'organizations']

    for table in tables:
        # Drop SELECT policies
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table}")

        # Drop INSERT policies
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON {table}")

        # Disable RLS
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
