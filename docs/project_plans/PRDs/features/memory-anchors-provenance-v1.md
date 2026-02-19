---
title: 'PRD: Memory Anchors & Rich Provenance'
description: Enhance memory items with structured file anchors (typed, with line ranges
  and commit context), promoted queryable provenance columns, and auto-population
  from session tool calls and agent metadata.
audience:
- ai-agents
- developers
- architects
tags:
- prd
- memory
- anchors
- provenance
- extraction
- context-engineering
created: 2026-02-09
updated: 2026-02-09
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/features/memory-extraction-pipeline-v2.md
- /docs/project_plans/PRDs/features/memory-context-system-v1-1.md
- /docs/project_plans/implementation_plans/features/memory-context-system-gap-closure-v1-2.md
- skillmeat/cache/models.py
- skillmeat/core/services/memory_extractor_service.py
- skillmeat/web/components/memory/memory-details-modal.tsx
---
# PRD: Memory Anchors & Rich Provenance

**Feature Name:** Memory Anchors & Rich Provenance
**Filepath Name:** `memory-anchors-provenance-v1`
**Date:** 2026-02-09
**Author:** Claude Opus 4.6 (Planning)
**Version:** 1.0
**Status:** Draft

---

## 1. Executive Summary

Memory items currently store anchors as plain string arrays and provenance as unstructured JSON blobs. Both fields live in opaque `TEXT` columns (`anchors_json` and `provenance_json`), making them unqueryable, unfilterable, and largely invisible to agents seeking contextual memories. When an agent retrieves a memory about a SQLAlchemy relationship gotcha, it cannot see which files the learning came from, what agent discovered it, which commit it was relevant to, or what model was used. This limits memory retrieval precision and contextual relevance.

This PRD enhances both systems across four dimensions:

1. **Structured Anchors** -- Transform anchors from `List[str]` to `List[AnchorObject]` with type classification (`code`, `plan`, `doc`, `config`, `test`), optional line ranges, commit SHA versioning, and descriptive context. This turns a flat file list into a rich source map.

