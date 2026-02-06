---
title: Memory & Context Intelligence System Operations Runbook
description: Operational procedures for monitoring, troubleshooting, and maintaining the memory system
---

# Memory & Context Intelligence System Operations Runbook

This runbook provides operational guidance for the Memory & Context Intelligence System, including alert response procedures, troubleshooting steps, and maintenance tasks.

## Table of Contents

- [System Overview](#system-overview)
- [Monitoring & Alerts](#monitoring--alerts)
- [Alert Response Procedures](#alert-response-procedures)
- [Common Issues](#common-issues)
- [Maintenance Tasks](#maintenance-tasks)
- [Escalation](#escalation)

## System Overview

The Memory & Context Intelligence System consists of three main components:

1. **Memory Service** (`MemoryService`) - Manages persistent knowledge items (decisions, constraints, gotchas, style rules, learnings)
2. **Context Packer** (`ContextPackerService`) - Generates token-budget-aware context packs for agent prompts
3. **Context Modules** (`ContextModuleService`) - Manages module selectors for filtering memory items

### Key Metrics

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Memory list query p95 | < 200ms | > 200ms | > 1000ms |
| Context pack generation p95 | < 500ms | > 500ms | > 1000ms |
| Error rate | < 1% | > 1% | > 5% |
| Inbox size (candidate items) | < 100 | > 200 | N/A |
| Memory operation failure rate | < 0.5% | > 0.5% | N/A |

### Architecture

```
┌─────────────────┐
│   API Router    │ ← FastAPI endpoints
├─────────────────┤
│ Service Layer   │ ← MemoryService, ContextPackerService
├─────────────────┤
│  Repository     │ ← MemoryItemRepository
├─────────────────┤
│   SQLite DB     │ ← ~/.skillmeat/cache/skillmeat.db
└─────────────────┘
```

## Monitoring & Alerts

### Dashboard Access

Access the Memory & Context dashboard:

**Grafana**: `/d/memory-context/memory-context-intelligence-system`

Key panels:
- Memory list query latency (p50, p95, p99)
- Context pack generation latency (p50, p95, p99)
- Memory operations rate (creates, promotes, deprecates per minute)
- Inbox size (candidate items)
- Error rate by endpoint
- Memory items distribution (by status and type)

### Metric Sources

All metrics are exported via Prometheus from the SkillMeat API server:

- **API metrics**: `skillmeat_api_request_duration_seconds`, `skillmeat_api_requests_total`, `skillmeat_api_errors_total`
- **Memory metrics**: `skillmeat_memory_items_total` (by status and type)
- **Context pack metrics**: `skillmeat_context_pack_token_utilization`

### Alert Channels

Alerts are routed based on severity:

- **Info**: Logs only
- **Warning**: Slack #skillmeat-alerts
- **Critical**: PagerDuty + Slack #skillmeat-critical

## Alert Response Procedures

### Memory List Latency Warning

**Alert**: `MemoryListLatencyWarning`
**Severity**: Warning
**Threshold**: p95 > 200ms for 2 minutes

#### Investigation Steps

1. **Check current load**:
   ```bash
   # Query current latency
   curl http://localhost:8080/health/detailed | jq '.components.memory_system'
   ```

2. **Check database size**:
   ```bash
   ls -lh ~/.skillmeat/cache/skillmeat.db
   sqlite3 ~/.skillmeat/cache/skillmeat.db "SELECT COUNT(*) FROM memory_items;"
   ```

3. **Check query patterns**:
   ```bash
   # Review recent query logs for inefficient filters
   tail -f logs/api.log | grep "memory.list_items"
   ```

4. **Check system resources**:
   ```bash
   # CPU and memory usage
   top -p $(pgrep -f "uvicorn.*skillmeat.api.server")
   ```

#### Resolution Actions

- **If database is large (>10,000 items)**: Consider archiving deprecated items or adding indexes
- **If many candidate items**: Review inbox and promote/deprecate items
- **If slow disk I/O**: Check disk performance, consider moving database to faster storage
- **If high concurrent load**: Increase worker count or add caching

#### Prevention

- Monitor inbox size and keep candidate items < 200
- Regular cleanup of deprecated items older than 90 days
- Add database indexes if queries consistently exceed 100ms

---

### Memory List Latency Critical

**Alert**: `MemoryListLatencyCritical`
**Severity**: Critical
**Threshold**: p95 > 1000ms for 2 minutes

#### Immediate Actions

1. **Check service health**:
   ```bash
   curl http://localhost:8080/health
   ```

2. **Restart API server if unresponsive**:
   ```bash
   systemctl restart skillmeat-api
   # or
   pkill -f "uvicorn.*skillmeat.api.server" && uvicorn skillmeat.api.server:app --reload
   ```

3. **Check for database locks**:
   ```bash
   sqlite3 ~/.skillmeat/cache/skillmeat.db ".timeout 1000" "PRAGMA wal_checkpoint;"
   ```

4. **Review error logs**:
   ```bash
   tail -100 logs/api.log | grep ERROR
   ```

#### Escalation

If latency remains > 1000ms after restart:
- Page on-call engineer
- Consider disabling memory system temporarily: `export SKILLMEAT_MEMORY_CONTEXT_ENABLED=false`
- Investigate database corruption or disk issues

---

### Context Pack Latency Warning

**Alert**: `ContextPackLatencyWarning`
**Severity**: Warning
**Threshold**: p95 > 500ms for 2 minutes

#### Investigation Steps

1. **Check token budget settings**:
   ```bash
   # Review recent context pack requests
   tail -f logs/api.log | grep "context_pack.generate"
   ```

2. **Check item count per pack**:
   ```bash
   # Query average items per pack from logs
   grep "Generated pack" logs/api.log | tail -20
   ```

3. **Check markdown generation performance**:
   ```python
   # In Python shell
   from skillmeat.core.services.context_packer_service import ContextPackerService
   service = ContextPackerService(db_path=None)
   result = service.generate_pack("test-project", budget_tokens=4000)
   print(f"Items: {result['items_included']}, Tokens: {result['total_tokens']}")
   ```

#### Resolution Actions

- **If many items selected**: Increase selectivity with min_confidence filters
- **If token budget is very large (>8000)**: Consider reducing default budget
- **If markdown generation is slow**: Review item content sizes

---

### Context Pack Latency Critical

**Alert**: `ContextPackLatencyCritical`
**Severity**: Critical
**Threshold**: p95 > 1000ms for 2 minutes

#### Immediate Actions

Same as Memory List Latency Critical, plus:

1. **Check for infinite loops in selector logic**:
   ```bash
   # Review module selectors
   sqlite3 ~/.skillmeat/cache/skillmeat.db "SELECT id, name, selectors_json FROM context_modules LIMIT 10;"
   ```

2. **Temporarily disable problematic modules**:
   ```sql
   UPDATE context_modules SET enabled = 0 WHERE id = '<problematic_module_id>';
   ```

---

### Error Rate Warning

**Alert**: `MemorySystemErrorRateWarning`
**Severity**: Warning
**Threshold**: > 1% error rate for 5 minutes

#### Investigation Steps

1. **Identify error types**:
   ```bash
   grep "ERROR" logs/api.log | grep "memory\|context" | tail -50
   ```

2. **Check common error patterns**:
   ```bash
   # Group errors by type
   grep "ERROR" logs/api.log | grep "memory\|context" | awk '{print $NF}' | sort | uniq -c | sort -rn
   ```

3. **Check for validation errors**:
   ```bash
   # 422 errors indicate validation failures
   curl http://localhost:8080/metrics | grep "skillmeat_api_requests_total.*422"
   ```

4. **Check database constraints**:
   ```bash
   # Look for constraint violations
   grep "ConstraintError" logs/api.log | tail -20
   ```

#### Resolution Actions

- **If validation errors**: Review API request schemas and client code
- **If database errors**: Check database integrity
- **If duplicate content hash errors**: Expected behavior, no action needed
- **If 5xx errors**: Investigate server-side exceptions

---

### Error Rate Critical

**Alert**: `MemorySystemErrorRateCritical`
**Severity**: Critical
**Threshold**: > 5% error rate for 5 minutes

#### Immediate Actions

1. **Check service logs for exceptions**:
   ```bash
   tail -200 logs/api.log | grep -A 10 "ERROR\|CRITICAL"
   ```

2. **Check database accessibility**:
   ```bash
   sqlite3 ~/.skillmeat/cache/skillmeat.db "SELECT 1;"
   ```

3. **Disable feature if widespread failures**:
   ```bash
   export SKILLMEAT_MEMORY_CONTEXT_ENABLED=false
   systemctl restart skillmeat-api
   ```

4. **Page on-call engineer**

#### Root Cause Categories

- **Database corruption**: Restore from backup
- **Disk full**: Clear space, implement log rotation
- **Code bug**: Rollback to previous version
- **External dependency failure**: Check GitHub API, network connectivity

---

### Inbox Size Warning

**Alert**: `MemoryInboxSizeHigh`
**Severity**: Warning
**Threshold**: > 200 candidate items for 10 minutes

#### Investigation Steps

1. **Check inbox size by project**:
   ```bash
   sqlite3 ~/.skillmeat/cache/skillmeat.db \
     "SELECT project_id, COUNT(*) FROM memory_items WHERE status='candidate' GROUP BY project_id ORDER BY COUNT(*) DESC;"
   ```

2. **Review oldest candidate items**:
   ```bash
   sqlite3 ~/.skillmeat/cache/skillmeat.db \
     "SELECT id, project_id, type, created_at FROM memory_items WHERE status='candidate' ORDER BY created_at ASC LIMIT 20;"
   ```

3. **Check for automated creation**:
   ```bash
   # Look for rapid creation patterns
   grep "Created memory item" logs/api.log | tail -100
   ```

#### Resolution Actions

1. **Bulk review and promote high-confidence items**:
   ```bash
   # List high-confidence candidates
   sqlite3 ~/.skillmeat/cache/skillmeat.db \
     "SELECT id, confidence, content FROM memory_items WHERE status='candidate' AND confidence > 0.8 LIMIT 50;"
   ```

2. **Bulk deprecate low-confidence or stale items**:
   ```bash
   # Items older than 30 days with confidence < 0.5
   sqlite3 ~/.skillmeat/cache/skillmeat.db \
     "SELECT id, created_at, confidence FROM memory_items WHERE status='candidate' AND confidence < 0.5 AND created_at < datetime('now', '-30 days');"
   ```

3. **Set up automated cleanup job**:
   ```bash
   # Cron job to deprecate stale candidates
   0 2 * * * /usr/local/bin/skillmeat-cleanup-candidates.sh
   ```

#### Prevention

- Encourage regular inbox reviews
- Implement auto-promote for high-confidence items (confidence > 0.9)
- Set TTL policies for candidate items (auto-deprecate after 60 days)

---

### Operation Failure Rate

**Alert**: `MemoryOperationFailureRate`
**Severity**: Warning
**Threshold**: > 0.5% 5xx error rate for 5 minutes

#### Investigation Steps

1. **Check recent 5xx errors**:
   ```bash
   grep "status_code=5" logs/api.log | grep "memory-items" | tail -50
   ```

2. **Check for database connectivity issues**:
   ```bash
   systemctl status skillmeat-api
   ```

3. **Check for service exceptions**:
   ```bash
   grep "exception" logs/api.log | grep -i "memory" | tail -20
   ```

#### Resolution Actions

- **If database lock errors**: Enable WAL mode for better concurrency
- **If connection errors**: Check database file permissions
- **If service exceptions**: Review stack traces and fix bugs

---

## Common Issues

### Issue: High Memory Usage

**Symptoms**: API server memory usage > 1GB

**Diagnosis**:
```bash
ps aux | grep "uvicorn.*skillmeat"
```

**Resolution**:
1. Check for memory leaks in service layer
2. Restart API server
3. Reduce worker count if running multiple processes

---

### Issue: Database Lock Timeouts

**Symptoms**: "database is locked" errors in logs

**Diagnosis**:
```bash
sqlite3 ~/.skillmeat/cache/skillmeat.db "PRAGMA journal_mode;"
```

**Resolution**:
```bash
# Enable WAL mode for better concurrency
sqlite3 ~/.skillmeat/cache/skillmeat.db "PRAGMA journal_mode=WAL;"
```

---

### Issue: Context Packs Missing Items

**Symptoms**: Generated packs contain fewer items than expected

**Diagnosis**:
1. Check item statuses (only active/stable are included)
2. Check confidence thresholds
3. Check token budget constraints

**Resolution**:
```python
# Debug pack generation
from skillmeat.core.services.context_packer_service import ContextPackerService
service = ContextPackerService(db_path=None)
preview = service.preview_pack("project-id", budget_tokens=4000)
print(f"Available: {preview['items_available']}, Included: {preview['items_included']}")
```

---

### Issue: Feature Flag Disabled Unexpectedly

**Symptoms**: All memory endpoints return 503

**Diagnosis**:
```bash
echo $SKILLMEAT_MEMORY_CONTEXT_ENABLED
curl http://localhost:8080/health/detailed | jq '.components.memory_system'
```

**Resolution**:
```bash
# Re-enable feature
export SKILLMEAT_MEMORY_CONTEXT_ENABLED=true
systemctl restart skillmeat-api
```

---

## Maintenance Tasks

### Daily

- Review inbox size and promote/deprecate candidate items
- Check error logs for recurring issues
- Verify dashboard metrics are within normal ranges

### Weekly

- Review deprecated items and archive if older than 90 days
- Analyze token utilization trends
- Check database size growth

### Monthly

- Vacuum database to reclaim space:
  ```bash
  sqlite3 ~/.skillmeat/cache/skillmeat.db "VACUUM;"
  ```
- Review and update alert thresholds based on historical data
- Audit memory item quality and cleanup low-value items

### Quarterly

- Review and update module selectors
- Analyze memory item lifecycle patterns
- Update runbook based on recent incidents

---

## Escalation

### Severity Levels

**Info**: Self-service resolution using this runbook

**Warning**:
- Primary: On-call engineer via Slack #skillmeat-alerts
- Response time: 1 hour
- Escalate to Critical if unresolved in 4 hours

**Critical**:
- Primary: On-call engineer via PagerDuty
- Response time: 15 minutes
- Escalate to team lead if unresolved in 1 hour

### Escalation Contacts

- **On-call Engineer**: See PagerDuty schedule
- **Team Lead**: [contact info]
- **Platform Team**: #platform-support
- **Database Admin**: #database-support

### Incident Process

1. Create incident in incident management system
2. Notify stakeholders via #incidents channel
3. Follow incident response procedures
4. Document resolution in runbook
5. Schedule post-incident review

---

## Appendix

### Useful Commands

**Check service status**:
```bash
curl http://localhost:8080/health
curl http://localhost:8080/health/detailed
```

**Query memory items**:
```bash
sqlite3 ~/.skillmeat/cache/skillmeat.db "SELECT status, COUNT(*) FROM memory_items GROUP BY status;"
```

**Check inbox size**:
```bash
curl "http://localhost:8080/api/v1/memory-items/count?project_id=test&status=candidate"
```

**View feature flag status**:
```bash
curl http://localhost:8080/api/v1/config | jq '.memory_context_enabled'
```

**Generate test context pack**:
```bash
curl -X POST http://localhost:8080/api/v1/context-packs/generate \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test", "budget_tokens": 4000}'
```

### Log Locations

- API logs: `/var/log/skillmeat/api.log` or `logs/api.log`
- Error logs: `/var/log/skillmeat/error.log` or `logs/error.log`
- Access logs: `/var/log/skillmeat/access.log` or `logs/access.log`

### Configuration Files

- Feature flags: Environment variables or `.env` file
- API settings: `skillmeat/api/config.py`
- Database location: `~/.skillmeat/cache/skillmeat.db`

### Related Documentation

- [Feature Flags](../feature-flags.md)
- [API Documentation](../api/README.md)
- [Memory Service Documentation](../../skillmeat/core/services/memory_service.py)
- [Context Packer Documentation](../../skillmeat/core/services/context_packer_service.py)
