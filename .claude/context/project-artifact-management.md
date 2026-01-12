---
title: Project-Level Artifact Management Architecture
description: Complete guide to how projects manage deployed artifacts in SkillMeat
references:
  - skillmeat/core/deployment.py
  - skillmeat/core/artifact.py
  - skillmeat/storage/deployment.py
  - skillmeat/storage/project.py
  - skillmeat/api/routers/deployments.py
  - skillmeat/api/routers/projects.py
  - skillmeat/api/project_registry.py
last_verified: 2026-01-11
---

# Project-Level Artifact Management

## Overview

**Project** = A `.claude/` directory within a user's codebase that contains deployed artifacts from a collection. Projects act as deployment targets, tracking which artifacts have been deployed, their versions, and modification status.

### Core Concept

```
User's Codebase (Project)
  ├── .claude/
  │   ├── .skillmeat-deployed.toml    # Deployment metadata
  │   ├── .skillmeat-project.toml     # Project metadata
  │   ├── skills/
  │   │   ├── skillmeat-cli/
  │   │   └── meatycapture-capture/
  │   ├── commands/
  │   │   └── review.md
  │   ├── agents/
  │   │   └── pm/prd-writer.md
  │   └── context/, rules/, specs/    # Project context
  └── [other project files]
```

---

## Project Definition

### What is a Project?

**Project** = A directory containing a `.claude/` subdirectory with deployment tracking files.

**Required structure**:
- `{project_path}/.claude/` directory (created by `init` or first deployment)
- `{project_path}/.claude/.skillmeat-deployed.toml` (deployment tracking)
- Optional: `{project_path}/.claude/.skillmeat-project.toml` (project metadata)

**File locations**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/project.py`

### Project Metadata (.skillmeat-project.toml)

Stores project-level information separate from deployment tracking.

**File location**: `{project_path}/.claude/.skillmeat-project.toml`

**Class**: `ProjectMetadata` (skillmeat/storage/project.py:21)

**Structure**:
```toml
[project]
path = "/Users/me/my-project"              # Absolute project path
name = "my-project"                        # Project name (user-friendly)
description = "Description of project"    # Optional description
created_at = "2025-11-24T12:00:00"        # Creation timestamp (ISO format)
updated_at = "2025-11-24T14:30:00"        # Last update timestamp
```

**Storage class**: `ProjectMetadataStorage` (skillmeat/storage/project.py:75)

**Key methods**:
- `read_metadata(project_path)` → Optional[ProjectMetadata]
- `write_metadata(project_path, metadata)` → None
- `create_metadata(project_path, name, description)` → ProjectMetadata
- `update_metadata(project_path, name, description)` → Optional[ProjectMetadata]
- `delete_metadata(project_path)` → bool
- `exists(project_path)` → bool

---

## Deployment Metadata (.skillmeat-deployed.toml)

Tracks which artifacts have been deployed to the project.

**File location**: `{project_path}/.claude/.skillmeat-deployed.toml`

**Format**: TOML with `[[deployed]]` array of deployment records

### Deployment Record Structure

**Class**: `Deployment` (skillmeat/core/deployment.py:17)

**Fields**:
```python
# Core identification
artifact_name: str              # "skillmeat-cli"
artifact_type: str              # "skill", "command", "agent", "mcp", "hook"
from_collection: str            # "default" (source collection name)

# Deployment metadata
deployed_at: datetime           # When deployed (ISO format)
artifact_path: Path             # Relative path in .claude/ (e.g., "skills/skillmeat-cli")

# Version tracking (ADR-004)
content_hash: str               # SHA-256 of artifact content at deployment
local_modifications: bool       # True if file changed since deployment

# Optional version tracking fields
parent_hash: Optional[str]      # Hash of parent version (if from collection)
version_lineage: List[str]      # Array of hashes [newest_first]
last_modified_check: Optional[datetime]     # Last drift check timestamp
modification_detected_at: Optional[datetime] # When first detected as modified
merge_base_snapshot: Optional[str]          # Content hash for 3-way merges

