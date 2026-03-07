---
title: Developer Auth Patterns Guide
description: Comprehensive guide for implementing authentication and authorization in SkillMeat API endpoints
audience: developers
tags: [auth, rbac, api, security, patterns]
created: 2026-03-07
updated: 2026-03-07
category: development
status: published
related:
  - docs/api/authentication.md
  - skillmeat/api/CLAUDE.md
  - skillmeat/cache/auth_types.py
---

# Developer Auth Patterns Guide

This guide teaches you how to implement authentication and authorization in SkillMeat API endpoints. By following these patterns, you'll ensure consistent security practices across the codebase.

## Quick Start: Add Auth to a New Endpoint

Here's the fastest path to an authenticated endpoint:

```python
from fastapi import APIRouter, HTTPException, status
from skillmeat.api.dependencies import require_auth, AuthContextDep
from skillmeat.api.schemas.auth import AuthContext, Scope

router = APIRouter(prefix="/api/v1/my-resource", tags=["my-resource"])

@router.get("/items")
async def list_items(auth: AuthContextDep) -> dict:
    """List items for the authenticated user."""
    # auth is the AuthContext for the current request
    user_id = auth.user_id
    return {"items": [], "owner": str(user_id)}

@router.post("/items")
async def create_item(
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value]))
) -> dict:
    """Create a new item (requires artifact:write scope)."""
    return {"created": True, "owner": str(auth.user_id)}
```

## Core Concepts

### AuthContext: Your Request's Authentication State

`AuthContext` is an immutable dataclass that contains all authentication information for a request. It's constructed once per request and passed through your handler chain.

```python
from skillmeat.api.schemas.auth import AuthContext
import uuid

# Structure of AuthContext
auth = AuthContext(
    user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    tenant_id=uuid.UUID("660e8400-e29b-41d4-a716-446655440001"),  # None in local mode
    roles=["team_member"],  # Role strings carried by the user
    scopes=["artifact:read", "collection:read"],  # Fine-grained permission scopes
)
```

**Key properties:**

| Property | Type | Purpose |
|----------|------|---------|
| `user_id` | `uuid.UUID` | Identifier of the authenticated user |
| `tenant_id` | `uuid.UUID \| None` | Tenant ID (None in local/single-tenant mode) |
| `roles` | `list[str]` | Role assignments (e.g., `system_admin`, `team_member`) |
| `scopes` | `list[str]` | Permission scopes (e.g., `artifact:read`, `artifact:write`) |

**Helper methods:**

```python
# Check if user has a specific role
if auth.has_role(Role.system_admin):
    # User is a system administrator
    pass

# Check for a permission scope
if auth.has_scope(Scope.artifact_write):
    # User can write artifacts
    pass

# Check for ANY of multiple scopes
if auth.has_any_scope(Scope.artifact_read, Scope.artifact_write):
    # User can at least read or write artifacts
    pass

# Check if user is an admin
if auth.is_admin():
    # User has system_admin role
    pass
```

### Roles vs. Scopes

SkillMeat distinguishes between **roles** and **scopes**:

**Roles** — High-level positions that grant broad permissions:
- `system_admin`: Full access across the tenant
- `team_admin`: Administrative access within a specific team
- `team_member`: Standard team member access
- `viewer`: Read-only access (default for new users)

**Scopes** — Fine-grained permission tokens using `resource:action` naming:
- `artifact:read`: Read artifact metadata and content
- `artifact:write`: Create, update, and delete artifacts
- `collection:read`: Read collection metadata
- `collection:write`: Create, update, and delete collections
- `deployment:read`: Read deployment records
- `deployment:write`: Create and remove deployments
- `admin:*`: Wildcard scope granting all admin operations

Use scopes to gate specific endpoint capabilities; use roles for broad access patterns.

### The Propagation Chain

Auth flows through your code in this order:

```
1. Client sends HTTP request with Authorization header
   ↓
2. AuthProvider validates the token (LocalAuthProvider or ClerkAuthProvider)
   ↓
3. require_auth dependency receives the AuthContext from provider
   ↓
4. require_auth checks scopes (if specified) and raises 403 if missing
   ↓
5. Router handler receives the authenticated AuthContext as a parameter
   ↓
6. Service/repository layer receives user_id or full AuthContext
   ↓
7. Database operations are scoped to the user/tenant
```

