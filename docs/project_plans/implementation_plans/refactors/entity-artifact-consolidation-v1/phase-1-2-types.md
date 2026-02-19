---
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: entity-artifact-consolidation
prd_ref: null
plan_ref: null
---
# Phase 1-2: Type Definition & Registry Consolidation

**Phases**: 1 & 2 (combined for type-level changes)
**Effort**: 14 story points
**Duration**: 5-7 days
**Dependencies**: None (blocks Phase 3)

---

## Phase 1: Type Definition & Backward Compatibility

### Goal
Establish unified `Artifact` type definition with complete backward compatibility through aliases. Create `SyncStatus` enum merging artifact and entity status values.

### Phase 1 Tasks

#### P1-T1: Create Unified Artifact Interface

**Task ID**: P1-T1
**Effort**: 5 points
**Duration**: 1 day
**Assigned**: `backend-typescript-architect`

**Description**:
Create expanded `Artifact` interface in `types/artifact.ts` incorporating all properties from both current `Artifact` and `Entity` types. Flatten nested metadata from current `Artifact` structure. Include all optional fields with proper TypeScript optional markers.

**File**: `skillmeat/web/types/artifact.ts`

**Changes**:
```typescript
/**
 * Unified artifact type for SkillMeat collection and project contexts.
 *
 * Consolidates former Artifact and Entity types into a single representation
 * that supports both collection and deployment scenarios.
 *
 * @version 2.0.0
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
  syncStatus: SyncStatus;

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

export interface CollectionRef {
  id: string;
  name: string;
  artifact_count?: number;
}
```

**Acceptance Criteria**:
- [ ] New `Artifact` interface includes all 25+ properties with correct optionality
- [ ] Properties clearly documented with JSDoc comments
- [ ] Flattened metadata (no nested `metadata` object)
- [ ] Optional nested objects preserved (`upstream`, `usageStats`, `score`)
- [ ] `CollectionRef` interface defined
- [ ] TypeScript compiles without errors
- [ ] No changes to component behavior

**Testing**:
- Type checking passes in strict mode
- Import path works: `import { Artifact } from '@/types'`
- All new properties accessible in component code

---

#### P1-T2: Define SyncStatus Enum

**Task ID**: P1-T2
**Effort**: 2 points
**Duration**: 0.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Create unified `SyncStatus` type merging values from both `ArtifactStatus` (active | outdated | conflict | error) and `EntityStatus` (synced | modified | outdated | conflict). Define as 5-value enum.

**File**: `skillmeat/web/types/artifact.ts`

**Changes**:
```typescript
/**
 * Unified synchronization status enum.
 *
 * Represents the sync state of an artifact across both collection
 * and deployment contexts. Replaces former ArtifactStatus and EntityStatus.
 */
export type SyncStatus = 'synced' | 'modified' | 'outdated' | 'conflict' | 'error';

/**
 * Status mapping guide:
 *
 * Collection context:
 *   - synced: Artifact matches collection version
 *   - outdated: Newer version available upstream
 *   - conflict: Unresolvable conflict with upstream
 *   - error: Error fetching or processing
 *
 * Project context:
 *   - synced: Deployed artifact matches source
 *   - modified: Local changes not in source
 *   - outdated: Source has newer version
 *   - conflict: Merge conflict between local and source
 *   - error: Error in deployment or sync process
 */

// Status transition documentation
export const STATUS_DESCRIPTIONS: Record<SyncStatus, string> = {
  synced: 'Up to date with source',
  modified: 'Local modifications not in source',
  outdated: 'Newer version available',
  conflict: 'Unresolvable conflict',
  error: 'Error in sync process',
};
```

**Acceptance Criteria**:
- [ ] `SyncStatus` type defined with all 5 values
- [ ] Status descriptions documented for all values
- [ ] Mapping guide from old enums clear and documented
- [ ] TypeScript compiles without errors

---

#### P1-T3: Create Backward Compatibility Aliases

**Task ID**: P1-T3
**Effort**: 2 points
**Duration**: 0.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Create type aliases in `types/artifact.ts` for `Entity`, `EntityType`, `EntityStatus`, `ArtifactStatus`, and related types. These allow old code to continue working without modification during deprecation window.

**File**: `skillmeat/web/types/artifact.ts`

