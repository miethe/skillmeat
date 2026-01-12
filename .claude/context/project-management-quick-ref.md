---
title: Project Management Quick Reference
description: Fast lookup for project-related code patterns and APIs
references:
  - skillmeat/core/deployment.py
  - skillmeat/storage/deployment.py
  - skillmeat/api/routers/projects.py
last_verified: 2026-01-11
---

# Project Management Quick Reference

## File Locations

| What | Where |
|------|-------|
| Deployment metadata | `{project}/.claude/.skillmeat-deployed.toml` |
| Project metadata | `{project}/.claude/.skillmeat-project.toml` |
| Deployment code | `skillmeat/core/deployment.py` |
| Storage code | `skillmeat/storage/deployment.py` |
| Project storage | `skillmeat/storage/project.py` |
| API endpoints | `skillmeat/api/routers/deployments.py`, `projects.py` |
| Registry | `skillmeat/api/project_registry.py` |

## Key Classes

### Deployment Model
```python
from skillmeat.core.deployment import Deployment

# Create from dict (TOML)
dep = Deployment.from_dict({
    "artifact_name": "my-skill",
    "artifact_type": "skill",
    "from_collection": "default",
    "deployed_at": "2026-01-10T14:00:00",
    "artifact_path": "skills/my-skill",
    "content_hash": "abc123...",
})

# Convert to dict (for TOML)
data = dep.to_dict()
```

### DeploymentTracker
```python
from skillmeat.storage.deployment import DeploymentTracker
from pathlib import Path

project_path = Path("/path/to/project")

# Read all deployments
deployments = DeploymentTracker.read_deployments(project_path)

# Get one deployment
dep = DeploymentTracker.get_deployment(
    project_path,
    artifact_name="my-skill",
    artifact_type="skill"
)

# Record deployment
DeploymentTracker.record_deployment(
    project_path,
    artifact,
    collection_name="default",
    collection_sha="abc123..."
)

# Remove deployment
DeploymentTracker.remove_deployment(
    project_path,
    artifact_name="my-skill",
    artifact_type="skill"
)

# Detect modifications
is_modified = DeploymentTracker.detect_modifications(
    project_path,
    artifact_name="my-skill",
    artifact_type="skill"
)
```

### DeploymentManager
```python
from skillmeat.core.deployment import DeploymentManager

mgr = DeploymentManager()

# Deploy artifact(s)
deployments = mgr.deploy_artifacts(
    artifact_names=["skill1", "skill2"],
    collection_name="default",
    project_path=Path("/path/to/project"),
    artifact_type=None,  # Optional filter
    overwrite=False,
    dest_path=None  # Optional custom path
)

# Deploy all artifacts from collection
deployments = mgr.deploy_all(
    collection_name="default",
    project_path=Path("/path/to/project")
)

# Undeploy artifact
mgr.undeploy(
    artifact_name="my-skill",
    artifact_type=ArtifactType.SKILL,
    project_path=Path("/path/to/project")
)

# List deployments
deployments = mgr.list_deployments(project_path=Path("/path/to/project"))

# Check sync status
status = mgr.check_deployment_status(project_path=Path("/path/to/project"))
# Returns: {"skill1::skill": "synced", "agent1::agent": "modified"}
```

### ProjectMetadata
```python
from skillmeat.storage.project import ProjectMetadata, ProjectMetadataStorage
from pathlib import Path

project_path = Path("/path/to/project")

# Create metadata
metadata = ProjectMetadataStorage.create_metadata(
    project_path=project_path,
    name="my-project",
    description="Optional description"
)

# Read metadata
metadata = ProjectMetadataStorage.read_metadata(project_path)

# Update metadata
metadata = ProjectMetadataStorage.update_metadata(
    project_path=project_path,
    name="new-name",
    description="new description"
)

# Check if exists
exists = ProjectMetadataStorage.exists(project_path)

# Delete metadata
deleted = ProjectMetadataStorage.delete_metadata(project_path)
```

### ProjectRegistry
```python
from skillmeat.api.project_registry import ProjectRegistry

# Get singleton instance
registry = await ProjectRegistry.get_instance()

# Configure (optional)
registry.configure(
    cache_ttl=300,  # 5 minutes
    entry_ttl=60,
    search_paths=[Path("/Users/me/projects")],
    max_depth=3
)

# Get projects (with caching)
projects = await registry.get_projects(force_refresh=False)

# Refresh single entry
await registry.refresh_entry(Path("/path/to/project"))

# Invalidate entry
await registry.invalidate(Path("/path/to/project"))

# Get cache stats
stats = registry.get_cache_stats()
```

## API Endpoints

### Deployment Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/deploy` | Deploy artifact |
| POST | `/api/v1/deploy/undeploy` | Remove artifact |
| GET | `/api/v1/deploy` | List deployments |

