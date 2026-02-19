---
status: inferred_complete
schema_version: 2
doc_type: prd
feature_slug: entity-artifact-consolidation
---
# Entity and Artifact Type System Consolidation

**Status**: Approved for development
**Epic ID**: REFACTOR-TYPE-CONSOLIDATION
**Priority**: High (improves maintainability and eliminates bug class)
**Effort**: 3-4 sprints (phased approach)
**Start Date**: TBD
**Target Release**: v0.4.0

---

## Executive Summary

SkillMeat maintains two parallel type systems (`Entity` and `Artifact`) with separate data conversion pipelines that cause maintenance overhead, type safety issues, and intermittent bugs. This refactoring consolidates to a **unified `Artifact` type** that:

- Flattens nested metadata (description, tags, author, license at top level)
- Unifies status enum (`synced | modified | outdated | conflict | error`)
- Adds deployment context via `projectPath` (previously Entity-only)
- Preserves optional nested objects (`upstream`, `usageStats`)
- Maintains form configuration via `ARTIFACT_TYPES` registry

**Projected outcome**: Elimination of 4 redundant conversion functions, 3+ modal/data pipeline bugs, and ~150 lines of conversion boilerplate. **Single source of truth for artifact representation** across both `/collection` and `/manage` pages.

---

## Problem Statement

### Current Architecture Issues

Two parallel type systems create technical debt:

| Issue | Impact | Evidence |
|-------|--------|----------|
| **4 redundant conversion functions** | Code duplication, maintenance burden | `mapApiArtifact()`, `mapApiArtifactToEntity()`, `artifactToEntity()`, `entityToArtifact()` |
| **Status enum mismatch** | Manual mapping required, potential for bugs | Artifact: `active\|outdated\|conflict\|error`; Entity: `synced\|modified\|outdated\|conflict` |
| **Fallback object problem** | Collections tab empty, synthetic metadata | `/collection` page creates synthetic Artifact objects with empty `metadata` field |
| **Implicit cache dependencies** | Sources tab missing until /marketplace visited | `useSources()` lazy-loads; modal feature depends on unrelated user navigation |
| **Inconsistent component usage** | Silent feature degradation | `/collection` page didn't pass navigation handlers to `UnifiedEntityModal` |
| **Modal type constraint** | Forced conversion on every modal open | `UnifiedEntityModal` only accepts `Entity`, conversion required from `/collection` page |
| **Dual form schemas** | Configuration scattered | `ENTITY_TYPES` registry, but Artifact-aware code exists throughout |

### Documented Bugs from Reports

From `entity-vs-artifact-architecture-analysis.md` (2026-01-22):
- Collections tab empty on /manage page (missing field in mapper)
- Source tab missing until visiting /marketplace (lazy load cache dependency)
- Source link broken on /collection (inconsistent modal usage)
- Synthetic artifacts with empty metadata causing display issues

From `artifact-modal-architecture-analysis.md` (2026-01-28):
- Multiple mapping functions scattered across codebase
- Same modal used differently without contract enforcement
- Collection membership data inconsistencies between endpoints

### Root Cause

The architecture treats "what's displayed" and "what's edited" as fundamentally different concepts:
- **Artifact** = Backend representation, collection display
- **Entity** = UI component representation, CRUD operations

This distinction is artificial and unmaintainable. The backend (`ArtifactResponse`) already uses a single schema; the frontend introduces this complexity.

---

## Goals & Success Metrics

### Primary Goals

1. **Eliminate type duplication**: Single `Artifact` type definition, shared across all features
2. **Remove redundant conversions**: Zero manual conversion functions (except where API adapter pattern is necessary)
3. **Unify status tracking**: Single enum for deployment/collection sync state
4. **Improve type safety**: Stricter type enforcement prevents modal-related bugs
5. **Reduce codebase size**: ~400+ lines of type definitions and conversion logic removed
6. **Enable future migration**: Clean foundation for backend sync improvements

### Success Metrics

| Metric | Target | Baseline |
|--------|--------|----------|
| **Type definition files** | 1 (artifact.ts) | 2 (artifact.ts + entity.ts) |
| **Conversion functions** | 0-1 (API adapter only) | 4 |
| **Status enum values** | 5 unified | 4 (Artifact) + 4 (Entity) |
| **Bug escape rate** | 0 modal/conversion bugs | 3+ per sprint |
| **Codebase size (types + conversion)** | <300 lines | 500+ lines |
| **Component usage consistency** | 100% (modal contract enforced) | ~60% (handlers optional) |
| **Test coverage** (type system) | >85% | ~65% |

