---
title: 'Addendum: Architecture Review Findings — AAA & RBAC Foundation'
schema_version: 2
doc_type: implementation_plan
status: completed
created: 2026-03-07
updated: 2026-03-07
feature_slug: aaa-rbac-foundation
feature_version: v1
parent_plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
scope: Address security gaps and enterprise readiness issues identified during post-Phase-3
  architecture review. Items are tagged to the original plan's phases for integration.
priority: high
risk_level: high
category: product-planning
tags:
- addendum
- security
- architecture-review
- auth
- rbac
- tenancy
review_source: Post-Phase-3 architecture review (lead-architect + karen agents, 2026-03-07)
---
## Context

After completing Phases 1-3 of the AAA & RBAC Foundation plan, a comprehensive architecture review was conducted by two independent reviewers:

- **lead-architect**: Enterprise auth pattern correctness, scalability, security gaps, extensibility
- **karen**: Reality-check validation of actual implementation vs claimed completeness

This addendum captures the actionable findings as tasks tagged to the appropriate phases of the original plan. Items are prioritized P0-P3, where P0 items are security-critical and should be addressed before the dependent phase ships.

---

## Finding Categories

| Category | Count | Phases Affected |
|----------|-------|-----------------|
| P0 — Security (must-fix) | 2 | Phase 4 (pre-wiring) |
| P0 — Wiring (integration) | 3 | Phase 4 |
| P1 — Enterprise readiness | 4 | Phase 4, Phase 6 |
| P2 — Design improvements | 5 | Phase 4, Phase 5+ |
| P3 — Future enhancements | 5 | Phase 6+ |

---

## P0 — Security Fixes (Tag to Phase 4, execute before router wiring)

These MUST be completed before `require_auth` is added to any router in Phase 4.

### SEC-001: Add `aud` (audience) Claim Validation to Clerk JWT

**Source**: lead-architect finding C1
**File**: `skillmeat/api/auth/clerk_provider.py` (lines ~307-313)
**Risk**: Privilege escalation — a valid Clerk JWT issued for a *different* application on the same Clerk instance would be accepted by SkillMeat.

**Change Required**:
```python
jwt.decode(
    raw_token,
    signing_key.key,
    algorithms=_SUPPORTED_ALGORITHMS,
    audience=self._expected_audience,  # new: from config
    options={"require": ["sub", "exp", "iat", "aud"]},
)
```

**Acceptance Criteria**:
- `ClerkAuthProvider.__init__` accepts `audience: str` parameter (sourced from config)
- `jwt.decode()` validates `aud` claim matches expected audience
- Tokens with wrong `aud` are rejected with 401
- Unit test added: `test_clerk_provider_rejects_wrong_audience`

**Config Addition**: Add `clerk_audience: str | None` to `APISettings` (env: `CLERK_AUDIENCE` / `SKILLMEAT_CLERK_AUDIENCE`)

**Estimate**: 1 pt
**Assigned To**: python-backend-engineer

---

### SEC-002: Wire `iss` (issuer) Claim Validation Using Existing Config

**Source**: lead-architect finding C2
**File**: `skillmeat/api/auth/clerk_provider.py` (lines ~307-313)
**Risk**: Token forgery — tokens from any Clerk deployment (not just the configured one) could pass validation if the JWKS endpoint happened to serve a matching public key.

**Change Required**:
```python
jwt.decode(
    ...,
    issuer=self._expected_issuer,  # new: from clerk_issuer config
    options={"require": ["sub", "exp", "iat", "aud", "iss"]},
)
```

**Acceptance Criteria**:
- `ClerkAuthProvider.__init__` accepts `issuer: str | None` parameter
- When set, `jwt.decode()` validates `iss` claim matches expected issuer
- Tokens with wrong `iss` are rejected with 401
- Unit test added: `test_clerk_provider_rejects_wrong_issuer`

**Note**: `clerk_issuer` config field already exists in `APISettings` (added in AUTH-007). This task wires it into the provider.

**Estimate**: 1 pt
**Assigned To**: python-backend-engineer

---

## P0 — Wiring Gaps (Tag to Phase 4, Batch 0 — before API-001)

These are infrastructure-consumer connections that must exist before router protection is meaningful.

### WIRE-001: Instantiate Auth Provider in server.py Lifespan

**Source**: karen finding G1, G5
**File**: `skillmeat/api/server.py` (lifespan function)
**Risk**: Without this, `require_auth` returns 503 on every request — the entire auth system is inert.

**Change Required**:
- In the `lifespan` async context manager, read `settings.auth_provider`
- Instantiate `LocalAuthProvider` or `ClerkAuthProvider` based on config value
- Call `set_auth_provider(provider)` from `skillmeat.api.dependencies`
- Log which provider is active at startup

