# Marketplace GitHub Ingestion - Gaps Quick Reference

## One-Line Summary
**All code exists but critical integrations missing - heuristic detector disconnected, diff engine unused, import downloads stubbed.**

---

## The 3 Critical Gaps

### 1️⃣ Heuristic Detector Disconnected ⚠️ BLOCKING
- **File**: `skillmeat/core/marketplace/github_scanner.py`
- **Lines**: 30-34 (import), 101 (init), 161-167 (call), 464-471 (call)
- **Problem**: Import is commented out, detector never initialized, `detect_artifacts_in_tree()` calls commented
- **Result**: Every scan returns `artifacts_found=0` regardless of repository contents
- **Fix**: Uncomment 4 blocks (30 min)

### 2️⃣ Diff Engine Unused ⚠️ BLOCKING
- **File**: `skillmeat/api/routers/marketplace_sources.py`
- **Lines**: 545-548
- **Problem**: TODO comment, hardcoded `new_entries = []` instead of using `CatalogDiffEngine.compute_diff()`
- **Result**: Every rescan wipes catalog (no incremental updates)
- **Fix**: Implement 3-line diff call (1 hour)

### 3️⃣ Import Downloads Missing ⚠️ BLOCKING
- **File**: `skillmeat/core/marketplace/import_coordinator.py`
- **Lines**: 216-220
- **Problem**: Comment says "In a full implementation, this would download...", marks SUCCESS without downloading
- **Result**: Import succeeds but artifacts not persisted to disk
- **Fix**: Implement fetch + write (2 hours)

---

## What Actually Works ✅

| Component | File | Status |
|-----------|------|--------|
| Source CRUD | `marketplace_sources.py:151-461` | ✅ All endpoints functional |
| Heuristic Detector | `heuristic_detector.py` | ✅ Fully functional (just disconnected) |
| Diff Engine | `diff_engine.py` | ✅ Fully functional (just unused) |
| Link Harvester | `link_harvester.py` | ✅ Fully functional (just orphaned) |
| Import Coordinator | `import_coordinator.py` | ✅ Conflict detection works (downloads missing) |
| Observability | `observability.py` | ✅ Complete with OpenTelemetry |
| Error Handling | All routers | ✅ HTTPException, logging |
| Artifacts Listing | `marketplace_sources.py:600-727` | ✅ Pagination, filters |

---

## What Doesn't Work ❌

| Feature | Where | Issue |
|---------|-------|-------|
| Artifact Detection | `github_scanner.py:170` | Returns empty list always |
| Incremental Scans | `marketplace_sources.py:545` | Hardcoded `new_entries = []` |
| Artifact Persistence | `import_coordinator.py:220` | Marks SUCCESS without downloading |
| Background Jobs | API-007 not implemented | Scans block request thread |
| Authentication | All endpoints marked TODO | No user isolation |
| README Harvesting | Not integrated | Detector exists but never called |

---

## File Structure Summary

```
skillmeat/core/marketplace/
├── heuristic_detector.py     ✅ Complete, disconnected
├── github_scanner.py          ⚠️ Fetches tree, returns empty artifacts
├── link_harvester.py          ✅ Complete, orphaned
├── diff_engine.py             ✅ Complete, unused
├── import_coordinator.py       ⚠️ Conflict logic works, downloads missing
└── observability.py           ✅ Complete

skillmeat/api/routers/
└── marketplace_sources.py     ⚠️ All endpoints exist, key logic stubbed
```

---

## Implementation Status Grid

