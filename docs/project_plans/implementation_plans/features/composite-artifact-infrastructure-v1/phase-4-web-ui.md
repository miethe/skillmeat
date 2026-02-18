---
title: "Phase 4: Web UI Relationship Browsing"
description: "Frontend implementation of artifact relationships with contains/part-of tabs and import preview"
audience: [ai-agents, developers]
tags: [implementation, phase-4, frontend, react, ui, ux]
created: 2026-02-17
updated: 2026-02-17
category: "product-planning"
status: draft
related:
  - /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
---

# Phase 4: Web UI Relationship Browsing

**Phase ID**: CAI-P4
**Duration**: 3-4 days
**Dependencies**: Phase 3 complete (API endpoint stable)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, python-backend-engineer (API)
**Estimated Effort**: 14 story points

---

## Phase Overview

Phase 4 brings the Composite Artifact Infrastructure to the web UI, enabling users to:

1. Browse "Contains" tab showing which artifacts are in a Plugin
2. View "Part of" section showing which Plugins contain an artifact
3. See an import preview modal before confirming plugin import
4. Navigate parent↔child relationships within 2 clicks
5. Resolve version conflicts when deploying plugins with pinned versions

This phase transforms the system from invisible backend infrastructure into a user-facing feature.

---

## Task Breakdown

### CAI-P4-01: AssociationsDTO TypeScript Type

**Description**: Generate or manually create the TypeScript type for `AssociationsDTO` that matches the backend API response schema. This enables type-safe frontend code.

**Acceptance Criteria**:
- [x] TypeScript type `AssociationsDTO` defined with:
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
- [x] Type location: `skillmeat/web/types/associations.ts` (or similar)
- [x] Type matches backend OpenAPI schema exactly
- [x] Can be imported and used in React components
- [x] No type errors in IDE when using type

**Implementation Approach**:
- Option A: Use OpenAPI code-gen tool (if available in project): `openapi-generator` or `openapi-typescript`
- Option B: Manually create type based on backend schema from `skillmeat/api/schemas/associations.py`
- Option C: Hand-write type in TypeScript file

**Key Files to Create/Modify**:
- `skillmeat/web/types/associations.ts` (new) — Define AssociationsDTO and AssociationItemDTO

**Estimate**: 1 story point

---

### CAI-P4-02: useArtifactAssociations Hook

**Description**: Create a React hook that fetches artifact associations via the API endpoint. The hook handles loading/error/success states and caches results appropriately.

**Acceptance Criteria**:
- [x] Hook signature: `useArtifactAssociations(artifactId: string): AssociationsState`
- [x] Return type:
  ```typescript
  interface AssociationsState {
    data: AssociationsDTO | null;
    isLoading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
  }
  ```
