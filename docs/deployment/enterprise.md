---
title: Enterprise Deployment Guide
description: Deploy SkillMeat to production with PostgreSQL, Clerk authentication, monitoring, and advanced security
audience: operators, DevOps engineers, system administrators, team leads
tags:
- deployment
- enterprise
- production
- postgresql
- monitoring
- security
created: 2026-03-08
updated: 2026-03-08
category: operational
status: active
related_documents:
- docs/deployment/README.md
- docs/deployment/local.md
- docs/deployment/development.md
- docs/deployment/configuration.md
---

# Enterprise Deployment Guide

Deploy SkillMeat to production with PostgreSQL, Clerk authentication, monitoring, and TLS security. Designed for teams, self-hosted deployments, and multi-tenant scenarios.

## Quick Start

For a complete production setup with monitoring:

```bash
cp .env.enterprise.example .env
# Edit .env with your configuration (see Configuration section)
docker compose --profile enterprise -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

Then open [http://localhost:3000](http://localhost:3000). For TLS and reverse proxy setup, see [TLS & Reverse Proxy](#tls--reverse-proxy).

## Prerequisites

- **Docker Engine** v24 or later
- **Docker Compose** v2.0 or later
- **8 GB RAM** minimum (16 GB recommended)
- **20 GB disk space** (includes PostgreSQL and monitoring)
- **PostgreSQL 13+** (can use composed Postgres or external instance)
- **Clerk account** (free tier available at [clerk.com](https://clerk.com))
- **Monitoring stack** (optional): Prometheus, Grafana, Loki

## Architecture

Enterprise deployment provides production-ready services with database persistence, authentication, monitoring, and security:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Infrastructure                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Reverse Proxy (Nginx/Caddy)                         │   │
│  │  - TLS termination                                   │   │
│  │  - Rate limiting                                     │   │
│  │  - Load balancing (optional)                         │   │
│  └─────┬────────────────────────────────┬───────────────┘   │
│        │                                │                    │
│   ┌────▼──────┐  ┌──────────────┐ ┌────▼──────┐            │
│   │   Web     │  │  API         │ │ Prometheus│            │
│   │  3000     │  │  8080        │ │           │            │
│   └────┬──────┘  └──────┬───────┘ └───────────┘            │
│        │                │                                    │
│        └────────┬───────┘                                    │
│                 │                                            │
│        ┌────────▼──────────┐                                │
│        │    PostgreSQL     │                                │
│        │    5432           │                                │
│        └───────────────────┘                                │
│                                                               │
│        ┌──────────────────────────────────────────┐         │
│        │  Monitoring (optional)                   │         │
│        │  ├─ Prometheus (metrics)                 │         │
│        │  ├─ Grafana (dashboards)                 │         │
│        │  └─ Loki (logs)                          │         │
│        └──────────────────────────────────────────┘         │
│                                                               │
└─────────────────────────────────────────────────────────────┘

External Services:
├─ Clerk (authentication)
└─ GitHub API (optional: for artifact marketplace)
```

### Services

| Service | Port | Profile | Purpose |
|---------|------|---------|---------|
| API (FastAPI) | 8080 | enterprise | Backend REST API |
| Web (Next.js) | 3000 | enterprise | Frontend web interface |
| PostgreSQL | 5432 | enterprise | Production database |
| Prometheus | 9090 | enterprise + monitoring | Metrics collection |
| Grafana | 3001 | enterprise + monitoring | Metrics dashboards |
| Loki | 3100 | enterprise + monitoring | Log aggregation |

## Installation & Setup

### Step 1: Initialize Configuration

Copy the enterprise environment template:

```bash
cp .env.enterprise.example .env
```

### Step 2: Configure Essential Variables

Edit `.env` with your settings:

