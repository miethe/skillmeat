# Smart Import & Discovery API Documentation

Complete API reference for SkillMeat's Smart Import & Discovery feature endpoints.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [POST /api/v1/artifacts/discover](#post-apiv1artifactsdiscover)
  - [POST /api/v1/artifacts/discover/import](#post-apiv1artifactsdiscover-import)
  - [GET /api/v1/artifacts/metadata/github](#get-apiv1artifactsmetadatagithub)
  - [PUT /api/v1/artifacts/{artifact_id}/parameters](#put-apiv1artifactsartifact_idparameters)
  - [POST /api/v1/projects/{project_id}/skip-preferences](#post-apiv1projectsproject_idskip-preferences)
  - [DELETE /api/v1/projects/{project_id}/skip-preferences/{artifact_key}](#delete-apiv1projectsproject_idskip-preferencesartifact_key)
  - [DELETE /api/v1/projects/{project_id}/skip-preferences](#delete-apiv1projectsproject_idskip-preferences)
  - [GET /api/v1/projects/{project_id}/skip-preferences](#get-apiv1projectsproject_idskip-preferences)
- [Status Codes](#status-codes)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Import Result Status Enum](#import-result-status-enum)
- [Examples](#examples)

## Overview

The Smart Import & Discovery API provides endpoints for:

- **Discovering artifacts** in local directories (.claude/)
- **Bulk importing** multiple artifacts into collection
- **Fetching GitHub metadata** for auto-population
- **Updating artifact parameters** (tags, scope, version, etc.)

### Base URL

```
https://api.skillmeat.local/api/v1
```

Or for development:

```
http://localhost:8000/api/v1
```

### API Version

Current API version: **v1**

All endpoints use the `/api/v1/` prefix.

## Authentication

All endpoints require authentication via Bearer token in the Authorization header:

```http
Authorization: Bearer <your_api_token>
```

### Getting an API Token

1. **Generate token in SkillMeat web interface**
   - Navigate to Settings > API Tokens
   - Click "Generate New Token"
   - Copy and save token securely

2. **Or use environment variable**
   ```bash
   export SKILLMEAT_API_TOKEN=your_token_here
   ```

3. **Or configure in CLI**
   ```bash
   skillmeat config set api-token your_token_here
   ```

### Missing or Invalid Token

Requests without valid token receive:

```http
HTTP/1.1 401 Unauthorized

{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid API token"
  }
}
```

## Endpoints

### POST /api/v1/artifacts/discover

**Description:** Scan .claude/ directories and discover existing artifacts.

**Purpose:** Find artifacts that can be imported into the collection.

#### Request

```http
POST /api/v1/artifacts/discover
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body** (optional):

```json
{
  "scan_path": "/Users/username/.claude/skills"
}
```

**Parameters:**

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `scan_path` | string | No | Custom path to scan for artifacts | Collection artifacts directory |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "discovered_count": 3,
  "artifacts": [
    {
      "type": "skill",
      "name": "canvas-design",
      "source": "anthropics/skills/canvas-design",
      "version": "latest",
      "scope": "user",
      "tags": ["design", "visual", "art"],
      "description": "Create beautiful visual art in PDF and PNG documents",
      "path": "/Users/username/.skillmeat/collection/artifacts/skills/canvas-design",
      "discovered_at": "2025-11-30T14:30:00Z"
    },
    {
      "type": "command",
      "name": "list-files",
      "source": null,
      "version": null,
      "scope": "local",
      "tags": ["utility", "files"],
      "description": "List files in a directory",
      "path": "/Users/username/.claude/commands/list-files",
      "discovered_at": "2025-11-30T14:30:01Z"
    },
    {
      "type": "agent",
      "name": "research-agent",
      "source": "my-org/my-repo/agents/research",
      "version": "v1.0.0",
      "scope": "local",
      "tags": ["research", "ai"],
      "description": "Research and summarize information",
      "path": "/Users/username/.claude/agents/research-agent",
      "discovered_at": "2025-11-30T14:30:02Z"
    }
  ],
  "errors": [
    "Failed to parse SKILL.md in /path/to/broken/skill: Invalid YAML syntax",
    "Permission denied accessing /path/to/protected/artifact"
  ],
  "scan_duration_ms": 245.67
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `discovered_count` | integer | Total number of artifacts found in scan (before any filtering) |
| `importable_count` | integer | Number of artifacts not yet in collection (post-scan filtered results) |
| `artifacts` | array | List of discovered artifacts (filtered by manifest if provided) |
| `artifacts[].type` | string | Artifact type: skill, command, agent, hook, mcp |
| `artifacts[].name` | string | Artifact identifier/name |
| `artifacts[].source` | string or null | GitHub source if known (user/repo/path[@version]) |
| `artifacts[].version` | string or null | Version identifier if known |
| `artifacts[].scope` | string | Scope: "user" (global) or "local" (project) |
| `artifacts[].tags` | array | Tags/categories extracted from metadata |
| `artifacts[].description` | string | Description from artifact metadata |
| `artifacts[].path` | string | Full file system path to artifact |
| `artifacts[].discovered_at` | string | ISO 8601 timestamp when discovered |
| `errors` | array | Non-fatal errors encountered during scan |
| `scan_duration_ms` | number | Total scan duration in milliseconds |

**Discovery Filtering:**

The discovery endpoint filters results based on:
- **importable_count**: Reflects artifacts not yet imported to the collection
- **artifacts array**: Contains only artifacts that are new or can be imported
- **discovered_count vs importable_count**: Difference indicates artifacts already in collection

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Scan completed successfully |
| 400 | Bad Request | Invalid scan_path or request format |
| 401 | Unauthorized | Missing or invalid authentication token |
| 500 | Internal Server Error | Server error during scan |

#### Examples

**Basic discovery:**

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/discover \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json"
```

**Custom scan path:**

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/discover \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_path": "/Users/john/.claude/skills"
  }'
```

**Python example:**

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

# Discover artifacts
response = requests.post(
    "http://localhost:8000/api/v1/artifacts/discover",
    headers=headers
)

result = response.json()
print(f"Discovered {result['discovered_count']} artifacts")

for artifact in result['artifacts']:
    print(f"  - {artifact['type']}: {artifact['name']}")

if result['errors']:
    print(f"Errors: {len(result['errors'])}")
    for error in result['errors']:
        print(f"  - {error}")
```

---

### POST /api/v1/artifacts/discover/import

**Description:** Bulk import multiple discovered or specified artifacts.

**Purpose:** Import artifacts into the SkillMeat collection from list of sources.

#### Request

```http
POST /api/v1/artifacts/discover/import
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "artifacts": [
    {
      "source": "anthropics/skills/canvas-design@latest",
      "artifact_type": "skill",
      "name": "canvas-design",
      "description": "Create beautiful visual art",
      "author": "Anthropic",
      "tags": ["design", "canvas", "art"],
      "scope": "user"
    },
    {
      "source": "https://github.com/my-org/my-repo/tree/main/agents/research",
      "artifact_type": "agent",
      "tags": ["research", "ai"],
      "scope": "local"
    }
  ],
  "auto_resolve_conflicts": false,
  "apply_path_tags": true
}
```

**Parameters:**

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `artifacts` | array | Yes | List of artifacts to import (min 1) | - |
| `artifacts[].source` | string | Yes | GitHub source or local path (user/repo/path[@version] or full URL) | - |
| `artifacts[].artifact_type` | string | Yes | Type: skill, command, agent, hook, mcp | - |
| `artifacts[].name` | string | No | Artifact identifier (auto-derived from source if omitted) | auto-derived |
| `artifacts[].description` | string | No | Artifact description | None |
| `artifacts[].author` | string | No | Artifact author | None |
| `artifacts[].tags` | array | No | Tags/categories to apply | [] |
| `artifacts[].scope` | string | No | Scope: "user" or "local" | "user" |
| `auto_resolve_conflicts` | boolean | No | Overwrite existing artifacts | false |
| `apply_path_tags` | boolean | No | Apply approved path-based tags extracted from artifact paths to imported artifacts | true |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "total_requested": 3,
  "total_imported": 1,
  "total_skipped": 1,
  "total_failed": 1,
  "imported_to_collection": 1,
  "added_to_project": 1,
  "total_tags_applied": 5,
  "results": [
    {
      "artifact_id": "skill:canvas-design",
      "status": "success",
      "message": "Artifact 'canvas-design' imported successfully",
      "error": null,
      "skip_reason": null,
      "tags_applied": 3,
      "success": true
    },
    {
      "artifact_id": "skill:existing-skill",
      "status": "skipped",
      "message": "Artifact already exists",
      "error": null,
      "skip_reason": "Artifact already exists in collection",
      "tags_applied": 0,
      "success": false
    },
    {
      "artifact_id": "agent:research",
      "status": "failed",
      "message": "Import failed",
      "error": "Artifact already exists and auto_resolve_conflicts is false",
      "skip_reason": null,
      "tags_applied": 0,
      "success": false
    }
  ],
  "duration_ms": 1234.56,
  "summary": "1 imported, 1 skipped, 1 failed"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_requested` | integer | Number of artifacts requested for import |
| `total_imported` | integer | Number successfully imported |
| `total_skipped` | integer | Number skipped (already exist) |
| `total_failed` | integer | Number that failed |
| `imported_to_collection` | integer | Number added to the Collection |
| `added_to_project` | integer | Number deployed to the Project |
| `total_tags_applied` | integer | Total number of path-based tags applied across all artifacts (sum of per-artifact `tags_applied`) |
| `results` | array | Per-artifact import results |
| `results[].artifact_id` | string | Artifact identifier (type:name) |
| `results[].status` | string | Import status: "success", "skipped", or "failed" |
| `results[].message` | string | Human-readable status message |
| `results[].error` | string or null | Error message if status=failed |
| `results[].skip_reason` | string or null | Reason for skip if status=skipped |
| `results[].tags_applied` | integer | Number of path-based tags applied to this specific artifact (only non-zero when apply_path_tags=true) |
| `results[].success` | boolean | Backward compatibility: true if status=success |
| `duration_ms` | number | Total import duration in milliseconds |
| `summary` | string | Human-readable summary of import results |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Import operation completed (check per-artifact results) |
| 400 | Bad Request | Invalid request format or missing required fields |
| 401 | Unauthorized | Missing or invalid authentication token |
| 422 | Unprocessable Entity | Validation error in artifact data |
| 500 | Internal Server Error | Server error during import |

#### Examples

**Basic bulk import with path tags:**

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/discover/import \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "artifacts": [
      {
        "source": "anthropics/skills/canvas-design@latest",
        "artifact_type": "skill",
        "tags": ["design", "visual"]
      },
      {
        "source": "user/repo/agents/my-agent",
        "artifact_type": "agent",
        "name": "my-agent",
        "scope": "local"
      }
    ],
    "auto_resolve_conflicts": false,
    "apply_path_tags": true
  }'
```

**With auto-conflict resolution:**

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/discover/import \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "artifacts": [
      {
        "source": "anthropics/skills/pdf@v2.0.0",
        "artifact_type": "skill"
      }
    ],
    "auto_resolve_conflicts": true
  }'
```

**Python example:**

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

# Import multiple artifacts
import_data = {
    "artifacts": [
        {
            "source": "anthropics/skills/canvas-design@latest",
            "artifact_type": "skill",
            "tags": ["design", "visual"]
        },
        {
            "source": "user/repo/commands/cli-tool",
            "artifact_type": "command",
            "scope": "local"
        }
    ],
    "auto_resolve_conflicts": False,
    "apply_path_tags": True
}

response = requests.post(
    "http://localhost:8000/api/v1/artifacts/discover/import",
    headers=headers,
    json=import_data
)

result = response.json()
print(f"Requested: {result['total_requested']}")
print(f"Imported: {result['total_imported']}")
print(f"Failed: {result['total_failed']}")
print(f"Tags applied: {result['total_tags_applied']}")

for artifact_result in result['results']:
    if artifact_result['success']:
        tags_msg = f" ({artifact_result['tags_applied']} tags)" if artifact_result['tags_applied'] > 0 else ""
        print(f"✓ {artifact_result['artifact_id']}{tags_msg}")
    else:
        print(f"✗ {artifact_result['artifact_id']}: {artifact_result['error']}")
```

---

### GET /api/v1/artifacts/metadata/github

**Description:** Fetch metadata from GitHub for auto-population.

**Purpose:** Automatically populate artifact metadata from GitHub repository.

#### Request

```http
GET /api/v1/artifacts/metadata/github?source=anthropics/skills/canvas-design@latest
Authorization: Bearer <token>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | GitHub source: user/repo/path[@version] or full URL |

#### Response

**Status Code:** `200 OK`

**Response Body (Success):**

```json
{
  "success": true,
  "metadata": {
    "title": "Canvas Design Skill",
    "description": "Create beautiful visual art in PDF and PNG documents",
    "author": "Anthropic",
    "license": "MIT",
    "topics": ["design", "canvas", "art", "generative"],
    "url": "https://github.com/anthropics/skills/tree/main/canvas-design",
    "fetched_at": "2025-11-30T14:30:00Z",
    "source": "auto-populated"
  },
  "error": null
}
```

**Response Body (Failure):**

```json
{
  "success": false,
  "metadata": null,
  "error": "Repository not found or is inaccessible"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether fetch succeeded |
| `metadata` | object or null | Fetched metadata (if successful) |
| `metadata.title` | string | Artifact title |
| `metadata.description` | string | Artifact description |
| `metadata.author` | string | Repository owner or author |
| `metadata.license` | string | SPDX license identifier |
| `metadata.topics` | array | Repository topics/tags |
| `metadata.url` | string | Full GitHub URL to artifact |
| `metadata.fetched_at` | string | ISO 8601 fetch timestamp |
| `metadata.source` | string | Always "auto-populated" |
| `error` | string or null | Error message (if failed) |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Fetch completed (check success field) |
| 400 | Bad Request | Invalid source format |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Repository not found |
| 429 | Too Many Requests | GitHub API rate limit exceeded |
| 500 | Internal Server Error | Server error during fetch |

#### Examples

**Fetch metadata:**

```bash
curl http://localhost:8000/api/v1/artifacts/metadata/github \
  -H "Authorization: Bearer sk_test_abc123" \
  -G --data-urlencode "source=anthropics/skills/canvas-design@latest"
```

**With versioned source:**

```bash
curl http://localhost:8000/api/v1/artifacts/metadata/github \
  -H "Authorization: Bearer sk_test_abc123" \
  -G --data-urlencode "source=anthropics/skills/canvas-design@v2.1.0"
```

**With GitHub URL:**

```bash
curl http://localhost:8000/api/v1/artifacts/metadata/github \
  -H "Authorization: Bearer sk_test_abc123" \
  -G --data-urlencode "source=https://github.com/anthropics/skills/tree/main/canvas-design"
```

**Python example:**

```python
import requests
from urllib.parse import urlencode

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

# Fetch metadata from GitHub
source = "anthropics/skills/canvas-design@latest"
url = f"http://localhost:8000/api/v1/artifacts/metadata/github?source={source}"

response = requests.get(url, headers=headers)
result = response.json()

if result['success']:
    metadata = result['metadata']
    print(f"Title: {metadata['title']}")
    print(f"Description: {metadata['description']}")
    print(f"Author: {metadata['author']}")
    print(f"License: {metadata['license']}")
    print(f"Topics: {', '.join(metadata['topics'])}")
else:
    print(f"Error: {result['error']}")
```

---

### PUT /api/v1/artifacts/{artifact_id}/parameters

**Description:** Update artifact parameters (tags, scope, version, source).

**Purpose:** Modify artifact configuration after import.

#### Request

```http
PUT /api/v1/artifacts/skill:canvas-design/parameters
Authorization: Bearer <token>
Content-Type: application/json
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_id` | string | Yes | Artifact identifier (type:name, e.g., skill:canvas-design) |

**Request Body:**

```json
{
  "parameters": {
    "source": "anthropics/skills/canvas-design@v2.0.0",
    "version": "v2.0.0",
    "scope": "user",
    "tags": ["design", "canvas", "art", "generative"],
    "aliases": ["canvas", "design-tool"]
  }
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parameters` | object | Yes | Parameters object |
| `parameters.source` | string | No | GitHub source or local path |
| `parameters.version` | string | No | Version specification |
| `parameters.scope` | string | No | Scope: "user" or "local" |
| `parameters.tags` | array | No | Tags (replaces existing) |
| `parameters.aliases` | array | No | Aliases (replaces existing) |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "success": true,
  "artifact_id": "skill:canvas-design",
  "updated_fields": ["source", "version", "tags"],
  "message": "Artifact 'canvas-design' parameters updated successfully"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether update succeeded |
| `artifact_id` | string | Updated artifact identifier |
| `updated_fields` | array | Fields that were updated |
| `message` | string | Human-readable status message |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Parameters updated successfully |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Artifact not found |
| 422 | Unprocessable Entity | Validation error in parameters |
| 500 | Internal Server Error | Server error during update |

#### Examples

**Update tags and version:**

```bash
curl -X PUT http://localhost:8000/api/v1/artifacts/skill:canvas-design/parameters \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "version": "v2.1.0",
      "tags": ["design", "visual", "pdf", "png", "ai"]
    }
  }'
```

**Change scope:**

```bash
curl -X PUT http://localhost:8000/api/v1/artifacts/command:my-command/parameters \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "scope": "local"
    }
  }'
```

**Add aliases:**

```bash
curl -X PUT http://localhost:8000/api/v1/artifacts/agent:research/parameters \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "aliases": ["research-agent", "research", "info-gatherer"]
    }
  }'
```

**Python example:**

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

artifact_id = "skill:canvas-design"
url = f"http://localhost:8000/api/v1/artifacts/{artifact_id}/parameters"

update_data = {
    "parameters": {
        "version": "v2.1.0",
        "tags": ["design", "visual", "pdf", "png"],
        "scope": "user"
    }
}

response = requests.put(url, headers=headers, json=update_data)
result = response.json()

if result['success']:
    print(f"Updated: {result['artifact_id']}")
    print(f"Fields changed: {', '.join(result['updated_fields'])}")
else:
    print(f"Error: {result.get('error', 'Unknown error')}")
```

---

### POST /api/v1/projects/{project_id}/skip-preferences

**Description:** Add a skip preference for an artifact in a specific project.

**Purpose:** Mark artifacts to skip during discovery and import operations within a project scope.

#### Request

```http
POST /api/v1/projects/my-project/skip-preferences
Authorization: Bearer <token>
Content-Type: application/json
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier (path-based, e.g., /path/to/project) |

**Request Body:**

```json
{
  "artifact_key": "skill:canvas-design",
  "skip_reason": "Already have a newer version in use"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_key` | string | Yes | Artifact identifier (format: type:name) |
| `skip_reason` | string | Yes | Human-readable reason for skipping |

#### Response

**Status Code:** `201 Created`

**Response Body:**

```json
{
  "artifact_key": "skill:canvas-design",
  "skip_reason": "Already have a newer version in use",
  "added_date": "2025-12-04T10:00:00Z"
}
```

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 201 | Created | Skip preference added successfully |
| 400 | Bad Request | Invalid artifact_key or skip_reason format |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Project not found |
| 422 | Unprocessable Entity | Validation error in request body |
| 500 | Internal Server Error | Server error during operation |

#### Examples

```bash
curl -X POST http://localhost:8000/api/v1/projects/my-project/skip-preferences \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_key": "skill:canvas-design",
    "skip_reason": "Already have it installed"
  }'
```

---

### DELETE /api/v1/projects/{project_id}/skip-preferences/{artifact_key}

**Description:** Remove a single skip preference by artifact key.

**Purpose:** Unmark an artifact that was previously skipped.

#### Request

```http
DELETE /api/v1/projects/my-project/skip-preferences/skill:canvas-design
Authorization: Bearer <token>
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier |
| `artifact_key` | string | Yes | Artifact identifier (format: type:name) |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "artifact_key": "skill:canvas-design",
  "message": "Removed skip preference for 'skill:canvas-design'"
}
```

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Skip preference removed successfully |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Project or skip preference not found |
| 500 | Internal Server Error | Server error during operation |

#### Examples

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/my-project/skip-preferences/skill:canvas-design \
  -H "Authorization: Bearer sk_test_abc123"
```

---

### DELETE /api/v1/projects/{project_id}/skip-preferences

**Description:** Clear all skip preferences for a project.

**Purpose:** Remove all skip preferences at once for a project.

#### Request

```http
DELETE /api/v1/projects/my-project/skip-preferences
Authorization: Bearer <token>
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "success": true,
  "cleared_count": 5,
  "message": "Cleared 5 skip preferences"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether operation succeeded |
| `cleared_count` | integer | Number of skip preferences removed |
| `message` | string | Human-readable status message |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Skip preferences cleared successfully |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Project not found |
| 500 | Internal Server Error | Server error during operation |

#### Examples

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/my-project/skip-preferences \
  -H "Authorization: Bearer sk_test_abc123"
```

---

### GET /api/v1/projects/{project_id}/skip-preferences

**Description:** List all skip preferences for a project.

**Purpose:** View artifacts that are marked to skip in a project.

#### Request

```http
GET /api/v1/projects/my-project/skip-preferences
Authorization: Bearer <token>
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "skips": [
    {
      "artifact_key": "skill:canvas-design",
      "skip_reason": "Already have a newer version",
      "added_date": "2025-12-04T10:00:00Z"
    },
    {
      "artifact_key": "command:my-command",
      "skip_reason": "Not needed for this project",
      "added_date": "2025-12-04T11:00:00Z"
    }
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `skips` | array | List of skip preferences |
| `skips[].artifact_key` | string | Artifact identifier (type:name) |
| `skips[].skip_reason` | string | Reason for skipping |
| `skips[].added_date` | string | ISO 8601 timestamp when added |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Skip preferences retrieved successfully |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Project not found |
| 500 | Internal Server Error | Server error during operation |

#### Examples

```bash
curl http://localhost:8000/api/v1/projects/my-project/skip-preferences \
  -H "Authorization: Bearer sk_test_abc123" | jq '.skips'
```

---

## Import Result Status Enum

The `ImportResult.status` field can have one of three values:

### success

**When:** Artifact was successfully imported into the collection or project.

**Behavior:**
- Artifact is now available for use
- No `error` field is populated
- No `skip_reason` field is populated
- `success` backward-compatibility field is `true`

**Example:**
```json
{
  "artifact_id": "skill:canvas-design",
  "status": "success",
  "message": "Artifact 'canvas-design' imported successfully",
  "error": null,
  "skip_reason": null,
  "success": true
}
```

### skipped

**When:** Artifact was not imported because it already exists.

**Behavior:**
- Artifact import is skipped to avoid duplicates
- `skip_reason` field explains why (e.g., "Artifact already exists in collection")
- No `error` field is populated (not a failure)
- `success` backward-compatibility field is `false`

**Reasons for Skip:**
- Artifact already exists in collection
- Artifact already exists in project
- Artifact marked in skip preferences
- Auto-resolve conflicts disabled

**Example:**
```json
{
  "artifact_id": "skill:existing-skill",
  "status": "skipped",
  "message": "Artifact already exists",
  "error": null,
  "skip_reason": "Artifact already exists in collection",
  "success": false
}
```

### failed

**When:** Artifact import failed due to an error.

**Behavior:**
- Artifact was not imported due to an error condition
- `error` field contains the error message
- No `skip_reason` field is populated
- `success` backward-compatibility field is `false`

**Common Failure Reasons:**
- Network error fetching artifact source
- Invalid artifact format or metadata
- Permission denied accessing artifact path
- Corrupted or incomplete artifact
- Dependency resolution failed

**Example:**
```json
{
  "artifact_id": "agent:research",
  "status": "failed",
  "message": "Import failed",
  "error": "Failed to parse artifact metadata: invalid YAML",
  "skip_reason": null,
  "success": false
}
```

---

## Status Codes

### Common HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error in request body |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | API unavailable |
| 503 | Service Unavailable | Maintenance or overload |

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "parameter_name",
      "constraint": "validation_constraint"
    }
  },
  "request_id": "req_abc123xyz"
}
```

### Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| `UNAUTHORIZED` | Missing or invalid token | Check API token configuration |
| `VALIDATION_ERROR` | Invalid request data | Review request format |
| `NOT_FOUND` | Resource doesn't exist | Verify artifact_id or path |
| `CONFLICT` | Artifact already exists | Use auto_resolve_conflicts or delete existing |
| `RATE_LIMITED` | Too many requests | Wait before retrying (rate limits reset hourly) |
| `GITHUB_ERROR` | GitHub API error | Check repository exists and is accessible |
| `INVALID_SOURCE` | Source format invalid | Use format: user/repo/path[@version] |

### Retry Logic

For retryable errors (429, 502, 503):

```python
import requests
import time

def fetch_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            wait_time = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited, waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        return response

    raise Exception("Max retries exceeded")
```

## Rate Limiting

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1701346800
```

### Rate Limit Windows

- **Default:** 100 requests per minute per user
- **GitHub metadata:** Separate rate limiting (5000 req/hour with token)
- **Bulk import:** Counted per artifact

### Handling Rate Limits

When rate limited:

1. **Check headers** - See X-RateLimit-Reset timestamp
2. **Wait** - Pause requests until reset time
3. **Retry** - Resume requests after reset

```python
import requests
from datetime import datetime

response = requests.get(url, headers=headers)

if response.status_code == 429:
    reset_time = int(response.headers['X-RateLimit-Reset'])
    wait_seconds = reset_time - datetime.now().timestamp()
    print(f"Wait {wait_seconds} seconds before retrying")
```

## Examples

### Complete Workflow Example

```python
import requests
import json

class SkillMeatClient:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "http://localhost:8000/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def discover_artifacts(self, scan_path=None):
        """Discover artifacts in local directories."""
        url = f"{self.base_url}/artifacts/discover"
        data = {}
        if scan_path:
            data["scan_path"] = scan_path

        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def import_artifacts(self, artifacts, auto_resolve=False, apply_path_tags=True):
        """Bulk import artifacts.

        Args:
            artifacts: List of artifact specifications to import
            auto_resolve: Whether to overwrite existing artifacts
            apply_path_tags: Whether to apply path-based tags during import
        """
        url = f"{self.base_url}/artifacts/discover/import"
        data = {
            "artifacts": artifacts,
            "auto_resolve_conflicts": auto_resolve,
            "apply_path_tags": apply_path_tags
        }

        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def fetch_github_metadata(self, source):
        """Fetch metadata from GitHub."""
        url = f"{self.base_url}/artifacts/metadata/github"
        params = {"source": source}

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def update_artifact_parameters(self, artifact_id, parameters):
        """Update artifact parameters."""
        url = f"{self.base_url}/artifacts/{artifact_id}/parameters"
        data = {"parameters": parameters}

        response = requests.put(url, headers=self.headers, json=data)
        return response.json()

# Example usage
client = SkillMeatClient("sk_test_abc123")

# 1. Discover local artifacts
discovery = client.discover_artifacts()
print(f"Found {discovery['discovered_count']} artifacts")

# 2. Fetch GitHub metadata for one
metadata = client.fetch_github_metadata("anthropics/skills/canvas-design@latest")
if metadata['success']:
    print(f"Title: {metadata['metadata']['title']}")

# 3. Bulk import artifacts
artifacts_to_import = [
    {
        "source": "anthropics/skills/canvas-design@latest",
        "artifact_type": "skill",
        "tags": ["design", "visual"]
    },
    {
        "source": "user/repo/agents/research",
        "artifact_type": "agent",
        "scope": "local"
    }
]

import_result = client.import_artifacts(artifacts_to_import)
print(f"Imported {import_result['total_imported']} artifacts")

# 4. Update parameters
update_result = client.update_artifact_parameters(
    "skill:canvas-design",
    {
        "version": "v2.0.0",
        "tags": ["design", "visual", "pdf", "png"]
    }
)
print(f"Updated: {update_result['message']}")
```

### Bash Examples

**Discover artifacts:**

```bash
API_TOKEN="sk_test_abc123"

curl -X POST http://localhost:8000/api/v1/artifacts/discover \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" | jq '.artifacts[] | {name, type, tags}'
```

**Fetch GitHub metadata:**

```bash
API_TOKEN="sk_test_abc123"
SOURCE="anthropics/skills/canvas-design@latest"

curl "http://localhost:8000/api/v1/artifacts/metadata/github?source=$SOURCE" \
  -H "Authorization: Bearer $API_TOKEN" | jq '.metadata'
```

**Bulk import:**

```bash
API_TOKEN="sk_test_abc123"

curl -X POST http://localhost:8000/api/v1/artifacts/discover/import \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "artifacts": [
    {
      "source": "anthropics/skills/canvas-design@latest",
      "artifact_type": "skill",
      "tags": ["design"]
    }
  ],
  "auto_resolve_conflicts": false
}
EOF
```
