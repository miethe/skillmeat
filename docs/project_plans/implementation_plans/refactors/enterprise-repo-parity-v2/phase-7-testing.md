---
title: "Phase 7: Testing & Validation"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-12
updated: 2026-03-12
feature_slug: enterprise-repo-parity
feature_version: v2
phase: 7
phase_title: Testing & Validation
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
entry_criteria:
  - All of Phases 1-6 complete
  - All per-phase unit tests passing (test_enterprise_parity_phase3.py, phase4.py, phase5.py)
  - All 16 repositories classified and wired (Group A: 8 DI providers; Group B: 8 non-DI providers)
  - Alembic migration `ent_008_*` applied and confirmed on PostgreSQL
  - No 503 stubs remaining in `dependencies.py` for the 8 Group A interfaces
  - Phase 6 grep audit confirmed zero unguarded SQLite instantiations in `dependencies.py`
exit_criteria:
  - Full pytest suite passes in local mode with zero regressions
  - Integration tests confirm all 8 previously-503 endpoints return 200 in enterprise mode
  - Tenant isolation tests pass: data created under tenant A is not visible under tenant B for all new repos
  - `alembic heads` == 1 after all migrations
  - senior-code-reviewer sign-off: all new enterprise repos use SQLAlchemy 2.x style, no session.query(), no integer PKs, no missing _apply_tenant_filter()
  - All acceptance criteria AC-1 through AC-10 verified
---

# Phase 7: Testing & Validation

## Overview

**Duration:** 2-3 days | **Effort:** 9-10 story points | **Subagents:** `python-backend-engineer`, `senior-code-reviewer`

Phase 7 is the final validation gate before the feature is considered complete. It runs the full test suite in both modes, executes integration tests against a real PostgreSQL instance (docker-compose enterprise profile), performs tenant isolation verification, and conducts a code review pass.

**Why this phase exists separately from per-phase testing:**

Per-phase unit tests (Phases 3-5) use `MagicMock(spec=Session)` and test individual classes in isolation. Phase 7 tests the full stack end-to-end: real HTTP requests → FastAPI → DI layer → enterprise repository → PostgreSQL → tenant isolation. It also validates that local mode is completely unaffected, which can only be confirmed after all changes are finalized.

---

## Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-7.1 | Full pytest suite in local mode | Run `pytest -v` against the full test suite with `SKILLMEAT_EDITION=local` (or no edition env set); confirm zero regressions; any existing pre-phase-7 failures are documented as pre-existing and do not count as regressions | `pytest` exits 0 OR all failures are documented as pre-existing in the test run; no new test failures introduced by phases 2-6 changes; output saved to `.claude/worknotes/enterprise-repo-parity/local-mode-test-results.md` | 1 pt | python-backend-engineer | All prior phases complete | test output |
| ENT2-7.2 | Integration tests: enterprise mode endpoint smoke | Write or update integration tests in `skillmeat/cache/tests/test_enterprise_parity_integration.py` (marked `@pytest.mark.integration`); test each of the 8 previously-503 endpoints against a real PostgreSQL via docker-compose enterprise profile; verify HTTP 200 response with valid (possibly empty) response body; test must explicitly set `SKILLMEAT_EDITION=enterprise` | Test file created; all 8 endpoints tested; all return HTTP 200 in enterprise mode; test is marked `@pytest.mark.integration`; test is skipped if PostgreSQL docker-compose is not running (skip marker or env guard) | 3 pts | python-backend-engineer | ENT2-7.1 | `skillmeat/cache/tests/test_enterprise_parity_integration.py` |
| ENT2-7.3 | Tenant isolation integration tests | In `test_enterprise_parity_integration.py`, add a tenant isolation test suite (marked `@pytest.mark.integration`); for each new repository class, test the negative case: create a record with tenant A's context, query with tenant B's context, verify empty result; cover at minimum: tags, groups, settings, projects, deployments, marketplace sources; document which repos are Stub/Passthrough and excluded from isolation testing | Isolation tests written for all Full-tier new repos; each test explicitly creates with tenant A, queries with tenant B, asserts empty result; Stub/Passthrough repos documented as excluded with comment | 3 pts | python-backend-engineer | ENT2-7.2 | `skillmeat/cache/tests/test_enterprise_parity_integration.py` |
| ENT2-7.4 | Alembic migration verification | Run `alembic heads` in the docker-compose enterprise environment after all migrations applied; confirm output is exactly 1 revision; run `alembic history` and verify `ent_008_*` appears in the chain with correct `down_revision`; run `alembic downgrade -1` then `alembic upgrade head` to verify `downgrade()` function works cleanly | `alembic heads` output == 1 line; `alembic history` shows linear chain ending at `ent_008_*`; downgrade+upgrade round-trip exits 0; results documented | 0.5 pt | python-backend-engineer | ENT2-7.3 | migration environment |
| ENT2-7.5 | Code review: enterprise repo compliance | Review all new enterprise repository classes added in Phases 3-5 against the review checklist below; flag any violations with file:line references; confirm all fixes are applied before sign-off | Review checklist completed for all new enterprise repo classes; zero remaining violations at sign-off; review notes saved to `.claude/worknotes/enterprise-repo-parity/code-review-notes.md` | 2 pts | senior-code-reviewer | ENT2-7.4 | `skillmeat/cache/enterprise_repositories.py`, `skillmeat/api/dependencies.py` |

