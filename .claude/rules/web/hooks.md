<!-- Path Scope: skillmeat/web/hooks/**/*.ts -->

# Web Frontend Hooks - Patterns and Best Practices

Custom React hooks for SkillMeat web frontend using TanStack Query v5.

---

## Stub Pattern (Not Yet Implemented)

### Identifying Stubs

Hooks may throw `ApiError('Feature not yet implemented', 501)` immediately in mutation functions. These are **stubs** for Phase 4 implementation.

**Example Stub**:
```typescript
export function useUpdateCollection() {
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateCollectionRequest }) => {
      // TODO: Backend endpoint not yet implemented (Phase 4)
      throw new ApiError('Collection update not yet implemented', 501);
    },
  });
}
```

### Fix Pattern

When implementing a stubbed hook:

1. **Find the API client function** in `lib/api/{domain}.ts`
2. **Import and call it** instead of throwing
3. **Wire cache invalidation** in `onSuccess` callback
4. **Update types** if needed (add optional fields to match backend schema)

**Example Fix**:
```typescript
// Before (stub)
mutationFn: async (data: CreateCollectionRequest) => {
  throw new ApiError('Collection creation not yet implemented', 501);
}

// After (implemented)
import { createCollection } from '@/lib/api/collections';

mutationFn: async (data: CreateCollectionRequest) => {
  return createCollection(data);
}
```

### Recent Example: Collection Creation

**Issue**: `useCreateCollection()` threw stub error despite backend being fully implemented.

**Fix**:
1. **Endpoint change**: `/collections` (read-only) → `/user-collections` (full CRUD)
2. **Hook change**: Import `createCollection` from `@/lib/api/collections`
3. **Call**: `return createCollection(data)` instead of throwing
4. **Type update**: Added `description?: string` to `CreateCollectionRequest`

**Reference**: See `.claude/worknotes/bug-fixes-2025-12.md` (2025-12-13 entry)

---

## TanStack Query Conventions

### Query Key Factories

Use factory pattern for type-safe cache keys:

```typescript
export const collectionKeys = {
  all: ['collections'] as const,
  lists: () => [...collectionKeys.all, 'list'] as const,
  list: (filters?: CollectionFilters) => [...collectionKeys.lists(), filters] as const,
  details: () => [...collectionKeys.all, 'detail'] as const,
  detail: (id: string) => [...collectionKeys.details(), id] as const,
  artifacts: (id: string) => [...collectionKeys.detail(id), 'artifacts'] as const,
};
```

**Usage**:
```typescript
// In queries
queryKey: collectionKeys.list({ limit: 10 })

// In cache invalidation
queryClient.invalidateQueries({ queryKey: collectionKeys.all });
queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
```

**Benefits**:
- Type-safe key construction
- Centralized key management
- Easy hierarchical invalidation

### Stale Time Configuration

Default configuration (from `components/providers.tsx`):

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      retry: 1,
    },
  },
});
```

**Override when needed**:
```typescript
export function useCollections() {
  return useQuery({
    queryKey: collectionKeys.all,
    queryFn: fetchCollections,
    staleTime: 1 * 60 * 1000,  // 1 minute for frequently changing data
  });
}
```

### Cache Invalidation Patterns

**Invalidate all collections** (after create/delete):
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: collectionKeys.all });
}
```

**Invalidate specific collection** (after update):
```typescript
onSuccess: (_, { id }) => {
  queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
  queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
}
```

**Invalidate collection artifacts** (after add/remove artifact):
```typescript
onSuccess: (_, { collectionId }) => {
  queryClient.invalidateQueries({ queryKey: collectionKeys.artifacts(collectionId) });
  queryClient.invalidateQueries({ queryKey: collectionKeys.detail(collectionId) });
}
```

---

## API Client Mapping

Hooks call corresponding functions in `lib/api/{domain}.ts`:

| Hook Domain | API Client File |
|-------------|----------------|
| `use-collections.ts` | `lib/api/collections.ts` |
| `use-groups.ts` | `lib/api/groups.ts` |
| `use-deployments.ts` | `lib/api/deployments.ts` |

**Import Pattern**:
```typescript
import { createCollection, updateCollection } from '@/lib/api/collections';
```

---

## Hook Structure Template

```typescript
/**
 * Hook description
 */
export function useEntityAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EntityRequest): Promise<EntityResponse> => {
      // Call API client function (NOT inline fetch)
      return apiClientFunction(data);
    },
    onSuccess: (data, variables) => {
      // Invalidate relevant cache keys
      queryClient.invalidateQueries({ queryKey: entityKeys.all });
    },
    onError: (error) => {
      // Optional: Add toast notification
      console.error('Operation failed:', error);
    },
  });
}
```

---

## Common Antipatterns

❌ **Inline fetch in hooks**:
```typescript
// BAD: Inline fetch logic
mutationFn: async (data) => {
  const response = await fetch('/api/v1/collections', { ... });
  return response.json();
}
```

✅ **Use API client**:
```typescript
// GOOD: Call API client function
import { createCollection } from '@/lib/api/collections';
mutationFn: async (data) => createCollection(data)
```

❌ **Generic cache invalidation**:
```typescript
// BAD: Invalidates too much
queryClient.invalidateQueries();
```

✅ **Targeted invalidation**:
```typescript
// GOOD: Invalidates only what changed
queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
```

❌ **Leaving stubs in production**:
```typescript
// BAD: Stub still throwing error
throw new ApiError('Not implemented', 501);
```

✅ **Implement or remove**:
```typescript
// GOOD: Call real API or remove hook
return apiClientFunction(data);
```

---

## Error Handling

All hooks use `ApiError` from `lib/api.ts`:

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

**Usage in hooks**:
```typescript
mutationFn: async (data) => {
  try {
    return await apiClientFunction(data);
  } catch (error) {
    if (error instanceof ApiError) {
      // Handle API-specific errors
      throw error;
    }
    // Re-wrap generic errors
    throw new ApiError('Operation failed', 500);
  }
}
```

---

## Testing Hooks

Use `@testing-library/react-hooks` for hook tests:

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCollections } from '@/hooks/use-collections';

describe('useCollections', () => {
  it('fetches collections', async () => {
    const queryClient = new QueryClient();
    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCollections(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });
});
```

---

## Reference

- **TanStack Query Docs**: https://tanstack.com/query/latest
- **Stub Detection**: Look for `throw new ApiError(..., 501)`
- **API Client Location**: `skillmeat/web/lib/api/{domain}.ts`
- **Bug Fixes Log**: `.claude/worknotes/bug-fixes-2025-12.md`
