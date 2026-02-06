# Memory & Context Intelligence System -- Production Rollout Plan

**Target**: Graduated rollout of the Memory & Context Intelligence System
**Strategy**: Feature flag controlled, phased activation with rollback at every stage
**Initial State**: `SKILLMEAT_MEMORY_CONTEXT_ENABLED=false` (deployed but disabled)

---

## Success Criteria (All Phases)

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Error rate | < 0.1% | Prometheus: `rate(skillmeat_api_errors_total[5m])` |
| p95 latency | < 500ms | Prometheus: `histogram_quantile(0.95, skillmeat_api_request_duration_seconds)` |
| P0 issues | 0 | Alertmanager + manual review |
| Memory usage | < 512MB | Docker stats / Grafana dashboard |
| CPU usage | < 80% sustained | Docker stats / Grafana dashboard |

---

## Phase 1: Infrastructure Verification (Day 0)

**Goal**: Confirm the production deployment is healthy with the feature flag OFF.

### Steps

1. Deploy with `./deploy.sh --confirm`
2. Verify all smoke tests pass: `./smoke-tests.sh`
3. Confirm the feature flag is OFF:
   ```bash
   curl -s http://localhost:8080/api/v1/config | grep memory_context_enabled
   # Expected: "memory_context_enabled": false
   ```
4. Verify monitoring stack is operational:
   - Prometheus scraping metrics: http://localhost:9090/targets
   - Grafana dashboards loading: http://localhost:3000
   - Alertmanager reachable: http://localhost:9093
5. Verify memory endpoints return disabled/error responses:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" \
     -X POST http://localhost:8080/api/v1/memory-items \
     -H "Content-Type: application/json" \
     -d '{"project_id":"test","type":"decision","content":"test"}'
   # Expected: 404, 403, or 503 (disabled)
   ```

### Rollback

No rollback needed -- system is running without the new feature.
If infrastructure issues arise, use `./deploy.sh --rollback`.

### Duration

Monitor for **4 hours** minimum before proceeding to Phase 2.

### Gate Criteria

- [ ] All smoke tests pass
- [ ] Monitoring stack operational
- [ ] No increase in error rate from baseline
- [ ] No increase in latency from baseline
- [ ] No P0 alerts fired

---

## Phase 2: Internal / Test Users (Day 1-2)

**Goal**: Enable the Memory & Context system for internal testing only.

### Steps

1. Enable the feature flag for the environment:
   ```bash
   # Option A: Update docker-compose environment variable
   # In docker-compose.production.yml, change:
   #   SKILLMEAT_MEMORY_CONTEXT_ENABLED=false
   # to:
   #   SKILLMEAT_MEMORY_CONTEXT_ENABLED=true

   # Option B: Override at runtime (no file change)
   SKILLMEAT_MEMORY_CONTEXT_ENABLED=true \
     docker-compose -f docker-compose.production.yml up -d skillmeat-api

   # Option C: Per-request header (if API supports it)
   curl -H "X-Feature-Memory-Context: enabled" \
     http://localhost:8080/api/v1/memory-items
   ```

2. Verify memory endpoints are now active:
   ```bash
   # Create a test memory item
   curl -s -X POST http://localhost:8080/api/v1/memory-items \
     -H "Content-Type: application/json" \
     -d '{
       "project_id": "internal-test",
       "type": "decision",
       "content": "Phase 2 rollout test",
       "tags": ["rollout-test"],
       "confidence": 0.9,
       "status": "active",
       "metadata": {"phase": "2"}
     }'
   # Expected: HTTP 201

   # List memory items
   curl -s http://localhost:8080/api/v1/memory-items?project_id=internal-test
   # Expected: HTTP 200 with items

   # Generate context pack
   curl -s -X POST http://localhost:8080/api/v1/context-packs/preview \
     -H "Content-Type: application/json" \
     -d '{"project_id": "internal-test", "budget_tokens": 4000}'
   # Expected: HTTP 200
   ```

3. Run the full staging-style smoke tests:
   ```bash
   SKILLMEAT_API_URL=http://localhost:8080 ./smoke-tests.sh
   ```

4. Monitor dashboards for:
   - Memory item creation/retrieval latency
   - Error rates on memory endpoints
   - Database size growth
   - Overall API latency impact

### Rollback

```bash
# Disable the feature flag immediately
SKILLMEAT_MEMORY_CONTEXT_ENABLED=false \
  docker-compose -f docker-compose.production.yml up -d skillmeat-api

