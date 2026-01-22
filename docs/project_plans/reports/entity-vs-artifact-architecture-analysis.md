# Entity vs Artifact Architecture Analysis

**Date**: 2026-01-22
**Author**: Claude (Opus 4.5)
**Status**: Analysis Complete
**Related Bug**: Commit `283b106` - Fix synthetic source display on collection page

---

## Executive Summary

The SkillMeat web frontend maintains two parallel type systems (`Entity` and `Artifact`) with separate data pipelines for the `/collection` and `/manage` pages. This architecture has led to data inconsistencies, redundant conversion logic, and maintenance overhead. This report analyzes the current state, identifies pain points, and recommends consolidation strategies.

---

## 1. Current Architecture

### 1.1 Type Definitions

#### Artifact (`types/artifact.ts`)

**Purpose**: Represents artifacts as stored in the collection with rich metadata and usage statistics.

```typescript
interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;  // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'
  scope: ArtifactScope;  // 'user' | 'local'
  status: ArtifactStatus;  // 'active' | 'outdated' | 'conflict' | 'error'
  version?: string;
  source?: string;
  origin?: string;
  origin_source?: string;
  metadata: ArtifactMetadata;  // Nested: title, description, license, author, version, tags
  upstreamStatus: UpstreamStatus;  // Nested: hasUpstream, upstreamUrl, isOutdated, etc.
  usageStats: UsageStats;  // Nested: totalDeployments, activeProjects, usageCount
  createdAt: string;
  updatedAt: string;
  aliases?: string[];
  collection?: { id: string; name: string };
  collections?: { id: string; name: string }[];
  score?: ArtifactScore;
}
```

**Key characteristics**:
- Nested metadata objects
- Backend API-aligned structure
- Usage statistics tracking
- Upstream version tracking

#### Entity (`types/entity.ts`)

**Purpose**: Unified interface for artifact management across collection and project contexts.

```typescript
interface Entity {
  id: string;
  name: string;
  type: EntityType;  // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'
  collection?: string;
  projectPath?: string;
  status?: EntityStatus;  // 'synced' | 'modified' | 'outdated' | 'conflict'
  tags?: string[];
  description?: string;
  version?: string;
  source?: string;
  deployedAt?: string;
  modifiedAt?: string;
  aliases?: string[];
  collections?: Collection[];
  origin?: string;
  origin_source?: string;
  author?: string;
  license?: string;
  dependencies?: string[];
}
```

**Key characteristics**:
- Flat property structure
- Sync status for deployment tracking
- Form schema support via `ENTITY_TYPES` registry
- Dual context (collection OR project)

### 1.2 Comparison Matrix

| Aspect | Artifact | Entity |
|--------|----------|--------|
| **Primary Use** | Collection/marketplace display | CRUD operations, sync management |
| **Metadata** | Nested objects | Flat properties |
| **Scope Model** | `user` \| `local` (storage) | `collection` OR `projectPath` (deployment) |
| **Status Values** | `active` \| `outdated` \| `conflict` \| `error` | `synced` \| `modified` \| `outdated` \| `conflict` |
| **Usage Stats** | Tracked | Not tracked |
| **Form Schema** | None | `ENTITY_TYPES` registry |
| **File Count** | ~87 files | ~45 files |

---

## 2. Data Pipelines

### 2.1 Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND API                                          │
│                    ArtifactResponse (single schema)                          │
│                    skillmeat/api/schemas/artifacts.py                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │                                                      │
         ▼                                                      ▼
