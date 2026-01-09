---
title: Marketplace Catalog Structure & Components (Phase 2)
description: Reference guide for bulk tag application feature - catalog page, data types, API clients, and existing components
references:
  - skillmeat/web/app/marketplace/page.tsx
  - skillmeat/web/types/marketplace.ts
  - skillmeat/web/types/path-tags.ts
  - skillmeat/web/lib/api/catalog.ts
  - skillmeat/web/lib/api/marketplace.ts
  - skillmeat/web/lib/api/tags.ts
  - skillmeat/web/lib/utils.ts
  - skillmeat/web/components/marketplace/path-tag-review.tsx
last_verified: 2026-01-08
---

# Marketplace Catalog Structure for Phase 2

This document provides a complete map of the marketplace catalog structure needed for implementing the **bulk tag application feature (Phase 2)**.

## 1. Catalog Page Location

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/marketplace/page.tsx`

**Description**: The main marketplace catalog page displaying paginated listings with filters.

**Key Elements**:
- Browse marketplace listings (read-only file-based collections)
- Filter by broker, query, tags, license, publisher
- Install bundles with conflict strategy selection
- Paginated results with "Load More" button

**Note**: This page displays **MarketplaceListing** items (published bundles), NOT **CatalogEntry** items (detected artifacts from GitHub sources).

---

## 2. Artifact Data Structures

### CatalogEntry (GitHub Source Detection)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/marketplace.ts` (lines 165-199)

**Usage**: Represents artifacts detected from GitHub sources during catalog scanning.

```typescript
export interface CatalogEntry {
  // Identity
  id: string;                              // Unique entry ID
  source_id: string;                       // GitHub source ID
  artifact_type: ArtifactType;             // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'

  // Naming & Location
  name: string;                            // Detected artifact name
  path: string;                            // Relative path in repository (e.g., 'skills/canvas-design')
  upstream_url: string;                    // GitHub URL to artifact

  // Detection Info
  detected_version?: string;               // Extracted version
  detected_sha?: string;                   // Git blob SHA
  detected_at: string;                     // ISO 8601 timestamp
  confidence_score: number;                // 0-100 detection confidence

  // Status & Tracking
  status: CatalogStatus;                   // 'new' | 'updated' | 'removed' | 'imported' | 'excluded'
  import_date?: string;                    // When imported to collection
  import_id?: string;                      // Reference to imported artifact
  excluded_at?: string | null;             // When excluded
  excluded_reason?: string | null;         // Why excluded

  // Scoring Details (for debugging/display)
  raw_score?: number;
  score_breakdown?: {
    dir_name_score: number;
    manifest_score: number;
    extensions_score: number;
    parent_hint_score: number;
    frontmatter_score: number;
    skill_manifest_bonus: number;
    container_hint_score: number;
    frontmatter_type_score: number;
    depth_penalty: number;
    raw_total: number;
    normalized_score: number;
  };

  // Deduplication (Phase 3)
  is_duplicate?: boolean;
  duplicate_reason?: 'within_source' | 'cross_source';
  duplicate_of?: string;                   // Path of original artifact
}
```

**Key Fields for Phase 2**:
- `id`: Entry ID for targeting bulk operations
- `path`: **Source of path tags** (used for deriving tags from path segments)
- `name`: Artifact name (may be auto-generated from path)
- `status`: Filters available entries
- `confidence_score`: May filter shown entries

**IMPORTANT**: No `full_path` field exists in the type. The `path` field IS the full relative path within the repository (e.g., `skills/canvas-design` or `commands/ai/prompt-generator`).

---

### MarketplaceListing (Published Bundles)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/marketplace.ts` (lines 7-21)

**Usage**: Represents bundles published to marketplace brokers (different from catalog entries).

```typescript
export interface MarketplaceListing {
  listing_id: string;
  name: string;
  publisher: string;
  license: string;
  artifact_count: number;
  tags: string[];                          // Already has tags!
  created_at: string;
  source_url: string;
  description?: string;
  version?: string;
  downloads?: number;
  rating?: number;
  price: number;                           // In cents, 0 for free
}
```

---

### Path Tags (Extracted from path)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/path-tags.ts`

**Usage**: Extracted segments from artifact paths, used to generate tags.

