# Deployment Data Flows Context

Agent context for deployment lifecycle, cache sync patterns, and API response generation.

**Updated**: 2026-02-25

## Quick Reference

| Operation | FS Write | DB Cache | Frontend Invalidation |
|-----------|----------|----------|----------------------|
| **Deploy** | `DeploymentManager.deploy()` → `.claude/` | `add_deployment_to_cache()` | `['artifacts', 'entities', 'deployments']` |
| **Undeploy** | `DeploymentManager.undeploy()` → remove files | `remove_deployment_from_cache()` | `['artifacts', 'entities', 'deployments']` |
| **Startup** | N/A | `populate_collection_artifact_metadata()` full scan | N/A |

---

## Deployment Lifecycle

### 1. Deploy Workflow

**Trigger**: `POST /api/v1/deploy`
**Handler**: `skillmeat/api/routers/deployments.py`

```
1. Validate artifact exists (collection_mgr)
2. Resolve project path (project_registry)
3. Write to filesystem:
   - DeploymentManager.deploy(artifact, project_path, dest_path, profile_id)
   - Creates .claude/skills/{name}/, .claude/commands/{name}/, etc.
   - Records metadata in .claude/deployment-manifest.toml
4. Sync to DB cache:
   - add_deployment_to_cache(artifact_id, project_path, project_name, deployed_at, ...)
   - Appends entry to CollectionArtifact.deployments_json JSON array
   - If entry with same project_path + profile_id exists, updates in-place
5. Invalidate frontend caches:
   - queryClient.invalidateQueries(['artifacts', 'entities', 'deployments'])
```

**Surgical Update** (no full cache refresh required):
```python
add_deployment_to_cache(
    session=session,
    artifact_id="skill:pdf",
    project_path="/Users/miethe/dev/project",
    project_name="my-project",
    deployed_at=datetime.utcnow(),
    content_hash=sha256_of_deployed_content,
    deployment_profile_id="codex-default",
    local_modifications=False,
    platform="claude-code",
    collection_id="default",
)
# Returns: bool (success/failure)
# Side effect: Updates CollectionArtifact.deployments_json in-place (flush not commit)
```

### 2. Undeploy Workflow

**Trigger**: `POST /api/v1/undeploy`
**Handler**: `skillmeat/api/routers/deployments.py`

```
1. Resolve project path & artifact
2. Remove from filesystem:
   - DeploymentManager.undeploy(artifact, project_path, profile_id)
   - Deletes .claude/skills/{name}/ recursively
   - Updates .claude/deployment-manifest.toml
3. Sync to DB cache:
   - remove_deployment_from_cache(artifact_id, project_path, profile_id)
   - Filters out entries matching project_path + profile_id from JSON array
4. Invalidate frontend caches:
   - queryClient.invalidateQueries(['artifacts', 'entities', 'deployments'])
```

**Surgical Removal**:
```python
remove_deployment_from_cache(
    session=session,
    artifact_id="skill:pdf",
    project_path="/Users/miethe/dev/project",
    collection_id="default",
    profile_id="codex-default",  # Optional; None removes all profiles for project
)
# Returns: bool (success/failure)
# Side effect: Removes matching entries from JSON array (flush not commit)
```

### 3. Import-from-Project Workflow

**Trigger**: `POST /api/v1/user-collections/{collection_id}/import`
**Handler**: `skillmeat/api/routers/user_collections.py`

```
1. Discovery phase:
   - Scan .claude/ directory for deployed artifacts
   - Match against local filesystem & GitHub
   - Build ImportEntry objects
2. Record deployments:
   - populate_collection_artifact_from_import(session, artifact_mgr, collection_id, entry)
   - Reads artifact metadata from filesystem
   - Creates CollectionArtifact row with deployments_json initialized
3. Invalidate frontend caches:
   - queryClient.invalidateQueries(['artifacts', 'entities'])
```

---

## Startup Cache Sync

**Trigger**: API server lifespan (server.py `lifespan()` function)

```
1. Baseline population:
   - populate_collection_artifact_metadata() reads ~/.skillmeat/collection/ recursively
   - For each artifact found, upserts CollectionArtifact row
   - Scans deployment manifests (.claude/deployment-manifest.toml)
   - Initializes deployments_json from manifest data
2. State after startup:
   - DB cache is authoritative view of collection artifacts
   - Web API serves all artifact/deployment data from DB cache
```

---

## Deployment JSON Schema

**Column**: `CollectionArtifact.deployments_json` (TEXT, nullable)