**Changes**:
```typescript
// Backward compatibility aliases (6-month deprecation window)
// These are replaced incrementally over time. See entity-to-artifact-migration.md

/**
 * @deprecated Use `Artifact` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type Entity = Artifact;

/**
 * @deprecated Use `ArtifactType` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityType = ArtifactType;

/**
 * @deprecated Use `SyncStatus` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityStatus = SyncStatus;

/**
 * @deprecated Use `SyncStatus` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type ArtifactStatus = SyncStatus;

/**
 * @deprecated Use `ArtifactScope` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityScope = ArtifactScope;
```

**Acceptance Criteria**:
- [ ] All legacy type aliases defined and exported
- [ ] Each alias includes `@deprecated` JSDoc with removal date
- [ ] Deprecation message references migration guide
- [ ] Old imports still resolve (verified with test imports)
- [ ] IDE shows deprecation warning for aliased types

**Testing**:
```typescript
// Both imports should work identically
import type { Entity } from '@/types';
import type { Artifact } from '@/types';

// TypeScript should treat Entity === Artifact
const entity: Entity = artifact; // No type error
const artifact2: Artifact = entity; // No type error
```

---

#### P1-T4: Update types/entity.ts with Deprecation Notice

**Task ID**: P1-T4
**Effort**: 1 point
**Duration**: 0.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Update `types/entity.ts` file to import and re-export types from `types/artifact.ts`. Add prominent deprecation notice at top of file. Keep file for backward compatibility but mark all exports as deprecated.

**File**: `skillmeat/web/types/entity.ts`

**Changes**:
```typescript
/**
 * DEPRECATED: This file is maintained for backward compatibility only.
 *
 * All type definitions have been consolidated into types/artifact.ts
 * under a unified Artifact type system.
 *
 * MIGRATION REQUIRED:
 * - Replace all imports of Entity with Artifact
 * - Replace EntityStatus with SyncStatus
 * - Replace ENTITY_TYPES with ARTIFACT_TYPES
 *
 * See: .claude/guides/entity-to-artifact-migration.md
 * Removal Date: Q3 2026
 */

// Re-export all types from artifact.ts for backward compatibility
export type {
  Artifact as Entity,
  ArtifactType as EntityType,
  SyncStatus as EntityStatus,
  ArtifactScope as EntityScope,
  ArtifactScope as EntityScope,
} from './artifact';

export { STATUS_DESCRIPTIONS } from './artifact';

// All other exports remain unchanged (ENTITY_TYPES, etc. handled in Phase 2)
```

**Acceptance Criteria**:
- [ ] File header includes deprecation notice with migration link
- [ ] All essential types re-exported from artifact.ts
- [ ] Old code importing from entity.ts still works
- [ ] IDE shows deprecation warnings for entity.ts imports
- [ ] No circular imports

---

#### P1-T5: TypeScript Compilation & Testing

**Task ID**: P1-T5
**Effort**: 1 point
**Duration**: 0.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Verify TypeScript compilation succeeds with strict mode. Run type checking across all files using old type names to ensure backward compatibility works. Create simple test file verifying both old and new type imports work.

**Files**:
- `skillmeat/web/types/artifact.ts`
- `skillmeat/web/types/entity.ts`
- `skillmeat/web/types/index.ts` (exports)

**Testing Checklist**:
```bash
# TypeScript strict mode
tsc --noEmit --strict

# Run existing tests (should all pass)
pnpm test

# Type checking on key files that use Entity type
tsc --noEmit skillmeat/web/app/collection/page.tsx
tsc --noEmit skillmeat/web/app/manage/page.tsx
tsc --noEmit skillmeat/web/components/entity/*.tsx
```

**Acceptance Criteria**:
- [ ] TypeScript compilation succeeds in strict mode
- [ ] All existing tests pass
- [ ] No type errors in files importing Entity (backward compat working)
- [ ] No type errors in files importing Artifact
- [ ] Deprecation warnings appear in IDE for entity.ts imports
- [ ] Visual regression tests pass (no UI changes)

---

## Phase 2: Registry Consolidation

### Goal
Migrate `ENTITY_TYPES` registry to `ARTIFACT_TYPES` with identical structure. Consolidate form schemas and field validators. Create deprecation alias for backward compatibility.

### Phase 2 Tasks

