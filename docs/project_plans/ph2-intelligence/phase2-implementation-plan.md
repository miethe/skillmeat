---
title: "Implementation Plan: SkillMeat Phase 2 - Intelligence & Sync"
description: "Phased AI-agent build-out covering search, smart updates, sync, and analytics deliverables"
audience: [ai-agents, developers]
tags: [implementation, planning, phase2, intelligence, sync]
created: 2025-11-10
updated: 2025-11-10
category: "product-planning"
status: draft
related:
  - /docs/project_plans/ph2-intelligence/AI_AGENT_PRD_PHASE2.md
  - /docs/project_plans/ph1-initialization/init-prd.md
---

# Implementation Plan: SkillMeat Phase 2 - Intelligence & Sync

**Plan ID**: `IMPL-2025-11-10-SKILLMEAT-PH2`

**Date**: 2025-11-10

**Author**: implementation-planner

**Related Documents**:
- **PRD**: `/docs/project_plans/ph2-intelligence/AI_AGENT_PRD_PHASE2.md`
- **Phase Context**: `/docs/project_plans/ph1-initialization/init-prd.md`

**Complexity**: XL

**Total Estimated Effort**: 14 agent-weeks (4 agents over 6 weeks)

**Target Timeline**: Week 9 → Week 14 (post-MVP schedule)

## Executive Summary

Phase 2 layers intelligence on top of the SkillMeat collection core by introducing cross-project discovery, three-way smart updates, bi-directional sync, and artifact analytics. Work starts by closing the F1.5 upstream-update gap, then progresses through parallel agent tracks (Diff/Merge, Search, Sync, Analytics) with explicit handoffs. Success is defined by meeting every DoD item in the Phase 2 PRD: new CLI commands, MergeEngine-backed update flows, sync pipelines, analytics storage, >75% coverage, and documentation refresh.

## Implementation Strategy

### Architecture Sequence

1. **Storage Layer**: finalize artifact event schema + SQLite deployment tables; extend manifests/locks for sync metadata.
2. **Core Utilities**: implement `DiffEngine`, `MergeEngine`, `SearchManager`, `SyncManager`, and `AnalyticsManager` under `skillmeat/core` + `skillmeat/utils`.
3. **Service Layer**: wire ArtifactManager update logic, sync orchestration, and search facades that coordinate config, manifests, and CLI I/O.
4. **CLI Layer**: expose `diff`, `search`, `find-duplicates`, `update`, `sync`, and `analytics` commands with consistent UX, prompts, and error envelopes.
5. **Testing Layer**: new unit + integration suites per module plus fixtures in `tests/fixtures/phase2`.
6. **Documentation Layer**: command references, guides (`searching`, `updating-safely`, `syncing-changes`, `using-analytics`), and README + CHANGELOG updates.
7. **Deployment Layer**: feature flag hooks (if needed), telemetry toggles, and release packaging for 0.2.0-alpha.

### Parallel Work Opportunities

- Weeks 9-10: Agent 1 builds DiffEngine while Agent 2 ships SearchManager (shared fixtures, no blocking dependency).
- Weeks 11-12: Agent 1 continues MergeEngine while Agent 3 finishes ArtifactManager.update + strategy UX using DiffEngine drop 1.
- Weeks 13-14: Agent 3 finalizes SyncManager while Agent 4 lands Analytics, integration tests, and doc set; test specialists run in parallel once APIs stabilize.

### Critical Path

1. **F1.5 Patch → DiffEngine v1 → MergeEngine**: ArtifactManager.update cannot progress until DiffEngine APIs stabilize; MergeEngine is prerequisite for smart updates + sync strategies.
2. **Search CLI**: must land before analytics so usage tracking can emit meaningful events during internal dogfood.
3. **Sync → Analytics**: sync instrumentation feeds analytics event tables; analytics waits for final schema + CLI contract.
4. **Integration Tests**: `test_update_flow` and `test_sync_flow` require all modules + fixtures; they gate release branch cut.

