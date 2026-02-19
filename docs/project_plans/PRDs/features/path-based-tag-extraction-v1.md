---
title: 'PRD: Path-Based Tag Extraction'
description: Extract organizational metadata from artifact source paths during marketplace
  scanning with user review and approval workflow
audience:
- ai-agents
- developers
tags:
- prd
- planning
- feature
- marketplace
- tagging
- metadata
created: 2025-01-04
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md
- /docs/project_plans/PRDs/enhancements/marketplace-source-enhancements-v1.md
schema_version: 2
doc_type: prd
feature_slug: path-based-tag-extraction
---

# PRD: Path-Based Tag Extraction

**Feature Name:** Path-Based Tag Extraction

**Filepath Name:** `path-based-tag-extraction-v1`

**Date:** 2025-01-04

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Builds On:**
- Marketplace GitHub Ingestion PRD
- Marketplace Source Enhancements PRD

---

## 1. Executive Summary

Path-Based Tag Extraction automatically extracts organizational metadata from artifact source paths during marketplace scanning (e.g., `categories/05-data-ai/ai-engineer.md` → tag suggestion: `data-ai`), enabling users to review and approve path segments before they become artifact tags during import. This feature surfaces latent organizational structure in marketplace repositories, reducing manual tagging effort and improving artifact discoverability.

**Priority:** MEDIUM

**Key Outcomes:**
- Marketplace scans automatically extract path segments from artifact locations
- Users review and approve/reject suggested tags per catalog entry
- Approved path tags are applied as artifact tags during import (opt-in)
- Backward compatible with existing catalogs (new scans only)
- Minimal backend configuration (sensible defaults)

---

## 2. Context & Background

### Current State

**What Exists Today:**

1. **Marketplace Scanning:**
   - `skillmeat/marketplace/scanner.py` scans GitHub repositories for artifacts
   - Detects artifacts by heuristic matching and frontmatter inspection
   - Stores metadata in `MarketplaceCatalogEntry` (SQLAlchemy ORM model)
   - Currently captures: name, type, description, confidence score, file content

2. **Artifact Tagging:**
   - Artifacts support tags (stored in user collection)
   - Tags are manually assigned during import or post-import
   - No automatic tag suggestion from source metadata
   - Users frequently assign organizational tags (domain, category, level, language)

3. **Path Structure (Repository Examples):**
   - Anthropic skills: `skills/{category}/{name}.md`
   - Community catalogs: `categories/{05-domain}/{artifact}.md`
   - Nested org: `src/ai/ml/{category}/{artifact}.ts`
   - Flat repos: `artifacts/{artifact}.md`

**Key Components:**
- `skillmeat/cache/models.py` - SQLAlchemy models for marketplace
- `skillmeat/marketplace/scanner.py` - Marketplace scanning logic
- `skillmeat/api/routers/marketplace_sources.py` - API endpoints
- `skillmeat/web/components/marketplace/` - Frontend marketplace UI

### Problem Space

**Pain Points:**

1. **Manual Tagging Overhead**
   - Users import artifacts and manually assign category/domain tags
   - No automatic suggestion from organizational structure evident in paths
   - Time-consuming for bulk imports (10+ artifacts)
   - Inconsistent tagging across collection due to effort required

2. **Lost Organizational Context**
   - Repository path structure (e.g., `categories/data-ai/`) contains semantic meaning
   - This structure is visible during scanning but not captured or offered to users
   - Users must re-enter organizational info as tags manually
   - Rich metadata discarded after scan completes

3. **Poor Discoverability**
   - Untagged artifacts are harder to browse and filter
   - Users miss artifacts that match their interests due to lack of categorical tags
   - Cross-collection search benefits from consistent tagging

4. **Inconsistent Normalization**
   - Path segments may include numeric prefixes (e.g., `05-data-ai`)
   - Users must decide which segments are meaningful tags
   - No standardized approach to path segment extraction rules

### Current Alternatives / Workarounds

**Manual Tagging Workflow:**
- Import artifact
- View artifact metadata
- Manually type tags based on path or content understanding
- Inefficient for bulk operations

**Repository Documentation:**
- Some repos document path structure in README
- Users must manually read and interpret documentation
- Not machine-readable; no enforcement

### Architectural Context

**Backend Architecture:**
- SQLAlchemy models in `skillmeat/cache/models.py`
- FastAPI routers for marketplace operations
- JSON columns used for flexible metadata (e.g., confidence scores)
- Alembic migrations for schema changes

**Frontend Architecture:**
- React components for marketplace browsing
- TanStack Query for server state management
- Modal-based catalog entry detail view
- Per-entry workflow patterns established

**Data Flow:**
```
GitHub Repo → Scanner → MarketplaceCatalogEntry → API → Frontend Browse/Import
                ↓
          (NEW) Extract Path Segments
                ↓
          (NEW) Store in path_segments column
                ↓
          (NEW) Frontend Review Component
                ↓
          (NEW) Import with opt-in checkbox
```

