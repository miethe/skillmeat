# Staging Deployment Validation Checklist

This document provides comprehensive validation procedures for the SkillMeat staging deployment, including the Memory & Context Intelligence System.

## Pre-Deployment Validation

### Environment Configuration

- [ ] **Environment file reviewed**: Verify `env.staging` has all required variables
  - [ ] `SKILLMEAT_ENV=staging` is set
  - [ ] Feature flags configured correctly (`SKILLMEAT_MEMORY_CONTEXT_ENABLED=true`)
  - [ ] CORS origins include staging frontend URLs
  - [ ] Rate limiting enabled (`SKILLMEAT_RATE_LIMIT_ENABLED=true`)
  - [ ] Log format set to `json` for structured logging
  - [ ] No hardcoded secrets (only placeholders present)

- [ ] **Secrets provided**: All placeholder secrets replaced with actual values
  - [ ] `SKILLMEAT_GITHUB_TOKEN` (optional but recommended)
  - [ ] `SKILLMEAT_API_KEY` (if authentication enabled)
  - [ ] `GRAFANA_ADMIN_PASSWORD` (changed from default)

### Infrastructure Prerequisites

- [ ] **Docker environment ready**
  - [ ] Docker daemon running (`docker info` succeeds)
  - [ ] Docker Compose installed and working
  - [ ] Sufficient disk space (minimum 10GB available)
  - [ ] Network connectivity verified

- [ ] **Monitoring configuration**
  - [ ] `prometheus.yml` exists and references correct targets
  - [ ] Alert rules present in `monitoring/alerts/`
  - [ ] Grafana dashboards present in `monitoring/dashboards/`
  - [ ] `alertmanager.yml` configured (even if just defaults)

- [ ] **Database migrations ready**
  - [ ] Alembic configuration exists at `skillmeat/cache/migrations/alembic.ini`
  - [ ] Migration scripts present in `skillmeat/cache/migrations/versions/`
  - [ ] Database backup taken (if upgrading existing deployment)

### Code Readiness

- [ ] **Tests passing**
  - [ ] Unit tests: `pytest tests/test_memory*.py -v`
  - [ ] Integration tests: `pytest tests/test_api*.py -v`
  - [ ] Coverage acceptable (>80% for new code)

- [ ] **Code quality checks**
  - [ ] Linting passed: `flake8 skillmeat --select=E9,F63,F7,F82`
  - [ ] Formatting applied: `black skillmeat --check`
  - [ ] Type checking passed: `mypy skillmeat --ignore-missing-imports`

- [ ] **Build verification**
  - [ ] API Docker image builds successfully
  - [ ] Web Docker image builds successfully (if deploying frontend)
  - [ ] Images tagged correctly (`:latest` or specific version)

---

## Deployment Execution

### Deployment Process

- [ ] **Run deployment script**: `./deploy/staging/deploy.sh`
  - [ ] Prerequisites check passed
  - [ ] Images built successfully
  - [ ] Database migrations completed (or skipped if not needed)
  - [ ] Services started (`docker-compose up -d` succeeded)
  - [ ] Health checks passed
  - [ ] Smoke tests passed

### Service Status

- [ ] **All services running**: `docker-compose -f docker-compose.staging.yml ps`
  - [ ] `skillmeat-api` - Status: Up
  - [ ] `prometheus` - Status: Up
  - [ ] `grafana` - Status: Up
  - [ ] `alertmanager` - Status: Up
  - [ ] `skillmeat-web` - Status: Up (if enabled)

- [ ] **Container health checks passing**
  - [ ] API health endpoint: `curl http://localhost:8080/health`
  - [ ] Expected response: `{"status": "healthy"}`

---

## Post-Deployment Verification

### API Functionality

- [ ] **Core endpoints responding**
  - [ ] Health: `GET /health` → 200 OK
  - [ ] Detailed health: `GET /health/detailed` → 200 OK with components
  - [ ] API docs: `GET /docs` → 200 OK (Swagger UI)
  - [ ] Config: `GET /api/v1/config` → 200 OK
  - [ ] Metrics: `GET /metrics` → 200 OK (Prometheus format)

