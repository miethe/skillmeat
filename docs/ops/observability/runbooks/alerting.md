# Alerting Best Practices and Configuration

## Overview

This guide covers alerting best practices, alert configuration, and guidelines for creating effective alerts in SkillMeat.

## Alert Philosophy

### Principles

1. **Alert on symptoms, not causes**: Alert when users are affected, not on internal metrics
2. **Make alerts actionable**: Every alert should have a clear action to take
3. **Avoid alert fatigue**: Too many alerts = ignored alerts
4. **Provide context**: Include relevant information in alert messages
5. **Set appropriate severity**: Not everything is critical

### Alert Levels

- **Critical**: Service down, data loss, security breach (page immediately)
- **Warning**: Degraded performance, approaching limits (notify within 15 minutes)
- **Info**: Informational, no action needed (log only)

## Alert Configuration

### Prometheus Alert Rules

Create alert rules in `/docker/prometheus-alerts.yml`:

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # Template for alerts
      - alert: AlertName
        expr: promql_query > threshold
        for: duration
        labels:
          severity: critical|warning|info
          component: api|marketplace|mcp|bundle
        annotations:
          summary: "Brief description"
          description: "Detailed description with {{ $value }}"
          runbook: "https://docs.skillmeat.com/runbooks/alert-name"
```

### Example Alert Rules

#### API Alerts

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(skillmeat_api_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(skillmeat_api_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High API error rate detected"
          description: "API error rate is {{ $value | humanizePercentage }}"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#high-error-rate"

      # Critical error rate
      - alert: CriticalErrorRate
        expr: |
          (
            sum(rate(skillmeat_api_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(skillmeat_api_requests_total[5m]))
          ) > 0.25
        for: 2m
        labels:
          severity: critical
          component: api
        annotations:
          summary: "CRITICAL: Very high API error rate"
          description: "API error rate is {{ $value | humanizePercentage }}"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#high-error-rate"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(skillmeat_api_request_duration_seconds_bucket[5m])
          ) > 5
        for: 10m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High API latency detected"
          description: "P95 latency is {{ $value }}s"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#high-latency"

      # Service down
      - alert: ServiceDown
        expr: up{job="skillmeat-api"} == 0
        for: 1m
        labels:
          severity: critical
          component: api
        annotations:
          summary: "CRITICAL: SkillMeat API is down"
          description: "The API service is not responding to health checks"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#service-down"
```

#### Marketplace Alerts

```yaml
groups:
  - name: marketplace_alerts
    interval: 30s
    rules:
      # High marketplace error rate
      - alert: MarketplaceErrorsHigh
        expr: |
          sum(rate(skillmeat_marketplace_errors_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
          component: marketplace
        annotations:
          summary: "High marketplace error rate"
          description: "Marketplace error rate is {{ $value }} errors/s"

      # GitHub publish failures
      - alert: GitHubPublishFailures
        expr: |
          sum(rate(skillmeat_marketplace_publishes_total{broker="github",status="error"}[5m]))
          /
          sum(rate(skillmeat_marketplace_publishes_total{broker="github"}[5m]))
          > 0.5
        for: 5m
        labels:
          severity: warning
          component: marketplace
        annotations:
          summary: "High GitHub publish failure rate"
          description: "{{ $value | humanizePercentage }} of GitHub publishes are failing"
```

#### Resource Alerts

```yaml
groups:
  - name: resource_alerts
    interval: 30s
    rules:
      # GitHub rate limit low
      - alert: GitHubRateLimitLow
        expr: skillmeat_github_rate_limit_remaining < 100
        for: 1m
        labels:
          severity: warning
          component: github
        annotations:
          summary: "GitHub API rate limit low"
          description: "Only {{ $value }} GitHub API requests remaining"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#github-rate-limit-low"

      # GitHub rate limit exhausted
      - alert: GitHubRateLimitExhausted
        expr: skillmeat_github_rate_limit_remaining == 0
        for: 1m
        labels:
          severity: critical
          component: github
        annotations:
          summary: "CRITICAL: GitHub API rate limit exhausted"
          description: "GitHub API rate limit has been exhausted"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#github-rate-limit-low"

      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: |
          sum(rate(skillmeat_cache_hits_total[5m]))
          /
          (sum(rate(skillmeat_cache_hits_total[5m])) + sum(rate(skillmeat_cache_misses_total[5m])))
          < 0.5
        for: 10m
        labels:
          severity: warning
          component: cache
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

#### MCP Alerts

```yaml
groups:
  - name: mcp_alerts
    interval: 30s
    rules:
      # MCP server unhealthy
      - alert: MCPServerUnhealthy
        expr: skillmeat_mcp_servers_total{status="healthy"} == 0
        for: 5m
        labels:
          severity: critical
          component: mcp
        annotations:
          summary: "CRITICAL: No healthy MCP servers"
          description: "All MCP servers are unhealthy or unavailable"
          runbook: "https://docs.skillmeat.com/runbooks/monitoring#mcp-server-unhealthy"

      # MCP health check failures
      - alert: MCPHealthCheckFailures
        expr: |
          sum(rate(skillmeat_mcp_health_checks_total{status="error"}[5m]))
          /
          sum(rate(skillmeat_mcp_health_checks_total[5m]))
          > 0.5
        for: 5m
        labels:
          severity: warning
          component: mcp
        annotations:
          summary: "High MCP health check failure rate"
          description: "{{ $value | humanizePercentage }} of MCP health checks are failing"
