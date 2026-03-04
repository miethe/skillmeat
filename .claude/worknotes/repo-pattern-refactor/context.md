---
type: context
schema_version: 2
doc_type: context
prd: "repo-pattern-refactor"
feature_slug: "repo-pattern-refactor"
created: 2026-03-01
updated: 2026-03-04
---

# Context: Storage Abstraction & Repository Pattern Refactor

## PRD Reference
- PRD: `docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md`
- Plan: `docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md`

## Key Decisions

_Decisions will be recorded during execution._

## Agent Observations

_Observations from executing agents will be appended here._

## Blockers

_Active blockers will be tracked here._

## Cross-Phase Dependencies

- Phase 0 (Test Scaffolding) → must complete before Phase 1 begins
- Phase 0 tasks are all independent (batch_1 parallel) except TASK-0.8 (validation)
- Phase 1 (Interface Design) -> Phase 2 (Local Repos) -> Phase 3 (DI Wiring) -> Phase 4 (Router Migration)
- Phase 5 (Test Alignment) can start after Phase 1 but needs Phase 4 for full validation
- Phase 6 (Validation) requires all previous phases complete

## Test Coverage Gaps (Pre-Refactor)

### Routers with Zero Test Coverage (8 of 15)
- `deployments.py` — CRITICAL: FS-heavy deployment operations
- `deployment_sets.py` — CRITICAL: Atomic group mutations
- `context_sync.py` — CRITICAL: Data integrity sync operations
- `mcp.py` — HIGH: MCP server management
- `icon_packs.py` — MEDIUM: Icon file operations
- `versions.py` — MEDIUM: Version resolution
- `artifact_history.py` — MEDIUM: History tracking
- `deployment_profiles.py` — MEDIUM: Only 3 existing tests (needs expansion)

### Well-Tested Routers (6 of 15)
- `artifacts.py` — 36 tests (LOW risk)
- `marketplace_sources.py` — 102 tests (LOW risk)
- `context_entities.py` — 39 tests (LOW risk)
- `projects.py` — 21 tests (LOW risk)
- `user_collections.py` — Multiple tests (LOW risk)
- `bundles.py` — Multiple tests (LOW risk)

## Architecture Prerequisites

- ABC pattern precedent: `skillmeat/sources/base.py` (ArtifactSource)
- DTO pattern: `@dataclass` for core, Pydantic for API layer
- Session management: Sync-only, per-call `_get_session()` in `skillmeat/cache/repository.py:162-179`
- `config.EDITION` does NOT exist yet — must be created in Phase 0
- All managers are sync (not async) — repositories should also be sync

## Performance Baseline

**Date**: 2026-03-04
**Endpoint**: GET /api/v1/artifacts
**Requests**: 50
**Server**: Started fresh via `python -m skillmeat.api.server` (was not already running at time of measurement)

| Metric | Value |
|--------|-------|
| P50 | 0.000901s |
| P95 | 0.014845s |
| P99 | 0.016221s |
| Min | 0.000702s |
| Max | 0.016221s |

**Notes**: Baseline recorded before any architectural changes (branch: `refactor/repo-pattern-refactor`,
no commits yet). All 50 requests returned HTTP 200. Latencies measured end-to-end via
`curl --time_total` on localhost — values reflect server processing time with no network overhead.
Server had no warm-up period; first request hit cold caches.

## Pre-existing Test Failures

_To be documented during Phase 0 TASK-0.8_

## Related PRDs

- PRD 2 (AAA/RBAC): Depends on this PRD's RequestContext and repository interfaces
- PRD 3 (Enterprise DB): Implements this PRD's interfaces for cloud database
