---
title: "Implementation Plan: Memory Anchors & Rich Provenance"
description: "Phased implementation for structured anchors, promoted provenance columns, extraction auto-population, and agent-assisted capture."
audience: [ai-agents, developers]
tags: [implementation, planning, memory, anchors, provenance]
created: 2026-02-09
updated: 2026-02-09
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/memory-anchors-provenance-v1.md
  - /docs/project_plans/PRDs/features/memory-extraction-pipeline-v2.md
  - /docs/project_plans/implementation_plans/features/memory-context-system-gap-closure-v1-2.md
parallelization:
  batch_1: [DB-001, DB-002]  # sequential - migration then model update
  batch_2: [DB-003]  # schemas - depends on model
  batch_3: [REPO-001, SVC-001, CLI-001]  # parallel - all depend on schemas
  batch_4: [API-001, EXT-001, EXT-002]  # parallel - API depends on repo, extraction independent
  batch_5: [EXT-003, UI-001]  # parallel - extraction finalization, frontend types
  batch_6: [UI-002, UI-003]  # parallel - anchors tab and provenance UI
  batch_7: [DOC-001, DOC-002]  # parallel - docs
---

# Implementation Plan: Memory Anchors & Rich Provenance

**Plan ID**: `IMPL-2026-02-09-memory-anchors-provenance`
**Date**: 2026-02-09
**Author**: Claude Opus 4.6 (Planning)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/memory-anchors-provenance-v1.md`
- **Gap Closure Plan**: `/docs/project_plans/implementation_plans/features/memory-context-system-gap-closure-v1-2.md`
- **Extraction Pipeline PRD**: `/docs/project_plans/PRDs/features/memory-extraction-pipeline-v2.md`

**Complexity**: Large
**Total Estimated Effort**: ~37 story points
**Target Timeline**: 4-5 days (phased, each phase shippable)

---

## 1. Executive Summary

This plan implements four capabilities in a strict layered sequence: (1) structured anchor objects replacing flat string arrays with type classification, line ranges, and commit context; (2) six promoted provenance columns on `memory_items` with indexed filtering; (3) auto-population of anchors and provenance from JSONL session tool calls during extraction; and (4) CLI flags for agent-assisted manual anchor attachment. Each phase is independently shippable and builds on the previous phase's schema foundation.

---

## 2. Implementation Strategy

### Architecture Sequence

Following SkillMeat's layered architecture:
1. **Database Layer** -- Alembic migration, model columns, data migration
2. **Schema Layer** -- Pydantic models for structured anchors and new provenance fields
3. **Repository Layer** -- Filter/sort support for promoted columns
4. **Service Layer** -- Write-through provenance population, anchor construction
5. **API Layer** -- Query parameter filters on list endpoint
6. **CLI Layer** -- `--anchor` and `--provenance-*` flags
7. **Extraction Layer** -- Tool-call parsing, anchor auto-linking, metadata capture
8. **UI Layer** -- TypeScript types, Anchors tab enhancement, Provenance tab update
9. **Documentation Layer** -- Agent instructions, skill docs, CLAUDE.md updates

### Parallel Work Opportunities

- **Phase 2 tasks**: Repository filters, service write-through, and CLI flags can run in parallel once schemas land (batch_3).
- **Phase 3 tasks**: Extraction pipeline work is independent of API layer work; EXT-001/EXT-002 can parallel API-001 (batch_4).
- **Phase 4 tasks**: Frontend type updates can start once schemas land; full UI work after API is ready. UI-002/UI-003 can run in parallel (batch_6).
- **Phase 3 and Phase 4 overlap**: Extraction finalization (EXT-003) and frontend type updates (UI-001) can run simultaneously (batch_5).

### Critical Path

```
DB-001 (migration) → DB-002 (model) → DB-003 (schemas)
  → REPO-001 (filters) → API-001 (endpoint filters) → UI-001 (TS types) → UI-002/UI-003 (UI)
