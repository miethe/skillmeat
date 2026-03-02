# Python Backend Engineer Memory

## Project: SkillMeat

### Join Table FK Migration (CAI-P5)
- `CollectionArtifact`, `GroupArtifact`, `ArtifactTag` all use `artifact_uuid` (not `artifact_id`) as FK
- FK references `artifacts.uuid` (stable ADR-007 identity), NOT `artifacts.id` (mutable type:name string)
- External DTOs still use `type:name` format — resolve via join: `Artifact.id.in_(ids)` + join on `artifact_uuid == Artifact.uuid`
- See: `skillmeat/cache/models.py` lines 983-1270, fix in `skillmeat/api/routers/artifacts.py` ~line 2255

### CLI Deploy/Undeploy Non-TTY Patterns
- Deploy outputs JSON in non-TTY (CliRunner); assert `"test-skill" in result.output` and `"success" in result.output` instead of `"Deployed" in result.output`
- `undeploy` command requires `--force` in non-TTY mode (exit 2 otherwise); all test invocations must pass `--force`
- Deploy with already-deployed artifact in non-TTY: prompts for overwrite (EOFError) — pass `--overwrite` to skip
- Deploy nonexistent artifact: returns exit 0 with `{"deployments": []}` — check empty deployments, not exit 1
- Bug fixed: `DeploymentManager.undeploy()` called `artifact_type.value` when `artifact_type=None` — fixed via `find_deployment_by_name()` in `DeploymentTracker`
- New method: `DeploymentTracker.find_deployment_by_name()` in `skillmeat/storage/deployment.py` — searches all types by name only

### CLI add Command Bug (FIXED)
- `_format_artifact_output` in `skillmeat/cli/__init__.py` used `artifact.artifact_type.value` — wrong attribute name
- `Artifact` dataclass (in `skillmeat/core/artifact.py`) uses `artifact.type` (not `artifact_type`)
- Fix: changed both lines in `_format_artifact_output` to use `artifact.type.value`
- GitHub test mocks in `tests/cli/test_add.py` must return `FetchResult` (not a tuple); import from `skillmeat.sources.base`
- GitHub test mock `side_effect` receives `(spec, artifact_type)` — NOT `(self, spec, artifact_type)` — mock strips `self`
- Correct import for `ArtifactMetadata` in tests: `from skillmeat.core.artifact import ArtifactMetadata`

### Pre-existing Test Failures (not our concern)
- `tests/test_claude_marketplace.py` — ModuleNotFoundError: `skillman`
- `tests/test_duplicate_detection.py` — ImportError: `ArtifactMetadata` from `skillmeat.utils.metadata`
- `tests/test_search_projects.py` — same ImportError
- `tests/unit/api/test_perform_scan_clone_integration.py` — ImportError: `_convert_manifest_to_search_metadata`
- `tests/cli/test_add.py` — failures: `'Artifact' object has no attribute 'artifact_type'` (production bug) + github tests
- `tests/cli/test_list_show_remove.py` — remove/show failures: `--force` required in non-TTY (same pattern as undeploy)
- `tests/cli/test_deploy.py` — FIXED (was 10 failures, now 0)
- `tests/cli/test_collection_refresh.py::TestFieldsOption::test_fields_option_multiple_fields` — pre-existing
- Several `tests/api/` tests fail due to fixture/mock issues — pre-existing

### CLI Test Isolation Pattern
- `ConfigManager.DEFAULT_CONFIG_DIR` is a class variable evaluated at import time (caches `Path.home()`)
- `monkeypatch.setenv("HOME", ...)` alone does NOT fix it — must also patch the class attr
- Fix: `monkeypatch.setattr(ConfigManager, "DEFAULT_CONFIG_DIR", home_dir / ".skillmeat")`
- Applied to both `isolated_cli_runner` and `temp_home` fixtures in `tests/conftest.py`
- Also patch Rich console: `monkeypatch.setattr(cli_module, "console", Console(no_color=True, highlight=False))`
  to prevent ANSI codes from breaking `"text in result.output"` assertions
- `Console(force_terminal=True)` in `skillmeat/cli/__init__.py` line 40 ignores NO_COLOR env var

### CLI JSON Output Format (SmartDefaults)
- `SmartDefaults.detect_output_format()` returns `"json"` when `sys.stdout.isatty()` is False
- CliRunner is non-TTY, so ALL CLI tests using output assertions must account for JSON format
- `config list` in JSON mode: `{"status":"success","config":{...}}` — NOT "Configuration" table title
- `config get nonexistent` in JSON mode: `{"status":"success","key":"nonexistent","value":null}` — NOT "not set"
- Test assertions should check for key strings present in JSON instead of human-readable table text

### Alembic + create_tables() Race Condition
- `CacheRepository.__init__` calls `create_tables()` (Base.metadata.create_all) WITHOUT running Alembic
- This creates all ORM tables but does NOT create `alembic_version` table
- Later `CacheManager.initialize_cache()` → `run_migrations()` → Alembic sees no revision → tries to run `001_initial_schema` → FAILS with "table projects already exists"
- Fix: `CacheManager._stamp_untracked_db_if_needed()` — detects `projects` table + no `alembic_version` → stamps DB at head via `alembic command.stamp`
- In `skillmeat/cache/manager.py` — called in `initialize_cache()` before `run_migrations()`

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

### WorkflowService / WorkflowExecutionService Session Global (get_session)
- `get_session(db_path)` in `models.py` only calls `init_session_factory()` when module-level `SessionLocal is None`
- Between tests using different `tmp_path` db files, `SessionLocal` retains the first test's engine → FK violations on the second test
- Fix: reset `SessionLocal = None` before each test via `autouse=True` fixture
- `WorkflowExecutionService` (uses `get_session`) does NOT call `create_tables` — tables only exist if `WorkflowService` (BaseRepository) was instantiated first
- Fix: always instantiate `WorkflowService(db_path=...)` before `WorkflowExecutionService` in tests to ensure tables are created
- `plan.workflow_id` = SWDL `workflow.id` field (kebab-case string from YAML), NOT the DB UUID primary key (`workflow.id` from DTO)
- Test file: `tests/test_workflow_e2e.py`

### Alembic Migration Table Existence Checks
- When migrations create new tables (via `op.create_table()`), failure occurs if tables already exist (e.g., from `Base.metadata.create_all()`)
- Solution: Use `sqlalchemy.inspect()` to check table existence before creating:
  ```python
  from sqlalchemy import inspect as sa_inspect
  bind = op.get_bind()
  inspector = sa_inspect(bind)
  existing_tables = inspector.get_table_names()
  if "table_name" not in existing_tables:
      op.create_table(...)
  ```
- Same check needed for indexes (`if "table_name" not in existing_tables:` before `op.create_index(...)`)
- Makes migrations idempotent and safe on DBs pre-populated via ORM
- Applied to: `20260224_1000_add_deployment_set_tables.py`
