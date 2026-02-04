# Sync/Diff Modal Inconsistency Analysis

**Date**: 2026-02-04
**Branch**: `feat/refresh-metadata-extraction-v1`
**Status**: Investigation Complete

## Executive Summary

The Sync Status tab behaves differently between the `/manage` and `/projects/{ID}` pages due to **three distinct root causes**: a frontend-backend mismatch in upstream source validation, missing `projectPath` in collection mode, and two separate modal component implementations with divergent prop-passing patterns.

---

## Issue 1: Frontend-Backend Source Validation Mismatch (400 Errors)

**Severity**: High
**Impact**: Marketplace-sourced artifacts trigger failed API calls with 400 errors on the /manage page

### Root Cause

The frontend and backend use **different fields** to determine if an artifact supports upstream diff:

| Layer | Field Checked | Example (codex) | Result |
|-------|--------------|------------------|--------|
| **Frontend** `hasValidUpstreamSource()` | `entity.source` | `"https://github.com/davila7/..."` | **Passes** (contains `/`) |
| **Backend** upstream-diff endpoint | `artifact.origin` | `"marketplace"` | **Fails** (not `"github"`) |

**Frontend logic** (`sync-status-tab.tsx:98-104`):
```typescript
function hasValidUpstreamSource(source: string | undefined | null): boolean {
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;
  return source.includes('/') && !source.startsWith('local');
}
```
This checks `entity.source` (the URL string), which for marketplace artifacts contains a GitHub URL.

**Backend logic** (`artifacts.py:4160-4164`):
```python
if artifact.origin != "github":
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Artifact origin '{artifact.origin}' does not support upstream diff...",
    )
```
This checks `artifact.origin` (the origin enum: `"github"`, `"marketplace"`, `"local"`).

### Evidence

API call for `codex` artifact:
```
GET /api/v1/artifacts/skill%3Acodex/upstream-diff?collection=default → 400
Response: {"detail": "Artifact origin 'marketplace' does not support upstream diff. Only GitHub artifacts are supported."}
```

Artifact data:
```json
{
  "name": "codex",
  "source": "https://github.com/davila7/claude-code-templates/tree/main/...",
  "origin": "marketplace",
  "origin_source": "github",
  "upstream": null
}
```

The frontend sees the GitHub URL in `source` and fires the query. The backend rejects it because `origin` is `"marketplace"`, not `"github"`. This also causes TanStack Query retries (observed 4 consecutive 400 responses).

### Additional Check: `upstream: null`

Even if the origin check passed, the backend would fail at line 4166-4170:
```python
if not artifact.upstream:
    raise HTTPException(status_code=400, detail="Artifact does not have upstream tracking configured")
```
Marketplace artifacts have `upstream: null` because they were imported through the marketplace flow, not directly from GitHub with tracking enabled.

### Fix Required

The frontend `hasValidUpstreamSource()` function needs to also check `entity.origin` (or `entity.upstream`) to align with backend expectations:

```typescript
function hasValidUpstreamSource(entity: Artifact): boolean {
  // Must have GitHub origin AND upstream tracking configured
  if (entity.origin !== 'github') return false;
  if (!entity.upstream?.tracking_enabled) return false;
  if (!entity.source) return false;
  return entity.source.includes('/') && !entity.source.startsWith('local');
}
```

The `enabled` condition on the upstream-diff query (`sync-status-tab.tsx:238-239`) should incorporate this check.

---

## Issue 2: Missing `projectPath` in Collection Mode

**Severity**: High
**Impact**: The /manage Sync Status tab can never show collection-vs-project diffs

### Root Cause

The `ArtifactOperationsModal` passes `SyncStatusTab` in collection mode **without a `projectPath` prop**:

**`artifact-operations-modal.tsx:1185-1191`**:
```tsx
<SyncStatusTab
  entity={artifact}
  mode="collection"
  onClose={onClose}
  // NOTE: No projectPath prop!
/>
```

