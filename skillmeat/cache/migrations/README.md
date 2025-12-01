# SkillMeat Cache Database Migrations

This directory contains Alembic migration scripts for the SkillMeat cache database.

## Overview

The cache database uses Alembic for schema versioning and migrations. This provides:

- **Version control** for database schema changes
- **Rollback capability** to revert problematic migrations
- **Migration history** tracking all schema changes
- **Idempotent operations** that can be safely run multiple times

## Database Location

By default, the cache database is located at:

```
~/.skillmeat/cache/cache.db
```

You can use a custom location by passing the `db_path` parameter to migration functions.

## Quick Start

### Running Migrations (Recommended)

Use the Python API for programmatic migration management:

```python
from skillmeat.cache.migrations import run_migrations

# Apply all pending migrations
run_migrations()

# Use custom database path
run_migrations("/path/to/custom/cache.db")
```

### Checking Migration Status

```python
from skillmeat.cache.migrations import get_current_revision, show_current_revision

# Get current revision ID
revision = get_current_revision()
print(f"Current revision: {revision}")

# Show detailed migration status (CLI-friendly)
show_current_revision()
```

### Rolling Back Migrations

```python
from skillmeat.cache.migrations import downgrade_migration

# Rollback one migration
downgrade_migration(revision="-1")

# Rollback to specific revision
downgrade_migration(revision="001_initial_schema")

# Rollback all migrations (WARNING: destroys all cached data)
downgrade_migration(revision="base")
```

### Viewing Migration History

```python
from skillmeat.cache.migrations import show_migration_history

# Show all migrations
show_migration_history()
```

## Migration Files

### Directory Structure

```
migrations/
├── README.md              # This file
├── alembic.ini           # Alembic configuration (minimal)
├── env.py                # Alembic environment setup
├── script.py.mako        # Migration template
├── __init__.py           # Python API functions
└── versions/             # Migration scripts
    └── 001_initial_schema.py  # Initial database schema
```

### Current Migrations

#### 001_initial_schema.py

Creates the complete initial schema:

**Tables:**
- `projects` - Project metadata and status
- `artifacts` - Artifact metadata per project
- `artifact_metadata` - Extended artifact metadata (YAML frontmatter)
- `marketplace` - Cached marketplace artifact listings
- `cache_metadata` - Cache system metadata

**Indexes:**
- 11 strategic indexes for query optimization
- Composite indexes for common query patterns

**Triggers:**
- 3 auto-update triggers for timestamp maintenance

**PRAGMA Configuration:**
- WAL mode for concurrent access
- Foreign key enforcement
- Performance optimizations (64MB cache, 256MB mmap)

## Using Alembic CLI (Alternative)

You can also use the Alembic CLI directly for advanced operations:

### Setup

First, export the database path:

```bash
export SQLALCHEMY_URL="sqlite:////path/to/cache.db"
```

### Common Commands

```bash
# Show current revision
alembic -c skillmeat/cache/migrations/alembic.ini current

# Show migration history
alembic -c skillmeat/cache/migrations/alembic.ini history

# Upgrade to latest version
alembic -c skillmeat/cache/migrations/alembic.ini upgrade head

# Downgrade one revision
alembic -c skillmeat/cache/migrations/alembic.ini downgrade -1

# Downgrade to base (remove all tables)
alembic -c skillmeat/cache/migrations/alembic.ini downgrade base
```

### Creating New Migrations

When the schema needs to change:

```bash
# Create a new migration
alembic -c skillmeat/cache/migrations/alembic.ini revision -m "Add new column"

# Create auto-generated migration (requires SQLAlchemy models)
alembic -c skillmeat/cache/migrations/alembic.ini revision --autogenerate -m "Auto migration"
```

## Development Workflow

### Adding a New Migration

1. **Create migration file:**
   ```bash
   alembic -c skillmeat/cache/migrations/alembic.ini revision -m "description"
   ```

