---
title: "Cache API Reference"
description: "Complete reference for all SkillMeat cache API endpoints"
audience: [developers]
tags: [cache, API, REST, endpoints, reference]
created: 2025-12-01
updated: 2025-12-01
category: "reference"
status: "published"
related: ["configuration-guide.md", "troubleshooting-guide.md"]
---

# Cache API Reference

Complete documentation for all cache management API endpoints in SkillMeat.

## Overview

The cache API provides endpoints for:

- **Cache status** - Query cache statistics and status
- **Cache refresh** - Trigger manual refreshes
- **Cache invalidation** - Mark cache as stale
- **Project listing** - List cached projects with filtering
- **Artifact listing** - List cached artifacts with filtering
- **Outdated artifacts** - Find artifacts with available updates
- **Cache search** - Full-text search of cached artifacts
- **Marketplace cache** - Access cached marketplace data

All endpoints require API key authentication via the `Authorization` header.

## Table of Contents

- [Authentication](#authentication)
- [Status & Statistics](#status--statistics)
- [Cache Management](#cache-management)
- [Project Endpoints](#project-endpoints)
- [Artifact Endpoints](#artifact-endpoints)
- [Search Endpoints](#search-endpoints)
- [Marketplace Endpoints](#marketplace-endpoints)
- [Error Responses](#error-responses)
- [Rate Limiting](#rate-limiting)

## Authentication

All cache endpoints require an API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/cache/status
```

### Getting an API Key

```bash
# Generate API key
skillmeat config set api-key

# View current key
skillmeat config get api-key

# Output: sk_live_abc123def456...
```

## Status & Statistics

### GET /api/v1/cache/status

Get comprehensive cache statistics and status information.

**Request:**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/status
```

**Response (200 OK):**

```json
{
  "total_projects": 12,
  "total_artifacts": 87,
  "stale_projects": 2,
  "outdated_artifacts": 5,
  "cache_size_bytes": 15728640,
  "oldest_entry": "2025-11-15T08:30:00Z",
  "newest_entry": "2025-12-01T14:22:00Z",
  "last_refresh": "2025-12-01T12:00:00Z",
  "refresh_job_status": {
    "is_running": true,
    "next_run_time": "2025-12-01T18:00:00Z",
    "last_run_time": "2025-12-01T12:00:00Z"
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_projects` | integer | Total number of cached projects |
| `total_artifacts` | integer | Total number of cached artifacts |
| `stale_projects` | integer | Number of projects past TTL |
| `outdated_artifacts` | integer | Number of artifacts with newer versions |
| `cache_size_bytes` | integer | Cache database size in bytes |
| `oldest_entry` | datetime | Timestamp of oldest cached entry |
| `newest_entry` | datetime | Timestamp of newest cached entry |
| `last_refresh` | datetime | When cache was last refreshed |
| `refresh_job_status.is_running` | boolean | Whether refresh scheduler is running |
| `refresh_job_status.next_run_time` | datetime | When next refresh will run |
| `refresh_job_status.last_run_time` | datetime | When last refresh completed |

**Examples:**

```bash
# Get cache statistics
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/status | jq .

# Check if cache is running
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/status | jq .refresh_job_status.is_running

# Get cache size in MB
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/cache/status | \
  jq '.cache_size_bytes / (1024 * 1024) | round'
```

## Cache Management

### POST /api/v1/cache/refresh

Trigger manual cache refresh for all projects or a specific project.

**Request:**

```bash
# Refresh all projects
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project_id": null, "force": false}' \
  http://localhost:8000/api/v1/cache/refresh

# Force refresh specific project
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-123", "force": true}' \
  http://localhost:8000/api/v1/cache/refresh
```

**Request Body:**

```json
{
  "project_id": "proj-123",
  "force": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `project_id` | string \| null | null | Project ID (null = all projects) |
| `force` | boolean | false | Force refresh even if not stale |

**Response (200 OK):**

```json
{
  "success": true,
  "projects_refreshed": 5,
  "changes_detected": true,
  "errors": [],
  "duration_seconds": 3.45,
  "message": "Refresh completed successfully"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether refresh succeeded |
| `projects_refreshed` | integer | Number of projects refreshed |
| `changes_detected` | boolean | Whether any changes were found |
| `errors` | array | Error messages (if any) |
| `duration_seconds` | number | Time taken for operation |
| `message` | string | Human-readable status message |

**Error Responses:**

```json
{
  "detail": "Project 'proj-999' not found"
}
```

Status code: 404

### POST /api/v1/cache/invalidate

Mark cache as stale to force refresh on next access.

**Request:**

```bash
# Invalidate entire cache
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project_id": null}' \
  http://localhost:8000/api/v1/cache/invalidate

# Invalidate specific project
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-123"}' \
  http://localhost:8000/api/v1/cache/invalidate
```

**Request Body:**

```json
{
  "project_id": null
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "invalidated_count": 12,
  "message": "Invalidated entire cache (12 projects)"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether invalidation succeeded |
| `invalidated_count` | integer | Number of projects invalidated |
| `message` | string | Human-readable status message |

## Project Endpoints

### GET /api/v1/cache/projects

List all cached projects with optional filtering and pagination.

**Request:**

```bash
# List all projects
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/projects"

# List stale projects with pagination
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/projects?status=stale&limit=10&skip=0"

# Filter by status
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/projects?status=active"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | null | Filter by status (active, stale, error) |
| `skip` | integer | 0 | Number of items to skip |
| `limit` | integer | 100 | Max items to return (1-500) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "proj-1",
      "name": "My Project",
      "path": "/home/user/projects/my-project",
      "status": "active",
      "last_fetched": "2025-12-01T12:00:00Z",
      "artifact_count": 5
    },
    {
      "id": "proj-2",
      "name": "Old Project",
      "path": "/home/user/projects/old-project",
      "status": "stale",
      "last_fetched": "2025-11-20T08:30:00Z",
      "artifact_count": 3
    }
  ],
  "total": 12,
  "skip": 0,
  "limit": 100
}
```

**Examples:**

```bash
# Get all active projects
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/projects?status=active" | jq .items

# Get stale projects
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/projects?status=stale" | jq .items

# Pagination example
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/projects?limit=10&skip=20" | jq .
```

## Artifact Endpoints

### GET /api/v1/cache/artifacts

List all cached artifacts with filtering and pagination.

**Request:**

```bash
# List all artifacts
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/artifacts"

# Filter by project
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/artifacts?project_id=proj-1"

# Filter by type and outdated status
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/artifacts?type=skill&is_outdated=true"

# With pagination
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/artifacts?limit=50&skip=0"
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Filter by project ID |
| `type` | string | Filter by artifact type (skill, command, agent) |
| `is_outdated` | boolean | Filter by outdated status |
| `skip` | integer | Number of items to skip (default: 0) |
| `limit` | integer | Max items to return (1-500, default: 100) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "art-1",
      "name": "canvas",
      "type": "skill",
      "project_id": "proj-1",
      "deployed_version": "1.0.0",
      "upstream_version": "1.2.0",
      "is_outdated": true
    },
    {
      "id": "art-2",
      "name": "python",
      "type": "skill",
      "project_id": "proj-1",
      "deployed_version": "2.1.0",
      "upstream_version": "2.1.0",
      "is_outdated": false
    }
  ],
  "total": 87,
  "skip": 0,
  "limit": 100
}
```

### GET /api/v1/cache/stale-artifacts

List artifacts with available upstream updates (outdated artifacts).

**Request:**

```bash
# List all outdated artifacts
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/stale-artifacts"

# Filter by type
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/stale-artifacts?type=skill"

# Sort by version difference
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/stale-artifacts?sort_by=version_diff&sort_order=desc"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | null | Filter by artifact type |
| `project_id` | string | null | Filter by project ID |
| `sort_by` | string | "name" | Sort field (name, type, project, version_diff) |
| `sort_order` | string | "asc" | Sort direction (asc, desc) |
| `skip` | integer | 0 | Number of items to skip |
| `limit` | integer | 100 | Max items to return (1-500) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "art-1",
      "name": "canvas",
      "type": "skill",
      "project_name": "My Project",
      "project_id": "proj-1",
      "deployed_version": "1.0.0",
      "upstream_version": "1.2.0",
      "version_difference": "minor version upgrade (0 -> 2)"
    },
    {
      "id": "art-5",
      "name": "docker",
      "type": "skill",
      "project_name": "DevOps Project",
      "project_id": "proj-3",
      "deployed_version": "2.0.0",
      "upstream_version": "3.1.0",
      "version_difference": "major version upgrade (2 -> 3)"
    }
  ],
  "total": 5
}
```

**Examples:**

```bash
# Get all outdated skills
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/stale-artifacts?type=skill" | jq .items

# Sort by biggest version differences first
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/stale-artifacts?sort_by=version_diff&sort_order=desc" | jq .items

# Outdated artifacts in specific project
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/stale-artifacts?project_id=proj-1" | jq .
```

## Search Endpoints

### GET /api/v1/cache/search

Search cached artifacts by name with relevance scoring.

**Request:**

```bash
# Search for "docker" artifacts
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=docker"

# Search with filters
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=canvas&type=skill&sort_by=relevance"

# Search in specific project
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=python&project_id=proj-1"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query (min 1 char) |
| `project_id` | string | null | Filter by project ID |
| `type` | string | null | Filter by artifact type |
| `skip` | integer | 0 | Number of items to skip |
| `limit` | integer | 50 | Max items to return (1-200) |
| `sort_by` | string | "relevance" | Sort order (relevance, name, type, updated) |

**Relevance Scoring:**

- **100.0** - Exact match (query matches artifact name exactly)
- **80.0** - Prefix match (artifact name starts with query)
- **60.0** - Contains match (artifact name contains query)

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "art-3",
      "name": "docker",
      "type": "skill",
      "project_id": "proj-2",
      "project_name": "DevOps Project",
      "score": 100.0
    },
    {
      "id": "art-8",
      "name": "docker-compose",
      "type": "command",
      "project_id": "proj-2",
      "project_name": "DevOps Project",
      "score": 80.0
    },
    {
      "id": "art-12",
      "name": "containerize",
      "type": "skill",
      "project_id": "proj-1",
      "project_name": "My Project",
      "score": 60.0
    }
  ],
  "total": 3,
  "query": "docker",
  "skip": 0,
  "limit": 50
}
```

**Examples:**

```bash
# Search for Python artifacts
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=python" | jq .

