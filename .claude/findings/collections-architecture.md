# Collections Architecture - Visual Guide

## 1. Collection Filtering Architecture

### Current (Broken)

```
┌─────────────────────────────────────────────────────────┐
│                  Collection Page                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  CollectionSwitcher ──────────┐                         │
│  (dropdown with list)         │                         │
│                               ▼                         │
│                    CollectionContext                    │
│                   ┌──────────────────┐                  │
│                   │ selectedCollection│                 │
│                   │        Id         │                 │
│                   │  = "design-tools" │                 │
│                   └────────┬──────────┘                  │
│                            │                            │
│          ┌─────────────────┼─────────────────┐          │
│          ▼                                   ▼          │
│   useCollections()                    useArtifacts()   │
│   (works)                             (IGNORES          │
│   GET /user-collections              selectedCollection)
│   ✅                                  ❌                │
│                                   GET /artifacts       │
│                                   ?limit=100            │
│                                                         │
│   collections:                  artifacts:            │
│   - Design Tools                - All 100 artifacts    │
│   - Developer Tools             - No filtering by ID   │
│                                                         │
│          ┌────────────────────────────────────┐        │
│          │      Render ArtifactGrid           │        │
│          │   (shows ALL artifacts regardless) │        │
│          │      ❌ WRONG ARTIFACTS            │        │
│          └────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Fixed (Correct)

```
┌─────────────────────────────────────────────────────────┐
│                  Collection Page                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  CollectionSwitcher ──────────┐                         │
│  (dropdown with list)         │                         │
│                               ▼                         │
│                    CollectionContext                    │
│                   ┌──────────────────┐                  │
│                   │ selectedCollection│                 │
│                   │        Id         │                 │
│                   │  = "design-tools" │                 │
│                   └────────┬──────────┘                  │
│                            │                            │
│   ┌────────────────────────┼────────────────────────┐  │
│   ▼                        ▼                         ▼  │
│ Is selected?         useCollections()     useCollectionArtifacts()
│ NO ✅                (works)               (NOW USED) ✅
│ │                    GET /user-collections
│ │                    ✅                 GET /user-collections/{id}/artifacts
│ │                                        ?limit=100
│ │   collections:
│ │   - Design Tools                   artifacts:
│ │   - Developer Tools                - Only Design Tools
│ │                                    - 23 artifacts
│ │
│ │                    ┌──────────────────────────┐
│ │                    │ Render ArtifactGrid      │
│ │                    │ (shows correct artifacts)│
│ │                    │ ✅ CORRECT               │
│ │                    └──────────────────────────┘
│ │
│ └──── YES
│      └──► collections filtered to ["Design Tools"]
│          artifacts: All 100
│          (same as "All Collections")
│
│          ┌──────────────────────────────────┐
│          │ Render ArtifactGrid              │
│          │ (shows all artifacts)            │
│          │ ✅ CORRECT                       │
│          └──────────────────────────────────┘
└─────────────────────────────────────────────────────────┘
```

---

## 2. Artifact Modal Collections Tab Architecture

### Current (Broken)

```
┌──────────────────────────────────────────────┐
│        UnifiedEntityModal                     │
│        (shows artifact details)               │
├──────────────────────────────────────────────┤
│                                              │
│  ArtifactGrid item clicked                  │
│  Artifact: {                                 │
│    id: "canvas-design"                      │
│    name: "Canvas Design"                    │
│    collection: { id: "design-tools", ... }  │
│  }                                           │
│       ▼                                      │
│  artifactToEntity() {                       │
│    return {                                  │
│      id: "canvas-design"                    │
│      name: "Canvas Design"                  │
│      collection: 'default'  ❌ HARDCODED!   │
│                                              │
│      (original collection data LOST)        │
│    }                                         │
│  }                                           │
│       ▼                                      │
│  ModalCollectionsTab {                      │
│    collections = [                          │
│      {id: "design-tools", name: "..."},    │
│      {id: "developer-tools", name: "..."}   │
│    ]                                         │
│    entity.collection = "default"            │
│                                              │
│    artifactCollections = collections.filter(│
│      (c) => c.id === "default" ||           │
│             c.name === "default"            │
│    )                                         │
│    Result: [] ❌ EMPTY!                     │
│  }                                           │
│       ▼                                      │
│  Display: "This artifact is not in any      │
│  collection."  ❌ WRONG!                    │
│                                              │
│  Add/Remove buttons available but no        │
│  collections shown                          │
└──────────────────────────────────────────────┘
```

### Fixed (Correct)

```
┌──────────────────────────────────────────────┐
│        UnifiedEntityModal                     │
│        (shows artifact details)               │
├──────────────────────────────────────────────┤
│                                              │
│  ArtifactGrid item clicked                  │
│  Artifact: {                                 │
│    id: "canvas-design"                      │
│    name: "Canvas Design"                    │
│    collection: { id: "design-tools", ... }  │
│  }                                           │
│       ▼                                      │
│  artifactToEntity() {                       │
│    return {                                  │
│      id: "canvas-design"                    │
│      name: "Canvas Design"                  │
│      collection: "design-tools" ✅          │
│      collections: [                         │
│        {id: "design-tools", name: "..."}    │
│      ] ✅ PRESERVE COLLECTION DATA          │
│    }                                         │
│  }                                           │
│       ▼                                      │
│  ModalCollectionsTab {                      │
│    collections = [                          │
│      {id: "design-tools", name: "..."},    │
│      {id: "developer-tools", name: "..."}   │
│    ]                                         │
│    entity.collections = [                   │
│      {id: "design-tools", name: "..."}      │
│    ]                                         │
│                                              │
│    artifactCollections = entity.collections │
│    Result: [                                 │
│      {id: "design-tools", name: "..."}      │
│    ] ✅ CORRECT!                            │
│  }                                           │
│       ▼                                      │
│  Display:                                    │
│  - Design Tools                 [23 items]  │
│    [Remove button]              [... menu]  │
│                                              │
│  Plus "Add to Collection" button ✅         │
└──────────────────────────────────────────────┘
```

---

## 3. Type System Impact

### Current Entity Type (Incomplete)

```typescript
interface Entity {
  id: string;
  name: string;
  type: 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
  collection: string;              // ❌ Single string
  status: EntityStatus;
  tags?: string[];
  description?: string;
  version?: string;
  source: string;
  deployedAt?: string;
  modifiedAt?: string;
  aliases?: string[];
  // Missing: relationship to multiple collections
}
```

### Updated Entity Type (Complete)

```typescript
interface Entity {
  id: string;
  name: string;
  type: 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
  collection?: string;             // ✅ Keep for backward compat
  collections?: Array<{            // ✅ ADD: array of full collection objects
    id: string;
    name: string;
  }>;
  status: EntityStatus;
  tags?: string[];
  description?: string;
  version?: string;
  source: string;
  deployedAt?: string;
  modifiedAt?: string;
  aliases?: string[];
  // Now supports multiple collections!
}
```

### Artifact Type (Already Has)

```typescript
interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  scope: ArtifactScope;
  status: ArtifactStatus;
  version?: string;
  source: string;
  metadata?: ArtifactMetadata;
  upstreamStatus?: ArtifactUpstreamStatus;
  usageStats?: ArtifactUsageStats;
  createdAt: string;
  updatedAt: string;
  aliases?: string[];
  collection?: {                   // ✅ Already has collection
    id: string;
    name: string;
  };
}
```

---

## 4. Data Flow Comparison

### Problem 1: Collection Filtering

```
USER ACTION                    CURRENT STATE                   CORRECT STATE
─────────────────────────────────────────────────────────────────────────────

