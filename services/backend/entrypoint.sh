#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Backend entrypoint${NC}"

wait_for_postgres() {
    echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"

    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"

    if [ -n "$DATABASE_URL" ]; then
        HOST_PORT=$(echo "$DATABASE_URL" | awk -F'[@/]' '{print $4}')
        DB_HOST=$(echo "$HOST_PORT" | cut -d':' -f1)
        DB_PORT=$(echo "$HOST_PORT" | cut -d':' -f2)

        [ -z "$DB_HOST" ] && DB_HOST="localhost"
        [ -z "$DB_PORT" ] && DB_PORT="5432"
    fi

    echo "Checking PostgreSQL at ${DB_HOST}:${DB_PORT}"

    MAX_RETRIES=30
    RETRY_COUNT=0

    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "${DB_USER:-postgres}" > /dev/null 2>&1; do
        RETRY_COUNT=$((RETRY_COUNT + 1))

        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo -e "${RED}PostgreSQL unavailable after ${MAX_RETRIES} attempts${NC}"
            exit 1
        fi

        echo "PostgreSQL is unavailable (attempt ${RETRY_COUNT}/${MAX_RETRIES}) - sleeping"
        sleep 2
    done

    echo -e "${GREEN}PostgreSQL is ready${NC}"
}

run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"

    RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

    if [ "$RUN_MIGRATIONS" = "false" ]; then
        echo -e "${YELLOW}Migrations disabled by RUN_MIGRATIONS=false${NC}"
        return 0
    fi

    if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ] || [ "$PRODUCTION" = "true" ]; then
        python manage.py migrate --noinput --settings=config.settings.production
    else
        python manage.py migrate --noinput
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Migrations completed${NC}"
    else
        echo -e "${RED}Migrations failed${NC}"
        exit 1
    fi
}

collect_static() {
    echo -e "${YELLOW}Collecting static files...${NC}"

    COLLECT_STATIC="${COLLECT_STATIC:-true}"

    if [ "$COLLECT_STATIC" = "false" ]; then
        echo -e "${YELLOW}Static collection disabled by COLLECT_STATIC=false${NC}"
        return 0
    fi

    if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ] || [ "$PRODUCTION" = "true" ]; then
        python manage.py collectstatic --noinput --settings=config.settings.production || true
    else
        python manage.py collectstatic --noinput || true
    fi

    echo -e "${GREEN}Static files collected${NC}"
}

validate_environment() {
    echo -e "${YELLOW}Validating environment...${NC}"

    if [ -z "$SECRET_KEY" ] && [ "$PRODUCTION" = "true" ]; then
        echo -e "${RED}SECRET_KEY is not set in production${NC}"
        exit 1
    fi

    if [ -z "$ALLOWED_HOSTS" ] && [ "$PRODUCTION" = "true" ]; then
        echo -e "${RED}ALLOWED_HOSTS is not set in production${NC}"
        exit 1
    fi

    if [ "$USE_VAULT" = "true" ]; then
        if [ -n "$VAULT_ADDR" ] && [ -n "$VAULT_TOKEN" ]; then
            echo -e "${GREEN}Vault enabled (${VAULT_ADDR})${NC}"
        else
            echo -e "${YELLOW}USE_VAULT=true but VAULT_ADDR or VAULT_TOKEN not set${NC}"
            echo -e "${YELLOW}Falling back to environment variables${NC}"
        fi
    else
        echo "Vault disabled (using environment variables)"
    fi

    echo -e "${GREEN}Environment validation complete${NC}"
}

echo "Starting backend initialization..."

validate_environment

wait_for_postgres

run_migrations

collect_static

echo -e "${GREEN}Initialization complete${NC}"
echo "Starting application..."
echo ""

exec "$@"
