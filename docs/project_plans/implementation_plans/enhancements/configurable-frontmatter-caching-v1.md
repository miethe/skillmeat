---
title: "Implementation Plan: Configurable Frontmatter Indexing for Cross-Source Artifact Search"
description: "Detailed phased implementation with task breakdown and subagent assignments for search indexing controls"
audience: [ai-agents, developers]
tags: [implementation, planning, phases, tasks, marketplace, search, configuration, indexing]
created: 2026-01-20
updated: 2026-01-23
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/enhancements/configurable-frontmatter-caching-v1.md
  - /docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md
  - /docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1.md
---

# Implementation Plan: Configurable Frontmatter Indexing for Cross-Source Search

**Plan ID**: `IMPL-2026-01-20-configurable-frontmatter-caching`
**Date**: 2026-01-20
**Updated**: 2026-01-23
**Author**: Implementation Planner (Sonnet 4.5)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/enhancements/configurable-frontmatter-caching-v1.md`
- **SPIKE**: `/docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md`
- **Prerequisite (Complete)**: `/docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1.md`

**Complexity**: Medium
**Total Estimated Effort**: 26 story points (~3-4 days)
**Target Timeline**: 3-4 days (single developer)

## Executive Summary

This implementation adds configurable search indexing control for cross-source artifact search. Users can choose between three global modes (off/on/opt_in) and override behavior per-source, balancing storage costs against search capabilities.

**Prerequisite Context**: The `enhanced-frontmatter-utilization` feature (complete) already implements:
- Frontmatter extraction and caching in `artifact.metadata.extra['frontmatter']`
- Platform and Tool enums (17 Claude Code tools)
- Artifact linking system with UI components

This plan adds the **search indexing layer** on top of that foundation, enabling:
- Configurable control over whether extracted frontmatter is indexed for search
- Per-source granularity for indexing decisions
- Storage optimization for users who want frontmatter display but not search indexing

The implementation follows SkillMeat's layered architecture: ConfigManager → Database → API → Frontend, with parallel execution opportunities in testing and documentation phases.

## Implementation Strategy

### Architecture Sequence

Following SkillMeat's layered architecture:
1. **Configuration Layer** - Add `artifact_search.indexing_mode` config key with validation
2. **Database Layer** - Add `indexing_enabled` column to MarketplaceSource model
3. **API Layer** - Update schemas and endpoints to handle per-source flag
4. **UI Layer** - Add toggle controls to add/edit source modals with mode-aware visibility
5. **Testing Layer** - Unit tests for config, integration tests for full flow, E2E for UI
6. **Documentation Layer** - Update docstrings, inline comments, SPIKE references

### Parallel Work Opportunities

**Phase 1 (Backend foundation)**: Config and database work can be done sequentially (small tasks, dependencies)

**Phase 2 (API Layer)**: Schema updates can happen in parallel with endpoint changes

**Phase 3 (Frontend)**: add-source-modal and edit-source-modal can be updated in parallel

**Phase 4 (Testing + Docs)**: Unit tests, integration tests, and documentation can all proceed in parallel after implementation complete

### Critical Path

1. ConfigManager updates (FR-1, FR-6, FR-7) - **Blocks everything**
2. Database migration (FR-2) - **Blocks API and Frontend**
3. API schemas (FR-3) - **Blocks Frontend**
4. Frontend toggles (FR-4, FR-5) - **Final user-facing deliverable**
5. Testing and documentation - **Quality gates before release**

---

## Phase Breakdown

### Phase 1: Configuration Layer

**Duration**: 0.5 days
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer (Sonnet)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CFG-001 | Add config defaults | Add `artifact_search.indexing_mode` to ConfigManager default config with validation | Config key defaults to "opt_in", accepts "off"/"on"/"opt_in", invalid values log warning and default to "opt_in" | 2 pts | python-backend-engineer | None |
| CFG-002 | Add helper methods | Implement `get_indexing_mode()` and `set_indexing_mode()` convenience methods | Methods work, validate input, log changes at INFO level | 1 pt | python-backend-engineer | CFG-001 |
| CFG-003 | CLI command support | Add CLI command handler for `skillmeat config set artifact_search.indexing_mode` | CLI command works, validates values, persists to config.toml | 1 pt | python-backend-engineer | CFG-002 |

**Phase 1 Quality Gates:**
- [ ] Config persists to `~/.skillmeat/config.toml`
- [ ] Invalid mode values log warning and default to "opt_in"
- [ ] CLI command validates input and returns helpful errors
- [ ] Config survives app restart (persistence test)

**Implementation Notes:**
- Add to `ConfigManager._ensure_config_exists()` default config dict
- Validation in `set()` method or dedicated `set_indexing_mode()` helper
- CLI command can use existing `config set` infrastructure
- Log format: `"artifact_search.indexing_mode set to '{value}'"`

---

### Phase 2: Database Layer

**Duration**: 0.5 days
**Dependencies**: Phase 1 complete (conceptually, though not strictly required)
**Assigned Subagent(s)**: data-layer-expert (Opus)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DB-001 | Alembic migration | Create migration to add `indexing_enabled` boolean column to MarketplaceSource | Migration runs cleanly, column added as nullable boolean with no default, existing records unaffected | 2 pts | data-layer-expert | None |
| DB-002 | Model update | Update MarketplaceSource model with `indexing_enabled` mapped column | Column mapping added with nullable=True, comment describes purpose | 1 pt | data-layer-expert | DB-001 |
| DB-003 | Migration testing | Test migration on database with existing MarketplaceSource records | Migration applies cleanly, existing records have NULL for new column, rollback works | 1 pt | data-layer-expert | DB-002 |

**Phase 2 Quality Gates:**
- [ ] Migration runs successfully on fresh database
- [ ] Migration runs successfully on database with existing sources
- [ ] Existing MarketplaceSource records unaffected (NULL for new column)
- [ ] Migration rollback (downgrade) works correctly
- [ ] Model validates with new column in SQLAlchemy

**Implementation Notes:**
- Column definition: `indexing_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, comment="Enable frontmatter extraction for search indexing")`
- Place after `enable_frontmatter_detection` in model definition for logical grouping
- Migration should NOT set a default value (keep NULL to distinguish "not set" from explicit choice)
- Use `op.add_column()` in upgrade, `op.drop_column()` in downgrade

**Migration Template:**
```python
def upgrade():
    op.add_column('marketplace_sources',
        sa.Column('indexing_enabled', sa.Boolean, nullable=True,
                  comment='Enable frontmatter extraction for search indexing'))

