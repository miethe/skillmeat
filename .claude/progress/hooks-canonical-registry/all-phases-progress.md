---
type: progress
prd: hooks-canonical-registry
phase: 1
title: Canonical Hooks Registry Implementation
status: completed
started: '2026-01-12'
completed:
- id: TASK-0.1
  description: Create hooks/index.ts canonical registry
  status: complete
  completed_date: '2026-01-12'
  completed_by: codebase-explorer
- id: TASK-0.2
  description: Audit all hook imports (73 files identified)
  status: complete
  completed_date: '2026-01-12'
  completed_by: codebase-explorer
overall_progress: 10
completion_estimate: on-track
total_tasks: 25
completed_tasks: 25
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer
contributors:
- codebase-explorer
- documentation-writer
tasks:
- id: TASK-1.1
  description: Update collection/page.tsx - Convert 7 direct imports
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 10m
  priority: high
- id: TASK-1.2
  description: Update context-entities/page.tsx - Convert 2 direct imports
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 5m
  priority: medium
- id: TASK-1.3
  description: Update deployments/page.tsx - Convert 1 direct import
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 5m
  priority: medium
- id: TASK-1.4
  description: Update marketplace pages (4 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 15m
  priority: medium
- id: TASK-1.5
  description: Update mcp pages (2 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 10m
  priority: medium
- id: TASK-1.6
  description: Update projects pages (4 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 15m
  priority: medium
- id: TASK-1.7
  description: Update templates/page.tsx
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  estimated_effort: 5m
  priority: medium
- id: TASK-1.8
  description: Type check after Phase 1
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  - TASK-1.4
  - TASK-1.5
  - TASK-1.6
  - TASK-1.7
  estimated_effort: 5m
  priority: high
- id: TASK-2.1
  description: Update collection dialogs (6 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-1.8
  estimated_effort: 20m
  priority: high
- id: TASK-2.2
  description: Update collection views (5 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-1.8
  estimated_effort: 15m
  priority: high
- id: TASK-2.3
  description: Type check after Phase 2
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.1
  - TASK-2.2
  estimated_effort: 5m
  priority: high
- id: TASK-3.1
  description: Update entity components (7 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.3
  estimated_effort: 25m
  priority: high
- id: TASK-3.2
  description: Update dashboard components (5 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.3
  estimated_effort: 20m
  priority: medium
- id: TASK-3.3
  description: Update collection context
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.3
  estimated_effort: 10m
  priority: medium
- id: TASK-3.4
  description: Type check after Phase 3
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  estimated_effort: 5m
  priority: high
- id: TASK-4.1
  description: Update marketplace modals (8 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-3.4
  estimated_effort: 25m
  priority: medium
- id: TASK-4.2
  description: Update discovery modals (4 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-3.4
  estimated_effort: 15m
  priority: medium
- id: TASK-4.3
  description: Type check after Phase 4
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-4.1
  - TASK-4.2
  estimated_effort: 5m
  priority: high
- id: TASK-5.1
  description: Update history, merge, and remaining components (15 files)
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-4.3
  estimated_effort: 35m
  priority: medium
- id: TASK-5.2
  description: Type check after Phase 5
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-5.1
  estimated_effort: 5m
  priority: high
- id: TASK-6.1
  description: Update all test files (16 files) - convert namespace imports
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-5.2
  estimated_effort: 40m
  priority: medium
- id: TASK-6.2
  description: Run full test suite
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-6.1
  estimated_effort: 10m
  priority: critical
- id: TASK-7.1
  description: Update hooks.md rule with registry pattern
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - TASK-6.2
  estimated_effort: 20m
  priority: medium
- id: TASK-7.2
  description: Update web CLAUDE.md hooks section
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - TASK-6.2
  estimated_effort: 15m
  priority: medium
- id: TASK-8.1
  description: Remove analysis files and audit doc, final validation
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-7.1
  - TASK-7.2
  estimated_effort: 15m
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
  batch_2:
  - TASK-1.8
  batch_3:
  - TASK-2.1
  - TASK-2.2
  batch_4:
  - TASK-2.3
  batch_5:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  batch_6:
  - TASK-3.4
  batch_7:
  - TASK-4.1
  - TASK-4.2
  batch_8:
  - TASK-4.3
  batch_9:
  - TASK-5.1
  batch_10:
  - TASK-5.2
  batch_11:
  - TASK-6.1
  batch_12:
  - TASK-6.2
  batch_13:
  - TASK-7.1
  - TASK-7.2
  batch_14:
  - TASK-8.1
  critical_path:
  - TASK-1.1
  - TASK-1.8
  - TASK-2.1
  - TASK-2.3
  - TASK-3.1
  - TASK-3.4
  - TASK-4.1
  - TASK-4.3
  - TASK-5.1
  - TASK-5.2
  - TASK-6.1
  - TASK-6.2
  - TASK-7.1
  - TASK-8.1
  estimated_total_time: 4-6h
blockers: []
success_criteria:
- id: SC-1
  description: All 73 files import from @/hooks barrel export
  status: pending
- id: SC-2
  description: Zero direct imports from individual hook files
  status: pending
- id: SC-3
  description: pnpm type-check passes
  status: pending
- id: SC-4
  description: pnpm test passes
  status: pending
- id: SC-5
  description: pnpm build succeeds
  status: pending
- id: SC-6
  description: Documentation updated
  status: pending
files_modified:
- skillmeat/web/hooks/index.ts
progress: 100
updated: '2026-01-12'
---

# hooks-canonical-registry - All Phases: Canonical Hooks Registry Implementation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/hooks-canonical-registry/all-phases-progress.md -t TASK-X -s completed
```

---

## Objective

Implement Layer 1 of the Agentic Code Mapping Recommendations: establish `@/hooks` as the canonical import path for all hooks throughout the SkillMeat web frontend.

**Deliverables**:
1. All 73 files updated to use barrel imports
2. Documentation reflecting new pattern
3. Clean codebase with no direct hook file imports

---

## Implementation Notes

### Transformation Pattern

**Before**:
```typescript
import { useCollections } from '@/hooks/use-collections';
import { useGroups } from '@/hooks/use-groups';
import { useToast } from '@/hooks/use-toast';
```

**After**:
```typescript
import { useCollections, useGroups, useToast } from '@/hooks';
```

### Special Cases

1. **Multiple imports from same file** - Merge into single barrel import
2. **Type-only imports** - Keep separate with `import type`
3. **Namespace imports** - Convert to named imports (test files)

### Known Gotchas

- Some files import from both kebab-case and camelCase files - merge all
- `EntityLifecycleProvider.tsx` re-exports - update imports in consumers
- Marketplace test files use namespace imports - convert to named

### Commands

```bash
# Type check
cd skillmeat/web && pnpm type-check

# Run tests
cd skillmeat/web && pnpm test

# Build
cd skillmeat/web && pnpm build
```

---

## Quick Reference: Orchestration Commands

```bash
# Update single task
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/hooks-canonical-registry/all-phases-progress.md \
  -t TASK-1.1 -s completed

# Batch update multiple tasks
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/hooks-canonical-registry/all-phases-progress.md \
  --updates "TASK-1.1:completed,TASK-1.2:completed,TASK-1.3:completed"

# Query pending tasks
python .claude/skills/artifact-tracking/scripts/query_artifacts.py \
  --status pending

# Validate artifact
python .claude/skills/artifact-tracking/scripts/validate_artifact.py \
  -f .claude/progress/hooks-canonical-registry/all-phases-progress.md
```

---

## Completion Notes

_Fill in when implementation is complete_
