# Entity to Artifact Type Migration Guide

## Overview

This guide helps you migrate from the deprecated `Entity` type to the consolidated `Artifact` type in the SkillMeat web application.

### Why This Migration?

The Entity-to-Artifact consolidation eliminates unnecessary type duplication between frontend and backend, providing:

- **Single source of truth**: One `Artifact` type used consistently across the codebase
- **Simplified data flow**: No conversion needed between API responses and UI components
- **Reduced complexity**: Fewer type definitions, imports, and conversions to maintain
- **Better maintainability**: Changes to artifact structure only need to happen in one place

### Timeline

| Date | Status |
|------|--------|
| **January 2026** | Entity type deprecated, migration guide published |
| **Q3 2026** | Entity type removed entirely |

**Action Required**: Migrate all Entity usage to Artifact before Q3 2026.

---

## Migration Steps

### Step 1: Update Type Imports

Replace `Entity` imports with `Artifact`.

**Before:**
```typescript
import { Entity, EntityStatus, EntityMetadata } from '@/types';
import { ENTITY_TYPES } from '@/types/entity';
```

**After:**
```typescript
import { Artifact, SyncStatus } from '@/types';
import { ARTIFACT_TYPES } from '@/types/artifact';
```

**Note**: `EntityMetadata` is removed—metadata fields are now flattened into `Artifact`.

---

### Step 2: Update Component Props

Change component prop types from `Entity` to `Artifact`.

**Before:**
```typescript
interface ArtifactCardProps {
  entity: Entity;
  onSelect?: (entity: Entity) => void;
}

export function ArtifactCard({ entity, onSelect }: ArtifactCardProps) {
  return (
    <Card onClick={() => onSelect?.(entity)}>
      <h3>{entity.name}</h3>
    </Card>
  );
}
```

**After:**
```typescript
interface ArtifactCardProps {
  artifact: Artifact;
  onSelect?: (artifact: Artifact) => void;
}

export function ArtifactCard({ artifact, onSelect }: ArtifactCardProps) {
  return (
    <Card onClick={() => onSelect?.(artifact)}>
      <h3>{artifact.name}</h3>
    </Card>
  );
}
```

---

### Step 3: Update Metadata Access (Critical)

The `Artifact` type has a **flattened structure**—metadata fields are at the top level, not nested under `metadata`.

**Before:**
```typescript
function ArtifactDetails({ entity }: { entity: Entity }) {
  return (
    <div>
      <p>{entity.metadata?.description || 'No description'}</p>
      <p>By: {entity.metadata?.author || 'Unknown'}</p>
      <ul>
        {entity.metadata?.tags?.map(tag => <li key={tag}>{tag}</li>)}
      </ul>
      <p>License: {entity.metadata?.license || 'Unknown'}</p>
    </div>
  );
}
```

**After:**
```typescript
function ArtifactDetails({ artifact }: { artifact: Artifact }) {
  return (
    <div>
      <p>{artifact.description || 'No description'}</p>
      <p>By: {artifact.author || 'Unknown'}</p>
      <ul>
        {artifact.tags?.map(tag => <li key={tag}>{tag}</li>)}
      </ul>
      <p>License: {artifact.license || 'Unknown'}</p>
    </div>
  );
}
```

**Key Changes**:
- `entity.metadata?.description` → `artifact.description`
- `entity.metadata?.author` → `artifact.author`
- `entity.metadata?.tags` → `artifact.tags`
- `entity.metadata?.license` → `artifact.license`
- `entity.metadata?.dependencies` → `artifact.dependencies`

---

### Step 4: Update Status Property

The status property name has changed from `status` to `syncStatus`.

**Before:**
```typescript
import { EntityStatus } from '@/types';

function StatusBadge({ entity }: { entity: Entity }) {
  const statusColor = entity.status === 'synced' ? 'green' : 'yellow';
  return <Badge color={statusColor}>{entity.status}</Badge>;
}
```

**After:**
```typescript
import { SyncStatus } from '@/types';

function StatusBadge({ artifact }: { artifact: Artifact }) {
  const statusColor = artifact.syncStatus === 'synced' ? 'green' : 'yellow';
  return <Badge color={statusColor}>{artifact.syncStatus}</Badge>;
}
```

