---
title: 'PRD: Sync/Diff Modal Standardization Refactor'
description: Fix sync/diff inconsistencies between /manage and /projects pages, establish
  shared modal foundation, and enable complete sync workflows
audience:
- ai-agents
- developers
- architects
tags:
- prd
- planning
- refactor
- sync
- diff
- modal
- standardization
- collection
created: 2026-02-04
updated: 2026-02-04
category: product-planning
status: inferred_complete
priority: HIGH
related:
- /docs/project_plans/reports/sync-diff-modal-inconsistency-analysis-2026-02-04.md
- /docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md
- /docs/project_plans/implementation_plans/refactors/modal-architecture-improvements-r2r3.md
schema_version: 2
doc_type: prd
feature_slug: sync-diff-modal-standardization
---
# PRD: Sync/Diff Modal Standardization Refactor

**Feature Name:** Sync/Diff Modal Standardization

**Filepath Name:** `sync-diff-modal-standardization-v1`

**Date:** 2026-02-04

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Planned

**Priority:** HIGH

**Scope:** Refactor (modal unification deferred; foundation layer is in-scope)

---

## 1. Executive Summary

The SkillMeat web UI has **two separate modal implementations** (`ArtifactOperationsModal` and `UnifiedEntityModal`) serving overlapping purposes across `/manage` and `/projects/{ID}` pages. This causes **sync/diff workflows to fail on /manage** due to four root causes: frontend-backend source validation mismatch, missing project context in collection mode, divergent architecture, and incomplete mutation handling.

**Key Outcomes:**
- Stop 400 API errors on `/manage` by aligning frontend validation with backend expectations
- Enable collection-vs-project diffs on `/manage` via project selector or auto-detection
- Standardize mutation handling (keep-local, batch actions, push-to-collection)
- Establish shared modal foundation (`BaseArtifactModal` pattern) for future convergence
- Verify sync workflows work consistently across both pages

**Success Metrics:**
- Zero 400 errors on `/manage` for valid artifacts
- Upstream, collection-vs-project, and source-vs-project diffs load on `/manage`
- Sync mutations execute without no-ops or "coming soon" stubs
- Foundation layer enables 80% code reuse between modals by Q3 2026

---

## 2. Context & Background

### Current State

**Dual Modal Architecture:**

| Aspect | `/manage` | `/projects/{ID}` |
|--------|----------|-----------------|
| Modal | `ArtifactOperationsModal` (1,411 lines) | `ProjectArtifactModal` wrapper → `UnifiedEntityModal` (2,566 lines) |
| Sync Mode | Hardcoded `mode="collection"` | Dynamic: `entity.projectPath ? 'project' : 'collection'` |
| Project Path | Always undefined | `entity.projectPath \|\| selectedProjectForDiff` (state-driven) |
| Lifecycle | `mode="collection"` only | `mode="project"` with project context |
| Upstream Diff Query | Query fires, 400 errors | Query fires, works correctly |
| Project Diff Query | Query disabled (projectPath null) | Query enabled, works correctly |

**Investigation Report** (`sync-diff-modal-inconsistency-analysis-2026-02-04.md`) identified four root causes.

### Entity → Artifact Migration (Context)

- `Entity` is now a **deprecated type alias** for `Artifact` (types/entity.ts re-exports types/artifact.ts)
- Codebase has 21+ consumers of `Entity` type; planned deprecation: Q3 2026
- This PRD uses both terms interchangeably; implementation MUST use `Artifact` type

### Key Files Involved

**Frontend:**
- `web/components/manage/artifact-operations-modal.tsx` (1,411 lines) - /manage modal, missing projectPath
- `web/components/entity/unified-entity-modal.tsx` (2,566 lines) - /projects modal, working sync
- `web/components/shared/ProjectArtifactModal.tsx` (87 lines) - /projects wrapper
- `web/components/sync-status/sync-status-tab.tsx` (648 lines) - Shared sync orchestration (source of issues)
- `web/components/sync-status/comparison-selector.tsx` - Scope selector (option disabling)
- `web/components/entity/project-selector-for-diff.tsx` - Project picker (only on /projects)
- `web/types/artifact.ts` - Canonical type
- `web/types/entity.ts` - Deprecated shim

