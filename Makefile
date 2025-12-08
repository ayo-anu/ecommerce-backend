.PHONY: help install dev prod build test clean logs restart health migrate collectstatic createsuperuser shell backup restore deploy

# ==============================================================================
# E-Commerce Platform Makefile
# ==============================================================================
# Provides convenient commands for common development and deployment tasks
# ==============================================================================

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Docker Compose files
COMPOSE_FILE := infrastructure/docker-compose.yaml
COMPOSE_DEV := infrastructure/docker-compose.dev.yaml
COMPOSE_PROD := infrastructure/docker-compose.prod.yaml

# Default environment
ENV ?= development

help: ## Show this help message
	@echo "$(BLUE)E-Commerce Platform - Available Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make install          - Install dependencies and setup project"
	@echo "  make dev              - Start all services in development mode"
	@echo "  make build            - Build all Docker images"
	@echo "  make rebuild          - Rebuild all images from scratch"
	@echo "  make stop             - Stop all services"
	@echo "  make restart          - Restart all services"
	@echo "  make logs             - Show logs from all services"
	@echo "  make logs-f           - Follow logs from all services"
	@echo "  make shell            - Open Django shell"
	@echo "  make clean            - Stop and remove all containers, volumes, images"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  make migrate          - Run Django migrations"
	@echo "  make migrations       - Create new migrations"
	@echo "  make makemigrations   - Alias for migrations"
	@echo "  make dbshell          - Open PostgreSQL shell"
	@echo "  make createsuperuser  - Create Django superuser"
	@echo "  make seed             - Load sample data"
	@echo "  make backup           - Backup databases"
	@echo "  make restore          - Restore databases from backup"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test             - Run all tests"
	@echo "  make test-backend     - Run backend tests only"
	@echo "  make test-ai          - Run AI services tests"
	@echo "  make test-frontend    - Run frontend tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo ""
	@echo "$(GREEN)Production:$(NC)"
	@echo "  make prod             - Start services in production mode"
	@echo "  make deploy           - Deploy to production"
	@echo "  make collectstatic    - Collect static files"
	@echo ""
	@echo "$(GREEN)SSL/TLS:$(NC)"
	@echo "  make setup-ssl        - Setup SSL certificates with Let's Encrypt"
	@echo "  make renew-ssl        - Renew SSL certificates"
	@echo ""
	@echo "$(GREEN)Backup & Restore:$(NC)"
	@echo "  make backup-all       - Backup all databases"
	@echo "  make backup-to-s3     - Backup databases to S3"
	@echo "  make restore          - Restore database (BACKUP_FILE=path/to/backup.sql.gz)"
	@echo "  make setup-auto-backup - Setup automated daily backups"
	@echo "  make list-backups     - List available backups"
	@echo ""
	@echo "$(GREEN)Load Testing:$(NC)"
	@echo "  make load-test-smoke  - Run smoke test (10 users, 2 min)"
	@echo "  make load-test-baseline - Run baseline test (50 users, 10 min)"
	@echo "  make load-test-stress - Run stress test (200 users, 15 min)"
	@echo "  make load-test-web    - Launch Locust web UI"
	@echo ""
	@echo "$(GREEN)Docker Optimization:$(NC)"
	@echo "  make build-fast       - Build all images with BuildKit (60-85% faster)"
	@echo "  make build-service    - Build specific service (SERVICE=name)"
	@echo "  make rebuild-fast     - Rebuild all images with BuildKit (no cache)"
	@echo "  make verify-images    - Verify image sizes after optimization"
	@echo "  make show-deps        - Show dependencies for a service (SERVICE=name)"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make health           - Check health of all services"
	@echo "  make ps               - Show running containers"
	@echo "  make stats            - Show resource usage statistics"
	@echo "  make prune            - Remove unused Docker resources"

# ==============================================================================
# Installation & Setup
# ==============================================================================

install: ## Install and setup the project
	@echo "$(BLUE)Installing E-Commerce Platform...$(NC)"
	@if [ ! -f infrastructure/env/.env.development ]; then \
		echo "$(YELLOW)Creating environment file...$(NC)"; \
		cp infrastructure/env/.env.example infrastructure/env/.env.development; \
	fi
	@echo "$(GREEN)Building Docker images...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) build
	@echo "$(GREEN)Starting services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up -d postgres postgres_ai redis
	@echo "$(YELLOW)Waiting for databases...$(NC)"
	@sleep 10
	@echo "$(GREEN)Running migrations...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) run --rm backend python manage.py migrate
	@echo "$(GREEN)Collecting static files...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) run --rm backend python manage.py collectstatic --no-input
	@echo "$(GREEN)✓ Installation complete!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Run 'make createsuperuser' to create an admin user"
	@echo "  2. Run 'make dev' to start all services"
	@echo "  3. Visit http://localhost:8000/admin/ for Django admin"
	@echo "  4. Visit http://localhost:3000 for the frontend"

