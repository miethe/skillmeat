---
title: 'Phase 1: Data Model Foundations'
parent: ../multi-platform-project-deployments-v1.md
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: multi-platform-project-deployments
prd_ref: null
plan_ref: null
---
# Phase 1: Data Model Foundations

**Duration**: 1 week
**Dependencies**: None (can start immediately)
**Total Effort**: 12 story points

## Overview

Phase 1 establishes the data layer for multi-platform deployments. It extends platform enums, introduces optional artifact platform targeting, and creates deployment profile models with DB tables, API schemas, and project-profile associations. No business logic changes in this phase — only data structure additions ensuring backward compatibility and foundation for Phases 2-5.

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P1-T1 | Extend Platform enum | Add `CODEX = "codex"` and `GEMINI = "gemini"` to `skillmeat/core/enums.py`; mirror changes to `skillmeat/web/types/enums.ts`; ensure `CLAUDE_CODE = "claude_code"` remains primary | Enums in both Python/TS match; backward-compatible (no existing values renamed); all enum values documented in code comments | 0.5 pts | python-backend-engineer | None |
| P1-T2 | Add target_platforms to Artifact model | Add optional `target_platforms: list[Platform] | None` field to `skillmeat/core/artifact.py` line 232 (after `origin_source`); semantics: `null` = deployable everywhere, non-empty list = platform-filtered | Field added; no changes to existing artifact behavior; field defaults to `None`; field is serializable to TOML | 1 pt | python-backend-engineer | P1-T1 |
| P1-T3 | Extend Artifact DB model | Add `target_platforms` column to `skillmeat/cache/models.py` (Artifact table); create Alembic migration; ensure backfill defaults to `None` for existing artifacts | Migration runs cleanly on empty/existing DBs; column type supports JSON/ARRAY based on dialect; no data loss on existing records | 1 pt | data-layer-expert | P1-T2 |
| P1-T4 | Extend Artifact API schemas | Add `target_platforms: list[Platform] | None = None` to request/response schemas in `skillmeat/api/schemas/artifacts.py` (line 282 area); update `ArtifactRead` and `ArtifactCreate` | Schemas validate correctly; OpenAPI docs auto-generate from Pydantic; backwards compatible (field optional) | 1 pt | python-backend-engineer | P1-T1 |
| P1-T5 | Create DeploymentProfile model (core) | Create `skillmeat/core/models/deployment_profile.py` with schema: `profile_id`, `platform`, `root_dir`, `artifact_path_map`, `project_config_filenames`, `context_path_prefixes`, `supported_artifact_types`, `created_at`, `updated_at` | Model is Pydantic; serializable to TOML; includes docstrings explaining each field; supports platform extensibility | 2 pts | python-backend-engineer | P1-T1 |
| P1-T6 | Create DeploymentProfile DB model | Create `DeploymentProfile` table in `skillmeat/cache/models.py` with columns: `id` (PK), `project_id` (FK), `profile_id` (text, unique per project), `platform` (enum), `root_dir` (text), `artifact_path_map` (JSON), `config_filenames` (JSON), `context_prefixes` (JSON), `supported_types` (JSON), `created_at`, `updated_at`; create migration | Migration creates table; index on `(project_id, profile_id)` for unique constraint; `artifact_path_map` JSON validated against schema | 1.5 pts | data-layer-expert | P1-T5 |
| P1-T7 | Create DeploymentProfile API schema | Create request/response schemas in `skillmeat/api/schemas/deployment_profiles.py`: `DeploymentProfileCreate`, `DeploymentProfileRead`, `DeploymentProfileUpdate` | Schemas Pydantic; validate field types and enums; OpenAPI docs auto-generate; `profile_id` immutable in `DeploymentProfileUpdate` | 1 pt | python-backend-engineer | P1-T5 |
| P1-T8 | Extend Project model for profile associations | Add `deployment_profiles: list[DeploymentProfile]` relationship to `skillmeat/core/models/project.py`; update DB Project model to include FK to DeploymentProfile table | Relationship bidirectional; cascade delete profiles if project deleted; existing projects have empty profiles list (backfilled in Phase 5) | 1 pt | python-backend-engineer | P1-T6 |
| P1-T9 | Extend Deployment record model | Add `deployment_profile_id` (text), `platform` (enum), `profile_root_dir` (text) fields to `skillmeat/core/models/deployment.py`; update DB Deployment model | Fields optional initially (Phase 2 makes required); existing deployments will have `None` values | 1 pt | python-backend-engineer | P1-T1 |
| P1-T10 | Create repository for DeploymentProfile CRUD | Create `skillmeat/cache/repositories/deployment_profile_repository.py` with methods: `create()`, `read_by_id()`, `read_by_project_and_profile_id()`, `list_by_project()`, `update()`, `delete()` | Repo uses SQLAlchemy; all methods support transaction context; tests cover CRUD ops and queries | 1 pt | python-backend-engineer | P1-T6 |
| P1-T11 | Create API router for DeploymentProfile endpoints | Create `skillmeat/api/routers/deployment_profiles.py` with endpoints: `POST /projects/{project_id}/profiles` (create), `GET /projects/{project_id}/profiles` (list), `GET /projects/{project_id}/profiles/{profile_id}` (read), `PUT /projects/{project_id}/profiles/{profile_id}` (update), `DELETE /projects/{project_id}/profiles/{profile_id}` (delete) | All endpoints return appropriate status codes; OpenAPI docs complete; authentication integrated (Clerk) | 1.5 pts | python-backend-engineer | P1-T7, P1-T10 |
| P1-T12 | Unit tests for Phase 1 models and repos | Create test suite covering: Platform enum values, Artifact `target_platforms` serialization, DeploymentProfile model validation, DB migrations, repository CRUD, API schema validation | Coverage >85% for all new code; tests pass on clean and existing DBs | 1 pt | python-backend-engineer | P1-T2 through P1-T11 |

