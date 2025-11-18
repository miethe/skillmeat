# SkillMeat Monitoring Runbook

## Overview

This runbook provides operational procedures for monitoring and responding to alerts in SkillMeat. Use this guide when investigating incidents, responding to alerts, or troubleshooting production issues.

## Quick Reference

### Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| SkillMeat API | http://localhost:8000 | Main API service |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3001 | Dashboards (admin/admin) |
| Loki | http://localhost:3100 | Log aggregation |
| Health Check | http://localhost:8000/health | Service health |
| Metrics | http://localhost:8000/metrics | Prometheus metrics |

### Common Commands

```bash
# Check service status
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics

# Check logs with trace ID
docker logs skillmeat-api 2>&1 | jq 'select(.trace_id == "TRACE_ID")'

# Restart observability stack
docker-compose -f docker-compose.observability.yml restart

# View Prometheus targets
curl http://localhost:9090/api/v1/targets
```

## Alert Runbooks

### High Error Rate

**Alert**: `HighErrorRate`
**Severity**: Warning
**Threshold**: Error rate > 0.1 req/s for 5 minutes

#### Investigation Steps

1. **Check error distribution**:
   ```promql
   topk(10, rate(skillmeat_api_requests_total{status=~"5.."}[5m]))
   ```

2. **View recent error logs**:
   ```bash
   python -m skillmeat.api.server | jq 'select(.level == "ERROR")' | tail -20
   ```

3. **Identify affected endpoints**:
   ```promql
   rate(skillmeat_api_requests_total{status=~"5.."}[5m]) > 0
   ```

4. **Check error types**:
   ```promql
   rate(skillmeat_api_errors_total[5m])
   ```

#### Common Causes

- **Database connection issues**: Check database connectivity and pool exhaustion
- **External service failures**: Check GitHub API, marketplace brokers
- **Resource exhaustion**: Check memory, disk space, file descriptors
- **Bug in recent deployment**: Review recent changes

#### Resolution

1. **Immediate mitigation**:
   ```bash
   # Restart API service if needed
   systemctl restart skillmeat-api

   # Or with Docker
   docker restart skillmeat-api
   ```

2. **Fix root cause**:
   - If external service: Wait for recovery or implement fallback
   - If resource issue: Scale up or free resources
   - If bug: Rollback deployment or hotfix

3. **Verify resolution**:
   ```promql
   rate(skillmeat_api_requests_total{status=~"5.."}[5m])
   ```

### High Latency

**Alert**: `HighLatency`
**Severity**: Warning
**Threshold**: P95 latency > 5 seconds for 5 minutes

#### Investigation Steps

1. **Check slowest endpoints**:
   ```promql
   topk(10, histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m])))
   ```

2. **View slow request traces**:
   ```bash
   # Find slow requests in logs
   python -m skillmeat.api.server | jq 'select(.duration_ms > 5000)'
   ```

3. **Check database queries**:
   - Review query performance
   - Check for missing indexes
   - Look for N+1 queries

4. **Check external dependencies**:
   ```promql
   histogram_quantile(0.95, rate(skillmeat_github_clone_duration_seconds_bucket[5m]))
   histogram_quantile(0.95, rate(skillmeat_marketplace_operation_duration_seconds_bucket[5m]))
   ```

#### Common Causes

- **Slow database queries**: Unoptimized queries or missing indexes
- **External API delays**: GitHub API, marketplace brokers
- **Resource contention**: CPU, memory, or I/O bottlenecks
- **Large payloads**: Oversized bundle exports/imports

#### Resolution

1. **Identify bottleneck**:
   ```bash
   # Check CPU usage
   top

   # Check memory
   free -h

   # Check I/O
   iostat -x 1
   ```

2. **Optimize slow operations**:
   - Add caching for repeated operations
   - Optimize database queries
   - Implement pagination for large results
   - Add timeouts for external calls

3. **Scale if needed**:
   ```bash
   # Add more API instances
   docker-compose scale api=3
   ```

4. **Verify resolution**:
   ```promql
   histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m]))
   ```

### GitHub Rate Limit Low

**Alert**: `GitHubRateLimitLow`
**Severity**: Warning
**Threshold**: < 100 requests remaining for 1 minute

#### Investigation Steps

1. **Check current rate limit**:
   ```promql
   skillmeat_github_rate_limit_remaining
   ```

2. **Check request rate**:
   ```promql
   rate(skillmeat_github_requests_total[5m])
   ```

3. **Identify heavy users**:
   ```bash
   # Check logs for frequent GitHub operations
   python -m skillmeat.api.server | jq 'select(.logger | contains("github"))' | grep -o 'user_id":"[^"]*' | sort | uniq -c | sort -rn
   ```