# Backward compatibility
collection_sha: Optional[str]   # Deprecated: use content_hash instead
```

### Example TOML

```toml
[[deployed]]
artifact_name = "skillmeat-cli"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-01-05T15:07:49.157370"
artifact_path = "skills/skillmeat-cli"
content_hash = "2e7442e246b43330c40e3a09313bc002a3c08b28261f35ac64d1f6a4201944a5"
local_modifications = false
version_lineage = ["2e7442e246b43330c40e3a09313bc002a3c08b28261f35ac64d1f6a4201944a5"]
collection_sha = "2e7442e246b43330c40e3a09313bc002a3c08b28261f35ac64d1f6a4201944a5"

[[deployed]]
artifact_name = "prd-writer"
artifact_type = "agent"
from_collection = "default"
deployed_at = "2026-01-09T14:32:10.550083"
artifact_path = "agents/pm/prd-writer.md"
content_hash = "4c1dd9d428073f665d9b198c506da53b6337ca7676d80684b7126fae77bf5ff2"
local_modifications = false
merge_base_snapshot = "4c1dd9d428073f665d9b198c506da53b6337ca7676d80684b7126fae77bf5ff2"
```

---

## Artifact Scopes: "User" vs "Local"

### Two-Level Scope System

**Scope** = Where an artifact lives when deployed.

| Scope | Location | Audience | Use Case |
|-------|----------|----------|----------|
| **user** | `~/.skillmeat/skills/user/{name}/` | Global across all projects | Shared utilities, personal tools |
| **local** | `{project_path}/.claude/{type}/{name}/` | Project-specific only | Project templates, custom agents |

### Artifact Registration by Scope

**CLAUDE.md notes** (important):
- `user` scope artifacts are **globally accessible** from any project
- `local` scope artifacts are **stored in the project** itself
- Collection manifest specifies scope: `scope = "user"` or `scope = "local"`

### Deployment Behavior

**Current implementation** (skillmeat/core/deployment.py:228-239):
```python
if artifact.type == ArtifactType.SKILL:
    final_dest_path = dest_base / "skills" / artifact.name
elif artifact.type == ArtifactType.COMMAND:
    final_dest_path = dest_base / "commands" / f"{artifact.name}.md"
elif artifact.type == ArtifactType.AGENT:
    final_dest_path = dest_base / "agents" / f"{artifact.name}.md"
elif artifact.type == ArtifactType.MCP:
    final_dest_path = dest_base / "mcp" / artifact.name
elif artifact.type == ArtifactType.HOOK:
    final_dest_path = dest_base / "hooks" / f"{artifact.name}.md"
