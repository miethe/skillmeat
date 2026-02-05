# SkillMeat Sync API Endpoints: Complete Reference

## API Endpoints Quick Summary

| Endpoint | Method | Direction | Implements |
|----------|--------|-----------|------------|
| `/artifacts/{id}/sync` | POST | ⬆ Pull Source→Collection OR ⬇ Pull Project→Collection | Pull from upstream or sync from project |
| `/artifacts/{id}/deploy` | POST | → Collection→Project | Push/deploy to project |
| `/artifacts/{id}/diff` | GET | Collection ↔ Project | Compare for drift detection |
| `/artifacts/{id}/upstream-diff` | GET | Source ↔ Collection | Compare for update detection |

---

## Endpoint 1: POST /artifacts/{id}/sync

### Purpose
**Unified sync endpoint** serving two directions:
- **Pull from Source → Collection** (no `project_path`)
- **Pull from Project → Collection** (with `project_path`)

### Request

**URL**:
```
POST /api/v1/artifacts/{artifact_id}/sync?collection={optional-name}
```

**Path Parameters**:
- `artifact_id` (required): Format `"type:name"` (e.g., `"skill:pdf-parser"`)

**Query Parameters**:
- `collection` (optional): Collection name; defaults to active collection if omitted

**Request Body**:

```json
{
  "project_path": "/path/to/project",  // Optional: if present, syncs FROM project
  "force": false,                        // Optional: skip confirmation prompts
  "strategy": "theirs"                   // Optional: 'ours' | 'theirs' | 'manual'
}
```

**Scenarios**:

1. **Pull from upstream source** (empty body):
   ```json
   {}
   ```
   - No `project_path` triggers upstream sync
   - Fetches latest from GitHub
   - Applies strategy: overwrite (default)

2. **Pull from project** (with project_path):
   ```json
   {
     "project_path": "/Users/me/my-project",
     "strategy": "theirs"
   }
   ```
   - Takes project version as "theirs"
   - Overwrites collection with project changes

3. **Manual conflict resolution**:
   ```json
   {
     "force": true,
     "strategy": "manual"
   }
   ```
   - Preserves conflicts for manual resolution
   - Returns ConflictInfo array

### Response

**Status Code**: 200 (success) or error

**Response Body** (ArtifactSyncResponse):

```typescript
{
  success: boolean,
  message: string,
  artifact_name: string,
  artifact_type: string,
  conflicts?: [
    {
      filePath: string,
      conflictType: 'modified' | 'deleted' | 'added',
      currentVersion: string,
      upstreamVersion: string,
      description: string
    }
  ],
  updated_version?: string,
  synced_files_count?: number
}
```

### Example: Pull from Source

**Request**:
```bash
curl -X POST http://localhost:8080/api/v1/artifacts/skill:my-skill/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}'
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Sync Successful",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "updated_version": "v1.1.0",
  "synced_files_count": 3
}
```

**Response (Conflicts)**:
```json
{
  "success": true,
  "message": "Pull completed with conflicts",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "conflicts": [
    {
      "filePath": "SKILL.md",
      "conflictType": "modified",
      "currentVersion": "abc123...",
      "upstreamVersion": "def456...",
      "description": "Both sides modified file"
    }
  ]
}
```

### Error Responses

**404 Not Found**:
```json
{
  "detail": "Artifact 'skill:unknown' not found in collection 'default'"
}
```

**400 Bad Request** (no GitHub origin):
```json
{
  "detail": "Artifact does not have a GitHub origin. Upstream sync only supported for GitHub artifacts."
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Failed to fetch update from upstream: {error details}"
}
```

### Implementation Details

**Backend File**: `/skillmeat/api/routers/artifacts.py` (lines 3061-3250)

**Logic Flow**:
1. Parse artifact ID (type:name format)
2. If no `project_path`: upstream sync
   - Load collection and find artifact
   - Verify artifact.origin == "github"
   - Call `artifact_mgr.fetch_update()` → GitHub API
   - Call `artifact_mgr.apply_update_strategy()` → apply changes
3. If `project_path`: project sync
   - Load collection and find artifact
   - Get project version
   - Merge project changes into collection
4. Detect conflicts (look for `<<<<<<< ` markers)
5. Return response with conflicts if any

---

## Endpoint 2: POST /artifacts/{id}/deploy

### Purpose
**Deploy artifact from Collection to Project**
- Copies artifact files to project `.claude/` directory
- Updates deployment tracking in `.skillmeat-deployed.toml`
- One-way operation (Collection → Project only)

### Request

