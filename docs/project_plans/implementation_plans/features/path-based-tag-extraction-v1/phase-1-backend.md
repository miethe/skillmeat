---
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: path-based-tag-extraction
prd_ref: null
plan_ref: null
---
# Phase 1: Backend Core Implementation

**Phase**: 1 (Backend Core)
**Duration**: 1.5-2 weeks
**Story Points**: 25-30
**Status**: Ready for Implementation
**Dependencies**: None

---

## Phase Overview

Implement the backend extraction logic, database layer, and API endpoints for path-based tag review. This phase establishes the foundation for all downstream functionality (frontend and import integration).

### Deliverables

1. Database migration (two new JSON columns)
2. PathSegmentExtractor service with dataclasses
3. Scanner integration for automatic extraction
4. API schemas for path tag operations
5. GET and PATCH endpoints for path tag review
6. Comprehensive unit + integration tests (>90% coverage)

### Success Criteria

- Database migrations pass (upgrade and downgrade)
- PathSegmentExtractor achieves >95% test coverage
- Scanner automatically populates path_segments for new entries
- API endpoints respond with correct status codes
- All operations complete <200ms (extraction <50ms per entry)
- No regressions in existing marketplace functionality

---

## Task Breakdown

### Task 1.1: Database Migration

**Assigned To**: data-layer-expert
**Model**: Sonnet
**Estimation**: 3 story points
**Duration**: 3-4 hours
**Status**: Not Started

#### Description

Create Alembic migration to add two new nullable JSON columns to marketplace tables:
- `MarketplaceSource.path_tag_config` (Text/nullable)
- `MarketplaceCatalogEntry.path_segments` (Text/nullable)

#### Acceptance Criteria

- [ ] Migration file created at `skillmeat/api/migrations/versions/{timestamp}_add_path_segments.py`
- [ ] `upgrade()` function adds both columns with proper nullability
- [ ] `downgrade()` function safely drops both columns
- [ ] Migration tested in local environment:
  - [ ] Upgrade executes without errors
  - [ ] Downgrade executes without errors
  - [ ] Column properties verified (nullable, type, comments)
- [ ] Comments added to columns explaining purpose
- [ ] No data loss on downgrade (columns are new, no existing data)
- [ ] Migration follows project Alembic patterns (check existing migrations for style)

#### Implementation Notes

**File Location**: `skillmeat/api/migrations/versions/{new_timestamp}_add_path_segments.py`

**Pseudo-code**:
```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add path_tag_config to marketplace_sources
    op.add_column(
        'marketplace_sources',
        sa.Column(
            'path_tag_config',
            sa.Text(),
            nullable=True,
            comment="JSON config for path-based tag extraction rules"
        )
    )

    # Add path_segments to marketplace_catalog_entries
    op.add_column(
        'marketplace_catalog_entries',
        sa.Column(
            'path_segments',
            sa.Text(),
            nullable=True,
            comment="JSON array of extracted path segments with approval status"
        )
    )

def downgrade():
    op.drop_column('marketplace_catalog_entries', 'path_segments')
    op.drop_column('marketplace_sources', 'path_tag_config')
```

#### Dependencies

- None (independent)

#### Reference Files

- Existing migrations: `skillmeat/api/migrations/versions/`
- Models to update: `skillmeat/cache/models.py`

---

### Task 1.2: Update Models

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 2 story points
**Duration**: 2-3 hours
**Status**: Not Started

#### Description

Update SQLAlchemy ORM models to include new columns with proper type annotations and comments.

#### Acceptance Criteria

- [ ] `MarketplaceSource` model includes `path_tag_config: Mapped[Optional[str]]` column
- [ ] `MarketplaceCatalogEntry` model includes `path_segments: Mapped[Optional[str]]` column
- [ ] Both columns use `mapped_column(Text, nullable=True, comment="...")`
- [ ] Type hints are explicit and correct
- [ ] Docstrings updated (if applicable)
- [ ] Models pass mypy type checking
- [ ] No breaking changes to existing model usage

#### Implementation Notes

**File Location**: `skillmeat/cache/models.py`

**Location in file**:
- `path_tag_config` added to `MarketplaceSource` (around line 1310)
- `path_segments` added to `MarketplaceCatalogEntry` (around line 1420)