┌─────────────────────────┐                    ┌─────────────────────────────┐
│   /collection Pipeline  │                    │      /manage Pipeline       │
├─────────────────────────┤                    ├─────────────────────────────┤
│                         │                    │                             │
│ useInfiniteArtifacts()  │                    │ useEntityLifecycle()        │
│         │               │                    │         │                   │
│         ▼               │                    │         ▼                   │
│ mapApiArtifact()        │                    │ mapApiArtifactToEntity()    │
│ hooks/useArtifacts.ts   │                    │ hooks/useEntityLifecycle.tsx│
│ :291-352                │                    │ :194-255                    │
│         │               │                    │         │                   │
│         ▼               │                    │         ▼                   │
│     Artifact[]          │                    │      Entity[]               │
│         │               │                    │         │                   │
│         ▼               │                    │         ▼                   │
│ enrichArtifactSummary() │                    │   (direct usage)            │
│ app/collection/page.tsx │                    │         │                   │
│ :44-89                  │                    │         ▼                   │
│         │               │                    │  UnifiedEntityModal         │
│         ▼               │                    │                             │
│ artifactToEntity()      │◄── Modal needs ─► │                             │
│ app/collection/page.tsx │    Entity type    │                             │
│ :100-147                │                    │                             │
│         │               │                    │                             │
│         ▼               │                    │                             │
│   Entity (for modal)    │                    │                             │
└─────────────────────────┘                    └─────────────────────────────┘
```

### 2.2 Conversion Functions

| Function | Location | Direction | Purpose |
|----------|----------|-----------|---------|
| `mapApiArtifact()` | `hooks/useArtifacts.ts:291-352` | API → Artifact | Primary API mapping |
| `mapApiArtifactToEntity()` | `hooks/useEntityLifecycle.tsx:194-255` | API → Entity | Management page mapping |
| `artifactToEntity()` | `app/collection/page.tsx:100-147` | Artifact → Entity | Modal compatibility |
| `entityToArtifact()` | `components/sync-status/sync-status-tab.tsx:50-80` | Entity → Artifact | Sync dialog compatibility |

### 2.3 Pipeline Differences

| Aspect | /collection | /manage |
|--------|-------------|---------|
| **Hook** | `useInfiniteArtifacts` + `useInfiniteCollectionArtifacts` | `useEntityLifecycle` |
| **Intermediate Type** | `Artifact[]` | `Entity[]` (direct) |
| **Enrichment** | `enrichArtifactSummary()` with fallback objects | None needed |
| **Modal Conversion** | `artifactToEntity()` on selection | None needed |
| **Failure Mode** | Creates synthetic objects with empty metadata | Returns null/error |

---

## 3. Identified Pain Points

### 3.1 Redundant Conversion Logic

Three separate functions convert between API response and frontend types:
- `mapApiArtifact()` - API to Artifact
- `mapApiArtifactToEntity()` - API to Entity
- `artifactToEntity()` - Artifact to Entity (lossy conversion)

Each function duplicates field mapping logic and can drift out of sync.

### 3.2 Status Value Mismatch

```typescript
// Artifact status values
type ArtifactStatus = 'active' | 'outdated' | 'conflict' | 'error';

// Entity status values
type EntityStatus = 'synced' | 'modified' | 'outdated' | 'conflict';
```

Conversion requires manual mapping:
- `active` → `synced`
- `error` → `conflict`
- `modified` has no Artifact equivalent

### 3.3 Fallback Object Problem

The `/collection` page's `enrichArtifactSummary()` function creates synthetic Artifact objects when matching fails:

```typescript
// Creates artifact with empty metadata when no match found
return {
  id: artifactId,
  name: summary.name,
  type: summary.type,
  // ... minimal fields
  metadata: {}, // EMPTY - causes missing descriptions
  upstreamStatus: { hasUpstream: false, isOutdated: false },
  usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
};
```

This was the root cause of the bug fixed in commit `283b106`.

### 3.4 Duplicate Type Definitions

Both types define identical artifact type enums:
```typescript
// types/artifact.ts
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

// types/entity.ts
export type EntityType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
```

### 3.5 Modal Type Constraint

`UnifiedEntityModal` only accepts `Entity` type, forcing conversion whenever the `/collection` page opens the modal:

```typescript
// collection/page.tsx
const handleArtifactClick = (artifact: Artifact) => {
  setSelectedEntity(artifactToEntity(artifact)); // Conversion required
};
```

---

## 4. Recommendations

### 4.1 Option A: Consolidate to Single Type (Recommended)

**Approach**: Merge `Artifact` and `Entity` into a unified `Artifact` type.

```typescript
// Proposed unified type
interface Artifact {
  // Identity
  id: string;
  name: string;
  type: ArtifactType;

  // Context (supports both modes)
  scope: 'user' | 'local';
  collection?: CollectionRef;
  collections?: CollectionRef[];
  projectPath?: string;

  // Metadata (flattened)
  description?: string;
  tags?: string[];
  author?: string;
  license?: string;
  version?: string;
  dependencies?: string[];

  // Source & Origin
  source?: string;
  origin?: 'local' | 'github' | 'marketplace';
  origin_source?: string;
  aliases?: string[];

  // Status (unified enum)
  syncStatus: 'synced' | 'modified' | 'outdated' | 'conflict' | 'error';

  // Upstream tracking (optional)
  upstream?: {
    enabled: boolean;
    url?: string;
    version?: string;
    currentSha?: string;
    upstreamSha?: string;
    updateAvailable: boolean;
  };

  // Usage stats (optional)
  usageStats?: {
    deployments: number;
    projects: number;
    lastUsed?: string;
  };