## Phase Breakdown

### Phase 0: Upstream Update Execution (F1.5)

**Duration**: 3 days  
**Dependencies**: Phase 1 core existing; requires PRD F1.5 context  
**Assigned Subagent(s)**: python-backend-engineer, cli-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P0-001 | Update Fetch Pipeline | Implement ArtifactManager.update fetch + cache of upstream refs | Fetches latest artifact revision, persists temp workspace, surfaces errors | 2 pts | python-backend-engineer | Existing Artifact model |
| P0-002 | Strategy Execution | Apply overwrite/merge/prompt strategies, integrate DiffEngine stub | All strategies selectable via CLI flag; prompt default requests confirmation | 3 pts | python-backend-engineer, cli-engineer | P0-001 |
| P0-003 | Lock & Manifest Updates | Persist new versions to collection manifests and lock files atomically | collection.toml + lock stay consistent even on failure (rollback) | 2 pts | python-backend-engineer | P0-002 |
| P0-004 | Regression Tests | Add unit/integration tests for update flows, including failure rollback | `test_update_flow.py` passes; coverage for update path >80% | 2 pts | test-engineer | P0-003 |

**Phase 0 Quality Gates**
- `skillmeat update <artifact>` performs real updates without raising `NotImplementedError`.
- Update transaction rolls back on network/merge failure.
- CLI help + docs describe `--strategy` options.
- `tests/test_update_flow.py` green in CI.

---

### Phase 1: Diff & Merge Foundations (Agent 1)

**Duration**: 4 weeks (Weeks 9-12)  
**Dependencies**: Phase 0 complete  
**Assigned Subagent(s)**: backend-architect, python-backend-engineer, cli-engineer, test-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P1-001 | DiffEngine Scaffolding | Implement `diff_files` + `diff_directories` with ignore patterns & stats | Handles text/binary, returns `DiffResult` with accurate counts | 4 pts | python-backend-engineer | P0-004 |
| P1-002 | Three-Way Diff | Add `three_way_diff` supporting base/local/remote comparisons | Produces conflict metadata consumed by MergeEngine | 3 pts | backend-architect | P1-001 |
| P1-003 | MergeEngine Core | Implement auto-merge, conflict detection, marker generation | `merge()` merges simple cases; conflict files use Git-style markers | 4 pts | backend-architect | P1-002 |
| P1-004 | CLI Diff UX | Add `skillmeat diff` command with upstream/project targets & Rich formatting | CLI prints unified diff + summary stats; handles >100 files gracefully | 2 pts | cli-engineer | P1-001 |
| P1-005 | Diff/Merge Tests | Add `test_diff.py` + `test_merge.py` covering binary skips, conflicts, auto-merge | Coverage ≥75%, fixtures under `tests/fixtures/phase2/diff/` reusable | 3 pts | test-engineer | P1-003 |

**Phase 1 Quality Gates**
- DiffEngine + MergeEngine APIs documented with docstrings.
- CLI diff supports upstream comparison flag.
- Conflict markers validated via unit tests.
- Handoff notes delivered to Agent 3 (Sync).

---

### Phase 2: Search & Discovery (Agent 2)

**Duration**: 2 weeks (Weeks 9-10)  
**Dependencies**: None (read-only)  
**Assigned Subagent(s)**: search-engineer, cli-engineer, test-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P2-001 | SearchManager Core | Build metadata + content search with optional ripgrep acceleration | `search_collection` handles tag/content queries; fallback works when `rg` absent | 3 pts | search-engineer | None |
| P2-002 | Cross-Project Indexing | Support scanning multiple project paths with caching + scopes | Handles >10 projects with caching TTL 60s; config-driven root discovery | 2 pts | search-engineer | P2-001 |
| P2-003 | Duplicate Detection | Implement similarity hashing + threshold filtering | `find_duplicates` reports artifact pairs w/ similarity score | 2 pts | backend-architect | P2-001 |
| P2-004 | CLI Commands | Add `skillmeat search`, `search --projects`, `find-duplicates` | Commands show ranked results (score, path, context) and export JSON | 2 pts | cli-engineer | P2-002 |
| P2-005 | Search Tests | `test_search.py` covering metadata, regex, fuzzy, cross-project, duplicates | 100+ artifact dataset fixture; runtime <5s | 2 pts | test-engineer | P2-004 |

