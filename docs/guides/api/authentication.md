---
title: API Authentication Guide
description: Authenticate requests to the SkillMeat API using Bearer tokens, PAT tokens, or local mode
category: API Development
---

# API Authentication Guide

The SkillMeat API supports multiple authentication modes depending on your deployment. This guide explains how to authenticate requests and work with the authentication system.

## Overview

SkillMeat provides flexible authentication to support both local development and multi-tenant enterprise deployments:

- **Local Mode (Default)** — Zero-auth mode for single-user development. No authentication required.
- **Bearer Token Mode** — Production-ready JWT validation via authentication providers (e.g., Clerk).
- **Enterprise PAT Mode** — Static API key validation for enterprise deployments.

### Authentication is Configurable

Authentication is disabled by default in development. Enable it via environment variables or configuration files.

## Authentication Methods

### 1. Local Mode (Zero-Auth)

In local (single-user) development, no authentication is required.

```bash
# Start API in local mode (default)
skillmeat web dev --api-only

# All requests succeed without an Authorization header
curl http://localhost:8080/api/v1/artifacts
# Returns 200 OK
```

**When to use**: Local development, testing, single-user deployments.

### 2. Bearer Token Authentication

For production deployments, use Bearer token authentication with JWT validation.

#### Header Format

```
Authorization: Bearer <token>
```

#### Example Request

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/artifacts
```

#### Enable Bearer Token Auth

Set `SKILLMEAT_AUTH_ENABLED=true` to require Bearer tokens:

```bash
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_ENV=production

# Restart the API server
uvicorn skillmeat.api.server:app --host 0.0.0.0 --port 8080
```

#### Token Validation

The API validates tokens using an authentication provider. Token validation includes:

- **Token presence** — `Authorization` header with `Bearer` prefix required
- **Token format** — Must be a valid JWT token
- **Token expiration** — Expired tokens are rejected with 401

**Invalid token response**:

```json
{
  "detail": "Invalid or expired token",
  "WWW-Authenticate": "Bearer"
}
```

### 3. Enterprise PAT (Personal Access Token)

For enterprise deployments, use a static API token stored in `ENTERPRISE_PAT_SECRET`.

#### Header Format

```
Authorization: Bearer <pat_token>
```

#### Example Request

```bash
PAT="your-enterprise-pat-token-here"

curl -H "Authorization: Bearer $PAT" \
  http://localhost:8080/api/v1/artifacts
```

#### Enable Enterprise PAT Auth

```bash
export ENTERPRISE_PAT_SECRET="your-static-api-token"
export SKILLMEAT_EDITION=enterprise

# Restart the API server
uvicorn skillmeat.api.server:app --host 0.0.0.0 --port 8080
```

**Token validation**:
- PAT is compared using constant-time comparison (prevents timing attacks)
- Missing token returns 401 Unauthorized
- Invalid token returns 403 Forbidden

## Authentication Context

When a request is authenticated, the API attaches an `AuthContext` to the request containing:

```python
@dataclass(frozen=True)
class AuthContext:
    user_id: uuid.UUID           # Authenticated user ID
    tenant_id: uuid.UUID | None  # Tenant ID (None in local mode)
    roles: list[str]             # Role assignments (e.g., "system_admin", "team_member")
    scopes: list[str]            # Permission scopes (e.g., "artifact:read", "artifact:write")
