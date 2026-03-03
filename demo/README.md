# SkillMeat Backstage Integration Demo

Docker Compose stack for the SkillMeat / Backstage IDP integration demo.

## Services

| Service | URL | Profile |
|---|---|---|
| SkillMeat API | http://localhost:8080 | `full`, `api-only` |
| SkillMeat Web UI | http://localhost:3000 | `full` |
| Backstage (stub) | http://localhost:7007 | `full` |
| PostgreSQL | localhost:5432 | `full`, `api-only` |

## Quick Start

```bash
# Full stack (API + Web + Backstage stub + DB)
docker compose -f docker-compose.demo.yml --profile full up

# API + DB only (faster, good for backend/API demos)
docker compose -f docker-compose.demo.yml --profile api-only up

# Stop (data volume preserved)
docker compose -f docker-compose.demo.yml down

# Stop + wipe database
docker compose -f docker-compose.demo.yml down -v
```

## Prerequisites

- Docker and Docker Compose v2.x
- (Optional) `~/.skillmeat/collection` directory with local artifacts for the API to serve
- (Optional) `SKILLMEAT_GITHUB_TOKEN` env var for live GitHub artifact fetching

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SKILLMEAT_GITHUB_TOKEN` | _(empty)_ | GitHub token for live artifact fetching |
| `GITHUB_TOKEN` | _(empty)_ | GitHub token for Backstage catalog integrations |
| `SKILLMEAT_COLLECTION_PATH` | `~/.skillmeat` | Path to local SkillMeat collection |

Example:

```bash
SKILLMEAT_GITHUB_TOKEN=ghp_xxx \
SKILLMEAT_COLLECTION_PATH=/path/to/collection \
docker compose -f docker-compose.demo.yml --profile full up
```

## Database

The `demo-db` PostgreSQL instance is seeded on first startup from `demo/init-db.sql`.
It contains fictional financial-services data:

- `accounts` - Customer and institutional accounts
- `transactions` - Transaction ledger
- `compliance_checks` - AML/KYC compliance review records
- `audit_log` - Immutable audit trail

Connection details: `postgresql://demo:demo_password@localhost:5432/demo_finserv`

## Backstage Setup

The `backstage` service is a placeholder container that prints setup instructions
on startup. To run a real Backstage instance:

1. Exec into the container and follow the printed instructions, or
2. Set up Backstage on your host and point it at `http://localhost:8080`

Copy `demo/backstage-app-config.yaml` to your Backstage app root as
`app-config.local.yaml` and fill in the required tokens.

See `plugins/backstage-plugin-scaffolder-backend/README.md` for plugin
installation and wiring instructions.
