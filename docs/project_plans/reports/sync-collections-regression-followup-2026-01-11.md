# Sync + Collections Regression Analysis - Follow-up Report

**Date**: 2026-01-11
**Original Analysis**: 2026-01-09
**Status**: Verification Complete

## Executive Summary

Verification of the 7 findings from the original regression analysis reveals:
- **2 findings fully resolved** (no action needed)
- **4 findings partially addressed** (require targeted fixes)
- **1 finding not addressed** (critical, requires immediate action)

## Verification Results

| Finding | Issue | Status | Priority |
|---------|-------|--------|----------|
| #1 | Deployment metadata schema mismatch | ⚠️ Partially Addressed | P2 |
| #2 | Cache migrations not run at runtime | ❌ Not Addressed | **P0 Critical** |
| #3 | Collection identity inconsistent | ⚠️ Partially Addressed | P1 |
| #4 | Artifact linking name-only | ⚠️ Partially Addressed | P1 |
| #5 | MCP/Hook deployment not supported | ✅ Resolved | None |
| #6 | Context sync service stubbed | ⚠️ Partially Addressed | P2 |
| #7 | Artifact metadata cache fallback | ✅ Resolved | None |

---

## Detailed Findings

### Finding #1: Deployment Metadata Schema Mismatch

**Original Issue**: `sync.py` and `deployment.py` write different TOML schemas to the same file.

**Current State**:
- Two parallel systems still exist:
  - System 1 (`sync.py`): Uses `[deployment]` + `[[artifacts]]` with `DeploymentRecord`
  - System 2 (`deployment.py`): Uses `[[deployed]]` with richer `Deployment` class
- **Mitigated** because recent development uses System 2 exclusively
- `sync.py` write methods are not actively called in current workflows

**Evidence**:
- `skillmeat/core/sync.py:320-420` - Old schema reading/writing
- `skillmeat/storage/deployment.py:30-71` - New schema with backward compatibility
- `skillmeat/core/deployment.py:17-128` - Rich Deployment class

**Risk**: Low (mitigated by usage patterns, but technical debt remains)

**Remediation**: Migrate `sync.py` to use `DeploymentTracker` from `storage/deployment.py`

---

### Finding #2: Cache Migrations Not Run at Runtime

**Original Issue**: `CacheManager` only calls `create_tables()`, never runs Alembic migrations.

**Current State**: ❌ **NOT ADDRESSED - CRITICAL**
- `initialize_cache()` at line 155 only calls `create_tables()`
- `run_migrations()` function exists in `skillmeat/cache/migrations/__init__.py:59` but is never called
- Collections and groups tables are only created via migrations
- **Result**: Groups/collections features fail on existing databases

**Evidence**:
- `skillmeat/cache/manager.py:155-182` - Missing migration call
- `skillmeat/cache/migrations/versions/20251212_1600_create_collections_schema.py` - Migration exists but not applied

**Risk**: **CRITICAL** - Breaks groups and collections features for existing users

**Remediation**: Add `run_migrations()` call to `initialize_cache()` (1 line fix)

---

### Finding #3: Collection Identity Inconsistent

**Original Issue**: UI hard-codes `'default'` collection, breaking multi-collection support.

**Current State**: ⚠️ **Backend ready, frontend not updated**
- Backend API accepts `?collection=` query parameter correctly
- Frontend still hard-codes `collection: 'default'` in multiple locations:
  - `useEntityLifecycle.tsx:236` - Entity mapping
  - `deploy-from-collection-dialog.tsx:66` - Deploy dialog
  - `useEntityLifecycle.tsx:714,727,740` - Mock data
- Deploy requests don't pass collection parameter to API

**Evidence**:
- `skillmeat/api/routers/artifacts.py:2652-2713` - Backend supports collection param
- `skillmeat/web/hooks/useEntityLifecycle.tsx:236` - Hard-coded 'default'
- `skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx:66,111-119` - Missing collection context

**Risk**: High - Multi-collection feature is broken

**Remediation**: Wire collection IDs through frontend, pass to API calls

---

### Finding #4: Artifact-to-Deployment Linking Name-Only

**Original Issue**: Matching uses name only, not (name, type) tuple.

**Current State**: ⚠️ **Backend fixed, frontend still name-only**
- Backend `DeploymentTracker.get_deployment()` uses `(artifact_name, artifact_type)` tuple ✅
- Frontend matching still uses name-only:
  - `projects/[id]/page.tsx:136-166` - `artifact.name === deployedArtifact.artifact_name`
  - `collection/page.tsx:39-84` - `a.name === summary.name`

**Evidence**:
- `skillmeat/api/routers/projects.py:1084-1086` - Backend uses tuple
- `skillmeat/web/app/projects/[id]/page.tsx:136` - Frontend name-only
- `skillmeat/web/app/collection/page.tsx:39` - Frontend name-only

**Risk**: Medium - Collision when same name exists with different types

**Remediation**: Update frontend matching to include artifact type

---

### Finding #5: MCP/Hook Deployment Not Supported

