# Codebase Exploration Memory - SkillMeat

## AAA & RBAC Infrastructure (PRD 2 Planning)

### Current Auth & Tenancy Foundation (Phase 1 Complete)

**Enterprise Auth:**
- `verify_enterprise_pat()` in `skillmeat/api/middleware/enterprise_auth.py` (lines 49–110)
  - Constant-time Bearer token validation via HMAC
  - Returns token or raises HTTPException(401/403)
  - Type alias: `EnterprisePATDep` for DI

**Tenant Filtering (Automatic):**
- `TenantContext: ContextVar[Optional[uuid.UUID]]` in `enterprise_repositories.py` (lines 99–101)
- `tenant_scope(tenant_id)` context manager (lines 104–138) — nests safely
- `EnterpriseRepositoryBase` auto-injects `WHERE tenant_id = ?` via `_apply_tenant_filter()` (structural isolation)
- `DEFAULT_TENANT_ID` constant in `skillmeat/cache/constants.py` (deterministic UUID for Phase 1)

**Repository Pattern:**
- Abstract interfaces in `skillmeat/core/interfaces/repositories.py` (I*Repository ABCs)
- Factory routing: `RepositoryFactory` in `skillmeat/cache/repository_factory.py` selects edition ("local" vs "enterprise")
- Enterprise models (`EnterpriseArtifact`, `EnterpriseCollection`, etc.) use PostgreSQL + UUID PKs
- Local models (SQLite) are separate; no cross-contamination

**RequestContext Contract:**
- Dataclass in `skillmeat/core/interfaces/context.py` with `user_id`, `request_id`, `tenant_id`, `edition`
- Currently unfilled; Phase 2 will populate from Clerk JWT

**Dependency Injection:**
- `AppState` container in `dependencies.py` (lifespan-managed singletons)
- `DbSessionDep` for per-request PostgreSQL sessions (enterprise routers)
- Example: `enterprise_content.py` router uses PAT auth + `ContentServiceDep`

### PRD 2 Gaps (What to Add)

- User, Team, TeamMember ORM models (enterprise schema)
- AuthProvider abstraction (LocalAuthProvider, ClerkAuthProvider)
- RBAC scope validation middleware (e.g., `require_auth(scopes=["artifact:write"])`)
- AuthContext injection into FastAPI requests (user_id, tenant_id, roles)
- Row-level filtering in repositories based on user role
- Clerk SDK in frontend; device code flow in CLI

### Key Invariants

- **Tenant filtering rule:** Every enterprise repo method MUST include `_apply_tenant_filter()` on queries. Omitting is a security defect.
- **Parameter convention:** `tenant_id: uuid.UUID` is always 2nd parameter in repo methods (after `session`).
- **Phase 1→Phase 2 swap:** Only service layer changes (swap `DEFAULT_TENANT_ID` constant for `ctx.tenant_id` from auth). No repo signature changes.
- **SQLAlchemy split (intentional):** Local repos use 1.x `session.query()`, enterprise repos use 2.x `select()`. Different backends justify divergence.

### File Locations Quick Ref

| Component | File | Notes |
|-----------|------|-------|
| PAT Auth | `skillmeat/api/middleware/enterprise_auth.py:49–110` | `verify_enterprise_pat()` |
| Tenant ContextVar | `skillmeat/cache/enterprise_repositories.py:99–138` | `TenantContext`, `tenant_scope()` |
| Repo Base | `skillmeat/cache/enterprise_repositories.py:150+` | `EnterpriseRepositoryBase` + `_apply_tenant_filter()` |
| Default Tenant | `skillmeat/cache/constants.py:11–22` | `DEFAULT_TENANT_ID` UUID |
| Request Context | `skillmeat/core/interfaces/context.py:15–58` | RequestContext dataclass |
| Repo Interfaces | `skillmeat/core/interfaces/repositories.py:77+` | I*Repository ABCs |
| Repo Factory | `skillmeat/cache/repository_factory.py:79+` | RepositoryFactory, edition routing |
| API Settings | `skillmeat/api/config.py:25–100` | APISettings, `edition` field |
| AppState | `skillmeat/api/dependencies.py:59+` | AppState container, lifespan |
| Enterprise Router | `skillmeat/api/routers/enterprise_content.py:40+` | Download endpoint, PAT-protected |
| Server Lifespan | `skillmeat/api/server.py:72–80` | FastAPI setup, middleware order |
