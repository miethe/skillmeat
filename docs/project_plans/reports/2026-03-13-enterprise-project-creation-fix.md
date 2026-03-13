# Enterprise Project Creation: Permission Denied Fix

**Date**: 2026-03-13
**Severity**: High (blocks demo)
**Commit**: `946445ca fix(api): skip filesystem ops in enterprise project creation`
**Status**: Hotfix applied, long-term redesign needed

---

## Problem

When creating a Project via the SkillMeat web UI running in **Enterprise mode** (Docker Compose with `--profile enterprise`), the API returns a **400 Bad Request** with:

```
Permission denied: '/home/miethe'
```

The user submits a `POST /api/v1/projects` with a path like `/home/miethe/projects/demo`. The API container (`skillmeat-api`) attempts to create that directory on the filesystem, but the container's filesystem is isolated -- only `/home/app/.skillmeat` is volume-mounted. The host path `/home/miethe` does not exist inside the container.

## Root Cause

The `create_project` handler in `skillmeat/api/routers/projects.py` unconditionally performs filesystem operations regardless of edition:

```python
# Line 708 -- fails with PermissionError inside container
project_path.mkdir(parents=True, exist_ok=True)

# Line 720 -- also fails
claude_dir.mkdir(parents=True, exist_ok=True)
```

These operations are appropriate in **local mode** (single-user, filesystem is source of truth) but invalid in **enterprise mode** (multi-tenant, PostgreSQL is source of truth).

The `filesystem_error_handler.py` middleware catches these errors and converts them to 503 in enterprise mode, but the handler itself raises a 400 before the middleware can intercept.

## Hotfix Applied

The fix gates all filesystem operations behind an `is_enterprise` check, following the same pattern used in 20+ other locations across the codebase (`settings.edition == "enterprise"`).

### Changes

**File**: `skillmeat/api/routers/projects.py`

| Operation | Local Mode | Enterprise Mode |
|-----------|------------|-----------------|
| `ProjectMetadataStorage.exists()` check | Runs | Skipped |
| `project_path.mkdir()` | Runs | Skipped |
| `.claude/` subdirectory creation | Runs | Skipped |
| `ProjectMetadataStorage.create_metadata()` | Runs | Skipped |
| `DeploymentTracker.write_deployments()` | Runs | Skipped |
| `project_repo.create(new_dto)` | Runs | **Runs** |
| `cache_manager.upsert_project()` | Runs | **Runs** |
| `registry.refresh_entry()` | Runs | Skipped |

In enterprise mode, `metadata_created_at` is set to `datetime.utcnow().isoformat()` instead of being read from the filesystem metadata file.

### Patch

