---
prd: discovery-cache-fixes
phase: 1
title: Discovery Cache & Invalidation Fixes
status: completed
completion: 100%
updated_at: 2025-12-03 12:00:00+00:00
completed_at: 2025-12-03 12:00:00+00:00
tasks:
- id: BUG1-001
  title: Backend discovery filtering
  description: Modify discover_artifacts() to filter already-imported artifacts
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_time: 2h
  commit: e09951c
  files:
  - skillmeat/core/discovery.py
- id: BUG1-002
  title: API endpoint update
  description: Update /discover endpoint to pass manifest and return importable_count
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BUG1-001
  estimated_time: 1h
  commit: e09951c
  files:
  - skillmeat/api/routers/artifacts.py
- id: BUG2-001
  title: Frontend cache invalidation fixes
  description: Fix async/await race conditions and implement granular cache invalidation
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_time: 2h
  commit: e09951c
  files:
  - skillmeat/web/hooks/useProjectDiscovery.ts
  - skillmeat/web/hooks/useCacheRefresh.ts
  - skillmeat/web/hooks/useDeploy.ts
  - skillmeat/web/hooks/useDiscovery.ts
- id: BUG1-003
  title: Frontend UI update - show remaining count
  description: Update DiscoveryBanner to display importable_count instead of discovered_count
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - BUG1-002
  - BUG2-001
  estimated_time: 1h
  commit: e09951c
  files:
  - skillmeat/web/components/discovery/DiscoveryBanner.tsx
  - skillmeat/web/hooks/useProjectDiscovery.ts
  - skillmeat/web/types/discovery.ts
- id: BUG2-002
  title: Backend integration tests
  description: Add integration tests for discovery filtering and cache invalidation
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BUG1-002
  estimated_time: 2h
  commit: e09951c
  files:
  - skillmeat/api/tests/test_discovery_cache_fixes.py
- id: BUG1-004
  title: Frontend component tests
  description: Add unit tests for DiscoveryBanner count display and hiding behavior
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - BUG1-003
  estimated_time: 1h
  commit: e09951c
  files:
  - skillmeat/web/__tests__/discovery-banner.test.tsx
parallelization:
  batch_1:
  - BUG1-001
  - BUG2-001
  batch_2:
  - BUG1-002
  batch_3:
  - BUG1-003
  - BUG2-002
  batch_4:
  - BUG1-004
  critical_path:
  - BUG1-001
  - BUG1-002
  - BUG1-003
  - BUG1-004
  estimated_total_time: 9h
blockers: []
work_log: []
schema_version: 2
doc_type: progress
feature_slug: discovery-cache-fixes
type: progress
---

# Phase 1: Discovery Cache & Invalidation Fixes

## Overview

Fixes for two interconnected caching issues:
1. Discovery banner shows stale count after imports
2. Cache invalidation invalidates all projects instead of target project

## Orchestration Quick Reference

**Batch 1** (Parallel - No dependencies):
- BUG1-001 -> `python-backend-engineer` (2h): Backend discovery filtering
- BUG2-001 -> `ui-engineer` (2h): Frontend cache invalidation fixes

### Task Delegation Commands

```
Task("python-backend-engineer", "BUG1-001: Modify discover_artifacts() in skillmeat/core/discovery.py to:
1. Accept optional manifest parameter
2. Filter discovered artifacts against already-imported artifacts in manifest
3. Add importable_count field to DiscoveryResult
4. Return both discovered_count (all) and importable_count (unimported)
5. Add unit tests with >80% coverage
6. Ensure performance <2s for 50+ artifacts")

Task("ui-engineer", "BUG2-001: Fix cache invalidation race conditions in frontend hooks:
1. useProjectDiscovery.ts - await invalidateQueries() in onSuccess
2. useCacheRefresh.ts - add optional projectId param for granular invalidation
3. useDeploy.ts - pass projectId to cache refresh
4. useDiscovery.ts - await invalidateQueries() in onSuccess
Ensure cache invalidation only affects target project, not all projects")
```

**Batch 2** (After BUG1-001):
- BUG1-002 -> `python-backend-engineer` (1h): API endpoint update

```
Task("python-backend-engineer", "BUG1-002: Update /discover endpoint in skillmeat/api/routers/artifacts.py to:
1. Load manifest from collection manager
2. Pass manifest to discover_artifacts() service
3. Return both discovered_count and importable_count in response
4. Handle missing manifest gracefully (return all as importable)")
```

**Batch 3** (After BUG1-002 and BUG2-001):
- BUG1-003 -> `ui-engineer` (1h): Frontend UI update
- BUG2-002 -> `python-backend-engineer` (2h): Backend integration tests

```
Task("ui-engineer", "BUG1-003: Update DiscoveryBanner and hooks to show importable count:
1. Update DiscoveryBanner.tsx props to accept importableCount and discoveredCount
2. Display importableCount instead of discoveredCount
3. Hide banner when importableCount is 0
4. Update useProjectDiscovery to expose importableCount
5. Update types/discovery.ts with new fields")

Task("python-backend-engineer", "BUG2-002: Add integration tests in skillmeat/api/tests/test_discovery_cache_fixes.py:
1. test_discovery_filters_imported_artifacts
2. test_importable_count_decreases_after_import
3. test_cache_invalidation_specific_project
4. test_refetch_waits_for_fresh_data")
```

**Batch 4** (After BUG1-003):
- BUG1-004 -> `ui-engineer` (1h): Frontend component tests

```
Task("ui-engineer", "BUG1-004: Add unit tests for DiscoveryBanner in skillmeat/web/__tests__/discovery-banner.test.tsx:
1. displays importable count, not total discovered
2. hides when importable count is 0
3. shows singular 'Artifact' when count is 1
4. Achieve >80% component coverage")
```

## Success Criteria

- [ ] Discovery banner shows only unimported artifact count
- [ ] After importing, banner count updates immediately (no stale data)
- [ ] Importing to Project A does not invalidate Project B's cache
- [ ] All tests passing (unit + integration)
- [ ] No performance regressions
