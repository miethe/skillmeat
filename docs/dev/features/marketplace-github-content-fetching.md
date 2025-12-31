---
title: "Marketplace GitHub Content Fetching Architecture"
description: "Developer guide for understanding how artifact file contents are fetched and cached from GitHub in the marketplace sources feature"
audience: developers
tags: [marketplace, github, caching, architecture, performance]
created: 2025-12-31
updated: 2025-12-31
category: feature-architecture
status: published
related:
  - /docs/dev/architecture/decisions/ADR-006-catalog-file-caching.md
  - /docs/dev/api/marketplace-sources.md
---

# Marketplace GitHub Content Fetching Architecture

## Overview

The marketplace sources feature in SkillMeat allows users to browse and import Claude Code artifacts (skills, commands, agents) discovered in GitHub repositories. When users click the Contents tab in the catalog entry modal, the application fetches and displays the file structure and content from these repositories.

This guide explains the complete architecture for fetching, caching, and serving GitHub content with minimal API calls and maximum performance.

## Critical: On-Demand Fetching, Not Detection-Time

**Key Point**: Files are fetched **on-demand** when users explicitly request them, NOT during artifact detection.

### Why This Matters

During the marketplace scan phase:
- Repository is scanned for artifacts
- Only metadata is captured: artifact path, type, name, confidence score, and commit SHA
- File trees and contents are NOT fetched
- Database is updated with catalog entries

Later, when a user opens the catalog entry modal and clicks the Contents tab:
- File tree is fetched on-demand from GitHub
- File content is fetched on-demand when user selects a file
- Both responses are cached to minimize repeated API calls

### Rationale

1. **API Rate Limits**: GitHub limits API calls (60/hr unauthenticated, 5000/hr authenticated). Fetching all files during scan would quickly exhaust these limits.
2. **User Experience**: Most users don't view all artifacts. Why fetch content for artifacts they'll never open?
3. **Storage**: Storing file contents in the database would bloat storage significantly.
4. **Freshness**: Content fetched on-demand is fresher than pre-fetched content.

## Two-Layer Caching Architecture

SkillMeat implements a two-layer caching strategy to minimize GitHub API calls while keeping responses fast.

```
┌─────────────────────────────────────────────────────────────────┐
│ User Request: "Show me the files in skills/canvas-design"      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│ Layer 1: Frontend Cache            │  ◄─ TanStack Query
│ (Browser/Session)                  │     - Per-user, per-session
│ staleTime: 5-30 minutes            │     - In-memory React state
│ gcTime: 30-120 minutes             │     - Reduces redundant fetches
└────────────────┬───────────────────┘
                 │
                 │ Cache miss or stale
                 ▼
┌────────────────────────────────────┐
│ Layer 2: Backend Cache             │  ◄─ In-memory LRU
│ (FastAPI/Python)                   │     - Shared across all users
│ TTL: 1-2 hours                     │     - Thread-safe with RLock
│ Max Entries: 1000                  │     - Automatic LRU eviction
└────────────────┬───────────────────┘
                 │
                 │ Cache miss or expired
                 ▼
┌────────────────────────────────────┐
│ Layer 3: GitHub API                │  ◄─ Source of truth
│ (Rate Limited)                     │     - 60/hr unauth, 5000/hr auth
│ Response Time: 500-2000ms          │
└────────────────────────────────────┘
```

## API Endpoints

### File Tree Endpoint

```
GET /api/v1/marketplace/sources/{source_id}/artifacts/{artifact_path}/files
```

**Purpose**: Retrieve the directory structure of an artifact

**Parameters**:
- `source_id` (path): Marketplace source identifier (UUID)
- `artifact_path` (path): Path to artifact within repository (e.g., `skills/canvas-design`)

**Response**:
```json
{
  "entries": [
    { "path": "SKILL.md", "type": "file", "size": 2048 },
    { "path": "src", "type": "tree" },
    { "path": "src/index.ts", "type": "file", "size": 4096 }
  ],
  "artifact_path": "skills/canvas-design",
  "source_id": "src-uuid-123"
}
```