# ==============================================================================
# Development
# ==============================================================================

dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up -d
	@echo "$(GREEN)✓ All services started!$(NC)"
	@echo ""
	@echo "$(BLUE)Services:$(NC)"
	@echo "  Frontend:       http://localhost:3000"
	@echo "  Backend API:    http://localhost:8000"
	@echo "  API Docs:       http://localhost:8000/api/docs/"
	@echo "  Django Admin:   http://localhost:8000/admin/"
	@echo "  API Gateway:    http://localhost:8080"
	@echo "  Gateway Docs:   http://localhost:8080/docs"
	@echo "  Prometheus:     http://localhost:9090"
	@echo "  Grafana:        http://localhost:3001"
	@echo "  RabbitMQ:       http://localhost:15672"
	@echo "  MailHog:        http://localhost:8025"
	@echo ""
	@echo "$(YELLOW)Run 'make logs-f' to follow logs$(NC)"
	@echo "$(YELLOW)Run 'make health' to check service health$(NC)"

build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker-compose build
	@echo "$(GREEN)✓ Build complete!$(NC)"

build-fast: ## Build all images with BuildKit optimization (60-85% faster)
	@echo "$(BLUE)Building Docker images with BuildKit optimization...$(NC)"
	@echo "$(YELLOW)This will be 60-85% faster than regular builds!$(NC)"
	@export DOCKER_BUILDKIT=1 && export COMPOSE_DOCKER_CLI_BUILD=1 && docker-compose build --parallel
	@echo "$(GREEN)✓ Optimized build complete!$(NC)"
	@echo "$(BLUE)Verifying image sizes...$(NC)"
	@docker images | grep ecommerce | head -10

build-service: ## Build a specific service (usage: make build-service SERVICE=gateway)
	@echo "$(BLUE)Building service: $(SERVICE)...$(NC)"
	@export DOCKER_BUILDKIT=1 && docker-compose build $(SERVICE)
	@echo "$(GREEN)✓ Service $(SERVICE) built!$(NC)"

rebuild: ## Rebuild all images from scratch (no cache)
	@echo "$(BLUE)Rebuilding Docker images from scratch...$(NC)"
	@docker-compose build --no-cache
	@echo "$(GREEN)✓ Rebuild complete!$(NC)"

rebuild-fast: ## Rebuild all images with BuildKit and no cache
	@echo "$(BLUE)Rebuilding Docker images with BuildKit (no cache)...$(NC)"
	@export DOCKER_BUILDKIT=1 && export COMPOSE_DOCKER_CLI_BUILD=1 && docker-compose build --no-cache --parallel
	@echo "$(GREEN)✓ Optimized rebuild complete!$(NC)"

stop: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) stop
	@echo "$(GREEN)✓ All services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting all services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) restart
	@echo "$(GREEN)✓ All services restarted$(NC)"

logs: ## Show logs from all services
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) logs --tail=100

logs-f: ## Follow logs from all services
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) logs -f

logs-backend: ## Show backend logs
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) logs --tail=100 -f backend

logs-frontend: ## Show frontend logs
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) logs --tail=100 -f frontend

logs-gateway: ## Show API gateway logs
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) logs --tail=100 -f api_gateway

shell: ## Open Django shell
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend python manage.py shell

clean: ## Stop and remove all containers, volumes, and images
	@echo "$(RED)⚠ This will remove all containers, volumes, and images. Continue? [y/N]$(NC)"
	@read -p "" confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) down -v --remove-orphans
	@docker system prune -af
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"

# ==============================================================================
# Database Management
# ==============================================================================

migrate: ## Run Django migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend python manage.py migrate
	@echo "$(GREEN)✓ Migrations complete!$(NC)"

makemigrations: ## Create new migrations
	@echo "$(BLUE)Creating migrations...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend python manage.py makemigrations
	@echo "$(GREEN)✓ Migrations created!$(NC)"

migrations: makemigrations ## Alias for makemigrations

dbshell: ## Open PostgreSQL shell
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec postgres psql -U postgres -d ecommerce

createsuperuser: ## Create Django superuser
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend python manage.py createsuperuser

seed: ## Load sample data
	@echo "$(BLUE)Loading sample data...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend python manage.py loaddata fixtures/sample_data.json
	@echo "$(GREEN)✓ Sample data loaded!$(NC)"

