# SkillMeat Staging Deployment

This directory contains the complete staging deployment configuration for SkillMeat, including the Memory & Context Intelligence System (Phase 6).

## Quick Start

```bash
# 1. Configure environment variables
cp env.staging env.staging.local
# Edit env.staging.local with your secrets (never commit this file)

# 2. Deploy to staging
./deploy.sh

# 3. Verify deployment
./smoke-tests.sh
```

## Files Overview

| File | Purpose |
|------|---------|
| `deploy.sh` | Main deployment script with migrations and rollback |
| `docker-compose.staging.yml` | Service definitions (API, Prometheus, Grafana, Alertmanager) |
| `env.staging` | Environment configuration template (placeholders only) |
| `smoke-tests.sh` | Post-deployment validation tests |
| `VALIDATION.md` | Comprehensive validation checklist |
| `prometheus.yml` | Prometheus scraping configuration |
| `alertmanager.yml` | Alert routing configuration |
| `grafana/provisioning/` | Grafana datasource and dashboard config |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Staging Environment                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐         ┌─────────────┐          │
│  │ SkillMeat API│────────▶│ Prometheus  │          │
│  │   :8080      │ metrics │   :9090     │          │
│  └──────────────┘         └─────────────┘          │
│         │                        │                   │
│         │                        ▼                   │
│         │                 ┌─────────────┐          │
│         │                 │  Grafana    │          │
│         │                 │   :3000     │          │
│         │                 └─────────────┘          │
│         │                                            │
│         │                 ┌──────────────┐         │
│         └────────────────▶│ Alertmanager │         │
│           (alerts)         │   :9093      │         │
│                            └──────────────┘         │
│                                                      │
│  Optional:                                           │
│  ┌──────────────┐                                   │
│  │ SkillMeat Web│                                   │
│  │   :3001      │                                   │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

## Deployment Process

The `deploy.sh` script follows this workflow:

1. **Pre-deployment checks**
   - Verify Docker and Docker Compose installed
   - Check required files exist
   - Validate environment configuration

2. **Build phase**
   - Build API Docker image
   - Build Web Docker image (if applicable)

3. **Database migrations**
   - Run Alembic migrations (if available)
   - Fallback to post-deployment migration

4. **Service startup**
   - Start all services via docker-compose
   - Pull monitoring service images

5. **Health verification**
   - Wait for API health endpoint
   - Retry with exponential backoff

6. **Post-deployment**
   - Retry migrations if needed
   - Run comprehensive smoke tests

7. **Status reporting**
   - Display service status
   - Show endpoint URLs
   - Provide useful commands

## Smoke Tests

The `smoke-tests.sh` script validates the critical user journey:

- ✅ Health endpoints (basic + detailed)
- ✅ Feature flag configuration
- ✅ Memory item creation and listing
- ✅ Context module creation and listing
- ✅ Context pack generation (preview + full)
- ✅ Prometheus metrics endpoint

**Exit codes:**
- `0` - All tests passed
- `1` - One or more tests failed

## Validation Checklist

See `VALIDATION.md` for the complete validation checklist covering:

- Pre-deployment validation
- Deployment execution verification
- Post-deployment functional testing
- Performance validation criteria
- Monitoring and observability checks
- Security validation
- Rollback readiness

## Monitoring

### Prometheus

**Access**: http://localhost:9090

**Key queries:**
```promql
# Request rate
rate(skillmeat_api_requests_total[5m])

# Error rate
rate(skillmeat_api_requests_total{status=~"5.."}[5m])

# Memory items created
skillmeat_memory_items_total

# API latency (95th percentile)
histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m]))
```

### Grafana

**Access**: http://localhost:3000
**Default credentials**: admin/admin (change on first login)

Dashboards are automatically provisioned from `monitoring/dashboards/`.

### Alertmanager

**Access**: http://localhost:9093

Alerts are defined in `monitoring/alerts/` and loaded by Prometheus.

## Environment Configuration

### Required Variables

```bash
# Core settings
SKILLMEAT_ENV=staging
SKILLMEAT_HOST=0.0.0.0
SKILLMEAT_PORT=8080

# Feature flags
SKILLMEAT_MEMORY_CONTEXT_ENABLED=true
SKILLMEAT_MEMORY_AUTO_EXTRACT=false

# Security
SKILLMEAT_RATE_LIMIT_ENABLED=true
```

### Optional but Recommended

```bash
# GitHub API token (5000 req/hr vs 60/hr)
SKILLMEAT_GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Grafana admin password (change from default!)
GRAFANA_ADMIN_PASSWORD=secure_password_here
```

