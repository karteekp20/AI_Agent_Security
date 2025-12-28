"""Create multi-tenant schema with 8 core tables

Revision ID: 900dc3026ec6
Revises:
Create Date: 2025-12-27 22:01:26.313790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '900dc3026ec6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('org_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_name', sa.String(255), nullable=False),
        sa.Column('org_slug', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('subscription_tier', sa.String(50), default='free', comment='free, starter, pro, enterprise'),
        sa.Column('subscription_status', sa.String(50), default='active', comment='active, suspended, cancelled, trialing'),
        sa.Column('subscription_started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('billing_email', sa.String(255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True, index=True),
        sa.Column('max_users', sa.Integer, default=5),
        sa.Column('max_api_requests_per_month', sa.Integer, default=10000),
        sa.Column('max_storage_mb', sa.Integer, default=1000),
        sa.Column('current_users', sa.Integer, default=0),
        sa.Column('api_requests_this_month', sa.Integer, default=0),
        sa.Column('storage_used_mb', sa.Float, default=0.0),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True, comment='bcrypt hash'),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('role', sa.String(50), default='member', nullable=False, comment='owner, admin, member, viewer, auditor'),
        sa.Column('permissions', postgresql.JSONB, default=[]),
        sa.Column('mfa_enabled', sa.Boolean, default=False),
        sa.Column('mfa_secret', sa.String(255), nullable=True, comment='TOTP secret'),
        sa.Column('sso_provider', sa.String(50), nullable=True, comment='google, okta, azure_ad, github'),
        sa.Column('sso_user_id', sa.String(255), nullable=True, index=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('email_verified', sa.Boolean, default=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer', 'auditor')", name='valid_role'),
    )

    # 3. Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_name', sa.String(255), nullable=False),
        sa.Column('workspace_slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('environment', sa.String(50), default='production', comment='production, staging, development, testing'),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 4. Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('key_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('key_hash', sa.String(255), unique=True, nullable=False, index=True, comment='SHA-256 hash of the actual API key'),
        sa.Column('key_prefix', sa.String(20), nullable=False, comment='First few characters for UI display (sk_live_abc...)'),
        sa.Column('key_name', sa.String(255), nullable=True, comment='User-friendly name'),
        sa.Column('scopes', postgresql.JSONB, default=['process']),
        sa.Column('rate_limit_per_minute', sa.Integer, default=60),
        sa.Column('rate_limit_per_hour', sa.Integer, default=1000),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Optional expiration'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 5. Create policies table
    op.create_table(
        'policies',
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('policy_name', sa.String(255), nullable=False),
        sa.Column('policy_type', sa.String(50), nullable=False, index=True, comment='pii_pattern, injection_rule, custom_filter, content_moderation'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('policy_config', postgresql.JSONB, nullable=False, comment="Configuration: {pattern: '...', action: 'block', threshold: 0.8, ...}"),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('parent_policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('policies.policy_id'), nullable=True, comment='For versioning - points to previous version'),
        sa.Column('status', sa.String(50), default='draft', nullable=False, index=True, comment='draft, testing, active, archived'),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_mode', sa.Boolean, default=False, comment='Test mode before full deployment'),
        sa.Column('test_percentage', sa.Integer, default=0, comment='Percentage of traffic (0-100) for canary rollout'),
        sa.Column('triggered_count', sa.Integer, default=0, comment='How many times this policy matched'),
        sa.Column('false_positive_count', sa.Integer, default=0, comment='Reported false positives'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("status IN ('draft', 'testing', 'active', 'archived')", name='valid_policy_status'),
        sa.CheckConstraint('test_percentage >= 0 AND test_percentage <= 100', name='valid_test_percentage'),
    )

    # 6. Create reports table
    op.create_table(
        'reports',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('report_name', sa.String(255), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False, index=True, comment='pci_dss, gdpr, hipaa, soc2, custom'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('date_range_start', sa.DateTime(timezone=True), nullable=False, comment='Report data start date'),
        sa.Column('date_range_end', sa.DateTime(timezone=True), nullable=False, comment='Report data end date'),
        sa.Column('filters', postgresql.JSONB, default={}, comment="Report filters: {workspace_id: '...', threat_type: 'pii', ...}"),
        sa.Column('file_format', sa.String(20), nullable=False, comment='pdf, excel, json'),
        sa.Column('file_url', sa.String(512), nullable=True, comment='S3 signed URL or file path'),
        sa.Column('file_size_bytes', sa.Integer, default=0),
        sa.Column('status', sa.String(50), default='pending', nullable=False, index=True, comment='pending, processing, completed, failed'),
        sa.Column('progress_percentage', sa.Integer, default=0, comment='0-100 for progress tracking'),
        sa.Column('error_message', sa.Text, nullable=True, comment='Error details if generation failed'),
        sa.Column('total_requests_analyzed', sa.Integer, default=0),
        sa.Column('threats_detected', sa.Integer, default=0),
        sa.Column('pii_instances', sa.Integer, default=0),
        sa.Column('injections_blocked', sa.Integer, default=0),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=True, comment='User who requested report generation'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='When generation started'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='When generation finished'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='S3 signed URL expiration (typically 24h after completion)'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='valid_report_status'),
        sa.CheckConstraint("file_format IN ('pdf', 'excel', 'json')", name='valid_file_format'),
        sa.CheckConstraint('progress_percentage >= 0 AND progress_percentage <= 100', name='valid_progress_percentage'),
        sa.CheckConstraint('date_range_start <= date_range_end', name='valid_date_range'),
    )

    # 7. Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True, nullable=True, index=True, comment='Stripe subscription ID (sub_xxx)'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True, index=True, comment='Stripe customer ID (cus_xxx)'),
        sa.Column('stripe_price_id', sa.String(255), nullable=True, comment='Stripe price ID (price_xxx)'),
        sa.Column('plan_name', sa.String(100), nullable=False, comment='free, starter, pro, enterprise'),
        sa.Column('billing_cycle', sa.String(50), default='monthly', comment='monthly, yearly, lifetime'),
        sa.Column('amount', sa.Numeric(10, 2), default=0.00, comment='Subscription amount in USD'),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('status', sa.String(50), default='active', nullable=False, index=True, comment='active, trialing, past_due, canceled, unpaid'),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True, comment='Trial period end date'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True, comment='Current billing period start'),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True, comment='Current billing period end'),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_billing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_payment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_payment_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('payment_failed_count', sa.Integer, default=0, comment='Number of failed payment attempts'),
        sa.Column('features', postgresql.JSONB, default={}, comment='Enabled features: {api_rate_limit: 10000, max_users: 10, reports: true, ...}'),
        sa.Column('stripe_metadata', postgresql.JSONB, default={}, comment='Additional Stripe metadata or custom fields'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'trialing', 'past_due', 'canceled', 'unpaid', 'incomplete')", name='valid_subscription_status'),
        sa.CheckConstraint("billing_cycle IN ('monthly', 'yearly', 'lifetime')", name='valid_billing_cycle'),
        sa.CheckConstraint('amount >= 0', name='valid_amount'),
        sa.CheckConstraint('payment_failed_count >= 0', name='valid_payment_failed_count'),
    )


def downgrade() -> None:
    # Drop tables in reverse order (to respect foreign key constraints)
    op.drop_table('subscriptions')
    op.drop_table('reports')
    op.drop_table('policies')
    op.drop_table('api_keys')
    op.drop_table('workspaces')
    op.drop_table('users')
    op.drop_table('organizations')
