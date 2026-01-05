---
type: context
prd: "marketplace-source-detection-improvements"
created: 2026-01-05
updated: 2026-01-05
---

# Context: Marketplace Source Detection Improvements

## Overview

Two enhancements to marketplace source artifact detection:

1. **Manual Source Mapping** - UI to map directories to artifact types
   - User can override heuristic detection for specific directories
   - Hierarchical inheritance (parent directory mapping applies to children)
   - Confidence scoring (manual=95, parent_match=90, heuristic=variable)
   - Persisted in MarketplaceSource.manual_map (JSON column)

2. **Auto-detection Deduplication** - SHA256-based duplicate removal
   - Within-source deduplication (keep highest confidence)
   - Cross-source deduplication (mark as excluded)
   - Content hashing with caching and size limits (10MB)
   - Dedup counts returned in scan results

## Key Files

### Backend Core

**Detection & Hashing**:
- `skillmeat/core/marketplace/heuristic_detector.py` - Detection logic (modify for manual mappings)
- `skillmeat/core/marketplace/deduplication_engine.py` - New file for dedup logic
- `skillmeat/core/marketplace/github_scanner.py` - Integration point for scan workflow

**Database Models**:
- `skillmeat/cache/models.py:1173` - `MarketplaceSource` model (has manual_map column)
- `skillmeat/cache/models.py:1368` - `MarketplaceCatalogEntry` model (has metadata_json column)

### API Layer

**Routers & Schemas**:
- `skillmeat/api/routers/marketplace_sources.py` - PATCH, GET, rescan endpoints
- `skillmeat/api/schemas/marketplace.py` - Request/response schemas for manual_map

### Frontend

**Components**:
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Source detail page
- `skillmeat/web/components/marketplace/source-toolbar.tsx` - Toolbar with Map Directories button
- `skillmeat/web/components/marketplace/DirectoryMapModal.tsx` - New component (to be created)

**Types & API**:
- `skillmeat/web/types/marketplace.ts` - TypeScript types for manual_map and dedup fields
- `skillmeat/web/lib/api/marketplace.ts` - API client functions for PATCH/rescan

## Architecture Notes

### Data Model

**MarketplaceSource.manual_map** (JSON):
```json
{
  "path/to/directory": "skill",
  "another/path": "command"
}
```

**MarketplaceCatalogEntry.metadata_json** (JSON):
```json
{
  "content_hash": "sha256:abc123...",
  "file_size": 12345,
  "other_metadata": "..."
}
```

### Workflow

1. **User sets manual mappings** → PATCH /marketplace-sources/{id} with manual_map
2. **User triggers rescan** → POST /marketplace-sources/{id}/rescan
3. **Backend scans source**:
   - Fetch GitHub tree
   - Apply manual mappings (confidence 95 for exact, 90 for parent match)
   - Run heuristic detection for unmapped directories
   - Hash all detected artifacts
   - Run deduplication (within-source, then cross-source)
   - Return dedup counts in response
4. **Frontend displays results**:
   - Show dedup counts in toast notification
   - Display duplicate badges on excluded entries
   - Allow filtering for duplicates in excluded list

### Confidence Scoring

| Source | Confidence |
|--------|-----------|
| Manual exact match | 95 |
| Manual parent match | 90 |
| Heuristic (varies) | 50-85 |

On hash collision, keep highest confidence artifact.

### Deduplication Logic

**Within-source**:
- Group artifacts by content_hash
- For each group, keep highest confidence
- Mark others as excluded

**Cross-source**:
- Query existing artifacts in other sources by content_hash
- If found, mark new artifact as excluded
- Log cross-source duplicates

## Decisions Made

### Database Schema
- **No migrations needed** - reuse existing columns (manual_map, metadata_json)
- manual_map stored as Text column (JSON serialized)
- content_hash stored in metadata_json (already flexible JSON column)

### Deduplication Strategy
- **SHA256 hashing** - industry standard, collision probability ~0
- **Keep highest confidence** - tie-break by path order (alphabetical)
- **Mark as excluded** - don't delete duplicates (reversible)
- **Cross-source dedup** - check all sources, not just current

### Performance
- **Lazy hashing** - hash files only when needed (on scan)
- **Hash caching** - cache hashes in metadata_json to avoid recomputation
- **File size limit** - 10MB max to prevent timeout on large files
- **Target performance** - <120s for 1000 artifacts

### UI/UX
- **Tree rendering** - use source.tree_data from GitHub API
- **Hierarchical selection** - selecting parent auto-selects children
- **Rescan integration** - rescan button in modal triggers immediate scan
- **Duplicate visibility** - badge + filter for excluded duplicates

## Open Questions

None at this time.

## Session Notes

### 2026-01-05: Initial Setup
- Created progress tracking file with 58 tasks across 5 phases
- Created context file with key files and architecture notes
- Parallelization strategy defined for efficient execution
- Quality gates defined for each phase
