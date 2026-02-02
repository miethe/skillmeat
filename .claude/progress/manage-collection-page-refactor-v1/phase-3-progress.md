---
phase: 3
phase_name: Modal Separation
prd: manage-collection-page-refactor-v1
status: completed
estimated_hours: 7-9
created_at: 2026-02-02
updated_at: 2026-02-02
parallelization:
  batch_1:
  - MODAL-3.3
  - rationale: Shared modal components are dependencies for MODAL-3.1 and MODAL-3.2
  batch_2:
  - - MODAL-3.1
    - MODAL-3.2
  - rationale: ArtifactDetailsModal and ArtifactOperationsModal can run in parallel
      after shared components
  - can_parallelize: true
  batch_3:
  - - MODAL-3.4
    - MODAL-3.5
  - rationale: Tab updates and cross-navigation state can run in parallel
  - can_parallelize: true
  batch_4:
  - MODAL-3.6
  - rationale: Integration depends on all modals being complete
tasks:
- id: MODAL-3.1
  name: Create ArtifactDetailsModal (collection-focused)
  description: 'Discovery modal reusing existing content: Overview + Contents + Links
    + Collections + Sources + history (general artifact timeline); includes ''Manage
    Artifact'' button'
  estimated_hours: 2.5
  assigned_to:
  - ui-engineer-enhanced
  status: completed
  batch: 2
  depends_on:
  - MODAL-3.3
  acceptance_criteria:
  - All tabs render (Overview, Contents, Links, Collections, Sources, history)
  - Overview + Contents present with correct content
  - Overview is default tab
  - Cross-navigation 'Manage Artifact' button works
  - Deploy action available
  - Add to Group action available
  - Upstream status summary shown (if any)
  - No project-level sync details shown (operations-only)
  notes: ''
- id: MODAL-3.2
  name: Create ArtifactOperationsModal (manage-focused)
  description: 'Operations modal reusing existing content: Overview + Contents + Status
    + Sync Status + Deployments + version-history (version timeline with rollback
    options)'
  estimated_hours: 2.5
  assigned_to:
  - ui-engineer-enhanced
  status: completed
  batch: 2
  depends_on:
  - MODAL-3.3
  acceptance_criteria:
  - All tabs render (Overview, Contents, Status, Sync Status, Deployments, version-history)
  - Overview + Contents present with correct content
  - Status tab is default tab
  - Health indicators display correctly
  - Sync actions work and are functional
  - Cross-navigation 'Collection Details' button present and functional
  - Version history shows correctly with rollback options
  notes: ''
- id: MODAL-3.3
  name: Extract shared modal components
  description: 'Create reusable modal subcomponents: TabNavigation, ModalHeader, TabContent
    wrapper to eliminate duplication between modals'
  estimated_hours: 1
  assigned_to:
  - frontend-developer
  status: completed
  batch: 1
  depends_on: []
  acceptance_criteria:
  - TabNavigation component is reusable and accepts customization props
  - ModalHeader component is reusable with title, icon, actions slots
  - TabContent wrapper handles tab content rendering
  - No duplication between ArtifactDetailsModal and ArtifactOperationsModal
  - Props accept customization for different use cases
  - Accessibility preserved (ARIA labels, keyboard navigation)
  notes: ''
- id: MODAL-3.4
  name: Update ModalCollectionsTab component
  description: Add optional 'View in Collection' and 'Manage Artifact' actions per
    collection when in operations context
  estimated_hours: 1
  assigned_to:
  - ui-engineer-enhanced
  status: completed
  batch: 3
  depends_on:
  - MODAL-3.1
  - MODAL-3.2
  acceptance_criteria:
  - Action buttons appear in modal when appropriate context
  - Navigation works correctly from buttons
  - Collection list renders without errors
  - Focus management correct after navigation
  - Buttons only appear in relevant contexts (operations/discovery)
  notes: ''
- id: MODAL-3.5
  name: Implement cross-navigation state preservation
  description: 'Ensure modal context preserved when navigating between pages. Implement
    ?returnTo= query param: serialize origin URL with filters; show ''Return to [origin]''
    button when returnTo present; handle browser back button correctly'
  estimated_hours: 1.5
  assigned_to:
  - frontend-developer
  status: completed
  batch: 3
  depends_on:
  - MODAL-3.1
  - MODAL-3.2
  acceptance_criteria:
  - returnTo query param serialized on cross-navigation
  - Return button appears when returnTo is present in URL
  - Return navigation restores filters and scroll position
  - Browser back button works correctly with returnTo
  - Modal reopens correctly after return navigation
  - No data loss on navigation between pages
  - URL state properly updated on all navigation events
  notes: ''
