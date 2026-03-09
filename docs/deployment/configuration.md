# SkillMeat Environment Variable Reference

Complete reference for all environment variables used in SkillMeat deployments across local, local-auth, and enterprise editions.

## Quick Start

### Create Your Configuration

Copy the appropriate template based on your deployment model:

```bash
# Local edition (SQLite, no authentication)
cp .env.local.example .env

# Local with authentication (SQLite + Clerk)
cp .env.local-auth.example .env

# Enterprise edition (PostgreSQL + authentication)
cp .env.enterprise.example .env
```

### Start Services

```bash
# Local (zero-config)
docker compose --profile local up

# Local with authentication
docker compose --profile local-auth up

# Enterprise
docker compose --profile enterprise up
```

## Variable Overview by Category

### Core Configuration

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_EDITION` | Deployment edition | `local` | Yes | All | `local`, `enterprise` |
| `SKILLMEAT_ENV` | Application environment | `development` | No | All | `development`, `production`, `testing` |

### API Server

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_API_PORT` | API server port | `8080` | No | All | `8080`, `9080` |
| `SKILLMEAT_API_HOST` | API server host binding | `0.0.0.0` | No | All | `0.0.0.0`, `127.0.0.1` |
| `SKILLMEAT_HOST` | Legacy host binding (docker-compose override) | `0.0.0.0` | No | All | `0.0.0.0` |
| `SKILLMEAT_PORT` | Legacy port binding (docker-compose override) | `8080` | No | All | `8080` |
| `SKILLMEAT_WORKERS` | Number of API worker processes | `1` | No | All | `1`, `2`, `4` |
| `SKILLMEAT_RELOAD` | Enable auto-reload on code changes (dev only) | `false` | No | All | `true`, `false` |

**Notes:**
- `SKILLMEAT_WORKERS`: Range 1-8. Set higher for production with multiple CPU cores.
- `SKILLMEAT_RELOAD`: Use only in development with `docker compose up --build`. Ignored in production.

### Web Server (Next.js Frontend)

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_WEB_PORT` | Web server port | `3000` | No | All | `3000`, `4000` |
| `NEXT_PUBLIC_API_URL` | Frontend-to-API URL (client & SSR) | `http://localhost:8080` | No | All | `http://localhost:8080`, `https://api.example.com` |
| `NEXT_TELEMETRY_DISABLED` | Disable Next.js telemetry | `1` | No | All | `0`, `1` |

**Notes:**
- `NEXT_PUBLIC_API_URL`: This variable is exposed to the browser. Set to your production API URL.
- In docker-compose, internally uses `http://skillmeat-api:8080` for server-side rendering.

### Database Configuration

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | None | Yes (Enterprise) | Enterprise | `postgresql://skillmeat:password@postgres:5432/skillmeat` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `skillmeat` | No | Enterprise | `your-secure-password` |
| `POSTGRES_USER` | PostgreSQL username | `skillmeat` | No | Enterprise | `skillmeat` |
| `POSTGRES_DB` | PostgreSQL database name | `skillmeat` | No | Enterprise | `skillmeat` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | No | Enterprise | `5432` |

**Notes:**
- `DATABASE_URL`: Required for enterprise edition only. Format: `postgresql://username:password@host:port/database`
- Entrypoint script detects PostgreSQL vs SQLite from `DATABASE_URL` prefix
- Local editions use SQLite stored in `SKILLMEAT_COLLECTION_DIR`

