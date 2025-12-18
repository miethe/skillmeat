---
title: Tags API
description: Complete API reference for managing tags and artifact-tag associations in SkillMeat
audience: developers
tags: [api, tags, artifacts, organization]
created: 2025-12-18
updated: 2025-12-18
category: API Documentation
status: published
related: [artifacts.md, discovery-endpoints.md]
---

# Tags API Documentation

Complete API reference for SkillMeat's Tags endpoints that enable flexible artifact organization through tagging.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Pagination](#pagination)
- [Endpoints](#endpoints)
  - [POST /tags](#post-tags) - Create tag
  - [GET /tags](#get-tags) - List tags
  - [GET /tags/{tag_id}](#get-tagstag_id) - Get tag by ID
  - [GET /tags/slug/{slug}](#get-tagsslugslug) - Get tag by slug
  - [PUT /tags/{tag_id}](#put-tagstag_id) - Update tag
  - [DELETE /tags/{tag_id}](#delete-tagstag_id) - Delete tag
  - [GET /tags/search](#get-tagssearch) - Search tags
  - [GET /artifacts/{artifact_id}/tags](#get-artifactsartifact_idtags) - Get artifact tags
  - [POST /artifacts/{artifact_id}/tags/{tag_id}](#post-artifactsartifact_idtagstag_id) - Add tag to artifact
  - [DELETE /artifacts/{artifact_id}/tags/{tag_id}](#delete-artifactsartifact_idtagstag_id) - Remove tag from artifact
- [Status Codes](#status-codes)
- [Error Handling](#error-handling)
- [Data Models](#data-models)
- [Examples](#examples)

## Overview

The Tags API provides endpoints for:

- **Creating and managing tags** with unique names and URL slugs
- **Listing tags** with pagination and artifact counts
- **Searching tags** by name pattern
- **Managing artifact-tag associations** for flexible organization
- **Retrieving artifact tags** to understand artifact categorization

### Key Features

- **Unique Slugs**: Tags require unique URL-friendly slugs (kebab-case)
- **Hex Colors**: Optional color codes for visual customization
- **Artifact Counts**: Each tag includes count of associated artifacts
- **Cursor Pagination**: Efficient pagination for large tag lists
- **Case-Insensitive Search**: Find tags by name pattern matching

### Typical Workflow

```
1. Create tag        → POST /tags
2. Add to artifact   → POST /artifacts/{id}/tags/{tag_id}
3. List artifact tags → GET /artifacts/{id}/tags
4. Search tags       → GET /tags/search?q=python
5. Manage tags       → PUT/DELETE /tags/{tag_id}
```

## Authentication

Currently, the Tags API does not require authentication. Future versions will support API key-based authentication.

```
Authorization: Bearer <api_token>
```

## Base URL

```
http://localhost:8080/api/v1
```

## Pagination

Tag list endpoints support cursor-based pagination for efficiency. Include the `after` cursor from the previous response to fetch the next page.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Number of items per page (1-100, default: 50) |
| `after` | string | No | Cursor for next page (base64-encoded tag ID) |

### Response Structure

```json
{
  "items": [/* tag objects */],
  "page_info": {
    "has_next_page": false,
    "has_previous_page": false,
    "start_cursor": "base64-encoded-cursor",
    "end_cursor": "base64-encoded-cursor",
    "total_count": 45
  }
}
```

---

## Endpoints

### POST /tags

Create a new tag for organizing artifacts.

**Path**: `/api/v1/tags`
**Method**: `POST`
**Status Code**: `201 Created`

#### Description

Creates a new tag with a unique name and URL-friendly slug. Tag names and slugs must be unique across the system. Color is optional and should be a valid hex code.

#### Authentication

No authentication required.

#### Request Body

```typescript
interface TagCreateRequest {
  /**
   * Tag name (1-100 characters)
   * Examples: "Python", "AI Tools", "Productivity"
   */
  name: string;

  /**
   * URL-friendly slug (kebab-case, 1-100 characters)
   * Pattern: ^[a-z0-9]+(?:-[a-z0-9]+)*$
   * Examples: "python", "ai-tools", "productivity"
   */
  slug: string;

  /**
   * Optional hex color code for visual identification
   * Pattern: ^#[0-9A-Fa-f]{6}$
   * Examples: "#FF5733", "#3498DB"
   */
  color?: string;
}
```

**Validation Rules:**
- `name`: Required, 1-100 characters, must be unique
- `slug`: Required, 1-100 characters, lowercase alphanumeric with hyphens, must be unique
  - Cannot start or end with hyphen
  - Cannot contain consecutive hyphens
  - Must be lowercase
- `color`: Optional, valid hex color code (#RRGGBB format)

#### Response

**Success (201)**:
```json
{
  "id": "tag-550e8400-e29b-41d4-a716-446655440000",
  "name": "Python",
  "slug": "python",
  "color": "#3776AB",
  "artifact_count": 0,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T10:30:00Z"
}
```

**Error (400) - Validation Failed**:
```json
{
  "detail": "Slug must be lowercase"
}
```

**Error (409) - Duplicate**:
```json
{
  "detail": "Tag with name 'Python' already exists"
}
```

#### Examples

**Create Python tag:**
```bash
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python",
    "slug": "python",
    "color": "#3776AB"
  }'
```

**Response:**
```json
{
  "id": "tag-550e8400-e29b-41d4-a716-446655440000",
  "name": "Python",
  "slug": "python",
  "color": "#3776AB",
  "artifact_count": 0,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T10:30:00Z"
}
```

---

### GET /tags

Retrieve a paginated list of all tags with artifact counts.

**Path**: `/api/v1/tags`
**Method**: `GET`
**Status Code**: `200 OK`

#### Description

Returns a paginated list of all tags ordered by name. Each tag includes the count of associated artifacts. Use cursor-based pagination for efficient retrieval of large tag lists.

#### Authentication

No authentication required.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Items per page, 1-100 (default: 50) |
| `after` | string | No | Cursor for pagination (from previous response) |

#### Response

**Success (200)**:
```json
{
  "items": [
    {
      "id": "tag-550e8400-e29b-41d4-a716-446655440000",
      "name": "AI Tools",
      "slug": "ai-tools",
      "color": "#3498DB",
      "artifact_count": 8,
      "created_at": "2025-12-18T09:00:00Z",
      "updated_at": "2025-12-18T09:00:00Z"
    },
    {
      "id": "tag-660e8400-e29b-41d4-a716-446655440001",
      "name": "Python",
      "slug": "python",
      "color": "#3776AB",
      "artifact_count": 15,
      "created_at": "2025-12-18T10:30:00Z",
      "updated_at": "2025-12-18T10:30:00Z"
    }
  ],
  "page_info": {
    "has_next_page": true,
    "has_previous_page": false,
    "start_cursor": "dGFnLTU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMA==",
    "end_cursor": "dGFnLTY2MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMQ==",
    "total_count": 47
  }
}
```

**Error (400) - Invalid Cursor**:
```json
{
  "detail": "Invalid cursor format: tag not found"
}
```

#### Examples

**Get first 20 tags:**
```bash
curl "http://localhost:8080/api/v1/tags?limit=20" \
  -H "Accept: application/json"
```

**Get next page:**
```bash
curl "http://localhost:8080/api/v1/tags?limit=20&after=dGFnLTY2MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMQ==" \
  -H "Accept: application/json"
```

---

### GET /tags/{tag_id}

Get a specific tag by its ID.

**Path**: `/api/v1/tags/{tag_id}`
**Method**: `GET`
**Status Code**: `200 OK`

#### Description

Retrieves detailed information about a specific tag including the count of artifacts tagged with it.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_id` | string | Yes | Tag identifier |

#### Response

**Success (200)**:
```json
{
  "id": "tag-550e8400-e29b-41d4-a716-446655440000",
  "name": "Python",
  "slug": "python",
  "color": "#3776AB",
  "artifact_count": 15,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T10:30:00Z"
}
```

**Error (404) - Not Found**:
```json
{
  "detail": "Tag 'tag-550e8400-e29b-41d4-a716-446655440000' not found"
}
```

#### Examples

**Get tag details:**
```bash
curl http://localhost:8080/api/v1/tags/tag-550e8400-e29b-41d4-a716-446655440000 \
  -H "Accept: application/json"
```

---

### GET /tags/slug/{slug}

Get a specific tag by its URL slug.

**Path**: `/api/v1/tags/slug/{slug}`
**Method**: `GET`
**Status Code**: `200 OK`

#### Description

Retrieves a tag using its URL-friendly slug instead of the numeric ID. Slugs are easier to remember and use in URLs.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | Yes | URL-friendly tag slug (kebab-case) |

#### Response

**Success (200)**:
```json
{
  "id": "tag-550e8400-e29b-41d4-a716-446655440000",
  "name": "Python",
  "slug": "python",
  "color": "#3776AB",
  "artifact_count": 15,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T10:30:00Z"
}
```

**Error (404) - Not Found**:
```json
{
  "detail": "Tag with slug 'python' not found"
}
```

#### Examples

**Get tag by slug:**
```bash
curl http://localhost:8080/api/v1/tags/slug/python \
  -H "Accept: application/json"
```

---

### PUT /tags/{tag_id}

Update tag metadata.

**Path**: `/api/v1/tags/{tag_id}`
**Method**: `PUT`
**Status Code**: `200 OK`

#### Description

Updates tag metadata. All fields are optional for partial updates. If slug is updated, it must remain unique across the system.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_id` | string | Yes | Tag identifier |

#### Request Body

```typescript
interface TagUpdateRequest {
  /**
   * Updated tag name (optional)
   * 1-100 characters, must be unique if provided
   */
  name?: string;

  /**
   * Updated URL slug (optional)
   * 1-100 characters, kebab-case, must be unique if provided
   */
  slug?: string;

  /**
   * Updated hex color code (optional)
   * Pattern: ^#[0-9A-Fa-f]{6}$
   */
  color?: string;
}
```

**Note**: Submit only the fields you want to update. Omitted fields remain unchanged.

#### Response

**Success (200)**:
```json
{
  "id": "tag-550e8400-e29b-41d4-a716-446655440000",
  "name": "Python 3.x",
  "slug": "python-3x",
  "color": "#3776AB",
  "artifact_count": 15,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T11:45:00Z"
}
```

**Error (404) - Not Found**:
```json
{
  "detail": "Tag 'tag-550e8400-e29b-41d4-a716-446655440000' not found"
}
```

**Error (409) - Slug Conflict**:
```json
{
  "detail": "Tag with slug 'python-3x' already exists"
}
```

#### Examples

**Update tag color:**
```bash
curl -X PUT http://localhost:8080/api/v1/tags/tag-550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "color": "#FF6600"
  }'
```

**Update name and slug:**
```bash
curl -X PUT http://localhost:8080/api/v1/tags/tag-550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python 3.x",
    "slug": "python-3x"
  }'
```

---

### DELETE /tags/{tag_id}

Delete a tag.

**Path**: `/api/v1/tags/{tag_id}`
**Method**: `DELETE`
**Status Code**: `204 No Content`

#### Description

Deletes a tag and all its associations with artifacts. Artifacts themselves are not affected; only the tag associations are removed.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_id` | string | Yes | Tag identifier |

#### Response

**Success (204)**:
```
(empty body)
```

**Error (404) - Not Found**:
```json
{
  "detail": "Tag 'tag-550e8400-e29b-41d4-a716-446655440000' not found"
}
```

#### Examples

**Delete tag:**
```bash
curl -X DELETE http://localhost:8080/api/v1/tags/tag-550e8400-e29b-41d4-a716-446655440000
```

**Verify deletion with verbose output:**
```bash
curl -v -X DELETE http://localhost:8080/api/v1/tags/tag-550e8400-e29b-41d4-a716-446655440000
# HTTP/1.1 204 No Content
```

---

### GET /tags/search

Search tags by name pattern.

**Path**: `/api/v1/tags/search`
**Method**: `GET`
**Status Code**: `200 OK`

#### Description

Searches for tags by name using case-insensitive substring matching. Results are limited to 50 tags by default and ordered alphabetically by name.

#### Authentication

No authentication required.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (1-100 characters, case-insensitive) |
| `limit` | integer | No | Maximum results, 1-100 (default: 50) |

#### Response

**Success (200)**:
```json
[
  {
    "id": "tag-550e8400-e29b-41d4-a716-446655440000",
    "name": "Python",
    "slug": "python",
    "color": "#3776AB",
    "artifact_count": 15,
    "created_at": "2025-12-18T10:30:00Z",
    "updated_at": "2025-12-18T10:30:00Z"
  },
  {
    "id": "tag-770e8400-e29b-41d4-a716-446655440002",
    "name": "Python Data Science",
    "slug": "python-data-science",
    "color": "#1f77b4",
    "artifact_count": 5,
    "created_at": "2025-12-18T11:00:00Z",
    "updated_at": "2025-12-18T11:00:00Z"
  }
]
```

**Error (400) - Invalid Query**:
```json
{
  "detail": "Search query must be between 1 and 100 characters"
}
```

#### Examples

**Search for Python-related tags:**
```bash
curl "http://localhost:8080/api/v1/tags/search?q=python" \
  -H "Accept: application/json"
```

**Search with custom limit:**
```bash
curl "http://localhost:8080/api/v1/tags/search?q=ai&limit=10" \
  -H "Accept: application/json"
```

---

### GET /artifacts/{artifact_id}/tags

Get all tags for a specific artifact.

**Path**: `/api/v1/artifacts/{artifact_id}/tags`
**Method**: `GET`
**Status Code**: `200 OK`

#### Description

Retrieves all tags associated with a specific artifact, showing how the artifact is categorized in the system.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_id` | string | Yes | Artifact identifier |

#### Response

**Success (200)**:
```json
[
  {
    "id": "tag-550e8400-e29b-41d4-a716-446655440000",
    "name": "Python",
    "slug": "python",
    "color": "#3776AB",
    "artifact_count": 15,
    "created_at": "2025-12-18T10:30:00Z",
    "updated_at": "2025-12-18T10:30:00Z"
  },
  {
    "id": "tag-660e8400-e29b-41d4-a716-446655440001",
    "name": "AI Tools",
    "slug": "ai-tools",
    "color": "#3498DB",
    "artifact_count": 8,
    "created_at": "2025-12-18T09:00:00Z",
    "updated_at": "2025-12-18T09:00:00Z"
  }
]
```

**Error (404) - Artifact Not Found**:
```json
{
  "detail": "Artifact 'art-550e8400-e29b-41d4-a716-446655440000' not found"
}
```

#### Examples

**Get tags for artifact:**
```bash
curl http://localhost:8080/api/v1/artifacts/art-550e8400-e29b-41d4-a716-446655440000/tags \
  -H "Accept: application/json"
```

---

### POST /artifacts/{artifact_id}/tags/{tag_id}

Add a tag to an artifact.

**Path**: `/api/v1/artifacts/{artifact_id}/tags/{tag_id}`
**Method**: `POST`
**Status Code**: `201 Created`

#### Description

Associates a tag with an artifact for organization and categorization. Adding the same tag twice returns an error.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_id` | string | Yes | Artifact identifier |
| `tag_id` | string | Yes | Tag identifier to add |

#### Response

**Success (201)**:
```json
{
  "id": "tag-550e8400-e29b-41d4-a716-446655440000",
  "name": "Python",
  "slug": "python",
  "color": "#3776AB",
  "artifact_count": 16,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T10:30:00Z"
}
```

**Error (404) - Not Found**:
```json
{
  "detail": "Artifact or tag not found"
}
```

**Error (409) - Already Tagged**:
```json
{
  "detail": "Artifact already has tag 'Python'"
}
```

#### Examples

**Add tag to artifact:**
```bash
curl -X POST http://localhost:8080/api/v1/artifacts/art-550e8400-e29b-41d4-a716-446655440000/tags/tag-550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json"
```

---

### DELETE /artifacts/{artifact_id}/tags/{tag_id}

Remove a tag from an artifact.

**Path**: `/api/v1/artifacts/{artifact_id}/tags/{tag_id}`
**Method**: `DELETE`
**Status Code**: `204 No Content`

#### Description

Removes a tag association from an artifact. The tag itself is not deleted; only the artifact-tag relationship is removed.

#### Authentication

No authentication required.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_id` | string | Yes | Artifact identifier |
| `tag_id` | string | Yes | Tag identifier to remove |

#### Response

**Success (204)**:
```
(empty body)
```

**Error (404) - Not Found**:
```json
{
  "detail": "Artifact or tag association not found"
}
```

#### Examples

**Remove tag from artifact:**
```bash
curl -X DELETE http://localhost:8080/api/v1/artifacts/art-550e8400-e29b-41d4-a716-446655440000/tags/tag-550e8400-e29b-41d4-a716-446655440000
```

---

## Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| `200 OK` | Success | GET requests, successful updates |
| `201 Created` | Resource created | POST requests creating new resources |
| `204 No Content` | Success (no body) | DELETE requests, successful updates with no response |
| `400 Bad Request` | Invalid input | Malformed request, validation failures |
| `404 Not Found` | Resource not found | Tag, artifact, or association doesn't exist |
| `409 Conflict` | Uniqueness violation | Duplicate tag name/slug, already-tagged artifact |
| `500 Internal Server Error` | Server error | Unexpected server-side failures |

---

## Error Handling

All error responses follow a consistent format:

```json
{
  "detail": "Error description message"
}
```

### Common Error Scenarios

#### 1. Duplicate Tag Creation

When creating a tag with a name or slug that already exists:

```bash
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python",
    "slug": "python"
  }'

# Response (409 Conflict):
{
  "detail": "Tag with name 'Python' already exists"
}
```

#### 2. Invalid Slug Format

When the slug doesn't follow kebab-case rules:

```bash
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Tag",
    "slug": "Test-Tag"  # Contains uppercase
  }'

# Response (400 Bad Request):
{
  "detail": "Slug must be lowercase"
}
```

#### 3. Invalid Color Code

When the color isn't a valid hex code:

```bash
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Design",
    "slug": "design",
    "color": "blue"  # Not a hex code
  }'

# Response (422 Unprocessable Entity):
{
  "detail": "Invalid color format. Use hex code like #FF5733"
}
```

#### 4. Missing Required Field

```bash
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python"
    # Missing required "slug" field
  }'

# Response (422 Unprocessable Entity):
{
  "detail": "Field required"
}
```

---

## Data Models

### Tag Response

Complete representation of a tag object:

```typescript
interface TagResponse {
  /** Unique tag identifier */
  id: string;

  /** Tag name (1-100 characters) */
  name: string;

  /** URL-friendly slug (kebab-case) */
  slug: string;

  /** Optional hex color code for visual customization */
  color?: string;

  /** Number of artifacts with this tag */
  artifact_count?: number;

  /** ISO 8601 timestamp when tag was created */
  created_at: string;

  /** ISO 8601 timestamp of last update */
  updated_at: string;
}
```

### Page Info

Pagination metadata for list responses:

```typescript
interface PageInfo {
  /** Whether there are more results after this page */
  has_next_page: boolean;

  /** Whether there are results before this page */
  has_previous_page: boolean;

  /** Cursor pointing to the first item on this page */
  start_cursor: string;

  /** Cursor for fetching the next page */
  end_cursor: string;

  /** Total count of all items (if computed) */
  total_count?: number;
}
```

### Tag List Response

Paginated list of tags:

```typescript
interface TagListResponse {
  /** List of tags for this page */
  items: TagResponse[];

  /** Pagination metadata */
  page_info: PageInfo;
}
```

---

## Examples

### Complete Tag Workflow

#### 1. Create Tags

```bash
# Create Python tag
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python",
    "slug": "python",
    "color": "#3776AB"
  }'

# Create AI Tools tag
curl -X POST http://localhost:8080/api/v1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Tools",
    "slug": "ai-tools",
    "color": "#3498DB"
  }'
```

#### 2. List All Tags

```bash
curl "http://localhost:8080/api/v1/tags?limit=20" \
  -H "Accept: application/json"
```

#### 3. Search for Tags

```bash
curl "http://localhost:8080/api/v1/tags/search?q=python&limit=10" \
  -H "Accept: application/json"
```

#### 4. Get Tag by Slug

```bash
curl "http://localhost:8080/api/v1/tags/slug/python" \
  -H "Accept: application/json"
```

#### 5. Add Tags to Artifact

Assuming artifact ID is `art-123`:

```bash
# Add Python tag
curl -X POST http://localhost:8080/api/v1/artifacts/art-123/tags/tag-python-001 \
  -H "Content-Type: application/json"

# Add AI Tools tag
curl -X POST http://localhost:8080/api/v1/artifacts/art-123/tags/tag-ai-tools-001 \
  -H "Content-Type: application/json"
```

#### 6. Get Artifact Tags

```bash
curl "http://localhost:8080/api/v1/artifacts/art-123/tags" \
  -H "Accept: application/json"
```

#### 7. Update Tag

```bash
curl -X PUT http://localhost:8080/api/v1/tags/tag-python-001 \
  -H "Content-Type: application/json" \
  -d '{
    "color": "#FF6600"
  }'
```

#### 8. Remove Tag from Artifact

```bash
curl -X DELETE http://localhost:8080/api/v1/artifacts/art-123/tags/tag-python-001
```

#### 9. Delete Tag

```bash
curl -X DELETE http://localhost:8080/api/v1/tags/tag-python-001
```

---

## Rate Limiting

Currently, the Tags API does not enforce rate limiting. Future versions may implement request rate limiting.

---

## API Versioning

The Tags API is part of the v1 API. All endpoints use the `/api/v1/` prefix. Future breaking changes will be introduced in a new version (v2, v3, etc.).

---

## Best Practices

### Tag Naming

- Use descriptive, meaningful names
- Keep names concise (10-20 characters when possible)
- Use consistent naming conventions
- Avoid acronyms unless widely recognized

```
Good:    "Python", "JavaScript", "Data Science"
Avoid:   "py", "js", "ds"  (unclear without context)
```

### Slug Creation

- Slugs should be derived from tag names
- Always use lowercase
- Use hyphens to separate words
- Keep slugs URL-safe and memorable

```
Good:    "python", "data-science", "machine-learning"
Avoid:   "python_123", "Data-Science", "ML"
```

### Color Usage

- Choose colors that contrast well for UI visibility
- Use standard hex color codes
- Ensure colors align with your design system

```
Good:    "#FF5733", "#3498DB", "#27AE60"
Avoid:   "red", "rgb(255, 87, 51)", "bright-blue"
```

### Artifact Organization

- Tag artifacts consistently for better discoverability
- Use 2-4 tags per artifact for optimal organization
- Avoid creating too many similar tags (consolidate when possible)
- Regularly review and prune unused tags

---

## Troubleshooting

### "Tag with name already exists"

**Cause**: Attempting to create a tag with a name that's already in use.

**Solution**:
- Use a different name, or
- Retrieve the existing tag with `GET /tags/search?q=<name>`

### "Slug must be lowercase"

**Cause**: Slug contains uppercase letters.

**Solution**: Convert slug to lowercase before submission.

```javascript
const slug = tagName.toLowerCase().replace(/\s+/g, '-');
```

### "Slug cannot start or end with hyphen"

**Cause**: Slug has hyphens at the beginning or end.

**Solution**: Remove leading/trailing hyphens.

```javascript
const slug = tagName
  .toLowerCase()
  .replace(/\s+/g, '-')
  .replace(/^-+|-+$/g, '');  // Remove leading/trailing hyphens
```

### "Invalid cursor format: tag not found"

**Cause**: The pagination cursor from a previous response is no longer valid.

**Solution**:
- Start pagination over with a fresh request
- Don't reuse cursors across multiple sessions

### "Artifact already has tag"

**Cause**: Attempting to add a tag to an artifact that already has that tag.

**Solution**: Check artifact's current tags with `GET /artifacts/{artifact_id}/tags` before adding.

---

## Related Documentation

- [Artifacts API](./artifacts.md) - Artifact management endpoints
- [Discovery Endpoints](./discovery-endpoints.md) - Finding and browsing artifacts
- [Marketplace Sources](./marketplace-sources.md) - Managing artifact sources