- id: MODAL-3.6
  name: Integrate modals into respective pages
  description: Wire ArtifactDetailsModal to collection page, ArtifactOperationsModal
    to manage page with proper event handlers and data flow
  estimated_hours: 1
  assigned_to:
  - frontend-developer
  status: completed
  batch: 4
  depends_on:
  - MODAL-3.1
  - MODAL-3.2
  - MODAL-3.4
  - MODAL-3.5
  acceptance_criteria:
  - ArtifactDetailsModal opens on collection page artifact click
  - ArtifactOperationsModal opens on manage page artifact click
  - Artifact data flows correctly to modals
  - Modal close handlers work (ESC, backdrop click, close button)
  - No console errors during modal operations
  - No visual regressions on page layouts
  - Deep link ?artifact={id} opens correct modal automatically
  notes: ''
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-02'
---

# Phase 3: Modal Separation

## Objective

Create purpose-specific modals that reduce feature confusion and improve task completion flows by clearly separating discovery-focused content (ArtifactDetailsModal) from operations-focused content (ArtifactOperationsModal).

## Progress Summary

- **Status**: Pending
- **Estimated Hours**: 7-9 hours
- **Completed Tasks**: 0/6
- **In Progress Tasks**: 0/6
- **Blocked Tasks**: 0/6

## Tasks Overview

### Batch 1: Shared Components Foundation
- **MODAL-3.3**: Extract shared modal components (TabNavigation, ModalHeader, TabContent)

### Batch 2: Modal Implementation (Parallel)
- **MODAL-3.1**: Create ArtifactDetailsModal (collection-focused)
- **MODAL-3.2**: Create ArtifactOperationsModal (manage-focused)

### Batch 3: Enhanced Navigation (Parallel)
- **MODAL-3.4**: Update ModalCollectionsTab component
- **MODAL-3.5**: Implement cross-navigation state preservation

### Batch 4: Integration
- **MODAL-3.6**: Integrate modals into respective pages

## Quality Gate Checklist

- [ ] ArtifactDetailsModal shows discovery-focused content (overview/contents/links/collections/sources/history tab)
- [ ] ArtifactOperationsModal shows operations-focused content (overview/contents/status/sync status/deployments/version-history tab)
- [ ] Cross-navigation buttons present in both modals with returnTo handling
- [ ] Return button appears when navigated from other page
- [ ] Modals integrate into pages without errors
- [ ] All tabs in both modals render and function correctly
- [ ] Modal state preserved across navigations
- [ ] Focus management correct (trapped in modal, restored on close)
- [ ] ESC key closes modals
- [ ] Deep links (?artifact={id}) open correct modals automatically
- [ ] No console errors during modal operations

## Output Artifacts

- New `skillmeat/web/components/collection/artifact-details-modal.tsx`
- New `skillmeat/web/components/manage/artifact-operations-modal.tsx`
- New `skillmeat/web/components/shared/modal-header.tsx`
- New `skillmeat/web/components/shared/tab-navigation.tsx`
- New `skillmeat/web/components/shared/tab-content.tsx`
- New `skillmeat/web/components/shared/cross-navigation-buttons.tsx`
- Updated `skillmeat/web/components/entity/modal-collections-tab.tsx`
- Updated `skillmeat/web/app/collection/page.tsx` (modal integration)
- Updated `skillmeat/web/app/manage/page.tsx` (modal integration)

## Key Decisions

### Modal Content Separation

**ArtifactDetailsModal (Collection Page)**:
- Focus: Discovery and exploration
- Default tab: Overview
- Tabs: Overview, Contents, Links, Collections, Sources, history
- Actions: Deploy, Add to Group, "Manage Artifact →"
- Shows: Upstream status summary only (no project-level sync details)

**ArtifactOperationsModal (Manage Page)**:
- Focus: Operations and maintenance
- Default tab: Status
- Tabs: Overview, Contents, Status, Sync Status, Deployments, version-history
- Actions: Sync, Update, "Collection Details →"
- Shows: Full health indicators, sync actions, version rollback options

### Cross-Navigation Pattern

- Both modals include cross-navigation buttons
- URL serialization via `?returnTo=` parameter
- Return button appears when navigating from other page
- Browser back button support
- Filter state preservation on return

## Dependencies

- **Phase 0**: Complete (deployments data available)
- **Phase 1**: Complete (deep linking infrastructure available)
- **Phase 2**: Complete (card components available)

## Risks & Mitigation

| Risk | Mitigation | Status |
|------|-----------|--------|
| Modal component complexity | Extract shared components early (Batch 1) | Addressed |
| Cross-navigation state loss | Comprehensive URL state management | Addressed |
| Tab content duplication | Reuse existing modal tab components where possible | Addressed |
| Focus management issues | Use Radix Dialog primitive, test keyboard navigation | Planned |

## Testing Requirements

- Unit tests for modal components (tabs, navigation, state)
- Integration tests for cross-navigation flows
- E2E tests for user journeys (browse → manage, manage → collection)
- Accessibility tests (keyboard navigation, ARIA, focus trapping)
- URL state preservation tests (filters, scroll position)

## Notes

This phase establishes the core UX improvement by creating modals tailored to each page's purpose. By separating discovery content from operations content, users will have clearer mental models and more efficient task completion flows.

The shared component extraction (MODAL-3.3) is critical - it must complete first to avoid duplication and ensure consistency between the two modals.
