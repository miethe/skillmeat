---
title: Versioning & Merge API Reference
description: Complete REST API documentation for SkillMeat's versioning and merge system endpoints
audience: developers
tags: [api, versions, merge, snapshots, rollback]
created: 2025-12-17
updated: 2025-12-17
category: API Documentation
status: complete
related_documents:
  - docs/features/versioning/overview.md
  - docs/features/versioning/merge-strategy.md
---

# Versioning & Merge API Reference

Complete REST API documentation for SkillMeat's versioning and merge system endpoints.

## Authentication

All endpoints require Bearer token authentication via the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.example.com/api/v1/versions/snapshots
```

**Missing or invalid token response (401 Unauthorized)**:
```json
{
  "detail": "Missing or invalid token"
}
```

## Base URL

All endpoints are prefixed with `/api/v1`:

```
https://api.example.com/api/v1/versions/...
https://api.example.com/api/v1/merge/...
```

---

## Version Management API

Version management endpoints handle snapshot creation, retrieval, deletion, and rollback operations.

### List Snapshots

`GET /versions/snapshots`

Retrieve a paginated list of collection snapshots using cursor-based pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `collection_name` | string | No | Active collection | Collection name (uses active collection if not specified) |
| `limit` | integer | No | 20 | Number of items per page (1-100) |
| `after` | string | No | - | Cursor for pagination (base64-encoded, used for next page) |

**Response: 200 OK**

```json
{
  "items": [
    {
      "id": "abc123def456789...",
      "timestamp": "2025-12-17T12:00:00Z",
      "message": "Manual snapshot before upgrade",
      "collection_name": "default",
      "artifact_count": 15
    },
    {
      "id": "def789abc123...",
      "timestamp": "2025-12-17T10:30:00Z",
      "message": "Auto-snapshot after deployment",
      "collection_name": "default",
      "artifact_count": 14
    }
  ],
  "page_info": {
    "has_next_page": true,
    "has_previous_page": false,
    "start_cursor": "YWJjMTIzZGVm",
    "end_cursor": "ZGVmNzg5YWJj",
    "total_count": null
  }
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to list snapshots: [error message]"
}
```

**Example Usage:**

```bash
# Get first page of snapshots
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots?limit=10"

# Get next page using cursor
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots?limit=10&after=ZGVmNzg5YWJj"

# Get snapshots for specific collection
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots?collection_name=production"
```

---

### Get Snapshot Details

`GET /versions/snapshots/{snapshot_id}`

Retrieve detailed information about a specific snapshot.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `snapshot_id` | string | Yes | Snapshot unique identifier (SHA-256 hash) |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `collection_name` | string | No | Active collection | Collection name (uses active collection if not specified) |

**Response: 200 OK**

```json
{
  "id": "abc123def456789...",
  "timestamp": "2025-12-17T12:00:00Z",
  "message": "Manual snapshot before upgrade",
  "collection_name": "default",
  "artifact_count": 15
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'abc123def456789...' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to get snapshot: [error message]"
}
```

**Example Usage:**

```bash
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots/abc123def456789..."
```

---

### Create Snapshot

`POST /versions/snapshots`

Create a new point-in-time snapshot of a collection.

**Request Body:**

```json
{
  "collection_name": "default",
  "message": "Manual snapshot before major upgrade"
}
```

**Request Schema:**

| Field | Type | Required | Max Length | Description |
|-------|------|----------|-----------|-------------|
| `collection_name` | string | No | - | Collection name (uses active collection if not specified) |
| `message` | string | No | 500 | Snapshot description or commit message |

**Response: 201 Created**

```json
{
  "snapshot": {
    "id": "abc123def456789...",
    "timestamp": "2025-12-17T12:00:00Z",
    "message": "Manual snapshot before major upgrade",
    "collection_name": "default",
    "artifact_count": 15
  },
  "created": true
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Collection 'production' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to create snapshot: [error message]"
}
```

**Example Usage:**

```bash
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "default",
    "message": "Before schema migration"
  }' \
  https://api.example.com/api/v1/versions/snapshots
