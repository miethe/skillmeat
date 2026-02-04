---
phase: 2
phase_name: Card Components
prd: manage-collection-page-refactor-v1
status: completed
estimated_hours: 4-6
created_at: 2026-02-02
updated_at: 2026-02-02
parallelization:
  batch_1:
  - CARD-2.3
  - rationale: Shared utilities (StatusBadge, HealthIndicator, DeploymentBadgeStack)
      are dependencies for CARD-2.1 and CARD-2.2
  - duration: ~1.5 hours
  batch_2:
  - - CARD-2.1
    - CARD-2.2
  - rationale: ArtifactBrowseCard and ArtifactOperationsCard can run in parallel;
      both depend on CARD-2.3
  - duration: ~2 hours each
  - can_parallelize: true
  batch_3:
  - - CARD-2.4
    - CARD-2.5
  - rationale: Integration tasks can run in parallel; CARD-2.4 depends on CARD-2.1,
      CARD-2.5 depends on CARD-2.2
  - duration: ~1 hour each
  - can_parallelize: true
tasks:
- id: CARD-2.1
  name: Create ArtifactBrowseCard component
  description: 'Discovery-focused card: type icon, name, author, description (truncated),
    tags, tools, score badge, quick actions menu; "Deployed" badge with project count
    when applicable (no sync/drift indicators)'
  estimated_hours: 2
  assigned_to: ui-engineer-enhanced
  status: completed
  batch: 2
  depends_on:
  - CARD-2.3
  notes: ''
- id: CARD-2.2
  name: Create ArtifactOperationsCard component
  description: 'Operations-focused card: checkbox, type icon, name, version arrows,
    deployments, badges (drift/update), sync time, action buttons'
  estimated_hours: 2
  assigned_to: ui-engineer-enhanced
  status: completed
  batch: 2
  depends_on:
  - CARD-2.3
  notes: ''
- id: CARD-2.3
  name: Create shared status utility components
  description: 'StatusBadge, HealthIndicator, DeploymentBadgeStack components with
    proper styling and tooltips. DeploymentBadgeStack: hover overflow badge shows
    tooltip with full project list; click overflow badge opens modal on deployments
    tab'
  estimated_hours: 1.5
  assigned_to: ui-engineer-enhanced
  status: completed
  batch: 1
  depends_on: []
  notes: ''
- id: CARD-2.4
  name: Integrate ArtifactBrowseCard into collection page
  description: Replace existing card rendering with ArtifactBrowseCard; update prop
    passing and event handlers
  estimated_hours: 1
  assigned_to: frontend-developer
  status: completed
  batch: 3
  depends_on:
  - CARD-2.1
  notes: ''
- id: CARD-2.5
  name: Integrate ArtifactOperationsCard into manage page
  description: Replace existing card rendering with ArtifactOperationsCard; integrate
    bulk selection, action handlers
  estimated_hours: 1
  assigned_to: frontend-developer
  status: completed
  batch: 3
  depends_on:
  - CARD-2.2
  notes: ''
quality_gates:
- criterion: ArtifactBrowseCard shows "Deployed (N)" badge when applicable; no sync/drift
    indicators
  verified: false
- criterion: ArtifactOperationsCard shows health and deployment status
  verified: false
- criterion: Shared utilities (StatusBadge, HealthIndicator, DeploymentBadgeStack)
    exported and working
  verified: false
- criterion: Both cards integrate into pages with no console errors
  verified: false
- criterion: Quick actions on browse card and operation buttons on operations card
    functional
  verified: false
blockers: []
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-02'
---

# Phase 2: Card Components

## Overview

Phase 2 focuses on building reusable card components that display artifacts in two distinct contexts:

1. **ArtifactBrowseCard** — Discovery-focused view for the collection page (showing metadata, deployments, quick actions)
2. **ArtifactOperationsCard** — Operations-focused view for the manage page (showing selection, status, health indicators, bulk actions)
3. **Shared Utilities** — Common status display components (StatusBadge, HealthIndicator, DeploymentBadgeStack)

## Execution Strategy

### Batch 1: Shared Utilities (1.5 hours)
- **CARD-2.3**: Create StatusBadge, HealthIndicator, and DeploymentBadgeStack components
- These are dependencies for both card types in Batch 2
- Must include proper styling, tooltips, and modal integration for deployment badge overflow

### Batch 2: Card Components (2 hours each, parallel)
- **CARD-2.1**: ArtifactBrowseCard (discovery UI, quick actions)
- **CARD-2.2**: ArtifactOperationsCard (operations UI, health badges, bulk selection support)
- Both depend on CARD-2.3 utilities

### Batch 3: Integration (1 hour each, parallel)
- **CARD-2.4**: Integrate ArtifactBrowseCard into collection page
- **CARD-2.5**: Integrate ArtifactOperationsCard into manage page
- Both depend on their respective cards from Batch 2

## Deliverables

### CARD-2.1: ArtifactBrowseCard Component
- Type icon (with color coding)
- Artifact name and author
- Truncated description (2-3 lines)
- Tags display
- Tools/dependencies badges
- Score badge (if applicable)
- "Deployed (N)" badge showing project count
- Quick actions menu (icon button with dropdown)
- No sync/drift indicators (those are operations-only)

**Location**: `skillmeat/web/components/collection/ArtifactBrowseCard.tsx`

### CARD-2.2: ArtifactOperationsCard Component
- Checkbox for bulk selection
- Type icon (with color coding)
- Artifact name and version navigation arrows
- Deployment status with badge stack
- Health indicator (drift/update status)
- Last sync timestamp
- Action buttons (edit, delete, more options)
- Hover states and visual feedback

**Location**: `skillmeat/web/components/manage/ArtifactOperationsCard.tsx`

### CARD-2.3: Shared Status Utilities
- **StatusBadge**: Generic badge component for artifact status (e.g., "healthy", "update available", "out of sync")
- **HealthIndicator**: Visual indicator showing health status with icon and color
- **DeploymentBadgeStack**: Displays list of deployment badges with tooltip on hover for overflow; modal on click for full list

**Location**: `skillmeat/web/components/shared/StatusUtilities.tsx`

### CARD-2.4: Collection Page Integration
- Replace existing card rendering with ArtifactBrowseCard
- Ensure event handlers (quick actions) work correctly
- Verify no console errors

### CARD-2.5: Manage Page Integration
- Replace existing card rendering with ArtifactOperationsCard
- Integrate bulk selection checkbox with parent selection logic
- Ensure action buttons trigger correct handlers

## Quality Assurance

- All quality gates must be verified before proceeding to Phase 3
- Component unit tests written with >80% coverage
- No TypeScript errors or console warnings
- Accessibility: ARIA labels on icon buttons, proper button semantics
- Styling: Consistent with Radix UI + shadcn patterns, responsive design
