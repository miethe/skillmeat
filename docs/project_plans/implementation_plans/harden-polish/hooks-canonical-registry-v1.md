---
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: hooks-canonical-registry
prd_ref: null
---
# Implementation Plan: Layer 1 - Canonical Hooks Registry

**PRD Reference**: docs/project_plans/reports/agentic-code-mapping-recommendations-2026-01-10.md
**Created**: 2026-01-12
**Status**: done

---

## Executive Summary

Implement Layer 1 of the Agentic Code Mapping Recommendations - creating and enforcing a canonical hooks registry entry point (`hooks/index.ts`) throughout the SkillMeat web frontend.

**Goal**: Establish `@/hooks` as the single import path for all hooks, eliminating direct imports from individual hook files.

**Scope**:
- hooks/index.ts: Already created ✓
- 73 files requiring import updates
- Documentation updates

**Estimated Effort**: 4-6 hours
**Risk Level**: Low (purely additive, backward compatible)

---

## Current State

### Completed
- ✅ `hooks/index.ts` created with 144+ hook exports
- ✅ All 40 hook files covered in barrel export
- ✅ Query key factories exported
- ✅ Deprecation comments for `useDeploy`/`useUndeploy`

### Remaining Work
- 73 files import hooks directly from individual files
- Documentation needs updating to reflect new pattern
- ESLint rule needed to enforce pattern (future Phase 2)

---

## Implementation Strategy

### Approach: Systematic File-by-File with Batching

1. Update imports by category (pages → components → tests)
2. Run type check after each batch
3. Run tests after major batches
4. Commit incrementally

### Why Not Bulk Find-Replace?

- Some files have multiple imports that should be merged
- Type-only imports need special handling
- Namespace imports need conversion to named imports
- Incremental commits allow easy rollback

---

## Phase Breakdown

### Phase 1: App Routes (16 files)
**Effort**: 1 hour | **Assigned**: ui-engineer

Update all page.tsx files in app/ directory:
- `app/collection/page.tsx`
- `app/context-entities/page.tsx`
- `app/deployments/page.tsx`
- `app/marketplace/*.tsx` (4 files)
- `app/mcp/*.tsx` (2 files)
- `app/projects/*.tsx` (4 files)
- `app/templates/page.tsx`

**Quality Gate**: `pnpm type-check` passes

### Phase 2: Core Collection Components (11 files)
**Effort**: 45 min | **Assigned**: ui-engineer

Update all collection/ component files:
- `components/collection/artifact-detail.tsx`
- `components/collection/collection-switcher.tsx`
- `components/collection/conflict-resolver.tsx`
- `components/collection/create-collection-dialog.tsx`
- `components/collection/deploy-dialog.tsx`
- `components/collection/edit-collection-dialog.tsx`
- `components/collection/grouped-artifact-view.tsx`
- `components/collection/manage-groups-dialog.tsx`
- `components/collection/move-copy-dialog.tsx`
- `components/collection/progress-indicator.tsx`
- `components/collection/sync-dialog.tsx`

**Quality Gate**: `pnpm type-check` passes

### Phase 3: Entity & Dashboard Components (13 files)
**Effort**: 45 min | **Assigned**: ui-engineer

Update entity/ and dashboard/ component files:
- `components/entity/*.tsx` (7 files)
- `components/dashboard/*.tsx` (5 files)
- `context/collection-context.tsx` (1 file)

**Quality Gate**: `pnpm type-check` passes

### Phase 4: Marketplace & Discovery Components (12 files)
**Effort**: 45 min | **Assigned**: ui-engineer

Update marketplace/ and discovery/ component files:
- `components/marketplace/*.tsx` (8 files)
- `components/discovery/*.tsx` (4 files)

**Quality Gate**: `pnpm type-check` passes

### Phase 5: History, Merge & Other Components (15 files)
**Effort**: 45 min | **Assigned**: ui-engineer

Update remaining component files:
- `components/history/*.tsx` (4 files)
- `components/merge/*.tsx` (2 files)
- `components/mcp/*.tsx` (1 file)
- `components/sharing/*.tsx` (3 files)
- `components/sync-status/*.tsx` (1 file)
- `components/ui/tag-filter-popover.tsx` (1 file)
- `components/manage/components/*.tsx` (1 file)
- Root components (3 files)

**Quality Gate**: `pnpm type-check` passes

### Phase 6: Test Files (16 files)
**Effort**: 45 min | **Assigned**: ui-engineer

Update all test files:
- `__tests__/a11y/*.tsx` (2 files)
- `__tests__/components/**/*.tsx` (4 files)
- `__tests__/hooks/*.tsx` (5 files)
- `__tests__/integration/*.tsx` (2 files)
- `__tests__/marketplace/*.tsx` (2 files)
- `__tests__/useProjectCache.test.tsx` (1 file)

**Special Handling**: Convert namespace imports to named imports

**Quality Gate**: `pnpm test` passes

### Phase 7: Documentation Updates
**Effort**: 30 min | **Assigned**: documentation-writer

Update documentation to reflect new pattern:
- `.claude/rules/web/hooks.md` - Add registry section
- `skillmeat/web/CLAUDE.md` - Update hooks section
- Update any README references

**Quality Gate**: Documentation review

### Phase 8: Cleanup
**Effort**: 15 min | **Assigned**: ui-engineer