```
Phase 3: Service Layer
┌─────────────────────────┬──────────┬───────────┬─────────┐
│ Task                    │ Planned  │ Code      │ Working │
├─────────────────────────┼──────────┼───────────┼─────────┤
│ SVC-001 DTOs            │ ✅ Yes   │ ✅ Done   │ ✅ Yes  │
│ SVC-002 Heuristic       │ ✅ Yes   │ ✅ Done   │ ❌ No   │
│ SVC-003 GitHub Scanner  │ ✅ Yes   │ ✅ Done   │ ⚠️ Partial │
│ SVC-004 README Harvester│ ✅ Yes   │ ✅ Done   │ ❌ No   │
│ SVC-005 Catalog Diff    │ ✅ Yes   │ ✅ Done   │ ❌ No   │
│ SVC-006 Import Coord    │ ✅ Yes   │ ✅ Done   │ ⚠️ Partial │
│ SVC-007 Observability   │ ✅ Yes   │ ✅ Done   │ ✅ Yes  │
└─────────────────────────┴──────────┴───────────┴─────────┘

Phase 4: API Layer
┌─────────────────────────┬──────────┬───────────┬─────────┐
│ Task                    │ Planned  │ Code      │ Working │
├─────────────────────────┼──────────┼───────────┼─────────┤
│ API-001 Sources Router  │ ✅ Yes   │ ✅ Done   │ ✅ Yes  │
│ API-002 Rescan          │ ✅ Yes   │ ✅ Done   │ ❌ No   │
│ API-003 Artifacts List  │ ✅ Yes   │ ✅ Done   │ ✅ Yes  │
│ API-004 Import          │ ✅ Yes   │ ✅ Done   │ ⚠️ Partial │
│ API-005 Error/Validation│ ✅ Yes   │ ✅ Done   │ ⚠️ Partial │
│ API-006 Auth/Security   │ ✅ Yes   │ ❌ Stub   │ ❌ No   │
│ API-007 Background Jobs │ ✅ Yes   │ ❌ Stub   │ ❌ No   │
└─────────────────────────┴──────────┴───────────┴─────────┘
```

---

## Quick Checklist to Enable MVP

```
[ ] 1. Uncomment heuristic detector import (30 min)
    [ ] github_scanner.py line 30-34 (uncomment import)
    [ ] github_scanner.py line 101 (uncomment init)
    [ ] github_scanner.py line 161-167 (uncomment call)
    [ ] github_scanner.py line 464-471 (uncomment call)

[ ] 2. Use diff engine for incremental updates (1 hour)
    [ ] marketplace_sources.py line 545-548
    [ ] Fetch existing entries from DB
    [ ] Call compute_diff()
    [ ] Apply new/updated/removed

[ ] 3. Implement import downloads (2 hours)
    [ ] import_coordinator.py line 220
    [ ] Fetch artifact from upstream_url
    [ ] Write to local_path
    [ ] Update manifest
```

**Total Time to MVP**: ~3.5 hours

---

## Evidence

### Gap 1: Detector Disconnected
```python
# github_scanner.py lines 159-174 (WARNING shown every scan)
# NOTE: This will be uncommented once SVC-002 (heuristic detector) is implemented
# base_url = f"https://github.com/{owner}/{repo}"
# artifacts = detect_artifacts_in_tree(...)

# Placeholder until heuristic detector is implemented
artifacts = []
logger.warning("Heuristic detector not yet implemented (SVC-002).")
```

### Gap 2: Diff Engine Unused
```python
# marketplace_sources.py lines 545-548
# TODO: Use diff engine for incremental updates
# Currently heuristic detector returns empty list, so this is a placeholder
new_entries: List[MarketplaceCatalogEntry] = []
ctx.replace_catalog_entries(new_entries)
```

### Gap 3: Downloads Missing
```python
# import_coordinator.py lines 216-220
# In a full implementation, this would:
# 1. Download artifact files from upstream_url
# 2. Write to local_path
# 3. Update manifest
entry.status = ImportStatus.SUCCESS
```

---

## Related Documentation

- **Full Analysis**: `.claude/worknotes/marketplace-gaps-analysis-2025-12-26.md` (detailed breakdown by task)
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/marketplace-github-ingestion-v1.md`
- **Router Reference**: `.claude/rules/api/routers.md`

