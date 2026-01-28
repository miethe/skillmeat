---
type: progress
prd: "entity-artifact-consolidation"
phase: "1-2"
status: pending
progress: 0
last_updated: "2026-01-28"

tasks:
  # Phase 1: Type Definition & Backward Compatibility
  - id: "P1-T1"
    name: "Create unified Artifact interface"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: []
    model: "opus"
    effort: 5
    files: ["skillmeat/web/types/artifact.ts"]

  - id: "P1-T2"
    name: "Define SyncStatus enum"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P1-T1"]
    model: "opus"
    effort: 2
    files: ["skillmeat/web/types/artifact.ts"]

  - id: "P1-T3"
    name: "Create backward compatibility aliases"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P1-T1", "P1-T2"]
    model: "opus"
    effort: 2
    files: ["skillmeat/web/types/artifact.ts"]

  - id: "P1-T4"
    name: "Update types/entity.ts with deprecation notice"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P1-T3"]
    model: "opus"
    effort: 1
    files: ["skillmeat/web/types/entity.ts"]

  - id: "P1-T5"
    name: "TypeScript compilation and testing"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P1-T4"]
    model: "opus"
    effort: 1
    files: ["skillmeat/web/types/artifact.ts", "skillmeat/web/types/entity.ts", "skillmeat/web/types/index.ts"]

  # Phase 2: Registry Consolidation
  - id: "P2-T1"
    name: "Create ARTIFACT_TYPES registry"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P1-T5"]
    model: "opus"
    effort: 3
    files: ["skillmeat/web/types/artifact.ts"]

  - id: "P2-T2"
    name: "Create ENTITY_TYPES deprecation alias"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P2-T1"]
    model: "sonnet"
    effort: 1
    files: ["skillmeat/web/types/entity.ts"]

  - id: "P2-T3"
    name: "Update all imports to use ARTIFACT_TYPES"
    status: "pending"
    assigned_to: ["backend-typescript-architect", "codebase-explorer"]
    dependencies: ["P2-T2"]
    model: "opus"
    effort: 4
    files: ["skillmeat/web/components/entity/*.tsx", "skillmeat/web/app/collection/page.tsx", "skillmeat/web/app/manage/page.tsx"]

  - id: "P2-T4"
    name: "Validation and testing"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["P2-T3"]
    model: "opus"
    effort: 2
    files: []

parallelization:
  batch_1: ["P1-T1"]
  batch_2: ["P1-T2"]
  batch_3: ["P1-T3"]
  batch_4: ["P1-T4", "P1-T5"]
  batch_5: ["P2-T1"]
  batch_6: ["P2-T2"]
  batch_7: ["P2-T3"]
  batch_8: ["P2-T4"]

quality_gates:
  - "TypeScript strict mode: zero errors"
  - "All existing tests pass"
  - "Old imports still resolve (backward compat)"
  - "IDE shows deprecation warnings for old type names"
  - "No visual or behavioral changes"
  - "Code review approval from 2+ team members"
---

# Phase 1-2: Type Definition & Registry Consolidation

## Quick Reference

### Task() Commands

```
# Phase 1 Tasks
Task("backend-typescript-architect", "Execute P1-T1: Create unified Artifact interface in skillmeat/web/types/artifact.ts with all 25+ properties. See implementation spec in docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1/phase-1-2-types.md", model="opus")

Task("backend-typescript-architect", "Execute P1-T2: Define SyncStatus enum in skillmeat/web/types/artifact.ts with 5 values: synced | modified | outdated | conflict | error. Include STATUS_DESCRIPTIONS constant.", model="opus")

Task("backend-typescript-architect", "Execute P1-T3: Create backward compatibility aliases (Entity = Artifact, EntityType = ArtifactType, etc.) with @deprecated JSDoc notices referencing Q3 2026 removal.", model="opus")

Task("backend-typescript-architect", "Execute P1-T4: Update skillmeat/web/types/entity.ts with deprecation notice and re-exports from artifact.ts.", model="opus")

Task("backend-typescript-architect", "Execute P1-T5: Run TypeScript compilation tests. Verify both old and new imports work. Commands: tsc --noEmit --strict, pnpm test", model="opus")

# Phase 2 Tasks
Task("backend-typescript-architect", "Execute P2-T1: Create ARTIFACT_TYPES registry with all 5 types (skill, command, agent, mcp, hook). Include form schemas, validators, getArtifactTypeConfig() helper.", model="opus")

Task("backend-typescript-architect", "Execute P2-T2: Create ENTITY_TYPES deprecation alias in types/entity.ts pointing to ARTIFACT_TYPES.", model="sonnet")

Task("backend-typescript-architect", "Execute P2-T3: Update all ENTITY_TYPES imports to ARTIFACT_TYPES. Use codebase-explorer to find files. Estimated 15-20 files.", model="opus")

Task("backend-typescript-architect", "Execute P2-T4: Run full validation - TypeScript strict, all tests, manual QA on form rendering.", model="opus")
```

