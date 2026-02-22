---
type: quick-feature
status: completed
created: 2026-02-21
feature: Marketplace modal live update + collection card dual buttons
files_affected:
  - skillmeat/web/app/marketplace/sources/[id]/page.tsx
  - skillmeat/web/components/collection/artifact-browse-card.tsx
  - skillmeat/web/components/collection/artifact-grid.tsx
  - skillmeat/web/app/collection/page.tsx
---

# Quick Feature: Marketplace Modal Live Update + Collection Card Dual Buttons

## Task 1: Sync selectedEntry with catalog data after import

**File**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

**Problem**: After importing from CatalogEntryModal, `selectedEntry` state holds stale data (status='new'). The Collections/Deployments tabs in the modal are gated by `entry.status === 'imported'` (CatalogEntryModal.tsx:827), so they don't appear until the modal is closed and reopened.

**Fix**: Add an effect that syncs `selectedEntry` with the latest matching entry from `allEntries` when catalog data refreshes:

```tsx
// After line ~624 (existing effects), add:
useEffect(() => {
  if (selectedEntry && allEntries.length > 0) {
    const updated = allEntries.find(e => e.id === selectedEntry.id);
    if (updated && updated.status !== selectedEntry.status) {
      setSelectedEntry(updated);
    }
  }
}, [allEntries, selectedEntry]);
```

## Task 2: Add dual action buttons to collection card

**File**: `skillmeat/web/components/collection/artifact-browse-card.tsx`

**Problem**: Collection card only has a single click handler. User wants 2 explicit buttons: "Collection" (open details modal on collection page) and "Manage" (navigate to /manage page).

**Fix**:
1. Add `onManage?: (artifact: Artifact) => void` prop to `ArtifactBrowseCardProps`
2. Add two small action buttons in the card footer area (before or instead of the deploy button)
3. Wire up the "Manage" button in parent components (artifact-grid.tsx, collection page)

The Manage button should navigate to `/manage?artifact={artifact.id}`.
