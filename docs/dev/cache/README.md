---
title: "Cache Documentation"
description: "Comprehensive documentation for the SkillMeat persistent cache system"
audience: [developers, users, maintainers]
tags: [cache, documentation, reference, guides]
created: 2025-12-01
updated: 2025-12-01
category: "reference"
status: "published"
---

# Cache Documentation

Welcome to the SkillMeat cache system documentation. This directory contains comprehensive guides for understanding, configuring, and managing the cache system.

## Quick Links

### For Users

- **[Configuration Guide](configuration-guide.md)** - Configure cache behavior, TTL, refresh intervals, and size limits
- **[Troubleshooting Guide](troubleshooting-guide.md)** - Solve common issues and optimize performance

### For Developers

- **[API Reference](api-reference.md)** - Complete REST API documentation with examples
- **[Architecture Decision Record](architecture-decision-record.md)** - Design decisions and trade-offs

## Overview

The SkillMeat cache system provides:

- **Persistent Storage**: SQLite database for reliable metadata storage
- **Fast Queries**: Quick lookups and searches across cached data
- **Version Tracking**: Monitor deployed vs. upstream versions
- **Background Refresh**: Automatic cache updates without blocking operations
- **Flexible Management**: Manual invalidation and refresh controls

## Getting Started

### Basic Usage

```bash
# Check cache status
skillmeat cache status

# View cache statistics
skillmeat cache stats

# Force refresh all projects
skillmeat cache refresh --force

# Clean up old entries
skillmeat cache cleanup

# View cache configuration
skillmeat config list --filter cache
```

### API Access

```bash
# Get cache status via API
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/status

# List cached artifacts
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/artifacts

# Search cached artifacts
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=docker"
```

## Documentation Structure

### [Configuration Guide](configuration-guide.md)

How to configure the cache system:

- Core configuration parameters
- Environment variables
- CLI configuration commands
- Programmatic configuration (Python API)
- Cache storage locations
- Configuration examples for different scenarios
- Best practices and optimization tips

**Example:**
```bash
# Set cache TTL to 4 hours
skillmeat config set cache.ttl_minutes 240

# Enable background refresh
skillmeat config set cache.enable_background_refresh true
```

### [API Reference](api-reference.md)

Complete REST API documentation:

- Authentication (API keys)
- Cache status and statistics endpoints
- Cache management (refresh, invalidate)
- Project listing and filtering
- Artifact listing and outdated detection
- Search with relevance scoring
- Marketplace cache access
- Error responses and rate limiting

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/cache/refresh \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### [Troubleshooting Guide](troubleshooting-guide.md)

Solutions for common cache issues:

- Diagnostic commands
- Cache not updating (and solutions)
- Cache too large (cleanup strategies)
- Stale data problems
- Cache corruption recovery
- Refresh job failures
- Performance optimization
- Debug logging
- Health monitoring

**Example:**
```bash
# Diagnose cache issues
skillmeat cache check

# Rebuild corrupted database
skillmeat cache rebuild

# Monitor cache health
skillmeat logs cache --follow
```

### [Architecture Decision Record](architecture-decision-record.md)

Design decisions and technical details:

- Why SQLite was chosen (vs. PostgreSQL, Redis, etc.)
- TTL-based invalidation strategy
- Thread safety with RLock
- Background refresh mechanism
- RESTful API design
- Performance optimization strategies
- Future enhancement plans

## Key Concepts

### TTL (Time-To-Live)

Cache entries expire after a configurable duration (default: 6 hours). After expiration, the cache is refreshed on next access.

```bash
# Check current TTL
skillmeat config get cache.ttl_minutes

# Set to 4 hours
skillmeat config set cache.ttl_minutes 240
```

### Background Refresh

Automatic periodic refresh of stale cache entries. Runs in background without blocking operations.

```bash
# Check refresh status
skillmeat cache refresh-status

# Disable if needed
skillmeat config set cache.enable_background_refresh false
```

### Cache Invalidation

Mark cache entries as stale to force refresh on next access.

```bash
# Invalidate entire cache
skillmeat cache invalidate

# Invalidate specific project
skillmeat cache invalidate --project proj-123
```

### Cache Cleanup

Remove old entries and optimize storage based on retention policy.

```bash
# Cleanup old entries (default: older than 30 days)
skillmeat cache cleanup

# Cleanup entries older than 60 days
skillmeat cache cleanup --older-than-days 60
```

## Common Tasks

### Monitor Cache Health

```bash
# Get cache status
skillmeat cache status

# View detailed statistics
skillmeat cache stats

# Check database integrity
skillmeat cache check
```

### Configure for Your Use Case

**Development (frequent updates, small cache):**
```bash
skillmeat config set cache.ttl_minutes 30
skillmeat config set cache.enable_background_refresh true
skillmeat config set cache.refresh_interval_hours 1.0
skillmeat config set cache.max_cache_size_mb 200
```

**Production (stable data, large cache):**
```bash
skillmeat config set cache.ttl_minutes 1440  # 24 hours
skillmeat config set cache.enable_background_refresh true
skillmeat config set cache.refresh_interval_hours 12.0
skillmeat config set cache.max_cache_size_mb 2000
```

### Find Outdated Artifacts

```bash
# Via CLI
skillmeat cache list-stale-artifacts

# Via API
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/stale-artifacts
```

### Search Cached Data

```bash
# Via CLI
skillmeat cache search "docker"

# Via API
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=docker&type=skill"
```

## Performance Guidelines

| Metric | Target | Optimization |
|--------|--------|-------------|
| Cache hit rate | > 85% | Increase TTL, reduce frequency of changes |
| Query latency | < 100ms | Use indexes, limit result size |
| Refresh time | < 5 min | Reduce projects, increase max_concurrent |
| Cache size | < 500 MB | Enable cleanup, reduce retention days |

## Troubleshooting Quick Start

| Problem | Check | Solution |
|---------|-------|----------|
| Cache not updating | `skillmeat cache refresh-status` | Enable refresh or force refresh |
| Cache too large | `du -sh ~/.skillmeat/cache/` | Run cleanup command |
| Stale data shown | Last refresh timestamp | Reduce TTL or force refresh |
| Slow queries | `skillmeat cache stats` | Add indexes or reduce data size |
| Database errors | `skillmeat cache check` | Run rebuild or clear cache |

## See Also

- **Project Documentation**: See main [README.md](/docs) for other guides
- **API Documentation**: Full OpenAPI docs at `/docs` when API is running
- **CLI Reference**: Run `skillmeat --help` for command help

## File Structure

```
docs/dev/cache/
├── README.md                           # This file
├── configuration-guide.md              # Configuration reference
├── api-reference.md                    # REST API documentation
├── troubleshooting-guide.md            # Common issues and solutions
└── architecture-decision-record.md     # Design decisions and trade-offs
```

## Contributing

To improve this documentation:

1. Make changes locally
2. Test with actual examples
3. Submit pull request with updates
4. Update cross-references if needed

All documentation should:
- Be clear and concise
- Include working examples
- Reference other relevant docs
- Follow Markdown formatting standards
