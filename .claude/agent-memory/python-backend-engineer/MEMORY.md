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

### Composite Import DB Population Pattern
- `ArtifactManager.show()` does NOT handle `composite` type — calling it for a composite entry returns None/fails
- `create_or_update_collection_artifact()` requires an `Artifact` row to exist; `_ensure_artifact_row()` creates it if absent
- `_ensure_artifacts_in_cache()` in `user_collections.py` only lists filesystem types (skill/command/agent/etc.) — composites are never listed there
- Fix: in `populate_collection_artifact_from_import()`, composite branch skips `artifact_mgr.show()`, calls `_ensure_artifact_row()` + `_upsert_composite_artifact_row()` first
- `_COLLECTION_ARTIFACTS_PROJECT_ID = "collection_artifacts_global"` sentinel must match user_collections.py constant
- Child artifacts of a composite are found via catalog path prefix: `child.path.startswith(composite_path + "/")`
- `_import_composite_children()` in `marketplace_sources.py` handles auto-importing children after composite import
- Files: `skillmeat/api/services/artifact_cache_service.py`, `skillmeat/api/routers/marketplace_sources.py`

### validate_source_id — Underscores Not Allowed
- `validate_source_id()` in `marketplace_sources.py` rejects underscores: pattern is `^[a-zA-Z0-9\-]+$`
- API tests using `src_test_123` will get 400; use `src-test-abc` style instead
- Pre-existing tests in `TestGetFileContent` use `src_test_123` and fail with 400 — pre-existing issue

### Embedded Artifacts in Heuristic Detector (P1-T4)
- `_embedded_by_skill` dict on `HeuristicDetector` instance captures single-file artifacts inside Skill dirs
- `matches_to_artifacts()` only attaches embedded children when `artifact_type == "skill"` (not composite)
- When a Skill dir has BOTH commands/ AND agents/, detector promotes it to `composite` — embedded_artifacts stays empty for composites
- Directory-based child Skills (with own SKILL.md inside a parent Skill dir) surface as top-level; MAX_EMBED_DEPTH only guards recursive attachment depth
- Test file: `tests/core/marketplace/test_heuristic_detector.py` → `TestEmbeddedArtifactHandling`

### File Serving Endpoint Defensive Path Resolution (P2-T1)
- Endpoint: `GET /{source_id}/artifacts/{artifact_path:path}/files/{file_path:path}` in `marketplace_sources.py`
- Three cases: (1) artifact_path ends with file_path → use artifact_path; (2) artifact_path ends with known extension → defensive fallback, use artifact_path, log debug; (3) directory → concatenate
- File extension list: `.md .py .yaml .yml .json .toml .txt .sh .ts .tsx .jsx .js .css`
- Test file: `tests/api/test_marketplace_sources.py` → `TestFileServingPathResolution`