---

## Code Review Checklist (ENT2-7.5)

The `senior-code-reviewer` must verify each new enterprise repository class against all items:

### SQLAlchemy Style
- [ ] All SELECT queries use `select(Model)` not `session.query(Model)`
- [ ] All results retrieved via `session.execute(stmt).scalars().all()` or `.scalar_one_or_none()`
- [ ] No `session.query()` calls anywhere in the class
- [ ] No `session.execute(text(...))` raw SQL strings for tenant filtering

### Tenant Isolation
- [ ] `_apply_tenant_filter(stmt, Model)` called on every SELECT statement
- [ ] No SELECT statement bypasses tenant filtering (e.g., for "admin" lookups)
- [ ] INSERT/CREATE sets `tenant_id` from `TenantContext` or `_get_tenant_id()` helper
- [ ] No hardcoded tenant_id values in any method

### Model Usage
- [ ] Imports only `EnterpriseBase`-inheriting models — no `Base` from `models.py`
- [ ] No direct integer PK references (all IDs are `uuid.UUID`)
- [ ] FK references use UUID, not integer

### Session Management
- [ ] `Session` is injected via constructor, not created internally
- [ ] No `Session()` or `SessionLocal()` calls inside repository methods
- [ ] No `with session:` context managers (session lifecycle is DI-managed)

### DI Wiring (dependencies.py)
- [ ] Every updated DI provider has an explicit `if settings.edition == "enterprise":` branch
- [ ] Enterprise branch returns enterprise class with injected `session=db`
- [ ] Local branch returns local class (unchanged from pre-phase state)
- [ ] No 503 stub remains (`raise HTTPException(status_code=503, ...)` for repository-missing)

### Stub Classes
- [ ] Stub classes return empty collections/None, never raise exceptions
- [ ] Stubs have a `logger.debug(...)` line explaining the stub behavior
- [ ] Stubs do not issue any database queries

---

## Integration Test Setup

Integration tests require the docker-compose enterprise profile. The test file should include a pytest fixture that skips gracefully if PostgreSQL is not available:

```python
import pytest
import os

pytestmark = pytest.mark.integration

@pytest.fixture(scope="session")
def enterprise_settings():
    """Skip if not running in enterprise integration test environment."""
    if os.getenv("SKILLMEAT_EDITION") != "enterprise":
        pytest.skip("Integration tests require SKILLMEAT_EDITION=enterprise")
    # ... return configured settings
```

**Running integration tests:**

```bash
# Start docker-compose enterprise profile
docker compose --profile enterprise up -d

# Run integration tests only
SKILLMEAT_EDITION=enterprise pytest -m integration -v skillmeat/cache/tests/test_enterprise_parity_integration.py

# Run all tests (local mode, skips integration)
pytest -v -m "not integration"
```