### Project Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/projects` | List all projects |
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects/{id}` | Get project details |
| PUT | `/api/v1/projects/{id}` | Update project |
| DELETE | `/api/v1/projects/{id}` | Delete project |
| DELETE | `/api/v1/projects/{id}/deployments/{name}` | Remove deployment |
| POST | `/api/v1/projects/{id}/check-modifications` | Check modifications |
| GET | `/api/v1/projects/{id}/modified-artifacts` | Get modified artifacts |
| GET | `/api/v1/projects/{id}/drift/summary` | Get drift summary |
| GET | `/api/v1/projects/{id}/context-map` | Discover context entities |

## Artifact Destination Paths

```python
# Default paths based on artifact type:
artifact_type = "skill"    → .claude/skills/{name}/
artifact_type = "command"  → .claude/commands/{name}.md
artifact_type = "agent"    → .claude/agents/{name}.md
artifact_type = "mcp"      → .claude/mcp/{name}/
artifact_type = "hook"     → .claude/hooks/{name}.md

# Custom path
dest_path = ".claude/custom/path/"
# Result: .claude/custom/path/{artifact_name}/ or .claude/custom/path/{artifact_name}.md
```

## Deployment Record Fields

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| artifact_name | str | "skillmeat-cli" | Name in collection |
| artifact_type | str | "skill" | skill, command, agent, mcp, hook |
| from_collection | str | "default" | Source collection name |
| deployed_at | datetime | 2026-01-10T14:00:00 | ISO format |
| artifact_path | Path | "skills/skillmeat-cli" | Relative to .claude/ |
| content_hash | str | "abc123de..." | SHA-256 of content |
| local_modifications | bool | false | True if file differs from deployment |
| version_lineage | List[str] | ["abc123..."] | Hash history (newest first) |
| merge_base_snapshot | str | "abc123..." | For 3-way merge baseline |

## Common Patterns

### Deploy Single Artifact
```python
from skillmeat.core.deployment import DeploymentManager
from skillmeat.core.artifact import ArtifactType
from pathlib import Path

mgr = DeploymentManager()
deployments = mgr.deploy_artifacts(
    artifact_names=["my-skill"],
    collection_name="default",
    project_path=Path.cwd(),
    overwrite=True
)
```

### Detect Modifications
```python
from skillmeat.storage.deployment import DeploymentTracker
from pathlib import Path

project_path = Path.cwd()
deployments = DeploymentTracker.read_deployments(project_path)

for dep in deployments:
    is_modified = DeploymentTracker.detect_modifications(
        project_path,
        dep.artifact_name,
        dep.artifact_type
    )
    if is_modified:
        print(f"{dep.artifact_name}: modified")
```

### List All Projects
```python
from skillmeat.api.project_registry import ProjectRegistry

registry = await ProjectRegistry.get_instance()
projects = await registry.get_projects(force_refresh=False)

for proj in projects:
    print(f"{proj.name}: {proj.path}")
    print(f"  Deployments: {proj.deployment_count}")
    print(f"  Last: {proj.last_deployment}")
```

### API: Deploy via cURL
```bash
curl -X POST http://localhost:8000/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_name": "my-skill",
    "artifact_type": "skill",
    "collection_name": "default",
    "project_path": "/path/to/project",
    "overwrite": true
  }'
```

### API: List Projects
```bash
curl "http://localhost:8000/api/v1/projects?limit=10&refresh=false"
```

## Error Codes

| Code | Meaning | Common Causes |
|------|---------|--------------|
| 400 | Bad Request | Invalid artifact type, path traversal, absolute path in dest_path |
| 404 | Not Found | Artifact not in collection, project not found, deployment not found |
| 409 | Conflict | Artifact already deployed (use `overwrite=true`) |
| 500 | Internal Error | Deployment failed, I/O error, sync error |

## Performance Tips

1. **Cache projects**: Use `ProjectRegistry` for <50ms responses
2. **Batch operations**: Deploy multiple artifacts in one call
3. **Skip re-checks**: Don't repeatedly call `detect_modifications()` on stable projects
4. **Force refresh carefully**: Only use `force_refresh=true` when needed (expensive)
5. **Pagination**: Use `limit` and `after` cursor for large project lists

## Debugging

### Find Deployment File
```bash
find /path/to/project -name ".skillmeat-deployed.toml"
```

### View Deployments (TOML)
```bash
cat /path/to/project/.claude/.skillmeat-deployed.toml
```

### Check Project Metadata
```bash
cat /path/to/project/.claude/.skillmeat-project.toml
```

### Trace Deployment Issue
1. Check `.skillmeat-deployed.toml` exists
2. Verify artifact in collection: `skillmeat list`
3. Check collection is loaded: `skillmeat config get active-collection`
4. Verify permissions: Can write to project directory?
5. Check path validation (no `..`, no `/`, no null bytes)