**Acceptance Criteria**:
- `SKILLMEAT_AUTH_PROVIDER=local` → LocalAuthProvider instantiated and logged
- `SKILLMEAT_AUTH_PROVIDER=clerk` → ClerkAuthProvider instantiated with JWKS URL from config
- Invalid provider value → startup failure with clear error message
- `get_auth_provider()` returns the configured provider after startup

**Estimate**: 2 pts
**Assigned To**: python-backend-engineer
**Dependencies**: SEC-001, SEC-002 (provider must have aud/iss validation before instantiation)

---

### WIRE-002: Register TenantContext Dependency on Enterprise Routers

**Source**: karen finding G3
**File**: `skillmeat/api/server.py` or router-level `dependencies=[]`
**Risk**: Without this, TenantContext ContextVar is never set — enterprise repos fall back to DEFAULT_TENANT_ID on every request.

**Change Required**:
- Register `set_tenant_context_dep` as a dependency (app-level or router-level)
- Follow the registration pattern documented in `skillmeat/api/middleware/tenant_context.py` (lines ~149-174)

**Acceptance Criteria**:
- Enterprise requests set TenantContext from AuthContext.tenant_id
- Local mode requests skip TenantContext (no-op path)
- ContextVar is properly reset after each request (no tenant leakage)

**Estimate**: 1 pt
**Assigned To**: python-backend-engineer
**Dependencies**: WIRE-001

---

### WIRE-003: Set request.state.auth_context in require_auth

**Source**: lead-architect finding I5
**File**: `skillmeat/api/dependencies.py` (require_auth `_dependency` function)
**Risk**: Observability gap — logging middleware, error handlers, and audit trail cannot access auth context.

**Change Required**:
```python
async def _dependency(request: Request) -> AuthContext:
    provider = get_auth_provider()
    auth_context = await provider.validate(request)
    request.state.auth_context = auth_context  # ADD THIS
    # ... scope validation ...
    return auth_context
```

**Acceptance Criteria**:
- `request.state.auth_context` is set after successful auth
- Middleware and error handlers can read `request.state.auth_context`
- Unit test verifies `request.state` is populated

**Estimate**: 0.5 pt
**Assigned To**: python-backend-engineer

---

## P1 — Enterprise Readiness (Tag to Phase 4 / Phase 6)

### ENT-001: Secure-by-Default Route Protection (Phase 4)

**Source**: lead-architect finding I6
**Risk**: Security regression — new routes added without `require_auth` are silently unprotected.

**Recommendation**: Apply `require_auth()` as a default dependency at the app level or on a parent router, then explicitly exclude public routes (health, cache refresh, public marketplace endpoints) using dependency overrides or separate router groups.

**Implementation Options**:
1. `app = FastAPI(dependencies=[Depends(require_auth())])` + public routes on a separate router without the dependency
2. `protected_router = APIRouter(dependencies=[Depends(require_auth())])` for all protected routes; `public_router = APIRouter()` for health/public

**Estimate**: 3 pts
**Assigned To**: python-backend-engineer
**Phase**: 4 (integrate with API-001 through API-004)

---

### ENT-002: Visibility-Based Filtering in Repositories (Phase 4)

**Source**: lead-architect finding I7
**Risk**: Data leakage — tenant isolation exists via `_apply_tenant_filter`, but users within the same tenant can see each other's private artifacts.

**Change Required**: Add `_apply_visibility_filter(stmt, auth_context)` to repository base classes:
- `public` items: visible to all within tenant
- `team` items: visible to team members (requires team membership lookup)
- `private` items: visible only to `owner_id == auth_context.user_id`

**Estimate**: 5 pts
**Assigned To**: python-backend-engineer, data-layer-expert
**Phase**: 4 (integrate with API-005)
**Dependencies**: WIRE-001

---

### ENT-003: Integration Test — End-to-End Auth Flow (Phase 4)

**Source**: karen finding G6
**Risk**: Components are tested in isolation but never together. No test proves auth flows from HTTP request through to service layer.

**Test Scenarios**:
1. Start app with `LocalAuthProvider` → request without auth header → succeeds with local_admin context
2. Start app with mock `ClerkAuthProvider` → request with valid JWT → succeeds with mapped context
3. Request to protected endpoint without token → 401
4. Request to scope-protected endpoint without required scope → 403
5. Verify `auth_context` reaches service layer (not just router)

**Estimate**: 3 pts
**Assigned To**: python-backend-engineer
**Phase**: 4 (integrate with API-007)

---

### ENT-004: Structured Audit Events for Auth Operations (Phase 6)

**Source**: lead-architect cross-cutting concern
**Risk**: Compliance gap — no audit trail for auth events.

**Design**:
- Define `AuditEvent` schema (who, what, when, from_where, result)
- Emit events from: `require_auth` (success/failure), `ClerkAuthProvider.validate` (JWT validation), `_assert_tenant_owns` (tenant isolation violations)
- Initially log to structured logger; later persist to audit table

