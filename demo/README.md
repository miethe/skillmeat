# SkillMeat Backstage Integration Demo

Docker Compose stack for the SkillMeat / Backstage IDP integration demo.

## Services

| Service | URL | Profile |
|---|---|---|
| SkillMeat API | http://localhost:8080 | `full`, `api-only` |
| SkillMeat Web UI | http://localhost:3000 | `full` |
| Backstage | http://localhost:7007 | `full`, `backstage-only` |
| PostgreSQL | localhost:5432 | `full`, `api-only` |

## Quick Start

```bash
# With podman-compose (recommended on RHEL/Fedora):
podman-compose -f docker-compose.yml --profile full up

# API + DB only (faster, good for backend/API demos)
podman-compose -f docker-compose.yml --profile api-only up

# Backstage only (uses already-running skillmeat web dev on host)
podman-compose -f docker-compose.yml --profile backstage-only up

# Stop (data volume preserved)
podman-compose -f docker-compose.yml down

# Stop + wipe database
podman-compose -f docker-compose.yml down -v
```

## Prerequisites

- Docker / Podman with Compose support
- (Optional) `~/.skillmeat/collection` directory with local artifacts
- (Optional) `SKILLMEAT_GITHUB_TOKEN` for live GitHub artifact fetching
- Backstage app set up in `demo/backstage-app/` — see **Backstage Setup** below

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SKILLMEAT_GITHUB_TOKEN` | _(empty)_ | GitHub token for live artifact fetching |
| `GITHUB_TOKEN` | _(empty)_ | GitHub token for Backstage catalog integrations |
| `SKILLMEAT_COLLECTION_PATH` | `~/.skillmeat` | Path to local SkillMeat collection |
| `SKILLMEAT_API_URL` | `http://host.containers.internal:8080` | API URL used by Backstage (backstage-only profile) |

Example:

```bash
SKILLMEAT_GITHUB_TOKEN=ghp_xxx \
SKILLMEAT_COLLECTION_PATH=/path/to/collection \
podman-compose -f docker-compose.yml --profile full up
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

The Backstage app lives at `demo/backstage-app/` inside this repo.
Run these steps once from the repo root before starting any profile that includes Backstage.

### 1. Create the Backstage app

```bash
cd demo
npx @backstage/create-app@latest
# When prompted for a name enter: backstage-app
cd backstage-app
```

### 2. Set up the SkillMeat scaffolder plugin

The plugin ships with this repo at `plugins/backstage-plugin-scaffolder-backend/` and is
already copied into `demo/backstage-app/plugins/` as a local workspace package — no npm
install needed. It is also pre-wired into `packages/backend/src/index.ts`.

### 3. Apply the demo app-config

```bash
cp ../backstage-app-config.yaml app-config.local.yaml
```

Edit `app-config.local.yaml` and set your `GITHUB_TOKEN` if you want live catalog integrations.

### 4. Build the Backstage backend

```bash
yarn build:backend
```

### 5. Build the container image

From the repo root:

```bash
# docker (recommended):
docker compose -f docker-compose.yml build backstage

# podman needs BUILDAH_FORMAT=docker for --mount=type=cache in the Dockerfile
# and requires a profile to see the backstage service:
BUILDAH_FORMAT=docker podman-compose -f docker-compose.yml --profile backstage-only build backstage
```

### 6. Start Backstage

```bash
# Against the in-compose API (full profile):
podman-compose -f docker-compose.yml --profile full up

# Against an already-running skillmeat web dev on the host:
podman-compose -f docker-compose.yml --profile backstage-only up
```

### Rebuilding after plugin changes

```bash
cd demo/backstage-app && yarn build:backend && cd ../..
docker compose -f docker-compose.yml build backstage
docker compose -f docker-compose.yml --profile backstage-only up --force-recreate backstage
```

See `plugins/backstage-plugin-scaffolder-backend/README.md` for full plugin documentation.
