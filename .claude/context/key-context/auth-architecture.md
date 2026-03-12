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
| `skillmeat/core/ownership.py` | `OwnerTarget`, `ResolvedOwnership` domain DTOs |
| `skillmeat/core/services/ownership_resolver.py` | Request-time `OwnershipResolver` service |
| `skillmeat/core/interfaces/repositories.py` | `IMembershipRepository` interface |
| `skillmeat/core/repositories/local_membership.py` | Local membership lookups (team_members table) |
| `skillmeat/core/repositories/enterprise_membership.py` | Enterprise membership lookups (enterprise_team_members) |
| `skillmeat/core/repositories/filters.py` | Visibility, ownership, membership-aware filter helpers |

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
| `OwnerType` | `user`, `team`, `enterprise` | `owner_type` column on resources |
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

### TenantContextDep Middleware

Attach `TenantContextDep` to enterprise routers so that DB queries are scoped to the correct tenant automatically:

```python
router = APIRouter(dependencies=[TenantContextDep])
```

When `tenant_id` is `None` (local mode), the dependency is a no-op. Enterprise repos access tenant via `TenantContext` ContextVar:

```python
from skillmeat.api.middleware.tenant_context import get_tenant_id

# In enterprise repository
class EnterpriseArtifactRepository(IArtifactRepository):
    def _get_tenant_id(self) -> UUID:
        """Resolve tenant_id from TenantContext ContextVar."""
        return get_tenant_id()  # Raises if not in enterprise context
```

### Transaction Lifecycle (Enterprise Edition)

Enterprise repos use DI-injected `Session` for query execution:

```python
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_repo: ArtifactRepoDep,           # Gets enterprise repo + injected session
    db: SessionDep,                           # Manages transaction boundary
):
    try:
        # Repository calls session.flush() internally
        artifact_dto = artifact_repo.create(...)
        # Router commits transaction
        db.commit()
        return artifact_dto
    except Exception:
        db.rollback()
        raise
```

The `TenantContextDep` must be declared **before** `AuthContextDep` in the dependency chain, as it depends on `AuthContext` being present.

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
- Do not infer `owner_id` directly from `auth_context.user_id` for writes — use `ResolvedOwnership.default_owner` or explicit `OwnerTargetInput`.
- Do not assume tenant-wide visibility for `visibility=team` rows — use `apply_membership_visibility_filter` which checks actual team membership.
- Do not add enterprise scopes without checking `tenant_id is not None` — enterprise resolution only activates when enterprise context exists.
- Do not modify `OwnershipResolver` to persist state — it must remain request-scoped and stateless.

## Edition Configuration

| `SKILLMEAT_EDITION` | Behavior | Repository Layer | Session Management |
|---|---|---|---|
| `local` (default) | Single-tenant, filesystem-backed | Artifact/Collection repos use `LocalArtifactRepository`, `LocalCollectionRepository` | Auto-committed per-request, no explicit flush |
| `enterprise` | Multi-tenant, database-backed | Artifact/Collection repos use `EnterpriseArtifactRepository`, `EnterpriseCollectionRepository` | DI-injected session, explicit `flush()` per repo, `commit()` per router |

Enterprise edition uses DB-backed SQLAlchemy repositories with explicit transaction management. Unsupported providers (project, deployment, settings, etc.) return stubs (empty lists, no-ops).

### Repository Session Semantics (Enterprise)

- **Session ownership**: Routers own the transaction boundary, not repositories
- **Flush vs Commit**:
  - Repository calls `session.flush()` to persist changes within the transaction
  - Router calls `session.commit()` to finalize the transaction
  - Router calls `session.rollback()` on exception
- **No-op repositories**: Stub implementations (EnterpriseProjectRepository, etc.) don't query the session — they log and return synthetic/empty responses
- **Tenant context**: All queries automatically filtered by `_get_tenant_id()` from `TenantContext` ContextVar

## Visibility Model (Enterprise Edition)

Enterprise repositories enforce row-level visibility on all read paths via `apply_visibility_filter_stmt`:

| Visibility | Owner Type | Access |
|---|---|---|
| `private` | User | Owner only + system_admin |
| `public` | User or Team | All users in tenant |
| `team` | Team | Team members + system_admin |

