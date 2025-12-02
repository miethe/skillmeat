---
title: "Cache Troubleshooting Guide"
description: "Solutions for common cache issues and optimization tips"
audience: [developers, users, maintainers]
tags: [cache, troubleshooting, debugging, performance, optimization]
created: 2025-12-01
updated: 2025-12-01
category: "guides"
status: "published"
related: ["configuration-guide.md", "api-reference.md", "architecture-decision-record.md"]
---

# Cache Troubleshooting Guide

Common cache issues, diagnostic commands, and solutions to keep your SkillMeat cache running smoothly.

## Table of Contents

- [Diagnostic Commands](#diagnostic-commands)
- [Common Issues](#common-issues)
- [Performance Optimization](#performance-optimization)
- [Debug Logging](#debug-logging)
- [Cache Corruption Recovery](#cache-corruption-recovery)
- [Monitoring and Health Checks](#monitoring-and-health-checks)

## Diagnostic Commands

### Check Cache Status

```bash
# Get comprehensive cache status
skillmeat cache status

# Output:
# Cache Status
# ├─ Total Projects:      12
# ├─ Total Artifacts:     87
# ├─ Stale Projects:      2
# ├─ Outdated Artifacts:  5
# ├─ Cache Size:          156.3 MB
# ├─ Hit Rate:            87.3%
# ├─ Last Refresh:        2025-12-01T12:00:00Z
# └─ Refresh Running:     true
```

### Verify Cache Database

```bash
# Check cache database integrity
skillmeat cache check

# Output:
# Cache Database Check
# ├─ Database: OK
# ├─ Tables: OK (3 tables)
# ├─ Records: OK (87 artifacts, 12 projects)
# └─ Indexes: OK

# Or with errors:
# Cache Database Check
# ├─ Database: ERROR
# ├─ Message: Database corruption detected
# ├─ Recommendation: Run 'skillmeat cache rebuild'
```

### List Cache Statistics

```bash
# Get detailed cache statistics
skillmeat cache stats

# Output:
# Cache Statistics
# ├─ Total Projects:      12
# ├─ Active Projects:     10
# ├─ Stale Projects:      2
# ├─ Total Artifacts:     87
# ├─ Outdated Artifacts:  5
# ├─ Cache Size:          156.3 MB
# ├─ Hit Rate:            87.3%
# ├─ Miss Rate:           12.7%
# ├─ Last Refresh:        2025-12-01T12:00:00Z
# ├─ Oldest Entry:        2025-11-15T08:30:00Z
# └─ Newest Entry:        2025-12-01T14:22:00Z
```

### Check Refresh Job Status

```bash
# Check background refresh scheduler
skillmeat cache refresh-status

# Output:
# Refresh Job Status
# ├─ Running:            true
# ├─ Next Run:           2025-12-01T18:00:00Z
# ├─ Last Run:           2025-12-01T12:00:00Z
# ├─ Last Duration:      3.45 seconds
# ├─ Failures:           0
# └─ Last Error:         None
```

## Common Issues

### Cache Not Updating

**Symptoms:**
- Web UI shows stale data
- CLI shows different data than API
- `Last Refresh` timestamp is old
- Stale projects count is high

**Diagnostics:**

```bash
# Check refresh job status
skillmeat cache refresh-status

# Check if background refresh is enabled
skillmeat config get cache.enable_background_refresh

# Check refresh interval
skillmeat config get cache.refresh_interval_hours

# Check for errors in logs
skillmeat logs cache --level ERROR
```

**Solutions:**

1. **Enable background refresh if disabled:**

```bash
skillmeat config set cache.enable_background_refresh true
```

2. **Check and adjust refresh interval:**

```bash
# Current setting
skillmeat config get cache.refresh_interval_hours

# Set to more frequent refresh (e.g., every 2 hours)
skillmeat config set cache.refresh_interval_hours 2.0
```

3. **Force manual refresh:**

```bash
# Refresh all projects
skillmeat cache refresh --force

# Refresh specific project
skillmeat cache refresh --force --project proj-123
```

4. **Restart refresh scheduler:**

```bash
# Stop and restart (if API running)
curl -X POST http://localhost:8000/api/v1/cache/refresh \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Cache Too Large

**Symptoms:**
- Disk space usage is high
- Cache operations are slow
- Frequent out-of-memory errors
- Cache size exceeds configured limit

**Diagnostics:**

```bash
# Check cache size
skillmeat cache status | grep "Cache Size"

# Get detailed size breakdown
du -sh ~/.skillmeat/cache/

# Check configured max size
skillmeat config get cache.max_cache_size_mb

# Check cleanup retention days
skillmeat config get cache.cleanup_retention_days
```

**Solutions:**

1. **Run cache cleanup:**

```bash
# Cleanup old entries (default: older than retention days)
skillmeat cache cleanup

# Cleanup entries older than 60 days
skillmeat cache cleanup --older-than-days 60

# Prune to specific size
skillmeat cache cleanup --max-size-mb 500

# Output:
# Cache Cleanup Report
# ├─ Entries Removed:    234
# ├─ Space Freed:        45.3 MB
# ├─ New Cache Size:     111.0 MB
# └─ Status:             OK
```

2. **Adjust retention policy:**

```bash
# Reduce retention from 30 to 14 days
skillmeat config set cache.cleanup_retention_days 14

# Run cleanup to apply new policy
skillmeat cache cleanup
```

3. **Reduce TTL to avoid storing stale data:**

```bash
# Set shorter TTL (4 hours instead of 6)
skillmeat config set cache.ttl_minutes 240

# This will cause entries to expire sooner
```

4. **Set lower max cache size:**

```bash
# Set max to 200 MB (from default 500)
skillmeat config set cache.max_cache_size_mb 200

# Cleanup will enforce limit
skillmeat cache cleanup
```

5. **Clear entire cache if necessary (last resort):**

```bash
# WARNING: This will remove all cache entries
skillmeat cache clear

# Confirm: This will delete all cache data. Continue? [y/N]: y
# Cache cleared successfully
```

### Stale Data in Web UI

**Symptoms:**
- Artifact versions show as outdated incorrectly
- Project status shows as "stale" but is active
- Data doesn't update even after refresh

**Diagnostics:**

```bash
# Check last refresh time
skillmeat cache status | grep "Last Refresh"

# Check stale projects
skillmeat cache projects --status stale

# Manually check project metadata
skillmeat config get cache.ttl_minutes
```

**Solutions:**

1. **Force refresh all stale projects:**

```bash
# Refresh with force flag
skillmeat cache refresh --force

# Or via API
curl -X POST http://localhost:8000/api/v1/cache/refresh \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

2. **Invalidate specific project:**

```bash
# Mark project as stale to force refresh
skillmeat cache invalidate --project proj-123

# Refresh
skillmeat cache refresh
```

3. **Reduce TTL for fresher data:**

```bash
# Set very short TTL for testing (30 minutes)
skillmeat config set cache.ttl_minutes 30

# Projects will refresh sooner
```

### Cache Corruption

**Symptoms:**
- Database errors in logs
- "Database corruption detected" in cache check
- Inability to query cache
- Unexplained crashes

**Diagnostics:**

```bash
# Check database integrity
skillmeat cache check

# Output might show:
# Cache Database Check
# ├─ Database: ERROR
# └─ Message: Database corruption detected at page 123

# View detailed logs
skillmeat logs cache --level ERROR --tail 50
```

**Solutions:**

1. **Attempt automatic repair:**

```bash
# Rebuild cache database
skillmeat cache rebuild

# This will:
# - Validate all entries
# - Remove corrupted entries
# - Reindex database
# - Output repair report

# Output:
# Cache Rebuild Report
# ├─ Entries Checked:     87
# ├─ Entries Repaired:    3
# ├─ Entries Removed:     1
# └─ Status:              OK
```

2. **If rebuild fails, clear and resync:**

```bash
# Clear entire cache
skillmeat cache clear

# Force full refresh
skillmeat cache refresh --force

# This will repopulate cache from projects
```

3. **Check disk space:**

```bash
# Ensure sufficient disk space
df -h ~/.skillmeat/

# If low on space, cleanup:
skillmeat cache cleanup --max-size-mb 200
```

### Refresh Job Failures

**Symptoms:**
- Refresh job stops running
- "Last Error" shows error message
- Frequent refresh timeout errors
- Projects marked as error status

**Diagnostics:**

```bash
# Check refresh status
skillmeat cache refresh-status

# Check for errors
skillmeat logs cache --level ERROR

# Check system resources
free -h  # Memory
df -h    # Disk space
ps aux | grep skillmeat  # CPU usage
```

**Solutions:**

1. **Increase refresh timeout:**

```bash
# If refreshes are timing out
skillmeat config set cache.refresh_timeout_seconds 300  # 5 minutes
```

2. **Reduce concurrent refreshes:**

```bash
# Too many concurrent operations
skillmeat config set cache.max_concurrent_refreshes 2  # Down from 3
```

3. **Increase refresh interval to reduce frequency:**

```bash
# Refresh less frequently
skillmeat config set cache.refresh_interval_hours 12.0  # 12 hours
```

4. **Check and fix network issues:**

```bash
# Test connectivity to projects
ping -c 3 <project-host>

# Test API connectivity
curl -I http://localhost:8000/api/v1/health

# Check DNS resolution
nslookup github.com
```

5. **Restart refresh job:**

```bash
# Via CLI (if available)
skillmeat cache restart-refresh

# Via API
curl -X POST http://localhost:8000/api/v1/cache/refresh \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

## Performance Optimization

### Monitor Cache Hit Rate

```bash
# Check cache statistics
skillmeat cache stats

# Look for "Hit Rate" - should be > 80%
# If lower, consider:
# - Longer TTL
# - More frequent refreshes
# - Larger cache size
```

### Optimize Refresh Settings

**For high-traffic systems:**

```bash
# More concurrent refreshes
skillmeat config set cache.max_concurrent_refreshes 5

# Shorter refresh interval
skillmeat config set cache.refresh_interval_hours 3.0

# Longer TTL to reduce refreshes
skillmeat config set cache.ttl_minutes 480  # 8 hours
```

**For resource-constrained systems:**

```bash
# Fewer concurrent refreshes
skillmeat config set cache.max_concurrent_refreshes 1

# Longer refresh interval
skillmeat config set cache.refresh_interval_hours 24.0

# Shorter TTL to minimize storage
skillmeat config set cache.ttl_minutes 240  # 4 hours
```

### Database Optimization

```bash
# Rebuild and optimize database (vacuuming)
skillmeat cache optimize

# Output:
# Cache Optimization Report
# ├─ Original Size:       156.3 MB
# ├─ Optimized Size:      142.1 MB
# ├─ Space Saved:         14.2 MB
# └─ Status:              OK
```

### Use Indexes Effectively

Cached queries benefit from database indexes:

```bash
# Via API - indexed queries
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/artifacts?type=skill&is_outdated=true"

# This is faster than:
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/artifacts" | \
  jq 'select(.type=="skill" and .is_outdated==true)'
```

## Debug Logging

### Enable Debug Logging

```bash
# Set log level to DEBUG
export SKILLMEAT_LOG_LEVEL=DEBUG

# Start API server
skillmeat web dev --api-only

# Or for CLI
skillmeat cache status --debug
```

### View Cache Logs

```bash
# View cache-specific logs
skillmeat logs cache

# View with filters
skillmeat logs cache --level ERROR
skillmeat logs cache --level WARNING
skillmeat logs cache --tail 100  # Last 100 lines

# View in real-time
skillmeat logs cache --follow

# Search logs
skillmeat logs cache | grep "refresh"
skillmeat logs cache | grep "stale"
```

### Enable Query Logging

```bash
# Log all cache queries
export SKILLMEAT_CACHE_LOG_QUERIES=true

# Check logs for performance
skillmeat logs cache | grep "query_time"

# Example output:
# [2025-12-01 12:00:00] Query: get_projects, Time: 45ms, Rows: 12
# [2025-12-01 12:00:01] Query: get_artifacts, Time: 127ms, Rows: 87
```

## Cache Corruption Recovery

### Step-by-Step Recovery

1. **Stop all operations:**

```bash
# Stop API server
pkill -f "uvicorn.*skillmeat"

# Stop CLI operations
pkill -f "skillmeat cache"
```

2. **Check current state:**

```bash
# Backup current cache
cp -r ~/.skillmeat/cache ~/.skillmeat/cache.backup

# Check integrity
skillmeat cache check
```

3. **Attempt repair:**

```bash
# Rebuild database
skillmeat cache rebuild

# Verify
skillmeat cache check
```

4. **If rebuild fails:**

```bash
# Clear cache
skillmeat cache clear

# Restore from backup if needed
rm -rf ~/.skillmeat/cache
cp -r ~/.skillmeat/cache.backup ~/.skillmeat/cache
```

5. **Force full resync:**

```bash
# Clear cache entirely
skillmeat cache clear

# Force refresh of all projects
skillmeat cache refresh --force

# Verify
skillmeat cache status
```

### Backup and Restore

```bash
# Create backup
tar -czf ~/cache-backup-$(date +%Y%m%d).tar.gz ~/.skillmeat/cache

# Restore from backup
tar -xzf ~/cache-backup-20251201.tar.gz -C ~/

# List backups
ls -lh ~/cache-backup-*.tar.gz
```

## Monitoring and Health Checks

### Health Check Endpoint

```bash
# Check API and cache health
curl http://localhost:8000/health

# Output:
# {
#   "status": "healthy",
#   "cache": "healthy",
#   "refresh_job": "running"
# }
```

### Automated Health Monitoring

```bash
# Create health check script
cat > ~/bin/check-cache-health.sh << 'EOF'
#!/bin/bash

# Check cache status
STATUS=$(skillmeat cache status)
STALE=$(echo "$STATUS" | grep "Stale Projects" | grep -o '[0-9]*')

if [ "$STALE" -gt 5 ]; then
  echo "WARNING: Cache has $STALE stale projects"
  skillmeat cache refresh --force
fi

# Check cache size
SIZE=$(du -b ~/.skillmeat/cache/cache.db | cut -f1)
MAX=$((500 * 1024 * 1024))  # 500 MB

if [ "$SIZE" -gt "$MAX" ]; then
  echo "WARNING: Cache size exceeds limit"
  skillmeat cache cleanup
fi
EOF

chmod +x ~/bin/check-cache-health.sh

# Run periodically via cron
crontab -e
# Add: 0 * * * * ~/bin/check-cache-health.sh
```

### Set Up Alerts

```bash
# Create alert script
cat > ~/bin/cache-alert.sh << 'EOF'
#!/bin/bash

THRESHOLD_STALE=10
THRESHOLD_SIZE=400  # MB

STALE=$(skillmeat cache status | grep "Stale Projects" | grep -o '[0-9]*')
SIZE=$(du -m ~/.skillmeat/cache/cache.db | cut -f1)

if [ "$STALE" -gt "$THRESHOLD_STALE" ]; then
  # Send alert (email, Slack, etc.)
  echo "ALERT: Cache has $STALE stale projects" | mail -s "Cache Alert" admin@example.com
fi

if [ "$SIZE" -gt "$THRESHOLD_SIZE" ]; then
  echo "ALERT: Cache size is ${SIZE}MB" | mail -s "Cache Size Alert" admin@example.com
fi
EOF

chmod +x ~/bin/cache-alert.sh
```

### Dashboard Queries

```bash
# Get metrics for monitoring dashboard
curl -s http://localhost:8000/api/v1/cache/status | jq '
{
  total_projects: .total_projects,
  total_artifacts: .total_artifacts,
  stale_projects: .stale_projects,
  outdated_artifacts: .outdated_artifacts,
  cache_size_mb: (.cache_size_bytes / (1024 * 1024)),
  is_healthy: (.stale_projects < 5 and .cache_size_bytes < (500 * 1024 * 1024))
}'
```

## Quick Reference

| Issue | Command | Expected Result |
|-------|---------|-----------------|
| Check status | `skillmeat cache status` | Shows cache statistics |
| Force refresh | `skillmeat cache refresh --force` | Refreshes all projects |
| Clean cache | `skillmeat cache cleanup` | Removes old entries |
| Clear all | `skillmeat cache clear` | Deletes entire cache |
| Verify integrity | `skillmeat cache check` | Reports OK or errors |
| Rebuild database | `skillmeat cache rebuild` | Repairs corruption |
| Optimize storage | `skillmeat cache optimize` | Reduces cache size |

## When to Contact Support

If you've tried these solutions and still have issues:

1. Collect diagnostic information:

```bash
# Generate diagnostic report
skillmeat cache diagnose > cache-diagnostics.txt

# Includes:
# - System info
# - Cache configuration
# - Database integrity
# - Recent logs
# - Statistics
```

2. Include in support request:
   - `cache-diagnostics.txt`
   - Relevant error messages
   - Steps to reproduce
   - System information (OS, RAM, disk space)

## See Also

- [Configuration Guide](configuration-guide.md) - Cache settings
- [API Reference](api-reference.md) - API endpoints
- [Architecture Decision Record](architecture-decision-record.md) - Design decisions
