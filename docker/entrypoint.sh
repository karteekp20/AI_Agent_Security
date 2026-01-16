#!/bin/bash
set -e

echo "======================================"
echo "Sentinel API - Starting Up"
echo "======================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-sentinel_user} -d ${POSTGRES_DB:-sentinel}; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."

# Check current migration status
CURRENT_REV=$(alembic current 2>/dev/null | grep -o '^[a-f0-9]\+' | head -n1)

if [ -z "$CURRENT_REV" ]; then
  echo "No migration version tracked. Checking if tables exist..."

  # Check if organizations table exists (indicator of schema being present)
  TABLE_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -tAc \
    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations');")

  if [ "$TABLE_EXISTS" = "t" ]; then
    echo "Tables exist but not tracked by Alembic. Stamping database..."
    alembic stamp head
  else
    echo "Fresh database. Running all migrations..."
    alembic upgrade head
  fi
else
  echo "Current revision: $CURRENT_REV. Running any pending migrations..."
  alembic upgrade head
fi

echo "Migrations complete!"

# Execute the main command (passed as arguments)
echo "Starting application..."
exec "$@"
