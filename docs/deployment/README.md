---
title: Deployment Guide
description: Get SkillMeat running locally or in production with Docker Compose and unified deployment profiles
audience: developers, operators, self-hosting users
tags:
- deployment
- docker
- docker-compose
- local-development
- production
created: 2026-03-08
updated: 2026-03-08
category: operational
status: active
related_documents:
- docs/deployment/local.md
- docs/deployment/enterprise.md
- docs/deployment/development.md
- docs/deployment/configuration.md
- docs/ops/operations-guide.md
---

# Deployment Guide

Get SkillMeat running in under 5 minutes using Docker Compose with unified deployment profiles.

## Quick Start

Choose your deployment pattern below and copy the command into your terminal.

### Local (SQLite, No Authentication)

Perfect for personal testing and development without login requirements.

```bash
cp .env.local.example .env && ./compose.sh --profile local up -d
```

Then open [http://localhost:3000](http://localhost:3000).

### Local with Authentication (SQLite + Clerk)

Personal use with login and authentication via Clerk.

```bash
cp .env.local-auth.example .env && ./compose.sh --profile local-auth up -d
```

You'll need a Clerk application configured in your `.env` file. See [Local Authentication Setup](local.md#authentication).

### Enterprise (PostgreSQL + Monitoring)

Team deployment with PostgreSQL, enterprise authentication, and optional monitoring stack (Prometheus, Grafana, Loki).

```bash
cp .env.enterprise.example .env && ./compose.sh --profile enterprise -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

Then open [http://localhost:3000](http://localhost:3000). Full setup guide: [Enterprise Deployment](enterprise.md).

## Which Pattern Should I Use?

Use this decision tree to find your deployment pattern:

| Scenario | Pattern | Why |
|----------|---------|-----|
| **Testing SkillMeat locally** | Local | No database setup, no auth, instant start |
| **Personal collection with login** | Local + Auth | Single-user, persistent auth, SQLite |
| **Team/production deployment** | Enterprise | PostgreSQL, monitoring, multi-user support |
| **Development environment** | [Native / Makefile](development.md) | Hot reload, full debugging, fastest iteration |

## Prerequisites

- **Container Runtime**: Docker Engine v24+ **or** Podman v4.7+
- **Compose Tool**: Docker Compose v2+ (included in Docker Desktop) **or** `podman compose`
- **4 GB RAM** minimum (8 GB recommended for enterprise)
- **5 GB disk space** for all three editions (including monitoring)

Check your versions:

```bash
# Docker
docker --version
docker compose version

# Podman
podman --version
podman compose version
```

### Using the Compose Wrapper (Recommended)

The `compose.sh` wrapper auto-detects Docker vs Podman and runs the correct compose command:

```bash
./compose.sh --profile local up -d
```

Override detection with `COMPOSE_ENGINE=podman ./compose.sh ...` if needed.

### Podman Setup

If using Podman instead of Docker:

1. **Enable the Podman socket** (required for compose compatibility):
   ```bash
   systemctl --user enable --now podman.socket
   ```

2. **Install compose support** (one of):
   - `podman compose` — built-in since Podman 4.7 (recommended)
   - `pip install podman-compose` — standalone fallback

3. **Set `DOCKER_HOST`** if compose tools can't find the socket:
   ```bash
   export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
   ```

> **Note**: The Python-based `docker-compose` v1 is **not compatible** with Podman due to URL scheme issues in the Python `docker` library. Use `podman compose` or `docker compose` v2 instead.

## Deployment Overview

SkillMeat uses unified Docker Compose with edition-specific profiles:

### Services by Edition

| Service | Local | Local + Auth | Enterprise |
|---------|-------|---|-----------|
| API (Python/FastAPI) | ✓ | ✓ | ✓ |
| Web (Next.js) | ✓ | ✓ | ✓ |
| SQLite Database | ✓ | ✓ | — |
| PostgreSQL Database | — | — | ✓ |
| Prometheus (monitoring) | — | — | ✓ (optional) |
| Grafana (dashboards) | — | — | ✓ (optional) |
| Loki (logs) | — | — | ✓ (optional) |

### Compose File Structure

```
docker-compose.yml                    # Unified config with all three profiles
├─ services:
│  ├─ api                            # FastAPI service
│  ├─ web                            # Next.js service
│  ├─ postgres                       # Enterprise database (profile: enterprise)
│  ├─ prometheus                     # Metrics (profile: enterprise)
│  ├─ grafana                        # Dashboards (profile: enterprise)
│  └─ loki                           # Log aggregation (profile: enterprise)
└─ profiles: [local, local-auth, enterprise]

docker-compose.override.yml           # Development overrides (hot reload)
docker-compose.monitoring.yml         # Optional: monitoring addon
```

### Environment Files

All templates are at the repository root:

| File | Edition | Database | Auth |
|------|---------|----------|------|
| `.env.local.example` | local | SQLite | None |
| `.env.local-auth.example` | local | SQLite | Clerk JWT |
| `.env.enterprise.example` | enterprise | PostgreSQL | Clerk JWT + PAT |

Copy the appropriate template to `.env` before deploying.

## Common Tasks

### Start Services

```bash
# Local edition
./compose.sh --profile local up -d

# Local with authentication
./compose.sh --profile local-auth up -d

# Enterprise with monitoring
./compose.sh --profile enterprise -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### Stop Services

```bash
./compose.sh down
```

### View Logs

```bash
# All services
./compose.sh logs -f

# Specific service
./compose.sh logs -f skillmeat-api
./compose.sh logs -f skillmeat-web
```

### Run Database Migrations

Migrations run automatically on API startup via the entrypoint script. To manually trigger:

```bash
./compose.sh exec skillmeat-api alembic upgrade head
```

### Access Database

**Local (SQLite)**:
```bash
./compose.sh exec skillmeat-api sqlite3 ~/.skillmeat/skillmeat.db
```

**Enterprise (PostgreSQL)**:
```bash
./compose.sh exec postgres psql -U skillmeat -d skillmeat
```

### Rebuild Images

```bash
./compose.sh build
```

## Detailed Guides

For detailed information on each deployment pattern, see:

- **[Local Deployment](local.md)** — SQLite setup, volume mounts, native development
- **[Enterprise Deployment](enterprise.md)** — PostgreSQL, monitoring, production hardening
- **[Development Environment](development.md)** — Makefile targets, hot reload, debugging
- **[Configuration Reference](configuration.md)** — All environment variables documented

## Health Checks

All services include health checks. View status:

```bash
docker compose ps
```

Expected output:
```
NAME       IMAGE              STATUS              PORTS
skillmeat-api-1    ...       Up 2 minutes (healthy)   0.0.0.0:8000->8000/tcp
skillmeat-web-1    ...       Up 2 minutes (healthy)   0.0.0.0:3000->3000/tcp
```

## Troubleshooting

### Port Already in Use

If port 3000 or 8000 is already in use:

```bash
# Change ports in .env or override in docker-compose.override.yml
SKILLMEAT_PORT_WEB=3001 docker compose --profile local up -d
```

### Permission Denied on ~/.skillmeat/

The API container runs as non-root. Ensure the host directory is readable:

```bash
chmod 755 ~/.skillmeat
```

### PostgreSQL Connection Fails

Ensure PostgreSQL service is healthy:

```bash
docker compose logs postgres
```

Then verify connection string in `.env` matches the container setup.

### Podman: "Not supported URL scheme http+docker"

This error occurs when using the Python-based `docker-compose` v1 with Podman. Solutions:

1. **Use `./compose.sh`** — it auto-detects Podman and uses the right command
2. **Use `podman compose`** directly (built-in since Podman 4.7)
3. **Ensure socket is running**: `systemctl --user enable --now podman.socket`
4. **Set DOCKER_HOST**: `export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`

### Podman: Permission Denied on Volumes

Podman runs rootless by default. If volume mounts fail:

```bash
podman unshare chown 1000:1000 ~/.skillmeat
```

### Migrations Timeout

Increase startup timeout for API service in docker-compose.override.yml:

```yaml
services:
  api:
    healthcheck:
      timeout: 30
      start_period: 60
```

## Advanced Topics

- **Custom domain/TLS**: See [Enterprise Deployment](enterprise.md#tls)
- **Backup strategies**: See [Enterprise Deployment](enterprise.md#backup)
- **Scaling**: See [Operations Guide](../ops/operations-guide.md)
- **Monitoring dashboards**: See [Enterprise Deployment](enterprise.md#monitoring)

## Next Steps

1. **Choose your pattern** from the table above
2. **Copy the quick-start command** for your edition
3. **Open [http://localhost:3000](http://localhost:3000)** — you're running!
4. **Read the pattern-specific guide** for detailed configuration

## Support

- **Configuration issues** → [Configuration Reference](configuration.md)
- **Deployment-specific questions** → [Pattern Guide](local.md) / [Enterprise Guide](enterprise.md)
- **Development setup** → [Development Guide](development.md)
- **Operations & monitoring** → [Operations Guide](../ops/operations-guide.md)
