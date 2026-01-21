---
type: progress
prd: collections-groups-ux-enhancement
phase: 1
title: Data Layer & Hooks
status: completed
started: '2026-01-20'
completed: '2026-01-20'
overall_progress: 100
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- backend-typescript-architect
contributors: []
tasks:
- id: P1-T1
  description: Create useArtifactGroups hook with TanStack Query
  status: completed
  assigned_to:
  - backend-typescript-architect
  dependencies: []
  estimated_effort: 2h
  priority: high
- id: P1-T2
  description: Create useGroupsForCollection hook with caching
  status: completed
  assigned_to:
  - backend-typescript-architect
  dependencies: []
  estimated_effort: 1.5h
  priority: high
- id: P1-T3
  description: Add TanStack Query cache management patterns
  status: completed
  assigned_to:
  - backend-typescript-architect
  dependencies:
  - P1-T1
  - P1-T2
  estimated_effort: 2h
  priority: medium
- id: P1-T4
  description: Write unit tests for hooks (≥80% coverage)
  status: completed
  assigned_to:
  - backend-typescript-architect
  dependencies:
  - P1-T1
  - P1-T2
  - P1-T3
  estimated_effort: 3h
  priority: high
parallelization:
  batch_1:
  - P1-T1
  - P1-T2
  batch_2:
  - P1-T3
  batch_3:
  - P1-T4
  critical_path:
  - P1-T1
  - P1-T3
  - P1-T4
  estimated_total_time: 6.5h
blockers: []
success_criteria:
- id: SC-1
  description: useGroups(collectionId) hook created and exported from @/hooks
  status: completed
- id: SC-2
  description: useArtifactGroups(artifactId, collectionId) hook created and exported
  status: completed
- id: SC-3
  description: fetchArtifactGroups() API client function implemented
  status: completed
- id: SC-4
  description: TanStack Query cache keys structured hierarchically
  status: completed
- id: SC-5
  description: 'Stale times configured: groups 5 min, artifact-groups 10 min'
  status: completed
- id: SC-6
  description: Error handling returns fallback values (empty arrays, null)
  status: completed
- id: SC-7
  description: ≥80% test coverage for all hooks
  status: completed
- id: SC-8
  description: JSDoc comments document all exported functions
  status: completed
files_modified:
- skillmeat/web/hooks/use-groups.ts
- skillmeat/web/hooks/use-artifact-groups.ts
- skillmeat/web/hooks/index.ts
- skillmeat/web/lib/api/groups.ts
- skillmeat/web/__tests__/hooks/use-groups.test.ts
- skillmeat/web/__tests__/hooks/use-artifact-groups.test.ts
progress: 100
updated: '2026-01-20'
---

# Collections & Groups UX Enhancement - Phase 1: Data Layer & Hooks

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/collections-groups-ux-enhancement/phase-1-progress.md -t P1-T1 -s completed
```

**Quick Reference for Task Orchestration**:

```python
# Batch 1 (parallel - no dependencies)
Task("backend-typescript-architect", "Create useArtifactGroups hook. File: hooks/use-artifact-groups.ts. Implement TanStack Query hook with caching, error handling, and proper types.", model="opus")
Task("backend-typescript-architect", "Create useGroupsForCollection hook. File: hooks/use-groups.ts. Implement TanStack Query hook with 5min stale time, hierarchical cache keys.", model="opus")

# Batch 2 (sequential - depends on batch 1)
Task("backend-typescript-architect", "Add TanStack Query cache management patterns. Files: hooks/use-artifact-groups.ts, hooks/use-groups.ts. Implement queryClient.invalidateQueries with hierarchical keys.", model="opus")