AuthContext is immutable and frozen after construction, preventing accidental modifications.

## How to Add Auth to an Endpoint

### Step 1: Import Dependencies

```python
from fastapi import APIRouter, HTTPException, status, Depends
from skillmeat.api.dependencies import require_auth, AuthContextDep
from skillmeat.api.schemas.auth import AuthContext, Scope
```

### Step 2: Declare Auth Requirement

**Option A: Require authentication only (no scope check)**

Use the `AuthContextDep` type alias for cleaner code:

```python
@router.get("/items")
async def list_items(auth: AuthContextDep) -> dict:
    """List items for the authenticated user."""
    user_id = str(auth.user_id)
    # ... your handler logic
    return {"items": [...]}
```

**Option B: Require authentication + specific scopes**

Use `require_auth(scopes=[...])` for scope validation:

```python
@router.post("/items")
async def create_item(
    request_data: ItemCreate,
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value]))
) -> dict:
    """Create a new item.

    Raises:
        HTTPException 403: If user lacks artifact:write scope.
    """
    user_id = str(auth.user_id)
    # ... your handler logic
    return {"created": True, "id": "..."}
```

**Option C: Multiple scopes (user must have ALL)**

```python
@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    auth: AuthContext = Depends(require_auth(scopes=[
        Scope.artifact_write.value,
        Scope.collection_write.value,
    ]))
) -> dict:
    """Delete an item (requires both artifact:write AND collection:write)."""
    # ... your handler logic
```

### Step 3: Implement Authorization Logic

In your handler, use `auth` to enforce business rules:

```python
@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    auth: AuthContextDep,
    artifact_repo: ArtifactRepoDep,
) -> ItemResponse:
    """Get item by ID with owner-only access.

    Raises:
        HTTPException 404: If item not found.
        HTTPException 403: If user does not own the item.
    """
    # Fetch the item from repository
    item = await artifact_repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check owner-only access
    if str(item.owner_id) != str(auth.user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return ItemResponse(**item.dict())
```

## Common Patterns

### Pattern 1: Owner-Only Access

Restrict an operation to the resource owner:

```python
@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    request: ItemUpdate,
    auth: AuthContextDep,
    artifact_repo: ArtifactRepoDep,
) -> ItemResponse:
    """Update item if user is the owner."""
    item = await artifact_repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Owner-only check
    if str(item.owner_id) != str(auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update this item"
        )

    # Update and save
    item.update(**request.dict(exclude_unset=True))
    await artifact_repo.save(item)
    return ItemResponse(**item.dict())
```

### Pattern 2: Admin-Only Access

Restrict an operation to system administrators:

```python
@router.post("/admin/users")
async def create_user(
    request: UserCreate,
    auth: AuthContextDep,
    user_repo: UserRepoDep,
) -> UserResponse:
    """Create a new user (admin only)."""
    # Check admin role
    if not auth.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can create users"
        )

    user = await user_repo.create(
        username=request.username,
        email=request.email,
    )
    return UserResponse(**user.dict())
```

### Pattern 3: Team Member Access

Grant access to all members of a team:

```python
@router.get("/teams/{team_id}/members")
async def list_team_members(
    team_id: str,
    auth: AuthContextDep,
    team_repo: TeamRepoDep,
) -> list[TeamMemberResponse]:
    """List team members if user is a member of the team."""
    # Check if user is a member of the team
    is_member = await team_repo.is_user_member(team_id, str(auth.user_id))
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team"
        )

    members = await team_repo.list_members(team_id)
    return [TeamMemberResponse(**m.dict()) for m in members]
```

### Pattern 4: Public vs. Private Access

Allow public access to certain resources while restricting others:

```python
@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    auth: AuthContext | None = Depends(optional_verify_token),
    artifact_repo: ArtifactRepoDep,
) -> ArtifactResponse:
    """Get artifact by ID with visibility checks.

    Public artifacts are visible to all authenticated users.
    Private artifacts are only visible to the owner.
    """
    artifact = await artifact_repo.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Allow public access
    if artifact.visibility == "public":
        return ArtifactResponse(**artifact.dict())

    # Private: check ownership
    if auth is None or str(artifact.owner_id) != str(auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This artifact is private"
        )

    return ArtifactResponse(**artifact.dict())
```

