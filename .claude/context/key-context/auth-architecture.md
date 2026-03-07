# Auth Architecture: AAA/RBAC System

**Load this when**: adding auth to endpoints, modifying middleware, debugging 401/403, working with RBAC checks.

## Provider Selection (startup, `server.py` lifespan)

| `SKILLMEAT_AUTH_PROVIDER` | Provider | Behavior |
|--------------------------|----------|----------|
| `local` (default) | `LocalAuthProvider` | Returns `LOCAL_ADMIN_CONTEXT` — all requests pass as system_admin |
| `clerk` | `ClerkAuthProvider` | Validates Bearer JWT via Clerk JWKS; requires `CLERK_JWKS_URL` + `CLERK_ISSUER` |

`LocalAuthProvider` **must always remain the default fallback**. Never remove it.

Provider is registered once via `set_auth_provider()` in lifespan, then retrieved per-request by `require_auth()`.

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/api/schemas/auth.py` | `AuthContext`, `Role`, `Scope`, `LOCAL_ADMIN_CONTEXT` |
| `skillmeat/api/auth/provider.py` | `AuthProvider` ABC |
| `skillmeat/api/auth/local_provider.py` | Local passthrough impl |
| `skillmeat/api/auth/clerk_provider.py` | Clerk JWT impl |
| `skillmeat/api/dependencies.py` | `require_auth()`, `AuthContextDep`, `set_auth_provider()` |
| `skillmeat/api/middleware/auth.py` | Legacy `verify_token`/`TokenDep` (pre-AAA) |
| `skillmeat/api/middleware/enterprise_auth.py` | `verify_enterprise_pat` / `EnterprisePATDep` (bootstrap PAT) |
| `skillmeat/api/middleware/tenant_context.py` | `set_tenant_context_dep` / `TenantContextDep` |
| `skillmeat/cache/auth_types.py` | DB-layer enums: `OwnerType`, `Visibility`, `UserRole` |
| `skillmeat/api/config.py` | `auth_provider`, `clerk_jwks_url`, `clerk_issuer`, `auth_enabled` |

## AuthContext Fields

```python
@dataclass(frozen=True)
class AuthContext:
    user_id:   uuid.UUID       # authenticated user
    tenant_id: uuid.UUID | None  # None in local/single-tenant mode
    roles:     list[str]       # Role enum values
    scopes:    list[str]       # Scope enum values
```

Helpers: `has_role(role)`, `is_admin()`, `has_scope(scope)`, `has_any_scope(*scopes)`.
`admin:*` wildcard in scopes satisfies every `has_scope()` check automatically.

## Roles

| Role | Value | Privilege |
|------|-------|-----------|
| `system_admin` | `"system_admin"` | Full tenant access |
| `team_admin` | `"team_admin"` | Admin within team |
| `team_member` | `"team_member"` | Standard team access |
| `viewer` | `"viewer"` | Read-only (default) |

`system_admin > team_admin > team_member > viewer`

## Scopes

| Scope | Value |
|-------|-------|
| `artifact_read` | `"artifact:read"` |
| `artifact_write` | `"artifact:write"` |
| `collection_read` | `"collection:read"` |
| `collection_write` | `"collection:write"` |
| `deployment_read` | `"deployment:read"` |
| `deployment_write` | `"deployment:write"` |
| `admin_wildcard` | `"admin:*"` |

## DB-Layer Enums (`auth_types.py`)

| Enum | Values | Used for |
|------|--------|---------|
| `OwnerType` | `user`, `team` | `owner_type` column on resources |
| `Visibility` | `private`, `team`, `public` | Who can see a resource |
| `UserRole` | mirrors `Role` above | DB storage on users/team_members rows |

Import path: `from skillmeat.cache.auth_types import OwnerType, Visibility, UserRole`

## Adding Auth to an Endpoint

```python
# Authenticate only
@router.get("/items")
async def list_items(auth: AuthContextDep) -> ...:
    ...

# Authenticate + scope gate
@router.post("/items")
async def create_item(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:write"]))
) -> ...:
    ...

# Enterprise PAT (bootstrap — separate from require_auth)
router = APIRouter(dependencies=[Depends(verify_enterprise_pat)])
```

## Tenant Context (enterprise multi-tenant)

Attach `TenantContextDep` to enterprise routers so that DB queries are scoped to the correct tenant automatically:

```python
router = APIRouter(dependencies=[TenantContextDep])
```

When `tenant_id` is `None` (local mode), the dependency is a no-op. Enterprise repos fall back to `DEFAULT_TENANT_ID`.

## owner_id Type Mismatch

`cache/models.py` stores `owner_id` as `Column(String)`. `AuthContext.user_id` is `uuid.UUID`. Always convert:

```python
from skillmeat.api.schemas.auth import str_owner_id
owner_filter = str_owner_id(auth_context)  # "550e8400-..."
```

Never compare `uuid.UUID` directly to a string column — use `str_owner_id()`.

## Anti-Patterns

- Do not import from `cache.auth_types` in routers — use `skillmeat.api.schemas.auth` (re-exports all needed types).
- Do not create a new `AuthContext` inside a route — rely on `require_auth()` / the provider.
- Do not use the legacy `TokenDep` / `verify_token` (pre-AAA) for new endpoints — use `AuthContextDep`.
- Do not skip `str_owner_id()` when filtering by owner — direct UUID-to-String comparison silently returns nothing.
- Do not attach `TenantContextDep` before `require_auth` resolves — it depends on `AuthContext` being present.

## Excluded Paths (no auth required)

`/health`, `/docs`, `/redoc`, `/openapi.json`, `/`, `/api/v1/version`

All other `/api/v1/*` paths go through the registered `AuthProvider`.