**Backend:**
- `api/routers/artifacts.py` - `upstream-diff` (line 4160), `diff` endpoints
- `api/routers/context_sync.py` - push/pull/status/resolve endpoints

---

## 3. Problem Statement

### Issue 1: Frontend-Backend Source Validation Mismatch (HIGH)

**Problem:** Frontend `hasValidUpstreamSource()` checks `entity.source` (URL string), but backend checks `artifact.origin` (enum: "github", "marketplace", "local").

- Marketplace-sourced artifacts: Frontend sees GitHub URL → fires query; backend rejects with 400 because `origin: "marketplace"`
- **Evidence:** Codex artifact: `origin: "marketplace"`, `source: "https://github.com/..."` → GET `/artifacts/codex/upstream-diff` returns 400
- **Impact:** 400 errors on `/manage` for marketplace artifacts; TanStack Query retry loop (4 consecutive failures observed)

**Current Logic:**
```typescript
// sync-status-tab.tsx:98-104
function hasValidUpstreamSource(source: string | undefined | null): boolean {
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;
  return source.includes('/') && !source.startsWith('local');  // ← Checks URL only
}
```

**Backend Check:**
```python
# artifacts.py:4160-4170
if artifact.origin != "github":
    raise HTTPException(status_code=400, detail="...")
if not artifact.upstream:
    raise HTTPException(status_code=400, detail="...")
```

### Issue 2: Missing projectPath in Collection Mode (HIGH)

**Problem:** `ArtifactOperationsModal` passes `SyncStatusTab` in `mode="collection"` **without** `projectPath` prop.

- Line 1185-1191: `<SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />` (no projectPath)
- Query enablement condition (line 254-256): `enabled: !!projectPath` → always false on /manage
- **Impact:** Collection-vs-project diffs never work on /manage; flow banner always shows "Not deployed"

### Issue 3: Dual Modal Architecture Divergence (MEDIUM)

**Problem:** Two 1000+ line components with overlapping functionality diverge in:
- Default tabs (status vs overview)
- Sync mode handling (hardcoded vs dynamic)
- Project context handling (missing vs present)
- Lifecycle provider configuration

**Impact:** Maintenance burden, inconsistent UX, code duplication for future features

### Issue 4: Sync Action Mutations (MEDIUM)

**Problem:** Missing or stubbed implementations:
- `keepLocalMutation`: `Promise.resolve()` (no-op)
- `handleApplyActions`: Toast "Batch actions not yet implemented"
- Push to collection: Toast "Coming Soon"

---

## 4. Goals & Success Metrics

| Goal | Metric | Success Criteria |
|------|--------|-----------------|
| Stop validation errors | 400 error rate on /manage | Zero 400s for valid artifacts; upstream-diff fires only when `origin: "github"` + `upstream.tracking_enabled` |
| Enable diffs on /manage | Collection-vs-project diff load rate | 100% of eligible artifacts show diff data (project selector available) |
| Standardize mutations | Stub implementation coverage | All 4 mutations wired to endpoints (keep-local, batch actions, push-to-collection, deploy) |
| Foundation layer | Modal code reuse by Q3 2026 | `BaseArtifactModal` pattern enables 80%+ shared logic; both modals compose from foundation |
| Consistency across pages | UX parity tests | Sync workflows work identically on /manage and /projects pages |

---

## 5. Functional Requirements

### FR-1: Fix Frontend Source Validation

**Requirement:** Update `hasValidUpstreamSource()` to align with backend expectations.

**Changes:**
1. Update function signature to accept `Artifact` type (not string)
2. Check: `artifact.origin === 'github'`
3. Check: `artifact.upstream?.tracking_enabled` (truthy)
4. Disable upstream-diff query if either check fails

