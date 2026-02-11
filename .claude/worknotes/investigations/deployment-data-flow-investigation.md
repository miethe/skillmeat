# Deployment Data Flow Investigation: /manage Page

**Investigation Date**: 2026-02-11
**Issue**: Only a subset of ~120 deployed artifacts showing on /manage page with deployments visible on artifact cards

## Executive Summary

The deployment data pipeline consists of 5 distinct layers with clear data flow. The issue appears to be related to how deployment data is **queried and paginated** at the API layer, rather than how it's stored. The investigation reveals that:

1. **API endpoint** (`/api/v1/artifacts`) correctly queries deployments from the DB cache
2. **DB cache** (`CollectionArtifact.deployments_json`) properly stores deployment data
3. **Mapper** (entity-mapper) correctly maps API responses to frontend Artifact objects
4. **Hook** (`useEntityLifecycle`) properly fetches all pages with pagination
5. **Component** (artifact-operations-card) correctly displays `artifact.deployments`

**Root cause area**: The pagination/filtering at the API level OR the paginated fetch may be filtering artifacts unexpectedly.

---

## Data Pipeline Architecture

### Layer 1: API Endpoint (Backend)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py:1756`

**Endpoint**: `GET /api/v1/artifacts`

The endpoint performs these critical operations:

```python
# Lines 1977-2005: Query deployments from DB cache
artifact_ids = [f"{a.type.value}:{a.name}" for a in page_artifacts]
deployments_lookup: Dict[str, List[DeploymentSummary]] = {}

db_rows = (
    db_session.query(
        CollectionArtifact.artifact_id,
        CollectionArtifact.source,
        CollectionArtifact.deployments_json,
    )
    .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
    .all()
)
for row in db_rows:
    parsed = parse_deployments(row.deployments_json)
    if parsed:
        deployments_lookup[row.artifact_id] = parsed
```

**Key observations**:
- Deployments are queried from `CollectionArtifact.deployments_json` in the DB
- The query is **scoped to page_artifacts only** (line 1978 creates artifact_ids from paginated results)
- Each row is parsed using `parse_deployments()` helper function
- Results stored in `deployments_lookup` dict keyed by artifact_id

**Important**: The deployment query happens **AFTER pagination** (line 1940: `page_artifacts = artifacts[start_idx:end_idx]`)

---

### Layer 2: Database Cache Model

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py:968`

**Table**: `collection_artifacts`

**Deployment Storage Field**:
```python
deployments_json: Mapped[Optional[str]] = mapped_column(
    Text, nullable=True
)  # JSON array of deployment paths
```

**Deployment Format** (stored as JSON string):
```json
[
  {
    "project_path": "/home/user/project1",
    "project_name": "project1",
    "deployed_at": "2024-02-11T12:34:56Z",
    "content_hash": "abc123...",
    "deployment_profile_id": "profile_1",
    "local_modifications": false,
    "platform": "linux"
  }
]
```

**Cache Sync Mechanism**:
- Written via `add_deployment_to_cache()` in `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/services/artifact_cache_service.py:580`
- Called from deployment router after successful deploy operation (line 266)

---

### Layer 3: Parse Deployments Helper

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/services/artifact_cache_service.py:517`

```python
def parse_deployments(deployments_json: Optional[str]) -> Optional[list[DeploymentSummary]]:
    """Parse deployments_json field from CollectionArtifact into DeploymentSummary list."""
    if not deployments_json:
        return None  # Empty deployments_json returns None (not [])

    try:
        deployments_data = json.loads(deployments_json)
        if not deployments_data or not isinstance(deployments_data, list):
            return None

        # Parse each deployment dict into DeploymentSummary
        deployments = []
        for dep in deployments_data:
            deployments.append(DeploymentSummary(...))

        return deployments if deployments else None
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"Failed to parse deployments_json: {e}")
        return None
```

**Important**: Returns `None` if `deployments_json` is empty or unparseable (not empty list).

---

### Layer 4: Frontend Hook

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useEntityLifecycle.tsx:581`

**Function**: `fetchCollectionEntities()`

```typescript
// Lines 612-637: Paginated fetch with cursor-based pagination
let allItems: ApiArtifactResponse[] = [];
let cursor: string | null = null;
let hasNextPage = true;

while (hasNextPage) {
    const params = new URLSearchParams({ limit: '100' });
    if (typeFilter) {
        params.set('artifact_type', typeFilter);
    }
    if (cursor) {
        params.set('after', cursor);
    }

    const response = await apiRequest<ArtifactListResponse>(`/artifacts?${params.toString()}`);
    allItems = [...allItems, ...(response.items as ApiArtifactResponse[])];

    hasNextPage = response.page_info?.has_next_page ?? false;
    cursor = response.page_info?.end_cursor ?? null;
}