---

## 3. Problem Statement

**Core Gap:** Repository organizational structure (visible in artifact source paths) is not captured or offered to users as tag suggestions, requiring manual tag assignment and resulting in incomplete artifact metadata.

**User Story Format:**

> "As a user browsing a marketplace source with 20+ artifacts, I want to see suggested tags extracted from the path structure (e.g., `categories/data-ai/` → suggest `data-ai` tag), so I can quickly tag artifacts during import without manually reading each path."

> "As a curator managing a collection, I want to review path-based tag suggestions per artifact and approve/reject them individually, so I can ensure only relevant organizational tags are applied to my artifacts."

> "As a user importing multiple artifacts from `categories/python-basics/`, I want to opt-in to apply the extracted `python-basics` tag to all imported artifacts, so I can quickly organize my collection by source category without manual tag entry."

---

## 4. Goals & Success Metrics

### Business Goals

1. **Reduce manual tagging friction** - Surface organizational metadata automatically; reduce per-artifact tagging time
2. **Improve collection discoverability** - More consistently tagged artifacts enable better filtering and search
3. **Enable marketplace repository standardization** - Encourage repos to use consistent path structures by making them valuable

### User Goals

1. **Bulk importers:** Import multiple artifacts with consistent categorical tags in one workflow
2. **Curators:** Review and approve organizational suggestions before they become permanent tags
3. **Explorers:** Browse collections with better filtering based on auto-applied tags

### Technical Goals

1. Implement extraction with sensible defaults (no per-source configuration in MVP)
2. Maintain backward compatibility (new scans only; existing entries unaffected)
3. Enable flexible review workflow (per-entry approval UI)
4. Support future source-level configuration (Phase 4)

### Success Metrics

**Phase 1 (Backend Core - Scanning & Extraction):**
- 100% of new catalog entries include `path_segments` JSON with extracted segments
- Extraction correctly identifies 90%+ meaningful path segments (normalizes numbers, excludes common dirs)
- Zero overhead to scanning performance (<50ms per entry for extraction)

**Phase 2 (Frontend Review):**
- Users can review and approve/reject segments in <5 seconds per entry
- 80%+ of extracted segments are either approved or explicitly rejected
- Component renders correctly for entries with 1-10 segments

**Phase 3 (Import Integration):**
- <10ms overhead to import flow when applying approved path tags
- 100% of approved segments successfully converted to artifact tags
- Opt-in checkbox has >50% adoption rate in bulk import flows

**Overall:**
- Average manual tagging time per artifact reduced by 60% for tagged imports
- Tag consistency score increased by 40% (measure via tag distribution analysis)

---

## 5. Detailed Requirements

### Functional Requirements

#### 5.1 Data Model: Path Segment Storage

**File:** `skillmeat/cache/models.py`

Add two new JSON columns to support path-based tag extraction:

**On `MarketplaceSource` model:**
```python
path_tag_config: Mapped[Optional[str]] = mapped_column(
    Text,
    nullable=True,
    comment="JSON config for path-based tag extraction rules"
)
```

**On `MarketplaceCatalogEntry` model:**
```python
path_segments: Mapped[Optional[str]] = mapped_column(
    Text,
    nullable=True,
    comment="JSON array of extracted path segments with approval status"
)
```

**Schema Definitions:**

`path_tag_config` JSON structure (on MarketplaceSource):
```json
{
  "enabled": true,
  "rules": {
    "skip_segments": [0],
    "max_depth": 3,
    "normalize_numbers": true,
    "exclude_patterns": ["^\\d+$", "^(src|lib|test|docs|examples)$"]
  }
}
```

`path_segments` JSON structure (on MarketplaceCatalogEntry):
```json
{
  "raw_path": "categories/05-data-ai/ai-engineer.md",
  "extracted": [
    {
      "segment": "categories",
      "normalized": "categories",
      "status": "excluded",
      "reason": "matches exclude_patterns"
    },
    {
      "segment": "05-data-ai",
      "normalized": "data-ai",
      "status": "pending",
      "reason": null
    }
  ],
  "extracted_at": "2025-01-04T10:00:00Z"
}
```

**Status Values:**
- `pending`: Extracted segment awaiting user review
- `approved`: User approved; ready to apply as tag
- `rejected`: User rejected; will not apply as tag
- `excluded`: Filtered by extraction rules (excluded_patterns or skip_segments)

#### 5.2 Database Migration

**File:** `skillmeat/api/migrations/versions/{timestamp}_add_path_segments.py`

Create Alembic migration to:
- Add `path_tag_config` column to `marketplace_sources` table
- Add `path_segments` column to `marketplace_catalog_entries` table
- Both columns nullable (backward compatible)
- Add comment on each column explaining purpose