```

---

### Delete Snapshot

`DELETE /versions/snapshots/{snapshot_id}`

Delete a specific snapshot.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `snapshot_id` | string | Yes | Snapshot unique identifier |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `collection_name` | string | No | Active collection | Collection name |

**Response: 204 No Content**

No response body.

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'abc123def456789...' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to delete snapshot: [error message]"
}
```

**Example Usage:**

```bash
curl -X DELETE -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots/abc123def456789..."
```

---

## Rollback Operations

### Analyze Rollback Safety

`GET /versions/snapshots/{snapshot_id}/rollback-analysis`

Analyze potential conflicts and safety before executing a rollback. This performs a dry-run to detect issues without modifying any files.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `snapshot_id` | string | Yes | Snapshot to analyze rollback for |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `collection_name` | string | No | Active collection | Collection name |

**Response: 200 OK**

```json
{
  "is_safe": true,
  "files_with_conflicts": [
    ".claude/skills/pdf/SKILL.md"
  ],
  "files_safe_to_restore": [
    ".claude/skills/canvas/SKILL.md",
    ".claude/skills/document/SKILL.md"
  ],
  "warnings": [
    "2 files have been modified since snapshot",
    "Cannot auto-merge file with binary content"
  ]
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'abc123def456789...' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to analyze rollback safety: [error message]"
}
```

**Example Usage:**

```bash
# Analyze rollback safety before proceeding
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots/abc123def456789.../rollback-analysis"
```

---

### Execute Rollback

`POST /versions/snapshots/{snapshot_id}/rollback`

Rollback to a specific snapshot with optional intelligent merge to preserve local changes.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `snapshot_id` | string | Yes | Snapshot to rollback to |

**Request Body:**

```json
{
  "collection_name": "default",
  "preserve_changes": true,
  "selective_paths": null
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `collection_name` | string | No | Collection name (uses active if not specified) |
| `preserve_changes` | boolean | No | Use intelligent merge to preserve local changes (default: true) |
| `selective_paths` | array[string] | No | Only rollback these specific paths (optional) |

**Response: 200 OK**

```json
{
  "success": true,
  "files_merged": [
    ".claude/skills/pdf/SKILL.md"
  ],
  "files_restored": [
    ".claude/skills/canvas/SKILL.md",
    ".claude/skills/document/SKILL.md"
  ],
  "conflicts": [
    {
      "file_path": ".claude/config/manifest.toml",
      "conflict_type": "both_modified",
      "auto_mergeable": false,
      "is_binary": false
    }
  ],
  "safety_snapshot_id": "def789abc123..."
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'abc123def456789...' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to execute rollback: [error message]"
}
```

**Example Usage:**

```bash
# Simple rollback with change preservation (recommended)
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "default",
    "preserve_changes": true
  }' \
  https://api.example.com/api/v1/versions/snapshots/abc123def456789.../rollback

# Selective rollback of specific paths
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "default",
    "preserve_changes": true,
    "selective_paths": [".claude/skills/pdf/"]
  }' \
  https://api.example.com/api/v1/versions/snapshots/abc123def456789.../rollback