2. **Promoted Provenance Columns** -- Elevate `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, and `source_type` from the JSON blob to indexed database columns. This enables filtering and sorting memories by any of these dimensions without resorting to `json_extract()` hacks.

3. **Auto-Population** -- Parse tool calls (`Read`, `Edit`, `Write`, `Grep`, `Glob`) from session JSONL during extraction to auto-link file anchors. Capture agent type, model, and commit SHA from session metadata. Extracted memories arrive pre-enriched rather than requiring manual annotation.

4. **Agent-Assisted Capture** -- Provide CLI flags and documented instructions for agents to manually attach anchors and provenance during in-session memory creation, closing the loop for memories captured outside the extraction pipeline.

**Priority:** HIGH

---

## 2. Context & Background

### 2.1 Current State

The memory system (v1.0, extended by v1.1 and gap-closure v1.2) stores project-scoped development knowledge -- patterns, decisions, gotchas, constraints -- in a SQLAlchemy-backed `memory_items` table. The current schema includes two relevant columns:

- **`anchors_json`** (`Text`): Contains a serialized `List[str]` of bare file paths (e.g., `["skillmeat/api/routers/memory_items.py", "skillmeat/cache/models.py"]`). No structure for file type, line ranges, commit context, or descriptions.

- **`provenance_json`** (`Text`): Contains an unstructured `Dict[str, Any]` with whatever the extraction pipeline or manual creator chose to include. The extraction pipeline currently populates: `source`, `format`, `run_id`, `session_id`, `commit_sha`, `workflow_stage`, `classification_method`, `message_uuid`, `message_role`, `timestamp`, `git_branch`. None of these are queryable without JSON parsing at the application level.

The frontend modal (`memory-details-modal.tsx`) has five tabs: Overview, Provenance, Contexts, Anchors, and Activity. The Anchors tab renders the string list with `FileText` icons. The Provenance tab displays the raw JSON dictionary.

### 2.2 Extraction Pipeline

The `MemoryExtractorService` parses JSONL session logs from Claude Code. It extracts text content from user and assistant messages and classifies candidates by type. However, it does **not**:

- Parse tool calls to extract file references from `Read`, `Edit`, `Write`, `Grep`, or `Glob` invocations.
- Capture `agent_type` or `model` from message metadata.
- Auto-detect the current git commit at extraction time.

### 2.3 CLI Surface

The `skillmeat memory item create` command supports `--type`, `--content`, `--confidence`, and `--status` flags. It lacks `--provenance` and `--anchors` flags entirely, meaning agents creating memories in-session cannot attach file context or session metadata without constructing raw JSON payloads.

### 2.4 Problem Space

Memories lack the contextual richness needed to be truly useful for agent workflows. The pre-task memory load (`skillmeat memory search`) returns items with no source context: no files, no commits, no agent provenance. Agents cannot assess whether a memory is relevant to their current task because they cannot see the codebase surfaces it originated from. Human reviewers triaging candidate memories in the web UI see raw JSON blobs rather than structured provenance, making it difficult to evaluate quality and relevance at a glance.

---

## 3. Problem Statement

**User Story:**

> As an AI agent preparing for implementation work, when I search for relevant memories, I need to see which files, commits, and tools produced each memory so I can assess its relevance to my current task -- instead of just seeing unstructured text with no source context.

**Technical Root Causes:**

1. **`anchors_json` stores `List[str]`** -- No structure for types, line ranges, commits, or descriptions. A bare path like `"skillmeat/cache/models.py"` provides no signal about what in that file is relevant or why.

2. **`provenance_json` is untyped `Dict[str, Any]`** -- Cannot be queried, filtered, or sorted via SQL. Filtering memories by git branch or agent type requires deserializing every row.

3. **No indexed DB columns for commonly-filtered provenance fields** -- Even though the extraction pipeline writes `git_branch` and `session_id` into the JSON, these cannot participate in `WHERE` clauses or index scans.

4. **Extraction pipeline does not parse tool calls** -- File references embedded in `Read`, `Edit`, `Write`, `Grep`, and `Glob` tool invocations are discarded during extraction, losing the most direct evidence of which files a memory relates to.

5. **No CLI flags for `--provenance` / `--anchors`** -- Agents creating memories during sessions must omit anchors and provenance entirely or construct raw API payloads, which is error-prone and undocumented.

---

## 4. Goals & Success Metrics

### Goal 1: Structured Anchors

Transform anchors from flat string arrays to typed objects containing path, classification, optional line ranges, optional commit SHA, and optional description.

- **Anchor types:** `code`, `plan`, `doc`, `config`, `test`
- **Success metric:** 80%+ of extracted memories have at least one auto-linked anchor after pipeline enhancement.

### Goal 2: Queryable Provenance

Promote key provenance fields to indexed database columns: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`.

- **Success metric:** Memories are filterable by any promoted field in the API list endpoint with <50ms query time for 10K memories.

### Goal 3: Auto-Population from Extraction

Parse tool calls from JSONL session logs to extract file paths and classify them as anchors. Capture agent type and model from message metadata. Auto-detect git commit from extraction context.

- **Success metric:** Extraction populates anchors and all promoted provenance fields without manual intervention. 80%+ anchor coverage on extracted memories.

### Goal 4: Agent-Assisted Manual Capture

Provide `--anchor` flags on the CLI `memory item create` command and documented instructions for agents to attach anchors during in-session capture.

- **Success metric:** Agent-created memories can include relevant file anchors via CLI flags without constructing raw JSON.

---

## 5. User Personas & Journeys

### Primary: AI Agent (Memory Consumer)

An agent beginning implementation work searches memories before writing code. It needs to filter by `git_branch` to find context from the current feature branch, filter by `agent_type` to find learnings from similar agents, and inspect file anchors to assess whether a memory about "SQLAlchemy lazy loading" is relevant to the specific models it is about to modify.

