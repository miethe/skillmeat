---
type: progress
schema_version: 2
doc_type: progress
prd: repo-pattern-refactor
feature_slug: repo-pattern-refactor
phase: 0
phase_title: Test Scaffolding & Prerequisites
status: pending
created: 2026-03-01
updated: '2026-03-04'
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- task-completion-validator
contributors: []
tasks:
- id: TASK-0.1
  title: 'Baseline tests: deployments.py'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 1.5 pts
- id: TASK-0.2
  title: 'Baseline tests: deployment_sets.py + deployment_profiles.py'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 1 pt
- id: TASK-0.3
  title: 'Baseline tests: context_sync.py'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 1 pt
- id: TASK-0.4
  title: 'Baseline tests: mcp.py, icon_packs.py, versions.py, artifact_history.py'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 1.5 pts
- id: TASK-0.5
  title: Add config.EDITION to APISettings
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.5 pts
- id: TASK-0.6
  title: Snapshot OpenAPI spec (pre-refactor baseline)
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies: []
  estimate: 0.5 pts
- id: TASK-0.7
  title: Record P95 latency baseline
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.5 pts
- id: TASK-0.8
  title: Run full test suite and document pre-existing failures
  status: pending
  assigned_to:
  - task-completion-validator
  dependencies:
  - TASK-0.1
  - TASK-0.2
  - TASK-0.3
  - TASK-0.4
  - TASK-0.5
  - TASK-0.6
  - TASK-0.7
  estimate: 0.5 pts
parallelization:
  batch_1:
  - TASK-0.1
  - TASK-0.2
  - TASK-0.3
  - TASK-0.4
  - TASK-0.5
  - TASK-0.6
  - TASK-0.7
  batch_2:
  - TASK-0.8
total_tasks: 8
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
progress: 62
---

# Phase 0: Test Scaffolding & Prerequisites — Progress

## Purpose

Create baseline test coverage for 8 untested routers and establish safety nets before any architectural changes. This phase ensures regressions are detectable during the refactor.

## Orchestration Quick Reference

```bash
# Batch 1 (ALL parallel — no dependencies between tasks)
Task("python-backend-engineer", "Create tests/api/test_deployments.py with endpoint tests for all routes in skillmeat/api/routers/deployments.py. Use tests/api/test_artifacts.py as template pattern (TestClient + MagicMock dependency overrides). Test every endpoint for expected status codes with mocked managers. Include at minimum: list, get, create, delete operations.")

Task("python-backend-engineer", "Create tests/api/test_deployment_sets.py with endpoint tests for all routes in skillmeat/api/routers/deployment_sets.py. Also expand tests/api/test_api_deployment_profiles.py (currently only 3 tests) to cover all deployment_profiles.py endpoints. Use existing test patterns.")

Task("python-backend-engineer", "Create tests/api/test_context_sync.py with endpoint tests for all routes in skillmeat/api/routers/context_sync.py. Test sync operations with mocked dependencies. Ensure data integrity endpoints are covered.")

Task("python-backend-engineer", "Create test files for 4 remaining untested routers: tests/api/test_mcp.py, tests/api/test_icon_packs.py, tests/api/test_versions.py, tests/api/test_artifact_history.py. Use tests/api/test_artifacts.py as template. Cover all endpoints in each router.")

Task("python-backend-engineer", "Add edition field to APISettings in skillmeat/api/config.py: edition: str = 'local'. This will be used by repository factory providers to select LocalXxxRepository vs future EnterpriseXxxRepository.")

Task("task-completion-validator", "Save current skillmeat/api/openapi.json as docs/project_plans/baselines/openapi-pre-refactor.json for post-migration diff verification. Create the baselines/ directory if needed.")

Task("python-backend-engineer", "Record P95 latency baseline on GET /api/v1/artifacts endpoint. Run 100 requests against the dev server, record P50/P95/P99 latency. Save results to .claude/worknotes/repo-pattern-refactor/context.md under a '## Performance Baseline' section.")

# Batch 2 (after all batch 1 complete)
Task("task-completion-validator", "Run full pytest suite: pytest -v --tb=short. Verify all tests pass. Document any pre-existing failures in .claude/worknotes/repo-pattern-refactor/context.md under '## Pre-existing Test Failures' section. Confirm new test files from TASK-0.1 through TASK-0.4 are included and passing.")
```

## Quality Gates

- [ ] `tests/api/test_deployments.py` exists with endpoint tests
- [ ] `tests/api/test_deployment_sets.py` exists with endpoint tests
- [ ] `tests/api/test_context_sync.py` exists with endpoint tests
- [ ] `tests/api/test_mcp.py` exists with endpoint tests
- [ ] `tests/api/test_icon_packs.py` exists with endpoint tests
- [ ] `tests/api/test_versions.py` exists with endpoint tests
- [ ] `tests/api/test_artifact_history.py` exists with endpoint tests
- [ ] `tests/api/test_api_deployment_profiles.py` expanded (>3 tests)
- [ ] `config.EDITION` defaults to `"local"` in APISettings
- [ ] OpenAPI pre-refactor snapshot saved
- [ ] P95 latency baseline recorded in context.md
- [ ] Full pytest suite passes (pre-existing failures documented)

## Notes

_Phase notes will be added during execution._