```

---

### Compare Snapshots (Diff)

`POST /versions/snapshots/diff`

Generate a diff showing changes between two snapshots.

**Request Body:**

```json
{
  "snapshot_id_1": "abc123def456789...",
  "snapshot_id_2": "def789abc123...",
  "collection_name": "default"
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `snapshot_id_1` | string | Yes | First snapshot ID (older) |
| `snapshot_id_2` | string | Yes | Second snapshot ID (newer) |
| `collection_name` | string | No | Collection name (uses active if not specified) |

**Response: 200 OK**

```json
{
  "files_added": [
    ".claude/skills/new-skill/SKILL.md"
  ],
  "files_removed": [
    ".claude/skills/old-skill/SKILL.md"
  ],
  "files_modified": [
    ".claude/skills/pdf/SKILL.md",
    ".claude/config/manifest.toml"
  ],
  "total_lines_added": 150,
  "total_lines_removed": 75
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'abc123def456789...' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to generate diff: [error message]"
}
```

**Example Usage:**

```bash
# Compare two snapshots
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id_1": "abc123def456789...",
    "snapshot_id_2": "def789abc123...",
    "collection_name": "default"
  }' \
  https://api.example.com/api/v1/versions/snapshots/diff
```

---

## Merge Operations API

Merge operations provide three-way merge capabilities for combining changes from different collection versions.

### Analyze Merge Safety

`POST /merge/analyze`

Analyze whether a merge is safe before attempting it. Performs a dry-run three-way diff to identify potential conflicts without modifying any files.

**Request Body:**

```json
{
  "base_snapshot_id": "snap_20241215_120000",
  "local_collection": "default",
  "remote_snapshot_id": "snap_20241216_150000",
  "remote_collection": null
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_snapshot_id` | string | Yes | Snapshot ID of base/ancestor version |
| `local_collection` | string | Yes | Name of the local collection |
| `remote_snapshot_id` | string | Yes | Snapshot ID of remote version to merge |
| `remote_collection` | string | No | Name of remote collection (defaults to local_collection) |

**Response: 200 OK**

```json
{
  "can_auto_merge": true,
  "auto_mergeable_count": 5,
  "conflict_count": 2,
  "conflicts": [
    {
      "file_path": ".claude/skills/pdf/SKILL.md",
      "conflict_type": "both_modified",
      "auto_mergeable": false,
      "is_binary": false
    },
    {
      "file_path": ".claude/data/assets/image.png",
      "conflict_type": "both_modified",
      "auto_mergeable": false,
      "is_binary": true
    }
  ],
  "warnings": [
    "Binary file conflict detected: image.png"
  ]
}
```

**Response: 400 Bad Request**

```json
{
  "detail": "Invalid request parameters"
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'snap_20241215_120000' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to analyze merge: [error message]"
}
```

**Example Usage:**

```bash
# Analyze merge safety
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "base_snapshot_id": "snap_20241215_120000",
    "local_collection": "default",
    "remote_snapshot_id": "snap_20241216_150000"
  }' \
  https://api.example.com/api/v1/merge/analyze
```

---

### Preview Merge Changes

`POST /merge/preview`

Get a preview of merge changes without executing the merge. Shows what files will be added, removed, or changed.

**Request Body:**

```json
{
  "base_snapshot_id": "snap_20241215_120000",
  "local_collection": "default",
  "remote_snapshot_id": "snap_20241216_150000",
  "remote_collection": null
}
```

**Request Schema:**

Same as Analyze Merge Safety.

**Response: 200 OK**

```json
{
  "files_added": [
    ".claude/skills/new-feature/SKILL.md"
  ],
  "files_removed": [
    ".claude/skills/deprecated/SKILL.md"
  ],
  "files_changed": [
    ".claude/skills/pdf/SKILL.md",
    ".claude/config/manifest.toml"
  ],
  "potential_conflicts": [
    {
      "file_path": ".claude/skills/pdf/SKILL.md",
      "conflict_type": "both_modified",
      "auto_mergeable": true,
      "is_binary": false
    }
  ],
  "can_auto_merge": true
}
```

**Response: 400 Bad Request**

```json
{
  "detail": "Invalid request parameters"
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'snap_20241215_120000' not found"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to generate merge preview: [error message]"
}
```

**Example Usage:**

```bash
# Preview merge changes before executing
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "base_snapshot_id": "snap_20241215_120000",
    "local_collection": "default",
    "remote_snapshot_id": "snap_20241216_150000"
  }' \
  https://api.example.com/api/v1/merge/preview
```

---

### Execute Merge

`POST /merge/execute`

Execute a merge operation with full conflict detection. Automatically creates a safety snapshot before merge for rollback capability.

**Request Body:**

```json
{
  "base_snapshot_id": "snap_20241215_120000",
  "local_collection": "default",
  "remote_snapshot_id": "snap_20241216_150000",
  "remote_collection": null,
  "auto_snapshot": true
}
```

**Request Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `base_snapshot_id` | string | Yes | - | Snapshot ID of base/ancestor version |
| `local_collection` | string | Yes | - | Name of the local collection |
| `remote_snapshot_id` | string | Yes | - | Snapshot ID of remote version to merge |
| `remote_collection` | string | No | local_collection | Name of remote collection |
| `auto_snapshot` | boolean | No | true | Automatically create safety snapshot before merge |

**Response: 200 OK**

```json
{
  "success": true,
  "files_merged": [
    ".claude/skills/pdf/SKILL.md",
    ".claude/config/manifest.toml"
  ],
  "conflicts": [],
  "pre_merge_snapshot_id": "snap_20241216_150000_premerge",
  "error": null
}
```

**Response: 400 Bad Request**

```json
{
  "detail": "Invalid request parameters"
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Snapshot 'snap_20241215_120000' not found"
}
```

**Response: 409 Conflict**

```json
{
  "detail": "Merge has 2 unresolved conflicts"
}
```

**Response: 422 Unprocessable Entity**

```json
{
  "detail": "Validation errors"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to execute merge: [error message]"
}
```

**Example Usage:**

```bash
# Execute merge with automatic safety snapshot
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "base_snapshot_id": "snap_20241215_120000",
    "local_collection": "default",
    "remote_snapshot_id": "snap_20241216_150000",
    "auto_snapshot": true
  }' \
  https://api.example.com/api/v1/merge/execute
```

---

### Resolve Merge Conflict

`POST /merge/resolve`

Resolve a single merge conflict by specifying which version to use or providing custom content.

**Request Body:**

```json
{
  "file_path": "SKILL.md",
  "resolution": "use_local",
  "custom_content": null
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | string | Yes | Relative path to the conflicting file |
| `resolution` | enum | Yes | Resolution strategy: `use_local`, `use_remote`, `use_base`, or `custom` |
| `custom_content` | string | No | Custom content to use (required if resolution='custom') |

**Resolution Strategies:**

| Strategy | Description |
|----------|-------------|
| `use_local` | Use the local version of the file |
| `use_remote` | Use the remote version of the file |
| `use_base` | Use the base/ancestor version of the file |
| `custom` | Use custom content (must provide `custom_content` field) |

**Response: 200 OK**

```json
{
  "success": true,
  "file_path": "SKILL.md",
  "resolution_applied": "use_local"
}
```

**Response: 400 Bad Request**

```json
{
  "detail": "Invalid resolution parameters"
}
```

**Response: 401 Unauthorized**

```json
{
  "detail": "Missing or invalid token"
}
```

**Response: 404 Not Found**

```json
{
  "detail": "Conflict or file not found"
}
```

**Response: 422 Unprocessable Entity**

```json
{
  "detail": "custom_content required when resolution='custom'"
}
```

**Response: 500 Internal Server Error**

```json
{
  "detail": "Failed to resolve conflict: [error message]"
}
```

**Example Usage:**

```bash
# Resolve conflict using local version
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "SKILL.md",
    "resolution": "use_local"
  }' \
  https://api.example.com/api/v1/merge/resolve