### Non-Functional Goals

1. **Zero breaking changes** to public APIs during transition (use deprecation aliases)
2. **Backward compatibility** for existing code paths (6-month deprecation window)
3. **Zero runtime performance regression**
4. **Type safety** enforced at compile time

---

## Proposed Unified Type Definition

### New `Artifact` Interface

```typescript
/**
 * Unified artifact type for SkillMeat collection and project contexts
 *
 * Consolidates former Artifact and Entity types into a single representation
 * that supports both collection and deployment scenarios.
 */
export interface Artifact {
  // Identity (required)
  id: string;                    // "type:name" format
  name: string;
  type: ArtifactType;           // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'

  // Context (supports collection OR project scope)
  scope: ArtifactScope;          // 'user' | 'local'
  collection?: string;           // Collection name (if in collection scope)
  collections?: CollectionRef[]; // All collections this artifact belongs to
  projectPath?: string;          // Project path (if in project scope)

  // Metadata (flattened from former nested objects)
  description?: string;
  tags?: string[];
  author?: string;
  license?: string;
  version?: string;
  dependencies?: string[];

  // Source & origin
  source?: string;               // GitHub spec or local path
  origin?: 'local' | 'github' | 'marketplace';
  origin_source?: string;        // 'github' | 'gitlab' | 'bitbucket'
  aliases?: string[];

  // Unified status (replaces ArtifactStatus and EntityStatus)
  syncStatus: 'synced' | 'modified' | 'outdated' | 'conflict' | 'error';

  // Upstream tracking (optional, formerly nested)
  upstream?: {
    enabled: boolean;
    url?: string;
    version?: string;
    currentSha?: string;
    upstreamSha?: string;
    updateAvailable: boolean;
    lastChecked?: string;
  };

  // Usage statistics (optional, formerly nested)
  usageStats?: {
    totalDeployments: number;
    activeProjects: number;
    lastUsed?: string;
    usageCount: number;
  };

  // Scoring (optional)
  score?: {
    confidence: number;
    trustScore?: number;
    qualityScore?: number;
    matchScore?: number;
    lastUpdated?: string;
  };

  // Timestamps
  createdAt: string;             // ISO 8601
  updatedAt: string;             // ISO 8601
  deployedAt?: string;           // When deployed (former Entity field)
  modifiedAt?: string;           // Last local modification (former Entity field)
}
```

### Type & Enum Consolidation

```typescript
// Unified artifact type (unchanged, already consistent)
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

// Scope: same as before
export type ArtifactScope = 'user' | 'local';

// **NEW**: Unified status (merge of ArtifactStatus + EntityStatus)
export type SyncStatus = 'synced' | 'modified' | 'outdated' | 'conflict' | 'error';

// Reference types
export interface CollectionRef {
  id: string;
  name: string;
  artifact_count?: number;
}

// Backward compatibility aliases (6-month deprecation window)
export type Entity = Artifact;
export type EntityType = ArtifactType;
export type EntityStatus = SyncStatus;
export type ArtifactStatus = SyncStatus;
export type EntityScope = ArtifactScope;

// (MOVED: ENTITY_TYPES registry renamed to ARTIFACT_TYPES, see Phase 2)
```

### Status Enum Migration Map

| Artifact Status | Entity Status | Unified SyncStatus | Meaning |
|-----------------|---------------|-------------------|---------|
| `active` | `synced` | `synced` | Matches upstream/collection |
| `error` | `conflict` | `conflict` | Unresolvable state issue |
| N/A | `modified` | `modified` | Local changes not in collection |
| `outdated` | `outdated` | `outdated` | Upstream has newer version |
| N/A | `conflict` | `conflict` | Merge conflict |

### API Mapping Function

New single-source-of-truth mapper (replaces all 4 conversion functions):

