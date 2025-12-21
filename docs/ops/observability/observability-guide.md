# SkillMeat Observability Guide

## Overview

SkillMeat provides comprehensive observability through structured logging, distributed tracing, and Prometheus metrics. This guide covers setup, usage, and best practices for monitoring SkillMeat in production.

## Architecture

The observability stack consists of four pillars:

1. **Structured Logging**: JSON-formatted logs with trace context
2. **Distributed Tracing**: Request flow tracking with spans
3. **Metrics**: Prometheus metrics for monitoring
4. **Dashboards**: Grafana dashboards for visualization

```
┌─────────────────┐
│  SkillMeat API  │
│                 │
│  - Logging      │──┐
│  - Tracing      │  │
│  - Metrics      │  │
└─────────────────┘  │
                     │
        ┌────────────┴──────────────┐
        │                           │
        ▼                           ▼
┌──────────────┐          ┌──────────────┐
│  Prometheus  │          │   Promtail   │
│  (Metrics)   │          │  (Log Ship)  │
└──────┬───────┘          └──────┬───────┘
       │                         │
       │                         ▼
       │                  ┌──────────────┐
       │                  │     Loki     │
       │                  │  (Log Store) │
       │                  └──────┬───────┘
       │                         │
       └─────────┬───────────────┘
                 │
                 ▼
         ┌──────────────┐
         │   Grafana    │
         │ (Dashboards) │
         └──────────────┘
```

## Quick Start

### 1. Start Observability Stack

```bash
# Start Prometheus, Grafana, Loki, and Promtail
docker-compose -f docker-compose.observability.yml up -d

# Check status
docker-compose -f docker-compose.observability.yml ps
```

### 2. Access Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **Loki**: http://localhost:3100

### 3. Start SkillMeat API with Observability

```bash
# Run with structured logging
python -m skillmeat.api.server

# Or with environment variables
SKILLMEAT_LOG_LEVEL=INFO python -m skillmeat.api.server
```

## Structured Logging

### Log Format

All logs are emitted as JSON with the following structure:

```json
{
  "timestamp": "2025-11-17T10:30:45.123456Z",
  "level": "INFO",
  "logger": "skillmeat.api.server",
  "message": "Request completed",
  "module": "server",
  "function": "dispatch",
  "line": 145,
  "trace_id": "abc123-def456",
  "request_id": "req-789",
  "user_id": "user-123",
  "extra": {
    "method": "GET",
    "path": "/api/v1/collections",
    "status_code": 200,
    "duration_ms": 45.67
  }
}
```

### Viewing Logs

```bash
# View all logs (pretty-printed)
python -m skillmeat.api.server | jq

# Filter by level
python -m skillmeat.api.server | jq 'select(.level == "ERROR")'

# Filter by trace ID (track single request)
python -m skillmeat.api.server | jq 'select(.trace_id == "abc123")'

# Filter by operation
python -m skillmeat.api.server | jq 'select(.message | contains("bundle"))'

# Extract specific fields
python -m skillmeat.api.server | jq '{time: .timestamp, level: .level, msg: .message}'
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (potential issues)
- **ERROR**: Error messages (failures)
- **CRITICAL**: Critical errors (service degradation)

Configure log level via environment:
```bash
export SKILLMEAT_LOG_LEVEL=DEBUG
```

## Distributed Tracing

### Trace Context

Every request is assigned:
- **trace_id**: Unique identifier for the entire request flow
- **request_id**: Unique identifier for the HTTP request
- **span_id**: Unique identifier for each operation within the request

### Using Traces in Code

```python
from skillmeat.observability.tracing import trace_operation

# Automatic tracing with context manager
with trace_operation("bundle.export", bundle_id=bundle.id) as span:
    # Operation code
    artifacts = load_artifacts(bundle)

    # Add attributes
    span.set_attribute("artifact_count", len(artifacts))

    # Add events
    span.add_event("validation_complete")

    # Any exceptions are automatically captured
    export_bundle(artifacts)
```

### Trace Propagation

Traces automatically propagate through:
- HTTP headers (`X-Trace-ID`, `X-Request-ID`)
- Context variables (async-safe)
- Nested operations (parent-child relationships)

Example multi-service trace:
```
trace_id: abc123-def456
├── span: POST /api/v1/bundles/export [45ms]
│   ├── span: bundle.load [10ms]
│   ├── span: bundle.validate [5ms]
│   └── span: bundle.serialize [30ms]
└── span: marketplace.publish [200ms]
    ├── span: github.upload [150ms]
    └── span: index.update [50ms]
```

## Metrics

### Available Metrics

#### API Metrics

```promql
# Request rate by endpoint
rate(skillmeat_api_requests_total[5m])