## Quality Gates

- [ ] All enum, model, and schema changes compile without errors
- [ ] DB migrations run cleanly on fresh and existing databases
- [ ] API endpoints functional and documented in OpenAPI
- [ ] Unit tests pass with >85% coverage
- [ ] Backward compatibility verified (existing projects/artifacts unchanged)
- [ ] Code review approved for all new models and migrations

## Key Files

**Core Models** (new/modified):
- `skillmeat/core/enums.py` — Extended Platform enum (P1-T1)
- `skillmeat/core/artifact.py` — Added `target_platforms` field (P1-T2)
- `skillmeat/core/models/deployment_profile.py` — New (P1-T5)
- `skillmeat/core/models/deployment.py` — Added profile-related fields (P1-T9)
- `skillmeat/core/models/project.py` — Added profile relationship (P1-T8)

**Database** (new/modified):
- `skillmeat/cache/models.py` — Added Artifact `target_platforms`, DeploymentProfile table (P1-T3, P1-T6)
- `skillmeat/cache/repositories/deployment_profile_repository.py` — New (P1-T10)
- `alembic/versions/` — New migration for Phase 1 schema changes (P1-T3, P1-T6)

**API** (new/modified):
- `skillmeat/api/schemas/artifacts.py` — Added `target_platforms` to artifact schemas (P1-T4)
- `skillmeat/api/schemas/deployment_profiles.py` — New (P1-T7)
- `skillmeat/api/routers/deployment_profiles.py` — New (P1-T11)

**Frontend** (new/modified):
- `skillmeat/web/types/enums.ts` — Extended Platform enum (P1-T1)
- `skillmeat/web/types/deployments.ts` — Can add `target_platforms` type hints (optional in Phase 1)

**Tests** (new):
- `tests/test_core_models_deployment_profile.py` — DeploymentProfile model tests (P1-T12)
- `tests/test_cache_deployment_profile_repository.py` — Repository tests (P1-T12)
- `tests/test_api_deployment_profiles.py` — Router tests (P1-T12)

## Integration Notes

**Backward Compatibility**: All new fields are optional. Existing artifacts without `target_platforms` default to `None` (deployable everywhere). Existing projects without profiles have an empty `deployment_profiles` list.

**DB Migration Strategy**: Alembic migration (P1-T3, P1-T6) adds columns with `nullable=True`, ensuring no data loss on existing records.

**Phase 2 Dependency**: Phase 2 uses these models to implement deployment logic. DeploymentProfile defines the contract for how artifacts map to filesystem paths per platform.

**Phase 3 Dependency**: Phase 3 references `context_path_prefixes` from DeploymentProfile to validate context entity paths.

---

**Phase Status**: Ready to start
**Blocks**: Phase 2 (Deployment Engine Refactor) — awaits P1 API contracts
**Blocked By**: Nothing
