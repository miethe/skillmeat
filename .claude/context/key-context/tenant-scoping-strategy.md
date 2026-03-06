# Tenant Scoping Strategy

**Feature:** enterprise-db-storage (branch: `feat/enterprise-db-storage`)
**Phase scope:** Phase 1 (single-tenant bootstrap) through Phase 3
**Schema reference:** `docs/project_plans/architecture/enterprise-db-schema-v1.md` §6

---

## 1. DEFAULT_TENANT_ID Constant

**File:** `skillmeat/cache/constants.py`

```python
import os, uuid

DEFAULT_TENANT_ID: uuid.UUID = uuid.UUID(
    os.environ.get("SKILLMEAT_DEFAULT_TENANT_ID", "00000000-0000-4000-a000-000000000001")
)
```

**Value:** `00000000-0000-4000-a000-000000000001`
**ENV override:** `SKILLMEAT_DEFAULT_TENANT_ID`

**Why a UUID, not a string:**
- The `tenant_id` column type is `UUID` at the PostgreSQL level. Passing a bare string forces an implicit cast on every query — a type mismatch that some drivers reject and all drivers make slower.
- SQLAlchemy's `UUID(as_uuid=True)` maps columns to `uuid.UUID` objects. Passing a `uuid.UUID` constant satisfies the type system end-to-end without a cast.
- Using a Python `uuid.UUID` makes it impossible to accidentally pass a free-form string (e.g., `"default"`) into a column expecting a UUID, catching errors at import time rather than at query time.

**Import pattern:**

```python
from skillmeat.cache.constants import DEFAULT_TENANT_ID
```

---

## 2. WHERE tenant_id = ? Filtering Contract

**Rule:** Every method in an enterprise repository MUST include a `tenant_id` predicate. No query against an enterprise table may return rows across tenant boundaries. Omitting the filter is a security defect, not a style issue.

### Correct pattern

```python
def get_artifact(
    session: Session,
    artifact_id: uuid.UUID,
    tenant_id: uuid.UUID,          # required — always passed by caller
) -> EnterpriseArtifact | None:
    return (
        session.query(EnterpriseArtifact)
        .filter(
            EnterpriseArtifact.id == artifact_id,
            EnterpriseArtifact.tenant_id == tenant_id,   # MANDATORY
        )
        .one_or_none()
    )
```

### Prohibited pattern

```python
# NEVER — returns data across all tenants; this is a security defect
def get_artifact(session: Session, artifact_id: uuid.UUID):
    return (
        session.query(EnterpriseArtifact)
        .filter(EnterpriseArtifact.id == artifact_id)
        # Missing tenant_id filter
        .one_or_none()
    )
```

### List queries

```python
def list_artifacts(
    session: Session,
    tenant_id: uuid.UUID,
    artifact_type: str | None = None,
) -> list[EnterpriseArtifact]:
    q = session.query(EnterpriseArtifact).filter(
        EnterpriseArtifact.tenant_id == tenant_id   # always first
    )
    if artifact_type:
        q = q.filter(EnterpriseArtifact.type == artifact_type)
    return q.order_by(EnterpriseArtifact.created_at.desc()).all()
```

Apply `tenant_id` filter first. All subsequent predicates narrow within the tenant's data.

---

## 3. Context Propagation — Phase 1

**Approach:** no middleware, no global context variables, no thread-locals. `tenant_id` is an explicit parameter threaded through the call stack.

### Call stack

```
FastAPI route handler
  → service method(tenant_id=DEFAULT_TENANT_ID)
      → repository method(session, tenant_id, ...)
          → SQL: WHERE tenant_id = $1
```

### Repository method signature convention

`tenant_id: uuid.UUID` is always the **first positional parameter after `session`**:

```python
def create_artifact(
    session: Session,
    tenant_id: uuid.UUID,      # position 2, always
    name: str,
    artifact_type: str,
    ...
) -> EnterpriseArtifact:
    ...
```

This convention makes the tenant parameter visually obvious and enables `grep`/symbol search to quickly verify coverage.

### Service layer (Phase 1)

```python
from skillmeat.cache.constants import DEFAULT_TENANT_ID

class EnterpriseArtifactService:
    def list_artifacts(self, artifact_type: str | None = None):
        with get_session() as session:
            return artifact_repo.list_artifacts(
                session,
                tenant_id=DEFAULT_TENANT_ID,   # Phase 1: constant
                artifact_type=artifact_type,
            )
```

The service is the only layer that knows whether it's using a constant or a live context. Repository code never imports `DEFAULT_TENANT_ID` — it only receives `tenant_id` as a parameter.

---

## 4. Phase 2 AuthContext DI Swap

When PRD 2 lands, the only change needed is at the service call site. Repository signatures remain identical.

### Planned FastAPI dependency

```python
# Phase 2 — sketch; not implemented yet
from fastapi import Depends, Request

class TenantContext:
    def __init__(self, tenant_id: uuid.UUID):
        self.tenant_id = tenant_id

async def get_tenant_context(request: Request) -> TenantContext:
    # Extract from Clerk JWT / session token
    tenant_id = uuid.UUID(request.state.auth.tenant_id)
    return TenantContext(tenant_id=tenant_id)
```

### Service layer after Phase 2

```python
class EnterpriseArtifactService:
    def list_artifacts(
        self,
        ctx: TenantContext,                # injected by FastAPI
        artifact_type: str | None = None,
    ):
        with get_session() as session:
            return artifact_repo.list_artifacts(
                session,
                tenant_id=ctx.tenant_id,   # Phase 2: from auth
                artifact_type=artifact_type,
            )
```

**No repository changes. No schema changes. No migration.** The `tenant_id` column exists from Phase 1; the swap is purely at the injection point.

---

## 5. RLS Future Migration Path (Phase 3+)

PostgreSQL Row Level Security provides defense-in-depth on top of the application-layer `WHERE tenant_id = ?` filters. It is deferred from Phase 1 because:

- Requires `SET LOCAL app.current_tenant_id = ?` on every transaction — session variable overhead needs profiling at real tenant scale.
- RLS policies bypass the PostgreSQL superuser role — test suites running as superuser must connect as `skillmeat_app_role` or RLS is silently skipped, adding test infrastructure complexity.
- Application-layer filtering is sufficient for initial single-tenant enterprise deployments.

### DDL when RLS is enabled

```sql
-- Step 1: Enable RLS (non-destructive; existing rows unaffected)
ALTER TABLE enterprise_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifact_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE enterprise_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE enterprise_collection_artifacts ENABLE ROW LEVEL SECURITY;

-- Step 2: Create isolation policy per table
-- Pattern: tenant_id column must match the session variable set by middleware
CREATE POLICY tenant_isolation ON enterprise_artifacts
    FOR ALL
    TO skillmeat_app_role
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Repeat for each enterprise table (artifact_versions, enterprise_collections,
-- enterprise_collection_artifacts) with the same USING clause pattern.

-- Step 3: Middleware sets session variable per transaction
-- In FastAPI middleware or dependency:
--   await session.execute(
--       text("SET LOCAL app.current_tenant_id = :tid"),
--       {"tid": str(ctx.tenant_id)}
--   )
```

**Transition is zero-downtime and backward-compatible:**
- Application-layer `WHERE tenant_id = ?` filters continue to work unchanged.
- RLS adds a second enforcement layer; it does not replace the first.
- Existing data requires no migration — `tenant_id` is present from Phase 1.

### What needs to be in place before enabling RLS

1. `skillmeat_app_role` PostgreSQL role created and assigned to the connection pool user.
2. FastAPI middleware that issues `SET LOCAL app.current_tenant_id = ?` before handing the session to the service layer.
3. Integration test suite updated to run as `skillmeat_app_role` (not superuser) so RLS policies are exercised.
4. Performance profiling of the `SET LOCAL` overhead at expected tenant scale.

---

## 6. Isolation Test Requirement

All enterprise repository integration tests MUST include a negative isolation assertion:

```python
def test_tenant_isolation(session):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    session.add(EnterpriseArtifact(
        tenant_id=tenant_a, name="my-skill", type="skill", scope="user",
        tags=[], custom_fields={},
    ))
    session.flush()

    result = (
        session.query(EnterpriseArtifact)
        .filter(EnterpriseArtifact.tenant_id == tenant_b)
        .all()
    )
    assert result == [], "Tenant B must not see Tenant A data"
```

This test pattern is required for every enterprise repository, not just `EnterpriseArtifactRepository`.

---

## Quick Reference

| Item | Value / Location |
|------|-----------------|
| Constant file | `skillmeat/cache/constants.py` |
| Constant name | `DEFAULT_TENANT_ID` |
| Default UUID | `00000000-0000-4000-a000-000000000001` |
| ENV override | `SKILLMEAT_DEFAULT_TENANT_ID` |
| Parameter position | 2nd (after `session`) in all repo methods |
| Phase 1 call site | `tenant_id=DEFAULT_TENANT_ID` in service layer |
| Phase 2 call site | `tenant_id=ctx.tenant_id` from `TenantContext` DI |
| RLS phase | Phase 3+ (deferred) |
| Schema reference | `enterprise-db-schema-v1.md` §6 |
