# Quick Feature: Source Card Badges Update

**Status**: completed
**Created**: 2026-01-25
**Branch**: feat/cross-source-artifact-search

## Request

Update the cards for sources on the /marketplace/sources page:
1. Remove text labels from badges (trust level, sync status), keep only icons + colored boxes
2. Add new search indexing badge with different states
3. All badges should have hover tooltips showing:
   - Badge name and current status
   - For sync status: last sync timestamp
   - For search indexing: last indexed timestamp (when available)

## Analysis

### Current Implementation
- **File**: `skillmeat/web/components/marketplace/source-card.tsx`
- Two existing badge components: `TrustBadge` and `StatusBadge`
- Both currently show: Icon + Text label
- Already have tooltip infrastructure using `@/components/ui/tooltip`

### Data Available (GitHubSource type)
- `trust_level`: 'untrusted' | 'basic' | 'verified' | 'official'
- `scan_status`: 'pending' | 'scanning' | 'success' | 'error'
- `last_sync_at`: timestamp (for sync status tooltip)
- `indexing_enabled`: boolean | null (whether search indexing enabled)
- `last_indexed_tree_sha`: string | null (non-null = indexed)
- Need: `last_indexed_at` timestamp (may need to add to API/types)

### Required Changes

1. **Update TypeScript types** (`skillmeat/web/types/marketplace.ts`)
   - Add `last_indexed_at?: string` to GitHubSource interface (if API provides it)

2. **Update badge components** (`skillmeat/web/components/marketplace/source-card.tsx`)
   - `TrustBadge`: Remove text label, keep icon + colored background
   - `StatusBadge`: Remove text label, keep icon + colored background
   - Create new `IndexingBadge` component for search indexing status
   - Update tooltips to show metadata (timestamps)

### Badge Design Spec

| Badge | States | Icon | Tooltip Content |
|-------|--------|------|-----------------|
| Trust | untrusted, basic, verified, official | Shield, ShieldCheck, Star | "Trust: {level}" + description |
| Sync | pending, scanning, success, error | Clock, Loader2, CheckCircle2, AlertTriangle | "Sync: {status}" + "Last synced: {timestamp}" |
| Indexing | disabled, enabled-pending, indexed, error | SearchSlash, Search, SearchCheck, SearchX | "Search Index: {status}" + "Last indexed: {timestamp}" |

### Icon Selection for Indexing Badge
- `SearchSlash` (Lucide) - disabled/not indexed
- `Search` (Lucide) - enabled but not yet indexed
- `SearchCheck` (Lucide) - successfully indexed
- `SearchX` (Lucide) - indexing error

## Tasks

- [x] Read current badge implementation
- [x] Update TrustBadge - icon only with tooltip
- [x] Update StatusBadge - icon only with tooltip, add timestamp
- [x] Create IndexingBadge component
- [x] Update GitHubSource type
- [x] Test hover tooltips
- [x] Run type check and lint
- [x] Fix bug: clone_target not persisted (IndexingBadge stuck on Pending)
- [x] Add `last_indexed_at` to API response schema
- [x] Update user documentation

## Files Modified

1. `skillmeat/web/components/marketplace/source-card.tsx` - Badge components updated
2. `skillmeat/web/types/marketplace.ts` - Added `last_indexed_at`, `last_indexed_tree_sha` fields
3. `skillmeat/api/routers/marketplace_sources.py` - Fixed clone_target persistence bug
4. `skillmeat/api/schemas/marketplace.py` - Added `last_indexed_at` to SourceResponse
5. `docs/user/guides/marketplace-github-sources.md` - Documented new Source Card Badges section
