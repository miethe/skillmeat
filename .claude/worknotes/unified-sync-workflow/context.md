# Unified Sync Workflow - Development Context

**PRD**: unified-sync-workflow
**Started**: 2026-02-04
**Status**: Planning Complete, Ready for Implementation

## Quick Links

| Resource | Location |
|----------|----------|
| Implementation Plan | `docs/project_plans/implementation_plans/features/unified-sync-workflow-v1.md` |
| Phase 1 Progress | `.claude/progress/unified-sync-workflow/phase-1-progress.md` |
| Phase 2 Progress | `.claude/progress/unified-sync-workflow/phase-2-progress.md` |
| Phase 3 Progress | `.claude/progress/unified-sync-workflow/phase-3-progress.md` |
| Phase 4 Progress | `.claude/progress/unified-sync-workflow/phase-4-progress.md` |
| Exploration Docs | `.claude/worknotes/unified-sync-workflow/SYNC_QUICK_START.md` |
| Request Log | `REQ-20260204-skillmeat` (MeatyCapture) |

## Feature Summary

Enhance SkillMeat's sync workflow to provide conflict-aware operations across all three directions:

1. **Pull from Source → Collection** (already implemented)
2. **Deploy Collection → Project** (add pre-conflict check + diff viewer)
3. **Push Project → Collection** (add solid arrow, confirmation, diff viewer)

## Key Decisions

### Architecture
- **Frontend-only changes**: All backend APIs already exist and work
- **Reuse existing DiffViewer**: Integrate into confirmation dialogs
- **Progressive enhancement**: Add features without breaking existing flows

### UX Pattern
All sync directions follow unified pattern:
```
Action button → Pre-check diff API → [Show dialog if changes] →
User confirms strategy → Execute → Cache invalidate → Toast
```

### File Structure
```
New Components:
├── conflict-aware-deploy-dialog.tsx    # Phase 1
├── conflict-aware-push-dialog.tsx      # Phase 2
└── sync-confirmation-dialog.tsx        # Phase 3 (shared base)

New Hooks:
├── use-pre-deploy-check.ts             # Phase 1
├── use-pre-push-check.ts               # Phase 2
└── use-conflict-check.ts               # Phase 3 (unified)

Modified:
├── sync-status-tab.tsx                 # Integration
├── artifact-flow-banner.tsx            # Solid push arrow
└── comparison-selector.tsx             # Source vs Project option
```

## API Reference

All APIs are production-ready:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/artifacts/{id}/sync` | POST | Pull from source or push from project |
| `/artifacts/{id}/deploy` | POST | Deploy to project with overwrite |
| `/artifacts/{id}/diff` | GET | Compare collection vs project |
| `/artifacts/{id}/upstream-diff` | GET | Compare source vs collection |

## Current State

| Direction | Status | What Exists | What's Missing |
|-----------|--------|-------------|----------------|
| Pull Source→Collection | ✅ Complete | Full flow with merge dialog | - |
| Deploy Collection→Project | ⚠️ Partial | Works with overwrite | Pre-conflict check, diff preview |
| Push Project→Collection | ⚠️ Partial | Backend ready, footer button | Solid arrow, confirmation dialog, diff preview |

## Subagent Assignments

| Phase | Primary Agent | Model | Secondary |
|-------|--------------|-------|-----------|
| Phase 1 | ui-engineer-enhanced | Opus | - |
| Phase 2 | ui-engineer-enhanced | Opus | - |
| Phase 3 | ui-engineer-enhanced | Opus/Sonnet | - |
| Phase 4 | ui-engineer-enhanced | Sonnet | code-reviewer |

## Blockers & Notes

_None at this time_

## Session Log

### 2026-02-04 - Planning Session

- Created implementation plan with 4 phases, 25 tasks
- Total effort: 23 story points, 10-14 days
- All backend APIs confirmed working
- Created progress files for all phases
- Ready for Phase 1 execution

**Next Step**: Execute Phase 1 Batch 1 (SYNC-001 + SYNC-002 in parallel)
