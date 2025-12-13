---
title: Stub Patterns Catalog
purpose: Catalog of stub implementations - load for "not yet implemented" errors
references:
  - skillmeat/web/hooks/use-collections.ts
  - skillmeat/web/lib/api/collections.ts
last_verified: 2025-12-13
---

# Stub Patterns Catalog

Comprehensive catalog of stub implementations across SkillMeat frontend.

## Frontend Collection Hooks (use-collections.ts)

**File**: `skillmeat/web/hooks/use-collections.ts`

| Hook | Status | Error Pattern | API Call | Cache Keys |
|------|--------|---------------|----------|------------|
| useCollections | ✅ ACTIVE | - | `apiRequest<CollectionListResponse>(/collections)` | `collectionKeys.list(filters)` |
| useCollection | ✅ ACTIVE | - | `apiRequest<Collection>(/collections/{id})` | `collectionKeys.detail(id)` |
| useCollectionArtifacts | ✅ ACTIVE | - | `apiRequest<CollectionArtifactsResponse>(/collections/{id}/artifacts)` | `collectionKeys.artifacts(id)` |
| useCreateCollection | ✅ FIXED | - | `createCollection(data)` | Invalidates: `collectionKeys.lists()` |
| useUpdateCollection | ⚠️ STUB | `throw new ApiError('Collection update not yet implemented', 501)` | N/A | Would invalidate: `collectionKeys.detail(id)`, `collectionKeys.lists()` |
| useDeleteCollection | ⚠️ STUB | `throw new ApiError('Collection deletion not yet implemented', 501)` | N/A | Would invalidate: `collectionKeys.lists()` |
| useAddArtifactToCollection | ⚠️ STUB | `throw new ApiError('Adding artifacts to collections not yet implemented', 501)` | N/A | Would invalidate: `collectionKeys.detail(id)`, `collectionKeys.artifacts(id)` |
| useRemoveArtifactFromCollection | ⚠️ STUB | `throw new ApiError('Removing artifacts from collections not yet implemented', 501)` | N/A | Would invalidate: `collectionKeys.detail(id)`, `collectionKeys.artifacts(id)` |

### Grep Patterns

```bash
# Find all stub hooks
grep -n "throw new ApiError.*not yet implemented" skillmeat/web/hooks/use-collections.ts

# Find specific hook
grep -A 20 "export function useUpdateCollection" skillmeat/web/hooks/use-collections.ts

# Find all mutation hooks
grep -n "export function use.*Collection" skillmeat/web/hooks/use-collections.ts
```

### Hook Implementation Pattern

**Stub Pattern** (current):
```typescript
export function useUpdateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (_params: {
      id: string;
      data: UpdateCollectionRequest;
    }): Promise<Collection> => {
      // TODO: Backend endpoint not yet implemented (Phase 4)
      throw new ApiError('Collection update not yet implemented', 501);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
    },
  });
}
```

**Active Pattern** (useCreateCollection - REFERENCE):
```typescript
export function useCreateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateCollectionRequest): Promise<Collection> => {
      return createCollection(data);  // Calls API client
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
    },
  });
}
```

### Fix Pattern Steps

When converting stub to active implementation:

1. **Check API endpoint exists** (see `api-endpoint-mapping.md`):
   ```bash
   grep -A 5 "@router.put.*collection_id" skillmeat/api/routers/user_collections.py
   ```

2. **Add API client function** (`lib/api/collections.ts`):
   ```typescript
   export async function updateCollection(
     id: string,
     data: UpdateCollectionRequest
   ): Promise<Collection> {
     return apiRequest<Collection>(`/user-collections/${id}`, {
       method: 'PUT',
       body: JSON.stringify(data),
     });
   }
   ```

3. **Replace mutationFn**:
   ```typescript
   mutationFn: async ({ id, data }: {
     id: string;
     data: UpdateCollectionRequest;
   }): Promise<Collection> => {
     return updateCollection(id, data);
   },
   ```

4. **Remove underscore prefixes** (signals unused params):
   ```diff
   - mutationFn: async (_params: { id: string; data: UpdateCollectionRequest })
   + mutationFn: async ({ id, data }: { id: string; data: UpdateCollectionRequest })
   ```

5. **Remove TODO comment**.

6. **Test cache invalidation** is still correct.

## API Client Functions (lib/api/collections.ts)

**File**: `skillmeat/web/lib/api/collections.ts`

| Function | Status | Endpoint | Method | Used By |
|----------|--------|----------|--------|---------|
| createCollection | ✅ ACTIVE | `/user-collections` | POST | useCreateCollection |
| updateCollection | ⚠️ NEEDED | `/user-collections/{id}` | PUT | useUpdateCollection (stub) |
| deleteCollection | ⚠️ NEEDED | `/user-collections/{id}` | DELETE | useDeleteCollection (stub) |
| addArtifactToCollection | ⚠️ NEEDED | `/user-collections/{id}/artifacts` | POST | useAddArtifactToCollection (stub) |
| removeArtifactFromCollection | ⚠️ NEEDED | `/user-collections/{id}/artifacts/{artifact_id}` | DELETE | useRemoveArtifactFromCollection (stub) |

