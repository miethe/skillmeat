---
# === TOOLS API SUPPORT - DEVELOPMENT CONTEXT ===
# PRD-level sticky pad for agent notes and observations

type: context
prd: "tools-api-support"
title: "Tools API Support - Development Context"
status: "active"
created: "2026-02-02"
updated: "2026-02-02"

critical_notes_count: 1
implementation_decisions_count: 2
active_gotchas_count: 1
agent_contributors: ["Opus (planner)"]

agents:
  - { agent: "Opus", note_count: 4, last_contribution: "2026-02-02" }
---

# Tools API Support - Development Context

**Status**: Active Development
**Created**: 2026-02-02
**Last Updated**: 2026-02-02

> **Purpose**: Shared worknotes for agents implementing tools API support. This feature wires up the `tools` field from artifact frontmatter to API responses and the collection cache.

---

## Quick Reference

**Agent Notes**: 4 notes from 1 agent
**Critical Items**: 1 item requiring attention
**Last Contribution**: Opus on 2026-02-02

**Implementation Plan**: `/docs/project_plans/implementation_plans/features/tools-api-support-v1.md`
**PRD**: `/docs/project_plans/PRDs/tools-api-support-v1.md`
**Downstream**: `/docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md` (FILTER-4.2)

---

## Implementation Decisions

### 2026-02-02 - Opus (Planner) - Reuse existing Tool enum

**Decision**: Use existing `Tool` enum from `skillmeat/core/enums.py` without modification

**Rationale**: Enum already contains all 18 Claude Code tools with proper PascalCase naming, and has a TypeScript mirror

**Location**: `skillmeat/core/enums.py:58-135`

**Impact**: No enum work needed; focus on wiring

---

### 2026-02-02 - Opus (Planner) - JSON column pattern for tools

**Decision**: Store tools as JSON array in `tools_json` TEXT column (same as `tags_json` pattern)

**Rationale**: Consistent with existing CollectionArtifact patterns, supports arbitrary tool lists, enables JSON containment queries

**Location**: `skillmeat/cache/models.py` (CollectionArtifact class)

**Impact**: Need property accessor for convenient Python access

---

## Gotchas & Observations

### 2026-02-02 - Opus (Planner) - MarketplaceCatalogEntry migration exists but model not updated

**What**: Migration `20260122_1100_add_tools_and_linked_artifacts.py` adds tools to `marketplace_catalog_entries`, but the `MarketplaceCatalogEntry` model in `models.py` doesn't have the field

**Why**: Migration was created but model definition wasn't updated to match

**Solution**: May need to add `tools` field to MarketplaceCatalogEntry model too, or confirm the migration was never applied

**Affects**: `skillmeat/cache/models.py:1599` (MarketplaceCatalogEntry)

---

## Integration Notes

### 2026-02-02 - Opus (Planner) - Tools flow from frontmatter to UI

**From**: Artifact SKILL.md frontmatter
**To**: ArtifactBrowseCard (UI)
**Method**:
1. Frontmatter parsed by `markdown_parser.py`
2. Tools stored in `CollectionArtifact.tools_json`
3. API returns tools in `ArtifactSummary` response
4. Frontend renders tool badges (manage-collection-page-refactor Phase 4)

**Notes**: This PRD only covers backend (steps 1-3). Frontend badges/filter (step 4) is in FILTER-4.2 of manage-collection-page-refactor

---

## Key Files Reference

| File | Purpose | Notes |
|------|---------|-------|
| `skillmeat/core/enums.py:58-135` | Tool enum | ✅ Complete, 18 tools |
| `skillmeat/web/types/enums.ts:23-42` | Tool enum (TS) | ✅ Mirror of Python enum |
| `skillmeat/api/schemas/artifacts.py:189-212` | ArtifactMetadataResponse.tools | ✅ Already has tools field |
| `skillmeat/api/schemas/user_collections.py:211` | ArtifactSummary | ❌ Needs tools field |
| `skillmeat/api/schemas/collections.py:43` | ArtifactSummary | ❌ Needs tools field |
| `skillmeat/cache/models.py:893` | CollectionArtifact | ❌ Needs tools_json column |
| `skillmeat/core/parsers/markdown_parser.py` | Frontmatter parser | ❌ Needs tools extraction |

---

## Agent Handoff Notes

### 2026-02-02 - Opus (Planner) → Phase 1 Agents

**Completed**: Implementation plan, progress tracking, and context files created

**Next**: Execute Phase 1 tasks (TOOLS-1.1 through TOOLS-1.5) following batch order in progress file

**Watch Out For**:
- Start with batch_1 tasks in parallel (TOOLS-1.1, 1.2, 1.3)
- Don't start batch_2 until batch_1 complete (migration depends on model)
- Use Sonnet model for implementation tasks (well-scoped, single file)

---

## References

**Progress Tracking**:
- `.claude/progress/tools-api-support/phase-1-progress.md`
- `.claude/progress/tools-api-support/phase-2-progress.md`

**Related Plans**:
- `/docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md`
- `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`
