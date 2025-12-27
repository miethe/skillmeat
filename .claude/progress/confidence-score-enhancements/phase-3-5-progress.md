---
type: progress
prd: "confidence-score-enhancements"
phase: "3-5"
status: pending
progress: 0
total_tasks: 21
completed_tasks: 0

tasks:
  - id: "TASK-3.1"
    name: "Create CatalogEntryModal component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "2h"

  - id: "TASK-3.2"
    name: "Build modal header section"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimate: "0.5h"

  - id: "TASK-3.3"
    name: "Create reusable ScoreBreakdown component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1h"

  - id: "TASK-3.4"
    name: "Add confidence section to modal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.2", "TASK-3.3"]
    estimate: "0.5h"

  - id: "TASK-3.5"
    name: "Add description and file list sections"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimate: "1h"

  - id: "TASK-3.6"
    name: "Add action buttons"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimate: "0.5h"

  - id: "TASK-3.7"
    name: "Wire modal to catalog card click"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1", "TASK-3.4", "TASK-3.5", "TASK-3.6"]
    estimate: "0.5h"

  - id: "TASK-3.8"
    name: "Add accessibility features"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.7"]
    estimate: "0.5h"

  - id: "TASK-3.9"
    name: "Write Storybook stories for modal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.8"]
    estimate: "0.5h"

  - id: "TASK-4.1"
    name: "Create ScoreBreakdownTooltip wrapper"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.3"]
    estimate: "1h"

  - id: "TASK-4.2"
    name: "Update ScoreBadge component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.1"]
    estimate: "1h"

  - id: "TASK-4.3"
    name: "Wire breakdown data from API"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.2"]
    estimate: "0.5h"

  - id: "TASK-4.4"
    name: "Add accessibility (keyboard & aria)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.2"]
    estimate: "0.5h"

  - id: "TASK-4.5"
    name: "Write Storybook stories for tooltip"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.4"]
    estimate: "0.5h"

  - id: "TASK-5.1"
    name: "Create ConfidenceFilter component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1.5h"

  - id: "TASK-5.2"
    name: "Add 'Include low-confidence artifacts' checkbox"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.1"]
    estimate: "0.5h"

  - id: "TASK-5.3"
    name: "Integrate filter into source page"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.2"]
    estimate: "1h"

  - id: "TASK-5.4"
    name: "Sync filter state with URL query params"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.3"]
    estimate: "1h"

  - id: "TASK-5.5"
    name: "Update API client"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "0.5h"

  - id: "TASK-5.6"
    name: "Wire filter to list updates"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.4", "TASK-5.5"]
    estimate: "1h"

  - id: "TASK-5.7"
    name: "Test filter shareable URLs"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.6"]
    estimate: "0.5h"

parallelization:
  batch_1: ["TASK-3.1", "TASK-3.3", "TASK-5.1", "TASK-5.5"]
  batch_2: ["TASK-3.2", "TASK-3.5", "TASK-3.6", "TASK-5.2"]
  batch_3: ["TASK-3.4"]
  batch_4: ["TASK-3.7"]
  batch_5: ["TASK-3.8", "TASK-4.1", "TASK-5.3"]
  batch_6: ["TASK-3.9", "TASK-4.2", "TASK-5.4"]
  batch_7: ["TASK-4.3", "TASK-4.4", "TASK-5.6"]
  batch_8: ["TASK-4.5", "TASK-5.7"]
---

# Phase 3-5: Frontend Components (Modal, Tooltip, Filter)

## Overview

Build the frontend user experience for confidence score transparency: detailed modal view, hover tooltip breakdown, and filtering controls. All components consume breakdown data from Phase 1-2 API.

**Duration**: 18-23 hours | **Story Points**: 12

**Prerequisites**: Phase 1-2 backend must be complete and API returning raw_score and score_breakdown.

## Orchestration Quick Reference

