# Root-Level Artifacts Handling Analysis

## Executive Summary

Root-level artifacts (artifacts at the source root with no parent folder, e.g., path is just `"my-skill"` with no slash) are **completely excluded** from the marketplace folder view due to design decisions in both `buildFolderTree` and `getDisplayArtifactsForFolder`.

**Impact**: Any artifact without a parent directory is invisible in folder view.

---

## How Root-Level Artifacts Are Handled

### 1. `buildFolderTree()` - Tree Construction
**File**: `/skillmeat/web/lib/tree-builder.ts` (lines 99-102)

```typescript
// Build path to parent folder (all segments except last)
const folderSegments = isLeaf ? effectiveSegments.slice(0, -1) : effectiveSegments;

// If no folder segments, skip (artifact at root level)
if (folderSegments.length === 0) {
  continue;  // ← ROOT-LEVEL ARTIFACTS ARE SKIPPED HERE
}
```

**Behavior**:
- For an artifact with path `"my-skill"` (no slash):
  - `segments = ["my-skill"]`
  - `folderSegments = []` (all segments except last)
  - The artifact is **skipped** with `continue`
  - **Never added to the folder tree**

- For an artifact with path `"plugins/my-skill"`:
  - `segments = ["plugins", "my-skill"]`
  - `folderSegments = ["plugins"]` (valid)
  - Added to the tree under `plugins` folder

**Test Case** (line 308-315):
```typescript
it('skips root-level artifacts (no folder path)', () => {
  const entries = [
    createEntry('artifact-at-root'),
    createEntry('plugins/linter')
  ];
  const tree = buildFolderTree(entries, 0);

  // Only plugins should be in tree, root-level artifact is skipped
  expect(Object.keys(tree)).toHaveLength(1);
  expect(tree).toHaveProperty('plugins');
});
```

---

### 2. `getDisplayArtifactsForFolder()` - Artifact Retrieval
**File**: `/skillmeat/web/lib/folder-filter-utils.ts` (lines 238-319)

Even if root-level artifacts were in the tree, this function would never return them:

```typescript
// Line 248 - Critical filter
if (lastSlash === -1) return false; // Root-level artifact, no folder
```

**Logic**:
- For `entry.path = "my-skill"` (no slash):
  - `lastSlash = entry.path.lastIndexOf('/') = -1`
  - Function returns `false` immediately
  - **Artifact is filtered out**

- For `entry.path = "plugins/my-skill"`:
  - `lastSlash = 10` (position of `/`)
  - `entryDir = "plugins"`
  - Artifact is included if it matches the folder path

**Test Case** (line 685-690):
```typescript
it('handles root-level artifacts (no folder)', () => {
  const catalog = [
    createEntry({ id: '1', path: 'root-skill' })  // No slash
  ];

  const result = getDisplayArtifactsForFolder(catalog, 'anything');
  expect(result).toEqual([]);  // Always empty, regardless of folder param
});
```

**Programmatic Explanation** (lines 246-254):
```typescript
return catalog.filter((entry) => {
  const lastSlash = entry.path.lastIndexOf('/');
  if (lastSlash === -1) return false;  // ← ROOT-LEVEL BLOCKED

  const entryDir = entry.path.substring(0, lastSlash);

  // Case 1: Direct match
  if (entryDir === folderPath) {
    return true;
  }

  // Cases 2-3: Leaf container handling (only applies to foldered artifacts)
  // ...
});
```

---

### 3. Folder View Page - No Root Display
**File**: `/skillmeat/web/app/marketplace/sources/[id]/page.tsx` (lines 628-632)

```typescript
// Build folder tree (applies semantic filtering)
const folderTree = useMemo(() => {
  if (viewMode !== 'folder') return {};
  const rawTree = buildFolderTree(filteredEntries, 0);  // ← Skips root artifacts
  return filterSemanticTree(rawTree);
});
```

**Result**:
- `filteredEntries` contains all catalog entries (including root-level)
- `buildFolderTree()` strips out root-level artifacts
- Tree only contains foldered artifacts
- Users can only navigate folders that exist

