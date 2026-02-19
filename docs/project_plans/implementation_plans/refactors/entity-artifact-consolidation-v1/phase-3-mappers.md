---
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: entity-artifact-consolidation
prd_ref: null
plan_ref: null
---
# Phase 3: API Mapper Centralization

**Phase**: 3
**Effort**: 12 story points
**Duration**: 4-5 days
**Dependencies**: Phase 1-2 complete (types and registry)
**Critical Path**: Yes (blocks Phase 4)

---

## Phase Overview

### Goal

Create single `mapApiResponseToArtifact()` function as the authoritative converter from backend `ArtifactResponse` to frontend `Artifact` type. Implement `determineSyncStatus()` logic. Update hooks and pages to use new unified mapper. Remove all 4 redundant conversion functions.

### Why This Matters

**Current State** (Broken):
- 4 separate conversion functions scatter logic across codebase
- `useArtifacts.ts` and `useEntityLifecycle.tsx` duplicate logic
- `collection/page.tsx` and `sync-status-tab.tsx` have additional converters
- Fields drift out of sync between converters (like missing `collections` field)
- Modal data inconsistent between /collection and /manage pages

**After Phase 3** (Fixed):
- Single mapper function with complete logic
- All artifact conversions go through same path
- Status determination centralized and consistent
- Modal receives identical data from both pages
- Collections tab populated, source tab appears correctly

---

## Phase 3 Tasks

### P3-T1: Create lib/api/mappers.ts with mapApiResponseToArtifact()

**Task ID**: P3-T1
**Effort**: 4 points
**Duration**: 1.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Create new file `skillmeat/web/lib/api/mappers.ts` with `mapApiResponseToArtifact()` function. This function converts `ArtifactResponse` from backend API to unified `Artifact` type. Implement `determineSyncStatus()` logic for accurate status mapping based on artifact state.

**File**: `skillmeat/web/lib/api/mappers.ts` (NEW)