**Example**:
```python
# In MarketplaceSource class:
path_tag_config: Mapped[Optional[str]] = mapped_column(
    Text,
    nullable=True,
    comment="JSON config for path-based tag extraction rules"
)

# In MarketplaceCatalogEntry class:
path_segments: Mapped[Optional[str]] = mapped_column(
    Text,
    nullable=True,
    comment="JSON array of extracted path segments with approval status"
)
```

#### Dependencies

- Task 1.1: Migration file provides context for column definitions

---

### Task 1.3: PathTagConfig & ExtractedSegment Dataclasses

**Assigned To**: python-backend-engineer
**Model**: Opus
**Estimation**: 5 story points
**Duration**: 6-8 hours
**Status**: Not Started

#### Description

Implement dataclasses and supporting types for path tag configuration and extracted segments. These will be used by the PathSegmentExtractor service and API schemas.

#### Acceptance Criteria

- [ ] `PathTagConfig` dataclass created with fields:
  - [ ] `enabled: bool = True`
  - [ ] `skip_segments: list[int] = field(default_factory=list)`
  - [ ] `max_depth: int = 3`
  - [ ] `normalize_numbers: bool = True`
  - [ ] `exclude_patterns: list[str] = field(default_factory=...)`
- [ ] `ExtractedSegment` dataclass created with fields:
  - [ ] `segment: str` (original segment value)
  - [ ] `normalized: str` (after normalization rules)
  - [ ] `status: Literal["pending", "approved", "rejected", "excluded"]`
  - [ ] `reason: Optional[str]` (why excluded, if applicable)
- [ ] `PathTagConfig` includes class methods:
  - [ ] `from_json(json_str: str) -> PathTagConfig` (deserialize from JSON)
  - [ ] `to_json() -> str` (serialize to JSON string)
  - [ ] `defaults() -> PathTagConfig` (create instance with recommended defaults)
- [ ] `ExtractedSegment` can be converted to dict with `asdict(segment)`
- [ ] Default exclude_patterns includes:
  - [ ] `^\\d+$` (pure numbers)
  - [ ] `^(src|lib|test|docs|examples|__pycache__|node_modules)$` (common dirs)
- [ ] All dataclasses include docstrings
- [ ] JSON serialization handles edge cases (invalid JSON returns helpful error)
- [ ] Type hints are correct and pass mypy

#### Implementation Notes

**File Location**: `skillmeat/core/path_tags.py` (new file)

**Pseudo-code**:
```python
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional
import json

@dataclass
class PathTagConfig:
    """Configuration for path-based tag extraction."""
    enabled: bool = True
    skip_segments: list[int] = field(default_factory=list)
    max_depth: int = 3
    normalize_numbers: bool = True
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "^\\d+$",
        "^(src|lib|test|docs|examples|__pycache__|node_modules)$"
    ])

    @classmethod
    def from_json(cls, json_str: str) -> "PathTagConfig":
        """Deserialize from JSON string."""
        try:
            data = json.loads(json_str)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in path_tag_config: {e}")

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self))

    @classmethod
    def defaults(cls) -> "PathTagConfig":
        """Create instance with recommended defaults."""
        return cls()

@dataclass
class ExtractedSegment:
    """A single extracted path segment."""
    segment: str          # original segment from path
    normalized: str       # after normalization
    status: Literal["pending", "approved", "rejected", "excluded"]
    reason: Optional[str] = None  # why excluded
```

#### Dependencies

- None (pure Python)

---

### Task 1.4: PathSegmentExtractor Service

**Assigned To**: python-backend-engineer
**Model**: Opus
**Estimation**: 8 story points
**Duration**: 12-16 hours
**Status**: Not Started

#### Description

Implement the core `PathSegmentExtractor` class that extracts, normalizes, and filters path segments according to configuration rules.

#### Acceptance Criteria

- [ ] `PathSegmentExtractor` class created with:
  - [ ] `__init__(config: PathTagConfig | None = None)` constructor
  - [ ] `extract(path: str) -> list[ExtractedSegment]` method