```

## Alertmanager Configuration

### Basic Configuration

Create `/docker/alertmanager.yml`:

```yaml
global:
  # Global defaults
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

# Route tree
route:
  # Default receiver
  receiver: 'team-notifications'

  # Group by alert name and severity
  group_by: ['alertname', 'severity', 'component']

  # Wait before sending initial notification
  group_wait: 30s

  # Wait before sending notifications about new alerts in group
  group_interval: 5m

  # Wait before repeating notifications
  repeat_interval: 4h

  # Routes for specific alerts
  routes:
    # Critical alerts go to PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true

    # API alerts go to Slack #api-alerts
    - match:
        component: api
      receiver: 'slack-api'
      continue: true

    # Marketplace alerts go to Slack #marketplace-alerts
    - match:
        component: marketplace
      receiver: 'slack-marketplace'

# Inhibition rules (suppress alerts)
inhibit_rules:
  # If service is down, don't alert on high error rate
  - source_match:
      alertname: 'ServiceDown'
    target_match:
      alertname: 'HighErrorRate'
    equal: ['component']

  # If critical error rate, don't alert on warning error rate
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'component']

# Receivers
receivers:
  # Default receiver (Slack)
  - name: 'team-notifications'
    slack_configs:
      - channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  # PagerDuty for critical alerts
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

  # API alerts
  - name: 'slack-api'
    slack_configs:
      - channel: '#api-alerts'
        title: 'API Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        color: '{{ if eq .GroupLabels.severity "critical" }}danger{{ else }}warning{{ end }}'

  # Marketplace alerts
  - name: 'slack-marketplace'
    slack_configs:
      - channel: '#marketplace-alerts'
        title: 'Marketplace Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Email Notifications

```yaml
receivers:
  - name: 'email-team'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@skillmeat.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@skillmeat.com'
        auth_password: 'your-password'
        headers:
          Subject: '[SkillMeat] {{ .GroupLabels.alertname }}'
        html: |
          <h2>{{ .GroupLabels.alertname }}</h2>
          <p><strong>Severity:</strong> {{ .GroupLabels.severity }}</p>
          <p><strong>Component:</strong> {{ .GroupLabels.component }}</p>
          {{ range .Alerts }}
          <p>{{ .Annotations.description }}</p>
          <p><a href="{{ .Annotations.runbook }}">Runbook</a></p>
          {{ end }}
```

### Webhook Notifications

```yaml
receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'http://localhost:8080/alerts'
        send_resolved: true
        http_config:
          basic_auth:
            username: 'alert-user'
            password: 'alert-password'
```

## Alert Design Patterns

### Multi-Window Multi-Burn-Rate Alerts

For SLO-based alerting:

```yaml
# Fast burn (short window, page immediately)
- alert: ErrorBudgetBurnFast
  expr: |
    (
      sum(rate(skillmeat_api_requests_total{status=~"5.."}[1h]))
      /
      sum(rate(skillmeat_api_requests_total[1h]))
    ) > (14.4 * 0.001)  # 1% error budget, 1 hour window
  for: 2m
  labels:
    severity: critical

# Slow burn (long window, ticket)
- alert: ErrorBudgetBurnSlow
  expr: |
    (
      sum(rate(skillmeat_api_requests_total{status=~"5.."}[6h]))
      /
      sum(rate(skillmeat_api_requests_total[6h]))
    ) > (6 * 0.001)  # 1% error budget, 6 hour window
  for: 30m
  labels:
    severity: warning
```

### Percentage-Based Alerts

