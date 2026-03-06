---
title: "Implementation Plan: AAA & RBAC Foundation (Individual & Team)"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-03-06
updated: 2026-03-06
feature_slug: aaa-rbac-foundation
feature_version: v1
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: null
scope: "Implement pluggable authentication (LocalAuthProvider/ClerkAuthProvider), centralized RBAC middleware, data tenancy with owner_id/visibility fields, and CLI auth flows (device code + PAT) while maintaining zero-auth local mode."
effort_estimate: "47 story points"
architecture_summary: "Database layer adds users/teams/team_members tables and owner/visibility columns. Repository layer gains TenantContext propagation. Service layer becomes auth-context-aware. API layer gains dependency-injected require_auth middleware. Frontend integrates Clerk SDK. CLI implements device code flow + PAT storage."
priority: high
risk_level: medium
category: product-planning
tags: [implementation, planning, phases, auth, rbac, tenancy, cli]
related_documents:
  - /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
  - /.claude/context/key-context/tenant-scoping-strategy.md
  - /docs/project_plans/architecture/enterprise-db-schema-v1.md
request_log_ids: ["REQ-20260306-skillmeat"]
---

# Implementation Plan: AAA & RBAC Foundation (Individual & Team)

**Plan ID**: `IMPL-2026-03-06-AAA-RBAC-FOUNDATION`
**Date**: 2026-03-06
**Author**: Implementation Planner (Haiku)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md`
- **Tenant Strategy**: `/.claude/context/key-context/tenant-scoping-strategy.md`
- **Enterprise Schema**: `/docs/project_plans/architecture/enterprise-db-schema-v1.md`

**Complexity**: Large
**Total Estimated Effort**: 47 story points
**Target Timeline**: 5-6 weeks (10 days per phase)

---

## Executive Summary

This implementation plan establishes Authentication, Authorization, and Accounting (AAA) as a foundational system across SkillMeat. Building on the enterprise database infrastructure from PRD 1, we introduce:

1. **Pluggable Auth Providers** — Abstract `AuthProvider` interface supporting both zero-auth (`LocalAuthProvider`) and JWT-based (`ClerkAuthProvider`) strategies
2. **Centralized RBAC** — Scope-based endpoint protection via FastAPI dependency injection; roles include `system_admin`, `team_admin`, `team_member`, `viewer`
3. **Data Tenancy** — All key entities gain `owner_id` (UUID), `owner_type` (user/team enum), and `visibility` (private/team/public enum) columns
4. **CLI Authentication** — Device code flow for OAuth login and PAT storage for headless environments
5. **Zero-Auth Preservation** — Local mode continues to work transparently with an elevated `local_admin` context

The plan spans 5 phases: Database layer, Middleware/Providers, Frontend identity integration, CLI authentication, and comprehensive testing. All work follows MeatyPrompts layered architecture and maintains backward compatibility with the existing zero-auth local experience.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Phase 1: Database Layer** — Define `users`, `teams`, `team_members` tables; add tenancy columns (`owner_id`, `owner_type`, `visibility`) to local models; create migration for both local and enterprise schemas
2. **Phase 2: Repository & Service Layer** — Create `AuthContext` dataclass; implement repository TenantContext propagation; update service layer to accept auth context
3. **Phase 3: Middleware & Auth Providers** — Abstract `AuthProvider` interface; implement `LocalAuthProvider` and `ClerkAuthProvider`; wire `require_auth` dependency with scope validation; update `verify_enterprise_pat()` per REQ-20260306
4. **Phase 4: API Layer** — Add `AuthContext` injection to all 30+ routers via dependency injection; phase rollout to avoid merge conflicts
5. **Phase 5: Frontend & CLI** — Clerk SDK integration in Next.js, login/signup flows, workspace switcher; CLI device code flow, credential storage, auth token injection
6. **Phase 6: Testing & Validation** — Unit tests for auth providers, integration tests for tenant isolation and RBAC, E2E flows
7. **Phase 7: Documentation** — Security docs, API docs updates, CLI auth guide
8. **Phase 8: Deployment** — Feature flags, monitoring, rollout strategy

### Parallel Work Opportunities

- **Database** and **Repository** work can be parallelized after Phase 1 migrations land (data layer expert + backend engineer)
- **Frontend SDK integration** can begin once **Service layer** is complete (UI engineer can build UI components independently)
- **Testing** infrastructure can be established concurrently with Phase 4 API layer work
- **Documentation** can be drafted during Phase 4-5, finalized in Phase 7

### Critical Path

1. Phase 1 (Database) → Phase 2 (Auth context dataclass & repository propagation) → Phase 3 (Auth providers) → Phase 4 (API injection)
   - All other work depends on Auth context being threaded through the stack
2. Phase 3 middleware → Phase 4 API rollout (30+ routers need sequential rollout to avoid conflicts)
3. Phase 5 frontend and CLI depend on Phase 3/4 to be substantially complete

**Timeline Impact**: Phases 1-2 are the gating factor (~2 weeks); Phases 3-4 (~2 weeks); Phases 5-8 (~2 weeks) can proceed in parallel.

---

## Phase Breakdown

### Phase 1: Database Layer — Authentication Schema & Tenancy Fields

**Duration**: 5 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, backend-architect

#### Goals

- Add `users`, `teams`, `team_members` tables to support multi-user identity (Phase 1 uses defaults; Phase 2 will wire to auth context)
- Add `owner_id`, `owner_type`, `visibility` columns to key local models (`Artifact`, `Collection`, `Project`, `Group`)
- Create Alembic migrations for both local (SQLite) and enterprise (PostgreSQL) schemas
- Default all existing data to `local_admin` user ID (constant UUID for local mode)

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| DB-001 | Design Auth Schema | Define users, teams, team_members, roles tables with relationships | Schema design doc with ERD; all tables have timestamps and tenant_id where applicable | 2 pts | data-layer-expert, backend-architect | None |
| DB-002 | Local Model Updates | Add owner_id, owner_type, visibility columns to Artifact, Collection, Project, Group models in cache/models.py | All models have new columns; type annotations correct; default values match enums | 3 pts | data-layer-expert | DB-001 |
| DB-003 | Enterprise Model Updates | Add same columns to enterprise_models.py (UUID PKs); ensure consistency with local models | Enterprise models mirror local tenancy; UUID types for owner_id | 2 pts | data-layer-expert | DB-001 |
| DB-004 | Local Migration | Create Alembic migration for SQLite schema (users, teams, team_members, column adds) | Migration runs cleanly; DOWN reversal works; all new columns present | 2 pts | data-layer-expert | DB-002 |
| DB-005 | Enterprise Migration | Create Alembic migration for PostgreSQL enterprise schema | Migration runs on PostgreSQL test instance; DDL is idempotent | 2 pts | data-layer-expert | DB-003 |
| DB-006 | Data Defaults | Add data migration script to populate local_admin user (UUID constant) and assign ownership to existing data | Existing artifacts default to local_admin; verified via query | 1 pt | data-layer-expert | DB-004 |
| DB-007 | Indexes & Constraints | Add indexes on owner_id, tenant_id; foreign key constraints for team_members | Query plans show index usage; constraints prevent orphaned rows | 1 pt | data-layer-expert | DB-005 |

#### Quality Gates

- [ ] Database schema validated (ERD doc reviewed)
- [ ] Local migration runs successfully on SQLite
- [ ] Enterprise migration runs successfully on PostgreSQL
- [ ] All constraints and indexes in place
- [ ] Existing data defaults to local_admin user
- [ ] Down migrations tested and work correctly

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/cache/models.py` | Add owner_id, owner_type, visibility to local models | data-layer-expert |
| `skillmeat/cache/enterprise_models.py` | Add owner_id, owner_type, visibility to enterprise models | data-layer-expert |
| `skillmeat/cache/migrations/alembic/versions/*.py` | Local and enterprise migrations | data-layer-expert |
| `skillmeat/cache/constants.py` | Add LOCAL_ADMIN_USER_ID constant (UUID) | data-layer-expert |