**Phase 2 Quality Gates**
- Search commands documented in `docs/guides/searching.md`.
- Duplicate detection handles hash collisions gracefully.
- CLI respects `--limit` and `--json` flags.
- Telemetry hooks emit `DEPLOY` + `SEARCH` events for analytics seed data.

---

### Phase 3: Smart Updates & Sync (Agent 3)

**Duration**: 3 weeks (Weeks 11-13)  
**Dependencies**: Phases 0 & 1 complete  
**Assigned Subagent(s)**: sync-engineer, python-backend-engineer, cli-engineer, test-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P3-001 | ArtifactManager Update Integration | Wire MergeEngine into update flow, add preview diff + strategy prompts | `skillmeat update` shows diff summary, handles auto-merge + conflicts | 3 pts | python-backend-engineer | P1-003 |
| P3-002 | Sync Metadata & Detection | Track deployed artifact hashes via `.skillmeat-deployed.toml`, detect drift | `sync check` lists modified artifacts with reason + timestamp | 3 pts | sync-engineer | P3-001 |
| P3-003 | SyncManager Pull | Implement `sync_from_project`, preview, conflict handling, strategies (overwrite/merge/fork) | `sync pull` updates collection + lock, records analytics event | 4 pts | sync-engineer | P3-002 |
| P3-004 | CLI & UX Polish | Add `sync check/pull/preview`, integrate with prompts, rollback, logging | CLI commands support dry-run, `--strategy`, exit codes, failure messaging | 2 pts | cli-engineer | P3-003 |
| P3-005 | Sync Tests | `test_sync.py` + fixtures for drift + conflict scenarios | Coverage ≥75%, ensures rollback on failure | 3 pts | test-engineer | P3-003 |

**Phase 3 Quality Gates**
- End-to-end update + sync flows recorded in screencasts for regression reference.
- `.skillmeat-deployed.toml` schema documented and versioned.
- Integration tests `test_sync_flow.py` green.
- All sync commands respect non-interactive mode via flags.

---

### Phase 4: Analytics & Insights (Agent 4)

**Duration**: 2 weeks (Weeks 13-14)  
**Dependencies**: Sync events instrumented (Phase 3)  
**Assigned Subagent(s)**: data-layer-expert, analytics-engineer, cli-engineer, documentation-writer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P4-001 | Schema & Storage | Initialize SQLite DB, migrations, connection mgmt, retention policy | Tables + indexes from PRD exist; vacuum + rotation supported | 3 pts | data-layer-expert | P3-003 |
| P4-002 | Event Tracking Hooks | Emit analytics events from deploy/update/sync/remove flows | Events buffered on failure, retried, and unit-tested | 2 pts | analytics-engineer | P4-001 |
| P4-003 | Usage Reports API | Implement `get_usage_report`, `suggest_cleanup`, JSON export | Aggregations performant (<500ms for 10k events) | 3 pts | analytics-engineer | P4-002 |
| P4-004 | CLI Analytics Suite | Add `skillmeat analytics` commands + export flags | CLI filters by artifact/time window, supports table + JSON output | 2 pts | cli-engineer | P4-003 |
| P4-005 | Analytics Tests | `test_analytics.py` covering event write/read, cleanup suggestions, exports | Deterministic tests using temp DB fixture | 2 pts | test-engineer | P4-003 |

**Phase 4 Quality Gates**
- Analytics DB path configurable via config manager.
- Usage report highlights most/least used artifacts accurately.
- Export file passes JSON schema validation.
- Docs include troubleshooting for locked DB files.

