"""
Row-Level Security (RLS) Context Management
Utilities for setting organization context in PostgreSQL sessions
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import contextmanager


def set_org_context(db: Session, org_id: UUID) -> None:
    """
    Set organization context for Row-Level Security

    This sets the PostgreSQL session variable 'app.current_org_id' which is used
    by RLS policies to filter rows automatically.

    Args:
        db: SQLAlchemy session
        org_id: Organization UUID

    Example:
        >>> from sentinel.saas.dependencies import get_db
        >>> from sentinel.saas.rls import set_org_context
        >>>
        >>> db = next(get_db())
        >>> set_org_context(db, org_id)
        >>> # Now all queries are automatically filtered by org_id
        >>> users = db.query(User).all()  # Only returns users in org_id
    """
    db.execute(text(f"SET app.current_org_id = '{org_id}'"))


def clear_org_context(db: Session) -> None:
    """
    Clear organization context

    Removes the organization filter. Use this when you need to perform
    cross-organization queries (e.g., superuser operations).

    Args:
        db: SQLAlchemy session

    Example:
        >>> clear_org_context(db)
        >>> # Now queries return all rows (no RLS filtering)
    """
    db.execute(text("SET app.current_org_id = ''"))


@contextmanager
def org_context(db: Session, org_id: Optional[UUID] = None):
    """
    Context manager for organization-scoped database operations

    Automatically sets and clears the organization context.

    Args:
        db: SQLAlchemy session
        org_id: Organization UUID (None to clear context)

    Example:
        >>> with org_context(db, org_id):
        ...     users = db.query(User).all()
        ...     # Users are automatically filtered by org_id
        >>> # Context is automatically cleared after the block
    """
    if org_id:
        set_org_context(db, org_id)
    else:
        clear_org_context(db)

    try:
        yield
    finally:
        # Clear context after the block
        clear_org_context(db)


def bypass_rls(db: Session) -> None:
    """
    Bypass Row-Level Security (superuser only)

    WARNING: This disables RLS for the current session. Only use for
    administrative operations that require access to all data.

    Requires database superuser privileges.

    Args:
        db: SQLAlchemy session

    Example:
        >>> bypass_rls(db)
        >>> all_orgs = db.query(Organization).all()  # Returns ALL organizations
    """
    db.execute(text("SET row_security = OFF"))


def enable_rls(db: Session) -> None:
    """
    Re-enable Row-Level Security

    Re-enables RLS after it was bypassed with bypass_rls().

    Args:
        db: SQLAlchemy session
    """
    db.execute(text("SET row_security = ON"))


# ============================================================================
# MIDDLEWARE FOR AUTOMATIC CONTEXT SETTING
# ============================================================================

class RLSMiddleware:
    """
    SQLAlchemy event listener for automatic RLS context setting

    This middleware automatically sets the organization context based on
    the current user's org_id for all database operations.

    Usage:
        >>> from sqlalchemy import event
        >>> from sentinel.saas.rls import RLSMiddleware
        >>>
        >>> # Attach to engine
        >>> middleware = RLSMiddleware()
        >>> event.listen(engine, "connect", middleware.set_search_path)
    """

    def __init__(self):
        self.current_org_id: Optional[UUID] = None

    def set_current_org(self, org_id: UUID):
        """Set the current organization for subsequent connections"""
        self.current_org_id = org_id

    def set_search_path(self, dbapi_conn, connection_record):
        """Event listener: Set RLS context on new connections"""
        if self.current_org_id:
            cursor = dbapi_conn.cursor()
            cursor.execute(f"SET app.current_org_id = '{self.current_org_id}'")
            cursor.close()
