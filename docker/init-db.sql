-- ============================================================================
-- SENTINEL AI SECURITY - DATABASE INITIALIZATION
-- ============================================================================
-- This script is automatically executed when PostgreSQL container starts
-- Tables are created by the PostgreSQLAdapter, but we can add extras here

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Trigram matching for text search

-- Create schema
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions
GRANT ALL ON SCHEMA public TO sentinel_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sentinel_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sentinel_user;

-- Create indexes for common queries (tables will be created by adapter)
-- Note: These indexes are also created by PostgreSQLAdapter._create_tables()
-- but we include them here for reference

-- Performance hints
COMMENT ON SCHEMA public IS 'Sentinel AI Security audit logs and pattern storage';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Sentinel database initialized successfully';
END $$;
