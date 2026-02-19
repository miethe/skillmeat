---
status: inferred_complete
---
# Phase 4-5: Component Unification & Deprecation

**Phases**: 4 & 5
**Effort**: 19 story points
**Duration**: 7-10 days
**Dependencies**: Phase 1-3 complete
**Critical Path**: Phase 4 (blocks completion), Phase 5 (docs/cleanup only)

---

## Phase Overview

### Phase 4: Component Type Unification

**Goal**: Update all components accepting Entity type to use unified Artifact type instead. Update modal and form components to handle flattened metadata. Enforce required modal handlers. Ensure type consistency across all pages and modals.

### Phase 5: Deprecation & Cleanup

**Goal**: Add deprecation notices to old types. Document migration path. Audit remaining Entity usages. Update architecture documentation. Plan removal timeline.

---

## Phase 4: Component Type Unification

### P4-T1: Update UnifiedEntityModal Props

**Task ID**: P4-T1
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `ui-engineer-enhanced`

**Description**:
Update `UnifiedEntityModal` component props to accept `Artifact` type instead of `Entity`. Make navigation handlers required when artifact has source. Update modal to handle flattened metadata structure.

**File**: `skillmeat/web/components/entity/unified-entity-modal.tsx`

**Changes**:
```typescript
import type { Artifact } from '@/types';

interface UnifiedEntityModalProps {
  entity: Artifact | null;  // Changed from Entity to Artifact
  open: boolean;
  onClose: () => void;

  // Navigation handlers - required when entity has source
  onNavigateToSource: (sourceId: string, path: string) => void;
  onNavigateToDeployment: (projectPath: string, artifactId: string) => void;

  // Optional: custom title
  title?: string;
}

export function UnifiedEntityModal({
  entity,
  open,
  onClose,
  onNavigateToSource,
  onNavigateToDeployment,
  title,
}: UnifiedEntityModalProps) {
  // Runtime validation: warn if handlers not provided for artifacts with source
  useEffect(() => {
    if (entity?.source && !onNavigateToSource) {
      console.warn(
        'UnifiedEntityModal: onNavigateToSource handler not provided for artifact with source',
        entity.id
      );
    }
  }, [entity, onNavigateToSource]);

  // Component continues to work as before, but now accepts Artifact type
  // Modal tabs access properties from flat Artifact structure:
  // - entity.description (not entity.metadata?.description)
  // - entity.author (not entity.metadata?.author)
  // - entity.tags (not entity.metadata?.tags)
  // etc.

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        {/* Modal tabs continue to work with flattened structure */}
        <BasicInfoTab artifact={entity} />
        <CollectionsTab artifact={entity} />
        <SourcesTab
          artifact={entity}
          onNavigateToSource={onNavigateToSource}
        />
        <UpstreamTab artifact={entity} />
      </DialogContent>
    </Dialog>
  );
}
```

**Acceptance Criteria**:
- [ ] Props accept `Artifact` type (not `Entity`)
- [ ] Navigation handlers remain same signature
- [ ] Runtime warning for missing handlers on artifacts with source
- [ ] Modal tabs access flattened properties
- [ ] TypeScript compilation succeeds
- [ ] All modal functionality preserved
- [ ] Visual appearance unchanged

---

### P4-T2: Update Modal Tab Components

**Task ID**: P4-T2
**Effort**: 3 points
**Duration**: 1.5 days
**Assigned**: `ui-engineer-enhanced`

**Description**:
Update all modal tab components to accept `Artifact` type and access flattened metadata. Specifically update `modal-collections-tab.tsx`, `modal-sources-tab.tsx`, and other tab components.

**Files**:
- `skillmeat/web/components/entity/modal-collections-tab.tsx`
- `skillmeat/web/components/entity/modal-sources-tab.tsx`
- `skillmeat/web/components/entity/modal-upstream-tab.tsx`
- `skillmeat/web/components/entity/modal-basic-info-tab.tsx`

**Example Changes**:

**modal-basic-info-tab.tsx** (before):
```typescript
interface BasicInfoTabProps {
  entity: Entity;
}

export function BasicInfoTab({ entity }: BasicInfoTabProps) {
  return (
    <div>
      <p>{entity.metadata?.description}</p>
      <p>Author: {entity.metadata?.author}</p>
      <p>License: {entity.metadata?.license}</p>
      <ul>
        {entity.metadata?.tags?.map(tag => (
          <li key={tag}>{tag}</li>
        ))}
      </ul>
    </div>
  );
}
```

**modal-basic-info-tab.tsx** (after):
```typescript
interface BasicInfoTabProps {
  artifact: Artifact;
}

export function BasicInfoTab({ artifact }: BasicInfoTabProps) {
  return (
    <div>
      <p>{artifact.description}</p>
      <p>Author: {artifact.author}</p>
      <p>License: {artifact.license}</p>
      <ul>
        {artifact.tags?.map(tag => (
          <li key={tag}>{tag}</li>
        ))}
      </ul>
    </div>
  );
}
```