---

### Phase 5: Verification & Hardening

**Duration**: 1 week overlapping Weeks 13-14  
**Dependencies**: Phases 1-4 code delivered  
**Assigned Subagent(s)**: qa-engineer, performance-engineer, security-reviewer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P5-001 | Fixture Library | Build `tests/fixtures/phase2/` with sample artifacts, modified copies, conflict cases | Fixtures reused across diff/search/sync tests; documented README | 2 pts | qa-engineer | P1-005 |
| P5-002 | Integration Suites | Finalize `test_update_flow.py`, `test_sync_flow.py`, `test_search_across_projects.py` | Tests cover CLI workflows, run in CI <5 min | 3 pts | qa-engineer | P3-005 |
| P5-003 | Performance Benchmarks | Benchmark diff/search/sync on collections with 500 artifacts | Meets PRD perf targets (<2s diff, <3s search, <4s sync preview) | 2 pts | performance-engineer | P2-005 |
| P5-004 | Security & Telemetry Review | Ensure temp files cleaned, analytics opt-out, PII safe | Security checklist signed; logs redact user paths | 1 pt | security-reviewer | P4-004 |

**Phase 5 Quality Gates**
- Total coverage across new modules ≥75%.
- Performance benchmarks documented and shared.
- Security review report stored with release artifacts.
- CI workflow updated to include new tests + DB setup.

---

### Phase 6: Documentation & Release

**Duration**: 1 week (Week 14)  
**Dependencies**: All prior phases complete  
**Assigned Subagent(s)**: documentation-writer, release-manager, cli-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P6-001 | Command Reference Updates | Update `docs/commands.md` + CLI `--help` strings for new commands | All new flags documented with examples | 2 pts | cli-engineer | P4-004 |
| P6-002 | Feature Guides | Write guides: `searching`, `updating-safely`, `syncing-changes`, `using-analytics` | Guides include prerequisites, CLI samples, troubleshooting | 3 pts | documentation-writer | P3-004 |
| P6-003 | README + CHANGELOG Refresh | Highlight Phase 2 features, bump version to 0.2.0-alpha | CHANGELOG entries reference issues; README hero updated | 1 pt | release-manager | P6-002 |
| P6-004 | Release Checklist | Execute DoD checklist, tag release, upload artifacts | DoD items marked, release artifacts archived | 1 pt | release-manager | P5-004 |

**Phase 6 Quality Gates**
- All docs reviewed by owning engineers.
- CHANGELOG + version bump merged before tag.
- Release checklist stored alongside plan.
- Support channels notified of new commands + workflows.

## Global Quality Gates & Compliance

- **Definition of Done Alignment**: Each feature tracked back to PRD DoD list (code, tests, docs, perf, CLI help, review).
- **Testing Targets**: Unit coverage ≥75% for new modules; integration suites run in CI; smoke tests for CLI commands across macOS/Linux.
- **Observability**: Logging + telemetry enable tracing for diff/update/sync operations; analytics opt-out documented.
- **Handoffs**: Agent 1 → Agent 3 (Diff/Merge), Agent 3 → Agent 4 (Sync events), final integration review before release branch.

## Risk Register & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Merge conflicts more complex than anticipated | Delays sync/update adoption | Provide manual conflict editor hook + fallback to abort/rollback, extend fixtures early |
| Search performance on large workspaces | CLI perceived as slow | Enforce `--limit`, add caching, allow user-provided project roots |
| Analytics DB locks in concurrent CLI usage | Lost events / UX degradation | Use WAL mode, queue events, surface retries + health check command |
| Update rollback corruption | Collection state inconsistent | Wrap manifest + lock writes in temp file swap with fsync |

## Next Steps

1. Assign agents per phase and import tasks into `.claude/progress` tracking structure.
2. Kick off Phase 0 immediately so MergeEngine work can start on schedule.