### API Client Implementation Pattern

**Template** (for creating new API client functions):
```typescript
/**
 * Update collection metadata
 */
export async function updateCollection(
  id: string,
  data: UpdateCollectionRequest
): Promise<Collection> {
  return apiRequest<Collection>(`/user-collections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Delete collection
 */
export async function deleteCollection(id: string): Promise<void> {
  return apiRequest<void>(`/user-collections/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Add artifact to collection
 */
export async function addArtifactToCollection(
  collectionId: string,
  artifactId: string,
  position?: number
): Promise<void> {
  return apiRequest<void>(`/user-collections/${collectionId}/artifacts`, {
    method: 'POST',
    body: JSON.stringify({
      artifact_id: artifactId,
      position
    }),
  });
}

/**
 * Remove artifact from collection
 */
export async function removeArtifactFromCollection(
  collectionId: string,
  artifactId: string
): Promise<void> {
  return apiRequest<void>(
    `/user-collections/${collectionId}/artifacts/${artifactId}`,
    { method: 'DELETE' }
  );
}
```

### Grep Patterns for API Client

```bash
# Find all API client functions
grep -n "export async function" skillmeat/web/lib/api/collections.ts

# Find createCollection implementation (reference)
grep -A 15 "export async function createCollection" skillmeat/web/lib/api/collections.ts

# Check apiRequest usage pattern
grep "apiRequest<" skillmeat/web/lib/api/collections.ts
```

## Cache Invalidation Patterns

### Query Keys Structure

**File**: `skillmeat/web/hooks/use-collections.ts`

```typescript
const collectionKeys = {
  all: ['collections'] as const,
  lists: () => [...collectionKeys.all, 'list'] as const,
  list: (filters?: CollectionFilters) => [...collectionKeys.lists(), { filters }] as const,
  details: () => [...collectionKeys.all, 'detail'] as const,
  detail: (id: string) => [...collectionKeys.details(), id] as const,
  artifacts: (id: string) => [...collectionKeys.detail(id), 'artifacts'] as const,
};
```

### Invalidation Strategy

| Operation | Invalidate Keys | Reason |
|-----------|----------------|--------|
| Create Collection | `collectionKeys.lists()` | New item appears in lists |
| Update Collection | `collectionKeys.detail(id)`, `collectionKeys.lists()` | Details changed, may affect list display |
| Delete Collection | `collectionKeys.lists()` | Item removed from lists |
| Add Artifact | `collectionKeys.detail(id)`, `collectionKeys.artifacts(id)` | Artifact count/list changed |
| Remove Artifact | `collectionKeys.detail(id)`, `collectionKeys.artifacts(id)` | Artifact count/list changed |

### Pattern Example

```typescript
// Mutation that affects multiple cache keys
onSuccess: (_, { id }) => {
  // Invalidate specific collection detail
  queryClient.invalidateQueries({
    queryKey: collectionKeys.detail(id)
  });

  // Invalidate all collection lists (may contain this item)
  queryClient.invalidateQueries({
    queryKey: collectionKeys.lists()
  });

  // Invalidate specific collection's artifacts
  queryClient.invalidateQueries({
    queryKey: collectionKeys.artifacts(id)
  });
},
```

## TypeScript Type Patterns

### Request/Response Types

**Location**: Inferred from schemas or defined locally

```typescript
// Creation request (minimal required fields)
interface CreateCollectionRequest {
  name: string;
  description?: string;
  is_public?: boolean;
}

// Update request (partial fields)
interface UpdateCollectionRequest {
  name?: string;
  description?: string;
  is_public?: boolean;
}

// Response type (full object)
interface Collection {
  id: string;
  name: string;
  description?: string;
  is_public: boolean;
  artifact_count: number;
  created_at: string;
  updated_at: string;
}
```

### Type Verification

```bash
# Find type definitions
grep -n "interface.*Collection.*Request" skillmeat/web/hooks/use-collections.ts
grep -n "interface Collection\b" skillmeat/web/types/collection.ts

# Check what SDK provides
grep -n "export.*interface.*Collection" skillmeat/web/sdk/models/*.ts
```

## Error Handling Patterns

### ApiError Class

**File**: `skillmeat/web/lib/api.ts`

```typescript
export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}
```

### Stub Error Pattern

```typescript
throw new ApiError('Collection update not yet implemented', 501);
//                 ^message                                  ^status (501 Not Implemented)
```

**Status Codes**:
- `501 Not Implemented`: Stub/placeholder
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server-side error

### Error Detection in Components

```typescript
const updateCollection = useUpdateCollection();

try {
  await updateCollection.mutateAsync({ id, data });
} catch (error) {
  if (error instanceof ApiError && error.status === 501) {
    // Handle stub error (show "Coming Soon" message)
  }
}
```

## Complete Fix Workflow

### Example: Implement useUpdateCollection

**1. Verify backend endpoint exists**:
```bash
grep -A 10 '@router.put.*collection_id' skillmeat/api/routers/user_collections.py
```

**Expected**:
```python
@router.put(
    "/{collection_id}",
    response_model=UserCollectionResponse,
    summary="Update user collection",
```

**2. Add API client function** (`lib/api/collections.ts`):
```typescript
export async function updateCollection(
  id: string,
  data: UpdateCollectionRequest
): Promise<Collection> {
  return apiRequest<Collection>(`/user-collections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}
```

**3. Update hook** (`hooks/use-collections.ts`):
```diff
export function useUpdateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
-   mutationFn: async (_params: {
+   mutationFn: async ({ id, data }: {
      id: string;
      data: UpdateCollectionRequest;
    }): Promise<Collection> => {
-     // TODO: Backend endpoint not yet implemented (Phase 4)
-     throw new ApiError('Collection update not yet implemented', 501);
+     return updateCollection(id, data);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
    },
  });
}
```

**4. Test**:
```bash
pnpm type-check  # Verify no TypeScript errors
pnpm test -- use-collections  # Run tests
```

**5. Verify cache invalidation**:
- Update collection → detail cache updates
- Update collection → list cache updates (if name/description shown)

## Discovery Commands

### Find All Stubs

```bash
# Find all stub implementations (501 errors)
grep -rn "throw new ApiError.*501" skillmeat/web/

