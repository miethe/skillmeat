---
title: "Cache Configuration Guide"
description: "How to configure and manage the SkillMeat persistent cache system"
audience: [developers, users, maintainers]
tags: [cache, configuration, performance, TTL, storage]
created: 2025-12-01
updated: 2025-12-01
category: "reference"
status: "published"
related: ["api-reference.md", "troubleshooting-guide.md", "architecture-decision-record.md"]
---

# Cache Configuration Guide

The SkillMeat cache system provides persistent storage for project metadata and artifact information with configurable TTL (Time-To-Live), automatic refresh scheduling, and comprehensive management options.

## Table of Contents

- [Overview](#overview)
- [Cache Configuration](#cache-configuration)
- [Environment Variables](#environment-variables)
- [CLI Configuration Commands](#cli-configuration-commands)
- [Programmatic Configuration](#programmatic-configuration)
- [Cache Locations](#cache-locations)
- [Configuration Examples](#configuration-examples)
- [Best Practices](#best-practices)

## Overview

The cache system automatically stores and manages:

- **Project metadata** - Project paths, status, artifact counts
- **Artifact information** - Name, type, versions, deployment status
- **Marketplace data** - Available artifacts and their metadata
- **Version information** - Deployed vs. upstream versions

Cache entries are automatically invalidated after the configured TTL expires, prompting a refresh on next access.

## Cache Configuration

### Core Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl_minutes` | int | 360 | Time-to-live for cache entries in minutes (6 hours) |
| `cache_path` | string | `~/.skillmeat/cache/` | Directory where cache database is stored |
| `cleanup_retention_days` | int | 30 | Days to retain old cache entries before cleanup |
| `enable_background_refresh` | bool | true | Enable automatic background cache refresh |
| `refresh_interval_hours` | float | 6.0 | Hours between automatic cache refreshes |
| `max_concurrent_refreshes` | int | 3 | Maximum concurrent refresh operations |
| `max_cache_size_mb` | int | 500 | Maximum cache database size in megabytes |

### Configuration File Format

Cache configuration is stored in `~/.skillmeat/config.toml`:

```toml
[cache]
# Time-to-live in minutes (6 hours = 360 minutes)
ttl_minutes = 360

# Storage location (relative to collection directory)
cache_path = "cache/"

# Cleanup policy
cleanup_retention_days = 30

# Background refresh settings
enable_background_refresh = true
refresh_interval_hours = 6.0
max_concurrent_refreshes = 3

# Size limits
max_cache_size_mb = 500

# Optional: Per-project refresh intervals
[cache.project_refresh_intervals]
# Override default interval for specific projects
"my-critical-project" = 2.0  # 2 hours instead of 6
"experimental-project" = 24.0  # 24 hours for less critical projects
```

## Environment Variables

Configure cache behavior via environment variables. These override config file settings:

### Basic Configuration

```bash
# Time-to-live in minutes
export SKILLMEAT_CACHE_TTL_MINUTES=360

# Cache storage path
export SKILLMEAT_CACHE_PATH="~/.skillmeat/cache/"

# Cleanup retention period
export SKILLMEAT_CACHE_CLEANUP_RETENTION_DAYS=30
```

### Background Refresh

```bash
# Enable/disable background refresh
export SKILLMEAT_CACHE_ENABLE_BACKGROUND_REFRESH=true

# Refresh interval in hours
export SKILLMEAT_CACHE_REFRESH_INTERVAL_HOURS=6.0

# Maximum concurrent refresh operations
export SKILLMEAT_CACHE_MAX_CONCURRENT_REFRESHES=3
```

### Size Management

```bash
# Maximum cache database size in MB
export SKILLMEAT_CACHE_MAX_CACHE_SIZE_MB=500
```

### Complete .env Example

```bash
# ~/.skillmeat/.env
SKILLMEAT_CACHE_TTL_MINUTES=360
SKILLMEAT_CACHE_PATH=~/.skillmeat/cache/
SKILLMEAT_CACHE_CLEANUP_RETENTION_DAYS=30
SKILLMEAT_CACHE_ENABLE_BACKGROUND_REFRESH=true
SKILLMEAT_CACHE_REFRESH_INTERVAL_HOURS=6.0
SKILLMEAT_CACHE_MAX_CONCURRENT_REFRESHES=3
SKILLMEAT_CACHE_MAX_CACHE_SIZE_MB=500
```

## CLI Configuration Commands

### View Current Cache Configuration

```bash
# Show all cache settings
skillmeat config list --filter cache

# Output:
# Cache Configuration
# ┌─────────────────────────────┬────────────┐
# │ Key                         │ Value      │
# ├─────────────────────────────┼────────────┤
# │ cache.ttl_minutes           │ 360        │
# │ cache.cache_path            │ ~/.skillmeat/cache/ │
# │ cache.cleanup_retention_days│ 30         │
# │ cache.enable_background_refresh│ true    │
# │ cache.refresh_interval_hours│ 6.0        │
# └─────────────────────────────┴────────────┘
```

### Set Cache Configuration

```bash
# Set TTL to 2 hours (120 minutes)
skillmeat config set cache.ttl_minutes 120

# Set refresh interval to 3 hours
skillmeat config set cache.refresh_interval_hours 3.0

# Disable background refresh
skillmeat config set cache.enable_background_refresh false

# Set maximum cache size
skillmeat config set cache.max_cache_size_mb 1000

# Set cleanup retention to 60 days
skillmeat config set cache.cleanup_retention_days 60
```

### Get Specific Setting

```bash
# Get current TTL
skillmeat config get cache.ttl_minutes

# Output: 360

# Get refresh interval
skillmeat config get cache.refresh_interval_hours

# Output: 6.0
```

### Reset Cache Configuration to Defaults

```bash
# Reset all cache settings to defaults
skillmeat cache reset-config

# Confirmation: This will reset all cache configuration to defaults. Continue? [y/N]: y
# Cache configuration reset successfully
```

## Programmatic Configuration

### Python API

```python
from skillmeat.cache.manager import CacheManager
from skillmeat.cache.refresh import RefreshJob

# Create cache manager with custom settings
cache_manager = CacheManager(
    ttl_minutes=180,  # 3 hours
    cache_path="~/.skillmeat/cache/",
    cleanup_retention_days=30,
)

# Initialize the cache
cache_manager.initialize_cache()

# Create refresh job with custom settings
refresh_job = RefreshJob(
    cache_manager=cache_manager,
    interval_hours=4.0,  # Refresh every 4 hours
    max_concurrent=5,    # Up to 5 concurrent refreshes
)

# Start background refresh
refresh_job.start()

# Check cache status
status = cache_manager.get_cache_status()
print(f"Total projects: {status['total_projects']}")
print(f"Stale projects: {status['stale_projects']}")
print(f"Cache size: {status['cache_size_bytes']} bytes")

# Stop background refresh
refresh_job.stop()
```

### FastAPI Configuration

The cache system is automatically configured in the API startup:

```python
from skillmeat.api.server import app
from skillmeat.cache.manager import CacheManager
from skillmeat.cache.refresh import RefreshJob

@app.lifespan
async def startup_shutdown(app):
    # Startup
    settings = app.state.settings

    # Initialize cache manager from settings
    cache_manager = CacheManager(
        ttl_minutes=settings.cache_ttl_minutes,
        cache_path=settings.cache_path,
    )
    cache_manager.initialize_cache()
    app.state.cache_manager = cache_manager

    # Start refresh job
    refresh_job = RefreshJob(
        cache_manager=cache_manager,
        interval_hours=settings.cache_refresh_interval,
        max_concurrent=settings.cache_max_concurrent,
    )
    refresh_job.start()
    app.state.refresh_job = refresh_job

    yield

    # Shutdown
    refresh_job.stop()
```

## Cache Locations

### Cache Storage Paths

```
~/.skillmeat/
├── cache/                          # Cache directory
│   ├── cache.db                    # SQLite database
│   ├── cache.db-wal                # Write-ahead log
│   ├── cache.db-shm                # Shared memory file
│   └── cache-metadata.json         # Cache metadata
├── collections/
├── config.toml                     # Configuration file
└── logs/
```

### Temporary Cache Files

Some temporary files are created during operations:

```
/tmp/
└── skillmeat-cache-*/              # Temporary cache operations
    ├── refresh-*.lock              # Refresh operation locks
    └── validation-*.tmp            # Validation temporary files
```

### Accessing Cache Location

```bash
# Get cache directory path
skillmeat config get cache.cache_path

# View cache database size
du -h ~/.skillmeat/cache/cache.db

# Output: 125M    ~/.skillmeat/cache/cache.db
```

## Configuration Examples

### Development Configuration

For development environments, use shorter TTLs and more frequent refreshes:

```toml
[cache]
ttl_minutes = 30                    # Short TTL for fresh data
cache_path = "cache/"
cleanup_retention_days = 7          # Keep fewer old entries
enable_background_refresh = true
refresh_interval_hours = 1.0        # Refresh hourly
max_concurrent_refreshes = 2
max_cache_size_mb = 200             # Smaller cache
```

### Production Configuration

For production environments, use longer TTLs and less frequent refreshes:

```toml
[cache]
ttl_minutes = 1440                  # 24-hour TTL
cache_path = "cache/"
cleanup_retention_days = 60         # Keep more history
enable_background_refresh = true
refresh_interval_hours = 12.0       # Refresh twice daily
max_concurrent_refreshes = 5
max_cache_size_mb = 2000            # Larger cache

[cache.project_refresh_intervals]
"critical-project" = 6.0            # Refresh critical projects every 6 hours
"archive-project" = 168.0           # Refresh archives weekly
```

### High-Traffic Configuration

For systems with many projects/artifacts:

```toml
[cache]
ttl_minutes = 240                   # 4-hour TTL
cache_path = "cache/"
cleanup_retention_days = 30
enable_background_refresh = true
refresh_interval_hours = 3.0        # Frequent refreshes
max_concurrent_refreshes = 10       # Many concurrent operations
max_cache_size_mb = 5000            # Very large cache

[cache.project_refresh_intervals]
# Override for hot projects
"main-project" = 1.0               # Every hour
"shared-project" = 2.0             # Every 2 hours
"secondary-project" = 6.0          # Every 6 hours
```

### Low-Resource Configuration

For resource-constrained environments:

```toml
[cache]
ttl_minutes = 720                   # 12-hour TTL
cache_path = "cache/"
cleanup_retention_days = 10         # Minimal history
enable_background_refresh = false   # Disable automatic refresh
refresh_interval_hours = 24.0
max_concurrent_refreshes = 1        # Single refresh at a time
max_cache_size_mb = 100             # Minimal cache size
```

## Best Practices

### TTL Configuration

1. **Development**: Use 30-60 minute TTL for fresh data during active development
2. **Staging**: Use 2-4 hour TTL for reasonable freshness without excessive overhead
3. **Production**: Use 12-24 hour TTL to reduce database operations
4. **Adjust based on change frequency**: Lower TTL for frequently changing projects

```bash
# Quick development setup
skillmeat config set cache.ttl_minutes 30

# Standard production
skillmeat config set cache.ttl_minutes 1440

# Update TTL for a specific project later
skillmeat config set cache.project_refresh_intervals.critical-project 2.0
```

### Refresh Interval Optimization

1. **More projects** = Longer intervals to avoid overwhelming the system
2. **Fewer projects** = Shorter intervals for fresher data
3. **Network constraints** = Longer intervals to reduce API calls
4. **Real-time requirements** = Shorter intervals (minimum 1 hour recommended)

```bash
# Frequent refresh for active development
skillmeat config set cache.refresh_interval_hours 1.0

# Balanced refresh for standard use
skillmeat config set cache.refresh_interval_hours 6.0

# Minimal refresh for resource-constrained environments
skillmeat config set cache.refresh_interval_hours 24.0
```

### Size Management

1. **Monitor cache size** regularly with `skillmeat cache status`
2. **Set appropriate max size** based on available disk space
3. **Enable cleanup** with reasonable retention periods
4. **Manual cleanup** when cache becomes too large

```bash
# Check cache status
skillmeat cache status

# Manual cleanup of old entries
skillmeat cache cleanup --older-than-days 30

# Prune to specific size
skillmeat cache cleanup --max-size-mb 500
```

### Performance Tuning

1. **Concurrent refreshes**: Increase for systems with many projects
2. **Background refresh**: Disable if causing performance issues
3. **Cache path**: Use fast SSD storage for better performance
4. **Monitoring**: Track cache hit rates to optimize TTL

```bash
# View cache statistics
skillmeat cache stats

# Output:
# Cache Statistics
# ├─ Total Projects:      45
# ├─ Total Artifacts:     234
# ├─ Cache Size:          156 MB
# ├─ Hit Rate:            87.3%
# └─ Stale Entries:       3
```

### Troubleshooting Configuration

If experiencing issues:

1. **Cache not updating**: Check `enable_background_refresh` and `refresh_interval_hours`
2. **Cache too large**: Reduce `max_cache_size_mb` or `cleanup_retention_days`
3. **Stale data**: Reduce `ttl_minutes` or manually invalidate
4. **Performance issues**: Increase `refresh_interval_hours` or disable background refresh

```bash
# Clear entire cache if needed
skillmeat cache clear

# Invalidate specific project
skillmeat cache invalidate --project my-project

# Force full refresh
skillmeat cache refresh --force
```

## See Also

- [API Reference](api-reference.md) - Cache API endpoints
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues and solutions
- [Architecture Decision Record](architecture-decision-record.md) - Design decisions