backup: ## Backup databases
	@echo "$(BLUE)Backing up databases...$(NC)"
	@mkdir -p backups
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres pg_dump -U postgres ecommerce > backups/ecommerce_$(shell date +%Y%m%d_%H%M%S).sql
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres_ai pg_dump -U postgres ecommerce_ai > backups/ecommerce_ai_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup complete!$(NC)"

restore: ## Restore databases from latest backup
	@echo "$(YELLOW)Restoring from latest backup...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U postgres ecommerce < $(shell ls -t backups/ecommerce_*.sql | head -1)
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres_ai psql -U postgres ecommerce_ai < $(shell ls -t backups/ecommerce_ai_*.sql | head -1)
	@echo "$(GREEN)✓ Restore complete!$(NC)"

# ==============================================================================
# Testing
# ==============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	@./scripts/test_all.sh

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend pytest

test-ai: ## Run AI services tests
	@echo "$(BLUE)Running AI services tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec recommender pytest /app/tests
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec search pytest /app/tests
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec pricing pytest /app/tests
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec chatbot pytest /app/tests
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec fraud pytest /app/tests
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec forecasting pytest /app/tests
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec vision pytest /app/tests

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec frontend npm test

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend pytest tests/integration

test-coverage: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec backend pytest --cov=. --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

# ==============================================================================
# Production
# ==============================================================================

prod: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	@if [ ! -f infrastructure/env/.env.production ]; then \
		echo "$(RED)Error: infrastructure/env/.env.production not found!$(NC)"; \
		exit 1; \
	fi
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD) up -d
	@echo "$(GREEN)✓ Production services started!$(NC)"

deploy: ## Deploy to production
	@echo "$(BLUE)Deploying to production...$(NC)"
	@./scripts/deploy.sh

collectstatic: ## Collect static files
	@echo "$(BLUE)Collecting static files...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend python manage.py collectstatic --no-input
	@echo "$(GREEN)✓ Static files collected!$(NC)"

# ==============================================================================
# Utilities
# ==============================================================================

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@python3 scripts/health_check.py

ps: ## Show running containers
	@docker-compose -f $(COMPOSE_FILE) ps

stats: ## Show resource usage statistics
	@docker stats --no-stream

prune: ## Remove unused Docker resources
	@echo "$(YELLOW)Removing unused Docker resources...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"

# ==============================================================================
# Docker Optimization Utilities
# ==============================================================================

verify-images: ## Verify image sizes after optimization
	@echo "$(BLUE)Verifying Docker image sizes...$(NC)"
	@echo ""
	@echo "$(GREEN)Expected sizes after optimization:$(NC)"
	@echo "  API Gateway:        ~600 MB (was 3-4 GB)"
	@echo "  Recommendation:     ~1.5 GB (was 3-4 GB)"
	@echo "  Visual Recognition: ~2.0 GB (was 4-5 GB)"
	@echo "  Other ML services:  ~1.5-2 GB (was 3-4 GB)"
	@echo ""
	@echo "$(BLUE)Actual sizes:$(NC)"
	@docker images | grep -E "REPOSITORY|ecommerce-" | grep -v "<none>"
	@echo ""
	@echo "$(YELLOW)Checking for build tools in production images...$(NC)"
	@docker run --rm ecommerce-gateway which gcc 2>/dev/null && echo "$(RED)⚠️  gcc found in gateway (should not be there)$(NC)" || echo "$(GREEN)✓ No gcc in gateway$(NC)"
	@docker run --rm ecommerce-vision which gcc 2>/dev/null && echo "$(RED)⚠️  gcc found in vision (should not be there)$(NC)" || echo "$(GREEN)✓ No gcc in vision$(NC)"

show-deps: ## Show dependencies for a service (usage: make show-deps SERVICE=gateway)
	@echo "$(BLUE)Dependencies for $(SERVICE):$(NC)"
	@docker run --rm ecommerce-$(SERVICE) pip list

verify-optimization: ## Run full optimization verification
	@echo "$(BLUE)Running full optimization verification...$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Checking image sizes...$(NC)"
	@docker images | grep ecommerce | awk '{print $$1, $$7, $$8}'
	@echo ""
	@echo "$(YELLOW)2. Checking for build tools (should be absent)...$(NC)"
	@for service in gateway recommender vision chatbot search pricing fraud forecasting; do \
		echo -n "  $$service: "; \
		docker run --rm ecommerce-$$service which gcc 2>/dev/null && echo "$(RED)gcc found ❌$(NC)" || echo "$(GREEN)clean ✅$(NC)"; \
	done
	@echo ""
	@echo "$(YELLOW)3. Checking dependency counts...$(NC)"
	@echo "  API Gateway:        $$(docker run --rm ecommerce-gateway pip list 2>/dev/null | wc -l) packages (expected: ~25-30)"
	@echo "  Visual Recognition: $$(docker run --rm ecommerce-vision pip list 2>/dev/null | wc -l) packages (expected: ~45-55)"
	@echo ""
	@echo "$(GREEN)✓ Verification complete!$(NC)"
	@echo "See docs/DOCKER_OPTIMIZATION.md for details"