**Batch 1** (Parallel - 5h):
- TASK-3.1 → `ui-engineer-enhanced` (2h) - Create CatalogEntryModal component skeleton
- TASK-3.3 → `ui-engineer-enhanced` (1h) - Create reusable ScoreBreakdown component
- TASK-5.1 → `ui-engineer-enhanced` (1.5h) - Create ConfidenceFilter component
- TASK-5.5 → `ui-engineer-enhanced` (0.5h) - Update API client for filter params

**Batch 2** (Parallel - 2.5h, requires Batch 1):
- TASK-3.2 → `ui-engineer-enhanced` (0.5h) - Build modal header section
- TASK-3.5 → `ui-engineer-enhanced` (1h) - Add description and file list sections
- TASK-3.6 → `ui-engineer-enhanced` (0.5h) - Add action buttons to modal
- TASK-5.2 → `ui-engineer-enhanced` (0.5h) - Add low-confidence checkbox to filter

**Batch 3** (Sequential - 0.5h, requires Batch 2):
- TASK-3.4 → `ui-engineer-enhanced` (0.5h) - Add confidence section to modal

**Batch 4** (Sequential - 0.5h, requires Batch 3):
- TASK-3.7 → `ui-engineer-enhanced` (0.5h) - Wire modal to catalog card click

**Batch 5** (Parallel - 2.5h, requires Batch 4):
- TASK-3.8 → `ui-engineer-enhanced` (0.5h) - Add accessibility features to modal
- TASK-4.1 → `ui-engineer-enhanced` (1h) - Create ScoreBreakdownTooltip wrapper
- TASK-5.3 → `ui-engineer-enhanced` (1h) - Integrate filter into source page

**Batch 6** (Parallel - 2.5h, requires Batch 5):
- TASK-3.9 → `ui-engineer-enhanced` (0.5h) - Write Storybook stories for modal
- TASK-4.2 → `ui-engineer-enhanced` (1h) - Update ScoreBadge component with tooltip
- TASK-5.4 → `ui-engineer-enhanced` (1h) - Sync filter state with URL query params

**Batch 7** (Parallel - 2h, requires Batch 6):
- TASK-4.3 → `ui-engineer-enhanced` (0.5h) - Wire breakdown data from API
- TASK-4.4 → `ui-engineer-enhanced` (0.5h) - Add accessibility to tooltip
- TASK-5.6 → `ui-engineer-enhanced` (1h) - Wire filter to list updates

**Batch 8** (Parallel - 1h, requires Batch 7):
- TASK-4.5 → `ui-engineer-enhanced` (0.5h) - Write Storybook stories for tooltip
- TASK-5.7 → `ui-engineer-enhanced` (0.5h) - Test filter shareable URLs

### Task Delegation Commands