```

---

## 3. Phase Breakdown

### Phase 1: Database & Schema Foundation

**Duration**: 1 day
**Dependencies**: None
**Goal**: Establish the data layer that all subsequent phases depend on.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Deps |
|---------|-----------|-------------|---------------------|------|----------|------|
| DB-001 | Alembic migration | Create migration that: (a) adds 6 nullable `VARCHAR` columns (`git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type` with default `'manual'`) to `memory_items`; (b) creates individual indexes on each new column; (c) transforms existing `anchors_json` data from `List[str]` to `List[AnchorObject]` by wrapping each string as `{"path": str, "type": "code"}`. | Migration runs forward and backward cleanly. Existing anchor strings are wrapped in object format. All 6 indexes exist. `source_type` defaults to `'manual'`. | 5 pts | python-backend-engineer | None |
| DB-002 | Update MemoryItem model | Add 6 new `mapped_column` declarations to `MemoryItem` in `skillmeat/cache/models.py`: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`. Update the `anchors` property docstring to document the new `AnchorObject` structure. Ensure the property still deserializes `anchors_json` correctly for the new object format. | Model reflects all 6 columns. `anchors` property returns `List[Dict]` with `path`, `type`, and optional fields. Existing code that reads `anchors` does not break. | 3 pts | python-backend-engineer | DB-001 |
| DB-003 | Update Pydantic schemas | In `skillmeat/api/schemas/memory.py`: (a) Create `AnchorCreate` model (`path: str`, `type: Literal["code","plan","doc","config","test"]`, optional `line_start`, `line_end`, `commit_sha`, `description`); (b) Create `AnchorResponse` model (same fields); (c) Add 6 optional provenance fields to `MemoryItemCreate` and `MemoryItemUpdate`; (d) Add 6 fields and `anchors: List[AnchorResponse]` to `MemoryItemResponse`; (e) Update `anchors` field on create/update to accept `List[AnchorCreate]`. | Schema validation passes for both new anchor objects and provenance fields. Create/update accept structured anchors. Response includes all new fields. Old tests updated to match new anchor format. | 5 pts | python-backend-engineer | DB-002 |

**Phase 1 Quality Gates:**
- [ ] `alembic upgrade head` runs without errors on a fresh DB and on a DB with existing memory items
- [ ] `alembic downgrade -1` reverses cleanly (anchors revert to string arrays)
- [ ] Model `anchors` property correctly deserializes new object format
- [ ] Pydantic schemas validate: `AnchorCreate` rejects invalid types, accepts valid line ranges
- [ ] Existing memory API tests pass with updated fixture data
- [ ] All 6 indexes confirmed via `sqlite3 .schema` or equivalent

**Files Modified:**
- `skillmeat/cache/migrations/versions/<new_migration>.py` (new)
- `skillmeat/cache/models.py`
- `skillmeat/api/schemas/memory.py`

---

### Phase 2: Backend Service, Repository & CLI

**Duration**: 1 day
**Dependencies**: Phase 1 complete (DB-003)
**Goal**: Wire filtering, write-through population, and CLI anchor capture.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Deps |
|---------|-----------|-------------|---------------------|------|----------|------|
| REPO-001 | Repository filter support | Update `list_items()` in `skillmeat/cache/memory_repositories.py` to accept optional filter parameters: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`. Apply as equality `WHERE` clauses when provided. Support `None` (no filter) vs explicit value. | Filtered queries return correct subsets. Combining multiple filters works (AND semantics). No filter = all items returned. Query performance acceptable (<50ms for 1K items). | 3 pts | python-backend-engineer | DB-003 |
| SVC-001 | Service write-through | Update `MemoryService` in `skillmeat/core/services/memory_service.py` to: (a) on create/update, if provenance dict is provided, extract and populate promoted columns (`git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`) from it; (b) always write values to both the promoted column and into `provenance_json` blob for backwards compatibility; (c) on read, promoted column takes precedence over JSON blob value. | Creating a memory with provenance dict populates all 6 columns. Values appear in both the column and the JSON blob. Reading returns column values. Manual create without provenance defaults `source_type` to `'manual'`. | 3 pts | python-backend-engineer | DB-003 |
| CLI-001 | CLI anchor and provenance flags | Update `skillmeat/cli.py` `memory item create` command to add: (a) `--anchor` (repeatable Click option, format `path:type` or `path:type:start-end`); (b) `--provenance-branch`, `--provenance-commit`, `--provenance-model`, `--provenance-agent-type` (string options); (c) parsing logic that converts `--anchor` strings to `AnchorCreate`-compatible dicts; (d) `source_type` defaults to `'manual'` for CLI creates. | `skillmeat memory item create --anchor "file.py:code:10-20" --anchor "test.py:test"` creates a memory with 2 structured anchors. Provenance flags populate promoted columns. Invalid anchor format shows helpful error. | 3 pts | python-backend-engineer | DB-003 |
| API-001 | API filter query params | Update `GET /memory-items/` in `skillmeat/api/routers/memory_items.py` to accept optional query parameters: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`. Pass through to repository `list_items()`. | API returns filtered results when params provided. OpenAPI spec shows new query params. Combining filters works correctly. Empty string vs omitted param handled correctly. | 3 pts | python-backend-engineer | REPO-001 |