```typescript
/**
 * Map API ArtifactResponse to unified Artifact type
 *
 * Single source of truth for all API→frontend conversions
 * Replaces: mapApiArtifact(), mapApiArtifactToEntity(), artifactToEntity()
 */
export function mapApiResponseToArtifact(
  response: ArtifactResponse,
  context: 'collection' | 'project' = 'collection'
): Artifact {
  // Determine sync status based on context and upstream state
  const syncStatus = determineSyncStatus(response, context);

  return {
    // Identity
    id: response.id,
    name: response.name,
    type: response.type as ArtifactType,

    // Context
    scope: response.scope,
    collection: response.collection,
    collections: response.collections || [],
    projectPath: context === 'project' ? response.projectPath : undefined,

    // Metadata (flattened)
    description: response.metadata?.description,
    tags: response.metadata?.tags,
    author: response.metadata?.author,
    license: response.metadata?.license,
    version: response.version,
    dependencies: response.metadata?.dependencies,

    // Source
    source: response.source,
    origin: response.origin,
    origin_source: response.origin_source,
    aliases: response.aliases,

    // Status (unified)
    syncStatus,

    // Upstream (optional)
    upstream: response.upstream ? {
      enabled: response.upstream.enabled ?? false,
      url: response.upstream.url,
      version: response.upstream.version,
      currentSha: response.upstream.currentSha,
      upstreamSha: response.upstream.upstreamSha,
      updateAvailable: response.upstream.updateAvailable ?? false,
      lastChecked: response.upstream.lastChecked,
    } : undefined,

    // Usage stats (optional)
    usageStats: response.usageStats ? {
      totalDeployments: response.usageStats.totalDeployments,
      activeProjects: response.usageStats.activeProjects,
      lastUsed: response.usageStats.lastUsed,
      usageCount: response.usageStats.usageCount,
    } : undefined,

    // Timestamps
    createdAt: response.createdAt,
    updatedAt: response.updatedAt,
    deployedAt: response.deployedAt,
    modifiedAt: response.modifiedAt,

    // Score (optional)
    score: response.score,
  };
}

function determineSyncStatus(response: ArtifactResponse, context: string): SyncStatus {
  // Logic to determine current sync state based on:
  // - response.upstream state (if any)
  // - response.localModifications (if any)
  // - response.conflictState (if any)
  // - deployment context
  // Returns one of: synced | modified | outdated | conflict | error
}
```

---

## Migration Strategy

### Phased Rollout (5 phases, 4-6 weeks)

#### Phase 1: Type Definition & Aliases (Week 1)

**Goal**: Establish unified type, ensure backward compatibility

**Tasks**:
- Create new `Artifact` interface in `types/artifact.ts` with all fields
- Create backward compatibility aliases for `Entity`, `EntityType`, `EntityStatus`
- Update `types/artifact.ts` exports to include aliases
- Deprecation notice in `types/entity.ts` (mark as deprecated, re-export from artifact.ts)
- Update TypeScript configuration if needed

**Files Modified**:
- `skillmeat/web/types/artifact.ts` (expanded)
- `skillmeat/web/types/entity.ts` (deprecated, re-export)

**Testing**:
- All existing imports of `Entity` still work
- No runtime behavior changes
- Type safety maintained (both `Entity` and `Artifact` valid in same context)

**Acceptance Criteria**:
- [ ] New `Artifact` interface includes all 25+ properties
- [ ] `Entity` aliased to `Artifact` (backward compatible)
- [ ] All status enum values represented
- [ ] TypeScript compiles without errors
- [ ] No changes to component behavior

---

#### Phase 2: Registry & Config Consolidation (Week 1)

**Goal**: Migrate `ENTITY_TYPES` registry to `ARTIFACT_TYPES`, consolidate form schemas

**Tasks**:
- Create `ARTIFACT_TYPES` registry in `types/artifact.ts` (identical to `ENTITY_TYPES`)
- Create deprecation export: `export const ENTITY_TYPES = ARTIFACT_TYPES`
- Update all imports referencing `ENTITY_TYPES` to use `ARTIFACT_TYPES`
- Add helper: `getArtifactTypeConfig()` (replaces `getEntityTypeConfig()`)
- Create deprecation alias: `export const getEntityTypeConfig = getArtifactTypeConfig`

**Files Modified**:
- `skillmeat/web/types/artifact.ts` (add registry)
- `skillmeat/web/types/entity.ts` (deprecation re-export)
- All component/hook files using `ENTITY_TYPES` (search + update)