### Pattern 5: Scope-Based Feature Gates

Use scopes to gate fine-grained features:

```python
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,
    artifact_repo: ArtifactRepoDep,
) -> ArtifactResponse:
    """Create artifact with optional validation scope."""
    artifact = await artifact_repo.create(
        name=request.name,
        owner_id=str(auth.user_id),
    )

    # Premium validation feature (behind a scope)
    if auth.has_scope(Scope.artifact_write):
        await artifact_repo.validate(artifact)

    return ArtifactResponse(**artifact.dict())
```

## Writing Tests for Auth-Aware Endpoints

### Test Pattern 1: Local Mode (No Auth)

In local mode, no authentication is enforced. Use `LocalAuthProvider`:

```python
import pytest
from fastapi.testclient import TestClient
from skillmeat.api.auth.local_provider import LocalAuthProvider
from skillmeat.api.dependencies import set_auth_provider

@pytest.fixture
def local_client():
    """TestClient with local (zero-auth) provider."""
    set_auth_provider(LocalAuthProvider())
    app = create_test_app()  # Your FastAPI app factory
    return TestClient(app)

def test_local_mode_no_auth_required(local_client):
    """Endpoints work without Authorization header in local mode."""
    response = local_client.get("/api/v1/artifacts")
    assert response.status_code == 200
```

### Test Pattern 2: Mock Auth Provider

Use a mock provider to test auth enforcement:

```python
from unittest.mock import MagicMock
from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.schemas.auth import AuthContext, Role, Scope

class MockAuthProvider(AuthProvider):
    """Test double that returns a configured AuthContext."""

    def __init__(self, auth_context: AuthContext):
        self._context = auth_context

    async def validate(self, request):
        return self._context

@pytest.fixture
def test_auth_context():
    """Typical team member with read-only access."""
    import uuid
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_read.value],
    )

@pytest.fixture
def mock_auth_client(test_auth_context):
    """TestClient with mock auth provider."""
    set_auth_provider(MockAuthProvider(test_auth_context))
    app = create_test_app()
    return TestClient(app)

def test_authenticated_endpoint_returns_user_id(mock_auth_client, test_auth_context):
    """Authenticated endpoint receives the correct AuthContext."""
    response = mock_auth_client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_auth_context.user_id)
```

### Test Pattern 3: Scope Enforcement

Test that endpoints enforce required scopes:

```python
import uuid
from skillmeat.api.schemas.auth import AuthContext, Role, Scope

@pytest.fixture
def read_only_context():
    """AuthContext with only read scope."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[Role.viewer.value],
        scopes=[Scope.artifact_read.value],
    )

@pytest.fixture
def write_context():
    """AuthContext with write scope."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_write.value],
    )

def test_write_endpoint_requires_write_scope(read_only_context):
    """POST endpoint returns 403 when write scope is missing."""
    set_auth_provider(MockAuthProvider(read_only_context))
    client = TestClient(create_test_app())

    response = client.post("/api/v1/artifacts", json={"name": "test"})
    assert response.status_code == 403  # Forbidden
    assert "Missing required scopes" in response.json()["detail"]

def test_write_endpoint_succeeds_with_write_scope(write_context):
    """POST endpoint returns 201 when write scope is present."""
    set_auth_provider(MockAuthProvider(write_context))
    client = TestClient(create_test_app())

    response = client.post("/api/v1/artifacts", json={"name": "test"})
    assert response.status_code == 201
    assert response.json()["id"] is not None
```

### Test Pattern 4: Owner-Only Access

Test authorization logic:

```python
@pytest.fixture
def user_a():
    """User A context."""
    return AuthContext(
        user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        tenant_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_write.value],
    )

@pytest.fixture
def user_b():
    """User B context."""
    return AuthContext(
        user_id=uuid.UUID("660e8400-e29b-41d4-a716-446655440001"),
        tenant_id=uuid.uuid4(),
        roles=[Role.team_member.value],
        scopes=[Scope.artifact_write.value],
    )

def test_owner_can_update_artifact(user_a, artifact_repo):
    """Owner can update their artifact."""
    set_auth_provider(MockAuthProvider(user_a))
    client = TestClient(create_test_app())

    # Create artifact (owned by user_a)
    create_resp = client.post("/api/v1/artifacts", json={"name": "test"})
    artifact_id = create_resp.json()["id"]

    # User A can update
    response = client.put(
        f"/api/v1/artifacts/{artifact_id}",
        json={"name": "updated"}
    )
    assert response.status_code == 200

def test_non_owner_cannot_update_artifact(user_a, user_b):
    """Non-owner cannot update another user's artifact."""
    # Create artifact as user_a
    set_auth_provider(MockAuthProvider(user_a))
    client_a = TestClient(create_test_app())
    create_resp = client_a.post("/api/v1/artifacts", json={"name": "test"})
    artifact_id = create_resp.json()["id"]

    # Try to update as user_b
    set_auth_provider(MockAuthProvider(user_b))
    client_b = TestClient(create_test_app())
    response = client_b.put(
        f"/api/v1/artifacts/{artifact_id}",
        json={"name": "hacked"}
    )
    assert response.status_code == 403
```

## Anti-Patterns: What NOT to Do

### ❌ Don't: Ignore scope requirements

```python
# WRONG: This endpoint allows writes without checking the scope
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,  # No scope validation!
) -> ArtifactResponse:
    # Anyone with any auth can create artifacts
    artifact = await artifact_repo.create(...)
    return ArtifactResponse(**artifact.dict())
```

### ✅ Do: Enforce scope requirements

```python
# CORRECT: Require artifact:write scope
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value])),
) -> ArtifactResponse:
    artifact = await artifact_repo.create(...)
    return ArtifactResponse(**artifact.dict())
```

### ❌ Don't: Trust client-supplied user IDs

```python
# WRONG: User can specify any user_id in the request
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,  # request.owner_id comes from client!
    auth: AuthContextDep,
) -> ArtifactResponse:
    # Attacker can create artifacts owned by anyone
    artifact = await artifact_repo.create(
        name=request.name,
        owner_id=request.owner_id,  # SECURITY BUG!
    )
    return ArtifactResponse(**artifact.dict())
```

### ✅ Do: Always use auth.user_id for ownership

```python
# CORRECT: Always use authenticated user as owner
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,
) -> ArtifactResponse:
    # Artifacts are always owned by the authenticated user
    artifact = await artifact_repo.create(
        name=request.name,
        owner_id=str(auth.user_id),  # Cannot be spoofed
    )
    return ArtifactResponse(**artifact.dict())
```

### ❌ Don't: Log sensitive auth data

```python
# WRONG: Logging auth tokens is a security risk
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,
    token: str,  # Token passed as parameter
) -> ArtifactResponse:
    logger.info(f"Creating artifact with token: {token}")  # SECURITY BUG!
    ...
```

### ✅ Do: Log only non-sensitive user info

```python
# CORRECT: Log only safe user identifiers
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,
) -> ArtifactResponse:
    logger.info(f"User {auth.user_id} creating artifact")  # Safe
    ...
```

### ❌ Don't: Bypass scope checks for "trusted" operations

```python
# WRONG: Always enforce scopes, no exceptions
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,
) -> ArtifactResponse:
    # "Just this once" — but scope enforcement is forgotten
    artifact = await artifact_repo.create(...)  # No scope check!
    return ArtifactResponse(**artifact.dict())
```

### ✅ Do: Enforce scopes consistently

```python
# CORRECT: Every write operation requires artifact:write
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value])),
) -> ArtifactResponse:
    artifact = await artifact_repo.create(...)
    return ArtifactResponse(**artifact.dict())
```

## Accessing AuthContext in Service and Repository Layers

AuthContext flows through your entire call chain. Pass it explicitly when needed:

```python
# In a service layer
class ArtifactService:
    async def create_artifact(
        self,
        auth: AuthContext,  # Receive from router
        name: str,
    ) -> Artifact:
        """Create artifact for the authenticated user."""
        artifact = Artifact(
            name=name,
            owner_id=str(auth.user_id),  # Use to set owner
        )
        return await self.repo.save(artifact)

# In a router
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContextDep,
    service: ArtifactServiceDep,
) -> ArtifactResponse:
    artifact = await service.create_artifact(
        auth=auth,  # Pass down to service
        name=request.name,
    )
    return ArtifactResponse(**artifact.dict())
```

