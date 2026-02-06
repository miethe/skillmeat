# Memory & Context Intelligence System Monitoring

This directory contains monitoring configuration for the Memory & Context Intelligence System, including Grafana dashboards and Prometheus alert rules.

## Contents

- **dashboards/**: Grafana dashboard JSON configurations
- **alerts/**: Prometheus alert rule YAML files

## Quick Start

### 1. Prometheus Setup

Add the SkillMeat API metrics endpoint to your Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'skillmeat-api'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

### 2. Alert Rules Setup

Import the alert rules into Prometheus:

```bash
# Copy alert rules to Prometheus rules directory
cp monitoring/alerts/memory-context-alerts.yml /etc/prometheus/rules/

# Add to prometheus.yml
rule_files:
  - /etc/prometheus/rules/memory-context-alerts.yml

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
```

Verify rules are loaded:
```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name | contains("memory_context"))'
```

### 3. Grafana Dashboard Setup

Import the dashboard into Grafana:

**Option 1: Via UI**
1. Open Grafana → Dashboards → Import
2. Upload `monitoring/dashboards/memory-context.json`
3. Select Prometheus data source
4. Click Import

**Option 2: Via API**
```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @monitoring/dashboards/memory-context.json
```

**Option 3: Via Provisioning**
```yaml
# /etc/grafana/provisioning/dashboards/skillmeat.yml
apiVersion: 1
providers:
  - name: 'SkillMeat'
    folder: 'SkillMeat'
    type: file
    options:
      path: /path/to/skillmeat/monitoring/dashboards
```

## Dashboard Overview

The Memory & Context Intelligence dashboard (`memory-context.json`) provides comprehensive monitoring across 12 panels:

### Latency Metrics
- **Memory List Query Latency** (p50, p95, p99) - Target: p95 < 200ms
- **Context Pack Generation Latency** (p50, p95, p99) - Target: p95 < 500ms

### Throughput Metrics
- **Memory Operations Rate** - Creates, promotes, deprecates, deletes per minute
- **Context Pack Generation Rate** - Generations and previews per minute

### Capacity Metrics
- **Inbox Size** - Total candidate items awaiting review (warning at 200)
- **Memory Items by Status** - Distribution across candidate, active, stable, deprecated
- **Memory Items by Type** - Distribution by decision, constraint, gotcha, style_rule, learning

### Reliability Metrics
- **Error Rate by Endpoint** - 5-minute error rate percentage (warning at 1%, critical at 5%)
- **Request Success Rate** - Overall success rate gauge (target > 99%)
- **Memory Operation Failures** - Recent failures by endpoint and error type

### Performance Metrics
- **Average Context Pack Token Utilization** - Token budget efficiency
- **Feature Flag Status** - Memory system enabled/disabled state

## Alert Rules

The alert rules (`memory-context-alerts.yml`) define 13 alerts across 4 groups:

### memory_context_latency
- `MemoryListLatencyWarning` - p95 > 200ms for 2 minutes
- `MemoryListLatencyCritical` - p95 > 1000ms for 2 minutes
- `ContextPackLatencyWarning` - p95 > 500ms for 2 minutes
- `ContextPackLatencyCritical` - p95 > 1000ms for 2 minutes

### memory_context_errors
- `MemorySystemErrorRateWarning` - Error rate > 1% for 5 minutes
- `MemorySystemErrorRateCritical` - Error rate > 5% for 5 minutes
- `MemoryOperationFailureRate` - 5xx rate > 0.5% for 5 minutes

### memory_context_capacity
- `MemoryInboxSizeHigh` - Inbox > 200 items for 10 minutes
- `MemoryDatabaseGrowthRapid` - Growth > 100 items/hour for 15 minutes

### memory_context_availability
- `MemorySystemDisabled` - Feature flag disabled for 1 minute
- `MemorySystemUnhealthy` - API server down for 2 minutes

### memory_context_performance
- `ContextPackTokenUtilizationLow` - Avg < 30% for 15 minutes
- `ContextPackTokenUtilizationHigh` - Avg > 95% for 15 minutes

## Alert Severity Levels

| Severity | Response Time | Notification Channel | Escalation |
|----------|---------------|---------------------|------------|
| **Info** | Best effort | Logs only | None |
| **Warning** | 1 hour | Slack #skillmeat-alerts | Critical after 4 hours |
| **Critical** | 15 minutes | PagerDuty + Slack | Team lead after 1 hour |

## Metric Definitions

### API Metrics (from ObservabilityMiddleware)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skillmeat_api_requests_total` | Counter | method, endpoint, status | Total API requests |
| `skillmeat_api_request_duration_seconds` | Histogram | method, endpoint | Request duration in seconds |
| `skillmeat_api_errors_total` | Counter | method, endpoint, error_type | Total API errors |

### Memory Metrics (custom)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skillmeat_memory_items_total` | Gauge | status, type | Total memory items by status and type |
| `skillmeat_context_pack_token_utilization` | Histogram | - | Token budget utilization ratio (0-1) |

## Health Checks

The system provides multiple health check endpoints:

### Basic Health Check
```bash
curl http://localhost:8080/health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "0.3.0",
  "environment": "production",
  "uptime_seconds": 3600.5
}
```

### Detailed Health Check (with Memory System)
```bash
curl http://localhost:8080/health/detailed
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "0.3.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "components": {
    "collection_manager": {
      "status": "healthy",
      "details": "3 collections available"
    },
    "config_manager": {
      "status": "healthy",
      "details": "configuration loaded"
    },
    "filesystem": {
      "status": "healthy",
      "details": "collections directory accessible: /Users/user/.skillmeat/collections"
    },
    "memory_system": {
      "status": "healthy",
      "details": "database accessible, inbox_size=42"
    }
  },
  "system_info": {
    "python_version": "3.12.0",
    "platform": "Darwin",
    "platform_version": "23.0.0",
    "architecture": "arm64"
  }
}
```

Memory system component states:
- `healthy` - Database accessible, operations functioning normally
- `degraded` - Database accessible but experiencing issues (high latency, errors)
- `unhealthy` - Database inaccessible or major failures
- `disabled` - Feature flag `SKILLMEAT_MEMORY_CONTEXT_ENABLED=false`

### Readiness Check
```bash
curl http://localhost:8080/health/ready
```

Used by orchestrators (Kubernetes) to determine if the service is ready to accept traffic.

### Liveness Check
```bash
curl http://localhost:8080/health/live
```

Used by orchestrators to determine if the service is alive (not deadlocked/crashed).

## Troubleshooting

### Dashboard Not Showing Data

1. **Verify Prometheus is scraping metrics**:
   ```bash
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job == "skillmeat-api")'
   ```

2. **Check metrics endpoint directly**:
   ```bash
   curl http://localhost:8080/metrics | grep skillmeat_api
   ```

3. **Verify Grafana data source**:
   - Settings → Data Sources → Prometheus
   - Click "Test" to verify connection

### Alerts Not Firing

1. **Check alert rule syntax**:
   ```bash
   promtool check rules monitoring/alerts/memory-context-alerts.yml
   ```

2. **Verify rules are loaded**:
   ```bash
   curl http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
   ```

3. **Check alert evaluation**:
   - Open Prometheus → Alerts
   - Find alert and check "State" and "Active Since"

### Memory System Health Check Failing

1. **Check feature flag**:
   ```bash
   echo $SKILLMEAT_MEMORY_CONTEXT_ENABLED
   ```

2. **Check database accessibility**:
   ```bash
   sqlite3 ~/.skillmeat/cache/skillmeat.db "SELECT COUNT(*) FROM memory_items;"
   ```

3. **Check service logs**:
   ```bash
   tail -f logs/api.log | grep "memory_system"
   ```

## Integration with Existing Monitoring

### Alertmanager Configuration

Route memory system alerts:

```yaml
# alertmanager.yml
route:
  receiver: 'default'
  routes:
    - match:
        system: memory-context
        severity: critical
      receiver: 'pagerduty'
      continue: true
    - match:
        system: memory-context
        severity: warning
      receiver: 'slack-alerts'

receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<your-service-key>'

  - name: 'slack-alerts'
    slack_configs:
      - api_url: '<your-webhook-url>'
        channel: '#skillmeat-alerts'
        title: 'Memory System Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### Slack Notifications

Example alert message format:

```
🚨 Memory System Alert

Alert: MemoryListLatencyWarning
Severity: Warning
Status: Firing
Description: Memory list query p95 latency is 345ms (threshold: 200ms)

Runbook: https://github.com/skillmeat/skillmeat/blob/main/docs/operations/memory-context-runbook.md#memory-list-latency-warning
```

## Performance Baselines

Based on acceptance criteria:

| Metric | Target | Baseline | Max Acceptable |
|--------|--------|----------|----------------|
| Memory list query (p95) | < 200ms | 50-100ms | 1000ms |
| Context pack generation (p95) | < 500ms | 100-300ms | 1000ms |
| Error rate | < 1% | 0.1-0.5% | 5% |
| Inbox size | < 100 | 20-50 items | 200 items |

## Capacity Planning

Monitor these trends for capacity planning:

1. **Database growth rate**: Items per day/week
2. **Query latency trend**: Correlate with database size
3. **Inbox accumulation rate**: Items created vs. items promoted/deprecated
4. **Token utilization trend**: Average pack size vs. budget

### Scaling Thresholds

Consider scaling when:
- Database size > 100,000 items (consider archiving)
- Query latency consistently > 150ms (add indexes, optimize queries)
- Inbox size consistently > 150 items (improve review workflows)
- Error rate > 0.5% for sustained periods (investigate root causes)

## References

- [Operations Runbook](../docs/operations/memory-context-runbook.md) - Detailed troubleshooting procedures
- [Feature Flags](../docs/feature-flags.md) - Feature flag configuration
- [API Documentation](../docs/api/README.md) - API endpoint reference
- [Memory Service](../skillmeat/core/services/memory_service.py) - Service implementation
- [Context Packer](../skillmeat/core/services/context_packer_service.py) - Packer implementation

## Contributing

When updating monitoring configuration:

1. Test dashboard changes in Grafana before committing
2. Validate alert rules with `promtool check rules`
3. Update this README with any new metrics or panels
4. Document any changes in the operations runbook
5. Version control all configuration files
