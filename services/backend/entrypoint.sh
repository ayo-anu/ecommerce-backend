#!/bin/bash
# ==============================================================================
# Backend Entrypoint Script
# ==============================================================================
# This script handles:
# - Database connectivity checks
# - Database migrations (production-safe)
# - Graceful startup with proper error handling
# - Vault integration (optional, never crashes if unavailable)
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Django Backend Entrypoint ===${NC}"

# ==============================================================================
# Function: Wait for PostgreSQL
# ==============================================================================
wait_for_postgres() {
    echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"

    # Extract database host and port from DATABASE_URL or use defaults
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"

    # If DATABASE_URL is set, try to extract host and port
    if [ -n "$DATABASE_URL" ]; then
        # Extract host from DATABASE_URL (format: postgresql://user:pass@host:port/db)
        # Remove protocol and credentials, extract host:port
        HOST_PORT=$(echo "$DATABASE_URL" | awk -F'[@/]' '{print $4}')
        DB_HOST=$(echo "$HOST_PORT" | cut -d':' -f1)
        DB_PORT=$(echo "$HOST_PORT" | cut -d':' -f2)

        # Fallback if extraction failed
        [ -z "$DB_HOST" ] && DB_HOST="localhost"
        [ -z "$DB_PORT" ] && DB_PORT="5432"
    fi

    echo "Checking PostgreSQL at ${DB_HOST}:${DB_PORT}"

    MAX_RETRIES=30
    RETRY_COUNT=0

    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "${DB_USER:-postgres}" > /dev/null 2>&1; do
        RETRY_COUNT=$((RETRY_COUNT + 1))

        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo -e "${RED}ERROR: PostgreSQL is unavailable after ${MAX_RETRIES} attempts${NC}"
            exit 1
        fi

        echo "PostgreSQL is unavailable (attempt ${RETRY_COUNT}/${MAX_RETRIES}) - sleeping"
        sleep 2
    done

    echo -e "${GREEN}PostgreSQL is ready!${NC}"
}

# ==============================================================================
# Function: Run Database Migrations
# ==============================================================================
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"

    # Check if we should run migrations (controlled by env var)
    RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

    if [ "$RUN_MIGRATIONS" = "false" ]; then
        echo -e "${YELLOW}Migrations disabled by RUN_MIGRATIONS=false${NC}"
        return 0
    fi

    # Run migrations with appropriate settings
    if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ] || [ "$PRODUCTION" = "true" ]; then
        echo "Running migrations with production settings..."
        python manage.py migrate --noinput --settings=config.settings.production
    else
        echo "Running migrations with default settings..."
        python manage.py migrate --noinput
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Migrations completed successfully!${NC}"
    else
        echo -e "${RED}ERROR: Migrations failed${NC}"
        exit 1
    fi
}

# ==============================================================================
# Function: Collect Static Files
# ==============================================================================
collect_static() {
    echo -e "${YELLOW}Collecting static files...${NC}"

    # Check if we should collect static files
    COLLECT_STATIC="${COLLECT_STATIC:-true}"

    if [ "$COLLECT_STATIC" = "false" ]; then
        echo -e "${YELLOW}Static collection disabled by COLLECT_STATIC=false${NC}"
        return 0
    fi

    # Collect static files
    if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ] || [ "$PRODUCTION" = "true" ]; then
        python manage.py collectstatic --noinput --settings=config.settings.production || true
    else
        python manage.py collectstatic --noinput || true
    fi

    echo -e "${GREEN}Static files collected!${NC}"
}

# ==============================================================================
# Function: Validate Environment
# ==============================================================================
validate_environment() {
    echo -e "${YELLOW}Validating environment...${NC}"

    # Check critical environment variables
    if [ -z "$SECRET_KEY" ] && [ "$PRODUCTION" = "true" ]; then
        echo -e "${RED}ERROR: SECRET_KEY is not set in production${NC}"
        exit 1
    fi

    if [ -z "$ALLOWED_HOSTS" ] && [ "$PRODUCTION" = "true" ]; then
        echo -e "${RED}ERROR: ALLOWED_HOSTS is not set in production${NC}"
        exit 1
    fi

    # Vault is optional - just log status
    if [ "$USE_VAULT" = "true" ]; then
        if [ -n "$VAULT_ADDR" ] && [ -n "$VAULT_TOKEN" ]; then
            echo -e "${GREEN}Vault integration enabled (VAULT_ADDR: ${VAULT_ADDR})${NC}"
        else
            echo -e "${YELLOW}WARNING: USE_VAULT=true but VAULT_ADDR or VAULT_TOKEN not set${NC}"
            echo -e "${YELLOW}Falling back to environment variables${NC}"
        fi
    else
        echo "Vault integration disabled (using environment variables)"
    fi

    echo -e "${GREEN}Environment validation complete!${NC}"
}

# ==============================================================================
# Main Execution
# ==============================================================================

echo "Starting backend initialization..."

# Validate environment
validate_environment

# Wait for database
wait_for_postgres

# Run migrations
run_migrations

# Collect static files
collect_static

echo -e "${GREEN}=== Initialization Complete ===${NC}"
echo "Starting application..."
echo ""

# Execute the CMD from Dockerfile (gunicorn)
exec "$@"