**Implementation**:
```typescript
import type { Artifact, SyncStatus } from '@/types';
import type { ArtifactResponse } from '@/api/schemas';

/**
 * Map API ArtifactResponse to unified Artifact type.
 *
 * Single source of truth for all API → frontend artifact conversions.
 * Replaces: mapApiArtifact(), mapApiArtifactToEntity(), artifactToEntity()
 *
 * @param response - The ArtifactResponse from backend API
 * @param context - The context where artifact is being used ('collection' | 'project')
 * @returns Unified Artifact object ready for UI rendering
 *
 * @example
 * const artifact = mapApiResponseToArtifact(apiResponse, 'collection');
 * // artifact includes all fields: metadata flattened, status unified
 */
export function mapApiResponseToArtifact(
  response: ArtifactResponse,
  context: 'collection' | 'project' = 'collection'
): Artifact {
  // Validate required fields
  if (!response?.id || !response?.name || !response?.type) {
    throw new Error(
      `Invalid ArtifactResponse: missing required fields (id, name, type)`
    );
  }

  // Determine sync status based on context and artifact state
  const syncStatus = determineSyncStatus(response, context);

  // Map all fields with proper flattening and transformations
  const artifact: Artifact = {
    // Identity (required)
    id: response.id,
    name: response.name,
    type: response.type as ArtifactType,

    // Context
    scope: response.scope || 'user',
    ...(response.collection && { collection: response.collection }),
    ...(response.collections && { collections: response.collections }),
    ...(context === 'project' && response.projectPath && {
      projectPath: response.projectPath,
    }),

    // Metadata (flattened from nested structure)
    ...(response.metadata?.description && {
      description: response.metadata.description,
    }),
    ...(response.metadata?.tags && { tags: response.metadata.tags }),
    ...(response.metadata?.author && { author: response.metadata.author }),
    ...(response.metadata?.license && { license: response.metadata.license }),
    ...(response.version && { version: response.version }),
    ...(response.metadata?.dependencies && {
      dependencies: response.metadata.dependencies,
    }),

    // Source & Origin
    ...(response.source && { source: response.source }),
    ...(response.origin && { origin: response.origin as any }),
    ...(response.origin_source && { origin_source: response.origin_source }),
    ...(response.aliases && { aliases: response.aliases }),

    // Unified status
    syncStatus,

    // Upstream tracking (optional)
    ...(response.upstream && {
      upstream: {
        enabled: response.upstream.enabled ?? false,
        ...(response.upstream.url && { url: response.upstream.url }),
        ...(response.upstream.version && {
          version: response.upstream.version,
        }),
        ...(response.upstream.currentSha && {
          currentSha: response.upstream.currentSha,
        }),
        ...(response.upstream.upstreamSha && {
          upstreamSha: response.upstream.upstreamSha,
        }),
        updateAvailable: response.upstream.updateAvailable ?? false,
        ...(response.upstream.lastChecked && {
          lastChecked: response.upstream.lastChecked,
        }),
      },
    }),

    // Usage statistics (optional)
    ...(response.usageStats && {
      usageStats: {
        totalDeployments: response.usageStats.totalDeployments ?? 0,
        activeProjects: response.usageStats.activeProjects ?? 0,
        ...(response.usageStats.lastUsed && {
          lastUsed: response.usageStats.lastUsed,
        }),
        usageCount: response.usageStats.usageCount ?? 0,
      },
    }),

    // Score (optional)
    ...(response.score && { score: response.score }),

    // Timestamps
    createdAt: response.createdAt || new Date().toISOString(),
    updatedAt: response.updatedAt || new Date().toISOString(),
    ...(response.deployedAt && { deployedAt: response.deployedAt }),
    ...(response.modifiedAt && { modifiedAt: response.modifiedAt }),
  };

  return artifact;
}

/**
 * Determine the sync status of an artifact.
 *
 * Maps API response state to unified SyncStatus enum.
 * Logic differs slightly based on context (collection vs project deployment).
 *
 * Status Rules:
 *   synced    - Artifact matches source/upstream (no changes)
 *   modified  - Local changes not in source (project context only)
 *   outdated  - Upstream has newer version
 *   conflict  - Unresolvable conflict between versions
 *   error     - Error in sync or processing
 *
 * @param response - The ArtifactResponse from API
 * @param context - Context for status determination
 * @returns One of: synced | modified | outdated | conflict | error
 */
export function determineSyncStatus(
  response: ArtifactResponse,
  context: 'collection' | 'project'
): SyncStatus {
  // Error takes priority - if artifact is in error state, report error
  if (response.syncStatus === 'error' || response.error) {
    return 'error';
  }

  // Conflict - explicit conflict marker
  if (response.syncStatus === 'conflict' || response.conflictState?.hasConflict) {
    return 'conflict';
  }

  // Project context: check for local modifications
  if (context === 'project') {
    // modifiedAt > deployedAt indicates local changes
    if (
      response.modifiedAt &&
      response.deployedAt &&
      new Date(response.modifiedAt) > new Date(response.deployedAt)
    ) {
      return 'modified';
    }

    // If response explicitly marks as modified
    if (response.syncStatus === 'modified') {
      return 'modified';
    }
  }

  // Outdated - newer version available upstream
  if (
    response.upstream?.updateAvailable ||
    response.syncStatus === 'outdated' ||
    (response.upstream?.upstreamSha &&
      response.upstream?.currentSha &&
      response.upstream.upstreamSha !== response.upstream.currentSha)
  ) {
    return 'outdated';
  }

  // Default to synced - matches upstream/source
  // Covers: no upstream (local-only), explicit 'active'/'synced', or no drift
  return 'synced';
}

/**
 * Batch convert multiple API responses to artifacts.
 *
 * @param responses - Array of ArtifactResponse objects
 * @param context - Context for mapping
 * @returns Array of Artifact objects
 */
export function mapApiResponsesToArtifacts(
  responses: ArtifactResponse[],
  context: 'collection' | 'project' = 'collection'
): Artifact[] {
  return responses.map(response => mapApiResponseToArtifact(response, context));
}

/**
 * Validate that a mapped artifact has all required fields.
 *
 * Used in testing to ensure no fields are lost during conversion.
 *
 * @param artifact - The artifact to validate
 * @returns true if all required fields present, false otherwise
 */
export function validateArtifactMapping(artifact: Artifact): boolean {
  // Required fields
  if (!artifact.id || !artifact.name || !artifact.type || !artifact.syncStatus) {
    return false;
  }

  // At least one context indicator
  if (!artifact.scope && !artifact.collection && !artifact.projectPath) {
    return false;
  }

  // Timestamps
  if (!artifact.createdAt || !artifact.updatedAt) {
    return false;
  }

  return true;
}
```