```

### Local Admin Context

In local mode, all requests automatically carry the implicit admin context:

```python
LOCAL_ADMIN_CONTEXT = AuthContext(
    user_id=uuid.UUID("00000000-0000-4000-a000-000000000002"),
    tenant_id=None,
    roles=["system_admin"],
    scopes=[
        "artifact:read",
        "artifact:write",
        "collection:read",
        "collection:write",
        "deployment:read",
        "deployment:write",
        "admin:*",
    ]
)
```

### Enterprise Service Account

When using enterprise PAT authentication, the authenticated context is:

```python
AuthContext(
    user_id=uuid.UUID("00000000-0000-4000-a000-000000000003"),  # Enterprise service sentinel
    tenant_id=None,  # (wired in later phases)
    roles=["system_admin"],
    scopes=[all defined Scope values],  # Full permission set
)
```

## Scopes and Permissions

Scopes define fine-grained permissions for API operations. The scope naming convention is `resource:action`.

| Scope | Resource | Action | Purpose |
|-------|----------|--------|---------|
| `artifact:read` | Artifacts | Read | Read artifact metadata and content |
| `artifact:write` | Artifacts | Write | Create, update, and delete artifacts |
| `collection:read` | Collections | Read | Read collection metadata and membership |
| `collection:write` | Collections | Write | Create, update, and delete collections |
| `deployment:read` | Deployments | Read | Read deployment records and status |
| `deployment:write` | Deployments | Write | Create and remove deployments |
| `admin:*` | Admin | Wildcard | Grant all admin operations |

### Scope Checking in Code

Routes can require specific scopes:

```python
from fastapi import Depends
from skillmeat.api.dependencies import require_auth

@router.get("/artifacts")
async def list_artifacts(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:read"])),
):
    # Only proceeds if auth context carries "artifact:read" scope
    ...

@router.post("/artifacts")
async def create_artifact(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:write"])),
):
    # Requires "artifact:write" scope
    ...
```

## Roles and Hierarchy

Roles control broad access levels. The role hierarchy (most to least privileged):

| Role | Description | Typical Use |
|------|-------------|------------|
| `system_admin` | Full system access across tenant | Platform administrators |
| `team_admin` | Administrative access within a team | Team leads |
| `team_member` | Standard team member access | Team contributors |
| `viewer` | Read-only access (default) | Guests, external partners |

### Role Checking in Code

```python
from skillmeat.api.schemas.auth import Role

# Check single role
if auth.has_role(Role.system_admin):
    # User is system admin
    ...

# Check admin status
if auth.is_admin():
    # User carries system_admin role
    ...
```

## Error Responses

### 401 Unauthorized

Returned when authentication is required but missing or invalid.

**Causes**:
- Missing `Authorization` header
- `Authorization` header does not start with `Bearer `
- Token is invalid or expired

**Response**:

```json
{
  "detail": "Missing authentication token",
  "WWW-Authenticate": "Bearer"
}
```

or

```json
{
  "detail": "Invalid or expired token",
  "WWW-Authenticate": "Bearer"
}
```

### 403 Forbidden

Returned when authentication is valid but the user lacks required permissions.

**Causes**:
- User doesn't carry required scope
- User doesn't carry required role
- Enterprise PAT token is misconfigured

**Response** (enterprise PAT):

```json
{
  "detail": "Invalid enterprise PAT."
}
```

**Response** (missing enterprise config):

```json
{
  "detail": "Enterprise authentication is not configured on this server."
}
```

## Testing Endpoints Locally

### Without Authentication (Default)

In development (local mode), no authentication is required:

```bash
# List artifacts
curl http://localhost:8080/api/v1/artifacts

# Create artifact
curl -X POST http://localhost:8080/api/v1/artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-artifact",
    "artifact_type": "skill",
    "source": "user/repo/path"
  }'

# Get artifact
curl http://localhost:8080/api/v1/artifacts/{artifact_id}
```

### With Bearer Token (Production Testing)

When testing against a production server with authentication enabled:

```bash
# 1. Obtain a valid JWT token from your auth provider

# 2. Set the token in an environment variable
export TOKEN="your-jwt-token-here"

# 3. Include token in requests
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/artifacts

# 4. Create artifacts with authentication
curl -X POST http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-artifact",
    "artifact_type": "skill",
    "source": "user/repo/path"
  }'
```

### With Enterprise PAT (Enterprise Testing)

When testing against an enterprise deployment with PAT authentication:

```bash
# 1. Get the PAT token from your admin
PAT="enterprise-pat-token-here"

# 2. Include in Authorization header
curl -H "Authorization: Bearer $PAT" \
  http://localhost:8080/api/v1/artifacts

# 3. Make authenticated requests
curl -X POST http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-artifact",
    "artifact_type": "skill",
    "source": "user/repo/path"
  }'
