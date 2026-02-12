---
title: Deployment Data Write-Through Refactor
type: implementation_plan
status: completed
version: 1
created: 2026-02-11
prd: null
estimated_effort: 1-2 sessions
tags:
- deployment
- cache
- data-flow
- refactor
---

# Deployment Data Write-Through Refactor

## Context

The `/manage` page was recently switched from `/artifacts` to `/user-collections/default/artifacts` as a workaround because `/artifacts` doesn't return deployment data. This crosses semantic boundaries — `/user-collections` is for collection-scoped data, not general artifact browsing.

**Root causes:**
1. `deployments_json` on `CollectionArtifact` is ONLY populated at startup by `populate_collection_artifact_metadata()` via filesystem scan
2. `refresh_single_artifact_cache()` explicitly sets `deployments_json: None` (line 137), wiping deployment data on every per-artifact cache refresh
3. Deploy/undeploy operations don't update the DB column
4. The `/artifacts` endpoint's `ArtifactResponse` schema has no deployments field

**Outcome:** After this refactor, the `/artifacts` endpoint returns deployment data from DB cache, kept current via write-through on deploy/undeploy/import. The manage page reverts to the correct endpoint.

---

## Phase 1: Backend — Write-Through Deployment Cache (Core Fix)

### TASK-1.1: Create surgical deployment cache helpers
**File:** `skillmeat/api/services/artifact_cache_service.py`
**Agent:** python-backend-engineer

Create two functions:
- `add_deployment_to_cache(session, artifact_id, project_path, project_name, deployed_at, content_hash=None, deployment_profile_id=None, local_modifications=False, platform=None, collection_id="default")` — reads current `deployments_json`, appends new entry (or updates if project_path+profile match), writes back
- `remove_deployment_from_cache(session, artifact_id, project_path, collection_id="default", profile_id=None)` — reads current `deployments_json`, removes matching entry, writes back

These are O(1) surgical updates — no filesystem scan needed.

### TASK-1.2: Fix `refresh_single_artifact_cache()` to preserve deployments
**File:** `skillmeat/api/services/artifact_cache_service.py` (line 137)
**Agent:** python-backend-engineer

Remove `"deployments_json": None` from the metadata dict. Since `create_or_update_collection_artifact()` uses `setattr` for each key, omitting the key preserves the existing DB value. For new rows, it defaults to `None` (correct — populated on first deploy).

### TASK-1.3: Wire deploy endpoint to update DB
**File:** `skillmeat/api/routers/deployments.py` (~line 258, after successful deploy)
**Agent:** python-backend-engineer

After `deployment_mgr.deploy_artifacts()` succeeds, call `add_deployment_to_cache()` with data from the returned `Deployment` object. Wrap in try/except — cache failure should not block the deploy.

### TASK-1.4: Wire undeploy endpoint to update DB
**File:** `skillmeat/api/routers/deployments.py` (~line 360, after successful undeploy)
**Agent:** python-backend-engineer

After `deployment_mgr.undeploy()` succeeds, call `remove_deployment_from_cache()`. Same error handling pattern as 1.3.

**Parallelism:** TASK-1.1 first, then 1.2 + 1.3 + 1.4 in parallel.

---

## Phase 2: Backend — Add Deployments to `/artifacts` Response

### TASK-2.1: Enrich `DeploymentSummary` schema
**File:** `skillmeat/api/schemas/deployments.py`
**Agent:** python-backend-engineer

Add optional fields to `DeploymentSummary`:
- `content_hash: Optional[str]` — version deployed
- `deployment_profile_id: Optional[str]` — which profile
- `local_modifications: Optional[bool]` — drift flag
- `platform: Optional[str]` — target platform

All optional with `default=None` for backward compatibility.

### TASK-2.2: Add `deployments` field to `ArtifactResponse`
**File:** `skillmeat/api/schemas/artifacts.py` (~line 318)
**Agent:** python-backend-engineer

Add: `deployments: Optional[List[DeploymentSummary]] = None`

### TASK-2.3: Move `parse_deployments()` to shared location
**From:** `skillmeat/api/routers/user_collections.py` (lines 128-175)
**To:** `skillmeat/api/services/artifact_cache_service.py`
**Agent:** python-backend-engineer

Move function, update to handle new enriched fields, update imports in both `user_collections.py` and `artifacts.py`.

