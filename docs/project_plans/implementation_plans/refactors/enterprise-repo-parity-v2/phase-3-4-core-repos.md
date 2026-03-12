---
title: "Phases 3-4: Core Enterprise Repositories"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-12
updated: 2026-03-12
feature_slug: enterprise-repo-parity
feature_version: v2
phase: 3
phase_title: Core Enterprise Repositories (Tag/Group/Settings/ContextEntity + Project/Deployment)
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
entry_criteria:
  - Phase 2 complete: all new enterprise models in `models_enterprise.py`
  - `alembic upgrade head` confirmed working on PostgreSQL
  - `alembic heads` == 1
  - Interface signatures for ITagRepository, IGroupRepository, ISettingsRepository, IContextEntityRepository, IProjectRepository, IDeploymentRepository confirmed from Phase 1 triage
exit_criteria:
  - Phase 3 exit: EnterpriseTagRepository, EnterpriseGroupRepository, EnterpriseSettingsRepository, EnterpriseContextEntityRepository all implemented and DI-wired; endpoints return 200 in enterprise mode
  - Phase 4 exit: EnterpriseProjectRepository, EnterpriseDeploymentRepository, EnterpriseDeploymentSetRepository, EnterpriseDeploymentProfileRepository all implemented and DI-wired; endpoints return 200 in enterprise mode
  - All new repos use SQLAlchemy 2.x select() style — zero session.query() calls
  - All new repos call _apply_tenant_filter() on every query
  - Unit tests pass for all 8 new repository classes using MagicMock(spec=Session)
  - No SQLite writes for any of these endpoints when SKILLMEAT_EDITION=enterprise
---

# Phases 3-4: Core Enterprise Repositories

## Overview

**Duration:** 3-5 days | **Effort:** 20 story points | **Subagents:** `python-backend-engineer`

Phases 3 and 4 are grouped together because they share the same implementor (`python-backend-engineer`), the same target files, and the same implementation pattern. Phase 3 covers the four highest-impact "pure metadata" domains (tags, groups, settings, context entities). Phase 4 covers the two filesystem-coupled domains (projects, deployments) plus their Group B companions (deployment sets, deployment profiles).

**Phase 3 scope:** 4 Group A repositories + DI wiring for those 4 + unit tests

**Phase 4 scope:** 2 Group A repositories + 2 Group B repositories + DI wiring for all 4 + unit tests

### File Ownership

All repository implementations go in `skillmeat/cache/enterprise_repositories.py`. All DI wiring goes in `skillmeat/api/dependencies.py`. Because both phases target the same files, they MUST be executed sequentially — not in parallel.

**Execution order:** Phase 3 fully complete → Phase 4 begins.

---

## Implementation Pattern Reference

All new enterprise repositories must follow this exact pattern (from existing `EnterpriseArtifactRepository`):

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from skillmeat.cache.enterprise_repositories import EnterpriseRepositoryBase
from skillmeat.cache.models_enterprise import EnterpriseTag  # (example)
from skillmeat.core.interfaces.repositories import ITagRepository  # (example)

