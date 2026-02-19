---
type: context
prd: configurable-frontmatter-caching-v1
title: Configurable Frontmatter Caching - Development Context
status: active
created: '2026-01-20'
updated: '2026-01-20'
critical_notes_count: 0
implementation_decisions_count: 2
active_gotchas_count: 1
agent_contributors:
- orchestrator
agents:
- agent: orchestrator
  note_count: 3
  last_contribution: '2026-01-20'
schema_version: 2
doc_type: context
feature_slug: configurable-frontmatter-caching-v1
---

# Configurable Frontmatter Caching - Development Context

**Status**: Active Development
**Created**: 2026-01-20
**Last Updated**: 2026-01-20

> **Purpose**: This is a shared worknotes file for all AI agents working on this PRD. Add brief observations, decisions, gotchas, and implementation notes that future agents should know.

---

## Quick Reference

**Agent Notes**: 3 notes from 1 agent
**Critical Items**: 0 items requiring attention
**Last Contribution**: orchestrator on 2026-01-20

---

## Implementation Decisions

### 2026-01-20 - orchestrator - Use nullable column for indexing_enabled

**Decision**: The `indexing_enabled` column will be `Optional[bool]` (nullable) rather than a non-null boolean with default.

**Rationale**: NULL distinguishes "user hasn't set a preference" from explicit `false`. This allows the mode precedence logic to apply defaults correctly.

**Location**: `skillmeat/cache/models.py` (MarketplaceSource model)

**Impact**: Mode precedence logic must handle NULL case: `source.indexing_enabled if source.indexing_enabled is not None else <mode_default>`

---

### 2026-01-20 - orchestrator - Config key uses underscore for section name

**Decision**: Config key is `artifact_search.indexing_mode` (underscore in section, hyphen would also work)

**Rationale**: Follows existing pattern in ConfigManager where section names can use underscores. CLI access: `skillmeat config set artifact_search.indexing_mode opt_in`

**Location**: `skillmeat/config.py`

**Impact**: Frontend will need to fetch via new `/config/indexing-mode` endpoint or similar

---

## Gotchas & Observations

### 2026-01-20 - orchestrator - Existing enable_frontmatter_detection flag

**What**: MarketplaceSource already has `enable_frontmatter_detection` boolean flag for a different purpose (controlling frontmatter parsing during scan)

**Why**: This is NOT the same as `indexing_enabled` - the existing flag controls whether to parse frontmatter for artifact detection, while `indexing_enabled` controls whether to persist extracted data for search indexing

**Solution**: Keep both flags separate with clear naming. `indexing_enabled` is specifically for search indexing. Document the distinction clearly.

**Affects**: `skillmeat/cache/models.py`, `skillmeat/web/components/marketplace/add-source-modal.tsx`

---

## Integration Notes

### 2026-01-20 - orchestrator - Config → API → Frontend flow

**From**: ConfigManager (backend)
**To**: Frontend components (add-source-modal)
**Method**: New GET `/config/indexing-mode` endpoint returns current mode
**Notes**: Frontend needs to know the mode to determine toggle visibility and default state. Consider caching this in React Query with long staleTime since it rarely changes.

---

## Performance Notes

*No performance notes yet*

---

## Agent Handoff Notes

### 2026-01-20 - orchestrator → python-backend-engineer

**Completed**: PRD, Implementation Plan, Progress Tracking artifacts created

**Next**: Start with TASK-1.1 (add config key) and TASK-1.2 (helper methods). These are the foundation for all other work.

**Watch Out For**:
- Existing `enable_frontmatter_detection` flag is different from `indexing_enabled`
- Use nullable column (Optional[bool]) for indexing_enabled to support mode precedence
- Default mode should be "opt_in" (balanced approach)

---

## References

**Related Files**:
- Progress: `.claude/progress/configurable-frontmatter-caching-v1/all-phases-progress.md`
- PRD: `docs/project_plans/PRDs/enhancements/configurable-frontmatter-caching-v1.md`
- Implementation Plan: `docs/project_plans/implementation_plans/enhancements/configurable-frontmatter-caching-v1.md`
- Parent SPIKE: `docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md`

**Key Codebase Patterns**:
- ConfigManager: `skillmeat/config.py` - see `get_score_weights()` for similar helper pattern
- Source toggles: `skillmeat/web/components/marketplace/add-source-modal.tsx:375-641` - follow existing toggle pattern
- Model boolean flags: `skillmeat/cache/models.py:1260-1280` - follow `enable_frontmatter_detection` pattern
