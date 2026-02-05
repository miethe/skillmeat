# Unified Sync Workflow - Development Context

**PRD**: unified-sync-workflow
**Started**: 2026-02-04
**Status**: Plan v2.0 - Ready for Implementation (post-review)

## Quick Links

| Resource | Location |
|----------|----------|
| Implementation Plan (v2) | `docs/project_plans/implementation_plans/features/unified-sync-workflow-v1.md` |
| Plan Review Report | `docs/project_plans/reports/unified-sync-workflow-plan-review-2026-02-05.md` |
| Phase 1 Progress | `.claude/progress/unified-sync-workflow/phase-1-progress.md` |
| Phase 2 Progress | `.claude/progress/unified-sync-workflow/phase-2-progress.md` |
| Phase 3 Progress | `.claude/progress/unified-sync-workflow/phase-3-progress.md` |
| Phase 4 Progress | `.claude/progress/unified-sync-workflow/phase-4-progress.md` |
| Exploration Docs | `.claude/worknotes/unified-sync-workflow/SYNC_QUICK_START.md` |
| Request Log | `REQ-20260204-skillmeat` (MeatyCapture) |

## Feature Summary

Enhance SkillMeat's sync workflow to provide conflict-aware, DiffViewer-first operations across all three directions:

1. **Pull from Source → Collection** (upgrade: add DiffViewer confirmation)
2. **Deploy Collection → Project** (upgrade: pre-diff check + merge strategy)
3. **Push Project → Collection** (upgrade: replace AlertDialog with DiffViewer)

## Plan v2 Changes (from review 2026-02-05)

| Change | Reason |
|--------|--------|
| Added Phase 1 backend tasks | Deploy needs merge strategy; source-vs-project needs endpoint |
| Single unified dialog | Build ONE SyncConfirmationDialog for all directions (not 2 separate) |
| Pull flow included | Original plan omitted pull despite stating "all directions" |
| Push tasks rewritten | Push UI already fully exists; tasks now UPGRADE, not build from scratch |
| useConflictCheck unified | Replaces separate hooks; push uses `/diff` (not upstream) |
| Estimates reconciled | 13→25 pts |

## Key Decisions

### Architecture
- **Backend changes needed**: Source-vs-project diff endpoint + merge-capable deploy
- **Single unified dialog**: SyncConfirmationDialog configurable for all 3 directions
- **Merge gating**: Enabled only when target has changes not in source
- **MergeWorkflowDialog**: Already bidirectional, route to it from unified dialog

### Validated Current State (2026-02-05)
- Push flow IS complete (button + dialog + mutation + cache invalidation)
- MergeWorkflowDialog IS bidirectional (not upstream-only)
- SyncDialog IS upstream-only (review was correct about this)
- Deploy API IS overwrite-only (needs merge strategy extension)
- DiffEngine IS production-ready (can handle source-vs-project trivially)

## API Reference

| Endpoint | Status | Purpose |
|----------|--------|---------|
| `POST /artifacts/{id}/sync` | Existing | Pull from source or push from project |
| `POST /artifacts/{id}/deploy` | **Extend** | Add `strategy: 'merge'` support |
| `GET /artifacts/{id}/diff` | Existing | Compare collection vs project |
| `GET /artifacts/{id}/upstream-diff` | Existing | Compare source vs collection |
| `GET /artifacts/{id}/source-project-diff` | **New** | Compare source vs project directly |

## Subagent Assignments

| Phase | Primary Agent | Model | Secondary |
|-------|--------------|-------|-----------|
| Phase 1 | python-backend-engineer, ui-engineer-enhanced | Opus | - |
| Phase 2 | ui-engineer-enhanced | Opus | Sonnet for tests |
| Phase 3 | ui-engineer-enhanced | Opus/Sonnet | - |
| Phase 4 | ui-engineer-enhanced | Sonnet | code-reviewer |

## Blockers & Notes

- **Risk**: MergeWorkflowDialog operates on snapshots; may need adapter for project paths (SYNC-A03)
- **Risk**: Deploy merge starts file-level only (no 3-way merge in v1)

## Session Log

### 2026-02-04 - Planning Session
- Created implementation plan v1 with 4 phases
- All exploration docs created

### 2026-02-05 - Review & Revision
- Received plan review report with 6 findings
- Validated all findings against codebase (4 explorers in parallel)
- Findings validated: F1 partially correct, F2 partially correct, F3-F6 correct
- Rewrote plan to v2.0: new task IDs, restructured phases, added backend work
- Updated all 4 progress files with new YAML frontmatter

**Next Step**: Execute Phase 1 Batch 1 (SYNC-B01, SYNC-B02, SYNC-H01 in parallel)
