---
title: Core Services Documentation
last_updated: 2025-12-15
---

# Core Services

Business logic services for SkillMeat. These services are called by API routers and implement domain operations.

## Available Services

### Content Hash Service

**File**: `content_hash.py`

**Purpose**: Content hashing for change detection and integrity verification

**Key Functions**:

- `compute_content_hash()` - Compute SHA256 hash of content
- `detect_changes()` - Detect if deployed file differs from collection entity
- `read_file_with_hash()` - Read file and compute hash in one operation
- `update_artifact_hash()` - Compute hash for artifact content
- `verify_content_integrity()` - Verify content matches expected hash

**Features**:

1. **Deterministic Hashing**: Same content always produces same hash (SHA256)
2. **Change Detection**: Compare collection entities with deployed files
3. **Graceful Handling**: Returns False (no change) for missing files
4. **Unicode Support**: Handles UTF-8 content correctly
5. **Content Integrity**: Verify content hasn't been corrupted or modified

**Usage Example**:

```python
from pathlib import Path
from skillmeat.core.services import (
    compute_content_hash,
    detect_changes,
    read_file_with_hash,
)

# Compute hash for collection entity content
collection_content = "# My Skill\n\nSkill content here."
collection_hash = compute_content_hash(collection_content)

# Store hash with artifact (in database)
artifact.content_hash = collection_hash

# Later: Detect if deployed file has been locally modified
deployed_file = Path(".claude/skills/user/my-skill/SKILL.md")
has_changes = detect_changes(collection_hash, deployed_file)

if has_changes:
    print("Local modifications detected!")
    # Read modified content
    modified_content, new_hash = read_file_with_hash(deployed_file)
    print(f"New hash: {new_hash}")
else:
    print("Deployed file matches collection")
```

**Hash Properties**:

- Algorithm: SHA256 (cryptographically secure)
- Output: 64-character hex string
- Deterministic: Same input = same output
- Collision-resistant: Different inputs produce different outputs

**Change Detection Behavior**:

- File doesn't exist → Returns `False` (not a change)
- File exists, matches collection → Returns `False` (no change)
- File exists, differs from collection → Returns `True` (change detected)
- File is directory/unreadable → Returns `False` (safer default)

**Test Coverage**: 100% (30 tests)

### Context Sync Service

**File**: `context_sync.py`

**Purpose**: Bi-directional synchronization of context entities between collections and deployed projects

**Key Features**:

1. **Change Detection**: Detect modified entities in project or collection
2. **Pull Changes**: Update collection from project (capture manual edits)
3. **Push Changes**: Deploy collection updates to project
4. **Conflict Detection**: Identify when both sides modified
5. **Conflict Resolution**: Keep local/remote/merge strategies

**Key Classes**:

- `ContextSyncService` - Main service class
- `SyncConflict` - Represents a sync conflict
- `SyncResult` - Result of sync operation

**Methods**:

```python
class ContextSyncService:
    def detect_modified_entities(self, project_path: str) -> List[Dict[str, Any]]:
        """Scan project for modified context entities."""

    def pull_changes(
        self, project_path: str, entity_ids: Optional[List[str]] = None
    ) -> List[SyncResult]:
        """Pull changes from project to collection."""

    def push_changes(
        self,
        project_path: str,
        entity_ids: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> List[SyncResult]:
        """Push collection changes to project."""

    def detect_conflicts(self, project_path: str) -> List[SyncConflict]:
        """Detect entities modified in both collection and project."""

    def resolve_conflict(
        self,
        conflict: SyncConflict,
        resolution: Literal["keep_local", "keep_remote", "merge"],
        merged_content: Optional[str] = None,
    ) -> SyncResult:
        """Resolve sync conflict based on user choice."""
```

**Usage Example**:

```python
from skillmeat.core.services import ContextSyncService
from skillmeat.core.collection import CollectionManager
from skillmeat.cache.manager import CacheManager

# Initialize service
collection_mgr = CollectionManager()
cache_mgr = CacheManager()
sync_service = ContextSyncService(collection_mgr, cache_mgr)

# Detect modified entities
modified = sync_service.detect_modified_entities("/path/to/project")
for entity in modified:
    print(f"{entity['entity_name']}: modified in {entity['modified_in']}")

# Pull changes from project
results = sync_service.pull_changes("/path/to/project")
for result in results:
    print(f"{result.action}: {result.entity_name} - {result.message}")

# Detect and resolve conflicts
conflicts = sync_service.detect_conflicts("/path/to/project")
for conflict in conflicts:
    # User chooses resolution strategy
    result = sync_service.resolve_conflict(conflict, "keep_local")
    print(f"Resolved: {result.message}")
```

**Modification Detection**:

- `"none"` - No changes since last sync
- `"project"` - Deployed file modified (pull available)
- `"collection"` - Collection entity modified (push available)
- `"both"` - Both modified (conflict)

**Conflict Resolution Strategies**:

- `"keep_local"` - Update collection from project (project wins)
- `"keep_remote"` - Update project from collection (collection wins)
- `"merge"` - Use provided merged content for both (manual merge)

**Security**:

- All file operations stay within `.claude/` directory
- Content integrity verified via SHA-256 hashes
- Atomic writes using temp files (future)

**Current Status**:

- ✅ Core sync logic implemented
- ✅ Change detection via content hashing
- ⚠️ Database integration pending (uses TODOs for cache operations)
- ⚠️ Full pull/push pending cache manager integration
- ✅ 19 unit tests (100% pass rate)

**TODO**:

- [ ] Integrate with CacheManager to read/write context entities
- [ ] Implement actual content updates (currently logged only)
- [ ] Update deployment records with new hashes after sync
- [ ] Add API endpoints for sync operations
- [ ] Add CLI commands for sync operations

