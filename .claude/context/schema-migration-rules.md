# Schema and Migration Rules

Guidance for keeping Pydantic schemas, ORM models, and Alembic migrations
aligned with the codebase graph.

## Schema Changes

- Add or update Pydantic models in `skillmeat/api/schemas/`.
- Ensure handlers reference schemas via type annotations so
  `handler_uses_schema` edges are captured.
- If a schema replaces another, mark the old one as deprecated in
  `docs/architecture/codebase-graph.overrides.yaml`.

## Model and Migration Changes

- Add or update SQLAlchemy models in `skillmeat/cache/models.py` with
  `__tablename__` defined.
- For new tables, add Alembic migrations in
  `skillmeat/cache/migrations/versions/` using `create_table()` so
  `model_migrated_by` edges can be derived.

## Graph Checks

- Run `python -m scripts.code_map.extract_backend` to refresh backend nodes.
- Run `python -m scripts.code_map.merge_graphs` and
  `python -m scripts.code_map.apply_overrides` before validation.
- Run `python -m scripts.code_map.validate_graph` to ensure OpenAPI endpoints
  have handlers and schemas are referenced.