**Testing**:
- Form rendering uses `ARTIFACT_TYPES` successfully
- Deprecated `ENTITY_TYPES` still works (backward compatible)
- No visual/behavioral changes

**Acceptance Criteria**:
- [ ] `ARTIFACT_TYPES` registry defined with all 5 types
- [ ] `ENTITY_TYPES` aliased to `ARTIFACT_TYPES`
- [ ] All form schemas preserved
- [ ] ~15-20 files updated to use `ARTIFACT_TYPES`
- [ ] No test failures

---

#### Phase 3: API Mapping Centralization (Week 1-2)

**Goal**: Create single `mapApiResponseToArtifact()` function, eliminate redundant conversions

**Tasks**:
- Create `lib/api/mappers.ts` with `mapApiResponseToArtifact()` function
- Implement `determineSyncStatus()` logic for status enum mapping
- Update `hooks/useArtifacts.ts`: Use new mapper instead of `mapApiArtifact()`
- Update `hooks/useEntityLifecycle.tsx`: Use new mapper instead of `mapApiArtifactToEntity()`
- Remove `artifactToEntity()` from `app/collection/page.tsx` (no longer needed)
- Remove `entityToArtifact()` from `components/sync-status/sync-status-tab.tsx`
- Search for and remove any remaining conversion boilerplate

**Files Modified**:
- NEW: `skillmeat/web/lib/api/mappers.ts`
- `skillmeat/web/hooks/useArtifacts.ts` (simplify)
- `skillmeat/web/hooks/useEntityLifecycle.tsx` (simplify)
- `skillmeat/web/app/collection/page.tsx` (remove conversion)
- `skillmeat/web/components/sync-status/sync-status-tab.tsx` (remove conversion)
- `skillmeat/web/lib/api/index.ts` (export new mapper)

**Testing**:
- Unit tests for `mapApiResponseToArtifact()` covering all status transitions
- Integration tests for both `/collection` and `/manage` pages
- Artifact data displayed identically before/after
- Modal opens with complete data in both contexts

**Acceptance Criteria**:
- [ ] Single `mapApiResponseToArtifact()` function handles all conversions
- [ ] `determineSyncStatus()` correctly maps all status enums
- [ ] All 4 old conversion functions removed or marked as deprecated
- [ ] `/collection` and `/manage` use same mapper
- [ ] Test coverage >85% for mapper function
- [ ] Collections tab populated on /manage page
- [ ] Source tab appears on /collection page without prior /marketplace visit

---

#### Phase 4: Component Type Unification (Week 2-3)

**Goal**: Update all components to accept unified `Artifact` type, remove Entity-specific variants

**Tasks**:
- Update `UnifiedEntityModal` props to accept `Artifact` (not just `Entity`)
- Update all modal-related components to use `Artifact`
- Refactor `app/collection/page.tsx` to use `Artifact` type throughout
- Refactor `app/manage/page.tsx` to use `Artifact` type throughout
- Update form components (`entity-form.tsx`, etc.) to use `Artifact`
- Update display components to handle flattened metadata structure
- Add runtime type guards where needed for optional fields

**Components Affected** (~15-20):
- `components/entity/unified-entity-modal.tsx`
- `components/entity/modal-collections-tab.tsx`
- `components/entity/modal-sources-tab.tsx`
- `components/entity/entity-form.tsx`
- `components/entity/entity-crud-modal.tsx`
- `app/collection/page.tsx`
- `app/manage/page.tsx`
- Related tabs and form fields

**Testing**:
- Component-level tests with `Artifact` props
- Integration tests for form submission (create/edit/delete)
- Modal navigation and handler invocation
- Collections and sources tab data population

**Acceptance Criteria**:
- [ ] All components accept `Artifact` type (not `Entity`)
- [ ] Form component works with flattened metadata
- [ ] Modal handlers (`onNavigateToSource`, etc.) consistently provided
- [ ] No TypeScript errors related to type mismatch
- [ ] All component tests passing
- [ ] Visual regression tests pass

---

#### Phase 5: Deprecation & Cleanup (Week 3-4)

**Goal**: Mark old types/functions as deprecated, document migration path, plan removal