User clicks                    selectedCollectionId = null     selectedCollectionId = null
"All Collections"              │                               │
                               ├─> useArtifacts()              ├─> useArtifacts()
                               │   /artifacts                   │   /artifacts
                               │   = ALL artifacts ✅           │   = ALL artifacts ✅
                               │                               │
                               └─> ArtifactGrid shows all      └─> ArtifactGrid shows all ✅


User clicks                    selectedCollectionId =          selectedCollectionId =
"Design Tools"                 "design-tools"                  "design-tools"
                               │                               │
                               ├─> useArtifacts()              ├─> useCollectionArtifacts()
                               │   /artifacts                   │   /user-collections/design-tools
                               │   (still = ALL) ❌             │   /artifacts
                               │                               │   = only Design Tools ✅
                               │                               │
                               └─> ArtifactGrid shows all ❌   └─> ArtifactGrid shows Design
                                   (wrong!)                        Tools only ✅
```

### Problem 2: Modal Collections Tab

```
USER ACTION                    CURRENT STATE                   CORRECT STATE
─────────────────────────────────────────────────────────────────────────────

User clicks artifact           Artifact extracted              Artifact extracted
in grid                        │                               │
                               ├─> artifactToEntity()          ├─> artifactToEntity()
                               │   collection = 'default' ❌   │   collections = [{
                               │   (hardcoded)                  │     id: "design-tools",
                               │                               │     name: "Design Tools"
                               │                               │   }] ✅
                               │                               │
                               ├─> ModalCollectionsTab         ├─> ModalCollectionsTab
                               │   filter where id === null     │   use entity.collections
                               │   Result: [] ❌                │   Result: [Design Tools] ✅
                               │                               │
                               └─> Empty state message ❌      └─> Show collections list ✅