**Format**: JSON array of deployment objects

```json
[
  {
    "project_path": "/Users/miethe/dev/homelab/development/skillmeat/.claude",
    "project_name": "SkillMeat",
    "deployed_at": "2025-02-11T10:30:00+00:00",
    "content_hash": "abc123def456...",
    "deployment_profile_id": "codex-default",
    "local_modifications": false,
    "platform": "claude-code"
  },
  {
    "project_path": "/Users/miethe/dev/other-project/.claude",
    "project_name": "Other Project",
    "deployed_at": "2025-02-10T15:00:00+00:00",
    "content_hash": null,
    "deployment_profile_id": null,
    "local_modifications": true,
    "platform": "claude-code"
  }
]
```

**Field Descriptions**:
- `project_path` (str, required): Absolute filesystem path to project
- `project_name` (str, required): Human-readable project name
- `deployed_at` (ISO 8601 string, required): Deployment timestamp
- `content_hash` (str|null, optional): SHA-256 hash of deployed content
- `deployment_profile_id` (str|null, optional): Profile identifier (e.g., "codex-default")
- `local_modifications` (bool, optional): Whether local modifications exist post-deploy
- `platform` (str|null, optional): Platform identifier (e.g., "claude-code")

**Upsert Logic** (in `add_deployment_to_cache`):
```
If entry with matching (project_path, deployment_profile_id) exists:
  → Update in-place (preserves ordering, exact match)
Else:
  → Append new entry to array
```

---

## API Response Generation

### GET /artifacts

**Response Schema**: `ArtifactResponse` (includes `deployments` field)

```python
# artifacts.py: _convert_artifact_to_response()

# 1. Query CollectionArtifact.deployments_json
deployments_json = assoc.deployments_json

# 2. Parse to DeploymentSummary list
deployments = parse_deployments(deployments_json)
# Returns: List[DeploymentSummary] | None

# 3. Include in response
return ArtifactResponse(
    ...,
    deployments=deployments,  # List of DeploymentSummary objects
)
```

### GET /user-collections/{id}/artifacts

**Response Schema**: `ArtifactSummary` (includes `deployments` field)

```python
# user_collections.py: list_artifacts_in_collection()

# 1. Query CollectionArtifact for artifact
assoc = session.query(CollectionArtifact).filter_by(...).first()

# 2. Parse deployments from cache
deployments = parse_deployments(assoc.deployments_json)

# 3. Build ArtifactSummary with deployments
artifact_summary = ArtifactSummary(
    ...,
    deployments=deployments,
)
```

### Parse Deployments Utility

**File**: `skillmeat/api/services/artifact_cache_service.py`

```python
def parse_deployments(deployments_json: Optional[str]) -> Optional[List[DeploymentSummary]]:
    """
    Convert JSON string to DeploymentSummary objects.

    - Handles both old-format (project_path, project_name, deployed_at only)
      and new-format (with content_hash, profile_id, local_modifications, platform)
    - Converts deployed_at ISO strings to datetime objects
    - Skips invalid entries, logs debug messages
    - Returns None if empty/unparseable
    """
```

---

## Write-Through vs Full Scan

| Pattern | When | Scope | Commit? |
|---------|------|-------|---------|
| **Write-Through** (surgical) | After deploy/undeploy | Single artifact's deployments_json | `session.flush()` only, caller commits |
| **Full Scan** (baseline) | Server startup | All artifacts + deployments | `session.commit()` auto |

**Implication**:
- Deploy/undeploy use `flush()` → transactional grouping with router response
- Startup uses `commit()` → independent baseline population

---

## Endpoint Summary

| Endpoint | Verb | Deployment Change | Cache Pattern |
|----------|------|-------------------|---|
| `/api/v1/deploy` | POST | Add | `add_deployment_to_cache()` |
| `/api/v1/undeploy` | POST | Remove | `remove_deployment_from_cache()` |
| `/api/v1/artifacts` | GET | Read | Query JSON, `parse_deployments()` |
| `/api/v1/user-collections/{id}/artifacts` | GET | Read | Query JSON, `parse_deployments()` |
| `/api/v1/user-collections/{id}/import` | POST | Add + Create | `populate_collection_artifact_from_import()` |

