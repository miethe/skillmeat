# SkillMeat Observability Quick Start

## TL;DR

```bash
# 1. Start observability stack
docker-compose -f docker-compose.observability.yml up -d

# 2. Access dashboards
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090

# 3. Start API with observability
python -m skillmeat.api.server

# 4. View metrics
curl http://localhost:8000/metrics

# 5. Make some requests
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/collections

# 6. View logs (structured JSON)
docker logs skillmeat-api 2>&1 | jq
```

## 5-Minute Setup

### Step 1: Start Observability Stack (1 min)

```bash
docker-compose -f docker-compose.observability.yml up -d
```

This starts:
- Prometheus (metrics collection)
- Grafana (dashboards)
- Loki (log aggregation)
- Promtail (log shipping)

### Step 2: Verify Services (1 min)

```bash
# Check services are running
docker-compose -f docker-compose.observability.yml ps

# Expected output:
# skillmeat-prometheus  Up  9090/tcp
# skillmeat-grafana     Up  3001/tcp
# skillmeat-loki        Up  3100/tcp
# skillmeat-promtail    Up

# Test connectivity
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3100/ready       # Loki
```

### Step 3: Start SkillMeat API (30 sec)

```bash
# Install dependencies if needed
pip install prometheus-client

# Start API
python -m skillmeat.api.server

# Or with Docker
docker run -p 8000:8000 skillmeat/api
```

### Step 4: Access Dashboards (1 min)

Open in browser:
1. **Grafana**: http://localhost:3001
   - Login: admin/admin
   - Navigate to Dashboards → SkillMeat Observability

2. **Prometheus**: http://localhost:9090
   - Navigate to Alerts to see alert rules
   - Navigate to Targets to see scrape targets

### Step 5: Generate Traffic (1 min)

```bash
# Generate some API traffic
for i in {1..100}; do
  curl -s http://localhost:8000/health > /dev/null
  curl -s http://localhost:8000/api/v1/collections > /dev/null
done

# View metrics
curl http://localhost:8000/metrics | grep skillmeat_api_requests_total

# View structured logs
docker logs skillmeat-api 2>&1 | jq 'select(.level == "INFO")' | tail -10
```

### Step 6: Explore Dashboards (1 min)

In Grafana (http://localhost:3001):

1. Go to **Dashboards** → **SkillMeat Observability**
2. View key metrics:
   - API request rate
   - P95 latency
   - Error rate
   - Marketplace activity
   - MCP server health

## Common Queries

### Prometheus Queries

```promql
# Request rate (last 5 minutes)
rate(skillmeat_api_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m]))

# Error rate
rate(skillmeat_api_requests_total{status=~"5.."}[5m])

# Top 10 slowest endpoints
topk(10, histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m])))
```

### Log Queries (with jq)

```bash
# All logs
docker logs skillmeat-api 2>&1 | jq

# Errors only
docker logs skillmeat-api 2>&1 | jq 'select(.level == "ERROR")'

# Follow logs with trace ID
docker logs -f skillmeat-api 2>&1 | jq 'select(.trace_id == "YOUR_TRACE_ID")'

# Logs from specific operation
docker logs skillmeat-api 2>&1 | jq 'select(.message | contains("bundle"))'

# Extract specific fields
docker logs skillmeat-api 2>&1 | jq '{time: .timestamp, level: .level, msg: .message}'
```

## Using Observability in Code

### Basic Logging

```python
from skillmeat.observability.logging_config import get_logger_with_context

logger = get_logger_with_context(__name__)

logger.info("Processing request", extra={
    "user_id": user.id,
    "operation": "export"
})
```

### Tracing Operations

```python
from skillmeat.observability.tracing import trace_operation

with trace_operation("bundle.export", bundle_id=bundle.id) as span:
    # Your code
    span.set_attribute("size", len(bundle))
    span.add_event("validation_complete")
```

### Recording Metrics

```python
from skillmeat.observability.metrics import bundle_exports_total

bundle_exports_total.labels(
    status="success",
    format="tar.gz"
).inc()
```

## Troubleshooting

### No metrics appearing in Prometheus

```bash
# 1. Check API metrics endpoint
curl http://localhost:8000/metrics

# 2. Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# 3. Check Prometheus logs
docker logs skillmeat-prometheus
```

### No logs in Grafana/Loki

```bash
# 1. Check Loki is running
curl http://localhost:3100/ready

# 2. Check Promtail is shipping logs
docker logs skillmeat-promtail

# 3. Check log format (must be valid JSON)
docker logs skillmeat-api 2>&1 | head -1 | jq
```

### Dashboards not showing data

1. Check time range (top right in Grafana)
2. Check datasource (should be "Prometheus")
3. Generate some traffic to API
4. Refresh dashboard

## Next Steps

1. **Explore Documentation**:
   - [Observability Guide](observability-guide.md) - Complete guide
   - [Monitoring Runbook](runbooks/monitoring.md) - Operational procedures
   - [Alerting Guide](runbooks/alerting.md) - Alert configuration

2. **Configure Alerts**:
   - Review `/docker/prometheus-alerts.yml`
   - Set up Alertmanager
   - Configure notification channels

3. **Customize Dashboards**:
   - Import pre-built dashboard
   - Create custom panels
   - Add business metrics

4. **Production Setup**:
   - Configure persistent storage
   - Set up backup/restore
   - Configure retention policies
   - Enable authentication

## Useful Links

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- Loki: http://localhost:3100
- API Health: http://localhost:8000/health
- API Metrics: http://localhost:8000/metrics
- API Docs: http://localhost:8000/docs

## Clean Up

```bash
# Stop observability stack
docker-compose -f docker-compose.observability.yml down

# Remove volumes (careful: deletes all data)
docker-compose -f docker-compose.observability.yml down -v
```

## Need Help?

- Check [Observability Guide](observability-guide.md)
- Review [Monitoring Runbook](runbooks/monitoring.md)
- Run example: `python examples/observability_example.py`
- Open an issue on GitHub
