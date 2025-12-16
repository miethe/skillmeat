---
title: "Collections API Consolidation - Implementation Plan"
description: "Consolidate legacy file-based /collections endpoints with modern DB-backed /user-collections system"
audience: [ai-agents, developers]
tags: [implementation, refactoring, backend, frontend, api]
created: 2025-12-13
updated: 2025-12-13
category: "refactoring"
status: completed
---

# Implementation Plan: Collections API Consolidation

## Executive Summary

**Goal**: Consolidate two separate collection systems into a single unified API that serves as the source of truth for collection management.

**Current State**:
- `/collections` (file-based, TOML manifests, 3 GET endpoints, read-only)
- `/user-collections` (DB-backed, SQLite, 7 CRUD endpoints, full featured)

**Problem**: Frontend calls endpoints that don't exist (PUT/DELETE on `/collections/*`), causing 404 errors.

**Solution**: Migrate all collection operations to `/user-collections`, update frontend to use correct endpoints, deprecate legacy `/collections` router.

**Scope**: Backend API gap-filling + Frontend API client refactoring + Data migration path

**Effort**: ~23 story points (Medium complexity refactor)

**Timeline**: 3-5 days

**Risk**: Medium - requires careful frontend coordination to avoid breaking existing functionality

---

## Current State Analysis

### System Inventory

| System | Router | Storage | Endpoints | Features |
|--------|--------|---------|-----------|----------|
| **Legacy** | `/collections` | TOML files | 3 GET (list, get, artifacts) | Read-only, file-based |
| **Active** | `/user-collections` | SQLite DB | 7 CRUD (list, create, get, update, delete, add artifacts, remove artifacts) | Full CRUD, groups, search |

### Frontend API Client Issues

**File**: `skillmeat/web/lib/api/collections.ts`

| Function | Calls Endpoint | Actual Status | Issue |
|----------|----------------|---------------|-------|
| `fetchCollections()` | `GET /collections` | Works | Uses legacy read-only endpoint |
| `fetchCollection(id)` | `GET /collections/{id}` | Works | Uses legacy read-only endpoint |
| `createCollection(data)` | `POST /user-collections` | Works | Correctly uses DB endpoint |
| `updateCollection(id, data)` | `PUT /collections/{id}` | 404 | Endpoint doesn't exist |
| `deleteCollection(id)` | `DELETE /collections/{id}` | 404 | Endpoint doesn't exist |
| `addArtifactToCollection(...)` | `POST /collections/{id}/artifacts/{aid}` | 404 | Endpoint doesn't exist |
| `removeArtifactFromCollection(...)` | `DELETE /collections/{id}/artifacts/{aid}` | 404 | Endpoint doesn't exist |
| `copyArtifactToCollection(...)` | `POST /collections/{id}/artifacts/{aid}/copy` | 404 | Endpoint doesn't exist |
| `moveArtifactToCollection(...)` | `POST /collections/{id}/artifacts/{aid}/move` | 404 | Endpoint doesn't exist |

### Frontend Hooks Status

**File**: `skillmeat/web/hooks/use-collections.ts`

| Hook | Status | Notes |
|------|--------|-------|
| `useCollections()` | Works | Calls `GET /collections` (legacy) |
| `useCollection(id)` | Works | Calls `GET /collections/{id}` (legacy) |
| `useCollectionArtifacts(id)` | Works | Calls `GET /collections/{id}/artifacts` (legacy) |
| `useCreateCollection()` | Works | Calls `POST /user-collections` (correct) |
| `useUpdateCollection()` | Stub | Throws 501 - not implemented |
| `useDeleteCollection()` | Stub | Throws 501 - not implemented |
| `useAddArtifactToCollection()` | Stub | Throws 501 - not implemented |
| `useRemoveArtifactFromCollection()` | Stub | Throws 501 - not implemented |

### API Gaps in `/user-collections`

**Missing Endpoints** (that exist in legacy `/collections`):

| Legacy Endpoint | Equivalent in `/user-collections` | Status |
|-----------------|-----------------------------------|--------|
| `GET /collections/{id}/artifacts?artifact_type={type}` | None | Missing - needs implementation |

**Additional Gaps**:
- Copy artifact endpoint (referenced in frontend but not implemented anywhere)
- Move artifact endpoint (referenced in frontend but not implemented anywhere)

---

## Implementation Strategy

### Approach