Downgrade should safely drop columns (no data loss risk as feature is new).

#### 5.3 Path Segment Extraction Service

**New File:** `skillmeat/core/path_tags.py`

Implement `PathSegmentExtractor` class:

```python
@dataclass
class PathTagConfig:
    """Configuration for path-based tag extraction."""
    enabled: bool = True
    skip_segments: list[int] = field(default_factory=list)
    max_depth: int = 3
    normalize_numbers: bool = True
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "^\\d+$",  # pure numbers
        "^(src|lib|test|docs|examples|__pycache__|node_modules)$"
    ])

    @classmethod
    def from_json(cls, json_str: str) -> "PathTagConfig":
        """Deserialize from JSON string."""

    def to_json(self) -> str:
        """Serialize to JSON string."""

@dataclass
class ExtractedSegment:
    """A single extracted path segment."""
    segment: str          # original segment
    normalized: str       # after normalization
    status: Literal["pending", "approved", "rejected", "excluded"]
    reason: Optional[str] = None  # why excluded, if applicable

class PathSegmentExtractor:
    """Extract and normalize path segments from artifact paths."""

    def __init__(self, config: PathTagConfig | None = None):
        self.config = config or PathTagConfig()

    def extract(self, path: str) -> list[ExtractedSegment]:
        """
        Extract path segments from artifact path.

        Args:
            path: Full artifact path (e.g., "categories/05-data-ai/ai-engineer.md")

        Returns:
            List of ExtractedSegment with status and normalization applied

        Algorithm:
        1. Split path by '/' and remove filename
        2. Apply skip_segments (remove first N segments)
        3. Apply max_depth (keep only first N segments)
        4. For each segment:
           - Normalize (remove number prefixes if normalize_numbers=true)
           - Check exclude_patterns regex
           - Assign status: "excluded" if matched, else "pending"
        5. Return list of ExtractedSegment
        """
```

**Normalization Rules:**

| Input | normalize_numbers=true | normalize_numbers=false |
|-------|------------------------|------------------------|
| `05-data-ai` | `data-ai` | `05-data-ai` |
| `data-ai` | `data-ai` | `data-ai` |
| `01_foundations` | `foundations` | `01_foundations` |
| `100-basics` | `basics` | `100-basics` |

**Exclusion Patterns (Default):**
- `^\\d+$` - Pure numbers (e.g., `00`, `05`)
- `^(src\|lib\|test\|docs\|examples\|__pycache__\|node_modules)$` - Common directories

#### 5.4 Scanner Integration

**File:** `skillmeat/marketplace/scanner.py`

Modify scanning logic to extract path segments:

1. When creating `MarketplaceCatalogEntry` for detected artifact:
   - Check if source has `path_tag_config` (if not, use defaults)
   - Call `PathSegmentExtractor.extract(artifact_path)`
   - Serialize extracted segments to JSON
   - Store in `entry.path_segments`

2. Extraction must happen after artifact detection but before saving entry to database

3. Extraction should not block scanning (all other metadata collected regardless)

**Pseudocode Integration:**
```python
def _create_catalog_entry(self, artifact_path: str, source: MarketplaceSource):
    # ... existing artifact detection and metadata collection ...

    entry = MarketplaceCatalogEntry(
        source_id=source.id,
        name=artifact_name,
        type=artifact_type,
        # ... other fields ...
    )

    # NEW: Extract path segments
    if source.path_tag_config:
        config = PathTagConfig.from_json(source.path_tag_config)
    else:
        config = PathTagConfig()  # use defaults

    if config.enabled:
        extractor = PathSegmentExtractor(config)
        segments = extractor.extract(artifact_path)
        entry.path_segments = json.dumps({
            "raw_path": artifact_path,
            "extracted": [asdict(s) for s in segments],
            "extracted_at": datetime.utcnow().isoformat()
        })

    session.add(entry)
```

#### 5.5 API Schemas

**File:** `skillmeat/api/schemas/marketplace.py`

Add request/response schemas for path tag operations:

```python
class PathTagConfigRequest(BaseModel):
    """Configuration for path-based tag extraction (user input)."""
    enabled: bool = True
    skip_segments: list[int] = Field(default_factory=list, description="Skip first N segments")
    max_depth: int = Field(3, ge=1, le=10, description="Max segments to extract")
    normalize_numbers: bool = True
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "^\\d+$",
            "^(src|lib|test|docs|examples)$"
        ],
        description="Regex patterns to exclude from extraction"
    )

class ExtractedSegmentResponse(BaseModel):
    """Single extracted path segment."""
    segment: str
    normalized: str
    status: Literal["pending", "approved", "rejected", "excluded"]
    reason: Optional[str] = None

class PathSegmentsResponse(BaseModel):
    """All path segments for a catalog entry."""
    entry_id: str
    raw_path: str
    extracted: list[ExtractedSegmentResponse]
    extracted_at: datetime

class UpdateSegmentStatusRequest(BaseModel):
    """Request to update approval status of a segment."""
    segment: str  # original segment value
    status: Literal["approved", "rejected"]

class UpdateSegmentStatusResponse(BaseModel):
    """Response after updating segment status."""
    entry_id: str
    raw_path: str
    extracted: list[ExtractedSegmentResponse]
    updated_at: datetime
```

