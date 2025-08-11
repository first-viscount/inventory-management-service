.PHONY: install dev test test-cov lint format check clean run docker-build docker-run docker-stop help

# Default Python interpreter
PYTHON := python3
PIP := pip3

# Project variables
PROJECT_NAME := inventory-management-service
DOCKER_IMAGE := $(PROJECT_NAME)
DOCKER_TAG := latest

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Run tests with coverage
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-report=json --cov-fail-under=60

lint: ## Run linting
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m mypy src/

format: ## Format code
	$(PYTHON) -m black src/ tests/
	$(PYTHON) -m ruff check --fix src/ tests/

check: format lint test-cov ## Run all checks (format, lint, test with coverage)

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

run: ## Run the application locally
	$(PYTHON) -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8083

docker-build: ## Build Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-run: ## Run Docker container
	docker-compose up -d

docker-stop: ## Stop Docker containers
	docker-compose down

docker-clean: ## Clean Docker resources
	docker-compose down -v --remove-orphans
	docker image rm $(DOCKER_IMAGE):$(DOCKER_TAG) 2>/dev/null || true

# Database management
db-init: ## Initialize database
	$(PYTHON) -c "import asyncio; from src.core.database import init_db; asyncio.run(init_db())"

db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose exec postgres dropdb -U inventory_user inventory_db --if-exists
	docker-compose exec postgres createdb -U inventory_user inventory_db
	$(MAKE) db-init

# Development workflow
dev-setup: docker-run db-init ## Setup development environment
	@echo "Development environment ready!"
	@echo "API: http://localhost:8083"
	@echo "Docs: http://localhost:8083/docs"
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"

dev-logs: ## Show development logs
	docker-compose logs -f inventory-management-service

# Testing
test-integration: ## Run integration tests
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build --abort-on-container-exit test-runner

# Monitoring
metrics: ## Show current metrics
	curl -s http://localhost:8083/metrics

health: ## Check service health
	curl -s http://localhost:8083/health | jq .