1. **Phase 1**: Fill API gaps in `/user-collections` backend
2. **Phase 2**: Update frontend API client to use `/user-collections` consistently
3. **Phase 3**: Update frontend hooks to call corrected API client functions
4. **Phase 4**: Create data migration path (file-based → DB)
5. **Phase 5**: Deprecate legacy `/collections` endpoints

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Keep `/user-collections` prefix | Clear separation from legacy; allows gradual migration |
| Implement artifact filtering in backend | More efficient than client-side filtering |
| Defer copy/move to post-MVP | Complex operations; can be done client-side initially |
| Soft deprecation (warnings) | Don't break existing consumers immediately |
| Data migration as optional script | Some users may want to keep file-based collections |

---

## Phase 1: Backend API Gap Filling

**Goal**: Add missing endpoints to `/user-collections` router to match frontend expectations

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|----|------|-------------|---------------------|----------|-------------|--------------|
| TASK-1.1 | Add GET /user-collections/{id}/artifacts endpoint | Implement endpoint to list artifacts in a collection with optional type filtering | Endpoint returns paginated artifacts; supports `artifact_type` query param; matches schema of legacy endpoint | 3 SP | python-backend-engineer | None |
| TASK-1.2 | Update user_collections schema | Add ArtifactSummary response model if not exists; ensure compatibility with frontend types | Schema matches `types/collections.ts` ArtifactSummary interface | 1 SP | python-backend-engineer | TASK-1.1 |
| TASK-1.3 | Add copy artifact endpoint (optional) | POST /user-collections/{source_id}/artifacts/{artifact_id}/copy | Endpoint copies artifact to target collection (idempotent) | 2 SP | python-backend-engineer | None |
| TASK-1.4 | Add move artifact endpoint (optional) | POST /user-collections/{source_id}/artifacts/{artifact_id}/move | Endpoint removes from source and adds to target (atomic) | 2 SP | python-backend-engineer | TASK-1.3 |

**Total Phase 1 Effort**: 8 story points (5 SP if copy/move deferred)

### Quality Gates

- [ ] New endpoints pass integration tests
- [ ] OpenAPI spec updated
- [ ] Response schemas match frontend TypeScript types
- [ ] Pagination works correctly
- [ ] Type filtering works correctly
- [ ] Error handling (404 for missing collection/artifact)

---

## Phase 2: Frontend API Client Refactoring

**Goal**: Update `lib/api/collections.ts` to call correct endpoints

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|----|------|-------------|---------------------|----------|-------------|--------------|
| TASK-2.1 | Refactor fetchCollections() | Change from `GET /collections` to `GET /user-collections` | Function calls correct endpoint; returns compatible data structure | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-1.1 |
| TASK-2.2 | Refactor fetchCollection(id) | Change from `GET /collections/{id}` to `GET /user-collections/{id}` | Function calls correct endpoint; handles groups in response | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-1.1 |
| TASK-2.3 | Fix updateCollection(id, data) | Change from `PUT /collections/{id}` to `PUT /user-collections/{id}` | Function calls existing `/user-collections` update endpoint (line 420 in router) | 1 SP | ui-engineer-enhanced, frontend-developer | None |
| TASK-2.4 | Fix deleteCollection(id) | Change from `DELETE /collections/{id}` to `DELETE /user-collections/{id}` | Function calls existing `/user-collections` delete endpoint (line 505 in router) | 1 SP | ui-engineer-enhanced, frontend-developer | None |
| TASK-2.5 | Fix addArtifactToCollection() | Change from `POST /collections/{id}/artifacts/{aid}` to `POST /user-collections/{id}/artifacts` with body `{artifact_ids: [aid]}` | Function calls existing `/user-collections` add artifacts endpoint (line 572 in router) | 2 SP | ui-engineer-enhanced, frontend-developer | None |
| TASK-2.6 | Fix removeArtifactFromCollection() | Change from `DELETE /collections/{id}/artifacts/{aid}` to `DELETE /user-collections/{id}/artifacts/{aid}` | Function calls existing `/user-collections` remove endpoint (line 671 in router) | 1 SP | ui-engineer-enhanced, frontend-developer | None |
| TASK-2.7 | Update copy/move or remove stubs | Either implement using new endpoints or remove functions if not used | Copy/move work or functions removed with deprecation comments | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-1.3, TASK-1.4 (if implementing) |
| TASK-2.8 | Update TypeScript types | Ensure `types/collections.ts` matches `/user-collections` response schemas | Types align with backend schemas; includes groups, created_by, etc. | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.1 |

