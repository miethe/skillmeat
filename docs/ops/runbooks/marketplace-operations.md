# Marketplace Operations Runbook

Operational guide for SkillMeat marketplace administrators, covering daily operations, monitoring, incident response, and maintenance tasks.

## Table of Contents

- [Overview](#overview)
- [Daily Operations](#daily-operations)
- [Monitoring](#monitoring)
- [Common Tasks](#common-tasks)
- [Incident Response](#incident-response)
- [Maintenance](#maintenance)
- [Alerts and Escalation](#alerts-and-escalation)
- [Contact and Support](#contact-and-support)

## Overview

The SkillMeat Marketplace is the distribution hub for curated artifact bundles. Operations team manages:

- Submission review and moderation
- Broker connections and feeds
- Marketplace health and performance
- Security scanning and compliance
- User support and incident response

### Key Systems

- **API Server** - REST API for marketplace operations
- **Search Engine** - Full-text search index (Elasticsearch)
- **Message Queue** - Async job processing (Redis)
- **Database** - Listings, submissions, users (PostgreSQL)
- **Cache** - Response caching and rate limit tracking (Redis)
- **CDN** - Bundle download distribution (CloudFront)

### Critical Paths

1. **User Search** - Web UI → API → Search Engine → Results
2. **Bundle Download** - CDN Edge → Origin (S3) → Local Cache
3. **Submission** - CLI/Web → Validation → Security Scan → Review Queue
4. **Broker Sync** - Periodic fetch → Transform → Index → Search

## Daily Operations

### Morning Check (8 AM)

**System Status:**
```bash
# Check all service health
curl https://marketplace.skillmeat.dev/health

# Should return:
# {
#   "status": "healthy",
#   "services": {
#     "api": "ok",
#     "search": "ok",
#     "database": "ok",
#     "cache": "ok"
#   }
# }
```

**Dashboard Review:**
```
1. Open Grafana Dashboard
   URL: http://grafana.skillmeat.internal/d/marketplace

2. Check key metrics:
   - API response time (target: <500ms p95)
   - Search response time (target: <1s p95)
   - Error rate (target: <0.5%)
   - Queue depth (target: <100 pending jobs)
```

**Submission Queue:**
```bash
# Check pending submissions
skillmeat admin marketplace submissions --status pending --limit 5

# Expected: Review within 24 hours
# If > 20 pending: escalate to review team
```

**Alert Review:**
```
1. Check PagerDuty for overnight alerts
2. Review alert logs
3. Investigate any P1/P2 alerts
4. Document in incident log
```

### Hourly Checks (Every Hour)

**API Status:**
```bash
# Check endpoint latency
skillmeat admin marketplace metrics --period 1h \
  --metrics api_latency,error_rate

# Alert thresholds:
# - API latency p95 > 1s: CRITICAL
# - Error rate > 1%: CRITICAL
# - API latency p95 > 500ms: WARNING
# - Error rate > 0.5%: WARNING
```

**Search Index Health:**
```bash
# Verify search is working
curl -s "https://marketplace.skillmeat.dev/api/search?q=test" | jq '.status'

# Check index stats
skillmeat admin marketplace search-stats
```

**Queue Status:**
```bash
# Monitor async job queue
skillmeat admin marketplace queue-status

# Queue depth should be:
# - < 100: Normal
# - 100-500: Monitor (may need worker scaling)
# - > 500: CRITICAL (scale workers immediately)
```

### Bundle Publishing Review

**Review Queue:**
```bash
# Check submissions awaiting review
skillmeat admin marketplace submissions \
  --status pending \
  --sort-by created_at \
  --limit 10

# For each submission:
# 1. Review metadata completeness
# 2. Check security scan results
# 3. Verify license compatibility
# 4. Review bundle contents
# 5. Approve or request revisions
```

**Approval Process:**
```bash
# Approve submission
skillmeat admin marketplace submissions approve <submission-id>

# Request revisions
skillmeat admin marketplace submissions request-revisions <submission-id> \
  --reason "Description too short, provide more details about use cases"

# Reject submission
skillmeat admin marketplace submissions reject <submission-id> \
  --reason "Bundled artifacts have incompatible licenses (MIT + GPL-2.0)"
```

**High-Volume Periods:**
- Additional reviewers on call
- Prioritize by rating/downloads
- Expedite popular publishers
- Use templates for common rejections

## Monitoring

### Metrics Dashboard

**Key Performance Indicators:**

```
SEARCH PERFORMANCE:
- Queries per minute (QPS): Baseline ~1000
- p50 latency: <100ms
- p95 latency: <500ms (alert if >1s)
- p99 latency: <2s (alert if >5s)
- Error rate: <0.5% (alert if >1%)

API PERFORMANCE:
- Requests per minute: Baseline ~5000
- p50 latency: <50ms
- p95 latency: <200ms (alert if >500ms)
- p99 latency: <1s (alert if >5s)
- Error rate: <0.5% (alert if >1%)

PUBLISHING:
- Submissions per day: Typically 5-20
- Pending submissions: Target <5
- Average review time: <4 hours
- Approval rate: ~80%

DOWNLOADS:
- Total bundles downloaded: Tracking
- Unique users: Baseline growing
- Repeat users (30 days): ~40%
- Popular bundles (top 10): 30% of downloads

CACHE:
- Hit rate: Target >70% (alert if <60%)
- Eviction rate: Should be minimal
- Memory usage: Monitor growth trend
```

**Access Monitoring:**

```bash
# Real-time metrics
curl https://marketplace.skillmeat.dev/metrics

# Prometheus integration
# Scrape endpoint: https://marketplace.skillmeat.dev/metrics
# Interval: 30s
# Retention: 90 days
```

### Search Index Health

**Index Status:**
```bash
# Check Elasticsearch cluster
curl -s http://elasticsearch:9200/_cluster/health | jq '.status'

# Should return: "green"
# "yellow" = minor issue, "red" = critical issue

# Check index stats
curl -s http://elasticsearch:9200/marketplace/_stats | jq '.indices.marketplace'
```

**Stale Indices:**
```bash
# Last index refresh time
curl -s http://elasticsearch:9200/marketplace/_mapping | jq '.[]'

# If last refresh > 1 hour:
# 1. Check syncer status
# 2. Check for broker sync failures
# 3. Manually trigger sync if needed
```

### Database Performance

**Query Performance:**
```bash
# Check slow query log
tail -f /var/log/postgresql/slow-queries.log

# Queries > 1 second = slow
# If > 10 slow queries per hour: escalate

# Check for long-running transactions
psql -c "SELECT * FROM pg_stat_activity WHERE state='active' AND query_start < now() - interval '5 min';"
```

**Replication Lag:**
```bash
# For read replicas, check lag
psql -c "SELECT extract(epoch from (now() - pg_last_wal_receive_lsn()));"

# If > 10 seconds: investigate and escalate
# If > 1 minute: failover may be required
```

### Rate Limiting

**Rate Limit Status:**
```bash
# Check rate limit cache (Redis)
redis-cli INFO

# Key metrics:
# - used_memory_human: Should be stable
# - connected_clients: Normal operation ~10
# - evicted_keys: Should be minimal

# Rate limits:
# - Unauthenticated: 100 req/min
# - Authenticated: 1000 req/min
# - Publishing: 10 req/hour
```

## Common Tasks

### Adding New Broker

**Create Broker Configuration:**

```bash
# Create new broker definition
skillmeat admin marketplace brokers create \
  --name "anthropic-hub" \
  --url "https://marketplace.anthropic.com/api" \
  --type "remote" \
  --sync-interval "6h" \
  --auth-token "env:BROKER_API_TOKEN"
```

**Test Broker Connection:**

```bash
# Verify broker is reachable
skillmeat admin marketplace brokers test anthropic-hub

# Should output:
# ✓ Connection successful
# ✓ Authentication valid
# ✓ Fetched sample metadata
# Version: 1.0, Artifacts: 245
```

**Initial Sync:**

```bash
# Trigger full sync from broker
skillmeat admin marketplace brokers sync anthropic-hub --full

# Monitor progress
skillmeat admin marketplace jobs --broker anthropic-hub --status running

# Check results
skillmeat admin marketplace brokers stats anthropic-hub
```

**Enable Broker:**

```bash
# Activate broker for search and browsing
skillmeat admin marketplace brokers enable anthropic-hub

# Verify it's searchable
skillmeat marketplace-search --broker anthropic-hub "test"
```

### Clearing Cache

**Cache Invalidation:**

```bash
# Clear all marketplace cache
skillmeat admin marketplace cache clear

# Or specific caches:
skillmeat admin marketplace cache clear --type search    # Search index
skillmeat admin marketplace cache clear --type api       # API responses
skillmeat admin marketplace cache clear --type cdn       # CDN cache
```

**Partial Cache Clear:**

```bash
# Clear cache for specific bundle
skillmeat admin marketplace cache clear --bundle skillmeat-42

# Clear cache for specific broker
skillmeat admin marketplace cache clear --broker skillmeat
```

### Handling Submission Issues

**Check Submission Details:**
```bash
# Get full submission info
skillmeat admin marketplace submissions show <submission-id> --full

# Shows:
# - Bundle manifest
# - Validation results
# - Security scan report
# - Publisher info
# - Metadata completeness
```

**Security Scan Review:**
```bash
# View detailed scan results
skillmeat admin marketplace submissions scan-results <submission-id>

# Review any findings:
# - Potential secrets (review for false positives)
# - Suspicious patterns (code review if needed)
# - File type violations
```

**License Compatibility Check:**
```bash
# View license analysis
skillmeat admin marketplace submissions licenses <submission-id>

# Check:
# - Bundle license validity
# - Artifact licenses
# - Compatibility matrix
# - Any conflicts
```

### Updating Marketplace Feeds

**Broker Sync:**
```bash
# Sync specific broker
skillmeat admin marketplace brokers sync skillmeat

# Or sync all brokers
skillmeat admin marketplace brokers sync-all

# Monitor sync progress
skillmeat admin marketplace jobs --type broker-sync --limit 5
```

**Re-index Search:**
```bash
# If search becomes out of sync
skillmeat admin marketplace search reindex

# This is resource-intensive, do during low-traffic periods:
# - Schedule for 2-4 AM UTC
# - Monitor Elasticsearch CPU/memory
# - Expected time: 10-30 minutes
```

### Performance Tuning

**Search Query Optimization:**
```bash
# Analyze slow searches
skillmeat admin marketplace search analyze --threshold 1s

# Output shows:
# - Slow queries
# - Frequency
# - Index usage
# - Suggestions for indexing

# Add index if recommended
skillmeat admin marketplace search index-add --field publisher_name
```

**Database Query Optimization:**
```bash
# Analyze slow database queries
skillmeat admin marketplace db analyze --threshold 1s

# Run VACUUM and ANALYZE
psql -c "VACUUM ANALYZE;"

# Check for missing indexes
psql -c "SELECT * FROM pg_stat_user_indexes ORDER BY idx_scan;"
```

## Incident Response

### High Error Rate (>1%)

**Severity:** CRITICAL

**Steps:**

1. **Immediate Response:**
   ```bash
   # Confirm error rate
   curl https://marketplace.skillmeat.dev/metrics | grep http_requests_total

   # Check application logs
   tail -f /var/log/skillmeat/marketplace-api.log | grep ERROR
   ```

2. **Root Cause Analysis:**
   ```bash
   # Check what's failing
   grep ERROR /var/log/skillmeat/marketplace-api.log | tail -20 | sort | uniq -c

   # Common causes:
   # - Database connection pool exhausted
   # - Elasticsearch unavailable
   # - Search indexing failure
   # - Rate limit misconfiguration
   ```

3. **Mitigation:**
   ```bash
   # Restart affected service
   systemctl restart skillmeat-marketplace-api

   # Or scale horizontally
   kubectl scale deployment marketplace-api --replicas 5
   ```

4. **Resolution:**
   - Address root cause
   - Verify error rate returns to normal
   - Post-incident review

### High Latency (API p95 > 1s)

**Severity:** HIGH

**Steps:**

1. **Confirm Issue:**
   ```bash
   # Check API latency
   curl -w "@curl-format.txt" -o /dev/null -s https://marketplace.skillmeat.dev/api/search?q=test

   # Expected: <500ms
   # If > 1s: investigate
   ```

2. **Identify Bottleneck:**
   ```bash
   # Check database slow queries
   psql -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

   # Check Elasticsearch
   curl -s http://elasticsearch:9200/_nodes/stats | jq '.nodes[] | {name, indices, jvm}'

   # Check memory/CPU
   top -b -n 1 | head -20
   ```

3. **Remediation:**
   ```bash
   # If database slow:
   psql -c "ANALYZE;"  # Optimize query planner

   # If Elasticsearch slow:
   curl -X POST "elasticsearch:9200/_cache/clear"

   # If resource constrained:
   # Add more resources or scale horizontally
   ```

### Search Not Working

**Severity:** CRITICAL

**Steps:**

1. **Verify Issue:**
   ```bash
   curl -s "https://marketplace.skillmeat.dev/api/search?q=python" | jq '.error'

   # If returns error: search is down
   ```

2. **Check Elasticsearch:**
   ```bash
   # Is cluster healthy?
   curl -s http://elasticsearch:9200/_cluster/health | jq '.status'

   # If not green:
   # - Check unassigned shards
   # - Check disk space
   # - Restart node if needed
   ```

3. **Rebuild Index:**
   ```bash
   # If index corrupted
   skillmeat admin marketplace search reindex

   # Estimated time: 15-30 minutes
   # User impact: Search unavailable during rebuild
   ```

### CDN Distribution Failures

**Severity:** HIGH

**Steps:**

1. **Verify Issue:**
   ```bash
   # Test CDN endpoint
   curl -I https://cdn.marketplace.skillmeat.dev/bundles/skillmeat-42.skillmeat-pack

   # Check response time and cache status
   ```

2. **Check Origin:**
   ```bash
   # Test S3 directly
   curl -I https://s3.amazonaws.com/skillmeat-marketplace/bundles/skillmeat-42.skillmeat-pack

   # If S3 is up but CDN fails:
   # - Check CloudFront distribution status
   # - Verify origin DNS resolves
   # - Check security groups/IAM
   ```

3. **Invalidate Cache:**
   ```bash
   # If files updated
   aws cloudfront create-invalidation \
     --distribution-id E123ABC \
     --paths "/*"

   # Wait 5-10 minutes for propagation
   ```

### Database Replication Lag

**Severity:** MEDIUM

**Steps:**

1. **Check Replication:**
   ```bash
   # On primary
   psql -c "SELECT * FROM pg_stat_replication;"

   # On replica
   psql -c "SELECT extract(epoch from (now() - pg_last_wal_receive_lsn()));"
   ```

2. **Cause Analysis:**
   - Long-running transaction on primary
   - High write volume
   - Network latency
   - Replica resource constraints

3. **Resolution:**
   ```bash
   # Cancel long transaction if blocking
   psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE 'UPDATE%';"

   # Monitor until lag < 10 seconds
   # If persistent: investigate replica resources
   ```

### Security Scanning Failures

**Severity:** HIGH (blocks submissions)

**Steps:**

1. **Check Scanner Service:**
   ```bash
   # Verify security scanner is running
   systemctl status skillmeat-security-scanner

   # Check logs
   tail -f /var/log/skillmeat/security-scanner.log | grep ERROR
   ```

2. **Restart Service:**
   ```bash
   systemctl restart skillmeat-security-scanner
   ```

3. **Manual Scan:**
   ```bash
   # If service doesn't recover
   skillmeat admin marketplace submissions scan <submission-id> --force
   ```

## Maintenance

### Daily (Automated)

- Broker sync (every 6 hours)
- Cache expiration (continuous)
- Log rotation (daily at 2 AM)
- Metrics collection (continuous)

### Weekly

**Database Maintenance:**
```bash
# Tuesday 2 AM UTC
psql -c "VACUUM ANALYZE;"
psql -c "REINDEX DATABASE marketplace;"
```

**Search Index Optimization:**
```bash
# Tuesday 3 AM UTC
curl -X POST "elasticsearch:9200/_optimize?max_num_segments=1"
```

**Backup Verification:**
```bash
# Verify latest backups are valid
aws s3 ls s3://skillmeat-backups/marketplace/ | tail -5
```

### Monthly

**Full Reindex:**
```bash
# First Sunday of month, 1 AM UTC
# During low-traffic period
skillmeat admin marketplace search reindex --full

# Estimated duration: 30-60 minutes
# May impact search performance
```

**Performance Analysis:**
```bash
# Generate performance report
skillmeat admin marketplace report performance --period 30days --output report.json

# Identify trends:
# - Latency increase
# - Error rate changes
# - Popular features
# - Performance regressions
```

**Security Audit:**
```bash
# Review all published bundles
skillmeat admin marketplace audit security --days 30

# Check for:
# - Policy violations
# - Security updates needed
# - Suspicious patterns
```

## Alerts and Escalation

### Alert Levels

**P0 (Critical):**
- Marketplace completely down
- All searches failing
- Database unavailable
- Security breach detected

**Response:** Immediate (5 min), ops on-call

**P1 (High):**
- Error rate > 5%
- API latency p95 > 2s
- Search latency p95 > 5s
- Security scan failing

**Response:** Urgent (15 min), ops on-call or eng manager

**P2 (Medium):**
- Error rate > 1%
- API latency p95 > 500ms
- Delayed broker sync
- Cache performance degraded

**Response:** Within 1 hour, ops engineer

**P3 (Low):**
- Warnings in logs
- Minor performance issues
- Non-critical features degraded

**Response:** Next business day

### Alert Configuration

**PagerDuty Integration:**
```
Trigger Policies:

1. Marketplace Down (P0)
   - If /health returns error for 2 consecutive checks
   - Alert: On-call ops engineer
   - Escalate: After 10 minutes

2. High Error Rate (P1)
   - If error_rate > 5% for 5 minutes
   - Alert: On-call ops engineer
   - Escalate: After 10 minutes

3. High Latency (P1)
   - If api_latency_p95 > 2s for 5 minutes
   - Alert: On-call ops engineer
   - Escalate: After 15 minutes

4. Search Issues (P1)
   - If search_errors > 10/min or search unavailable
   - Alert: On-call ops engineer
   - Escalate: After 10 minutes

5. Database Issues (P1)
   - If db_connection_errors > 5
   - Alert: On-call dba
   - Escalate: After 10 minutes
```

## Contact and Support

### Operations Team

**On-Call Rotation:**
- Schedule: PagerDuty
- Primary: See weekly rotation
- Backup: See weekly rotation

**Escalation:**
- Ops Manager: escalation@skillmeat.com
- Engineering Manager: eng-manager@skillmeat.com
- Director: director@skillmeat.com

### External Contacts

**AWS Support:**
- Account: skillmeat-prod
- Case: Create in AWS Console
- Preferred contact: ops-aws@skillmeat.com

**Database Vendor:**
- PostgreSQL community
- Elasticsearch support (if commercial)

### Communication Channels

**Internal:**
- Slack: #skillmeat-operations
- Incident channel: #incident-<id>
- War room: Zoom link in incidents

**Customer Communication:**
- Status page: https://status.skillmeat.com
- Email: support@skillmeat.com
- Twitter: @skillmeat

## See Also

- [Marketplace Troubleshooting](./marketplace-troubleshooting.md)
- [MCP Operations Runbook](./mcp-operations.md)
- [Security Scanning Guide](../guides/publishing-to-marketplace.md#security-requirements)
- [Monitoring Dashboard](http://grafana.skillmeat.internal/d/marketplace)