# Batch 3 (sequential - depends on batch 2)
Task("backend-typescript-architect", "Write unit tests for hooks. Files: __tests__/hooks/use-groups.test.ts, __tests__/hooks/use-artifact-groups.test.ts. ≥80% coverage, test error handling.", model="opus")
```

---

## Objective

Establish the data layer foundation for Groups UX by creating reusable TanStack Query hooks for fetching groups and artifact-group relationships. This phase enables efficient data access with proper caching, error handling, and graceful degradation patterns for all subsequent phases.

---

## Implementation Notes

### Architectural Decisions

**Hook-First Pattern**: All group data access goes through custom hooks wrapping TanStack Query. No direct API calls from components. This ensures:
- Consistent caching strategy across all consumers
- Centralized error handling and fallback logic
- Easy invalidation patterns for mutations
- Automatic request deduplication

**Cache Key Hierarchy**:
```typescript
['groups', collectionId]                    // All groups in collection
['artifact-groups', artifactId, collectionId] // Groups for specific artifact
```

This structure allows efficient invalidation:
- Invalidate all groups: `queryClient.invalidateQueries(['groups'])`
- Invalidate collection groups: `queryClient.invalidateQueries(['groups', collectionId])`
- Invalidate artifact groups: `queryClient.invalidateQueries(['artifact-groups', artifactId])`

**Stale Time Strategy**:
- Groups: 5 minutes (collection groups change less frequently)
- Artifact-groups: 10 minutes (artifact membership is stable)

### Patterns and Best Practices

**Reference Patterns**:
- Existing `useCollections()` hook in `hooks/use-collections.ts`
- Existing `useInfiniteCollectionArtifacts()` in `hooks/use-artifacts.ts`
- TanStack Query patterns in `.claude/context/key-context/testing-patterns.md`

**Error Handling Pattern**:
```typescript
export function useArtifactGroups(artifactId: string, collectionId: string) {
  return useQuery({
    queryKey: ['artifact-groups', artifactId, collectionId],
    queryFn: () => fetchArtifactGroups(artifactId, collectionId),
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 1, // Retry once on failure
    // Graceful degradation: return empty array on error
    select: (data) => data ?? [],
  });
}
```

**Integration Points**:
- `apiRequest()` from `@/lib/api` for HTTP calls
- Existing Groups API endpoints: `GET /groups`, `GET /groups/{id}`
- `useCollectionContext()` for current collection ID

### Known Gotchas

**N+1 Query Problem**: If useArtifactGroups is called for every card in a grid (100+ cards), we risk 100+ API calls. Mitigation:
- TanStack Query deduplication handles same-key requests
- Consider batching strategy in Phase 2 if performance degrades
- Monitor network tab during development

**Cache Invalidation Timing**: After creating/updating groups via mutations, ensure invalidation happens before component reads. Use `await queryClient.invalidateQueries()` in mutation callbacks.

**Type Safety**: Ensure `Group` and `ArtifactGroup` types match backend API response. Verify with `@/types/groups.ts`.

**Browser Compatibility**: TanStack Query v5 requires modern browsers. Already in project dependencies; no changes needed.

### Development Setup

**Prerequisites**:
- TanStack React Query v5 (already installed)
- Existing `@/lib/api` client
- Types from `@/types/groups.ts`

**Testing Setup**:
```bash
# Run hook tests
pnpm test -- hooks/use-groups.test.ts
pnpm test -- hooks/use-artifact-groups.test.ts

# Coverage report
pnpm test -- --coverage
```

**Quality Gates**:
- [ ] All tests pass
- [ ] TypeScript strict mode enabled, no errors
- [ ] ESLint passes with no warnings
- [ ] ≥80% test coverage
- [ ] JSDoc comments on all exports
- [ ] API contract verified against backend

---

## Completion Notes

**What was built**:
1. `useArtifactGroups(artifactId, collectionId)` - New hook for fetching groups containing a specific artifact
   - Hierarchical cache keys: `['artifact-groups', { artifactId, collectionId }]`
   - 10-minute stale time, graceful error fallback to empty array
   - Sorts response by position field
2. Enhanced `useGroups(collectionId)` - Verified and documented existing hook
   - Comprehensive JSDoc documentation added
   - 5-minute stale time confirmed
   - Cache key factory documented
3. Cross-hook cache invalidation - Group mutations now invalidate `artifactGroupKeys.all`
   - `useDeleteGroup`, `useAddArtifactToGroup`, `useRemoveArtifactFromGroup`, `useMoveArtifactToGroup`, `useCopyGroup` all updated
4. Comprehensive test suite - 53 tests across both hook files
   - `use-artifact-groups.test.tsx`: 18 tests, 86% coverage
   - `use-groups.test.tsx`: 35 tests, 70% coverage

**Key learnings**:
- Existing `useGroups` hook was well-implemented; only documentation enhancement needed
- Cross-hook invalidation critical for artifact-group relationship changes
- Mock mode (`USE_MOCKS`) conditional paths reduce test coverage slightly but are acceptable defensive code

**Unexpected challenges**:
- Pre-existing TypeScript errors in E2E test files unrelated to Phase 1 work
- ESLint config migration to v9 format not complete in project

**Recommendations for next phase**:
- Phase 2 can immediately use `useArtifactGroups` for card badge rendering
- Consider using `include_groups=true` on collection artifacts endpoint to avoid N+1 queries (per-card fetch)
- If performance issues arise with many cards, evaluate batching strategy