**Total Phase 2 Effort**: 9 story points

### Quality Gates

- [ ] TypeScript compiles without errors
- [ ] All API client functions call correct endpoints
- [ ] Request/response types match backend schemas
- [ ] No 404 errors in browser console
- [ ] Existing UI functionality still works

---

## Phase 3: Frontend Hooks Refactoring

**Goal**: Update `hooks/use-collections.ts` to use refactored API client

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|----|------|-------------|---------------------|----------|-------------|--------------|
| TASK-3.1 | Update useCollections() | Change to call `/user-collections` via updated API client | Hook fetches from correct endpoint; returns correct data structure | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.1 |
| TASK-3.2 | Update useCollection(id) | Change to call `/user-collections/{id}` via updated API client | Hook fetches collection with groups; types correct | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.2 |
| TASK-3.3 | Implement useUpdateCollection() | Remove stub; call actual API client function | Hook calls correct endpoint; invalidates cache on success | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.3 |
| TASK-3.4 | Implement useDeleteCollection() | Remove stub; call actual API client function | Hook calls correct endpoint; invalidates cache on success | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.4 |
| TASK-3.5 | Implement useAddArtifactToCollection() | Remove stub; call actual API client function | Hook calls correct endpoint; invalidates collection cache on success | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.5 |
| TASK-3.6 | Implement useRemoveArtifactFromCollection() | Remove stub; call actual API client function | Hook calls correct endpoint; invalidates collection cache on success | 1 SP | ui-engineer-enhanced, frontend-developer | TASK-2.6 |

**Total Phase 3 Effort**: 6 story points

### Quality Gates

- [ ] All hooks use updated API client
- [ ] No 501 "Not implemented" errors
- [ ] TanStack Query cache invalidation works correctly
- [ ] Hooks have proper loading/error states
- [ ] TypeScript types correct

---

## Phase 4: Data Migration (Optional)

**Goal**: Provide migration path for users with existing file-based collections

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|----|------|-------------|---------------------|----------|-------------|--------------|
| TASK-4.1 | Create migration script | Python CLI command to import TOML collections into SQLite DB | Script reads manifest.toml, creates Collection records, preserves metadata | 2 SP | python-backend-engineer, data-layer-expert | None |
| TASK-4.2 | Document migration process | Add migration guide to docs | Clear instructions for running migration; rollback steps documented | 1 SP | documentation-writer | TASK-4.1 |
| TASK-4.3 | Test migration with sample data | Verify migration preserves all data correctly | Test collection migrated; artifact associations preserved; no data loss | 1 SP | python-backend-engineer | TASK-4.1 |

**Total Phase 4 Effort**: 4 story points

**Note**: This phase is optional and can be deferred. Most users likely haven't created file-based collections yet.

### Quality Gates

- [ ] Migration script completes without errors
- [ ] All collections migrated to DB
- [ ] Artifact associations preserved
- [ ] Metadata (created, updated timestamps) preserved
- [ ] Script handles edge cases (duplicate names, missing artifacts)

---

## Phase 5: Deprecation & Cleanup

**Goal**: Deprecate legacy `/collections` endpoints and update documentation

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|----|------|-------------|---------------------|----------|-------------|--------------|
| TASK-5.1 | Add deprecation warnings | Add deprecation headers to `/collections` endpoints | Endpoints return `Deprecation: true` header; response includes deprecation message | 1 SP | python-backend-engineer | TASK-2.1 |
| TASK-5.2 | Update API documentation | Update OpenAPI spec and docs to mark `/collections` as deprecated | Documentation clearly states deprecation; recommends `/user-collections` | 1 SP | documentation-writer | TASK-5.1 |
| TASK-5.3 | Add removal timeline | Document when `/collections` will be removed | Clear timeline communicated (e.g., "will be removed in v1.0.0") | 0.5 SP | documentation-writer | TASK-5.2 |
| TASK-5.4 | Create removal PR (future) | Remove `/collections` router entirely | Router deleted; all tests pass; no references in codebase | 1 SP | python-backend-engineer | Phase 2, Phase 3 complete |

**Total Phase 5 Effort**: 3.5 story points

### Quality Gates

- [ ] Deprecation warnings visible in API responses
- [ ] Documentation updated
- [ ] Removal timeline communicated
- [ ] No breaking changes until removal date

---

