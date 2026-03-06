# CLAUDE.md - cache/tests

Scope: Tests for `skillmeat/cache/` — repositories, enterprise repos, refresh, workflow.

## Enterprise Repository Testing

### Test strategy by layer

| Layer | Approach | Rationale |
|-------|----------|-----------|
| Unit tests | `MagicMock(spec=Session)` | Fully isolated, no SQLite compat issues, tests all logic paths |
| Integration tests | Real PostgreSQL via docker-compose | Required for JSONB operators, UUID types, constraint enforcement |

**Do not use SQLite in-memory for enterprise repo unit tests** unless you also apply the comparator cache fix (see below). Mock-based tests are safer and faster for unit-level coverage.

### SQLAlchemy comparator cache poisoning (critical gotcha)

Enterprise models use PostgreSQL-specific types (`JSONB`, `UUID(as_uuid=True)`). When tests patch these column types for SQLite compatibility (e.g., replacing `UUID` with a `_UUIDString` TypeDecorator), SQLAlchemy's ORM comparator cache retains the **original** types.

**The mechanism:**
1. `configure_mappers()` runs (triggered by any ORM model instantiation) and snapshots each column's `type` into `InstrumentedAttribute.comparator.__dict__['type']`.
2. A test fixture patches `column.type = _UUIDString()` on the Table object.
3. The comparator still holds stale `UUID(as_uuid=True)`.
4. `INSERT` uses the Table column's type (patched, correct — stores `"aaa-bbb-ccc"` with hyphens).
5. `WHERE col = ?` uses the comparator's type (stale, wrong — binds `"aaabbbccc"` without hyphens).
6. String comparison fails silently — queries return zero rows with no error.

**Required fix when patching column types for SQLite:**
After patching Table columns, propagate to comparator caches:

```python
from sqlalchemy import inspect as sa_inspect

for model_cls in [EnterpriseArtifact, EnterpriseArtifactVersion, ...]:
    mapper = sa_inspect(model_cls)
    for col_name, mapped_col in mapper.columns.items():
        attr = getattr(model_cls, col_name, None)
        if attr is not None and hasattr(attr, "comparator"):
            comparator = attr.comparator
            if "type" in comparator.__dict__:
                comparator.__dict__["type"] = mapped_col.type
```

This fix is implemented in `test_enterprise_collection_repository.py::_patch_enterprise_metadata_for_sqlite()`.

**Cross-module trigger:** This bug only manifests when another test module imports enterprise models before the SQLite patch runs (e.g., mock-based artifact tests run first, triggering `configure_mappers()`). Tests pass in isolation but fail when run together.

### JSONB operators require PostgreSQL

`search_by_tags()` uses the `@>` JSONB containment operator, which SQLite does not support. Tag search tests must be marked `@pytest.mark.integration` and run against real PostgreSQL (ENT-2.13).

## Read When

- Enterprise repo architecture: `skillmeat/cache/CLAUDE.md`
- Data flow patterns: `.claude/context/key-context/data-flow-patterns.md`