**Exports from lib/api/index.ts**:
```typescript
export {
  mapApiResponseToArtifact,
  mapApiResponsesToArtifacts,
  determineSyncStatus,
  validateArtifactMapping,
} from './mappers';
```

**Acceptance Criteria**:
- [ ] `mapApiResponseToArtifact()` function implemented
- [ ] All 25+ artifact properties mapped correctly
- [ ] Flattened metadata structure correct (no nested object)
- [ ] `determineSyncStatus()` handles all 5 status values
- [ ] Context parameter affects projectPath inclusion
- [ ] Batch converter `mapApiResponsesToArtifacts()` works
- [ ] Validation helper `validateArtifactMapping()` works
- [ ] TypeScript compilation succeeds
- [ ] JSDoc documentation complete

**Testing**:
```bash
# Unit tests for mapper
pnpm test lib/api/mappers.test.ts
```

---

### P3-T2: Implement Unit Tests for mapApiResponseToArtifact()

**Task ID**: P3-T2
**Effort**: 3 points
**Duration**: 1.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Write comprehensive unit tests for `mapApiResponseToArtifact()` covering all properties, all status transitions, edge cases, and validation. Tests ensure no fields are lost during conversion and status determination logic is correct.

**File**: `skillmeat/web/lib/api/mappers.test.ts` (NEW)

