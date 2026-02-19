---
title: 'Implementation Plan: Tools API Support for Artifact Metadata'
description: Wire up tools field from artifact frontmatter to API responses and database
  cache for collection filtering and badges.
audience:
- ai-agents
- developers
tags:
- implementation
- api
- tools
- metadata
- cache
created: 2026-02-02
updated: 2026-02-02
category: features
status: inferred_complete
complexity: Small
total_effort: 4-5 hours
phases: 2
related:
- /docs/project_plans/PRDs/tools-api-support-v1.md
- /docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md
- /docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1.md
---
# Implementation Plan: Tools API Support for Artifact Metadata

**Plan ID**: `IMPL-2026-02-02-tools-api-support`
**Date**: 2026-02-02
**Author**: Implementation Planner (Opus)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/tools-api-support-v1.md`
- **Downstream**: `/docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md` (Phase 4: FILTER-4.2)
- **Prior Work**: `/docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1.md`

**Complexity**: Small
**Total Estimated Effort**: 4-5 hours (reduced due to prior work)
**Target Timeline**: Single sprint

---

## Executive Summary

Complete the tools field wiring for collection API endpoints. Prior work (enhanced-frontmatter-utilization) established the Tool enum, core model, and artifact detail response. This plan adds tools to `ArtifactSummary` (collection endpoints), populates `tools_json` in the cache, and extracts tools from frontmatter.

**Key Outcomes**:
1. `tools` field appears in `ArtifactSummary` responses (collection endpoints)
2. `tools_json` cached in `CollectionArtifact` for DB-first reads
3. Frontmatter tools extracted and populated during artifact sync
4. Frontend can filter by tools once Phase 4 of manage-collection-page-refactor is implemented

---

## Gap Analysis (Prior Work)

### Already Implemented (enhanced-frontmatter-utilization)

| Component | Location | Status |
|-----------|----------|--------|
| Tool enum (Python) | `skillmeat/core/enums.py:58-135` | ✅ Complete (18 tools) |
| Tool enum (TypeScript) | `skillmeat/web/types/enums.ts:23-42` | ✅ Complete (mirror) |
| Core artifact model `.tools` | `skillmeat/core/artifact.py:57` | ✅ Complete |
| ArtifactMetadataResponse.tools | `skillmeat/api/schemas/artifacts.py:189-193` | ✅ Complete |
| API response conversion | `skillmeat/api/routers/artifacts.py:527-531` | ✅ Complete |
| API filtering by tools param | `skillmeat/api/routers/artifacts.py:1707-1821` | ✅ Complete |
| Migration template | `skillmeat/cache/migrations/versions/20260122_1100_*` | ✅ Pattern exists |

### Still Missing (This Plan)

| Component | Location | Required Change |
|-----------|----------|-----------------|
| ArtifactSummary.tools | `skillmeat/api/schemas/user_collections.py:211` | Add `tools: Optional[List[str]]` |
| ArtifactSummary.tools | `skillmeat/api/schemas/collections.py:43` | Add `tools: Optional[List[str]]` |
| CollectionArtifact.tools_json | `skillmeat/cache/models.py:893` | Add column + property |
| Alembic migration | `skillmeat/cache/migrations/versions/` | Add tools_json to collection_artifacts |
| Frontmatter extraction | `skillmeat/core/parsers/markdown_parser.py` | Extract tools field |
| Cache population | Cache sync code (TBD) | Populate tools_json from metadata |

### Architecture Flow

```
Artifact Frontmatter (SKILL.md)
    ↓
Marketplace Source / GitHub Import
    ↓
Frontmatter Parser (extract tools)
    ↓
CollectionArtifact.tools_json (cached)
    ↓
API Response (ArtifactSummary.tools)
    ↓
UI Tools Filter & Badges
```

### Parallel Work Opportunities

- Schema updates (API + model) can run in parallel
- Migration can be created while schema work is in progress
- Tests can be written alongside implementation

---

## Phase Breakdown

### Phase 1: Schema & Data Model (3-4 hours)

**Objective**: Add tools field to schemas and database model with migration.

**Dependencies**: None
**Assigned Subagents**: python-backend-engineer, data-layer-expert

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) |
|---------|-----------|-------------|---------------------|-----|-------------|
| TOOLS-1.1 | Add tools to ArtifactSummary (user_collections) | Add `tools: Optional[List[str]] = Field(default=None)` to ArtifactSummary in user_collections.py | 1. Field present in schema<br>2. Default is None<br>3. Type is List[str] | 0.5h | python-backend-engineer |
| TOOLS-1.2 | Add tools to ArtifactSummary (collections) | Add `tools: Optional[List[str]] = Field(default=None)` to ArtifactSummary in collections.py | 1. Field present in schema<br>2. Consistent with user_collections | 0.5h | python-backend-engineer |
| TOOLS-1.3 | Add tools_json to CollectionArtifact | Add `tools_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to CollectionArtifact model | 1. Column defined in model<br>2. Type is Text/nullable<br>3. Property to parse JSON | 1h | data-layer-expert |
| TOOLS-1.4 | Create Alembic migration | Create migration `add_tools_to_collection_artifacts` with tools_json column and index | 1. Migration runs cleanly<br>2. Index on tools_json created<br>3. Upgrade/downgrade work | 1h | data-layer-expert |
| TOOLS-1.5 | Add tools property to CollectionArtifact | Add `@property def tools(self) -> List[str]` that parses tools_json | 1. Returns empty list if None<br>2. Parses JSON correctly<br>3. Type safe | 0.5h | python-backend-engineer |