**Status Values** (new `error` value added):
- Old: `'synced' | 'modified' | 'outdated' | 'conflict'`
- New: `'synced' | 'modified' | 'outdated' | 'conflict' | 'error'`

---

### Step 5: Update Hook Usage

Update hooks to use `Artifact` type parameters.

**Before:**
```typescript
import { useArtifacts } from '@/hooks';

function MyComponent() {
  const { data: entities, isLoading } = useArtifacts();

  const handleSelect = (entity: Entity) => {
    console.log('Selected:', entity.name);
  };

  return (
    <div>
      {entities?.map(entity => (
        <ArtifactCard key={entity.id} entity={entity} onSelect={handleSelect} />
      ))}
    </div>
  );
}
```

**After:**
```typescript
import { useArtifacts } from '@/hooks';

function MyComponent() {
  const { data: artifacts, isLoading } = useArtifacts();

  const handleSelect = (artifact: Artifact) => {
    console.log('Selected:', artifact.name);
  };

  return (
    <div>
      {artifacts?.map(artifact => (
        <ArtifactCard key={artifact.id} artifact={artifact} onSelect={handleSelect} />
      ))}
    </div>
  );
}
```

---

### Step 6: Update Type Registries

Replace `ENTITY_TYPES` with `ARTIFACT_TYPES`.

**Before:**
```typescript
import { ENTITY_TYPES } from '@/types/entity';

const skillEntities = entities.filter(e => e.type === ENTITY_TYPES.SKILL);
```

**After:**
```typescript
import { ARTIFACT_TYPES } from '@/types/artifact';

const skillArtifacts = artifacts.filter(a => a.type === ARTIFACT_TYPES.SKILL);
```

---

## Common Patterns Reference

### Property Mappings

| Old Pattern (Entity) | New Pattern (Artifact) | Notes |
|----------------------|------------------------|-------|
| `entity.id` | `artifact.id` | Unchanged |
| `entity.name` | `artifact.name` | Unchanged |
| `entity.type` | `artifact.type` | Unchanged |
| `entity.version` | `artifact.version` | Unchanged |
| `entity.source` | `artifact.source` | Unchanged |
| `entity.status` | `artifact.syncStatus` | **Property renamed** |
| `entity.metadata?.description` | `artifact.description` | **Flattened** |
| `entity.metadata?.author` | `artifact.author` | **Flattened** |
| `entity.metadata?.license` | `artifact.license` | **Flattened** |
| `entity.metadata?.tags` | `artifact.tags` | **Flattened** |
| `entity.metadata?.dependencies` | `artifact.dependencies` | **Flattened** |
| `entity.createdAt` | `artifact.createdAt` | Unchanged |
| `entity.updatedAt` | `artifact.updatedAt` | Unchanged |

### Type Mappings

| Old Type | New Type | Notes |
|----------|----------|-------|
| `Entity` | `Artifact` | Main type |
| `EntityStatus` | `SyncStatus` | Enum renamed, added `'error'` value |
| `EntityMetadata` | *(removed)* | Fields flattened into `Artifact` |
| `ENTITY_TYPES` | `ARTIFACT_TYPES` | Registry renamed |

---

## Complete Migration Example

### Before (Entity-based)

```typescript
import { Entity, EntityStatus, ENTITY_TYPES } from '@/types';
import { useArtifacts } from '@/hooks';

interface ArtifactListProps {
  onSelect: (entity: Entity) => void;
}

export function ArtifactList({ onSelect }: ArtifactListProps) {
  const { data: entities, isLoading } = useArtifacts();

  const skills = entities?.filter(e => e.type === ENTITY_TYPES.SKILL);

  return (
    <div>
      {skills?.map(entity => (
        <div key={entity.id}>
          <h3>{entity.name}</h3>
          <p>{entity.metadata?.description}</p>
          <p>By: {entity.metadata?.author}</p>
          <span>Status: {entity.status}</span>
          <button onClick={() => onSelect(entity)}>Select</button>
        </div>
      ))}
    </div>
  );
}
```

### After (Artifact-based)

