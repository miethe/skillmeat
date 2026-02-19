---
type: progress
prd: multi-platform-project-deployments-v1
phase: 1
title: Data Model Foundations
status: completed
started: '2026-02-07T00:00:00Z'
completed: '2026-02-07T00:00:00Z'
overall_progress: 100
completion_estimate: completed
total_tasks: 12
completed_tasks: 12
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- data-layer-expert
contributors: []
tasks:
- id: P1-T1
  description: Extend Platform enum - Add CODEX and GEMINI to skillmeat/core/enums.py;
    mirror to skillmeat/web/types/enums.ts; ensure CLAUDE_CODE remains primary
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 0.5 pts
  priority: critical
- id: P1-T2
  description: 'Add target_platforms to Artifact model - Add optional target_platforms:
    list[Platform] | None field to skillmeat/core/artifact.py; null = deployable everywhere'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  estimated_effort: 1 pt
  priority: high
- id: P1-T3
  description: Extend Artifact DB model - Add target_platforms column to skillmeat/cache/models.py;
    create Alembic migration; backfill defaults to None
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - P1-T2
  estimated_effort: 1 pt
  priority: high
- id: P1-T4
  description: Extend Artifact API schemas - Add target_platforms to request/response
    schemas in skillmeat/api/schemas/artifacts.py; update ArtifactRead and ArtifactCreate
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  estimated_effort: 1 pt
  priority: high
- id: P1-T5
  description: Create DeploymentProfile model (core) - Create skillmeat/core/models/deployment_profile.py
    with profile_id, platform, root_dir, artifact_path_map, project_config_filenames,
    context_path_prefixes, supported_artifact_types
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  estimated_effort: 2 pts
  priority: critical
- id: P1-T6
  description: Create DeploymentProfile DB model - Create DeploymentProfile table
    in skillmeat/cache/models.py with all columns; create migration; index on (project_id,
    profile_id)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - P1-T5
  estimated_effort: 1.5 pts
  priority: high
- id: P1-T7
  description: 'Create DeploymentProfile API schema - Create request/response schemas
    in skillmeat/api/schemas/deployment_profiles.py: Create, Read, Update'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T5
  estimated_effort: 1 pt
  priority: high
- id: P1-T8
  description: Extend Project model for profile associations - Add deployment_profiles
    relationship to skillmeat/core/models/project.py; update DB Project model with
    FK; cascade delete
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T6
  estimated_effort: 1 pt
  priority: high
- id: P1-T9
  description: Extend Deployment record model - Add deployment_profile_id, platform,
    profile_root_dir fields to skillmeat/core/models/deployment.py; update DB model
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  estimated_effort: 1 pt
  priority: medium
- id: P1-T10
  description: Create repository for DeploymentProfile CRUD - Create skillmeat/cache/repositories/deployment_profile_repository.py
    with create, read, list, update, delete methods
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T6
  estimated_effort: 1 pt
  priority: high
- id: P1-T11
  description: Create API router for DeploymentProfile endpoints - Create skillmeat/api/routers/deployment_profiles.py
    with POST/GET/PUT/DELETE under /projects/{project_id}/profiles
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T7
  - P1-T10
  estimated_effort: 1.5 pts
  priority: high
- id: P1-T12
  description: Unit tests for Phase 1 models and repos - Test Platform enum values,
    Artifact target_platforms serialization, DeploymentProfile model validation, DB
    migrations, repository CRUD, API schema validation
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T2
  - P1-T3
  - P1-T4
  - P1-T5
  - P1-T6
  - P1-T7
  - P1-T8
  - P1-T9
  - P1-T10
  - P1-T11
  estimated_effort: 1 pt
  priority: high
parallelization:
  batch_1:
  - P1-T1
  batch_2:
  - P1-T2
  - P1-T4
  - P1-T5
  - P1-T9
  batch_3:
  - P1-T3
  - P1-T6
  - P1-T7
  batch_4:
  - P1-T8
  - P1-T10
  batch_5:
  - P1-T11
  batch_6:
  - P1-T12
  critical_path:
  - P1-T1
  - P1-T5
  - P1-T6
  - P1-T10
  - P1-T11
  - P1-T12
  estimated_total_time: 12 pts (6 batches)
