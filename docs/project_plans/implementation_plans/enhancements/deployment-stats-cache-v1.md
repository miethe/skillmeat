---
title: "Implementation Plan: Deployment Statistics In-Memory Cache"
description: "Cache deployment statistics to eliminate repeated filesystem scanning when viewing Sync Status tab"
audience: [ai-agents, developers]
tags: [implementation, cache, performance, backend, sync]
created: 2026-02-04
updated: 2026-02-04
category: "implementation"
status: completed
prd_reference: /docs/project_plans/PRDs/refactors/sync-diff-modal-standardization-v1.md
related:
  - skillmeat/cache/collection_cache.py
  - skillmeat/api/routers/artifacts.py (lines 248-326)
  - skillmeat/api/routers/projects.py (lines 142-207)
---

# Implementation Plan: Deployment Statistics In-Memory Cache

**Complexity:** Small (S) | **Track:** Fast Track

**Estimated Effort:** 3-4 hours | **Story Points:** 3

**Scope:** Backend-only performance optimization for deployment statistics endpoint

---

## Executive Summary

When viewing the Sync Status tab in the `/manage` ArtifactOperationsModal, the `ProjectSelectorForDiff` component shows a slow "Loading projects..." spinner. The root cause is `build_deployment_statistics()` performing a recursive filesystem scan across multiple home directories on every request, with zero caching. This plan adds a two-level in-memory TTL cache following the existing `CollectionCountCache` pattern to make successive loads near-instant while keeping data fresh with a 2-minute TTL and event-driven invalidation.

**Key Outcomes:**
- Successive artifact views load in ~0ms (vs ~2-5s filesystem scan)
- No schema changes, no migrations, no frontend changes
- Integrates with existing FileWatcher for CWD invalidation
- 2-minute TTL ensures data freshness for filesystem-backed operations

---

## Current State Analysis

| Component | Status | Notes |
|-----------|--------|-------|
| **`build_deployment_statistics()`** | Uncached | Full filesystem scan on every call (`artifacts.py:248-326`) |
| **`discover_projects()`** | Uncached | `.rglob()` across ~/projects, ~/dev, ~/workspace, ~/src, CWD (`projects.py:142-207`) |
| **`compute_content_hash()`** | Per-call | Reads and SHA256-hashes each deployed artifact file |
| **`CollectionCountCache`** | Pattern exists | Thread-safe singleton TTL cache (`cache/collection_cache.py`) |
| **FileWatcher** | Active | Watches ~/.skillmeat/ and ./.claude/ but NOT `.skillmeat-deployed.toml` |
| **Frontend caching** | Adequate | 5min staleTime + 30min gcTime on `ProjectSelectorForDiff` |
| **DB cache** | Not applicable | Doesn't track per-artifact `is_modified` across all projects |

### Root Cause Trace

```
ProjectSelectorForDiff (frontend)
  -> GET /artifacts/{id}?include_deployments=true
    -> get_artifact_detail() (artifacts.py:1990)
      -> build_deployment_statistics() (artifacts.py:248)
        -> discover_projects() (projects.py:142)    # SLOW: recursive .rglob()
        -> DeploymentTracker.read_deployments()      # SLOW: reads TOML per project
        -> compute_content_hash()                    # SLOW: reads + hashes files
```

**Note on line 266**: The existing code already has a comment: `"This function scans the filesystem for projects, which may be slow for large directory structures. Consider implementing caching."`

---

## Architecture Decision

**Approach:** In-memory TTL cache (Option A)

**Why not use the DB cache?** The existing `CacheManager` doesn't track `is_modified` status or content hashes across all discovered projects. Adding that would require schema changes, a new population mechanism scanning all projects at startup, and a migration. This violates YAGNI for a 2-minute cache scenario.

**Why in-memory is sufficient:**
- Single-worker dev mode means per-process cache is fully effective
- The `CollectionCountCache` pattern already validates this approach in production
- Worst case (multi-worker) degrades to current behavior, not worse
- 2-minute TTL means memory usage is negligible (<1MB even with 100 artifacts)

---

## Implementation Tasks

| ID | Task | Description | Acceptance Criteria | Assigned To |
|----|------|-------------|---------------------|-------------|
| DSC-1 | Create `DeploymentStatsCache` | New module `skillmeat/cache/deployment_stats_cache.py` following `CollectionCountCache` pattern | Thread-safe singleton with two-level TTL cache, get/set/invalidate methods | python-backend-engineer |
| DSC-2 | Integrate cache in `build_deployment_statistics()` | Modify `skillmeat/api/routers/artifacts.py:248-326` to check/populate cache | Cache hit returns immediately; cache miss runs existing logic then caches result | python-backend-engineer |
| DSC-3 | Add FileWatcher support for `.skillmeat-deployed.toml` | Modify `skillmeat/cache/watcher.py:145-204` to detect deployment file changes | FileWatcher recognizes `.skillmeat-deployed.toml` as relevant and invalidates deployment stats cache | python-backend-engineer |
| DSC-4 | Add invalidation to deploy/undeploy handlers | Modify `skillmeat/api/routers/deployments.py` to invalidate cache after mutations | Deploy and undeploy operations clear the deployment stats cache | python-backend-engineer |
| DSC-5 | Write unit tests | New test file `skillmeat/cache/tests/test_deployment_stats_cache.py` | Tests cover: cache miss, cache hit, TTL expiry, invalidation (single + all), thread safety | python-pro |

**Total Effort:** ~3-4 hours

---

## Technical Details

### DSC-1: `DeploymentStatsCache` Class

**File:** `skillmeat/cache/deployment_stats_cache.py` (CREATE, ~100 lines)

**Pattern Reference:** `skillmeat/cache/collection_cache.py`