### Authentication & Authorization

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_AUTH_PROVIDER` | Authentication provider | None | No | Local-Auth, Enterprise | `clerk`, `local` |
| `CLERK_SECRET_KEY` | Clerk secret key (backend) | None | Yes (if using Clerk) | Local-Auth, Enterprise | `sk_test_...`, `sk_live_...` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk publishable key (frontend) | None | Yes (if using Clerk) | Local-Auth, Enterprise | `pk_test_...`, `pk_live_...` |
| `CLERK_WEBHOOK_SECRET` | Clerk webhook signing secret | None | No | Local-Auth, Enterprise | `whsec_...` |
| `SKILLMEAT_ENTERPRISE_PAT_SECRET` | Enterprise PAT (bearer token) secret | None | No | Enterprise | Any secure string |

**Notes:**
- `SKILLMEAT_AUTH_PROVIDER`: Only set if using authentication. Valid values: `clerk`, `local`
- Clerk test keys start with `pk_test_` / `sk_test_`; production keys start with `pk_live_` / `sk_live_`
- Leave `CLERK_WEBHOOK_SECRET` empty unless you're configured to receive Clerk webhooks
- `SKILLMEAT_ENTERPRISE_PAT_SECRET`: Used for enterprise service-to-service authentication; format is arbitrary but should be cryptographically secure

### CORS Configuration

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_CORS_ENABLED` | Enable CORS middleware | `true` | No | All | `true`, `false` |
| `SKILLMEAT_CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,http://localhost:8080` | No | All | `http://localhost:3000,https://example.com` |
| `SKILLMEAT_CORS_ALLOW_CREDENTIALS` | Allow credentials in CORS requests | `true` | No | All | `true`, `false` |
| `SKILLMEAT_CORS_ALLOW_METHODS` | Allowed HTTP methods | `*` | No | All | `*`, `GET,POST,PUT,DELETE` |
| `SKILLMEAT_CORS_ALLOW_HEADERS` | Allowed headers | `*` | No | All | `*`, `Content-Type,Authorization` |

**Notes:**
- `SKILLMEAT_CORS_ORIGINS`: Separate multiple values with commas (no spaces)
- Use `*` with caution in production; explicitly list trusted origins instead

### Logging Configuration

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_LOG_LEVEL` | Logging level | `INFO` | No | All | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `SKILLMEAT_LOG_FORMAT` | Log output format | `json` | No | All | `json`, `text` |

**Notes:**
- `SKILLMEAT_LOG_FORMAT`: `json` produces structured logs; `text` produces human-readable format
- `SKILLMEAT_LOG_LEVEL`: Order from most verbose: `DEBUG` > `INFO` > `WARNING` > `ERROR` > `CRITICAL`

### Collection & Storage

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_COLLECTION_DIR` | Collection storage directory path | `/home/app/.skillmeat` | No | All | `/home/app/.skillmeat`, `~/.skillmeat` |

**Notes:**
- In Docker: path is inside container; persisted via named volume `skillmeat-data:/home/app/.skillmeat`
- Entrypoint script creates this directory if it doesn't exist
- Used for both SQLite database and artifact storage

### Advanced / Feature Flags

| Variable | Description | Default | Required | Editions | Example |
|----------|-------------|---------|----------|----------|---------|
| `SKILLMEAT_API_KEY_ENABLED` | Enable API key authentication | `false` | No | All | `true`, `false` |
| `SKILLMEAT_API_KEY` | Static API key value | None | No | All | Any string |
| `SKILLMEAT_RATE_LIMIT_ENABLED` | Enable rate limiting | `false` | No | All | `true`, `false` |
| `SKILLMEAT_RATE_LIMIT_REQUESTS` | Requests per minute limit | `60` | No | All | `30`, `60`, `100` |
| `SKILLMEAT_ENABLE_AUTO_DISCOVERY` | Enable artifact auto-discovery | `false` | No | All | `true`, `false` |
| `SKILLMEAT_ENABLE_AUTO_POPULATION` | Enable automatic population | `false` | No | All | `true`, `false` |
| `SKILLMEAT_GITHUB_TOKEN` | GitHub personal access token | None | No | All | `ghp_...` |
| `SKILLMEAT_COMPOSITE_ARTIFACTS_ENABLED` | Enable composite artifacts | `false` | No | All | `true`, `false` |
| `SKILLMEAT_DEPLOYMENT_SETS_ENABLED` | Enable deployment sets | `false` | No | All | `true`, `false` |
| `SKILLMEAT_MEMORY_CONTEXT_ENABLED` | Enable memory context system | `false` | No | All | `true`, `false` |
| `SKILLMEAT_WORKFLOW_ENGINE_ENABLED` | Enable workflow engine | `false` | No | All | `true`, `false` |
| `SKILLMEAT_MODULAR_CONTENT_ARCHITECTURE` | Enable modular content | `false` | No | All | `true`, `false` |
| `SKILLMEAT_MEMORY_AUTO_EXTRACT` | Auto-extract memories | `false` | No | All | `true`, `false` |
| `SKILLMEAT_DISCOVERY_CACHE_TTL` | Discovery cache TTL (seconds) | `3600` | No | All | `1800`, `3600` |
| `SKILLMEAT_DIFF_EXCLUDE_DIRS` | Directories to exclude from diffs | `.git,node_modules,__pycache__` | No | All | `.git,node_modules` |

