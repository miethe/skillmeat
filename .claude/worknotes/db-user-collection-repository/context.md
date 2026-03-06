---
type: context
schema_version: 2
doc_type: context
prd: db-user-collection-repository
feature_slug: db-user-collection-repository
created: 2026-03-05
updated: '2026-03-05'
---

# Context: DB User Collection Repository Migration

## Origin

Captured as REQ-20260305-skillmeat-01 during Phase 4 of repo-pattern-gap-closure.
TASK-4.1 (user_collections.py migration) was marked "completed" with TODO annotations
rather than full migration, because the existing ICollectionRepository targets filesystem
and is incompatible with the DB-backed Collection/CollectionArtifact models.

## Architecture Decision

- **New ABCs needed**: `IDbUserCollectionRepository` + `IDbCollectionArtifactRepository`
- **Why not extend ICollectionRepository**: Filesystem vs DB are fundamentally different domains
- **Concrete impl location**: `cache/repositories.py` (DB-backed), NOT `core/repositories/` (filesystem)
- **Reference pattern**: LocalGroupRepository — transactional, DTO-returning, try/finally session lifecycle

## Key Files

| File | Role |
|------|------|
| `skillmeat/core/interfaces/repositories.py` | ABC definitions |
| `skillmeat/core/interfaces/dtos.py` | DTO definitions |
| `skillmeat/cache/repositories.py` | Concrete DB-backed implementations |
| `skillmeat/api/dependencies.py` | DI factories and typed aliases |
| `skillmeat/api/routers/user_collections.py` | Router to migrate (3,195 lines, ~110 session calls) |
| `skillmeat/core/repositories/local_group.py` | Reference implementation pattern |
| `tests/mocks/repositories.py` | Mock implementations for tests |

## ORM Models

- `Collection` (cache/models.py ~line 774): id, name, description, created_by, collection_type, context_category, timestamps, relationships to groups/collection_artifacts/templates
- `CollectionArtifact` (cache/models.py ~line 1104): composite PK (collection_id + artifact_uuid), metadata fields, fingerprints, source tracking, JSON fields (tags_json, tools_json, deployments_json)

## Existing TODOs in user_collections.py

Lines 80-89 contain header TODO block. Per-function TODOs on:
- `ensure_default_collection()` → needs `IDbUserCollectionRepository.ensure_default()`
- `_ensure_collection_project_sentinel()` → needs `IDbProjectRepository.ensure_sentinel()`
- `_ensure_artifacts_in_cache()` → needs `IArtifactRepository.list_ids()` + `create_batch()`
- `migrate_artifacts_to_default_collection()` → needs both new repos
- `_sync_all_tags_to_orm()` → needs `IDbCollectionArtifactRepository.list_with_tags()`
- `populate_collection_artifact_metadata()` → needs `IDbCollectionArtifactRepository.upsert_metadata()`
- `_refresh_single_collection_cache()` → needs `IDbCollectionArtifactRepository` methods
- `list_user_collections()` → needs `IDbUserCollectionRepository.list()`

## Blockers / Risks

- Large scope (110 session calls) mitigated by phased approach
- Complex joins in list_collection_artifacts() — extract and test independently
- JSON field parsing (tags_json, tools_json, deployments_json) — handle nulls gracefully