**Tasks**:
- Add JSDoc deprecation notices to `Entity` interface (in entity.ts)
- Add deprecation comment to `types/entity.ts` (file-level)
- Create deprecation guide: `.claude/guides/entity-to-artifact-migration.md`
- Update CLAUDE.md web section to reference `Artifact` (not `Entity`)
- Audit codebase for remaining direct `Entity` type usages (should be rare)
- Document removal timeline (e.g., "Remove Phase 1 of Q2 2026")
- Update existing PRDs/architecture docs to reference unified type

**Files Modified**:
- `skillmeat/web/types/entity.ts` (deprecation notices)
- NEW: `.claude/guides/entity-to-artifact-migration.md`
- `skillmeat/web/CLAUDE.md` (update type references)
- `docs/project_plans/architecture/` (update architecture docs)

**Testing**:
- TypeScript compiler issues listed (if any)
- Deprecation notices appear in IDE hints
- No new code uses `Entity` type

**Acceptance Criteria**:
- [ ] Deprecation notices appear in IDE for old types
- [ ] Migration guide published
- [ ] Code audit completed (remaining Entity usages <10)
- [ ] CLAUDE.md updated to reference Artifact
- [ ] Removal timeline documented

---

### Rollback Plan

Each phase can be rolled back independently:
- **Phase 1 rollback**: Delete new `Artifact` interface, revert aliases
- **Phase 2 rollback**: Keep `ARTIFACT_TYPES`, update imports back to `ENTITY_TYPES`
- **Phase 3 rollback**: Restore old mappers, revert hook implementations
- **Phase 4 rollback**: Restore Entity-specific component variants, update props
- **Phase 5 rollback**: Remove deprecation notices (already in cleanup phase)

**Emergency rollback procedure**: If blockers discovered, revert to last stable commit and file post-mortem.

---

## Requirements

### Functional Requirements

| ID | Requirement | Phase | Acceptance Criteria |
|----|-------------|-------|-------------------|
| FR-1 | Single unified `Artifact` type definition | 1 | New interface with 25+ properties, all tests pass |
| FR-2 | Flattened metadata structure | 1 | `description`, `tags`, `author`, `license` at top level |
| FR-3 | Unified sync status enum | 1 | 5 values: synced \| modified \| outdated \| conflict \| error |
| FR-4 | Deployment context tracking | 1 | `projectPath` field support, no data loss |
| FR-5 | Single API mapper function | 3 | `mapApiResponseToArtifact()`, 0 conversion functions in components |
| FR-6 | Optional nested objects preserved | 1 | `upstream`, `usageStats` optional, structure unchanged |
| FR-7 | Form schema consolidation | 2 | `ARTIFACT_TYPES` registry, all forms work |
| FR-8 | Modal type contract enforcement | 4 | `UnifiedEntityModal` requires `Artifact` + handlers |
| FR-9 | Zero modal/conversion bugs | 4 | Collections tab populated, sources tab appears, navigation works |
| FR-10 | Backward compatibility (6 months) | 1-5 | Old `Entity` imports still work, deprecation warnings |

### Non-Functional Requirements

| ID | Requirement | Phase | Acceptance Criteria |
|----|-------------|-------|-------------------|
| NFR-1 | Type safety | All | TypeScript strict mode, no `any` types in unified mapper |
| NFR-2 | Zero runtime performance regression | All | Bundle size delta <2%, no additional renders |
| NFR-3 | Maintainability | All | Conversion logic <100 lines (down from 400+), well-documented |
| NFR-4 | Test coverage | All | >85% for new mapper, >80% for affected components |
| NFR-5 | No breaking API changes | All | Public APIs stable, internal changes only |
| NFR-6 | Documentation | All | README updated, migration guide written |

---

## Scope

### In Scope

1. **Frontend type consolidation** (SkillMeat web UI)
   - New unified `Artifact` type
   - `ARTIFACT_TYPES` registry and form schemas
   - `mapApiResponseToArtifact()` mapper function
   - Component updates to use `Artifact`
   - Deprecation aliases and migration path

2. **Bug fixes** (as side effects of consolidation)
   - Collections tab empty on /manage page → Fixed by unified mapper
   - Source tab missing on /collection → Fixed by modal data consistency
   - Source link navigation broken → Fixed by consistent handler usage
   - Synthetic fallback artifacts → Eliminated (mapper always provides complete data)

3. **Refactoring** (code cleanup)
   - Remove 4 redundant conversion functions
   - Consolidate form schemas
   - Simplify hooks (useArtifacts, useEntityLifecycle)
   - Update component props and type signatures