- Remove temporary analysis files (.claude/analysis/*)
- Remove HOOKS_IMPORT_AUDIT.md (root)
- Verify all imports use `@/hooks`
- Final test run

**Quality Gate**: Full test suite passes, type check passes

---

## Task Breakdown

### Phase 1 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 1.1 | Update collection/page.tsx | Convert 7 direct imports to barrel | Imports from `@/hooks` only | ui-engineer |
| 1.2 | Update context-entities/page.tsx | Convert 2 direct imports | Imports from `@/hooks` only | ui-engineer |
| 1.3 | Update deployments/page.tsx | Convert 1 direct import | Imports from `@/hooks` only | ui-engineer |
| 1.4 | Update marketplace pages | Convert 4 page imports | All marketplace pages use `@/hooks` | ui-engineer |
| 1.5 | Update mcp pages | Convert 2 page imports | All mcp pages use `@/hooks` | ui-engineer |
| 1.6 | Update projects pages | Convert 4 page imports | All projects pages use `@/hooks` | ui-engineer |
| 1.7 | Update templates page | Convert 1 direct import | Imports from `@/hooks` only | ui-engineer |
| 1.8 | Type check Phase 1 | Run pnpm type-check | No errors | ui-engineer |

### Phase 2 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 2.1 | Update collection dialogs | Convert 6 dialog imports | All dialogs use `@/hooks` | ui-engineer |
| 2.2 | Update collection views | Convert 5 view imports | All views use `@/hooks` | ui-engineer |
| 2.3 | Type check Phase 2 | Run pnpm type-check | No errors | ui-engineer |

### Phase 3 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 3.1 | Update entity components | Convert 7 component imports | All entity components use `@/hooks` | ui-engineer |
| 3.2 | Update dashboard components | Convert 5 widget imports | All dashboard components use `@/hooks` | ui-engineer |
| 3.3 | Update collection context | Convert context provider imports | Context uses `@/hooks` | ui-engineer |
| 3.4 | Type check Phase 3 | Run pnpm type-check | No errors | ui-engineer |

### Phase 4 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 4.1 | Update marketplace modals | Convert 8 modal imports | All modals use `@/hooks` | ui-engineer |
| 4.2 | Update discovery modals | Convert 4 modal imports | All modals use `@/hooks` | ui-engineer |
| 4.3 | Type check Phase 4 | Run pnpm type-check | No errors | ui-engineer |

### Phase 5 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 5.1 | Update history components | Convert 4 component imports | All history components use `@/hooks` | ui-engineer |
| 5.2 | Update merge components | Convert 2 component imports | All merge components use `@/hooks` | ui-engineer |
| 5.3 | Update remaining components | Convert 9 misc imports | All remaining components use `@/hooks` | ui-engineer |
| 5.4 | Type check Phase 5 | Run pnpm type-check | No errors | ui-engineer |

### Phase 6 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 6.1 | Update a11y tests | Convert 2 test imports | Tests use `@/hooks` | ui-engineer |
| 6.2 | Update component tests | Convert 4 test imports | Tests use `@/hooks` | ui-engineer |
| 6.3 | Update hook tests | Convert 5 test imports | Tests use `@/hooks` | ui-engineer |
| 6.4 | Update integration tests | Convert 2 test imports | Tests use `@/hooks` | ui-engineer |
| 6.5 | Update marketplace tests | Convert namespace imports | Tests use named imports from `@/hooks` | ui-engineer |
| 6.6 | Run full test suite | Run pnpm test | All tests pass | ui-engineer |

### Phase 7 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 7.1 | Update hooks.md rule | Add registry pattern section | Registry documented | documentation-writer |
| 7.2 | Update web CLAUDE.md | Update hooks section | CLAUDE.md reflects registry | documentation-writer |

### Phase 8 Tasks

| ID | Task | Description | Acceptance Criteria | Assigned |
|-----|------|-------------|---------------------|----------|
| 8.1 | Remove analysis files | Delete .claude/analysis/* | Analysis files removed | ui-engineer |
| 8.2 | Remove audit file | Delete HOOKS_IMPORT_AUDIT.md | Audit file removed | ui-engineer |
| 8.3 | Final validation | Full type check + test | All checks pass | ui-engineer |

---

## Import Transformation Pattern

### Before (Direct Import)
```typescript
import { useCollections } from '@/hooks/use-collections';
import { useGroups } from '@/hooks/use-groups';
import { useToast } from '@/hooks/use-toast';
```

### After (Barrel Import)
```typescript
import { useCollections, useGroups, useToast } from '@/hooks';
```

### Special Cases

**Type-only imports** (keep separate):
```typescript
import type { CollectionFilters } from '@/hooks';
```

**Namespace imports** (convert to named):
```typescript
// Before
import * as useMarketplaceSources from '@/hooks/useMarketplaceSources';

// After
import { useSources, useCreateSource, sourceKeys } from '@/hooks';
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Breaking imports | Low | Medium | Type check after each phase |
| Missing exports in index.ts | Low | Low | Index already verified complete |
| Test failures | Low | Low | Run tests incrementally |
| IDE autocomplete issues | Very Low | Low | Barrel exports well-supported |

---

## Success Criteria

- [ ] All 73 files import from `@/hooks` barrel export
- [ ] Zero direct imports from individual hook files (except within hooks/)
- [ ] `pnpm type-check` passes
- [ ] `pnpm test` passes
- [ ] `pnpm build` succeeds
- [ ] Documentation updated
- [ ] Analysis artifacts cleaned up

---

## Commands Reference

```bash
# Type check
pnpm type-check

# Run tests
pnpm test

# Build
pnpm build

# Lint
pnpm lint
```

---

## Related Documents

- **Original Report**: `docs/project_plans/reports/agentic-code-mapping-recommendations-2026-01-10.md`
- **Hooks Index**: `skillmeat/web/hooks/index.ts`
- **Hooks Rules**: `.claude/rules/web/hooks.md`
- **Import Audit**: `HOOKS_IMPORT_AUDIT.md` (temporary)