#### 5.6 API Endpoints

**File:** `skillmeat/api/routers/marketplace_sources.py`

Add endpoints for path tag review operations:

```python
@router.get(
    "/{source_id}/catalog/{entry_id}/path-tags",
    response_model=PathSegmentsResponse,
    summary="Get path-based tag suggestions for catalog entry",
    description="Retrieve extracted path segments and their approval status"
)
async def get_path_tags(
    source_id: str = Path(..., description="Marketplace source ID"),
    entry_id: str = Path(..., description="Catalog entry ID"),
    manager: MarketplaceManagerDep,
) -> PathSegmentsResponse:
    """
    Get extracted path segments for a catalog entry.

    Returns:
        PathSegmentsResponse with all segments and their status

    Raises:
        404: If source or entry not found
        400: If entry has no path_segments (not extracted yet)
    """

@router.patch(
    "/{source_id}/catalog/{entry_id}/path-tags",
    response_model=UpdateSegmentStatusResponse,
    summary="Update approval status of a path segment",
    description="Approve or reject a suggested path-based tag"
)
async def update_path_tag_status(
    source_id: str = Path(...),
    entry_id: str = Path(...),
    request: UpdateSegmentStatusRequest = Body(...),
    manager: MarketplaceManagerDep,
) -> UpdateSegmentStatusResponse:
    """
    Update approval status of a single path segment.

    Modifies the status field in path_segments JSON:
    - "approved": Segment will be applied as tag during import
    - "rejected": Segment will not be applied as tag

    Returns:
        Updated PathSegmentsResponse with changed segment status

    Raises:
        404: If source, entry, or segment not found
        409: If segment already approved/rejected (no double-status)
    """
```

**Response Codes:**
- GET returns 200 (success) or 404 (not found)
- PATCH returns 200 (success), 404 (not found), or 409 (conflict - already approved/rejected)

#### 5.7 Import Request Enhancement

**File:** `skillmeat/api/schemas/discovery.py` (or marketplace.py)

Add opt-in flag to bulk import request:

```python
class BulkImportRequest(BaseModel):
    """Request to import multiple catalog entries."""
    entry_ids: list[str]
    # ... existing fields (collection_id, etc) ...
    apply_path_tags: bool = Field(
        default=True,
        description="Apply approved path-based tags to imported artifacts"
    )
```

**Backward Compatibility:** Default `apply_path_tags=true` assumes user wants tags applied; can be set to false to skip.

#### 5.8 Import Logic Enhancement

**File:** `skillmeat/marketplace/importer.py` (or core equivalent)

Update import function to apply approved path tags:

```python
def import_catalog_entries(
    request: BulkImportRequest,
    session: Session,
    user_id: str
):
    """
    Import catalog entries and optionally apply path-based tags.

    For each entry:
    1. Import artifact normally
    2. If request.apply_path_tags=true and entry.path_segments exists:
       a. Parse path_segments JSON
       b. Find all segments with status="approved"
       c. Create/find corresponding tags
       d. Apply tags to imported artifact
    3. Return import result per entry
    """
    results = []

    for entry_id in request.entry_ids:
        entry = get_catalog_entry(entry_id)
        artifact = import_artifact(entry, session, user_id)

        if request.apply_path_tags and entry.path_segments:
            try:
                segments_data = json.loads(entry.path_segments)
                approved = [
                    s for s in segments_data["extracted"]
                    if s["status"] == "approved"
                ]

                for seg in approved:
                    tag_name = seg["normalized"]
                    tag = get_or_create_tag(tag_name, session)
                    apply_tag_to_artifact(artifact.id, tag.id, session)

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to apply path tags for {entry_id}: {e}")
                # Continue with import; tags are optional enhancement

        results.append(ImportResult(entry_id=entry_id, status="success", ...))

    return results
```

### Non-Functional Requirements

#### 5.9 Performance

- **Extraction:** <50ms per entry for path segment extraction (no regex compilation per call)
- **API Response:** GET/PATCH endpoints respond in <200ms
- **Import:** <10ms overhead per artifact when applying approved tags
- **Database:** No N+1 queries; use joins for tag creation/application

#### 5.10 Reliability

