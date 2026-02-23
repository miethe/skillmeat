# Marketplace Sources API Endpoints

API endpoints for managing GitHub repository sources in the marketplace.

**Base URL**: `/api/v1/marketplace/sources`

---

updated: 2026-01-27

---

## Overview

The marketplace sources API allows you to manage GitHub repositories as artifact sources. These repositories are scanned for Claude Code artifacts (skills, commands, agents, hooks, MCP servers, etc.) and provide a centralized catalog for discovery and import.

**Key Features**:
- GitHub repository ingestion with automated scanning
- Search indexing for all artifact types (skills, commands, agents, hooks, MCP servers)
- Filtering by artifact type, tags, trust level, and text search
- Manual directory-to-type mappings for custom repository structures
- Tag management and path-based tag extraction
- Repository metadata import (description, README)
- Artifact catalog with confidence scoring
- On-demand rescan to refresh artifact metadata and search index

---

## Endpoints

### POST /marketplace/sources

Create a new GitHub repository source and trigger initial scan.

**Request Body** (`CreateSourceRequest`):

```typescript
{
  repo_url: string;                       // Full GitHub URL (required)
  ref?: string;                           // Branch, tag, or SHA (default: "main")
  root_hint?: string;                     // Subdirectory path to scan
  access_token?: string;                  // PAT for private repos (not stored)
  manual_map?: Record<string, string[]>;  // Directory → artifact type mapping
  trust_level?: "untrusted" | "basic" | "verified" | "official";  // Default: "basic"
  description?: string;                   // User description (max 500 chars)
  notes?: string;                         // Internal notes (max 2000 chars)
  enable_frontmatter_detection?: boolean; // Parse markdown frontmatter
  import_repo_description?: boolean;      // Fetch GitHub repo description
  import_repo_readme?: boolean;           // Fetch README content
  tags?: string[];                        // Tags for categorization (max 20)
}
```

**Example Request**:

```bash
curl -X POST http://localhost:8080/api/v1/marketplace/sources \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
    "ref": "main",
    "root_hint": "skills",
    "trust_level": "verified",
    "description": "Official Anthropic quickstart examples",
    "import_repo_description": true,
    "import_repo_readme": true,
    "tags": ["official", "quickstart", "examples"]
  }'
```

**Response** (`SourceResponse` - 201 Created):

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
  "scan_status": "scanning",
  "artifact_count": 0,
  "last_sync_at": null,
  "last_error": null,
  "created_at": "2025-01-18T10:00:00Z",
  "updated_at": "2025-01-18T10:00:00Z",
  "description": "Official Anthropic quickstart examples",
  "notes": null,
  "enable_frontmatter_detection": false,
  "manual_map": null,
  "repo_description": "Official quickstart examples from Anthropic",
  "repo_readme": "# Anthropic Quickstarts\n\nWelcome to...",
  "tags": ["official", "quickstart", "examples"],
  "counts_by_type": {}
}
```

**Field Descriptions**:

- **repo_url**: Full GitHub repository URL (must be `https://github.com/{owner}/{repo}`)
- **ref**: Git reference to scan (branch, tag, or SHA). Default: `main`
- **root_hint**: Optional subdirectory to start scanning (e.g., `"skills"` to only scan `/skills/**`)
- **manual_map**: Override automatic artifact type detection for specific directories
- **trust_level**: Controls how artifacts from this source are treated
  - `untrusted`: Not verified
  - `basic`: Basic trust (default)
  - `verified`: Verified trustworthy source
  - `official`: Official Anthropic source
- **import_repo_description**: Fetch repository description from GitHub API on creation
- **import_repo_readme**: Fetch README.md content from repository
- **tags**: Searchable tags for categorization (normalized to lowercase, max 20 tags, each 1-50 chars)
- **counts_by_type**: Artifact counts broken down by type (e.g., `{"skill": 8, "command": 3}`)

**Error Responses**:

- **400 Bad Request**: Invalid repository URL format
- **409 Conflict**: Repository URL already exists
- **422 Unprocessable Entity**: Invalid `manual_map` directory paths
- **500 Internal Server Error**: Database or GitHub API error