### TASK-2.4: Populate deployments in `/artifacts` list endpoint
**File:** `skillmeat/api/routers/artifacts.py` (~lines 1928-1973)
**Agent:** python-backend-engineer

1. Add `deployments_json` to the existing `CollectionArtifact` DB query (where `source_lookup` is built)
2. Build `deployments_lookup` dict via `parse_deployments()`
3. Add `deployments` param to `artifact_to_response()` and pass it through
4. Update `artifact_to_response()` signature (~line 517) to accept and set `deployments`

**Parallelism:** 2.1 + 2.2 parallel, then 2.3, then 2.4.

---

## Phase 3: Frontend — Revert to `/artifacts` Endpoint

### TASK-3.1: Revert `fetchCollectionEntities` endpoint
**File:** `skillmeat/web/hooks/useEntityLifecycle.tsx` (line ~626)
**Agent:** ui-engineer-enhanced

Change from `/user-collections/${collectionPath}/artifacts?...` back to `/artifacts?...`. Verify the entity mapper handles the `ArtifactResponse` shape.

### TASK-3.2: Update frontend `DeploymentSummary` type
**File:** `skillmeat/web/types/artifact.ts`
**Agent:** ui-engineer-enhanced

Add optional enrichment fields: `content_hash`, `deployment_profile_id`, `local_modifications`, `platform`.

### TASK-3.3: Verify query key invalidation
**Files:** `skillmeat/web/hooks/useDeploy.ts`, deploy/undeploy mutation hooks
**Agent:** ui-engineer-enhanced

Ensure deploy/undeploy mutations invalidate `['artifacts']` query key per the invalidation graph.

**Parallelism:** All 3 tasks in parallel.

---

## Phase 4: Handle Local Discovery + Import Path

### TASK-4.1: Record deployment on project artifact import
**File:** `skillmeat/api/routers/artifacts.py` — `POST /artifacts/import` endpoint
**Agent:** python-backend-engineer

When an artifact discovered in a project is imported to collection, it's already deployed there. After import + cache refresh, call `add_deployment_to_cache()` with the source project path.

---

## Phase 5: Documentation & Context Updates

### TASK-5.1: Create deployment data flow context doc
**File:** `.claude/context/key-context/deployment-data-flows.md`
**Agent:** documentation-writer (Haiku)

Document:
- Deployment lifecycle: deploy → FS write → DB write-through → frontend cache invalidation
- Undeploy lifecycle: same pattern in reverse
- Import-from-project: discovery → import → record deployment
- Startup sync: `populate_collection_artifact_metadata()` full filesystem scan
- Which endpoints return deployment data and why
- `deployments_json` schema with all fields
- Write-through vs full-scan tradeoffs

### TASK-5.2: Regenerate OpenAPI spec
Reflect the new `deployments` field on `ArtifactResponse` and enriched `DeploymentSummary`.

---

## Enriched DeploymentSummary Schema (Final)

```python
class DeploymentSummary(BaseModel):
    project_path: str                              # Absolute path to project
    project_name: str                              # Human-readable name
    deployed_at: datetime                          # When deployed
    content_hash: Optional[str] = None             # SHA-256 at deploy time
    deployment_profile_id: Optional[str] = None    # "claude_code", "codex", etc.
    local_modifications: Optional[bool] = None     # Drift detected?
    platform: Optional[str] = None                 # Target platform
```

---

## Deployment Data Flow Report

### Current Flow (Pre-Refactor)

```
DEPLOY:
  CLI/API → DeploymentManager.deploy_artifacts()
    → FilesystemManager.copy_artifact() (copies files)
    → DeploymentTracker.record_deployment() (writes .skillmeat-deployed.toml)
    → refresh_single_artifact_cache() → sets deployments_json = None ← BUG

UNDEPLOY:
  CLI/API → DeploymentManager.undeploy()
    → FilesystemManager.remove_artifact() (removes files)
    → DeploymentTracker.remove_deployment() (updates TOML)
    → NO DB update ← BUG

STARTUP:
  lifespan() → populate_collection_artifact_metadata()
    → DeploymentManager.list_deployments(project_path=CWD)
    → Groups by artifact_name → builds JSON array
    → SQLAlchemy UPDATE → sets deployments_json ← ONLY POPULATION POINT

LOCAL DISCOVERY + IMPORT:
  POST /artifacts/discover/project/{id} → scans .claude/ directory
  POST /artifacts/import → bulk import to collection
    → refresh_single_artifact_cache() → sets deployments_json = None ← BUG
    → NO deployment recorded for source project ← GAP
```

