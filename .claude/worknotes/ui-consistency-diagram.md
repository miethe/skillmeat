# UI Consistency Data Flow Diagram

## Overview: Two Paths to Same Component

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Collection Page (/collection)                          │
│                     selectedCollectionId state                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
            ┌────────▼─────────┐        ┌─────────▼────────────┐
            │ selectedCollectionId   │  │  selectedCollectionId │
            │ is 'all' or empty      │  │  is set (specific ID) │
            └────────┬─────────┘        └─────────┬────────────┘
                     │                             │
                     │                             │
        ┌────────────▼──────────────┐  ┌──────────▼────────────────┐
        │  useArtifacts()            │  │  useCollectionArtifacts() │
        │  (all artifacts)           │  │  (collection artifacts)   │
        └────────────┬──────────────┘  └──────────┬────────────────┘
                     │                             │
        ┌────────────▼──────────────┐              │
        │  GET /api/v1/artifacts    │              │
        │  limit=100                 │              │
        │  [type filter]             │              │
        │                            │              │
        │  Returns:                  │              │
        │  {                         │              │
        │    items: ApiArtifact[]    │              │
        │    page_info: {...}        │              │
        │  }                         │              │
        └────────────┬──────────────┘              │
                     │                             │
        ┌────────────▼──────────────────────┐      │
        │  mapApiArtifact()                 │      │
        │  - metadata                       │      │
        │  - upstream status                │      │
        │  - usage stats                    │      │
        │  - all 16+ fields                 │      │
        └────────────┬──────────────────────┘      │
                     │                             │
        ┌────────────▼──────────────────────┐      │
        │  data: ArtifactsResponse          │      │
        │  {                                │      │
        │    artifacts: Artifact[]  ✅      │      │
        │    total: number                  │      │
        │    page: number                   │      │
        │    pageSize: number               │      │
        │  }                                │      │
        └────────────┬──────────────────────┘      │
                     │                             │
                     │         ┌───────────────────┘
                     │         │
        ┌────────────▼─────────▼──────┐
        │  ArtifactGrid / ArtifactList  │
        │  (Same component for both)    │
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │  artifacts.map(artifact =>    │
        │    <UnifiedCard item={...} />)│
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────────────────────────┐
        │                    UnifiedCard                     │
        │  (Type-agnostic component)                        │
        │  - Type guard: isArtifact()                       │
        │  - Normalize to NormalizedCardData                │
        │  - Access: metadata.title, tags, etc.            │
        └────────────┬──────────────────────────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │  FULL CARD RENDERING ✅       │
        │  - Title + Name               │
        │  - Description                │
        │  - Version + Updated + Usage  │
        │  - Tags (3 + overflow)        │
        │  - Outdated warning           │
        └───────────────────────────────┘




                         SPECIFIC COLLECTION PATH
                               │
        ┌──────────────────────▼────────────────────────┐
        │  GET /api/v1/user-collections/{id}/artifacts  │
        │  limit=20 (optional)                          │
        │  after=cursor (optional)                      │
        │                                               │
        │  Returns:                                     │
        │  {                                            │
        │    items: Array<{                            │
        │      name: string                            │
        │      type: string                            │
        │      version?: string    ⚠️  MINIMAL!        │
        │      source: string                          │
        │    }>                                        │
        │    page_info: {...}                          │
        │  }                                            │
        └──────────────────────┬────────────────────────┘
                               │
        ┌──────────────────────▼────────────────────────┐
        │  NO MAPPING                                   │
        │  - Direct pass-through                        │
        │  - No metadata enrichment                     │
        │  - No upstream status                        │
        │  - No usage stats                            │
        └──────────────────────┬────────────────────────┘
                               │
        ┌──────────────────────▼────────────────────────┐
        │  data: CollectionArtifactsResponse            │
        │  {                                            │
        │    items: ArtifactSummary[]  ⚠️               │
        │    total: number                             │
        │    page: number                              │
        │    page_size: number                         │
        │  }                                            │
        └──────────────────────┬────────────────────────┘
                               │
        ┌──────────────────────▼────────────────────────┐
        │  ArtifactGrid / ArtifactList                  │
        │  (Same component receives DIFFERENT data)    │
        └──────────────────────┬────────────────────────┘
                               │
        ┌──────────────────────▼────────────────────────┐
        │  artifacts.map(summary =>                     │
        │    <UnifiedCard item={...} />)                │
        └──────────────────────┬────────────────────────┘
                               │
        ┌──────────────────────▼────────────────────────┐
        │                  UnifiedCard                   │
        │  - Type guard: isArtifact() → FALSE           │
        │  - Can't normalize missing fields             │
        │  - Access: metadata?.title → undefined        │
        │  - Access: tags → undefined                   │
        │  - Access: usageStats → undefined             │
        └──────────────────────┬────────────────────────┘
                               │
        ┌──────────────────────▼────────────────────────┐
        │  SPARSE CARD RENDERING ❌                     │
        │  - Name only                                  │
        │  - Type icon                                  │
        │  - Version (sometimes)                        │
        │  - NO description                             │
        │  - NO metadata row                            │
        │  - NO tags                                    │
        │  - NO warnings                                │
        └───────────────────────────────────────────────┘