**Phase 1 Quality Gates**:
- [ ] Schema changes compile without errors
- [ ] Migration runs on dev database
- [ ] Model property returns correct types
- [ ] No breaking changes to existing API responses

**Phase 1 Output Artifacts**:
- Updated `skillmeat/api/schemas/user_collections.py`
- Updated `skillmeat/api/schemas/collections.py`
- Updated `skillmeat/cache/models.py`
- New migration in `skillmeat/cache/migrations/versions/`

---

### Phase 2: Cache Population & API Wiring (3-4 hours)

**Objective**: Populate tools during cache sync and include in API responses.

**Dependencies**: Phase 1 complete
**Assigned Subagents**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent(s) |
|---------|-----------|-------------|---------------------|-----|-------------|
| TOOLS-2.1 | Extract tools in frontmatter parser | Add `tools` extraction to `extract_metadata()` or create `extract_tools()` function | 1. Tools extracted from frontmatter<br>2. Returns List[str]<br>3. Handles missing tools gracefully | 1h | python-backend-engineer |
| TOOLS-2.2 | Populate tools in cache sync | Update cache population logic to store tools_json during artifact sync/refresh | 1. tools_json populated on sync<br>2. JSON serialized correctly<br>3. Works for new and existing artifacts | 1.5h | backend-architect |
| TOOLS-2.3 | Wire tools to user-collections endpoint | Update `/api/v1/user-collections/{id}/artifacts` to include tools from cache | 1. tools field in response<br>2. DB-first path works<br>3. Fallback path works | 0.5h | python-backend-engineer |
| TOOLS-2.4 | Wire tools to artifacts endpoint | Update `/api/v1/artifacts` to include tools from cache | 1. tools field in response<br>2. Consistent with user-collections | 0.5h | python-backend-engineer |
| TOOLS-2.5 | Add unit tests | Create tests for tools extraction, caching, and API responses | 1. Parser tests pass<br>2. Cache tests pass<br>3. API response tests pass<br>4. Coverage >80% | 1h | python-backend-engineer |

**Phase 2 Quality Gates**:
- [ ] Tools extracted from sample SKILL.md frontmatter
- [ ] Cache populated with tools_json on sync
- [ ] API responses include tools field
- [ ] All tests passing
- [ ] No performance regression in API response times

**Phase 2 Output Artifacts**:
- Updated `skillmeat/core/parsers/markdown_parser.py`
- Updated cache population code (location TBD by exploration)
- Updated API routers/services for tools inclusion
- Test files for tools functionality

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Migration conflicts with existing data | Medium | Low | Nullable column, no default value required |
| Tools parsing varies across sources | Low | Medium | Graceful fallback to empty list |
| Performance impact on API responses | Low | Low | JSON column is already indexed pattern |

### Dependencies

| Dependency | Status | Impact if Blocked |
|------------|--------|-------------------|
| Tool enum | ✅ Complete | N/A |
| Frontmatter parser | ✅ Infrastructure exists | N/A |
| CollectionArtifact model | Needs update | Blocking for Phase 1 |

---

## Resource Requirements

### Team Composition
- Backend Developer: 6-8 hours total
- No frontend work required (downstream in manage-collection-page-refactor)

### Skill Requirements
- Python, FastAPI, SQLAlchemy
- Alembic migrations
- JSON serialization

---

## Success Metrics

### Delivery Metrics
- All API tests passing
- Migration runs cleanly
- No breaking changes to existing responses

### Functional Metrics
- `tools` field appears in `/user-collections/{id}/artifacts` response
- `tools` field appears in `/artifacts` response
- Tools cached in DB for DB-first reads

---

## Open Questions (From PRD)

| Question | Recommended Answer | Rationale |
|----------|-------------------|-----------|
| Normalize tools to enum values on write? | Yes - validate against Tool enum | Ensures consistency, catches typos |
| Backfill tools for artifacts missing metadata? | Empty list (not null) | Consistent filtering behavior |
| Expose tools on marketplace endpoints? | Out of scope for this PRD | Add in future if needed |

---

## Integration with Downstream Work

This implementation unblocks **FILTER-4.2** in `manage-collection-page-refactor-v1.md`:

> **FILTER-4.2**: Enhance CollectionPageFilters with tools filter
> Add Tools multi-select popover to existing filters. **Depends on Tools API PRD**

Once this implementation is complete, the frontend can:
1. Display tool badges on ArtifactBrowseCard
2. Implement tools multi-select filter
3. Filter artifacts by tool usage

---

**Progress Tracking**: See `.claude/progress/tools-api-support/phase-1-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-02