```bash
# Application
SKILLMEAT_ENV=production
SKILLMEAT_EDITION=enterprise

# API Server
SKILLMEAT_API_PORT=8080
SKILLMEAT_API_HOST=0.0.0.0
SKILLMEAT_WORKERS=4

# Web Server
SKILLMEAT_WEB_PORT=3000
NEXT_PUBLIC_API_URL=https://api.example.com  # Your production API URL

# Database (PostgreSQL)
DATABASE_URL=postgresql://skillmeat:your-secure-password@postgres:5432/skillmeat
POSTGRES_PASSWORD=your-secure-password

# Authentication (Clerk)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_your_publishable_key
CLERK_SECRET_KEY=sk_live_your_secret_key
CLERK_WEBHOOK_SECRET=whsec_your_webhook_secret

# Enterprise features
SKILLMEAT_ENTERPRISE_PAT_SECRET=your-cryptographically-secure-secret
```

### Step 3: Configure PostgreSQL

#### Option A: Use Composed PostgreSQL (Recommended for Single Server)

PostgreSQL service is included in `docker-compose.yml` with profile `enterprise`. The entrypoint script automatically:

1. Creates the database and user
2. Runs all migrations
3. Seeds initial data if needed

No additional configuration needed—just ensure `DATABASE_URL` matches:

```bash
DATABASE_URL=postgresql://skillmeat:password@postgres:5432/skillmeat
```

#### Option B: External PostgreSQL Instance

If using an external PostgreSQL server:

```bash
# Create database and user
psql -h postgres.example.com -U postgres -c "CREATE DATABASE skillmeat;"
psql -h postgres.example.com -U postgres -d skillmeat -c "CREATE USER skillmeat WITH PASSWORD 'secure-password';"
psql -h postgres.example.com -U postgres -d skillmeat -c "GRANT ALL PRIVILEGES ON DATABASE skillmeat TO skillmeat;"

# Set DATABASE_URL
DATABASE_URL=postgresql://skillmeat:secure-password@postgres.example.com:5432/skillmeat
```

### Step 4: Configure Clerk Authentication

Clerk is the recommended authentication provider for enterprise deployments.

#### Get Clerk Keys