```

**Destination paths**:
- Skills: `.claude/skills/{name}/` (directory-based)
- Commands: `.claude/commands/{name}.md` (file-based)
- Agents: `.claude/agents/{path}/{name}.md` (file-based, may be nested)
- MCP: `.claude/mcp/{name}/` (directory-based)
- Hooks: `.claude/hooks/{name}.md` (file-based)

**Custom destination**: Can override with `dest_path` parameter to `deploy_artifacts()`

---

## Deployment Workflow

### Deploy Artifacts (Core Logic)

**File**: skillmeat/core/deployment.py:161-340

**Class**: `DeploymentManager`

**Main method**: `deploy_artifacts(artifact_names, collection_name, project_path, artifact_type, overwrite, dest_path)`

**Workflow**:

1. **Load Collection** (line 191-194)
   - Find source collection
   - Get collection path from CollectionManager

2. **For Each Artifact** (line 204-340)
   - Find artifact by name in collection
   - Resolve source path: `{collection_path}/{artifact.path}`
   - Determine destination path (based on type)
   - Validate destination is within project
   - Check if already deployed (line 250)
     - If yes and `overwrite=False`, prompt user
     - If yes and `overwrite=True`, undeploy first (line 186)
   - Copy artifact files (line 260)
   - Compute content hash (line 269)
   - **Record deployment** (line 272-274)
   - Create version record (line 277-282) - stores in cache database
   - Create Deployment object (line 295-305)
     - Set `merge_base_snapshot` = `content_hash` (baseline for 3-way merges)

3. **Record Events** (line 308-316)
   - Analytics tracking for deploy event

4. **Capture Snapshot** (line 318-338)
   - Auto-snapshot after deployment for version tracking

**Returns**: List of Deployment objects

### Record Deployment

**File**: skillmeat/storage/deployment.py:74-132

**Class**: `DeploymentTracker.record_deployment(project_path, artifact, collection_name, collection_sha)`

**Workflow**:

1. Read existing deployments from TOML
2. Determine artifact_path based on artifact type
3. Check if artifact already deployed
4. Create new Deployment object
5. Add or replace in deployments list
6. Write back to `.skillmeat-deployed.toml`

---

## Deployment API Endpoints

**File**: skillmeat/api/routers/deployments.py

### POST /api/v1/deploy

**Deploy artifact to project**

**Request**:
```json
{
  "artifact_id": "skillmeat-cli",
  "artifact_name": "skillmeat-cli",
  "artifact_type": "skill",
  "collection_name": "default",
  "project_path": "/Users/me/my-project",
  "dest_path": ".claude/skills/custom/",  // Optional custom path
  "overwrite": false
}
```

**Response** (201):
```json
{
  "success": true,
  "message": "Artifact 'skillmeat-cli' deployed successfully",
  "deployment_id": "skill:skillmeat-cli",
  "artifact_name": "skillmeat-cli",
  "artifact_type": "skill",
  "project_path": "/Users/me/my-project",
  "deployed_path": "skills/skillmeat-cli",
  "deployed_at": "2026-01-10T14:00:00Z"
}
```

**Error codes**:
- 400: Invalid artifact type, invalid dest_path (directory traversal, absolute path)
- 404: Artifact not found in collection
- 409: Artifact already deployed (if `overwrite=false`)
- 500: Deployment failed

### POST /api/v1/deploy/undeploy

**Remove artifact from project**

**Request**:
```json
{
  "artifact_name": "skillmeat-cli",
  "artifact_type": "skill",
  "project_path": "/Users/me/my-project"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Artifact 'skillmeat-cli' removed successfully",
  "artifact_name": "skillmeat-cli",
  "artifact_type": "skill",
  "project_path": "/Users/me/my-project"
}
```

### GET /api/v1/deploy

**List deployments in project**

**Query parameters**:
- `project_path` (optional): Project directory path (defaults to CWD)

**Response**:
```json
{
  "project_path": "/Users/me/my-project",
  "deployments": [
    {
      "artifact_name": "skillmeat-cli",
      "artifact_type": "skill",
      "from_collection": "default",
      "deployed_at": "2026-01-05T15:07:49Z",
      "artifact_path": "skills/skillmeat-cli",
      "project_path": "/Users/me/my-project",
      "collection_sha": "2e7442e2...",
      "local_modifications": false,
      "sync_status": "synced"  // "synced", "modified", "outdated"
    }
  ],
  "total": 1
}
```

---

## Project Registry & Discovery

### Project Registry

**File**: skillmeat/api/project_registry.py

**Class**: `ProjectRegistry` (singleton)

**Purpose**: Cached project discovery to avoid expensive filesystem scans

**Architecture**:
- In-memory cache with TTL (default: 5 minutes)
- Caches discovered projects to ~50ms response times
- Background refresh task (non-blocking)
- Manual invalidation on mutations (deploy/delete)

**Key methods**:
```python
async def get_projects(force_refresh: bool = False) -> List[ProjectCacheEntry]
    # Get all projects with caching

async def refresh_entry(project_path: Path) -> None
    # Refresh cache for specific project

async def invalidate(project_path: Path) -> None
    # Remove project from cache

def get_cache_stats() -> dict
    # Return cache status info
```

**Cache entry**:
```python
@dataclass
class ProjectCacheEntry:
    path: Path                          # Absolute path
    name: str                           # Project name
    deployment_count: int               # Count of deployed artifacts
    last_deployment: Optional[datetime] # Most recent deployment timestamp
    cached_at: datetime                 # When cached
