"""Add individual policy columns (pattern_value, action, severity, is_active)

Revision ID: add_policy_columns
Revises: 2f8a45c1b9e7
Create Date: 2026-01-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_policy_columns'
down_revision = '2f8a45c1b9e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to policies table
    op.add_column('policies', sa.Column('pattern_value', sa.String(1000), nullable=True, comment='Regex pattern or keyword'))
    op.add_column('policies', sa.Column('action', sa.String(50), nullable=True, comment='block, redact, flag'))
    op.add_column('policies', sa.Column('severity', sa.String(50), nullable=True, comment='low, medium, high, critical'))
    op.add_column('policies', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Is policy enabled'))
    op.add_column('policies', sa.Column('ab_test_config', postgresql.JSON(), nullable=True, comment='A/B test configuration'))
    op.add_column('policies', sa.Column('dsl_source', sa.Text(), nullable=True, comment='Raw DSL source code'))
    op.add_column('policies', sa.Column('compiled_ast', postgresql.JSON(), nullable=True, comment='Compiled AST from DSL'))
    op.add_column('policies', sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Reference to policy template'))
    
    # Make policy_config nullable (it's now optional)
    op.alter_column('policies', 'policy_config', existing_type=postgresql.JSON(), nullable=True)


def downgrade() -> None:
    # Revert changes
    op.alter_column('policies', 'policy_config', existing_type=postgresql.JSON(), nullable=False)
    op.drop_column('policies', 'template_id')
    op.drop_column('policies', 'compiled_ast')
    op.drop_column('policies', 'dsl_source')
    op.drop_column('policies', 'ab_test_config')
    op.drop_column('policies', 'is_active')
    op.drop_column('policies', 'severity')
    op.drop_column('policies', 'action')
    op.drop_column('policies', 'pattern_value')
