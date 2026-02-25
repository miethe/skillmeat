---
type: progress
schema_version: 2
doc_type: progress
prd: similar-artifacts
feature_slug: similar-artifacts
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similar-artifacts-v1.md
phase: 5
phase_6_included: true
title: 'Phase 5-6: Collection Consolidation View + CLI Integration'
status: pending
started: '2026-02-25'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 18
completed_tasks: 17
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- ui-engineer-enhanced
contributors:
- backend-architect
- frontend-developer
tasks:
- id: SA-P5-001
  description: SimilarityService — cluster grouping
  status: completed
  assigned_to:
  - backend-architect
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2pts
  priority: high
- id: SA-P5-002
  description: Repository — ignored pair methods
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: SA-P5-003
  description: Consolidation clusters API endpoint
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P5-001
  estimated_effort: 2pts
  priority: high
- id: SA-P5-004
  description: Consolidation skip action endpoint
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P5-002
  estimated_effort: 1pt
  priority: high
- id: SA-P5-005
  description: useConsolidationClusters hook
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P5-003
  - SA-P5-004
  estimated_effort: 1pt
  priority: high
- id: SA-P5-006
  description: Consolidation page route
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P5-005
  estimated_effort: 0.5pt
  priority: medium
- id: SA-P5-007
  description: ConsolidationClusterList component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P5-005
  estimated_effort: 2pts
  priority: high
- id: SA-P5-008
  description: ConsolidationClusterDetail component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P5-007
  estimated_effort: 3pts
  priority: critical
- id: SA-P5-009
  description: Auto-snapshot gate for merge/replace
  status: completed
  assigned_to:
  - python-backend-engineer
  - backend-architect
  dependencies:
  - SA-P5-008
  estimated_effort: 2pts
  priority: critical
- id: SA-P5-010
  description: Un-ignore management UI
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P5-007
  estimated_effort: 1pt
  priority: medium
- id: SA-P5-011
  description: Collection page toolbar button
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P5-006
  estimated_effort: 0.5pt
  priority: medium
- id: SA-P5-012
  description: E2E test — consolidation merge
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P5-009
  estimated_effort: 1pt
  priority: high
- id: SA-P5-013
  description: Integration tests — consolidation API
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P5-003
  - SA-P5-004
  estimated_effort: 1pt
  priority: high
- id: SA-P6-001
  description: skillmeat similar CLI command
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2pts
  priority: high
- id: SA-P6-002
  description: skillmeat consolidate — interactive wizard
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P5-001
  estimated_effort: 2pts
  priority: high
- id: SA-P6-003
  description: skillmeat consolidate — non-interactive mode
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P6-002
  estimated_effort: 1pt
  priority: medium
- id: SA-P6-004
  description: Unit tests — CLI commands
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SA-P6-001
  - SA-P6-002
  - SA-P6-003
  estimated_effort: 1pt
  priority: high
- id: SA-P6-005
  description: Manual smoke test — help strings
  status: completed
  assigned_to:
  - orchestrator
  dependencies:
  - SA-P6-001
  - SA-P6-002
  estimated_effort: 0pts
  priority: medium
parallelization:
  batch_1:
  - SA-P5-001
  - SA-P5-002
  - SA-P6-001
  batch_2:
  - SA-P5-003
  - SA-P5-004
  - SA-P6-002
  batch_3:
  - SA-P5-005
  - SA-P5-013
  - SA-P6-003
  batch_4:
  - SA-P5-006
  - SA-P5-007
  - SA-P6-004
  batch_5:
  - SA-P5-008
  - SA-P5-010
  - SA-P5-011
  - SA-P6-005
  batch_6:
  - SA-P5-009
  batch_7:
  - SA-P5-012
  critical_path:
  - SA-P5-001
  - SA-P5-003
  - SA-P5-005
  - SA-P5-007
  - SA-P5-008
  - SA-P5-009
  - SA-P5-012
  estimated_total_time: 6-8 days
blockers: []
success_criteria:
- id: SC-P5-1
  description: GET /api/v1/artifacts/consolidation/clusters returns correct paginated
    clusters
  status: pending