def downgrade():
    op.drop_column('marketplace_sources', 'indexing_enabled')
```

---

### Phase 3: API Layer

**Duration**: 1 day
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer (Sonnet)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-001 | Update CreateSourceRequest | Add `indexing_enabled` optional boolean field to schema | Field present in schema, optional, validated as boolean | 1 pt | python-backend-engineer | DB-003 |
| API-002 | Update UpdateSourceRequest | Add `indexing_enabled` optional boolean field to schema | Field present in schema, optional, validated as boolean | 1 pt | python-backend-engineer | DB-003 |
| API-003 | Update SourceResponse | Add `indexing_enabled` optional boolean field to response schema | Field serializes correctly from database, handles NULL as None | 1 pt | python-backend-engineer | DB-003 |
| API-004 | Endpoint logic | Update create/update endpoints to persist `indexing_enabled` to database | Field persists to database when provided, remains NULL if not provided | 2 pts | python-backend-engineer | API-001, API-002 |
| API-005 | Effective state resolution | Add logic to resolve effective indexing state (global config + per-source override) | "off" mode forces false regardless of flag, "on" treats NULL as true, "opt_in" treats NULL as false | 2 pts | python-backend-engineer | API-004, CFG-003 |

**Phase 3 Quality Gates:**
- [ ] Schema validation accepts `indexing_enabled: true/false/null`
- [ ] Create endpoint persists flag to database
- [ ] Update endpoint can modify flag
- [ ] Response includes `indexing_enabled` field (nullable)
- [ ] Effective state resolution respects mode precedence
- [ ] OpenAPI docs updated automatically

**Implementation Notes:**
- Schema location: `skillmeat/api/schemas/marketplace.py`
- Add field: `indexing_enabled: Optional[bool] = None`
- Endpoint location: `skillmeat/api/routers/marketplace_sources.py`
- Resolution logic can be helper method: `get_effective_indexing_state(source: MarketplaceSource, config: ConfigManager) -> bool`

**Mode Precedence Logic:**
```python
def get_effective_indexing_state(source: MarketplaceSource, mode: str) -> bool:
    """Resolve effective indexing state from global mode and per-source flag."""
    if mode == "off":
        return False  # Global disable overrides all
    elif mode == "on":
        # Default enabled, can opt-out per-source
        return source.indexing_enabled if source.indexing_enabled is not None else True
    else:  # opt_in
        # Default disabled, can opt-in per-source
        return source.indexing_enabled if source.indexing_enabled is not None else False