Compare with `UnifiedEntityModal` (used by `/projects` page) at line 2111-2116:
```tsx
<SyncStatusTab
  entity={entity}
  mode={entity.projectPath ? 'project' : 'collection'}
  projectPath={entity.projectPath || selectedProjectForDiff || undefined}
  onClose={onClose}
/>
```

### Consequence

In `SyncStatusTab`, the project diff query (`sync-status-tab.tsx:254-256`) is disabled:
```typescript
enabled: !!entity.id && !!projectPath && entity.collection !== 'discovered',
//                       ^^^^^^^^^^^^^ always false in /manage modal
```

This means:
1. **Source-vs-Collection** (`upstream-diff`): Only works for `origin: "github"` artifacts with upstream tracking
2. **Collection-vs-Project** (`diff`): **Never works** - `projectPath` is always undefined
3. **Source-vs-Project**: Never works - depends on both queries above

For local-only artifacts (no GitHub source), ALL three comparison scopes are disabled, resulting in the "No comparison data available" message.

### Flow Banner Impact

The flow banner also shows "Not deployed" for the Project node because `projectDiff` is always null (query never fires), even if the artifact IS deployed to projects.

### Fix Required

The `/manage` modal needs a way to provide `projectPath` to the sync tab. Options:
1. Add a project selector within the sync tab when in collection mode (similar to `selectedProjectForDiff` in `UnifiedEntityModal`)
2. Pass deployment information to derive a default project path
3. If the artifact has exactly one deployment, auto-select that project

---

## Issue 3: Dual Modal Architecture Divergence

**Severity**: Medium
**Impact**: Inconsistent user experience and maintenance burden

### Architecture

Two separate modal components serve the same purpose but with different implementations:

| Aspect | `/manage` Page | `/projects/{ID}` Page |
|--------|---------------|----------------------|
| Modal Component | `ArtifactOperationsModal` (1412 lines) | `ProjectArtifactModal` -> `UnifiedEntityModal` (900+ lines) |
| Default Tab | `'status'` | `'overview'` |
| Sync Mode | Hardcoded `mode="collection"` | Dynamic: `entity.projectPath ? 'project' : 'collection'` |
| Project Path | Not provided | `entity.projectPath \|\| selectedProjectForDiff` |
| Project Selector | None | `ProjectSelectorForDiff` component available |
| Lifecycle Provider | `EntityLifecycleProvider mode="collection"` | `EntityLifecycleProvider mode="project" projectPath={...}` |

### Key Differences in Sync Tab

1. **`ArtifactOperationsModal`** hardcodes collection mode and provides no project context
2. **`UnifiedEntityModal`** dynamically determines mode and has a project selector fallback (`selectedProjectForDiff` state at line 622)
3. The `UnifiedEntityModal` also has a **disabled** upstream-diff query (line 720-722: `enabled: false`) because it delegates that to `SyncStatusTab` internally -- this is correct deduplication

### Implication

The `/manage` modal was designed for collection-centric operations but the sync tab needs project context for meaningful diffs. The `/projects` modal naturally has project context from its page route.

---

## Issue 4: Sync Action Mutations (Partial Functionality)

**Severity**: Medium
**Impact**: Sync/merge/push/pull actions may not work as expected even when diff data loads

### Analysis of Mutations in `sync-status-tab.tsx`

| Action | Implementation | Status |
|--------|---------------|--------|
| **Pull from Source** (syncMutation) | `POST /artifacts/{id}/sync` with empty body | Calls endpoint but body may not trigger upstream sync correctly |
| **Deploy to Project** (deployMutation) | `POST /artifacts/{id}/deploy` with `project_path` | Requires `projectPath` - broken in /manage (null) |
| **Take Upstream** (takeUpstreamMutation) | Delegates to sync or deploy based on scope | Dependent on above mutations |
| **Keep Local** (keepLocalMutation) | `Promise.resolve()` - no-op | Not implemented (line 358-361) |
| **Batch Actions** (handleApplyActions) | Toast: "Batch actions not yet implemented" | Not implemented (line 405) |
| **Push to Collection** | Toast: "Coming Soon" | Not implemented (line 483, 519) |