  // Timestamps
  createdAt: string;
  updatedAt: string;
}
```

**Migration Steps**:
1. Create unified `Artifact` type in `types/artifact.ts`
2. Update `mapApiArtifact()` to return unified type
3. Deprecate `Entity` type with re-export alias
4. Update all components to use `Artifact`
5. Remove conversion functions
6. Rename `ENTITY_TYPES` → `ARTIFACT_TYPES`

**Benefits**:
- Single source of truth
- No conversion functions needed
- Consistent status values
- Modal works with same type
- Reduced maintenance burden

**Effort**: Medium (2-3 days)

**Impact**: High - eliminates entire class of bugs

### 4.2 Option B: Entity as Display Layer

**Approach**: Keep both types with clearer boundaries:
- `Artifact` = Backend/API representation
- `Entity` = UI component representation

**Changes**:
1. Move conversion to hook level (`useArtifacts` returns `Entity[]`)
2. Remove page-level conversion functions
3. Update `UnifiedEntityModal` to accept either type

**Benefits**:
- Smaller refactor
- Clear separation of concerns
- Gradual migration possible

**Effort**: Low-Medium (1-2 days)

**Impact**: Medium - reduces but doesn't eliminate conversion

### 4.3 Option C: Fix the Pipeline (Quick Win)

**Approach**: Keep architecture but fix broken pipeline:

1. **Eliminate fallback objects** - Return null instead of synthetic artifacts
2. **Unify hooks** - Have `/collection` use `useEntityLifecycle`
3. **Add type adapter** - Modal accepts `Artifact | Entity`

**Implementation**:
```typescript
// collection/page.tsx - Use same hook as /manage
const { entities, isLoading } = useEntityLifecycle({
  mode: 'collection',
  collectionId: selectedCollection?.id
});

// No conversion needed - modal receives Entity directly
const handleEntityClick = (entity: Entity) => {
  setSelectedEntity(entity);
};
```

**Benefits**:
- Fixes immediate bugs
- No major refactor
- Incremental improvement

**Effort**: Low (0.5-1 day)

**Impact**: Medium - fixes current bugs, doesn't address root cause

---

## 5. Recommendation Summary

| Priority | Option | Effort | Impact | Timeline |
|----------|--------|--------|--------|----------|
| **1** | C - Fix Pipeline | Low | Medium | Immediate |
| **2** | A - Consolidate Types | Medium | High | Next sprint |
| **3** | Unify Status Enums | Low | Low | With Option A |

### Recommended Approach

1. **Immediate** (Option C): Make `/collection` page use `useEntityLifecycle` to eliminate the fallback object problem and dual pipeline complexity.

2. **Short-term** (Option A): Plan type consolidation as a dedicated refactoring task. Create PRD and implementation plan.

3. **Ongoing**: Ensure new features use the unified approach, avoiding introduction of new conversion logic.

---

## 6. Related Files

### Type Definitions
- `skillmeat/web/types/artifact.ts` (105 lines)
- `skillmeat/web/types/entity.ts` (417 lines)

### Conversion Functions
- `skillmeat/web/hooks/useArtifacts.ts:291-352` - `mapApiArtifact()`
- `skillmeat/web/hooks/useEntityLifecycle.tsx:194-255` - `mapApiArtifactToEntity()`
- `skillmeat/web/app/collection/page.tsx:100-147` - `artifactToEntity()`
- `skillmeat/web/components/sync-status/sync-status-tab.tsx:50-80` - `entityToArtifact()`

### Primary Hooks
- `skillmeat/web/hooks/useArtifacts.ts` - Artifact pipeline
- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Entity pipeline

### Backend Schema
- `skillmeat/api/schemas/artifacts.py:164-232` - `ArtifactResponse`

---

## 7. Appendix: Backend API Schema Reference

```python
# skillmeat/api/schemas/artifacts.py

class ArtifactResponse(BaseModel):
    id: str                          # "type:name"
    name: str
    type: str                        # skill|command|agent|mcp|hook
    source: str                      # GitHub spec or local path
    origin: str                      # local|github|marketplace
    origin_source: Optional[str]     # github|gitlab|bitbucket
    version: str
    aliases: Optional[List[str]]
    tags: Optional[List[str]]
    metadata: Optional[ArtifactMetadataResponse]
    upstream: Optional[ArtifactUpstreamInfo]
    deployment_stats: Optional[DeploymentStatistics]
    collections: List[ArtifactCollectionInfo]
    added: datetime
    updated: datetime
```

---

*Report generated during investigation of rendering inconsistencies between /collection and /manage pages.*
