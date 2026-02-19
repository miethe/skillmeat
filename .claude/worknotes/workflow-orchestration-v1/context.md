---
type: context
prd: workflow-orchestration-v1
created: '2026-02-06'
updated: '2026-02-06'
schema_version: 2
doc_type: context
feature_slug: workflow-orchestration-v1
---

# Workflow Orchestration v1 - Agent Context Notes

## Key Decisions

1. **Builder Pattern**: Structured vertical stage list with @dnd-kit, NOT freeform canvas/node-graph. Simpler, accessible, sufficient for v1.
2. **DnD Library**: @dnd-kit recommended (16.5K stars, best accessibility, ~11KB, MIT). Installed as @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities.
3. **StageDispatcher**: Pluggable interface for v1. Real agent dispatch (Claude CLI/SDK) is separate integration task.
4. **Execution State**: DB-native (SQLite), no filesystem run state. Snapshot semantics: execution locks workflow version at start.
5. **Max Concurrency**: 3 concurrent stages (configurable). Excess queued.
6. **Expression Language**: Limited to property access, comparisons, booleans, 4 built-in functions. No Jinja2.
7. **SSE + Polling**: Real-time via SSE, 30s polling fallback.
8. **Schema Source**: SWDL spec at `docs/project_plans/specs/workflow-orchestration-schema-spec.md`.
9. **Memory Integration**: Fully integrated with existing ContextPackerService (v1 implemented). Workflows bind Context Modules per stage.

## Key Files

- PRD: `docs/project_plans/PRDs/features/workflow-orchestration-v1.md`
- Schema Spec: `docs/project_plans/specs/workflow-orchestration-schema-spec.md`
- UI/UX Spec: `docs/project_plans/design/workflow-orchestration-ui-spec.md`
- Implementation Plan: `docs/project_plans/implementation_plans/features/workflow-orchestration-v1.md`
- Progress: `.claude/progress/workflow-orchestration-v1/phase-{0-7}-progress.md`

## Observations

(Add observations during implementation)

## Blockers

(Track blockers during implementation)
