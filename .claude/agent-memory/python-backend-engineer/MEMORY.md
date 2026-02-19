# Python Backend Engineer Memory

## Project: SkillMeat

### Join Table FK Migration (CAI-P5)
- `CollectionArtifact`, `GroupArtifact`, `ArtifactTag` all use `artifact_uuid` (not `artifact_id`) as FK
- FK references `artifacts.uuid` (stable ADR-007 identity), NOT `artifacts.id` (mutable type:name string)
- External DTOs still use `type:name` format — resolve via join: `Artifact.id.in_(ids)` + join on `artifact_uuid == Artifact.uuid`
- See: `skillmeat/cache/models.py` lines 983-1270, fix in `skillmeat/api/routers/artifacts.py` ~line 2255

### Pre-existing Test Failures (not our concern)
- `tests/test_claude_marketplace.py` — ModuleNotFoundError: `skillman`
- `tests/test_duplicate_detection.py` — ImportError: `ArtifactMetadata` from `skillmeat.utils.metadata`
- `tests/test_search_projects.py` — same ImportError
- `tests/unit/api/test_perform_scan_clone_integration.py` — ImportError: `_convert_manifest_to_search_metadata`
- Several `tests/api/` tests fail due to fixture/mock issues — pre-existing

### Key File Locations
- Models: `skillmeat/cache/models.py`
- Repositories: `skillmeat/cache/repositories.py`
- Refresh logic: `skillmeat/cache/refresh.py`
- API routers: `skillmeat/api/routers/`
- Tag write service: `skillmeat/core/services/tag_write_service.py`

### Query Pattern for UUID-keyed Join Tables
```python
# Wrong (artifact_id column does not exist on join tables):
session.query(CollectionArtifact.artifact_id, ...).filter(CollectionArtifact.artifact_id.in_(ids))

# Correct (join through Artifact to resolve type:name → uuid):
session.query(Artifact.id, CollectionArtifact.source, ...)
    .join(CollectionArtifact, CollectionArtifact.artifact_uuid == Artifact.uuid)
    .filter(Artifact.id.in_(ids))
```

### Cascade Delete Testing (SQLAlchemy + SQLite)
- Use `session.execute(sa.delete(Artifact).where(...))` NOT `session.delete(artifact)` for cascade tests
- ORM unit-of-work nulls FK before DELETE; since artifact_uuid is also a PK on join tables this raises IntegrityError
- Raw SQL bypasses ORM bookkeeping and lets SQLite ON DELETE CASCADE fire as intended
- Requires `PRAGMA foreign_keys=ON` on each connection (use `@event.listens_for(engine, "connect")`)

### Alembic Migration File Imports
- Migration files start with digits (e.g. `20260219_1000_...`) — cannot use normal `import`
- Load via: `importlib.util.spec_from_file_location(name, path)` + `spec.loader.exec_module(module)`
- Use `patch("alembic.op", "get_bind", return_value=conn)` to inject test connection into migration functions

### CollectionArtifactsResponse Schema
- Endpoint `/api/v1/user-collections/{id}/artifacts` returns `{items: [...], page_info: {...}}`
- Key is `items` not `artifacts` — use `data.get("items", [])` in tests
- To use DB cache path (not filesystem fallback), set `CollectionArtifact.synced_at` to non-null

### TagService Session Isolation
- `TagService()` calls `get_session()` internally — not injectable via endpoint dependency override
- For test isolation: `patch.object(TagService, "list_tags", return_value=mock_response)` or mock at TagRepository level

### Migration Safety Guard (FK migrations that JOIN artifacts)
- Any migration that JOINs artifacts to resolve type:name→uuid MUST call `ensure_artifacts_populated()` first
- Located in `skillmeat/cache/migrations/env.py` — import: `from skillmeat.cache.migrations.env import ensure_artifacts_populated`
- Raises `RuntimeError` if `artifacts` count == 0; logs WARNING if count < 10
- Uses `op.get_bind()` to get the live migration connection (no separate session needed)
- Pattern: empty artifacts table causes JOIN to silently produce zero rows → data loss in association tables