```

### Project Discovery

**File**: skillmeat/api/routers/projects.py:141-206

**Function**: `discover_projects(search_paths)`

**Algorithm**:
1. Scan `~/.skillmeat/projects/`, `~/dev`, `~/workspace`, `~/src`, `CWD` (configurable)
2. Look for `.claude/.skillmeat-deployed.toml` files
3. Extract project root (parent of .claude)
4. Validate paths (security check) and depth limit (MAX_DEPTH=3)
5. Return list of project paths

**Performance**: ~10-30 seconds for full scan on large filesystems

---

## Projects API Endpoints

**File**: skillmeat/api/routers/projects.py

### GET /api/v1/projects

**List all projects**

**Query parameters**:
- `limit` (default 20, max 100): Items per page
- `after` (optional): Pagination cursor
- `refresh` (default false): Force cache refresh

**Response** (200):
```json
{
  "items": [
    {
      "id": "L1VzZXJzL21lL3Byb2plY3Qx",  // base64-encoded path
      "path": "/Users/me/project1",
      "name": "project1",
      "deployment_count": 5,
      "last_deployment": "2026-01-10T14:00:00Z",
      "cache_info": {
        "cache_hit": true,
        "last_fetched": "2026-01-10T13:55:00Z",
        "is_stale": false
      }
    }
  ],
  "page_info": {
    "has_next_page": true,
    "has_previous_page": false,
    "start_cursor": "...",
    "end_cursor": "...",
    "total_count": 42
  }
}
```

**Performance notes**:
- Cache hit: <50ms response
- Cache miss: ~5-30s (full filesystem scan)
- Uses persistent SQLite cache for faster subsequent requests

### POST /api/v1/projects

**Create new project**

**Request**:
```json
{
  "name": "my-project",
  "path": "/Users/me/projects/my-project",
  "description": "Optional description"
}
```

**Response** (201):
```json
{
  "id": "L1VzZXJzL21lL3Byb2plY3Qx",
  "path": "/Users/me/projects/my-project",
  "name": "my-project",
  "description": "Optional description",
  "created_at": "2026-01-11T12:00:00Z"
}
```

**Workflow**:
1. Create project directory
2. Create `.claude/` subdirectory
3. Store project metadata
4. Create empty `.skillmeat-deployed.toml` (makes discoverable)
5. Update registries and caches

### GET /api/v1/projects/{project_id}

**Get project details**

**Response**:
```json
{
  "id": "L1VzZXJzL21lL3Byb2plY3Qx",
  "path": "/Users/me/project1",
  "name": "project1",
  "deployment_count": 5,
  "last_deployment": "2026-01-10T14:00:00Z",
  "deployments": [
    {
      "artifact_name": "skillmeat-cli",
      "artifact_type": "skill",
      "from_collection": "default",
      "deployed_at": "2026-01-05T15:07:49Z",
      "artifact_path": "skills/skillmeat-cli",
      "version": null,
      "collection_sha": "2e7442e2...",
      "local_modifications": false
    }
  ],
  "stats": {
    "by_type": {"skill": 3, "agent": 2},
    "by_collection": {"default": 5},
    "modified_count": 0
  }
}
```

### PUT /api/v1/projects/{project_id}

**Update project metadata**

**Request**:
```json
{
  "name": "renamed-project",
  "description": "Updated description"
}
```

### DELETE /api/v1/projects/{project_id}

**Delete project**

**Query parameters**:
- `delete_files` (default false): If true, delete project directory from disk

**Response**:
```json
{
  "success": true,
  "message": "Project removed from tracking successfully",
  "deleted_files": false
}
```

### DELETE /api/v1/projects/{project_id}/deployments/{artifact_name}

**Remove specific deployment**

**Query parameters**:
- `artifact_type` (required): Type of artifact (skill, command, agent, etc.)
- `remove_files` (default true): If true, remove files from filesystem

**Response**:
```json
{
  "success": true,
  "message": "Artifact 'skillmeat-cli' removed from project successfully",
  "artifact_name": "skillmeat-cli",
  "artifact_type": "skill",
  "project_path": "/Users/me/project1",
  "files_removed": true
}
```

### POST /api/v1/projects/{project_id}/check-modifications

**Check for local modifications**

**Response**:
```json
{
  "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
  "checked_at": "2026-01-11T12:00:00Z",
  "modifications_detected": 2,
  "deployments": [
    {
      "artifact_name": "skillmeat-cli",
      "artifact_type": "skill",
      "deployed_sha": "abc123...",
      "current_sha": "def456...",
      "is_modified": true,
      "modification_detected_at": "2026-01-10T15:45:00Z",
      "change_origin": "local_modification",
      "baseline_hash": "abc123..."
    }
  ]
}
```

### GET /api/v1/projects/{project_id}/drift/summary

**Detect drift between project and collection**

**Response**:
```json
{
  "project_path": "/Users/me/project1",
  "collection_name": "default",
  "upstream_changes": 2,
  "local_changes": 1,
  "conflicts": 0,
  "total": 3,
  "modified_count": 1,
  "outdated_count": 2,
  "conflict_count": 0,
  "added_count": 0,
  "removed_count": 0,
  "version_mismatch_count": 0,
  "drift_details": [...]
}
```

### GET /api/v1/projects/{project_id}/context-map

**Discover context entities in project**

**Response**:
```json
{
  "auto_loaded": [
    {
      "type": "spec_file",
      "name": "doc-policy-spec",
      "path": ".claude/specs/doc-policy-spec.md",
      "tokens": 800,
      "auto_load": true
    }
  ],
  "on_demand": [
    {
      "type": "context_file",
      "name": "api-endpoint-mapping",
      "path": ".claude/context/api-endpoint-mapping.md",
      "tokens": 3000,
      "auto_load": false
    }
  ],
  "total_auto_load_tokens": 800
}
```

---

## Version Tracking

### Content Hash (SHA-256)

Every deployed artifact gets a SHA-256 hash computed at deployment time.

**Purpose**:
- Detect local modifications (compare current hash vs `content_hash`)
- Track version history (`version_lineage`)
- 3-way merge baseline (`merge_base_snapshot`)

**Computed by**: `skillmeat.utils.filesystem.compute_content_hash(path)`

### Version Lineage

Array of hashes tracking deployment and modification history.

**Format**: `["newest_hash", "previous_hash", ...]`

**Example**:
```toml
version_lineage = [
    "2e7442e246b43330c40e3a09313bc002a3c08b28261f35ac64d1f6a4201944a5"
]
```

### Merge Base Snapshot

Hash used as baseline for 3-way merges when syncing with upstream.

**Set at**: Deployment time (`merge_base_snapshot = content_hash`)

**Used by**: Sync manager for conflict resolution

---

## Modification Detection

### Drift Detection

Uses `SyncManager.check_drift()` to detect:
- **local_modification**: Project artifact differs from deployment baseline
- **outdated**: Collection has newer version
- **conflict**: Both local and upstream changes
- **added**: New artifact in collection
- **removed**: Artifact no longer in collection

**File**: skillmeat/core/sync.py (uses DriftDetectionResult model)

**Key fields**:
- `drift_type`: Type of drift (local_modification, outdated, conflict, etc.)
- `change_origin`: "local_modification", "sync", "deployment"
- `current_hash`: Current SHA-256 of project artifact
- `baseline_hash`: Original deployment hash
- `modification_detected_at`: When modification was first detected

### Modification Flags

Deployment record tracks:
- `local_modifications: bool` - Simple flag for "modified or not"
- `last_modified_check: datetime` - When drift check ran
- `modification_detected_at: datetime` - When change first detected

---

## Important Implementation Details

### Artifact Path Resolution

**Relative paths in deployment metadata**:
- Stored relative to `.claude/` directory when possible
- Examples: `"skills/skillmeat-cli"`, `"commands/review.md"`, `"agents/pm/prd-writer.md"`
- Full path reconstructed as: `{project_path}/.claude/{artifact_path}`

**Code** (skillmeat/core/deployment.py:289-293):
```python
try:
    artifact_path = final_dest_path.relative_to(dest_base)  # Relative to .claude/
