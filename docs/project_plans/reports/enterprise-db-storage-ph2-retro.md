# Enterprise DB Storage — Phase 2 Retrospective

**Date**: 2026-03-06
**Phase**: 2 — Enterprise Repository Implementation
**PRD**: `docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md`
**Branch**: `feat/enterprise-db-storage`
**Tasks completed**: 12/14 (ENT-2.1 through ENT-2.12)

---

## Execution Summary

Phase 2 implemented the enterprise repository layer: `EnterpriseRepositoryBase` with automatic tenant isolation, full `EnterpriseArtifactRepository` and `EnterpriseCollectionRepository` implementations, a `RepositoryFactory` with FastAPI DI wiring, structured audit logging, and 95 unit tests.

**Batch timeline:**

| Batch | Tasks | Agents | Outcome |
|-------|-------|--------|---------|
| 1 | ENT-2.1 | 1 (data-layer-expert) | Clean — foundation class, committed solo |
| 2 | ENT-2.2–2.10 | 5 in parallel | All completed, 1 file shared by 3 agents (no merge conflicts) |
| 3 | ENT-2.11–2.12 | 2 in parallel | 95 tests written; cross-module isolation bug found and fixed |

---

## Orchestration Lessons

### 1. Parallel agents editing the same file is risky

Batch 2 had 5 agents, and 3 of them (ENT-2.2/2.3/2.6, ENT-2.4/2.5, ENT-2.10) all edited `enterprise_repositories.py`. This worked because git's merge logic handled non-overlapping sections, but it is fragile. ENT-2.7/2.8 was safely separated (new class appended at end of file), and ENT-2.9 created a new file entirely.

**Recommendation**: The safest pattern is one file per agent, or at minimum, clearly separate class/section boundaries with explicit instructions about where to insert code.

### 2. Batch grouping by file ownership > by task semantics

The tasks were grouped by semantic meaning (lookups, writes, collections, factory, audit). A more conflict-safe grouping would have been:

- Agent A: entire `EnterpriseArtifactRepository` (ENT-2.2–2.6)
- Agent B: entire `EnterpriseCollectionRepository` (ENT-2.7/2.8)
- Agent C: `repository_factory.py` (ENT-2.9)
- Agent D: audit method on base class (ENT-2.10)

This reduces file contention from 3 agents to 1 agent per file.

### 3. ENT-2.1 as a separate batch was correct

The foundation class (`EnterpriseRepositoryBase`) was the right critical-path gate. All 9 Batch 2 tasks genuinely depended on it, and the ~2 min wait was trivially small compared to the clarity it provided to downstream agents.

---

## Code-Specific Findings

### 4. SQLAlchemy 2.x vs 1.x style divergence is intentional

The existing `BaseRepository` in `repositories.py` uses legacy `session.query()` (1.x style), while the enterprise repos correctly use `select()` (2.x style). The `EnterpriseRepositoryBase` accepts a `Session` directly (matching FastAPI DI) rather than a `db_path` (matching the local repos). This is a deliberate divergence — the two patterns serve different backends (SQLite local vs PostgreSQL enterprise). Future agents should not try to "fix" this inconsistency.

### 5. Edition string is `"local"` not `"community"`

The progress doc and PRD reference `"community"` edition, but `APISettings.edition` in `skillmeat/api/config.py` uses `"local"/"enterprise"`. The ENT-2.9 agent discovered and corrected this at implementation time. Anyone reading the PRD vs the actual code should be aware of this mismatch.

### 6. Enterprise PKs are UUIDs, not integers

The progress doc and some task descriptions reference `artifact_id: int`, but enterprise models use `UUID` primary keys. The ENT-2.10 agent noted this and used `Optional[object]` for audit log entity IDs. This mismatch between plan and reality could trip up future tasks (ENT-2.13/2.14 and Phase 3+ especially).

---

## Testing Findings

### 7. SQLAlchemy comparator cache poisoning (critical discovery)

When enterprise models use PostgreSQL-specific types (`JSONB`, `UUID(as_uuid=True)`), and tests patch column types for SQLite compatibility, SQLAlchemy's ORM comparator cache retains the original types. This causes a subtle, silent data mismatch:

- `INSERT` uses the patched type processor (correct)
- `WHERE` clauses use the cached original type processor (wrong — e.g., strips UUID hyphens)
- Queries silently return zero rows

The fix requires propagating patched types to `comparator.__dict__['type']` via `sa_inspect(model_cls).columns`. This is **not documented in SQLAlchemy docs** and was only exposed because cross-module test execution triggered `configure_mappers()` before the SQLite patch ran.

**Location of fix**: `skillmeat/cache/tests/test_enterprise_collection_repository.py`, function `_patch_enterprise_metadata_for_sqlite()`.

### 8. Mock-based vs SQLite-based unit test strategy

Two approaches were used:

| Approach | Used by | Pros | Cons |
|----------|---------|------|------|
| `MagicMock(spec=Session)` | ENT-2.11 (artifact tests) | Fully isolated, fast, no SQLite compat issues | Doesn't exercise real SQL generation |
| SQLite in-memory with type shim | ENT-2.12 (collection tests) | More realistic, catches SQL bugs | Introduced comparator cache poisoning; requires maintenance of the shim |

**Recommendation**: For enterprise repos with PostgreSQL-only types, mock-based testing is safer for unit tests. Real PostgreSQL via docker-compose (ENT-2.13) should be the integration-level validation.

### 9. JSONB tag search cannot be unit-tested on SQLite

`search_by_tags()` uses PostgreSQL's `@>` JSONB containment operator, which SQLite does not support. The artifact tests correctly marked these as `@pytest.mark.integration`. This validates the need for ENT-2.13 (docker-compose PostgreSQL integration tests) to cover this code path.

---

## Recommended Knowledge Captures

| Finding | Target | Type |
|---------|--------|------|
| SQLAlchemy 2.x vs 1.x divergence (item 4) | SkillMeat Memory | `decision` |
| Edition string `"local"` not `"community"` (item 5) | SkillMeat Memory | `gotcha` |
| Enterprise PKs are UUIDs, not ints (item 6) | SkillMeat Memory | `constraint` |
| SQLAlchemy comparator cache poisoning (item 7) | SkillMeat Memory | `gotcha` |
| Mock vs SQLite unit test strategy (item 8) | SkillMeat Memory | `decision` |
| Batch grouping by file ownership (items 1–2) | Agent MEMORY.md | `learning` |