### CLI Updates

```bash
# Single task completion
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/entity-artifact-consolidation/phase-1-2-progress.md \
  -t P1-T1 -s completed

# Batch update (after parallel tasks)
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/entity-artifact-consolidation/phase-1-2-progress.md \
  --updates "P1-T4:completed,P1-T5:completed"
```

## Phase Overview

**Phase 1**: Establish unified `Artifact` type definition with complete backward compatibility through aliases. Create `SyncStatus` enum merging artifact and entity status values.

**Phase 2**: Migrate `ENTITY_TYPES` registry to `ARTIFACT_TYPES` with identical structure. Consolidate form schemas and field validators.

**Total Effort**: 14 story points
**Duration**: 5-7 days
**Dependencies**: None (blocks Phase 3)

---

## Tasks

### P1-T1: Create unified Artifact interface

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 5 points
- **File**: `skillmeat/web/types/artifact.ts`

**Description**: Create expanded `Artifact` interface incorporating all properties from both current `Artifact` and `Entity` types. Flatten nested metadata. Include all optional fields.

**Key Properties**:
- Identity: id, name, type (required)
- Context: scope, collection, collections, projectPath (optional)
- Metadata: description, tags, author, license, version, dependencies (flattened)
- Source: source, origin, origin_source, aliases
- Status: syncStatus (unified)
- Optional nested: upstream, usageStats, score
- Timestamps: createdAt, updatedAt, deployedAt, modifiedAt

**Acceptance Criteria**:
- [ ] New `Artifact` interface includes all 25+ properties with correct optionality
- [ ] Properties clearly documented with JSDoc comments
- [ ] Flattened metadata (no nested `metadata` object)
- [ ] `CollectionRef` interface defined
- [ ] TypeScript compiles without errors

---

### P1-T2: Define SyncStatus enum

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/types/artifact.ts`

**Description**: Create unified `SyncStatus` type merging values from both `ArtifactStatus` and `EntityStatus`.

**Values**: `'synced' | 'modified' | 'outdated' | 'conflict' | 'error'`

**Acceptance Criteria**:
- [ ] `SyncStatus` type defined with all 5 values
- [ ] `STATUS_DESCRIPTIONS` constant with human-readable descriptions
- [ ] Mapping guide documented in JSDoc comments
- [ ] TypeScript compiles without errors

---

### P1-T3: Create backward compatibility aliases

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/types/artifact.ts`

**Description**: Create type aliases for `Entity`, `EntityType`, `EntityStatus`, `ArtifactStatus`, `EntityScope`.

**Aliases**:
```typescript
export type Entity = Artifact;
export type EntityType = ArtifactType;
export type EntityStatus = SyncStatus;
export type ArtifactStatus = SyncStatus;
export type EntityScope = ArtifactScope;
```

**Acceptance Criteria**:
- [ ] All legacy type aliases defined and exported
- [ ] Each alias includes `@deprecated` JSDoc with Q3 2026 removal date
- [ ] Deprecation message references migration guide
- [ ] IDE shows deprecation warning for aliased types

---

### P1-T4: Update types/entity.ts with deprecation notice

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 1 point
- **File**: `skillmeat/web/types/entity.ts`

**Description**: Add prominent deprecation notice and re-export types from `artifact.ts`.

**Acceptance Criteria**:
- [ ] File header includes deprecation notice with migration link
- [ ] All essential types re-exported from artifact.ts
- [ ] Old code importing from entity.ts still works
- [ ] No circular imports

---

### P1-T5: TypeScript compilation and testing

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 1 point
- **Files**: `types/artifact.ts`, `types/entity.ts`, `types/index.ts`

**Testing Commands**:
```bash
# TypeScript strict mode
tsc --noEmit --strict

# Run existing tests
pnpm test

# Verify imports work
tsc --noEmit skillmeat/web/app/collection/page.tsx
tsc --noEmit skillmeat/web/app/manage/page.tsx
```