## File Changes Summary

### Backend Files

| File | Changes | Phase |
|------|---------|-------|
| `skillmeat/api/routers/user_collections.py` | Add GET /{id}/artifacts endpoint; optionally add copy/move endpoints | Phase 1 |
| `skillmeat/api/schemas/user_collections.py` | Add ArtifactSummary response model if missing | Phase 1 |
| `skillmeat/api/routers/collections.py` | Add deprecation warnings to all endpoints | Phase 5 |
| `skillmeat/api/server.py` | (No changes required - routers already registered) | - |

### Frontend Files

| File | Changes | Phase |
|------|---------|-------|
| `skillmeat/web/lib/api/collections.ts` | Update all functions to call `/user-collections` endpoints | Phase 2 |
| `skillmeat/web/types/collections.ts` | Update Collection interface to include groups, created_by, etc. | Phase 2 |
| `skillmeat/web/hooks/use-collections.ts` | Implement all stubbed hooks; update to use new API client | Phase 3 |

### Migration Files (Optional)

| File | Changes | Phase |
|------|---------|-------|
| `skillmeat/cli/commands/migrate.py` | New CLI command for migrating file-based collections to DB | Phase 4 |
| `docs/guides/migration-guide.md` | Documentation for migration process | Phase 4 |

---

## API Endpoint Mapping

### Before (Fragmented)

| Operation | Frontend Calls | Backend Status |
|-----------|----------------|----------------|
| List collections | `GET /collections` | Works (legacy) |
| Get collection | `GET /collections/{id}` | Works (legacy) |
| List artifacts | `GET /collections/{id}/artifacts` | Works (legacy) |
| Create collection | `POST /user-collections` | Works (DB) |
| Update collection | `PUT /collections/{id}` | 404 |
| Delete collection | `DELETE /collections/{id}` | 404 |
| Add artifact | `POST /collections/{id}/artifacts/{aid}` | 404 |
| Remove artifact | `DELETE /collections/{id}/artifacts/{aid}` | 404 |

### After (Unified)

| Operation | Frontend Calls | Backend Status |
|-----------|----------------|----------------|
| List collections | `GET /user-collections` | Works (DB) |
| Get collection | `GET /user-collections/{id}` | Works (DB) |
| List artifacts | `GET /user-collections/{id}/artifacts` | Works (DB) - NEW |
| Create collection | `POST /user-collections` | Works (DB) |
| Update collection | `PUT /user-collections/{id}` | Works (DB) |
| Delete collection | `DELETE /user-collections/{id}` | Works (DB) |
| Add artifact | `POST /user-collections/{id}/artifacts` | Works (DB) |
| Remove artifact | `DELETE /user-collections/{id}/artifacts/{aid}` | Works (DB) |

---

## Success Metrics

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Zero 404 errors from collection API calls | 0 errors | Browser console + API logs |
| All collection CRUD operations work | 100% | Manual testing + E2E tests |
| Frontend hooks functional | 0 "Not implemented" errors | Manual testing |
| TypeScript compilation | No errors | `pnpm type-check` |
| API consistency | All collection ops use `/user-collections` | Code review |
| Performance | No regression | Compare response times before/after |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing UI flows | Medium | High | Thorough testing; incremental rollout |
| Data loss during migration | Low | High | Test migration thoroughly; provide rollback |
| Type mismatches | Medium | Medium | Validate TypeScript types against schemas |
| Cache invalidation issues | Medium | Medium | Test all mutation hooks invalidate correctly |
| Performance degradation | Low | Medium | Monitor API response times; optimize queries if needed |
| Orphaned data in legacy system | Low | Low | Document cleanup process |

---

## Testing Strategy

### Backend Tests

| Test Type | Coverage |
|-----------|----------|
| Unit tests | New endpoints (GET artifacts, copy/move if implemented) |
| Integration tests | Full CRUD cycle on `/user-collections` |
| Schema validation | Response schemas match OpenAPI spec |
| Error handling | 404 for missing collections/artifacts |
| Pagination | Correct page boundaries; cursor handling |

### Frontend Tests

| Test Type | Coverage |
|-----------|----------|
| Unit tests | API client functions call correct URLs |
| Hook tests | All hooks return correct data structures |
| Integration tests | E2E collection CRUD flows |
| Type tests | TypeScript compilation |
| UI tests | Collection management UI still works |

---

## Rollout Plan