```typescript
export interface ExtractedSegment {
  segment: string;                         // Original segment (e.g., 'ai', 'prompt')
  normalized: string;                      // Normalized for tag use
  status: 'pending' | 'approved' | 'rejected' | 'excluded';
  reason?: string;                         // Why excluded (if status='excluded')
}

export interface PathSegmentsResponse {
  entry_id: string;
  raw_path: string;                        // Original artifact path
  extracted: ExtractedSegment[];           // List of segment statuses
  extracted_at: string;
}
```

---

## 3. Existing Utility Functions

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/utils.ts`

Current utilities available for Phase 2 implementation:

```typescript
// Tailwind CSS utilities
export function cn(...inputs: ClassValue[]): string
// Merges Tailwind classes, handling conflicts

// Date formatting
export function formatDate(value: string | number | Date, options?: Intl.DateTimeFormatOptions): string
export function formatDistanceToNow(value: string | number | Date): string

// Number formatting
export function formatNumber(value: number, decimals = 1): string
// Formats 1000 → '1K', 1000000 → '1M', etc.

export function calculatePercentage(value: number, total: number, decimals = 1): number
// Safe zero handling
```

**For Phase 2 bulk tag operations**, may need to add:
- `slugify()` - Convert names to URL-safe slugs (for tag slugs)
- `batchArray()` - Split arrays into batches for bulk operations
- Path parsing utilities

---

## 4. API Client Functions

### Catalog API

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/catalog.ts`

Functions for fetching file trees and content:

```typescript
// File tree navigation
export async function fetchCatalogFileTree(
  sourceId: string,
  artifactPath: string
): Promise<FileTreeResponse>

// File content retrieval
export async function fetchCatalogFileContent(
  sourceId: string,
  artifactPath: string,
  filePath: string
): Promise<FileContentResponse>
```

**Note**: These are for browsing artifact files, not catalog metadata.

---

### Marketplace API

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/marketplace.ts`

Functions for path tags:

```typescript
// Get extracted path segments for an entry
export async function getPathTags(
  sourceId: string,
  entryId: string
): Promise<PathSegmentsResponse>

// Update status of a segment (approve/reject)
export async function updatePathTagStatus(
  sourceId: string,
  entryId: string,
  segment: string,
  status: 'approved' | 'rejected'
): Promise<PathSegmentsResponse>

// Infer GitHub repo structure
export async function inferUrl(url: string): Promise<InferUrlResponse>
```

---

### Tags API

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/tags.ts`

Current tag operations:

```typescript
// Tag management
export async function fetchTags(limit?: number, after?: string): Promise<TagListResponse>
export async function searchTags(query: string, limit?: number): Promise<Tag[]>
export async function createTag(data: TagCreateRequest): Promise<Tag>
export async function updateTag(id: string, data: TagUpdateRequest): Promise<Tag>
export async function deleteTag(id: string): Promise<void>

// Artifact tag associations (single operations only)
export async function getArtifactTags(artifactId: string): Promise<Tag[]>
export async function addTagToArtifact(artifactId: string, tagId: string): Promise<void>
export async function removeTagFromArtifact(artifactId: string, tagId: string): Promise<void>
```

**Note for Phase 2**: These are single operations. **Bulk operations** will need new endpoints/functions.

---

## 5. Existing Tag-Related Components

### PathTagReview Component

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/path-tag-review.tsx`

**Purpose**: Display and approve/reject extracted path segments for individual entries.

**Key Features**:
- Status-colored badges (pending, approved, rejected, excluded)
- Approve/reject buttons for pending segments
- Loading, error, and empty states
- Summary footer with segment counts
- Dark mode and responsive design

**Props**:
```typescript
interface PathTagReviewProps {
  sourceId: string;              // Marketplace source ID
  entryId: string;               // Catalog entry ID
  className?: string;
}
```

**Related Hook**: `usePathTags()` and `useUpdatePathTagStatus()` (in `hooks/use-path-tags.ts`)

---

### Other Marketplace Components

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/`

Available components for integration:

```
├── MarketplaceListingCard.tsx          # Display single listing
├── MarketplaceListingDetail.tsx        # Detailed listing view
├── MarketplaceFilters.tsx              # Filter UI
├── MarketplaceInstallDialog.tsx        # Install bundle dialog
├── MarketplaceStats.tsx                # Summary statistics
├── MarketplacePublishWizard.tsx        # Publish flow
├── add-source-modal.tsx                # Add GitHub source
├── edit-source-modal.tsx               # Edit GitHub source
├── delete-source-dialog.tsx            # Delete source confirmation
├── exclude-artifact-dialog.tsx         # Exclude entry confirmation
├── DirectoryMapModal.tsx               # Manual path mapping
├── MarketplaceBrokerSelector.tsx       # Select broker
├── source-card.tsx                     # Display GitHub source
└── path-tag-review.tsx                 # Path tag approval UI
```