- [ ] Extraction algorithm correctly implements:
  - [ ] **Step 1**: Split path by `/` and remove filename (last segment)
  - [ ] **Step 2**: Apply `skip_segments` (remove first N segments)
  - [ ] **Step 3**: Apply `max_depth` (keep only first N segments after skip)
  - [ ] **Step 4**: For each remaining segment:
    - [ ] Normalize (apply `normalize_numbers` rules)
    - [ ] Check `exclude_patterns` regex
    - [ ] Assign status: `excluded` if matched pattern, else `pending`
  - [ ] **Step 5**: Return list of `ExtractedSegment` objects
- [ ] Normalization correctly handles:
  - [ ] `05-data-ai` → `data-ai` (remove leading digits and dash)
  - [ ] `01_foundations` → `foundations` (remove leading digits and underscore)
  - [ ] `100-basics` → `basics` (remove leading digits and dash)
  - [ ] `data-ai` → `data-ai` (no change if no prefix)
  - [ ] `v1.2` → `v1.2` (preserve non-leading digits)
- [ ] Regex patterns:
  - [ ] Pre-compiled for performance (not compiled per call)
  - [ ] Invalid patterns raise `ValueError` with helpful message
  - [ ] Patterns tested against sample paths
- [ ] Edge cases handled:
  - [ ] Empty path: returns empty list
  - [ ] Single-segment path (no directories): returns empty list
  - [ ] Path with only filename: returns empty list
  - [ ] All segments excluded: returns list of `excluded` statuses
  - [ ] skip_segments larger than segment count: returns empty list
  - [ ] max_depth=0: returns empty list
- [ ] Performance verified:
  - [ ] Single extraction <50ms (including regex matching)
  - [ ] 1000 extractions <50s (average <50ms per entry)
- [ ] Docstring includes algorithm description and examples
- [ ] Type hints are complete and pass mypy

#### Implementation Notes

**File Location**: `skillmeat/core/path_tags.py` (same file as dataclasses)

**Normalization Algorithm**:
```
Input: "05-data-ai"
1. If normalize_numbers=true:
   - Find leading digits: "05"
   - Find separator: "-"
   - Remove prefix and separator: "data-ai"
2. Normalize punctuation (dash to underscore optionally): keep as-is for now
Output: "data-ai"
```

**Exclusion Pattern Example**:
```
Pattern: "^(src|lib|test)$"
Segment: "src"
Match: YES → status = "excluded"
Reason: "matches exclude_patterns"
```

**Performance Optimization**:
```python
# Pre-compile regex patterns once
self._compiled_patterns = [re.compile(p) for p in config.exclude_patterns]

# Reuse compiled patterns for each segment (not per-call compilation)
for pattern in self._compiled_patterns:
    if pattern.match(normalized):
        # Mark as excluded
```

#### Test Cases (15+)

1. **Normalization**:
   - `05-data-ai` → `data-ai`
   - `01_foundations` → `foundations`
   - `100-basics` → `basics`
   - `data-ai` → `data-ai` (no change)
   - `v1` → `v1` (not leading digits)

2. **Depth Limiting**:
   - Path with 5 segments, max_depth=3 → keep first 3
   - Path with 2 segments, max_depth=3 → keep 2
   - max_depth=0 → return empty

3. **Skip Segments**:
   - Path `a/b/c/d.md`, skip_segments=[0] → `b`, `c`
   - Path `a/b/c.md`, skip_segments=[0,1] → `c`

4. **Pattern Exclusion**:
   - Pattern `^\\d+$` excludes `05`
   - Pattern `^src$` excludes `src`
   - Multiple patterns work correctly

5. **Edge Cases**:
   - Empty path: `""` → empty list
   - Single segment: `file.md` → empty list
   - All excluded: only excluded statuses returned

#### Dependencies

- Task 1.3: PathTagConfig and ExtractedSegment dataclasses

---

### Task 1.5: Unit Tests for PathSegmentExtractor

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 5 story points
**Duration**: 6-8 hours
**Status**: Not Started

#### Description

Create comprehensive unit tests for PathSegmentExtractor covering normalization, depth limiting, pattern matching, and edge cases.

#### Acceptance Criteria