**Test Coverage**: 19 tests (all passing)

### Template Service

**File**: `template_service.py`

**Purpose**: Secure template deployment with variable substitution

**Key Functions**:

- `deploy_template()` - Deploy project template to directory
- `validate_variables()` - Validate variable values against whitelist
- `render_content()` - Simple string-based variable substitution
- `resolve_file_path()` - Secure path resolution with traversal prevention

**Security Features**:

1. **Simple Variable Substitution**: Uses `str.replace()` only - no `eval()` or `exec()`
2. **Variable Whitelist**: Only approved variables allowed:
   - `{{PROJECT_NAME}}` (required)
   - `{{PROJECT_DESCRIPTION}}` (optional)
   - `{{AUTHOR}}` (optional)
   - `{{DATE}}` (optional, defaults to current date)
   - `{{ARCHITECTURE_DESCRIPTION}}` (optional)
3. **Path Traversal Prevention**: Rejects paths containing `..`
4. **Path Validation**: Verifies resolved paths stay within project directory
5. **Atomic Deployment**: All-or-nothing deployment using temp directory

**Usage Example**:

```python
from sqlalchemy.orm import Session
from skillmeat.core.services import deploy_template

# Deploy template with variables
result = deploy_template(
    session=session,
    template_id="tpl_abc123",
    project_path="/path/to/project",
    variables={
        "PROJECT_NAME": "my-awesome-project",
        "PROJECT_DESCRIPTION": "Full-stack web application",
        "AUTHOR": "John Doe",
    },
    selected_entity_ids=None,  # Deploy all entities
    overwrite=False,  # Don't overwrite existing files
)

if result.success:
    print(f"Deployed {len(result.deployed_files)} files")
    print(f"Skipped {len(result.skipped_files)} existing files")
else:
    print(f"Deployment failed: {result.message}")
```

**DeploymentResult Schema**:

```python
@dataclass
class DeploymentResult:
    success: bool                # True if deployment completed
    project_path: str            # Target project path
    deployed_files: list[str]    # List of deployed file paths (relative)
    skipped_files: list[str]     # List of skipped file paths (relative)
    message: str                 # Human-readable status message
```

**Error Handling**:

- `ValueError`: Invalid template ID, variables, or paths
- `PermissionError`: Cannot write to project directory
- `FileExistsError`: File exists and `overwrite=False`

**Atomic Deployment Process**:

1. Create temporary directory
2. Render all entities to temp directory with variable substitution
3. On success: Move all files to project directory atomically
4. On failure: Cleanup temp directory, return error
5. No partial deployments - all files succeed or none

**TODO**:

- [ ] Implement `_fetch_artifact_content()` to integrate with ArtifactManager
- [ ] Add support for reading artifact content from collection storage
- [ ] Add support for marketplace artifact content
- [ ] Add unit tests for service functions
- [ ] Add integration tests for full deployment flow

## Service Pattern

All services should follow these patterns:

### Structure

```python
"""Service description and purpose."""

from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

@dataclass
class ServiceResult:
    """Result of service operation."""
    success: bool
    message: str
    # ... other fields

def service_operation(
    session: Session,
    arg1: str,
    arg2: Optional[str] = None,
) -> ServiceResult:
    """Service operation description.

    Args:
        session: Database session
        arg1: First argument
        arg2: Optional argument

    Returns:
        ServiceResult with operation outcome

    Raises:
        ValueError: Invalid input
        PermissionError: Permission denied
    """
    # Implementation
```

### Error Handling

Services should:

1. **Validate inputs early** - raise `ValueError` for invalid inputs
2. **Use specific exceptions** - `ValueError`, `PermissionError`, `FileExistsError`, etc.
3. **Return result objects** - Use dataclasses for structured results
4. **Log errors** - Use logging for debugging (future)

### Security Guidelines

1. **NO eval/exec** - Ever. Use simple string operations.
2. **Validate all inputs** - Whitelist patterns, reject unknown
3. **Path validation** - Prevent traversal attacks (`..`)
4. **Atomic operations** - Use temp directories for multi-step operations
5. **Permission checks** - Verify write permissions before operations

### Testing

Each service should have:

1. **Unit tests** - Test individual functions in isolation
2. **Integration tests** - Test service with database
3. **Security tests** - Verify path traversal prevention, variable whitelist
4. **Error tests** - Verify proper error handling

**Test Location**: `skillmeat/core/tests/test_services/`

## Integration with API

Services are called by API routers via dependency injection:

```python
# In router
from skillmeat.core.services import deploy_template
from skillmeat.api.dependencies import DbSessionDep

@router.post("/templates/{template_id}/deploy")
async def deploy_template_endpoint(
    template_id: str,
    request: DeployTemplateRequest,
    session: DbSessionDep,
) -> DeployTemplateResponse:
    # Call service
    result = deploy_template(
        session=session,
        template_id=template_id,
        project_path=request.project_path,
        variables=request.variables.model_dump(),
        selected_entity_ids=request.selected_entity_ids,
        overwrite=request.overwrite,
    )

    # Convert to API response
    return DeployTemplateResponse(
        success=result.success,
        project_path=result.project_path,
        deployed_files=result.deployed_files,
        skipped_files=result.skipped_files,
        message=result.message,
    )
```

## Related Documentation

- **API Layer**: `skillmeat/api/CLAUDE.md`
- **Router Patterns**: `.claude/rules/api/routers.md`
- **Database Models**: `skillmeat/cache/models.py`
- **Template Schemas**: `skillmeat/api/schemas/project_template.py`