## Configuration by Deployment Edition

### Local Edition

Minimal configuration for zero-setup development:

```bash
SKILLMEAT_EDITION=local
SKILLMEAT_API_PORT=8080
SKILLMEAT_API_HOST=0.0.0.0
SKILLMEAT_WEB_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8080
```

**Features:**
- SQLite database (no setup required)
- No authentication
- Single-user local development
- Volumes: `skillmeat-data` (container-persisted)

### Local-Auth Edition

Local development with Clerk authentication:

```bash
SKILLMEAT_EDITION=local
SKILLMEAT_AUTH_PROVIDER=clerk
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
SKILLMEAT_API_PORT=8080
SKILLMEAT_API_HOST=0.0.0.0
SKILLMEAT_WEB_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8080
```

**Features:**
- SQLite database
- Clerk authentication
- Same-machine setup
- Volumes: `skillmeat-data`

### Enterprise Edition

Production-grade multi-user deployment:

```bash
SKILLMEAT_EDITION=enterprise
DATABASE_URL=postgresql://skillmeat:password@postgres:5432/skillmeat
POSTGRES_PASSWORD=password
SKILLMEAT_AUTH_PROVIDER=clerk
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_WEBHOOK_SECRET=whsec_...
SKILLMEAT_ENTERPRISE_PAT_SECRET=secure-secret-here
SKILLMEAT_API_PORT=8080
SKILLMEAT_API_HOST=0.0.0.0
SKILLMEAT_WEB_PORT=3000
NEXT_PUBLIC_API_URL=https://api.example.com
SKILLMEAT_WORKERS=4
```

**Features:**
- PostgreSQL database (multi-user)
- Clerk authentication with webhooks
- Enterprise PAT for service-to-service auth
- Multiple workers for concurrency
- Explicit CORS configuration recommended
- Volumes: `skillmeat-data`, `postgres-data`

## Variable Precedence & Override Behavior

### Precedence Order (Highest to Lowest)

1. **Environment variables** (set directly or via `-e` flag)
2. **.env file** (loaded via `env_file: .env` in docker-compose)
3. **docker-compose.yml environment section** (used as fallback)
4. **Pydantic defaults** (hardcoded in `skillmeat/api/config.py`)

### Examples

```bash
# Override via shell environment
SKILLMEAT_API_PORT=9080 docker compose --profile local up

# Override multiple
SKILLMEAT_API_PORT=9080 SKILLMEAT_WEB_PORT=4000 docker compose --profile local up

# .env file is loaded but can be overridden:
export SKILLMEAT_LOG_LEVEL=DEBUG
docker compose --profile local up  # Uses DEBUG, overriding .env
```

### Docker Compose Service Overrides

The `docker-compose.yml` uses variable substitution for service-to-service URLs:

```yaml
environment:
  - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://skillmeat-api:8080}
```

This means:
- Browser clients use `NEXT_PUBLIC_API_URL` (from `.env` or env)
- Container SSR uses docker service name: `http://skillmeat-api:8080`
- If `NEXT_PUBLIC_API_URL` is not set, fallback is `http://skillmeat-api:8080`

## Secrets Management Best Practices

### Do NOT Commit `.env`

Your `.env` file contains secrets and should NEVER be committed:

```bash
# Add to .gitignore if not already present
echo ".env" >> .gitignore
```

### Safe Secret Handling

1. **Keep templates as examples:**
   ```bash
   # Commit templates (with placeholder values)
   .env.local.example
   .env.local-auth.example
   .env.enterprise.example
   ```