---

### GET /marketplace/sources

List all GitHub sources with filtering and pagination.

**Query Parameters**:

```typescript
{
  limit?: number;           // Max items per page (1-100, default: 50)
  cursor?: string;          // Cursor for next page
  artifact_type?: string;   // Filter by artifact type ("skill", "command", etc.)
  tags?: string[];          // Filter by tags (AND logic - must match all)
  trust_level?: string;     // Filter by trust level
  search?: string;          // Search in repo name, description, tags
}
```

**Filtering Behavior**:

All filters use **AND logic** - sources must match ALL provided filters:

- **artifact_type**: Sources that contain at least one artifact of this type
- **tags**: Sources that have ALL specified tags (e.g., `?tags=ui&tags=ux` requires both tags)
- **trust_level**: Sources with this exact trust level
- **search**: Text search across `repo_name`, `description`, and `tags` (case-insensitive)

**Example Requests**:

```bash
# List all sources (paginated)
curl "http://localhost:8080/api/v1/marketplace/sources?limit=20"

# Filter by artifact type
curl "http://localhost:8080/api/v1/marketplace/sources?artifact_type=skill"

# Filter by multiple tags (AND logic)
curl "http://localhost:8080/api/v1/marketplace/sources?tags=official&tags=verified"

# Filter by trust level
curl "http://localhost:8080/api/v1/marketplace/sources?trust_level=verified"

# Combine filters and search
curl "http://localhost:8080/api/v1/marketplace/sources?artifact_type=skill&search=python&trust_level=verified"

# Pagination with cursor
curl "http://localhost:8080/api/v1/marketplace/sources?limit=20&cursor=src_abc123"
```

**Response** (`SourceListResponse`):

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
      "last_sync_at": "2025-01-18T10:30:00Z",
      "last_error": null,
      "created_at": "2025-01-18T09:00:00Z",
      "updated_at": "2025-01-18T10:30:00Z",
      "description": "Official Anthropic skills repository",
      "notes": null,
      "enable_frontmatter_detection": false,
      "manual_map": null,
      "repo_description": "Official quickstart examples",
      "repo_readme": "# Anthropic Quickstarts\n\n...",
      "tags": ["official", "quickstart", "examples"],
      "counts_by_type": {
        "skill": 8,
        "command": 3,
        "agent": 1
      }
    }
  ],
  "page_info": {
    "has_next_page": true,
    "has_previous_page": false,
    "start_cursor": "src_anthropics_quickstarts",
    "end_cursor": "src_xyz789",
    "total_count": 50
  }
}
```

**Pagination**:

- Uses **cursor-based pagination** for stable results
- `start_cursor`: First item ID on current page
- `end_cursor`: Last item ID on current page (use this as `cursor` param for next page)
- `total_count`: Total matching sources (only computed when filters are active)

**Performance Notes**:

- **Without filters**: Efficient database query with pagination
- **With filters**: Loads all sources, applies filters in-memory, then paginates (includes `total_count`)

---

### GET /marketplace/sources/{id}

Get a specific source by ID with all metadata.

**Path Parameters**:

- `id` (string, required): Source ID

**Example Request**:

```bash
curl "http://localhost:8080/api/v1/marketplace/sources/src_anthropics_quickstarts"
```

**Response** (`SourceResponse`):

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
  "last_sync_at": "2025-01-18T10:30:00Z",
  "last_error": null,
  "created_at": "2025-01-18T09:00:00Z",
  "updated_at": "2025-01-18T10:30:00Z",
  "description": "Official Anthropic skills repository",
  "notes": "Contains verified skills from Anthropic team",
  "enable_frontmatter_detection": false,
  "manual_map": null,
  "repo_description": "Official quickstart examples from Anthropic",
  "repo_readme": "# Anthropic Quickstarts\n\nWelcome to...",
  "tags": ["official", "quickstart", "examples"],
  "counts_by_type": {
    "skill": 8,
    "command": 3,
    "agent": 1
  }
}
```

