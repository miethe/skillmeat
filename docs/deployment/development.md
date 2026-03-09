---
title: Developer Environment Guide
description: Set up your local development environment for SkillMeat with hot reload, debugging, and testing
audience: developers, contributors
tags:
- development
- setup
- makefile
- testing
- debugging
- hot-reload
created: 2026-03-08
updated: 2026-03-08
category: operational
status: active
related_documents:
- docs/deployment/README.md
- docs/deployment/local.md
- docs/deployment/enterprise.md
- CONTRIBUTING.md
---

# Developer Environment Guide

Set up your local development environment for contributing to SkillMeat with native hot reload, debugging, and full test coverage.

## Quick Start

### Option 1: Native Setup (Fastest)

For rapid development with hot reload:

```bash
# Install dependencies
pip install -e ".[dev]"
# or with uv
uv tool install --editable ".[dev]"

# Start dev servers (API + Web)
make dev
```

Then open [http://localhost:3000](http://localhost:3000). Both API and Web servers auto-reload on file changes.

### Option 2: Docker Containerized

For isolated development environment:

```bash
make dev-docker
```

Services run in containers with hot reload via bind mounts.

## Prerequisites

### For Native Development

- **Python 3.9+** (3.11+ recommended)
- **Node.js 18+**
- **pnpm** (recommended) or **npm** v9+
- **SQLite 3** (usually pre-installed)
- **Git**

Check versions:

```bash
python --version
node --version
pnpm --version
```

### For Docker Development

- **Docker Engine** v24+
- **Docker Compose** v2.0+

## Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/skillmeat.git
cd skillmeat
```

### Step 2: Create Virtual Environment

```bash
# Using venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using uv (faster)
uv venv
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
# With development dependencies
pip install -e ".[dev]"

# Or with uv
uv tool install --editable ".[dev]"
```

This installs:
- Core dependencies (FastAPI, SQLAlchemy, etc.)
- Development tools (pytest, black, mypy, flake8)
- Web dependencies (Next.js, React, etc.)

### Step 4: Install Node/Web Dependencies

```bash
cd skillmeat/web
pnpm install
cd ../..
```

### Step 5: Create Environment File

Copy the local example:

```bash
cp .env.local.example .env
```

For development with authentication:

```bash
cp .env.local-auth.example .env
# Add Clerk keys if testing authentication
```

## Development Commands

All development commands are available through the **Makefile**. View all targets:

```bash
make help
```

### Starting Development Servers

#### Native (Recommended for Rapid Development)

Start both API and Web servers with hot reload:

```bash
make dev
```

This runs:
- API: `skillmeat web dev --api-only` (port 8080, auto-reload)
- Web: `skillmeat web dev --web-only` (port 3000, hot module reload)

Then open:
- Web UI: [http://localhost:3000](http://localhost:3000)
- API docs: [http://localhost:8080/docs](http://localhost:8080/docs)

#### API Only

```bash
make dev-api
```

Useful when working on backend only.

#### Web Only

```bash
make dev-web
```

Useful when working on frontend only.

#### Docker Containerized

For containerized development with hot reload:

```bash
make dev-docker
```

Services run in containers with code directories bind-mounted. Changes to source files trigger rebuilds automatically.

Access at [http://localhost:3000](http://localhost:3000).

## Testing

### Run All Tests

```bash
make test
```

This runs:
- Python tests with coverage
- Web (Next.js) tests

### Run Python Tests Only

```bash
make test-python
```

View test coverage report:

```bash
pytest -v --cov=skillmeat --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Run Web Tests Only

```bash
make test-web
```

Run specific test file:

```bash
cd skillmeat/web
pnpm test -- --testPathPattern="src/__tests__/home.test.tsx"
```

Watch mode (re-run on changes):

```bash
cd skillmeat/web
pnpm test -- --watch
```

### Run Integration Tests

```bash
make test-integration
```

These tests require PostgreSQL (enterprise edition) or use SQLite shim.

### Test Coverage

```bash
# Python coverage
pytest -v --cov=skillmeat --cov-report=term-missing

# HTML report
pytest -v --cov=skillmeat --cov-report=html
open htmlcov/index.html
```

Minimum coverage: **80%** for new features.

## Code Quality

### Format Code

```bash
make format
```

Applies Black formatter to all Python files.

### Check Linting

```bash
make lint
```

Runs flake8 to check for errors and style issues.

### Type Check

```bash
make typecheck
```

Runs mypy to check type annotations. For web:

```bash
cd skillmeat/web
pnpm type-check
```

### All Quality Checks

```bash
# Run format, lint, and typecheck
make format lint typecheck
```

Pre-commit hook runs these automatically.

## Database Operations

### Create & Initialize Database

Automatically done on first startup. Manual reset:

```bash
make db-reset
```

### Run Migrations

```bash
# Apply pending migrations
make db-migrate

# View migration status
docker compose exec api alembic current

# Rollback one migration
docker compose exec api alembic downgrade -1
```

### Seed Database

```bash
make db-seed
```

Adds sample artifacts and collections for testing.

### Access Database

For native development (SQLite):

```bash
sqlite3 ~/.skillmeat/skillmeat.db
```

For Docker development (SQLite):

```bash
docker compose exec api sqlite3 ~/.skillmeat/skillmeat.db
```

For enterprise (PostgreSQL):

```bash
docker compose exec postgres psql -U skillmeat -d skillmeat
```

## Debugging

### Python Debugger (Native)

Add breakpoint in code:

```python
def my_function():
    breakpoint()  # Execution pauses here
    return result
```

Run with API server:

```bash
make dev-api
```

Debugger prompt appears in terminal. Commands:

```
(Pdb) n          # Next line
(Pdb) c          # Continue
(Pdb) s          # Step into function
(Pdb) p var      # Print variable
(Pdb) l          # List current code
(Pdb) h          # Help
```

### Python Debugger (Docker)

Enable debug port in docker-compose.override.yml:

```yaml
services:
  skillmeat-api:
    ports:
      - "5678:5678"
    environment:
      - SKILLMEAT_DEBUG=1
```

Connect from IDE (VS Code, PyCharm):

```
Host: localhost
Port: 5678
```

### API Logs

View real-time API logs:

```bash
make dev-api  # Shows logs in terminal

# Or in separate terminal
docker compose logs -f api
```

Enable more verbose logging in `.env`:

```bash
SKILLMEAT_LOG_LEVEL=DEBUG
```

### Web Logs

Browser console logs appear in terminal when running `make dev-web`.

View in browser:
- Open DevTools: F12 or Cmd+Option+I
- Console tab

### Database Query Logging

Enable SQLAlchemy query logging:

```python
# In Python code
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

Or set environment variable:

```bash
SQLALCHEMY_ECHO=1 make dev-api
```

## Docker Development

### Docker with Hot Reload

```bash
make dev-docker
```

Code changes trigger automatic rebuilds. Volumes map to host directories:

- `/app/skillmeat/` → `./skillmeat/` (source code)
- `/app/skillmeat/web/` → `./skillmeat/web/` (web code)

### Run Docker Containers Individually

```bash
# Build API image
make build-api

# Build Web image
make build-web

# Build all
make build
```

### Enter Container Shell

```bash
# API container
docker compose exec api /bin/bash

# Web container
docker compose exec web /bin/sh
```

### Run Commands in Container

```bash
# Run pytest in API container
docker compose exec api pytest -v

# Run pnpm in Web container
docker compose exec web pnpm test
```

## Environment Variables

Development environment file (`.env`):

```bash
# Application
SKILLMEAT_ENV=development
SKILLMEAT_EDITION=local
SKILLMEAT_LOG_LEVEL=DEBUG

# API
SKILLMEAT_API_PORT=8080
SKILLMEAT_API_HOST=0.0.0.0
SKILLMEAT_WORKERS=1
SKILLMEAT_RELOAD=true

# Web
SKILLMEAT_WEB_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8080

# Collection
SKILLMEAT_COLLECTION_DIR=~/.skillmeat

# Optional: Clerk authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key
CLERK_SECRET_KEY=sk_test_your_key
```

For complete reference, see [Configuration Guide](configuration.md).

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit files in your editor. Both API and Web servers auto-reload:

- **Backend changes**: API auto-reloads (FastAPI with `SKILLMEAT_RELOAD=true`)
- **Frontend changes**: Web hot-reloads (Next.js HMR)

### 3. Run Tests

```bash
make test
```

Before committing, ensure all tests pass:

```bash
make test-python test-web
```

### 4. Check Code Quality

```bash
make format lint typecheck
```

Pre-commit hook runs these checks automatically when you run `git commit`.

### 5. Create Commit

```bash
git add .
git commit -m "feat: description of changes"
```

Pre-commit hooks validate:
- Python formatting (Black)
- Linting (flake8)
- Type checking (mypy)
- No secrets committed

Fix any issues and commit again.

### 6. Push & Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Common Development Tasks

### Add Python Dependency

```bash
# Add to pyproject.toml
pip install package-name

# Record in lock file
pip freeze > requirements.txt
```

### Add JavaScript/Web Dependency

```bash
cd skillmeat/web
pnpm add package-name
pnpm install  # Update lock file
```

### Create Database Migration

```bash
# Generate migration file
docker compose exec api alembic revision --autogenerate -m "Description of change"

# Review generated file in skillmeat/cache/migrations/versions/

# Apply migration
docker compose exec api alembic upgrade head
```

### Create New API Endpoint

1. Create router in `skillmeat/api/routers/`
2. Define request/response schemas in `skillmeat/api/schemas/`
3. Implement business logic using repositories
4. Add tests in `tests/api/test_*.py`
5. Check OpenAPI docs at [http://localhost:8080/docs](http://localhost:8080/docs)

### Create New Web Component

1. Create component in `skillmeat/web/components/`
2. Use Radix UI primitives for accessibility
3. Add Storybook story in `.storybook/`
4. Add tests in `skillmeat/web/__tests__/`
5. Run `pnpm test` to verify

## Troubleshooting

### Port Already in Use

Kill process on port:

```bash
# macOS/Linux
lsof -ti:3000 | xargs kill -9
lsof -ti:8080 | xargs kill -9

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

Or use different ports in `.env`:

```bash
SKILLMEAT_WEB_PORT=3001
SKILLMEAT_API_PORT=8081
make dev
```

### Virtual Environment Issues

```bash
# Recreate venv
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Node Modules Issues

```bash
# Clear pnpm cache
pnpm store prune
rm -rf skillmeat/web/node_modules
cd skillmeat/web
pnpm install
cd ../..
```

### Database Locked

```bash
# SQLite lock
rm ~/.skillmeat/skillmeat.db
make dev  # Recreates database
```

### Tests Fail Randomly

```bash
# Run with verbose output
pytest -v -s

# Run single test multiple times
pytest -v tests/test_something.py -x --count=10
```

### Hot Reload Not Working

Ensure `SKILLMEAT_RELOAD=true` in `.env`:

```bash
SKILLMEAT_RELOAD=true make dev-api
```

For Docker:

```bash
make dev-docker
```

## Performance Tips

### Speed Up Tests

```bash
# Run only fast tests (skip integration tests)
pytest -v -m "not integration"

# Run specific test
pytest -v tests/test_module.py::test_function

# Run in parallel
pytest -v -n auto
```

### Speed Up Builds

```bash
# Use --no-cache only if necessary
docker compose build --no-cache

# Otherwise, Docker uses layer cache for speed
```

### Reduce Web Build Time

```bash
# Skip Next.js telemetry
NEXT_TELEMETRY_DISABLED=1 pnpm build
```

## Pre-Commit Hooks

Pre-commit hooks automatically run on `git commit`:

```bash
# View all hooks
cat .pre-commit-config.yaml

# Run hooks manually
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

Hooks verify:
- Black formatting
- flake8 linting
- mypy type checking
- No secrets in commits

## IDE Setup

### VS Code

Install extensions:
- Python (Microsoft)
- Pylance
- ES7+ React/Redux/React-Native snippets

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

1. Set Python interpreter: Settings → Project → Python Interpreter
2. Point to `.venv/bin/python`
3. Enable pytest: Settings → Tools → Python Integrated Tools

### Debugging in IDE

**VS Code** — Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: API Debug",
      "type": "python",
      "request": "launch",
      "module": "skillmeat.cli",
      "args": ["web", "dev", "--api-only"],
      "justMyCode": true
    }
  ]
}
```

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for full contribution guidelines.

## Next Steps

- **[Testing Strategy](../../docs/development/testing.md)** — Full testing guide
- **[API Documentation](../../docs/api/README.md)** — API endpoint reference
- **[Contributing Guide](../../CONTRIBUTING.md)** — Code of conduct and process
- **[Architecture](../../docs/architecture/overview.md)** — System design

## Support

For development setup issues:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review [CONTRIBUTING.md](../../CONTRIBUTING.md)
3. Check existing issues on GitHub
4. Ask in discussions or create an issue