**URL**:
```
POST /api/v1/artifacts/{artifact_id}/deploy?collection={optional-name}
```

**Path Parameters**:
- `artifact_id` (required): Format `"type:name"`

**Query Parameters**:
- `collection` (optional): Collection name; defaults to first available

**Request Body**:

```json
{
  "project_path": "/path/to/project",
  "overwrite": true
}
```

**Fields**:
- `project_path` (required): Absolute path to project directory
- `overwrite` (required): Whether to overwrite existing files

### Response

**Status Code**: 200 (success) or error

**Response Body** (ArtifactDeployResponse):

```typescript
{
  success: boolean,
  message: string,
  artifact_name: string,
  artifact_type: string,
  error_message?: string,
  deployment_id?: string
}
```

### Example

**Request**:
```bash
curl -X POST http://localhost:8080/api/v1/artifacts/skill:my-skill/deploy \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "project_path": "/Users/me/my-project",
    "overwrite": true
  }'
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Deployed skill:my-skill to /Users/me/my-project",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "deployment_id": "dep_abc123"
}
```

**Response (Failed)**:
```json
{
  "success": false,
  "message": "Deployment failed",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "error_message": "Permission denied writing to /Users/me/my-project/.claude/skills/my-skill"
}
```

### Error Responses

**400 Bad Request** (invalid project path):
```json
{
  "detail": "Project path does not exist: /nonexistent/path"
}
```

**404 Not Found**:
```json
{
  "detail": "Artifact 'skill:unknown' not found in collection 'default'"
}
```

### Implementation Details

**Backend File**: `/skillmeat/api/routers/artifacts.py` (lines 2898-3000)

**Logic Flow**:
1. Validate project path exists
2. Load collection and find artifact
3. Create DeploymentManager
4. Call `deployment_mgr.deploy_artifacts()`
   - Copy artifact files to project/.claude/
   - Update .skillmeat-deployed.toml with deployment record
5. Return deployment result

---

## Endpoint 3: GET /artifacts/{id}/diff

### Purpose
**Compare Collection vs Project versions**
- Detects drift (local project modifications)
- Returns file-level diffs in unified format
- Used by SyncStatusTab for project-vs-collection comparison

### Request

**URL**:
```
GET /api/v1/artifacts/{artifact_id}/diff?project_path={path}&collection={optional-name}
```

**Path Parameters**:
- `artifact_id` (required): Format `"type:name"`

**Query Parameters**:
- `project_path` (required): Absolute path to project directory
- `collection` (optional): Collection name; searches all if omitted

### Response

**Status Code**: 200 (success) or error

**Response Body** (ArtifactDiffResponse):

```typescript
{
  artifact_id: string,
  artifact_name: string,
  artifact_type: string,
  collection_name: string,
  project_path: string,
  has_changes: boolean,
  files: [
    {
      file_path: string,
      status: 'added' | 'modified' | 'deleted' | 'unchanged',
      collection_hash: string,
      project_hash: string,
      unified_diff?: string  // Only for modified files
    }
  ],
  summary: {
    added: number,
    modified: number,
    deleted: number,
    unchanged: number
  }
}
```

### Example

**Request**:
```bash
curl "http://localhost:8080/api/v1/artifacts/skill:my-skill/diff?project_path=/Users/me/my-project"
```

**Response**:
```json
{
  "artifact_id": "skill:my-skill",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "collection_name": "default",
  "project_path": "/Users/me/my-project",
  "has_changes": true,
  "files": [
    {
      "file_path": "SKILL.md",
      "status": "modified",
      "collection_hash": "abc123def456",
      "project_hash": "def456abc123",
      "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1,5 +1,6 @@\n context line\n-old line\n+new line\n context line\n"
    },
    {
      "file_path": "examples.md",
      "status": "unchanged",
      "collection_hash": "same123",
      "project_hash": "same123",
      "unified_diff": null
    }
  ],
  "summary": {
    "added": 0,
    "modified": 1,
    "deleted": 0,
    "unchanged": 3
  }
}
```

### Error Responses

**404 Not Found** (artifact not in project):
```json
{
  "detail": "Artifact 'skill:unknown' not found in project /Users/me/my-project"
}
```

**400 Bad Request** (invalid project path):
```json
{
  "detail": "Project path does not exist: /nonexistent/path"
}
```

### Implementation Details

**Backend File**: `/skillmeat/api/routers/artifacts.py` (lines 3693-3900)

**Logic Flow**:
1. Validate project path
2. Find deployment record (or infer from standard paths)
3. Load collection and find artifact
4. Get artifact files from collection
5. Get artifact files from project
6. For each file:
   - Compute content hash (MD5)
   - If hashes differ: generate unified diff using difflib