```

---

## Component Type Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Input to UnifiedCard                              │
└─────────────────────────────────────────────────────────────────────────────┘

All Collections Path:
  artifact: Artifact = {
    id: string
    name: string
    type: ArtifactType
    scope: ArtifactScope
    status: ArtifactStatus                           ← Can render status badge
    version?: string
    source?: string
    metadata: {                                       ← Can access nested properties
      title?: string       ← Used for card title
      description?: string ← Shows in card body
      tags?: string[]      ← Shows as badges
    }
    upstreamStatus: {
      isOutdated: boolean  ← Shows warning
    }
    usageStats: {
      usageCount: number   ← Shows in metadata row
    }
    createdAt: string
    updatedAt: string
    collection?: { ... }
  }
  ✅ UnifiedCard.normalizeCardData() extracts all properties


Specific Collection Path:
  summary: ArtifactSummary = {
    name: string         ← ONLY this is used
    type: string         ← And this
    version?: string     ← And this
    source: string       ← And this
  }
  ❌ UnifiedCard.normalizeCardData() gets undefined for:
     - metadata (missing)
     - upstreamStatus (missing)
     - usageStats (missing)
     - status (missing)
     - collection (missing)

Rendering Logic (lines 378-429):
  if (truncatedDescription) render description  ← undefined for summary
  if (version) render version                  ← works for both
  if (updatedAt) render date                    ← undefined for summary
  if (usageCount) render usage                  ← undefined for summary
  if (tags.length > 0) render tags              ← undefined for summary
  if (isOutdated) render warning                ← undefined for summary
```

---

## List View Problem

```
ArtifactList Component (artifact-list.tsx)

For Full Artifact (All Collections):
  Line 307: artifact.metadata.title || artifact.name
           → ✅ "Canvas Design"

  Line 316: artifact.metadata.description
           → ✅ "Create visual designs..."

  Line 308: artifact.upstreamStatus.isOutdated
           → ✅ Shows outdated indicator

  Line 367: artifact.usageStats.totalDeployments
           → ✅ Shows deployment count


For ArtifactSummary (Specific Collection):
  Line 307: artifact.metadata.title || artifact.name
           → ❌ TypeError: Cannot read property 'title' of undefined
             Falls back to artifact.name

  Line 316: artifact.metadata.description
           → ❌ Undefined, no fallback, renders empty

  Line 308: artifact.upstreamStatus.isOutdated
           → ❌ TypeError: Cannot read property 'isOutdated' of undefined
             Condition fails, indicator missing

  Line 367: artifact.usageStats.totalDeployments
           → ❌ TypeError: Cannot read property 'totalDeployments' of undefined
             Column empty or error
```