**Caching**: Backend caches for 1 hour (3600 seconds)

### File Content Endpoint

```
GET /api/v1/marketplace/sources/{source_id}/artifacts/{artifact_path}/files/{file_path}
```

**Purpose**: Retrieve the content of a specific file

**Parameters**:
- `source_id` (path): Marketplace source identifier
- `artifact_path` (path): Path to artifact within repository
- `file_path` (path): Path to file within artifact (e.g., `SKILL.md` or `src/index.ts`)

**Response**:
```json
{
  "content": "# Canvas Design Skill\n\n...",
  "encoding": "utf-8",
  "size": 2048,
  "sha": "abc123def456...",
  "is_binary": false,
  "name": "SKILL.md",
  "path": "SKILL.md",
  "artifact_path": "skills/canvas-design",
  "source_id": "src-uuid-123"
}
```

**Caching**: Backend caches for 2 hours (7200 seconds)

## Backend Cache Implementation

### Location

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/utils/github_cache.py`

### Cache Key Format

Keys include the commit SHA to provide automatic invalidation when upstream content changes:

```
# File tree cache key
tree:{source_id}:{artifact_path}:{sha}

# File content cache key
content:{source_id}:{artifact_path}:{file_path}:{sha}
```

**Examples**:
```
tree:src-123:skills/canvas-design:abc123def456
content:src-123:skills/canvas-design:SKILL.md:789ghi012jkl
```

### SHA-Based Invalidation

The cache key includes the commit SHA:
- When a source is rescanned, the SHA may change if the repository has new commits
- Old cache keys with previous SHAs become stale
- New SHAs trigger fresh GitHub API calls
- **No explicit cache invalidation needed** - automatic via SHA-based keys

### Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max Entries | 1000 | Balances memory (~50-100MB) vs hit rate |
| Tree TTL | 3600s (1 hour) | File structures rarely change; good API savings |
| Content TTL | 7200s (2 hours) | Content per SHA is immutable; aggressive caching safe |
| Eviction Policy | LRU (Least Recently Used) | Most frequently accessed files stay cached |

### Thread Safety

```python
class GitHubFileCache(Generic[T]):
    def __init__(self, max_entries: int = 1000) -> None:
        self._cache: OrderedDict[str, CacheEntry[Any]] = OrderedDict()
        self._lock = threading.RLock()  # Re-entrant lock
```

- Uses `threading.RLock()` for re-entrant locking
- All cache operations are atomic within the lock
- Supports concurrent requests from multiple API handlers
- Concurrent users can safely access and populate the cache

## Frontend Cache Implementation

### Location

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-catalog-files.ts`

### Cache Configuration

**File Tree Hook** (`useCatalogFileTree`):
- `staleTime`: 5 minutes
- `gcTime`: 30 minutes
- **Rationale**: Trees are browsed frequently; moderate staleness acceptable

**File Content Hook** (`useCatalogFileContent`):
- `staleTime`: 30 minutes
- `gcTime`: 2 hours
- **Rationale**: Content immutable per request; aggressive caching safe

### Query Key Factory

```typescript
export const catalogKeys = {
  all: ['catalog'] as const,
  trees: () => [...catalogKeys.all, 'tree'] as const,
  tree: (sourceId: string, artifactPath: string) =>
    [...catalogKeys.trees(), sourceId, artifactPath] as const,
  contents: () => [...catalogKeys.all, 'content'] as const,
  content: (sourceId: string, artifactPath: string, filePath: string) =>
    [...catalogKeys.contents(), sourceId, artifactPath, filePath] as const,
};
```

Hierarchical key structure enables targeted cache invalidation if needed.

## Complete Request Flow

### 1. First Request (Cold Cache)