- [ ] **Memory & Context Intelligence System**
  - [ ] Create memory item: `POST /api/v1/memory-items` → 201 Created
  - [ ] List memory items: `GET /api/v1/memory-items` → 200 OK
  - [ ] Get memory item: `GET /api/v1/memory-items/{id}` → 200 OK
  - [ ] Update memory item: `PUT /api/v1/memory-items/{id}` → 200 OK
  - [ ] Delete memory item: `DELETE /api/v1/memory-items/{id}` → 204 No Content

- [ ] **Context module operations**
  - [ ] Create context module: `POST /api/v1/context-modules` → 201 Created
  - [ ] List context modules: `GET /api/v1/context-modules` → 200 OK
  - [ ] Generate context pack preview: `POST /api/v1/context-packs/preview` → 200 OK
  - [ ] Generate context pack: `POST /api/v1/context-packs/generate` → 200 OK

- [ ] **Collection management** (core functionality)
  - [ ] List artifacts: `GET /api/v1/artifacts` → 200 OK
  - [ ] Get artifact: `GET /api/v1/artifacts/{id}` → 200 OK
  - [ ] List collections: `GET /api/v1/collections` → 200 OK

### Feature Flag Verification

- [ ] **Feature flags configured correctly**: `GET /api/v1/config`
  - [ ] `memory_context_enabled`: `true`
  - [ ] `memory_auto_extract`: `false` (default for staging)
  - [ ] `enable_auto_discovery`: `true`
  - [ ] `enable_auto_population`: `true`

- [ ] **Feature flags being respected**
  - [ ] Memory endpoints accessible when enabled
  - [ ] Auto-extraction not triggering (when disabled)
  - [ ] Discovery features working (when enabled)

### Data Integrity

- [ ] **Database connectivity**
  - [ ] SQLite database created at expected location
  - [ ] Tables created by migrations
  - [ ] Sample data creation works (via API)
  - [ ] Sample data retrieval works (via API)

- [ ] **Data persistence**
  - [ ] Create test memory item
  - [ ] Restart API service: `docker-compose restart skillmeat-api`
  - [ ] Verify test memory item still exists
  - [ ] Delete test memory item

- [ ] **Cache behavior**
  - [ ] Collection data cached correctly
  - [ ] Cache invalidation working on mutations
  - [ ] Cache refresh endpoint works: `POST /api/v1/cache/refresh`

---

## Performance Validation

### Response Time Criteria

Test with realistic load. All endpoints should meet these criteria:

- [ ] **Health endpoints**: < 100ms (p95)
- [ ] **List operations**: < 500ms (p95)
- [ ] **Single item retrieval**: < 200ms (p95)
- [ ] **Create operations**: < 1000ms (p95)
- [ ] **Context pack generation**: < 3000ms (p95, depends on budget)

### Load Testing (Optional but Recommended)

- [ ] **Concurrent requests**: 10 concurrent users
  - [ ] API remains responsive
  - [ ] No 5xx errors
  - [ ] Error rate < 1%

- [ ] **Memory operations under load**
  - [ ] Create 100 memory items sequentially
  - [ ] List memory items (verify performance doesn't degrade)
  - [ ] Generate context packs with varying budgets

### Resource Utilization

- [ ] **Container resource usage acceptable**
  - [ ] API CPU usage: < 50% under normal load
  - [ ] API memory usage: < 512MB under normal load
  - [ ] No memory leaks (monitor over 1 hour)

---

## Monitoring & Observability Verification

### Prometheus Metrics

- [ ] **Metrics endpoint accessible**: `http://localhost:8080/metrics`
  - [ ] Counter metrics: `skillmeat_api_requests_total`
  - [ ] Histogram metrics: `skillmeat_api_request_duration_seconds`
  - [ ] Memory metrics: `skillmeat_memory_items_total`
  - [ ] Context metrics: `skillmeat_context_modules_total`

- [ ] **Prometheus scraping metrics**: `http://localhost:9090`
  - [ ] Navigate to Status → Targets
  - [ ] Verify `skillmeat-api` target is UP
  - [ ] Verify last scrape was recent (< 1 minute ago)

### Grafana Dashboards

- [ ] **Grafana accessible**: `http://localhost:3000`
  - [ ] Login successful (credentials from `env.staging`)
  - [ ] Prometheus data source configured and working
  - [ ] Test query: `up{job="skillmeat-api"}` returns data

- [ ] **Dashboards functioning**
  - [ ] API Overview dashboard shows data
  - [ ] Memory System dashboard shows metrics
  - [ ] Request rate panels updating
  - [ ] Error rate panels showing (ideally 0%)

### Alerting

- [ ] **Alertmanager accessible**: `http://localhost:9093`
  - [ ] Alert rules loaded in Prometheus (Status → Rules)
  - [ ] No firing alerts (or alerts are expected)
  - [ ] Alert routing configured in Alertmanager

- [ ] **Test alert firing** (optional but recommended)
  - [ ] Trigger a test alert (e.g., stop API service)
  - [ ] Verify alert fires in Prometheus
  - [ ] Verify alert routed to Alertmanager
  - [ ] Verify notification sent (if configured)
  - [ ] Restore service and verify alert resolves

### Logging

- [ ] **Structured logging working**
  - [ ] View logs: `docker-compose logs skillmeat-api --tail 100`
  - [ ] Logs in JSON format
  - [ ] Log level appropriate (INFO for staging)
  - [ ] No excessive ERROR or WARN messages
  - [ ] Request/response logging present

- [ ] **Log aggregation** (if configured)
  - [ ] Logs being shipped to external system
  - [ ] Searchable in log aggregation tool
  - [ ] Retention policy configured

---

## Security Validation

### Authentication & Authorization

- [ ] **Rate limiting enforced**
  - [ ] Verify `SKILLMEAT_RATE_LIMIT_ENABLED=true`
  - [ ] Attempt > 100 requests in 1 minute
  - [ ] Verify 429 Too Many Requests response

- [ ] **CORS configured correctly**
  - [ ] Allowed origins match frontend URLs
  - [ ] Preflight requests (OPTIONS) work
  - [ ] Credentials allowed if needed

- [ ] **API key authentication** (if enabled)
  - [ ] Requests without key rejected (401 Unauthorized)
  - [ ] Requests with valid key succeed (200 OK)
  - [ ] Requests with invalid key rejected (401 Unauthorized)

### Secrets Management

- [ ] **No secrets in logs**
  - [ ] Check logs for API keys, tokens, passwords
  - [ ] Verify sensitive data is redacted

- [ ] **Secrets mounted correctly**
  - [ ] Environment variables loaded from secure source
  - [ ] No secrets in Docker image layers
  - [ ] No secrets in compose file (only env var references)

### Network Security

- [ ] **Service isolation**
  - [ ] Services communicate within Docker network
  - [ ] Only necessary ports exposed to host
  - [ ] No unnecessary external exposure

---

## Rollback Readiness

### Pre-Rollback Preparation

- [ ] **Backup exists**
  - [ ] Database backup taken before deployment
  - [ ] Backup location documented
  - [ ] Backup tested (can be restored)

- [ ] **Rollback procedure documented**
  - [ ] Previous version tagged/identified
  - [ ] Rollback commands prepared
  - [ ] Rollback tested in non-production environment

### Rollback Testing (Optional)

- [ ] **Simulate rollback**
  - [ ] Stop current deployment: `docker-compose down`
  - [ ] Deploy previous version
  - [ ] Verify services start successfully
  - [ ] Run smoke tests on previous version
  - [ ] Restore current version

---

## Documentation & Communication

### Deployment Documentation

- [ ] **Deployment log created**
  - [ ] Deployment date/time recorded
  - [ ] Version/commit SHA documented
  - [ ] Any issues encountered noted
  - [ ] Resolution steps documented

- [ ] **Known issues documented**
  - [ ] Any degraded functionality noted
  - [ ] Workarounds documented
  - [ ] Planned fixes identified

### Team Communication

- [ ] **Stakeholders notified**
  - [ ] Deployment start communicated
  - [ ] Deployment success/failure communicated
  - [ ] Any incidents during deployment reported

- [ ] **Status page updated** (if applicable)
  - [ ] Staging environment status updated
  - [ ] Maintenance window closed
  - [ ] Known issues published

---

## Final Approval

### Sign-Off Checklist

- [ ] **All critical validations passed**
  - [ ] API responding correctly
  - [ ] Memory & Context system functional
  - [ ] Monitoring dashboards showing data
  - [ ] No critical errors in logs
  - [ ] Performance within acceptable limits

- [ ] **Stakeholder approval**
  - [ ] Technical lead approval: _______________
  - [ ] Product owner approval: _______________
  - [ ] Date: _______________

### Post-Deployment Actions

- [ ] **Monitor for 24 hours**
  - [ ] Check metrics/dashboards regularly
  - [ ] Review logs for anomalies
  - [ ] Respond to any alerts

- [ ] **Schedule follow-up review**
  - [ ] Review after 1 week
  - [ ] Assess performance trends
  - [ ] Plan any necessary adjustments

---

## Troubleshooting Common Issues

### Services Won't Start

**Symptoms**: `docker-compose up -d` fails or services crash immediately

**Check**:
- Docker daemon running: `docker info`
- Port conflicts: `lsof -i :8080` (or other ports)
- Log errors: `docker-compose logs`
- Disk space: `df -h`

**Resolution**:
- Free up ports: Stop conflicting services
- Check compose file syntax
- Review environment variables
- Verify image availability

### Health Checks Failing

**Symptoms**: Services running but health endpoint returns errors

**Check**:
- Application logs: `docker-compose logs skillmeat-api --tail 100`
- Database connectivity
- Environment variables loaded correctly
- Migrations completed successfully

**Resolution**:
- Run migrations manually: `docker-compose exec skillmeat-api alembic upgrade head`
- Verify database file exists and is writable
- Check for initialization errors in logs
- Restart service: `docker-compose restart skillmeat-api`

### Smoke Tests Failing

**Symptoms**: Deployment succeeds but smoke tests fail

**Check**:
- Which specific test failed
- API logs at time of test
- Network connectivity from test script to API
- Feature flags configured correctly

**Resolution**:
- Run individual test sections from `smoke-tests.sh`
- Test endpoints manually with curl
- Verify feature is actually enabled
- Check for data persistence issues

### Performance Issues

**Symptoms**: Slow response times, timeouts

**Check**:
- Container resource usage: `docker stats`
- Database query performance
- Network latency
- Concurrent request load

**Resolution**:
- Increase container resources in compose file
- Add database indexes
- Enable query caching
- Review slow query logs

### Monitoring Not Working

**Symptoms**: Prometheus not scraping, Grafana shows no data

**Check**:
- Prometheus target status: `http://localhost:9090/targets`
- Metrics endpoint accessible: `curl http://localhost:8080/metrics`
- Grafana data source configuration
- Alert rules loaded

**Resolution**:
- Verify `prometheus.yml` scrape config
- Check network connectivity between services
- Restart Prometheus: `docker-compose restart prometheus`
- Verify Grafana data source URL

---

## Reference: Expected Metrics

### API Performance Benchmarks

| Metric | Expected Value | Alert Threshold |
|--------|----------------|-----------------|
| Request rate | 10-100 req/sec | N/A |
| Error rate | < 1% | > 5% |
| P95 latency (list) | < 500ms | > 1000ms |
| P95 latency (get) | < 200ms | > 500ms |
| P95 latency (create) | < 1000ms | > 2000ms |

### Resource Utilization Benchmarks

| Resource | Normal | Warning | Critical |
|----------|--------|---------|----------|
| API CPU | < 30% | 50-70% | > 80% |
| API Memory | < 256MB | 384-512MB | > 768MB |
| Disk Usage | < 50% | 70-80% | > 90% |

---

## Appendix: Validation Scripts

### Quick Validation Script

```bash
#!/usr/bin/env bash
# Quick validation for critical endpoints

API_URL="http://localhost:8080"

echo "Testing health endpoint..."
curl -f "$API_URL/health" || echo "FAILED"

echo "Testing memory creation..."
curl -f -X POST "$API_URL/api/v1/memory-items" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"test","type":"decision","content":"Test"}' \
  || echo "FAILED"

echo "Testing metrics..."
curl -f "$API_URL/metrics" | grep -q "skillmeat_" || echo "FAILED"

echo "All quick validations complete!"
```

### Full Validation Script

For comprehensive validation, use the provided smoke tests:

```bash
./deploy/staging/smoke-tests.sh
```

---

**Document Version**: 1.0.0
**Last Updated**: 2026-02-06
**Maintained By**: SkillMeat DevOps Team
