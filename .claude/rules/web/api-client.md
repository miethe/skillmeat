<!-- Path Scope: skillmeat/web/lib/api/**/*.ts -->

# Web Frontend API Client - Conventions and Patterns

API client functions for SkillMeat web frontend communicating with FastAPI backend.

---

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
