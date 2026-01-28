---
type: progress
prd: "entity-artifact-consolidation"
phase: "3"
status: pending
progress: 0
last_updated: "2026-01-28"

tasks:
  - id: "P3-T1"
    name: "Create mapApiResponseToArtifact() function"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P2-T4"]
    model: "opus"
    effort: 4
    files: ["skillmeat/web/lib/api/mappers.ts"]

  - id: "P3-T2"
    name: "Implement unit tests for mapper"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P3-T1"]
    model: "opus"
    effort: 3
    files: ["skillmeat/web/lib/api/mappers.test.ts"]

  - id: "P3-T3"
    name: "Update useArtifacts hook"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P3-T1"]
    model: "opus"
    effort: 2
    files: ["skillmeat/web/hooks/useArtifacts.ts"]

  - id: "P3-T4"
    name: "Update useEntityLifecycle hook"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P3-T1"]
    model: "opus"
    effort: 2
    files: ["skillmeat/web/hooks/useEntityLifecycle.tsx"]

  - id: "P3-T5"
    name: "Remove conversion functions from pages"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P3-T3", "P3-T4"]
    model: "opus"
    effort: 2
    files: ["skillmeat/web/app/collection/page.tsx", "skillmeat/web/components/sync-status/sync-status-tab.tsx"]

  - id: "P3-T6"
    name: "Integration testing and validation"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P3-T5"]
    model: "opus"
    effort: 3
    files: ["skillmeat/web/hooks/useArtifacts.integration.test.ts"]

parallelization:
  batch_1: ["P3-T1"]
  batch_2: ["P3-T2", "P3-T3", "P3-T4"]
  batch_3: ["P3-T5"]
  batch_4: ["P3-T6"]

quality_gates:
  - "mapApiResponseToArtifact() handles all 25+ properties"
  - "determineSyncStatus() handles all 5 status values"
  - "All 4 old conversion functions removed"
  - "Unit tests >85% coverage for mappers.ts"
  - "Integration tests pass"
  - "Collections tab populated on /manage (bug fix verified)"
  - "Source tab appears on /collection (bug fix verified)"
  - "No data loss in conversion"
---

# Phase 3: API Mapper Centralization

## Quick Reference

### Task() Commands

```
# Create mapper function
Task("backend-typescript-architect", "Execute P3-T1: Create lib/api/mappers.ts with mapApiResponseToArtifact() and determineSyncStatus(). Single source of truth for all API->frontend conversions. See spec in docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1/phase-3-mappers.md", model="opus")

# Write unit tests
Task("backend-typescript-architect", "Execute P3-T2: Create lib/api/mappers.test.ts with comprehensive unit tests. Cover all 25+ properties, all 5 status values, edge cases. Target >85% coverage.", model="opus")

# Update hooks (can run in parallel)
Task("backend-typescript-architect", "Execute P3-T3: Update hooks/useArtifacts.ts to use mapApiResponsesToArtifacts(). Remove old mapApiArtifact() function.", model="opus")

Task("backend-typescript-architect", "Execute P3-T4: Update hooks/useEntityLifecycle.tsx to use mapApiResponsesToArtifacts(). Remove old mapApiArtifactToEntity() function.", model="opus")

# Remove page-level conversions
Task("backend-typescript-architect", "Execute P3-T5: Remove artifactToEntity() from app/collection/page.tsx and entityToArtifact() from components/sync-status/sync-status-tab.tsx. Use direct assignment instead.", model="opus")

# Integration testing
Task("backend-typescript-architect", "Execute P3-T6: Run integration tests for mapper consolidation. Verify modal receives complete data from both /collection and /manage pages. Verify bug fixes.", model="opus")
```

### CLI Updates

```bash
# Single task completion
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/entity-artifact-consolidation/phase-3-progress.md \
  -t P3-T1 -s completed

# Batch update after parallel tasks
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/entity-artifact-consolidation/phase-3-progress.md \
  --updates "P3-T2:completed,P3-T3:completed,P3-T4:completed"
```

## Phase Overview

**Goal**: Create single `mapApiResponseToArtifact()` function as the authoritative converter. Implement `determineSyncStatus()` logic. Update hooks and pages. Remove all 4 redundant conversion functions.

**Total Effort**: 12 story points (adjusted from 16)
**Duration**: 4-5 days
**Dependencies**: Phase 1-2 complete (types and registry)
**Critical Path**: Yes (blocks Phase 4)

---

## Tasks

### P3-T1: Create mapApiResponseToArtifact() function

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 4 points
- **File**: `skillmeat/web/lib/api/mappers.ts` (NEW)

**Description**: Create new mapper file with `mapApiResponseToArtifact()` as the single source of truth. Implement `determineSyncStatus()` for accurate status mapping. Include batch converter and validation helper.

**Functions to Create**:
- `mapApiResponseToArtifact(response, context)` - Main mapper
- `determineSyncStatus(response, context)` - Status determination
- `mapApiResponsesToArtifacts(responses, context)` - Batch converter
- `validateArtifactMapping(artifact)` - Validation helper

**Status Determination Logic**:
1. Error takes priority (response.syncStatus === 'error' or response.error)
2. Conflict (response.syncStatus === 'conflict' or conflictState.hasConflict)
3. Modified (project context only, modifiedAt > deployedAt)
4. Outdated (upstream.updateAvailable or SHA mismatch)
5. Default: synced

