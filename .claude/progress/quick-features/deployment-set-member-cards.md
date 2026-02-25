---
feature: deployment-set-member-cards
status: in-progress
created: 2026-02-25
scope: frontend-only
files_affected:
  - skillmeat/web/components/deployment-sets/mini-group-card.tsx (new)
  - skillmeat/web/components/deployment-sets/mini-deployment-set-card.tsx (new)
  - skillmeat/web/components/deployment-sets/add-member-dialog.tsx (modify)
  - skillmeat/web/components/deployment-sets/member-list.tsx (modify)
---

# Deployment Set Member Cards Enhancement

## Requirements
1. "Already Selected" state in Add Member dialog (greyed out + disabled + overlay text)
2. Minified cards for Groups and Sets in Add Member dialog (matching MiniArtifactCard pattern)
3. Hover tooltip on Group/Set cards showing stacked member list with type icons
4. Members tab uses minified cards (clickable, with set-specific info like member position)

## Batch 1: New Components (parallel)
- [ ] MiniGroupCard - compact card with group name, artifact count, color bar, tooltip with member list
- [ ] MiniDeploymentSetCard - compact card with set name, member count, color, tooltip with member list

## Batch 2: Integration (parallel, depends on batch 1)
- [ ] Update add-member-dialog.tsx - use new cards, add "Already Selected" disabled state
- [ ] Update member-list.tsx - replace MemberRow with minified cards, maintain click-to-open + remove
