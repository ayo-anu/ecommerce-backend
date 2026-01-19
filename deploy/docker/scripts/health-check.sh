#!/bin/bash

set -e
set -u
set -o pipefail

TIMEOUT=300
INTERVAL=5
SERVICE=""
VERBOSE=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

declare -a SERVICES=(
    "api_gateway:8080:/health"
    "backend:8000:/api/health/"
    "recommender:8001:/health"
    "search:8002:/health"
    "pricing:8003:/health"
    "chatbot:8004:/health"
    "fraud:8005:/health"
    "forecasting:8006:/health"
    "vision:8007:/health"
)

while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        --service) SERVICE="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log() {
    if [ "$VERBOSE" = true ]; then
        echo -e "$1"
    fi
}

check_service() {
    local service=$1
    local port=$2
    local endpoint=$3
    local max_attempts=$((TIMEOUT / INTERVAL))
    local attempt=0

    log "${YELLOW}Checking $service...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if docker exec ecommerce_nginx curl -sf "http://$service:$port$endpoint" > /dev/null 2>&1; then
            echo -e "${GREEN}$service is healthy${NC}"
            return 0
        fi

        attempt=$((attempt + 1))
        log "  Attempt $attempt/$max_attempts..."
        sleep $INTERVAL
    done

    echo -e "${RED}$service is unhealthy (timeout after ${TIMEOUT}s)${NC}"
    return 1
}

main() {
    local failed=0
    local checked=0

    echo "Health check (timeout ${TIMEOUT}s, interval ${INTERVAL}s)"

    for service_def in "${SERVICES[@]}"; do
        IFS=':' read -r name port endpoint <<< "$service_def"

        if [ -n "$SERVICE" ] && [ "$SERVICE" != "$name" ]; then
            continue
        fi

        checked=$((checked + 1))

        if ! check_service "$name" "$port" "$endpoint"; then
            failed=$((failed + 1))
        fi
    done

    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}All services healthy ($checked/$checked)${NC}"
        exit 0
    else
        echo -e "${RED}$failed services unhealthy${NC} ($((checked - failed))/$checked healthy)"
        exit 1
    fi
}

main
