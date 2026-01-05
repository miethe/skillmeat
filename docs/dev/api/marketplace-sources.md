---
title: Marketplace Sources API
description: Complete API reference for managing GitHub repository sources and discovering artifacts in the SkillMeat marketplace
audience: developers
tags: [api, marketplace, sources, github]
created: 2025-12-08
updated: 2025-12-08
category: API Documentation
status: published
related: [discovery-endpoints.md]
---

# Marketplace Sources API Documentation

Complete API reference for SkillMeat's Marketplace Sources endpoints that manage GitHub repository sources and discover artifacts within them.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
  - [POST /marketplace/sources](#post-marketplacesources)
  - [GET /marketplace/sources](#get-marketplacesources)
  - [GET /marketplace/sources/{source_id}](#get-marketplacesourcessource_id)
  - [PATCH /marketplace/sources/{source_id}](#patch-marketplacesourcessource_id)
  - [DELETE /marketplace/sources/{source_id}](#delete-marketplacesourcessource_id)
  - [POST /marketplace/sources/{source_id}/rescan](#post-marketplacesourcessource_idrescan)
  - [GET /marketplace/sources/{source_id}/artifacts](#get-marketplacesourcessource_idartifacts)
  - [POST /marketplace/sources/{source_id}/import](#post-marketplacesourcessource_idimport)
  - [GET /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags](#get-marketplacesourcessource_idcatalogentry_idpath-tags)
  - [PATCH /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags](#patch-marketplacesourcessource_idcatalogentry_idpath-tags)
- [Status Codes](#status-codes)
- [Error Handling](#error-handling)
- [Data Models](#data-models)
- [Examples](#examples)

## Overview

The Marketplace Sources API provides endpoints for:

- **Adding GitHub repositories** as sources for artifact discovery
- **Listing and managing** multiple repository sources
- **Scanning repositories** to detect Claude Code artifacts (skills, commands, agents, etc.)
- **Listing detected artifacts** with filtering and pagination
- **Importing artifacts** from the catalog to your local collection

### Typical Workflow

```
1. Create source → POST /marketplace/sources
2. Trigger scan  → POST /marketplace/sources/{id}/rescan
3. List artifacts → GET /marketplace/sources/{id}/artifacts
4. Filter results → GET /marketplace/sources/{id}/artifacts?artifact_type=skill
5. Import selected → POST /marketplace/sources/{id}/import
```

### Base URL

```
https://api.skillmeat.local/api/v1
```

Or for development:

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require authentication via Bearer token in the Authorization header:

```http
Authorization: Bearer <your_api_token>
```

### Note on Authentication

Currently, authentication is a placeholder. Multi-user support and proper authentication will be implemented in future versions.

## Endpoints

### POST /marketplace/sources

**Description:** Create a new GitHub repository source.

**Purpose:** Add a GitHub repository to the marketplace for artifact discovery and scanning.

#### Request

```http
POST /api/v1/marketplace/sources
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
  "ref": "main",
  "root_hint": "skills",
  "trust_level": "verified",
  "access_token": null,
  "manual_map": null
}
```

**Parameters:**

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `repo_url` | string | Yes | Full GitHub repository URL | — |
| `ref` | string | No | Branch, tag, or commit SHA to scan | `"main"` |
| `root_hint` | string | No | Subdirectory path to start scanning (e.g., "skills", "src/artifacts") | `null` |
| `trust_level` | string | No | Trust level for artifacts: `untrusted`, `basic`, `verified`, `official` | `"basic"` |
| `access_token` | string | No | GitHub Personal Access Token for private repos (not stored) | `null` |
| `manual_map` | object | No | Manual override: artifact_type → list of paths | `null` |

**Example Request with root_hint:**

```bash
curl -X POST http://localhost:8000/api/v1/marketplace/sources \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
    "ref": "main",
    "root_hint": "skills",
    "trust_level": "verified"
  }'
```

#### Response

**Status Code:** `201 Created`

**Response Body:**

```json
{
  "id": "src_anthropics_quickstarts",
  "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
  "owner": "anthropics",
  "repo_name": "anthropic-quickstarts",
  "ref": "main",
  "root_hint": "skills",
  "trust_level": "verified",
  "visibility": "public",
  "scan_status": "pending",
  "artifact_count": 0,
  "last_sync_at": null,
  "last_error": null,
  "created_at": "2025-12-06T10:00:00Z",
  "updated_at": "2025-12-06T10:00:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique source identifier |
| `repo_url` | string | Full GitHub repository URL |
| `owner` | string | Repository owner username |
| `repo_name` | string | Repository name (extracted from URL) |
| `ref` | string | Currently tracked branch/tag/SHA |
| `root_hint` | string or null | Subdirectory hint for scanning |
| `trust_level` | string | Trust level: untrusted, basic, verified, official |
| `visibility` | string | Repository visibility: public or private |
| `scan_status` | string | Current scan status: pending, scanning, success, error |
| `artifact_count` | integer | Number of artifacts detected (0 until first scan) |
| `last_sync_at` | string or null | ISO 8601 timestamp of last successful scan |
| `last_error` | string or null | Last error message if scan failed |
| `created_at` | string | ISO 8601 timestamp when source was added |
| `updated_at` | string | ISO 8601 timestamp when source was last modified |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 201 | Created | Source created successfully |
| 400 | Bad Request | Invalid repository URL format |
| 409 | Conflict | Repository URL already exists as a source |
| 500 | Internal Server Error | Server error during creation |

#### Error Examples

**Invalid URL format:**

```json
{
  "detail": "Invalid GitHub repository URL format. Expected: https://github.com/owner/repo, got: invalid-url"
}
```

**URL already exists:**

```json
{
  "detail": "Source with repository URL 'https://github.com/anthropics/anthropic-quickstarts' already exists"
}
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

# Create new source
response = requests.post(
    "http://localhost:8000/api/v1/marketplace/sources",
    headers=headers,
    json={
        "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
        "ref": "main",
        "root_hint": "skills",
        "trust_level": "verified"
    }
)

source = response.json()
print(f"Created source: {source['id']}")
print(f"Status: {source['scan_status']}")
```

---

### GET /marketplace/sources

**Description:** List all GitHub repository sources with cursor-based pagination.

**Purpose:** Retrieve all configured marketplace sources.

#### Request

```http
GET /api/v1/marketplace/sources?limit=50&cursor=null
Authorization: Bearer <token>
```

**Query Parameters:**

| Parameter | Type | Required | Description | Default | Range |
|-----------|------|----------|-------------|---------|-------|
| `limit` | integer | No | Maximum items per page | `50` | 1-100 |
| `cursor` | string | No | Cursor from previous response for pagination | `null` | — |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "items": [
    {
      "id": "src_anthropics_quickstarts",
      "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
      "owner": "anthropics",
      "repo_name": "anthropic-quickstarts",
      "ref": "main",
      "root_hint": "skills",
      "trust_level": "verified",
      "visibility": "public",
      "scan_status": "success",
      "artifact_count": 12,
      "last_sync_at": "2025-12-06T10:30:00Z",
      "last_error": null,
      "created_at": "2025-12-05T09:00:00Z",
      "updated_at": "2025-12-06T10:30:00Z"
    },
    {
      "id": "src_user_repo",
      "repo_url": "https://github.com/user/custom-repo",
      "owner": "user",
      "repo_name": "custom-repo",
      "ref": "develop",
      "root_hint": null,
      "trust_level": "basic",
      "visibility": "private",
      "scan_status": "pending",
      "artifact_count": 0,
      "last_sync_at": null,
      "last_error": null,
      "created_at": "2025-12-07T14:00:00Z",
      "updated_at": "2025-12-07T14:00:00Z"
    }
  ],
  "page_info": {
    "has_next_page": false,
    "has_previous_page": false,
    "start_cursor": "src_anthropics_quickstarts",
    "end_cursor": "src_user_repo",
    "total_count": null
  }
}
```

**Pagination:**

- Uses cursor-based pagination for stable ordering
- `has_next_page` indicates if more results exist
- Use `end_cursor` as the `cursor` parameter for next request
- `total_count` is `null` for efficiency (not computed for large result sets)

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Request successful |
| 500 | Internal Server Error | Database operation failed |

#### Examples

**List first page:**

```bash
curl http://localhost:8000/api/v1/marketplace/sources \
  -H "Authorization: Bearer sk_test_abc123" | jq '.items[] | {id, repo_name, artifact_count}'
```

**List with custom page size:**

```bash
curl "http://localhost:8000/api/v1/marketplace/sources?limit=10" \
  -H "Authorization: Bearer sk_test_abc123"
```

**Get next page:**

```bash
curl "http://localhost:8000/api/v1/marketplace/sources?limit=50&cursor=src_anthropics_quickstarts" \
  -H "Authorization: Bearer sk_test_abc123"
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

# List sources
response = requests.get(
    "http://localhost:8000/api/v1/marketplace/sources?limit=50",
    headers=headers
)

result = response.json()
print(f"Found {len(result['items'])} sources")

for source in result['items']:
    print(f"  - {source['repo_name']}: {source['artifact_count']} artifacts")

# Check for next page
if result['page_info']['has_next_page']:
    next_cursor = result['page_info']['end_cursor']
    print(f"More sources available. Next cursor: {next_cursor}")
```

---

### GET /marketplace/sources/{source_id}

**Description:** Retrieve a specific GitHub repository source by its ID.

**Purpose:** Get detailed information about a particular source.

#### Request

```http
GET /api/v1/marketplace/sources/src_anthropics_quickstarts
Authorization: Bearer <token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Unique source identifier |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "id": "src_anthropics_quickstarts",
  "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
  "owner": "anthropics",
  "repo_name": "anthropic-quickstarts",
  "ref": "main",
  "root_hint": "skills",
  "trust_level": "verified",
  "visibility": "public",
  "scan_status": "success",
  "artifact_count": 12,
  "last_sync_at": "2025-12-06T10:30:00Z",
  "last_error": null,
  "created_at": "2025-12-05T09:00:00Z",
  "updated_at": "2025-12-06T10:30:00Z"
}
```

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Source found |
| 404 | Not Found | Source does not exist |
| 500 | Internal Server Error | Database error |

#### Examples

**Get source details:**

```bash
curl http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts \
  -H "Authorization: Bearer sk_test_abc123" | jq '.'
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

source_id = "src_anthropics_quickstarts"
response = requests.get(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}",
    headers=headers
)

if response.status_code == 200:
    source = response.json()
    print(f"Repository: {source['repo_url']}")
    print(f"Status: {source['scan_status']}")
    print(f"Artifacts: {source['artifact_count']}")
elif response.status_code == 404:
    print(f"Source '{source_id}' not found")
```

---

### PATCH /marketplace/sources/{source_id}

**Description:** Update a GitHub repository source configuration.

**Purpose:** Modify source settings (branch, subdirectory, trust level).

#### Request

```http
PATCH /api/v1/marketplace/sources/src_anthropics_quickstarts?ref=develop&trust_level=official
Authorization: Bearer <token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Unique source identifier |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ref` | string | No | New branch, tag, or commit SHA |
| `root_hint` | string | No | New subdirectory path |
| `trust_level` | string | No | New trust level: untrusted, basic, verified, official |

**At least one query parameter must be provided.**

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "id": "src_anthropics_quickstarts",
  "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
  "owner": "anthropics",
  "repo_name": "anthropic-quickstarts",
  "ref": "develop",
  "root_hint": "skills",
  "trust_level": "official",
  "visibility": "public",
  "scan_status": "success",
  "artifact_count": 12,
  "last_sync_at": "2025-12-06T10:30:00Z",
  "last_error": null,
  "created_at": "2025-12-05T09:00:00Z",
  "updated_at": "2025-12-08T15:00:00Z"
}
```

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Source updated successfully |
| 400 | Bad Request | No update parameters provided |
| 404 | Not Found | Source does not exist |
| 500 | Internal Server Error | Database error |

#### Error Examples

**No parameters provided:**

```json
{
  "detail": "At least one update parameter must be provided"
}
```

#### Examples

**Switch to different branch:**

```bash
curl -X PATCH "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts?ref=develop" \
  -H "Authorization: Bearer sk_test_abc123"
```

**Update trust level:**

```bash
curl -X PATCH "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts?trust_level=official" \
  -H "Authorization: Bearer sk_test_abc123"
```

**Change both ref and root_hint:**

```bash
curl -X PATCH "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts?ref=v1.0.0&root_hint=src/artifacts" \
  -H "Authorization: Bearer sk_test_abc123"
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

source_id = "src_anthropics_quickstarts"

# Update to track develop branch
response = requests.patch(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}",
    headers=headers,
    params={"ref": "develop"}
)

if response.status_code == 200:
    source = response.json()
    print(f"Updated source to track: {source['ref']}")
else:
    print(f"Error: {response.json()}")
```

---

### DELETE /marketplace/sources/{source_id}

**Description:** Delete a GitHub repository source and all its associated catalog entries.

**Purpose:** Remove a source and clean up all detected artifacts from it.

**WARNING:** This operation cannot be undone and removes all catalog entries for this source.

#### Request

```http
DELETE /api/v1/marketplace/sources/src_anthropics_quickstarts
Authorization: Bearer <token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Unique source identifier |

#### Response

**Status Code:** `204 No Content`

Response body is empty.

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 204 | No Content | Source deleted successfully |
| 404 | Not Found | Source does not exist |
| 500 | Internal Server Error | Database error |

#### Examples

**Delete a source:**

```bash
curl -X DELETE http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts \
  -H "Authorization: Bearer sk_test_abc123"
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

source_id = "src_anthropics_quickstarts"

response = requests.delete(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}",
    headers=headers
)

if response.status_code == 204:
    print(f"Source '{source_id}' deleted successfully")
elif response.status_code == 404:
    print(f"Source not found")
else:
    print(f"Error: {response.status_code}")
```

---

### POST /marketplace/sources/{source_id}/rescan

**Description:** Trigger a rescan of a GitHub repository to discover artifacts.

**Purpose:** Scan the repository to find and catalog Claude Code artifacts (skills, commands, agents, etc.).

#### Request

```http
POST /api/v1/marketplace/sources/src_anthropics_quickstarts/rescan
Authorization: Bearer <token>
Content-Type: application/json
```

**Optional Request Body:**

```json
{
  "force": false
}
```

**Parameters:**

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `force` | boolean | No | Force rescan even if recently scanned | `false` |

#### Response

**Status Code:** `200 OK`

**Response Body (Success):**

```json
{
  "source_id": "src_anthropics_quickstarts",
  "status": "success",
  "artifacts_found": 12,
  "new_count": 3,
  "updated_count": 2,
  "removed_count": 1,
  "unchanged_count": 6,
  "scan_duration_ms": 1234.56,
  "errors": [],
  "scanned_at": "2025-12-06T10:35:00Z"
}
```

**Response Body (Error):**

```json
{
  "source_id": "src_anthropics_quickstarts",
  "status": "error",
  "artifacts_found": 0,
  "new_count": 0,
  "updated_count": 0,
  "removed_count": 0,
  "unchanged_count": 0,
  "scan_duration_ms": 0,
  "errors": ["Failed to fetch repository: 404 Not Found"],
  "scanned_at": "2025-12-06T10:35:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | string | ID of the source that was scanned |
| `status` | string | Scan result: success, error, or partial |
| `artifacts_found` | integer | Total number of artifacts detected |
| `new_count` | integer | Number of newly detected artifacts |
| `updated_count` | integer | Number of artifacts with changes |
| `removed_count` | integer | Number of artifacts no longer present |
| `unchanged_count` | integer | Number of artifacts with no changes |
| `scan_duration_ms` | number | Scan duration in milliseconds |
| `errors` | array | List of error messages encountered |
| `scanned_at` | string | ISO 8601 timestamp when scan completed |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Scan completed (check status field) |
| 404 | Not Found | Source does not exist |
| 500 | Internal Server Error | Scan operation failed |

#### Examples

**Trigger scan:**

```bash
curl -X POST http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/rescan \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json"
```

**Force rescan:**

```bash
curl -X POST http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/rescan \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

source_id = "src_anthropics_quickstarts"

# Trigger scan
response = requests.post(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}/rescan",
    headers=headers
)

result = response.json()
print(f"Scan Status: {result['status']}")
print(f"Artifacts Found: {result['artifacts_found']}")
print(f"New: {result['new_count']}, Updated: {result['updated_count']}")
print(f"Duration: {result['scan_duration_ms']:.2f}ms")

if result['errors']:
    print("Errors:")
    for error in result['errors']:
        print(f"  - {error}")
```

---

### GET /marketplace/sources/{source_id}/artifacts

**Description:** List all artifacts discovered in a source with optional filtering.

**Purpose:** View detected artifacts with filtering by type, status, and confidence.

#### Request

```http
GET /api/v1/marketplace/sources/src_anthropics_quickstarts/artifacts?artifact_type=skill&status=new&limit=50
Authorization: Bearer <token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Unique source identifier |

**Query Parameters:**

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `artifact_type` | string | No | Filter by type: skill, command, agent, mcp_server, hook | — |
| `status` | string | No | Filter by status: new, updated, removed, imported | — |
| `min_confidence` | integer | No | Minimum confidence score (0-100) | — |
| `limit` | integer | No | Items per page | `50` |
| `cursor` | string | No | Pagination cursor | `null` |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "items": [
    {
      "id": "cat_canvas_design",
      "source_id": "src_anthropics_quickstarts",
      "artifact_type": "skill",
      "name": "canvas-design",
      "path": "skills/canvas-design",
      "upstream_url": "https://github.com/anthropics/quickstarts/tree/main/skills/canvas-design",
      "detected_version": "1.2.0",
      "detected_sha": "abc123def456",
      "detected_at": "2025-12-06T10:30:00Z",
      "confidence_score": 95,
      "status": "new",
      "import_date": null,
      "import_id": null
    },
    {
      "id": "cat_pdf_skill",
      "source_id": "src_anthropics_quickstarts",
      "artifact_type": "skill",
      "name": "pdf-processing",
      "path": "skills/pdf-processing",
      "upstream_url": "https://github.com/anthropics/quickstarts/tree/main/skills/pdf-processing",
      "detected_version": "2.0.0",
      "detected_sha": "abc123def456",
      "detected_at": "2025-12-06T10:30:00Z",
      "confidence_score": 88,
      "status": "new",
      "import_date": null,
      "import_id": null
    }
  ],
  "page_info": {
    "has_next_page": false,
    "has_previous_page": false,
    "start_cursor": "cat_canvas_design",
    "end_cursor": "cat_pdf_skill",
    "total_count": null
  },
  "counts_by_status": {
    "new": 8,
    "updated": 2,
    "removed": 1,
    "imported": 1
  },
  "counts_by_type": {
    "skill": 9,
    "command": 2,
    "agent": 1
  }
}
```

**Pagination:**

- Uses cursor-based pagination
- `counts_by_status` and `counts_by_type` show aggregated statistics across all artifacts in source
- Filters apply to the list items, not the counts

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Artifacts retrieved |
| 404 | Not Found | Source does not exist |
| 500 | Internal Server Error | Database error |

#### Examples

**List all artifacts from source:**

```bash
curl "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/artifacts" \
  -H "Authorization: Bearer sk_test_abc123" | jq '.items[] | {name, artifact_type, status}'
```

**Filter by artifact type:**

```bash
curl "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/artifacts?artifact_type=skill" \
  -H "Authorization: Bearer sk_test_abc123"
```

**Filter by status and confidence:**

```bash
curl "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/artifacts?status=new&min_confidence=90" \
  -H "Authorization: Bearer sk_test_abc123"
```

**Paginate results:**

```bash
curl "http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/artifacts?limit=10&cursor=cat_canvas_design" \
  -H "Authorization: Bearer sk_test_abc123"
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

source_id = "src_anthropics_quickstarts"

# Get high-confidence new artifacts
response = requests.get(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}/artifacts",
    headers=headers,
    params={
        "status": "new",
        "min_confidence": 90,
        "limit": 50
    }
)

result = response.json()
print(f"Found {len(result['items'])} new artifacts (confidence >= 90)")

# Show statistics
print("\nCounts by Status:")
for status, count in result['counts_by_status'].items():
    print(f"  {status}: {count}")

print("\nCounts by Type:")
for atype, count in result['counts_by_type'].items():
    print(f"  {atype}: {count}")

# List artifacts
for artifact in result['items']:
    print(f"\n{artifact['name']} ({artifact['artifact_type']})")
    print(f"  Path: {artifact['path']}")
    print(f"  Version: {artifact['detected_version']}")
    print(f"  Confidence: {artifact['confidence_score']}")
```

---

### POST /marketplace/sources/{source_id}/import

**Description:** Import selected artifacts from the catalog to your local collection.

**Purpose:** Download and install discovered artifacts into your SkillMeat collection.

#### Request

```http
POST /api/v1/marketplace/sources/src_anthropics_quickstarts/import
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "entry_ids": ["cat_canvas_design", "cat_pdf_skill"],
  "conflict_strategy": "skip"
}
```

**Parameters:**

| Field | Type | Required | Description | Options |
|-------|------|----------|-------------|---------|
| `entry_ids` | array | Yes | List of catalog entry IDs to import (min 1) | — |
| `conflict_strategy` | string | No | How to handle conflicts with existing artifacts | `skip`, `overwrite`, `rename` |

**Conflict Strategies:**

- `skip` - Skip any artifacts that already exist locally (default)
- `overwrite` - Replace existing artifacts with imported versions
- `rename` - Rename imported artifacts with a suffix (e.g., `-imported-1`)

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "imported_count": 2,
  "skipped_count": 0,
  "error_count": 0,
  "imported_ids": ["cat_canvas_design", "cat_pdf_skill"],
  "skipped_ids": [],
  "errors": []
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `imported_count` | integer | Number of artifacts successfully imported |
| `skipped_count` | integer | Number of artifacts skipped (conflicts or other reasons) |
| `error_count` | integer | Number of artifacts that failed to import |
| `imported_ids` | array | List of entry IDs that were imported |
| `skipped_ids` | array | List of entry IDs that were skipped |
| `errors` | array | List of {entry_id, error} for failed imports |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Import completed (check counts for details) |
| 400 | Bad Request | entry_ids is empty or invalid |
| 404 | Not Found | Source not found or entry IDs don't belong to source |
| 500 | Internal Server Error | Import operation failed |

#### Error Examples

**Empty entry_ids:**

```json
{
  "detail": "entry_ids cannot be empty"
}
```

**Entry doesn't belong to source:**

```json
{
  "detail": "Entry 'cat_other_source' does not belong to source 'src_anthropics_quickstarts'"
}
```

#### Examples

**Import specific artifacts:**

```bash
curl -X POST http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/import \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_ids": ["cat_canvas_design", "cat_pdf_skill"],
    "conflict_strategy": "skip"
  }'
```

**Import with overwrite:**

```bash
curl -X POST http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/import \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_ids": ["cat_canvas_design"],
    "conflict_strategy": "overwrite"
  }'
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

source_id = "src_anthropics_quickstarts"
entry_ids = ["cat_canvas_design", "cat_pdf_skill"]

# Import artifacts
response = requests.post(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}/import",
    headers=headers,
    json={
        "entry_ids": entry_ids,
        "conflict_strategy": "skip"
    }
)

result = response.json()
print(f"Import Results:")
print(f"  Imported: {result['imported_count']}")
print(f"  Skipped: {result['skipped_count']}")
print(f"  Errors: {result['error_count']}")

if result['imported_ids']:
    print("\nImported:")
    for entry_id in result['imported_ids']:
        print(f"  ✓ {entry_id}")

if result['errors']:
    print("\nErrors:")
    for error in result['errors']:
        print(f"  ✗ {error['entry_id']}: {error['error']}")
```

---

### GET /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags

**Description:** Retrieve extracted path segments and their approval status for a catalog entry.

**Purpose:** View suggested tags extracted from the artifact's path in the repository.

#### Request

```http
GET /api/v1/marketplace/sources/src_anthropics_quickstarts/catalog/cat_canvas_design/path-tags
Authorization: Bearer <token>
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Unique source identifier |
| `entry_id` | string | Yes | Unique catalog entry identifier |

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "entry_id": "cat_canvas_design",
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "pending",
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "extracted_at": "2025-12-07T14:30:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | Catalog entry identifier |
| `raw_path` | string | Full artifact path in repository |
| `extracted` | array | List of extracted segments with approval status |
| `extracted_at` | string | ISO 8601 timestamp of extraction |

**Extracted Segment Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `segment` | string | Original segment value from path (e.g., "05-ui-ux") |
| `normalized` | string | Normalized value (e.g., "ui-ux") |
| `status` | string | Status: pending, approved, rejected, excluded |
| `reason` | string or null | Reason if excluded (e.g., matched exclude pattern) |

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Path tags retrieved successfully |
| 404 | Not Found | Source or entry not found |
| 400 | Bad Request | Entry has no path_segments (not extracted yet) |
| 500 | Internal Server Error | Malformed path_segments JSON |

#### Error Examples

**Entry not extracted yet:**

```json
{
  "detail": "Entry 'cat_canvas_design' has no path_segments (not extracted yet)"
}
```

#### Examples

**Get path-based tag suggestions:**

```bash
curl http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/catalog/cat_canvas_design/path-tags \
  -H "Authorization: Bearer sk_test_abc123" | jq '.extracted[] | {segment, normalized, status}'
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {"Authorization": f"Bearer {api_token}"}

source_id = "src_anthropics_quickstarts"
entry_id = "cat_canvas_design"

response = requests.get(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags",
    headers=headers
)

if response.status_code == 200:
    result = response.json()
    print(f"Artifact Path: {result['raw_path']}")
    print("\nExtracted Tags:")
    for seg in result['extracted']:
        print(f"  - {seg['normalized']} (status: {seg['status']})")
        if seg['reason']:
            print(f"    Reason: {seg['reason']}")
elif response.status_code == 400:
    print("Entry not yet extracted. Rescan the source.")
else:
    print(f"Error: {response.json()}")
```

---

### PATCH /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags

**Description:** Approve or reject a suggested path-based tag.

**Purpose:** Update the approval status of an extracted path segment.

#### Request

```http
PATCH /api/v1/marketplace/sources/src_anthropics_quickstarts/catalog/cat_canvas_design/path-tags
Authorization: Bearer <token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_id` | string | Yes | Unique source identifier |
| `entry_id` | string | Yes | Unique catalog entry identifier |

**Request Body:**

```json
{
  "segment": "ui-ux",
  "status": "approved"
}
```

**Parameters:**

| Field | Type | Required | Description | Options |
|-------|------|----------|-------------|---------|
| `segment` | string | Yes | Original segment value to update | — |
| `status` | string | Yes | New approval status | `approved`, `rejected` |

**Status Transitions:**

- Only `pending` segments can be changed
- Cannot change `excluded` segments (filtered by configuration)
- Cannot change already approved/rejected segments (409 Conflict)

#### Response

**Status Code:** `200 OK`

**Response Body:**

```json
{
  "entry_id": "cat_canvas_design",
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "approved",
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "updated_at": "2025-12-07T15:00:00Z"
}
```

#### Status Codes

| Code | Meaning | Reason |
|------|---------|--------|
| 200 | OK | Segment status updated successfully |
| 404 | Not Found | Source, entry, or segment not found |
| 409 | Conflict | Segment already approved/rejected or is excluded |
| 400 | Bad Request | Entry has no path_segments (not extracted yet) |
| 500 | Internal Server Error | Malformed path_segments JSON |

#### Error Examples

**Segment already approved:**

```json
{
  "detail": "Segment 'ui-ux' already has status 'approved'"
}
```

**Cannot change excluded segment:**

```json
{
  "detail": "Cannot change status of excluded segment 'src'"
}
```

**Segment not found:**

```json
{
  "detail": "Segment 'nonexistent' not found in entry 'cat_canvas_design'"
}
```

#### Examples

**Approve a segment:**

```bash
curl -X PATCH http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/catalog/cat_canvas_design/path-tags \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{"segment": "ui-ux", "status": "approved"}'
```

**Reject a segment:**

```bash
curl -X PATCH http://localhost:8000/api/v1/marketplace/sources/src_anthropics_quickstarts/catalog/cat_canvas_design/path-tags \
  -H "Authorization: Bearer sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{"segment": "canvas-design", "status": "rejected"}'
```

#### Python Example

```python
import requests

api_token = "sk_test_abc123"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

source_id = "src_anthropics_quickstarts"
entry_id = "cat_canvas_design"

# Approve a segment
response = requests.patch(
    f"http://localhost:8000/api/v1/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags",
    headers=headers,
    json={"segment": "ui-ux", "status": "approved"}
)

if response.status_code == 200:
    result = response.json()
    print(f"Updated segment status")
    print(f"\nAll segments for {result['raw_path']}:")
    for seg in result['extracted']:
        status_symbol = "✓" if seg['status'] == "approved" else "○"
        print(f"  [{status_symbol}] {seg['normalized']} ({seg['status']})")
else:
    error = response.json()
    print(f"Error: {error['detail']}")

# Batch-approve multiple segments (via multiple requests)
segments_to_approve = ["data-ai", "python"]
for segment in segments_to_approve:
    response = requests.patch(
        f"http://localhost:8000/api/v1/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags",
        headers=headers,
        json={"segment": segment, "status": "approved"}
    )
    if response.status_code == 200:
        print(f"✓ Approved: {segment}")
    else:
        print(f"✗ Failed to approve: {segment}")
```

---

## Status Codes

### Common HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 204 | No Content | Successful deletion (empty response) |
| 400 | Bad Request | Invalid request format or parameters |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate resource or conflict |
| 500 | Internal Server Error | Server error |

## Error Handling

### Error Response Format

Error responses follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

For 4xx errors, the detail field explains what went wrong and how to fix it.

### Common Errors

| Scenario | Status | Detail |
|----------|--------|--------|
| Invalid URL format | 400 | `Invalid GitHub repository URL format. Expected: https://github.com/owner/repo, got: ...` |
| Source already exists | 409 | `Source with repository URL '...' already exists` |
| Source not found | 404 | `Source with ID '...' not found` |
| Entry not found | 404 | `Catalog entry with ID '...' not found` |
| Wrong entry belongs to source | 400 | `Entry '...' does not belong to source '...'` |
| No update parameters | 400 | `At least one update parameter must be provided` |
| Empty import list | 400 | `entry_ids cannot be empty` |

### Retry Logic

For retryable errors (500, 502, 503):

```python
import requests
import time

def api_call_with_retry(url, headers, method="GET", json=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, params=json)

            # Retry on server errors
            if response.status_code >= 500:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Error {response.status_code}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

            return response
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request failed: {e}, retrying...")
                time.sleep(2 ** attempt)
                continue
            raise

    raise Exception("Max retries exceeded")
```

## Data Models

### SourceResponse

Complete representation of a GitHub repository source:

```json
{
  "id": "string",
  "repo_url": "string",
  "owner": "string",
  "repo_name": "string",
  "ref": "string",
  "root_hint": "string or null",
  "trust_level": "untrusted | basic | verified | official",
  "visibility": "public | private",
  "scan_status": "pending | scanning | success | error",
  "artifact_count": "integer",
  "last_sync_at": "ISO 8601 timestamp or null",
  "last_error": "string or null",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp"
}
```

### CatalogEntryResponse

Representation of a detected artifact in the catalog:

```json
{
  "id": "string",
  "source_id": "string",
  "artifact_type": "skill | command | agent | mcp_server | hook",
  "name": "string",
  "path": "string",
  "upstream_url": "string",
  "detected_version": "string or null",
  "detected_sha": "string or null",
  "detected_at": "ISO 8601 timestamp",
  "confidence_score": "integer (0-100)",
  "status": "new | updated | removed | imported",
  "import_date": "ISO 8601 timestamp or null",
  "import_id": "string or null"
}
```

### ScanResultDTO

Result of scanning a repository:

```json
{
  "source_id": "string",
  "status": "success | error | partial",
  "artifacts_found": "integer",
  "new_count": "integer",
  "updated_count": "integer",
  "removed_count": "integer",
  "unchanged_count": "integer",
  "scan_duration_ms": "number",
  "errors": ["string"],
  "scanned_at": "ISO 8601 timestamp"
}
```

### ImportResultDTO

Result of importing artifacts:

```json
{
  "imported_count": "integer",
  "skipped_count": "integer",
  "error_count": "integer",
  "imported_ids": ["string"],
  "skipped_ids": ["string"],
  "errors": [
    {
      "entry_id": "string",
      "error": "string"
    }
  ]
}
```

## Examples

### Complete Workflow

```python
import requests
from typing import List

class MarketplaceClient:
    def __init__(self, api_token: str, base_url: str = "http://localhost:8000/api/v1"):
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def create_source(self, repo_url: str, ref: str = "main", root_hint: str = None) -> dict:
        """Add a GitHub repository as a source."""
        response = requests.post(
            f"{self.base_url}/marketplace/sources",
            headers=self.headers,
            json={
                "repo_url": repo_url,
                "ref": ref,
                "root_hint": root_hint,
                "trust_level": "basic"
            }
        )
        return response.json()

    def list_sources(self, limit: int = 50) -> dict:
        """List all sources."""
        response = requests.get(
            f"{self.base_url}/marketplace/sources",
            headers=self.headers,
            params={"limit": limit}
        )
        return response.json()

    def get_source(self, source_id: str) -> dict:
        """Get source details."""
        response = requests.get(
            f"{self.base_url}/marketplace/sources/{source_id}",
            headers=self.headers
        )
        return response.json()

    def rescan_source(self, source_id: str) -> dict:
        """Trigger a rescan of the repository."""
        response = requests.post(
            f"{self.base_url}/marketplace/sources/{source_id}/rescan",
            headers=self.headers,
            json={"force": False}
        )
        return response.json()

    def list_artifacts(self, source_id: str, artifact_type: str = None) -> dict:
        """List artifacts from a source."""
        params = {}
        if artifact_type:
            params["artifact_type"] = artifact_type

        response = requests.get(
            f"{self.base_url}/marketplace/sources/{source_id}/artifacts",
            headers=self.headers,
            params=params
        )
        return response.json()

    def import_artifacts(self, source_id: str, entry_ids: List[str]) -> dict:
        """Import artifacts to collection."""
        response = requests.post(
            f"{self.base_url}/marketplace/sources/{source_id}/import",
            headers=self.headers,
            json={
                "entry_ids": entry_ids,
                "conflict_strategy": "skip"
            }
        )
        return response.json()

# Usage
client = MarketplaceClient("sk_test_abc123")

# 1. Create a source
print("Creating source...")
source = client.create_source(
    repo_url="https://github.com/anthropics/anthropic-quickstarts",
    ref="main",
    root_hint="skills"
)
source_id = source["id"]
print(f"Source created: {source_id}")

# 2. Trigger scan
print("\nScanning repository...")
scan_result = client.rescan_source(source_id)
print(f"Found {scan_result['artifacts_found']} artifacts")
print(f"Status: {scan_result['status']}")

# 3. List new artifacts
print("\nListing new artifacts...")
artifacts = client.list_artifacts(source_id, artifact_type="skill")
print(f"Skills available: {len(artifacts['items'])}")

# 4. Import high-confidence artifacts
print("\nImporting artifacts...")
high_confidence = [
    a["id"] for a in artifacts["items"]
    if a["confidence_score"] >= 90
]
if high_confidence:
    result = client.import_artifacts(source_id, high_confidence)
    print(f"Imported: {result['imported_count']}")
    print(f"Skipped: {result['skipped_count']}")
    if result['errors']:
        print(f"Errors: {result['error_count']}")
else:
    print("No high-confidence artifacts found")
```

---

## Best Practices

### URL Format

Always use full GitHub HTTPS URLs:

```
✓ https://github.com/anthropics/anthropic-quickstarts
✗ git@github.com:anthropics/anthropic-quickstarts.git
✗ https://github.com/anthropics/anthropic-quickstarts.git
```

### Pagination

When iterating through results:

```python
cursor = None
all_items = []

while True:
    result = requests.get(
        url,
        headers=headers,
        params={"limit": 50, "cursor": cursor}
    ).json()

    all_items.extend(result["items"])

    if not result["page_info"]["has_next_page"]:
        break

    cursor = result["page_info"]["end_cursor"]
```

### Error Handling

Always check response status codes:

```python
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    # Process data
elif response.status_code == 404:
    print("Resource not found")
elif response.status_code >= 500:
    print("Server error, retry later")
else:
    print(f"Error: {response.json()}")
```

### Scanning Large Repositories

For large repositories, scans may take several seconds. Consider:

1. Using background/polling pattern if available
2. Setting reasonable timeouts in your HTTP client
3. Retrying with exponential backoff on timeouts

---

## Rate Limiting

Currently, there are no documented rate limits. If you experience rate limiting in the future, look for these headers in responses:

```
X-RateLimit-Limit: maximum requests per window
X-RateLimit-Remaining: requests remaining in current window
X-RateLimit-Reset: Unix timestamp when limit resets
```

If you receive a 429 Too Many Requests response, wait until the reset time before retrying.
