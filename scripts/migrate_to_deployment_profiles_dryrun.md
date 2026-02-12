# Dry-Run Guide: `migrate_to_deployment_profiles.py`

Use dry-run mode to preview migration impact before writing to disk or database.

## Command

```bash
python scripts/migrate_to_deployment_profiles.py --dry-run --verbose
```

## What You See

- Number of discovered projects
- Per-project default profile creation (planned)
- Per-record backfill fields (planned)
- Summary totals:
  - projects scanned/migrated
  - profiles created
  - records backfilled
  - records already populated
  - failures

## Safety Properties

In dry-run mode:

- No `.skillmeat-deployed.toml` files are modified
- No `deployment_profiles` rows are created
- Existing project data is untouched

## Suggested Upgrade Flow

1. Run dry-run and inspect output.
2. Run full migration without `--dry-run`.
3. Run:
   - `pytest -q tests/test_migration_script.py`
   - `pytest -q tests/test_claude_only_regression.py`
   - `pytest -q tests/test_multi_platform_fresh_projects.py`