```
# Batch 1
Task("ui-engineer-enhanced", "TASK-3.1: Create CatalogEntryModal component. New React component using Radix Dialog and unified-entity-modal patterns. Component renders modal with title, close button, sections for metadata/files/actions. File: skillmeat/web/components/CatalogEntryModal.tsx (NEW)")

Task("ui-engineer-enhanced", "TASK-3.3: Create reusable ScoreBreakdown component. Extract breakdown display logic (table of signals) into standalone component for reuse in tooltip and modal. Component accepts breakdown object; renders as formatted list with +/- indicators and totals. File: skillmeat/web/components/ScoreBreakdown.tsx (NEW)")

Task("ui-engineer-enhanced", "TASK-5.1: Create ConfidenceFilter component. Range slider (0-100) or min/max input fields. Component renders with visible min/max inputs; default min=50, max=100. File: skillmeat/web/components/ConfidenceFilter.tsx (NEW)")

Task("ui-engineer-enhanced", "TASK-5.5: Update API client for filter params. Pass filter params to GET /catalog endpoint. fetchCatalogEntries() accepts filter object; converts to query params (min_confidence, max_confidence, include_below_threshold). File: skillmeat/web/lib/api/marketplace.ts")

# Batch 2 (after Batch 1)
Task("ui-engineer-enhanced", "TASK-3.2: Build modal header section. Display artifact icon, name, type badge, source path. Header shows icon+name in large text; type badge (skill/command/agent); source as subtitle. File: skillmeat/web/components/CatalogEntryModal.tsx")

Task("ui-engineer-enhanced", "TASK-3.5: Add description and file list sections. Display artifact description (if available) and file list. Sections collapsible if space constrained; shows SKILL.md content preview if available. File: skillmeat/web/components/CatalogEntryModal.tsx")

Task("ui-engineer-enhanced", "TASK-3.6: Add action buttons to modal. Import button and 'View on GitHub' link. Buttons positioned in modal footer; import triggers import dialog; GitHub opens upstream_url in new tab. File: skillmeat/web/components/CatalogEntryModal.tsx")

Task("ui-engineer-enhanced", "TASK-5.2: Add 'Include low-confidence artifacts' checkbox. Toggle to show/hide artifacts below 30% threshold. Checkbox below slider; controlled state; label clear. File: skillmeat/web/components/ConfidenceFilter.tsx")

# Batch 3 (after Batch 2)
Task("ui-engineer-enhanced", "TASK-3.4: Add confidence section to modal. Integrate ScoreBreakdown with score badge in modal header/body section. Shows 'Confidence: 95%'; breakdown section below with raw→normalized calculation. File: skillmeat/web/components/CatalogEntryModal.tsx")

# Batch 4 (after Batch 3)
Task("ui-engineer-enhanced", "TASK-3.7: Wire modal to catalog card click. Update catalog entry card component to open modal on click. Click card → modal opens with clicked entry data. File: skillmeat/web/components/CatalogCard.tsx")

# Batch 5 (after Batch 4)
Task("ui-engineer-enhanced", "TASK-3.8: Add accessibility features to modal. Focus trap, escape key close, aria labels. Focus management: initial focus on close button; trap within modal; Escape key closes; aria-describedby on all sections. File: skillmeat/web/components/CatalogEntryModal.tsx")

Task("ui-engineer-enhanced", "TASK-4.1: Create ScoreBreakdownTooltip wrapper. Wrap ScoreBreakdown in Radix Tooltip component. Tooltip renders on hover and focus; displays full breakdown. File: skillmeat/web/components/ScoreBreakdownTooltip.tsx (NEW)")

Task("ui-engineer-enhanced", "TASK-5.3: Integrate filter into source page. Add ConfidenceFilter to catalog entry list page. Filter appears in sidebar or header; updating controls doesn't refresh entire page. File: skillmeat/web/app/marketplace/sources/[id]/page.tsx")

# Batch 6 (after Batch 5)
Task("ui-engineer-enhanced", "TASK-3.9: Write Storybook stories for modal. Create stories for modal in different states (loading, with/without breakdown, empty). Stories cover: open/closed states; with/without data; accessibility features visible. File: skillmeat/web/stories/CatalogEntryModal.stories.tsx (NEW)")

Task("ui-engineer-enhanced", "TASK-4.2: Update ScoreBadge component. Add optional breakdown prop; integrate ScoreBreakdownTooltip. ScoreBadge without breakdown shows simple badge; with breakdown prop shows tooltip on hover. File: skillmeat/web/components/ScoreBadge.tsx")

Task("ui-engineer-enhanced", "TASK-5.4: Sync filter state with URL query params. onChange handlers update URL with min_confidence, max_confidence, include_below_threshold. URL changes as user adjusts filters; page reload preserves filter state from URL params. File: skillmeat/web/app/marketplace/sources/[id]/page.tsx")

# Batch 7 (after Batch 6)
Task("ui-engineer-enhanced", "TASK-4.3: Wire breakdown data from API. Update components to receive breakdown from CatalogEntryResponse. ScoreBadge receives breakdown via props from parent component. Files: skillmeat/web/components/ScoreBadge.tsx, parent components")

Task("ui-engineer-enhanced", "TASK-4.4: Add accessibility (keyboard & aria). Ensure tooltip accessible via keyboard focus; proper ARIA attributes. Tooltip triggers on Tab+Enter; aria-describedby links badge to tooltip content; role='tooltip'. File: skillmeat/web/components/ScoreBreakdownTooltip.tsx")

Task("ui-engineer-enhanced", "TASK-5.6: Wire filter to list updates. List updates when filter state changes. List re-queries with new params; shows loading state; updates on change (debounce if needed). File: skillmeat/web/app/marketplace/sources/[id]/page.tsx")

# Batch 8 (after Batch 7)
Task("ui-engineer-enhanced", "TASK-4.5: Write Storybook stories for tooltip. Stories showing tooltip with different scores and penalties. Stories show: 100% confidence, 50% confidence, with large penalties, keyboard access. File: skillmeat/web/stories/ScoreBreakdownTooltip.stories.tsx (NEW)")

Task("ui-engineer-enhanced", "TASK-5.7: Test filter shareable URLs. Verify filter state persists across page shares. User can copy URL with filters applied; shared link applies same filters. File: skillmeat/web/app/marketplace/sources/[id]/page.tsx")
```