**Estimate**: 5 pts
**Phase**: 6

---

## P2 — Design Improvements (Phase 4-5+)

### DES-001: Document owner_id Type Mismatch (String vs UUID) (Phase 4)

**Source**: lead-architect finding C3
**Files**: `skillmeat/cache/models.py` (owner_id is `str`), `skillmeat/api/schemas/auth.py` (user_id is `uuid.UUID`)

**Action**: Add a `str_owner_id(auth_context)` helper to the repository base that handles the conversion consistently. Document the pattern in a code comment and in the repository architecture key-context doc.

**Estimate**: 2 pts

---

### DES-002: Document system_admin Assignment Path for Clerk (Phase 4)

**Source**: lead-architect finding C4
**File**: `skillmeat/api/auth/clerk_provider.py`

**Decision Required**: Is `system_admin` intentionally reserved for service accounts (local_admin + enterprise PAT only)? If yes, document it. If not, add a mapping path (e.g., custom Clerk metadata claim `skillmeat_role: system_admin` or database-driven role lookup).

**Estimate**: 2 pts

---

### DES-003: Plan AuthorizationService Interface for Dynamic RBAC (Phase 5+)

**Source**: lead-architect finding I1
**Current State**: Role-to-scope mapping is a static dictionary in `clerk_provider.py`

**Future Need**: Custom roles per tenant, runtime scope grants/revocations, role hierarchies.

**Action**: Design an `AuthorizationService` interface that resolves `(user_id, tenant_id) -> roles, scopes` at runtime. Initially backed by the static map, but replaceable with a DB-driven RBAC engine.

**Estimate**: 3 pts

---

### DES-004: Token Revocation Strategy (Phase 5+)

**Source**: lead-architect finding I4
**Current State**: No mechanism to revoke a compromised token before expiry.

**Options**:
1. Redis-backed token blocklist (check on every `require_auth` call)
2. Clerk session verification on sensitive write operations only
3. Short-lived access tokens (5 min) + refresh tokens

**Estimate**: 5 pts

---

### DES-005: String-Based Scope Registry for Runtime Extensibility (Phase 5+)

**Source**: lead-architect finding I3
**Current State**: `Scope` is a closed enum with 7 values. Adding new resource types requires code changes.

**Recommendation**: Transition to string-based scope constants with a registry pattern. `has_scope()` already accepts raw strings, so the transition is backward-compatible.

**Estimate**: 3 pts

---

## P3 — Future Enhancements (Phase 6+)

| ID | Enhancement | Notes | Estimate |
|----|-------------|-------|----------|
| FUT-001 | OpenTelemetry spans for auth operations | `auth.validate`, `auth.scope_check`, `tenant.resolve` spans | 2 pts |
| FUT-002 | Per-user rate limiting (keyed on user_id, not IP) | Current IP-based limiter fails behind reverse proxy | 3 pts |
| FUT-003 | Webhook authentication (HMAC-SHA256 signature verification) | Define pattern before SkillMeat emits/receives webhooks | 2 pts |
| FUT-004 | Per-user/per-service API keys (scoped, hashed, rotatable) | Replace single global API key with proper key management | 5 pts |
| FUT-005 | Session management (active session tracking, logout-all) | Track sessions per user, enforce concurrent limits | 5 pts |

---

## Integration with Original Plan

### Phase 4 Modifications

The original Phase 4 ("API Layer — Auth Injection & Endpoint Protection") should incorporate the following as a **Batch 0** executed before API-001:

```
Batch 0 (pre-wiring): SEC-001, SEC-002, WIRE-001, WIRE-003
Batch 1 (original):   API-001 (critical routers) + ENT-001 (secure-by-default)
Batch 2 (original):   API-002 (supporting routers)
Batch 3 (original):   API-003 (marketplace routers) + WIRE-002 (TenantContext)
Batch 4 (original):   API-004 (public routes), API-005 + ENT-002 (visibility filtering)
Batch 5 (original):   API-006, API-007 + ENT-003 (integration tests), API-008
```

### Additional Effort

| Priority | Points | Phase |
|----------|--------|-------|
| P0 (security + wiring) | 5.5 pts | Phase 4 Batch 0 |
| P1 (enterprise readiness) | 16 pts | Phase 4 + Phase 6 |
| P2 (design improvements) | 15 pts | Phase 4-5+ |
| P3 (future enhancements) | 17 pts | Phase 6+ |
| **Total addendum** | **53.5 pts** | |

**Note**: P0 items add ~1 day to Phase 4. P1 items ENT-001 and ENT-002 fold into existing Phase 4 tasks (API-001 and API-005 respectively). ENT-003 folds into API-007. Net Phase 4 impact: +2-3 days.
