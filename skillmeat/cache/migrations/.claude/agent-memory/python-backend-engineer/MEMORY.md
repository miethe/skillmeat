# Python Backend Engineer Memory

## Testing Patterns

### Alembic Migration Bypass for Unit Tests
- `CompositeMembershipRepository.__init__` calls `run_migrations` (imported locally as
  `from skillmeat.cache.migrations import run_migrations`) then `create_tables`.
- Running full Alembic migrations against an empty test DB fails because intermediate
  migrations try to `ADD COLUMN` to tables that don't exist yet in the migration chain.
- Fix: patch `"skillmeat.cache.migrations.run_migrations"` (source module, not the
  calling module — import is local so caller module attribute doesn't exist).
- After patching out migrations, `create_tables` (`Base.metadata.create_all`) creates
  all ORM-declared tables, which is sufficient for unit tests.

### SQLAlchemy Identity Map and Duplicate PK Tests
- Testing a composite PK UNIQUE constraint with the same session raises
  `SAWarning` (identity map conflict) instead of `IntegrityError`.
- Fix: use a fresh `sessionmaker` session per insert so the identity map is separate
  for each attempt. The DB-level constraint then fires correctly on the second insert.

### Coverage Command
- Use dotted module paths with `--cov`: `--cov=skillmeat.cache.composite_repository`
- File paths (`skillmeat/cache/composite_repository`) produce "never imported" warnings.

### SQLAlchemy Cascade Delete via Non-PK FK Column
- `CompositeMembership.child_artifact_uuid` references `artifacts.uuid` (unique, not PK).
- SQLAlchemy ORM `session.delete(artifact)` raises `AssertionError: Dependency rule tried
  to blank-out primary key column 'composite_memberships.child_artifact_uuid'` because the
  ORM cascade tries to null-out the FK column before delete, but it's part of the composite PK.
- Fix: use raw SQL `session.execute(text("DELETE FROM artifacts WHERE id = :aid"), {"aid": ...})`
  to let SQLite's native `ON DELETE CASCADE` handle it instead.
- Also: capture string attribute values (e.g. `artifact.uuid`) into local variables BEFORE
  the raw SQL delete. After `session.commit()` the ORM instance is expired; accessing
  attributes raises `ObjectDeletedError`.

### Alembic Migration Round-Trip Tests with create_tables
- `create_tables()` calls `Base.metadata.create_all()` which creates ALL ORM tables,
  including composite tables. If you then try to stamp at `20260218_1000` and run
  `upgrade("head")` the composite tables migration fails: `table composite_artifacts already exists`.
- Fix: after `create_tables()`, manually drop the composite tables (`DROP TABLE IF EXISTS
  composite_memberships; DROP TABLE IF EXISTS composite_artifacts`), then stamp. The upgrade
  will then re-create them cleanly.
- Pattern: `create_tables(db_path)` → drop composite tables → `command.stamp(cfg, "prev_rev")` →
  `run_migrations(db_path)` → verify tables present.

### FK PRAGMA and SQLAlchemy Event Listeners
- SQLite foreign key enforcement requires `PRAGMA foreign_keys=ON` per connection.
- Use `@sa_event.listens_for(engine, "connect")` to set it on every connection created
  by the engine. This is the canonical way; setting it in one session doesn't affect others.

## Key File Paths

- `skillmeat/cache/composite_repository.py` — `CompositeMembershipRepository` CRUD
- `skillmeat/core/services/composite_service.py` — `CompositeService` (type:name → UUID)
- `skillmeat/cache/models.py` — `Artifact` (uuid col), `CompositeArtifact`, `CompositeMembership`
- `tests/test_composite_memberships.py` — unit tests (31 tests, 92.7% coverage)
- `tests/integration/test_composite_memberships_integration.py` — integration tests (17 tests)