except ValueError:
    artifact_path = final_dest_path.relative_to(project_path)  # Custom path outside .claude/
```

### Directory vs File-Based Artifacts

| Type | Format | Deployment Structure |
|------|--------|----------------------|
| Skill | Directory | `.claude/skills/{name}/` (contains SKILL.md, etc.) |
| Command | File | `.claude/commands/{name}.md` |
| Agent | File | `.claude/agents/{path}/{name}.md` |
| MCP | Directory | `.claude/mcp/{name}/` |
| Hook | File | `.claude/hooks/{name}.md` |

### Base64 Project ID Encoding

Projects are identified by base64-encoded absolute paths in API.

**Example**:
- Path: `/Users/me/project1`
- Encoded ID: `L1VzZXJzL21lL3Byb2plY3Qx`

**Used by**: All project API endpoints

**Codec**: Python `base64` module (URL-safe not used)

---

## Security Considerations

### Path Validation

All destination paths validated:
1. No directory traversal (`..` not allowed)
2. No absolute paths (`/` or `C:` prefixes)
3. No null bytes or control characters
4. Final resolved path must be within project directory

**Code** (skillmeat/api/routers/deployments.py:32-66):
```python
def validate_dest_path(dest_path: Optional[str]) -> Optional[str]:
    # Check for directory traversal
    if ".." in dest_path:
        raise ValueError("Directory traversal ('..') not allowed")
    # Check for absolute path
    if dest_path.startswith("/"):
        raise ValueError("Absolute paths not allowed")
    # ... more validation