**Acceptance Criteria**:
- [ ] `mapApiResponseToArtifact()` function implemented
- [ ] All 25+ artifact properties mapped correctly
- [ ] Flattened metadata structure (no nested object)
- [ ] `determineSyncStatus()` handles all 5 status values
- [ ] Context parameter affects projectPath inclusion
- [ ] Batch converter works
- [ ] Validation helper works
- [ ] JSDoc documentation complete

---

### P3-T2: Implement unit tests for mapper

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 3 points
- **File**: `skillmeat/web/lib/api/mappers.test.ts` (NEW)

**Test Categories**:
- Required fields mapping (id, name, type)
- Metadata flattening
- Context handling (collection vs project)
- Status determination (all 5 values)
- Optional nested objects (upstream, usageStats)
- Batch conversion
- Validation helper

**Acceptance Criteria**:
- [ ] >85% code coverage for mappers.ts
- [ ] All property mapping tested
- [ ] All 5 status values tested
- [ ] Edge cases covered (missing fields, null values)
- [ ] Context parameter behavior tested
- [ ] All tests pass

---

### P3-T3: Update useArtifacts hook

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/hooks/useArtifacts.ts`

**Changes**:
- Import `mapApiResponsesToArtifacts` from `@/lib/api/mappers`
- Remove old `mapApiArtifact()` function (~60 lines)
- Update `useInfiniteArtifacts` query to use new mapper
- Update `useInfiniteCollectionArtifacts` to use new mapper

**Acceptance Criteria**:
- [ ] Old `mapApiArtifact()` function removed
- [ ] Hook uses `mapApiResponsesToArtifacts()` from new mapper
- [ ] All hook queries use unified mapper
- [ ] TypeScript compilation succeeds
- [ ] Hook return type unchanged externally (Artifact[])
- [ ] All tests pass

---

### P3-T4: Update useEntityLifecycle hook

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/hooks/useEntityLifecycle.tsx`

**Changes**:
- Import `mapApiResponsesToArtifacts` from `@/lib/api/mappers`
- Remove old `mapApiArtifactToEntity()` function (~60 lines)
- Update queries to use new mapper with appropriate context
- CRUD operations remain unchanged

**Acceptance Criteria**:
- [ ] Old `mapApiArtifactToEntity()` function removed
- [ ] Hook uses `mapApiResponsesToArtifacts()` from new mapper
- [ ] Context parameter passed correctly (collection vs project)
- [ ] Hook return type unchanged (Entity/Artifact[])
- [ ] CRUD operations unaffected
- [ ] All tests pass

---

### P3-T5: Remove conversion functions from pages

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 2 points
- **Files**:
  - `skillmeat/web/app/collection/page.tsx`
  - `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Changes in collection/page.tsx**:
- Remove `artifactToEntity()` function (~40 lines)
- Update `handleArtifactClick` to use direct assignment
- No conversion needed (Artifact = Entity alias)

**Changes in sync-status-tab.tsx**:
- Remove `entityToArtifact()` function (~30 lines)
- Use direct assignment instead

**Acceptance Criteria**:
- [ ] `artifactToEntity()` removed from collection/page.tsx
- [ ] `entityToArtifact()` removed from sync-status-tab.tsx
- [ ] All usages updated to direct assignment
- [ ] TypeScript compilation succeeds
- [ ] Modal still opens with complete data

---

### P3-T6: Integration testing and validation

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 3 points
- **File**: `skillmeat/web/hooks/useArtifacts.integration.test.ts` (NEW)

**Integration Tests**:
- Collection pipeline (useArtifacts + mapper)
- Project pipeline (useEntityLifecycle + mapper)
- Data consistency between pipelines
- Modal data completeness
- Status determination accuracy

**Bug Fix Verification**:
- [ ] Collections tab populated on /manage page (was empty)
- [ ] Source tab appears on /collection page (was missing)
- [ ] Source link navigation works
- [ ] No synthetic fallback artifacts

**Manual QA Checklist**:
- [ ] `/collection` page loads with real data
- [ ] `/manage` page loads with collections data
- [ ] Modal opens with complete data from both pages
- [ ] Form CRUD operations work
- [ ] No console errors or warnings

**Acceptance Criteria**:
- [ ] Integration tests pass (>85% coverage)
- [ ] All 4 old mapper functions removed
- [ ] New mapper used consistently
- [ ] Modal receives complete data from both pages
- [ ] Bug fixes verified
- [ ] Manual QA passes

---

## Quality Gates (Before Phase 4)

- [ ] Single `mapApiResponseToArtifact()` function created
- [ ] All 4 old conversion functions removed:
  - `mapApiArtifact()` in useArtifacts.ts
  - `mapApiArtifactToEntity()` in useEntityLifecycle.tsx
  - `artifactToEntity()` in collection/page.tsx
  - `entityToArtifact()` in sync-status-tab.tsx
- [ ] Both hook pipelines use new mapper
- [ ] Unit tests >85% coverage
- [ ] Integration tests pass
- [ ] Collections tab populated on /manage (bug fix)
- [ ] Source tab appears on /collection (bug fix)
- [ ] No data loss in conversion
- [ ] TypeScript compilation succeeds
- [ ] Manual QA verification complete

---

## Notes

- **Implementation Spec**: `docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1/phase-3-mappers.md`
- **PRD**: `docs/project_plans/PRDs/refactors/entity-artifact-consolidation-v1.md`
- **Key Files to Delete/Modify**:
  - Remove: ~200 lines of conversion logic across 4 files
  - Add: ~150 lines in new mappers.ts + tests