**Test Coverage**:
```typescript
describe('mapApiResponseToArtifact', () => {
  describe('Required fields mapping', () => {
    it('should map id, name, type correctly', () => {
      // Test basic identity mapping
    });

    it('should throw on missing required fields', () => {
      // Test validation for id, name, type
    });
  });

  describe('Metadata flattening', () => {
    it('should flatten nested metadata to top level', () => {
      const response = {
        // ...
        metadata: {
          description: 'Test description',
          author: 'Test Author',
          license: 'MIT',
          tags: ['tag1', 'tag2'],
        },
      };
      const artifact = mapApiResponseToArtifact(response);
      expect(artifact.description).toBe('Test description');
      expect(artifact.author).toBe('Test Author');
      expect(artifact.license).toBe('MIT');
      expect(artifact.tags).toEqual(['tag1', 'tag2']);
      expect(artifact.metadata).toBeUndefined(); // Not present in unified type
    });

    it('should preserve optional metadata fields', () => {
      // Test with partial metadata
    });

    it('should handle missing metadata gracefully', () => {
      // Test with metadata: undefined
    });
  });

  describe('Context handling', () => {
    it('should include projectPath in project context', () => {
      const response = {
        // ...
        projectPath: '/path/to/project',
      };
      const artifact = mapApiResponseToArtifact(response, 'project');
      expect(artifact.projectPath).toBe('/path/to/project');
    });

    it('should exclude projectPath in collection context', () => {
      const response = {
        // ...
        projectPath: '/path/to/project',
      };
      const artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.projectPath).toBeUndefined();
    });

    it('should include collection field when present', () => {
      // Test collection field mapping
    });

    it('should include collections array when present', () => {
      // Test collections array mapping
    });
  });

  describe('Status determination', () => {
    it('should return "synced" for normal state', () => {
      // No upstream updates, no local changes
    });

    it('should return "modified" in project context with recent changes', () => {
      // modifiedAt > deployedAt
    });

    it('should return "outdated" when upstream has updates', () => {
      // updateAvailable = true or SHA mismatch
    });

    it('should return "conflict" for conflicted artifacts', () => {
      // conflictState.hasConflict = true
    });

    it('should return "error" for error state', () => {
      // response.error = true
    });

    it('should prioritize error over other statuses', () => {
      // Even if conflicted, if error state, return 'error'
    });
  });

  describe('Optional nested objects', () => {
    it('should map upstream object when present', () => {
      const response = {
        // ...
        upstream: {
          enabled: true,
          url: 'https://github.com/user/repo',
          version: '1.0.0',
          currentSha: 'abc123',
          upstreamSha: 'def456',
          updateAvailable: true,
          lastChecked: '2026-01-28T10:00:00Z',
        },
      };
      const artifact = mapApiResponseToArtifact(response);
      expect(artifact.upstream).toBeDefined();
      expect(artifact.upstream?.url).toBe('https://github.com/user/repo');
    });

    it('should map usageStats object when present', () => {
      const response = {
        // ...
        usageStats: {
          totalDeployments: 5,
          activeProjects: 3,
          lastUsed: '2026-01-27T10:00:00Z',
          usageCount: 42,
        },
      };
      const artifact = mapApiResponseToArtifact(response);
      expect(artifact.usageStats?.totalDeployments).toBe(5);
    });

    it('should omit upstream when not present', () => {
      const response = {
        // ... no upstream field
      };
      const artifact = mapApiResponseToArtifact(response);
      expect(artifact.upstream).toBeUndefined();
    });

    it('should omit usageStats when not present', () => {
      const response = {
        // ... no usageStats field
      };
      const artifact = mapApiResponseToArtifact(response);
      expect(artifact.usageStats).toBeUndefined();
    });
  });

  describe('Batch conversion', () => {
    it('should convert multiple artifacts correctly', () => {
      const responses = [
        { id: 'skill:test1', name: 'Test 1', type: 'skill' },
        { id: 'command:test2', name: 'Test 2', type: 'command' },
      ];
      const artifacts = mapApiResponsesToArtifacts(responses);
      expect(artifacts).toHaveLength(2);
      expect(artifacts[0].id).toBe('skill:test1');
      expect(artifacts[1].id).toBe('command:test2');
    });
  });
});

describe('determineSyncStatus', () => {
  describe('Error priority', () => {
    it('should return error when response.error = true', () => {
      const status = determineSyncStatus({ error: true }, 'collection');
      expect(status).toBe('error');
    });

    it('should return error when syncStatus = error', () => {
      const status = determineSyncStatus({ syncStatus: 'error' }, 'collection');
      expect(status).toBe('error');
    });
  });

  describe('Conflict detection', () => {
    it('should return conflict when hasConflict = true', () => {
      const status = determineSyncStatus(
        { conflictState: { hasConflict: true } },
        'collection'
      );
      expect(status).toBe('conflict');
    });
  });

  describe('Modified detection (project context only)', () => {
    it('should return modified when modifiedAt > deployedAt', () => {
      const status = determineSyncStatus(
        {
          deployedAt: '2026-01-27T10:00:00Z',
          modifiedAt: '2026-01-28T10:00:00Z', // Later
        },
        'project'
      );
      expect(status).toBe('modified');
    });

    it('should not return modified in collection context', () => {
      const status = determineSyncStatus(
        {
          deployedAt: '2026-01-27T10:00:00Z',
          modifiedAt: '2026-01-28T10:00:00Z',
        },
        'collection'
      );
      expect(status).not.toBe('modified');
    });
  });

  describe('Outdated detection', () => {
    it('should return outdated when updateAvailable = true', () => {
      const status = determineSyncStatus(
        { upstream: { updateAvailable: true } },
        'collection'
      );
      expect(status).toBe('outdated');
    });

    it('should return outdated on SHA mismatch', () => {
      const status = determineSyncStatus(
        {
          upstream: {
            currentSha: 'abc123',
            upstreamSha: 'def456',
            updateAvailable: false,
          },
        },
        'collection'
      );
      expect(status).toBe('outdated');
    });
  });

  describe('Synced detection', () => {
    it('should return synced for artifact with no upstream', () => {
      const status = determineSyncStatus({}, 'collection');
      expect(status).toBe('synced');
    });

    it('should return synced when SHAs match', () => {
      const status = determineSyncStatus(
        {
          upstream: {
            currentSha: 'abc123',
            upstreamSha: 'abc123',
            updateAvailable: false,
          },
        },
        'collection'
      );
      expect(status).toBe('synced');
    });
  });
});
```