- id: SC-P5-2
  description: Ignored pairs excluded from cluster list by default; toggle reveals
    them
  status: pending
- id: SC-P5-3
  description: Merge and Replace actions abort if auto-snapshot fails (never destructive
    without snapshot)
  status: pending
- id: SC-P5-4
  description: Skip marks pair ignored; un-ignore restores to active list
  status: pending
- id: SC-P5-5
  description: Consolidation page accessible from Collection page toolbar
  status: pending
- id: SC-P5-6
  description: E2E merge test passes with auto-snapshot verification
  status: pending
- id: SC-P5-7
  description: Integration tests for cluster and ignore/unignore endpoints pass
  status: pending
- id: SC-P5-8
  description: WCAG 2.1 AA contrast on all cluster table and detail view elements
  status: pending
- id: SC-P6-1
  description: skillmeat similar <artifact> exits 0 and renders Rich table
  status: pending
- id: SC-P6-2
  description: skillmeat similar --help and skillmeat consolidate --help render all
    options
  status: pending
- id: SC-P6-3
  description: skillmeat consolidate --non-interactive exits 0 with valid JSON
  status: pending
- id: SC-P6-4
  description: Non-TTY auto-detected; falls back to non-interactive with stderr warning
  status: pending
- id: SC-P6-5
  description: Auto-snapshot fires before Merge/Replace in interactive wizard
  status: pending
- id: SC-P6-6
  description: Unit tests pass using Click's CliRunner with mocked SimilarityService
  status: pending
- id: SC-P6-7
  description: task-completion-validator sign-off
  status: pending
files_modified:
- skillmeat/core/similarity.py
- skillmeat/cache/repositories.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/api/openapi.json
- skillmeat/web/hooks/similarity.ts
- skillmeat/web/app/collection/consolidate/page.tsx
- skillmeat/web/components/consolidation/consolidation-cluster-list.tsx
- skillmeat/web/components/consolidation/consolidation-cluster-detail.tsx
- skillmeat/cli.py
- tests/test_consolidation_api.py
- tests/test_cli_similar.py
progress: 94
updated: '2026-02-25'
---

# Similar Artifacts - Phase 5-6: Collection Consolidation View + CLI Integration

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/similar-artifacts/phase-5-6-progress.md -t TASK-ID -s completed
```

For batch updates:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/similar-artifacts/phase-5-6-progress.md --updates "SA-P5-001:completed,SA-P5-002:completed,SA-P6-001:completed"
```

---

## Objective

Phase 5 delivers the dedicated Collection Consolidation page at `/collection/consolidate`, exposing similarity clusters with merge/replace/skip actions gated by auto-snapshot verification. Phase 6 adds CLI parity via `skillmeat similar` and `skillmeat consolidate` commands with interactive and non-interactive modes. Combined: 13 backend + frontend + CLI tasks across 7 batches with 6-8 day estimated duration.

---

## Implementation Notes

### Architectural Decisions

**Cluster grouping approach**: SimilarityService extends with `get_consolidation_clusters()` method that leverages existing `find_similar()` logic, filters by `ignored` flag, and implements cursor-based pagination for 500+ artifact collections.

**Auto-snapshot as critical gate**: Merge and Replace actions must complete auto-snapshot step before proceeding. If snapshot fails, action is aborted with clear error messaging. This prevents data loss and ensures audit trail.

**CLI direct import strategy**: Both `skillmeat similar` and `skillmeat consolidate` commands import `SimilarityService` directly (Python code path, not HTTP) for performance. This keeps latency under 3s for typical collections.

**Reuse of existing components**: Consolidation detail view reuses existing `DiffViewer` component and `VersionMergeService` for merge operations — no reimplementation.

### Patterns and Best Practices

- **React Query cursor pagination**: useConsolidationClusters hook uses infinite query pattern with 30s staleTime for interactive freshness per data-flow-patterns.md.
- **Optimistic updates**: ignore/unignore mutations use React Query optimistic updates to reflect changes immediately while mutations complete in background.
- **Rich table formatting in CLI**: `skillmeat similar` output uses Rich library for clean TTY tables; non-TTY pipes plain text without color codes.
- **Click CliRunner testing**: All CLI commands mockable via Click's CliRunner for unit testing without actual filesystem or DB access.