**Current pain:** The agent receives unstructured blobs. It cannot filter by branch, agent, or model. Anchor paths are bare strings with no indication of relevance.

**Target state:** The agent filters memories by branch and model, sees structured anchors with file types and line ranges, and can make an informed decision about which memories to load into context.

### Secondary: AI Agent (Memory Producer)

An agent discovers a root cause during debugging and wants to capture it immediately. It uses `skillmeat memory item create` with `--anchor skillmeat/cache/models.py:code:142-156` to record exactly which lines contained the issue.

**Current pain:** The agent cannot set anchors or provenance via CLI. The discovery context is lost.

**Target state:** The agent captures anchors and provenance in a single CLI command. The memory is immediately enrichable and queryable.

### Tertiary: Human Developer (Memory Reviewer)

A developer opens the web UI to triage candidate memories. The Anchors tab shows rich cards with file type badges (code, config, test), clickable line references, and commit context. The Provenance section shows the agent type, model, git branch, and session ID in a structured layout rather than raw JSON.

**Current pain:** The Provenance tab shows a raw JSON dictionary. The Anchors tab shows a list of plain file paths with generic icons.

**Target state:** Both tabs display structured, formatted information that enables fast triage decisions.

---

## 6. Requirements

### 6.1 Functional Requirements

| ID | Requirement | Priority | Notes |
| :-: | ----------- | :------: | ----- |
| FR-1 | Transform `anchors_json` schema from `List[str]` to `List[AnchorObject]` with `type`, `path`, `line_start`, `line_end`, `commit_sha`, `description` | Must | Breaking change -- requires data migration |
| FR-2 | Add indexed columns to `memory_items`: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type` | Must | Alembic migration with index creation |
| FR-3 | Update Pydantic schemas (create/update/response) for structured anchors and new provenance columns | Must | `AnchorCreate`, `AnchorResponse` schemas |
| FR-4 | Update repository layer to support filtering and sorting by new columns | Must | Add filter params to list query |
| FR-5 | Update API list endpoint to accept filter parameters for all new columns | Must | Query params: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type` |
| FR-6 | Parse tool calls from JSONL messages to extract file paths during extraction | Must | Handle `Read`, `Edit`, `Write`, `Grep`, `Glob` tool call payloads |
| FR-7 | Classify extracted file paths into anchor types based on extension and path patterns | Should | `.py` in `tests/` = `test`, `.toml`/`.yaml` = `config`, `.md` in `docs/` = `doc`, etc. |
| FR-8 | Capture `agent_type` and `model` from JSONL message metadata during extraction | Must | From message envelope `type` and `model` fields |
| FR-9 | Auto-detect git commit SHA at extraction time from git context or JSONL metadata | Should | `git rev-parse HEAD` fallback if not in JSONL |
| FR-10 | Update frontend Anchors tab to render structured anchor objects with type badges, line ranges, and commit info | Must | Replace plain string list with rich anchor cards |
| FR-11 | Update frontend Provenance tab to display promoted fields with structured formatting | Should | Render promoted columns prominently; overflow JSON secondary |
| FR-12 | Add `--anchor` flag to CLI `memory item create` command | Must | Format: `path:type` or `path:type:start-end` |
| FR-13 | Add `--provenance-*` flags to CLI for `git_commit`, `agent_type`, `model` | Should | E.g., `--provenance-branch`, `--provenance-model` |
| FR-14 | Update TypeScript SDK types for `MemoryItemResponse` to include new fields and structured anchors | Must | `Anchor` type with all fields |
| FR-15 | Migrate existing `anchors_json` data from string arrays to structured format | Must | Wrap existing strings as `{path: str, type: "code"}` |
| FR-16 | Retain `provenance_json` for overflow fields (`llm_reasoning`, `tool_call_details`, `message_uuid`, etc.) | Must | Supplementary data store -- do not remove |
| FR-17 | Add documentation and instructions for agents to attach anchors during in-session `skillmeat memory item create` | Should | Update skillmeat-cli skill docs |
| FR-18 | Capture additional JSONL metadata when available: tool call type, calling agent name, parent session info | Could | Enriches `provenance_json` overflow |