- **Extraction Failures:** Non-blocking (extraction failures don't prevent artifact detection)
- **Import Failures:** Path tag application failures don't block artifact import (soft-fail)
- **Data Integrity:** All updates use transactional semantics (ACID)

#### 5.11 Security

- **Input Validation:** All regex patterns validated; max 10 exclude_patterns per source
- **Authorization:** API endpoints protected with existing marketplace source access controls
- **Injection Prevention:** All path input sanitized before regex matching

#### 5.12 Usability

- **Discoverability:** Path tags feature visible in UI without explicit onboarding
- **Default Behavior:** Reasonable defaults for extraction rules (no configuration needed in MVP)
- **Review Workflow:** Per-entry review requires <5 clicks to approve/reject all segments
- **Accessibility:** UI follows WCAG 2.1 AA standards

---

## 6. Scope (In-Scope vs Out-of-Scope)

### In-Scope (MVP)

1. **Backend Core (Phase 1)**
   - Data model (two new JSON columns)
   - Database migration
   - PathSegmentExtractor service
   - Scanner integration
   - API schemas and endpoints for GET/PATCH path tags
   - Error handling and validation

2. **Frontend Review (Phase 2)**
   - Per-entry path tag review component
   - Approve/reject buttons for individual segments
   - Integration into catalog entry modal
   - API client functions for GET/PATCH operations

3. **Import Integration (Phase 3)**
   - Opt-in checkbox in bulk import dialog
   - Backend logic to apply approved tags during import
   - Error handling for tag application failures

4. **Default Behavior**
   - Sensible default extraction rules (no per-source configuration)
   - New scans only (no backfill of existing entries)

### Out-of-Scope (Future Phases)

1. **Source Configuration UI (Phase 4)**
   - UI to configure path_tag_config per source
   - Skip segments, max_depth, exclude_patterns customization
   - Preview extraction on sample paths

2. **Bulk Approval Workflow (Phase 4)**
   - UI to review and approve/reject all segments across multiple entries at once
   - Batch approval operations
   - Approval recommendations based on patterns

3. **Advanced Features (Backlog)**
   - Machine learning suggestions based on artifact content
   - Tag merging/aliasing (e.g., "python-basics" → "python")
   - Tag relationship graphs
   - Automatic exclusion rules based on user feedback

4. **Mobile/CLI Support**
   - Mobile UI for path tag review (deferred to future mobile work)
   - CLI commands for path tag approval (nice-to-have)

---

## 7. Dependencies & Assumptions

### Dependencies

**External:**
- Python 3.9+ regex engine (standard library)
- SQLAlchemy for ORM operations (already in use)
- Alembic for migrations (already in use)
- FastAPI for API endpoints (already in use)
- React 18+ for frontend (already in use)

**Internal:**
- Marketplace source scanning functionality (core/marketplace/)
- Artifact import infrastructure (core/importer/)
- API framework and schemas (api/)
- Frontend component library (shadcn/radix-ui)

### Assumptions

1. **Path Structure Consistency**
   - Assumption: Most repos have predictable path structures (categories, domains, etc.)
   - Fallback: If no meaningful segments extracted, offer no suggestions (no empty tags)

2. **Default Rules Adequacy**
   - Assumption: Default exclude_patterns work for 90%+ of repositories
   - Validation: Test against 5+ large public repositories

3. **User Review Engagement**
   - Assumption: Users will review and approve tags (not ignore feature)
   - Fallback: If <20% approval rate, revisit UX in Phase 2

4. **Tag Creation**
   - Assumption: Importing user has permission to create tags
   - Fallback: If tag creation fails, skip tag application but continue import

5. **Backward Compatibility**
   - Assumption: Existing catalog entries without path_segments can coexist
   - Design: All path tag features gracefully degrade if path_segments is null

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| **Over-extraction of segments** | Too many irrelevant tags suggested; user fatigue | Medium | Default exclude_patterns refined during testing; max 5 segments extracted |
| **Regex performance degradation** | Scanning slows down with complex patterns | Low | Regex patterns pre-compiled; no per-entry compilation; <50ms target enforced |
| **Database migration conflicts** | Migration fails on existing databases | Low | Backward-compatible nullable columns; downgrade path is safe |
| **User ignores feature** | Low adoption of path tag review; wasted effort | Medium | Default apply_path_tags=true (opt-out is easier than opt-in); monitor adoption metrics |
| **Tag explosion** | Many single-use path tags created; collection becomes unwieldy | Medium | Phase 4: tag merging/aliasing features; review guidelines for tag naming |
| **Scanner performance impact** | Marketplace scanning slows down significantly | Low | Extraction <50ms per entry; async in future iterations if needed |
| **API rate limiting** | User reviews hundreds of segments; hits rate limits | Low | Frontend batches updates; per-source rate limits on GET path-tags endpoint |
| **Frontend performance** | Review component slow with 10+ segments per entry | Low | Virtualization for large segment lists; lazy loading if needed |

---

## 9. Target State (After Implementation)

### User Experience

1. **Marketplace Browsing:**
   - User opens marketplace source with 20+ artifacts
   - Each catalog entry card shows "badge: 3 suggested tags" (if extracted)
   - User clicks entry to open detail modal

2. **Per-Entry Review:**
   - Modal shows artifact name, type, description
   - New tab/section: "Suggested Tags" with list of extracted segments
   - Each segment shows: original (e.g., "05-data-ai"), normalized (e.g., "data-ai"), status icon
   - Approve button (checkmark) and Reject button (X) for each segment
   - Summary at bottom: "2 approved, 1 excluded, 0 rejected"

3. **Bulk Import:**
   - User selects 10 artifacts to import
   - Click "Bulk Import" → dialog opens
   - Existing fields: collection, etc.
   - NEW: Checkbox "Apply approved path tags" (checked by default)
   - Helper text: "Will apply 15 tags from 10 artifacts"
   - User clicks Import → artifacts imported with tags automatically applied

4. **Post-Import:**
   - Artifacts appear in collection with tags applied
   - User can see consistent categorical tags without manual entry
   - User can further edit tags in artifact detail view (existing feature)

### System Behavior

1. **Scanning:**
   - Marketplace scan detects artifact at path `categories/05-data-ai/ai-engineer.md`
   - PathSegmentExtractor applies default rules → extracts `["data-ai"]` (pending)
   - Stored in entry.path_segments JSON
   - Scan completes normally (extraction doesn't block)

2. **Review Workflow:**
   - User calls GET `/api/v1/marketplace-sources/{id}/catalog/{entry_id}/path-tags`
   - API returns PathSegmentsResponse with all segments
   - User clicks "Approve" for `data-ai` segment
   - API called: PATCH `/api/v1/marketplace-sources/{id}/catalog/{entry_id}/path-tags`
   - Request body: `{"segment": "data-ai", "status": "approved"}`
   - Segment status in DB updated to "approved"

3. **Import Execution:**
   - User calls POST `/api/v1/artifacts/discover/import` with `apply_path_tags=true`
   - Backend queries each entry's path_segments
   - Finds all segments with status="approved"
   - Creates/finds corresponding tags in collection
   - Links tags to imported artifact
   - Returns success with tag count in result

---

## 10. Acceptance Criteria

### Backend Core (Phase 1)

- [ ] Database migration creates `path_tag_config` column on `marketplace_sources` (nullable)
- [ ] Database migration creates `path_segments` column on `marketplace_catalog_entries` (nullable)
- [ ] PathSegmentExtractor class implemented with >95% test coverage
  - [ ] Normalizes number prefixes correctly (05-data-ai → data-ai)
  - [ ] Applies skip_segments correctly (removes first N segments)
  - [ ] Applies max_depth correctly (keeps only first N segments)
  - [ ] Applies exclude_patterns correctly (regex matching)
  - [ ] Returns ExtractedSegment objects with correct status
- [ ] Scanner integration calls PathSegmentExtractor for new entries
  - [ ] path_segments column populated for scanned artifacts
  - [ ] Extraction JSON validates against schema
  - [ ] Scanning performance unaffected (<50ms extraction per entry)
- [ ] API schemas defined and integrated
- [ ] GET `/api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags` endpoint implemented
  - [ ] Returns 200 with PathSegmentsResponse for valid entry
  - [ ] Returns 404 for missing source or entry
  - [ ] Returns 400 if entry has no path_segments (not extracted)
- [ ] PATCH `/api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags` endpoint implemented
  - [ ] Updates segment status to approved/rejected
  - [ ] Returns 200 with updated PathSegmentsResponse
  - [ ] Returns 404 for missing resource
  - [ ] Returns 409 if segment already has final status (no double-approval)
- [ ] Error handling for all edge cases
  - [ ] Invalid regex patterns rejected with clear error
  - [ ] Malformed path_segments JSON handled gracefully
  - [ ] Segment not found returns 404
- [ ] Unit tests cover extraction logic and edge cases (>90% coverage)
- [ ] Integration tests verify scanner → API flow end-to-end

### Frontend Review (Phase 2)

- [ ] API client functions implemented in `lib/api/marketplace.ts`
  - [ ] `getPathTags(sourceId, entryId)` calls GET endpoint
  - [ ] `updatePathTagStatus(sourceId, entryId, segment, status)` calls PATCH endpoint
  - [ ] Error handling with ApiError wrapper
- [ ] usePathTags hook implemented in `hooks/use-path-tags.ts`
  - [ ] useQuery for fetching segments
  - [ ] useMutation for updating status
  - [ ] Cache invalidation after status update
- [ ] PathTagReview component created in `components/marketplace/path-tag-review.tsx`
  - [ ] Displays segment list with segment → normalized mapping
  - [ ] Status badges (pending, approved, excluded, rejected)
  - [ ] Approve/Reject buttons for pending segments
  - [ ] Summary footer showing counts
  - [ ] Loading state while fetching
  - [ ] Error message if fetch fails
  - [ ] Disabled state while mutation in progress
- [ ] Integration into CatalogEntryModal
  - [ ] New "Suggested Tags" tab/section visible when path_segments exists
  - [ ] Component renders correctly for entries with 1-10 segments
  - [ ] Component hides gracefully if no path_segments
- [ ] Component accessibility
  - [ ] Buttons keyboard accessible
  - [ ] ARIA labels for screen readers
  - [ ] Proper focus management
- [ ] E2E test: User can view and approve segments in modal

### Import Integration (Phase 3)

- [ ] BulkImportRequest schema includes `apply_path_tags: bool` field
  - [ ] Default value is true
  - [ ] Field documented with description
- [ ] Import logic updated to apply approved tags
  - [ ] Queries path_segments from each entry
  - [ ] Finds segments with status="approved"
  - [ ] Creates/finds corresponding tags
  - [ ] Links tags to imported artifact
  - [ ] Handles tag creation failures gracefully (soft-fail)
- [ ] Import UI checkbox implemented in bulk import dialog
  - [ ] Checkbox labeled "Apply approved path tags"
  - [ ] Helper text shows count of tags that will be applied
  - [ ] Unchecking disables tag application
  - [ ] Visual feedback when selected/unselected
- [ ] Import result includes tag count
  - [ ] Backend returns count of tags applied per artifact
  - [ ] Frontend displays total tags applied in import result notification
- [ ] Integration tests verify full flow
  - [ ] Scan → Review → Import → Verify tags on artifact

### Non-Functional Criteria

- [ ] All extraction operations complete <50ms per entry
- [ ] All API endpoints respond <200ms
- [ ] Import overhead <10ms per artifact for tag application
- [ ] Zero extraction failures that block artifact detection
- [ ] Migration is backward compatible (no data loss on existing entries)
- [ ] All new code follows project style guidelines (black, mypy, flake8)
- [ ] All frontend code passes linting (eslint, prettier)
- [ ] Documentation updated for new features
- [ ] Manual QA: User can review and approve tags per entry
- [ ] Manual QA: User can import with apply_path_tags=true/false
- [ ] Load testing: Extraction on 1000-entry catalog completes <30s

---

## 11. Implementation Phases

### Phase 1: Backend Core (1.5 - 2 weeks)

**Deliverables:**
- Database migration (new columns)
- PathSegmentExtractor service
- Scanner integration
- API schemas and endpoints
- Comprehensive test coverage

**Tasks:**
1. Create Alembic migration
2. Implement PathTagConfig and ExtractedSegment dataclasses
3. Implement PathSegmentExtractor with unit tests
4. Integrate into scanner.py
5. Create API schemas in marketplace.py
6. Implement GET and PATCH endpoints in marketplace_sources.py router
7. Write integration tests

**Acceptance:** All Phase 1 acceptance criteria met; endpoints tested and documented

### Phase 2: Frontend Review UI (1 - 1.5 weeks)

**Deliverables:**
- API client functions
- React Query hooks
- PathTagReview component
- Integration into catalog entry modal
- E2E testing

**Tasks:**
1. Create API client functions in lib/api/marketplace.ts
2. Implement usePathTags hook in hooks/use-path-tags.ts
3. Build PathTagReview component with Approve/Reject UX
4. Integrate into CatalogEntryModal
5. Accessibility audit (WCAG 2.1 AA)
6. E2E tests with user review workflow

**Acceptance:** All Phase 2 acceptance criteria met; component tested with real data

### Phase 3: Import Integration (1 week)

**Deliverables:**
- Enhanced import request schema
- Backend logic for applying tags
- Frontend UI checkbox
- Integration tests

**Tasks:**
1. Update BulkImportRequest schema (add apply_path_tags field)
2. Implement tag application logic in importer.py
3. Add checkbox to import dialog UI
4. Update import result to include tag counts
5. Integration tests end-to-end
6. Manual QA of full flow

**Acceptance:** All Phase 3 acceptance criteria met; bulk imports apply tags correctly

### Phase 4: Source Configuration (Future - deferred)

**Deliverables:**
- Source-level configuration UI
- Customizable extraction rules
- Path preview/sample extraction

**Status:** Deferred; to be prioritized based on Phase 3 feedback

---

## 12. Testing Strategy

### Unit Tests

| Component | Test Cases | Target Coverage |
|-----------|-----------|-----------------|
| PathSegmentExtractor | 15+ cases (normalization, depth, patterns, edge cases) | >95% |
| PathTagConfig | 5+ cases (deserialization, defaults) | >90% |
| API schemas | 5+ cases (validation, edge cases) | >85% |

**Test Files:**
- `tests/core/test_path_tags.py` - Extraction logic
- `tests/api/test_marketplace_path_tags.py` - API schemas

### Integration Tests

| Scenario | Test Location |
|----------|---------------|
| Scanner → path_segments population | `tests/marketplace/test_scanner_path_tags.py` |
| GET path-tags endpoint | `tests/api/routers/test_marketplace_sources_path_tags.py` |
| PATCH path-tags endpoint | `tests/api/routers/test_marketplace_sources_path_tags.py` |
| Import with apply_path_tags | `tests/core/test_import_with_path_tags.py` |

### E2E Tests

| User Flow | Test Location |
|-----------|---------------|
| Scan → view path tags → approve → import | `tests/e2e/test_path_tag_workflow.py` |
| Review multiple entries | `tests/e2e/test_catalog_review_multiple.py` |

### Performance Tests

- [ ] Extraction: 1000 entries scan <30s (avg <50ms per entry)
- [ ] API: GET/PATCH endpoints response <200ms
- [ ] Import: 100 artifacts with 10+ tags each <5s

---

## 13. Documentation

### User Documentation

- [ ] Marketplace browsing guide: "Using Suggested Tags" section
- [ ] Bulk import guide: "Applying Path-Based Tags" section
- [ ] FAQ: "How are suggested tags extracted?" and "How do I customize extraction rules?"

### Developer Documentation

- [ ] Architecture doc: Path-based tag extraction system overview
- [ ] API documentation: GET/PATCH path-tags endpoints in OpenAPI spec
- [ ] Code comments: PathSegmentExtractor algorithm documented
- [ ] Migration guide: How to backfill path tags for existing catalogs (Phase 4 prep)

### Code Examples

- [ ] Example: Extract path tags from custom path structure
- [ ] Example: Configure extraction rules (Phase 4)
- [ ] Example: Apply tags during import via API

---

## 14. Success Metrics (Post-Launch)

### Adoption Metrics

- % of users who use apply_path_tags checkbox in bulk import
- % of catalog entries with at least one approved segment
- Avg time spent per entry in path tag review

### Quality Metrics

- % of approved path tags that users later modify or remove (indicate low quality)
- % of catalog entries with no extracted segments (indicate need for rule tuning)
- Tag distribution: % increase in consistently-named categorical tags

### Performance Metrics

- Marketplace scanning time delta (should be <1% overhead)
- API endpoint p95 latency (target: <200ms)
- Import operation time delta (should be <1% overhead)

### User Feedback

- NPS for path tag feature (target: >7/10)
- User requests for source-level configuration (indicates Phase 4 demand)
- Support tickets related to incorrect tag suggestions (indicates need for tuning)

---

## 15. References

### Technical Design
- `/Users/miethe/.claude/plans/warm-marinating-eich.md` - Detailed technical implementation plan

### Related PRDs
- Marketplace GitHub Ingestion v1
- Marketplace Source Enhancements v1
- Smart Import & Discovery v1

### Project Standards
- SkillMeat CLAUDE.md - Development conventions
- API Router Patterns - `skillmeat/api/CLAUDE.md`
- Frontend Hooks Patterns - `.claude/rules/web/hooks.md`
- Frontend API Client - `.claude/rules/web/api-client.md`

---

## Appendix: Default Extraction Rules

### Default Configuration

```json
{
  "enabled": true,
  "rules": {
    "skip_segments": [0],
    "max_depth": 3,
    "normalize_numbers": true,
    "exclude_patterns": [
      "^\\d+$",
      "^(src|lib|test|docs|examples|__pycache__|node_modules)$"
    ]
  }
}
```

### Rule Justification

| Rule | Rationale | Examples |
|------|-----------|----------|
| skip_segments: [0] | Skip repo root (redundant as tag) | `github.com/org/repo/categories/...` → skip first segment |
| max_depth: 3 | Limit extracted segments to 3 (avoid tag explosion) | Deep paths: `a/b/c/d/e.md` → extract `[b, c, d]` |
| normalize_numbers: true | Remove numeric prefixes (not useful as tags) | `05-data-ai` → `data-ai`; `100-basics` → `basics` |
| ^\\d+$| Exclude pure numbers (e.g., versioning) | Skip `v1`, `2024`, `01` |
| ^(src\|lib\|...) | Exclude common dir names (not organizational) | Skip `src`, `lib`, `test`, `docs`, etc. |

### Testing Against Real Repositories

Validation against:
1. Anthropic skills catalog (anthropics/skills)
2. Community plugin repo (typical structure)
3. Large open-source project (varied path structure)
4. Flat artifact repo (minimal path hierarchy)
5. Deeply nested repo (test max_depth enforcement)

---

**Document Status:** Ready for review by development team

**Next Steps:**
1. Review and approve PRD
2. Schedule Phase 1 backend work
3. Prepare test data and sample repositories
4. Begin Phase 1 implementation
