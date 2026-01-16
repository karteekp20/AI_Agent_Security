"""Add email_logs table with Row-Level Security

Revision ID: 1e937302beb3
Revises: 46dcb1d07b70
Create Date: 2026-01-10 00:00:00.000000

This migration adds the email_logs table for tracking all emails sent by the system.
Includes proper foreign key constraints with CASCADE/SET NULL behaviors and RLS policies.

Foreign Key Behavior:
- org_id: ON DELETE CASCADE (delete all logs when organization is deleted)
- user_id: ON DELETE SET NULL (preserve logs when user is deleted, for audit trail)

Row-Level Security:
- Users can only see email logs for their organization
- Automatic tenant isolation at the database level
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1e937302beb3'
down_revision: Union[str, None] = '46dcb1d07b70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create email_logs table with RLS policies

    This table tracks all emails sent by the system for compliance and troubleshooting.
    """

    # =========================================================================
    # CREATE EMAIL_LOGS TABLE
    # =========================================================================

    op.create_table(
        'email_logs',

        # Primary key
        sa.Column('email_log_id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Multi-tenant foreign keys
        sa.Column(
            'org_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('organizations.org_id', ondelete='CASCADE'),
            nullable=False,
            index=True
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.user_id', ondelete='SET NULL'),
            nullable=True,
            index=True
        ),

        # Email details
        sa.Column('template_name', sa.String(100), nullable=False),
        sa.Column('to_email', sa.String(255), nullable=False, index=True),
        sa.Column('subject', sa.String(500), nullable=False),

        # Delivery tracking
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default='pending',
            index=True
        ),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('ses_message_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=sa.func.now(), index=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bounced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('complained_at', sa.DateTime(timezone=True), nullable=True),
    )

    # =========================================================================
    # ENABLE ROW-LEVEL SECURITY
    # =========================================================================

    # Enable RLS on email_logs table
    op.execute("ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY")

    # Policy: Users can only see email logs in their organization
    op.execute("""
        CREATE POLICY email_logs_isolation_policy ON email_logs
        USING (org_id::text = current_setting('app.current_org_id', TRUE))
    """)

    # Policy: Users can only insert email logs into their organization
    op.execute("""
        CREATE POLICY email_logs_insert_policy ON email_logs
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', TRUE))
    """)


def downgrade() -> None:
    """
    Remove email_logs table and RLS policies

    WARNING: This will delete all email log data.
    Only use in development or when removing email tracking functionality.
    """

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS email_logs_isolation_policy ON email_logs")
    op.execute("DROP POLICY IF EXISTS email_logs_insert_policy ON email_logs")

    # Disable RLS
    op.execute("ALTER TABLE email_logs DISABLE ROW LEVEL SECURITY")

    # Drop table
    op.drop_table('email_logs')