### Secrets Management

**Never commit secrets!**

1. Copy `env.staging` to `env.staging.local`
2. Replace placeholders with actual values
3. Add to `.gitignore`: `*.local`
4. Pass secrets via environment variables or Docker secrets

## Common Operations

### View Service Logs

```bash
# All services
docker-compose -f docker-compose.staging.yml logs -f

# Specific service
docker-compose -f docker-compose.staging.yml logs -f skillmeat-api

# Last 100 lines
docker-compose -f docker-compose.staging.yml logs --tail 100 skillmeat-api
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.staging.yml restart

# Restart specific service
docker-compose -f docker-compose.staging.yml restart skillmeat-api
```

### Update Configuration

```bash
# 1. Edit env.staging.local or docker-compose.staging.yml
# 2. Recreate services with new config
docker-compose -f docker-compose.staging.yml up -d --force-recreate
```

### Run Migrations Manually

```bash
# Inside running container
docker-compose -f docker-compose.staging.yml exec skillmeat-api \
  alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head

# Or in temporary container
docker run --rm -v "$(pwd)/../..:/app" -w /app \
  skillmeat/api:latest \
  alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head
```

### Clean Up

```bash
# Stop services (keep data)
docker-compose -f docker-compose.staging.yml down

# Stop services and remove volumes (DESTROYS DATA!)
docker-compose -f docker-compose.staging.yml down -v

# Remove unused images
docker image prune -a
```

## Troubleshooting

### Services Won't Start

**Check logs:**
```bash
docker-compose -f docker-compose.staging.yml logs
```

**Common causes:**
- Port conflicts (8080, 9090, 3000, 9093)
- Missing environment variables
- Insufficient disk space
- Docker daemon issues

### Health Checks Failing

**Test manually:**
```bash
curl -v http://localhost:8080/health
```

**Check container:**
```bash
docker-compose -f docker-compose.staging.yml ps
docker-compose -f docker-compose.staging.yml logs skillmeat-api --tail 50
```

### Smoke Tests Failing

**Run tests with debug output:**
```bash
bash -x ./smoke-tests.sh
```

**Test individual endpoints:**
```bash
# Health
curl http://localhost:8080/health

# Feature flags
curl http://localhost:8080/api/v1/config

# Metrics
curl http://localhost:8080/metrics
```

### Database Issues

**Check migrations:**
```bash
docker-compose -f docker-compose.staging.yml exec skillmeat-api \
  alembic -c /app/skillmeat/cache/migrations/alembic.ini current
```

**Reset database (DESTROYS DATA):**
```bash
docker-compose -f docker-compose.staging.yml down -v
rm -rf data/skillmeat/*
./deploy.sh
```

## Rollback Procedure

If deployment fails, follow these steps:

1. **Stop current deployment:**
   ```bash
   docker-compose -f docker-compose.staging.yml down
   ```

2. **Restore database backup:**
   ```bash
   cp data/skillmeat.db.backup data/skillmeat/skillmeat.db
   ```

3. **Deploy previous version:**
   ```bash
   export SKILLMEAT_VERSION=v0.2.0  # or previous stable version
   ./deploy.sh
   ```

4. **Verify with smoke tests:**
   ```bash
   ./smoke-tests.sh
   ```

## Security Considerations

- ✅ Rate limiting enabled by default
- ✅ CORS configured for staging domains only
- ✅ Structured JSON logging (no secrets logged)
- ✅ Secrets via environment variables (not in images)
- ⚠️ Update Grafana admin password immediately
- ⚠️ Configure Alertmanager notifications for production

## Performance Benchmarks

Expected performance for staging (2 workers):

| Endpoint | P95 Latency | Target |
|----------|-------------|--------|
| Health | < 100ms | ✅ |
| List items | < 500ms | ✅ |
| Get item | < 200ms | ✅ |
| Create item | < 1000ms | ✅ |
| Generate context pack | < 3000ms | ✅ |

## Next Steps

After successful staging deployment:

1. ✅ Monitor for 24-48 hours
2. ✅ Run full validation checklist (see `VALIDATION.md`)
3. ✅ Load testing (optional but recommended)
4. ✅ Security scan
5. ✅ Documentation review
6. ➡️ Production deployment planning

## Support

- **Documentation**: See `VALIDATION.md` for comprehensive guidance
- **Logs**: `docker-compose logs` for debugging
- **Monitoring**: Grafana dashboards at http://localhost:3000
- **Issues**: Check smoke test output and application logs

---

**Deployment Version**: Phase 6 (Memory & Context Intelligence System)
**Last Updated**: 2026-02-06