4. **Documentation**
   - Migration guide for developers
   - Updated CLAUDE.md with type references
   - Architecture documentation

### Out of Scope

1. **Backend changes** (handled separately)
   - Backend `ArtifactResponse` already uses single schema (no changes needed)
   - Database schema modifications (future work)
   - API endpoint changes (none required)

2. **Other type systems**
   - Collection type system (separate from artifacts)
   - Deployment type system (future work)
   - Analytics/metrics types (future work)

3. **UI/UX changes**
   - No visual changes to pages or components
   - No new features introduced
   - Modal behavior unchanged

4. **Performance optimizations**
   - Caching improvements (future work)
   - Query optimization (future work)
   - Bundle size reduction (secondary goal)

---

## Risks & Mitigations

### Risk 1: Type Compatibility Issues During Migration

**Risk**: Old code expecting `Entity` breaks before all components updated
**Severity**: High
**Mitigation**:
- Phase 1 creates backward compatibility aliases (`Entity = Artifact`)
- Both old and new imports work throughout migration
- TypeScript strict mode catches mismatches during development
- Fallback: Keep deprecated `types/entity.ts` file during 6-month window

---

### Risk 2: Data Loss During Mapper Consolidation

**Risk**: New unified mapper misses fields that old separate mappers handled
**Severity**: High
**Mitigation**:
- Side-by-side testing: Run old and new mappers on same API response, compare output
- Unit tests for all field mappings (25+ properties)
- Integration tests comparing modal data before/after
- QA verification on /collection and /manage pages
- Rollback plan: Restore old mappers if discrepancies found

---

### Risk 3: Incomplete Modal Handler Coverage

**Risk**: Components still omit `onNavigateToSource` or `onNavigateToDeployment` handlers
**Severity**: Medium
**Mitigation**:
- Phase 4 makes handlers required in `UnifiedEntityModal` props
- Runtime warning if handlers missing but artifact has source
- Page-specific modal wrappers ensure handlers provided
- Integration tests verify handlers called correctly

---

### Risk 4: Complex Status Determination Logic

**Risk**: `determineSyncStatus()` function has subtle bugs for edge cases
**Severity**: Medium
**Mitigation**:
- Implement logic incrementally with test coverage for each status transition
- Document status determination rules clearly
- QA testing on artifacts in all possible states (synced, modified, outdated, conflict, error)
- Fallback: Use conservative default if status uncertain (e.g., `error`)

---

### Risk 5: Breaking Changes to Existing Code

**Risk**: Subtle incompatibilities between old `Entity` and new `Artifact` props
**Severity**: Medium
**Mitigation**:
- Run full test suite after each phase
- Use TypeScript strict mode to catch incompatibilities
- Component-level testing before integration
- Manual QA before each phase merge

---

### Risk 6: Performance Regression

**Risk**: New mapper function slower than old parallel pipelines
**Severity**: Low
**Mitigation**:
- Profile old vs new mapper performance (should be identical)
- Monitor bundle size delta (target <2%)
- No additional renders introduced
- Defer optimization if needed (low priority)

---

## Acceptance Criteria

### Phase 1: Type Definition & Aliases

- [ ] New `Artifact` interface defined with all required fields (id, name, type, scope, syncStatus, etc.)
- [ ] All optional fields properly marked with `?`
- [ ] `Entity` interface aliased to `Artifact`
- [ ] `EntityStatus` aliased to `SyncStatus`
- [ ] `types/entity.ts` deprecated with clear notice
- [ ] TypeScript compilation succeeds
- [ ] All type imports (old and new) work
- [ ] No visual or behavioral changes

### Phase 2: Registry & Config Consolidation

- [ ] `ARTIFACT_TYPES` registry defined in `types/artifact.ts`
- [ ] All 5 types (skill, command, agent, mcp, hook) included
- [ ] Form schemas identical to original `ENTITY_TYPES`
- [ ] `ENTITY_TYPES` aliased to `ARTIFACT_TYPES`
- [ ] `getArtifactTypeConfig()` function works
- [ ] ~15-20 files updated to use `ARTIFACT_TYPES`
- [ ] All tests pass
- [ ] Form rendering unchanged

### Phase 3: API Mapping Centralization