#### P2-T1: Create ARTIFACT_TYPES Registry

**Task ID**: P2-T1
**Effort**: 3 points
**Duration**: 1.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Create `ARTIFACT_TYPES` registry in `types/artifact.ts` with identical structure to current `ENTITY_TYPES`. Registry includes form schemas, field mappings, validators for all 5 artifact types (skill, command, agent, mcp, hook).

**File**: `skillmeat/web/types/artifact.ts`

**Changes**:
```typescript
/**
 * Artifact type configuration and form schema registry.
 *
 * Defines all artifact types, their field requirements, form layouts,
 * and validation rules. Used by form components and type introspection.
 */
export const ARTIFACT_TYPES: ArtifactTypeConfig[] = [
  {
    type: 'skill',
    label: 'Skill',
    description: 'Reusable skill or capability',
    icon: 'BookOpen',
    fields: ['name', 'description', 'tags', 'author', 'license', 'version', 'dependencies'],
    required: ['name', 'type'],
    validators: {
      name: (value: string) => value.length > 0 && value.length <= 255,
      description: (value: string) => value.length <= 2000,
      tags: (value: string[]) => value.every(tag => tag.length > 0 && tag.length <= 100),
    },
  },
  {
    type: 'command',
    label: 'Command',
    description: 'CLI command or utility',
    icon: 'Terminal',
    fields: ['name', 'description', 'tags', 'author', 'license', 'version'],
    required: ['name', 'type'],
    validators: {
      name: (value: string) => value.length > 0 && value.length <= 255,
      description: (value: string) => value.length <= 2000,
    },
  },
  {
    type: 'agent',
    label: 'Agent',
    description: 'Autonomous agent or orchestration',
    icon: 'Bot',
    fields: ['name', 'description', 'tags', 'author', 'license', 'version', 'dependencies'],
    required: ['name', 'type'],
    validators: {
      name: (value: string) => value.length > 0 && value.length <= 255,
      description: (value: string) => value.length <= 2000,
    },
  },
  {
    type: 'mcp',
    label: 'MCP Server',
    description: 'Model Context Protocol server',
    icon: 'Zap',
    fields: ['name', 'description', 'tags', 'author', 'license', 'version', 'dependencies'],
    required: ['name', 'type'],
    validators: {
      name: (value: string) => value.length > 0 && value.length <= 255,
      description: (value: string) => value.length <= 2000,
    },
  },
  {
    type: 'hook',
    label: 'Hook',
    description: 'Event hook or trigger',
    icon: 'Link',
    fields: ['name', 'description', 'tags', 'author', 'license', 'version'],
    required: ['name', 'type'],
    validators: {
      name: (value: string) => value.length > 0 && value.length <= 255,
      description: (value: string) => value.length <= 2000,
    },
  },
];

/**
 * Get configuration for a specific artifact type.
 * @param type - The artifact type (skill | command | agent | mcp | hook)
 * @returns Type configuration including fields, validators, and form schema
 * @throws Error if type not found
 */
export function getArtifactTypeConfig(type: ArtifactType): ArtifactTypeConfig {
  const config = ARTIFACT_TYPES.find(t => t.type === type);
  if (!config) {
    throw new Error(`Unknown artifact type: ${type}`);
  }
  return config;
}

/**
 * Validate artifact field against type schema.
 * @param type - Artifact type
 * @param field - Field name
 * @param value - Field value
 * @returns true if valid, false otherwise
 */
export function validateArtifactField(
  type: ArtifactType,
  field: string,
  value: unknown
): boolean {
  const config = getArtifactTypeConfig(type);
  const validator = config.validators?.[field as keyof typeof config.validators];
  if (!validator) {
    return true; // No validator = field is valid
  }
  return validator(value);
}

// Type definitions for registry
export interface ArtifactTypeConfig {
  type: ArtifactType;
  label: string;
  description: string;
  icon: string;
  fields: string[];
  required: string[];
  validators?: Record<string, (value: any) => boolean>;
}
```

**Acceptance Criteria**:
- [ ] `ARTIFACT_TYPES` registry defined with all 5 types
- [ ] Form schemas identical to current `ENTITY_TYPES`
- [ ] All field validators present
- [ ] `getArtifactTypeConfig()` function works correctly
- [ ] `validateArtifactField()` helper works correctly
- [ ] TypeScript compilation succeeds
- [ ] Registry is exported from `types/index.ts`