**Acceptance Criteria**:
- [ ] >85% code coverage for mappers.ts
- [ ] All property mapping tested
- [ ] All 5 status values tested
- [ ] Edge cases covered (missing fields, null values, etc.)
- [ ] Context parameter behavior tested
- [ ] All tests pass
- [ ] Test file is well-documented

---

### P3-T3: Update useArtifacts.ts Hook

**Task ID**: P3-T3
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `backend-typescript-architect`

**Description**:
Update `hooks/useArtifacts.ts` to use new `mapApiResponseToArtifact()` function. Remove old `mapApiArtifact()` function. Update hook to return Artifact[] instead of going through intermediate mapping.

**File**: `skillmeat/web/hooks/useArtifacts.ts`

**Changes**:
```typescript
import {
  mapApiResponseToArtifact,
  mapApiResponsesToArtifacts,
} from '@/lib/api/mappers';
import type { Artifact } from '@/types';

// ... existing hook code ...

// Replace old mapApiArtifact() with call to new mapper
// Old code (~60 lines):
// function mapApiArtifact(response: ArtifactResponse): Artifact { ... }

// New code:
function useInfiniteArtifacts(filters?: ArtifactFilters) {
  return useInfiniteQuery({
    queryKey: artifactKeys.lists(filters),
    queryFn: async ({ pageParam }) => {
      const response = await apiClient.artifacts.list({
        skip: pageParam,
        limit: ITEMS_PER_PAGE,
        ...filters,
      });

      // Use unified mapper with 'collection' context
      return {
        items: mapApiResponsesToArtifacts(response.items, 'collection'),
        nextCursor: response.nextCursor,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
  });
}

// Similarly update useInfiniteCollectionArtifacts
function useInfiniteCollectionArtifacts(collectionId: string) {
  return useInfiniteQuery({
    queryKey: artifactKeys.byCollection(collectionId),
    queryFn: async ({ pageParam }) => {
      const response = await apiClient.artifacts.byCollection(collectionId, {
        skip: pageParam,
        limit: ITEMS_PER_PAGE,
      });

      // Use unified mapper with 'collection' context
      return {
        items: mapApiResponsesToArtifacts(response.items, 'collection'),
        nextCursor: response.nextCursor,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
  });
}
```

**Acceptance Criteria**:
- [ ] Old `mapApiArtifact()` function removed
- [ ] Hook uses `mapApiResponsesToArtifacts()` from new mapper
- [ ] All hook queries use unified mapper
- [ ] TypeScript compilation succeeds
- [ ] Hook return type is Artifact[] (unchanged externally)
- [ ] All tests pass

---

### P3-T4: Update useEntityLifecycle.tsx Hook

**Task ID**: P3-T4
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `backend-typescript-architect`

**Description**:
Update `hooks/useEntityLifecycle.tsx` to use new `mapApiResponseToArtifact()` function. Hook returns Entity/Artifact type for `/manage` page. Remove old `mapApiArtifactToEntity()` function.

**File**: `skillmeat/web/hooks/useEntityLifecycle.tsx`