# ==============================================================================
# AI Services Management
# ==============================================================================

train-recommender: ## Train recommendation model
	@echo "$(BLUE)Training recommendation model...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec recommender python -m app.train

train-all: ## Train all ML models
	@echo "$(BLUE)Training all ML models...$(NC)"
	@./scripts/train_all_models.sh

# ==============================================================================
# Monitoring
# ==============================================================================

monitoring: ## Start monitoring stack
	@echo "$(BLUE)Starting monitoring services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) up -d prometheus grafana
	@echo "$(GREEN)✓ Monitoring stack started!$(NC)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001 (admin/admin)"

# ==============================================================================
# SSL/TLS Management
# ==============================================================================

setup-ssl: ## Setup SSL/TLS certificates with Let's Encrypt
	@echo "$(BLUE)Setting up SSL/TLS certificates...$(NC)"
	@./scripts/setup_ssl.sh $(DOMAIN) $(EMAIL)

renew-ssl: ## Renew SSL certificates
	@echo "$(BLUE)Renewing SSL certificates...$(NC)"
	@./scripts/renew_ssl.sh

# ==============================================================================
# Backup & Restore
# ==============================================================================

backup-all: ## Backup all databases
	@echo "$(BLUE)Backing up all databases...$(NC)"
	@./scripts/backup_databases.sh --all
	@echo "$(GREEN)✓ Backup complete!$(NC)"

backup-main: ## Backup main database only
	@echo "$(BLUE)Backing up main database...$(NC)"
	@./scripts/backup_databases.sh --main

backup-ai: ## Backup AI database only
	@echo "$(BLUE)Backing up AI database...$(NC)"
	@./scripts/backup_databases.sh --ai

backup-to-s3: ## Backup databases and upload to S3
	@echo "$(BLUE)Backing up databases to S3...$(NC)"
	@./scripts/backup_databases.sh --all --s3

restore: ## Restore database from backup (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Error: BACKUP_FILE not specified$(NC)"; \
		echo "Usage: make restore BACKUP_FILE=backups/databases/main_db_20250128_120000.sql.gz"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring database from $(BACKUP_FILE)...$(NC)"
	@./scripts/restore_database.sh $(BACKUP_FILE)

setup-auto-backup: ## Setup automated daily backups via cron
	@echo "$(BLUE)Setting up automated backups...$(NC)"
	@./scripts/setup_backup_cron.sh --daily
	@echo "$(GREEN)✓ Automated backups configured!$(NC)"

list-backups: ## List available backups
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -lh backups/databases/ 2>/dev/null || echo "No backups found"

# ==============================================================================
# Load Testing
# ==============================================================================

load-test-smoke: ## Run smoke test (10 users, 2 min)
	@echo "$(BLUE)Running smoke test...$(NC)"
	@./scripts/run_load_tests.sh smoke

load-test-baseline: ## Run baseline test (50 users, 10 min)
	@echo "$(BLUE)Running baseline performance test...$(NC)"
	@./scripts/run_load_tests.sh baseline --report

load-test-stress: ## Run stress test (200 users, 15 min)
	@echo "$(BLUE)Running stress test...$(NC)"
	@./scripts/run_load_tests.sh stress --report

load-test-spike: ## Run spike test (500 users, 5 min)
	@echo "$(BLUE)Running spike test...$(NC)"
	@./scripts/run_load_tests.sh spike --report

load-test-endurance: ## Run endurance test (100 users, 60 min)
	@echo "$(BLUE)Running endurance test...$(NC)"
	@./scripts/run_load_tests.sh endurance --report

load-test-web: ## Launch Locust web UI
	@echo "$(BLUE)Launching Locust web UI...$(NC)"
	@./scripts/run_load_tests.sh baseline --web

# ==============================================================================
# Version Info
# ==============================================================================

version: ## Show version information
	@echo "$(BLUE)E-Commerce Platform$(NC)"
	@echo "Version: 1.0.0"
	@echo ""
	@echo "$(BLUE)Component Versions:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend python --version
	@docker-compose -f $(COMPOSE_FILE) exec backend python -c "import django; print(f'Django: {django.__version__}')"
	@docker-compose -f $(COMPOSE_FILE) exec frontend node --version
	@docker-compose -f $(COMPOSE_FILE) exec recommender python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