```

## Protected and Unprotected Routes

### Unprotected Routes

These routes are always available, even when authentication is enabled:

- `GET /health` — Health check
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc
- `GET /openapi.json` — OpenAPI specification
- `GET /api/v1/version` — API version

### Protected Routes

All other routes under `/api/v1` are protected when `SKILLMEAT_AUTH_ENABLED=true`:

- `GET /api/v1/artifacts`
- `POST /api/v1/artifacts`
- `GET /api/v1/artifacts/{id}`
- `PUT /api/v1/artifacts/{id}`
- `DELETE /api/v1/artifacts/{id}`
- (and all other `/api/v1/*` endpoints)

## Configuration Reference

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SKILLMEAT_AUTH_ENABLED` | bool | `false` | Require Bearer token authentication |
| `SKILLMEAT_ENV` | string | `development` | Environment: `development`, `production`, or `testing` |
| `SKILLMEAT_EDITION` | string | `local` | Deployment edition: `local` or `enterprise` |
| `ENTERPRISE_PAT_SECRET` | string | (none) | Enterprise PAT token (required if edition is enterprise) |

### Example Configurations

**Development (zero-auth)**:

```bash
export SKILLMEAT_ENV=development
export SKILLMEAT_AUTH_ENABLED=false
```

**Production (Bearer token)**:

```bash
export SKILLMEAT_ENV=production
export SKILLMEAT_AUTH_ENABLED=true
# (Token validation configured via auth provider)
```

**Enterprise (PAT)**:

```bash
export SKILLMEAT_ENV=production
export SKILLMEAT_EDITION=enterprise
export ENTERPRISE_PAT_SECRET="your-secret-token"
```

## Authentication Dependency Injection

### Using `require_auth()` in Routes

Routes can access the authenticated context using the `require_auth()` dependency:

```python
from fastapi import APIRouter, Depends
from skillmeat.api.dependencies import require_auth
from skillmeat.api.schemas.auth import AuthContext

router = APIRouter()

@router.get("/protected")
async def protected_route(auth: AuthContext = Depends(require_auth())):
    """This endpoint requires valid authentication."""
    return {
        "user_id": str(auth.user_id),
        "is_admin": auth.is_admin(),
        "has_read": auth.has_scope("artifact:read"),
    }
```

### With Scope Requirements

```python
@router.post("/artifacts")
async def create_artifact(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:write"])),
):
    """This endpoint requires artifact:write scope."""
    ...
```

### Router-Level Protection

Protect an entire router with authentication:

```python
from fastapi import APIRouter, Depends
from skillmeat.api.middleware.enterprise_auth import verify_enterprise_pat

router = APIRouter(
    prefix="/api/v1/enterprise",
    dependencies=[Depends(verify_enterprise_pat)],
)

@router.get("/resource")
async def get_resource():
    """All endpoints in this router require enterprise PAT."""
    ...
```

## Common Authentication Patterns

### Pattern: Read-Write Split with Different Scopes

```python
@router.get("/artifacts")
async def list_artifacts(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:read"])),
):
    # Read-only access
    ...

@router.post("/artifacts")
async def create_artifact(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:write"])),
):
    # Write-only access
    ...
```

### Pattern: Admin-Only Operations

```python
@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    auth: AuthContext = Depends(require_auth()),
):
    if not auth.is_admin():
        raise HTTPException(status_code=403, detail="Admins only")
    # Admin operation
    ...
```

### Pattern: Scope Negotiation

```python
@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    auth: AuthContext = Depends(require_auth()),
):
    # Check if user has read access
    if not auth.has_scope("artifact:read"):
        raise HTTPException(status_code=403, detail="Missing artifact:read scope")
    # Return artifact
    ...
```

## Switching Authentication Providers

SkillMeat uses an authentication provider pattern that decouples the API from specific auth backends. To change authentication providers (e.g., from local to Clerk), see the separate guide on provider configuration (currently managed in `skillmeat/api/auth/provider.py` and `dependencies.py`).

The provider must implement the `AuthProvider` abstract interface to validate requests and return `AuthContext`.

## See Also

- [API Reference](/docs/api/endpoints.md) — Endpoint documentation
- [Repository Architecture](/docs/guides/api/repository-architecture.md) — How authentication integrates with data access
