# CLAUDE.md - cache

Scope: DB cache models, repositories, refresh/sync in `skillmeat/cache/`.

## Invariants

- DB cache is the web runtime source for listable data.
- Preserve write-through + refresh semantics between filesystem and DB.
- Schema/migration changes require compatibility checks.

## Enterprise Repository Architecture

- **Local repos** (`repositories.py`): SQLAlchemy 1.x `session.query()` style, accept `db_path`, use SQLite.
- **Enterprise repos** (`enterprise_repositories.py`): SQLAlchemy 2.x `select()` style, accept `Session` via FastAPI DI, use PostgreSQL.
- This divergence is **intentional** — do not "fix" local repos to use 2.x style or enterprise repos to use 1.x style. They serve different backends with different lifecycles.
- `RepositoryFactory` (`repository_factory.py`) routes between them based on `SKILLMEAT_EDITION` env var (`"local"` or `"enterprise"`).
- Enterprise PKs are `UUID` (not `int`) — all method signatures use `uuid.UUID` for entity IDs.

## Read When

- Cache/write-through model: `.claude/context/key-context/data-flow-patterns.md`
- FE/BE consistency work: `.claude/context/key-context/fe-be-type-sync-playbook.md`
- Enterprise testing gotchas: `skillmeat/cache/tests/CLAUDE.md`