**File:** `web/components/sync-status/sync-status-tab.tsx`

**Acceptance Criteria:**
- Marketplace artifacts with no tracking don't fire upstream-diff query
- GitHub artifacts with tracking enabled fire query and succeed
- Zero 400 errors on /manage for any artifact type

### FR-2: Add Project Context to Collection Mode

**Requirement:** Enable collection-vs-project diffs on /manage via project selector.

**Options:**
1. **Auto-detect:** If artifact has exactly one deployment, auto-select that project
2. **Manual selector:** Add `ProjectSelectorForDiff` component in sync tab (similar to /projects modal)
3. **Hybrid:** Auto-detect if available; show selector if multiple deployments or no deployments

**Recommendation:** Hybrid approach (auto-detect with fallback to selector)

**File:** `web/components/manage/artifact-operations-modal.tsx`

**Acceptance Criteria:**
- `/manage` modal can select a project for diffs
- Collection-vs-project diff query enables when projectPath is set
- Flow banner shows deployment status correctly

### FR-3: Establish BaseArtifactModal Foundation (MEDIUM)

**Requirement:** Extract shared modal patterns into base component for future convergence.

**Changes:**
1. Create `BaseArtifactModal` component with:
   - Unified modal structure (header, tabs, footer)
   - Tab orchestration logic
   - Lifecycle provider setup
   - Query/mutation hooks
2. Update `ArtifactOperationsModal` to compose from base
3. Document for `UnifiedEntityModal` composition (future PR)

**File:** `web/components/shared/BaseArtifactModal.tsx` (new)

**Acceptance Criteria:**
- Base component provides 60%+ of modal boilerplate
- Both modals pass all existing tests
- Future modal implementation requires minimal new code

### FR-4: Wire Up Missing Mutations

**Requirement:** Implement all sync action mutations.

**Changes:**

| Mutation | Endpoint | Implementation |
|----------|----------|-----------------|
| Keep Local | No endpoint | Dismiss diff state, mark as reviewed |
| Deploy to Project | `POST /artifacts/{id}/deploy` | Already wired; fix requires FR-2 (projectPath) |
| Batch Actions | `POST /context-sync/push` (partial) | Implement batch endpoint call, invalidate caches |
| Push to Collection | `POST /context-sync/pull` | Wire up for project-to-collection push |

**Acceptance Criteria:**
- No "coming soon" or "not yet implemented" toasts
- All mutations call their respective endpoints
- Mutations invalidate appropriate TanStack Query cache keys per data-flow-patterns

---

## 6. Non-Functional Requirements

| NFR | Requirement | Implementation |
|-----|-------------|-----------------|
| **Performance** | Query latency < 500ms | No new queries; reuse existing endpoints |
| **Accessibility** | WCAG 2.1 AA | Project selector inherits existing patterns |
| **Backward Compatibility** | Both pages remain functional | Changes are additive; no breaking mutations |
| **Type Safety** | 100% TypeScript strict mode | Use `Artifact` type, not deprecated `Entity` |
| **Cache Consistency** | Follow data-flow-patterns | All mutations invalidate per invalidation graph |
| **Testing** | 80%+ coverage for new code | Unit tests for validation, integration for mutations |

---

## 7. Scope

### In Scope

- Fix frontend source validation logic
- Add project selector/auto-detection to /manage sync tab
- Extract `BaseArtifactModal` foundation
- Wire up missing mutations (keep-local, batch, push-to-collection)
- Update tests to cover new/modified code
- Verification that sync workflows work on both pages

### Out of Scope

- Full modal unification (deferred to Q3 2026, post-entity migration)
- Backend endpoint changes (all required endpoints already exist)
- Entity → Artifact type migration (separate EPIC, ongoing)
- UI redesign beyond foundation extraction

---

## 8. Dependencies