```typescript
import { Artifact, SyncStatus, ARTIFACT_TYPES } from '@/types';
import { useArtifacts } from '@/hooks';

interface ArtifactListProps {
  onSelect: (artifact: Artifact) => void;
}

export function ArtifactList({ onSelect }: ArtifactListProps) {
  const { data: artifacts, isLoading } = useArtifacts();

  const skills = artifacts?.filter(a => a.type === ARTIFACT_TYPES.SKILL);

  return (
    <div>
      {skills?.map(artifact => (
        <div key={artifact.id}>
          <h3>{artifact.name}</h3>
          <p>{artifact.description}</p>
          <p>By: {artifact.author}</p>
          <span>Status: {artifact.syncStatus}</span>
          <button onClick={() => onSelect(artifact)}>Select</button>
        </div>
      ))}
    </div>
  );
}
```

---

## FAQ

### Q: Why was metadata flattened?

**A**: Metadata was originally a nested object to group optional fields. However, this added unnecessary complexity:
- Required optional chaining everywhere (`entity.metadata?.description`)
- Created inconsistency (some fields at top level, others nested)
- Made type definitions more complex

Flattening metadata makes the type simpler and more consistent.

### Q: Do I need to update API calls?

**A**: No. The API already returns `Artifact` types. The migration removes frontend conversion logic that was translating API responses into `Entity` types.

### Q: What if I'm using third-party libraries that expect Entity?

**A**: You should update those integrations to use `Artifact`. If you maintain a library, publish an updated version. If it's external, consider creating a small adapter until the library updates.

### Q: Can I use both types during migration?

**A**: Yes. The `Entity` type is deprecated but still available. However, mixing both types in the same file or component is discouraged—complete migration per file is recommended.

### Q: Will the Entity type be completely removed?

**A**: Yes, in Q3 2026. All deprecation warnings will become errors at that point.

### Q: What about `entityToArtifact` conversion functions?

**A**: These are being removed as part of the migration. Since the API now returns `Artifact` directly, no conversion is needed.

---

## Migration Checklist

Use this checklist to verify your migration is complete:

### Type Imports
- [ ] Replace `Entity` imports with `Artifact`
- [ ] Replace `EntityStatus` imports with `SyncStatus`
- [ ] Remove `EntityMetadata` imports
- [ ] Replace `ENTITY_TYPES` with `ARTIFACT_TYPES`

### Component Props
- [ ] Update all component prop types from `Entity` to `Artifact`
- [ ] Update prop variable names from `entity` to `artifact`
- [ ] Update callback signatures to use `Artifact`

### Metadata Access
- [ ] Change `entity.metadata?.description` → `artifact.description`
- [ ] Change `entity.metadata?.author` → `artifact.author`
- [ ] Change `entity.metadata?.license` → `artifact.license`
- [ ] Change `entity.metadata?.tags` → `artifact.tags`
- [ ] Change `entity.metadata?.dependencies` → `artifact.dependencies`

### Status Property
- [ ] Change `entity.status` → `artifact.syncStatus`
- [ ] Update type references from `EntityStatus` to `SyncStatus`

### Hook Usage
- [ ] Update hook return types to use `Artifact`
- [ ] Update variable names from `entities` to `artifacts`
- [ ] Update callback signatures

### Type Registries
- [ ] Replace `ENTITY_TYPES.*` with `ARTIFACT_TYPES.*`

### Testing
- [ ] Run TypeScript compiler (`pnpm type-check`)
- [ ] Run tests (`pnpm test`)
- [ ] Verify no deprecation warnings in console
- [ ] Test all affected components in UI

---

## Need Help?

If you encounter issues during migration:

1. **Check the type definitions**: Review `/web/types/artifact.ts` for the complete `Artifact` interface
2. **Look at examples**: Check `/web/app/(dashboard)/(artifacts)/manage/page.tsx` for a complete example
3. **Search the codebase**: Look for other migrated components using `grep -r "artifact: Artifact" web/`
4. **Ask for help**: Open an issue or discussion on the SkillMeat repository

---

**Last Updated**: January 2026
**Deprecation Date**: January 2026
**Removal Date**: Q3 2026