```

---

### Phase 4: UI Layer

**Duration**: 1 day
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: ui-engineer-enhanced (Opus)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-001 | Fetch indexing mode | Add state to fetch global indexing mode from config (or default to "opt_in") | Mode fetched on component mount, defaults to "opt_in" if unavailable | 1 pt | ui-engineer-enhanced | API-005 |
| UI-002 | Add toggle to add-source-modal | Add Switch + Tooltip for indexing_enabled in add-source-modal.tsx | Toggle visible when mode != "off", default checked when mode = "on", tooltip shows storage impact | 3 pts | ui-engineer-enhanced | UI-001 |
| UI-003 | Wire toggle to API | Connect toggle state to CreateSourceRequest payload | Toggle state included in mutation payload as `indexing_enabled` | 1 pt | ui-engineer-enhanced | UI-002 |
| UI-004 | Add toggle to edit-source-modal | Add same toggle to edit-source-modal.tsx with pre-populated state | Toggle shows current source state, updates via UpdateSourceRequest | 2 pts | ui-engineer-enhanced | UI-003 |
| UI-005 | TypeScript types | Update marketplace types to include `indexing_enabled` field | Types in `types/marketplace.ts` include new field | 1 pt | ui-engineer-enhanced | API-003 |

**Phase 4 Quality Gates:**
- [ ] Toggle visible in "on" and "opt_in" modes, hidden in "off" mode
- [ ] Toggle default state matches mode ("on" = checked, "opt_in" = unchecked)
- [ ] Tooltip displays storage impact message (~850 bytes/artifact)
- [ ] Add-source workflow persists toggle state to database
- [ ] Edit-source workflow shows current state and updates correctly
- [ ] No TypeScript errors in components

**Implementation Notes:**
- Follow existing Switch + Tooltip pattern from add-source-modal (lines 74-76, 199-201)
- Fetch mode via new API endpoint or include in app initialization state
- Temporary: Can hardcode mode to "opt_in" if config API endpoint doesn't exist yet (add TODO comment)

**Toggle Component Template:**
```tsx
{indexingMode !== 'off' && (
  <div className="flex items-center justify-between">
    <Label htmlFor="indexing-enabled" className="text-sm font-medium">
      Enable artifact search indexing
    </Label>
    <div className="flex items-center gap-2">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <HelpCircle className="h-4 w-4 text-muted-foreground" />
          </TooltipTrigger>
          <TooltipContent>
            <p>Index artifacts for cross-source search. Adds ~850 bytes per artifact.</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <Switch
        id="indexing-enabled"
        checked={indexingEnabled}
        onCheckedChange={setIndexingEnabled}
        aria-label="Enable artifact search indexing"
      />
    </div>
  </div>
)}
```

---

### Phase 5: Testing Layer

**Duration**: 1 day
**Dependencies**: Phases 1-4 complete
**Assigned Subagent(s)**: python-backend-engineer (Sonnet), ui-engineer-enhanced (Opus) - parallel

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Config unit tests | Test ConfigManager mode get/set, validation, defaults | >80% coverage, all mode values tested, invalid values handled | 2 pts | python-backend-engineer | CFG-003 |
| TEST-002 | Database tests | Test migration and model with new column | Migration runs, column nullable, existing records unaffected | 1 pt | python-backend-engineer | DB-003 |
| TEST-003 | API integration tests | Test create/update endpoints with `indexing_enabled` field | Endpoints persist field correctly, handle NULL, validate types | 2 pts | python-backend-engineer | API-005 |
| TEST-004 | Frontend component tests | Test toggle visibility and state in different modes | Toggle shown/hidden correctly, default state matches mode, state updates | 2 pts | ui-engineer-enhanced | UI-005 |
| TEST-005 | E2E workflow test | Test full add-source flow with indexing toggle in "opt_in" mode | User can add source with toggle checked, flag persists to database | 1 pt | ui-engineer-enhanced | TEST-004 |

**Phase 5 Quality Gates:**
- [ ] Unit test coverage >80% for new code
- [ ] All mode combinations tested (off, on, opt_in)
- [ ] Invalid config values handled gracefully
- [ ] Migration tested on populated database
- [ ] Frontend toggle behavior verified in all modes
- [ ] E2E test covers critical user journey

**Test Coverage Requirements:**

**Backend (Python)**:
- ConfigManager: get/set indexing mode, validation, defaults
- Database: Migration up/down, NULL handling
- API: Create/update with flag, effective state resolution
- Mode precedence: off forces false, on defaults true, opt_in defaults false

**Frontend (TypeScript/React)**:
- Toggle visibility based on mode
- Toggle default state based on mode
- State persistence to mutation payload
- Tooltip rendering

---

### Phase 6: Documentation Layer

**Duration**: 0.5 days
**Dependencies**: Implementation complete
**Assigned Subagent(s)**: documentation-writer (Haiku)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DOC-001 | ConfigManager docstrings | Update ConfigManager docstring with `artifact_search.indexing_mode` example | Docstring includes key, valid values, example usage | 1 pt | documentation-writer | TEST-005 |
| DOC-002 | Model docstrings | Update MarketplaceSource docstring to mention `indexing_enabled` | Field documented in class docstring Attributes section | 1 pt | documentation-writer | TEST-005 |
| DOC-003 | Inline comments | Add comments explaining mode precedence logic in API layer | Logic commented with mode behavior explanation | 1 pt | documentation-writer | TEST-005 |
| DOC-004 | SPIKE update | Update SPIKE document to reference this PRD as "Phase 0" | SPIKE mentions Phase 0 complete, links to PRD and implementation plan | 1 pt | documentation-writer | DOC-003 |

**Phase 6 Quality Gates:**
- [ ] ConfigManager docstring updated with example
- [ ] MarketplaceSource docstring includes `indexing_enabled`
- [ ] Mode precedence logic has clear inline comments
- [ ] SPIKE document updated with Phase 0 reference
- [ ] No broken documentation links

**Documentation Locations:**
- `skillmeat/config.py` - ConfigManager class docstring
- `skillmeat/cache/models.py` - MarketplaceSource class docstring (lines 1182+)
- `skillmeat/api/routers/marketplace_sources.py` - Inline comments in endpoints
- `docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md` - Reference this implementation

**Note**: The existing `enable_frontmatter_detection` flag in MarketplaceSource controls whether frontmatter is parsed for display. The new `indexing_enabled` flag controls whether frontmatter is indexed for cross-source search - a separate concern.

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Global mode changes don't affect existing sources | Low | High | Document behavior clearly; NULL in database means "use mode default" |
| Users confused by three-mode system | Medium | Low | Clear tooltip text, sensible "opt_in" default, documentation |
| Invalid config values crash app | High | Low | Validate in ConfigManager, log warning, default to "opt_in" |
| Database migration fails on existing deployments | Medium | Low | Test on copy of production data, make column nullable, no default value |
| Frontend can't fetch global mode | Medium | Medium | Hardcode "opt_in" default if config endpoint unavailable, add TODO for API endpoint |
| Mode precedence logic implemented inconsistently | Medium | Medium | Centralize logic in helper function, thorough unit tests |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Frontend work blocked by API completion | Medium | Low | API schemas can be defined early for frontend to start mocking |
| Testing reveals mode precedence bugs | Medium | Medium | Implement mode resolution logic early, unit test thoroughly |
| E2E tests flaky due to timing | Low | Medium | Use proper wait strategies, test on stable state |

---

## Resource Requirements

### Team Composition
- Backend Developer (Python): 2 days (Phases 1-3, 5)
- Data Engineer: 0.5 days (Phase 2)
- Frontend Developer (React): 1.5 days (Phases 4-5)
- Documentation Writer: 0.5 days (Phase 6)

**Total estimated effort**: ~4 days with parallel work

### Skill Requirements
- Python (FastAPI, SQLAlchemy, Alembic)
- TypeScript/React (Next.js 15, TanStack Query)
- TOML configuration management
- Database migrations
- Component testing (Jest, RTL, Playwright)

---

## Success Metrics

### Delivery Metrics
- On-time delivery (3-4 days)
- Code coverage >80%
- Zero P0/P1 bugs in first week
- All quality gates passed

### Functional Metrics
- Config mode persists across app restarts (100%)
- Per-source flag accuracy (100% - database matches UI state)
- UI toggle visibility correct in all 3 modes (100%)
- Storage savings when indexing disabled (0MB frontmatter storage)

### Technical Metrics
- 100% API documentation (OpenAPI auto-generated)
- All docstrings updated
- Mode precedence logic well-commented
- SPIKE document references Phase 0

---

## Communication Plan

**Daily Updates**: Progress on current phase, blockers, next steps
**Phase Reviews**: Formal review at end of each phase before proceeding
**Quality Gates**: Document pass/fail for each phase's quality gates
**Final Review**: Code review before merge, walkthrough of all functionality

---

## Post-Implementation

### Monitoring
- Config file reads/writes (ensure no performance issues)
- Source creation with `indexing_enabled` flag distribution (analytics)
- Storage usage over time (validate savings when disabled)

### Iteration Planning (Cross-Source Search)

**Note**: Frontmatter extraction and caching is already complete via the `enhanced-frontmatter-utilization` feature. The SPIKE phases below build on both that work AND this configurable indexing feature.

- **Phase 1 (SPIKE)**: Schema extension for search columns (title, description, search_tags, search_text) - conditional on `indexing_enabled`
- **Phase 2 (SPIKE)**: FTS5 full-text search (conditional on `indexing_enabled`)
- **Phase 3 (SPIKE)**: Frontend search UI with dual-mode toggle (show "indexing disabled" message if needed)

### Technical Debt
- Add API endpoint for fetching global mode (currently may be hardcoded in UI)
- Consider bulk update tool if users request changing many sources at once
- Analytics on mode usage distribution (off vs on vs opt_in)
- Consider relationship with existing `enable_frontmatter_detection` flag (display vs search indexing)

---

## Overall Acceptance Criteria (Definition of Done)

### Functional Acceptance
- [ ] Global config mode set via `skillmeat config set artifact_search.indexing_mode [value]` persists to `~/.skillmeat/config.toml`
- [ ] Invalid mode values log warning and default to "opt_in"
- [ ] Per-source `indexing_enabled` flag saves to database via add-source workflow
- [ ] Per-source flag updates via edit-source workflow
- [ ] Toggle visibility matches mode: hidden in "off", shown in "on"/"opt_in"
- [ ] Toggle default state matches mode: checked in "on", unchecked in "opt_in"
- [ ] Tooltip displays storage impact message (~850 bytes per artifact)
- [ ] Config and flag values accessible to SPIKE Phase 1 implementation (scan logic can check effective state)

### Technical Acceptance
- [ ] Alembic migration adds `indexing_enabled` column as nullable boolean
- [ ] MarketplaceSource model updated with new column mapping
- [ ] CreateSourceRequest, UpdateSourceRequest, SourceResponse schemas include `indexing_enabled`
- [ ] ConfigManager supports `artifact_search.indexing_mode` get/set operations
- [ ] No breaking changes to existing source creation workflow
- [ ] Mode precedence logic centralized and well-tested

### Quality Acceptance
- [ ] Unit tests verify ConfigManager mode persistence
- [ ] Unit tests verify default mode logic ("opt_in" when unset)
- [ ] Integration tests verify source creation with indexing_enabled true/false/null
- [ ] Migration tested on database with existing MarketplaceSource records
- [ ] Manual testing confirms toggle behavior in all three modes
- [ ] Code coverage >80% for new code

### Documentation Acceptance
- [ ] ConfigManager docstring updated with new key example
- [ ] MarketplaceSource model docstring mentions indexing_enabled
- [ ] Inline comments explain mode precedence logic
- [ ] SPIKE document updated to reference Phase 0 (this implementation)

---

## Task Summary by Layer

### Configuration Layer (4 pts)
- CFG-001: Add config defaults (2 pts)
- CFG-002: Add helper methods (1 pt)
- CFG-003: CLI command support (1 pt)

### Database Layer (4 pts)
- DB-001: Alembic migration (2 pts)
- DB-002: Model update (1 pt)
- DB-003: Migration testing (1 pt)

### API Layer (7 pts)
- API-001: Update CreateSourceRequest (1 pt)
- API-002: Update UpdateSourceRequest (1 pt)
- API-003: Update SourceResponse (1 pt)
- API-004: Endpoint logic (2 pts)
- API-005: Effective state resolution (2 pts)

### UI Layer (8 pts)
- UI-001: Fetch indexing mode (1 pt)
- UI-002: Add toggle to add-source-modal (3 pts)
- UI-003: Wire toggle to API (1 pt)
- UI-004: Add toggle to edit-source-modal (2 pts)
- UI-005: TypeScript types (1 pt)

### Testing Layer (8 pts)
- TEST-001: Config unit tests (2 pts)
- TEST-002: Database tests (1 pt)
- TEST-003: API integration tests (2 pts)
- TEST-004: Frontend component tests (2 pts)
- TEST-005: E2E workflow test (1 pt)

### Documentation Layer (4 pts)
- DOC-001: ConfigManager docstrings (1 pt)
- DOC-002: Model docstrings (1 pt)
- DOC-003: Inline comments (1 pt)
- DOC-004: SPIKE update (1 pt)

**Total**: 35 points across all tasks (26 unique story points accounting for parallelization)

---

**Progress Tracking:**

See `.claude/progress/configurable-frontmatter-caching-v1/` (create when implementation begins)

---

**Implementation Plan Version**: 1.1
**Last Updated**: 2026-01-23

### Changelog

- **v1.1 (2026-01-23)**: Updated to reflect completed `enhanced-frontmatter-utilization` feature. Reframed plan as enhancement building on existing frontmatter infrastructure. Fixed project name references (MeatyPrompts → SkillMeat). Added prerequisite documentation link.
- **v1.0 (2026-01-20)**: Initial plan creation as "Phase 0" of cross-source search.