---

## 6. Integration Points for Phase 2

### Bulk Tag Application Flow

```
1. User selects multiple CatalogEntry items
   ↓
2. Display bulk action panel (new component)
   ↓
3. Show combined path tags from all entries
   ↓
4. User approves/rejects segments collectively
   ↓
5. Apply tags to catalog entries
   ↓
6. Create entries in tag system if needed
   ↓
7. Associate tags with artifacts
```

### Required New Components

- **BulkTagSelector**: Checkbox selection on catalog grid
- **BulkTagPanel**: Summary and bulk approve/reject controls
- **BulkTagStatus**: Progress indicator during bulk operation

### Required New Hooks

- `useBulkSelectCatalog()`: Manage selected entries
- `useBulkPathTags()`: Fetch and combine tags from multiple entries
- `useBulkApplyTags()`: Apply tags to entries (new API endpoint)

### Required New API Endpoints

Backend needs:
- `POST /api/v1/marketplace/sources/{source_id}/catalog/bulk-apply-tags`
- `POST /api/v1/marketplace/sources/{source_id}/catalog/bulk-update-path-tags`

---

## 7. Data Flow Reference

### Single Entry Tag Application

```
CatalogEntry (path = 'skills/ai/prompt-generator')
  ↓
getPathTags(sourceId, entryId)
  ↓
PathSegmentsResponse {
  raw_path: 'skills/ai/prompt-generator'
  extracted: [
    { segment: 'skills', status: 'approved', normalized: 'skills' },
    { segment: 'ai', status: 'pending', normalized: 'ai' },
    { segment: 'prompt-generator', status: 'pending', normalized: 'prompt-generator' }
  ]
}
  ↓
User approves segments
  ↓
Create/fetch Tag entities
  ↓
Associate with artifact (if imported)
```

### Path Field Structure

For artifact at `skills/ai/prompt-generator/`:
- `CatalogEntry.path` = `"skills/ai/prompt-generator"`
- Segments extracted: `["skills", "ai", "prompt-generator"]`
- Tags generated: `skills`, `ai`, `prompt-generator` (after normalization)

---

## 8. Key Implementation Notes

### No `full_path` Field

The `CatalogEntry` type uses `path` (relative path from repo root). There is no separate `full_path` field. This path is the source of truth for tag extraction.

### Tag Lifecycle

1. **Creation**: Segments extracted from `CatalogEntry.path`
2. **Review**: `PathTagReview` component shows status
3. **Approval**: User approves/rejects segments
4. **Generation**: Create `Tag` entities from approved segments
5. **Association**: Link tags to artifacts in collection

### Utilities to Consider Adding

```typescript
// Path parsing
export function extractPathSegments(path: string): string[]
export function normalizePath(path: string): string

// Tag generation
export function generateSlugFromName(name: string): string
export function validateTagName(name: string): boolean

// Batch operations
export function chunkArray<T>(array: T[], size: number): T[][]
```

---

## 9. File Reference Summary

| Component | File | Type | Purpose |
|-----------|------|------|---------|
| Marketplace Catalog Page | `app/marketplace/page.tsx` | Page | Main catalog UI |
| CatalogEntry Type | `types/marketplace.ts` | Type | Artifact detection result |
| PathTagReview | `components/marketplace/path-tag-review.tsx` | Component | Individual tag approval |
| Path Tags API | `lib/api/marketplace.ts` | API Client | Path tag operations |
| Catalog API | `lib/api/catalog.ts` | API Client | File tree/content |
| Tags API | `lib/api/tags.ts` | API Client | Tag CRUD |
| Utils | `lib/utils.ts` | Utilities | Formatting & helpers |
| Path Tags Type | `types/path-tags.ts` | Type | Extracted segments |

---

## Status: Ready for Phase 2

All structural information needed for bulk tag application feature is documented. Backend API contracts should be confirmed with `skillmeat/api/CLAUDE.md` before implementation.

**Next Steps**:
1. Verify backend bulk tag endpoints exist or create them
2. Create new component for bulk selection UI
3. Implement `useBulkSelectCatalog()` hook
4. Implement bulk tag application hook
5. Wire components together in catalog page
