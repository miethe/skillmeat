---
type: progress
prd: manage-collection-page-refactor-v1
phase: 0
phase_name: Schema & Cache Extensions
status: completed
progress: 100
tasks:
- id: SCHEMA-0.1
  name: Add deployments to ArtifactSummary schema
  status: completed
  assigned_to:
  - python-backend-engineer
  model: sonnet
  dependencies: []
  description: 'Add `deployments: Optional[List[DeploymentInfo]]` to `ArtifactSummary`
    in `user_collections.py`.

    DeploymentInfo includes `project_path`, `project_name`, `deployed_at`.

    '
  acceptance_criteria:
  - Schema updated with deployments field
  - Field is optional (backward compatible)
  - OpenAPI spec regenerated
  - SDK types updated
- id: SCHEMA-0.2
  name: Add deployments_json to CollectionArtifact cache
  status: completed
  assigned_to:
  - data-layer-expert
  model: sonnet
  dependencies: []
  description: 'Add `deployments_json` column to `CollectionArtifact` model.

    Create Alembic migration (nullable column).

    '
  acceptance_criteria:
  - Migration created and tested
  - Column is nullable for backward compat
  - Migration reversible
- id: SCHEMA-0.3
  name: Populate deployments in cache
  status: completed
  assigned_to:
  - python-backend-engineer
  model: sonnet
  dependencies:
  - SCHEMA-0.1
  - SCHEMA-0.2
  description: 'Update `populate_collection_artifact_metadata()` to store deployments
    from file-based CollectionManager.

    Update refresh-cache endpoints.

    '
  acceptance_criteria:
  - Deployments populated from metadata
  - Refresh endpoints update deployments
  - Cache miss fallback includes deployments
- id: SCHEMA-0.4
  name: Emit deployments in API responses
  status: completed
  assigned_to:
  - python-backend-engineer
  model: sonnet
  dependencies:
  - SCHEMA-0.3
  description: 'Update collection artifact endpoints to include deployments from cache.

    Ensure `/user-collections/{id}/artifacts` returns deployments.

    '
  acceptance_criteria:
  - Deployments appear in API response
  - Count matches actual deployments
  - No performance regression
- id: SCHEMA-0.5
  name: Update frontend Artifact type and mapper
  status: completed
  assigned_to:
  - frontend-developer
  model: sonnet
  dependencies:
  - SCHEMA-0.4
  description: 'Add `deployments` to frontend `Artifact` type.

    Update `entity-mapper.ts` to map deployments from API response.

    '
  acceptance_criteria:
  - TypeScript type updated
  - Mapper handles deployments
  - No type errors in build
parallelization:
  batch_1:
  - SCHEMA-0.1
  - SCHEMA-0.2
  batch_2:
  - SCHEMA-0.3
  batch_3:
  - SCHEMA-0.4
  batch_4:
  - SCHEMA-0.5
estimated_hours: 2-3
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
updated: '2026-02-02'
schema_version: 2
doc_type: progress
feature_slug: manage-collection-page-refactor-v1
---

# Phase 0: Schema & Cache Extensions

**Objective**: Extend ArtifactSummary schema and collection cache to include deployment information, enabling the "Deployed (N)" badge on browse cards.

## Quality Gate Checklist

- [ ] ArtifactSummary schema includes optional deployments field
- [ ] CollectionArtifact cache stores deployments_json
- [ ] `/user-collections/{id}/artifacts` returns deployments in response
- [ ] Frontend Artifact type includes deployments
- [ ] No migration errors, no type errors

## Output Artifacts

- Updated `skillmeat/api/schemas/user_collections.py`
- New Alembic migration for deployments_json column
- Updated `skillmeat/api/managers/collection_cache_manager.py`
- Updated `skillmeat/web/types/artifact.ts`
- Updated `skillmeat/web/lib/api/entity-mapper.ts`
- Regenerated SDK types

## Execution Log

### Batch 1: SCHEMA-0.1, SCHEMA-0.2 (parallel)
*Status: Pending*

### Batch 2: SCHEMA-0.3
*Status: Pending - awaits Batch 1*

### Batch 3: SCHEMA-0.4
*Status: Pending - awaits Batch 2*

### Batch 4: SCHEMA-0.5
*Status: Pending - awaits Batch 3*