---

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/api/routers/deployments.py` | Deploy/undeploy endpoints |
| `skillmeat/api/routers/artifacts.py` | Artifact CRUD, response generation |
| `skillmeat/api/routers/user_collections.py` | Collection artifact listing |
| `skillmeat/api/services/artifact_cache_service.py` | `add_deployment_to_cache()`, `remove_deployment_from_cache()`, `parse_deployments()` |
| `skillmeat/cache/models.py` | `CollectionArtifact.deployments_json` column definition |
| `skillmeat/api/schemas/deployments.py` | `DeploymentSummary`, `DeployRequest`, `UndeployRequest` |
| `skillmeat/core/deployment.py` | `DeploymentManager` (filesystem ops) |

---

## Common Tasks

### Add a deployment to cache

```python
from skillmeat.api.services.artifact_cache_service import add_deployment_to_cache
from skillmeat.cache.models import get_session

session = get_session()
success = add_deployment_to_cache(
    session=session,
    artifact_id="skill:pdf",
    project_path="/path/to/project/.claude",
    project_name="My Project",
    deployed_at=datetime.utcnow(),
    content_hash="sha256hash",
    deployment_profile_id="codex-default",
    local_modifications=False,
    platform="claude-code",
)
session.commit()  # Caller responsible for commit
```

### Remove a deployment from cache

```python
from skillmeat.api.services.artifact_cache_service import remove_deployment_from_cache

session = get_session()
success = remove_deployment_from_cache(
    session=session,
    artifact_id="skill:pdf",
    project_path="/path/to/project/.claude",
    profile_id="codex-default",
)
session.commit()
```

### Get deployments for an artifact

```python
from skillmeat.api.services.artifact_cache_service import parse_deployments
from skillmeat.cache.models import CollectionArtifact, get_session

session = get_session()
assoc = session.query(CollectionArtifact).filter_by(
    collection_id="default",
    artifact_id="skill:pdf",
).first()

if assoc:
    deployments = parse_deployments(assoc.deployments_json)
    for dep in deployments:
        print(f"Deployed to {dep.project_name} at {dep.deployed_at}")
```

---

## Error Handling

**When adding deployment fails**:
- Log warning → `add_deployment_to_cache()` returns `False`
- Deployment still succeeds on filesystem
- Frontend querying after deploy will see stale cache
- Next cache refresh or explicit `POST /cache/refresh` syncs

**When removing deployment fails**:
- Log warning → `remove_deployment_from_cache()` returns `False`
- Files removed from filesystem
- DB cache becomes inconsistent
- Next cache refresh syncs

**Recovery**: `POST /api/v1/cache/refresh` triggers full rescan and DB sync.

---

## Deployment Sets Data Flow

### Resolution Flow

```
DeploymentSet → resolve members recursively (DFS)
  ├── Direct artifacts → add to result set
  ├── Group members → expand group artifacts → add
  └── Nested set members → recurse (with depth limit)
  → Deduplicate by artifact_uuid
  → Return flat resolved artifact list
```

**Implementation**: `skillmeat/api/services/deployment_sets_service.py::resolve_deployment_set()`

### Batch Deploy Flow

```
POST /api/v1/deployment-sets/{id}/batch-deploy
  ├── Resolve set → flat artifact list
  ├── For each artifact: deploy to target project + profile
  │   ├── Success → record in results
  │   └── Failure → record error, continue (partial failure OK)
  └── Return BatchDeployResult with per-artifact status
```

**Handler**: `skillmeat/api/routers/deployment_sets.py::batch_deploy_set()`

**Response Schema**: `BatchDeployResult` containing:
- `deployment_set_id` (str): Set identifier
- `target_project_id` (str): Target project path
- `results` (List[ArtifactDeploymentResult]): Per-artifact outcomes
  - `artifact_id` (str): Artifact identifier
  - `status` ('success' | 'failed'): Deployment status
  - `error` (str|null): Error message if failed

### Cache Invalidation

**Set CRUD mutations** invalidate:
- `deployment-sets` (list cache)
- `deployment-set-{id}` (detail cache)

**Member mutations** invalidate:
- `deployment-set-{id}` (detail and member list)
- `deployment-set-members-{id}` (member collection)

**Batch deploy** invalidates:
- `deployments` (deployment list)
- `deployment-stats` (analytics)
- `project-{id}` (project artifacts)

### Feature Flag

Deployment Sets feature is gated by environment variable:
- **Gate**: `SKILLMEAT_DEPLOYMENT_SETS_ENABLED` (boolean)
- **Frontend**: `useFeatureFlags()` hook controls sidebar visibility
- **Backend**: All endpoints return 501 Not Implemented when disabled
- **Default**: False (feature in beta)
