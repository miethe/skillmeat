# Phase 1 Tasks: Data Layer & Hooks

**Phase**: 1 | **Duration**: 3-4 days | **Story Points**: 8 | **Assigned To**: backend-typescript-architect (Opus)

---

## Overview

Phase 1 establishes the foundational data layer for the Collections & Groups UX enhancement. This phase creates reusable React hooks for fetching groups and artifact-group relationships, implements proper TanStack Query caching, and establishes error handling patterns that Phases 2-5 depend on.

**Deliverables**:
- `useGroups()` hook for fetching groups in a collection
- `useArtifactGroups()` hook for fetching groups containing a specific artifact
- `fetchArtifactGroups()` API client function
- Hierarchical TanStack Query cache key structure
- Error handling patterns with graceful fallbacks
- ≥80% test coverage
- JSDoc documentation

---

## Task P1-T1: Create useGroups Hook Enhancement

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Enhance the existing `useGroups()` hook (already implemented in `skillmeat/web/hooks/use-groups.ts`) to ensure it's properly exported and documented for use in card badge rendering and filters. If not already present, implement missing features like error fallbacks and stale time configuration.

### Acceptance Criteria

- [x] `useGroups(collectionId)` hook exports from `@/hooks`
- [x] Hook accepts `collectionId` parameter
- [x] Returns `UseQueryResult<GroupListResponse, Error>` with data and isLoading
- [x] Calls API endpoint: `GET /groups?collection_id={collectionId}`
- [x] Sorts groups by position field for consistent ordering
- [x] Configures stale time: 5 minutes
- [x] Error handling: returns empty groups array on failure (graceful degradation)
- [x] Only runs query when `collectionId` is defined (enabled flag)
- [x] JSDoc comment documents purpose, parameters, return type, and usage example

### Implementation Details

**File**: `skillmeat/web/hooks/use-groups.ts`

The hook already exists but verify:

```typescript
export function useGroups(collectionId: string | undefined): UseQueryResult<GroupListResponse, Error> {
  return useQuery({
    queryKey: groupKeys.list(collectionId),
    queryFn: async (): Promise<GroupListResponse> => {
      // Must handle collectionId undefined
      // Sort by position
      // Return fallback empty array on error if USE_MOCKS
    },
    enabled: !!collectionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

### Test Cases

- [ ] Hook fetches and sorts groups correctly
- [ ] Hook returns empty groups array on API error
- [ ] Query only runs when collectionId is provided
- [ ] Cache key structured correctly for invalidation
- [ ] Stale time set to 5 minutes
- [ ] JSDoc example is accurate and runnable

### Quality Gates

- [ ] Unit test coverage ≥80%
- [ ] TypeScript strict mode, no errors
- [ ] ESLint passes
- [ ] JSDoc comment complete and accurate

---

## Task P1-T2: Create useArtifactGroups Hook

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Create a new `useArtifactGroups()` hook for fetching which groups contain a specific artifact within a collection. This hook is called from card components to display group badges.

### Acceptance Criteria

- [x] Hook created at `skillmeat/web/hooks/use-artifact-groups.ts`
- [x] Accepts `artifactId` and `collectionId` parameters
- [x] Returns `UseQueryResult<Group[], Error>` with groups array
- [x] Calls API endpoint: `GET /groups?collection_id={collectionId}&artifact_id={artifactId}`
- [x] Or alternative endpoint if backend uses different contract (verify in PRD Appendix A)
- [x] Configures stale time: 10 minutes (longer cache for per-artifact data)
- [x] Error handling: returns empty groups array on failure
- [x] Only runs query when both `artifactId` and `collectionId` are defined
- [x] Uses hierarchical cache keys for efficient invalidation
- [x] JSDoc comment with usage example

### Implementation Details

**File**: `skillmeat/web/hooks/use-artifact-groups.ts` (new)

```typescript
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { Group } from '@/types/groups';

// Cache key factory
const artifactGroupKeys = {
  all: ['artifact-groups'] as const,
  list: (artifactId?: string, collectionId?: string) =>
    [...artifactGroupKeys.all, { artifactId, collectionId }] as const,
};