blockers: []
success_criteria:
- id: SC-1
  description: All enum, model, and schema changes compile without errors
  status: pending
- id: SC-2
  description: DB migrations run cleanly on fresh and existing databases
  status: pending
- id: SC-3
  description: API endpoints functional and documented in OpenAPI
  status: pending
- id: SC-4
  description: Unit tests pass with >85% coverage
  status: pending
- id: SC-5
  description: Backward compatibility verified (existing projects/artifacts unchanged)
  status: pending
files_modified:
- skillmeat/core/enums.py
- skillmeat/web/types/enums.ts
- skillmeat/core/artifact.py
- skillmeat/cache/models.py
- skillmeat/core/models/deployment_profile.py
- skillmeat/core/models/deployment.py
- skillmeat/core/models/project.py
- skillmeat/cache/repositories/deployment_profile_repository.py
- skillmeat/api/schemas/artifacts.py
- skillmeat/api/schemas/deployment_profiles.py
- skillmeat/api/routers/deployment_profiles.py
- alembic/versions/
progress: 100
updated: '2026-02-07'
schema_version: 2
doc_type: progress
feature_slug: multi-platform-project-deployments-v1
---

# Phase 1: Data Model Foundations

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/multi-platform-project-deployments/phase-1-progress.md -t P1-T1 -s completed
```

---

## Objective

Establish the data layer for multi-platform deployments. Extend platform enums, introduce optional artifact platform targeting, and create deployment profile models with DB tables, API schemas, and project-profile associations. No business logic changes -- only data structure additions ensuring backward compatibility.

---

## Orchestration Quick Reference

**Batch 1** (Sequential - enum foundation):
- P1-T1 -> `python-backend-engineer` (0.5 pts)

**Batch 2** (Parallel - core models depend on enum):
- P1-T2 -> `python-backend-engineer` (1 pt)
- P1-T4 -> `python-backend-engineer` (1 pt)
- P1-T5 -> `python-backend-engineer` (2 pts)
- P1-T9 -> `python-backend-engineer` (1 pt)

**Batch 3** (Parallel - DB models depend on core models):
- P1-T3 -> `data-layer-expert` (1 pt)
- P1-T6 -> `data-layer-expert` (1.5 pts)
- P1-T7 -> `python-backend-engineer` (1 pt)

**Batch 4** (Parallel - relationships and repos depend on DB models):
- P1-T8 -> `python-backend-engineer` (1 pt)
- P1-T10 -> `python-backend-engineer` (1 pt)

**Batch 5** (Sequential - router depends on schema + repo):
- P1-T11 -> `python-backend-engineer` (1.5 pts)

**Batch 6** (Sequential - tests depend on everything):
- P1-T12 -> `python-backend-engineer` (1 pt)

### Task Delegation Commands

**Batch 1**:
```python
Task("python-backend-engineer", "P1-T1: Extend Platform enum. Add CODEX='codex' and GEMINI='gemini' to skillmeat/core/enums.py; mirror changes to skillmeat/web/types/enums.ts; ensure CLAUDE_CODE='claude_code' remains primary. All enum values documented in code comments. Backward-compatible (no existing values renamed).")
```

**Batch 2**:
```python
Task("python-backend-engineer", "P1-T2: Add target_platforms to Artifact model. File: skillmeat/core/artifact.py (after origin_source ~line 232). Add optional target_platforms: list[Platform] | None field. Semantics: null = deployable everywhere, non-empty list = platform-filtered. Default to None. Must be serializable to TOML.")

Task("python-backend-engineer", "P1-T4: Extend Artifact API schemas. File: skillmeat/api/schemas/artifacts.py (~line 282). Add target_platforms: list[Platform] | None = None to ArtifactRead and ArtifactCreate. OpenAPI docs auto-generate from Pydantic. Backwards compatible (field optional).")