```python
class DeploymentStatsCache:
    DEFAULT_TTL: int = 120  # 2 minutes

    # Level 1: Project discovery results
    # Key: "discovered_projects"
    # Value: (List[Path], timestamp)
    _projects_cache: Optional[Tuple[List[Path], float]]

    # Level 2: Per-artifact deployment statistics
    # Key: (artifact_name, artifact_type)
    # Value: (DeploymentStatistics, timestamp)
    _stats_cache: Dict[Tuple[str, str], Tuple[DeploymentStatistics, float]]

    # Thread safety
    _lock: threading.Lock
```

**Methods:**
- `get_discovered_projects() -> Optional[List[Path]]` -- returns cached paths or None if expired
- `set_discovered_projects(paths: List[Path])` -- caches with current timestamp
- `get_stats(name: str, type: str) -> Optional[DeploymentStatistics]` -- returns cached stats or None
- `set_stats(name: str, type: str, stats: DeploymentStatistics)` -- caches with timestamp
- `invalidate_all()` -- clears both cache levels
- `invalidate_artifact(name: str, type: str)` -- clears single artifact entry

**Singleton:** `get_deployment_stats_cache()` function, identical to `get_collection_count_cache()` pattern.

### DSC-2: `build_deployment_statistics()` Integration

**File:** `skillmeat/api/routers/artifacts.py` (MODIFY, ~15 lines changed at lines 248-326)

```python
async def build_deployment_statistics(artifact_name, artifact_type):
    from skillmeat.cache.deployment_stats_cache import get_deployment_stats_cache
    cache = get_deployment_stats_cache()

    # Fast path: full cache hit
    cached = cache.get_stats(artifact_name, artifact_type.value)
    if cached is not None:
        return cached

    # Medium path: reuse cached project discovery
    from skillmeat.api.routers.projects import discover_projects
    project_paths = cache.get_discovered_projects()
    if project_paths is None:
        project_paths = discover_projects()
        cache.set_discovered_projects(project_paths)

    # ... existing logic using project_paths (unchanged) ...

    result = DeploymentStatistics(...)
    cache.set_stats(artifact_name, artifact_type.value, result)
    return result
```

### DSC-3: FileWatcher Extension

**File:** `skillmeat/cache/watcher.py` (MODIFY, ~8 lines)

In `_is_relevant_file()` (after line 198):
```python
# Check for deployment tracking files
if filename == ".skillmeat-deployed.toml":
    return True
```

In `_handle_file_change()`, add deployment stats cache invalidation when deployment files change:
```python
if ".skillmeat-deployed.toml" in path:
    from skillmeat.cache.deployment_stats_cache import get_deployment_stats_cache
    get_deployment_stats_cache().invalidate_all()
```

**Limitation:** FileWatcher only watches `~/.skillmeat/` and `./.claude/` by default, not all project search directories. This provides CWD invalidation; other projects rely on the 2-minute TTL.

### DSC-4: Deploy/Undeploy Invalidation

**File:** `skillmeat/api/routers/deployments.py` (MODIFY, ~4 lines)

After successful `deploy_artifact()` (line ~109) and `undeploy_artifact()` (line ~261):
```python
from skillmeat.cache.deployment_stats_cache import get_deployment_stats_cache
get_deployment_stats_cache().invalidate_all()
```

### DSC-5: No Frontend Changes

The frontend already has appropriate caching:
- `ProjectSelectorForDiff`: `staleTime: 5 * 60 * 1000`, `gcTime: 30 * 60 * 1000`
- `useDeployments`: `staleTime: 2 * 60 * 1000`

Combined cache behavior:
1. First load: backend scans filesystem (~2-5s), caches in memory, returns
2. Same artifact within 5 min: TanStack Query serves from frontend cache (~0ms)
3. Different artifact within 2 min: backend serves from in-memory cache (~0ms)
4. After deploy/undeploy: cache invalidated, next load rescans once

---

## Files Summary

| File | Action | Est. Lines |
|------|--------|------------|
| `skillmeat/cache/deployment_stats_cache.py` | CREATE | ~100 |
| `skillmeat/api/routers/artifacts.py` | MODIFY | ~15 changed |
| `skillmeat/cache/watcher.py` | MODIFY | ~8 added |
| `skillmeat/api/routers/deployments.py` | MODIFY | ~4 added |
| `skillmeat/cache/tests/test_deployment_stats_cache.py` | CREATE | ~80 |

---

## Performance Impact

| Scenario | Before | After |
|----------|--------|-------|
| First load (cold) | ~2-5s | ~2-5s (same, caches result) |
| Different artifact (within 2 min) | ~2-5s | ~0ms (in-memory cache hit) |
| Same artifact (within 5 min) | ~2-5s | ~0ms (TanStack Query cache) |
| After deploy/undeploy | ~2-5s | ~2-5s (cache invalidated, rescans once) |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Multi-worker per-process cache | Workers have independent caches | Worst case = current behavior; single worker is default |
| Stale data from CLI changes | Up to 2 min stale | FileWatcher handles CWD; TTL handles other projects |
| Memory usage | Negligible | <1MB even with 100 cached artifacts |

---

## Verification

1. Start dev servers: `skillmeat web dev`
2. Open `/manage`, click an artifact with deployments, go to Sync Status tab
3. Observe "Loading projects..." duration on first load (baseline)
4. Close and reopen the same artifact -- should be near-instant (TanStack cache)
5. Open a different artifact's Sync Status tab -- should be faster (project discovery cached)
6. Deploy/undeploy an artifact, then reopen -- should show fresh data
7. Run tests: `pytest skillmeat/cache/tests/test_deployment_stats_cache.py -v`
8. Run existing tests: `pytest skillmeat/api/tests/ -v`
