"""Add password management fields to users table

Revision ID: 2f8a45c1b9e7
Revises: 1e937302beb3
Create Date: 2026-01-10 12:00:00.000000

This migration adds password management fields to the users table to support:
- Forced password changes on first login (temporary passwords)
- Password expiration tracking
- Password change history

New Fields:
- password_must_change: Boolean flag to force password change on next login
- password_changed_at: Timestamp of last password change
- password_expires_at: Timestamp when temporary password expires (typically 7 days)

Security Use Cases:
1. New user invitations with temporary passwords
2. Admin-initiated password resets
3. Password expiration policies
4. Compliance requirements for periodic password changes
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2f8a45c1b9e7'
down_revision: Union[str, None] = '1e937302beb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add password management fields to users table

    These fields enable secure temporary password flows and password expiration policies.
    """

    # Add password_must_change column
    op.add_column(
        'users',
        sa.Column(
            'password_must_change',
            sa.Boolean,
            nullable=False,
            server_default='false',
            comment='Force user to change password on next login (e.g., temp passwords)'
        )
    )

    # Add password_changed_at column
    op.add_column(
        'users',
        sa.Column(
            'password_changed_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last time user changed their password'
        )
    )

    # Add password_expires_at column
    op.add_column(
        'users',
        sa.Column(
            'password_expires_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When temporary password expires (typically 7 days)'
        )
    )

    # Create index on password_must_change for faster login queries
    op.create_index(
        'idx_users_password_must_change',
        'users',
        ['password_must_change'],
        unique=False
    )


def downgrade() -> None:
    """
    Remove password management fields from users table

    WARNING: This will delete password management metadata.
    Only use in development or when rolling back password management feature.
    """

    # Drop index
    op.drop_index('idx_users_password_must_change', table_name='users')

    # Drop columns
    op.drop_column('users', 'password_expires_at')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'password_must_change')