### Target Flow (Post-Refactor)

```
DEPLOY:
  CLI/API → DeploymentManager.deploy_artifacts()
    → FilesystemManager.copy_artifact()
    → DeploymentTracker.record_deployment() (FS write)
    → refresh_single_artifact_cache() (preserves deployments_json) ← FIXED
    → add_deployment_to_cache() (DB write-through) ← NEW
    → Frontend: invalidate ['artifacts', 'deployments']

UNDEPLOY:
  CLI/API → DeploymentManager.undeploy()
    → FilesystemManager.remove_artifact()
    → DeploymentTracker.remove_deployment() (FS write)
    → remove_deployment_from_cache() (DB write-through) ← NEW
    → Frontend: invalidate ['artifacts', 'deployments']

STARTUP:
  lifespan() → populate_collection_artifact_metadata()
    → Full filesystem scan (baseline, catches all projects)
    → Same as before — this is the authoritative resync

LOCAL DISCOVERY + IMPORT:
  POST /artifacts/import → bulk import to collection
    → refresh_single_artifact_cache() (preserves deployments_json) ← FIXED
    → add_deployment_to_cache() (records source project) ← NEW

QUERY:
  GET /artifacts → ArtifactResponse now includes deployments ← NEW
  GET /user-collections/{id}/artifacts → ArtifactSummary (unchanged)
  Both read from same deployments_json column
```

### Version Tracking Chain

```
Upstream Source (GitHub)
  ↓ resolved_sha, resolved_version
Collection Lock File (collection.lock)
  ↓ content_hash (SHA-256 of collection copy)
Deployment Record (.skillmeat-deployed.toml)
  ↓ content_hash (SHA-256 at deploy time)
  ↓ version_lineage (parent chain)
DB Cache (deployments_json on CollectionArtifact)
  ↓ content_hash, local_modifications, platform
Frontend (/manage page via /artifacts endpoint)
```

### Key Files Reference

| Component | File | Purpose |
|-----------|------|---------|
| DB model | `skillmeat/cache/models.py:968-1044` | `CollectionArtifact.deployments_json` |
| Cache service | `skillmeat/api/services/artifact_cache_service.py` | `refresh_single_artifact_cache()`, new helpers |
| Deploy API | `skillmeat/api/routers/deployments.py` | Deploy/undeploy endpoints |
| Artifacts API | `skillmeat/api/routers/artifacts.py` | `/artifacts` list endpoint |
| User collections | `skillmeat/api/routers/user_collections.py` | `parse_deployments()`, startup population |
| Deploy core | `skillmeat/core/deployment.py` | `DeploymentManager`, `Deployment` dataclass |
| Deploy tracker | `skillmeat/storage/deployment.py` | FS read/write for `.skillmeat-deployed.toml` |
| Schemas | `skillmeat/api/schemas/deployments.py` | `DeploymentSummary` |
| Frontend hook | `skillmeat/web/hooks/useEntityLifecycle.tsx` | Fetch endpoint selection |
| Frontend types | `skillmeat/web/types/artifact.ts` | `DeploymentSummary` TS type |

---

## Verification

1. **Backend:** `pytest tests/ -k deployment`
2. **Backend:** `black skillmeat && flake8 skillmeat --select=E9,F63,F7,F82`
3. **Frontend:** `cd skillmeat/web && pnpm type-check && pnpm build`
4. **Frontend:** `pnpm test -- --testPathPattern="manage"`
5. **E2E:** Start dev servers, deploy artifact, verify `/manage` shows data, undeploy and verify removal
6. **OpenAPI:** Verify `skillmeat/api/openapi.json` includes `deployments` on `ArtifactResponse`

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Schema backward compat | All new DeploymentSummary fields are Optional with None defaults |
| `parse_deployments()` consumers | Shared function handles both old and new JSON shapes |
| Multi-project tracking gaps | Startup full-scan catches everything; write-through keeps it current |
| Deploy/undeploy cache failure | Wrapped in try/except — cache miss degrades gracefully, next startup rescans |
| `/user-collections` endpoint | Unchanged — continues to work via same `parse_deployments()` |