```diff
diff --git a/skillmeat/api/routers/projects.py b/skillmeat/api/routers/projects.py
index 1cea536d..5e21b121 100644
--- a/skillmeat/api/routers/projects.py
+++ b/skillmeat/api/routers/projects.py
@@ -14,6 +14,7 @@ from typing import Annotated, List, Optional
 from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
 from sqlalchemy.orm import Session

+from skillmeat.api.config import get_settings
 from skillmeat.api.dependencies import (
     DbSessionDep,
     DeploymentProfileRepoDep,
@@ -683,6 +684,9 @@ async def create_project(
     try:
         logger.info(f"Creating project: {request.name} at {request.path}")

+        settings = get_settings()
+        is_enterprise = settings.edition == "enterprise"
+
         # Resolve path
         # TODO: IProjectRepository.create() should handle path resolution internally.
         project_path = Path(request.path).resolve()
@@ -695,50 +699,65 @@ async def create_project(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail=f"Project already exists at path: {request.path}",
             )
-        # Also check filesystem metadata in case the project exists but is unregistered
-        if ProjectMetadataStorage.exists(project_path):
-            raise HTTPException(
-                status_code=status.HTTP_400_BAD_REQUEST,
-                detail=f"Project already exists at path: {request.path}",
-            )

-        # Create project directory if it doesn't exist
-        # TODO: Directory creation should move into IProjectRepository.create() impl.
-        try:
-            project_path.mkdir(parents=True, exist_ok=True)
-            logger.info(f"Created project directory: {project_path}")
-        except Exception as e:
-            raise HTTPException(
-                status_code=status.HTTP_400_BAD_REQUEST,
-                detail=f"Failed to create project directory: {str(e)}",
+        if is_enterprise:
+            # Enterprise mode: DB is source of truth -- skip all filesystem operations
+            logger.info(
+                f"Enterprise mode: creating DB-only project {request.name}, "
+                "skipping filesystem operations"
             )
+            metadata_created_at = datetime.utcnow().isoformat()
+        else:
+            # Also check filesystem metadata in case the project exists but is unregistered
+            if ProjectMetadataStorage.exists(project_path):
+                raise HTTPException(
+                    status_code=status.HTTP_400_BAD_REQUEST,
+                    detail=f"Project already exists at path: {request.path}",
+                )

-        # Create .claude subdirectory
-        # TODO: .claude directory scaffolding should move into IProjectRepository.create() impl.
-        claude_dir = project_path / ".claude"
-        try:
-            claude_dir.mkdir(parents=True, exist_ok=True)
-            logger.info(f"Created .claude directory: {claude_dir}")
-        except Exception as e:
-            raise HTTPException(
-                status_code=status.HTTP_400_BAD_REQUEST,
-                detail=f"Failed to create .claude directory: {str(e)}",
+            # Create project directory if it doesn't exist
+            try:
+                project_path.mkdir(parents=True, exist_ok=True)
+                logger.info(f"Created project directory: {project_path}")
+            except Exception as e:
+                raise HTTPException(
+                    status_code=status.HTTP_400_BAD_REQUEST,
+                    detail=f"Failed to create project directory: {str(e)}",
+                )
+
+            # Create .claude subdirectory
+            claude_dir = project_path / ".claude"
+            try:
+                claude_dir.mkdir(parents=True, exist_ok=True)
+                logger.info(f"Created .claude directory: {claude_dir}")
+            except Exception as e:
+                raise HTTPException(
+                    status_code=status.HTTP_400_BAD_REQUEST,
+                    detail=f"Failed to create .claude directory: {str(e)}",
+                )
+
+            # Create project metadata on filesystem
+            metadata = ProjectMetadataStorage.create_metadata(
+                project_path=project_path,
+                name=request.name,
+                description=request.description,
             )

-        # Create project metadata on filesystem
-        metadata = ProjectMetadataStorage.create_metadata(...)
-        from skillmeat.storage.deployment import DeploymentTracker
-        DeploymentTracker.write_deployments(project_path, [])
+            from skillmeat.storage.deployment import DeploymentTracker
+            DeploymentTracker.write_deployments(project_path, [])
+
+            metadata_created_at = (
+                metadata.created_at.isoformat()
+                if hasattr(metadata.created_at, "isoformat")
+                else str(metadata.created_at) if metadata.created_at else None
+            )

-        # Register project via repository
+        # Register project via repository (always runs -- DB is always updated)
         new_dto = ProjectDTO(
             id=project_id,
             name=request.name,
             path=str(project_path),
             description=request.description,
             status="active",
             artifact_count=0,
-            created_at=( ... metadata.created_at ... ),
+            created_at=metadata_created_at,
         )
         try:
             project_repo.create(new_dto)
@@ ...
-        registry = await get_project_registry()
-        await registry.refresh_entry(project_path)
+        if not is_enterprise:
+            registry = await get_project_registry()
+            await registry.refresh_entry(project_path)

         # cache_manager.upsert_project() -- always runs (unchanged)

+        created_at_value = (
+            datetime.fromisoformat(metadata_created_at)
+            if isinstance(metadata_created_at, str)
+            else metadata_created_at
+        )
         return ProjectCreateResponse(
             id=project_id,
             path=str(project_path),
-            name=metadata.name,
-            description=metadata.description,
-            created_at=metadata.created_at,
+            name=request.name,
+            description=request.description,
+            created_at=created_at_value,
         )
```

---

## Affected Endpoints Audit

The project creation fix resolves the immediate blocker, but other project-related endpoints may also attempt filesystem access in enterprise mode. These should be audited:

| Endpoint | File:Line | Filesystem Access | Risk |
|----------|-----------|-------------------|------|
| `POST /projects` | projects.py:622 | `mkdir`, metadata write | **Fixed** |
| `GET /projects/{id}` | projects.py:826 | `ProjectMetadataStorage.load()` | Medium -- may fail if path doesn't exist on disk |
| `DELETE /projects/{id}` | projects.py (if exists) | `shutil.rmtree` or similar | Medium |
| `POST /projects/{id}/deploy` | deployments.py | Writes to project path | High -- core deployment flow |
| `GET /projects/{id}/deployments` | deployments.py | Reads deployment tracker | Medium |
| Context entity CRUD | context_entities.py | Reads/writes `.claude/` files | High |

---

## Long-Term Recommendations

### 1. Enterprise Project Model Redesign

The current project model is fundamentally filesystem-oriented: a project **is** a directory on disk. Enterprise mode needs a different mental model where a project is a **logical entity** in the database that may or may not correspond to a real directory.