2. **Edit the migration file:**
   - Implement `upgrade()` function
   - Implement `downgrade()` function
   - Test both directions

3. **Test the migration:**
   ```python
   from skillmeat.cache.migrations import run_migrations, downgrade_migration

   # Test upgrade
   run_migrations("/tmp/test_cache.db")

   # Test downgrade
   downgrade_migration("/tmp/test_cache.db", "-1")

   # Test re-upgrade
   run_migrations("/tmp/test_cache.db")
   ```

4. **Verify idempotency:**
   ```python
   # Running multiple times should be safe
   run_migrations("/tmp/test_cache.db")
   run_migrations("/tmp/test_cache.db")
   run_migrations("/tmp/test_cache.db")
   ```

### Migration Best Practices

1. **Always implement both upgrade and downgrade**
   - Never leave `pass` in production migrations
   - Ensure downgrade fully reverts upgrade changes

2. **Test migrations thoroughly**
   - Test on a copy of production data
   - Verify data integrity after migration
   - Test rollback scenarios

3. **Keep migrations atomic**
   - One migration = one logical change
   - Don't mix schema changes with data migrations

4. **Document complex migrations**
   - Add detailed docstrings
   - Explain the rationale for changes
   - Note any data transformations

5. **Use SQLAlchemy operations**
   - Prefer `op.create_table()` over raw SQL
   - Use `op.batch_alter_table()` for SQLite ALTER operations
   - Leverage Alembic's type system

## SQLite-Specific Considerations

### Batch Operations

SQLite has limited ALTER TABLE support. For complex alterations, use batch mode:

```python
def upgrade():
    with op.batch_alter_table("table_name") as batch_op:
        batch_op.add_column(sa.Column("new_col", sa.Text()))
        batch_op.alter_column("old_col", new_column_name="new_name")
```

### Foreign Keys

SQLite foreign key enforcement must be explicitly enabled:

```python
# This is handled automatically in env.py
connection.execute(text("PRAGMA foreign_keys = ON"))
```

### Triggers

Triggers must be dropped explicitly (not cascaded):

```python
def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trigger_name")
```

## Troubleshooting

### Migration Fails with "table already exists"

The migration was partially applied. Options:

1. **Rollback and retry:**
   ```python
   downgrade_migration(revision="base")
   run_migrations()
   ```

2. **Stamp to current version (if schema is correct):**
   ```bash
   alembic -c migrations/alembic.ini stamp head
   ```

### "Current revision" shows None

Database hasn't been initialized or alembic_version table is missing:

```python
# Initialize with migrations
run_migrations()
```

### Foreign Key Constraint Errors

Ensure foreign keys are enabled in PRAGMA settings (handled automatically in `env.py`).

### Performance Issues During Migration

For large databases:

1. Use transactions appropriately
2. Consider batch operations
3. Disable triggers temporarily if needed
4. Run VACUUM after major schema changes

## Integration with SkillMeat

The migration system integrates with the cache module:

```python
# In skillmeat/cache/__init__.py
from skillmeat.cache.migrations import run_migrations
from skillmeat.cache.schema import get_engine

# Ensure migrations are applied on first use
run_migrations()

# Then use the database
conn = get_engine()
# ... query cache ...
```

## Testing

Run the test suite:

```bash
# Run cache-specific tests
pytest tests/cache/test_migrations.py -v

# Test with coverage
pytest tests/cache/test_migrations.py --cov=skillmeat.cache.migrations
```

## Schema Version

Current schema version: **1.0.0**

The schema version is stored in the `cache_metadata` table:

```sql
SELECT value FROM cache_metadata WHERE key = 'schema_version';
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLite ALTER TABLE Limitations](https://www.sqlite.org/lang_altertable.html)
- [SkillMeat Cache Schema](../schema.py)

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Alembic documentation
3. Examine migration history: `show_migration_history()`
4. Check database integrity: `PRAGMA integrity_check;`