---

### Phase 2: Repository & Service Layer — Auth Context Definition & Propagation

**Duration**: 5 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect, data-layer-expert

#### Goals

- Define `AuthContext` dataclass with user_id, tenant_id, roles, scopes
- Implement RBAC role enum and scope constants
- Create `TenantContext` ContextVar for implicit tenant_id threading (used by enterprise repos)
- Update repository layer to accept tenant_id parameter
- Wire service layer to propagate auth context to repositories
- Ensure backward compatibility: when no auth context present, default to local_admin/DEFAULT_TENANT_ID

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| SVR-001 | AuthContext Dataclass | Create frozen dataclass with user_id, tenant_id, roles (list[str]), scopes (list[str]) | Dataclass is immutable; __init__ validates required fields; imports work in routers/services | 1 pt | python-backend-engineer | None |
| SVR-002 | RBAC Enums | Define Role enum (system_admin, team_admin, team_member, viewer) and Scope enum (artifact:read, artifact:write, collection:read, etc.) | Enums cover all endpoints; scope naming is consistent (resource:action); can serialize to JSON | 1 pt | python-backend-engineer | None |
| SVR-003 | TenantContext ContextVar | Create ContextVar for tenant_id in enterprise_repositories.py; add set_tenant_context() helper | ContextVar used by all enterprise repo methods; graceful fallback to DEFAULT_TENANT_ID | 1 pt | data-layer-expert | None |
| SVR-004 | Repository Layer Auth | Update IArtifactRepository, ICollectionRepository interfaces to accept optional auth_context parameter | Interface signatures updated; all implementations support auth_context injection | 2 pts | python-backend-engineer, backend-architect | SVR-001 |
| SVR-005 | Local Repository Auth | Update local repository implementations to validate owner_id against auth context (negative: reject write if owner doesn't match) | Repo methods accept auth_context; enforce owner checks; unit tests verify rejection | 2 pts | python-backend-engineer | SVR-004 |
| SVR-006 | Enterprise Repository Auth | Update enterprise repository implementations to enforce tenant_id filtering and owner_id checks | Enterprise repos filter by tenant_id + owner_id; TenantContext ContextVar used implicitly | 2 pts | python-backend-engineer, data-layer-expert | SVR-004 |
| SVR-007 | Service Layer Auth | Update artifact/collection services to accept AuthContext, thread to repositories | Services accept auth_context param; pass to repository calls; default to local_admin in local mode | 2 pts | backend-architect | SVR-001, SVR-004 |
| SVR-008 | DTO Updates | Add owner_id, owner_type, visibility to request/response DTOs | DTOs serialize/deserialize new fields; validation includes enum checks | 2 pts | python-backend-engineer | SVR-001 |

#### Quality Gates

- [ ] AuthContext dataclass compiles and validates
- [ ] RBAC enums define all required roles and scopes
- [ ] TenantContext ContextVar threads through enterprise repos
- [ ] Repository interfaces updated with auth_context param
- [ ] Service layer accepts and propagates auth_context
- [ ] DTOs include new fields with validation
- [ ] Unit tests for auth context validation pass
- [ ] Zero-auth local mode still works without auth_context

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/api/schemas/auth.py` (new) | AuthContext, Role, Scope definitions | python-backend-engineer |
| `skillmeat/cache/enterprise_repositories.py` | TenantContext ContextVar, tenant_id filtering | data-layer-expert |
| `skillmeat/core/interfaces/repositories.py` | Update IArtifactRepository, ICollectionRepository with auth_context param | python-backend-engineer |
| `skillmeat/core/repositories/local_*.py` | Add auth_context param, owner_id validation | python-backend-engineer |
| `skillmeat/cache/enterprise_repositories.py` | Add auth_context param, owner_id + tenant_id validation | data-layer-expert |
| `skillmeat/core/services/artifact_service.py`, `collection_service.py` | Accept AuthContext, thread to repos | backend-architect |
| `skillmeat/api/schemas/artifacts.py`, `collections.py` | Add owner_id, owner_type, visibility to DTOs | python-backend-engineer |

---

### Phase 3: Middleware & Auth Providers — Pluggable Authentication

**Duration**: 5 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: backend-architect, python-backend-engineer

#### Goals

- Create abstract `AuthProvider` interface with `validate()` method returning `AuthContext`
- Implement `LocalAuthProvider` returning static `local_admin` context (zero-auth transparent)
- Implement `ClerkAuthProvider` validating Clerk JWTs and mapping claims to `AuthContext`
- Build `require_auth` FastAPI dependency with optional scope validation
- Update `verify_enterprise_pat()` per REQ-20260306 to return `AuthContext` instead of bare token
- Wire `TenantContext` from `AuthContext` before service layer execution
- Add auth provider selection logic (env: SKILLMEAT_AUTH_PROVIDER)

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| AUTH-001 | Abstract AuthProvider | Create ABC with validate(request) -> AuthContext method; handle missing auth gracefully | ABC has validate() signature; subclass pattern clear; error handling documented | 1 pt | backend-architect | SVR-001 |
| AUTH-002 | LocalAuthProvider | Return fixed local_admin AuthContext with system_admin role and all scopes | LocalAuthProvider always succeeds; returns consistent local_admin context; zero-auth preserved | 1 pt | python-backend-engineer | AUTH-001 |
| AUTH-003 | ClerkAuthProvider | Validate Clerk JWT in Authorization header; map org_id -> tenant_id, user_id -> user_id, roles -> roles | JWT validation works; claims mapping tested; invalid JWTs raise 401; rate-limit-safe | 3 pts | backend-architect, python-backend-engineer | AUTH-001 |
| AUTH-004 | require_auth Dependency | Create FastAPI dependency that calls AuthProvider.validate(); optionally checks scopes | Dependency injects AuthContext into routers; scope validation works; missing auth returns 401 | 2 pts | python-backend-engineer | AUTH-001 |
| AUTH-005 | PAT Return Type Update | Refactor verify_enterprise_pat() to return AuthContext instead of bare token string | Per REQ-20260306: PAT validation returns structured AuthContext with tenant_id, user_id | 2 pts | python-backend-engineer | SVR-001 |
| AUTH-006 | TenantContext Middleware | Create middleware or pre-request hook that extracts tenant_id from AuthContext and sets TenantContext ContextVar | Per REQ-20260306: TenantContext set before service layer; _get_content_service() uses it | 2 pts | backend-architect | AUTH-004, SVR-003 |
| AUTH-007 | Provider Configuration | Load SKILLMEAT_AUTH_PROVIDER env var; instantiate appropriate provider at startup | Config wiring in APISettings; provider injected via DI; testable via env override | 1 pt | python-backend-engineer | AUTH-001 |
| AUTH-008 | Unit Tests — Providers | Test LocalAuthProvider always succeeds; ClerkAuthProvider validates JWT; invalid tokens raise 401 | All unit tests pass; 90%+ coverage of auth provider logic | 2 pts | python-backend-engineer | AUTH-002, AUTH-003 |

#### Quality Gates

- [ ] AuthProvider ABC compiles and is documented
- [ ] LocalAuthProvider returns consistent local_admin context
- [ ] ClerkAuthProvider validates JWTs and maps claims
- [ ] require_auth dependency injects AuthContext correctly
- [ ] verify_enterprise_pat() returns AuthContext (REQ-20260306)
- [ ] TenantContext is set before service layer execution (REQ-20260306)
- [ ] Auth provider selected via SKILLMEAT_AUTH_PROVIDER env var
- [ ] Unit tests for auth providers pass
- [ ] Zero-auth mode still works transparently

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/api/auth/provider.py` (new) | AuthProvider ABC | backend-architect |
| `skillmeat/api/auth/local_provider.py` (new) | LocalAuthProvider implementation | python-backend-engineer |
| `skillmeat/api/auth/clerk_provider.py` (new) | ClerkAuthProvider implementation | backend-architect |
| `skillmeat/api/dependencies.py` | Add require_auth dependency; instantiate auth provider from config | python-backend-engineer |
| `skillmeat/api/middleware/enterprise_auth.py` | Refactor verify_enterprise_pat() to return AuthContext; add TenantContext middleware | python-backend-engineer |
| `skillmeat/api/config.py` | Add SKILLMEAT_AUTH_PROVIDER setting | python-backend-engineer |
| `skillmeat/api/tests/test_auth_providers.py` (new) | Unit tests for providers | python-backend-engineer |

---

### Phase 4: API Layer — Auth Injection & Endpoint Protection

**Duration**: 8 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

#### Goals

- Add `require_auth` dependency to all 30+ API routers for endpoint protection
- Implement scope validation for critical endpoints (artifact:write, collection:write, etc.)
- Update request handlers to receive AuthContext and pass to services
- Ensure OpenAPI documentation reflects auth requirements
- Phased rollout: critical endpoints first (artifacts, collections), then supporting endpoints (tags, groups, etc.)
- Verify zero-auth local mode still works without requiring auth header

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| API-001 | Critical Routers Auth (Batch 1) | Add require_auth to artifacts, collections, projects routers; scope validation for write ops | Batch 1 routers protected; valid auth passes; missing auth returns 401; local mode works | 4 pts | python-backend-engineer | AUTH-004 |
| API-002 | Supporting Routers Auth (Batch 2) | Add require_auth to deployments, groups, tags, versions, bundles routers | Batch 2 routers protected; scope validation consistent | 3 pts | python-backend-engineer | API-001 |
| API-003 | Marketplace & Content Routers Auth (Batch 3) | Add require_auth to marketplace, marketplace-sources, marketplace-catalog, context-sync routers | Batch 3 routers protected | 2 pts | python-backend-engineer | API-002 |
| API-004 | Health & Utility Routers (No Auth) | Ensure health, cache, settings routers remain auth-free (public endpoints) | Health and public endpoints don't require auth; verify 200 responses without header | 1 pt | python-backend-engineer | API-003 |
| API-005 | Router Signatures | Update all router function signatures to accept AuthContext param; thread to service calls | All routers receive auth_context via dependency; pass to service layer | 3 pts | python-backend-engineer | API-001 |
| API-006 | OpenAPI Documentation | Add auth requirements to OpenAPI schema; document scopes and roles | OpenAPI /docs reflects Bearer token requirement; scope names documented | 1 pt | api-documenter | API-005 |
| API-007 | Scope Validation Tests | Create integration tests for each protected endpoint with valid/invalid auth and scopes | All endpoints tested; scope validation works; invalid scopes return 403 | 2 pts | python-backend-engineer | API-005 |
| API-008 | Zero-Auth Verification | Verify local mode works without auth header; LocalAuthProvider injects silently | Running with SKILLMEAT_AUTH_PROVIDER=local, endpoints work without Authorization header | 1 pt | python-backend-engineer | API-001 |

#### Quality Gates

- [ ] All 30+ routers have require_auth or are explicitly marked public
- [ ] Write endpoints validate scopes (artifact:write, collection:write)
- [ ] AuthContext threaded through all router → service calls
- [ ] OpenAPI documentation reflects auth requirements
- [ ] Phased rollout completed without merge conflicts
- [ ] Integration tests for protected endpoints pass
- [ ] Local zero-auth mode works transparently
- [ ] 401/403 error responses are consistent

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/api/routers/artifacts.py` | Add require_auth, scope validation; update signatures | python-backend-engineer |
| `skillmeat/api/routers/collections.py` | Add require_auth, scope validation | python-backend-engineer |
| `skillmeat/api/routers/projects.py` | Add require_auth | python-backend-engineer |
| `skillmeat/api/routers/[all other].py` | Batch 2-3 routers: add require_auth | python-backend-engineer |
| `skillmeat/api/openapi.py` | Update security schemes and documentation | api-documenter |
| `skillmeat/api/tests/test_auth_api.py` (new) | Integration tests for protected endpoints | python-backend-engineer |

---

### Phase 5: Frontend Identity Integration — Clerk SDK & UI

**Duration**: 6 days
**Dependencies**: Phase 4 mostly complete (API can be in-progress)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

#### Goals

- Integrate Clerk SDK into Next.js app for user authentication
- Build Login and Signup pages with Clerk components
- Implement Workspace Switcher component for toggling Personal vs Team contexts
- Add auth token to API client headers (fetch, axios)
- Protect client-side routes with Clerk middleware
- Build user profile/settings page showing current user and teams
- Maintain zero-auth local mode: no Clerk init when NEXT_PUBLIC_AUTH_ENABLED=false

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| FE-001 | Clerk SDK Setup | Install @clerk/nextjs; add ClerkProvider to app root; configure public/sign-in paths | ClerkProvider wraps app; Clerk middleware configured; env vars set | 1 pt | ui-engineer-enhanced | API-001 |
| FE-002 | Login/Signup Pages | Create pages/login and pages/signup using Clerk components; route /auth to Clerk | Login/signup pages render; form submission works; redirects on success | 2 pts | frontend-developer | FE-001 |
| FE-003 | Workspace Switcher Component | Build component showing personal workspace and team workspaces; switching updates auth context (Clerk organizationId) | Component lists user's orgs; org switch updates context; reflected in subsequent API calls | 2 pts | ui-engineer-enhanced | FE-001 |
| FE-004 | Auth Token Injection | Update API client (fetch/axios wrapper) to inject Clerk auth token in Authorization header | All API requests include Authorization: Bearer <token>; token refreshes automatically | 1 pt | frontend-developer | FE-001 |
| FE-005 | Route Protection | Implement Clerk middleware to protect authenticated routes; redirect unauthenticated users to /login | Protected routes require auth; unauthenticated access redirected | 1 pt | frontend-developer | FE-001 |
| FE-006 | User Profile Page | Create settings page showing current user info, teams, role, logout button | Profile page displays user/team info; logout works; team list accurate | 1 pt | ui-engineer-enhanced | FE-002 |
| FE-007 | Zero-Auth Mode | Add NEXT_PUBLIC_AUTH_ENABLED env var; conditionally skip Clerk init in local mode | Local mode works without Clerk; no auth required; feature flag controls behavior | 1 pt | frontend-developer | FE-001 |
| FE-008 | E2E Auth Flow Tests | Create Playwright tests for login, signup, workspace switch, API calls with auth | E2E tests verify complete auth flow; token injection verified | 2 pts | frontend-developer | FE-004, FE-006 |

#### Quality Gates

- [ ] Clerk SDK integrated successfully
- [ ] Login and signup pages functional
- [ ] Workspace switcher works
- [ ] Auth token injected into all API calls
- [ ] Protected routes redirect unauthenticated users
- [ ] User profile page displays correctly
- [ ] Zero-auth local mode works without Clerk
- [ ] E2E auth flow tests pass

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/web/app/layout.tsx` | Add ClerkProvider | ui-engineer-enhanced |
| `skillmeat/web/app/auth/login/page.tsx` (new) | Login page | frontend-developer |
| `skillmeat/web/app/auth/signup/page.tsx` (new) | Signup page | frontend-developer |
| `skillmeat/web/components/workspace-switcher.tsx` (new) | Workspace switcher component | ui-engineer-enhanced |
| `skillmeat/web/lib/api-client.ts` | Update to inject auth token | frontend-developer |
| `skillmeat/web/middleware.ts` | Add Clerk auth middleware | frontend-developer |
| `skillmeat/web/app/settings/page.tsx` (new) | User profile/settings page | ui-engineer-enhanced |
| `skillmeat/web/tests/auth.e2e.ts` (new) | E2E auth tests | frontend-developer |
| `.env.local` | Add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY etc. | frontend-developer |

---

### Phase 6: CLI Authentication — Device Code Flow & Credential Storage

**Duration**: 5 days
**Dependencies**: Phase 3 complete (auth providers)
**Assigned Subagent(s)**: python-backend-engineer

#### Goals

- Implement `skillmeat login` command using OAuth device code flow
- Implement `skillmeat auth --token <PAT>` for headless PAT authentication
- Build local credential storage (encrypted file or system keyring)
- Add auth token injection to CLI HTTP requests (to API or marketplace)
- Update existing CLI commands to use auth context where needed
- Maintain zero-auth backward compatibility: CLI works without login in local mode

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| CLI-001 | Device Code Flow | Implement OAuth device code flow for `skillmeat login`; handle polling and timeout | User runs `skillmeat login`; shown device code and URL; polls until authorized; token stored | 3 pts | python-backend-engineer | AUTH-003 |
| CLI-002 | Credential Storage | Implement secure credential storage (keyring or encrypted file) for auth token | Credentials stored securely; token retrieved on demand; ~/.skillmeat/credentials protected | 2 pts | python-backend-engineer | CLI-001 |
| CLI-003 | Auth Command | Implement `skillmeat auth --token <PAT>` for direct PAT input (headless) | Command accepts PAT; validates against server; stores token | 1 pt | python-backend-engineer | CLI-002 |
| CLI-004 | Token Refresh | Implement token refresh logic for expired JWTs; refresh tokens stored alongside access tokens | Expired tokens refreshed automatically; user not interrupted | 1 pt | python-backend-engineer | CLI-002 |
| CLI-005 | HTTP Client Integration | Update CLI HTTP client (requests library wrapper) to inject auth token into requests | All CLI HTTP calls include Authorization header; no auth required in local mode | 1 pt | python-backend-engineer | CLI-002 |
| CLI-006 | Logout Command | Implement `skillmeat logout` to clear stored credentials | User runs `skillmeat logout`; credentials cleared; next command requires login | 1 pt | python-backend-engineer | CLI-002 |
| CLI-007 | Zero-Auth Verification | Verify CLI works without login in local mode; `SKILLMEAT_ENV=local` bypasses auth | Running locally, CLI works without `skillmeat login` prerequisite | 1 pt | python-backend-engineer | CLI-001 |
| CLI-008 | CLI Integration Tests | Test device code flow (mocked), PAT input, credential storage, token injection | Integration tests pass; mocked Clerk endpoint works | 1 pt | python-backend-engineer | CLI-005 |

#### Quality Gates

- [ ] Device code flow works end-to-end (can test with mock Clerk endpoint)
- [ ] Credentials stored securely (encrypted or keyring)
- [ ] `skillmeat auth --token <PAT>` works
- [ ] Token refresh works for expired JWTs
- [ ] Auth token injected into all CLI HTTP requests
- [ ] `skillmeat logout` clears credentials
- [ ] Local zero-auth mode works without login
- [ ] Integration tests pass

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/cli/commands/auth.py` (new) | login, auth, logout commands | python-backend-engineer |
| `skillmeat/cli/auth_flow.py` (new) | Device code flow implementation | python-backend-engineer |
| `skillmeat/cli/credential_store.py` (new) | Secure credential storage | python-backend-engineer |
| `skillmeat/cli/http_client.py` | Update to inject auth token | python-backend-engineer |
| `skillmeat/cli.py` | Register auth commands | python-backend-engineer |
| `skillmeat/cli/tests/test_auth_flow.py` (new) | Integration tests for auth | python-backend-engineer |

---

### Phase 7: Testing & Validation — Auth & RBAC Coverage

**Duration**: 5 days
**Dependencies**: Phases 1-6 complete
**Assigned Subagent(s)**: python-backend-engineer, frontend-developer, testing specialist

#### Goals

- Unit tests for auth providers, RBAC validation, scope checking
- Integration tests for tenant isolation (negative assertions: tenant A cannot see tenant B data)
- Component tests for Clerk integration, workspace switcher
- E2E tests for complete auth flows (login, API calls, logout)
- Security tests for edge cases (invalid tokens, scope bypass attempts, owner mismatch)
- Verify zero-auth mode still works

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| TEST-001 | Auth Provider Unit Tests | Test LocalAuthProvider, ClerkAuthProvider with valid/invalid inputs | All unit tests pass; 95%+ coverage of auth logic; no side effects | 2 pts | python-backend-engineer | AUTH-001, AUTH-003 |
| TEST-002 | RBAC Scope Tests | Test require_auth dependency with various scopes; verify scope validation | Endpoint rejects valid user with insufficient scope; returns 403 | 2 pts | python-backend-engineer | AUTH-004 |
| TEST-003 | Tenant Isolation Tests | Integration tests verifying tenant A data isolation; negative assertions | Queries for tenant B return empty; cross-tenant writes rejected | 2 pts | python-backend-engineer | SVR-006 |
| TEST-004 | Owner Validation Tests | Test owner_id checks; verify users can't modify others' artifacts | Users can only modify own artifacts/collections; cross-owner writes rejected | 2 pts | python-backend-engineer | SVR-005 |
| TEST-005 | Frontend Auth Tests | Component tests for Clerk integration, workspace switcher, token injection | Clerk components render; org switch works; API client includes token | 2 pts | frontend-developer | FE-001, FE-004 |
| TEST-006 | E2E Auth Flow | Playwright tests for complete login → API call → logout flow | E2E tests verify full workflow; token injection verified in network tab | 2 pts | frontend-developer | FE-002, FE-005 |
| TEST-007 | CLI Auth Tests | Integration tests for device code flow (mocked), PAT input, token storage | CLI auth flow works with mock Clerk; credentials stored securely | 1 pt | python-backend-engineer | CLI-001, CLI-005 |
| TEST-008 | Security Edge Cases | Test invalid token rejection, expired token handling, scope bypass attempts | All edge cases handled; no auth bypass possible; errors logged | 2 pts | python-backend-engineer | AUTH-003 |
| TEST-009 | Zero-Auth Regression | Verify local mode works without auth; endpoints accessible without header | Local mode still works transparently; no breaking changes | 1 pt | python-backend-engineer | API-008 |

#### Quality Gates

- [ ] Auth provider unit tests: 95%+ coverage
- [ ] RBAC scope validation tests pass
- [ ] Tenant isolation tests pass (negative assertions)
- [ ] Owner validation tests pass
- [ ] Frontend component tests pass
- [ ] E2E auth flow tests pass
- [ ] CLI auth integration tests pass
- [ ] Security edge case tests pass
- [ ] Zero-auth mode regression tests pass
- [ ] Overall code coverage >85%

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `skillmeat/api/tests/test_auth_providers.py` | Unit tests for auth providers | python-backend-engineer |
| `skillmeat/api/tests/test_rbac_scopes.py` (new) | RBAC scope validation tests | python-backend-engineer |
| `skillmeat/cache/tests/test_tenant_isolation.py` (new) | Tenant isolation integration tests | python-backend-engineer |
| `skillmeat/cache/tests/test_owner_validation.py` (new) | Owner validation tests | python-backend-engineer |
| `skillmeat/web/tests/auth.test.tsx` (new) | Frontend auth component tests | frontend-developer |
| `skillmeat/web/tests/auth.e2e.ts` | E2E auth flow tests | frontend-developer |
| `skillmeat/cli/tests/test_auth_flow.py` | CLI auth integration tests | python-backend-engineer |
| `skillmeat/tests/test_security_edge_cases.py` (new) | Security edge case tests | python-backend-engineer |

---

### Phase 8: Documentation & Deployment

**Duration**: 4 days
**Dependencies**: Phases 1-7 complete
**Assigned Subagent(s)**: documentation-writer, documentation-complex, backend-architect

#### Goals

- Update API documentation with auth requirements and scopes
- Write security documentation (auth flows, scope definitions, tenant isolation model)
- Write CLI authentication guide (login, PAT setup, credential management)
- Update developer guide with auth context propagation pattern
- Create migration guide for upgrading from zero-auth to authenticated mode
- Set up feature flags for gradual auth rollout
- Add monitoring and alerting for auth failures

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| DOC-001 | API Documentation | Update OpenAPI docs with auth requirements, scope definitions, example auth headers | OpenAPI shows Bearer token requirement; scope list documented; examples correct | 1 pt | api-documenter | API-006 |
| DOC-002 | Security Guide | Document auth architecture, role/scope model, tenant isolation guarantees | Guide covers LocalAuthProvider, ClerkAuthProvider, RBAC model, data isolation | 2 pts | documentation-complex | AUTH-001, SVR-002 |
| DOC-003 | CLI Auth Guide | Document `skillmeat login`, `skillmeat auth --token`, credential storage, logout | Guide includes step-by-step login flow, headless PAT setup, troubleshooting | 1 pt | documentation-writer | CLI-001, CLI-003 |
| DOC-004 | Developer Auth Guide | Document AuthContext propagation, writing auth-aware services/routers, testing patterns | Developers can add auth to new endpoints; pattern is clear | 1 pt | documentation-writer | SVR-001, API-005 |
| DOC-005 | Migration Guide | Document upgrading from zero-auth local mode to authenticated mode | Guide covers env var changes, existing data defaults, role assignment | 1 pt | documentation-writer | DB-006 |
| DOC-006 | Deployment Guide | Document feature flags for gradual rollout, monitoring auth failures, alerting setup | Deployment team can safely roll out by endpoint | 1 pt | documentation-complex | DEPLOY-001 |

#### Quality Gates

- [ ] API documentation complete and accurate
- [ ] Security guide covers all auth scenarios
- [ ] CLI authentication guide is step-by-step and clear
- [ ] Developer guide enables independent endpoint addition
- [ ] Migration guide covers local → authenticated transition
- [ ] Deployment guide enables safe rollout
- [ ] All docs reviewed and approved

#### Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `docs/guides/api/authentication.md` (new) | API auth guide | api-documenter |
| `docs/guides/security/rbac-model.md` (new) | Security and RBAC documentation | documentation-complex |
| `docs/guides/cli/authentication.md` (new) | CLI auth guide | documentation-writer |
| `docs/guides/developer/auth-patterns.md` (new) | Developer auth patterns guide | documentation-writer |
| `docs/guides/deployment/auth-rollout.md` (new) | Deployment and rollout guide | documentation-complex |
| `docs/migration/zero-auth-to-authenticated.md` (new) | Migration guide | documentation-writer |
| `skillmeat/api/openapi.json` | Updated with auth requirements | api-documenter |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Auth context threading complexity | High | Medium | Early phase gates and integration tests; simplify with TenantContext ContextVar pattern |
| Clerk JWT validation latency | Medium | Low | Implement token caching; profile with real workloads; add timeout fallbacks |
| 30+ router changes cause merge conflicts | High | High | Phase rollout (3 batches) in Phase 4; each batch <15 minutes; PR reviews sequential |
| Local mode regression (zero-auth broken) | Critical | Low | LocalAuthProvider unit tests + integration tests; Phase 1 API-008 verification gates |
| Tenant isolation leaks data | Critical | Low | Negative assertion tests in Phase 7; mandatory `tenant_id` filter in all enterprise queries |
| Owner ID validation bypassed | High | Low | Code review checklist; unit tests for owner mismatch; security tests in Phase 7 |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Database migrations take longer than expected | Medium | Medium | Pre-test migrations on PostgreSQL staging; parallel migration development (local + enterprise) |
| Clerk JWT claims mapping incorrect | Medium | Low | Coordinate with Clerk documentation early; test with sandbox org |
| Frontend integration slower than estimated | Medium | Medium | Parallelize UI work with backend; unblock with mock API responses |
| CLI device code flow UX issues | Low | Medium | Prototype with sample Clerk app; iterate based on testing feedback |

### Resource Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Backend engineer context switching | Medium | High | Assign one primary backend engineer to orchestrate; minimize context switches |
| Frontend engineer unavailable | Medium | Medium | Frontend work can proceed in parallel after Phase 4; contingency: defer to Phase 6 |
| Unclear Clerk integration details | Medium | Low | Schedule Clerk integration call early; document assumptions in Phase 2 |

---

## Resource Requirements

### Team Composition

| Role | FTE | Phases | Notes |
|------|-----|--------|-------|
| Data Layer Expert | 1.0 | 1-2, 7-8 | Database schema, migrations, enterprise repos |
| Python Backend Engineer | 1.0 | 1-8 | Orchestration; critical path owner; routers, services, CLI |
| Backend Architect | 0.5 | 1-4, 7-8 | Design review; auth providers; service layer; deployment |
| UI Engineer (Enhanced) | 0.5 | 5-8 | Frontend components, workspace switcher |
| Frontend Developer | 0.5 | 5, 6-8 | Login/signup pages, routing, E2E tests |
| API Documenter | 0.25 | 4, 8 | OpenAPI updates, API docs |
| Documentation Writer | 0.5 | 7-8 | Security, CLI, developer guides |
| Testing Specialist | 0.5 | 6-7 | Test strategy, integration/E2E testing |

### Skill Requirements

- Backend: FastAPI, SQLAlchemy, Alembic, JWT validation
- Frontend: Next.js, Clerk SDK, React Testing Library, Playwright
- Database: PostgreSQL, SQLite, migrations
- Security: OAuth flows, JWT, RBAC design, tenant isolation patterns

### Infrastructure

- PostgreSQL test instance for enterprise migrations
- Clerk sandbox org for JWT testing
- GitHub Actions for CI/CD (existing)
- Staging environment for canary rollout

---

## Success Metrics

### Delivery Metrics
- On-time phase completion (±2 days per phase)
- Zero P0 auth-related bugs in first week post-launch
- All tests passing (>85% coverage)
- Local zero-auth mode working transparently

### Business Metrics
- Users can log in and access personal/team workspaces
- RBAC scopes correctly enforce permissions
- Tenant isolation holds (no cross-tenant data leaks)
- CLI auth flow < 2 minutes from `skillmeat login` to authenticated

### Technical Metrics
- AuthContext threaded through all layers
- 100% of write endpoints protected with scope validation
- Integration tests verify tenant isolation (negative assertions)
- Zero regressions in local mode
- API documentation complete

---

## Communication Plan

- **Daily standups**: 15min, async Slack updates on blockers
- **Phase gates**: Review meeting at end of each phase (1-2 hours)
- **Weekly sync**: Architect + leads, Tuesday 10am PT
- **Risk escalation**: Immediate Slack notification for blockers
- **Stakeholder updates**: Bi-weekly summary (Fridays)

---

## Post-Implementation

### Monitoring & Alerting

- Track auth failure rates (401/403 responses)
- Monitor token validation latency (p50, p95, p99)
- Alert on tenant isolation anomalies (cross-tenant queries)
- Log all auth decisions for audit trail

### Iteration Plan

- **Week 1 post-launch**: Gather user feedback on login UX
- **Week 2**: Address any auth provider issues with Clerk
- **Week 3**: Performance optimization if needed (token caching, JWT size)
- **Month 2**: RBAC role enhancements based on user requests
- **Month 3+**: RLS (Row Level Security) in PostgreSQL (Phase 3 of tenant strategy)

### Technical Debt

- Phase 3+: Implement PostgreSQL RLS policies for defense-in-depth
- Consider OAuth token signing to prevent JWT tampering
- Implement audit logging for all auth decisions
- Add metrics dashboard for auth performance

---

## Appendix: Phased Rollout Schedule (Example)

Assuming 1.5-2 week sprints:

| Week | Phase | Milestones |
|------|-------|-----------|
| Week 1-2 | Phase 1: Database | Schema finalized, migrations tested |
| Week 2-3 | Phase 2: Auth Context | AuthContext dataclass, repos updated, tests passing |
| Week 3-4 | Phase 3: Auth Providers | LocalAuthProvider & ClerkAuthProvider working, middleware wired |
| Week 4-5 | Phase 4: API Injection | Batch 1 routers protected; Batch 2-3 in progress |
| Week 5-6 | Phase 5: Frontend | Clerk SDK integrated, login/signup working, workspace switcher UI |
| Week 6-7 | Phase 6: CLI Auth | Device code flow working, credential storage implemented |
| Week 7-8 | Phase 7: Testing | Integration tests written, tenant isolation verified, E2E flows passing |
| Week 8-9 | Phase 8: Docs & Deploy | Documentation complete, feature flags set up, canary rollout |

**Total**: 8-9 weeks (2 weeks per phase, some overlap)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-06
**Status**: Draft (awaiting review and approval)

---

**See Also**:
- `.claude/progress/aaa-rbac-foundation/all-phases-progress.md` (progress tracking, created during Phase 1 kickoff)
