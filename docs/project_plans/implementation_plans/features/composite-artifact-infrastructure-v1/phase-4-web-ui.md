---
title: 'Phase 4: Web UI Relationship Browsing'
description: Frontend implementation of artifact relationships with contains/part-of
  tabs and import preview
audience:
- ai-agents
- developers
tags:
- implementation
- phase-4
- frontend
- react
- ui
- ux
created: 2026-02-17
updated: '2026-02-18'
category: product-planning
status: completed
related:
- /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
schema_version: 2
doc_type: phase_plan
feature_slug: composite-artifact-infrastructure
prd_ref: null
plan_ref: null
---

# Phase 4: Web UI Relationship Browsing

**Phase ID**: CAI-P4
**Duration**: 3-4 days
**Dependencies**: Phase 3 complete (API endpoint stable)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, python-backend-engineer (API + CLI)
**Estimated Effort**: 13 story points

---

## Phase Overview

Phase 4 brings the Composite Artifact Infrastructure to the web UI, enabling users to:

1. Browse "Contains" tab showing which artifacts are in a Plugin
2. View "Part of" section showing which Plugins contain an artifact
3. See an import preview modal before confirming plugin import
4. Navigate parent<->child relationships within 2 clicks
5. Resolve version conflicts when deploying plugins, connected to real backend API

Accessibility requirements are integrated into each component task rather than as a separate pass.

Composites appear alongside atomic artifacts in CLI listings, filtered by platform profile (default: Claude Code).

This phase transforms the system from invisible backend infrastructure into a user-facing feature.

---

## Task Breakdown

### CAI-P4-01: AssociationsDTO TypeScript Type

**Description**: Generate the TypeScript type for `AssociationsDTO` from OpenAPI so frontend contracts remain aligned with backend schema.

**Acceptance Criteria**:
- [ ] TypeScript type `AssociationsDTO` defined with:
  ```typescript
  interface AssociationsDTO {
    artifact_id: string;
    parents: AssociationItemDTO[];
    children: AssociationItemDTO[];
  }

  interface AssociationItemDTO {
    artifact_id: string;
    artifact_name: string;
    artifact_type: string;  // "skill", "command", "plugin", etc.
    relationship_type: string;  // "contains", etc.
    pinned_version_hash: string | null;
    created_at: string;  // ISO 8601
  }
  ```
- [ ] Type location: `skillmeat/web/types/associations.ts` (or similar)
- [ ] Type matches backend OpenAPI schema exactly
- [ ] Can be imported and used in React components
- [ ] No type errors in IDE when using type

**Implementation Approach**:
- Use OpenAPI code generation (`skillmeat/web/sdk/` + derived thin types) as canonical source
- Avoid manual type drift from hand-authored DTO copies

**Key Files to Create/Modify**:
- `skillmeat/web/types/associations.ts` (new) — Define AssociationsDTO and AssociationItemDTO

**Estimate**: 1 story point

---

### CAI-P4-02: useArtifactAssociations Hook

**Description**: Create a React hook that fetches artifact associations via the API endpoint. The hook handles loading/error/success states and caches results appropriately.

**Acceptance Criteria**:
- [ ] Hook signature: `useArtifactAssociations(artifactId: string): AssociationsState`
- [ ] Return type:
  ```typescript
  interface AssociationsState {
    data: AssociationsDTO | null;
    isLoading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
  }
  ```