**Acceptance Criteria**:
- [ ] TypeScript compilation succeeds in strict mode
- [ ] All existing tests pass
- [ ] No type errors in files importing Entity
- [ ] No type errors in files importing Artifact
- [ ] Deprecation warnings appear in IDE

---

### P2-T1: Create ARTIFACT_TYPES registry

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 3 points
- **File**: `skillmeat/web/types/artifact.ts`

**Description**: Create `ARTIFACT_TYPES` registry with identical structure to current `ENTITY_TYPES`. Include form schemas, field mappings, validators for all 5 artifact types.

**Registry Structure**:
```typescript
export const ARTIFACT_TYPES: ArtifactTypeConfig[] = [
  { type: 'skill', label: 'Skill', description: '...', icon: 'BookOpen', fields: [...], required: [...], validators: {...} },
  { type: 'command', label: 'Command', ... },
  { type: 'agent', label: 'Agent', ... },
  { type: 'mcp', label: 'MCP Server', ... },
  { type: 'hook', label: 'Hook', ... },
];
```

**Helpers**:
- `getArtifactTypeConfig(type: ArtifactType): ArtifactTypeConfig`
- `validateArtifactField(type, field, value): boolean`

**Acceptance Criteria**:
- [ ] `ARTIFACT_TYPES` registry defined with all 5 types
- [ ] Form schemas identical to current `ENTITY_TYPES`
- [ ] All field validators present
- [ ] Helper functions work correctly
- [ ] Registry exported from `types/index.ts`

---

### P2-T2: Create ENTITY_TYPES deprecation alias

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: sonnet
- **Effort**: 1 point
- **File**: `skillmeat/web/types/entity.ts`

**Description**: Add deprecation alias for `ENTITY_TYPES` pointing to `ARTIFACT_TYPES`. Create `getEntityTypeConfig()` alias.

**Acceptance Criteria**:
- [ ] `ENTITY_TYPES` aliased to `ARTIFACT_TYPES`
- [ ] `getEntityTypeConfig()` aliased to `getArtifactTypeConfig()`
- [ ] Both old and new names work identically
- [ ] IDE shows deprecation warning for old names

---

### P2-T3: Update all imports to use ARTIFACT_TYPES

- **Status**: pending
- **Agent**: backend-typescript-architect (with codebase-explorer)
- **Model**: opus
- **Effort**: 4 points
- **Files**: ~15-20 component files

**Process**:
```bash
# Find all ENTITY_TYPES usages
grep -r "ENTITY_TYPES" skillmeat/web --include="*.ts" --include="*.tsx"

# Find all getEntityTypeConfig usages
grep -r "getEntityTypeConfig" skillmeat/web --include="*.ts" --include="*.tsx"

# Find imports from types/entity
grep -r "from.*types/entity" skillmeat/web --include="*.ts" --include="*.tsx"
```

**Acceptance Criteria**:
- [ ] All `ENTITY_TYPES` imports updated to `ARTIFACT_TYPES`
- [ ] All `getEntityTypeConfig()` calls updated to `getArtifactTypeConfig()`
- [ ] All updated files compile without TypeScript errors
- [ ] No regression in form rendering or validation
- [ ] All tests pass

---

### P2-T4: Validation and testing

- **Status**: pending
- **Agent**: backend-typescript-architect
- **Model**: opus
- **Effort**: 2 points

**Testing Checklist**:
- [ ] TypeScript strict mode: zero errors
- [ ] All Phase 1-2 tests pass
- [ ] Backward compatibility: 100% (old code works unchanged)
- [ ] Visual regression: zero differences
- [ ] Performance: no bundle size increase
- [ ] Form rendering unchanged visually
- [ ] Form validation works for all types
- [ ] Integration: `/collection` and `/manage` pages load correctly

---

## Quality Gates (Before Phase 3)

- [ ] TypeScript compilation succeeds with strict mode
- [ ] Full test suite passes
- [ ] All backward compatibility aliases work
- [ ] Both old and new type names resolve correctly
- [ ] IDE shows deprecation warnings for old names
- [ ] Form rendering identical before/after
- [ ] Code review approval

---

## Notes

- **Implementation Spec**: `docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1/phase-1-2-types.md`
- **PRD**: `docs/project_plans/PRDs/refactors/entity-artifact-consolidation-v1.md`