**Original Issue**: Deployment tracking only handled skill, command, agent.

**Current State**: ✅ **FULLY RESOLVED**
- Both MCP and Hook artifact types now fully supported
- Deployment paths implemented:
  - `hooks/{name}.md` (file-based)
  - `mcp/{name}/` (directory-based)
- Full feature support: version tracking, analytics, undeploy

**Evidence**:
- `skillmeat/storage/deployment.py:99-102` - Hook/MCP path routing
- `skillmeat/core/deployment.py:234-237` - Deployment manager support
- `skillmeat/core/mcp/deployment.py` - MCP-specific Claude Desktop integration

**Action**: None required

---

### Finding #6: Context Sync Service Stubbed

**Original Issue**: `ContextSyncService` is largely stubbed, making sync status misleading.

**Current State**: ⚠️ **Detection works, persistence stubbed**
- Working components:
  - `detect_modified_entities()` - Correctly identifies changes
  - `detect_conflicts()` - Identifies both-modified cases
  - UI component - Displays status correctly
- Stubbed components (log but don't persist):
  - `pull_changes()` - Lines 321-330 are TODO with pass
  - `push_changes()` - Lines 435-447 are TODO with pass
  - `resolve_conflict()` - Lines 588-613 are empty pass blocks
- **No preview badge** warns users that feature is incomplete

**Evidence**:
- `skillmeat/core/services/context_sync.py:321-330` - Pull stub
- `skillmeat/core/services/context_sync.py:435-447` - Push stub
- `skillmeat/core/services/context_sync.py:588-613` - Resolve stub
- `skillmeat/web/components/entity/context-sync-status.tsx` - No preview badge

**Risk**: Medium - Misleading UI, but non-critical feature

**Remediation**: Either add preview badge OR implement stub methods

---

### Finding #7: Artifact Metadata Cache Fallback

**Original Issue**: `get_artifact_metadata()` only checks cache DB, not file-based collections.

**Current State**: ✅ **FULLY RESOLVED**
- 3-tier fallback system implemented:
  1. Cache DB (`Artifact` table)
  2. Marketplace catalog (`MarketplaceCatalogEntry`)
  3. Minimal fallback (never returns null)
- Background sync via `RefreshJob` (6-hour interval)
- Manual refresh via `POST /cache/refresh` endpoint

**Evidence**:
- `skillmeat/api/services/artifact_metadata_service.py` - 3-tier fallback
- `skillmeat/cache/refresh.py` - Background sync job
- `skillmeat/api/routers/cache.py` - Manual refresh endpoints

**Action**: None required

---

## Prioritized Remediation Plan

### P0 - Critical (Immediate)

| Finding | Action | Effort | Files |
|---------|--------|--------|-------|
| #2 | Add `run_migrations()` to cache init | 5 min | `cache/manager.py` |

### P1 - High (This Sprint)

| Finding | Action | Effort | Files |
|---------|--------|--------|-------|
| #4 | Add type to frontend artifact matching | 30 min | `projects/[id]/page.tsx`, `collection/page.tsx` |
| #3 | Wire collection IDs through frontend | 2-3 hours | `useEntityLifecycle.tsx`, `deploy-from-collection-dialog.tsx` |

### P2 - Medium (Next Sprint)

| Finding | Action | Effort | Files |
|---------|--------|--------|-------|
| #6 | Add preview badge to context sync UI | 30 min | `context-sync-status.tsx` |
| #1 | Migrate sync.py to unified Deployment class | 2-3 hours | `core/sync.py` |

### No Action Required

| Finding | Status |
|---------|--------|
| #5 | Fully resolved - MCP/Hook support implemented |
| #7 | Fully resolved - 3-tier fallback system works |

---

## Risk Assessment

### If P0 Not Addressed
- **Impact**: Groups and collections features fail for existing users
- **Scope**: Any user with pre-existing cache database
- **Mitigation**: None (requires code fix)

### If P1 Not Addressed
- **Impact**: Multi-collection feature broken; artifact collisions possible
- **Scope**: Users with multiple collections or same-name artifacts
- **Mitigation**: Single-collection workflows still work

### If P2 Not Addressed
- **Impact**: Technical debt; misleading context sync UI
- **Scope**: Low user impact (advanced features)
- **Mitigation**: Features work partially; users adapt

---

## Appendix: File References

### Critical Files (P0)
- `skillmeat/cache/manager.py:155-182`
- `skillmeat/cache/migrations/__init__.py:59`

### Frontend Files (P1)
- `skillmeat/web/app/projects/[id]/page.tsx:136-166`
- `skillmeat/web/app/collection/page.tsx:39-84`
- `skillmeat/web/hooks/useEntityLifecycle.tsx:236,714,727,740`
- `skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx:66,111-119`

### Backend Files (P2)
- `skillmeat/core/sync.py:320-420`
- `skillmeat/core/services/context_sync.py:321-330,435-447,588-613`
- `skillmeat/web/components/entity/context-sync-status.tsx`