**Phase 2 Quality Gates:**
- [ ] `GET /memory-items/?git_branch=feat/x` returns only items on that branch
- [ ] `GET /memory-items/?agent_type=python-backend-engineer&model=claude-opus-4-6` combines filters correctly
- [ ] CLI creates memory with structured anchors visible in API response
- [ ] Write-through confirmed: promoted columns and `provenance_json` both populated
- [ ] OpenAPI spec (`skillmeat/api/openapi.json`) regenerated with new query params
- [ ] Integration tests cover: single filter, multi-filter, no filter, empty result

**Files Modified:**
- `skillmeat/cache/memory_repositories.py`
- `skillmeat/core/services/memory_service.py`
- `skillmeat/api/routers/memory_items.py`
- `skillmeat/cli.py`
- `skillmeat/api/openapi.json` (regenerated)

---

### Phase 3: Extraction Pipeline Enhancement

**Duration**: 1-2 days
**Dependencies**: Phase 1 complete (DB-003 for schema types); Phase 2 SVC-001 for service write-through
**Goal**: Auto-populate anchors and provenance from JSONL session logs.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Deps |
|---------|-----------|-------------|---------------------|------|----------|------|
| EXT-001 | Tool-call parser | Add a method to `MemoryExtractorService` in `skillmeat/core/services/memory_extractor_service.py` that: (a) iterates message content blocks looking for `tool_use` blocks; (b) identifies tool names `Read`, `Edit`, `Write`, `Grep`, `Glob`; (c) extracts file path parameters from each tool call's input dict (Read: `file_path`, Edit: `file_path`, Write: `file_path`, Grep: `path`, Glob: `path`); (d) returns a deduplicated list of file paths associated with each extracted memory candidate. | Parser extracts file paths from all 5 tool types. Unknown tool types are skipped. Missing path params are handled gracefully. Deduplication by path works. | 5 pts | python-backend-engineer | DB-003 |
| EXT-002 | Anchor type classifier and metadata capture | Implement: (a) a helper function `classify_anchor_type(path: str) -> str` using extension and path pattern rules from PRD Appendix C (`tests/` or `test_` prefix = `test`, `.md` in `docs/` or `project_plans/` = `doc`, `.md` in `.claude/progress/` or `.claude/worknotes/` = `plan`, `.toml`/`.yaml`/`.yml`/`.json`/`.ini`/`.cfg`/`.env` = `config`, all other = `code`); (b) metadata capture from JSONL message envelopes: extract `model` from assistant messages, extract agent type from message metadata if available; (c) auto-detect `git_commit` via `subprocess.run(["git", "rev-parse", "HEAD"])` with fallback to JSONL metadata fields. | Type classifier correctly categorizes 10+ test cases across all 5 types. Model field captured from assistant messages. Git commit detected from subprocess or JSONL fallback. Edge cases (no git repo, missing metadata) handled gracefully. | 4 pts | python-backend-engineer | DB-003 |
| EXT-003 | Anchor assembly and integration | Wire EXT-001 and EXT-002 into the extraction pipeline: (a) after extracting a memory candidate, collect file paths from surrounding tool-call context (messages in the candidate's extraction window); (b) classify each path into an anchor type; (c) prioritize mutation tool calls (`Edit`, `Write`) over read-only (`Read`, `Grep`, `Glob`); (d) deduplicate by path, keeping the most specific reference (narrowest line range if available); (e) cap at 20 anchors per memory; (f) construct `AnchorCreate`-compatible dicts and attach to the memory candidate; (g) populate `source_type = 'extraction'`, `agent_type`, `model`, `git_commit`, `git_branch`, `session_id` on each extracted memory. Log anchor counts per memory. | Extracted memories have auto-linked anchors from tool calls. Mutation files ranked above read-only. Max 20 anchors enforced. All 6 provenance fields populated. Extraction of a 500KB JSONL completes in <5 seconds. Logging shows anchor counts. | 5 pts | python-backend-engineer | EXT-001, EXT-002, SVC-001 |

**Phase 3 Quality Gates:**
- [ ] Tool-call parser extracts paths from a sample JSONL with `Read`, `Edit`, `Write`, `Grep`, `Glob` calls
- [ ] Anchor type classifier passes unit tests for all 5 types plus edge cases
- [ ] Extracted memories have 80%+ anchor coverage on sessions with tool invocations
- [ ] Mutation prioritization confirmed: `Edit`/`Write` paths appear before `Read`/`Grep`/`Glob` paths
- [ ] 20-anchor cap enforced (test with session containing 30+ unique file references)
- [ ] `source_type` is `'extraction'` on all pipeline-produced memories
- [ ] Performance: 500KB JSONL processes in <5 seconds including anchor linking

**Files Modified:**
- `skillmeat/core/services/memory_extractor_service.py`

---

### Phase 4: Frontend Enhancement

**Duration**: 1 day
**Dependencies**: Phase 1 (DB-003) for types; Phase 2 (API-001) for filter params
**Goal**: Surface structured anchors and promoted provenance in the web UI.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Deps |
|---------|-----------|-------------|---------------------|------|----------|------|
| UI-001 | TypeScript type updates | Update `skillmeat/web/sdk/models/MemoryItemResponse.ts` (or equivalent type file): (a) add `Anchor` interface with `path`, `type`, `line_start?`, `line_end?`, `commit_sha?`, `description?`; (b) add 6 optional fields to `MemoryItemResponse`: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`; (c) update `anchors` field type from `string[]` to `Anchor[]`; (d) update any `MemoryItemCreate` type to include `anchors: AnchorCreate[]` and provenance fields. | TypeScript types match API schema exactly. `pnpm type-check` passes. No regressions in existing components consuming memory types. | 2 pts | ui-engineer-enhanced | DB-003 |
| UI-002 | Anchors tab enhancement | Update `skillmeat/web/components/memory/memory-details-modal.tsx` Anchors tab: (a) replace plain file path list with anchor cards showing type badge (color-coded: `code`=blue, `test`=green, `doc`=purple, `config`=orange, `plan`=teal), file path, optional line range display (e.g., "L142-156"), optional commit SHA chip (truncated to 7 chars), and optional description text; (b) sort anchors by type priority (code first, then test, doc, config, plan); (c) show anchor count in tab label. Use existing shadcn `Badge` component for type badges. | Anchors display with colored type badges. Line ranges shown when present. Commit SHA shown as truncated chip. Empty anchors show "No anchors" placeholder. Tab label shows count. | 3 pts | ui-engineer-enhanced | UI-001, API-001 |
| UI-003 | Provenance display and filter controls | (a) Update Provenance tab in `memory-details-modal.tsx` to display promoted fields (`git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`) in a structured key-value layout with labels; render remaining `provenance_json` fields as secondary expandable detail; (b) add filter controls to memory list hooks in `skillmeat/web/hooks/use-memory-items.ts`: pass optional `git_branch`, `agent_type`, `model`, `source_type` params to the list query; (c) if memory list page has a filter bar, add dropdowns/inputs for promoted fields. | Provenance tab shows promoted fields prominently with labels. Overflow JSON shown as secondary detail. Filter params passed to API when set. Filter controls visible and functional in memory list (if filter bar exists). | 3 pts | ui-engineer-enhanced | UI-001, API-001 |

**Phase 4 Quality Gates:**
- [ ] `pnpm type-check` passes with updated types
- [ ] Anchors tab renders structured cards for a memory with mixed anchor types
- [ ] Anchors tab gracefully handles: no anchors, anchors without line ranges, anchors without commit SHA
- [ ] Provenance tab shows promoted fields in structured layout, not raw JSON
- [ ] Filter hooks pass query params to API correctly
- [ ] No visual regressions in memory detail modal (other tabs unaffected)

**Files Modified:**
- `skillmeat/web/sdk/models/MemoryItemResponse.ts` (or relevant type file)
- `skillmeat/web/components/memory/memory-details-modal.tsx`
- `skillmeat/web/hooks/use-memory-items.ts`

---

### Phase 5: Documentation & Agent Instructions

**Duration**: 0.5 days
**Dependencies**: Phases 1-4 substantially complete
**Goal**: Ensure agents and developers can use the new capabilities without reading source code.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Deps |
|---------|-----------|-------------|---------------------|------|----------|------|
| DOC-001 | CLAUDE.md and skill doc updates | (a) Update `CLAUDE.md` Memory System section: add `--anchor` flag to the quick capture command example; add anchor type reference; mention provenance flags; (b) update `.claude/skills/skillmeat-cli/` memory workflow routes with anchor capture instructions, CLI examples (single anchor, multiple anchors, anchors with line ranges, provenance flags), and anchor type classification rules for agent reference. | CLAUDE.md shows updated CLI examples with `--anchor` flags. Skill docs include anchor format reference and provenance flag examples. An agent reading the docs can construct a valid `--anchor` flag without seeing source code. | 1 pt | documentation-writer | CLI-001, EXT-003 |
| DOC-002 | Agent instruction updates | (a) Add guidance to `.claude/rules/memory.md` for in-session anchor attachment: "When capturing a memory, include `--anchor` flags for files you touched or discovered the learning in"; (b) update the memory capture trigger list with anchor-aware examples; (c) document the anchor type classification heuristic so agents can manually specify the correct type. | Memory rule includes anchor guidance. Trigger examples show anchor flags. Type classification rules documented for agent reference. | 1 pt | documentation-writer | CLI-001 |

**Phase 5 Quality Gates:**
- [ ] CLAUDE.md memory section shows correct `--anchor` CLI examples
- [ ] Skill docs include complete anchor format reference
- [ ] `.claude/rules/memory.md` includes anchor capture guidance
- [ ] All documented CLI commands work correctly when copy-pasted

**Files Modified:**
- `CLAUDE.md`
- `.claude/skills/skillmeat-cli/` (relevant route files)
- `.claude/rules/memory.md`

---

## 4. Batch Execution Plan

The parallelization strategy maps tasks to execution batches for orchestrated agent delegation:

| Batch | Tasks | Execution | Rationale |
|-------|-------|-----------|-----------|
| **batch_1** | DB-001 → DB-002 | Sequential | Migration must complete before model update |
| **batch_2** | DB-003 | Sequential | Schemas depend on model columns |
| **batch_3** | REPO-001, SVC-001, CLI-001 | Parallel (3 agents) | All depend only on schemas; touch different files |
| **batch_4** | API-001, EXT-001, EXT-002 | Parallel (3 agents) | API depends on repo (done); extraction is independent |
| **batch_5** | EXT-003, UI-001 | Parallel (2 agents) | Extraction assembly; frontend types (no file overlap) |
| **batch_6** | UI-002, UI-003 | Parallel (2 agents) | Both modify modal but different tabs; can merge cleanly |
| **batch_7** | DOC-001, DOC-002 | Parallel (2 agents) | Different files, no overlap |

**Total batches**: 7
**Critical path length**: batch_1 + batch_2 + batch_3 + batch_4 + batch_5 + batch_6 = 6 sequential stages
**Maximum parallelism**: 3 agents (batches 3 and 4)

---

## 5. Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| Anchor data migration corrupts existing memories | High | Low | Migration wraps strings in objects atomically. Include rollback (`downgrade`) that unwraps back to strings. Test on a copy of production DB before running. |
| `anchors_json` format change breaks frontend before types update | High | Medium | Batch_2 (schemas) completes before any frontend work. API response includes both old and new consumers during transition. Deploy Phase 1 + 2 together. |
| Extraction pipeline performance regression from tool-call parsing | Medium | Low | Only parse messages containing `tool_use` content blocks (skip others entirely). Lazy iteration. Performance test: 500KB JSONL must process in <5 seconds. |
| Over-linking: noisy anchors dilute memory relevance | Medium | Medium | Cap at 20 anchors. Prioritize mutation calls over reads. Deduplicate by path. Agents can prune anchors post-extraction via update. |
| Parallel agents modifying `memory-details-modal.tsx` (UI-002 + UI-003) | Medium | Medium | UI-002 modifies Anchors tab; UI-003 modifies Provenance tab and hooks. Different sections of the file. Git should merge cleanly. If conflict occurs, resolve in batch_6. |
| JSONL format variations across Claude Code versions | Medium | Low | Robust parser with fallbacks already established in extraction-pipeline-v2. Unknown message types skipped gracefully. |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| Phase 3 extraction work takes longer than estimated | Medium | Medium | Phase 3 is independent of Phase 4 frontend work. Frontend can ship with manual provenance while extraction catches up. |
| Existing test suite breaks due to anchor format change | Medium | High | Update test fixtures in DB-003 (schema task). Allocate explicit test-fix time within each task estimate. |
| Scope creep into anchor validation or cross-project linking | Low | Medium | PRD explicitly marks these as out of scope. Reject scope additions during execution. |

---

## 6. Success Metrics

### Delivery Metrics
- All 5 phases completed within target timeline (4-5 days)
- All quality gates passed per phase
- Zero P0 regressions in existing memory functionality

### Functional Metrics
- 80%+ of extracted memories have at least one auto-linked anchor (post Phase 3)
- All 6 promoted provenance fields filterable via API with <50ms query time for 10K items
- CLI `--anchor` flag accepted and produces valid structured anchors

### Technical Metrics
- Migration runs forward and backward cleanly
- Extraction of 500KB JSONL completes in <5 seconds including anchor linking
- TypeScript type-check passes with zero new errors
- OpenAPI spec regenerated and consistent with implementation

---

## 7. Testing Strategy

### Unit Tests (per phase)
- **Phase 1**: Anchor schema validation (valid/invalid types, line ranges), migration up/down
- **Phase 2**: Repository filter queries (single filter, multi-filter, no results), CLI anchor parsing (valid formats, invalid formats, edge cases)
- **Phase 3**: Tool-call parser (all 5 tool types, missing params, unknown tools), anchor type classifier (all 5 types + edge cases), deduplication logic, 20-anchor cap
- **Phase 4**: Component render tests for anchor cards (all anchor types, missing optional fields)

### Integration Tests
- Create memory via API with structured anchors, retrieve and verify format
- Create memory via CLI with `--anchor` flags, verify in API response
- Filter memories by `git_branch` + `agent_type`, verify correct subset returned
- Run extraction on sample JSONL, verify anchors and provenance auto-populated

### Regression Tests
- Existing memory CRUD operations unaffected
- Memory search returns correct results
- Memory detail modal renders without errors for pre-migration memories
- Extraction pipeline produces valid memories for JSONL without tool calls

---

## 8. Post-Implementation

- Monitor anchor coverage rate on extracted memories (target: 80%+)
- Review extracted anchor quality after first 50 extractions -- tune classification rules if needed
- Evaluate whether anchor type classifier needs additional patterns
- Track filter usage in API to identify most-used provenance dimensions
- Consider future enhancements: anchor validation (file existence), anchor diff visualization, vector search on anchors

---

**Progress Tracking:**

See `.claude/progress/memory-anchors-provenance/`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-09