class EnterpriseTagRepository(EnterpriseRepositoryBase, ITagRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_all(self) -> list[TagDTO]:
        stmt = select(EnterpriseTag)
        stmt = self._apply_tenant_filter(stmt, EnterpriseTag)
        result = self._session.execute(stmt).scalars().all()
        return [self._to_dto(row) for row in result]

    def get_by_id(self, tag_id: uuid.UUID) -> TagDTO | None:
        stmt = select(EnterpriseTag).where(EnterpriseTag.id == tag_id)
        stmt = self._apply_tenant_filter(stmt, EnterpriseTag)
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_dto(row) if row else None

    # ... other interface methods
```

**DI provider pattern** (from existing `get_artifact_repository`):

```python
def get_tag_repository(
    settings: SettingsDep,
    db: EnterpriseDatabaseDep,
) -> ITagRepository:
    if settings.edition == "enterprise":
        return EnterpriseTagRepository(session=db)
    return LocalTagRepository()  # existing local impl
```

---

## Phase 3 Task Breakdown

### ENT2-3: Tag, Group, Settings, ContextEntity Repositories

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-3.1 | EnterpriseTagRepository | Implement `EnterpriseTagRepository(EnterpriseRepositoryBase, ITagRepository)` in `enterprise_repositories.py`; implement all methods required by `ITagRepository` (get_all, get_by_id, create, update, delete, get_by_name); every select statement calls `_apply_tenant_filter()`; use SQLAlchemy 2.x `select()` throughout | All `ITagRepository` methods implemented; no `session.query()` calls; `_apply_tenant_filter()` called on every select; DTO mapping correct; class importable without errors | 3 pts | python-backend-engineer | Phase 2 complete | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-3.2 | EnterpriseGroupRepository | Implement `EnterpriseGroupRepository(EnterpriseRepositoryBase, IGroupRepository)` following same pattern; handle `is_default` flag logic (only one default group per tenant); all select statements filtered by tenant | All `IGroupRepository` methods implemented; `is_default` constraint enforced at DB or application level; tenant filtering on all queries | 3 pts | python-backend-engineer | ENT2-3.1 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-3.3 | EnterpriseSettingsRepository | Implement `EnterpriseSettingsRepository(EnterpriseRepositoryBase, ISettingsRepository)`; key-value storage with `get(key)`, `set(key, value)`, `get_all()`, `delete(key)` methods; the `(tenant_id, key)` unique constraint must be respected — use upsert pattern for `set()` | All `ISettingsRepository` methods implemented; `set()` uses upsert (INSERT ... ON CONFLICT DO UPDATE); tenant filtering on all queries; `get(key)` returns None for missing keys | 2 pts | python-backend-engineer | ENT2-3.2 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-3.4 | EnterpriseContextEntityRepository | Implement `EnterpriseContextEntityRepository(EnterpriseRepositoryBase, IContextEntityRepository)`; handle nullable `artifact_id` FK; support filtering by `entity_type` in list methods; JSONB `metadata` field — if interface has metadata filter, use standard equality not `@>` operator (save JSONB ops for integration tests only) | All `IContextEntityRepository` methods implemented; nullable FK handled correctly; entity_type filtering works; no `@>` JSONB operator in unit-testable paths | 3 pts | python-backend-engineer | ENT2-3.3 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-3.5 | DI wiring for Phase 3 repos | Update `get_tag_repository`, `get_group_repository`, `get_settings_repository`, `get_context_entity_repository` in `dependencies.py`; each provider checks `settings.edition == "enterprise"` and returns the appropriate enterprise class; local path returns existing local implementation unchanged | All 4 DI providers updated; enterprise path returns enterprise class; local path returns local class; no 503 stubs remain for these 4 interfaces | 1 pt | python-backend-engineer | ENT2-3.1 through ENT2-3.4 | `skillmeat/api/dependencies.py` |
| ENT2-3.6 | Unit tests for Phase 3 repos | Write unit tests for all 4 new repositories using `MagicMock(spec=Session)`; test: (a) happy path for each interface method, (b) tenant filter is applied (verify `_apply_tenant_filter` is called or mock returns only tenant-scoped data), (c) None/empty returns for missing records; do NOT use SQLite shims; mark any JSONB `@>` operator tests as `@pytest.mark.integration` | Test file created at `skillmeat/cache/tests/test_enterprise_parity_phase3.py`; all tests pass with `MagicMock(spec=Session)`; >= 80% line coverage for each of the 4 new classes; no SQLite shim usage | 4 pts | python-backend-engineer | ENT2-3.5 | `skillmeat/cache/tests/test_enterprise_parity_phase3.py` |

**Phase 3 Quality Gate:** Before proceeding to Phase 4, verify:
- `pytest skillmeat/cache/tests/test_enterprise_parity_phase3.py` — all pass
- Import check: `python -c "from skillmeat.cache.enterprise_repositories import EnterpriseTagRepository, EnterpriseGroupRepository, EnterpriseSettingsRepository, EnterpriseContextEntityRepository"`
- Manual smoke (or integration test): endpoints `/api/v1/tags`, `/api/v1/groups`, `/api/v1/settings`, `/api/v1/context-entities` return 200 in enterprise mode with empty list

---

## Phase 4 Task Breakdown

### ENT2-4: Project, Deployment, DeploymentSet, DeploymentProfile Repositories

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-4.1 | EnterpriseProjectRepository | Implement `EnterpriseProjectRepository(EnterpriseRepositoryBase, IProjectRepository)` implementing all `IProjectRepository` methods; enterprise projects are DB records — `filesystem_path` is a nullable metadata field, NOT a live filesystem reference; methods that would normally do filesystem operations (e.g., `get_project_path()`, `scan_deployments()`) must either: return the stored path string if available, or return None/empty if not; document any methods where enterprise behavior meaningfully diverges from local behavior | All `IProjectRepository` methods implemented; `filesystem_path` stored and returned as nullable string; no `os.path`, `pathlib.Path`, or filesystem operations; methods with filesystem-only semantics return None or empty list with a debug log; tenant filtering on all queries | 4 pts | python-backend-engineer | Phase 3 complete | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-4.2 | EnterpriseDeploymentRepository | Implement `EnterpriseDeploymentRepository(EnterpriseRepositoryBase, IDeploymentRepository)`; deployment records reference project by UUID (`project_id` FK); handle nullable `project_id` and `artifact_id`; implement `get_by_project()` and `list_by_status()` filtered query patterns; SQLAlchemy 2.x `select()` throughout | All `IDeploymentRepository` methods implemented; FK lookups via `select()` not `session.query()`; tenant filtering on all queries; FK nullable handling tested | 3 pts | python-backend-engineer | ENT2-4.1 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-4.3 | EnterpriseDeploymentSetRepository | Implement `EnterpriseDeploymentSetRepository(EnterpriseRepositoryBase)` for `DeploymentSetRepository` Group B replacement; implement the same interface as `DeploymentSetRepository` in `repositories.py`; no inheritance from the local class (use `EnterpriseRepositoryBase` base only); check what interface/protocol `DeploymentSetRepository` satisfies in `repositories.py` before implementing | Enterprise class implements same callable interface as local `DeploymentSetRepository`; no SQLite path references; tenant filtering on all queries; can be substituted for local class in DI provider | 2 pts | python-backend-engineer | ENT2-4.2 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-4.4 | EnterpriseDeploymentProfileRepository | Implement `EnterpriseDeploymentProfileRepository(EnterpriseRepositoryBase)` for `DeploymentProfileRepository` Group B replacement; `config` column is JSONB; `set_id` FK is nullable; follow same pattern as ENT2-4.3 | Enterprise class implements same callable interface as local `DeploymentProfileRepository`; JSONB `config` stored and returned correctly; tenant filtering on all queries | 2 pts | python-backend-engineer | ENT2-4.3 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-4.5 | DI wiring for Phase 4 repos | Update `get_project_repository`, `get_deployment_repository`, `get_deployment_set_repository`, `get_deployment_profile_repository` in `dependencies.py`; all 4 providers get edition-check with enterprise path; local path returns existing local/SQLite implementation unchanged; no 503 stubs remain for project/deployment | All 4 DI providers updated; no 503 stubs; local path unchanged; enterprise path returns enterprise class with injected session | 1 pt | python-backend-engineer | ENT2-4.1 through ENT2-4.4 | `skillmeat/api/dependencies.py` |
| ENT2-4.6 | Unit tests for Phase 4 repos | Write unit tests for all 4 new repositories in `skillmeat/cache/tests/test_enterprise_parity_phase4.py`; for `EnterpriseProjectRepository`: include explicit test that `filesystem_path` operations return None/empty without filesystem access; for deployment repos: include FK lookup tests; all tests use `MagicMock(spec=Session)` | Test file created; all tests pass; `EnterpriseProjectRepository` filesystem-path test verifies no `os.path` or `pathlib` calls; >= 80% line coverage per class | 4 pts | python-backend-engineer | ENT2-4.5 | `skillmeat/cache/tests/test_enterprise_parity_phase4.py` |

**Phase 4 Quality Gate:** Before proceeding to Phase 5:
- `pytest skillmeat/cache/tests/test_enterprise_parity_phase4.py` — all pass
- Import check: all 4 new classes importable from `enterprise_repositories.py`
- Endpoints `/api/v1/projects`, `/api/v1/deployments`, `/api/v1/deployment-sets`, `/api/v1/deployment-profiles` return 200 in enterprise mode
- Confirm no SQLite writes for any of the 4 endpoints in enterprise mode

---

## Parallelization Strategy

Phases 3 and 4 are sequential (same target files). Within each phase, repository implementation tasks are also sequential within `enterprise_repositories.py` to prevent edit conflicts. Test tasks (ENT2-3.6, ENT2-4.6) can be started immediately after the DI wiring task for that phase completes — the test file is a new file with no conflicts.

**Batch execution:**

```
Phase 3 Batch A (sequential, 1 agent): ENT2-3.1 → ENT2-3.2 → ENT2-3.3 → ENT2-3.4 → ENT2-3.5
Phase 3 Batch B (after Batch A): ENT2-3.6 (new test file)
                                  ↓ Phase 3 quality gate passes
Phase 4 Batch A (sequential, 1 agent): ENT2-4.1 → ENT2-4.2 → ENT2-4.3 → ENT2-4.4 → ENT2-4.5
Phase 4 Batch B (after Batch A): ENT2-4.6 (new test file)
                                  ↓ Phase 4 quality gate passes
```

---

## Key Files

| File | Role |
|------|------|
| `skillmeat/cache/enterprise_repositories.py` | Target: all new enterprise repository classes (~2370 lines, will grow) |
| `skillmeat/api/dependencies.py` | Target: DI providers for wiring (~1100 lines) |
| `skillmeat/cache/models_enterprise.py` | Input: new models from Phase 2 |
| `skillmeat/core/interfaces/repositories.py` | Input: interface signatures to fulfill (~4000 lines) |
| `skillmeat/core/repositories/local_*.py` | Reference: local implementations for interface comparison |
| `skillmeat/cache/repositories.py` | Reference: Group B local classes (DeploymentSetRepository, DeploymentProfileRepository) |
| `skillmeat/cache/tests/test_enterprise_parity_phase3.py` | Output: Phase 3 unit tests (new file) |
| `skillmeat/cache/tests/test_enterprise_parity_phase4.py` | Output: Phase 4 unit tests (new file) |

---

**Parent plan:** [enterprise-repo-parity-v2.md](../enterprise-repo-parity-v2.md)
**Previous phase:** [phase-2-schema.md](./phase-2-schema.md)
**Next phase:** [phase-5-6-marketplace-nondi.md](./phase-5-6-marketplace-nondi.md)