- [ ] `mapApiResponseToArtifact()` function defined in `lib/api/mappers.ts`
- [ ] Handles all properties from API `ArtifactResponse`
- [ ] `determineSyncStatus()` correctly maps all status enum values
- [ ] Unit tests for mapper (>85% coverage)
- [ ] Old conversion functions removed from:
  - `hooks/useArtifacts.ts`
  - `hooks/useEntityLifecycle.tsx`
  - `app/collection/page.tsx`
  - `components/sync-status/sync-status-tab.tsx`
- [ ] Collections tab shows data on /manage page
- [ ] Source tab appears on /collection page without prior /marketplace visit
- [ ] Integration tests pass (before/after data identical)

### Phase 4: Component Type Unification

- [ ] `UnifiedEntityModal` accepts `Artifact` type
- [ ] All modal-related components updated
- [ ] `/collection` and `/manage` pages use `Artifact` throughout
- [ ] Form components work with flattened metadata
- [ ] Handlers (`onNavigateToSource`, etc.) consistently provided
- [ ] Component tests pass (>80% coverage)
- [ ] No TypeScript errors
- [ ] Visual regression tests pass

### Phase 5: Deprecation & Cleanup

- [ ] JSDoc deprecation notices on `Entity` interface
- [ ] `.claude/guides/entity-to-artifact-migration.md` written
- [ ] `skillmeat/web/CLAUDE.md` updated
- [ ] Code audit completed (<10 remaining `Entity` usages)
- [ ] Removal timeline documented
- [ ] Architecture docs updated

---

## Related Files & Dependencies

### Type Definitions (Primary Impact)

| File | Lines | Status | Impact |
|------|-------|--------|--------|
| `skillmeat/web/types/artifact.ts` | 105 | Expand | Add properties, add registry |
| `skillmeat/web/types/entity.ts` | 417 | Deprecate | Re-export aliases |
| `skillmeat/web/types/enums.ts` | ~50 | Unchanged | ArtifactType already unified |

### API & Hooks (Medium Impact)

| File | Lines | Function | Change |
|------|-------|----------|--------|
| `skillmeat/web/hooks/useArtifacts.ts` | ~350 | `mapApiArtifact()` | Remove, use unified mapper |
| `skillmeat/web/hooks/useEntityLifecycle.tsx` | ~300 | `mapApiArtifactToEntity()` | Remove, use unified mapper |
| `skillmeat/web/lib/api/` | NEW | `mappers.ts` | Create mapper function |

### Components (High Impact)

| File | Type | Change |
|------|------|--------|
| `skillmeat/web/components/entity/unified-entity-modal.tsx` | Modal | Accept `Artifact` instead of `Entity` |
| `skillmeat/web/components/entity/entity-form.tsx` | Form | Handle flattened metadata |
| `skillmeat/web/app/collection/page.tsx` | Page | Remove `artifactToEntity()` conversion |
| `skillmeat/web/app/manage/page.tsx` | Page | Use `Artifact` type throughout |
| `skillmeat/web/components/sync-status/sync-status-tab.tsx` | Tab | Remove `entityToArtifact()` conversion |

### Backend Reference (No Changes Required)

| File | Status | Reason |
|------|--------|--------|
| `skillmeat/api/schemas/artifacts.py` | Unchanged | Backend already uses single `ArtifactResponse` schema |
| API endpoints | Unchanged | No API contract changes needed |

---

## Open Questions & Assumptions

### Assumptions

1. **Status enum mapping** is deterministic based on API response fields (upstream state, local mods, etc.)
   - *Assumption*: Backend provides sufficient info to determine sync status
   - *Mitigation*: Implement incrementally, QA each status transition
   - *Owner*: Backend architect (API schema review needed)

2. **Flattened metadata** doesn't lose information from nested structures
   - *Assumption*: All nested fields needed at top level; unused nested objects can be optional
   - *Mitigation*: Audit current usage of `metadata.*` fields
   - *Owner*: Frontend architect (Phase 1)

3. **Form schema** for `ARTIFACT_TYPES` matches `ENTITY_TYPES` exactly
   - *Assumption*: No new fields needed, current schema is complete
   - *Mitigation*: Review form logic in all components
   - *Owner*: UI/UX team (Phase 2)

4. **Backward compatibility** for 6 months is acceptable
   - *Assumption*: No immediate deadline to remove `Entity` type
   - *Mitigation*: Document removal timeline, plan for Q2 2026
   - *Owner*: Product management (Phase 5)