1. Create a free account at [clerk.com](https://clerk.com)
2. Create a new application (choose "Show custom signup/login pages" for self-hosting)
3. Copy credentials from **API Keys** section:
   - **Publishable Key** (`pk_live_...`)
   - **Secret Key** (`sk_live_...`)
4. Set webhook secret in Clerk dashboard → **Webhooks** → **Endpoints**

Add to `.env`:

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_your_key
CLERK_SECRET_KEY=sk_live_your_key
CLERK_WEBHOOK_SECRET=whsec_your_secret
```

### Step 5: Start Services

With monitoring (recommended for production):

```bash
docker compose --profile enterprise -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

Without monitoring:

```bash
docker compose --profile enterprise up -d
```

Wait ~60 seconds for services to initialize. Check status:

```bash
docker compose ps
```

Expected output:
```
NAME                      IMAGE                      STATUS
skillmeat-api-1          skillmeat:latest           Up 45 seconds (healthy)
skillmeat-web-1          node:18-alpine             Up 40 seconds (healthy)
postgres-1               postgres:15-alpine         Up 50 seconds (healthy)
prometheus-1             prom/prometheus            Up 10 seconds (healthy)
grafana-1                grafana/grafana            Up 15 seconds (healthy)
loki-1                   grafana/loki               Up 12 seconds (healthy)
```

### Step 6: Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | [http://localhost:3000](http://localhost:3000) | Main application |
| API | [http://localhost:8080](http://localhost:8080) | REST API |
| Grafana | [http://localhost:3001](http://localhost:3001) | Monitoring dashboards |
| Prometheus | [http://localhost:9090](http://localhost:9090) | Metrics exploration |

## TLS & Reverse Proxy

### Using Nginx with Let's Encrypt

For production, use a reverse proxy with TLS termination. Example Nginx configuration:

```nginx
upstream skillmeat_api {
    server skillmeat-api:8080;
}

upstream skillmeat_web {
    server skillmeat-web:3000;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # API routes
    location /api/ {
        proxy_pass http://skillmeat_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Web routes
    location / {
        proxy_pass http://skillmeat_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Save to `nginx.conf`, then run:

```bash
docker run -d \
  -p 80:80 -p 443:443 \
  -v $(pwd)/nginx.conf:/etc/nginx/conf.d/default.conf \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  --network skillmeat_default \
  nginx:latest
```

### Using Caddy (Simpler Alternative)

Caddy automatically handles TLS with Let's Encrypt:

Create `Caddyfile`:

```caddyfile
example.com {
    # API routes
    handle /api/* {
        reverse_proxy skillmeat-api:8080
    }

    # Web routes
    handle {
        reverse_proxy skillmeat-web:3000 {
            header_up X-Forwarded-Proto https
        }
    }
}
```

Run:

```bash
docker run -d \
  -p 80:80 -p 443:443 \
  -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy-data:/data \
  --network skillmeat_default \
  caddy:latest
```

## Database Management

### Migrations

Migrations run automatically on API startup via the entrypoint script. To manually trigger:

```bash
docker compose exec api alembic upgrade head
```

Check migration status:

```bash
docker compose exec api alembic current
docker compose exec api alembic history
```

### Accessing PostgreSQL

Connect to PostgreSQL directly:

```bash
docker compose exec postgres psql -U skillmeat -d skillmeat
```

Common queries:

```sql
-- List all tables
\dt

-- Check artifact counts
SELECT type, COUNT(*) FROM artifacts GROUP BY type;

-- View database size
SELECT pg_size_pretty(pg_database_size('skillmeat'));

-- Check active connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

-- Exit
\q
```

### Backup

Create automated PostgreSQL backups:

```bash
# Manual backup
docker compose exec postgres pg_dump -U skillmeat skillmeat > backup-$(date +%Y%m%d-%H%M%S).sql

# Store in backups directory
mkdir -p backups
docker compose exec postgres pg_dump -U skillmeat skillmeat | gzip > backups/skillmeat-$(date +%Y%m%d-%H%M%S).sql.gz

# Verify backup
ls -lh backups/
```

### Restore

Restore from backup:

```bash
# Stop API (prevents concurrent writes)
docker compose stop api

# Restore database
zcat backups/skillmeat-YYYYMMDD-HHMMSS.sql.gz | docker compose exec -T postgres psql -U skillmeat skillmeat

# Restart API
docker compose start api
```

## Monitoring & Observability

### Prometheus Metrics

Prometheus collects metrics from all services. Access at [http://localhost:9090](http://localhost:9090).

Common queries:

```promql
# API request rate (requests per second)
rate(http_requests_total[1m])

# API response time (95th percentile)
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# API errors
rate(http_requests_total{status=~"5.."}[1m])

# Database connection pool
skillmeat_db_pool_size
```

### Grafana Dashboards

Grafana provides visual dashboards. Access at [http://localhost:3001](http://localhost:3001).

Default credentials:
- **Username**: `admin`
- **Password**: `admin` (change immediately in production)

Pre-loaded dashboards:
- **SkillMeat API**: Request rate, errors, latency
- **PostgreSQL**: Connection pool, query performance
- **System**: CPU, memory, disk usage

#### Change Admin Password

```bash
docker compose exec grafana grafana-cli admin reset-admin-password <new-password>
```

### Loki Logs

Loki aggregates logs from all services. Query in Grafana → **Explore** → **Loki**.

Example queries:

```logql
# All API logs
{job="skillmeat-api"}

# Errors only
{job="skillmeat-api"} | json | level="ERROR"

# Web app logs
{job="skillmeat-web"}
```

## Security Hardening

### Network Security

Restrict API to internal network only:

Edit `.env`:
```bash
SKILLMEAT_API_HOST=127.0.0.1
```

Then access only through the reverse proxy.

### Database Security

Use strong passwords and limit connections:

```bash
# Change default password
POSTGRES_PASSWORD=your-very-secure-password-here-64-chars-min

# Limit concurrent connections
docker compose exec postgres psql -U skillmeat -d skillmeat -c \
  "ALTER ROLE skillmeat WITH CONNECTION LIMIT 20;"
```

### Rate Limiting

Configure in reverse proxy (Nginx/Caddy) for API routes:

**Nginx example:**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;

location /api/ {
    limit_req zone=api_limit burst=10;
    proxy_pass http://skillmeat_api;
}
```

### Secrets Management

Never commit `.env` to version control. Use environment variable secrets:

```bash
# Generate secure secret for enterprise PAT
openssl rand -base64 32
```

Store in:
- **Docker Swarm**: Use secrets
- **Kubernetes**: Use secrets or sealed-secrets
- **CI/CD**: Use provider's secrets manager

### Audit Logging

Enable detailed API logging:

```bash
SKILLMEAT_ENV=production
SKILLMEAT_LOG_LEVEL=INFO
```

All API requests are logged. View logs:

```bash
docker compose logs -f api | grep -i "request\|error"
```

## Performance Tuning

### Database Connection Pool

Tune for your workload:

```bash
# In .env
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=40
SQLALCHEMY_POOL_RECYCLE=3600
```

### API Workers

Scale horizontally by increasing workers:

```bash
# 4 workers (good for 4+ CPU cores)
SKILLMEAT_WORKERS=4

# 8 workers (for high-traffic deployments)
SKILLMEAT_WORKERS=8
```

Monitor actual usage:

```bash
docker compose stats skillmeat-api
```

### PostgreSQL Tuning

For high-traffic deployments, tune PostgreSQL:

```bash
docker compose exec postgres psql -U skillmeat -d skillmeat << EOF
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET work_mem = '50MB';
EOF

docker compose restart postgres
```

## Scaling

### Horizontal Scaling (Multiple API Instances)

To scale API horizontally, add replicas in `docker-compose.override.yml`:

```yaml
services:
  skillmeat-api:
    deploy:
      replicas: 3
```

Then restart with compose:

```bash
docker compose up -d
```

Update reverse proxy to load-balance across replicas.

### Load Balancing

Configure round-robin in Nginx:

```nginx
upstream skillmeat_api {
    server skillmeat-api-1:8080;
    server skillmeat-api-2:8080;
    server skillmeat-api-3:8080;
}
```

## Troubleshooting

### Database Connection Fails

Check PostgreSQL is running:

```bash
docker compose logs postgres | tail -50
docker compose exec postgres pg_isready
```

Verify connection string in `.env`:

```bash
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://skillmeat:password@postgres:5432/skillmeat
```

### Migrations Timeout

Increase startup timeout:

```yaml
# In docker-compose.override.yml
services:
  api:
    healthcheck:
      timeout: 30
      start_period: 120
```

### Clerk Authentication Fails

Verify keys are correct:

```bash
# Check keys are set
env | grep CLERK

# Restart web service to pick up changes
docker compose restart web
```

View Clerk logs:

```bash
docker compose logs web | grep -i clerk
```

### Out of Memory

Monitor memory usage:

```bash
docker compose stats
```

If PostgreSQL is using too much memory:

```bash
docker compose exec postgres psql -U skillmeat -d skillmeat -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"
```

## Maintenance

### Update Services

Pull latest images and restart:

```bash
docker compose pull
docker compose --profile enterprise up -d
```

### Health Checks

All services include health checks. View status:

```bash
docker compose ps
```

### Log Rotation

Docker automatically rotates container logs. Configure in `docker-compose.override.yml`:

```yaml
services:
  skillmeat-api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

## High Availability (Advanced)

For production high-availability setups:

1. **Database**: Use PostgreSQL streaming replication or managed PostgreSQL service
2. **API**: Run multiple replicas behind load balancer
3. **Web**: Run multiple replicas (stateless)
4. **Monitoring**: Use external monitoring service (DataDog, New Relic, etc.)

Contact support for HA reference architectures.

## Next Steps

- **[Configuration Reference](configuration.md)** — All environment variables
- **[Local Deployment](local.md)** — For testing before production
- **[Development Guide](development.md)** — Development setup
- **[Main Deployment Guide](README.md)** — Choose deployment pattern

## Support

For enterprise deployment support:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review [Configuration Reference](configuration.md)
3. View logs: `docker compose logs -f`
4. Check PostgreSQL health: `docker compose exec postgres pg_isready`