# Request duration (P95)
histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m]))

# Error rate
rate(skillmeat_api_requests_total{status=~"5.."}[5m])

# Request/response sizes
histogram_quantile(0.95, rate(skillmeat_api_request_size_bytes_bucket[5m]))
```

#### Marketplace Metrics

```promql
# Install rate
rate(skillmeat_marketplace_installs_total[5m])

# Publish success rate
rate(skillmeat_marketplace_publishes_total{status="success"}[5m]) /
rate(skillmeat_marketplace_publishes_total[5m])

# Operation duration
histogram_quantile(0.95, rate(skillmeat_marketplace_operation_duration_seconds_bucket[5m]))
```

#### Bundle Metrics

```promql
# Export/import rates
rate(skillmeat_bundle_exports_total[5m])
rate(skillmeat_bundle_imports_total[5m])

# Bundle sizes
histogram_quantile(0.95, rate(skillmeat_bundle_size_bytes_bucket[5m]))

# Artifact counts
histogram_quantile(0.95, rate(skillmeat_bundle_artifacts_count_bucket[5m]))
```

#### MCP Metrics

```promql
# Server health
skillmeat_mcp_servers_total{status="healthy"}

# Health check success rate
rate(skillmeat_mcp_health_checks_total{status="success"}[5m]) /
rate(skillmeat_mcp_health_checks_total[5m])

# Deployment rate
rate(skillmeat_mcp_deployments_total[5m])
```

#### GitHub Metrics

```promql
# Rate limit remaining
skillmeat_github_rate_limit_remaining

# Clone duration
histogram_quantile(0.95, rate(skillmeat_github_clone_duration_seconds_bucket[5m]))

# API request success rate
rate(skillmeat_github_requests_total{status="success"}[5m]) /
rate(skillmeat_github_requests_total[5m])
```

#### Cache Metrics

```promql
# Cache hit rate
sum(rate(skillmeat_cache_hits_total[5m])) /
(sum(rate(skillmeat_cache_hits_total[5m])) + sum(rate(skillmeat_cache_misses_total[5m])))

# Cache size
skillmeat_cache_size_bytes

# Cache entries
skillmeat_cache_entries_total
```

### Recording Custom Metrics

```python
from skillmeat.observability.metrics import (
    marketplace_installs_total,
    bundle_operation_duration,
    track_operation
)

# Counter
marketplace_installs_total.labels(
    broker="skillmeat",
    listing_id=listing.id,
    status="success"
).inc()

# Histogram (manual)
import time
start = time.perf_counter()
# ... operation ...
duration = time.perf_counter() - start
bundle_operation_duration.labels(operation="export").observe(duration)

# Decorator (automatic)
@track_operation("bundle", "export")
def export_bundle(bundle_id: str):
    # Function automatically timed
    pass
```

## Dashboards

### Grafana Dashboards

SkillMeat includes pre-built Grafana dashboards:

1. **SkillMeat Observability** - Main overview dashboard
   - API request rate and latency
   - Error rates and top errors
   - Marketplace activity
   - MCP server health
   - Cache performance
   - GitHub API usage

### Creating Custom Dashboards

1. Access Grafana: http://localhost:3001
2. Login: admin/admin
3. Click "Create" → "Dashboard"
4. Add panels with PromQL queries
5. Save dashboard

Example panel configurations in `/docker/grafana-dashboard.json`

### Dashboard Best Practices

- Group related metrics into rows
- Use appropriate visualization types:
  - **Graphs**: Time-series data (request rates, latencies)
  - **Gauges**: Current values (rate limits, server counts)
  - **Tables**: Top-N queries (slowest endpoints, top errors)
  - **Stats**: Single values (current health status)
- Set appropriate time ranges and refresh intervals
- Use template variables for filtering
- Add alert thresholds to panels

## Adding Observability to Code

### Structured Logging

```python
import logging
from skillmeat.observability.context import LogContext

# Get logger with automatic context
from skillmeat.observability.logging_config import get_logger_with_context
logger = get_logger_with_context(__name__)

# Log with context (automatically includes trace_id, request_id, etc.)
logger.info("Processing bundle", extra={
    "bundle_id": bundle.id,
    "artifact_count": len(artifacts)
})

# Log errors with exceptions
try:
    process_bundle(bundle_id)
except Exception as e:
    logger.error("Bundle processing failed", exc_info=True, extra={
        "bundle_id": bundle_id,
        "error_type": type(e).__name__
    })
    raise
```

### Tracing Operations

```python
from skillmeat.observability.tracing import trace_operation, trace_function

