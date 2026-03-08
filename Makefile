# SkillMeat Makefile
# Self-documenting: run `make` or `make help` to see all targets.

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
COMPOSE        := docker compose
API_DIR        := skillmeat/api
WEB_DIR        := skillmeat/web
ALEMBIC_INI    := skillmeat/cache/migrations/alembic.ini

# ===========================================================================
# Development
# ===========================================================================

.PHONY: help dev dev-api dev-web dev-docker dev-enterprise

help: ## List all available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start native API + Web dev servers
	skillmeat web dev

dev-api: ## Start only API dev server
	skillmeat web dev --api-only

dev-web: ## Start only Web dev server
	skillmeat web dev --web-only

dev-docker: ## Containerized dev with hot reload (local profile)
	$(COMPOSE) --profile local up --build

dev-enterprise: ## Enterprise dev with Postgres
	$(COMPOSE) --profile enterprise up --build

# ===========================================================================
# Docker Operations
# ===========================================================================

.PHONY: build build-api build-web up up-auth up-enterprise down

build: ## Build all production images (local profile)
	$(COMPOSE) --profile local build

build-api: ## Build API image only
	docker build -t skillmeat-api .

build-web: ## Build Web image only
	docker build -t skillmeat-web $(WEB_DIR)/

up: ## Start local profile in background
	$(COMPOSE) --profile local up -d

up-auth: ## Start local-auth profile in background
	$(COMPOSE) --profile local-auth up -d

up-enterprise: ## Start enterprise profile in background
	$(COMPOSE) --profile enterprise up -d

down: ## Stop all services
	$(COMPOSE) down

# ===========================================================================
# Testing
# ===========================================================================

.PHONY: test test-python test-web test-integration

test: test-python test-web ## Run all tests (Python + Web)

test-python: ## Run Python tests with coverage
	pytest -v --cov=skillmeat

test-web: ## Run Web (Next.js) tests
	cd $(WEB_DIR) && pnpm test

test-integration: ## Run integration tests only
	pytest -v -m integration

# ===========================================================================
# Code Quality
# ===========================================================================

.PHONY: lint format typecheck

lint: ## Run all linters (flake8 + next lint)
	flake8 skillmeat --select=E9,F63,F7,F82
	cd $(WEB_DIR) && pnpm lint

format: ## Format code (black + prettier)
	black skillmeat
	cd $(WEB_DIR) && pnpm prettier --write .

typecheck: ## Type checking (mypy + tsc)
	mypy skillmeat --ignore-missing-imports
	cd $(WEB_DIR) && pnpm type-check

# ===========================================================================
# Database
# ===========================================================================

.PHONY: db-migrate db-reset db-seed

db-migrate: ## Run Alembic migrations to head
	alembic -c $(ALEMBIC_INI) upgrade head

db-reset: ## Reset database (drop + recreate + migrate)
	alembic -c $(ALEMBIC_INI) downgrade base
	alembic -c $(ALEMBIC_INI) upgrade head

db-seed: ## Seed database (not yet implemented)
	@echo "Database seeding is not yet implemented."

# ===========================================================================
# Utilities
# ===========================================================================

.PHONY: clean doctor logs logs-api logs-web shell-api shell-db

clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) down -v --remove-orphans

doctor: ## Diagnose environment issues
	skillmeat web doctor

logs: ## Tail all container logs
	$(COMPOSE) logs -f

logs-api: ## Tail API container logs
	$(COMPOSE) logs -f skillmeat-api

logs-web: ## Tail Web container logs
	$(COMPOSE) logs -f skillmeat-web

shell-api: ## Interactive shell in API container
	$(COMPOSE) exec skillmeat-api bash

shell-db: ## Interactive Postgres shell
	$(COMPOSE) exec postgres psql -U skillmeat