- **Existing modal implementations** (`ArtifactOperationsModal`, `UnifiedEntityModal`) must remain functional
- **Sync API endpoints** already exist; no backend work required
- **Entity → Artifact migration** ongoing; PRD uses `Artifact` type, but existing code uses `Entity`
- **Data flow principles** (write-through, cache invalidation graph) must be followed
- **TanStack Query hooks** for sync operations

---

## 9. Risks & Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking /manage modal | HIGH | Comprehensive integration tests before merging; both pages tested in same PR |
| Cache invalidation bugs | HIGH | Audit mutation code against invalidation graph; test with devtools |
| Project selector UX confusion | MEDIUM | Reuse patterns from /projects modal; document in CLAUDE.md |
| Entity type confusion during migration | MEDIUM | Use `Artifact` type in new code; update types/entity.ts import if needed |

---

## 10. Phased Implementation

### Phase 1: Fix Validation (Priority: HIGH)

**Goal:** Stop 400 errors on /manage.

**Tasks:**
- Update `hasValidUpstreamSource()` in `sync-status-tab.tsx`
- Update query enablement condition for upstream-diff
- Test with marketplace and GitHub artifacts
- Verify zero 400s in browser console

**Success:** All artifact types load without 400 errors.

### Phase 2: Add Project Context (Priority: HIGH)

**Goal:** Enable collection-vs-project diffs on /manage.

**Tasks:**
- Analyze deployments on artifact to auto-detect project
- Add project selector or integrate `ProjectSelectorForDiff`
- Pass `projectPath` to `SyncStatusTab`
- Test diff loading and flow banner accuracy

**Success:** Diffs load on /manage when project is selected.

### Phase 3: Extract Foundation (Priority: MEDIUM)

**Goal:** Establish `BaseArtifactModal` pattern.

**Tasks:**
- Create `BaseArtifactModal` component with shared structure
- Refactor `ArtifactOperationsModal` to use base
- Ensure all tests pass
- Document pattern in CLAUDE.md

**Success:** Base component reduces code duplication; both modals work identically.

### Phase 4: Wire Mutations (Priority: MEDIUM)

**Goal:** Implement all sync actions.

**Tasks:**
- Implement `keepLocalMutation` logic
- Implement batch actions endpoint call
- Implement push-to-collection endpoint call
- Update cache invalidation per data-flow-patterns
- Test each mutation flow

**Success:** All mutations execute without stubs.

### Phase 5: Testing & Documentation (Priority: MEDIUM)

**Goal:** Ensure quality and maintainability.

**Tasks:**
- Add unit tests for validation function
- Add integration tests for modal workflows
- Add E2E tests for sync flow (upstream → collection → project)
- Update CLAUDE.md with modal patterns
- Update README with sync workflow examples

**Success:** 80%+ code coverage; docs reflect new patterns.

---

## 11. Acceptance Criteria (by Phase)

### Phase 1 Acceptance Criteria

- [ ] `hasValidUpstreamSource()` checks `artifact.origin === 'github'` and `artifact.upstream?.tracking_enabled`
- [ ] Upstream-diff query enablement condition updated
- [ ] Zero 400 errors on `/manage` for any artifact type
- [ ] Browser console shows no TanStack Query retries for validation
- [ ] GitHub artifacts show upstream diff; marketplace/local artifacts show "N/A"

### Phase 2 Acceptance Criteria

- [ ] Project selector or auto-detection available on `/manage` sync tab
- [ ] Collection-vs-project diff query fires when projectPath is set
- [ ] Diff data loads and displays correctly
- [ ] Flow banner shows accurate deployment status (deployed vs not deployed)
- [ ] Artifact with one deployment auto-selects that project
- [ ] Artifact with multiple deployments shows selector

### Phase 3 Acceptance Criteria

- [ ] `BaseArtifactModal` component created with 60%+ of modal boilerplate
- [ ] `ArtifactOperationsModal` refactored to use base; all tests pass
- [ ] Modal structure, tabs, lifecycle provider setup inherited from base
- [ ] Documentation added to CLAUDE.md with composition pattern