- [x] Behavior:
  - Fetches `GET /api/v1/artifacts/{artifactId}/associations` on mount and when artifactId changes
  - Caches results (React Query or similar)
  - Handles loading state
  - Handles errors gracefully (doesn't crash, returns error in state)
  - Allows manual refetch
- [x] Performance:
  - Response cached for 5 minutes
  - Deduplicates requests for same artifact
  - Doesn't refetch if artifactId unchanged
- [x] Error handling:
  - 404 errors handled gracefully (artifact not found)
  - Network errors captured
  - Returns error in state (doesn't throw)
- [x] Unit tests:
  - Hook fetches associations on mount
  - Hook updates when artifactId changes
  - Error state works
  - Refetch works
  - Caching works (no duplicate requests)

**Key Files to Create/Modify**:
- `skillmeat/web/hooks/useArtifactAssociations.ts` (new) — Define hook
- `tests/hooks/useArtifactAssociations.test.ts` (new) — Hook tests

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
- [x] Tab implementation:
  - Added to artifact detail page tabs
  - Label: "Contains"
  - Visible only when `artifact.type === "plugin"` OR when `associations.children.length > 0`
- [x] Tab content displays:
  - List of child artifacts
  - For each child: name, type (icon), description snippet
  - Link to child artifact detail page
  - Sorted by name (or by relationship_type if needed)
- [x] Empty state:
  - If plugin has no children, show "This plugin contains no artifacts"
  - Still show tab to indicate plugin nature
- [x] Loading state:
  - While fetching associations, show loading spinner
  - Skeleton loaders for list items (if using shadcn Skeleton)
- [x] Error state:
  - If API error, show error message
  - Offer retry button
- [x] Mobile responsive:
  - Tab content readable on mobile
  - List items stack correctly
- [x] Accessibility:
  - Tab accessible via keyboard (Tab key)
  - Tab marked as current with `aria-current="page"` when active
  - List items have semantic meaning (use `<ul>` and `<li>`)

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
- [x] Section placement:
  - Sidebar (right side of detail page) OR below metadata section
  - Visible only when `associations.parents.length > 0`
  - Label: "Part of"
- [x] Content displays:
  - List of parent Plugins
  - For each parent: name, link to parent detail
  - Indicate relationship type (e.g., "contained in", "required by")
- [x] Empty state:
  - If no parents, section is hidden (no "Part of" section shown)
- [x] Loading state:
  - While fetching associations, show loading spinner
- [x] Error handling:
  - If API error, show error message gracefully
- [x] Mobile responsive:
  - Works on narrow screens
  - May move to below detail when on mobile
- [x] Accessibility:
  - List items semantic
  - Links have descriptive text
  - Section is announced by screen readers

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

**Description**: Update the import modal to show a breakdown of what will be imported when a composite artifact is detected. Preview shows: Plugin name, number of children, count of new vs existing artifacts.

**Acceptance Criteria**:
- [x] Modal enhancement:
  - When importing a Plugin (detected via `DiscoveredGraph`), show additional preview section
  - Atomic artifacts (non-composite) show existing import modal (no changes)
- [x] Preview content displays:
  - Plugin name
  - Total child count
  - Breakdown: "X new artifacts, Y already in collection, Z with version conflicts"
  - Expandable list of children with their import status
  - Example: "git-workflow-pro (Plugin)\n- 1 Skill (new)\n- 2 Commands (existing)\n- 1 Agent (conflict)"
- [x] Child status indicators:
  - "new" — artifact will be created
  - "existing" — artifact already in collection, will be linked/reused
  - "conflict" — artifact exists with different version, may need resolution
- [x] User actions:
  - User can expand/collapse child list
  - User can click child to see more details
  - Primary action: "Import" button (enabled when valid)
  - Secondary action: "Cancel" button
- [x] Before/after comparison (optional):
  - Show current collection artifact count before import
  - Show projected count after import
- [x] Mobile responsive:
  - Modal works on narrow screens
  - List items readable
- [x] Accessibility:
  - ARIA live region announces summary when modal opens
  - Keyboard navigation works (Tab, Enter, Esc to close)
  - Screen readers can access all information

**Key Files to Create/Modify**:
- `skillmeat/web/components/import-modal.tsx` — Update to detect composite and show preview
- May create new component: `skillmeat/web/components/import/composite-preview.tsx`

**Implementation Notes**:
- Import modal receives discovery result (flat or graph)
- Check if result is `DiscoveredGraph` to determine if composite
- If composite, show preview UI; if atomic, show existing modal
- Preview data comes from `DiscoveredGraph` (from discovery phase), not API
- Mock data for E2E tests: create fake `DiscoveredGraph` with known children

**Estimate**: 2 story points

---

### CAI-P4-06: Version Conflict Resolution Dialog

**Description**: Implement a dialog that appears when deploying a Plugin with pinned child versions that conflict with currently deployed versions. Dialog offers side-by-side or overwrite resolution.

**Acceptance Criteria**:
- [x] Dialog trigger:
  - Appears during plugin deployment if version conflict detected
  - Shows which child artifact has conflicting version
  - Displays: artifact name, pinned hash (brief), current hash (brief), date of conflict
- [x] Dialog content:
  - Clear explanation of conflict: "Plugin expects version A, but you have version B deployed"
  - Two resolution options:
    - **Side-by-side**: Deploy plugin version separately (renamed, e.g., `git-commit-v1.2.0`)
    - **Overwrite**: Use plugin's pinned version, override currently deployed version
  - Escape hatch: "Skip plugin deployment" to abort without changes
- [x] User decision:
  - User selects resolution option
  - Dialog closes
  - Deployment proceeds with chosen resolution
- [x] Multiple conflicts:
  - If multiple children have conflicts, show all in single dialog or wizard
  - Allow user to choose resolution per conflict
- [x] Mobile responsive:
  - Dialog readable on mobile
  - Options clear
- [x] Accessibility:
  - Dialog properly announced via ARIA
  - Buttons clearly labeled
  - Keyboard navigation (Tab, Enter)
  - Focus trap in dialog

**Key Files to Create/Modify**:
- `skillmeat/web/components/deployment/conflict-resolution-dialog.tsx` (new) — Define dialog
- May integrate with existing deployment flow

**Implementation Notes**:
- Dialog is triggered by deployment logic (not in this phase's scope, but integration point)
- Conflict detection happens on backend; frontend receives conflict info
- Side-by-side strategy: Backend handles renaming/versioning logic
- Overwrite strategy: User explicitly chooses to override; log this for audit
- Consider if user should see hash diff visualization (nice-to-have, not required)

**Estimate**: 2 story points

---

### CAI-P4-07: Accessibility (a11y)

**Description**: Ensure all UI components for relationships meet WCAG 2.1 AA standards. Focus on keyboard navigation, screen reader support, and semantic HTML.

**Acceptance Criteria**:
- [x] Keyboard navigation:
  - All tabs accessible via Tab key
  - All buttons/links accessible via Tab
  - Enter key activates buttons
  - Esc key closes dialogs
  - Tab order logical and visible (focus ring visible)
- [x] Screen readers:
  - Tabs announced correctly (role=`tablist`, role=`tab`)
  - Current tab indicated (aria-current or aria-selected)
  - Tab content announced when tab becomes active
  - List items announced with count (e.g., "1 of 3")
  - Links have descriptive text (not "click here")
  - Dialogs announced with aria-modal
- [x] Semantic HTML:
  - Use `<ul>`/`<li>` for lists
  - Use proper heading levels (h2, h3)
  - Use `<button>` for buttons (not `<div>` with click handler)
  - Use `<a>` for links
- [x] Color contrast:
  - Text meets 4.5:1 contrast ratio (AA standard)
  - Don't rely on color alone to convey status (use icons/text)
- [x] Labels and instructions:
  - Form inputs have associated labels
  - Dialogs have descriptive titles
  - Error messages associated with inputs (aria-describedby)
- [x] Testing:
  - Axe accessibility scanner runs on all new components
  - NVDA/JAWS screen reader testing (manual or automated)
  - Keyboard-only navigation tested
  - No automated a11y errors

**Key Files to Create/Modify**:
- `skillmeat/web/components/artifact/artifact-contains-tab.tsx` — Add a11y features
- `skillmeat/web/components/artifact/artifact-part-of-section.tsx` — Add a11y features
- `skillmeat/web/components/import/composite-preview.tsx` — Add a11y features
- `skillmeat/web/components/deployment/conflict-resolution-dialog.tsx` — Add a11y features

**Implementation Notes**:
- Use `aria-*` attributes from shadcn/ui components (they handle a lot automatically)
- Test with keyboard only (no mouse) — verify all interactions work
- Use WebAIM contrast checker for color compliance
- Run axe accessibility scanner in CI
- Consider user with screen reader testing tools (NVDA on Windows, VoiceOver on Mac)

**Estimate**: 1 story point

---

### CAI-P4-08: E2E Tests (Playwright)

**Description**: Write end-to-end tests using Playwright covering the full user journey: import flow with composite preview, "Contains" tab navigation, "Part of" section visibility, and conflict resolution.

**Acceptance Criteria**:
- [x] Test file: `skillmeat/web/__tests__/e2e/composite-artifacts.spec.ts`
- [x] Test scenarios:
  1. **Import composite flow**:
     - User navigates to import
     - Pastes plugin repo URL
     - Discovery detects composite
     - Import preview modal shows breakdown
     - User clicks "Import"
     - Plugin appears in collection
  2. **"Contains" tab**:
     - User opens plugin detail page
     - "Contains" tab visible
     - User clicks "Contains" tab
     - Child artifacts list displays
     - User clicks child artifact link
     - Navigates to child detail page
  3. **"Part of" section**:
     - User opens child artifact detail page
     - "Part of" section visible (if artifact has parents)
     - Shows parent plugin link
     - User clicks parent link
     - Navigates to parent detail page
  4. **Conflict resolution** (if deploy workflow in scope):
     - User deploys plugin
     - Conflict detected (version mismatch)
     - Dialog appears
     - User selects resolution
     - Dialog closes
     - Deployment proceeds
- [x] Test coverage:
  - Happy path: Import → browse relationships
  - Error scenarios: Network errors, missing data
  - Mobile: Tests run on mobile viewport
  - Accessibility: Tab navigation tested
- [x] Performance:
  - Tests complete in <60 seconds per scenario
  - No flakiness (re-run 5x, all pass)
- [x] CI integration:
  - Tests run in GitHub Actions
  - Headless Chromium browser
  - Screenshots on failure
  - Video recording optional

**Key Files to Create/Modify**:
- `skillmeat/web/__tests__/e2e/composite-artifacts.spec.ts` (new) — E2E test file
- `skillmeat/web/__tests__/e2e/fixtures/` — May add fixtures for test data

**Implementation Notes**:
- Use existing Playwright setup in project (if available)
- Tests should use test database (not production)
- Create test plugins/artifacts via API before running E2E (use `page.request()`)
- Use page object pattern for maintainability (separate selectors from test logic)
- Headless mode for CI; headed mode for local development
- Screenshots on failure help debugging

**Estimate**: 2 story points

---

## Phase 4 Quality Gates

Before Phase 4 is complete, all the following must pass:

- [ ] TypeScript types match backend OpenAPI schema
- [ ] `useArtifactAssociations` hook fetches and caches correctly
- [ ] "Contains" tab visible for plugins, lists children correctly
- [ ] "Part of" section visible for artifacts with parents
- [ ] Import preview modal shows composite breakdown before user confirms
- [ ] Version conflict dialog appears on deploy conflict, offers resolutions
- [ ] All new components pass accessibility checks (axe scanner <0 violations)
- [ ] Keyboard navigation works: Tab, Enter, Esc all functional
- [ ] Screen reader testing: NVDA/VoiceOver can access all content
- [ ] E2E tests pass: Import → browse relationships → conflicts (if applicable)
- [ ] E2E tests are not flaky (pass 5/5 consecutive runs)
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

Reference existing E2E tests in `skillmeat/web/__tests__/e2e/`:
- Use page objects for selectors
- Use fixtures for test data
- Use `waitFor()` for async operations
- Take screenshots on failure

---

## Deliverables Checklist

- [ ] TypeScript types for `AssociationsDTO` defined and exported
- [ ] `useArtifactAssociations` hook implemented with caching and error handling
- [ ] "Contains" tab added to artifact detail page (conditional on composite type)
- [ ] "Part of" section added to artifact detail page (conditional on parents)
- [ ] Import preview modal updated to show composite breakdown
- [ ] Version conflict resolution dialog implemented
- [ ] All components pass accessibility checks (axe <0 violations)
- [ ] Keyboard navigation tested and working
- [ ] E2E tests cover import flow, tab navigation, section visibility
- [ ] E2E tests pass consistently (5/5 runs)
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
Version: 1.0
Last Updated: 2026-02-17
