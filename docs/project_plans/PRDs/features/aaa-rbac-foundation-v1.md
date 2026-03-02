# PRD 2: AAA & RBAC Foundation (Individual & Team)

**Author**: Gemini
**Date**: 2026-03-01

## 1. Executive Summary

This PRD defines the implementation of Authentication, Authorization, and Accounting (AAA) for the application. Leveraging the abstraction layer built in PRD 1, this phase introduces a pluggable identity provider system, centralized Role-Based Access Control (RBAC) middleware, and ownership tracking in the data layer. It focuses on Individual and Team modes, ensuring the existing "zero-auth" local CLI experience remains completely unbroken.

**Priority:** HIGH

**Complexity:** MEDIUM

## 2. Goals & Outcomes

* **Pluggable Auth:** Implement an abstract `AuthProvider` supporting both "Local/Zero-Auth" and "Clerk JWT" strategies.
* **Centralized RBAC:** Secure all API endpoints via dependency-injected scope validation.
* **Data Tenancy:** Update DTOs and database schemas to include `owner_id` and `tenant_id` fields.
* **Secure CLI:** Implement device authorization flows and local credential storage for CLI users.

## 3. Architectural Design

### 3.1 Identity Provider (IdP) Abstraction

* **LocalAuthProvider:** Returns a static, elevated `local_admin` context for local filesystem users.
* **ClerkAuthProvider:** Validates incoming JWTs and maps Clerk user/organization IDs to internal models.

### 3.2 RBAC Middleware

Protect endpoints using declarative scopes.

```python
@router.post("/artifacts", dependencies=[Security(require_auth, scopes=["artifact:write"])])

```

* **Roles:** `system_admin`, `team_admin`, `team_member`, `viewer`.
* **Context Propagation:** The `AuthContext` object is passed from the router down to the Repository layer (built in PRD 1) to enforce row-level data isolation.

### 3.3 Data Model Updates

* Introduce `Users`, `Teams`, and `TeamMembers` models.
* Append `owner_id` (UUID), `owner_type` (User/Team), and `visibility` (Private/Team/Public) to all artifact and collection DTOs/schemas.

## 4. Implementation Phases

* **Phase 1: Tenancy Schema & DTOs:** Update all backend entities to support ownership fields. Default all existing local data to `local_admin`.
* **Phase 2: Auth Middleware & Providers:** Build the provider interfaces and configure FastAPI to inject `AuthContext` into requests.
* **Phase 3: Frontend Identity Integration:** Integrate Clerk SDK into the Next.js UI. Add Login/Signup flows and a "Workspace Switcher" for toggling between Personal and Team contexts.
* **Phase 4: CLI Authentication:** Implement `skillmeat login` (OAuth device code flow) and `skillmeat auth --token <PAT>` for headless environments.