User clicks                    Try to remove from              Remove from collection
"Remove from                   "default" collection            "Design Tools" ✅
Collection"                    (which doesn't exist) ❌


User clicks                    Can add but no context          Can add and know current
"Add to Collection"            about current collections ⚠️    memberships ✅
```

---

## 5. Hook Dependency Graph

### Current (Incomplete)

```
CollectionPageContent
│
├─ CollectionContext
│  ├─ useCollections()         ✅ Gets all collections
│  │  └─ GET /user-collections
│  │
│  └─ useCollection(id?)       ✅ Gets selected collection details
│     └─ GET /user-collections/{id}
│
├─ useArtifacts()              ❌ Gets ALL artifacts
│  └─ GET /artifacts
│
└─ (missing) useCollectionArtifacts()  ⚠️ Exists but not used
   └─ GET /user-collections/{id}/artifacts
```

### Fixed (Complete)

```
CollectionPageContent
│
├─ CollectionContext
│  ├─ useCollections()         ✅ Gets all collections
│  │  └─ GET /user-collections
│  │
│  └─ useCollection(id?)       ✅ Gets selected collection details
│     └─ GET /user-collections/{id}
│
├─ useArtifacts()              ✅ Gets all artifacts (when no collection selected)
│  └─ GET /artifacts
│
├─ useCollectionArtifacts(id?) ✅ Gets collection-specific artifacts
│  └─ GET /user-collections/{id}/artifacts
│
├─ Decision Logic (NEW):
│  │ if (selectedCollectionId)
│  │   use useCollectionArtifacts()
│  │ else
│  │   use useArtifacts()
│  │
│
└─ ModalCollectionsTab (for modal)
   ├─ entity.collections        ✅ From converted Artifact
   ├─ useCollections()          ✅ For "Add to Collection"
   └─ useRemoveArtifactFromCollection()  ✅ For removing
      └─ DELETE /user-collections/{id}/artifacts/{artifact_id}
```

---

## 6. Implementation Checklist

### Collection Filtering

- [ ] Import `useCollectionArtifacts` in `app/collection/page.tsx`
- [ ] Add conditional logic based on `selectedCollectionId`
- [ ] Replace artifact data source (use correct hook)
- [ ] Test: Select collection → artifacts update
- [ ] Test: Select "All Collections" → artifacts update back
- [ ] Test: Artifact counts match `collection.artifact_count`

### Modal Collections Tab

- [ ] Update `Entity` type to include `collections?: Collection[]`
- [ ] Update `artifactToEntity()` to preserve collection data
- [ ] Update `ModalCollectionsTab` to use `entity.collections`
- [ ] Test: Open modal → Collections tab shows collections
- [ ] Test: Add artifact to collection → Tab updates
- [ ] Test: Remove artifact from collection → Tab updates
- [ ] Test: Artifact with no collections → Empty state

---

## 7. Key Insights

| Problem | Root Cause | Impact | Fix Complexity |
|---------|-----------|--------|-----------------|
| Collection filtering | `useArtifacts()` ignores `selectedCollectionId` | Core UX broken | Low - switch hooks |
| Modal tab empty | `entity.collection` hardcoded to `'default'` | Core UX broken | Medium - type changes |
| Missing relationship | No API fetch for artifact-collection memberships | Can't determine artifact locations | Medium - add API call |
| Data loss in conversion | `artifactToEntity()` throws away collection data | Tab can't display it | Low - preserve data |

---

## 8. API Endpoints Ready to Use

| Endpoint | Status | Used By | Location |
|----------|--------|---------|----------|
| `GET /user-collections` | ✅ Ready | `useCollections()` | hooks/use-collections.ts:96 |
| `GET /user-collections/{id}` | ✅ Ready | `useCollection(id)` | hooks/use-collections.ts:151 |
| `GET /user-collections/{id}/artifacts` | ✅ Ready (not used) | `useCollectionArtifacts(id)` | hooks/use-collections.ts:178 |
| `POST /user-collections/{id}/artifacts` | ✅ Ready | `useAddArtifactToCollection()` | hooks/use-collections.ts:316 |
| `DELETE /user-collections/{id}/artifacts/{artifact_id}` | ✅ Ready | `useRemoveArtifactFromCollection()` | hooks/use-collections.ts:348 |

**Summary:** All backend endpoints already exist. This is purely a frontend wiring problem.