---

## Visual Difference

```
GRID VIEW COMPARISON

All Collections (Full Artifact):
┌────────────────────────────┐
│ 📦 Canvas Design    [Active]│  ← Icon, title, status
│ canvas-design              │  ← Separate name (when different)
├────────────────────────────┤
│ Create and edit visual     │  ← Description (line-clamped)
│ designs with canvas        │
│ v2.1.0  2d ago  42 uses    │  ← Rich metadata row
│ design visual canvas +1    │  ← Tags with overflow
│ ⚠ Update available         │  ← Outdated warning
└────────────────────────────┘


Specific Collection (ArtifactSummary):
┌────────────────────────────┐
│ 📦 canvas-design           │  ← Name only
│                            │  ← No title (missing)
├────────────────────────────┤
│                            │  ← No description (missing)
│ v2.1.0                     │  ← Version only (sparse metadata)
│                            │  ← No tags (missing)
│                            │  ← No warning (missing status)
└────────────────────────────┘
```

---

## Why This Happened

### Intentional Design Choice
- **Goal**: Reduce API response size for collection browsing
- **Solution**: Return minimal `ArtifactSummary` from collection endpoint
- **Result**: Lightweight payload (4 fields vs 16+ fields)

### Unintended Consequence
- **Assumption**: Components can handle sparse data gracefully
- **Reality**: Components assume full `Artifact` structure
- **Impact**: Visual inconsistency and potential runtime errors

### Code Comment Trail
- **page.tsx line 240**: `// NOTE: Type assertion needed temporarily - TASK-2.1 will properly handle ArtifactSummary conversion`
- **page.tsx lines 209-229**: Defensive filtering for both data types (metadata check)
- **unified-card.tsx lines 1-13**: Design notes about type detection and normalization

---

## Property Access Comparison

```
┌──────────────────────┬────────────────────┬──────────────────┐
│ Property             │ Artifact           │ ArtifactSummary  │
├──────────────────────┼────────────────────┼──────────────────┤
│ id                   │ ✅ string          │ ❌ missing       │
│ name                 │ ✅ string          │ ✅ string        │
│ type                 │ ✅ ArtifactType    │ ✅ string        │
│ scope                │ ✅ ArtifactScope   │ ❌ missing       │
│ status               │ ✅ ArtifactStatus  │ ❌ missing       │
│ version              │ ✅ string | undef  │ ✅ string | undef│
│ source               │ ✅ string          │ ✅ string        │
│ metadata             │ ✅ object          │ ❌ missing       │
│ metadata.title       │ ✅ string          │ ❌ N/A           │
│ metadata.description │ ✅ string          │ ❌ N/A           │
│ metadata.tags        │ ✅ string[]        │ ❌ N/A           │
│ upstreamStatus       │ ✅ object          │ ❌ missing       │
│ usageStats           │ ✅ object          │ ❌ missing       │
│ createdAt            │ ✅ string          │ ❌ missing       │
│ updatedAt            │ ✅ string          │ ❌ missing       │
│ aliases              │ ✅ string[]        │ ❌ missing       │
│ collection           │ ✅ object | undef  │ ❌ missing       │
└──────────────────────┴────────────────────┴──────────────────┘

Legend:
✅ = Field exists and can be safely accessed
❌ = Field missing, will return undefined or throw error
```

---

## Conclusion

The UI inconsistency is a **direct result of data structure mismatch**:

1. **Same component** (`UnifiedCard`) receives different data
2. **Different data shapes** cause incomplete rendering
3. **No adaptation logic** in components to handle sparse data

**Fix Options**:
- Enrich `ArtifactSummary` in API hook → Full card rendering everywhere
- Add fallback logic in `UnifiedCard` → Graceful sparse rendering
- Type-specific rendering in `ArtifactList` → View-specific handling

All three approaches restore visual consistency by handling both data types properly.