# Resolve conflict with custom content
curl -X POST -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "SKILL.md",
    "resolution": "custom",
    "custom_content": "# Manually merged content\n..."
  }' \
  https://api.example.com/api/v1/merge/resolve
```

---

## Common Error Responses

### 400 Bad Request

Invalid request parameters or malformed data.

```json
{
  "detail": "Invalid cursor format: must be base64-encoded"
}
```

### 401 Unauthorized

Missing or invalid authentication token.

```json
{
  "detail": "Missing or invalid token"
}
```

### 404 Not Found

Requested resource (snapshot, collection, etc.) not found.

```json
{
  "detail": "Snapshot 'abc123...' not found"
}
```

### 409 Conflict

Merge operation cannot be completed due to unresolved conflicts.

```json
{
  "detail": "Merge has 2 unresolved conflicts"
}
```

### 422 Unprocessable Entity

Validation errors in request data.

```json
{
  "detail": "custom_content required when resolution='custom'"
}
```

### 500 Internal Server Error

Unexpected server error.

```json
{
  "detail": "Failed to execute merge: [error message]"
}
```

---

## Pagination

List endpoints use cursor-based pagination for efficient data retrieval.

**Pagination Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Number of items per page (1-100, default 20) |
| `after` | string | Cursor for next page (base64-encoded) |

**PageInfo Response:**

```json
{
  "page_info": {
    "has_next_page": true,
    "has_previous_page": false,
    "start_cursor": "YWJjMTIzZGVm",
    "end_cursor": "ZGVmNzg5YWJj",
    "total_count": null
  }
}
```

**Pagination Strategy:**

1. Request first page with `limit` parameter
2. If `has_next_page` is true, use `end_cursor` as `after` parameter for next request
3. Continue until `has_next_page` is false

**Example:**

```bash
# Page 1
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots?limit=10"

