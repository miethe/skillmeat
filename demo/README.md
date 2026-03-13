# SkillMeat Backstage Integration Demo

Docker Compose stack for the SkillMeat / Backstage IDP integration demo.

## Services

| Service | URL | Profile |
|---|---|---|
| SkillMeat API | http://localhost:8080 | `full`, `api-only` |
| SkillMeat Web UI | http://localhost:3000 | `full` |
| Backstage | http://localhost:7007 | `full`, `backstage-only` |
| Demo DB (PostgreSQL) | localhost:5433 | `full`, `api-only`, `backstage-only` |

## Quick Start

```bash
# Full stack (API + Web + Backstage + demo-db):
./compose.sh --profile full up

# API + demo-db only (faster, good for backend/API demos):
./compose.sh --profile api-only up

# Backstage only (uses already-running SkillMeat API on host):
SKILLMEAT_API_URL=http://host.containers.internal:8080 \
  ./compose.sh --profile backstage-only up

# Stop (data volume preserved):
./compose.sh down

# Stop + wipe database:
./compose.sh down -v
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

Connection details: `postgresql://demo:demo_password@localhost:5433/demo_finserv`

## Backstage Setup

The Backstage app lives at `demo/backstage-app/` inside this repo.
Run these steps once from the repo root before starting any profile that includes Backstage.

### 1. Create the Backstage app

```bash
cd demo
npx @backstage/create-app@latest --path backstage-app --skip-install
# When prompted for a name enter: backstage-app
cd backstage-app
```

### 2. Set up the SkillMeat scaffolder plugin

Copy the plugin into the backstage-app workspace and add it as a dependency:

```bash
# Copy plugin source
cp -r ../../plugins/backstage-plugin-scaffolder-backend plugins/
```

Edit `packages/backend/package.json` and add to `dependencies`:

```json
"@skillmeat/backstage-plugin-scaffolder-backend": "link:../../plugins/backstage-plugin-scaffolder-backend"
```

Register the module in `packages/backend/src/index.ts` after the other scaffolder imports:

```typescript
backend.add(
  import('@skillmeat/backstage-plugin-scaffolder-backend'),
);
```

### 3. Apply the demo app-config

```bash
cp ../backstage-app-config.yaml app-config.local.yaml
```

Edit `app-config.local.yaml` and set your `GITHUB_TOKEN` if you want live catalog integrations.

### 4. Build the Backstage backend

```bash
# If Node/Yarn is installed on the host:
yarn install --no-immutable
yarn workspace @skillmeat/backstage-plugin-scaffolder-backend build
yarn tsc
yarn build:backend

# Without Node on the host (use a container):
podman run --rm -v "$(pwd):/app:Z" -w /app -e HOME=/tmp node:24-slim \
  sh -c 'corepack enable && yarn install --no-immutable && \
    yarn workspace @skillmeat/backstage-plugin-scaffolder-backend build && \
    yarn tsc && yarn build:backend'
```

### 5. Build the container image

From the repo root:

```bash
# Docker:
docker compose -f docker-compose.yml build backstage

# Podman:
BUILDAH_FORMAT=docker podman build --format docker \
  -t skillmeat-demo_backstage \
  -f demo/dockerfile demo/backstage-app
```

### 6. Start Backstage

```bash
# Full stack:
./compose.sh --profile full up

# Against an already-running SkillMeat API on the host:
SKILLMEAT_API_URL=http://host.containers.internal:8080 \
  ./compose.sh --profile backstage-only up

# Use a separate project name if the enterprise profile is already running:
SKILLMEAT_API_URL=http://host.containers.internal:8080 \
  podman-compose -p skillmeat-demo --profile backstage-only up -d
```

### Rebuilding after plugin changes

```bash
# Rebuild plugin + backend (from demo/backstage-app):
podman run --rm -v "$(pwd):/app:Z" -w /app -e HOME=/tmp node:24-slim \
  sh -c 'corepack enable && \
    yarn workspace @skillmeat/backstage-plugin-scaffolder-backend build && \
    yarn build:backend'

# Rebuild image (from repo root):
BUILDAH_FORMAT=docker podman build --format docker \
  -t skillmeat-demo_backstage -f demo/dockerfile demo/backstage-app

# Restart:
podman-compose -p skillmeat-demo --profile backstage-only up -d --force-recreate backstage
```

## Troubleshooting

**`ERR_SSL_PROTOCOL_ERROR` in browser**: Backstage's default Helmet headers may cause
browsers to cache an HTTPS upgrade policy. Clear the HSTS entry for your host:
- Chrome: `chrome://net-internals/#hsts` - Delete domain
- Firefox: Clear site data for the host
Then access `http://<host>:7007` explicitly.

**Port 5433 already in use**: A leftover `demo-db` container may be bound. Run
`podman ps -a | grep demo` to find it, then `podman rm -f <id>`.

**Pod conflicts with enterprise profile**: Use a separate project name:
`podman-compose -p skillmeat-demo --profile backstage-only up -d`

See `plugins/backstage-plugin-scaffolder-backend/README.md` for full plugin documentation.