return processItems(allItems);
```

**Key observations**:
- Hook implements **cursor-based pagination** with limit=100 per page
- Fetches **all pages** automatically (while loop continues until `has_next_page=false`)
- Items accumulated in `allItems` array across all pages
- Items then mapped to Entity objects with `mapArtifactsToEntities()`

**This is correct**: Hook properly handles pagination and accumulates all artifacts.

---

### Layer 5: Entity Mapper

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/entity-mapper.ts:410`

**Function**: `mapArtifactToEntity()`

```typescript
// Lines 410-411: Map deployments from API response
const deployments = mapDeployments(artifact);

function mapDeployments(artifact: ApiArtifactResponse): DeploymentSummary[] | null {
    if (!artifact.deployments) {
        return null;
    }

    if (artifact.deployments.length === 0) {
        return [];
    }

    return artifact.deployments.map((d) => ({
        project_path: d.project_path,
        project_name: d.project_name,
        deployed_at: d.deployed_at,
    }));
}

// Line 481: Include deployments in entity object
...(deployments !== null && { deployments }), // Include if present (even if empty array)
```

**Important**:
- Deployments mapped directly from API response `artifact.deployments`
- If `artifact.deployments` is `null`, deployments field not included in Entity
- If `artifact.deployments` is `[]` (empty array), deployments field IS included with empty array

---

### Layer 6: Frontend Component

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/manage/artifact-operations-card.tsx:252`

```typescript
// Line 252: Check for deployments
const hasDeployments = (artifact.deployments?.length ?? 0) > 0;

// Line 426-432: Render DeploymentBadgeStack with deployments array
<DeploymentBadgeStack
    deployments={artifact.deployments || []}
    maxBadges={3}
    onBadgeClick={(_deployment) => {
        onOpenWithTab ? onOpenWithTab('deployments') : onClick();
    }}
/>
```

**Component correctly**:
- Checks if deployments array exists and has items
- Passes `artifact.deployments || []` to DeploymentBadgeStack
- Only renders if `hasDeployments === true`

---

## Data Flow Diagram

```
┌─────────────────────────────────────┐
│ Deployment Operation (Deploy Route) │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────┐
│ Write to DB Cache                           │
│ add_deployment_to_cache()                   │
│ → Update CollectionArtifact.deployments_json│
└──────────────┬──────────────────────────────┘
               │
               ↓
┌────────────────────────────────────────────────┐
│ Frontend: useEntityLifecycle Hook              │
│ GET /api/v1/artifacts (paginated, limit=100)  │
│ Fetches all pages until has_next_page=false   │
└────────────────────┬─────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ API: list_artifacts()      │
        │ 1. Load all artifacts      │
        │ 2. Apply filters/search    │
        │ 3. Paginate (limit=100)    │ ← KEY: Pagination happens here
        │ 4. Query DB for deployments│
        │ 5. Parse deployments_json  │
        │ 6. Return paginated response
        └────────────┬────────────────┘
                     │
                     ↓
┌──────────────────────────────────────┐
│ Entity Mapper                        │
│ mapArtifactsToEntities()             │
│ Maps API response to Entity objects  │
│ Includes deployments array           │
└────────────────┬─────────────────────┘
                 │
                 ↓
┌──────────────────────────────────────┐
│ Frontend: Artifact Component         │
│ artifact-operations-card.tsx         │
│ Displays artifact.deployments[]      │
│ in DeploymentBadgeStack              │
└──────────────────────────────────────┘
```

---

## Identified Issues

### Issue 1: Potential Deployment Data Loss During Cache Refresh

**Location**: API layer - deployment cache update

When a full cache refresh occurs (e.g., at server startup), the `refresh_single_artifact_cache()` function may **overwrite** the `deployments_json` field if the filesystem artifact doesn't contain deployment metadata.

**File**: `skillmeat/cache/refresh.py` (needs investigation)

**Risk**: If cache refresh happens after a deployment operation, deployment data could be lost if not properly preserved.

---

### Issue 2: Partial Pagination of Deployments Query

**Location**: API endpoint `/api/v1/artifacts` (line 1978-2005)

The deployments are queried **ONLY for the current page** of artifacts:

```python
# Page_artifacts is ALREADY paginated (line 1940)
artifact_ids = [f"{a.type.value}:{a.name}" for a in page_artifacts]
deployments_lookup = {}

# Query only includes artifacts on current page
db_rows = db_session.query(...)
    .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
```

**This is correct by design**, but if there are issues with the artifact list itself being incomplete, deployments will also appear incomplete.

---

### Issue 3: Artifact List Filtering/Sorting

**Location**: API endpoint `list_artifacts()` (lines 1854-1922)

The artifact list is built from multiple collections and filtered by type, tags, and search query **before** pagination:

```python
# Lines 1854-1882: Get all artifacts from all collections
all_artifacts = []
for coll_name in collection_mgr.list_collections():
    coll_artifacts = artifact_mgr.list_artifacts(...)
    all_artifacts.extend(coll_artifacts)

