#!/bin/bash

# ==============================================================================
# Local Development Setup Script
# ==============================================================================
# Automates the setup of the e-commerce platform for local development
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker installed: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose installed: $(docker-compose --version)"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 is not installed. Some scripts may not work."
    else
        print_success "Python installed: $(python3 --version)"
    fi

    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed. Frontend development may not work."
    else
        print_success "Node.js installed: $(node --version)"
    fi

    # Check Make
    if ! command -v make &> /dev/null; then
        print_warning "Make is not installed. Use docker-compose commands directly."
    else
        print_success "Make installed"
    fi

    echo ""
}

# Setup environment files
setup_environment() {
    print_header "Setting Up Environment"

    ENV_FILE="infrastructure/env/.env.development"

    if [ -f "$ENV_FILE" ]; then
        print_warning "Environment file already exists: $ENV_FILE"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing environment file"
            return
        fi
    fi

    print_info "Creating environment file from template..."
    cp infrastructure/env/.env.example "$ENV_FILE"

    # Generate random secret key
    if command -v openssl &> /dev/null; then
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i.bak "s/django-insecure-change-this-to-a-secure-random-key-in-production/$SECRET_KEY/" "$ENV_FILE"
        rm "${ENV_FILE}.bak" 2>/dev/null || true
        print_success "Generated random SECRET_KEY"
    fi

    print_success "Environment file created: $ENV_FILE"
    print_warning "Please update the following in $ENV_FILE:"
    echo "  - OPENAI_API_KEY (for chatbot service)"
    echo "  - STRIPE_SECRET_KEY (for payments)"
    echo "  - STRIPE_PUBLISHABLE_KEY (for payments)"
    echo ""

    read -p "Do you want to edit the environment file now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} "$ENV_FILE"
    fi
}

# Build Docker images
build_images() {
    print_header "Building Docker Images"

    print_info "This may take several minutes on first run..."
    docker-compose -f deploy/docker/compose/base.yaml build

    print_success "Docker images built successfully"
    echo ""
}

# Start services
start_services() {
    print_header "Starting Services"

    print_info "Starting all services in detached mode..."
    docker-compose -f deploy/docker/compose/base.yaml \
                   -f deploy/docker/compose/base.dev.yaml up -d

    print_success "All services started"
    echo ""

    print_info "Waiting for services to be healthy..."
    sleep 10
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    print_info "Waiting for database to be ready..."
    sleep 5

    print_info "Running Django migrations..."
    docker-compose -f deploy/docker/compose/base.yaml exec -T backend \
        python manage.py migrate --noinput

    print_success "Migrations completed"
    echo ""
}

# Collect static files
collect_static() {
    print_header "Collecting Static Files"

    docker-compose -f deploy/docker/compose/base.yaml exec -T backend \
        python manage.py collectstatic --noinput

    print_success "Static files collected"
    echo ""
}

# Create superuser
create_superuser() {
    print_header "Creating Superuser"

    read -p "Do you want to create a Django superuser? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        docker-compose -f deploy/docker/compose/base.yaml exec backend \
            python manage.py createsuperuser
        print_success "Superuser created"
    else
        print_info "Skipped superuser creation"
    fi
    echo ""
}

# Load sample data
load_sample_data() {
    print_header "Loading Sample Data"

    read -p "Do you want to load sample data? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if [ -f "services/backend/fixtures/sample_data.json" ]; then
            docker-compose -f deploy/docker/compose/base.yaml exec -T backend \
                python manage.py loaddata fixtures/sample_data.json
            print_success "Sample data loaded"
        else
            print_warning "Sample data file not found"
        fi
    else
        print_info "Skipped sample data loading"
    fi
    echo ""
}

# Check service health
check_health() {
    print_header "Checking Service Health"

    if command -v python3 &> /dev/null; then
        python3 scripts/health_check.py
    else
        print_warning "Python 3 not available, skipping health check"
        print_info "You can check manually:"
        echo "  docker-compose ps"
    fi
    echo ""
}

# Show access information
show_access_info() {
    print_header "Access Information"

    echo -e "${GREEN}All services are now running!${NC}"
    echo ""
    echo "Frontend:       ${BLUE}http://localhost:3000${NC}"
    echo "Backend API:    ${BLUE}http://localhost:8000${NC}"
    echo "API Docs:       ${BLUE}http://localhost:8000/api/docs/${NC}"
    echo "Django Admin:   ${BLUE}http://localhost:8000/admin/${NC}"
    echo "API Gateway:    ${BLUE}http://localhost:8080${NC}"
    echo "Gateway Docs:   ${BLUE}http://localhost:8080/docs${NC}"
    echo "Prometheus:     ${BLUE}http://localhost:9090${NC}"
    echo "Grafana:        ${BLUE}http://localhost:3001${NC} (admin/admin)"
    echo "RabbitMQ:       ${BLUE}http://localhost:15672${NC} (admin/admin)"
    echo ""
    echo "${YELLOW}Useful Commands:${NC}"
    echo "  View logs:        ${BLUE}make logs-f${NC}"
    echo "  Stop services:    ${BLUE}make stop${NC}"
    echo "  Restart services: ${BLUE}make restart${NC}"
    echo "  Health check:     ${BLUE}make health${NC}"
    echo "  Django shell:     ${BLUE}make shell${NC}"
    echo ""
}

# Main execution
main() {
    print_header "E-Commerce Platform - Local Development Setup"
    echo ""

    check_prerequisites
    setup_environment
    build_images
    start_services
    run_migrations
    collect_static
    create_superuser
    load_sample_data
    check_health
    show_access_info

    print_success "Setup complete! Happy coding! 🚀"
}

# Run main function
main
