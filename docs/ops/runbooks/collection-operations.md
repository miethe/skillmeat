# Collection Operations Runbook

Operational guide for managing SkillMeat collections, including the default collection system and artifact migrations.

## Table of Contents

- [Overview](#overview)
- [Default Collection System](#default-collection-system)
- [Artifact Migration](#artifact-migration)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Overview

SkillMeat uses a dual-layer collection system:

1. **File-system collections** - Physical artifact storage in `~/.skillmeat/collections/`
2. **Database collections** - Organizational metadata enabling Groups and other features

The **default collection** bridges these layers, ensuring all artifacts can use advanced features like Groups.

### Key Components

- **Default Collection** - Auto-created collection (`id: "default"`) that all artifacts belong to
- **CollectionArtifact** - Database association between collections and artifacts
- **Groups** - Organizational feature requiring valid `collection_id`

## Default Collection System

### How It Works

1. **Server Startup**: The API server automatically:
   - Creates the "default" collection if it doesn't exist
   - Migrates any artifacts not yet in the default collection

2. **New Artifacts**: When creating artifacts without specifying a collection:
   - Artifacts are automatically assigned to the "default" collection
   - This enables immediate access to Groups and collection features

3. **Frontend Default**: The web UI defaults to showing the "default" collection view

### Configuration

The default collection uses fixed identifiers:

```python
DEFAULT_COLLECTION_ID = "default"
DEFAULT_COLLECTION_NAME = "Default Collection"
```

These are defined in `skillmeat/cache/models.py`.

## Artifact Migration

### Automatic Migration (Server Startup)

Migration runs automatically on every server startup:

```
INFO: Artifact migration: 42 migrated, 5 already present, 47 total
```

This is **idempotent** - running multiple times will not create duplicate entries.

### Manual Migration (API Endpoint)

Trigger migration without restarting the server:

```bash
# Using curl
curl -X POST http://localhost:8080/api/v1/user-collections/migrate-to-default

# Response
{
  "success": true,
  "message": "Migrated 42 artifacts to default collection",
  "migrated_count": 42,
  "already_present_count": 5,
  "total_artifacts": 47
}
```

### When to Run Manual Migration

- After bulk importing artifacts via CLI
- After restoring from backup
- After database reset/recreation
- When artifacts appear in "All Collections" but can't be added to Groups

### Migration Process Details

The migration function:

1. Ensures default collection exists in database
2. Scans all file-system collections via `CollectionManager`
3. Lists all artifacts from each collection
4. Creates artifact IDs in format `"{type}:{name}"` (e.g., `"skill:my-skill"`)
5. Queries existing `CollectionArtifact` entries for default collection
6. Adds missing entries (artifacts not yet associated)
7. Commits transaction and returns statistics

## Common Tasks

### Check Default Collection Status

```bash
# Via API
curl http://localhost:8080/api/v1/user-collections | jq '.items[] | select(.id == "default")'

# Expected output
{
  "id": "default",
  "name": "Default Collection",
  "description": "Default collection for all artifacts...",
  "artifact_count": 47,
  ...
}
```

### Verify Artifact Collection Membership

```bash
# List artifacts in default collection
curl "http://localhost:8080/api/v1/user-collections/default/artifacts?limit=100"
```

### Check for Orphaned Artifacts

Artifacts visible in "All Collections" view but not in default collection:

```bash
# Get all artifacts count
ALL_COUNT=$(curl -s "http://localhost:8080/api/v1/artifacts?limit=1" | jq '.page_info.total_count')

# Get default collection artifact count
DEFAULT_COUNT=$(curl -s "http://localhost:8080/api/v1/user-collections/default" | jq '.artifact_count')

echo "All artifacts: $ALL_COUNT, In default collection: $DEFAULT_COUNT"

# If counts differ, run migration
if [ "$ALL_COUNT" != "$DEFAULT_COUNT" ]; then
  curl -X POST http://localhost:8080/api/v1/user-collections/migrate-to-default
fi
```

### Force Recreation of Default Collection

In rare cases where the default collection is corrupted:

```bash
# 1. Delete existing default collection (caution: removes group associations)
curl -X DELETE http://localhost:8080/api/v1/user-collections/default

# 2. Restart server to recreate and migrate
skillmeat web dev --api-only

# Or trigger via API (creates collection if missing)
curl -X POST http://localhost:8080/api/v1/user-collections/migrate-to-default
```

## Troubleshooting

### "Artifacts can't be added to Groups"

**Symptom**: Artifacts visible in collection but "Add to Group" fails with collection_id error.

**Cause**: Artifact not in database collection (only in file-system).

**Fix**:
```bash
curl -X POST http://localhost:8080/api/v1/user-collections/migrate-to-default
```

### "Default collection not found"

**Symptom**: API returns 404 for default collection.

**Cause**: Database may have been reset or collection deleted.

**Fix**: Restart API server or call migration endpoint (creates collection if missing).

### Migration Shows 0 Artifacts

**Symptom**: `"total_artifacts": 0` in migration response.

**Possible Causes**:
1. No file-system collections exist
2. Collections directory is empty or misconfigured

**Debug**:
```bash
# Check collections directory
ls -la ~/.skillmeat/collections/

# List collections via API
curl http://localhost:8080/api/v1/collections
```

### Duplicate Collection Entries

**Symptom**: Same artifact appears multiple times.

**Note**: The migration is idempotent and uses a composite primary key (`collection_id`, `artifact_id`), so true duplicates are impossible. If you see duplicates in the UI, check:

1. Artifact exists in multiple file-system collections with same name
2. UI is showing artifacts from multiple collections

### Server Startup Fails with Migration Error

**Symptom**: Server won't start, logs show migration error.

**Cause**: Database connection issue or schema mismatch.

**Fix**:
```bash
# Check database file
ls -la ~/.skillmeat/cache/skillmeat.db

# If corrupted, backup and recreate
mv ~/.skillmeat/cache/skillmeat.db ~/.skillmeat/cache/skillmeat.db.bak
skillmeat web dev --api-only  # Will recreate database
```

## Related Documentation

- [Groups Feature Guide](../../user/groups-guide.md) - User guide for Groups
- [Collections Architecture](../../architecture/collections.md) - Technical design
- [API Reference](../../api/user-collections.md) - API endpoint documentation