### Phase 4 Acceptance Criteria

- [ ] `keepLocalMutation` dismisses diff state (no API call needed)
- [ ] Batch actions call `POST /context-sync/push` with entity IDs
- [ ] Push-to-collection calls appropriate endpoint
- [ ] Deploy mutation works on both pages with projectPath
- [ ] All mutations invalidate correct cache keys per invalidation graph
- [ ] No "coming soon" or "not yet implemented" toasts

### Phase 5 Acceptance Criteria

- [ ] Unit tests for `hasValidUpstreamSource()` function (3+ test cases)
- [ ] Integration tests for sync workflows on /manage and /projects (2 tests per page)
- [ ] E2E tests for complete sync flow (upstream → collection → project)
- [ ] CLAUDE.md updated with modal foundation pattern
- [ ] All code achieves 80%+ coverage
- [ ] README updated with sync workflow examples (if applicable)

---

## 12. Metrics & Monitoring

**Pre-Launch Metrics:**
- Baseline: Current 400 error rate on /manage (observed: 100% for marketplace artifacts)
- Baseline: Current diff load success rate on /manage (observed: 0% for collection-vs-project)

**Post-Launch Metrics:**
- Target: 0% 400 error rate on /manage
- Target: 95%+ diff load success rate on /manage
- Target: Sync workflow duration (establish baseline for Phase 5)

**Monitoring:**
- Error tracking: Sentry for 400 errors
- Performance: TanStack Query devtools for query duration
- User experience: Browser console for unexpected toasts/errors

---

## 13. Related Documents

- **Investigation Report:** `/docs/project_plans/reports/sync-diff-modal-inconsistency-analysis-2026-02-04.md`
- **Modal Redesign PRD:** `/docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md`
- **Modal Architecture Improvements:** `/docs/project_plans/implementation_plans/refactors/modal-architecture-improvements-r2r3.md`
- **Data Flow Patterns:** `/.claude/context/key-context/data-flow-patterns.md`
- **Component Patterns:** `/.claude/context/key-context/component-patterns.md`
- **NextJS Patterns:** `/.claude/context/key-context/nextjs-patterns.md`

---

## 14. Assumptions & Open Questions

**Assumptions:**
1. `ProjectSelectorForDiff` component can be reused in `/manage` modal (or adapted with minimal changes)
2. Auto-detection of single deployment is acceptable UX (vs always showing selector)
3. All required backend endpoints already exist and are functional (confirmed by investigation)
4. Entity → Artifact migration will complete by Q3 2026 (allows deprecation of `Entity` type)

**Open Questions:**
1. **Project selector UI**: Should auto-selected project be editable, or require explicit user selection?
2. **Mutation priority**: Should Phase 4 (mutations) be parallelized with Phase 2-3, or sequential?
3. **Modal unification timeline**: Target date for full modal convergence after this refactor?
4. **Testing scope**: Should E2E tests cover all three diff scopes (source, collection-vs-project, source-vs-project)?

---

## 15. Success Definition

This PRD is **complete and successful** when:

1. ✅ **All validation errors fixed** — Zero 400s on `/manage` for valid artifacts
2. ✅ **Diffs work on both pages** — Upstream, collection-vs-project, and source-vs-project diffs load consistently
3. ✅ **Mutations are operational** — All sync actions execute without stubs
4. ✅ **Foundation established** — `BaseArtifactModal` pattern enables future consolidation
5. ✅ **Quality verified** — 80%+ test coverage; all tests pass; docs reflect new patterns
6. ✅ **Both pages functional** — No regressions on `/manage` or `/projects`

**Success metrics (post-launch):**
- 0% 400 error rate on `/manage` (baseline: 100% for marketplace artifacts)
- 95%+ diff load success rate on `/manage` (baseline: 0% for collection-vs-project)
- 100% sync mutation completion rate (baseline: 0% with stubs)