# Find skills containing "review"
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=review&type=skill" | jq .items

# Get exact matches only (score >= 80)
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/search?query=canvas" | \
  jq '.items | map(select(.score >= 80))'
```

## Marketplace Endpoints

### GET /api/v1/cache/marketplace

Get cached marketplace entries with optional type filtering.

**Request:**

```bash
# Get all marketplace entries
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/marketplace"

# Filter by type
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/marketplace?type=skill"

# With pagination
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/cache/marketplace?limit=20&skip=0"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | null | Filter by artifact type |
| `skip` | integer | 0 | Number of items to skip |
| `limit` | integer | 100 | Max items to return (1-500) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "mkt-1",
      "name": "canvas",
      "type": "skill",
      "url": "https://github.com/anthropics/skills/canvas",
      "description": "Canvas design and prototyping skill",
      "cached_at": "2025-12-01T12:00:00Z",
      "data": {
        "publisher": "anthropics",
        "license": "MIT",
        "tags": ["design", "ui", "prototyping"],
        "version": "2.1.0",
        "downloads": 1250
      }
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 100
}
```

## Error Responses

### 400 Bad Request

Invalid request parameters or validation errors.

```json
{
  "detail": "Invalid sort_by field: invalid_field. Valid options: name, type, project, version_diff"
}
```

Common causes:
- Invalid query parameters
- Out-of-range limit values
- Invalid sort field names

### 404 Not Found

Resource not found.

```json
{
  "detail": "Project 'proj-999' not found"
}
```

Common causes:
- Project ID doesn't exist
- Artifact not in cache

### 401 Unauthorized

Missing or invalid API key.

```json
{
  "detail": "Missing or invalid API key"
}
```

Solution: Provide valid API key in Authorization header

### 429 Too Many Requests

Rate limit exceeded.

```json
{
  "detail": "Rate limit exceeded. Maximum 100 requests per minute per user"
}
```

Solution: Implement exponential backoff in client code

### 500 Internal Server Error

Server-side error during request processing.

```json
{
  "detail": "Internal server error"
}
```

Check:
- Server logs for detailed error information
- Cache status with `/api/v1/cache/status`
- Database integrity with `skillmeat cache check`

## Rate Limiting

Cache API endpoints are subject to rate limiting:

| Metric | Limit |
|--------|-------|
| Requests per minute | 100 |
| Requests per hour | 5000 |
| Concurrent requests | 10 |

Rate limit information is returned in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1701435000
```