- [ ] Test file created: `tests/core/test_path_tags.py`
- [ ] 15+ test cases with >95% code coverage
- [ ] Tests organized by category (normalization, depth, patterns, edges)
- [ ] Each test case is isolated and repeatable
- [ ] Tests use pytest fixtures for common test data
- [ ] All assertions are clear and specific
- [ ] Edge cases tested:
  - [ ] Empty paths
  - [ ] Single-segment paths
  - [ ] All segments excluded
  - [ ] skip_segments larger than path
  - [ ] max_depth=0
  - [ ] Complex regex patterns
- [ ] Performance test: 1000 extractions complete in <50s
- [ ] Test output is clear and helpful on failures
- [ ] Tests pass locally before code review

#### Test Structure

```python
# pytest test file
import pytest
from skillmeat.core.path_tags import (
    PathTagConfig, ExtractedSegment, PathSegmentExtractor
)

class TestNormalization:
    def test_normalize_number_prefix_with_dash(self):
        """05-data-ai → data-ai"""

    def test_normalize_number_prefix_with_underscore(self):
        """01_foundations → foundations"""

    # ... more normalization tests ...

class TestDepthLimiting:
    def test_max_depth_3_on_5_segment_path(self):
        """Keep only first 3 segments"""

    # ... more depth tests ...

class TestPatternExclusion:
    def test_exclude_pure_numbers(self):
        """Pattern ^\\d+$ excludes pure digit segments"""

    # ... more pattern tests ...

class TestEdgeCases:
    def test_empty_path(self):
        """Empty path returns empty list"""

    # ... more edge case tests ...

# Performance test
@pytest.mark.performance
def test_extraction_performance():
    """1000 extractions complete in <50s (avg <50ms each)"""
```

#### Dependencies

- Task 1.4: PathSegmentExtractor implementation

---

### Task 1.6: Scanner Integration

**Assigned To**: python-backend-engineer
**Model**: Opus
**Estimation**: 5 story points
**Duration**: 8-12 hours
**Status**: Not Started

#### Description

Integrate PathSegmentExtractor into marketplace scanner to automatically extract path segments when new catalog entries are detected.

#### Acceptance Criteria

- [ ] Scanner integration added to `skillmeat/marketplace/scanner.py`
- [ ] When creating new `MarketplaceCatalogEntry`:
  - [ ] Check if source has `path_tag_config` (if not, use defaults)
  - [ ] Call `PathSegmentExtractor.extract(artifact_path)`
  - [ ] Serialize extracted segments to JSON
  - [ ] Store in `entry.path_segments` before saving
- [ ] Extraction JSON structure matches spec:
  - [ ] `raw_path`: Full artifact path
  - [ ] `extracted`: Array of ExtractedSegment objects
  - [ ] `extracted_at`: ISO timestamp of extraction
- [ ] Extraction is non-blocking:
  - [ ] Extraction failures don't prevent artifact detection
  - [ ] Failures logged with context (path, error)
  - [ ] Entry saves even if extraction fails
- [ ] Scanning performance unaffected:
  - [ ] <50ms per entry for extraction
  - [ ] Overall scan time delta <1%
- [ ] Integration tested:
  - [ ] Test with 3+ sample paths
  - [ ] Verify path_segments column populated correctly
  - [ ] Verify JSON validates against schema
- [ ] Error handling:
  - [ ] Malformed paths handled gracefully
  - [ ] Invalid JSON in config caught and logged
  - [ ] Scanning continues even if config is invalid

#### Implementation Notes

**File Location**: `skillmeat/marketplace/scanner.py`

**Integration Point**: In method that creates `MarketplaceCatalogEntry` (typically `_create_catalog_entry()` or similar)

**Pseudo-code**:
```python
# After artifact detection, before saving entry:

# Load config (or use defaults)
config = PathTagConfig()
if source.path_tag_config:
    try:
        config = PathTagConfig.from_json(source.path_tag_config)
    except ValueError as e:
        logger.warning(f"Invalid path_tag_config for source {source.id}: {e}")
        config = PathTagConfig()

# Extract segments if enabled
if config.enabled:
    try:
        extractor = PathSegmentExtractor(config)
        segments = extractor.extract(artifact_path)

        entry.path_segments = json.dumps({
            "raw_path": artifact_path,
            "extracted": [asdict(s) for s in segments],
            "extracted_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to extract path segments for {artifact_path}: {e}")
        # Continue without path_segments; not critical

session.add(entry)
```