## Quality Gates

**Phase 3 (Modal)**:
- [ ] Modal opens/closes correctly (click, escape, backdrop)
- [ ] All artifact data displays properly
- [ ] Keyboard navigation works (Tab, Escape)
- [ ] Screen reader announces all sections
- [ ] Import and GitHub buttons functional
- [ ] Modal center-positioned and responsive on mobile

**Phase 4 (Tooltip)**:
- [ ] Tooltip appears on hover with no delay
- [ ] Tooltip accessible via keyboard (focus + enter)
- [ ] Breakdown renders in consistent format
- [ ] All signal names and values visible
- [ ] Raw → normalized calculation visible

**Phase 5 (Filter)**:
- [ ] Filter controls render and respond to input
- [ ] URL reflects current filter state
- [ ] Query params properly formatted
- [ ] List updates immediately on filter change
- [ ] Filter state persists on page reload
- [ ] Low-confidence toggle reveals hidden artifacts

## Key Files

**Phase 3 (Modal)**:
- `skillmeat/web/components/CatalogEntryModal.tsx` (NEW)
- `skillmeat/web/components/ScoreBreakdown.tsx` (NEW - reusable)
- `skillmeat/web/components/CatalogCard.tsx` (modified to add onClick)
- `skillmeat/web/stories/CatalogEntryModal.stories.tsx` (NEW)

**Phase 4 (Tooltip)**:
- `skillmeat/web/components/ScoreBadge.tsx` (modified)
- `skillmeat/web/components/ScoreBreakdownTooltip.tsx` (NEW - wrapper)
- `skillmeat/web/stories/ScoreBreakdownTooltip.stories.tsx` (NEW)

**Phase 5 (Filter)**:
- `skillmeat/web/components/ConfidenceFilter.tsx` (NEW)
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` (modified)
- `skillmeat/web/lib/api/marketplace.ts` (modified fetchCatalogEntries)

## Success Criteria

**Modal (Phase 3)**:
- [ ] CatalogEntryModal opens on card click and closes on escape/click outside
- [ ] Modal displays artifact name, type, path, description, files list
- [ ] Modal shows confidence breakdown with all signals and calculation
- [ ] Modal action buttons functional (Import, View on GitHub)
- [ ] All text and interactive elements accessible to screen readers

**Tooltip (Phase 4)**:
- [ ] Tooltip displays on hover and keyboard focus
- [ ] Tooltip shows complete breakdown with raw→normalized calculation
- [ ] ScoreBreakdown component reused in both modal and tooltip

**Filter (Phase 5)**:
- [ ] ConfidenceFilter component renders and responds to input changes
- [ ] Filter state persists in URL query parameters
- [ ] min_confidence and max_confidence parameters filter list correctly
- [ ] include_below_threshold=true reveals hidden artifacts
- [ ] List updates without full page reload when filters change
- [ ] Filter state preserved on page reload

## Notes

- Phases 3-5 can run largely in parallel within each batch
- All components should follow Radix UI patterns from existing components
- ScoreBreakdown component is shared between modal and tooltip (DRY principle)
- Filter integration requires coordination with API client
- Storybook stories document all component states for design review