---

### 4. Folder Detail Pane - Can't Show Root Artifacts
**File**: `/skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx` (lines 102-105)

```typescript
const folderArtifacts = useMemo(() => {
  if (!folder) return [];
  return getDisplayArtifactsForFolder(catalog, folder.fullPath);  // ← Double-blocked
}, [catalog, folder]);
```

**Flow**:
1. If folder is null (no selection) → empty state shown
2. If folder exists → calls `getDisplayArtifactsForFolder(catalog, folderPath)`
3. No way to show root-level artifacts because:
   - They're not in the tree (step 1)
   - `getDisplayArtifactsForFolder` filters them out (step 2)

---

## Complete Exclusion Chain

```
Catalog Entries
    ↓
buildFolderTree() → skips root-level artifacts
    ↓
folderTree → only contains foldered artifacts
    ↓
User selects folder → FolderDetailPane receives selectedFolderNode
    ↓
getDisplayArtifactsForFolder() → filters out any remaining root artifacts
    ↓
Result: root-level artifacts are INVISIBLE in folder view
```

---

## Why This Design Decision?

Based on code analysis, the design assumes:

1. **Source Structure Convention**: All artifacts are organized in directories
   - Pattern: `owner/artifacts/my-skill`
   - Pattern: `owner/skills/my-command`
   - Pattern: `owner/agents/my-agent`

2. **Navigation Model**: Folders are first-class concepts
   - Users navigate folders, not artifacts at root
   - Root-level artifacts don't fit the folder hierarchy concept

3. **Leaf Container Handling**: Root folders are always real organization
   - `skills/`, `commands/`, etc. are filtered semantically
   - Root-level artifacts have no container to filter

---

## Test Coverage

Tests explicitly verify root-level artifact exclusion:

| Test File | Test | Purpose |
|-----------|------|---------|
| `tree-builder.test.ts` | "skips root-level artifacts (no folder path)" | Confirms exclusion from tree |
| `folder-filter-utils.test.ts` | "handles root-level artifacts (no folder)" | Confirms filter blocks root |
| `bulk-tag-workflow.test.tsx` | "handles all root-level entries (no directories)" | Documents root-level behavior |
| `directory-utils.test.ts` | Multiple tests | Documents root artifacts are excluded |

---

## Current Behavior Comparison

### For Foldered Artifacts
✓ Shows in tree navigation
✓ Displays in folder detail pane
✓ Filtered by type/confidence/search
✓ Can be imported

### For Root-Level Artifacts
✗ Not in tree navigation
✗ Cannot be selected as a folder
✗ Never reach folder detail pane
✗ Invisible in folder view
✓ **Only visible in grid/list view**

---

## Key Code Locations

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Tree Builder | `lib/tree-builder.ts` | 99-102 | Skips root artifacts during build |
| Filter Function | `lib/folder-filter-utils.ts` | 248 | Excludes root artifacts from display |
| Page Component | `app/marketplace/sources/[id]/page.tsx` | 628-632 | Builds tree (removes root artifacts) |
| Detail Pane | `app/marketplace/sources/[id]/components/folder-detail-pane.tsx` | 102-105 | Retrieves artifacts via filter |

---

## Design Intent vs. Reality

**Design Intent**:
- Folder view is for navigating **organized sources**
- Root-level artifacts don't belong in folder hierarchy
- Grid/list view handles unorganized sources

**Reality**:
- No UI affordance to show this is intentional
- No warning or explanation to users
- Switching to grid/list view is the only way to see root artifacts
- Could cause confusion if a source has both foldered and root artifacts

---

## Summary

Root-level artifacts are deliberately excluded from folder view through two independent blocking points:

1. **`buildFolderTree()`** - Never creates folder nodes for root artifacts (no parent folder)
2. **`getDisplayArtifactsForFolder()`** - Filters out any artifact without a parent folder (path has no `/`)

This is a **design decision**, not a bug, based on the assumption that folder view is only for organized sources with hierarchical structure.