### Known Gotchas

- **VersionMergeService API contract**: The auto-snapshot gate (SA-P5-009) requires `VersionMergeService` to expose a callable method that returns snapshot confirmation before proceeding. If existing API is async-only or HTTP-based, a design spike is needed.
- **Cluster grouping performance**: O(N^2) cluster grouping for large collections. Implement keyword-score pre-filter (top-K candidates) to keep runtime under 5s for 500 artifacts.
- **Interactive wizard in CI**: Click's `prompt()` calls must be mockable with default values for CliRunner test compatibility. Use `click.prompt(..., default=...)` throughout.
- **Non-TTY detection**: CLI must auto-detect non-TTY environments (piped output, CI) and fall back to `--non-interactive` mode with warning on stderr.

### Development Setup

**Dependencies**: Phase 1 complete (SimilarityService available, DuplicatePair.ignored migration merged, repository methods in place).

**Test fixtures**: Ensure test DB includes 2-3 known similar artifact pairs for integration test setup.

**Frontend mocking**: Before SA-P5-003 API endpoint merges, frontend team can mock `useConsolidationClusters` to return test cluster data.

---

## Orchestration Quick Reference

Execute batches sequentially as dependencies resolve:

### Batch 1 (No dependencies)
```
Task("python-backend-engineer", "
Implement SA-P5-001 and SA-P5-002:
- SA-P5-001: Extend SimilarityService with get_consolidation_clusters() method
  File: skillmeat/core/similarity.py
  Must return paginated SimilarityCluster list, exclude ignored pairs, sort by max_score
  Includes unit tests for cluster grouping logic
- SA-P5-002: Add mark_pair_ignored() and unmark_pair_ignored() methods to DuplicatePair repository
  File: skillmeat/cache/repositories.py
  Includes unit tests for mark/unmark round-trip
")

Task("python-backend-engineer", "
Implement SA-P6-001: Add 'skillmeat similar' CLI command
File: skillmeat/cli.py
Rich table output with columns: Rank, Name, Type, Score %, Match Type
Options: --limit, --min-score, --source (collection/marketplace/all)
Handle empty results with descriptive message
")
```

### Batch 2 (After Batch 1)
```
Task("python-backend-engineer", "
Implement SA-P5-003 and SA-P5-004:
- SA-P5-003: Add GET /api/v1/artifacts/consolidation/clusters endpoint
  File: skillmeat/api/routers/artifacts.py
  Query params: min_score, limit, cursor
  Returns SimilarityClusterDTO with cursor pagination
  Includes integration tests
- SA-P5-004: Add POST/DELETE ignore endpoints
  Files: skillmeat/api/routers/artifacts.py, skillmeat/api/schemas/artifacts.py
  Calls repository mark_pair_ignored/unmark_pair_ignored
  Includes ownership enforcement and integration tests
")

Task("python-backend-engineer", "
Implement SA-P6-002: Add 'skillmeat consolidate' interactive wizard
File: skillmeat/cli.py
TTY detection with interactive cluster loop
Rich Panel display for each cluster
Merge/Replace/Skip/Quit prompts
Auto-snapshot gate before Merge/Replace
Graceful Quit on user exit
")
```

### Batch 3 (After Batch 2)
```
Task("frontend-developer", "
Implement SA-P5-005: Create useConsolidationClusters React Query hook
File: skillmeat/web/hooks/similarity.ts
Infinite query with cursor pagination
staleTime: 30s for interactive freshness
Provide ignorePair() and unignorePair() mutations
Optimistic update on mutation
")

Task("python-backend-engineer", "
Implement SA-P5-013: Integration tests for consolidation API
File: tests/test_consolidation_api.py
Test cases: happy path clusters, empty result, cursor pagination
Test ignored pairs excluded by default
Test ignore/unignore round-trip
Use test DB with known-similar fixtures
")

Task("python-backend-engineer", "
Implement SA-P6-003: Add --non-interactive mode to consolidate command
File: skillmeat/cli.py
--non-interactive / -n flag outputs JSON
--output=text for plain text variant
Non-TTY auto-detection with stderr warning
JSON schema: { 'clusters': [...], 'total_count': N }
")
```