### 6.2 Non-Functional Requirements

**Performance:**
- Index-based filtering on promoted columns must complete in <50ms for 10K memories.
- Anchor auto-linking during extraction must not add more than 2 seconds to processing a 500KB session log.

**Backwards Compatibility:**
- Existing memories with `List[str]` anchors must be migrated to structured format during the Alembic migration.
- The API should accept both legacy string arrays and new `AnchorObject` arrays during a transition period, or migrate all data at once so only the new format is needed going forward.
- `provenance_json` is retained for overflow data. No data loss during migration.

**Data Integrity:**
- Promoted column values are the canonical source of truth for their respective fields. The `provenance_json` blob is supplementary. On write, the service populates both the column and the JSON blob; on read, the column value takes precedence.

**Observability:**
- Anchor auto-linking operations should be logged with counts (files found, anchors created, duplicates skipped).
- Extraction pipeline spans should include anchor and provenance population steps.

---

## 7. Scope

### In Scope

- **Database schema migration:** New indexed columns on `memory_items`, anchors format transformation.
- **Backend updates:** Pydantic schemas, repository filter/sort support, service-layer provenance population, API list endpoint filter params.
- **Extraction pipeline enhancement:** Tool-call parsing, anchor auto-linking, anchor type classification, agent/model metadata capture, git commit detection.
- **Frontend updates:** Anchors tab enhancement with type badges and line ranges, Provenance tab structured display, memory list filter controls for new columns.
- **CLI updates:** `--anchor` and `--provenance-*` flags on `memory item create`.
- **Data migration:** Transform existing string anchors to structured objects.
- **Agent documentation:** Instructions and examples for manual anchor attachment during in-session capture.

### Out of Scope

- **Embedding/vector search on anchors** -- Future enhancement for semantic anchor retrieval.
- **Anchor validation** -- Checking if referenced files still exist at their paths is not included.
- **Real-time anchor updates** -- Anchors are snapshots; they do not update when files change.
- **Cross-project anchor resolution** -- Anchors are project-scoped; cross-project linking is out of scope.
- **Anchor diff visualization** -- Showing how anchored files changed since memory creation is a future feature.

---

## 8. Dependencies & Assumptions

### Internal Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| memory-extraction-pipeline-v2 (JSONL parser fixes) | Draft | Tool-call parsing builds on the JSONL parser infrastructure from that PRD. Can proceed in parallel if JSONL parsing is landed first. |
| Memory modal refactor (tabbed layout) | Completed | Anchors tab already exists as a UI surface ready for enhancement. |
| Memory system v1.0 + v1.1 (CRUD, extraction, CLI) | Completed | Foundation tables, services, and CLI commands are in place. |

### Assumptions

1. **JSONL session logs contain tool call data with file paths.** Verified: tool_use content blocks include file path parameters for `Read`, `Edit`, `Write`, `Grep`, and `Glob`.

2. **Agent type and model are available in JSONL message metadata.** Verified: message envelopes contain `type` (message type) and assistant messages include `model` fields.

3. **SQLite supports the required indexing.** Confirmed: indexed `VARCHAR` columns work correctly in SQLite for equality and prefix matching.