#### Dependencies

- Task 1.4: PathSegmentExtractor implementation
- Task 1.3: PathTagConfig and ExtractedSegment dataclasses

---

### Task 1.7: API Schemas for Path Tags

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 3 story points
**Duration**: 3-4 hours
**Status**: Not Started

#### Description

Create Pydantic schemas for path tag API operations (request/response models).

#### Acceptance Criteria

- [ ] Schemas added to `skillmeat/api/schemas/marketplace.py`
- [ ] `PathTagConfigRequest` schema with fields:
  - [ ] `enabled: bool = True`
  - [ ] `skip_segments: list[int] = Field(default_factory=list, description="...")`
  - [ ] `max_depth: int = Field(3, ge=1, le=10, description="...")`
  - [ ] `normalize_numbers: bool = True`
  - [ ] `exclude_patterns: list[str] = Field(default_factory=..., description="...")`
- [ ] `ExtractedSegmentResponse` schema with fields:
  - [ ] `segment: str`
  - [ ] `normalized: str`
  - [ ] `status: Literal["pending", "approved", "rejected", "excluded"]`
  - [ ] `reason: Optional[str] = None`
- [ ] `PathSegmentsResponse` schema with:
  - [ ] `entry_id: str`
  - [ ] `raw_path: str`
  - [ ] `extracted: list[ExtractedSegmentResponse]`
  - [ ] `extracted_at: datetime`
- [ ] `UpdateSegmentStatusRequest` schema with:
  - [ ] `segment: str` (original segment value)
  - [ ] `status: Literal["approved", "rejected"]`
- [ ] `UpdateSegmentStatusResponse` schema with:
  - [ ] `entry_id: str`
  - [ ] `raw_path: str`
  - [ ] `extracted: list[ExtractedSegmentResponse]`
  - [ ] `updated_at: datetime`
- [ ] All schemas include docstrings
- [ ] All fields have Field descriptions for OpenAPI
- [ ] Schemas can be validated with pydantic

#### Implementation Notes

**File Location**: `skillmeat/api/schemas/marketplace.py`

**Example**:
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class ExtractedSegmentResponse(BaseModel):
    """Single extracted path segment with approval status."""
    segment: str = Field(..., description="Original segment from path")
    normalized: str = Field(..., description="Normalized segment value")
    status: Literal["pending", "approved", "rejected", "excluded"] = Field(
        ..., description="Approval status"
    )
    reason: Optional[str] = Field(None, description="Reason if excluded")

class PathSegmentsResponse(BaseModel):
    """All path segments for a catalog entry."""
    entry_id: str = Field(..., description="Catalog entry ID")
    raw_path: str = Field(..., description="Full artifact path")
    extracted: list[ExtractedSegmentResponse] = Field(
        ..., description="Extracted segments with status"
    )
    extracted_at: datetime = Field(..., description="Extraction timestamp")
