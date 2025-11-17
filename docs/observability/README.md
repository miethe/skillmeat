# SkillMeat Observability Documentation

## Overview

This directory contains comprehensive documentation for SkillMeat's observability features, including structured logging, distributed tracing, metrics collection, and monitoring.

## Contents

### Guides

- **[Observability Guide](observability-guide.md)**: Complete guide to SkillMeat's observability stack
  - Architecture overview
  - Quick start
  - Structured logging
  - Distributed tracing
  - Metrics collection
  - Dashboards
  - Adding observability to code
  - Performance considerations
  - Troubleshooting

### Runbooks

- **[Monitoring Runbook](runbooks/monitoring.md)**: Operational procedures for monitoring
  - Alert response procedures
  - Performance monitoring
  - Incident response workflow
  - Regular maintenance tasks
  - Emergency contacts

- **[Alerting Guide](runbooks/alerting.md)**: Alert configuration and best practices
  - Alert philosophy and principles
  - Alert rule examples
  - Alertmanager configuration
  - Alert design patterns
  - Testing and tuning

## Quick Links

### Getting Started

1. [Start the observability stack](observability-guide.md#quick-start)
2. [View logs](observability-guide.md#viewing-logs)
3. [Query metrics](observability-guide.md#querying-metrics)
4. [Access dashboards](observability-guide.md#grafana-dashboards)

### Common Tasks

- [Add logging to code](observability-guide.md#structured-logging)
- [Add tracing to operations](observability-guide.md#tracing-operations)
- [Record custom metrics](observability-guide.md#recording-custom-metrics)
- [Create alerts](runbooks/alerting.md#alert-configuration)
- [Respond to incidents](runbooks/monitoring.md#incident-response-workflow)

### Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| SkillMeat API | http://localhost:8000 | Main API service |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3001 | Dashboards (admin/admin) |
| Loki | http://localhost:3100 | Log aggregation |
| Health Check | http://localhost:8000/health | Service health |
| Metrics | http://localhost:8000/metrics | Prometheus metrics |

## Architecture

```
┌─────────────────┐
│  SkillMeat API  │
│                 │
│  - Logging      │──────────┐
│  - Tracing      │          │
│  - Metrics      │          │
└─────────────────┘          │
                             │
        ┌────────────────────┴────────────────┐
        │                                     │
        ▼                                     ▼
┌──────────────┐                    ┌──────────────┐
│  Prometheus  │                    │   Promtail   │
│  (Metrics)   │                    │  (Log Ship)  │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │                                   ▼
       │                            ┌──────────────┐
       │                            │     Loki     │
       │                            │  (Log Store) │
       │                            └──────┬───────┘
       │                                   │
       └───────────┬───────────────────────┘
                   │
                   ▼
           ┌──────────────┐
           │   Grafana    │
           │ (Dashboards) │
           └──────────────┘
```

## Components

### Structured Logging

- **Format**: JSON with trace context
- **Fields**: timestamp, level, logger, message, trace_id, request_id, etc.
- **Output**: stdout (for container environments)
- **Aggregation**: Loki (optional)

### Distributed Tracing

- **Context Propagation**: trace_id, request_id, span_id
- **Span Tracking**: Operation timing, attributes, events
- **Hierarchy**: Parent-child span relationships
- **Integration**: Automatic via middleware

### Metrics

- **Format**: Prometheus exposition format
- **Collection**: Prometheus scraping
- **Storage**: Prometheus TSDB
- **Visualization**: Grafana dashboards

### Dashboards

- **Platform**: Grafana
- **Data Sources**: Prometheus, Loki
- **Pre-built**: API, Marketplace, MCP, Bundles
- **Custom**: Create your own

## Key Metrics

### RED Metrics (Requests, Errors, Duration)

```promql
# Request Rate
sum(rate(skillmeat_api_requests_total[5m]))

# Error Rate
sum(rate(skillmeat_api_requests_total{status=~"5.."}[5m])) /
sum(rate(skillmeat_api_requests_total[5m]))

# Duration (P95)
histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m]))
```

### Business Metrics

```promql
# Marketplace installs
rate(skillmeat_marketplace_installs_total[1h])

# Bundle exports
rate(skillmeat_bundle_exports_total[1h])

# MCP deployments
rate(skillmeat_mcp_deployments_total[1h])
```

## Example: Adding Observability to Code

### Structured Logging

```python
from skillmeat.observability.logging_config import get_logger_with_context

logger = get_logger_with_context(__name__)

logger.info("Processing bundle", extra={
    "bundle_id": bundle.id,
    "artifact_count": len(artifacts)
})
```

### Distributed Tracing

```python
from skillmeat.observability.tracing import trace_operation

with trace_operation("bundle.export", bundle_id=bundle.id) as span:
    artifacts = load_artifacts(bundle)
    span.set_attribute("artifact_count", len(artifacts))
    span.add_event("validation_complete")
    export_bundle(artifacts)
```

### Recording Metrics

```python
from skillmeat.observability.metrics import bundle_exports_total

bundle_exports_total.labels(
    status="success",
    format="tar.gz"
).inc()
```

## Alerting

### Alert Levels

- **Critical**: Service down, data loss (page immediately)
- **Warning**: Degraded performance (notify within 15 min)
- **Info**: Informational (log only)

### Common Alerts

- High error rate
- High latency
- GitHub rate limit low
- MCP server unhealthy
- Service down

See [Alerting Guide](runbooks/alerting.md) for configuration.

## Troubleshooting

### No metrics appearing

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

### Logs not in Grafana

```bash
# Check Loki
curl http://localhost:3100/ready

# Check Promtail logs
docker logs skillmeat-promtail
```

### Missing trace context

```bash
# Verify headers
curl -v http://localhost:8000/health | grep -i "x-trace"
```

See [Observability Guide](observability-guide.md#troubleshooting) for more.

## Best Practices

1. **Use structured logging** - JSON format with trace context
2. **Trace critical paths** - All API endpoints and long operations
3. **Monitor key metrics** - RED metrics, business metrics
4. **Create actionable alerts** - Every alert should have a clear action
5. **Review regularly** - Update thresholds, remove obsolete alerts

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)

## Contributing

When adding new features to SkillMeat:

1. Add structured logging with appropriate log levels
2. Add tracing to significant operations
3. Record relevant metrics (counters, histograms, gauges)
4. Update dashboards if needed
5. Create alerts for critical conditions
6. Update documentation

## Support

For questions or issues:

- Check the [Observability Guide](observability-guide.md)
- Review the [Monitoring Runbook](runbooks/monitoring.md)
- Open an issue on GitHub
- Contact the DevOps team

## Changelog

- **v1.0.0** (2025-11-17): Initial observability implementation
  - Structured logging with JSON format
  - Distributed tracing with context propagation
  - Prometheus metrics for all components
  - Grafana dashboards
  - Docker Compose observability stack
  - Comprehensive documentation and runbooks