4. **Anchor type classification can be reliably inferred from file extension and path patterns.** Reasonable heuristic: `.py` files in `tests/` are `test` type, `.md` files in `docs/` are `doc` type, `.toml`/`.yaml`/`.json` config files are `config` type, etc. Edge cases default to `code`.

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| Breaking change to `anchors_json` format disrupts existing consumers | High | Certain | Alembic migration wraps existing string entries in `AnchorObject` format (`{path: str, type: "code"}`). All data migrated atomically. API validates new format only post-migration. |
| Extraction slowed by tool-call parsing | Medium | Low | Only parse messages containing `tool_use` content blocks. Skip messages without tool calls entirely. Lazy iteration avoids loading all tool calls into memory. |
| Over-linking: too many anchors per memory | Medium | Medium | Cap at 20 anchors per memory. Prioritize files from mutation tool calls (`Edit`, `Write`) over read-only calls (`Read`, `Grep`, `Glob`). Deduplicate by path. |
| JSONL format variations across Claude Code versions | Medium | Low | Robust parser with fallbacks already established in extraction-pipeline-v2. Unknown message types are skipped gracefully. |
| Index bloat from 6 new columns | Low | Low | All columns are nullable `VARCHAR` with individual indexes. Memory item counts in typical projects (hundreds to low thousands) make this negligible. |

---

## 10. Target State

After implementation, the memory system achieves full contextual richness:

- **Every extracted memory has structured anchors** linking to source files with type classification, optional line ranges, and commit context. An agent searching for "SQLAlchemy relationship loading" can see that the memory references `skillmeat/cache/models.py` lines 142-156 (type: `code`) and `tests/test_cache_models.py` (type: `test`).

- **Memories are filterable by six promoted dimensions:** `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, and `source_type`. An agent working on branch `feat/new-api` can filter for memories discovered on that branch. A developer can filter by `source_type = extraction` to review auto-extracted candidates.

- **The Anchors tab shows rich cards** with file type badges (color-coded by `code`/`plan`/`doc`/`config`/`test`), clickable line references, and commit SHA context. The flat string list is replaced with an informative, scannable layout.

- **Agents can manually attach anchors via CLI flags** during in-session capture. The command `skillmeat memory item create --project 1 --type gotcha --content "..." --anchor "skillmeat/cache/models.py:code:142-156"` produces a fully-anchored memory in a single invocation.

- **The provenance system captures a full session snapshot** -- model, agent type, git branch, commit SHA, tool calls, session ID -- creating a complete audit trail from memory back to its originating context.

---

## 11. Acceptance Criteria

- [ ] New Alembic migration adds 6 indexed columns (`git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`) and transforms `anchors_json` schema from string arrays to object arrays.
- [ ] Existing memories are migrated: string anchors wrapped in `AnchorObject` format with `type: "code"` default.
- [ ] API list endpoint accepts filter params: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`. Queries return correct filtered results.
- [ ] Extraction pipeline auto-links file anchors from tool calls with 80%+ coverage on sessions containing tool invocations.
- [ ] Extraction pipeline captures `agent_type` and `model` from JSONL message metadata and populates promoted columns.
- [ ] Frontend Anchors tab renders structured anchors with type badges, optional line range display, and commit context.
- [ ] CLI `memory item create` accepts `--anchor path:type` and `--anchor path:type:start-end` flags (repeatable for multiple anchors).
- [ ] TypeScript SDK types updated with `Anchor` interface and new provenance fields on `MemoryItemResponse`.
- [ ] All existing tests pass. New tests cover: filter queries on promoted columns, anchor parsing from tool calls, anchor type classification, CLI `--anchor` flag parsing, and data migration.
- [ ] `provenance_json` retained for overflow fields. No data loss during migration.

---

## 12. Open Questions

**Q1: Should anchor `commit_sha` reference the commit at extraction time or the commit where the file was last modified?**

> **Decision:** Extraction time. The anchor represents a snapshot of when the memory was created, not the file's full history. File modification tracking is out of scope.

**Q2: Should we limit the number of auto-linked anchors per memory?**

> **Decision:** Yes. Cap at 20 anchors per memory item. Prioritize files from mutation tool calls (`Edit`, `Write`) over read-only calls (`Read`, `Grep`, `Glob`). Within each tier, deduplicate by path and keep the most specific reference (narrowest line range).

**Q3: What values should the `source_type` promoted column accept?**

> **Decision:** Four values: `extraction` (from the JSONL extraction pipeline), `manual` (CLI or API create), `in-session` (agent capture during active work), `import` (bulk import operations). Default for new items created via CLI/API is `manual`.

