---
type: context
schema_version: 2
doc_type: context
prd: deployment-sets-v2
feature_slug: deployment-sets
created: 2026-02-24
updated: 2026-02-24
---

# Deployment Sets v2 — Context Worknotes

**Plan**: `docs/project_plans/implementation_plans/features/deployment-sets-v2.md`
**Progress**: `.claude/progress/deployment-sets-v2/all-phases-progress.md`

## Key Decisions

- Frontend-only enhancement — no backend/API changes needed
- DeploymentSetMemberCard is a NEW component, not a fork of ArtifactBrowseCard (avoids 735-line entanglement)
- Detail page deprecated with redirect before removal (protect bookmarks)
- Nested modal (Set member) uses Radix Dialog built-in portal/focus management

## Key Files

| Component | Path |
|-----------|------|
| Modal (new) | `skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx` |
| Member Card (new) | `skillmeat/web/components/deployment-sets/deployment-set-member-card.tsx` |
| Set Card (modify) | `skillmeat/web/components/deployment-sets/deployment-set-card.tsx` |
| Add Dialog (modify) | `skillmeat/web/components/deployment-sets/add-member-dialog.tsx` |
| List Page (modify) | `skillmeat/web/app/deployment-sets/deployment-sets-page-client.tsx` |
| Detail Page (deprecate) | `skillmeat/web/app/deployment-sets/[id]/` |

## Reference Components

| Component | Path | Relevance |
|-----------|------|-----------|
| ArtifactDetailsModal | `skillmeat/web/components/collection/artifact-details-modal.tsx` | Modal pattern to follow |
| ArtifactBrowseCard | `skillmeat/web/components/collection/artifact-browse-card.tsx` | Visual style reference for member card |
| MiniArtifactCard | `skillmeat/web/components/collection/mini-artifact-card.tsx` | Used in AddMemberDialog grid |

## Observations

(Agent observations will be added during implementation)