### Open Questions for Clarification

**Q1**: Should `projectPath` always be optional, or only when `scope !== 'local'`?
- **Impact**: Type safety for form validation
- **Owner**: Frontend architect
- **Decision needed**: Phase 1

**Q2**: Does `upstream` object need to support partial updates (e.g., only `updateAvailable` changes)?
- **Impact**: API mapper and form field binding
- **Owner**: Backend architect
- **Decision needed**: Phase 3

**Q3**: How should `syncStatus` handle artifacts with no upstream (local-only)?
- **Impact**: `determineSyncStatus()` logic
- **Owner**: Backend architect
- **Decision needed**: Phase 3

---

## Implementation Notes

### Development Workflow

1. Create feature branch: `feat/entity-artifact-consolidation`
2. Implement phases sequentially (Phase 1 complete before Phase 2 starts)
3. Each phase: implement → test → review → merge
4. Run full test suite after each phase merge
5. Daily integration testing on /collection and /manage pages

### Code Review Checklist (Per Phase)

- [ ] All files in phase updated (no stragglers)
- [ ] TypeScript strict mode passes
- [ ] Test coverage >80% for changes
- [ ] Backward compatibility maintained (old imports still work)
- [ ] No performance regressions (bundle size, render count)
- [ ] Migration guide up to date
- [ ] Related documentation updated

### Testing Strategy

**Unit Tests** (Phase 3-4):
- `mapApiResponseToArtifact()` mapper function (all properties, all status values)
- `determineSyncStatus()` logic (all 5 status enum values, edge cases)
- Type definitions (TypeScript compilation)

**Integration Tests** (Phase 3-4):
- `/collection` page data loading and display
- `/manage` page data loading and display
- Modal opening with complete data
- Form submission with new type structure
- Navigation handlers working consistently

**E2E Tests** (Phase 4-5):
- Collection artifact display and interaction
- Artifact CRUD operations
- Modal open/close behavior
- Cross-page navigation (collection → source, artifact → deployment)

**Manual QA** (All phases):
- Visual regression testing
- Collections tab on /manage page (was empty, should be populated)
- Source tab on /collection page (should appear without prior /marketplace visit)
- Navigation links on both pages working

---

## Success Story

After consolidation, a developer adds a new artifact field:

**Before** (duplicated effort):
1. Add field to `Artifact` interface
2. Add field to `Entity` interface
3. Update `mapApiArtifact()` mapper
4. Update `mapApiArtifactToEntity()` mapper
5. Update `artifactToEntity()` converter
6. Update 3+ modal components
7. Update form component if applicable
8. Write tests for each mapping function

**After** (single effort):
1. Add field to `Artifact` interface
2. Update `mapApiResponseToArtifact()` mapper (single function)
3. Update form component if applicable
4. Write tests for mapper and form

Result: **6 fewer places to update, fewer bugs, faster iteration**.

---

## References

### Related Documents

- [`entity-vs-artifact-architecture-analysis.md`](/docs/project_plans/reports/entity-vs-artifact-architecture-analysis.md) - Root cause analysis (2026-01-22)
- [`artifact-modal-architecture-analysis.md`](/docs/project_plans/reports/artifact-modal-architecture-analysis.md) - Bug fixes and architectural recommendations (2026-01-28)
- [`skillmeat/api/schemas/artifacts.py`](/skillmeat/api/schemas/artifacts.py) - Backend `ArtifactResponse` schema (reference)
- [`skillmeat/web/CLAUDE.md`](/skillmeat/web/CLAUDE.md) - Frontend architecture and conventions
- [`skillmeat/web/types/artifact.ts`](/skillmeat/web/types/artifact.ts) - Current artifact type
- [`skillmeat/web/types/entity.ts`](/skillmeat/web/types/entity.ts) - Current entity type (to be deprecated)

### External References

- [TypeScript Handbook: Types](https://www.typescriptlang.org/docs/handbook/)
- [React Patterns: Lifting State Up](https://react.dev/learn/sharing-state-between-components)
- [Next.js 15 App Router](https://nextjs.org/docs/app)

---

**Document Owner**: Frontend Architect
**Last Updated**: 2026-01-28
**Next Review**: Upon Phase 1 completion
**Version**: 1.0
