# Quick Feature: Folder View UI Enhancements (v2)

**Status**: completed
**Created**: 2026-01-30
**Branch**: feat/marketplace-folder-view-v1

## Requirements

1. **Display artifacts as compact cards** - Instead of list rows, show artifacts in a grid of compact cards (like the main grid view) with visual indicators, clickable to open modal

2. **Increase API pagination limit** - Change default from 25 to 100 to reduce network calls

## Changes Made

### 1. Created ArtifactCompactCard component
**File**: `skillmeat/web/app/marketplace/sources/[id]/components/artifact-compact-card.tsx`

New compact card component for folder view grids:
- Type badge with color coding
- Name display (truncated)
- Confidence score badge with breakdown tooltip
- Status badge
- Duplicate/In Collection badges when applicable
- Icon-only action buttons (import/exclude) with tooltips
- Memoized with `React.memo` for performance
- Keyboard accessible (Enter/Space to click)
- ExcludeArtifactDialog integration

### 2. Updated ArtifactTypeSection
**File**: `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`

- Removed the ArtifactRow sub-component
- Added new props: `onArtifactClick`, `sourceId`, `isImporting`
- Changed content from list of rows to responsive grid of ArtifactCompactCards
- Grid: `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3`

### 3. Updated FolderDetailPane
**File**: `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`

- Added new props: `onArtifactClick`, `sourceId`, `isImporting`
- Passes these through to ArtifactTypeSection

### 4. Updated SourceFolderLayout
**File**: `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx`

- Added new props: `onArtifactClick`, `sourceId`, `isImporting`
- Passes these through to FolderDetailPane

### 5. Updated page.tsx
**File**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

- Changed default pagination from 25 to 100 items per page (line 434)
- Also updated fallback value on line 436 from 25 to 100
- Added new props to SourceFolderLayout:
  - `onArtifactClick` - opens the entry modal when clicking a card
  - `sourceId` - passes the source ID for exclude operations
  - `isImporting` - passes the import mutation pending state

## Verification

- [x] Build passes: `pnpm build`
- [x] TypeScript errors are pre-existing (in test files, not related to these changes)

## Result

1. Artifacts in folder view are now displayed as compact cards in a responsive grid (2/3/4 columns)
2. Each card shows type, name, confidence score, and status
3. Cards are clickable to open the artifact detail modal
4. Import/exclude actions are available as icon buttons with tooltips
5. Default pagination increased from 25 to 100, reducing API calls by 75%