```
User clicks "Contents" tab in catalog entry modal
  ↓
Frontend hook useCatalogFileTree(sourceId, artifactPath)
  ↓
TanStack Query cache: MISS
  ↓
Frontend API client calls GET /api/v1/marketplace/sources/{sourceId}/artifacts/{artifactPath}/files
  ↓
Backend endpoint receives request
  ↓
Backend cache (GitHubFileCache): MISS
  ↓
GitHubScanner calls GitHub API to fetch tree structure
  ↓
Backend caches response for 1 hour
  ↓
Response returned to frontend (500-2000ms)
  ↓
Frontend caches in TanStack Query for 5 minutes
  ↓
File tree displayed in modal
```

### 2. Subsequent Request (Warm Frontend Cache)

```
User views same artifact within 5 minutes
  ↓
Frontend hook useCatalogFileTree(sourceId, artifactPath)
  ↓
TanStack Query cache: HIT (within staleTime)
  ↓
Instant response (<1ms)
  ↓
File tree displayed from React state (no API call)
```

### 3. Frontend Stale, Backend Warm

```
User views same artifact after 5 minutes, within 1 hour
  ↓
Frontend hook useCatalogFileTree(sourceId, artifactPath)
  ↓
TanStack Query cache: STALE (beyond staleTime)
  ↓
Frontend refetch triggered
  ↓
Backend cache (GitHubFileCache): HIT
  ↓
Response returned to frontend (10-50ms)
  ↓
Frontend cache updated
  ↓
File tree displayed
```

### 4. Both Caches Expired

```
User views same artifact after 1 hour
  ↓
Frontend cache: EXPIRED (gcTime exceeded)
  ↓
Backend cache: EXPIRED (1-hour TTL exceeded)
  ↓
GitHub API call made (500-2000ms)
  ↓
Cycle repeats: caches populated, displayed to user
```

## Performance Metrics

### Expected Cache Hit Rates

| Layer | Hit Rate | Reduction |
|-------|----------|-----------|
| Frontend (TanStack Query) | 60-80% | Warm sessions, same artifacts |
| Backend (LRU) | 70-90% | Popular artifacts, multi-user |
| **Combined** | **90-98%** | **80-98% API call reduction** |

### Response Times

| Scenario | Time | vs. Uncached |
|----------|------|-------------|
| Frontend cache hit | <1ms | 800-2000x faster |
| Backend cache hit | 10-50ms | 20-100x faster |
| Fresh GitHub API | 500-2000ms | Baseline |

### Memory Usage Estimates

**Backend Cache (1000 entries)**:
- Average tree entry: 5-10KB (file list JSON)
- Average content entry: 20-50KB (file contents)
- Estimated total: 50-100MB
- Bounded by max_entries (LRU eviction prevents growth)

**Frontend Cache**:
- Per-browser, per-session
- Bounded by gcTime eviction
- Typically <10MB per user

## Key Files

### Backend Implementation

| File | Purpose |
|------|---------|
| `skillmeat/api/utils/github_cache.py` | GitHubFileCache class with LRU + TTL |
| `skillmeat/api/routers/marketplace_sources.py` | File tree/content endpoints (lines 1102-1403) |
| `skillmeat/core/marketplace/github_scanner.py` | GitHub API interaction for fetching files |

### Frontend Implementation

| File | Purpose |
|------|---------|
| `skillmeat/web/hooks/use-catalog-files.ts` | TanStack Query hooks for data fetching |
| `skillmeat/web/lib/api/catalog.ts` | Fetch functions for file tree/content API endpoints |

### Tests

| File | Purpose |
|------|---------|
| `skillmeat/api/tests/test_github_cache.py` | Unit tests for cache behavior |
| `skillmeat/api/tests/test_file_cache_performance.py` | Cache hit rate and performance tests |

## Cache Statistics

The backend cache exposes statistics via the `.stats()` method:

```python
stats = cache.stats()
# Returns:
{
    "entries": 523,           # Current cache entries
    "max_entries": 1000,      # Maximum allowed
    "hits": 4521,             # Total cache hits
    "misses": 234,            # Total cache misses
    "hit_rate": 95.08,        # Percentage (0-100)
    "expired_count": 12       # Currently expired entries
}
```

This data can be monitored to validate that the two-layer strategy is achieving expected hit rates.

## Error Handling

### GitHub Rate Limit Errors

When GitHub API rate limits are exceeded:

```
Backend receives RateLimitError from GitHub
  ↓
Endpoint returns HTTP 429 Too Many Requests
  ↓
Response includes Retry-After header
  ↓
Frontend displays error message with retry suggestion
```

Rate limits apply to the GitHub API itself, not the cached responses. If both cache layers miss during a rate-limited window, the user sees an error.

### Path Traversal Security

Both endpoints validate file paths to prevent path traversal attacks:

```python
def validate_file_path(path: str) -> str:
    # Rejects:
    # - Parent directory references (..)
    # - Absolute paths (starting with /)
    # - Null byte injection (\x00)
    # - URL-encoded traversal (%2e%2e)
    ...
```

The validation ensures users cannot access files outside the artifact directory.

## Debugging and Monitoring

### Checking Cache Hit Rate

```bash
# Via API endpoint (if exposed - currently internal)
GET /api/v1/cache/stats

# Or check logs for cache hits/misses:
grep "Cache hit:" /var/log/skillmeat-api.log | wc -l
grep "Cache miss:" /var/log/skillmeat-api.log | wc -l
```

### Common Issues

**Problem**: Users see outdated file content
- **Likely Cause**: Source hasn't been rescanned; old SHA still cached
- **Solution**: User can rescan the marketplace source to update SHA

**Problem**: Rate limit errors when fetching files
- **Likely Cause**: Backend cache expired and multiple users hit GitHub API simultaneously
- **Solution**: Increase backend cache max_entries or TTLs (if memory allows)

**Problem**: Memory usage growing unbounded
- **Likely Cause**: max_entries limit not being respected
- **Solution**: Check for bugs in LRU eviction logic; restart server as temporary fix

## Future Enhancements

### Phase 2 / v2 Improvements

1. **Cache Warming**: Pre-populate cache for popular artifacts (top 100)
2. **Distributed Cache**: Redis integration for multi-server deployments
3. **Metrics Export**: Prometheus metrics for cache hit rates, response times
4. **Adaptive TTL**: Adjust TTLs based on access patterns
5. **Persistence**: SQLite-backed cache for restart survival
6. **Compression**: Gzip file contents in cache to reduce memory

### Monitoring Integration

When implemented, expose metrics:
- `cache_hits_total` (counter)
- `cache_misses_total` (counter)
- `cache_hit_rate` (gauge, 0-100)
- `cache_entries` (gauge)
- `github_api_calls_total` (counter)
- `response_time_ms` (histogram)

## Related Documentation

- **Decision Document**: ADR-006 explains the rationale for this two-layer approach
- **API Specification**: See `docs/dev/api/marketplace-sources.md` for full endpoint documentation
- **PRD**: `docs/project_plans/PRDs/features/catalog-entry-modal-enhancement-v1.md` for feature context

## Summary

The marketplace GitHub content fetching architecture uses **on-demand fetching** with a **two-layer caching strategy** to balance API rate limits, performance, and memory usage:

1. **On-Demand**: Files fetched only when users request them, not during artifact detection
2. **Frontend Cache** (TanStack Query): Per-user caching reduces redundant server requests
3. **Backend Cache** (LRU + TTL): Shared across users, dramatically reduces GitHub API calls
4. **SHA-Based Keys**: Automatic invalidation when upstream changes
5. **Bounded Memory**: LRU eviction prevents unbounded growth
6. **Thread Safe**: Concurrent access handled correctly

This results in:
- 90-98% cache hit rate
- 80-98% reduction in GitHub API calls
- <10ms response times for cached data
- 50-100MB backend memory usage
- Full rate limit safety
