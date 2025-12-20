---
type: context
prd: "artifact-deletion-v1"
feature: "Artifact Deletion from Collections and Projects"
created: "2025-12-20"
updated: "2025-12-20"
---

# Artifact Deletion Feature - Context

## Quick Reference

| Document | Path |
|----------|------|
| PRD | docs/project_plans/PRDs/features/artifact-deletion-v1.md |
| Implementation Plan | docs/project_plans/implementation_plans/features/artifact-deletion-v1.md |
| Phase 1 Progress | .claude/progress/artifact-deletion-v1/phase-1-progress.md |
| Phase 2 Progress | .claude/progress/artifact-deletion-v1/phase-2-progress.md |
| Phase 3 Progress | .claude/progress/artifact-deletion-v1/phase-3-progress.md |

## Key Decisions

### Entry Points

1. **Artifact Card Menu** (EntityActions component)
   - Delete option in "..." dropdown menu
   - Uses existing onDelete callback pattern

2. **Artifact Modal** (UnifiedEntityModal)
   - Delete button in Overview tab, beside "Edit Parameters"
   - RED destructive variant styling

### Deletion Flow

Multi-step dialog with cascading options:

```
Step 1: Primary Confirmation
├── Context-aware message ("Delete from Collection X" or "Delete from Project Y")
├── Toggle: "Also delete from [opposite]"
└── Toggle: "Delete Deployments" (if deployments > 0, RED)

Step 2A: Project Selection (if "Also delete from Projects" enabled)
└── Expandable section with project checkboxes

Step 2B: Deployment Warning (if "Delete Deployments" enabled)
└── Expandable section with RED styling, deployment path list
```

### API Integration

No new backend endpoints needed:

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Delete from collection | `/api/v1/artifacts/{id}` | DELETE |
| Remove deployment | `/api/v1/deploy/undeploy` | POST |

### Cache Invalidation

After deletion:
- `['artifacts']` - artifact lists
- `['deployments']` - deployment lists
- Entity lists for affected collections/projects

## Technical Notes

### Component Patterns

Reference existing patterns:
- `DeleteSourceDialog` - Cascade warning styling
- `entity-actions.tsx` - Simple delete confirmation (to be replaced)
- `use-collections.ts` - Mutation hook structure

### State Management

Dialog manages:
- `deleteFromOpposite: boolean`
- `deleteDeployments: boolean`
- `selectedProjects: string[]`
- `selectedDeployments: string[]`

### Error Handling

Partial failure support:
- Multiple undeployments can fail independently
- Report which succeeded/failed
- Allow retry

## Implementation Sessions

### Session 1 (2025-12-20)
- Created PRD with comprehensive requirements
- Created implementation plan with 3 phases
- Created progress tracking files for all phases
- Identified all file targets and dependencies

## Blockers & Risks

None currently identified. All required APIs are production-ready.

## Notes

- RED styling for "Delete Deployments" is critical for UX safety
- Partial failure handling is important for reliability
- Mobile responsiveness needed for dialog