# Verify disabled
curl -s http://localhost:8080/api/v1/config | grep memory_context_enabled
```

### Duration

Monitor for **24 hours** minimum before proceeding to Phase 3.

### Gate Criteria

- [ ] Memory CRUD operations succeed for test users
- [ ] Context pack generation works correctly
- [ ] Error rate remains < 0.1%
- [ ] p95 latency remains < 500ms
- [ ] No P0 issues reported
- [ ] Database growth is within expected bounds
- [ ] No memory leaks observed (container memory stable)

---

## Phase 3: 10% Traffic (Day 3-5) -- Optional

**Goal**: If a load balancer or traffic splitting mechanism is available, route 10% of traffic to memory-enabled instances.

> **Note**: This phase requires a load balancer with traffic splitting capability
> (e.g., nginx weighted upstream, Envoy traffic splitting, Kubernetes canary).
> Skip to Phase 4 if not applicable.

### Steps

1. Deploy a second API instance with the flag ON:
   ```bash
   # Start a canary instance on a different port
   docker run -d \
     --name skillmeat-api-canary \
     --network skillmeat-production \
     -e SKILLMEAT_MEMORY_CONTEXT_ENABLED=true \
     -e SKILLMEAT_ENV=production \
     -e SKILLMEAT_WORKERS=4 \
     -p 8081:8080 \
     skillmeat/api:latest
   ```

2. Configure load balancer for 90/10 split:
   ```nginx
   # Example nginx configuration
   upstream skillmeat_api {
       server skillmeat-api-production:8080 weight=9;
       server skillmeat-api-canary:8080 weight=1;
   }
   ```

3. Monitor canary metrics separately:
   - Compare error rates between canary and stable
   - Compare latency percentiles between canary and stable
   - Watch for any degradation on the canary instance

### Rollback

```bash
# Remove canary from load balancer rotation
# Stop canary instance
docker stop skillmeat-api-canary && docker rm skillmeat-api-canary
```

### Duration

Monitor for **48 hours** minimum before proceeding to Phase 4.

### Gate Criteria

- [ ] Canary error rate < 0.1%
- [ ] Canary p95 latency < 500ms
- [ ] No divergence in behavior between canary and stable
- [ ] No P0 issues reported
- [ ] User-facing impact is zero or positive

---

## Phase 4: 100% Rollout (Day 5+)

**Goal**: Enable the Memory & Context system for all production traffic.

### Steps

1. Update the production configuration permanently:
   ```bash
   # Edit env.production
   # Change: SKILLMEAT_MEMORY_CONTEXT_ENABLED=false
   # To:     SKILLMEAT_MEMORY_CONTEXT_ENABLED=true
   ```

2. Update docker-compose.production.yml:
   ```bash
   # Change: SKILLMEAT_MEMORY_CONTEXT_ENABLED=false
   # To:     SKILLMEAT_MEMORY_CONTEXT_ENABLED=true
   ```

3. Restart the API service:
   ```bash
   docker-compose -f docker-compose.production.yml up -d skillmeat-api
   ```

4. Remove canary instance (if Phase 3 was used):
   ```bash
   docker stop skillmeat-api-canary && docker rm skillmeat-api-canary
   ```

5. Run full smoke tests:
   ```bash
   SKILLMEAT_API_URL=http://localhost:8080 ./smoke-tests.sh
   ```

6. Commit the configuration change:
   ```bash
   git add deploy/production/env.production deploy/production/docker-compose.production.yml
   git commit -m "feat(deploy): enable Memory & Context system in production"
   ```

### Rollback

```bash
# Emergency: Disable immediately via runtime override
SKILLMEAT_MEMORY_CONTEXT_ENABLED=false \
  docker-compose -f docker-compose.production.yml up -d skillmeat-api

# Then: Revert configuration files and commit
```

### Duration

Continue monitoring indefinitely. Declare full rollout success after **48 hours** of stable operation.

### Gate Criteria

- [ ] Error rate < 0.1% for 48 continuous hours
- [ ] p95 latency < 500ms for 48 continuous hours
- [ ] Zero P0 issues
- [ ] Database performance stable
- [ ] Memory/CPU usage within resource limits
- [ ] No customer-reported issues

---

## Emergency Procedures

### Immediate Disable (< 1 minute)

```bash
# Override feature flag without restarting
SKILLMEAT_MEMORY_CONTEXT_ENABLED=false \
  docker-compose -f docker-compose.production.yml up -d skillmeat-api
```

### Full Rollback (< 5 minutes)

```bash
cd deploy/production
./deploy.sh --rollback
```

### Data Recovery

Memory items are stored in the SQLite database at the persistent volume.
If data corruption occurs:

1. Stop the API: `docker-compose -f docker-compose.production.yml stop skillmeat-api`
2. Backup the database: `cp data/skillmeat/cache/skillmeat.db data/skillmeat/cache/skillmeat.db.bak`
3. If needed, restore from the last known good backup
4. Restart: `docker-compose -f docker-compose.production.yml up -d skillmeat-api`

---

## Monitoring Checklist

Use these Grafana dashboards and Prometheus queries throughout the rollout:

| What to Monitor | Where | Alert Threshold |
|-----------------|-------|-----------------|
| API error rate | Grafana: API Overview | > 0.1% for 5m |
| p95 latency | Grafana: API Overview | > 500ms for 5m |
| Memory items created | Grafana: Memory System | Unusual spike |
| Context pack generation time | Grafana: Memory System | > 2s p95 |
| Container memory | Grafana: Infrastructure | > 450MB |
| Container CPU | Grafana: Infrastructure | > 80% for 5m |
| Database size | Prometheus query | Growth > 10MB/day |
| Active alerts | Alertmanager | Any P0/P1 |

---

## Rollout Log

Track actual rollout progress here:

| Phase | Planned Date | Actual Date | Status | Notes |
|-------|-------------|-------------|--------|-------|
| Phase 1: Infrastructure | - | - | Pending | |
| Phase 2: Internal Users | - | - | Pending | |
| Phase 3: 10% Traffic | - | - | Pending | |
| Phase 4: 100% Rollout | - | - | Pending | |