### Step 1: Backend Gap Fill (Phase 1)
- Deploy new `/user-collections/{id}/artifacts` endpoint
- Verify endpoint works via Postman/curl
- Update OpenAPI spec

### Step 2: Frontend API Client (Phase 2)
- Update API client functions
- Verify TypeScript compilation
- Test in dev environment

### Step 3: Frontend Hooks (Phase 3)
- Implement stubbed hooks
- Test all collection operations in UI
- Verify cache invalidation

### Step 4: Deprecation (Phase 5)
- Add warnings to legacy endpoints
- Update documentation
- Communicate timeline to users

### Step 5: Migration (Phase 4 - Optional)
- Provide migration script
- Document migration process
- Support users who need to migrate

### Step 6: Removal (Future)
- Remove legacy `/collections` router
- Clean up old code

---

## Dependencies

### External
- None - all required infrastructure exists

### Internal
- Phase 2 depends on Phase 1 (backend endpoints must exist)
- Phase 3 depends on Phase 2 (API client must be correct)
- Phase 5 depends on Phase 2 + 3 (can't deprecate until migration complete)
- Phase 4 is independent (can happen anytime)

---

## Orchestration Quick Reference

### Batch 1: Backend Implementation (Sequential)

**TASK-1.1-1.2: Add artifacts endpoint**
```
Task("python-backend-engineer", "TASK-1.1-1.2: Add GET /user-collections/{id}/artifacts endpoint with type filtering

Files:
- skillmeat/api/routers/user_collections.py
- skillmeat/api/schemas/user_collections.py

Requirements:
1. Add new endpoint: GET /user-collections/{collection_id}/artifacts
2. Support query params: limit, after (cursor), artifact_type
3. Return paginated response with ArtifactSummary items
4. Reuse pagination pattern from existing list_user_collections (lines 171-279)
5. Add ArtifactSummary schema to user_collections.py schemas if not exists
6. Schema should match: {name: str, type: str, version: str, source: str}
7. Reference: Existing /collections/{id}/artifacts endpoint (collections.py lines 240-381) for pattern

Acceptance:
- Endpoint returns artifacts in collection
- Type filtering works (e.g., ?artifact_type=skill)
- Pagination works with cursor
- Response schema matches frontend types/collections.ts ArtifactSummary")
```

**TASK-1.3-1.4: Add copy/move endpoints (OPTIONAL - defer if needed)**
```
Task("python-backend-engineer", "TASK-1.3-1.4: Add copy/move artifact endpoints (optional)

Files:
- skillmeat/api/routers/user_collections.py

Requirements (if implementing):
1. POST /user-collections/{source_id}/artifacts/{artifact_id}/copy
   - Body: {target_collection_id: str}
   - Copies artifact to target collection (idempotent)
2. POST /user-collections/{source_id}/artifacts/{artifact_id}/move
   - Body: {target_collection_id: str}
   - Removes from source, adds to target (atomic transaction)

Note: Can defer these endpoints - frontend can implement client-side as:
- Copy = add to target
- Move = add to target + remove from source")
```

### Batch 2: Frontend API Client (Parallel after Batch 1)

**TASK-2.1-2.8: Refactor API client**
```
Task("ui-engineer-enhanced", "TASK-2.1-2.8: Refactor lib/api/collections.ts to use /user-collections consistently

File: skillmeat/web/lib/api/collections.ts

Changes Required:
1. fetchCollections() (line 23): Change to buildUrl('/user-collections')
2. fetchCollection(id) (line 34): Change to buildUrl('/user-collections/{id}')
3. updateCollection(id, data) (line 65): Change to buildUrl('/user-collections/{id}')
4. deleteCollection(id) (line 79): Change to buildUrl('/user-collections/{id}')
5. addArtifactToCollection(collectionId, artifactId) (line 99):
   - Change to buildUrl('/user-collections/{collectionId}/artifacts')
   - Change method: POST with body {artifact_ids: [artifactId]}
   - Match schema: AddArtifactsRequest from backend (line 50 in user_collections.py schemas)
6. removeArtifactFromCollection(collectionId, artifactId) (line 117):
   - Change to buildUrl('/user-collections/{collectionId}/artifacts/{artifactId}')
   - Keep method: DELETE
7. copyArtifactToCollection (line 136): Either implement or remove (mark deprecated)
8. moveArtifactToCollection (line 161): Either implement or remove (mark deprecated)

Also update: skillmeat/web/types/collections.ts
- Add fields to Collection interface: created_by, groups (optional)
- Ensure types match UserCollectionResponse schema from backend

Acceptance:
- TypeScript compiles without errors
- All functions call correct endpoints
- Request bodies match backend schemas")
```

### Batch 3: Frontend Hooks (Sequential after Batch 2)

**TASK-3.1-3.6: Implement stubbed hooks**
```
Task("ui-engineer-enhanced", "TASK-3.1-3.6: Implement all stubbed hooks in use-collections.ts

File: skillmeat/web/hooks/use-collections.ts

Changes:
1. useCollections() (line 90): Already works, but verify calls updated API client
2. useCollection(id) (line 145): Verify calls updated API client
3. useUpdateCollection() (line 256): Remove stub, implement:
   mutationFn: async ({ id, data }) => updateCollection(id, data)
4. useDeleteCollection() (line 289): Remove stub, implement:
   mutationFn: async (id) => deleteCollection(id)
5. useAddArtifactToCollection() (line 322): Remove stub, implement:
   mutationFn: async ({ collectionId, artifactId }) => addArtifactToCollection(collectionId, artifactId)
6. useRemoveArtifactFromCollection() (line 359): Remove stub, implement:
   mutationFn: async ({ collectionId, artifactId }) => removeArtifactFromCollection(collectionId, artifactId)

Remove all 'throw new ApiError(..., 501)' lines
Ensure cache invalidation works correctly (queryClient.invalidateQueries)

Acceptance:
- No 501 errors
- All hooks functional
- Cache invalidation works
- Types correct")
```

### Batch 4: Deprecation (Sequential after Batch 3)

**TASK-5.1-5.3: Deprecate legacy endpoints**
```
Task("python-backend-engineer", "TASK-5.1: Add deprecation warnings to /collections router

File: skillmeat/api/routers/collections.py

Changes:
1. Add deprecation header to all endpoints:
   - Use FastAPI Response object to set header: Deprecation: true
   - Add warning to response body or log
2. Add comment to router noting deprecation timeline

Pattern:
from fastapi import Response
response.headers['Deprecation'] = 'true'
response.headers['Sunset'] = '2025-06-01'  # example date")

Task("documentation-writer", "TASK-5.2-5.3: Update API docs with deprecation notice

Files:
- OpenAPI spec (auto-generated, but add notes)
- Add docs/guides/api-migration.md

Content:
- Mark /collections endpoints as deprecated
- Recommend /user-collections instead
- Document timeline for removal
- Provide migration examples")
```

---

## Post-Implementation Checklist

- [ ] All backend endpoints tested and working
- [ ] OpenAPI spec updated
- [ ] Frontend API client calls correct endpoints
- [ ] Frontend hooks implemented and functional
- [ ] TypeScript compiles without errors
- [ ] No 404/501 errors in browser console
- [ ] Collection CRUD operations work end-to-end
- [ ] Cache invalidation works correctly
- [ ] Deprecation warnings added
- [ ] Documentation updated
- [ ] Migration guide created (if Phase 4 implemented)
- [ ] Performance verified (no regressions)

---

## Future Enhancements

### Post-Consolidation Improvements

1. **Add bulk operations**: Bulk add/remove artifacts
2. **Add reordering**: Endpoint to reorder artifacts in collection
3. **Add search**: Full-text search within collection artifacts
4. **Add export/import**: Export collection as JSON/TOML
5. **Add sharing**: Share collections between users
6. **Add templates**: Collection templates for common use cases

### Complete Removal Timeline

| Milestone | Date | Action |
|-----------|------|--------|
| Deprecation warnings added | Phase 5 complete | Communicate to users |
| Grace period | 3-6 months | Monitor usage of legacy endpoints |
| Final removal | v1.0.0 release | Delete /collections router |

---

## Notes

- This is a **refactoring** task, not a feature addition
- Goal is **zero breaking changes** to frontend functionality
- Legacy endpoints remain functional during migration
- `/user-collections` becomes the single source of truth
- File-based collections remain supported (read-only) until migration

---

## Related Documents

- [Collections API Router (Legacy)](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/collections.py)
- [User Collections API Router (Active)](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/user_collections.py)
- [Frontend API Client](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/collections.ts)
- [Frontend Collection Hooks](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-collections.ts)
- [API CLAUDE.md](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/CLAUDE.md)
- [Web CLAUDE.md](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/CLAUDE.md)
