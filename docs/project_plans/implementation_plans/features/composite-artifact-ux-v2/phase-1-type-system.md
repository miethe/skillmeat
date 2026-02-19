---
schema_version: 2
doc_type: phase_plan
title: 'Phase 1: Type System + Backend CRUD'
status: inferred_complete
created: 2026-02-19
updated: 2026-02-19
feature_slug: composite-artifact-ux-v2
feature_version: v2
phase: 1
phase_title: Type System + Backend CRUD
prd_ref: /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
entry_criteria:
- v1 infrastructure deployed and stable (CompositeService, CompositeMembershipRepository,
  ORM models verified)
- CompositeService methods `create_composite`, `update_composite`, `delete_composite`
  exist and are tested
- CompositeMembership model has position column (or migration planned)
exit_criteria:
- All 6 CRUD endpoints implemented and integration tested
- openapi.json regenerated and committed
- pnpm type-check passes with zero new errors
- No regression in existing artifact type paths
related_documents:
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
---
# Phase 1: Type System + Backend CRUD

**Duration**: 3-4 days
**Dependencies**: v1 infrastructure complete
**Assigned Subagent(s)**: frontend-developer, python-backend-engineer

## Overview

This phase is the critical foundation for all downstream work. We add `'composite'` to the frontend type system (type union, config, ID parsing, platform defaults) and wire the 6 CRUD endpoints to the existing backend service layer. No new business logic is implemented — this is purely surface-level integration of already-built infrastructure.

## Frontend Tasks (Type System)

### Task 1: Type Union Extension (CUX-P1-01)

**Description**: Add `'composite'` to the `ArtifactType` union in `skillmeat/web/types/artifact.ts`.

**Deliverable**:
```typescript
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook' | 'composite';
```

**Acceptance Criteria**:
- Union includes `'composite'`
- All existing switch statements and type guards still handle all cases (exhaustiveness checked by TypeScript)
- File builds without errors

**Estimated**: 1 pt
**Subagent**: frontend-developer

---

### Task 2: ARTIFACT_TYPES Config (CUX-P1-02)

**Description**: Add `composite` entry to the `ARTIFACT_TYPES` registry with:
- icon: `Blocks` (Lucide)
- label: `Plugin`
- pluralLabel: `Plugins`
- color: `text-indigo-500`
- form schema: name (required), description, tags, members

**Deliverable**:
```typescript
composite: {
  type: 'composite',
  label: 'Plugin',
  pluralLabel: 'Plugins',
  icon: Blocks,
  color: 'text-indigo-500',
  requiredFile: '',  // or 'plugin.json' if strict
  formSchema: {
    name: z.string().min(1).max(100),
    description: z.string().max(500).optional(),
    tags: z.array(z.string()).optional(),
    members: z.array(z.object({
      artifact_id: z.string(),
      position: z.number().optional(),
    })),
  },
}
```

**Acceptance Criteria**:
- Config entry is accessible via `getArtifactTypeConfig('composite')`
- Returns valid config object
- Icon and color render correctly
- Form schema validates

**Estimated**: 1 pt
**Subagent**: frontend-developer
**Depends on**: CUX-P1-01

---

### Task 3: ID Parsing & Formatting (CUX-P1-03)

**Description**: Update `parseArtifactId()` and `formatArtifactId()` functions to handle `'composite'` type.

**Current behavior**: `parseArtifactId('composite:my-plugin')` probably returns `null` because the type isn't in the union.

**Deliverable**:
```typescript
parseArtifactId('composite:my-plugin')  // returns {type: 'composite', name: 'my-plugin'}
formatArtifactId({type: 'composite', name: 'my-plugin'})  // returns 'composite:my-plugin'
```

**Acceptance Criteria**:
- `parseArtifactId` handles `composite:` prefix
- `formatArtifactId` handles `{type: 'composite', name: 'X'}`
- No null returns for valid composite IDs
- Existing behavior for other types unchanged

**Estimated**: 1 pt
**Subagent**: frontend-developer
**Depends on**: CUX-P1-01

---

### Task 4: Platform Defaults (CUX-P1-04)

**Description**: Add `'composite'` to platform defaults constant (likely in `skillmeat/web/lib/constants/platform-defaults.ts` or equivalent).

**Deliverable**: Composite type participates in platform-level filtering and configuration without special cases.

**Acceptance Criteria**:
- `'composite'` appears in the platform defaults array/set
- No TypeScript errors when filtering by platform defaults
- Composite type treated equally to atomic types in platform logic

**Estimated**: 1 pt
**Subagent**: frontend-developer
**Depends on**: CUX-P1-01

---

## Backend Tasks (CRUD API)

### Task 5: Verify CompositeService (CUX-P1-05)

**Description**: Inspect `skillmeat/core/services/composite_service.py` and confirm that `create_composite()`, `update_composite()`, and `delete_composite()` methods exist and are tested. If absent, implement them as thin wrappers over the repository layer.

**Acceptance Criteria**:
- All 3 methods exist
- Methods are tested (unit tests pass)
- Methods return appropriate DTOs or status

**Estimated**: 1 pt
**Subagent**: python-backend-engineer

---

### Task 6: Verify Position Column (CUX-P1-06)

**Description**: Inspect `skillmeat/cache/models.py` and confirm that `CompositeMembership` ORM model has a `position` column (nullable int) for member ordering. If absent, plan a lightweight Alembic migration.

**Acceptance Criteria**:
- `position` column exists on `CompositeMembership`
- Column is accessible via repository methods
- Alembic migration created (if new)

**Estimated**: 1 pt
**Subagent**: python-backend-engineer

---

### Task 7: New Router: composites.py (CUX-P1-07)

**Description**: Create a new file `skillmeat/api/routers/composites.py` with all 6 endpoint stubs. Register the router in the main FastAPI app under `/api/v1/composites`.

**Deliverable**: Router file with 6 endpoint signatures (implementation in CUX-P1-08 through CUX-P1-13).

**Acceptance Criteria**:
- Router file created
- All 6 endpoints have signatures (may return 501 Not Implemented initially)
- Router registered in main app
- App starts without errors

**Estimated**: 2 pts
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-05, CUX-P1-06

---

### Task 8: POST /api/v1/composites (CUX-P1-08)

**Description**: Implement composite creation endpoint. Accepts request body:
```json
{
  "name": "my-plugin",
  "description": "optional description",
  "members": [
    {"artifact_id": "skill:foo", "position": 0},
    {"artifact_id": "command:bar", "position": 1}
  ]
}
```

Calls `CompositeService.create_composite()` and returns 201 with the created composite DTO.

**Acceptance Criteria**:
- Endpoint returns 201 Created
- Composite created in database
- Memberships created with correct positions
- Response DTO includes all fields
- Input validation works (name required, max lengths, etc.)
- 400 errors on bad input

**Estimated**: 2 pts
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 9: PUT /api/v1/composites/{id} (CUX-P1-09)

**Description**: Update composite metadata (name, description). Endpoint signature:
```
PUT /api/v1/composites/{composite_id}
{
  "name": "updated-name",
  "description": "updated description"
}
```

**Acceptance Criteria**:
- Endpoint returns 200 OK
- Composite updated in database
- Response DTO reflects changes
- 404 for unknown composite

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 10: DELETE /api/v1/composites/{id} (CUX-P1-10)

**Description**: Delete composite. Optional query parameter `?cascade_delete_children=true` to delete child artifacts (default: unlink only).

**Acceptance Criteria**:
- Endpoint returns 204 No Content
- Composite deleted from database
- By default, memberships deleted but child artifacts remain
- With `cascade_delete_children=true`, child artifacts deleted
- 404 for unknown composite

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 11: POST /api/v1/composites/{id}/members (CUX-P1-11)

**Description**: Add a member to an existing composite. Request body:
```json
{
  "artifact_id": "skill:foo",
  "position": 3
}
```

**Acceptance Criteria**:
- Endpoint returns 201 Created
- Membership created in database
- Position updated correctly
- 404 for unknown composite or artifact

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 12: DELETE /api/v1/composites/{id}/members/{member_id} (CUX-P1-12)

**Description**: Remove a member from a composite.

**Acceptance Criteria**:
- Endpoint returns 204 No Content
- Membership deleted from database
- Child artifact remains in collection
- 404 for unknown composite or membership

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 13: PATCH /api/v1/composites/{id}/members (CUX-P1-13)

**Description**: Reorder members. Request body is an array of position updates:
```json
[
  {"artifact_id": "skill:foo", "position": 0},
  {"artifact_id": "command:bar", "position": 1},
  {"artifact_id": "agent:baz", "position": 2}
]
```

**Acceptance Criteria**:
- Endpoint returns 200 OK
- Member positions updated in database
- All members in new order
- 404 for unknown composite

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 14: Pydantic Schemas (CUX-P1-14)

**Description**: Create request/response schemas for all endpoints in `skillmeat/api/schemas/` (or in the router file if following existing pattern).

**Schemas needed**:
- `CompositeCreateRequest`, `CompositeCreateResponse`
- `CompositeUpdateRequest`, `CompositeUpdateResponse`
- `CompositeDeleteRequest`
- `MembershipCreateRequest`, `MembershipCreateResponse`
- `MembershipDeleteRequest`
- `MembershipReorderRequest`

**Acceptance Criteria**:
- All schemas validate correctly
- OpenAPI doc generation works
- Response schemas match actual endpoint returns

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-07

---

### Task 15: Regenerate OpenAPI (CUX-P1-15)

**Description**: Run FastAPI schema generation to create updated `skillmeat/api/openapi.json` with all 6 new endpoints and their schemas.

**Acceptance Criteria**:
- `openapi.json` includes all 6 new endpoints
- Request/response schemas are correct
- File is committed to repo
- Frontend SDK can be regenerated from schema

**Estimated**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-14

---

### Task 16: Integration Tests (CUX-P1-16)

**Description**: Write integration tests for all 6 endpoints covering happy path and error cases (400, 404, etc.).

**Test scenarios per endpoint**:
- Create: happy path, missing name, duplicate name, invalid artifact IDs
- Update: happy path, unknown composite, missing fields
- Delete: happy path, unknown composite, cascade delete option
- Add member: happy path, unknown composite, unknown artifact, duplicate member
- Remove member: happy path, unknown composite, unknown membership
- Reorder: happy path, unknown composite, partial member list

**Acceptance Criteria**:
- All tests pass
- >80% coverage of new endpoint code
- CI passes

**Estimated**: 2 pts
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-15

---

## Phase 1 Quality Gates

- [ ] Enum change does not break existing type-checking (run `pnpm type-check` full suite)
- [ ] UUID column migration applies cleanly (if performed in Phase 1)
- [ ] All 6 CRUD endpoints implement and return correct status codes
- [ ] Integration tests for all endpoints pass
- [ ] `openapi.json` regenerated and includes all endpoints
- [ ] No regression in existing artifact type paths (run existing artifact tests)
- [ ] pnpm build succeeds
- [ ] pnpm lint passes with no new warnings

---

## Files Modified/Created

### Frontend
- **Modified**: `skillmeat/web/types/artifact.ts`
- **Modified**: `skillmeat/web/lib/constants/platform-defaults.ts`

### Backend
- **Created**: `skillmeat/api/routers/composites.py`
- **Modified**: `skillmeat/api/schemas/` (add new schemas)
- **Modified**: `skillmeat/core/services/composite_service.py` (if methods missing)
- **Modified**: `skillmeat/api/openapi.json` (regenerated)
- **Created**: `tests/test_composites_api.py`

---

## Key Implementation Notes

1. **Type Union First**: Complete CUX-P1-01 through CUX-P1-04 before touching backend, so the entire team has a stable foundation.
2. **Verify Before Implementing**: CUX-P1-05 and CUX-P1-06 are verification tasks — read the codebase and confirm v1 infrastructure is ready. If anything is missing, escalate and implement.
3. **Route Registration**: Make sure the new `composites.py` router is registered in the main FastAPI app with the correct prefix (`/api/v1/composites`).
4. **Schema Reuse**: Check if `AssociationsDTO` or similar already exists from v1; reuse where possible.
5. **Error Handling**: All endpoints should follow existing error response patterns in the codebase (likely an `ErrorResponse` envelope).
6. **Testing**: Use the existing test patterns (pytest, fixtures for DB state, etc.); ensure tests are isolated and reversible.

---

**Phase 1 Version**: 1.0
**Last Updated**: 2026-02-19