**Q4: Should the API accept both old (`List[str]`) and new (`List[AnchorObject]`) anchor formats?**

> **Decision:** Migrate all data at once in the Alembic migration. Post-migration, the API only accepts `List[AnchorObject]`. This avoids maintaining two code paths indefinitely. The migration is safe because existing anchor data is simple strings easily wrapped in objects.

---

## 13. Appendices

### A. Anchor Object Schema

```python
from typing import Literal, Optional
from pydantic import BaseModel

class Anchor(BaseModel):
    """Structured file anchor linking a memory to a specific codebase location."""
    path: str                              # File path relative to project root
    type: Literal["code", "plan", "doc", "config", "test"]
    line_start: Optional[int] = None       # Starting line number (1-indexed)
    line_end: Optional[int] = None         # Ending line number (inclusive)
    commit_sha: Optional[str] = None       # Git commit SHA when anchor was created
    description: Optional[str] = None      # Why this file is relevant to the memory
```

### B. Promoted Provenance Columns (SQL)

```sql
ALTER TABLE memory_items ADD COLUMN git_branch VARCHAR;
ALTER TABLE memory_items ADD COLUMN git_commit VARCHAR;
ALTER TABLE memory_items ADD COLUMN session_id VARCHAR;
ALTER TABLE memory_items ADD COLUMN agent_type VARCHAR;
ALTER TABLE memory_items ADD COLUMN model VARCHAR;
ALTER TABLE memory_items ADD COLUMN source_type VARCHAR DEFAULT 'manual';

CREATE INDEX idx_memory_items_git_branch ON memory_items(git_branch);
CREATE INDEX idx_memory_items_git_commit ON memory_items(git_commit);
CREATE INDEX idx_memory_items_session_id ON memory_items(session_id);
CREATE INDEX idx_memory_items_agent_type ON memory_items(agent_type);
CREATE INDEX idx_memory_items_model ON memory_items(model);
CREATE INDEX idx_memory_items_source_type ON memory_items(source_type);
```

### C. Anchor Type Classification Rules

| Pattern | Anchor Type | Examples |
|---------|:-----------:|---------|
| `tests/` prefix or `test_` prefix in filename | `test` | `tests/test_models.py`, `__tests__/button.test.tsx` |
| `.md` extension in `docs/` or `project_plans/` | `doc` | `docs/architecture.md`, `docs/project_plans/PRDs/feature.md` |
| `.md` extension in `.claude/progress/` or `.claude/worknotes/` | `plan` | `.claude/progress/prd/phase-1.md` |
| `.toml`, `.yaml`, `.yml`, `.json`, `.ini`, `.cfg`, `.env` extension | `config` | `pyproject.toml`, `tsconfig.json`, `.env.local` |
| All other files | `code` | `skillmeat/api/routers/memory_items.py`, `web/components/modal.tsx` |

### D. CLI Anchor Flag Format

```bash
# Single anchor (type only)
skillmeat memory item create --project 1 --type gotcha \
  --content "SQLAlchemy lazy loading fails silently in async contexts" \
  --anchor "skillmeat/cache/models.py:code"

# Single anchor with line range
skillmeat memory item create --project 1 --type gotcha \
  --content "SQLAlchemy lazy loading fails silently in async contexts" \
  --anchor "skillmeat/cache/models.py:code:142-156"

# Multiple anchors (repeatable flag)
skillmeat memory item create --project 1 --type decision \
  --content "Chose promoted columns over JSON queries for provenance filtering" \
  --anchor "skillmeat/cache/models.py:code:45-52" \
  --anchor "docs/project_plans/PRDs/features/memory-anchors-provenance-v1.md:plan"

# With provenance flags
skillmeat memory item create --project 1 --type learning \
  --content "Tool call parsing requires handling nested content blocks" \
  --anchor "skillmeat/core/services/memory_extractor_service.py:code:89-120" \
  --provenance-branch "feat/memory-anchors" \
  --provenance-model "claude-opus-4-6" \
  --provenance-agent-type "python-backend-engineer"
```

