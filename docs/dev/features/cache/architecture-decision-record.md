---
title: "Cache Architecture Decision Record"
description: "Design decisions, trade-offs, and architectural overview of the SkillMeat cache system"
audience: [developers, architects, maintainers]
tags: [cache, architecture, design, decisions, trade-offs]
created: 2025-12-01
updated: 2025-12-01
category: "architecture"
status: "published"
related: ["configuration-guide.md", "api-reference.md", "troubleshooting-guide.md"]
---

# Cache Architecture Decision Record

This document explains the design decisions, implementation choices, and trade-offs made in the SkillMeat cache system.

## Table of Contents

- [Overview](#overview)
- [Storage Technology](#storage-technology)
- [Invalidation Strategy](#invalidation-strategy)
- [Thread Safety](#thread-safety)
- [Refresh Mechanism](#refresh-mechanism)
- [API Design](#api-design)
- [Performance Considerations](#performance-considerations)
- [Future Enhancements](#future-enhancements)

## Overview

The SkillMeat cache system provides persistent, queryable storage of project metadata and artifact information. It enables:

1. **Fast metadata lookups** without filesystem scanning
2. **Version tracking** for update detection
3. **Search capabilities** across all cached data
4. **Background refresh** without blocking user operations
5. **Flexible invalidation** for cache management

## Storage Technology

### Decision: Use SQLite

**Selected Option:** SQLite database with file-based storage

**Alternatives Considered:**

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **SQLite** | Fast, no dependencies, ACID, easy queries | Single-threaded writer, file-based | ✓ Selected |
| PostgreSQL | Powerful, concurrent, production-grade | Requires external service, complexity | Rejected |
| Redis | Fast, simple, in-memory | Volatile, complexity, memory-bound | Rejected |
| In-memory dict | Simplest, fastest reads | Non-persistent, memory limits | Rejected |
| JSON files | Human-readable, simple | No queries, slow search, merge conflicts | Rejected |

### Why SQLite?

1. **Zero Dependencies**: Works out-of-box with Python standard library
2. **ACID Guarantees**: Reliable transaction handling
3. **Query Capability**: Full SQL for flexible searches and filtering
4. **Persistence**: Survives process restarts
5. **File-Based**: Can be backed up and versioned like code
6. **Sufficient Performance**: Handles SkillMeat's data volume efficiently
7. **Standard Tools**: Can inspect with `sqlite3` CLI

### Limitations and Mitigations

**Limitation 1: Single Writer**
- SQLite allows only one writer at a time
- Multiple readers can access concurrently

Mitigation:
- Use write locks (RLock) in Python
- Batch writes where possible
- Queue refresh operations

**Limitation 2: No Remote Access**
- SQLite is file-based, not network-accessible

Mitigation:
- API wraps cache access
- Future: Consider replication for distributed systems

**Limitation 3: File Size**
- Not suitable for multi-terabyte datasets

Mitigation:
- Cleanup policy removes old entries
- Max cache size limit
- Acceptable for SkillMeat's typical data volume

## Invalidation Strategy

### Decision: TTL-Based with Manual Invalidation

**Selected Approach:** Hybrid TTL + manual invalidation

**Strategy Flow:**

```
User Action
    ↓
Check Cache Age
    ├─ Still Fresh (< TTL)
    │  └─ Return Cached Data
    └─ Stale (≥ TTL)
       └─ Refresh from Source
           ├─ If Changes Found
           │  └─ Update Cache
           └─ If No Changes
              └─ Update Timestamp
```

### TTL Mechanism

**Time-To-Live Implementation:**

```python
entry = {
    "data": {...},
    "cached_at": 2025-12-01T12:00:00Z,
    "ttl_minutes": 360,
    "expires_at": 2025-12-01T18:00:00Z  # Calculated
}

# On access:
if current_time >= entry.expires_at:
    # Entry is stale, refresh needed
    refresh(entry)
```

**TTL Configuration:**

- Default: 360 minutes (6 hours)
- Configurable per system and per-project
- Reduces refresh frequency, minimizing API calls
- Balances freshness vs. overhead

### Manual Invalidation

**Use Cases:**

1. **Deployment**: After updating artifacts, invalidate immediately
2. **Testing**: Force refresh without waiting for TTL
3. **Error Recovery**: Invalidate corrupted entries
4. **Urgent Updates**: Bypass TTL for critical changes

**API:**

```bash
# Invalidate entire cache
curl -X POST .../cache/invalidate -d '{"project_id": null}'

# Invalidate specific project
curl -X POST .../cache/invalidate -d '{"project_id": "proj-123"}'
```

### Alternatives Rejected

**LRU (Least Recently Used)**
- Problem: Predicts what's needed based on access patterns
- Rejected: SkillMeat needs deterministic, time-based freshness

**Event-Based Invalidation**
- Problem: Requires webhooks from all sources
- Rejected: GitHub doesn't provide artifact change webhooks

**Zero-TTL with On-Demand Refresh**
- Problem: Every access triggers refresh (slow)
- Rejected: Defeats purpose of caching

## Thread Safety

### Decision: RLock-Based Synchronization

**Selected Approach:** `threading.RLock` for thread-safe cache access

**Architecture:**

```python
class CacheManager:
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock
        self._cache = {}

    def get(self, key):
        with self._lock:
            # Thread-safe read
            if key in self._cache:
                return self._cache[key]
            return None

    def set(self, key, value):
        with self._lock:
            # Thread-safe write
            self._cache[key] = value

    def invalidate(self, key):
        with self._lock:
            # Thread-safe delete
            self._cache.pop(key, None)
```

### Why RLock (Reentrant Lock)?

1. **Reentrant**: Same thread can acquire multiple times
2. **Safe**: Prevents deadlocks in nested operations
3. **Simple**: Clear, readable synchronization pattern
4. **Sufficient**: Python's GIL handles most concurrency

### Lock Duration

**Kept Minimal:**

```python
# Good: Lock only for actual data access
with self._lock:
    data = self._cache[key]  # Fast operation
# Long operations happen outside lock
process_data(data)  # Can be slow, no lock held
```

**Avoid:**

```python
# Bad: Lock held during slow operation
with self._lock:
    data = self._cache[key]
    result = slow_api_call(data)  # Holding lock!
    self._cache[key] = result
```

### Database Locking

**SQLite Locking Behavior:**

```
Read Operations:  Multiple concurrent readers (SHARED lock)
Write Operations: Exclusive lock (EXCLUSIVE)
```

**Implications:**

- Multiple threads can read simultaneously
- Only one writer at a time
- Readers block during writes (brief)

## Refresh Mechanism

### Decision: Background Refresh with Scheduling

**Selected Approach:** Async refresh scheduler with configurable intervals

**Architecture:**

```
RefreshJob (Background Thread)
    ├─ Check if refresh needed
    ├─ Determine stale projects
    ├─ Refresh in parallel (up to max_concurrent)
    ├─ Update cache with results
    └─ Reschedule for next interval
```

### Refresh Process

**Step 1: Identify Stale Projects**

```python
stale_projects = [
    p for p in projects
    if current_time - p.last_refreshed >= ttl
]
```

**Step 2: Refresh in Parallel**

```python
# Concurrent refresh (controlled)
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(refresh_project, proj)
        for proj in stale_projects
    ]
    results = [f.result(timeout=300) for f in futures]
```

**Step 3: Update Cache**

```python
for result in results:
    if result.success:
        cache.update_project(result.project)
    else:
        log.error(f"Refresh failed: {result.error}")
```

**Step 4: Reschedule**

```python
next_run = now + timedelta(hours=refresh_interval)
scheduler.schedule(next_run, refresh_all)
```

### Configuration Options

| Setting | Default | Purpose |
|---------|---------|---------|
| `refresh_interval_hours` | 6.0 | How often to refresh |
| `max_concurrent_refreshes` | 3 | Parallel refresh operations |
| `refresh_timeout_seconds` | 300 | Max time per project |
| `enable_background_refresh` | true | Enable/disable scheduler |

### Alternatives Considered

**On-Demand Refresh Only**
- Problem: User waits for refresh
- Rejected: Poor user experience

**Aggressive Polling (every few seconds)**
- Problem: High CPU and network overhead
- Rejected: Unnecessary traffic

**Event-Driven Webhooks**
- Problem: Requires external service setup
- Rejected: Too complex for current scope

## API Design

### Decision: RESTful JSON API

**Selected Approach:** FastAPI with Pydantic models

**Design Principles:**

1. **Consistent Structure**: All responses follow standard format
2. **Predictable Endpoints**: Standard CRUD patterns
3. **Rich Filtering**: Query parameters for flexible searches
4. **Pagination**: Support large result sets
5. **Status Codes**: Proper HTTP status for all cases

### Endpoint Organization

```
/api/v1/cache/
├── status           GET    Cache statistics
├── refresh          POST   Trigger refresh
├── invalidate       POST   Mark stale
├── projects         GET    List projects
├── artifacts        GET    List artifacts
├── stale-artifacts  GET    Find outdated
├── search           GET    Search artifacts
└── marketplace      GET    Marketplace cache
```

### Request/Response Format

**Consistent request pattern:**

```json
{
  "project_id": "optional-filter",
  "force": false,
  "limit": 100,
  "skip": 0
}
```

**Consistent response pattern:**

```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "message": "Human-readable status"
}
```

### Error Handling

**Standardized error responses:**

```json
{
  "detail": "Project not found",
  "status_code": 404,
  "timestamp": "2025-12-01T12:00:00Z"
}
```

## Performance Considerations

### Optimization Decisions

**1. Indexing Strategy**

```sql
-- Indexes on frequently queried fields
CREATE INDEX idx_project_id ON artifacts(project_id);
CREATE INDEX idx_artifact_type ON artifacts(type);
CREATE INDEX idx_last_refresh ON projects(last_refresh);
```

**Benefit:** Fast filtering and sorting (O(log n) instead of O(n))

**2. Query Optimization**

```python
# Bad: Fetch all, filter in Python
artifacts = db.query_all()
outdated = [a for a in artifacts if a.is_outdated]

# Good: Filter in database
outdated = db.query(
    "SELECT * FROM artifacts WHERE is_outdated = 1"
)
```

**Benefit:** Reduced memory usage, faster queries

**3. Pagination**

```python
# Support offset/limit pagination
artifacts = db.query(
    "SELECT * FROM artifacts LIMIT ? OFFSET ?",
    (limit, skip)
)
```

**Benefit:** Handle large datasets efficiently

**4. Connection Pooling**

SQLite doesn't support connection pooling, but Python's `sqlite3` module handles:
- Statement caching
- Connection reuse
- Query optimization

**5. Cache Hit Optimization**

```python
# In-memory cache of hot data
hot_cache = {}

def get_artifact(id):
    if id in hot_cache:
        return hot_cache[id]  # Fast
    db_result = db.query(id)  # Slower
    hot_cache[id] = db_result
    return db_result
```

### Memory Management

**Strategies:**

1. **Lazy Loading**: Load data only when accessed
2. **Cleanup**: Remove expired entries regularly
3. **Size Limits**: Enforce maximum cache size
4. **Streaming Responses**: Don't load entire result set

### Query Performance

**Typical Query Times (with 10k artifacts):**

| Operation | Time | Notes |
|-----------|------|-------|
| Get by ID | 5-10ms | Indexed |
| Filter by type | 20-50ms | Indexed |
| Search by name | 50-100ms | Full-text search |
| List all | 200-500ms | Depends on pagination |
| Refresh project | 500-2000ms | Network-bound |

## Future Enhancements

### Potential Improvements

**1. Full-Text Search**

```sql
-- SQLite FTS (Full-Text Search)
CREATE VIRTUAL TABLE artifacts_fts USING fts5(
    name, description, tags
);

-- Fast search
SELECT * FROM artifacts_fts WHERE artifacts_fts MATCH 'canvas'
```

**Timeline:** Phase 2

**2. Distributed Caching**

- Multi-instance cache replication
- Redis as backing store
- Requires significant refactoring

**Timeline:** Phase 3 (if needed)

**3. Compression**

- Compress old cache entries
- Reduce storage footprint
- Trade CPU for storage

**Timeline:** Phase 2

**4. Query Caching**

- Cache query results
- Invalidate on refresh
- Reduce database load

**Timeline:** Phase 2

**5. Analytics**

- Track cache hit/miss rates
- Monitor performance
- Optimize TTL based on usage

**Timeline:** Phase 2

**6. Backup/Restore**

- Automated cache snapshots
- Point-in-time recovery
- Disaster recovery

**Timeline:** Phase 3

### Monitoring Enhancements

**Metrics to Track:**

- Cache hit rate (target: > 85%)
- Query latency p50/p95/p99
- Refresh duration and success rate
- Stale entry percentage
- Database size growth rate

### Migration Path

If requirements exceed SQLite capabilities:

1. **Short term** (current): SQLite works well
2. **Medium term** (phase 2): Optimize indexes, add FTS
3. **Long term** (phase 3+): Consider PostgreSQL or distributed cache

**Migration considerations:**

- No application code changes (abstract behind manager)
- Database selection is internal implementation detail
- API remains stable across versions

## Design Principles Summary

1. **Simplicity First**: Use simplest solution that works
2. **Performance**: Optimize for common cases
3. **Reliability**: ACID guarantees, fail safely
4. **Flexibility**: Configurable for different use cases
5. **Observability**: Clear logging and metrics
6. **Maintainability**: Clear code, documented decisions
7. **Extensibility**: Easy to add features without refactor

## See Also

- [Configuration Guide](configuration-guide.md) - How to configure
- [API Reference](api-reference.md) - API endpoints
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues
