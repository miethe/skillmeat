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

## Complete DI Pattern Reference (2026-03-12)

Comprehensive guide to the Hexagonal Architecture DI pattern:
- **File**: `.claude/agent-memory/codebase-explorer/DI_PATTERN_REFERENCE.md`
- **Covers**: All 19 RepoDep aliases, interface signatures, getter functions, edition-aware routing
- **Use when**: Adding endpoints, migrating routers, understanding repository contracts

## Manager Dependency Audit (2026-03-12)

### Findings Summary

Complete audit of 9 routers reveals **10+ critical READ operations** using manager deps that must migrate to repository DI, and **5+ WRITE operations** that should keep managers but add cache refresh.

**Critical Issues** (Priority P0):
- artifacts.py: 3 utilities + 2 endpoints with manager dependency (discovery endpoints broken)
- marketplace_sources.py: 1 helper + 6 endpoints (duplicate detection fails silently)
- match.py: 1 endpoint using ArtifactManagerDep (returns empty results)

**Degraded Operations** (Priority P1):
- tags.py: Multiple endpoints using implicit CollectionManagerDep
- user_collections.py: Mixed read/write, reads fail in enterprise

**Key Pattern**: Edition-aware factory pattern established in dependencies.py (lines 536–685+). All *RepoDep aliases follow consistent routing: check settings.edition, return Local or Enterprise implementation.

### Audit Documents

- **Main audit**: `manager-dep-audit-detailed.md` - Complete analysis with router-by-router breakdown
- **Output deliverable**: `/home/miethe/dev/skillmeat/MANAGER_DEPENDENCY_AUDIT.md` - Structured audit for delegation
- **Quick reference**: `/home/miethe/dev/skillmeat/.claude/findings/MANAGER_MIGRATION_MATRIX.md` - Fast lookup matrix

### Key Files for Implementation

```
/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py
/home/miethe/dev/skillmeat/skillmeat/api/routers/marketplace_sources.py
/home/miethe/dev/skillmeat/skillmeat/api/routers/match.py
/home/miethe/dev/skillmeat/skillmeat/api/routers/tags.py
/home/miethe/dev/skillmeat/skillmeat/api/routers/user_collections.py
/home/miethe/dev/skillmeat/skillmeat/api/dependencies.py (reference)
/home/miethe/dev/skillmeat/skillmeat/cache/enterprise_repositories.py (reference)
/home/miethe/dev/skillmeat/skillmeat/api/routers/health.py (template, line 174)
```

### Migration Strategy

1. **Verify dependencies exist** before implementation:
   - `DbArtifactHistoryRepoDep` (for version history)
   - `TagRepoDep` (for tag lookups)
   - Methods: `ArtifactRepoDep.list_by_collection()`, `ArtifactRepoDep.search()`

2. **Phase 1 (P0)**: Fix broken endpoints (artifacts, marketplace_sources, match)
   - Replace manager calls with repo DI
   - Add edition checks to discovery endpoints (501 Not Implemented)

3. **Phase 2 (P1)**: Fix degraded operations (tags, user_collections)
   - Migrate READs to repo DI
   - Keep WRITEs but add cache refresh

4. **Phase 3 (P3)**: Polish (health, mcp)
   - Verify edition-awareness
   - Decide: disable MCP in enterprise or add DB support

### Invariants

- **Edition-aware routing**: All repository DI uses pattern from dependencies.py (check settings.edition)
- **Cache refresh required**: All WRITEs must call `cache_service.refresh_*()` after manager operation
- **Enterprise implementations ready**: All core repos exist in enterprise_repositories.py with tenant filtering
- **No write-through issues**: Managers handle filesystem; repos handle DB; cache service bridges both