### E. Related PRDs

| PRD | Status | Relationship |
|-----|--------|-------------|
| memory-extraction-pipeline-v2 | Draft | Prerequisite -- JSONL parser fixes that this PRD's tool-call parsing builds upon |
| memory-context-system-v1-1 | Completed | Foundation -- CLI and extraction infrastructure this PRD extends |
| memory-context-system-v1 | Completed | Foundation -- Core memory model and lifecycle |
| memory-context-system-gap-closure-v1-2 | In progress | Parallel -- Gap closure work; anchors/provenance enhancement is additive |

---

## Implementation

### Phased Approach

**Phase 1: Database & Schema Foundation** (1 day)

Establish the data layer changes that all subsequent phases depend on.

- Alembic migration: add 6 indexed `VARCHAR` columns to `memory_items` with appropriate defaults.
- Data migration: transform existing `anchors_json` from `List[str]` to `List[AnchorObject]` (wrap each string as `{"path": str, "type": "code"}`).
- Update SQLAlchemy model (`cache/models.py`) with new columns and updated `anchors_json` documentation.
- Update Pydantic schemas (`api/schemas/memory.py`): `AnchorCreate`, `AnchorResponse`, updated `MemoryItemCreate`, `MemoryItemUpdate`, `MemoryItemResponse`.
- Unit tests for schema validation and migration correctness.

**Phase 2: Backend Service & Repository** (1 day)

Wire the new schema through the service and API layers.

- Update `MemoryItemRepository` with filter/sort support for all 6 new columns.
- Update `MemoryService` to populate promoted columns from provenance during create/update operations (write-through pattern).
- Update API list endpoint (`GET /memory-items/`) to accept filter query parameters: `git_branch`, `git_commit`, `session_id`, `agent_type`, `model`, `source_type`.
- Update CLI `memory item create` with `--anchor` flag (repeatable, format `path:type[:start-end]`) and `--provenance-*` flags.
- Integration tests for filtered queries and CLI flag parsing.

**Phase 3: Extraction Pipeline Enhancement** (1-2 days)

The highest-value phase: auto-populate anchors and provenance from session data.

- Add tool-call parser to `MemoryExtractorService`: iterate message content blocks, identify `tool_use` blocks for `Read`, `Edit`, `Write`, `Grep`, `Glob`, extract file path parameters.
- Implement anchor type classification using extension and path pattern rules (see Appendix C).
- Capture `agent_type` and `model` from JSONL message envelope metadata.
- Auto-detect `git_commit` from extraction context (`git rev-parse HEAD` or JSONL `gitBranch`/commit fields).
- Anchor deduplication and prioritization: mutations (`Edit`, `Write`) ranked above reads (`Read`, `Grep`, `Glob`); cap at 20 per memory.
- Unit tests for tool-call parsing, type classification, deduplication, and metadata capture.

**Phase 4: Frontend Enhancement** (1 day)

Surface the new data in the web UI.

- Update TypeScript SDK types: `Anchor` interface with all fields, updated `MemoryItemResponse` type.
- Enhance Anchors tab: render structured anchor cards with type badges (color-coded), optional line range display, commit SHA chips, and description text.
- Add filter controls to the memory list page for promoted provenance columns.
- Update Provenance tab: display promoted fields prominently in a structured layout; render overflow `provenance_json` as secondary detail.

**Phase 5: Documentation & Agent Instructions** (0.5 day)

Ensure agents and developers can use the new capabilities.

- Update `skillmeat-cli` skill with anchor capture instructions and examples.
- Update CLAUDE.md memory section with new CLI flag documentation.
- Add examples for agent-assisted anchor creation to skill docs.
- Document anchor type classification rules for agent reference.

### Progress Tracking

`.claude/progress/memory-anchors-provenance/`
