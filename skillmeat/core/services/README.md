---
title: Core Services Documentation
last_updated: 2025-12-15
---

# Core Services

Business logic services for SkillMeat. These services are called by API routers and implement domain operations.

## Available Services

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