- [ ] Behavior:
  - Fetches `GET /api/v1/artifacts/{artifactId}/associations` on mount and when artifactId changes
  - Caches results (React Query or similar)
  - Handles loading state
  - Handles errors gracefully (doesn't crash, returns error in state)
  - Allows manual refetch
- [ ] Performance:
  - Response cached for 5 minutes
  - Deduplicates requests for same artifact
  - Doesn't refetch if artifactId unchanged
- [ ] Error handling:
  - 404 errors handled gracefully (artifact not found)
  - Network errors captured
  - Returns error in state (doesn't throw)
- [ ] Unit tests:
  - Hook fetches associations on mount
  - Hook updates when artifactId changes
  - Error state works
  - Refetch works
  - Caching works (no duplicate requests)

**Key Files to Create/Modify**:
- `skillmeat/web/hooks/useArtifactAssociations.ts` (new) — Define hook
- `skillmeat/web/__tests__/hooks/useArtifactAssociations.test.ts` (new) — Hook tests

**Implementation Notes**:
- Use existing data-fetching pattern in project (likely React Query, SWR, or Fetch API)
- Follow existing hook patterns in `skillmeat/web/hooks/`
- Cache key should include artifactId: `["associations", artifactId]`
- Consider dependency array carefully to avoid unnecessary refetches

**Estimate**: 2 story points

---

### CAI-P4-03: "Contains" Tab UI

**Description**: Add a new tab to the artifact detail page showing child artifacts for composite types (Plugins). The tab is only visible for Plugin-type artifacts.

**Acceptance Criteria**:
- [ ] Tab implementation:
  - Added to artifact detail page tabs
  - Label: "Contains"
  - Visible only when `artifact.type === "plugin"` OR when `associations.children.length > 0`
- [ ] Tab content displays:
  - List of child artifacts
  - For each child: name, type (icon), description snippet
  - Link to child artifact detail page
  - Sorted by name (or by relationship_type if needed)
- [ ] Empty state:
  - If plugin has no children, show "This plugin contains no artifacts"
  - Still show tab to indicate plugin nature
- [ ] Loading state:
  - While fetching associations, show loading spinner
  - Skeleton loaders for list items (if using shadcn Skeleton)
- [ ] Error state:
  - If API error, show error message
  - Offer retry button
- [ ] Mobile responsive:
  - Tab content readable on mobile
  - List items stack correctly
- [ ] Meets WCAG 2.1 AA: keyboard navigation (Tab/Enter), semantic HTML (ul/li), screen reader announced

**Key Files to Create/Modify**:
- `skillmeat/web/app/artifacts/[id]/page.tsx` — Update detail page to add "Contains" tab
- May create new component: `skillmeat/web/components/artifact/artifact-contains-tab.tsx`

**Implementation Notes**:
- Use existing tab pattern from project (likely from shadcn/ui `Tabs` component)
- Leverage `useArtifactAssociations` hook from Phase 4-02
- Child artifact items should be clickable (link to detail page)
- Consider lazy-loading: only fetch associations when tab is first clicked

**Estimate**: 2 story points

---

### CAI-P4-04: "Part of" Section UI

**Description**: Add a sidebar section or inline section to artifact detail pages showing which Plugins contain this artifact. Visible for any atomic artifact that has parent associations.

**Acceptance Criteria**:
- [ ] Section placement:
  - Sidebar (right side of detail page) OR below metadata section
  - Visible only when `associations.parents.length > 0`
  - Label: "Part of"
- [ ] Content displays:
  - List of parent Plugins
  - For each parent: name, link to parent detail
  - Indicate relationship type (e.g., "contained in", "required by")
- [ ] Empty state:
  - If no parents, section is hidden (no "Part of" section shown)
- [ ] Loading state:
  - While fetching associations, show loading spinner
- [ ] Error handling:
  - If API error, show error message gracefully
- [ ] Mobile responsive:
  - Works on narrow screens
  - May move to below detail when on mobile
- [ ] Meets WCAG 2.1 AA: semantic list, descriptive link text, screen reader support

**Key Files to Create/Modify**:
- `skillmeat/web/app/artifacts/[id]/page.tsx` — Update detail page to add "Part of" section
- May create new component: `skillmeat/web/components/artifact/artifact-part-of-section.tsx`

**Implementation Notes**:
- Use same `useArtifactAssociations` hook
- Place in sidebar or as a card below artifact metadata (UI design decision)
- Consider conditional rendering: `{associations?.parents?.length > 0 && <PartOfSection />}`
- Links should navigate to parent artifact detail page

**Estimate**: 2 story points

---

### CAI-P4-05: Import Preview Modal

**Description**: Update the import modal to show a breakdown of what will be imported when a composite artifact is detected. Preview shows three buckets: new artifacts, existing identical matches, and conflicts.

**Acceptance Criteria**:
- [ ] Modal enhancement:
  - When importing a Plugin (detected via `DiscoveredGraph`), show additional preview section
  - Atomic artifacts (non-composite) show existing import modal (no changes)
- [ ] Preview displays three buckets:
  - **"New (Will Import)"**: Artifacts not found in collection — will be created
  - **"Existing (Identical Hash - Will Link)"**: Artifacts already in collection with matching content hash — will be linked/reused
  - **"Conflict (Different Hash - Needs Resolution)"**: Artifacts with same name but different content hash — user can fork as new version or merge via Sync Status
- [ ] Summary line:
  - Plugin name + total child count
  - Breakdown: "X new, Y existing (will link), Z conflicts"
- [ ] Child status indicators per bucket:
  - Expandable list of children grouped by bucket
  - Each child shows: name, type, status icon
- [ ] Conflict handling:
  - For conflicts: user can choose to fork as new version or defer to merge via Sync Status
  - Primary action: "Import" button (imports new + links existing; conflicts handled per user choice)
  - Secondary action: "Cancel" button
- [ ] Mobile responsive:
  - Modal works on narrow screens
  - List items readable
- [ ] ARIA live region announces summary on open. Keyboard navigation works (Tab, Enter, Esc to close).

**Key Files to Create/Modify**:
- `skillmeat/web/components/import-modal.tsx` — Update to detect composite and show preview
- May create new component: `skillmeat/web/components/import/composite-preview.tsx`

**Implementation Notes**:
- Import modal receives discovery result (flat or graph)
- Check if result is `DiscoveredGraph` to determine if composite
- If composite, show preview UI; if atomic, show existing modal
- Preview data comes from `DiscoveredGraph` (from discovery phase), not API
- Dedup results (which bucket each child falls into) come from backend dedup logic (CAI-P3-02)

**Estimate**: 2 story points

---

### CAI-P4-06: Version Conflict Resolution Dialog

**Description**: Implement a dialog that appears when deploying a Plugin with pinned child versions that conflict with currently deployed versions. Wired to real backend API for conflict detection and resolution. No stub backends.

**Acceptance Criteria**:
- [ ] Dialog trigger:
  - Appears during Claude Code plugin deployment if version conflict detected
  - Shows which child artifact has conflicting version
  - Displays: artifact name, pinned hash (brief), current hash (brief), date of conflict
- [ ] Dialog content:
  - Clear explanation of conflict: "Plugin expects version A, but you have version B deployed"
  - Two resolution options:
    - **Side-by-side**: Deploy plugin version separately (renamed, e.g., `git-commit-v1.2.0`)
    - **Overwrite**: Use plugin's pinned version, override currently deployed version
  - Escape hatch: "Skip plugin deployment" to abort without changes
- [ ] Backend integration:
  - Backend deployment propagation (CAI-P3-05) provides conflict data
  - Dialog consumes real API responses — no stubs
  - Resolution choice sent back to API for execution
- [ ] User decision:
  - User selects resolution option
  - Dialog closes
  - Deployment proceeds with chosen resolution
- [ ] Platform scope:
  - Claude Code: dialog + resolution workflow enabled
  - Other platforms: no dialog; UI shows "plugin deployment not yet supported on this platform"
- [ ] Multiple conflicts:
  - If multiple children have conflicts, show all in single dialog or wizard
  - Allow user to choose resolution per conflict
- [ ] Mobile responsive:
  - Dialog readable on mobile
  - Options clear
- [ ] Dialog has aria-modal, focus trap, keyboard navigation (Tab, Enter, Esc)

**Key Files to Create/Modify**:
- `skillmeat/web/components/deployment/conflict-resolution-dialog.tsx` (new) — Define dialog
- May integrate with existing deployment flow

**Implementation Notes**:
- Conflict detection happens on backend; frontend receives conflict info via API
- Side-by-side strategy: Backend handles renaming/versioning logic
- Overwrite strategy: User explicitly chooses to override; log this for audit
- Consider if user should see hash diff visualization (nice-to-have, not required)

**Estimate**: 2 story points

---

> **Note**: Accessibility requirements have been integrated into each component task (CAI-P4-03 through CAI-P4-06) rather than as a separate pass.

---

### CAI-P4-08: Core E2E Test (Playwright)

**Description**: Write end-to-end tests using Playwright covering the core user journeys: import flow with composite preview and "Contains" tab navigation.

**Acceptance Criteria**:
- [ ] Test file: `skillmeat/web/tests/e2e/composite-artifacts.spec.ts`
- [ ] Test scenarios:
  1. **Import composite flow**:
     - User navigates to import
     - Pastes plugin repo URL
     - Discovery detects composite
     - Import preview modal shows three-bucket breakdown
     - User clicks "Import"
     - Plugin appears in collection
  2. **"Contains" tab navigation**:
     - User opens plugin detail page
     - "Contains" tab visible
     - User clicks "Contains" tab
     - Child artifacts list displays
     - User clicks child artifact link
     - Navigates to child detail page
- [ ] Tests complete in <60 seconds per scenario

**Key Files to Create/Modify**:
- `skillmeat/web/tests/e2e/composite-artifacts.spec.ts` (new) — E2E test file

**Implementation Notes**:
- Use existing Playwright setup in project (if available)
- Tests should use test database (not production)
- Create test plugins/artifacts via API before running E2E (use `page.request()`)
- Use page object pattern for maintainability (separate selectors from test logic)
- Headless mode for CI; headed mode for local development

**Estimate**: 1 story point

---

### CAI-P4-09: CLI Composite Listing

**Description**: Ensure composites (Plugins) appear alongside atomic artifacts in `skillmeat list` output. Filter by platform profile (default: Claude Code shows Plugins). CLI displays composite type and child count.

**Acceptance Criteria**:
- [ ] `skillmeat list` shows composites alongside skills, commands, etc.
- [ ] Output includes composite_type and child artifact count
- [ ] Platform profile filter works (default Claude Code)

**Key Files to Modify**:
- `skillmeat/cli.py` or relevant CLI module

**Implementation Notes**:
- Query composites from DB alongside atomic artifacts
- Display composite_type (e.g., "plugin") and child count in list output
- Platform profile filtering: default to Claude Code, which shows Plugins
- Use existing Rich table output pattern for consistent formatting

**Dependencies**: Phase 1 complete

**Estimate**: 1 story point

**Subagent**: python-backend-engineer

---

## Phase 4 Quality Gates

Before Phase 4 is complete, all the following must pass:

- [ ] TypeScript types match backend OpenAPI schema
- [ ] `useArtifactAssociations` hook fetches and caches correctly
- [ ] "Contains" tab visible for plugins, lists children correctly
- [ ] "Contains" tab meets WCAG 2.1 AA (keyboard nav, semantic HTML, screen reader)
- [ ] "Part of" section visible for artifacts with parents
- [ ] "Part of" section meets WCAG 2.1 AA (semantic list, descriptive links, screen reader)
- [ ] Import preview modal shows three-bucket breakdown (new, existing, conflict) before user confirms
- [ ] Import preview modal has ARIA live region and keyboard navigation
- [ ] Version conflict dialog appears on deploy conflict, offers resolutions via real backend API
- [ ] Conflict dialog has aria-modal, focus trap, keyboard navigation
- [ ] Non-Claude platforms show explicit "plugin deployment not yet supported" state
- [ ] Core import E2E test passes
- [ ] CLI `skillmeat list` shows composites alongside atomic artifacts with type and child count
- [ ] Mobile responsive: All components work on 375px width
- [ ] No P0/P1 bugs found in QA testing

---

## Implementation Notes & References

### Component Patterns

Follow existing patterns in `skillmeat/web/components/`:
- Use shadcn/ui components for consistency
- Use Tailwind CSS for styling
- Use `react-query` for data fetching (or whatever is standard)
- Separate container components (logic) from presentational components (UI)

### Responsive Design

- Desktop: Full layout, sidebar on right
- Tablet: Adjusted spacing, stacked elements if needed
- Mobile: Single column, tabs below content

### Form/Dialog Patterns

Reference existing modal implementations in codebase:
- Use shadcn `Dialog` component
- Handle focus trap
- Implement escape-to-close
- Support form submission via Enter key

### Testing Patterns

Reference existing E2E tests in `skillmeat/web/tests/e2e/`:
- Use page objects for selectors
- Use fixtures for test data
- Use `waitFor()` for async operations
- Take screenshots on failure

---

## Deliverables Checklist

- [ ] TypeScript types for `AssociationsDTO` defined and exported
- [ ] `useArtifactAssociations` hook implemented with caching and error handling
- [ ] "Contains" tab added to artifact detail page (conditional on composite type) with a11y
- [ ] "Part of" section added to artifact detail page (conditional on parents) with a11y
- [ ] Import preview modal updated to show three-bucket composite breakdown with a11y
- [ ] Version conflict resolution dialog implemented with real backend API and a11y
- [ ] Core E2E test covers import flow and Contains tab navigation
- [ ] CLI `skillmeat list` shows composites alongside atomic artifacts
- [ ] Components responsive on mobile (375px+)
- [ ] All Phase 4 quality gates passing
- [ ] Code reviewed and merged to main branch

---

**Phase 4 Status**: Ready for implementation
**Estimated Completion**: 3-4 days from Phase 3 completion
**Feature Completion**: Phase 4 completion marks end of Composite Artifact Infrastructure feature

---

## Post-Phase 4: Production Readiness Checklist

After all phases complete, before shipping to production:

- [ ] Feature flag set appropriately (enabled/disabled based on rollout strategy)
- [ ] Monitoring and alerting configured
- [ ] Performance benchmarks met
- [ ] Load testing completed
- [ ] Security review completed
- [ ] Backwards compatibility verified (old single-artifact imports still work)
- [ ] Database backups verified
- [ ] Rollback procedure documented
- [ ] Release notes written
- [ ] User documentation updated
- [ ] Support/documentation team briefed

---

**Implementation Plan Complete**
Version: 1.1
Last Updated: 2026-02-18