7. Aggregate summary statistics
8. Return ArtifactDiffResponse

---

## Endpoint 4: GET /artifacts/{id}/upstream-diff

### Purpose
**Compare Source (GitHub) vs Collection versions**
- Detects available updates from upstream
- Returns file-level diffs in unified format
- Used by SyncStatusTab for source-vs-collection comparison

### Request

**URL**:
```
GET /api/v1/artifacts/{artifact_id}/upstream-diff?collection={optional-name}
```

**Path Parameters**:
- `artifact_id` (required): Format `"type:name"`

**Query Parameters**:
- `collection` (optional): Collection name; searches all if omitted

### Response

**Status Code**: 200 (success) or error

**Response Body** (ArtifactUpstreamDiffResponse):

```typescript
{
  artifact_id: string,
  artifact_name: string,
  artifact_type: string,
  collection_name: string,
  upstream_source: string,
  upstream_version: string,
  has_changes: boolean,
  files: [
    {
      file_path: string,
      status: 'added' | 'modified' | 'deleted' | 'unchanged',
      collection_hash: string,
      upstream_hash: string,
      unified_diff?: string  // Only for modified files
    }
  ],
  summary: {
    added: number,
    modified: number,
    deleted: number,
    unchanged: number
  }
}
```

### Example

**Request**:
```bash
curl "http://localhost:8080/api/v1/artifacts/skill:my-skill/upstream-diff?collection=default"
```

**Response**:
```json
{
  "artifact_id": "skill:my-skill",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "collection_name": "default",
  "upstream_source": "anthropics/skills/pdf-parser",
  "upstream_version": "v1.2.0",
  "has_changes": true,
  "files": [
    {
      "file_path": "SKILL.md",
      "status": "modified",
      "collection_hash": "abc123",
      "upstream_hash": "xyz789",
      "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n..."
    }
  ],
  "summary": {
    "added": 1,
    "modified": 1,
    "deleted": 0,
    "unchanged": 2
  }
}
```

### Error Responses

**404 Not Found** (artifact not found):
```json
{
  "detail": "Artifact 'skill:unknown' not found in any collection"
}
```

**400 Bad Request** (no GitHub origin):
```json
{
  "detail": "Artifact does not have upstream source. Only GitHub-origin artifacts support upstream diffs."
}
```

### Implementation Details

**Backend File**: `/skillmeat/api/routers/artifacts.py` (lines 4055-4200)

**Logic Flow**:
1. Find artifact in collection
2. Verify artifact has GitHub origin
3. Fetch latest version from GitHub
4. For each file:
   - Compute hash of collection version
   - Compute hash of upstream version
   - If different: generate unified diff
5. Return ArtifactUpstreamDiffResponse

---

## Query Key Cache Invalidation

### On Sync Success

```typescript
queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
```

### On Deploy Success

```typescript
queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, collection] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
```

### On Push/Capture Success

```typescript
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
queryClient.invalidateQueries({ queryKey: ['collections'] });
```

---

## Authentication

All endpoints require:
- **API Key**: `X-API-Key` header (if enabled)
- **Bearer Token**: `Authorization: Bearer {token}` header (if auth enabled)

**Default**: Both disabled in development

---

## Rate Limiting

Subject to configured rate limits:
- **Default**: 100 requests/minute per IP
- **Burst threshold**: 10 requests in 60 seconds

Returns **429 Too Many Requests** if exceeded.

---

## Common Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| 200 | Success | Operation completed successfully |
| 201 | Created | Resource created (not used by sync endpoints) |
| 400 | Bad Request | Invalid artifact ID, missing required fields |
| 401 | Unauthorized | Missing or invalid authentication |
| 404 | Not Found | Artifact, collection, or project not found |
| 422 | Unprocessable Entity | Request validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | GitHub API error, file system error, etc. |

---

## Testing with cURL

### Test Pull from Source

```bash
curl -X POST http://localhost:8080/api/v1/artifacts/skill:test/sync \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Test Deploy to Project

```bash
curl -X POST http://localhost:8080/api/v1/artifacts/skill:test/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/Users/me/my-project",
    "overwrite": true
  }'
```

### Test Get Diff

```bash
curl "http://localhost:8080/api/v1/artifacts/skill:test/diff?project_path=/Users/me/my-project"
```

### Test Get Upstream Diff

```bash
curl "http://localhost:8080/api/v1/artifacts/skill:test/upstream-diff"
```