**Changes**:
```typescript
import {
  mapApiResponseToArtifact,
  mapApiResponsesToArtifacts,
} from '@/lib/api/mappers';
import type { Artifact } from '@/types'; // Using Artifact (Entity is alias)

// ... existing hook code ...

// Replace old mapApiArtifactToEntity() with call to new mapper
// Old code (~60 lines):
// function mapApiArtifactToEntity(response: ArtifactResponse): Entity { ... }

// New code:
function useEntityLifecycle(options: UseEntityLifecycleOptions) {
  const { mode = 'collection', collectionId } = options;

  return useQuery({
    queryKey: entityKeys.list(mode, collectionId),
    queryFn: async () => {
      let responses: ArtifactResponse[];

      if (mode === 'collection' && collectionId) {
        const result = await apiClient.artifacts.byCollection(collectionId);
        responses = result.items;
      } else {
        const result = await apiClient.artifacts.list();
        responses = result.items;
      }

      // Use unified mapper with appropriate context
      return mapApiResponsesToArtifacts(
        responses,
        mode === 'project' ? 'project' : 'collection'
      );
    },
  });
}

// CRUD operations remain unchanged - they work with Artifact/Entity type
// Create, update, delete operations continue to work as before
```

**Acceptance Criteria**:
- [ ] Old `mapApiArtifactToEntity()` function removed
- [ ] Hook uses `mapApiResponsesToArtifacts()` from new mapper
- [ ] Context parameter passed to mapper (collection vs project)
- [ ] Hook return type is Entity/Artifact[] (Entity is alias)
- [ ] TypeScript compilation succeeds
- [ ] CRUD operations unaffected
- [ ] All tests pass

---

### P3-T5: Remove Conversion Functions from Pages

**Task ID**: P3-T5
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `backend-typescript-architect`

**Description**:
Remove page-level conversion functions `artifactToEntity()` from `app/collection/page.tsx` and `entityToArtifact()` from `components/sync-status/sync-status-tab.tsx`. These are no longer needed since all conversions go through unified mapper.

**Files to Update**:
1. `skillmeat/web/app/collection/page.tsx`
2. `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Changes**:

**collection/page.tsx** (before):
```typescript
function artifactToEntity(artifact: Artifact): Entity {
  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,
    // ... ~40 lines of conversion logic
  };
}

const handleArtifactClick = (artifact: Artifact) => {
  setSelectedEntity(artifactToEntity(artifact)); // Conversion needed
};
```

**collection/page.tsx** (after):
```typescript
// Remove artifactToEntity() function entirely

// Artifact type is now an alias for Entity, no conversion needed
const handleArtifactClick = (artifact: Artifact) => {
  setSelectedEntity(artifact); // Direct use, no conversion
};
```

**sync-status-tab.tsx** (before):
```typescript
function entityToArtifact(entity: Entity): Artifact {
  return {
    id: entity.id,
    name: entity.name,
    type: entity.type,
    // ... ~30 lines of conversion logic
  };
}

const syncData = entityToArtifact(selectedEntity);
```

**sync-status-tab.tsx** (after):
```typescript
// Remove entityToArtifact() function entirely

