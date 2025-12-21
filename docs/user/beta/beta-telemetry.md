# Beta Program Telemetry Dashboard

Monitor SkillMeat beta program health, usage patterns, and performance in real-time via Grafana dashboard.

## Overview

The telemetry dashboard provides real-time insights into:
- User engagement and adoption
- Feature usage patterns
- System performance and reliability
- Error rates and troubleshooting
- User satisfaction signals

This data drives daily decisions about prioritization, bug fixes, and feature completeness assessment for GA release.

## Accessing the Dashboard

### Prerequisites
- Docker and Docker Compose installed
- 2GB free disk space for metrics database
- Ports 3001 (Grafana), 9090 (Prometheus), 3100 (Loki) available

### Start the Observability Stack

```bash
# Navigate to repo root
cd /path/to/skillmeat

# Start observability stack
docker-compose -f docker-compose.observability.yml up -d

# Wait for services to be ready (30 seconds)
sleep 30

# Verify all services running
docker-compose -f docker-compose.observability.yml ps
```

### Access Grafana

1. Open browser to http://localhost:3001
2. Login with default credentials:
   - Username: `admin`
   - Password: `admin`
3. Change password immediately (admin will prompt)
4. Navigate to "Dashboards" → "SkillMeat Beta" folder

### Dashboards Available

#### 1. Overview Dashboard
High-level metrics for daily monitoring:
- Daily active users (DAU) trend
- Commands executed per user (7-day average)
- Top 5 used features
- Error rate (%)
- Average API response time
- System uptime

**Use for**: Daily standup, quick health check, identifying critical issues

#### 2. Engagement Dashboard
Deep dive into user behavior:
- Cohort retention (users active by day since invite)
- Feature adoption timeline
- Session duration distribution
- Commands executed distribution
- User segment analysis (by role, platform, collection size)

**Use for**: Engagement analysis, adoption tracking, cohort health

#### 3. Performance Dashboard
System performance and reliability:
- API response times (P50, P95, P99) by endpoint
- Request volume over time
- Error rate by endpoint
- Database query latency
- Memory and CPU usage
- Network latency

**Use for**: Performance debugging, capacity planning, SLA verification

#### 4. Features Dashboard
Feature-specific metrics:
- Feature usage frequency (command/UI action counts)
- Feature adoption rate over time
- Most/least used features
- Feature error rates
- Time-to-first-use by feature

**Use for**: Feature prioritization, identifying gaps, success measurement

#### 5. Marketplace Dashboard
Marketplace-specific metrics:
- Package search volume
- Package installation counts
- Top searched packages
- Publish success rate
- Bundle export/import counts

**Use for**: Marketplace health, popular content, integration effectiveness

#### 6. Team Features Dashboard
Team collaboration metrics:
- Bundle exports (daily count, size distribution)
- Bundle imports (daily count, success rate)
- Team member counts per collection
- Sharing frequency

**Use for**: Team features health, collaboration patterns

#### 7. Error & Issues Dashboard
Error tracking and troubleshooting:
- Error count by type
- Error distribution by endpoint
- Stack traces for recent errors
- Crash reports (if enabled)
- Platform-specific error rates

**Use for**: Bug triage, priority assessment, issue clustering

#### 8. MCP Management Dashboard
MCP server management metrics:
- MCP deployments (count, success rate)
- MCP health check results
- MCP latency distribution
- Server uptime
- Configuration change frequency

**Use for**: MCP integration health, deployment patterns

## Key Metrics Explained

### Engagement Metrics

**Daily Active Users (DAU)**
- Users who executed at least one command in a calendar day
- Target for beta: DAU > 70% of total participants by Week 3
- Indicates overall engagement level

**Feature Adoption (%)**
- Percentage of DAU who used a given feature
- Target: 70%+ for core features by Week 4
- Helps prioritize which features work/don't work

**Session Duration**
- Average time per session (period of active usage)
- Target: 10-15 minutes
- Too short = feature incomplete or confusing
- Too long = power users or issues with workflow

**Retention by Day**
- Percentage of initial participants still active on Day N
- Target: 80%+ by Day 7, 60%+ by Day 21
- Shows if product becomes sticky

### Performance Metrics

**API Response Time (P95)**
- 95th percentile response time in milliseconds
- Target for beta: <100ms
- P99 should be <200ms
- Indicates user experience quality

**Error Rate (%)**
- Percentage of requests resulting in error
- Target: <1%
- Spike indicates regression or service issue

**Uptime**
- Percentage of time service is available
- Target: 99.5%+
- Lower indicates infrastructure issues

### Quality Metrics

**Crash Rate**
- Percentage of sessions ending with crash
- Target: <0.5%
- Tracks system stability

**Failed Operations**
- Counts by operation type (install, deploy, sync, etc.)
- Target: 0 for critical operations
- Highlights unreliable workflows

## Real-Time Alerting

Configured alerts notify team of critical issues:

### Alert Rules

| Alert | Condition | Action |
|-------|-----------|--------|
| **High Error Rate** | Error rate > 5% | Page on-call engineer immediately |
| **Service Down** | Uptime < 99% | Page on-call, notification to Slack |
| **P0 Bug Report** | New P0 issue filed | Notify engineering team |
| **Performance Degradation** | P95 response time > 200ms | Investigate query/resource usage |
| **DAU Decline** | DAU drops > 20% from previous day | Investigate recent changes |
| **Platform Specific Issue** | Error rate > 10% on single platform | Investigate platform-specific code |