```

#### Dependencies

- None (pure Pydantic schemas)

---

### Task 1.8: API Endpoints - GET Path Tags

**Assigned To**: python-backend-engineer
**Model**: Opus
**Estimation**: 5 story points
**Duration**: 8-12 hours
**Status**: Not Started

#### Description

Implement GET endpoint to retrieve extracted path segments for a catalog entry.

#### Acceptance Criteria

- [ ] Endpoint created: `GET /api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags`
- [ ] Endpoint implementation:
  - [ ] Accepts `source_id` and `entry_id` as path parameters
  - [ ] Retrieves `MarketplaceSource` and `MarketplaceCatalogEntry` from DB
  - [ ] Parses `path_segments` JSON (if present)
  - [ ] Returns `PathSegmentsResponse` with extracted segments
- [ ] Response codes:
  - [ ] 200: Success (valid entry with path_segments)
  - [ ] 404: Source or entry not found
  - [ ] 400: Entry has no path_segments (not extracted)
- [ ] Error handling:
  - [ ] Invalid source_id: return 404 with helpful message
  - [ ] Invalid entry_id: return 404 with helpful message
  - [ ] Malformed path_segments JSON: return 400 with error detail
  - [ ] All errors logged with context
- [ ] Performance:
  - [ ] Single query fetches both source and entry
  - [ ] Response completes in <200ms
  - [ ] No N+1 queries
- [ ] OpenAPI documentation:
  - [ ] Endpoint tagged with "marketplace"
  - [ ] Summary and description provided
  - [ ] Parameters documented
  - [ ] Response examples included
  - [ ] Error responses documented (404, 400)

#### Implementation Notes

**File Location**: `skillmeat/api/routers/marketplace_sources.py`

**Pattern** (follow existing router patterns in project):
```python
@router.get(
    "/{source_id}/catalog/{entry_id}/path-tags",
    response_model=PathSegmentsResponse,
    summary="Get path-based tag suggestions for catalog entry",
    description="Retrieve extracted path segments and their approval status",
    responses={
        404: {"description": "Source or entry not found"},
        400: {"description": "Entry has no path_segments"},
    }
)
async def get_path_tags(
    source_id: str = Path(..., description="Marketplace source ID"),
    entry_id: str = Path(..., description="Catalog entry ID"),
    manager: MarketplaceManagerDep,  # From dependencies
) -> PathSegmentsResponse:
    """
    Get extracted path segments for a catalog entry.

    Returns all extracted segments with their current approval status.
    Only includes entries that have been scanned with path extraction enabled.

    Raises:
        404: If source or entry not found
        400: If entry has no path_segments (not extracted yet)
    """
```

#### Dependencies

- Task 1.7: API schemas
- Task 1.1-1.2: Database migration and models

---

### Task 1.9: API Endpoints - PATCH Path Tag Status

**Assigned To**: python-backend-engineer
**Model**: Opus
**Estimation**: 5 story points
**Duration**: 8-12 hours
**Status**: Not Started

#### Description

Implement PATCH endpoint to update approval status of a single path segment.

#### Acceptance Criteria

- [ ] Endpoint created: `PATCH /api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags`
- [ ] Endpoint implementation:
  - [ ] Accepts `source_id` and `entry_id` as path parameters
  - [ ] Accepts `UpdateSegmentStatusRequest` in request body
  - [ ] Validates request (segment exists, status is valid)
  - [ ] Updates segment status in `entry.path_segments` JSON
  - [ ] Persists changes to database
  - [ ] Returns updated `PathSegmentsResponse`
- [ ] Status transitions allowed:
  - [ ] `pending` → `approved`
  - [ ] `pending` → `rejected`
  - [ ] `excluded` → (not allowed; return 409)
  - [ ] Cannot double-approve (if already approved, return 409)
- [ ] Response codes:
  - [ ] 200: Success (status updated)
  - [ ] 400: Invalid request (missing fields, invalid status)
  - [ ] 404: Source, entry, or segment not found
  - [ ] 409: Segment already has final status (no double-approval)
- [ ] Error handling:
  - [ ] Invalid segment value: return 404 with message
  - [ ] Status already approved: return 409 with message
  - [ ] Malformed JSON: return 400 with detail
  - [ ] All errors logged
- [ ] Performance:
  - [ ] Single query fetch + update
  - [ ] JSON parsing and update in memory
  - [ ] Response completes in <200ms
- [ ] OpenAPI documentation:
  - [ ] Endpoint tagged with "marketplace"
  - [ ] Request body documented
  - [ ] Response examples included
  - [ ] Error responses documented (404, 400, 409)

#### Implementation Notes

**File Location**: `skillmeat/api/routers/marketplace_sources.py`

**Pattern**:
```python
@router.patch(
    "/{source_id}/catalog/{entry_id}/path-tags",
    response_model=UpdateSegmentStatusResponse,
    summary="Update approval status of a path segment",
    description="Approve or reject a suggested path-based tag",
    responses={
        404: {"description": "Source, entry, or segment not found"},
        409: {"description": "Segment already approved or rejected"},
    }
)
async def update_path_tag_status(
    source_id: str = Path(...),
    entry_id: str = Path(...),
    request: UpdateSegmentStatusRequest = Body(...),
    session: DbSessionDep,
    manager: MarketplaceManagerDep,
) -> UpdateSegmentStatusResponse:
    """
    Update approval status of a single path segment.

    Modifies the status field in path_segments JSON:
    - "approved": Segment will be applied as tag during import
    - "rejected": Segment will not be applied as tag

    Cannot change status of "excluded" segments (filtered by rules).
    Cannot double-approve or double-reject (409 Conflict).
    """
