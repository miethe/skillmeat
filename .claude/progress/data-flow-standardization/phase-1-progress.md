---
type: progress
prd: data-flow-standardization
phase: 1
title: Frontend Standardization
status: planning
started: '2026-02-04'
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 11
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: TASK-1.1
  description: Change useArtifacts() stale time from 30sec to 5min in hooks/useArtifacts.ts:345
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 15m
  priority: high
- id: TASK-1.2
  description: Add stale time (5min) to useArtifact() in hooks/useArtifacts.ts:353-360
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 15m
  priority: high
- id: TASK-1.3
  description: Add stale time (5min) to useProject() in hooks/useProjects.ts:241-248
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 15m
  priority: medium
- id: TASK-1.4
  description: Add ['deployments'], ['projects'] to useRollback() invalidation in
    hooks/use-snapshots.ts:229-232
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 20m
  priority: high
- id: TASK-1.5
  description: Add ['deployments'] to context sync push/pull/resolve in hooks/use-context-sync.ts:59,82,109
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 30m
  priority: medium
- id: TASK-1.6
  description: Add ['artifacts'] to useAddTagToArtifact() and useRemoveTagFromArtifact()
    in hooks/use-tags.ts:206-210,232-237
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 20m
  priority: high
- id: TASK-1.7
  description: Add ['tags', 'artifact'] prefix invalidation to useDeleteTag() in hooks/use-tags.ts:176-182
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 15m
  priority: medium
- id: TASK-1.8
  description: Add ['artifacts'] to useInstallListing() in hooks/useMarketplace.ts:160-162
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 15m
  priority: medium
- id: TASK-1.9
  description: Add ['artifacts'] to useCacheRefresh() in hooks/useCacheRefresh.ts:66-77
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 15m
  priority: medium
- id: TASK-1.10
  description: Add ['deployments'], ['collections'] to useDeleteArtifact() or deprecate
    in hooks/useArtifacts.ts:413-416
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 20m
  priority: medium
- id: TASK-1.11
  description: Document stale time strategy in skillmeat/web/CLAUDE.md
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  - TASK-1.4
  - TASK-1.5
  - TASK-1.6
  - TASK-1.7
  - TASK-1.8
  - TASK-1.9
  - TASK-1.10
  estimated_effort: 30m
  priority: low
parallelization:
  batch_1:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  - TASK-1.4
  - TASK-1.5
  - TASK-1.6
  - TASK-1.7
  - TASK-1.8
  - TASK-1.9
  - TASK-1.10
  batch_2:
  - TASK-1.11
  critical_path:
  - TASK-1.1
  - TASK-1.11
  estimated_total_time: 4-6h
blockers: []
success_criteria:
- id: SC-1
  description: All stale times standardized per domain table
  status: pending
- id: SC-2
  description: All cache invalidations complete per invalidation graph
  status: pending
- id: SC-3
  description: Documentation updated in web/CLAUDE.md
  status: pending
files_modified:
- skillmeat/web/hooks/useArtifacts.ts
- skillmeat/web/hooks/useProjects.ts
- skillmeat/web/hooks/use-snapshots.ts
- skillmeat/web/hooks/use-context-sync.ts
- skillmeat/web/hooks/use-tags.ts
- skillmeat/web/hooks/useMarketplace.ts
- skillmeat/web/hooks/useCacheRefresh.ts
- skillmeat/web/CLAUDE.md
schema_version: 2
doc_type: progress
feature_slug: data-flow-standardization
---

# data-flow-standardization - Phase 1: Frontend Standardization

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/data-flow-standardization/phase-1-progress.md -t TASK-X -s completed
```

---

## Objective

Standardize frontend TanStack Query stale times and cache invalidation patterns according to the data-flow-patterns reference. This phase ensures all frontend hooks follow the standardized domain-based stale times (5min browsing, 30sec interactive, 2min deployments) and complete the cache invalidation graph.

---

## Implementation Notes

### Architectural Decisions

**Stale Time Strategy**:
- **Browsing queries** (artifacts, projects, collections): 5 minutes
- **Interactive/monitoring** (stats, tags, cache status): 30 seconds
- **Deployment-related** (deployments, snapshots, context sync): 2 minutes

**Cache Invalidation Graph**:
Per `.claude/context/key-context/data-flow-patterns.md`, every mutation must invalidate all affected query keys. This phase completes missing invalidation edges discovered during the data flow audit.

### Patterns and Best Practices

**Reference**: `.claude/context/key-context/data-flow-patterns.md`

All changes follow the standardized stale time table and invalidation graph defined in the data flow patterns reference. Each hook modification:

1. Adds explicit `staleTime` to `useQuery()` calls
2. Adds missing `queryClient.invalidateQueries()` calls per the invalidation graph
3. Uses array-based query key prefixes for bulk invalidation (e.g., `['artifacts']` invalidates all artifact queries)

**Example pattern**:
```typescript
// Before (no stale time)
const { data } = useQuery({ queryKey: ['artifact', id], queryFn: ... });

// After (5min stale time for browsing)
const { data } = useQuery({
  queryKey: ['artifact', id],
  queryFn: ...,
  staleTime: 5 * 60 * 1000  // 5 minutes
});
```

**Invalidation pattern**:
```typescript
// Mutation invalidates related queries
await queryClient.invalidateQueries({ queryKey: ['artifacts'] });
await queryClient.invalidateQueries({ queryKey: ['deployments'] });
```

### Known Gotchas

**Stale Time Units**: TanStack Query expects milliseconds, not seconds. Always multiply by 1000.

**Invalidation Scope**:
- `['artifacts']` invalidates ALL artifact queries (list + detail)
- `['artifacts', id]` invalidates ONLY that specific artifact

**useDeleteArtifact() Decision** (TASK-1.10):
This hook may be deprecated in favor of API-level deletion. If still in use, add proper invalidations. If deprecated, remove or mark as deprecated with warning.

**Context Sync Multi-Invalidation** (TASK-1.5):
Push/pull/resolve operations affect multiple domains. All three operations must invalidate `['deployments']` to reflect file system changes.

### Development Setup

No special setup required. Standard web development environment:

```bash
cd skillmeat/web
pnpm install
pnpm dev
```

Run tests after changes:
```bash
pnpm test hooks/useArtifacts
pnpm test hooks/useProjects
# ... etc
```

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