**New Fields (vs. legacy response)**:

- `repo_description`: GitHub repository description (fetched if `import_repo_description: true`)
- `repo_readme`: README.md content (fetched if `import_repo_readme: true`)
- `tags`: Array of searchable tags
- `counts_by_type`: Artifact counts by type (replaces simple `artifact_count`)

**Error Responses**:

- **404 Not Found**: Source ID does not exist
- **500 Internal Server Error**: Database error

---

### PATCH /marketplace/sources/{id}

Update source configuration (partial update).

**Path Parameters**:

- `id` (string, required): Source ID

**Request Body** (`UpdateSourceRequest`):

All fields are optional - only provided fields will be updated.

```typescript
{
  ref?: string;                           // Change branch/tag/SHA
  root_hint?: string;                     // Change scan root
  manual_map?: Record<string, string>;    // Update directory mappings
  trust_level?: "untrusted" | "basic" | "verified" | "official";
  description?: string;                   // Update user description
  notes?: string;                         // Update internal notes
  enable_frontmatter_detection?: boolean; // Toggle frontmatter parsing
  import_repo_description?: boolean;      // Re-fetch repo description
  import_repo_readme?: boolean;           // Re-fetch README
  tags?: string[];                        // Replace tags
}
```

**Example Requests**:

```bash
# Update tags only
curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src_abc123" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["updated", "production", "verified"]}'

# Update trust level and description
curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "trust_level": "verified",
    "description": "Updated description"
  }'

# Change branch and re-fetch README
curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "v2.0.0",
    "import_repo_readme": true
  }'
```

**Response** (`SourceResponse`):

Returns the updated source with all fields.

**Behavior**:

- **Partial update**: Only fields in request body are modified
- **Tag replacement**: `tags` field replaces ALL existing tags (not merge)
- **Validation**: Same rules as creation (tags normalized to lowercase, path traversal checks, etc.)
- **No automatic rescan**: Updating source does NOT trigger rescan. Use `POST /{id}/rescan` to rescan.

**Error Responses**:

- **400 Bad Request**: Invalid field values
- **404 Not Found**: Source ID does not exist
- **422 Unprocessable Entity**: Validation error (e.g., invalid `manual_map` paths)
- **500 Internal Server Error**: Database error

---

### POST /marketplace/sources/{id}/rescan

Trigger a rescan of a GitHub source to refresh the artifact catalog and search index.

**Path Parameters:**

- `id` (string, required): Source ID

**Request Body:** None required

**Example Request:**

```bash
# Rescan a specific source
curl -X POST "http://localhost:8080/api/v1/marketplace/sources/src_abc123/rescan"
```

**Response** (`SourceResponse` - 200 OK):

Returns the source with `scan_status: "scanning"` indicating rescan has started.

**What happens during rescan:**

1. Repository is re-scanned for artifacts
2. Artifact metadata is refreshed from frontmatter
3. Search index is updated for all artifact types (skills, commands, agents, hooks, MCP servers)
4. Tags are refreshed from artifact frontmatter
5. `last_sync_at` timestamp is updated on completion

**Use Cases:**

- After upstream repository changes
- To refresh search indexing after SkillMeat updates
- To fix stale artifact metadata

**Bulk Rescan (Developer Pattern):**

To rescan all sources programmatically:

```bash
# Get all source IDs and rescan each
for id in $(curl -s "http://localhost:8080/api/v1/marketplace/sources" | jq -r '.items[].id'); do
  curl -X POST "http://localhost:8080/api/v1/marketplace/sources/$id/rescan"
  sleep 1  # Rate limit between rescans
done
```

**Error Responses:**

- **404 Not Found**: Source ID does not exist
- **409 Conflict**: Source is already scanning
- **500 Internal Server Error**: GitHub API or database error

---

## Response Models

### SourceResponse