### Batch 4 (After Batch 3)
```
Task("frontend-developer", "
Implement SA-P5-006: Create consolidation page route
File: skillmeat/web/app/collection/consolidate/page.tsx
Server component with client component ConsolidationClusterList
Route accessible at /collection/consolidate
Include empty state (no clusters found)
")

Task("ui-engineer-enhanced", "
Implement SA-P5-007: Create ConsolidationClusterList component
File: skillmeat/web/components/consolidation/consolidation-cluster-list.tsx
Table with columns: artifact count, type badge, highest similarity score, primary artifact name
Click row opens ConsolidationClusterDetail modal
Load More button for cursor pagination
Show ignored-pairs toggle (show/hide ignored)
Accessible table with correct aria attributes
")

Task("python-backend-engineer", "
Implement SA-P6-004: Unit tests for CLI commands
File: tests/test_cli_similar.py
Use Click's CliRunner with mocked SimilarityService
Test cases: similar happy path, empty result, invalid artifact
Test consolidate non-interactive JSON output, text output, mock TTY flow
All tests exit 0 on happy paths, exit 1 on error with message
")
```

### Batch 5 (After Batch 4)
```
Task("ui-engineer-enhanced", "
Implement SA-P5-008: Create ConsolidationClusterDetail component
File: skillmeat/web/components/consolidation/consolidation-cluster-detail.tsx
Side-by-side comparison using existing DiffViewer for content and metadata diffs
Three action buttons: Merge (keep primary, apply changes), Replace (keep primary, discard secondary), Skip (mark ignored)
Confirmation dialog before Merge and Replace
Skip marks pair ignored and removes from list
Reuse existing VersionMergeService for merge operations
")

Task("ui-engineer-enhanced", "
Implement SA-P5-010: Add un-ignore management UI to ConsolidationClusterList
File: skillmeat/web/components/consolidation/consolidation-cluster-list.tsx
Show ignored pairs toggle in cluster list
Visual indicator for ignored pairs (strikethrough or gray badge)
Un-ignore button on ignored pair rows
Un-ignore mutation restores to active list with optimistic update
")

Task("frontend-developer", "
Implement SA-P5-011: Add Consolidation button to Collection page toolbar
File: skillmeat/web/app/collection/page.tsx (or relevant toolbar component)
Button: 'Consolidate Collection' links to /collection/consolidate
Descriptive aria-label for accessibility
")

Task("orchestrator", "
Manual smoke test SA-P6-005: Verify CLI help strings and output
Run: skillmeat similar --help
Run: skillmeat consolidate --help
Run: skillmeat similar canvas-skill (or known artifact)
Verify: all options documented, output visually aligned in Rich format
")
```

### Batch 6 (After Batch 5)
```
Task("python-backend-engineer", "
Implement SA-P5-009: Auto-snapshot gate for merge/replace actions
File: skillmeat/api/routers/artifacts.py (consolidation merge/replace endpoints)
Before executing Merge or Replace: call VersionMergeService auto-snapshot API
If snapshot fails: abort action with blocking error 'Snapshot failed — action aborted'
Success: snapshot created → execute action → show success toast
Never proceed with destructive action without confirmed snapshot
Includes unit test for abort-on-snapshot-failure path
")
```

### Batch 7 (After Batch 6)
```
Task("frontend-developer", "
Implement SA-P5-012: E2E test for consolidation merge with auto-snapshot verification
File: tests/e2e/consolidation.spec.ts (Playwright)
Navigate to /collection/consolidate
Select cluster with known similar pair
Click Merge, confirm dialog
Verify confirmation toast shown
Verify auto-snapshot created (API check)
Verify secondary artifact removed from collection
")
```

---

## Completion Notes

(To be filled when phase is complete)

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