2. **Store secrets securely:**
   - Use environment variables on the host
   - Use secrets management tools (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Use `.env.local` (git-ignored) for local development only

3. **Rotate credentials regularly:**
   - Clerk keys: regenerate from dashboard
   - PostgreSQL password: change via `ALTER USER` after initial setup
   - GitHub token: regenerate from settings

### Example Secure Workflow

```bash
# 1. Use template
cp .env.enterprise.example .env

# 2. Add to .gitignore
echo ".env" >> .gitignore

# 3. Fill in secrets from secure source
export CLERK_SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id skillmeat/clerk | jq -r .SecretString)
export POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value --secret-id skillmeat/postgres | jq -r .SecretString)

# 4. Export to .env
env | grep CLERK_ | tee -a .env
env | grep POSTGRES_PASSWORD | tee -a .env

# 5. Deploy (secrets stay in environment, never on disk)
docker compose up
```

## Common Configuration Scenarios

### Development Workflow

```bash
# Start with local edition (no auth, SQLite)
cp .env.local.example .env
docker compose --profile local up

# Your app is available at:
# - API: http://localhost:8080
# - Web: http://localhost:3000
# - OpenAPI docs: http://localhost:8080/docs
```

### Testing with Authentication

```bash
# Use local-auth to test Clerk integration
cp .env.local-auth.example .env

# Fill in your Clerk test credentials
# CLERK_SECRET_KEY=sk_test_...
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

docker compose --profile local-auth up
```

### Production Deployment

```bash
# Use enterprise template
cp .env.enterprise.example .env

# Configure production values:
# DATABASE_URL=postgresql://skillmeat:${SECURE_PASSWORD}@db.example.com:5432/skillmeat
# CLERK_SECRET_KEY=sk_live_...
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
# NEXT_PUBLIC_API_URL=https://api.example.com

# Deploy
docker compose --profile enterprise up -d

# Or with docker swarm/kubernetes:
docker stack deploy -c docker-compose.yml skillmeat
```

### Custom Ports & CORS

```bash
# Run on non-standard ports
SKILLMEAT_API_PORT=9080 SKILLMEAT_WEB_PORT=4000 docker compose --profile local up

# Configure CORS for production
SKILLMEAT_CORS_ORIGINS="https://example.com,https://app.example.com" \
docker compose --profile enterprise up
```

### Enable Detailed Logging

```bash
# Debug mode with JSON logs
SKILLMEAT_LOG_LEVEL=DEBUG SKILLMEAT_LOG_FORMAT=json docker compose --profile local up

# Or human-readable text format
SKILLMEAT_LOG_LEVEL=DEBUG SKILLMEAT_LOG_FORMAT=text docker compose --profile local up
```

## Troubleshooting Configuration Issues

### API Won't Start

**Error:** `Connection refused` or `Bind error`

**Check:**
```bash
# Verify port is available
lsof -i :8080

# Verify SKILLMEAT_API_PORT is set correctly
docker compose config | grep "SKILLMEAT_API_PORT"

# Check logs
docker compose logs skillmeat-api
```

### Frontend Can't Connect to API

**Error:** `Failed to fetch` or CORS errors

**Check:**
```bash
# Verify NEXT_PUBLIC_API_URL matches API location
docker compose config | grep "NEXT_PUBLIC_API_URL"

# Test API connectivity from container
docker compose exec skillmeat-web \
  node -e "fetch('http://skillmeat-api:8080/health').then(r => console.log(r.status))"
```

### Database Connection Failed (Enterprise)

**Error:** `could not connect to server`

**Check:**
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL

# Test postgres connectivity
docker compose exec postgres \
  pg_isready -U skillmeat -d skillmeat

# Check postgres password
docker compose logs postgres | grep -i "password"
```

### Authentication Not Working

**Error:** Clerk redirects to login loop or "Invalid credentials"

**Check:**
```bash
# Verify SKILLMEAT_AUTH_PROVIDER is set
docker compose config | grep "SKILLMEAT_AUTH_PROVIDER"

# Verify Clerk keys are valid (test keys vs live)
docker compose config | grep -E "CLERK_|NEXT_PUBLIC_CLERK"

# Check Clerk API health
curl https://api.clerk.com/health
```

### Collection Directory Issues

**Error:** `Permission denied` or `No space left on device`

**Check:**
```bash
# Verify collection directory exists and has space
docker compose exec skillmeat-api \
  df -h /home/app/.skillmeat

# Check permissions
docker compose exec skillmeat-api \
  ls -la /home/app/.skillmeat

# View docker volume
docker volume inspect skillmeat_skillmeat-data
```

## Related Documentation

- [Deployment Guide](./deployment.md) — Complete deployment procedures
- [Docker Setup](./docker.md) — Docker and compose configuration
- [API Configuration](../api/configuration.md) — API-specific settings
- [Authentication](../auth/overview.md) — Auth provider setup