# Context manager (recommended)
with trace_operation("artifact.deploy", artifact_id=artifact.id) as span:
    # Your code
    span.set_attribute("target_scope", "user")
    span.add_event("validation_complete")

    # Deploy artifact
    result = deploy(artifact)

    span.set_attribute("deployment_status", result.status)

# Decorator
@trace_function("bundle.validate")
def validate_bundle(bundle_id: str):
    # Function automatically traced
    pass

# Async decorator
from skillmeat.observability.tracing import trace_async_function

@trace_async_function("marketplace.search")
async def search_marketplace(query: str):
    # Async function automatically traced
    pass
```

### Recording Metrics

```python
from skillmeat.observability.metrics import (
    artifact_operations_total,
    artifact_operation_duration,
    track_operation
)

# Counter
artifact_operations_total.labels(
    operation="deploy",
    type="skill",
    status="success"
).inc()

# Histogram
import time
start = time.perf_counter()
result = perform_operation()
duration = time.perf_counter() - start
artifact_operation_duration.labels(
    operation="deploy",
    type="skill"
).observe(duration)

# Decorator (automatic timing)
@track_operation("artifact", "deploy")
def deploy_artifact(artifact_id: str):
    # Automatically timed and recorded
    pass
```

## Alerting

### Defining Alerts

Create alert rules in `/docker/prometheus-alerts.yml`:

```yaml
groups:
  - name: skillmeat_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(skillmeat_api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate"
          description: "Error rate is {{ $value }} req/s"

      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "P95 latency is {{ $value }}s"

      # Low GitHub rate limit
      - alert: GitHubRateLimitLow
        expr: skillmeat_github_rate_limit_remaining < 100
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "GitHub rate limit low"
          description: "Only {{ $value }} requests remaining"

      # MCP server unhealthy
      - alert: MCPServerUnhealthy
        expr: skillmeat_mcp_servers_total{status="healthy"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "No healthy MCP servers"
          description: "All MCP servers are unhealthy"
```

### Alert Channels

Configure Alertmanager to send alerts to:
- Email
- Slack
- PagerDuty
- Webhook

Example Alertmanager config:
```yaml
route:
  receiver: 'team-email'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
```

## Performance Considerations

### Log Volume Management

- Use appropriate log levels (INFO in production, DEBUG for troubleshooting)
- Configure log rotation and retention
- Use log sampling for high-volume operations
- Filter sensitive data from logs

### Metric Cardinality

- Avoid high-cardinality labels (e.g., user IDs, timestamps)
- Normalize paths in metrics (replace IDs with placeholders)
- Use recording rules to pre-aggregate expensive queries
- Set appropriate retention policies

### Trace Sampling

For high-traffic systems, implement trace sampling:

```python
import random
from skillmeat.observability.context import LogContext

# Sample 10% of traces
if random.random() < 0.1:
    LogContext.set_trace_id()
    # Continue with tracing
```

## Troubleshooting

### No Metrics Appearing

1. Check if Prometheus can reach the API:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Check Prometheus targets:
   ```
   http://localhost:9090/targets
   ```

3. Verify Prometheus config:
   ```bash
   docker exec skillmeat-prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

### Logs Not in Grafana

1. Check Loki status:
   ```bash
   curl http://localhost:3100/ready
   ```

2. Check Promtail status:
   ```bash
   docker logs skillmeat-promtail
   ```

3. Verify log format is valid JSON:
   ```bash
   python -m skillmeat.api.server | head -1 | jq
   ```

### Missing Trace Context

Ensure middleware is properly configured:

```python
# In server.py
app.add_middleware(ObservabilityMiddleware)
```

Verify headers are being set:
```bash
curl -v http://localhost:8000/health | grep -i "x-trace"
```

## Best Practices

1. **Use Structured Logging**
   - Log in JSON format
   - Include context (trace_id, request_id)
   - Use appropriate log levels
   - Don't log sensitive data

2. **Trace Critical Paths**
   - Trace all API endpoints
   - Trace long-running operations
   - Add meaningful attributes and events
   - Keep span names consistent

3. **Monitor Key Metrics**
   - Request rate, latency, errors (RED)
   - Resource utilization (USE)
   - Business metrics (installs, exports)
   - External dependencies (GitHub API)

4. **Create Actionable Alerts**
   - Alert on symptoms, not causes
   - Set appropriate thresholds
   - Avoid alert fatigue
   - Include runbook links

5. **Review Dashboards Regularly**
   - Update queries as system evolves
   - Remove obsolete panels
   - Add new metrics for new features
   - Share dashboards with team

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [OpenTelemetry](https://opentelemetry.io/)
- [SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
