---
title: "ENT2-7.1: Local Mode Test Results"
created: 2026-03-12
phase: 7
task: ENT2-7.1
---

# Local Mode Test Results

## Summary

| Metric | Count |
|--------|-------|
| Total tests (cache layer) | 576 |
| Passed | 556 |
| Failed | 1 (pre-existing) |
| Errors | 5 (pre-existing) |
| Skipped | 19 |
| New failures from phases 2-6 | **0** |

## Enterprise Parity Unit Tests

All 246 enterprise parity unit tests across phases 3-5 pass:

- `test_enterprise_parity_phase3.py` — PASSED (all tests)
- `test_enterprise_parity_phase4.py` — PASSED (all tests)
- `test_enterprise_parity_phase5.py` — PASSED (all tests)

Run time: 4.17s (246 passed)

## Pre-existing Failures

### 1. test_workflow_repositories.py::TestWorkflowRepositoryGetWithStages::test_get_with_stages

- **Type**: FAILED
- **Error**: `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) FOREIGN KEY constraint failed`
- **Cause**: Workflow stage insertion references workflow table with FK, but the FK constraint fails in test setup. This is a workflow feature issue, unrelated to enterprise parity changes.

### 2. test_enterprise_collection_repository.py (3 errors)

- **Tests**: `test_update_raises_value_error_for_missing`, `test_create_sets_tenant_id_automatically`, `test_list_artifacts_returns_empty_for_nonexistent_collection`
- **Error**: `sqlalchemy.exc.CompileError: Compiler can't render element of type TSVECTOR`
- **Cause**: `enterprise_marketplace_catalog_entries` table has a `search_vector TSVECTOR` column that SQLite cannot compile. These tests use real SQLite sessions (not mocks) and hit the PostgreSQL-only type. Should be marked `@pytest.mark.integration` or use mock sessions.

### 3. test_tenant_isolation.py (2 errors)

- **Tests**: `test_tenant_a_collection_not_visible_to_tenant_b`, `test_tenant_a_cannot_add_tenant_b_artifact_to_own_collection`
- **Error**: Same TSVECTOR compilation error as above.
- **Cause**: Same root cause — TSVECTOR in enterprise models incompatible with SQLite test sessions.

## New Failures

**None.** All failures are pre-existing and unrelated to phases 2-6 enterprise parity changes.

## Conclusion

**ENT2-7.1: PASS** — Zero regressions introduced by enterprise repository parity phases 2-6. All 246 enterprise-specific unit tests pass. All pre-existing failures are documented and unrelated to the enterprise parity feature.