**Admin bypass**: `system_admin` role can read all artifacts/collections in tenant regardless of visibility.

**Ownership error semantics**: Non-owners receive 404 (not disclosed as 403) when attempting to access private resources they don't own.

## Ownership Resolution

Request-time ownership resolution determines what a user can read and write based on their identity, team memberships, and enterprise context. The resolver produces a `ResolvedOwnership` object that downstream filters and validation helpers consume.

### Core Types (`skillmeat/core/ownership.py`)

```python
@dataclass(frozen=True)
class OwnerTarget:
    owner_type: OwnerType  # user | team | enterprise
    owner_id: str          # string for DB compat

@dataclass(frozen=True)
class ResolvedOwnership:
    default_owner: OwnerTarget         # new resources default to this
    readable_scopes: list[OwnerTarget] # all owners user can read from
    writable_scopes: list[OwnerTarget] # all owners user can write to
    has_enterprise_scope: bool         # True for system_admin in enterprise
    tenant_id: uuid.UUID | None        # enterprise tenant, if any
```

Helpers: `can_read_from(owner_type, owner_id)`, `can_write_to(owner_type, owner_id)`.

### Resolution Rules

| Condition | Readable Scopes | Writable Scopes | Default Owner |
|-----------|----------------|-----------------|---------------|
| Local mode (no tenant) | user only + teams | user only + writable teams | user |
| Enterprise, non-admin | user + teams + enterprise | user + writable teams | user |
| Enterprise, system_admin | user + teams + enterprise | user + writable teams + enterprise | user |

**Team role → write access**: `owner`, `team_admin`, `team_member` roles grant write; `viewer` is read-only.

**Default owner is always user-owned**. Team and enterprise ownership require explicit selection.

### FastAPI Dependencies (`skillmeat/api/dependencies.py`)

```python
# Inject resolved ownership into any route:
@router.get("/items")
async def list_items(
    auth: AuthContextDep,
    resolved: ResolvedOwnershipDep,
) -> ...:
    # Use resolved.readable_scopes for filtering
    ...

@router.post("/items")
async def create_item(
    auth: AuthContext = Depends(require_auth(scopes=["artifact:write"])),
    resolved: ResolvedOwnershipDep = ...,
) -> ...:
    # Validate write target against resolved.writable_scopes
    ...
```

DI chain: `get_membership_repository` (edition-aware) → `get_ownership_resolver` → `get_resolved_ownership`.

### API Contract Schemas (`skillmeat/api/schemas/auth.py`)

| Schema | Purpose | Default |
|--------|---------|---------|
| `OwnerScopeFilter` | Query param for list filtering (`user\|team\|enterprise\|all`) | `all` (return all readable) |
| `OwnerTargetInput` | Request body for mutation owner selection | `owner_type=user` (user-owned) |

### Mutation Semantics

- **Omitted owner target** → user-owned (the requesting user)
- **Explicit team selection** → requires `owner_type=team` + `owner_id=<team_uuid>` + user must have write role in that team
- **Explicit enterprise selection** → requires `owner_type=enterprise` + `owner_id=<tenant_uuid>` + `system_admin` role

Validate with `validate_write_target(target, resolved)` from `skillmeat/core/repositories/filters.py`.

### Filter Helpers (`skillmeat/core/repositories/filters.py`)

| Helper | Style | Purpose |
|--------|-------|---------|
| `apply_visibility_filter` / `_stmt` | 1.x / 2.x | Legacy visibility (public/private/team, admin bypass) |
| `apply_ownership_filter` / `_stmt` | 1.x / 2.x | Filter by `(owner_type, owner_id)` in readable_scopes |
| `apply_membership_visibility_filter` / `_stmt` | 1.x / 2.x | Membership-aware: team rows visible only if user is member |
| `validate_write_target` | — | Guard: checks target against writable_scopes |

**Prefer `apply_membership_visibility_filter`** over `apply_visibility_filter` when `ResolvedOwnership` is available — it gates team visibility by actual membership instead of tenant-wide access.

## Excluded Paths (no auth required)

`/health`, `/docs`, `/redoc`, `/openapi.json`, `/`, `/api/v1/version`

All other `/api/v1/*` paths go through the registered `AuthProvider`.