# Find all TODO comments
grep -rn "TODO.*not yet implemented" skillmeat/web/

# Find all mutation hooks
grep -rn "useMutation" skillmeat/web/hooks/
```

### Verify Backend Support

```bash
# Check if backend endpoint exists for operation
grep -rn "@router\.put" skillmeat/api/routers/user_collections.py
grep -rn "@router\.delete" skillmeat/api/routers/user_collections.py
grep -rn "@router\.post.*artifacts" skillmeat/api/routers/user_collections.py
```

### Check API Client Coverage

```bash
# List all API client functions
grep -n "export async function" skillmeat/web/lib/api/collections.ts

# Compare against hooks that need them
grep -n "export function use.*Collection" skillmeat/web/hooks/use-collections.ts
```

## Stub Status Summary

### Collections Domain

| Feature | Hook Status | API Client Status | Backend Status | Priority |
|---------|-------------|-------------------|----------------|----------|
| List collections | ✅ ACTIVE | ✅ ACTIVE | ✅ ACTIVE | - |
| Get collection | ✅ ACTIVE | ✅ ACTIVE | ✅ ACTIVE | - |
| Create collection | ✅ FIXED | ✅ ACTIVE | ✅ ACTIVE | - |
| Update collection | ⚠️ STUB | ⚠️ NEEDED | ✅ ACTIVE | HIGH |
| Delete collection | ⚠️ STUB | ⚠️ NEEDED | ✅ ACTIVE | HIGH |
| Add artifact | ⚠️ STUB | ⚠️ NEEDED | ✅ ACTIVE | MEDIUM |
| Remove artifact | ⚠️ STUB | ⚠️ NEEDED | ✅ ACTIVE | MEDIUM |

**Note**: Backend endpoints exist (verified in `api-endpoint-mapping.md`), only frontend stubs remain.

### Other Domains

Check for stubs in:
- `skillmeat/web/hooks/use-artifacts.ts`
- `skillmeat/web/hooks/use-projects.ts`
- `skillmeat/web/hooks/use-deployments.ts`
- `skillmeat/web/hooks/use-marketplace.ts`

```bash
# Find all hook files
find skillmeat/web/hooks -name "*.ts" -type f

# Check each for stubs
for file in skillmeat/web/hooks/*.ts; do
  echo "=== $file ==="
  grep -n "throw new ApiError.*not yet implemented" "$file" || echo "No stubs"
done
```

## Maintenance

### Update This File

When implementing stubs:
1. Change hook status from ⚠️ STUB to ✅ ACTIVE
2. Add API client function to table
3. Update Stub Status Summary
4. Update last_verified date
5. Document any new patterns discovered

### Regeneration Commands

```bash
# Find current stub count
grep -r "throw new ApiError.*not yet implemented" skillmeat/web/ | wc -l

# Generate stub report
echo "=== Collection Hooks ===" && \
grep -n "export function use.*Collection" skillmeat/web/hooks/use-collections.ts && \
echo "=== Stubs ===" && \
grep -n "throw new ApiError.*not yet implemented" skillmeat/web/hooks/use-collections.ts

# Check backend coverage
echo "=== Backend Endpoints ===" && \
grep "@router\." skillmeat/api/routers/user_collections.py | wc -l && \
echo "=== Frontend Hooks ===" && \
grep "export function use.*Collection" skillmeat/web/hooks/use-collections.ts | wc -l
```

### Verification

Before marking a stub as fixed:
1. ✅ Backend endpoint exists and is tested
2. ✅ API client function implemented
3. ✅ Hook calls API client (no more throw statement)
4. ✅ Cache invalidation strategy correct
5. ✅ TypeScript types match backend schema
6. ✅ Error handling implemented
7. ✅ Tests pass
