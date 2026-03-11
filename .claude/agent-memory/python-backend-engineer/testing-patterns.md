# Testing Patterns

## SQLite + TSVECTOR Workaround for Integration Tests

`Base.metadata.create_all()` fails on SQLite when `marketplace_catalog_entries.search_vector`
uses PostgreSQL's `TSVECTOR` type. The SQLite DDL compiler raises `CompileError`.

This affects ALL tests that call `create_tables()` directly or instantiate any repository
subclass (BaseRepository.__init__ calls `create_tables()` at line 323 of repositories.py).

**Fix**: Temporarily patch the column type to `Text()` before create_all, restore after:

```python
from sqlalchemy import Text
from skillmeat.cache.models import Base, create_db_engine

def _sqlite_safe_create_tables(db_path=None):
    catalog_table = Base.metadata.tables.get("marketplace_catalog_entries")
    if catalog_table is not None:
        sv_col = catalog_table.c.get("search_vector")
        if sv_col is not None:
            original_type = sv_col.type
            sv_col.type = Text()
            try:
                engine = create_db_engine(db_path)
                Base.metadata.create_all(engine, checkfirst=True)
            finally:
                sv_col.type = original_type
            return
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine, checkfirst=True)
```

**Inject via monkeypatch** in an autouse fixture:

```python
@pytest.fixture(autouse=True)
def _patch_create_tables(monkeypatch):
    monkeypatch.setattr("skillmeat.cache.models.create_tables", _sqlite_safe_create_tables)
    monkeypatch.setattr("skillmeat.cache.repositories.create_tables", _sqlite_safe_create_tables)
```

Both patch targets are needed: `models.create_tables` (direct calls) and
`repositories.create_tables` (imported by the repositories module).

**Reference**: `tests/integration/api/test_workflow_roundtrip.py`

## DetachedInstanceError on get_artifact_by_workflow_id

`WorkflowArtifactSyncRepository.get_artifact_by_workflow_id()` closes its session in the
`finally` block before returning the `Artifact` ORM object. Accessing `artifact.artifact_metadata`
after this causes `DetachedInstanceError` (lazy load fails on detached instance).

**Fix**: Query `ArtifactMetadata` directly in a separate session when you need the metadata JSON:

```python
def _get_artifact_metadata_json(db_path, workflow_id):
    engine = create_db_engine(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        row = (
            session.query(ArtifactMetadata)
            .join(Artifact, ArtifactMetadata.artifact_id == Artifact.id)
            .filter(Artifact.type == "workflow")
            .first()
        )
        return row.metadata_json if row is not None else None
    finally:
        session.close()
```

**Reference**: `tests/integration/api/test_workflow_roundtrip.py::test_artifact_metadata_links_workflow_id`

## Workflow YAML Schema — RoleAssignment format

`stages[].roles.primary` requires a `RoleAssignment` dict with `artifact` key — NOT a plain string.

Wrong:
```yaml
roles:
  primary: skill:some-skill
```

Correct:
```yaml
roles:
  primary:
    artifact: "skill:some-skill"
```

Model: `skillmeat/core/workflow/models.py::RoleAssignment`