```

**JSON Update Logic**:
```python
# Parse existing path_segments
segments_data = json.loads(entry.path_segments)

# Find and update the segment
for seg in segments_data["extracted"]:
    if seg["segment"] == request.segment:
        if seg["status"] not in ["pending", "excluded"]:
            # Already approved/rejected; cannot change
            raise HTTPException(409, "Segment already has final status")
        seg["status"] = request.status
        break
else:
    # Segment not found
    raise HTTPException(404, "Segment not found in entry")

# Save back to DB
entry.path_segments = json.dumps(segments_data)
session.commit()
```

#### Dependencies

- Task 1.7: API schemas
- Task 1.1-1.2: Database migration and models

---

### Task 1.10: Integration Tests - Scanner to API

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 4 story points
**Duration**: 5-7 hours
**Status**: Not Started

#### Description

Create integration tests verifying the full scanner → path_segments → API flow.

#### Acceptance Criteria

- [ ] Test file created: `tests/marketplace/test_scanner_path_tags.py`
- [ ] Tests for scanner integration:
  - [ ] New catalog entry includes extracted path_segments JSON
  - [ ] path_segments JSON has correct structure (raw_path, extracted, extracted_at)
  - [ ] Segments are extracted correctly for sample paths
  - [ ] Excluded segments have correct status
- [ ] Tests for GET endpoint:
  - [ ] GET returns 200 for valid entry with path_segments
  - [ ] GET returns 404 for missing source or entry
  - [ ] GET returns 400 for entry without path_segments
  - [ ] Response includes all extracted segments
  - [ ] Response timestamps are valid ISO format
- [ ] Tests for PATCH endpoint:
  - [ ] PATCH successfully changes status from pending to approved
  - [ ] PATCH successfully changes status from pending to rejected
  - [ ] PATCH returns 404 for missing segment
  - [ ] PATCH returns 409 if segment already approved
  - [ ] PATCH persists changes to database
  - [ ] Subsequent GET reflects updated status
- [ ] Test data uses realistic paths:
  - [ ] `categories/05-data-ai/ai-engineer.md`
  - [ ] `skills/python/basics.md`
  - [ ] `src/lib/utils.ts`
- [ ] All tests pass and are repeatable
- [ ] Test coverage includes happy path and error cases

#### Test Structure

```python
# Integration test file
import pytest
from skillmeat.cache.models import MarketplaceSource, MarketplaceCatalogEntry
from skillmeat.core.path_tags import PathTagConfig

class TestScannerPathTagIntegration:
    def test_scanner_populates_path_segments(self, db_session):
        """Scanner stores extracted path_segments in new catalog entry"""

    def test_path_segments_json_structure(self, db_session):
        """Extracted JSON has correct schema"""

    def test_get_path_tags_endpoint_success(self, client, db_session):
        """GET returns 200 with PathSegmentsResponse"""

    def test_get_path_tags_endpoint_not_found(self, client):
        """GET returns 404 for missing entry"""

    def test_patch_status_to_approved(self, client, db_session):
        """PATCH successfully updates status to approved"""

    def test_patch_double_approval_conflict(self, client, db_session):
        """PATCH returns 409 if already approved"""