export function useArtifactGroups(
  artifactId: string | undefined,
  collectionId: string | undefined
): UseQueryResult<Group[], Error> {
  return useQuery({
    queryKey: artifactGroupKeys.list(artifactId, collectionId),
    queryFn: async (): Promise<Group[]> => {
      // Verify parameters
      // Call API with artifact_id and collection_id params
      // Handle response and sort by position
    },
    enabled: !!artifactId && !!collectionId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
```

### Test Cases

- [ ] Hook fetches groups for artifact-collection pair
- [ ] Hook returns empty array on API error
- [ ] Query only runs when both parameters provided
- [ ] Cache key includes both artifactId and collectionId
- [ ] Stale time set to 10 minutes
- [ ] Can handle 100+ artifacts without memory leak

### Quality Gates

- [ ] Unit test coverage ≥80%
- [ ] TypeScript strict mode
- [ ] ESLint passes
- [ ] JSDoc example is accurate

---

## Task P1-T3: Create fetchArtifactGroups API Client Function

**Type**: Feature | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Create a new API client function for directly fetching groups for an artifact (used in tests and potentially in useArtifactGroups hook). This function wraps the API call with proper error handling.

### Acceptance Criteria

- [x] Function created at `skillmeat/web/lib/api/groups.ts` (or enhance existing if not present)
- [x] Function name: `fetchArtifactGroups(artifactId: string, collectionId: string)`
- [x] Returns: `Promise<Group[]>`
- [x] Calls API endpoint: `GET /groups?collection_id={collectionId}&artifact_id={artifactId}`
- [x] Throws error if API fails (no fallback at this layer)
- [x] JSDoc comment documents parameters, return type, errors thrown

### Implementation Details

**File**: `skillmeat/web/lib/api/groups.ts`

```typescript
export async function fetchArtifactGroups(
  artifactId: string,
  collectionId: string
): Promise<Group[]> {
  const params = new URLSearchParams({
    collection_id: collectionId,
    artifact_id: artifactId,
  });

  const response = await apiRequest<Group[]>(`/groups?${params.toString()}`);
  return response.sort((a, b) => a.position - b.position);
}
```

### Test Cases

- [ ] Function calls correct API endpoint
- [ ] Returns groups sorted by position
- [ ] Throws error on API failure
- [ ] Handles empty response gracefully

### Quality Gates

- [ ] Unit test ≥80% coverage
- [ ] TypeScript strict mode
- [ ] Exports from barrel (if using)

---

## Task P1-T4: Add Barrel Export for New Hooks

**Type**: Chore | **Story Points**: 0.5 | **Estimated Time**: 1-2 hours

### Description

Update the hooks barrel export (`skillmeat/web/hooks/index.ts`) to include the new `useArtifactGroups()` hook. This ensures the hook can be imported via `@/hooks` (canonical import path).

### Acceptance Criteria

- [x] `useArtifactGroups` added to `hooks/index.ts` exports
- [x] Export statement uses named export: `export { useArtifactGroups } from './use-artifact-groups'`
- [x] Import in hook consumer works: `import { useArtifactGroups } from '@/hooks'`
- [x] No circular dependencies created
- [x] ESLint passes

### Implementation Details

**File**: `skillmeat/web/hooks/index.ts`

Add line:
```typescript
export { useArtifactGroups } from './use-artifact-groups';
```

### Test Cases

- [ ] `import { useArtifactGroups } from '@/hooks'` resolves correctly
- [ ] No TypeScript errors from barrel export
- [ ] No circular dependency warnings

---

## Task P1-T5: Implement Cache Invalidation Strategy

**Type**: Feature | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Document and test the cache invalidation strategy for group-related queries. When groups are created, updated, or deleted (via mutations in `use-groups.ts`), the cache must be properly invalidated so card components show updated data.

### Acceptance Criteria

- [x] Cache key structure supports hierarchical invalidation
- [x] Group mutations (create, update, delete) invalidate `groupKeys.list(collectionId)`
- [x] Mutations that modify artifact-group relationships invalidate `artifactGroupKeys.list(artifactId, collectionId)`
- [x] Documentation in code comments explains invalidation strategy
- [x] Test verifies invalidation fires on mutation success
- [x] Test verifies cards re-fetch data after invalidation

### Implementation Details

The existing `useCreateGroup()`, `useUpdateGroup()`, `useDeleteGroup()` mutations in `use-groups.ts` already implement `queryClient.invalidateQueries()`. Verify they invalidate:

```typescript
// In useCreateGroup, useUpdateGroup, useDeleteGroup mutations:
onSuccess: (result, variables) => {
  queryClient.invalidateQueries({
    queryKey: groupKeys.list(collectionId)
  });
  // Also invalidate artifact-group cache if mutation affects artifact groups
}
```

### Test Cases

- [ ] Create group mutation invalidates collection's groups cache
- [ ] Update group mutation invalidates group detail and collection list
- [ ] Delete group mutation invalidates collection's groups cache
- [ ] Cards re-fetch after mutation-triggered invalidation
- [ ] No duplicate invalidation calls (efficient)

### Quality Gates

- [ ] Tests verify invalidation strategy
- [ ] Code comments explain cache key hierarchy

---

## Task P1-T6: Write Unit Tests for Phase 1

**Type**: Testing | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Comprehensive unit tests for all hooks and API client functions created in Phase 1. Tests should cover happy path, error scenarios, and cache behavior.

### Acceptance Criteria

- [x] Unit tests for `useGroups()` hook
- [x] Unit tests for `useArtifactGroups()` hook
- [x] Unit tests for `fetchArtifactGroups()` function
- [x] Test coverage: ≥80% for all code
- [x] Happy path: fetch succeeds, data returned correctly
- [x] Error path: fetch fails, fallback/error returned
- [x] Cache behavior: stale time configured correctly
- [x] Query key structure: correct for invalidation
- [x] All tests pass: `pnpm test`
- [x] No TypeScript errors in tests

### Test Structure

**File**: `skillmeat/web/__tests__/hooks/use-groups.test.ts` (new or enhance existing)

```typescript
describe('useGroups', () => {
  it('fetches and sorts groups by position', async () => { /* ... */ });
  it('returns empty array on API error', async () => { /* ... */ });
  it('only fetches when collectionId is defined', () => { /* ... */ });
  it('uses 5-minute stale time', () => { /* ... */ });
});

describe('useArtifactGroups', () => {
  it('fetches groups for artifact in collection', async () => { /* ... */ });
  it('requires both artifactId and collectionId', () => { /* ... */ });
  it('returns empty array on error', async () => { /* ... */ });
});

describe('fetchArtifactGroups', () => {
  it('calls correct API endpoint', async () => { /* ... */ });
  it('throws on API error', async () => { /* ... */ });
});
```

### Quality Gates

- [ ] All tests pass
- [ ] Coverage report shows ≥80%
- [ ] No TypeScript errors
- [ ] Mock setup clear and maintainable

---

## Task P1-T7: Document Phase 1 Implementation

**Type**: Documentation | **Story Points**: 1 | **Estimated Time**: 2-3 hours

### Description

Write JSDoc comments for all exported functions and hooks. Create brief architecture documentation explaining cache key strategy and error handling patterns.

### Acceptance Criteria

- [x] All exported hooks have JSDoc with:
  - Purpose (one-liner)
  - Parameter descriptions with types
  - Return type description
  - Usage example
  - Error handling notes
- [x] Cache key structure documented in code comments
- [x] Error handling strategy documented
- [x] File-level comment explaining module purpose
- [x] No "TODO" or "FIXME" comments left in Phase 1 code

### Example JSDoc Format

```typescript
/**
 * Fetch groups for a specific artifact within a collection.
 *
 * Groups are cached for 10 minutes to reduce API calls while still
 * providing fresh data after mutations.
 *
 * @param artifactId - ID of the artifact (required)
 * @param collectionId - ID of the collection (required)
 * @returns Query result with groups array, loading state, and error
 *
 * @example
 * ```tsx
 * const { data: groups, isLoading } = useArtifactGroups(artifactId, collectionId);
 * if (isLoading) return <Skeleton />;
 * if (error) return null; // Graceful fallback
 * return groups.map(group => <Badge key={group.id}>{group.name}</Badge>);
 * ```
 */
```

### Quality Gates

- [ ] JSDoc covers all public functions
- [ ] Examples are accurate and runnable
- [ ] No broken links or references

---

## Task P1-T8: Code Review & Integration Test

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Self-review and peer review of all Phase 1 code. Run integration tests to verify hooks work together with existing components (prepare for Phase 2).

### Acceptance Criteria

- [x] Self-review: code follows project conventions
- [x] Self-review: TypeScript strict mode passes
- [x] Self-review: ESLint passes with zero warnings
- [x] Peer review: at least one approval from senior engineer
- [x] Integration test: `useGroups()` works with existing artifact queries
- [x] Integration test: `useArtifactGroups()` integrates with UnifiedCard (dry run)
- [x] No breaking changes to existing APIs
- [x] Backward compatible: existing components unaffected

### Verification Steps

```bash
# Self-review checklist
pnpm type-check              # Zero TypeScript errors
pnpm lint                    # Zero ESLint warnings
pnpm test                    # All tests pass
pnpm test -- --coverage      # Coverage report ≥80%

# Integration test (manual)
# - Use hook in a test component
# - Verify it works with useCollectionContext
# - Verify cache keys don't collide with other queries
```

### Quality Gates

- [ ] Code review approved
- [ ] No integration issues found
- [ ] Ready for Phase 2 (other phases depend on Phase 1)

---

## Dependencies & Prerequisites

### External Dependencies
- React 19+ (already in project)
- TanStack Query v5+ (already in project)
- TypeScript 5+ (already in project)

### Internal Dependencies
- `@/lib/api` — apiRequest function
- `@/types/groups` — Group type definition
- `useCollectionContext()` hook (to be used by card components in Phase 2)

### Prerequisite: Backend Readiness
- [ ] Verify backend `/groups` API endpoint exists and works
- [ ] Verify API response format matches `GroupListResponse` type
- [ ] Verify backend supports filtering: `?collection_id=X&artifact_id=Y`
- [ ] Test API manually with curl or Postman before implementation

---

## Definition of Done

Phase 1 is complete when:

1. **Code Delivery**:
   - [x] `useArtifactGroups()` hook implemented and exported
   - [x] `fetchArtifactGroups()` API client function implemented
   - [x] Existing `useGroups()` hook verified and properly configured
   - [x] All hooks use hierarchical cache keys for invalidation
   - [x] Error handling with graceful fallbacks implemented
   - [x] Barrel export updated (`hooks/index.ts`)

2. **Testing**:
   - [x] ≥80% unit test coverage across all Phase 1 code
   - [x] All unit tests passing (`pnpm test`)
   - [x] Integration test: hooks work together without conflicts
   - [x] Manual testing: hooks integrate with existing components

3. **Quality**:
   - [x] TypeScript strict mode: zero errors
   - [x] ESLint: zero errors, zero warnings
   - [x] Code review: approved by 1+ senior engineer
   - [x] JSDoc: all exported functions documented with examples
   - [x] No breaking changes to existing APIs

4. **Documentation**:
   - [x] JSDoc comments complete
   - [x] Cache key strategy documented in code
   - [x] Error handling strategy documented

---

## Handoff to Phase 2

**Deliverables for Phase 2**:

1. Working `useGroups()` hook that Phase 2 can call for Collection filter dropdown
2. Working `useArtifactGroups()` hook that Phase 2 uses in card components
3. Tested cache key hierarchy that Phase 3-5 can safely use
4. Clear error handling pattern that card components can adopt
5. Documentation of hook usage patterns for Phase 2 engineers

**Integration Points Phase 2 Must Know**:

- Call `useCollectionContext()` to detect if in specific collection view
- Use `useArtifactGroups()` only when in specific collection context (avoid unnecessary calls)
- On mutation, hooks automatically refetch due to cache invalidation
- Graceful fallback: missing data renders no badges (not an error state)

---

## Rollback Plan

If Phase 1 cannot complete within timeline or discovers blocking issues:

1. **Short-term delay**: Push Phase 1 completion by 1-2 days; adjust overall timeline
2. **Scope reduction**: Focus on `useArtifactGroups()` and `fetchArtifactGroups()`; defer `useGroups()` enhancement to Phase 2
3. **Full rollback**: Use existing `useGroups()` hook without enhancement; Phase 2-5 proceed with less-optimized caching

**Rollback Criteria**: If >20% of Phase 1 tests fail due to API contract mismatch or type definition issues.

---

**End of Phase 1 Tasks**

Next: Phase 2 - Collection Badges on Cards