**Testing**:
```typescript
// Verify registry works
import { ARTIFACT_TYPES, getArtifactTypeConfig } from '@/types';

const skillConfig = getArtifactTypeConfig('skill');
expect(skillConfig.type).toBe('skill');
expect(skillConfig.fields).toContain('name');
```

---

#### P2-T2: Create ENTITY_TYPES Deprecation Alias

**Task ID**: P2-T2
**Effort**: 1 point
**Duration**: 0.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Add deprecation alias `ENTITY_TYPES` in `types/entity.ts` that points to `ARTIFACT_TYPES`. Create similar deprecation export for `getEntityTypeConfig()` function.

**File**: `skillmeat/web/types/entity.ts`

**Changes**:
```typescript
import {
  ARTIFACT_TYPES,
  getArtifactTypeConfig,
  type ArtifactTypeConfig,
} from './artifact';

/**
 * @deprecated Use ARTIFACT_TYPES instead
 * Maintained for backward compatibility until Q3 2026
 *
 * See: .claude/guides/entity-to-artifact-migration.md
 */
export const ENTITY_TYPES = ARTIFACT_TYPES;

/**
 * @deprecated Use getArtifactTypeConfig instead
 * Maintained for backward compatibility until Q3 2026
 */
export function getEntityTypeConfig(type: string): ArtifactTypeConfig {
  return getArtifactTypeConfig(type as ArtifactType);
}

export type { ArtifactTypeConfig as EntityTypeConfig };
```

**Acceptance Criteria**:
- [ ] `ENTITY_TYPES` aliased to `ARTIFACT_TYPES`
- [ ] `getEntityTypeConfig()` aliased to `getArtifactTypeConfig()`
- [ ] Both old and new names work identically
- [ ] IDE shows deprecation warning for old names
- [ ] TypeScript compiles without errors

---

#### P2-T3: Update All Imports to Use ARTIFACT_TYPES

**Task ID**: P2-T3
**Effort**: 4 points
**Duration**: 2 days
**Assigned**: `backend-typescript-architect` with delegation to `codebase-explorer`

**Description**:
Search codebase for all imports of `ENTITY_TYPES` and update to `ARTIFACT_TYPES`. Update all function calls to `getEntityTypeConfig()` to use `getArtifactTypeConfig()`. Update type imports from entity.ts to artifact.ts where applicable.

**Files to Update** (estimated 15-20):
- `skillmeat/web/components/entity/entity-form.tsx`
- `skillmeat/web/components/entity/entity-crud-modal.tsx`
- `skillmeat/web/components/entity/entity-list.tsx`
- `skillmeat/web/components/entity/modal-collections-tab.tsx`
- `skillmeat/web/components/entity/modal-sources-tab.tsx`
- `skillmeat/web/components/sync-status/**/*.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/web/app/manage/page.tsx`
- And others (use Grep to find all)

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
- [ ] Type imports updated to use `artifact.ts` (except where backward compat needed)
- [ ] All updated files compile without TypeScript errors
- [ ] No regression in form rendering or validation
- [ ] All tests pass

**Testing**:
- [ ] Run full test suite: `pnpm test`
- [ ] Verify form components render correctly
- [ ] Verify validation works for all artifact types
- [ ] Manual QA: Create new artifact, edit existing, verify form behavior unchanged

---

#### P2-T4: Validation & Testing

**Task ID**: P2-T4
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `backend-typescript-architect`

**Description**:
Comprehensive testing and validation of Phase 1-2 type system changes. Verify backward compatibility, test new types, validate form schemas, ensure no regressions.

**Testing Checklist**:

**Unit Tests**:
```bash
# Test type definitions
pnpm test types/artifact.test.ts

# Test registry
pnpm test types/artifact.registry.test.ts

# Verify backward compatibility
pnpm test types/entity.compat.test.ts
```

**Type Safety**:
```bash
# Strict mode compilation
tsc --noEmit --strict

# Check for type errors in all components
tsc --noEmit skillmeat/web/components/entity/*.tsx
tsc --noEmit skillmeat/web/app/*.tsx
tsc --noEmit skillmeat/web/hooks/*.ts
```