### Slack Integration

Alerts automatically post to `#skillmeat-beta-alerts` Slack channel:

```
[ERROR] 🔴 High Error Rate
Endpoint: POST /api/v1/skills/add
Error Rate: 8.2% (target: <1%)
Affected: 247 requests
Impact: High

Debug: Check logs in Loki dashboard
Contact: @on-call-eng
```

## Viewing Logs

### Loki Log Aggregation

All SkillMeat logs are aggregated in Loki for searching and debugging:

**Access Loki Explorer:**
1. In Grafana, navigate to: Explore → Select "Loki"
2. Query examples:

```promql
# All errors
{job="skillmeat"} | "ERROR"

# Specific endpoint errors
{job="skillmeat", endpoint="POST /api/v1/skills/add"} | "ERROR"

# Platform-specific issues
{job="skillmeat", platform="windows"} | "ERROR"

# Performance (requests taking >100ms)
{job="skillmeat"} | duration > 100

# Recent crash reports
{job="skillmeat"} | "panic" or "fatal"
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic info (disabled in prod for performance)
- `INFO`: General informational messages
- `WARN`: Warning messages that may indicate issues
- `ERROR`: Error conditions (always indexed)
- `FATAL`: Fatal errors causing shutdown

### Searching Logs

Use Loki query language (LogQL) for powerful searching:

```promql
# Search by participant ID
{job="skillmeat"} | "participant_id=abc123"

# Search by command
{job="skillmeat"} | "command=add_skill"

# Filter by response time
{job="skillmeat"} | duration >= 500

# Combine conditions
{job="skillmeat", platform="macos"} | "ERROR" | duration >= 200
```

## Data Retention

| Data Type | Retention | Resolution |
|-----------|-----------|-----------|
| Metrics (Prometheus) | 30 days | 1-minute interval |
| Logs (Loki) | 7 days | Raw logs |
| Dashboards | Permanent | Configuration stored in Git |
| Alerts | 30 days | Audit log of all alerts |

## Privacy and Security

### Data Collection Policy

SkillMeat collects:
- Command names (anonymized counts)
- Feature usage (which features used, how often)
- Performance data (latencies, error rates)
- System info (OS, Python version, for debugging)
- Aggregated collection stats (avg size, not content)

SkillMeat does NOT collect:
- Skill names or content
- Personal information
- Passwords or authentication tokens
- Private repository data
- File system contents

### Data Redaction

Sensitive data is automatically redacted:
- GitHub tokens: `***REDACTED***`
- API keys: `***REDACTED***`
- Email addresses: `***@***.***`
- File paths with PII: `/home/[USER]/*** → /home/user/***`

### Access Control

Dashboard access is restricted to:
- SkillMeat core team
- Beta program leads
- On-call engineers
- Authorized data analysts

## Common Dashboard Tasks

### Task: Identify Slow Endpoints

1. Open "Performance Dashboard"
2. Look at "Response Time by Endpoint" chart
3. Click on bar for slow endpoint
4. Drill down to individual requests
5. Check logs in Loki for errors or timeouts

### Task: Investigate Error Spike

1. Open "Overview Dashboard"
2. Notice error rate spike (red area in graph)
3. Click on timestamp to drill down
4. Open "Error & Issues Dashboard"
5. Use "Error Distribution" to identify affected endpoint
6. Check Loki logs for error details

### Task: Check Feature Adoption

1. Open "Features Dashboard"
2. Review "Feature Adoption Timeline" chart
3. Features below 50% adoption need investigation
4. Check "Feature Error Rates" for bugs blocking adoption
5. Review feedback in GitHub Discussions for complaints

### Task: Assess Release Readiness

1. Review "Overview Dashboard" - all metrics green?
2. Check "Error & Issues Dashboard" - any P0/P1 bugs?
3. Review "Engagement Dashboard" - is retention >60%?
4. Check "Performance Dashboard" - is P95 <100ms?
5. If all passing: ready for GA

## Troubleshooting Dashboard Issues

### Metrics not updating

```bash
# Check Prometheus is running
docker-compose -f docker-compose.observability.yml ps prometheus

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Restart Prometheus if needed
docker-compose -f docker-compose.observability.yml restart prometheus
```

### No logs appearing in Loki

```bash
# Check Loki is running
docker-compose -f docker-compose.observability.yml ps loki

# Check log files exist
ls -la /var/log/skillmeat/

# Restart log collection
docker-compose -f docker-compose.observability.yml restart loki
```

### Dashboard is slow

```bash
# Check Grafana memory usage
docker stats grafana

# If memory usage high, restart Grafana
docker-compose -f docker-compose.observability.yml restart grafana

# Clean up old data
docker exec prometheus promtool query instant 'up' | head -100
```

## Exporting Data

### Export Dashboard as PDF

1. In Grafana, open dashboard
2. Click dashboard title → Share
3. Select "Render as PDF"
4. Send to stakeholders

### Export Metrics as CSV

1. In Grafana, click "Explore"
2. Run query
3. Click "Download as CSV"

### Programmatic Access

Query Prometheus API directly:

```bash
# Query metrics via API
curl 'http://localhost:9090/api/v1/query_range?query=up&start=1609459200&end=1609545600&step=300'

# Export all SkillMeat metrics
curl 'http://localhost:9090/api/v1/label/job/values' | grep skillmeat
```

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [SkillMeat Observability Guide](../observability/observability-guide.md)
