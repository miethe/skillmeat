---
title: "Server Setup Guide"
description: "Configure SkillMeat server deployment: local mode with SQLite, enterprise mode with PostgreSQL, environment variables, and production best practices"
domain: "operations"
category: "guides"
subcategory: "deployment"
created: 2026-03-08
last_updated: 2026-03-08
tags: ["setup", "deployment", "database", "sqlite", "postgresql", "server", "configuration"]
---

# Server Setup Guide

## Overview

SkillMeat runs as a FastAPI backend + Next.js frontend. Choose the edition that matches your use case:

| Aspect | Local Edition | Enterprise Edition |
|--------|--------------|-------------------|
| Database | SQLite (automatic) | PostgreSQL (you provide) |
| Setup effort | Zero-config | Requires DB provisioning |
| Multi-tenant | No | Yes |
| Scaling | Single instance | Multiple workers, horizontal |
| Auth default | Zero-auth (local auth) | Configurable |
| Best for | Personal use, development | Teams, production deployments |

**In a hurry?** Jump to [Quick Start](#quick-start-local-edition).

## Quick Start (Local Edition)

```bash
# Install
pip install skillmeat  # or: uv tool install skillmeat

# Initialize collection
skillmeat init

# Start development servers (API + Next.js)
skillmeat web dev
```

That's it. SQLite database is created automatically at `~/.skillmeat/skillmeat.db`.

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API docs**: http://localhost:8080/docs

## Local Edition Setup

### Prerequisites

- Python 3.9+
- Node.js 18+ (for web frontend)
- pnpm (for frontend package management)

### Environment Variables

Core settings for local development (all optional — defaults work out of the box):

```bash
# .env file in project root (or export these)
SKILLMEAT_ENV=development
SKILLMEAT_HOST=127.0.0.1
SKILLMEAT_PORT=8080
SKILLMEAT_LOG_LEVEL=INFO
SKILLMEAT_LOG_FORMAT=text      # "text" for dev, "json" for production
SKILLMEAT_RELOAD=true          # Auto-reload on code changes
```

### Database

SQLite is used automatically. The database file lives at `~/.skillmeat/skillmeat.db`. No configuration needed.

To override the collection directory:

```bash
SKILLMEAT_COLLECTION_DIR=/custom/path/to/collections
```

### Running the Server

```bash
# Development (both API + frontend with hot reload)
skillmeat web dev

# API only
skillmeat web dev --api-only

# Frontend only (assumes API running separately)
skillmeat web dev --web-only

# Check environment health
skillmeat web doctor
```

### GitHub Token (Optional)

If working with private repositories or want higher API rate limits:

```bash
SKILLMEAT_GITHUB_TOKEN=ghp_your_personal_access_token
```

SkillMeat also checks `GITHUB_TOKEN` environment variable as a fallback.

## Enterprise Edition Setup

Enterprise edition uses PostgreSQL for production-grade deployments with multi-tenant support.

### Prerequisites

- Everything from Local Edition, plus:
- PostgreSQL 14+ with a dedicated database
- Network access from SkillMeat server to PostgreSQL

### Step 1: Provision PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE USER skillmeat WITH PASSWORD 'your-secure-password';
CREATE DATABASE skillmeat_db OWNER skillmeat;
GRANT ALL PRIVILEGES ON DATABASE skillmeat_db TO skillmeat;
\q
```

Verify the connection:

```bash
psql postgresql://skillmeat:your-secure-password@localhost:5432/skillmeat_db -c "SELECT 1"
```

### Step 2: Configure Environment

```bash
# Set edition to enterprise
export SKILLMEAT_EDITION=enterprise

# PostgreSQL connection
export DATABASE_URL=postgresql://skillmeat:your-secure-password@localhost:5432/skillmeat_db

# Optional: override default host/port
export SKILLMEAT_HOST=0.0.0.0
export SKILLMEAT_PORT=8080
```

Or create a `.env` file:

```bash
SKILLMEAT_EDITION=enterprise
DATABASE_URL=postgresql://skillmeat:your-secure-password@localhost:5432/skillmeat_db
SKILLMEAT_HOST=0.0.0.0
SKILLMEAT_PORT=8080
```

### Step 3: Run Database Migrations

From the SkillMeat repository root:

```bash
alembic upgrade head
```

This creates all required tables including enterprise-specific schemas (teams, audit logs, tenant isolation).

Check migration status:

```bash
alembic current
```

### Step 4: Start the Server

**Development:**
```bash
SKILLMEAT_EDITION=enterprise skillmeat web dev --api-only
```

**Production (with multiple workers):**
```bash
SKILLMEAT_EDITION=enterprise uvicorn skillmeat.api.server:app \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 4
```

## Production Deployment

### Environment Configuration

```bash
# Core
SKILLMEAT_ENV=production
SKILLMEAT_EDITION=enterprise     # or "local" for single-user production
SKILLMEAT_HOST=0.0.0.0
SKILLMEAT_PORT=8080
SKILLMEAT_WORKERS=4
SKILLMEAT_LOG_LEVEL=INFO
SKILLMEAT_LOG_FORMAT=json        # Structured logging for production

# Database (PostgreSQL)
DATABASE_URL=postgresql://skillmeat:password@db.example.com:5432/skillmeat_db

# CORS (restrict to your frontend domain)
SKILLMEAT_CORS_ORIGINS='["https://your-app.example.com"]'

# Rate limiting
SKILLMEAT_RATE_LIMIT_ENABLED=true
SKILLMEAT_RATE_LIMIT_REQUESTS=100

# GitHub integration (for artifact discovery)
SKILLMEAT_GITHUB_TOKEN=ghp_your_token
```

### Running with Uvicorn

```bash
uvicorn skillmeat.api.server:app \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 4 \
  --log-level info
```

For systemd service management, see [systemd Service Setup](#systemd-service-setup).

### Building the Frontend

```bash
# Build production frontend
skillmeat web build

# Start production servers
skillmeat web start
```

### Reverse Proxy Setup

**nginx example:**

```nginx
upstream skillmeat_api {
    server 127.0.0.1:8080;
}

upstream skillmeat_web {
    server 127.0.0.1:3000;
}

server {
    listen 443 ssl http2;
    server_name skillmeat.example.com;

    ssl_certificate /etc/letsencrypt/live/skillmeat.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skillmeat.example.com/privkey.pem;

    # API endpoints
    location /api/ {
        proxy_pass http://skillmeat_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://skillmeat_web;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name skillmeat.example.com;
    return 301 https://$server_name$request_uri;
}
```

**Apache example:**

```apache
ProxyPreserveHost On
ProxyPass /api/ http://127.0.0.1:8080/api/
ProxyPassReverse /api/ http://127.0.0.1:8080/api/
ProxyPass / http://127.0.0.1:3000/
ProxyPassReverse / http://127.0.0.1:3000/
```

### systemd Service Setup

Create `/etc/systemd/system/skillmeat.service`:

```ini
[Unit]
Description=SkillMeat Server
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=skillmeat
WorkingDirectory=/opt/skillmeat
EnvironmentFile=/opt/skillmeat/.env
ExecStart=/usr/local/bin/uvicorn skillmeat.api.server:app \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable skillmeat
sudo systemctl start skillmeat

# Check status
sudo systemctl status skillmeat
sudo journalctl -u skillmeat -f
```

## Feature Flags

Control optional features via environment variables:

| Feature | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Auto-discovery | `SKILLMEAT_ENABLE_AUTO_DISCOVERY` | `true` | Scan for artifacts automatically |
| Auto-population | `SKILLMEAT_ENABLE_AUTO_POPULATION` | `true` | Populate GitHub metadata |
| Composite artifacts | `SKILLMEAT_COMPOSITE_ARTIFACTS_ENABLED` | `true` | Detect multi-file artifact packages |
| Deployment sets | `SKILLMEAT_DEPLOYMENT_SETS_ENABLED` | `true` | Group deployments |
| Memory system | `SKILLMEAT_MEMORY_CONTEXT_ENABLED` | `true` | Memory items and context modules |
| Workflow engine | `SKILLMEAT_WORKFLOW_ENGINE_ENABLED` | `true` | Workflow orchestration |

## Health Checks

```bash
# Server health endpoint
curl http://localhost:8080/health
# Response: {"status": "ok"}

# Database connectivity (enterprise only)
curl http://localhost:8080/api/v1/health/db

# Environment diagnostics
skillmeat web doctor
```

Add to your monitoring/load balancer:

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30

# Readiness probe
readinessProbe:
  httpGet:
    path: /api/v1/health/db
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Troubleshooting

### Server won't start

**Port already in use:**
```bash
lsof -i :8080
# Kill the process if needed
kill -9 <PID>
```

**Python version:**
```bash
python --version  # Must be 3.9 or higher
```

**Dependencies missing:**
```bash
pip install -e .  # Reinstall from source
# or
pip install skillmeat --upgrade
```

### Database errors

**SQLite connection issue:**
```bash
# Check directory exists and is writable
ls -la ~/.skillmeat/
chmod 755 ~/.skillmeat/
```

**PostgreSQL connection issue:**
```bash
# Test connection directly
psql $DATABASE_URL -c "SELECT 1"

# Check credentials
echo $DATABASE_URL

# Verify PostgreSQL is running
psql -U postgres -c "SELECT version();"
```

**Migration errors:**
```bash
# Check current migration status
alembic current

# Show pending migrations
alembic history

# Apply migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Frontend build issues

**Node.js version:**
```bash
node --version  # Must be 18 or higher
```

**pnpm missing:**
```bash
npm install -g pnpm
pnpm --version
```

**Build failures:**
```bash
# Clean dependencies
rm -rf node_modules
pnpm install

# Rebuild
skillmeat web build
```

### Performance issues

**Enable query logging:**
```bash
SKILLMEAT_LOG_LEVEL=DEBUG
SQLALCHEMY_ECHO=true
```

**Adjust worker count:**
```bash
# Rule of thumb: (2 × CPU cores) + 1
SKILLMEAT_WORKERS=5
```

**Monitor resource usage:**
```bash
# CPU and memory
top -p $(pgrep -f uvicorn)

# Database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

## Configuration Reference

Environment profiles in the repository root provide ready-to-use templates:

| Profile | Command | Use Case |
|---------|---------|----------|
| [`.env.example`](../../../.env.example) | `cp .env.example .env` | Local dev, zero-auth |
| [`.env.local-auth.example`](../../../.env.local-auth.example) | `cp .env.local-auth.example .env` | Small teams, API key auth |
| [`.env.enterprise.example`](../../../.env.enterprise.example) | `cp .env.enterprise.example .env` | Production, PostgreSQL + Clerk |

Key categories:
- **Server**: `SKILLMEAT_*`
- **Database**: `DATABASE_URL`, `SQLALCHEMY_*`
- **Logging**: `SKILLMEAT_LOG_LEVEL`, `SKILLMEAT_LOG_FORMAT`
- **Features**: `SKILLMEAT_ENABLE_*`
- **Auth**: `SKILLMEAT_AUTH_*`
- **GitHub**: `SKILLMEAT_GITHUB_TOKEN`

## Next Steps

- [Quickstart Guide](../quickstart.md) — Get up and running in 5 minutes
- [Authentication Setup](authentication-setup.md) — Configure auth providers (GitHub, Clerk, etc.)
- [Web UI Guide](web-ui-guide.md) — Using the web interface
- [CLI Commands Reference](cli/commands.md) — Full command documentation