**Manual Verification**:
- [ ] Old imports still work: `import { Entity } from '@/types'`
- [ ] New imports work: `import { Artifact } from '@/types'`
- [ ] ENTITY_TYPES still accessible: `import { ENTITY_TYPES } from '@/types'`
- [ ] ARTIFACT_TYPES accessible: `import { ARTIFACT_TYPES } from '@/types'`
- [ ] IDE shows deprecation warnings for old names
- [ ] Form rendering unchanged visually
- [ ] Form validation works for all types

**Integration Testing**:
- [ ] `/collection` page loads and displays artifacts
- [ ] `/manage` page loads and displays artifacts
- [ ] Modal opens and displays entity/artifact data
- [ ] Form submission works (create/edit)

**Acceptance Criteria**:
- [ ] All Phase 1-2 tests pass (>85% coverage)
- [ ] TypeScript strict mode: zero errors
- [ ] Backward compatibility: 100% (old code works unchanged)
- [ ] Visual regression: zero differences
- [ ] Performance: no bundle size increase
- [ ] All files compile successfully

---

## Phase 1-2 Completion Checklist

### Required Before Phase 3 Can Start

- [ ] All Phase 1-2 tasks completed
- [ ] TypeScript compilation succeeds with strict mode
- [ ] Full test suite passes (>85% coverage for new code)
- [ ] All backward compatibility aliases work
- [ ] Both old and new type names resolve correctly
- [ ] IDE shows deprecation warnings for old names
- [ ] Form rendering identical before/after
- [ ] No visual or behavioral changes to any components
- [ ] Code review approval from 2+ team members
- [ ] No performance regressions

### Documentation Updates

- [ ] `skillmeat/web/CLAUDE.md` referenced in Phase 5 updates
- [ ] Type definitions documented with JSDoc
- [ ] Registry documented with usage examples
- [ ] Deprecation notices include migration link

---

## Risk Mitigations for Phase 1-2

### Risk: Type Compatibility Issues

**Issue**: Old code expecting `Entity` type breaks with new `Artifact`

**Mitigation**:
- Phase 1-T3 creates backward compatibility aliases
- Both old and new type names resolve to same type
- Deprecation warnings appear in IDE but code compiles
- All existing tests pass without modification

**Verification**:
```typescript
// This should compile without error
import type { Entity, Artifact } from '@/types';
const myEntity: Entity = { /* ... */ };
const myArtifact: Artifact = myEntity; // No type error
```

### Risk: Registry Field Mismatch

**Issue**: ARTIFACT_TYPES registry doesn't match current ENTITY_TYPES

**Mitigation**:
- Phase 2-T1 creates registry with identical structure
- Side-by-side comparison of old/new registries
- Form components render identically
- All form validators present and working

**Verification**:
```typescript
import { ENTITY_TYPES as OLD, ARTIFACT_TYPES as NEW } from '@/types';
// Both should have same length, same types, same fields
expect(OLD.length).toBe(NEW.length);
expect(OLD.map(t => t.type)).toEqual(NEW.map(t => t.type));
```

### Risk: Circular Imports

**Issue**: entity.ts re-exports from artifact.ts, creating circular reference

**Mitigation**:
- entity.ts only imports types, not values
- One-way dependency: entity.ts → artifact.ts
- Test for circular imports in CI/CD

**Verification**:
```bash
# Check for circular imports
npx depcheck skillmeat/web/types/
```

---

## Success Criteria Summary

**Phase 1-2 Complete When**:

1. ✅ Unified `Artifact` type defined with all 25+ properties
2. ✅ `SyncStatus` enum with 5 values (synced | modified | outdated | conflict | error)
3. ✅ Backward compatibility aliases (Entity = Artifact, etc.)
4. ✅ `ARTIFACT_TYPES` registry identical to current `ENTITY_TYPES`
5. ✅ All imports updated (~20 files)
6. ✅ TypeScript strict mode compilation succeeds
7. ✅ All tests pass (>85% coverage)
8. ✅ IDE shows deprecation warnings for old names
9. ✅ Zero visual/behavioral changes
10. ✅ Code review approval

---

## Next Phase

→ See [Phase 3: API Mapper Centralization](phase-3-mappers.md)

---

**Last Updated**: 2026-01-28
**Status**: Ready for Implementation