4. **Check rate limit reset time**:
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
   ```

#### Common Causes

- **High traffic volume**: More users than expected
- **Inefficient operations**: Unnecessary API calls
- **Missing caching**: Repeated requests for same data
- **No authentication token**: Lower rate limits for unauthenticated requests

#### Resolution

1. **Immediate mitigation**:
   ```bash
   # Enable GitHub token if not set
   export GITHUB_TOKEN=your_token_here

   # Restart service to pick up token
   systemctl restart skillmeat-api
   ```

2. **Implement caching**:
   - Cache repository metadata
   - Cache release information
   - Cache file contents

3. **Optimize requests**:
   - Batch operations where possible
   - Use conditional requests (ETag)
   - Implement request throttling

4. **Monitor recovery**:
   ```promql
   skillmeat_github_rate_limit_remaining
   ```

### MCP Server Unhealthy

**Alert**: `MCPServerUnhealthy`
**Severity**: Critical
**Threshold**: 0 healthy servers for 5 minutes

#### Investigation Steps

1. **Check MCP server status**:
   ```promql
   skillmeat_mcp_servers_total
   ```

2. **View health check logs**:
   ```bash
   python -m skillmeat.api.server | jq 'select(.logger | contains("mcp")) | select(.message | contains("health"))'
   ```

3. **Check MCP server errors**:
   ```promql
   rate(skillmeat_mcp_errors_total[5m])
   ```

4. **Verify MCP server processes**:
   ```bash
   # Check if MCP servers are running
   ps aux | grep mcp

   # Check MCP logs
   tail -f /var/log/skillmeat/mcp/*.log
   ```

#### Common Causes

- **Server process crashed**: Check for segfaults or OOM kills
- **Configuration errors**: Invalid MCP server configuration
- **Network issues**: Can't reach MCP servers
- **Resource exhaustion**: MCP servers out of memory or file descriptors

#### Resolution

1. **Restart unhealthy servers**:
   ```bash
   # List MCP servers
   skillmeat mcp list

   # Restart specific server
   skillmeat mcp restart server-name

   # Restart all servers
   skillmeat mcp restart --all
   ```

2. **Check server logs**:
   ```bash
   skillmeat mcp logs server-name
   ```

3. **Fix configuration if needed**:
   ```bash
   # Validate configuration
   skillmeat mcp validate server-name

   # Update configuration
   skillmeat mcp configure server-name
   ```

4. **Verify recovery**:
   ```bash
   skillmeat mcp health server-name
   ```

### High Memory Usage

**Alert**: `HighMemoryUsage`
**Severity**: Warning
**Threshold**: Memory usage > 80% for 10 minutes

#### Investigation Steps

1. **Check current memory usage**:
   ```bash
   free -h
   top -o %MEM
   ```

2. **Identify memory-heavy processes**:
   ```bash
   ps aux --sort=-%mem | head -20
   ```

3. **Check for memory leaks**:
   ```bash
   # Monitor memory over time
   while true; do
     ps -p $(pgrep -f skillmeat) -o pid,rss,vsz,cmd
     sleep 60
   done
   ```

4. **Review cache sizes**:
   ```promql
   skillmeat_cache_size_bytes
   ```

#### Common Causes

- **Memory leak**: Code not releasing memory
- **Large cache**: Cache growing unbounded
- **Large payloads**: Processing oversized bundles
- **Too many concurrent operations**: Resource pool exhaustion

#### Resolution

1. **Clear caches**:
   ```bash
   # Clear application caches
   skillmeat cache clear

   # Or restart service
   systemctl restart skillmeat-api
   ```

2. **Tune cache sizes**:
   ```bash
   # Edit configuration
   vim ~/.skillmeat/config.toml

   # Set cache limits
   [cache]
   max_size_mb = 100
   max_entries = 1000
   ```

3. **Scale horizontally**:
   ```bash
   # Add more instances to distribute load
   docker-compose scale api=3
   ```

4. **Fix memory leak** (if identified):
   - Review recent code changes
   - Use memory profiler to identify leak
   - Deploy fix

## Performance Monitoring

### Key Metrics to Watch

#### RED Metrics (Requests, Errors, Duration)

```promql
# Request Rate
sum(rate(skillmeat_api_requests_total[5m]))

# Error Rate
sum(rate(skillmeat_api_requests_total{status=~"5.."}[5m])) /
sum(rate(skillmeat_api_requests_total[5m]))

# Duration (P50, P95, P99)
histogram_quantile(0.50, rate(skillmeat_api_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(skillmeat_api_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(skillmeat_api_request_duration_seconds_bucket[5m]))
```

#### USE Metrics (Utilization, Saturation, Errors)

```bash
# CPU Utilization
mpstat 1

# Memory Utilization
free -h

# Disk Utilization
df -h

# Network Utilization
iftop

# Load Average
uptime
```

#### Business Metrics

```promql
# Marketplace installs
rate(skillmeat_marketplace_installs_total[1h])

# Bundle operations
rate(skillmeat_bundle_exports_total[1h])
rate(skillmeat_bundle_imports_total[1h])

# MCP deployments
rate(skillmeat_mcp_deployments_total[1h])
```

### Performance Baselines

Establish baselines for normal operation:

| Metric | Baseline | Warning | Critical |
|--------|----------|---------|----------|
| P95 Latency | < 500ms | > 1s | > 5s |
| Error Rate | < 0.1% | > 1% | > 5% |
| Request Rate | 10-100 req/s | N/A | N/A |
| Memory Usage | < 60% | > 80% | > 95% |
| CPU Usage | < 50% | > 80% | > 95% |
| Cache Hit Rate | > 80% | < 60% | < 40% |

## Incident Response Workflow

### 1. Detection

- Alert fires in monitoring system
- User reports issue
- Automated health check fails

### 2. Triage

```bash
# Quick health check
curl http://localhost:8000/health

# Check error rate
curl -s "http://localhost:9090/api/v1/query?query=rate(skillmeat_api_requests_total{status=~\"5..\"}[5m])"

# Check logs for errors
docker logs skillmeat-api 2>&1 | jq 'select(.level == "ERROR")' | tail -50
```

### 3. Investigation

1. **Identify scope**:
   - Is it affecting all requests or specific endpoints?
   - Is it affecting all users or specific users?
   - When did it start?

2. **Gather evidence**:
   - Error logs with trace IDs
   - Metrics showing issue
   - Recent changes or deployments

3. **Form hypothesis**:
   - What could cause this?
   - What changed recently?
   - Has this happened before?

### 4. Mitigation

1. **Stop the bleeding**:
   ```bash
   # Restart service
   systemctl restart skillmeat-api

   # Rollback deployment
   git revert HEAD
   docker-compose up -d --build

   # Scale up resources
   docker-compose scale api=5
   ```

2. **Implement workaround** (if possible):
   - Enable circuit breaker
   - Disable problematic feature
   - Route traffic to healthy instances

### 5. Resolution

1. **Fix root cause**:
   - Deploy bug fix
   - Update configuration
   - Scale resources permanently

2. **Verify fix**:
   ```bash
   # Monitor error rate
   watch -n 5 'curl -s "http://localhost:9090/api/v1/query?query=rate(skillmeat_api_requests_total{status=~\"5..\"}[5m])"'

   # Check logs
   docker logs -f skillmeat-api
   ```

3. **Monitor for recurrence**:
   - Watch metrics for 30+ minutes
   - Check for error spikes
   - Verify user reports

### 6. Post-Mortem

1. **Document incident**:
   - Timeline of events
   - Root cause analysis
   - Impact assessment

2. **Identify improvements**:
   - Better monitoring
   - Better alerts
   - Code improvements
   - Process improvements

3. **Create action items**:
   - Assign owners
   - Set deadlines
   - Track to completion

## Regular Maintenance

### Daily Checks

- Review dashboard for anomalies
- Check error logs for unexpected errors
- Verify all services are healthy
- Review alert firing history

### Weekly Checks

- Review performance trends
- Check disk space usage
- Review GitHub API usage
- Test backup/restore procedures
- Update documentation if needed

### Monthly Checks

- Review and update alert thresholds
- Analyze performance trends
- Review and optimize slow queries
- Update dependencies
- Capacity planning review

## Emergency Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | [Contact Info] | Primary |
| Team Lead | [Contact Info] | Secondary |
| DevOps Team | [Contact Info] | Tertiary |

## Escalation Procedures

1. **Severity 1 (Critical)**:
   - Service completely down
   - Data loss risk
   - Security breach
   - **Action**: Page on-call immediately

2. **Severity 2 (High)**:
   - Partial service degradation
   - High error rate
   - Security vulnerability
   - **Action**: Notify on-call within 15 minutes

3. **Severity 3 (Medium)**:
   - Minor service issues
   - Performance degradation
   - Non-critical bugs
   - **Action**: Create ticket, notify during business hours

4. **Severity 4 (Low)**:
   - Minor bugs
   - Feature requests
   - Documentation updates
   - **Action**: Create ticket, prioritize in backlog

## Additional Resources

- [SkillMeat Documentation](../../README.md)
- [Observability Guide](../observability-guide.md)
- [API Documentation](../../api/README.md)
- [Deployment Guide](../../deployment/README.md)
- [On-Call Handbook](./oncall-handbook.md)

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-17 | 1.0 | Initial runbook | DevOps Team |