# Page 2 - use end_cursor from previous response
curl -H "Authorization: Bearer token" \
  "https://api.example.com/api/v1/versions/snapshots?limit=10&after=ZGVmNzg5YWJj"
```

---

## Data Types

### Snapshot Response

Represents a single collection snapshot.

```json
{
  "id": "abc123def456789...",
  "timestamp": "2025-12-17T12:00:00Z",
  "message": "Manual snapshot before upgrade",
  "collection_name": "default",
  "artifact_count": 15
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Snapshot unique identifier (SHA-256 hash) |
| `timestamp` | string | ISO 8601 timestamp of snapshot creation |
| `message` | string | Snapshot description or commit message |
| `collection_name` | string | Name of the collection |
| `artifact_count` | integer | Number of artifacts captured |

### Conflict Metadata

Represents a merge conflict or rollback conflict.

```json
{
  "file_path": ".claude/skills/pdf/SKILL.md",
  "conflict_type": "content",
  "auto_mergeable": true,
  "is_binary": false
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path to the conflicting file |
| `conflict_type` | string | Type: `content`, `deletion`, `add_add`, `both_modified` |
| `auto_mergeable` | boolean | Whether conflict can be automatically merged |
| `is_binary` | boolean | Whether file is binary (cannot be text-merged) |

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Limit**: 100 requests per minute per API key
- **Headers**: Include rate limit information in responses

**Rate Limit Headers:**

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per minute |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

**Rate Limit Exceeded (429 Too Many Requests):**

```json
{
  "detail": "Rate limit exceeded"
}
```

---

## Performance Considerations

- **Snapshot Creation**: Average 1-5 seconds for typical collections
- **Merge Operations**: Average 2-10 seconds depending on collection size and conflict count
- **Diff Operations**: Average 1-3 seconds for comparing two snapshots
- **List Snapshots**: Optimized for fast retrieval with cursor-based pagination

**Optimization Tips:**

1. Use cursor-based pagination for large snapshot lists
2. Analyze merge safety before executing for large collections
3. Create targeted snapshots for specific features to reduce merge complexity
4. Use selective rollback for partial restoration when appropriate

---

## SDK Examples

### Python Client

```python
import requests
from typing import Optional

class VersionMergeClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def list_snapshots(
        self,
        collection_name: Optional[str] = None,
        limit: int = 20,
        after: Optional[str] = None,
    ):
        """List all snapshots with pagination."""
        params = {"limit": limit}
        if collection_name:
            params["collection_name"] = collection_name
        if after:
            params["after"] = after

        response = requests.get(
            f"{self.base_url}/api/v1/versions/snapshots",
            headers=self.headers,
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def analyze_merge(
        self,
        base_snapshot_id: str,
        local_collection: str,
        remote_snapshot_id: str,
        remote_collection: Optional[str] = None,
    ):
        """Analyze merge safety (dry run)."""
        payload = {
            "base_snapshot_id": base_snapshot_id,
            "local_collection": local_collection,
            "remote_snapshot_id": remote_snapshot_id,
        }
        if remote_collection:
            payload["remote_collection"] = remote_collection

        response = requests.post(
            f"{self.base_url}/api/v1/merge/analyze",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def execute_merge(
        self,
        base_snapshot_id: str,
        local_collection: str,
        remote_snapshot_id: str,
        auto_snapshot: bool = True,
    ):
        """Execute merge operation."""
        payload = {
            "base_snapshot_id": base_snapshot_id,
            "local_collection": local_collection,
            "remote_snapshot_id": remote_snapshot_id,
            "auto_snapshot": auto_snapshot,
        }
        response = requests.post(
            f"{self.base_url}/api/v1/merge/execute",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

# Usage
client = VersionMergeClient("https://api.example.com", "your_api_key")
snapshots = client.list_snapshots(limit=10)
analysis = client.analyze_merge(
    base_snapshot_id="snap_...",
    local_collection="default",
    remote_snapshot_id="snap_...",
)
```

### TypeScript/JavaScript Client

```typescript
interface VersionMergeClientOptions {
  baseUrl: string;
  apiKey: string;
}

class VersionMergeClient {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor({ baseUrl, apiKey }: VersionMergeClientOptions) {
    this.baseUrl = baseUrl;
    this.headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
  }

  async listSnapshots(options?: {
    collectionName?: string;
    limit?: number;
    after?: string;
  }): Promise<any> {
    const params = new URLSearchParams();
    if (options?.limit) params.set("limit", options.limit.toString());
    if (options?.after) params.set("after", options.after);
    if (options?.collectionName)
      params.set("collection_name", options.collectionName);

    const response = await fetch(
      `${this.baseUrl}/api/v1/versions/snapshots?${params.toString()}`,
      { headers: this.headers }
    );

    if (!response.ok) {
      throw new Error(
        `Failed to list snapshots: ${response.statusText}`
      );
    }
    return response.json();
  }

  async analyzeMerge(options: {
    baseSnapshotId: string;
    localCollection: string;
    remoteSnapshotId: string;
    remoteCollection?: string;
  }): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/merge/analyze`,
      {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify({
          base_snapshot_id: options.baseSnapshotId,
          local_collection: options.localCollection,
          remote_snapshot_id: options.remoteSnapshotId,
          remote_collection: options.remoteCollection,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(
        `Failed to analyze merge: ${response.statusText}`
      );
    }
    return response.json();
  }

  async executeMerge(options: {
    baseSnapshotId: string;
    localCollection: string;
    remoteSnapshotId: string;
    autoSnapshot?: boolean;
  }): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/merge/execute`,
      {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify({
          base_snapshot_id: options.baseSnapshotId,
          local_collection: options.localCollection,
          remote_snapshot_id: options.remoteSnapshotId,
          auto_snapshot: options.autoSnapshot ?? true,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(
        `Failed to execute merge: ${response.statusText}`
      );
    }
    return response.json();
  }
}

// Usage
const client = new VersionMergeClient({
  baseUrl: "https://api.example.com",
  apiKey: "your_api_key",
});

const snapshots = await client.listSnapshots({ limit: 10 });
const analysis = await client.analyzeMerge({
  baseSnapshotId: "snap_...",
  localCollection: "default",
  remoteSnapshotId: "snap_...",
});
```

---

## Best Practices

### Snapshot Management

1. **Create Snapshots Before Major Operations**: Always create a snapshot before major changes or deployments
2. **Use Descriptive Messages**: Include context in snapshot messages for easy identification
3. **Clean Up Old Snapshots**: Periodically delete old snapshots to save storage space
4. **Automate Snapshots**: Consider automating snapshot creation for critical collections

### Merge Operations

1. **Always Analyze First**: Use `/merge/analyze` before executing merges to check for conflicts
2. **Create Safety Snapshots**: Enable `auto_snapshot` to create pre-merge snapshots for rollback
3. **Preview Before Execute**: Use `/merge/preview` to understand merge changes
4. **Handle Conflicts Systematically**: Resolve conflicts one at a time using `/merge/resolve`
5. **Document Merge Decisions**: Record which resolution strategy was chosen and why

### Rollback Strategy

1. **Test Rollback Safety**: Use `/versions/snapshots/{id}/rollback-analysis` before executing
2. **Preserve Changes by Default**: Use `preserve_changes: true` to avoid data loss
3. **Selective Rollback for Precision**: Use `selective_paths` to rollback only specific directories
4. **Have a Backup Plan**: Keep multiple recent snapshots for additional safety

### Error Handling

1. **Check Response Status**: Always verify response status codes before processing
2. **Parse Error Details**: Extract `detail` field from error responses for debugging
3. **Implement Retry Logic**: Use exponential backoff for transient failures (5xx errors)
4. **Log API Calls**: Log important API calls for audit trails and debugging

---

## Related Documentation

- [Versioning System Overview](./overview.md) - High-level versioning architecture
- [Merge Strategy Guide](./merge-strategy.md) - Detailed merge algorithm documentation
- [Development Setup Guide](../../development/setup.md) - API setup and configuration
