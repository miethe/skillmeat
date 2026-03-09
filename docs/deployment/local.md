---
title: Local Deployment Guide
description: Run SkillMeat locally with SQLite for personal testing and development, with optional authentication
audience: developers, self-hosting users, power users
tags:
- deployment
- local
- sqlite
- docker
- zero-config
created: 2026-03-08
updated: 2026-03-08
category: operational
status: active
related_documents:
- docs/deployment/README.md
- docs/deployment/development.md
- docs/deployment/configuration.md
- docs/deployment/enterprise.md
---

# Local Deployment Guide

Run SkillMeat locally with SQLite for personal testing, development, and single-user collections. Choose between zero-config (no authentication) or lightweight authentication with Clerk.

## Quick Start

### Option 1: Zero-Config Local (No Authentication)

Fastest path for testing and personal use. No login required.

```bash
cp .env.local.example .env
docker compose --profile local up -d
```

Then open [http://localhost:3000](http://localhost:3000).

### Option 2: Local with Authentication (Clerk)

Personal use with login and team-ready authentication.

```bash
cp .env.local-auth.example .env
# Edit .env and set Clerk keys (see Authentication section below)
docker compose --profile local-auth up -d
```

Then open [http://localhost:3000](http://localhost:3000).

## Prerequisites

- **Docker Engine** v24 or later
- **Docker Compose** v2.0 or later (included in Docker Desktop)
- **2 GB RAM** minimum
- **2 GB disk space** for SQLite database and artifacts

## Architecture

Local deployment uses SQLite as the backend database, stored in `~/.skillmeat/`:

```
~/.skillmeat/
├── collection/            # Your artifact library
├── skillmeat.db          # SQLite database
└── snapshots/            # Version history
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| API (FastAPI) | 8080 | Backend REST API |
| Web (Next.js) | 3000 | Frontend web interface |

## Installation & Setup

### Step 1: Initialize Configuration

Copy the environment template for your edition:

**Zero-config (no auth):**
```bash
cp .env.local.example .env
```

**With authentication:**
```bash
cp .env.local-auth.example .env
```

### Step 2: Configure Authentication (Optional)

If using the `local-auth` profile, you need Clerk credentials for login.

#### Get Clerk Keys

1. Go to [clerk.com](https://clerk.com) and create a free account
2. Create a new application
3. Copy your **Publishable Key** and **Secret Key**
4. Add them to `.env`:

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_publishable_key
CLERK_SECRET_KEY=sk_test_your_secret_key
```

### Step 3: Start Services

**Zero-config:**
```bash
docker compose --profile local up -d
```

**With authentication:**
```bash
docker compose --profile local-auth up -d
```

Wait ~30 seconds for services to be ready. Check status:

```bash
docker compose ps
```

Expected output:
```
NAME                      IMAGE                      STATUS
skillmeat-api-1          skillmeat:latest           Up 30 seconds (healthy)
skillmeat-web-1          node:18-alpine             Up 25 seconds (healthy)
```

### Step 4: Access the Web UI

Open [http://localhost:3000](http://localhost:3000) in your browser.

- **Zero-config**: You're logged in immediately as the default user
- **With auth**: Log in with your Clerk account

## Data Persistence

### Docker Volumes

Local data is stored in a Docker named volume `skillmeat-data`, which maps to `~/.skillmeat/` on your host:

```bash
# View data location
docker volume inspect skillmeat-data

# Manually browse data
ls ~/.skillmeat/
```

### Preserving Data Across Restarts

Data persists automatically when you restart containers:

```bash
# Stop (preserves data)
docker compose down

# Start again (data still there)
docker compose --profile local up -d
```

To remove all data and start fresh:

```bash
docker compose down -v
```

## Common Operations

### View Logs

View all service logs:
```bash
docker compose logs -f
```

View specific service:
```bash
docker compose logs -f api
docker compose logs -f web
```

View last 50 lines with timestamps:
```bash
docker compose logs -f --tail=50 --timestamps api
```

### Restart Services

Restart all services:
```bash
docker compose restart
```

Restart specific service:
```bash
docker compose restart api
```

### Access Database

Open SQLite database directly:

```bash
docker compose exec api sqlite3 ~/.skillmeat/skillmeat.db
```

Then run SQL queries:
```sql
-- List all artifacts
SELECT id, name, type, scope FROM artifacts;

-- Check database size
SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();

.quit
```

Or use the CLI to interact with your collection:
```bash
docker compose exec api skillmeat list
docker compose exec api skillmeat search "skill-name"
```

### Update to Latest Version

Pull the latest images and restart:

```bash
docker compose pull
docker compose --profile local up -d
```

## Troubleshooting

### Port Already in Use

If port 3000 or 8080 is already in use, override in `.env`:

```bash
SKILLMEAT_WEB_PORT=3001
SKILLMEAT_API_PORT=8081
docker compose --profile local up -d
```

Then access at [http://localhost:3001](http://localhost:3001).

### "Permission Denied" on ~/.skillmeat/

The API container runs as non-root. Fix permissions:

```bash
chmod 755 ~/.skillmeat
docker compose restart api
```

### Database Locked Error

SQLite occasionally locks during concurrent writes. If you see "database is locked":

```bash
# Stop all containers
docker compose down

# Remove old database and let it be recreated
rm ~/.skillmeat/skillmeat.db

# Restart
docker compose --profile local up -d
```

### Web UI Won't Load

Check if services are healthy:

```bash
docker compose ps
```

If not healthy, view logs:

```bash
docker compose logs api | tail -50
docker compose logs web | tail -50
```

### API Returns 500 Error

View detailed API logs:

```bash
docker compose logs -f api
```

Common issues:
- Database corruption: Try `docker compose down -v` (wipes data)
- Out of disk space: Free up space and restart

### Migrations Fail on Startup

If API won't start with migration errors:

```bash
# View full startup logs
docker compose logs api

# Manually reset database
docker compose exec api sqlite3 ~/.skillmeat/skillmeat.db "DROP TABLE IF EXISTS alembic_version;"

# Restart API to re-run migrations
docker compose restart api
```

## Network & Connectivity

### Accessing from Other Machines

By default, services listen on `0.0.0.0` (all interfaces). From another machine on your network:

```bash
# Get your host IP
hostname -I  # Linux
ipconfig     # Windows
ifconfig     # macOS

# Access from another machine
# Replace YOURIP with the IP above
http://YOURIP:3000
```

To restrict to localhost only, edit `.env`:

```bash
SKILLMEAT_API_HOST=127.0.0.1
```

### Docker Desktop VM Network

Docker Desktop runs containers in a VM. To access from your host:
- Use `localhost:3000` / `localhost:8080` (Docker Desktop handles routing)
- Services inside containers access each other via container names (`skillmeat-api:8080`)

## Environment Variables

Key variables for local deployment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SKILLMEAT_EDITION` | `local` | Edition type |
| `SKILLMEAT_ENV` | `development` | Runtime environment |
| `SKILLMEAT_API_PORT` | `8080` | API server port |
| `SKILLMEAT_WEB_PORT` | `3000` | Web server port |
| `SKILLMEAT_COLLECTION_DIR` | `~/.skillmeat` | Local data directory |

For complete reference, see [Configuration Guide](configuration.md).

## Performance Tips

### SQLite Optimization

For better performance with large collections:

```bash
# Open database
docker compose exec api sqlite3 ~/.skillmeat/skillmeat.db

# Run optimization
PRAGMA optimize;
.quit
```

### Increase API Workers

If API feels slow, increase worker processes in `.env`:

```bash
SKILLMEAT_WORKERS=2
docker compose restart api
```

(Local profile supports 1-4 workers; enterprise supports up to 8)

## Backup & Restore

### Manual Backup

Backup your collection and database:

```bash
# Create backup directory
mkdir -p ~/skillmeat-backups
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

# Copy data directory
cp -r ~/.skillmeat ~/skillmeat-backups/skillmeat-$BACKUP_DATE

# Verify backup
ls ~/skillmeat-backups/
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Restore backup
rm -rf ~/.skillmeat
cp -r ~/skillmeat-backups/skillmeat-YYYYMMDD-HHMMSS ~/.skillmeat

# Start services
docker compose --profile local up -d
```

## Cleanup

### Stop Services (Keep Data)

```bash
docker compose down
```

Data remains in `~/.skillmeat/` and Docker volume. Restart anytime:

```bash
docker compose --profile local up -d
```

### Complete Removal (Delete Data)

Remove services and all data:

```bash
docker compose down -v
rm -rf ~/.skillmeat
```

## Next Steps

- **[Configuration Reference](configuration.md)** — All environment variables
- **[Development Guide](development.md)** — Native setup with hot reload
- **[Enterprise Deployment](enterprise.md)** — PostgreSQL + team features
- **[Main Deployment Guide](README.md)** — Choose deployment pattern

## Support

For deployment issues:

1. Check [Troubleshooting](#troubleshooting) section above
2. View logs: `docker compose logs -f`
3. Check [Configuration Guide](configuration.md) for variable reference
4. See [Enterprise Deployment](enterprise.md) for production hardening