```

#### Dependencies

- Task 1.4: PathSegmentExtractor
- Task 1.6: Scanner integration
- Task 1.8-1.9: API endpoints

---

### Task 1.11: Error Handling & Validation

**Assigned To**: python-backend-engineer
**Model**: Sonnet
**Estimation**: 3 story points
**Duration**: 4-5 hours
**Status**: Not Started

#### Description

Add comprehensive error handling and input validation across extraction, API, and scanner components.

#### Acceptance Criteria

- [ ] **Extraction Errors**:
  - [ ] Invalid regex patterns: raise ValueError with helpful message
  - [ ] Invalid path input: return empty list (not error)
  - [ ] Config deserialization: raise ValueError with JSON detail
- [ ] **API Errors**:
  - [ ] Missing path parameters: return 404 with message
  - [ ] Missing request body: return 400 with message
  - [ ] Invalid status value: return 400 with allowed values
  - [ ] Malformed path_segments JSON: return 500 with log context
  - [ ] All errors include `detail` field for frontend
- [ ] **Scanner Errors**:
  - [ ] Invalid path_tag_config JSON: log warning, use defaults
  - [ ] Extraction failure: log error, continue scan (non-blocking)
  - [ ] Segment serialization failure: log error, skip path_segments
- [ ] **Validation**:
  - [ ] max_depth: 1-10 range
  - [ ] exclude_patterns: max 10 patterns
  - [ ] skip_segments: non-negative integers
  - [ ] segment field in request: non-empty string
  - [ ] status field in request: valid Literal value
- [ ] All validation errors have clear, actionable messages
- [ ] Error cases logged with context (IDs, values, stack trace)
- [ ] No unhandled exceptions bubble up to user

#### Implementation Notes

Examples of error messages:

```
Invalid max_depth: must be between 1 and 10 (got 15)
Missing segment in request body
Segment "data-ai" not found in entry "abc123"
Entry "xyz" has no path_segments (not extracted yet)
Cannot approve segment already in status: "approved"
```

#### Dependencies

- Task 1.4: PathSegmentExtractor
- Task 1.8-1.9: API endpoints

---

### Task 1.12: Documentation & Code Comments

**Assigned To**: documentation-writer
**Model**: Haiku
**Estimation**: 3 story points
**Duration**: 3-4 hours
**Status**: Not Started

#### Description

Document architecture, API endpoints, and implementation details for developers.

#### Acceptance Criteria

- [ ] **Architecture Doc** (new file: `docs/architecture/path-based-tags.md`)
  - [ ] Overview of feature and data flow
  - [ ] Design decisions and rationale
  - [ ] Default extraction rules explained
  - [ ] JSON schema examples for path_segments and path_tag_config
- [ ] **API Documentation** (update `docs/api/marketplace.md`)
  - [ ] New endpoints: GET and PATCH path-tags
  - [ ] Request/response examples
  - [ ] Error codes and handling
  - [ ] OpenAPI spec reference
- [ ] **Code Comments**:
  - [ ] PathSegmentExtractor algorithm documented in docstring
  - [ ] Each API endpoint has clear docstring with examples
  - [ ] Complex regex patterns explained inline
  - [ ] JSON parsing/serialization logic documented
- [ ] **README** (if applicable):
  - [ ] How to use path tag feature (high-level)
  - [ ] Configuration options (Phase 4 reference)
  - [ ] Examples of extracted tags

#### File Locations

- `docs/architecture/path-based-tags.md` (new)
- `docs/api/marketplace.md` (update)
- Docstrings in `skillmeat/core/path_tags.py`, `skillmeat/api/routers/marketplace_sources.py`

#### Dependencies

- All Phase 1 tasks complete

---

## Phase 1 Summary

### Deliverables Checklist

- [ ] Database migration (upgrade + downgrade tested)
- [ ] ORM models updated with new columns
- [ ] PathTagConfig and ExtractedSegment dataclasses
- [ ] PathSegmentExtractor service (>95% test coverage)
- [ ] Scanner integration for automatic extraction
- [ ] API schemas for path tag operations
- [ ] GET path-tags endpoint
- [ ] PATCH path-tags endpoint
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests (scanner → API flow)
- [ ] Error handling and validation
- [ ] Developer documentation

### Definition of Done

Phase 1 is complete when:

1. All 12 tasks have passed code review
2. All acceptance criteria met for each task
3. All tests passing (unit + integration)
4. Performance targets achieved (<50ms extraction, <200ms API)
5. Zero regressions in existing marketplace functionality
6. Documentation complete and reviewed
7. Code follows project style guidelines (black, mypy, flake8)
8. Team approves Phase 1 for Phase 2 start

### Next Phase

Once Phase 1 is complete, proceed to **Phase 2: Frontend Review** to build the user-facing component for reviewing and approving path-based tags.

---

**Generated with Claude Code** - Implementation Planner Orchestrator