// Entity is alias for Artifact, no conversion needed
const syncData = selectedEntity; // Direct use
```

**Acceptance Criteria**:
- [ ] `artifactToEntity()` removed from collection/page.tsx
- [ ] `entityToArtifact()` removed from sync-status-tab.tsx
- [ ] All usages of removed functions updated to direct assignment
- [ ] TypeScript compilation succeeds
- [ ] No type errors
- [ ] All tests pass
- [ ] Modal still opens with complete data

---

### P3-T6: Integration Testing & Validation

**Task ID**: P3-T6
**Effort**: 3 points
**Duration**: 1.5 days
**Assigned**: `backend-typescript-architect`

**Description**:
Comprehensive integration testing of Phase 3 changes. Verify data consistency between old and new mappers, test both data pipelines (/collection and /manage), validate modal receives complete data.

**Integration Tests** (new file: `hooks/useArtifacts.integration.test.ts`):

```typescript
describe('API Mapper Integration', () => {
  describe('Collection pipeline (useArtifacts + mapApiResponseToArtifact)', () => {
    it('should map artifact with complete metadata', async () => {
      const mockResponse: ArtifactResponse = {
        id: 'skill:test',
        name: 'Test Skill',
        type: 'skill',
        metadata: {
          description: 'Test description',
          author: 'Test Author',
          license: 'MIT',
          tags: ['test'],
        },
        collections: [{ id: 'col1', name: 'Collection 1' }],
        syncStatus: 'synced',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      const artifact = mapApiResponseToArtifact(mockResponse, 'collection');

      // Verify all fields mapped correctly
      expect(artifact.id).toBe('skill:test');
      expect(artifact.name).toBe('Test Skill');
      expect(artifact.type).toBe('skill');
      expect(artifact.description).toBe('Test description');
      expect(artifact.author).toBe('Test Author');
      expect(artifact.license).toBe('MIT');
      expect(artifact.tags).toContain('test');
      expect(artifact.collections).toHaveLength(1);
      expect(artifact.syncStatus).toBe('synced');
    });

    it('should include all collection artifacts in query result', async () => {
      // Mock useInfiniteArtifacts query
      // Verify each artifact has required fields for display
      // Verify modal can open with any artifact
    });
  });

  describe('Project pipeline (useEntityLifecycle + mapApiResponseToArtifact)', () => {
    it('should map artifact with deployment context', async () => {
      const mockResponse: ArtifactResponse = {
        id: 'skill:test',
        name: 'Test Skill',
        type: 'skill',
        projectPath: '/path/to/project',
        deployedAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
        syncStatus: 'synced',
        // ...
      };

      const artifact = mapApiResponseToArtifact(mockResponse, 'project');

      // Verify project context fields
      expect(artifact.projectPath).toBe('/path/to/project');
      expect(artifact.deployedAt).toBeDefined();
      expect(artifact.modifiedAt).toBeDefined();
    });
  });

  describe('Data consistency between pipelines', () => {
    it('should produce identical results for same artifact in both contexts', () => {
      const mockResponse: ArtifactResponse = { /* complete response */ };

      const collectionArtifact = mapApiResponseToArtifact(
        mockResponse,
        'collection'
      );
      const projectArtifact = mapApiResponseToArtifact(
        mockResponse,
        'project'
      );

      // All common fields identical
      expect(collectionArtifact.id).toBe(projectArtifact.id);
      expect(collectionArtifact.name).toBe(projectArtifact.name);
      expect(collectionArtifact.description).toBe(projectArtifact.description);
      expect(collectionArtifact.syncStatus).toBe(projectArtifact.syncStatus);

      // Only context-specific fields differ
      expect(collectionArtifact.projectPath).toBeUndefined();
      expect(projectArtifact.projectPath).toBeDefined();
    });
  });

  describe('Modal data completeness', () => {
    it('should have complete data when opening modal from /collection', async () => {
      // Simulate opening artifact modal from /collection page
      // Verify all modal tabs have required data:
      // - Basic info tab: name, description, type
      // - Collections tab: collections array populated
      // - Sources tab: source field populated
      // - Upstream tab: upstream object populated
    });

    it('should have complete data when opening modal from /manage', async () => {
      // Simulate opening artifact modal from /manage page
      // Verify same data completeness as /collection
    });
  });

  describe('Status determination accuracy', () => {
    it('should correctly determine synced status', () => {
      // Test artifact with no changes
    });

    it('should correctly determine modified status in project context', () => {
      // Test artifact with recent local changes
    });

    it('should correctly determine outdated status', () => {
      // Test artifact with available upstream updates
    });

    it('should correctly determine conflict status', () => {
      // Test artifact with explicit conflict
    });

    it('should correctly determine error status', () => {
      // Test artifact in error state
    });
  });
});
```

**Manual QA Checklist**:
- [ ] `/collection` page loads and displays artifacts (no synthetic fallbacks)
- [ ] `/manage` page loads and displays artifacts with collections data
- [ ] Click artifact in /collection → modal opens with complete data
- [ ] Click artifact in /manage → modal opens with complete data
- [ ] Collections tab shows artifact collections (was empty, now populated)
- [ ] Sources tab shows source information (appears without prior /marketplace visit)
- [ ] Source link navigation works
- [ ] Status display correct for all artifact states
- [ ] No console errors or warnings
- [ ] Form CRUD operations work with new type structure

**Acceptance Criteria**:
- [ ] Integration tests pass (>85% coverage)
- [ ] Old mapper functions removed
- [ ] New mapper used consistently in both pipelines
- [ ] Modal receives complete data from both pages
- [ ] Collections tab populated on /manage page (bug fix)
- [ ] Source tab appears on /collection page (bug fix)
- [ ] All functional tests pass
- [ ] Manual QA passes all checks
- [ ] No performance regression

---

## Phase 3 Completion Checklist

### Before Phase 4 Can Start

- [ ] All Phase 3 tasks completed
- [ ] Single `mapApiResponseToArtifact()` function created
- [ ] All 4 old conversion functions removed
- [ ] Both hook pipelines use new mapper
- [ ] All mapper unit tests pass (>85% coverage)
- [ ] Integration tests pass
- [ ] Collections tab populated on /manage page
- [ ] Source tab appears on /collection page
- [ ] Modal opens with complete data from both pages
- [ ] TypeScript compilation succeeds
- [ ] Manual QA verification complete

### Data Consistency Verification

Before moving to Phase 4, verify data consistency:

```bash
# Run side-by-side test comparing old vs new mapper outputs
pnpm test lib/api/mappers.integration.test.ts --testNamePattern="Data consistency"

# Verify no fields lost in conversion
pnpm test lib/api/mappers.test.ts --testNamePattern="property mapping"
```

---

## Risk Mitigations for Phase 3

### Risk: Data Loss in Mapper Consolidation

**Issue**: New unified mapper misses fields that old separate mappers handled

**Mitigation**:
- Side-by-side test: Run old and new mappers on same API response
- Property-by-property unit tests (25+ properties tested)
- Integration tests comparing modal data before/after
- QA verification on /collection and /manage pages
- Rollback plan: Restore old mappers if discrepancies found

**Verification**:
```typescript
// Test that validates all fields are mapped
const oldOutput = mapApiArtifact(response); // Old mapper simulation
const newOutput = mapApiResponseToArtifact(response);

// All properties should match
expect(Object.keys(oldOutput).sort()).toEqual(
  Object.keys(newOutput).sort()
);
```

### Risk: Status Determination Bugs

**Issue**: `determineSyncStatus()` logic has subtle bugs for edge cases

**Mitigation**:
- Implement status logic incrementally
- Unit test for each status transition
- Document rules clearly
- QA test artifacts in all possible states
- Conservative fallback (default to 'synced' if uncertain)

### Risk: Breaking Changes in Hook Return Types

**Issue**: Components expecting specific structure break with new mapper

**Mitigation**:
- Entity is alias for Artifact (no breaking changes externally)
- Hook return type unchanged (returns Entity/Artifact[])
- Backward compatibility via type aliases
- All existing tests should pass without modification

---

## Success Criteria Summary

**Phase 3 Complete When**:

1. ✅ Single `mapApiResponseToArtifact()` function in `lib/api/mappers.ts`
2. ✅ All 4 old conversion functions removed
3. ✅ Both hooks use unified mapper
4. ✅ `determineSyncStatus()` correctly maps all 5 status values
5. ✅ Unit tests >85% coverage
6. ✅ Integration tests pass
7. ✅ Collections tab populated (bug fix verified)
8. ✅ Source tab appears (bug fix verified)
9. ✅ No data loss in conversion
10. ✅ Modal receives complete data from both /collection and /manage pages

---

## Next Phase

→ See [Phase 4-5: Component Unification & Deprecation](phase-4-5-components.md)

---

**Last Updated**: 2026-01-28
**Status**: Ready for Implementation