```

### Project Scope Isolation

Projects are isolated:
- Each project has independent deployment tracking
- Removing deployment from one project doesn't affect others
- Collection artifacts remain untouched

---

## Common Workflows

### Deploy a Skill to Project

```python
from skillmeat.core.deployment import DeploymentManager
from pathlib import Path

mgr = DeploymentManager()
deployments = mgr.deploy_artifacts(
    artifact_names=["skillmeat-cli"],
    collection_name="default",
    project_path=Path("/Users/me/my-project"),
    overwrite=False  # Prompt if already deployed
)

for dep in deployments:
    print(f"Deployed {dep.artifact_name} to {dep.artifact_path}")
```

### List Deployed Artifacts

```python
from skillmeat.storage.deployment import DeploymentTracker
from pathlib import Path

project_path = Path("/Users/me/my-project")
deployments = DeploymentTracker.read_deployments(project_path)

for dep in deployments:
    print(f"{dep.artifact_name}: {dep.artifact_type}")
```

### Check Modifications

```python
from skillmeat.core.sync import SyncManager
from pathlib import Path

sync_mgr = SyncManager()
drift_results = sync_mgr.check_drift(project_path=Path("/Users/me/my-project"))

for drift in drift_results:
    if drift.drift_type == "modified":
        print(f"{drift.artifact_name}: locally modified")
```

### Create Project via API

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "path": "/Users/me/projects/my-project",
    "description": "My awesome project"
  }'
```

### Deploy via API

```bash
curl -X POST http://localhost:8000/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_name": "skillmeat-cli",
    "artifact_type": "skill",
    "collection_name": "default",
    "project_path": "/Users/me/projects/my-project",
    "overwrite": false
  }'
```

---

## Related Concepts

- **Collection**: Source of artifacts (`~/.skillmeat/collection/`)
- **Artifact**: Reusable component (skill, command, agent, hook, MCP)
- **Scope**: Artifact visibility level (user or local)
- **Deployment**: Instance of artifact deployed to project
- **Drift**: Difference between deployed and current versions
- **Version**: Semantic version or git SHA of artifact

---

## Files Summary

| File | Purpose | Key Classes |
|------|---------|------------|
| `skillmeat/core/deployment.py` | Deployment logic | `Deployment`, `DeploymentManager` |
| `skillmeat/storage/deployment.py` | TOML persistence | `DeploymentTracker` |
| `skillmeat/storage/project.py` | Project metadata | `ProjectMetadata`, `ProjectMetadataStorage` |
| `skillmeat/api/routers/deployments.py` | Deployment API | Routes for deploy/undeploy |
| `skillmeat/api/routers/projects.py` | Project API | Routes for CRUD + drift detection |
| `skillmeat/api/project_registry.py` | Cached discovery | `ProjectRegistry` (singleton) |

