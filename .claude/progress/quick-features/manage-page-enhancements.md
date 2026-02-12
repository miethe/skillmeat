# Quick Feature: Manage Page Enhancements

**Status**: completed
**Started**: 2026-02-11
**Feature Slug**: manage-page-enhancements

## Overview

Enhance the /manage page with improved Projects filter and enriched artifact cards showing comprehensive management information.

## Requirements

### 1. Projects Filter Enhancement
- **Current**: Projects computed client-side from deployments
- **Target**: Use `useProjects()` hook to fetch all projects from API
- **Behavior**: Selecting a project filters artifacts to only those deployed to that project
- **File**: `skillmeat/web/components/manage/manage-page-filters.tsx`

### 2. Enhanced Artifact Cards (Operations)
- **Current Card**: `artifact-operations-card.tsx` (operations-focused)
- **Target**: Make cards slightly larger to accommodate new information
- **File**: `skillmeat/web/components/manage/artifact-operations-card.tsx`

#### Components to Add (from Browse Card)
- **Tag Cloud**: Display all linked tags (first 3 + overflow count)
  - Reference: `artifact-browse-card.tsx` lines showing tag display logic
- **Deployed Badge**: Show "Deployed (count)" with CheckCircle2 icon
  - Reference: Browse card deployment badge pattern
  - Count from `artifact.deployments?.length ?? 0`

#### Indicators to Wire/Add
- **Last Synced**: Wire to actual `last_synced` timestamp (currently may be placeholder)
- **Upstream Updates Available**: New indicator when source has newer version
- **Collection Updates (Pushable)**: New indicator when collection has changes that can be pushed
- **Project Updates (Pullable)**: New indicator when project has changes that can be pulled

#### Design Considerations
- Keep cards unique from /collection browse cards
- Focus on operational/management information
- Maintain operations-focused layout (health, drift, actions)
- Consider visual hierarchy: most critical info first

## Files Affected

1. `skillmeat/web/components/manage/manage-page-filters.tsx` - Projects filter
2. `skillmeat/web/components/manage/artifact-operations-card.tsx` - Enhanced card
3. `skillmeat/web/app/manage/page.tsx` - Pass projects data, update filtering logic

## Key Patterns

### Data Fetching
- **Projects**: `useProjects()` hook (2min stale time)
- **Deployments**: Available via `artifact.deployments`
- **Tags**: Available via `artifact.tags`
- **Sync Status**: Check `artifact.upstream_status`, `artifact.last_synced`

### Component References
- **Tag Display**: See `artifact-browse-card.tsx` tag rendering logic
- **Deployed Badge**: See browse card deployment badge pattern
- **Deployment Stack**: Already in operations card via `DeploymentBadgeStack`

## Implementation Strategy

1. **Projects Filter** (manage-page-filters.tsx):
   - Import and use `useProjects()` hook
   - Replace `availableProjects` prop with hook data
   - Map to dropdown options with proper formatting

2. **Enhanced Card** (artifact-operations-card.tsx):
   - Add Tag Cloud section (adapt from browse card)
   - Add Deployed badge (adapt from browse card)
   - Wire Last Synced to actual timestamp
   - Design and add new update indicators:
     - Check `artifact.upstream_status` for upstream updates
     - Add collection/project diff indicators (may need new data)
   - Adjust card sizing/layout to accommodate new info
   - Maintain operations focus

3. **Filtering Logic** (manage/page.tsx):
   - Ensure project filter works with deployments
   - Filter artifacts where `deployments.some(d => d.project_path matches selected project)`

## Success Criteria

- [x] Projects filter loads all projects from API via `useProjects()`
- [x] Selecting a project filters artifacts correctly
- [x] Tag Cloud displays on operations cards (first 3 + overflow)
- [x] Deployed badge shows deployment count
- [x] Last Synced indicator shows actual timestamp
- [x] New update indicators designed and implemented (Pushable, Deployment Drift)
- [x] Cards are visually distinct from collection browse cards
- [x] All TypeScript checks pass (build succeeds)
- [x] All tests pass (70/70 manage tests)
- [x] All linting passes

## Quality Gates

```bash
cd skillmeat/web
pnpm test
pnpm typecheck
pnpm lint
pnpm build
```

## Notes

- Operations card should remain operations-focused (not become a duplicate of browse card)
- Consider badge/indicator placement for visual hierarchy
- Sync status and update indicators are most critical for management use case
- Tag Cloud and Deployed count provide context but shouldn't dominate the layout
