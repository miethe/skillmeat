# Entity-Artifact Consolidation Context

**PRD**: `docs/project_plans/PRDs/refactors/entity-artifact-consolidation-v1.md`
**Implementation Plan**: `docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1.md`
**Phase Details**: `docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1/`

---

## Overview

Consolidate `Entity` and `Artifact` types into a unified `Artifact` type to eliminate redundant conversion functions and fix modal data inconsistency bugs.

**Key Outcome**: Single source of truth for artifact representation across `/collection` and `/manage` pages.

---

## Architectural Decisions

### AD-1: Flatten Metadata Structure

**Decision**: Metadata properties (description, author, license, tags) moved to top-level of Artifact type.

**Rationale**: Reduces cognitive load and eliminates nested optional chaining (`entity.metadata?.description` -> `artifact.description`).

**Impact**: All components accessing metadata must update property paths.

### AD-2: Unified SyncStatus Enum

**Decision**: Single 5-value enum: `synced | modified | outdated | conflict | error`

**Rationale**: Merges `ArtifactStatus` (4 values) and `EntityStatus` (4 values) with clear semantics for both collection and project contexts.

**Impact**: Status determination logic centralized in `determineSyncStatus()`.

### AD-3: Context-Aware Mapping

**Decision**: `mapApiResponseToArtifact()` accepts context parameter ('collection' | 'project').

**Rationale**: Allows status determination and field inclusion to vary by usage context while using single mapper function.

**Impact**: Hooks must pass correct context when calling mapper.

### AD-4: Backward Compatibility via Type Aliases

**Decision**: `Entity = Artifact` alias maintained for 6-month deprecation window (until Q3 2026).

**Rationale**: Allows gradual migration without breaking existing code.

**Impact**: Old imports continue working but show IDE deprecation warnings.

---

## Important File Paths

### Type Definitions

- `skillmeat/web/types/artifact.ts` - Unified Artifact type, ARTIFACT_TYPES registry
- `skillmeat/web/types/entity.ts` - Deprecated, re-exports from artifact.ts
- `skillmeat/web/types/index.ts` - Barrel export

### API Mappers

- `skillmeat/web/lib/api/mappers.ts` - NEW: mapApiResponseToArtifact()
- `skillmeat/web/lib/api/mappers.test.ts` - NEW: Unit tests

### Hooks

- `skillmeat/web/hooks/useArtifacts.ts` - Collection pipeline
- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Project pipeline

### Components

- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Main modal
- `skillmeat/web/components/entity/modal-*.tsx` - Tab components
- `skillmeat/web/components/entity/entity-form.tsx` - Form component

### Pages

- `skillmeat/web/app/collection/page.tsx` - Collection display
- `skillmeat/web/app/manage/page.tsx` - Management/CRUD

---

## Agent Handoff Notes

### For backend-typescript-architect

**Phase 1-2 Focus**: Type definitions and registry consolidation.
- Create Artifact interface with 25+ properties
- Define SyncStatus enum with 5 values
- Create backward compatibility aliases
- Port ENTITY_TYPES to ARTIFACT_TYPES

**Phase 3 Focus**: API mapper centralization.
- Create single mapApiResponseToArtifact() function
- Implement determineSyncStatus() logic
- Update useArtifacts and useEntityLifecycle hooks
- Remove 4 redundant conversion functions

**Key Files to Read First**:
1. `skillmeat/web/types/artifact.ts` - Current Artifact type
2. `skillmeat/web/types/entity.ts` - Current Entity type (to be deprecated)
3. `skillmeat/web/hooks/useArtifacts.ts` - See mapApiArtifact() to remove
4. `skillmeat/web/hooks/useEntityLifecycle.tsx` - See mapApiArtifactToEntity() to remove

### For ui-engineer-enhanced

**Phase 4 Focus**: Component type unification.
- Update UnifiedEntityModal to accept Artifact
- Update all modal tab components
- Update form components
- Refactor pages to use Artifact throughout

**Key Pattern Change**:
```typescript
// Before (nested metadata)
entity.metadata?.description

// After (flattened)
artifact.description
```

**Navigation Handler Contract**:
Modal must always receive `onNavigateToSource` and `onNavigateToDeployment` handlers when artifact has source field.

### For documentation-writer

**Phase 5 Focus**: Deprecation and documentation.
- Add @deprecated JSDoc to entity.ts exports
- Create migration guide at `.claude/guides/entity-to-artifact-migration.md`
- Update CLAUDE.md with Artifact references
- Audit remaining Entity usages

**Timeline to Document**: Q3 2026 removal date

---

## Open Questions

### Resolved

1. **Q**: Should projectPath be required when scope === 'local'?
   **A**: No, projectPath remains optional. It's only populated in project context.

2. **Q**: How to handle artifacts with no upstream?
   **A**: determineSyncStatus() returns 'synced' for local-only artifacts (no upstream to compare against).

### Open

1. **Q**: Should we rename UnifiedEntityModal to UnifiedArtifactModal?
   **Decision Needed**: Phase 4 (low priority, cosmetic)

2. **Q**: What happens to entity-form.tsx file name?
   **Decision Needed**: Phase 4 (keep name for backward compat, or rename?)

---

## Bug Fixes Addressed

| Bug | Root Cause | Fix Phase |
|-----|------------|-----------|
| Collections tab empty on /manage | Missing field in mapApiArtifactToEntity() | Phase 3 |
| Source tab missing on /collection | Inconsistent modal usage (no handlers) | Phase 3-4 |
| Source link broken | onNavigateToSource not provided | Phase 4 |
| Synthetic fallback artifacts | Parallel conversion pipelines creating inconsistent data | Phase 3 |

---

## Progress Tracking Files

- `.claude/progress/entity-artifact-consolidation/phase-1-2-progress.md`
- `.claude/progress/entity-artifact-consolidation/phase-3-progress.md`
- `.claude/progress/entity-artifact-consolidation/phase-4-5-progress.md`

---

## Related Documents

- **Root Cause Analysis**: `docs/project_plans/reports/entity-vs-artifact-architecture-analysis.md`
- **Modal Architecture**: `docs/project_plans/reports/artifact-modal-architecture-analysis.md`
- **Backend Schema**: `skillmeat/api/schemas/artifacts.py` (reference, no changes needed)

---

**Last Updated**: 2026-01-28
**Document Owner**: ai-artifacts-engineer