**modal-collections-tab.tsx** (before):
```typescript
interface CollectionsTabProps {
  entity: Entity;
}

export function CollectionsTab({ entity }: CollectionsTabProps) {
  return (
    <div>
      {!entity.collections || entity.collections.length === 0 ? (
        <p>No collections</p>
      ) : (
        <ul>
          {entity.collections.map(col => (
            <li key={col.id}>{col.name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**modal-collections-tab.tsx** (after):
```typescript
interface CollectionsTabProps {
  artifact: Artifact;
}

export function CollectionsTab({ artifact }: CollectionsTabProps) {
  return (
    <div>
      {!artifact.collections || artifact.collections.length === 0 ? (
        <p>No collections</p>
      ) : (
        <ul>
          {artifact.collections.map(col => (
            <li key={col.id}>{col.name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] All tab components accept `Artifact` type
- [ ] All access flattened metadata structure
- [ ] No more `metadata?.` paths
- [ ] Collections tab displays correctly (should now be populated)
- [ ] Sources tab shows source information
- [ ] Upstream tab shows upstream tracking
- [ ] TypeScript compilation succeeds
- [ ] All tests pass

---

### P4-T3: Update Entity Form Component

**Task ID**: P4-T3
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `ui-engineer-enhanced`

**Description**:
Update `entity-form.tsx` to accept `Artifact` type. Update form field binding to use flattened properties. Ensure form submission produces correct Artifact structure.

**File**: `skillmeat/web/components/entity/entity-form.tsx`

**Changes**:
```typescript
import type { Artifact } from '@/types';

interface EntityFormProps {
  artifact?: Artifact; // Changed from Entity
  onSubmit: (artifact: Artifact) => Promise<void>;
  isLoading?: boolean;
}

export function EntityForm({
  artifact,
  onSubmit,
  isLoading = false,
}: EntityFormProps) {
  // Form fields bind to flattened Artifact properties
  const [formData, setFormData] = useState<Artifact>(
    artifact || createEmptyArtifact()
  );

  // Field mapping: form inputs directly match Artifact properties
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, name: e.target.value }));
  };

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, description: e.target.value }));
  };

  const handleTagsChange = (tags: string[]) => {
    setFormData(prev => ({ ...prev, tags }));
  };

  // Form submission returns Artifact with all fields
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={formData.name}
        onChange={handleNameChange}
        placeholder="Name"
      />
      <textarea
        value={formData.description || ''}
        onChange={handleDescriptionChange}
        placeholder="Description"
      />
      <TagInput
        value={formData.tags || []}
        onChange={handleTagsChange}
      />
      {/* Other fields for author, license, version, etc. */}
      <button type="submit" disabled={isLoading}>
        Save
      </button>
    </form>
  );
}

function createEmptyArtifact(): Artifact {
  return {
    id: '',
    name: '',
    type: 'skill',
    scope: 'user',
    syncStatus: 'synced',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}
```

**Acceptance Criteria**:
- [ ] Form accepts `Artifact` type
- [ ] Form fields bind to flattened properties
- [ ] Form submission returns complete Artifact
- [ ] No nested metadata object in form
- [ ] TypeScript compilation succeeds
- [ ] Form validation works
- [ ] CRUD operations work (create/edit/delete)
- [ ] All tests pass

---

### P4-T4: Update Collection Page

**Task ID**: P4-T4
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `ui-engineer-enhanced`

**Description**:
Update `app/collection/page.tsx` to use `Artifact` type throughout. Remove any remaining Entity-specific logic. Ensure modal is opened with navigation handlers.

**File**: `skillmeat/web/app/collection/page.tsx`

**Changes**:
```typescript
import type { Artifact } from '@/types';
import { useInfiniteArtifacts } from '@/hooks/useArtifacts';

export default function CollectionPage() {
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const router = useRouter();

  // Hook returns Artifact[] (unified type)
  const { data, fetchNextPage, hasNextPage } = useInfiniteArtifacts();
  const artifacts = useMemo(
    () => data?.pages.flatMap(page => page.items) ?? [],
    [data]
  );

  // Modal handler: navigate to artifact source (GitHub, etc.)
  const handleNavigateToSource = (sourceId: string, path: string) => {
    router.push(`/marketplace/sources/${sourceId}/${path}`);
  };

  // Modal handler: navigate to artifact deployment
  const handleNavigateToDeployment = (projectPath: string, artifactId: string) => {
    router.push(`/projects/${projectPath}/artifacts/${artifactId}`);
  };

  // Click handler: open modal with artifact (no conversion needed)
  const handleArtifactClick = (artifact: Artifact) => {
    setSelectedArtifact(artifact); // Direct assignment, no artifactToEntity() conversion
  };

  return (
    <>
      <div className="artifacts-grid">
        {artifacts.map(artifact => (
          <ArtifactCard
            key={artifact.id}
            artifact={artifact}
            onClick={handleArtifactClick}
          />
        ))}
      </div>

      {/* Modal receives navigation handlers */}
      <UnifiedEntityModal
        entity={selectedArtifact}
        open={!!selectedArtifact}
        onClose={() => setSelectedArtifact(null)}
        onNavigateToSource={handleNavigateToSource}
        onNavigateToDeployment={handleNavigateToDeployment}
      />
    </>
  );
}
```

**Acceptance Criteria**:
- [ ] Page uses `Artifact` type throughout
- [ ] No Entity-specific logic remaining
- [ ] Modal receives navigation handlers
- [ ] No `artifactToEntity()` conversion
- [ ] Click handlers work correctly
- [ ] Modal opens with complete data
- [ ] TypeScript compilation succeeds
- [ ] All tests pass

---

### P4-T5: Update Manage Page

**Task ID**: P4-T5
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `ui-engineer-enhanced`

**Description**:
Update `app/manage/page.tsx` to use `Artifact` type consistently. Ensure form and modal components handle unified type correctly.

**File**: `skillmeat/web/app/manage/page.tsx`

**Changes**:
```typescript
import type { Artifact } from '@/types';
import { useEntityLifecycle } from '@/hooks/useEntityLifecycle';

export default function ManagePage() {
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const router = useRouter();

  // Hook returns Artifact[] (Entity is alias)
  const { data: artifacts, isLoading, mutate } = useEntityLifecycle({
    mode: 'project',
  });

  // Modal handlers for navigation
  const handleNavigateToSource = (sourceId: string, path: string) => {
    router.push(`/marketplace/sources/${sourceId}/${path}`);
  };

  const handleNavigateToDeployment = (projectPath: string, artifactId: string) => {
    router.push(`/projects/${projectPath}/artifacts/${artifactId}`);
  };

  // Form handlers for CRUD
  const handleCreateArtifact = async (artifact: Artifact) => {
    await apiClient.artifacts.create(artifact);
    mutate();
    setIsFormOpen(false);
  };

  const handleUpdateArtifact = async (artifact: Artifact) => {
    await apiClient.artifacts.update(artifact.id, artifact);
    mutate();
    setIsFormOpen(false);
    setSelectedArtifact(null);
  };

  const handleDeleteArtifact = async (artifactId: string) => {
    await apiClient.artifacts.delete(artifactId);
    mutate();
    setSelectedArtifact(null);
  };

  return (
    <>
      <div className="manage-container">
        <div className="artifacts-list">
          {artifacts?.map(artifact => (
            <ArtifactRow
              key={artifact.id}
              artifact={artifact}
              onClick={setSelectedArtifact}
            />
          ))}
        </div>

        {/* Modal with navigation handlers */}
        <UnifiedEntityModal
          entity={selectedArtifact}
          open={!!selectedArtifact}
          onClose={() => setSelectedArtifact(null)}
          onNavigateToSource={handleNavigateToSource}
          onNavigateToDeployment={handleNavigateToDeployment}
        />

        {/* Form for CRUD operations */}
        <EntityForm
          artifact={selectedArtifact}
          onSubmit={
            selectedArtifact
              ? handleUpdateArtifact
              : handleCreateArtifact
          }
          isLoading={isLoading}
        />
      </div>
    </>
  );
}
```

**Acceptance Criteria**:
- [ ] Page uses `Artifact` type (Entity is alias)
- [ ] Form and modal components work correctly
- [ ] CRUD operations work (create/update/delete)
- [ ] Collections tab shows data (bug fix verified)
- [ ] Modal opens with complete data
- [ ] Navigation handlers provided
- [ ] TypeScript compilation succeeds
- [ ] All tests pass

---

### P4-T6: Update Additional Components

**Task ID**: P4-T6
**Effort**: 3 points
**Duration**: 1.5 days
**Assigned**: `ui-engineer-enhanced`

**Description**:
Update remaining Entity-typed components across the codebase. Review all component files in `components/entity/` and `components/sync-status/` directories.

**Components to Update** (estimated 10-15 files):
- `components/entity/entity-list.tsx` → Accept Artifact
- `components/entity/entity-crud-modal.tsx` → Accept Artifact
- `components/entity/artifact-card.tsx` → Accept Artifact
- `components/sync-status/sync-status-badge.tsx` → Accept Artifact
- `components/sync-status/sync-status-dialog.tsx` → Accept Artifact
- `components/sync-status/sync-status-tab.tsx` → Accept Artifact
- Other related components

**Process**:
```bash
# Find all files using Entity type
grep -r "Entity" skillmeat/web/components --include="*.tsx" | grep -v "node_modules"

# Update each file to use Artifact instead
# Verify TypeScript compilation after each update
tsc --noEmit skillmeat/web/components/entity/*.tsx
tsc --noEmit skillmeat/web/components/sync-status/*.tsx
```

**Acceptance Criteria**:
- [ ] All Entity-typed components updated
- [ ] All components accept Artifact type
- [ ] Type consistency across all components
- [ ] TypeScript compilation succeeds
- [ ] All component tests pass
- [ ] No Entity type used in component props (except deprecation imports)

---

### P4-T7: Component Integration Testing

**Task ID**: P4-T7
**Effort**: 3 points
**Duration**: 1.5 days
**Assigned**: `ui-engineer-enhanced`

**Description**:
Comprehensive testing of all updated components. Test component interactions, form submission, modal behavior, navigation. Verify visual appearance unchanged.

**Test Files**:
- `components/entity/unified-entity-modal.test.tsx`
- `components/entity/entity-form.test.tsx`
- `app/collection/page.test.tsx`
- `app/manage/page.test.tsx`

**Test Coverage**:

```typescript
describe('UnifiedEntityModal with Artifact type', () => {
  it('should render with Artifact prop', () => {
    const artifact: Artifact = {
      id: 'skill:test',
      name: 'Test',
      type: 'skill',
      scope: 'user',
      syncStatus: 'synced',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      description: 'Test description',
      author: 'Test Author',
      tags: ['tag1'],
    };

    const { getByText } = render(
      <UnifiedEntityModal
        entity={artifact}
        open={true}
        onClose={() => {}}
        onNavigateToSource={() => {}}
        onNavigateToDeployment={() => {}}
      />
    );

    expect(getByText('Test description')).toBeInTheDocument();
    expect(getByText('Test Author')).toBeInTheDocument();
  });

  it('should display collections tab with artifact collections', () => {
    const artifact: Artifact = {
      // ...
      collections: [
        { id: 'col1', name: 'Collection 1', artifact_count: 5 },
      ],
    };

    const { getByText } = render(
      <UnifiedEntityModal
        entity={artifact}
        open={true}
        onClose={() => {}}
        onNavigateToSource={() => {}}
        onNavigateToDeployment={() => {}}
      />
    );

    expect(getByText('Collection 1')).toBeInTheDocument();
  });

  it('should call navigation handlers when provided', async () => {
    const handleNavigateToSource = jest.fn();
    const artifact: Artifact = {
      // ...
      source: 'user/repo/skill',
    };

    const { getByRole } = render(
      <UnifiedEntityModal
        entity={artifact}
        open={true}
        onClose={() => {}}
        onNavigateToSource={handleNavigateToSource}
        onNavigateToDeployment={() => {}}
      />
    );

    const sourceLink = getByRole('button', { name: /view source/i });
    await userEvent.click(sourceLink);

    expect(handleNavigateToSource).toHaveBeenCalled();
  });
});

describe('EntityForm with Artifact type', () => {
  it('should submit complete Artifact object', async () => {
    const onSubmit = jest.fn();

    const { getByLabelText, getByRole } = render(
      <EntityForm onSubmit={onSubmit} />
    );

    await userEvent.type(getByLabelText(/name/i), 'New Artifact');
    await userEvent.type(getByLabelText(/description/i), 'Test description');
    await userEvent.click(getByRole('button', { name: /save/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'New Artifact',
        description: 'Test description',
      })
    );
  });
});

describe('/collection page with Artifact type', () => {
  it('should display artifacts and open modal without conversion', async () => {
    const mockArtifacts: Artifact[] = [
      {
        id: 'skill:test1',
        name: 'Test 1',
        type: 'skill',
        scope: 'user',
        syncStatus: 'synced',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    // Mock useInfiniteArtifacts to return test data
    // Render page
    // Click artifact
    // Verify modal opens with same Artifact object (no conversion)
    // Verify navigation handlers provided
  });

  it('should show collections in modal', async () => {
    const mockArtifacts: Artifact[] = [
      {
        // ...
        collections: [{ id: 'col1', name: 'Collection 1' }],
      },
    ];

    // Render and open modal
    // Verify collections tab shows collection
  });
});

describe('/manage page with Artifact type', () => {
  it('should display artifacts with collections data', async () => {
    const mockArtifacts: Artifact[] = [
      {
        // ...
        collections: [{ id: 'col1', name: 'Collection 1' }],
      },
    ];

    // Render page
    // Verify artifacts displayed with collections
    // Open modal
    // Verify collections tab populated
  });

  it('should handle form submission with Artifact type', async () => {
    // Test create/update/delete operations
  });
});
```

**Acceptance Criteria**:
- [ ] All component tests pass
- [ ] >80% test coverage for updated components
- [ ] Modal displays complete artifact data
- [ ] Collections tab shows data (was empty, now populated)
- [ ] Form submission works with new type
- [ ] Navigation handlers called correctly
- [ ] No visual regression
- [ ] All integration tests pass

---

## Phase 5: Deprecation & Cleanup

### P5-T1: Add Deprecation Notices

**Task ID**: P5-T1
**Effort**: 1 point
**Duration**: 0.5 days
**Assigned**: `documentation-writer`

**Description**:
Add comprehensive deprecation notices to old Entity type definition and related exports. Include migration guide references and removal timeline.

**File**: `skillmeat/web/types/entity.ts`

**Changes**:
```typescript
/**
 * DEPRECATED: This module is maintained for backward compatibility only.
 *
 * MIGRATION REQUIRED - All Entity type usages should be replaced with Artifact.
 *
 * Timeline:
 * - January 2026: Deprecation phase begins (this file)
 * - Q2 2026: Removal phase begins (Entity types removed)
 * - June 2026: Complete removal
 *
 * Migration Guide:
 * - Replace import from 'types/entity' with 'types/artifact'
 * - Replace Entity with Artifact
 * - Replace EntityStatus with SyncStatus
 * - Replace ENTITY_TYPES with ARTIFACT_TYPES
 *
 * See: .claude/guides/entity-to-artifact-migration.md
 */

/**
 * @deprecated Use Artifact from types/artifact instead
 * This interface is maintained for backward compatibility until Q2 2026.
 *
 * The Entity type has been consolidated into the Artifact type to provide
 * a single source of truth for artifact representation across collection
 * and project contexts.
 *
 * See: .claude/guides/entity-to-artifact-migration.md
 */
export type Entity = Artifact;

/**
 * @deprecated Use SyncStatus from types/artifact instead
 */
export type EntityStatus = SyncStatus;

// All other exports include similar @deprecated notices
```

**JSDoc Examples**:
```typescript
/**
 * Get configuration for entity type.
 * @deprecated Use getArtifactTypeConfig instead
 *
 * This function is maintained for backward compatibility until Q2 2026.
 * New code should use getArtifactTypeConfig from types/artifact.
 */
export function getEntityTypeConfig(type: string): ArtifactTypeConfig {
  return getArtifactTypeConfig(type as ArtifactType);
}

/**
 * Entity type configuration registry.
 * @deprecated Use ARTIFACT_TYPES instead
 *
 * Maintained for backward compatibility until Q2 2026.
 * New code should import ARTIFACT_TYPES from types/artifact.
 */
export const ENTITY_TYPES = ARTIFACT_TYPES;
```

**Acceptance Criteria**:
- [ ] All Entity type exports marked as `@deprecated`
- [ ] Deprecation messages include removal timeline
- [ ] Migration guide referenced in all notices
- [ ] IDE shows deprecation warnings
- [ ] JSDoc comments clear and helpful

---

### P5-T2: Create Migration Guide

**Task ID**: P5-T2
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `documentation-writer`

**Description**:
Create comprehensive migration guide for developers explaining how to update their code from Entity to Artifact types. Include before/after examples, common patterns, FAQ.

**File**: `.claude/guides/entity-to-artifact-migration.md` (NEW)

**Content**:
```markdown
# Entity to Artifact Type Migration Guide

**Status**: This guide documents the migration from Entity to Artifact types.
**Timeline**: January 2026 - June 2026
**Last Updated**: 2026-01-28

## Overview

The Entity and Artifact types have been consolidated into a single `Artifact` type.
This guide explains how to update your code to use the new unified type system.

## Why This Change?

- **Single source of truth**: One type definition instead of two
- **Fewer bugs**: No more parallel conversion logic
- **Better maintainability**: Changes in one place instead of three
- **Type safety**: Stricter enforcement prevents modal-related bugs

## Migration Path

### Timeline

- **January 2026**: Deprecation phase begins - old types still work but show warnings
- **Q2 2026**: Removal phase begins - prepare for type removal
- **June 2026**: Final removal - all Entity types and imports removed

### Compatibility

During the deprecation phase (Jan-Jun 2026):
- Old imports still work: `import { Entity } from '@/types'`
- IDE shows deprecation warnings but code compiles
- Type checking passes: `Entity` is aliased to `Artifact`
- No runtime changes or breaking behavior

## Step-by-Step Migration

### Step 1: Update Type Imports

**Before**:
```typescript
import type { Entity, EntityStatus } from '@/types';

interface ComponentProps {
  entity: Entity;
  status: EntityStatus;
}
```

**After**:
```typescript
import type { Artifact, SyncStatus } from '@/types';

interface ComponentProps {
  artifact: Artifact;
  status: SyncStatus;
}
```

### Step 2: Update Registry Imports

**Before**:
```typescript
import { ENTITY_TYPES, getEntityTypeConfig } from '@/types';

const config = getEntityTypeConfig('skill');
```

**After**:
```typescript
import { ARTIFACT_TYPES, getArtifactTypeConfig } from '@/types';

const config = getArtifactTypeConfig('skill');
```

### Step 3: Update Component Props

**Before**:
```typescript
interface ModalProps {
  entity: Entity | null;
  onClose: () => void;
}

export function MyModal({ entity, onClose }: ModalProps) {
  return (
    <div>
      <p>{entity?.metadata?.description}</p>
    </div>
  );
}
```

**After**:
```typescript
interface ModalProps {
  artifact: Artifact | null;
  onClose: () => void;
}

export function MyModal({ artifact, onClose }: ModalProps) {
  return (
    <div>
      <p>{artifact?.description}</p>
    </div>
  );
}
```

### Step 4: Update Metadata Access

The Artifact type flattens metadata from nested objects to top-level properties.

**Before**:
```typescript
entity.metadata?.description
entity.metadata?.author
entity.metadata?.license
entity.metadata?.tags
```

**After**:
```typescript
artifact.description
artifact.author
artifact.license
artifact.tags
```

### Step 5: Update Hook Usage

**Before**:
```typescript
const { data: entities } = useEntityLifecycle();
entities.map(entity => (
  <EntityCard key={entity.id} entity={entity} />
))
```

**After**:
```typescript
const { data: artifacts } = useEntityLifecycle();
artifacts.map(artifact => (
  <ArtifactCard key={artifact.id} artifact={artifact} />
))
```

Note: `useEntityLifecycle` still returns Entity type (alias for Artifact), but you can treat it as Artifact.

## Common Patterns

### Accessing Properties

| Property | Old Path | New Path |
|----------|----------|----------|
| Description | `entity.metadata?.description` | `artifact.description` |
| Author | `entity.metadata?.author` | `artifact.author` |
| License | `entity.metadata?.license` | `artifact.license` |
| Tags | `entity.metadata?.tags` | `artifact.tags` |
| Dependencies | `entity.metadata?.dependencies` | `artifact.dependencies` |
| Status | `entity.status` | `artifact.syncStatus` |
| Collections | `entity.collections` | `artifact.collections` |

### Form Submission

**Before**:
```typescript
const handleSubmit = async (entity: Entity) => {
  await api.updateEntity({
    ...entity,
    metadata: {
      description: entity.metadata?.description,
      author: entity.metadata?.author,
      tags: entity.metadata?.tags,
    },
  });
};
```

**After**:
```typescript
const handleSubmit = async (artifact: Artifact) => {
  await api.updateArtifact({
    ...artifact,
    // No metadata nesting needed - properties at top level
  });
};
```

### Type Guards

**Before**:
```typescript
function isEntity(obj: unknown): obj is Entity {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'name' in obj &&
    'type' in obj
  );
}
```

**After**:
```typescript
function isArtifact(obj: unknown): obj is Artifact {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'name' in obj &&
    'type' in obj &&
    'syncStatus' in obj
  );
}
```

## FAQ

### Q: Do I have to update my code now?

**A**: No. During the deprecation phase (Jan-Jun 2026), old Entity imports still work. However, you'll see deprecation warnings in your IDE. It's recommended to update at your earliest convenience.

### Q: What if I forget to update before June 2026?

**A**: The types will be removed in Q2 2026. Code using Entity types will fail TypeScript compilation. Start migration early to avoid urgent updates.

### Q: Is the change backward compatible?

**A**: Yes, during the deprecation phase. `Entity` is aliased to `Artifact`, so old code compiles without changes. However, the IDE will show warnings encouraging migration.

### Q: What about runtime behavior - will anything break?

**A**: No. This is purely a type-level change. Runtime behavior is identical. The only differences are:
- Type names (Entity → Artifact)
- Property access patterns (metadata flattening)
- Status enum values (EntityStatus → SyncStatus)

### Q: What are the new status values?

**Old** (EntityStatus):
- `synced` - Matches source
- `modified` - Local changes
- `outdated` - Newer version available
- `conflict` - Merge conflict

**New** (SyncStatus):
- `synced` - Matches source (same)
- `modified` - Local changes (same)
- `outdated` - Newer version available (same)
- `conflict` - Unresolvable conflict (renamed from just "conflict")
- `error` - Error in sync process (new)

### Q: Where can I find more help?

**A**: See the related documentation:
- Type definitions: `skillmeat/web/types/artifact.ts`
- Architecture docs: `skillmeat/web/CLAUDE.md`
- Implementation plan: `docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1.md`

## Checklist

Use this checklist when migrating your code:

- [ ] Updated type imports from Entity to Artifact
- [ ] Updated registry imports from ENTITY_TYPES to ARTIFACT_TYPES
- [ ] Updated component props to accept Artifact
- [ ] Updated metadata access to use flattened properties
- [ ] Ran `tsc --noEmit` to check for type errors
- [ ] Updated related tests
- [ ] Verified visual appearance unchanged
- [ ] Removed IDE deprecation warnings

## Need Help?

If you encounter issues during migration:

1. Check this guide for your specific use case
2. Review the type definitions in `skillmeat/web/types/artifact.ts`
3. Look at recent changes in implementation plan
4. File an issue or reach out to the team

---

**Document Owner**: Frontend Architecture
**Last Updated**: 2026-01-28
**Next Review**: Q2 2026 (removal phase)
```

**Acceptance Criteria**:
- [ ] Comprehensive migration guide written
- [ ] Step-by-step instructions provided
- [ ] Before/after examples included
- [ ] Common patterns documented
- [ ] FAQ addresses likely questions
- [ ] Checklist provided for developers
- [ ] Timeline clearly stated
- [ ] Document is well-organized and easy to follow

---

### P5-T3: Update Architecture & Documentation

**Task ID**: P5-T3
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `documentation-writer`

**Description**:
Update `skillmeat/web/CLAUDE.md` and architecture docs to reference Artifact type instead of Entity. Update examples and patterns to use new type system. Update type system section.

**Files to Update**:
- `skillmeat/web/CLAUDE.md` - Update type references in architecture section
- `docs/project_plans/architecture/` - Update architecture diagrams and docs
- `.claude/context/key-context/component-patterns.md` - Update component examples

**Changes to skillmeat/web/CLAUDE.md**:

**Before**:
```markdown
## Type System

### Entity Type

The Entity type represents an artifact in collection or project context:

\`\`\`typescript
interface Entity {
  id: string;
  name: string;
  type: EntityType;
  status?: EntityStatus;  // 'synced' | 'modified' | 'outdated' | 'conflict'
  metadata?: ArtifactMetadata;  // Nested: description, author, license, tags
  // ...
}
\`\`\`
```

**After**:
```markdown
## Type System

### Artifact Type (Unified)

The Artifact type represents a skill, command, agent, MCP server, or hook
across collection and project contexts. All metadata is flattened to top-level
properties for consistency and simplicity.

\`\`\`typescript
interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;  // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'
  scope: ArtifactScope;  // 'user' | 'local'
  syncStatus: SyncStatus;  // 'synced' | 'modified' | 'outdated' | 'conflict' | 'error'

  // Flattened metadata (formerly nested)
  description?: string;
  author?: string;
  license?: string;
  tags?: string[];

  // Context indicators
  collection?: string;  // Collection scope
  projectPath?: string;  // Project scope

  // Optional tracking
  upstream?: { ... };
  usageStats?: { ... };
}
\`\`\`

**Deprecation Note**: The old `Entity` type is maintained as an alias to `Artifact`
for backward compatibility through Q2 2026. See migration guide for update instructions.
```

**Acceptance Criteria**:
- [ ] `CLAUDE.md` updated with Artifact type references
- [ ] Examples use new flattened metadata structure
- [ ] Status enum values updated (including 'error')
- [ ] Migration guide referenced
- [ ] Architecture diagrams updated if needed
- [ ] Type system section is current
- [ ] All documentation consistent

---

### P5-T4: Code Audit & Cleanup

**Task ID**: P5-T4
**Effort**: 1 point
**Duration**: 0.5 days
**Assigned**: `documentation-writer`

**Description**:
Audit codebase for remaining direct Entity type usages. Create list of files needing updates in future phases. Verify all deprecation notices are in place.

**Process**:
```bash
# Find all remaining Entity type usages
grep -r "Entity" skillmeat/web --include="*.ts" --include="*.tsx" \
  | grep -v "node_modules" \
  | grep -v ".deprecated" \
  | grep -v "UnifiedEntityModal"  # Intentional name

# Find remaining ENTITY_TYPES usages
grep -r "ENTITY_TYPES" skillmeat/web --include="*.ts" --include="*.tsx"

# Find remaining getEntityTypeConfig usages
grep -r "getEntityTypeConfig" skillmeat/web --include="*.ts" --include="*.tsx"
```

**Expected Results**:
- Less than 10 direct Entity type usages (mostly in entity.ts)
- Intentional usages only (like UnifiedEntityModal component name)
- All direct imports updated or marked as deprecated
- All conversion functions removed

**Acceptance Criteria**:
- [ ] Audit completed
- [ ] Remaining Entity usages documented (<10 files)
- [ ] All usages are intentional or marked as deprecated
- [ ] No stray conversion functions remaining
- [ ] Audit report generated

---

### P5-T5: Final Validation & Sign-Off

**Task ID**: P5-T5
**Effort**: 2 points
**Duration**: 1 day
**Assigned**: `documentation-writer`

**Description**:
Final comprehensive validation of entire consolidation. Verify all phases complete and working together. Test all bug fixes. Get sign-off from team.

**Validation Checklist**:

**Type System**:
- [ ] Artifact type defined and exported
- [ ] SyncStatus enum with 5 values
- [ ] Backward compatibility aliases in place
- [ ] Old type imports show deprecation warnings
- [ ] TypeScript strict mode passes

**Registry & Configuration**:
- [ ] ARTIFACT_TYPES registry defined
- [ ] All 5 types included with same fields
- [ ] ENTITY_TYPES aliased to ARTIFACT_TYPES
- [ ] Form schemas unchanged visually
- [ ] Validation works for all types

**API Mapping**:
- [ ] mapApiResponseToArtifact() single function
- [ ] determineSyncStatus() handles all 5 status values
- [ ] All 4 old conversion functions removed
- [ ] Both pipelines use unified mapper
- [ ] No data loss in conversion

**Components**:
- [ ] All components accept Artifact type
- [ ] Modal displays complete data from both pages
- [ ] Collections tab populated (bug fix)
- [ ] Source tab appears (bug fix)
- [ ] Navigation handlers consistently provided

**Testing**:
- [ ] Unit tests >85% coverage
- [ ] Integration tests pass
- [ ] Component tests pass
- [ ] E2E tests pass
- [ ] Visual regression tests pass

**Documentation**:
- [ ] Migration guide complete
- [ ] CLAUDE.md updated
- [ ] Deprecation notices in place
- [ ] Architecture docs updated
- [ ] Removal timeline documented

**Bug Fixes Verified**:
- [ ] Collections tab empty on /manage (FIXED)
- [ ] Source tab missing on /collection (FIXED)
- [ ] Source link navigation broken on /collection (FIXED)
- [ ] Synthetic fallback artifacts eliminated (FIXED)

**Acceptance Criteria**:
- [ ] All Phase 1-5 tasks complete
- [ ] All tests passing
- [ ] All bug fixes verified
- [ ] Documentation complete
- [ ] Code review approval
- [ ] Ready for deployment

---

## Phase 4-5 Completion Checklist

### Before Release

- [ ] All Phase 4-5 tasks completed
- [ ] All components accept Artifact type
- [ ] Modal works with unified type from both pages
- [ ] Form CRUD operations work
- [ ] All tests pass (>85% coverage)
- [ ] No visual regressions
- [ ] Migration guide published
- [ ] Architecture docs updated
- [ ] Deprecation notices in place
- [ ] Code review approval from 2+ team members
- [ ] Manual QA verification complete

### Bug Fixes Verified

- [ ] Collections tab populated on /manage page
- [ ] Source tab appears on /collection page
- [ ] Source link navigation functional
- [ ] No synthetic fallback artifacts

### Deprecation Readiness

- [ ] Entity type marked as deprecated
- [ ] JSDoc warnings appear in IDE
- [ ] Removal timeline documented (Q2 2026)
- [ ] Migration guide available
- [ ] Team informed of timeline

---

## Success Criteria Summary

**Project Complete When**:

1. ✅ Single unified `Artifact` type throughout codebase
2. ✅ All components accept `Artifact` type (Entity is alias)
3. ✅ Single `mapApiResponseToArtifact()` mapper function
4. ✅ All 4 old conversion functions removed
5. ✅ Collections tab populated on /manage page (bug fix)
6. ✅ Source tab appears on /collection page (bug fix)
7. ✅ Modal receives complete data from both pages
8. ✅ Navigation handlers consistently provided
9. ✅ TypeScript strict mode passes
10. ✅ All tests pass (>85% coverage)
11. ✅ No visual or behavioral changes
12. ✅ Migration guide published
13. ✅ Deprecation notices in place
14. ✅ Removal timeline documented (Q2 2026)
15. ✅ Code review approval from team

---

## Final Notes

### Timeline Summary

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| 1-2: Types & Registry | 5-7 days | Yes (blocks 3-4) |
| 3: API Mappers | 4-5 days | Yes (blocks 4-5) |
| 4: Components | 5-7 days | Yes (blocks 5) |
| 5: Deprecation | 2-3 days | No |
| **Total** | **16-22 days** | **4-6 weeks with breaks** |

### Effort Estimation

- **Phase 1-2**: 14 points
- **Phase 3**: 12 points
- **Phase 4**: 13 points
- **Phase 5**: 6 points
- **Total**: 45 points
- **Contingency**: +9 points (20%)
- **With contingency**: 54 points

### Quality Gates

All phases must maintain:
- TypeScript strict mode compilation
- Test coverage >85% for new/modified code
- Zero visual or behavioral changes
- Backward compatibility (until Phase 5)
- No performance regression (<2% bundle size change)

---

**Last Updated**: 2026-01-28
**Status**: Ready for Implementation
**Next Step**: Begin Phase 1 implementation