```yaml
# Alert when error rate exceeds percentage
- alert: HighErrorPercentage
  expr: |
    (
      sum(rate(skillmeat_api_requests_total{status=~"5.."}[5m]))
      /
      sum(rate(skillmeat_api_requests_total[5m]))
    ) > 0.05  # 5%
  for: 5m
```

### Threshold-Based Alerts

```yaml
# Alert when absolute value exceeds threshold
- alert: HighErrorCount
  expr: sum(rate(skillmeat_api_requests_total{status=~"5.."}[5m])) > 10
  for: 5m
```

### Rate-of-Change Alerts

```yaml
# Alert when rate of change is high
- alert: ErrorRateIncreasing
  expr: |
    deriv(
      rate(skillmeat_api_requests_total{status=~"5.."}[5m])[10m:]
    ) > 0.01
  for: 5m
```

## Alert Tuning

### Avoiding False Positives

1. **Set appropriate `for` duration**:
   - Too short: Alerts on temporary spikes
   - Too long: Miss real issues
   - Recommendation: 5-10 minutes for warnings, 1-2 minutes for critical

2. **Use appropriate thresholds**:
   - Base on historical data
   - Account for normal variation
   - Review and adjust regularly

3. **Add context to filters**:
   ```yaml
   # Don't alert on test traffic
   expr: |
     sum(rate(skillmeat_api_requests_total{
       status=~"5..",
       environment!="test"
     }[5m])) > 0.1
   ```

### Avoiding False Negatives

1. **Alert on absence**:
   ```yaml
   # Alert if no requests (service might be down)
   - alert: NoTraffic
     expr: sum(rate(skillmeat_api_requests_total[5m])) == 0
     for: 5m
   ```

2. **Use multiple thresholds**:
   - Warning at 80%
   - Critical at 95%

3. **Monitor upstream dependencies**:
   ```yaml
   # Alert if GitHub is unreachable
   - alert: GitHubUnreachable
     expr: up{job="github"} == 0
     for: 2m
   ```

## Testing Alerts

### Manual Testing

```bash
# Trigger high error rate
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/nonexistent
done

# Check if alert fired
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname == "HighErrorRate")'
```

### Alert Testing Tool

Use `promtool` to test alert rules:

```bash
# Validate alert rules
promtool check rules /docker/prometheus-alerts.yml

# Test alert rules
promtool test rules /docker/prometheus-alerts-test.yml
```

Example test file:

```yaml
# /docker/prometheus-alerts-test.yml
rule_files:
  - prometheus-alerts.yml

evaluation_interval: 1m

tests:
  - interval: 1m
    input_series:
      - series: 'skillmeat_api_requests_total{status="500"}'
        values: '0+10x10'
      - series: 'skillmeat_api_requests_total{status="200"}'
        values: '0+100x10'

    alert_rule_test:
      - eval_time: 5m
        alertname: HighErrorRate
        exp_alerts:
          - exp_labels:
              severity: warning
              component: api
            exp_annotations:
              summary: "High API error rate detected"
```

## Alert Dashboard

Create a Grafana dashboard to monitor alerts:

```json
{
  "panels": [
    {
      "title": "Active Alerts",
      "targets": [
        {
          "expr": "ALERTS{alertstate=\"firing\"}"
        }
      ]
    },
    {
      "title": "Alert Firing Rate",
      "targets": [
        {
          "expr": "rate(ALERTS{alertstate=\"firing\"}[5m])"
        }
      ]
    }
  ]
}
```

## Best Practices Checklist

- [ ] Every alert has a clear severity level
- [ ] Every alert has a runbook link
- [ ] Alert messages include relevant context
- [ ] Alerts are grouped appropriately
- [ ] Critical alerts page immediately
- [ ] Warning alerts notify within 15 minutes
- [ ] Info alerts log only
- [ ] Alerts have been tested
- [ ] Thresholds are based on historical data
- [ ] False positive rate is < 5%
- [ ] All alerts are actionable
- [ ] Alert fatigue is monitored
- [ ] Alerts are reviewed quarterly

## Alert Review Process

### Weekly Review

- Review fired alerts
- Identify false positives
- Adjust thresholds if needed
- Update runbooks

### Monthly Review

- Analyze alert trends
- Review alert coverage
- Add missing alerts
- Remove obsolete alerts

### Quarterly Review

- Full audit of all alerts
- Update thresholds based on growth
- Review and update runbooks
- Team training on new alerts

## References

- [Prometheus Alerting](https://prometheus.io/docs/alerting/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Google SRE - Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [My Philosophy on Alerting](https://docs.google.com/document/d/199PqyG3UsyXlwieHaqbGiWVa8eMWi8zzAn0YfcApr8Q/edit)
