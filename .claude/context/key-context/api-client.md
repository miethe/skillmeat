<!-- Path Scope: skillmeat/web/lib/api/**/*.ts -->

# Web API Clients - Inventory

<!-- CODEBASE_GRAPH:API_CLIENTS:START -->
| API Client | File | Endpoints |
| --- | --- | --- |
| <span title="Add artifact to collection">addArtifactToCollection</span> | skillmeat/web/lib/api/collections.ts | POST /api/v1/user-collections/{collectionId}/artifacts |
| <span title="Add artifact to group">addArtifactToGroup</span> | skillmeat/web/lib/api/groups.ts | POST /api/v1/groups/{groupId}/artifacts/{artifactId} |
| <span title="Add tag to artifact">addTagToArtifact</span> | skillmeat/web/lib/api/tags.ts | POST /api/v1/artifacts/{artifactId}/tags/{tagId} |
| <span title="Analyze merge safety between snapshots">analyzeMergeSafety</span> | skillmeat/web/lib/api/merge.ts | POST /api/v1/merge/analyze |
| <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span> | skillmeat/web/lib/api/snapshots.ts | GET /api/v1/versions/snapshots/{snapshotId}/rollback-analysis${params.toString()  |
| <span title="Compare two snapshots and get diff">diffSnapshots</span> | skillmeat/web/lib/api/snapshots.ts | POST /api/v1/versions/snapshots/diff |
| <span title="Copy artifact to another collection">copyArtifactToCollection</span> | skillmeat/web/lib/api/collections.ts | - |
| <span title="Create new collection">createCollection</span> | skillmeat/web/lib/api/collections.ts | POST /api/v1/user-collections |
| <span title="Create new context entity">createContextEntity</span> | skillmeat/web/lib/api/context-entities.ts | POST /api/v1/context-entities |
| <span title="Create new group">createGroup</span> | skillmeat/web/lib/api/groups.ts | POST /api/v1/groups |
| <span title="Create new tag">createTag</span> | skillmeat/web/lib/api/tags.ts | POST /api/v1/tags |
| <span title="Create new template">createTemplate</span> | skillmeat/web/lib/api/templates.ts | POST /api/v1/project-templates |
| <span title="Create new version snapshot">createSnapshot</span> | skillmeat/web/lib/api/snapshots.ts | POST /api/v1/versions/snapshots |
| <span title="Delete artifact from collection">deleteArtifactFromCollection</span> | skillmeat/web/lib/api/artifacts.ts | DELETE /api/v1/artifacts/{artifactId} |
| <span title="Delete collection">deleteCollection</span> | skillmeat/web/lib/api/collections.ts | DELETE /api/v1/user-collections/{id} |
| <span title="Delete context entity">deleteContextEntity</span> | skillmeat/web/lib/api/context-entities.ts | DELETE /api/v1/context-entities/{id} |
| <span title="Delete group">deleteGroup</span> | skillmeat/web/lib/api/groups.ts | DELETE /api/v1/groups/{id} |
| <span title="Delete snapshot by ID">deleteSnapshot</span> | skillmeat/web/lib/api/snapshots.ts | DELETE /api/v1/versions/snapshots/{id}${params.toString()  |
| <span title="Delete tag">deleteTag</span> | skillmeat/web/lib/api/tags.ts | DELETE /api/v1/tags/{id} |
| <span title="Delete template">deleteTemplate</span> | skillmeat/web/lib/api/templates.ts | DELETE /api/v1/project-templates/{id} |
| <span title="Deploy an artifact to a project">deployArtifact</span> | skillmeat/web/lib/api/deployments.ts | POST /api/v1/deploy |
| <span title="Deploy template to a project">deployTemplate</span> | skillmeat/web/lib/api/templates.ts | POST /api/v1/project-templates/{id}/deploy |
| <span title="Execute merge between snapshots">executeMerge</span> | skillmeat/web/lib/api/merge.ts | POST /api/v1/merge/execute |
| <span title="Execute rollback to a snapshot">executeRollback</span> | skillmeat/web/lib/api/snapshots.ts | POST /api/v1/versions/snapshots/{snapshotId}/rollback |
| <span title="Fetch all collections">fetchCollections</span> | skillmeat/web/lib/api/collections.ts | GET /api/v1/user-collections |
| <span title="Fetch all tags with pagination">fetchTags</span> | skillmeat/web/lib/api/tags.ts | GET /api/v1/tags${params.toString()  |
| <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span> | skillmeat/web/lib/api/templates.ts | GET /api/v1/project-templates${params.toString()  |
| <span title="Fetch content of a specific file from a catalog artifact">fetchCatalogFileContent</span> | skillmeat/web/lib/api/catalog.ts | GET /api/v1/marketplace/sources/{sourceId}/artifacts/{encodedArtifactPath}/files/{encodedFilePath} |
| <span title="Fetch context entities with optional filtering">fetchContextEntities</span> | skillmeat/web/lib/api/context-entities.ts | GET /api/v1/context-entities${params.toString()  |
| <span title="Fetch file tree for a catalog artifact">fetchCatalogFileTree</span> | skillmeat/web/lib/api/catalog.ts | GET /api/v1/marketplace/sources/{sourceId}/artifacts/{encodedPath}/files |
| <span title="Fetch groups for a collection">fetchGroups</span> | skillmeat/web/lib/api/groups.ts | GET /api/v1/groups |
| <span title="Fetch paginated artifacts from collection">fetchArtifactsPaginated</span> | skillmeat/web/lib/api/artifacts.ts | - |
| <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span> | skillmeat/web/lib/api/collections.ts | - |
| <span title="Fetch paginated list of snapshots">fetchSnapshots</span> | skillmeat/web/lib/api/snapshots.ts | GET /api/v1/versions/snapshots${params.toString()  |
| <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span> | skillmeat/web/lib/api/context-entities.ts | GET /api/v1/context-entities/{id}/content |
| <span title="Fetch single collection by ID">fetchCollection</span> | skillmeat/web/lib/api/collections.ts | GET /api/v1/user-collections/{id} |
| <span title="Fetch single context entity by ID">fetchContextEntity</span> | skillmeat/web/lib/api/context-entities.ts | GET /api/v1/context-entities/{id} |
| <span title="Fetch single group by ID">fetchGroup</span> | skillmeat/web/lib/api/groups.ts | GET /api/v1/groups/{id} |
| <span title="Fetch single snapshot by ID">fetchSnapshot</span> | skillmeat/web/lib/api/snapshots.ts | GET /api/v1/versions/snapshots/{id}${params.toString()  |
| <span title="Fetch template by ID with full entity details">fetchTemplateById</span> | skillmeat/web/lib/api/templates.ts | GET /api/v1/project-templates/{id} |
| <span title="Get all tags for an artifact">getArtifactTags</span> | skillmeat/web/lib/api/tags.ts | GET /api/v1/artifacts/{artifactId}/tags |
| <span title="Get deployment summary statistics">getDeploymentSummary</span> | skillmeat/web/lib/api/deployments.ts | - |
| <span title="Get deployments with optional filtering">getDeployments</span> | skillmeat/web/lib/api/deployments.ts | - |
| <span title="Get extracted path tag segments for a marketplace catalog entry">getPathTags</span> | skillmeat/web/lib/api/marketplace.ts | GET /api/v1/marketplace/sources/{sourceId}/catalog/{entryId}/path-tags |
| <span title="Get sync status for a project">getSyncStatus</span> | skillmeat/web/lib/api/context-sync.ts | GET /api/v1/context-sync/status |
| <span title="Infer repository structure from GitHub URL">inferUrl</span> | skillmeat/web/lib/api/marketplace.ts | POST /api/v1/marketplace/sources/infer-url |
| <span title="List all deployed artifacts in a project">listDeployments</span> | skillmeat/web/lib/api/deployments.ts | GET /api/v1/deploy${params.toString()  |
| <span title="Move artifact to another collection">moveArtifactToCollection</span> | skillmeat/web/lib/api/collections.ts | - |
| <span title="Move artifact to another group">moveArtifactToGroup</span> | skillmeat/web/lib/api/groups.ts | POST /api/v1/groups/{sourceGroupId}/artifacts/{artifactId}/move |
| <span title="Preview merge changes between snapshots">previewMerge</span> | skillmeat/web/lib/api/merge.ts | POST /api/v1/merge/preview |
| <span title="Pull changes from project to collection">pullChanges</span> | skillmeat/web/lib/api/context-sync.ts | POST /api/v1/context-sync/pull |
| <span title="Push collection changes to project">pushChanges</span> | skillmeat/web/lib/api/context-sync.ts | POST /api/v1/context-sync/push |
| <span title="Query keys factory">sourceKeys</span> | skillmeat/web/hooks/useMarketplaceSources.ts | - |
| <span title="Remove a deployed artifact from a specific project">removeProjectDeployment</span> | skillmeat/web/lib/api/deployments.ts | DELETE /api/v1/projects/{projectId}/deployments/{artifactName} |
| <span title="Remove artifact from collection">removeArtifactFromCollection</span> | skillmeat/web/lib/api/collections.ts | DELETE /api/v1/user-collections/{collectionId}/artifacts/{artifactId} |
| <span title="Remove artifact from group">removeArtifactFromGroup</span> | skillmeat/web/lib/api/groups.ts | DELETE /api/v1/groups/{groupId}/artifacts/{artifactId} |
| <span title="Remove tag from artifact">removeTagFromArtifact</span> | skillmeat/web/lib/api/tags.ts | DELETE /api/v1/artifacts/{artifactId}/tags/{tagId} |
| <span title="Reorder artifacts within group">reorderArtifactsInGroup</span> | skillmeat/web/lib/api/groups.ts | POST /api/v1/groups/{groupId}/artifacts/reorder |
| <span title="Reorder groups within a collection">reorderGroups</span> | skillmeat/web/lib/api/groups.ts | PUT /api/v1/collections/{collectionId}/groups/reorder |
| <span title="Resolve a merge conflict">resolveConflict</span> | skillmeat/web/lib/api/merge.ts | POST /api/v1/merge/resolve |
| <span title="Resolve sync conflict">resolveConflict</span> | skillmeat/web/lib/api/context-sync.ts | POST /api/v1/context-sync/resolve |
| <span title="Search tags by query string">searchTags</span> | skillmeat/web/lib/api/tags.ts | GET /api/v1/tags/search |
| <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span> | skillmeat/web/lib/api/deployments.ts | POST /api/v1/deploy/undeploy |
| <span title="Update existing collection">updateCollection</span> | skillmeat/web/lib/api/collections.ts | PUT /api/v1/user-collections/{id} |
| <span title="Update existing context entity">updateContextEntity</span> | skillmeat/web/lib/api/context-entities.ts | PUT /api/v1/context-entities/{id} |
| <span title="Update existing group">updateGroup</span> | skillmeat/web/lib/api/groups.ts | PUT /api/v1/groups/{id} |
| <span title="Update existing tag">updateTag</span> | skillmeat/web/lib/api/tags.ts | PUT /api/v1/tags/{id} |
| <span title="Update existing template">updateTemplate</span> | skillmeat/web/lib/api/templates.ts | PUT /api/v1/project-templates/{id} |
| <span title="Update status of a specific path tag segment (approve or reject)">updatePathTagStatus</span> | skillmeat/web/lib/api/marketplace.ts | PATCH /api/v1/marketplace/sources/{sourceId}/catalog/{entryId}/path-tags |
| <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | skillmeat/web/lib/api.ts | - |
| <span title="export class ApiError extends Error">ApiError</span> | skillmeat/web/lib/api.ts | - |
| <span title="export const apiConfig =">apiConfig</span> | skillmeat/web/lib/api.ts | - |
| <span title="export function buildApiHeaders(extra?: HeadersInit): HeadersInit">buildApiHeaders</span> | skillmeat/web/lib/api.ts | - |
| <span title="export function useToast()">useToast</span> | skillmeat/web/hooks/use-toast.tsx | - |
| type ArtifactsPaginatedResponse | skillmeat/web/lib/api/artifacts.ts | - |
| type CollectionArtifactsPaginatedResponse | skillmeat/web/lib/api/collections.ts | - |
| type DeploymentQueryParams | skillmeat/web/lib/api/deployments.ts | - |
| type DeploymentSummary | skillmeat/web/lib/api/deployments.ts | - |
| type FileContentResponse | skillmeat/web/lib/api/catalog.ts | - |
| type FileTreeResponse | skillmeat/web/lib/api/catalog.ts | - |
| type SyncResolution | skillmeat/web/lib/api/context-sync.ts | - |
| type SyncStatus | skillmeat/web/lib/api/context-sync.ts | - |
| type Tag | skillmeat/web/lib/api/tags.ts | - |
| type TagCreateRequest | skillmeat/web/lib/api/tags.ts | - |
| type TagListResponse | skillmeat/web/lib/api/tags.ts | - |
| type TagUpdateRequest | skillmeat/web/lib/api/tags.ts | - |
<!-- CODEBASE_GRAPH:API_CLIENTS:END -->

## Endpoint Mapping (Quick Reference)

| Operation | Endpoint | Method | Status | Notes |
|-----------|----------|--------|--------|-------|
| **Collections** |
| List collections (read-only) | `/collections` | GET | ✅ Implemented | Pagination supported |
| Get collection by ID | `/collections/{id}` | GET | ✅ Implemented | |
| Create collection | `/user-collections` | POST | ✅ Implemented | **Use this, not /collections** |
| Update collection | `/collections/{id}` | PUT | 🚧 Phase 4 | |
| Delete collection | `/collections/{id}` | DELETE | 🚧 Phase 4 | |
| Get collection artifacts | `/collections/{id}/artifacts` | GET | ✅ Implemented | Pagination supported |
| Add artifact to collection | `/collections/{id}/artifacts/{artifact_id}` | POST | 🚧 Phase 4 | |
| Remove artifact | `/collections/{id}/artifacts/{artifact_id}` | DELETE | 🚧 Phase 4 | |
| Copy artifact | `/collections/{source_id}/artifacts/{artifact_id}/copy` | POST | 🚧 Phase 4 | |
| Move artifact | `/collections/{source_id}/artifacts/{artifact_id}/move` | POST | 🚧 Phase 4 | |
| **Artifacts** |
| List artifacts | `/artifacts` | GET | ✅ Implemented | Read-only (imports via bulk) |
| Bulk import | `/artifacts/bulk-import` | POST | ✅ Implemented | For adding new artifacts |
| **Deployments** |
| Deploy artifact | `/deploy` | POST | ✅ Implemented | |
| Undeploy artifact | `/deploy/undeploy` | POST | ✅ Implemented | |
| List deployments | `/deploy` | GET | ✅ Implemented | Query params supported |
| **Groups** |
| List groups | `/groups` | GET | ✅ Implemented | |
| Create group | `/groups` | POST | ✅ Implemented | |
| Get group | `/groups/{id}` | GET | ✅ Implemented | |
| Update group | `/groups/{id}` | PUT | ✅ Implemented | |
| Delete group | `/groups/{id}` | DELETE | ✅ Implemented | |

**Key Insight**: `/collections` is read-only; use `/user-collections` for mutations (create/update/delete).

**Full Mapping**: For complete endpoint reference, see API documentation or backend OpenAPI spec.

---

## Configuration

API client configuration lives in `lib/api.ts` (shared) and individual API client files.

### Environment Variables

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';
```

**Set in `.env.local`**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_API_VERSION=v1
```

### URL Building Pattern

Every API client file uses consistent URL building:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}
```

**Usage**:
```typescript
const response = await fetch(buildUrl('/collections'));
// → http://localhost:8080/api/v1/collections
```

**Always use `buildUrl()`** - never hardcode URLs.

---

## Error Handling Pattern

All API client functions follow consistent error handling:

```typescript
export async function apiFunction(data: RequestType): Promise<ResponseType> {
  const response = await fetch(buildUrl('/endpoint'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    // Try to parse error body from backend
    const errorBody = await response.json().catch(() => ({}));
    // Throw with backend error detail or fallback to statusText
    throw new Error(errorBody.detail || `Failed to {operation}: ${response.statusText}`);
  }

  return response.json();
}
```

**Key Points**:
1. **Always check `response.ok`** before parsing JSON
2. **Try to extract `detail`** from error response (backend FastAPI format)
3. **Fallback to `response.statusText`** if no detail available
4. **Use descriptive error messages** - include operation name

**Example Error Responses**:
```json
// Backend FastAPI error format
{
  "detail": "Collection with name 'test' already exists"
}
```

---

## API Client File Structure

Each domain has its own API client file in `lib/api/`:

```
lib/api/
├── index.ts            # Re-exports all API clients
├── collections.ts      # Collection operations
├── groups.ts           # Group operations
└── deployments.ts      # Deployment operations
```

### File Template

```typescript
/**
 * {Domain} API service functions
 */
import type { Entity, CreateRequest, UpdateRequest } from '@/types/{domain}';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch all entities
 */
export async function fetchEntities(): Promise<Entity[]> {
  const response = await fetch(buildUrl('/entities'));
  if (!response.ok) {
    throw new Error(`Failed to fetch entities: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create new entity
 */
export async function createEntity(data: CreateRequest): Promise<Entity> {
  const response = await fetch(buildUrl('/entities'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create entity: ${response.statusText}`);
  }
  return response.json();
}
```

### Index File Pattern

```typescript
/**
 * API service module exports
 */
export * from './collections';
export * from './groups';
export * from './deployments';
```

**Usage in hooks**:
```typescript
import { createCollection } from '@/lib/api/collections';
// OR
import { createCollection } from '@/lib/api';
```

---

## Request Patterns

### GET Requests

```typescript
export async function fetchCollection(id: string): Promise<Collection> {
  const response = await fetch(buildUrl(`/collections/${id}`));
  if (!response.ok) {
    throw new Error(`Failed to fetch collection: ${response.statusText}`);
  }
  return response.json();
}
```

### GET with Query Parameters

```typescript
export async function fetchCollections(filters?: {
  limit?: number;
  after?: string;
}): Promise<Collection[]> {
  const params = new URLSearchParams();
  if (filters?.limit) params.set('limit', filters.limit.toString());
  if (filters?.after) params.set('after', filters.after);

  const url = buildUrl(`/collections${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch collections: ${response.statusText}`);
  }
  return response.json();
}
```

### POST Requests

```typescript
export async function createCollection(data: CreateCollectionRequest): Promise<Collection> {
  const response = await fetch(buildUrl('/user-collections'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create collection: ${response.statusText}`);
  }
  return response.json();
}
```

### PUT Requests

```typescript
export async function updateCollection(
  id: string,
  data: UpdateCollectionRequest
): Promise<Collection> {
  const response = await fetch(buildUrl(`/collections/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Failed to update collection: ${response.statusText}`);
  }
  return response.json();
}
```

### DELETE Requests

```typescript
export async function deleteCollection(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/collections/${id}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete collection: ${response.statusText}`);
  }
  // DELETE typically returns 204 No Content (no body)
}
```

---

## Type Safety

All API client functions use TypeScript types from `types/` directory:

```typescript
import type {
  Collection,
  CreateCollectionRequest,
  UpdateCollectionRequest,
} from '@/types/collections';

export async function createCollection(
  data: CreateCollectionRequest
): Promise<Collection> {
  // Implementation
}
```

**Type Sources**:
1. **Generated SDK types** (`sdk/models/`) - preferred for backend schemas
2. **Custom types** (`types/`) - for UI-specific data structures

---

## Authentication (Future)

Currently no authentication. When implemented, add to headers:

```typescript
const headers: HeadersInit = {
  'Content-Type': 'application/json',
};

// Add auth token if available
const token = process.env.NEXT_PUBLIC_API_TOKEN;
if (token) {
  headers['Authorization'] = `Bearer ${token}`;
}

const response = await fetch(buildUrl('/endpoint'), {
  method: 'POST',
  headers,
  body: JSON.stringify(data),
});
```

---

## Testing API Clients

Use `jest` with `fetch` mocking:

```typescript
import { createCollection } from '@/lib/api/collections';

// Mock global fetch
global.fetch = jest.fn();

describe('createCollection', () => {
  afterEach(() => {
    jest.resetAllMocks();
  });

  it('creates collection successfully', async () => {
    const mockCollection = { id: '1', name: 'test', ... };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockCollection,
    });

    const result = await createCollection({ name: 'test' });
    expect(result).toEqual(mockCollection);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/user-collections',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('handles errors correctly', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Name already exists' }),
    });

    await expect(createCollection({ name: 'test' }))
      .rejects.toThrow('Name already exists');
  });
});
```

---

## Common Antipatterns

❌ **Hardcoded URLs**:
```typescript
// BAD: Hardcoded URL
fetch('http://localhost:8080/api/v1/collections')
```

✅ **Use buildUrl**:
```typescript
// GOOD: Use buildUrl helper
fetch(buildUrl('/collections'))
```

❌ **No error handling**:
```typescript
// BAD: No error handling
return fetch(url).then(r => r.json());
```

✅ **Check response.ok**:
```typescript
// GOOD: Check response and handle errors
if (!response.ok) {
  const errorBody = await response.json().catch(() => ({}));
  throw new Error(errorBody.detail || `Failed: ${response.statusText}`);
}
```

❌ **Wrong endpoint**:
```typescript
// BAD: Using read-only endpoint for create
fetch(buildUrl('/collections'), { method: 'POST' })
```

✅ **Use correct endpoint**:
```typescript
// GOOD: Use user-collections for mutations
fetch(buildUrl('/user-collections'), { method: 'POST' })
```

❌ **Ignoring backend error detail**:
```typescript
// BAD: Generic error message
throw new Error('Failed');
```

✅ **Extract backend detail**:
```typescript
// GOOD: Use backend error detail
const errorBody = await response.json().catch(() => ({}));
throw new Error(errorBody.detail || `Failed: ${response.statusText}`);
```

---

## Reference

- **API Base Configuration**: `lib/api.ts`
- **Endpoint Mapping**: See table above or backend OpenAPI spec at `/api/v1/docs`
- **Type Definitions**: `types/` directory
- **Hook Integration**: `hooks/` directory (see `hooks.md` rule)
- **Backend API Docs**: `skillmeat/api/CLAUDE.md`
