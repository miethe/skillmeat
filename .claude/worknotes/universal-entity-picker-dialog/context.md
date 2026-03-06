---
type: context
prd: "universal-entity-picker-dialog"
title: "Universal Entity Picker Dialog - Development Context"
status: "active"
created: "2026-03-06"
updated: "2026-03-06"

critical_notes_count: 0
implementation_decisions_count: 1
active_gotchas_count: 0
agent_contributors: []

agents: []
---

# Universal Entity Picker Dialog - Development Context

**Status**: Active Development
**Created**: 2026-03-06
**Last Updated**: 2026-03-06

> **Purpose**: This is a shared worknotes file for all AI agents working on this PRD. Add brief observations, decisions, gotchas, and implementation notes that future agents should know. Think of this as a sticky-note pad for the development team.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: None yet

---

## Implementation Decisions

> Key architectural and technical decisions made during development

### 2026-03-06 - Orchestrator - Extract Domain-Agnostic EntityPickerDialog

**Decision**: Extract generic `EntityPickerDialog` from `AddMemberDialog` patterns, configured via `EntityPickerTab[]` interface. Dialog has no mutation coupling; parent components handle form state and persistence.

**Rationale**: Reusable component enables rich browsable entity selection across workflow UI without code duplication. Generic interface allows different data sources (artifacts, context modules) to be plugged in via adapter hooks.

**Location**: `skillmeat/web/components/shared/entity-picker-dialog.tsx` (TBD: created in Phase 1, UEPD-1.1)

**Impact**:
- Simplifies Stage Editor and Builder Sidebar integration (Phases 2-3)
- Reduces maintenance burden of multiple picker implementations
- Future use cases can reuse same component with new tab configurations

---

## Gotchas & Observations

> Things that tripped us up or patterns discovered during implementation

*None recorded yet. Add observations as work progresses.*

---

## Integration Notes

> How components interact and connect

*None recorded yet. Document integration points as work progresses.*

---

## Performance Notes

> Performance considerations discovered during implementation

*None recorded yet. Record any performance findings here.*

---

## Agent Handoff Notes

> Quick context for agents picking up work

*None recorded yet. Add handoff notes between batches/phases.*

---

## References

**Related Files**:
- **PRD**: `docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md`
- **Progress - Phase 1**: `.claude/progress/universal-entity-picker-dialog/phase-1-progress.md`
- **Progress - Phase 2**: `.claude/progress/universal-entity-picker-dialog/phase-2-progress.md`
- **Progress - Phase 3**: `.claude/progress/universal-entity-picker-dialog/phase-3-progress.md`

**Source Components (Reference)**:
- `skillmeat/web/components/deployment-sets/add-member-dialog.tsx` (patterns to extract)
- `skillmeat/web/components/collection/mini-artifact-card.tsx` (visual pattern for MiniContextEntityCard)
- `skillmeat/web/components/context/context-entity-card.tsx` (mini variant source)

**Integration Points** (Modified in Phases 2-3):
- `skillmeat/web/components/workflow/stage-editor.tsx` (lines ~413-432; Primary Agent + Support Tools pickers)
- `skillmeat/web/components/workflow/builder-sidebar.tsx` (lines ~426-443; Global Modules picker)

**Hooks** (Reused, no modifications):
- `skillmeat/web/hooks/index.ts` (useInfiniteArtifacts, useContextModules, useIntersectionObserver, useDebounce)

**Types & Config** (Referenced, no modifications):
- `skillmeat/web/types/workflow.ts` (RoleAssignment, StageRoles, ContextBinding)
- `skillmeat/web/types/index.ts` (Artifact, ContextModuleResponse)
- `skillmeat/web/lib/context-entity-config.ts` (type color mapping for badges)

---

## Template Examples

<details>
<summary>How to add an Implementation Decision</summary>

### [YYYY-MM-DD] - [Agent Name] - [Brief Decision Title]

**Decision**: [What was decided in 1-2 sentences]

**Rationale**: [Why in 1-2 sentences]

**Location**: `path/to/file.ext:line`

**Impact**: [What this affects]

</details>

<details>
<summary>How to add a Gotcha/Observation</summary>

### [YYYY-MM-DD] - [Agent Name] - [Brief Gotcha Title]

**What**: [What happened in 1-2 sentences]

**Why**: [Root cause in 1 sentence]

**Solution**: [How to avoid/fix in 1-2 sentences]

**Affects**: [Which files/components/phases]

</details>

<details>
<summary>How to add an Integration Note</summary>

### [YYYY-MM-DD] - [Agent Name] - [Integration Point Name]

**From**: [Component A]
**To**: [Component B]
**Method**: [API call, prop passing, event, etc.]
**Notes**: [Brief context, gotchas, or important details]

</details>

<details>
<summary>How to add an Agent Handoff</summary>

### [YYYY-MM-DD] - [Completing Agent] → [Next Agent]

**Completed**: [What was just finished]
**Next**: [What should be done next]
**Watch Out For**: [Any gotchas or warnings]

</details>
