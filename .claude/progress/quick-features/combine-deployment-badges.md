---
feature: combine-deployment-badges
status: completed
created: 2026-02-11
completed: 2026-02-11
---

# Quick Feature: Combine Deployment Badges on Artifact Cards

## Description

Currently, artifact cards on /manage page show deployment info on two separate lines:
- "Deployed (x)" badge in status row
- "Deployed to: [project badges]" on dedicated row

**Goal**: Combine both on single line, showing "Deployed" badge followed by project badges, with "+x" overflow indicator.

## Changes Required

### File: `skillmeat/web/components/manage/artifact-operations-card.tsx`

1. **Remove** the separate "Deployed to:" row (lines 374-382)
2. **Modify** the "Deployed (x)" badge section (lines 419-424) to:
   - Show "Deployed" badge (no count in parentheses)
   - Immediately followed by DeploymentBadgeStack component
   - DeploymentBadgeStack handles overflow with "+x" badge and tooltip
   - Clicking badge should open modal to Deployments tab

### Component Integration

- Reuse existing `DeploymentBadgeStack` component (already has overflow/tooltip logic)
- Maintain click handler to open deployments modal
- Keep existing styling patterns from status badges row

## Success Criteria

- [x] Pattern discovery complete
- [x] Implementation complete
- [x] Quality gates passed (build successful)
- [x] Type errors fixed
- [x] Modal tab navigation fixed

## Implementation Notes

DeploymentBadgeStack already provides:
- Individual project badges (up to maxBadges)
- "+N" overflow badge with tooltip
- Click handlers
- Proper spacing and layout