**Proposal**: Introduce a `ProjectType` enum:

```python
class ProjectType(str, Enum):
    LOCAL = "local"       # Filesystem-backed, current behavior
    VIRTUAL = "virtual"   # DB-only, no filesystem backing
    REMOTE = "remote"     # Future: references a remote git repo
```

Enterprise projects would default to `virtual`. The project path field becomes optional or informational (a label for the user's reference, not a real path the server accesses).

### 2. Enterprise Deployment Architecture

Deploying artifacts to a project is the core value proposition. In local mode, "deploy" means copying files to the project's `.claude/` directory. In enterprise mode, this needs a fundamentally different approach:

**Option A: Virtual Deployments (DB-only)**
- Deployments are tracked as DB records linking artifacts to projects
- No files are written anywhere -- the deployment is a logical association
- Frontend shows deployed artifacts per project; users download/install manually
- Simplest to implement, but limits the "push to project" experience

**Option B: Git-Based Deployments**
- Enterprise projects reference a git repository (GitHub, GitLab, etc.)
- "Deploy" creates a PR or commit adding the artifact to the repo's `.claude/` directory
- Requires GitHub App / OAuth integration per tenant
- Most powerful but highest implementation complexity

**Option C: Object Storage Deployments**
- Each tenant gets an S3/GCS bucket (or shared bucket with tenant prefix)
- "Deploy" writes artifact files to the tenant's storage
- Users sync from storage to their local projects via CLI
- Good middle ground between A and B

**Recommendation**: Start with **Option A** for the demo and near-term. Plan **Option B** for the production enterprise product. Option C is a useful intermediate if Option B timelines are too long.

### 3. IProjectRepository.create() Refactor

The existing TODOs in the codebase already call this out:

```python
# TODO: IProjectRepository.create() should handle path resolution internally.
# TODO: Directory creation should move into IProjectRepository.create() impl.
# TODO: .claude directory scaffolding should move into IProjectRepository.create() impl.
# TODO: ProjectMetadataStorage write should move into IProjectRepository.create() impl.
```

The router currently contains 6 distinct steps that should be encapsulated inside the repository implementation:

1. Path resolution
2. Existence check (filesystem)
3. Directory creation
4. Metadata storage
5. Deployment tracker initialization
6. Cache sync

Moving these into `IProjectRepository.create()` implementations means:
- `LocalProjectRepository.create()` performs all filesystem operations
- `EnterpriseProjectRepository.create()` performs only DB operations
- The router becomes a thin HTTP adapter with no edition-awareness

This is the cleanest long-term architecture and aligns with the hexagonal architecture already in use for other repositories.

### 4. Path Validation for Enterprise Mode

Enterprise mode should validate that submitted paths make sense:

- Reject paths that are clearly host-local (`/home/username/...`, `C:\Users\...`)
- Suggest or auto-generate logical project identifiers instead
- Consider removing the `path` field entirely from the enterprise `ProjectCreateRequest` schema and auto-generating an ID

### 5. Frontend Awareness

The project creation UI should adapt based on edition:

- **Local mode**: Show a file path picker or text input for the absolute path
- **Enterprise mode**: Show only name/description fields; path is either auto-generated or hidden

### 6. Comprehensive Enterprise Filesystem Audit

Beyond project creation, a systematic audit should identify every endpoint that touches the filesystem. The `filesystem_error_handler.py` middleware catches unhandled errors, but the proper fix is to prevent filesystem calls in enterprise mode at the source.

Candidates for audit:
- All routers in `skillmeat/api/routers/` that use `Path()`, `os.path`, `open()`, `mkdir()`, `shutil`
- All references to `ProjectMetadataStorage`, `DeploymentTracker`, `SnapshotManager`
- All imports from `skillmeat.storage.*`

A `grep -rn "Path\|os\.path\|\.mkdir\|open(" skillmeat/api/routers/` would produce the initial hit list.

---

## Verification Steps (Post-Deploy)

1. Rebuild the enterprise compose stack:
   ```bash
   docker compose --profile enterprise down
   docker compose --profile enterprise up --build -d
   ```

2. Create a project via API:
   ```bash
   curl -s http://localhost:8080/api/v1/projects \
     -X POST -H "Content-Type: application/json" \
     -d '{"name": "demo-project", "path": "/demo/projects/test", "description": "Demo project"}' \
     | jq .
   ```

3. Verify project appears in list:
   ```bash
   curl -s http://localhost:8080/api/v1/projects | jq '.items[].name'
   ```

4. Check logs for enterprise mode message:
   ```bash
   docker compose logs skillmeat-api | grep "Enterprise mode: creating DB-only"
   ```