## Accessing AuthContext from Request State

If an endpoint already has auth enforced at the router level, you can also read it from `request.state`:

```python
@router.get("/profile")
async def get_profile(
    request: Request,
    auth: AuthContextDep,  # Dependency still runs (and validates)
) -> ProfileResponse:
    """Get current user profile.

    Two ways to access AuthContext:
    1. From dependency injection (auth parameter)
    2. From request.state (set by require_auth dependency)
    """
    # Both of these are the same object:
    auth_from_param = auth
    auth_from_state = request.state.auth_context

    assert auth_from_param is auth_from_state

    return ProfileResponse(
        user_id=str(auth.user_id),
        roles=auth.roles,
    )
```

## Local Mode vs. Enterprise Mode

SkillMeat supports two deployment modes:

### Local Mode (Development/Single-Tenant)

- No authentication required
- Uses `LocalAuthProvider` (always grants access)
- `AuthContext.tenant_id` is `None`
- Perfect for CLI and local deployments

```python
# Local mode: this always works without a token
@router.get("/artifacts")
async def list_artifacts(auth: AuthContextDep) -> list[ArtifactResponse]:
    # auth is always LOCAL_ADMIN_CONTEXT with all scopes
    # No actual token validation happens
    artifacts = await artifact_repo.list_all()
    return [ArtifactResponse(**a.dict()) for a in artifacts]
```

### Enterprise Mode (Multi-Tenant)

- Requires valid JWT tokens (Clerk or similar)
- `AuthContext.tenant_id` is set
- Automatic tenant isolation via `TenantContext` middleware
- Full RBAC enforcement

```python
# Enterprise mode: token is required
@router.get("/artifacts")
async def list_artifacts(auth: AuthContextDep) -> list[ArtifactResponse]:
    # auth is constructed from JWT claims
    # Repositories automatically scope queries to tenant_id
    artifacts = await artifact_repo.list_for_tenant(auth.tenant_id)
    return [ArtifactResponse(**a.dict()) for a in artifacts]
```

## Converting UUIDs for Database Queries

AuthContext stores `user_id` as a `uuid.UUID`, but database models may store it differently. Use the helper:

```python
from skillmeat.api.schemas.auth import str_owner_id

@router.get("/artifacts")
async def list_artifacts(
    auth: AuthContextDep,
    artifact_repo: ArtifactRepoDep,
) -> list[ArtifactResponse]:
    """List artifacts owned by current user."""
    # Convert UUID to string for database query
    owner_id = str_owner_id(auth)  # Returns lowercase UUID string
    artifacts = await artifact_repo.list_by_owner(owner_id)
    return [ArtifactResponse(**a.dict()) for a in artifacts]
```

## Reference: Complete Endpoint Example

Here's a complete, production-ready example combining all patterns:

```python
from fastapi import APIRouter, HTTPException, status, Depends
from skillmeat.api.dependencies import require_auth, AuthContextDep, ArtifactRepoDep
from skillmeat.api.schemas.auth import AuthContext, Scope, str_owner_id
from skillmeat.api.schemas.artifacts import ArtifactCreate, ArtifactUpdate, ArtifactResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])

@router.post("/")
async def create_artifact(
    request: ArtifactCreate,
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value])),
    artifact_repo: ArtifactRepoDep = Depends(),
) -> ArtifactResponse:
    """Create a new artifact.

    Args:
        request: Artifact creation request
        auth: Authenticated user context (requires artifact:write scope)
        artifact_repo: Artifact repository (injected)

    Returns:
        Created artifact with ID

    Raises:
        HTTPException 403: If user lacks artifact:write scope
        HTTPException 422: If request validation fails
    """
    logger.info(f"User {auth.user_id} creating artifact: {request.name}")

    artifact = await artifact_repo.create(
        name=request.name,
        artifact_type=request.artifact_type,
        source=request.source,
        owner_id=str_owner_id(auth),  # Always use authenticated user
    )

    return ArtifactResponse(**artifact.dict())


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    auth: AuthContextDep,
    artifact_repo: ArtifactRepoDep,
) -> ArtifactResponse:
    """Get artifact by ID.

    Returns 404 if artifact not found.
    Returns 403 if artifact is private and user is not the owner.
    """
    artifact = await artifact_repo.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Check visibility
    if artifact.visibility == "private":
        if str(artifact.owner_id) != str_owner_id(auth):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This artifact is private"
            )

    return ArtifactResponse(**artifact.dict())


@router.put("/{artifact_id}")
async def update_artifact(
    artifact_id: str,
    request: ArtifactUpdate,
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value])),
    artifact_repo: ArtifactRepoDep,
) -> ArtifactResponse:
    """Update an artifact.

    Only the owner can update their artifacts.

    Raises:
        HTTPException 404: Artifact not found
        HTTPException 403: User is not the owner
    """
    artifact = await artifact_repo.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if str(artifact.owner_id) != str_owner_id(auth):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update this artifact"
        )

    logger.info(f"User {auth.user_id} updating artifact {artifact_id}")

    artifact.update(**request.dict(exclude_unset=True))
    updated = await artifact_repo.save(artifact)

    return ArtifactResponse(**updated.dict())


@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_write.value])),
    artifact_repo: ArtifactRepoDep,
) -> dict:
    """Delete an artifact.

    Only the owner can delete their artifacts.

    Returns:
        Empty 204 response

    Raises:
        HTTPException 404: Artifact not found
        HTTPException 403: User is not the owner
    """
    artifact = await artifact_repo.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if str(artifact.owner_id) != str_owner_id(auth):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete this artifact"
        )

    logger.info(f"User {auth.user_id} deleting artifact {artifact_id}")

    await artifact_repo.delete(artifact_id)

    return {}
```

## Troubleshooting

### Problem: "Missing authentication token" (401)

This means the endpoint requires a token but none was provided.

```python
# Check that your endpoint has auth requirement
@router.get("/protected")
async def protected(auth: AuthContextDep):  # ✓ Requires auth
    pass

@router.get("/unprotected")
async def unprotected():  # ✗ No auth required
    pass
```

### Problem: "Missing required scopes" (403)

The user has a token but lacks the required scope.

```python
# Solution: Ensure the auth context has the required scope
# Or: Change the endpoint to require a different/no scope
@router.post("/items")
async def create(
    # Change from artifact:write to a scope the user has
    auth: AuthContext = Depends(require_auth(scopes=[Scope.artifact_read.value]))
):
    pass
```

### Problem: AuthContext is None

This can happen if you try to access auth without declaring it as a dependency.

```python
# WRONG: auth is None here
@router.get("/items")
async def list_items(auth = None):
    return auth  # None!

# CORRECT: Declare as a dependency
@router.get("/items")
async def list_items(auth: AuthContextDep):
    return auth  # AuthContext instance
```

## References

- **Auth types**: `skillmeat/cache/auth_types.py` — Role and Visibility enums
- **Auth schemas**: `skillmeat/api/schemas/auth.py` — AuthContext dataclass and Scope enum
- **Dependencies**: `skillmeat/api/dependencies.py` — `require_auth`, dependency type aliases
- **Auth providers**: `skillmeat/api/auth/` — LocalAuthProvider, ClerkAuthProvider implementations
- **Middleware**: `skillmeat/api/middleware/tenant_context.py` — Tenant isolation for multi-tenant mode
- **Tests**: `skillmeat/api/tests/test_auth_*.py` — Complete test examples

## Key Takeaways

1. **Always use AuthContext dependencies** — Never manually construct auth state
2. **Enforce scopes explicitly** — Use `require_auth(scopes=[...])` for write operations
3. **Use auth.user_id for ownership** — Never trust client-supplied user IDs
4. **Check visibility rules** — Private resources need additional permission checks
5. **Log safely** — Log user IDs, not tokens
6. **Test with mock providers** — Use `MockAuthProvider` in tests to simulate different auth scenarios
7. **Respect local vs. enterprise modes** — Local mode has no auth, enterprise mode requires tokens
8. **Convert UUIDs carefully** — Use `str_owner_id()` when passing to database queries