### Backend Sync Endpoint Concern

The sync mutation sends an empty body to `POST /artifacts/{id}/sync`. The backend `/sync` endpoint behavior needs verification -- if it expects `project_path` to distinguish between upstream sync vs project sync, the empty body may cause unexpected behavior.

---

## Comparison: Working vs Broken Scenarios

### Working (Verified in Browser)

| Scenario | Page | Result |
|----------|------|--------|
| GitHub-origin artifact (e.g., `3d-graphics`) on `/manage` | Source vs Collection | Shows "All Synced" with diff viewer |
| Any artifact on `/projects/{ID}` with project context | Collection vs Project | Shows diff data |

### Broken (Verified in Browser)

| Scenario | Page | Result | Root Cause |
|----------|------|--------|------------|
| Marketplace-origin artifact (e.g., `codex`) on `/manage` | Source vs Collection | "No comparison data" + 400 errors | Issue 1 |
| Local-only artifact on `/manage` | Any scope | "No comparison data" | Issue 2 (no projectPath) + no source |
| Any artifact on `/manage` | Collection vs Project | "No comparison data" | Issue 2 (projectPath always null) |
| Any artifact on `/manage` | Source vs Project | "No comparison data" | Issues 1+2 combined |

---

## Files Involved

### Frontend

| File | Lines | Role |
|------|-------|------|
| `web/components/sync-status/sync-status-tab.tsx` | 98-104, 205, 238-239, 254-256 | Source validation, query enablement |
| `web/components/sync-status/comparison-selector.tsx` | 60-70 | Scope option disabling |
| `web/components/manage/artifact-operations-modal.tsx` | 1185-1191 | /manage modal sync tab (missing projectPath) |
| `web/components/entity/unified-entity-modal.tsx` | 2111-2116, 619-622 | /projects modal sync tab (has projectPath) |
| `web/app/manage/page.tsx` | 460-467, 495 | Modal invocation, lifecycle provider |
| `web/app/projects/[id]/page.tsx` | 322, 554-559 | Project lifecycle provider |

### Backend

| File | Lines | Role |
|------|-------|------|
| `api/routers/artifacts.py` | 4027-4246 | upstream-diff endpoint (origin check at 4160) |
| `api/routers/artifacts.py` | 3668-3990 | diff endpoint (requires project_path) |
| `api/routers/context_sync.py` | 39-475 | pull/push/status/resolve endpoints |

---

## Recommended Fix Priority

1. **Fix frontend source validation** (Issue 1) - Align `hasValidUpstreamSource()` with backend by checking `entity.origin` and `entity.upstream`, preventing unnecessary 400 errors
2. **Add project context to /manage sync tab** (Issue 2) - Add project selector or derive from deployment data so collection-vs-project diffs work
3. **Implement missing mutations** (Issue 4) - Wire up keep-local, push-to-collection, and batch actions
4. **Consider modal unification** (Issue 3) - Longer-term: evaluate whether the two modal systems should converge

---

## Appendix: API Endpoint Map for Sync/Diff

| Endpoint | Method | Purpose | Required Params |
|----------|--------|---------|----------------|
| `/artifacts/{id}/upstream-diff` | GET | Source vs Collection diff | `collection` (optional) |
| `/artifacts/{id}/diff` | GET | Collection vs Project diff | `project_path` (required) |
| `/artifacts/{id}/sync` | POST | Pull from upstream source | Body varies |
| `/artifacts/{id}/deploy` | POST | Deploy to project | `project_path`, `overwrite` |
| `/context-sync/status` | GET | Sync status check | `project_path` (required) |
| `/context-sync/pull` | POST | Pull project changes to collection | `project_path`, `entity_ids` |
| `/context-sync/push` | POST | Push collection to project | `project_path`, `entity_ids`, `overwrite` |
| `/context-sync/resolve` | POST | Resolve conflicts | `entity_id`, `resolution`, `merged_content` |
| `/merge/analyze` | POST | Three-way merge analysis | snapshot IDs |
