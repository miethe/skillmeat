---
title: "Multi-Platform Deployment Upgrade Guide"
description: "Upgrade legacy Claude-only projects to profile-aware multi-platform deployments with zero workflow breakage."
created: 2026-02-09
updated: 2026-02-09
status: published
priority: high
audience: users,developers
category: migration
tags:
  - migration
  - deployment
  - profiles
  - claude
  - codex
  - gemini
  - cursor
---

# Multi-Platform Deployment Upgrade Guide

This guide covers upgrading to profile-aware deployments while keeping existing Claude-only workflows unchanged.

## What Changed

SkillMeat now supports per-project deployment profiles for multiple platforms:

- `claude_code` (`.claude`)
- `codex` (`.codex`)
- `gemini` (`.gemini`)
- `cursor` (`.cursor`)

Deployments can now carry profile metadata:

- `deployment_profile_id`
- `platform`
- `profile_root_dir`

## What Stays the Same

If you keep using default commands (no `--profile` flag):

- Claude-only projects continue to work
- Existing deployment files are still read
- Legacy deployment records remain valid

## Run Migration

Use the migration script to add profile metadata and create default profiles for legacy projects:

```bash
python scripts/migrate_to_deployment_profiles.py
```

Preview without writing changes:

```bash
python scripts/migrate_to_deployment_profiles.py --dry-run --verbose
```

Use a custom cache DB path:

```bash
python scripts/migrate_to_deployment_profiles.py --db-path /path/to/cache.db
```

## Verify Upgrade

1. Run regression tests for Claude-only compatibility:

```bash
pytest -q tests/test_claude_only_regression.py
```

2. Run migration tests:

```bash
pytest -q tests/test_migration_script.py
```

3. Run fresh-project profile verification tests:

```bash
pytest -q tests/test_multi_platform_fresh_projects.py
```

## Opt In to Multi-Platform Workflows

Initialize project profiles:

```bash
skillmeat init --all-profiles --project-path /path/to/project
```

Deploy to a specific profile:

```bash
skillmeat deploy my-artifact --profile codex --project /path/to/project
```

Deploy to all configured profiles:

```bash
skillmeat deploy my-artifact --all-profiles --project /path/to/project
```

Check status for one profile:

```bash
skillmeat status --profile codex --project /path/to/project
```

Deploy context entities to a selected profile:

```bash
skillmeat context deploy my-entity --to-project /path/to/project --profile gemini
```

## Known Limitations

- Symlink-heavy profile roots can produce confusing file paths if external tools rewrite links during deployment.
- Legacy records without profile fields are inferred from profile root context (defaults to `.claude` if ambiguous).
- If cache DB project rows are missing, the migration script creates minimal project records for profile ownership.

## Troubleshooting

### Migration reports zero projects

Cause: no `.skillmeat-deployed.toml` files were discovered in default search locations.

Fix:

```bash
python scripts/migrate_to_deployment_profiles.py --search-path /absolute/path/to/workspace
```

### Deployment records not updated

Cause: records already had profile metadata, or deployment files are malformed.

Fix:

- Re-run with `--verbose` and inspect per-project output.
- Validate each deployment file is valid TOML and contains a `[[deployed]]` array.

### Unexpected profile/platform mapping

Cause: custom profile roots that are not one of `.claude/.codex/.gemini/.cursor` map to `platform=other`.

Fix:

- Keep custom profile IDs for `deployment_profile_id`.
- Update profile metadata in cache if you want a specific platform label.

## Rollback

The migration only writes profile metadata and default profile rows. It does not delete artifacts.

If needed, restore deployment tracker files from git/history backups and remove created profile rows from the cache DB.
