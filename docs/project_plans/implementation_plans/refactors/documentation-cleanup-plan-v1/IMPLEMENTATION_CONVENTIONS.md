# SkillMeat Implementation Conventions & Patterns

**Reference Guide** for maintaining consistency across all implementation plans and progress tracking.

---

## Table of Contents

1. [File Organization](#file-organization)
2. [Progress YAML Format](#progress-yaml-format)
3. [Task Definition Structure](#task-definition-structure)
4. [Phase Organization](#phase-organization)
5. [Orchestration Pattern](#orchestration-pattern)
6. [Naming Conventions](#naming-conventions)
7. [Status Values](#status-values)
8. [Story Point Estimation](#story-point-estimation)
9. [Component/File Naming](#componentfile-naming)
10. [Documentation Format](#documentation-format)

---

## File Organization

### Implementation Plan Directory Structure

```
docs/project_plans/implementation_plans/
├── features/               # New capabilities
│   ├── [feature-name]-v1.md         # Parent plan document
│   └── [feature-name]-v1/           # Phase subdirectory
│       ├── phase-1-*.md
│       ├── phase-2-*.md
│       └── ...
├── enhancements/           # Improvements to existing features
│   ├── [feature-name]-v1.md
│   └── [feature-name]-v1/
│       ├── phase-1-*.md
│       └── ...
└── refactors/              # Code/architecture improvements
    ├── [refactor-name]-v1.md
    └── [refactor-name]-v1/
        ├── phase-1-*.md
        └── ...
```

### Progress Tracking Directory Structure

```
.claude/progress/
└── [feature-name]/
    ├── all-phases-progress.md      # (optional) rollup summary
    ├── phase-1-progress.md         # YAML + Markdown per phase
    ├── phase-2-progress.md
    └── ...
```

### Worknotes Directory Structure

```
.claude/worknotes/
└── [feature-name]/
    ├── context.md                  # Implementation context
    ├── [phase-name]-context.md     # (optional) per-phase notes
    └── [topic]-insights.md         # (optional) specific topics
```

---

## Progress YAML Format

### Standard Frontmatter

```yaml
---
type: progress                              # Always "progress"
prd: [feature-name]                        # References PRD filename
phase: N                                    # Phase number (1-based)
title: "Brief Phase Description"           # Human-readable title
status: pending | in_progress | completed # Overall phase status
completed_at: "YYYY-MM-DD"                # Completion date (if done)
progress: X                                # Completion % (0-100)
total_tasks: N                             # Total task count
completed_tasks: N                         # Completed task count
total_story_points: X                      # Sum of all story points
completed_story_points: X                  # Sum of completed points
last_updated: "YYYY-MM-DD"                # Last update date
---
```

### Minimal Frontmatter (Quick Phases)

```yaml
---
type: progress
prd: feature-name
phase: 1
title: "Phase Name"
status: pending
---
```

### Complete Example

```yaml
---
type: progress
prd: collections-navigation-v1
phase: 1
title: Database Layer
status: completed
completed_at: "2025-12-12"
progress: 100
total_tasks: 5
completed_tasks: 5
total_story_points: 8.5
completed_story_points: 8.5
last_updated: "2025-12-12"
---
```

---

## Task Definition Structure

### Standard Task Format

```yaml
tasks:
  - id: TASK-N.M                    # TASK-[phase].[sequence]
    title: "Brief Title"            # Max 50 chars
    description: "Full description" # 1-2 sentences
    status: pending | in_progress | completed
    story_points: N                 # Fibonacci: 1, 1.5, 2, 3, 5, 8, 13, 21
    assigned_to:
      - agent-name                  # Array of agent names
    dependencies:
      - TASK-X.Y                    # Array of task IDs
    created_at: "YYYY-MM-DD"       # Creation date
    completed_at: "YYYY-MM-DD"     # Completion date (if done)
    files:                          # (optional) Files affected
      - path/to/file.py
      - path/to/file.tsx
    note: "Additional context"      # (optional) Extra notes
```

### Minimal Task Format

```yaml
tasks:
  - id: TASK-1.1
    title: "Do something"
    status: pending
    story_points: 2
    assigned_to: [agent-name]
    dependencies: []
```

### Complete Example

```yaml
tasks:
  - id: TASK-1.1
    title: Collection Model
    description: SQLAlchemy ORM model for collections
    status: completed
    story_points: 2
    assigned_to:
      - data-layer-expert
    dependencies: []
    created_at: "2025-12-12"
    completed_at: "2025-12-12"
    files:
      - skillmeat/cache/models.py
    note: "Includes relationships to artifacts"
```

---

## Phase Organization

### Phase File Naming

```
phase-N-[descriptor].md

Examples:
- phase-1-core-infrastructure.md
- phase-2-backend-api.md
- phase-3-web-ui-context-entities.md
- phase-3-4-progress.md (combined phases)
```

### Phase Section Headers

```markdown
---
[YAML Frontmatter]
---

# Phase N: [Full Phase Name]

**Status**: [pending|in_progress|completed]
**Story Points**: X/Y (Z%)
**Task Count**: A/B (C%)
**Estimated Duration**: N weeks
**Last Updated**: YYYY-MM-DD

## Orchestration Quick Reference

[Ready-to-copy Task() commands for each batch]

### Batch 1 - [Descriptor] (Parallel, No Dependencies)

**TASK-N.M: Title** (X points)
- File: `path/to/file.ext`
- Scope: Brief description
- Agent: agent-name
- Duration: ~X minutes

## Task Execution Strategy

[Description of batch execution order]

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Progress Tracking

| Task | Status | Story Points | ... |
|------|--------|--------------|-----|
| TASK-N.M | [status] | X | ... |
| TOTAL | [status] | X | ... |

## Notes

- Key implementation detail
- Dependency or constraint
```

---

## Orchestration Pattern

### Task() Command Template

```python
Task(
    "agent-name",
    """TASK-N.M: Brief Title

File: path/to/file.ext

Description of what to do:
1. Create/modify X
2. Add Y
3. Handle Z

Detailed instructions on specific changes needed.

Duration: ~X minutes"""
)
```

### Batch Organization Pattern

```yaml
parallelization:
  batch_1:
    - TASK-1.1
    - TASK-1.2
  batch_2:
    - TASK-1.3
    - TASK-1.4
  batch_3:
    - TASK-2.1
```

Execution pattern:
- **Batch 1**: Execute all tasks in parallel
- **Wait for Batch 1 completion**
- **Batch 2**: Execute all tasks in parallel
- **Wait for Batch 2 completion**
- **Batch 3**: Execute all tasks in parallel

### Context Files in Frontmatter

```yaml
context_files:
  - skillmeat/cache/models.py       # Files referenced in tasks
  - skillmeat/core/
  - skillmeat/api/routers/

blockers:
  - TASK-X.Y description            # Known blockers
  - External dependency

notes: "Phase-level notes and context"
```

---

## Naming Conventions

### Task IDs

Format: `TASK-[PHASE].[SEQUENCE]`

```
TASK-1.1 - First task of Phase 1
TASK-1.2 - Second task of Phase 1
TASK-2.1 - First task of Phase 2
TASK-2.3 - Third task of Phase 2
```

### Feature Names

Format: `[feature-name]-v[VERSION]`

```
collections-navigation-v1
agent-context-entities-v1
notification-system-v1
marketplace-github-ingestion-v1
```

### Directory Names

```
# Implementation plans
features/
enhancements/
refactors/

# Progress tracking
[feature-name]/
[feature-name]-v1/
[feature-category]/

# Worknotes
[feature-name]/
[feature-name]-v1/
fixes/  (for bug fixes)
observations/  (for learnings)
```

### File Paths (Backend Python)

```
skillmeat/
├── api/
│   ├── routers/[entity]_[operation].py
│   ├── schemas/[entity].py
│   └── middleware/[concern].py
├── core/
│   ├── [entity].py
│   ├── services/[service].py
│   ├── validators/[validator].py
│   └── parsers/[parser].py
├── cache/
│   └── models.py
└── cli.py
```

### File Paths (Frontend React)

```
skillmeat/web/
├── app/
│   ├── [entity]/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   └── layout.tsx
├── components/
│   ├── [entity]/
│   │   ├── [Entity]Card.tsx
│   │   ├── [Entity]Form.tsx
│   │   └── [Entity]Dialog.tsx
│   └── common/
├── hooks/
│   └── use-[entity].ts
├── lib/
│   └── api/[entity].ts
└── types/
    └── [entity].ts
```

---

## Status Values

### Valid Status Values

```
pending       - Task not yet started (waiting for dependencies or resources)
in_progress   - Task actively being worked on
completed     - Task fully finished and tested
blocked       - Task cannot proceed (waiting on external blocker)
planning      - Task in design/scoping phase (for phases)
not_started   - Initiative hasn't begun (for larger initiatives)
```

### Status Progression

```
pending → in_progress → completed
            ↓
         blocked → resolved → in_progress → completed

Phase statuses:
pending → planning → in_progress → completed
```

### Examples

```yaml
# Task
status: in_progress        # Currently being worked on

# Phase
status: completed          # All tasks done, testing done, merged
status: in_progress        # Some tasks active
status: pending            # Waiting to start
status: planning           # Design phase

# Initiative
status: not_started        # Proposed but no work begun
status: pending            # Scheduled to start
status: in_progress        # Active work
status: completed          # All phases done
```

---

## Story Point Estimation

### Fibonacci Scale

```
1     - Trivial (< 15 min, obvious implementation)
1.5   - Very small (15-30 min, straightforward)
2     - Small (30-60 min, minor complexity)
3     - Medium (1-2 hours, moderate complexity)
5     - Large (2-4 hours, notable complexity)
8     - Very Large (1-2 days, significant effort)
13    - XL (2-3 days, major effort)
21    - XXL (3-5 days, extensive work)
```

### Estimation Guidelines

**1 point** (Trivial):
- Simple function stub
- Add single field to model
- One-line validation

**1.5 points** (Very Small):
- Simple model property
- Basic endpoint
- Simple hook

**2 points** (Small):
- Simple CRUD operation
- Small component
- Validation logic

**3 points** (Medium):
- Router with multiple endpoints
- Complex component
- Service with business logic
- API client module

**5 points** (Large):
- Multiple related components
- Complex integration
- Service with multiple operations
- Full CRUD implementation

**8 points** (Very Large):
- Complete feature subsystem
- Major integration
- Complex state management

---

## Component/File Naming

### React Components

```typescript
// Functional component (standard)
function ComponentName() { }
export default ComponentName;

// Or named export
export function ComponentName() { }

// Files
ComponentName.tsx          // Single component
ComponentName.module.css   // Scoped styles
ComponentName.stories.tsx  // Storybook
ComponentName.test.tsx     // Tests
```

### Hooks

```typescript
// File: use-entity-name.ts
export function useEntityName(id: string) {
  // Hook implementation
}

// OR for complex hooks with subhooks
export function useEntityName(id: string) { }
export function useEntityNameData() { }
export function useEntityNameActions() { }
```

### API Client Functions

```typescript
// File: lib/api/entity-name.ts
export async function fetchEntityNames(): Promise<EntityName[]> { }
export async function createEntityName(data: CreateRequest): Promise<EntityName> { }
export async function updateEntityName(id: string, data: UpdateRequest): Promise<EntityName> { }
export async function deleteEntityName(id: string): Promise<void> { }
```

### Backend Models & Services

```python
# File: skillmeat/cache/models.py
class EntityName(Base):
    __tablename__ = "entity_names"

# File: skillmeat/core/services/entity_service.py
def create_entity(name: str) -> EntityName:
    pass

# File: skillmeat/api/routers/entity.py
@router.post("/entity-names")
async def create_entity(request: CreateEntityRequest) -> EntityResponse:
    pass
```

---

## Documentation Format

### Implementation Plan Documents

```markdown
---
title: "Implementation Plan: [Feature Name]"
description: "Brief description"
audience: [ai-agents, developers, engineering-leads]
tags: [tag1, tag2, tag3]
created: YYYY-MM-DD
updated: YYYY-MM-DD
category: "implementation-plan"
prd: "/docs/project_plans/PRDs/features/[prd-name].md"
complexity: "Small|Medium|Large|Extra Large"
track: "Standard"
---

# Implementation Plan: [Feature Name]

**Project**: [Name]
**PRD**: [Link]
**Complexity**: [Assessment]
**Estimated Effort**: X story points
**Timeline**: Y weeks

---

## Executive Summary

[Overview of feature, key deliverables, success metrics]

---

## Phase Breakdown

| Phase | Name | Duration | Points | Dependencies |
|-------|------|----------|--------|--------------|
| **1** | [Name] | X weeks | N points | None |
| **2** | [Name] | X weeks | N points | Phase 1 |

---

## Orchestration Quick Reference

[Task() commands for each batch]

---

## Risk Assessment

[High-risk items, mitigation strategies]

---

## Success Metrics

[Measurable outcomes]

---

## Related Documentation

- PRD: [Link]
- Architecture: [Link]
- Patterns: [Link]
```

### Phase Documentation

```markdown
# Phase N: [Full Phase Name]

[YAML Frontmatter]

---

# Phase N: [Full Phase Name]

**Objective**: What this phase accomplishes
**Story Points**: X (distributed across Y tasks)
**Prerequisites**: Prior phases, dependencies

## Orchestration Quick Reference

### Batch 1 - [Name] (Parallel, No Dependencies)

**TASK-N.M: Title** (X points)
- File: `path`
- Scope: Description
- Agent: agent-name
- Duration: ~X minutes

[Ready-to-copy Task() command]

---

## Task Execution Strategy

[Batch execution plan]

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Files Modified

- File 1
- File 2

## Progress Tracking

[Status table]

## Notes

[Implementation notes]
```

### Worknotes Format

```markdown
---
title: "Context: [Feature]"
feature: [feature-name]
phase: N
date: YYYY-MM-DD
---

# Implementation Context: [Feature]

## Overview

[High-level context for implementation]

## Key Decisions

1. **Decision Name**: [Decision]
   - Rationale: [Why]
   - Impact: [Consequences]

## Patterns Discovered

[Patterns found during implementation]

## Implementation Notes

[Specific notes, gotchas, solutions]

## References

- Related file: [Path]
- Related commit: [SHA]
```

---

## Examples

### Complete Phase File

See: `.claude/progress/collections-navigation-v1/phase-1-progress.md`

### Complete Implementation Plan

See: `docs/project_plans/implementation_plans/features/agent-context-entities-v1.md`

### Complete Worknotes

See: `.claude/worknotes/[feature]/context.md`

---

## Checklists for New Initiatives

### New Initiative Checklist

- [ ] Create PRD in `docs/project_plans/PRDs/`
- [ ] Create parent plan in `docs/project_plans/implementation_plans/[category]/`
- [ ] Create phase subdirectory
- [ ] Create phase-N-progress.md files
- [ ] Add to this tracking summary
- [ ] Get stakeholder approval
- [ ] Ready for execution

### New Phase Checklist

- [ ] Define all tasks with TASK-N.M IDs
- [ ] Assign agents and story points
- [ ] Define dependencies
- [ ] Create Task() commands in orchestration section
- [ ] Define success criteria
- [ ] Estimate duration
- [ ] Add to progress tracking
- [ ] Ready for execution

---

## Common Patterns & Examples

### Parallel + Sequential Pattern

```yaml
parallelization:
  batch_1:
    - TASK-1.1  # No dependencies
    - TASK-1.2  # No dependencies
  # Wait for batch 1
  batch_2:
    - TASK-1.3  # Depends on batch 1
    - TASK-1.4  # Depends on batch 1
  # Wait for batch 2
  batch_3:
    - TASK-2.1  # Depends on batch 2
```

### Database → API → UI Pattern

```
Phase 1: Database (models, migrations)
Phase 2: API (routers, schemas)
Phase 3: UI (components, hooks)
Phase 4: Integration (testing, polish)
```

### Feature Flag Pattern

```
Phase 1-2: Core functionality (feature-flagged)
Phase 3: Testing & refinement
Phase 4: Rollout planning
Phase 5: Staged release
Phase 6: Monitoring & polish
```

---

## For Maintainers

When creating new implementation plans:

1. **Follow the directory structure** exactly
2. **Use consistent YAML format** for all progress files
3. **Include orchestration quick reference** for all phases
4. **Define clear success criteria** for each phase
5. **Estimate story points accurately** using the Fibonacci scale
6. **Assign agents consistently** based on domain expertise
7. **Document dependencies** explicitly
8. **Include risk assessment** for complex features

When updating existing plans:

1. **Update `last_updated` field** in YAML
2. **Update progress percentages** accurately
3. **Complete all task metadata** (assigned_to, dependencies, files)
4. **Maintain task ID sequences** (no gaps)
5. **Update summary documents** (e.g., IMPLEMENTATION_TRACKING_SUMMARY.md)

---

## Validation

### Pre-Execution Checklist

- [ ] All tasks have unique IDs (TASK-N.M format)
- [ ] All tasks have assigned_to field
- [ ] All tasks have dependencies defined (may be empty array)
- [ ] All story points are valid (Fibonacci)
- [ ] Phase total points = sum of task points
- [ ] Batch dependencies are linear
- [ ] Task description is clear and actionable
- [ ] Files list is accurate
- [ ] Success criteria are measurable
- [ ] No circular dependencies

### Post-Completion Checklist

- [ ] All tasks marked completed with dates
- [ ] Progress updated to 100%
- [ ] Story points totals match
- [ ] Phase marked completed
- [ ] Learnings documented in worknotes
- [ ] Summary updated in tracking documents
- [ ] Next phase initiated or marked pending

---

**Last Updated**: 2025-12-15
**Maintained By**: Implementation tracking system