```typescript
interface SourceResponse {
  id: string;                    // Unique source ID
  repo_url: string;              // Full GitHub repository URL
  owner: string;                 // Repository owner
  repo_name: string;             // Repository name
  ref: string;                   // Branch, tag, or SHA
  root_hint: string | null;      // Subdirectory path for scanning
  trust_level: "untrusted" | "basic" | "verified" | "official";
  visibility: "public" | "private";
  scan_status: "pending" | "scanning" | "success" | "error";
  artifact_count: number;        // Total artifacts detected
  last_sync_at: string | null;   // ISO 8601 timestamp
  last_error: string | null;     // Last error message
  created_at: string;            // ISO 8601 timestamp
  updated_at: string;            // ISO 8601 timestamp
  description: string | null;    // User description
  notes: string | null;          // Internal notes
  enable_frontmatter_detection: boolean;
  manual_map: Record<string, string> | null;  // Directory → type mapping
  repo_description: string | null;  // GitHub repo description
  repo_readme: string | null;       // README content
  tags: string[];                   // Searchable tags
  counts_by_type: Record<string, number>;  // Counts by artifact type
  indexing_enabled: boolean;     // Whether search indexing is enabled for this source
  last_indexed_at: string | null;  // When search index was last updated (ISO 8601)
}
```

### SourceListResponse

```typescript
interface SourceListResponse {
  items: SourceResponse[];
  page_info: PageInfo;
}

interface PageInfo {
  has_next_page: boolean;
  has_previous_page: boolean;
  start_cursor: string | null;
  end_cursor: string | null;
  total_count: number | null;  // Only set when filters are active
}
```

---

## Common Patterns

### Filter Composition (AND Logic)

When multiple filters are provided, they compose with AND logic:

```bash
# Source must have:
# - At least one "skill" artifact
# - ALL tags: "ui" AND "ux"
# - Trust level: "verified"
# - Text "design" in name/description/tags
curl "http://localhost:8080/api/v1/marketplace/sources?\
artifact_type=skill&\
tags=ui&tags=ux&\
trust_level=verified&\
search=design"
```

### Tag Normalization

Tags are automatically normalized to lowercase:

```json
// Request
{"tags": ["UI-UX", "Production", "VERIFIED"]}

// Stored as
{"tags": ["ui-ux", "production", "verified"]}
```

### Pagination Loop

```bash
# Fetch first page
CURSOR=""
while true; do
  RESPONSE=$(curl "http://localhost:8080/api/v1/marketplace/sources?limit=50&cursor=$CURSOR")

  # Process items...

  # Check if more pages
  HAS_MORE=$(echo "$RESPONSE" | jq -r '.page_info.has_next_page')
  if [ "$HAS_MORE" != "true" ]; then
    break
  fi

  # Get next cursor
  CURSOR=$(echo "$RESPONSE" | jq -r '.page_info.end_cursor')
done
```

### Repository Metadata Import

To fetch repository description and README on creation:

```json
{
  "repo_url": "https://github.com/owner/repo",
  "import_repo_description": true,
  "import_repo_readme": true
}
```

These are stored in `repo_description` and `repo_readme` fields and can be updated later via PATCH.

---

## Rate Limiting

**GitHub API**:
- Unauthenticated: 60 requests/hour
- Authenticated (with `access_token`): 5,000 requests/hour

**Recommendation**: Provide `access_token` for private repositories and higher rate limits.

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Error Codes**:

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid URL format, malformed JSON |
| 404 | Not Found | Source ID does not exist |
| 409 | Conflict | Repository URL already exists |
| 422 | Unprocessable Entity | Validation error (invalid paths, tags, etc.) |
| 500 | Internal Server Error | Database error, GitHub API failure |

---

## Authentication

**Current**: No authentication required (single-user mode)

**Future**: Token-based authentication when multi-user support is added.

---

## See Also

- [Component Documentation](/Users/miethe/dev/homelab/development/skillmeat/docs/components/marketplace-source-components.md)
- [Marketplace Catalog API](/Users/miethe/dev/homelab/development/skillmeat/docs/api/endpoints/marketplace-catalog.md) (for artifact operations)
- [SkillMeat API Reference](/Users/miethe/dev/homelab/development/skillmeat/docs/api/README.md)