### Handling Rate Limits

Implement exponential backoff when rate limited:

```python
import requests
import time

def api_call_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            print(f"Rate limited. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            continue

        return response

    raise Exception("Max retries exceeded")
```

## Complete Example

Monitoring cache health:

```python
import requests
import json

API_KEY = "sk_live_abc123..."
BASE_URL = "http://localhost:8000/api/v1/cache"

def check_cache_health():
    headers = {"Authorization": f"Bearer {API_KEY}"}

    # Get cache status
    response = requests.get(f"{BASE_URL}/status", headers=headers)
    status = response.json()

    print(f"Cache Health Report")
    print(f"==================")
    print(f"Total Projects: {status['total_projects']}")
    print(f"Total Artifacts: {status['total_artifacts']}")
    print(f"Stale Projects: {status['stale_projects']}")
    print(f"Outdated Artifacts: {status['outdated_artifacts']}")
    print(f"Cache Size: {status['cache_size_bytes'] / (1024*1024):.1f} MB")
    print(f"Refresh Running: {status['refresh_job_status']['is_running']}")
    print(f"Last Refresh: {status['last_refresh']}")

    # Get outdated artifacts
    response = requests.get(f"{BASE_URL}/stale-artifacts", headers=headers)
    stale = response.json()

    if stale['items']:
        print(f"\nArtifacts Needing Updates:")
        for artifact in stale['items']:
            print(f"  - {artifact['name']} ({artifact['type']}) in {artifact['project_name']}")
            print(f"    {artifact['deployed_version']} -> {artifact['upstream_version']}")

if __name__ == "__main__":
    check_cache_health()
```

## See Also

- [Configuration Guide](configuration-guide.md) - Cache configuration options
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues and solutions
- [Architecture Decision Record](architecture-decision-record.md) - Design decisions