Task("python-backend-engineer", "P1-T5: Create DeploymentProfile model (core). File: skillmeat/core/models/deployment_profile.py. Pydantic model with: profile_id, platform, root_dir, artifact_path_map, project_config_filenames, context_path_prefixes, supported_artifact_types, created_at, updated_at. Serializable to TOML. Include docstrings. Support platform extensibility.")

Task("python-backend-engineer", "P1-T9: Extend Deployment record model. File: skillmeat/core/models/deployment.py. Add deployment_profile_id (text), platform (enum), profile_root_dir (text) fields. All optional initially (Phase 2 makes required). Update DB model. Existing deployments have None values.")
```

**Batch 3**:
```python
Task("data-layer-expert", "P1-T3: Extend Artifact DB model. File: skillmeat/cache/models.py. Add target_platforms column (JSON/ARRAY based on dialect). Create Alembic migration. Backfill defaults to None. Migration runs cleanly on empty/existing DBs. No data loss on existing records.")

Task("data-layer-expert", "P1-T6: Create DeploymentProfile DB model. File: skillmeat/cache/models.py. Table: DeploymentProfile with columns: id (PK), project_id (FK), profile_id (text), platform (enum), root_dir (text), artifact_path_map (JSON), config_filenames (JSON), context_prefixes (JSON), supported_types (JSON), created_at, updated_at. Index on (project_id, profile_id) unique constraint. Create migration.")

Task("python-backend-engineer", "P1-T7: Create DeploymentProfile API schema. File: skillmeat/api/schemas/deployment_profiles.py. Create DeploymentProfileCreate, DeploymentProfileRead, DeploymentProfileUpdate. Pydantic schemas. Validate field types and enums. OpenAPI docs auto-generate. profile_id immutable in Update.")
```

**Batch 4**:
```python
Task("python-backend-engineer", "P1-T8: Extend Project model for profile associations. File: skillmeat/core/models/project.py. Add deployment_profiles: list[DeploymentProfile] relationship. Update DB Project model with FK to DeploymentProfile table. Bidirectional relationship. Cascade delete profiles if project deleted. Existing projects have empty profiles list.")

Task("python-backend-engineer", "P1-T10: Create repository for DeploymentProfile CRUD. File: skillmeat/cache/repositories/deployment_profile_repository.py. Methods: create(), read_by_id(), read_by_project_and_profile_id(), list_by_project(), update(), delete(). SQLAlchemy. All methods support transaction context.")
```

**Batch 5**:
```python
Task("python-backend-engineer", "P1-T11: Create API router for DeploymentProfile endpoints. File: skillmeat/api/routers/deployment_profiles.py. Endpoints: POST /projects/{project_id}/profiles (create), GET /projects/{project_id}/profiles (list), GET /projects/{project_id}/profiles/{profile_id} (read), PUT /projects/{project_id}/profiles/{profile_id} (update), DELETE /projects/{project_id}/profiles/{profile_id} (delete). Appropriate status codes. OpenAPI docs complete.")
```

**Batch 6**:
```python
Task("python-backend-engineer", "P1-T12: Unit tests for Phase 1 models and repos. Test: Platform enum values, Artifact target_platforms serialization, DeploymentProfile model validation, DB migrations (up/down), repository CRUD operations, API schema validation. Coverage >85% for all new code. Tests pass on clean and existing DBs.")
```

---

## Implementation Notes

### Key Decisions
- All new fields are optional for backward compatibility
- DeploymentProfile is a new table (not modifying existing tables beyond adding FKs)
- Alembic migrations use nullable=True to avoid data loss

### Known Gotchas
- JSON column type varies by SQLAlchemy dialect (SQLite vs PostgreSQL)
- Ensure enum values match exactly between Python and TypeScript
- artifact_path_map JSON must be validated against expected schema

---

## Completion Notes

_Fill in when phase is complete._