---

## Acceptance Criteria Verification Matrix

| AC | Criterion | Verified By | Task |
|:--:|-----------|-------------|------|
| AC-1 | All 8 previously-503 endpoints return HTTP 200 in enterprise mode | ENT2-7.2 integration test | ENT2-7.2 |
| AC-2 | No SQLite/db_path references execute in enterprise mode | Phase 6 grep audit + ENT2-7.5 code review | ENT2-6.5, ENT2-7.5 |
| AC-3 | Tenant A cannot retrieve tenant B data | ENT2-7.3 isolation tests | ENT2-7.3 |
| AC-4 | `alembic upgrade head` completes on fresh DB | Phase 2 ENT2-2.8 + ENT2-7.4 | ENT2-7.4 |
| AC-5 | `alembic heads` == 1 | ENT2-7.4 | ENT2-7.4 |
| AC-6 | All new enterprise repos >= 80% line coverage | Per-phase unit tests + `pytest --cov` | ENT2-3.6, ENT2-4.6, ENT2-5.6 |
| AC-7 | Local mode zero regressions | ENT2-7.1 | ENT2-7.1 |
| AC-8 | All new models inherit `EnterpriseBase` | ENT2-7.5 code review | ENT2-7.5 |
| AC-9 | `IProjectTemplateRepository` returns HTTP 200 + empty list | ENT2-7.2 (endpoint smoke) | ENT2-7.2 |
| AC-10 | Excluded-tier routers return 404, not 503 | ENT2-7.2 (if any Excluded-tier) | ENT2-7.2 |

---

## Parallelization Strategy

Tasks in Phase 7 are largely sequential by design — each builds on the previous result. The one exception is that ENT2-7.5 (code review) can begin reviewing completed phases while integration tests run, but sign-off must happen after ENT2-7.4.

**Recommended order:**

```
ENT2-7.1 (local mode regression check)
    ↓
ENT2-7.2 (enterprise integration smoke)
    ↓
ENT2-7.3 (tenant isolation — builds on ENT2-7.2 test file)
    ↓
ENT2-7.4 (alembic verification — parallel with ENT2-7.3 acceptable)
    ↓
ENT2-7.5 (code review — final gate)
```

ENT2-7.4 can run concurrently with ENT2-7.3 since they target different environments (DB migration vs test suite). Both must complete before ENT2-7.5 sign-off.

---

## Key Files

| File | Role |
|------|------|
| `skillmeat/cache/enterprise_repositories.py` | Primary review target for ENT2-7.5 |
| `skillmeat/api/dependencies.py` | Review target: DI provider patterns |
| `skillmeat/cache/tests/test_enterprise_parity_integration.py` | Output: integration + isolation tests (new file) |
| `skillmeat/cache/tests/test_enterprise_parity_phase3.py` | Existing phase unit tests |
| `skillmeat/cache/tests/test_enterprise_parity_phase4.py` | Existing phase unit tests |
| `skillmeat/cache/tests/test_enterprise_parity_phase5.py` | Existing phase unit tests |
| `.claude/worknotes/enterprise-repo-parity/local-mode-test-results.md` | Output: ENT2-7.1 results |
| `.claude/worknotes/enterprise-repo-parity/code-review-notes.md` | Output: ENT2-7.5 review notes |

---

## Definition of Done

The Enterprise Repository Parity v2 feature is complete when:

1. ENT2-7.1 through ENT2-7.5 all have green checkmarks
2. All 10 acceptance criteria verified (see matrix above)
3. `senior-code-reviewer` has signed off on ENT2-7.5
4. Feature branch merged to main
5. No new Alembic branch heads introduced (`alembic heads` == 1 on main)

---

**Parent plan:** [enterprise-repo-parity-v2.md](../enterprise-repo-parity-v2.md)
**Previous phase:** [phase-5-6-marketplace-nondi.md](./phase-5-6-marketplace-nondi.md)
