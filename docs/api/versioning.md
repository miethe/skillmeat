---
title: Versioning & Merge System API
description: Complete API reference for SkillMeat's version management, snapshots, and merge operations with change attribution
audience: developers
tags: [api, versioning, merge, snapshots, change-attribution]
created: 2025-12-18
updated: 2025-12-18
category: API Documentation
status: published
related: [syncing-changes.md]
---

# Versioning & Merge System API Documentation

Complete API reference for SkillMeat's version management endpoints including snapshots, rollbacks, and merge operations with full change attribution tracking.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Snapshot Management](#snapshot-management)
  - [POST /api/v1/versions/snapshots](#post-apiv1versionssnapshots)
  - [GET /api/v1/versions/snapshots](#get-apiv1versionssnapshots)
  - [GET /api/v1/versions/snapshots/{snapshot_id}](#get-apiv1versionssnapshottssnapshot_id)
- [Rollback Operations](#rollback-operations)
  - [POST /api/v1/versions/rollback](#post-apiv1versionsrollback)
  - [POST /api/v1/versions/rollback/analyze](#post-apiv1versionsrollbackanalyze)
- [Version Comparison](#version-comparison)
  - [POST /api/v1/versions/diff](#post-apiv1versionsdiff)
- [Merge Operations](#merge-operations)
  - [POST /api/v1/merge/analyze](#post-apiv1mergeanalyze)
  - [POST /api/v1/merge/preview](#post-apiv1mergepreview)
  - [POST /api/v1/merge/execute](#post-apiv1mergeexecute)
  - [POST /api/v1/merge/resolve](#post-apiv1mergeresolve)
- [Data Models](#data-models)
- [Change Attribution](#change-attribution)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The Versioning & Merge System API provides endpoints for:

- **Snapshot Management**: Create, list, and retrieve collection snapshots
- **Rollback Operations**: Safely rollback to previous versions with safety analysis
- **Version Comparison**: Compare different versions of artifacts
- **Merge Operations**: Perform three-way merges with conflict detection
- **Change Attribution**: Track origin of changes (upstream, local, conflicting)
- **Baseline Tracking**: Proper baseline storage for accurate three-way merges

### Key Features

- **Version Lineage**: Complete version history graph with parent-child relationships
- **Change Origin Tracking**: Distinguish upstream, local, and conflicting changes
- **Correct Baseline Storage**: Three-way merge using proper merge base (not empty)
- **Conflict Detection**: Accurate identification of conflicts with change origin
- **Visual Change Badges**: Change origin indicators in UI (blue=upstream, amber=local, red=conflict)

### Typical Workflow

```
1. Create Snapshot      (POST /api/v1/versions/snapshots)
   ↓
2. Preview Changes      (GET /api/v1/versions/snapshots)
   ↓
3. Analyze Merge        (POST /api/v1/merge/analyze)
   ↓
4. Execute Merge        (POST /api/v1/merge/execute)
   ↓
5. Resolve Conflicts    (POST /api/v1/merge/resolve) - if needed
```

### Base URL

For development:
```
http://localhost:8080/api/v1
```

For production:
```
https://api.skillmeat.local/api/v1
```

## Authentication

All endpoints require authentication via Bearer token in the Authorization header:

```http
Authorization: Bearer <your_api_token>
```

### Note on Authentication

Currently, authentication is a placeholder for multi-user support planned in future versions.

---

## Snapshot Management

### POST /api/v1/versions/snapshots

**Description:** Create a new snapshot of the collection at the current state.

**Purpose:** Preserve collection state for safe experimentation and rollback capability.

#### Request

```http
POST /api/v1/versions/snapshots
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "message": "Before major refactor",
  "collection_name": "default"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Human-readable snapshot description (max 500 chars) |
| `collection_name` | string | No | Collection to snapshot (uses active if not specified) |

#### Response

**Success (201):**

```http
HTTP/1.1 201 Created
Content-Type: application/json
```

```json
{
  "id": "snap_20251218_103045_abc123",
  "timestamp": "2025-12-18T10:30:45Z",
  "message": "Before major refactor",
  "collection_name": "default",
  "artifact_count": 42,
  "size_bytes": 1048576
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique snapshot identifier |
| `timestamp` | ISO 8601 | When snapshot was created |
| `message` | string | Snapshot description |
| `collection_name` | string | Collection that was snapshotted |
| `artifact_count` | integer | Number of artifacts in snapshot |
| `size_bytes` | integer | Total size of snapshot in bytes |

**Error (400):**

```json
{
  "error": "Invalid collection name",
  "detail": "Collection 'invalid' not found",
  "code": "COLLECTION_NOT_FOUND"
}
```

#### Examples

**Basic snapshot:**

```bash
curl -X POST http://localhost:8080/api/v1/versions/snapshots \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Before major refactor"
  }'
```

**Snapshot specific collection:**

```bash
curl -X POST http://localhost:8080/api/v1/versions/snapshots \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Production backup",
    "collection_name": "work"
  }'
```

---

### GET /api/v1/versions/snapshots

**Description:** Retrieve a paginated list of collection snapshots.

**Purpose:** View snapshot history with cursor-based pagination.

#### Request

```http
GET /api/v1/versions/snapshots?limit=20&after=cursor123
Authorization: Bearer <token>
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `collection_name` | string | No | active collection | Collection to list snapshots from |
| `limit` | integer | No | 20 | Number of items per page (1-100) |
| `after` | string | No | null | Cursor for next page (base64 encoded) |

#### Response

**Success (200):**

```json
{
  "items": [
    {
      "id": "snap_20251218_103045_abc123",
      "timestamp": "2025-12-18T10:30:45Z",
      "message": "Before major refactor",
      "collection_name": "default",
      "artifact_count": 42,
      "size_bytes": 1048576
    },
    {
      "id": "snap_20251218_090000_def456",
      "timestamp": "2025-12-18T09:00:00Z",
      "message": "After sync",
      "collection_name": "default",
      "artifact_count": 40,
      "size_bytes": 1000000
    }
  ],
  "page_info": {
    "has_next_page": true,
    "has_previous_page": false,
    "start_cursor": "c25hcF8yMDI1MTIxOF8xMDMwNDVfYWJjMTIz",
    "end_cursor": "c25hcF8yMDI1MTIxOF8wOTAwMDBfZGVmNDU2",
    "total_count": null
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | Array of snapshot objects |
| `page_info` | object | Pagination metadata |
| `page_info.has_next_page` | boolean | Whether more results available |
| `page_info.start_cursor` | string | Cursor of first item (for going back) |
| `page_info.end_cursor` | string | Cursor of last item (for next page) |

#### Examples

**List snapshots:**

```bash
curl http://localhost:8080/api/v1/versions/snapshots \
  -H "Authorization: Bearer token"
```

**List with pagination:**

```bash
curl "http://localhost:8080/api/v1/versions/snapshots?limit=10&after=c25hcF8..." \
  -H "Authorization: Bearer token"
```

---

### GET /api/v1/versions/snapshots/{snapshot_id}

**Description:** Retrieve details of a specific snapshot.

**Purpose:** Get detailed information about a snapshot including all contained artifacts.

#### Request

```http
GET /api/v1/versions/snapshots/snap_20251218_103045_abc123
Authorization: Bearer <token>
```

#### Response

**Success (200):**

```json
{
  "id": "snap_20251218_103045_abc123",
  "timestamp": "2025-12-18T10:30:45Z",
  "message": "Before major refactor",
  "collection_name": "default",
  "artifact_count": 42,
  "size_bytes": 1048576,
  "artifacts": [
    {
      "name": "canvas-design",
      "type": "skill",
      "version": "v2.1.0",
      "hash": "abc123def456..."
    }
  ]
}
```

**Error (404):**

```json
{
  "error": "Snapshot not found",
  "detail": "Snapshot 'snap_invalid' does not exist",
  "code": "SNAPSHOT_NOT_FOUND"
}
```

---

## Rollback Operations

### POST /api/v1/versions/rollback

**Description:** Rollback collection to a previous snapshot.

**Purpose:** Restore collection to a previous state, reverting all changes since that snapshot.

#### Request

```http
POST /api/v1/versions/rollback
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "snapshot_id": "snap_20251218_103045_abc123",
  "create_backup": true
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `snapshot_id` | string | Yes | ID of snapshot to rollback to |
| `create_backup` | boolean | No | Create backup before rollback (default: true) |

#### Response

**Success (200):**

```json
{
  "success": true,
  "message": "Successfully rolled back to snapshot snap_20251218_103045_abc123",
  "snapshot_id": "snap_20251218_103045_abc123",
  "backup_snapshot_id": "snap_backup_20251218_110000_xyz789",
  "artifacts_affected": 5,
  "changes": {
    "added": 0,
    "removed": 2,
    "modified": 3
  }
}
```

**Error (400):**

```json
{
  "error": "Cannot rollback",
  "detail": "Rollback would create inconsistent state",
  "code": "INVALID_ROLLBACK"
}
```

#### Examples

**Rollback with backup:**

```bash
curl -X POST http://localhost:8080/api/v1/versions/rollback \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": "snap_20251218_103045_abc123",
    "create_backup": true
  }'
```

---

### POST /api/v1/versions/rollback/analyze

**Description:** Analyze rollback safety before executing.

**Purpose:** Get detailed analysis of what would happen if rollback is executed.

#### Request

```http
POST /api/v1/versions/rollback/analyze
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "snapshot_id": "snap_20251218_103045_abc123"
}
```

#### Response

**Success (200):**

```json
{
  "snapshot_id": "snap_20251218_103045_abc123",
  "can_rollback": true,
  "warnings": [],
  "changes": {
    "added": 0,
    "removed": 2,
    "modified": 3
  },
  "artifacts_affected": [
    {
      "name": "canvas-design",
      "type": "skill",
      "change": "modified",
      "local_changes": true,
      "warning": "Artifact has local modifications that will be lost"
    }
  ]
}
```

---

## Version Comparison

### POST /api/v1/versions/diff

**Description:** Compare two versions of the collection.

**Purpose:** Get detailed diff showing changes between versions.

#### Request

```http
POST /api/v1/versions/diff
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "base_snapshot_id": "snap_20251218_090000_def456",
  "target_snapshot_id": "snap_20251218_103045_abc123"
}
```

#### Response

**Success (200):**

```json
{
  "base_snapshot_id": "snap_20251218_090000_def456",
  "target_snapshot_id": "snap_20251218_103045_abc123",
  "changes": {
    "added": 2,
    "removed": 1,
    "modified": 3
  },
  "artifacts": [
    {
      "name": "canvas-design",
      "type": "skill",
      "change_type": "modified",
      "base_version": "v2.0.0",
      "target_version": "v2.1.0",
      "files_changed": 3,
      "lines_added": 45,
      "lines_removed": 12
    }
  ]
}
```

---

## Merge Operations

### POST /api/v1/merge/analyze

**Description:** Analyze merge safety before attempting merge.

**Purpose:** Perform dry-run three-way diff to identify conflicts without modifying files.

#### Request

```http
POST /api/v1/merge/analyze
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "base_snapshot_id": "snap_base_20251218_000000_001",
  "local_collection": "default",
  "remote_snapshot_id": "snap_remote_20251218_100000_002",
  "remote_collection": "upstream"
}
```

**Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `base_snapshot_id` | string | Common ancestor snapshot (merge base) |
| `local_collection` | string | Local collection name |
| `remote_snapshot_id` | string | Remote snapshot to merge from |
| `remote_collection` | string | Remote collection name (for reference) |

#### Response

**Success (200):**

```json
{
  "can_auto_merge": false,
  "auto_mergeable_count": 8,
  "conflict_count": 2,
  "conflicts": [
    {
      "file_path": "canvas/core.py",
      "conflict_type": "content_conflict",
      "auto_mergeable": false,
      "is_binary": false,
      "change_origin": "both"
    },
    {
      "file_path": "pdf-extractor/requirements.txt",
      "conflict_type": "content_conflict",
      "auto_mergeable": false,
      "is_binary": false,
      "change_origin": "both"
    }
  ],
  "warnings": [
    "2 binary files will require manual resolution"
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `can_auto_merge` | boolean | Whether merge can be auto-applied |
| `auto_mergeable_count` | integer | Number of non-conflicting changes |
| `conflict_count` | integer | Number of conflicts |
| `conflicts` | array | Detailed conflict information |
| `warnings` | array | Non-critical warnings |

**Conflict Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Path to conflicted file |
| `conflict_type` | string | Type: content_conflict, delete_conflict, etc. |
| `auto_mergeable` | boolean | Whether conflict can be auto-resolved |
| `is_binary` | boolean | Whether file is binary |
| `change_origin` | string | Origin of change: upstream, local_modification, or both |

---

### POST /api/v1/merge/preview

**Description:** Get preview of merge changes without executing.

**Purpose:** Show what files will be added, removed, or changed by merge.

#### Request

```http
POST /api/v1/merge/preview
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "base_snapshot_id": "snap_base_20251218_000000_001",
  "local_collection": "default",
  "remote_snapshot_id": "snap_remote_20251218_100000_002",
  "remote_collection": "upstream"
}
```

#### Response

**Success (200):**

```json
{
  "preview_status": "has_conflicts",
  "summary": {
    "files_added": 3,
    "files_removed": 1,
    "files_modified": 8,
    "conflicts": 2
  },
  "changes": [
    {
      "path": "canvas/core.py",
      "status": "modified",
      "change_origin": "both",
      "has_conflict": true,
      "additions": 45,
      "deletions": 12
    },
    {
      "path": "pdf-extractor/processor.py",
      "status": "added",
      "change_origin": "upstream",
      "has_conflict": false,
      "additions": 120,
      "deletions": 0
    },
    {
      "path": "old-tool/deprecated.py",
      "status": "deleted",
      "change_origin": "local_modification",
      "has_conflict": false,
      "additions": 0,
      "deletions": 45
    }
  ],
  "potential_conflicts": [
    {
      "file_path": "canvas/core.py",
      "conflict_type": "content_conflict",
      "change_origin": "both",
      "lines_conflicted": 15
    }
  ]
}
```

---

### POST /api/v1/merge/execute

**Description:** Execute the merge operation.

**Purpose:** Perform three-way merge and apply changes to local collection.

#### Request

```http
POST /api/v1/merge/execute
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "base_snapshot_id": "snap_base_20251218_000000_001",
  "local_collection": "default",
  "remote_snapshot_id": "snap_remote_20251218_100000_002",
  "remote_collection": "upstream",
  "strategy": "auto-merge",
  "create_snapshot": true
}
```

**Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `base_snapshot_id` | string | Common ancestor snapshot |
| `local_collection` | string | Local collection |
| `remote_snapshot_id` | string | Remote snapshot |
| `remote_collection` | string | Remote collection name |
| `strategy` | string | Merge strategy: auto-merge, manual, abort |
| `create_snapshot` | boolean | Create snapshot before merge (default: true) |

#### Response

**Success (200):**

```json
{
  "merge_status": "completed_with_conflicts",
  "snapshot_id": "snap_backup_20251218_110000_xyz789",
  "summary": {
    "merged_files": 8,
    "conflicts": 2,
    "change_origin_breakdown": {
      "upstream_only": 5,
      "local_only": 3,
      "both_sides": 2
    }
  },
  "conflicts": [
    {
      "file_path": "canvas/core.py",
      "change_origin": "both",
      "local_version_hash": "abc123...",
      "remote_version_hash": "def456..."
    }
  ],
  "message": "Merge completed with 2 conflicts requiring manual resolution"
}
```

**Error (400):**

```json
{
  "error": "Merge failed",
  "detail": "Cannot perform merge: base snapshot not found",
  "code": "INVALID_MERGE"
}
```

---

### POST /api/v1/merge/resolve

**Description:** Resolve conflicts after merge with manual decisions.

**Purpose:** Mark conflicts as resolved using chosen version or custom resolution.

#### Request

```http
POST /api/v1/merge/resolve
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "collection_name": "default",
  "resolutions": [
    {
      "file_path": "canvas/core.py",
      "resolution_type": "use_local",
      "reason": "Project customization is preferred"
    },
    {
      "file_path": "pdf-extractor/requirements.txt",
      "resolution_type": "use_remote",
      "reason": "Upstream has updated dependencies"
    }
  ]
}
```

**Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `collection_name` | string | Collection being resolved |
| `resolutions` | array | Array of conflict resolutions |
| `resolutions[].file_path` | string | Path to conflicted file |
| `resolutions[].resolution_type` | string | use_local, use_remote, or manual |
| `resolutions[].reason` | string | Human-readable reason for resolution |

#### Response

**Success (200):**

```json
{
  "resolved_count": 2,
  "unresolved_count": 0,
  "merge_status": "complete",
  "message": "All conflicts resolved successfully"
}
```

---

## Data Models

### Snapshot

```json
{
  "id": "snap_20251218_103045_abc123",
  "timestamp": "2025-12-18T10:30:45Z",
  "message": "Before major refactor",
  "collection_name": "default",
  "artifact_count": 42,
  "size_bytes": 1048576
}
```

### Change Origin Enum

Indicates the source of a change in merge operations:

- `upstream` - Change from upstream/remote source only
- `local_modification` - Change made locally only
- `both` - Both sides modified (potential conflict)

### Conflict

```json
{
  "file_path": "canvas/core.py",
  "conflict_type": "content_conflict",
  "auto_mergeable": false,
  "is_binary": false,
  "change_origin": "both",
  "local_version_hash": "abc123...",
  "remote_version_hash": "def456...",
  "base_version_hash": "xyz789..."
}
```

### MergePreview

```json
{
  "preview_status": "has_conflicts",
  "summary": {
    "files_added": 3,
    "files_removed": 1,
    "files_modified": 8,
    "conflicts": 2
  },
  "changes": [
    {
      "path": "canvas/core.py",
      "status": "modified",
      "change_origin": "both",
      "has_conflict": true,
      "additions": 45,
      "deletions": 12
    }
  ]
}
```

---

## Change Attribution

The versioning system tracks change origin to distinguish where changes came from:

### Change Origin Values

| Origin | Meaning | Badge Color | Indicates |
|--------|---------|-------------|-----------|
| `upstream` | From collection/upstream source | Blue | Changes pulled from upstream |
| `local_modification` | Made locally in project | Amber | Local customizations |
| `both` | Both sides changed | Red | Potential or actual conflict |

### How Change Attribution Works

1. **Baseline Storage**: System stores the correct merge base (not empty)
2. **Three-Way Diff**: Compares base → local and base → remote
3. **Change Detection**: Each change is attributed to its origin
4. **Conflict Identification**: Changes from both sides are marked as conflicts
5. **UI Display**: Change badges show origin visually

### Example: Change Attribution in Merge

```
Base (merge base):
  def process():
      pass

Local (project):
  def process():
      log("Processing")
      return result()

Remote (upstream):
  def process():
      validate_input()
      return execute()

Result:
  - log() call: change_origin = "local_modification"
  - validate_input(): change_origin = "upstream"
  - return statement: change_origin = "both" (CONFLICT)
```

---

## Error Handling

### Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Operation completed successfully |
| 201 | Created | Snapshot created |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 404 | Not Found | Snapshot doesn't exist |
| 422 | Unprocessable | Validation error |
| 500 | Server Error | Internal error |

### Error Response Format

```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "code": "ERROR_CODE"
}
```

### Common Errors

**Snapshot Not Found:**
```json
{
  "error": "Snapshot not found",
  "detail": "Snapshot 'snap_invalid' does not exist",
  "code": "SNAPSHOT_NOT_FOUND"
}
```

**Collection Not Found:**
```json
{
  "error": "Invalid collection name",
  "detail": "Collection 'invalid' not found",
  "code": "COLLECTION_NOT_FOUND"
}
```

**Merge Cannot Auto-Complete:**
```json
{
  "error": "Merge has conflicts",
  "detail": "Cannot auto-merge: 2 conflicts require manual resolution",
  "code": "MERGE_HAS_CONFLICTS"
}
```

---

## Examples

### Complete Merge Workflow

#### Step 1: Analyze Merge Safety

```bash
curl -X POST http://localhost:8080/api/v1/merge/analyze \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "base_snapshot_id": "snap_base_001",
    "local_collection": "default",
    "remote_snapshot_id": "snap_remote_001",
    "remote_collection": "upstream"
  }'
```

Response shows `can_auto_merge: false` with 2 conflicts.

#### Step 2: Preview Merge

```bash
curl -X POST http://localhost:8080/api/v1/merge/preview \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "base_snapshot_id": "snap_base_001",
    "local_collection": "default",
    "remote_snapshot_id": "snap_remote_001",
    "remote_collection": "upstream"
  }'
```

Response shows detailed file changes and conflict locations.

#### Step 3: Execute Merge

```bash
curl -X POST http://localhost:8080/api/v1/merge/execute \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "base_snapshot_id": "snap_base_001",
    "local_collection": "default",
    "remote_snapshot_id": "snap_remote_001",
    "remote_collection": "upstream",
    "strategy": "auto-merge",
    "create_snapshot": true
  }'
```

Response shows merge completed with conflicts.

#### Step 4: Resolve Conflicts

```bash
curl -X POST http://localhost:8080/api/v1/merge/resolve \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "default",
    "resolutions": [
      {
        "file_path": "canvas/core.py",
        "resolution_type": "use_local",
        "reason": "Keep project customization"
      },
      {
        "file_path": "pdf-extractor/requirements.txt",
        "resolution_type": "use_remote",
        "reason": "Use upstream dependencies"
      }
    ]
  }'
```

Response shows all conflicts resolved.

---

## Related Guides

- [Syncing Project Changes](../guides/syncing-changes.md) - User guide for sync operations
- [Version Timeline](../guides/syncing-changes.md#step-2-preview-changes) - Understanding version history
- [Conflict Resolution](../guides/syncing-changes.md#handling-sync-conflicts) - Resolving merge conflicts

## See Also

- [Command Reference: sync check](../commands.md#sync-check)
- [Command Reference: sync pull](../commands.md#sync-pull)
- [Command Reference: sync preview](../commands.md#sync-preview)
- Backend Implementation: `skillmeat/api/routers/versions.py`, `skillmeat/api/routers/merge.py`
