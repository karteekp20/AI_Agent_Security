"""
Database session management (stub for future implementation)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sentinel_user:sentinel_password@localhost:5432/sentinel"
)

# Create engine
engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI routes
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