# Lines 1938-1940: Sort and paginate
artifacts = sorted(artifacts, key=lambda a: (a.type.value, a.name))
page_artifacts = artifacts[start_idx:end_idx]
```

**If artifact list is incomplete here, deployments will also be incomplete.**

---

## Diagnostic Queries

To investigate whether deployments are actually stored in the DB, run:

```sql
-- Count all artifacts with deployment data
SELECT COUNT(*) as artifacts_with_deployments
FROM collection_artifacts
WHERE deployments_json IS NOT NULL
  AND deployments_json != '[]'
  AND deployments_json != 'null';

-- Count total artifacts
SELECT COUNT(*) as total_artifacts
FROM collection_artifacts;

-- Sample artifacts with deployments
SELECT
    artifact_id,
    length(deployments_json) as json_size,
    SUBSTR(deployments_json, 1, 100) as json_preview
FROM collection_artifacts
WHERE deployments_json IS NOT NULL
  AND deployments_json != '[]'
LIMIT 10;
```

---

## Recommended Investigations

### 1. Check DB Cache Contents

Use the diagnostic queries above to determine:
- How many artifacts have deployment data in `deployments_json`?
- Is the deployment data format correct JSON?
- Are all 120 artifacts with deployments actually in the database?

**Command**: Access SQLite database at `~/.skillmeat/cache.db` (or configured path)

### 2. Check Artifact List Response

Test the API endpoint directly:

```bash
curl -s "http://localhost:8080/api/v1/artifacts?limit=100" | jq '.items | length'

# Count items with deployments
curl -s "http://localhost:8080/api/v1/artifacts?limit=100" | jq '[.items[] | select(.deployments != null) | .deployments | length] | length'

# Get second page
curl -s "http://localhost:8080/api/v1/artifacts?limit=100&after=$(curl -s 'http://localhost:8080/api/v1/artifacts?limit=100' | jq -r '.page_info.end_cursor')" | jq '.items | length'
```

### 3. Check Hook Pagination

Add logging to `useEntityLifecycle.tsx` to trace pagination:

```typescript
const response = await apiRequest<ArtifactListResponse>(`/artifacts?${params.toString()}`);
console.log('Page result:', {
    itemsOnPage: response.items.length,
    hasNextPage: response.page_info?.has_next_page,
    totalCollected: allItems.length,
});
```

### 4. Check Cache Refresh Logic

Investigate if deployments are being cleared/overwritten during:
- Server startup (lifespan)
- Manual cache refresh endpoint
- Single artifact refresh

---

## Type Definitions

### DeploymentSummary (API Response)

```typescript
interface DeploymentSummary {
    project_path: string;
    project_name: string;
    deployed_at: string; // ISO 8601
    content_hash?: string;
    deployment_profile_id?: string;
    local_modifications?: boolean;
    platform?: string;
}
```

### Artifact Type (Frontend)

```typescript
interface Artifact {
    id: string;
    name: string;
    type: 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
    deployments?: DeploymentSummary[] | null; // ← The field in question
    // ... other fields
}
```

---

## Filtering Applied Before Pagination

The following filters are applied **before** artifacts are paginated (lines 1854-1920):

1. **Collection filter** (optional): Scope to single collection
2. **Type filter** (optional): Filter by artifact type
3. **Tag filter** (optional): Filter by tags
4. **Tools filter** (optional): Filter by tools
5. **Unlinked references filter** (optional): Filter by unlinked status
6. **Import ID filter** (optional): Filter by marketplace import batch
7. **Search query filter** (client-side in hook, not API)

If any of these filters are incorrectly applied or artifacts are excluded here, they won't appear on the manage page at all (with or without deployments).

---

## Key Files Reference

| Layer | File | Key Function/Component |
|-------|------|------------------------|
| API Router | `skillmeat/api/routers/artifacts.py:1756` | `list_artifacts()` |
| API Service | `skillmeat/api/services/artifact_cache_service.py:517` | `parse_deployments()` |
| DB Model | `skillmeat/cache/models.py:968` | `CollectionArtifact` |
| Frontend Hook | `skillmeat/web/hooks/useEntityLifecycle.tsx:581` | `fetchCollectionEntities()` |
| Entity Mapper | `skillmeat/web/lib/api/entity-mapper.ts:295` | `mapDeployments()` |
| Component | `skillmeat/web/components/manage/artifact-operations-card.tsx:252` | `ArtifactOperationsCard` |

---

## Next Steps

1. **Run diagnostic SQL queries** to determine if deployments are actually in the DB
2. **Test API endpoint directly** to see how many artifacts with deployments are returned
3. **Add logging to hook** to trace pagination and artifact accumulation
4. **Check cache refresh logic** to ensure deployments aren't being cleared
5. **Verify artifact list** is returning all 120+ artifacts before filtering

The data pipeline itself is well-structured; the issue is likely in one of:
- DB cache not containing all deployment data
- Artifact list being filtered/incomplete at the API level
- Cache refresh clearing deployment data
