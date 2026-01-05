---
title: Path-Based Tag Extraction
description: Automatic tag extraction from artifact source paths during marketplace scanning
audience: developers
tags:
  - marketplace
  - path-tags
  - tagging
  - artifacts
category: Architecture
status: complete
created: 2025-01-04
updated: 2025-01-04
related:
  - docs/dev/api/marketplace-sources.md
  - docs/dev/architecture/ADR-005-github-marketplace-ingestion.md
---

# Path-Based Tag Extraction

## Overview

Path-Based Tag Extraction automatically extracts organizational metadata from artifact source paths during marketplace scanning. Instead of manually assigning tags, the system analyzes the directory structure of artifacts and suggests meaningful tags based on their location within a repository.

**Example**: An artifact at path `categories/05-data-ai/ai-engineer.md` automatically extracts suggested tags like `categories` and `data-ai` (with the numeric prefix removed).

**Key Features:**
- Automatic extraction of path segments as potential tags
- Configurable rules for filtering and normalization
- User review and approval workflow for extracted segments
- Non-blocking extraction (scanning continues even if extraction fails)
- Support for customization per GitHub source

## Data Flow

### 1. Repository Scan Initialization

When a GitHub source is scanned:
1. User creates or triggers rescan of a marketplace source
2. System loads path tag configuration from the source (or uses defaults)
3. If extraction is enabled, creates a `PathSegmentExtractor` with the configuration

### 2. Artifact Detection

During artifact discovery:
1. GitHubScanner detects artifacts at various paths in the repository
2. For each detected artifact, `PathSegmentExtractor.extract()` is called with the artifact path
3. Path is split and processed according to configuration rules

### 3. Segment Extraction

The extractor processes path segments through these steps:
1. Split path by `/` and remove the filename (last segment)
2. Apply `skip_segments` rule (remove first N segments)
3. Apply `max_depth` rule (keep only first N segments after skip)
4. For each remaining segment:
   - Normalize using `normalize_numbers` rule (e.g., "05-" → "")
   - Check against `exclude_patterns` regex
   - Assign status: "excluded" (if matched) or "pending" (if not matched)
5. Return list of `ExtractedSegment` objects

### 4. Storage

Extracted segments are stored in the `MarketplaceCatalogEntry.path_segments` column as JSON:

```json
{
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "pending",
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "extracted_at": "2025-01-04T15:30:00.000000"
}
```

### 5. User Review Workflow

Users can approve or reject segments via the API:
1. **GET** `/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags` - View all extracted segments
2. **PATCH** `/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags` - Update segment status
3. Status transitions: `pending` → `approved` or `rejected` (one-way; cannot revert)

### 6. Import Integration (Future)

During artifact import:
1. All `approved` segments become tags on the imported artifact
2. `rejected` and `excluded` segments are ignored
3. User can optionally override or add additional tags

## Data Model

### PathTagConfig (Configuration)

Stored as JSON in `MarketplaceSource.path_tag_config`:

```typescript
interface PathTagConfig {
  /**
   * Enable/disable path-based tag extraction for this source
   */
  enabled: boolean;

  /**
   * Indices of path segments to skip (e.g., [0] skips the first segment)
   * Useful for skipping common root directories
   */
  skip_segments: number[];

  /**
   * Maximum number of segments to extract as tags (prevents tag explosion)
   */
  max_depth: number;

  /**
   * Remove numeric prefixes like "05-" or "01_" from segments
   */
  normalize_numbers: boolean;

  /**
   * Regex patterns for segments to exclude from extraction
   * Matched against normalized segment values
   */
  exclude_patterns: string[];
}
```

**JSON Example:**
```json
{
  "enabled": true,
  "skip_segments": [],
  "max_depth": 3,
  "normalize_numbers": true,
  "exclude_patterns": [
    "^\\d+$",
    "^(src|lib|test|docs|examples|__pycache__|node_modules)$"
  ]
}
```

### ExtractedSegment (Data Structure)

Represents a single extracted path segment:

```typescript
interface ExtractedSegment {
  /**
   * Original segment value from path (e.g., "05-data-ai")
   */
  segment: string;

  /**
   * Normalized value after normalization rules (e.g., "data-ai")
   */
  normalized: string;

  /**
   * Processing status
   * - "pending": Awaiting user approval/rejection
   * - "approved": User approved, will become a tag
   * - "rejected": User rejected, will not become a tag
   * - "excluded": Filtered by extraction rules (immutable)
   */
  status: "pending" | "approved" | "rejected" | "excluded";

  /**
   * Reason for exclusion (if applicable)
   */
  reason?: string;
}
```

### PathSegments (Storage Format)

Stored as JSON in `MarketplaceCatalogEntry.path_segments`:

```typescript
interface PathSegments {
  /**
   * Full artifact path in repository
   */
  raw_path: string;

  /**
   * All extracted segments with current approval status
   */
  extracted: ExtractedSegment[];

  /**
   * ISO 8601 timestamp when extraction occurred
   */
  extracted_at: string;
}
```

## Extraction Algorithm

The `PathSegmentExtractor` class implements the core extraction logic.

### Step-by-Step Process

```python
def extract(path: str) -> List[ExtractedSegment]:
    """Extract segments from path according to config rules."""

    # Step 1: Handle edge cases
    if not path or len(path.split("/")) <= 1:
        return []  # No directory segments

    # Step 2: Split path and remove filename
    segments = [s for s in path.split("/") if s]  # Filter empties
    directory_segments = segments[:-1]             # Remove filename

    # Step 3: Apply skip_segments
    skip_indices = set(self._config.skip_segments)
    filtered = [seg for i, seg in enumerate(directory_segments)
                if i not in skip_indices]

    # Step 4: Apply max_depth
    filtered = filtered[:self._config.max_depth]

    # Step 5: Process each segment
    result = []
    for segment in filtered:
        # Normalize
        normalized = self._normalize_segment(segment)

        # Check exclusion
        is_excluded, reason = self._check_exclusion(normalized)

        # Create ExtractedSegment
        result.append(ExtractedSegment(
            segment=segment,
            normalized=normalized,
            status="excluded" if is_excluded else "pending",
            reason=reason,
        ))

    return result
```

### Example Walkthrough

**Input Path:** `skills/05-ui-ux/canvas-design.md`

**Configuration:**
```json
{
  "enabled": true,
  "skip_segments": [],
  "max_depth": 3,
  "normalize_numbers": true,
  "exclude_patterns": ["^\\d+$", "^(src|lib|test|docs|examples)$"]
}
```

**Processing:**

| Step | Operation | Result |
|------|-----------|--------|
| 1 | Split path | `["skills", "05-ui-ux", "canvas-design.md"]` |
| 2 | Remove filename | `["skills", "05-ui-ux"]` |
| 3 | Apply skip_segments | `["skills", "05-ui-ux"]` (no skip) |
| 4 | Apply max_depth | `["skills", "05-ui-ux"]` (2 <= 3) |
| 5a | Normalize "skills" | `"skills"` (no prefix) |
| 5b | Check exclusion | Not matched, `status="pending"` |
| 6a | Normalize "05-ui-ux" | `"ui-ux"` (prefix removed) |
| 6b | Check exclusion | Not matched, `status="pending"` |

**Output:**
```python
[
    ExtractedSegment(segment="skills", normalized="skills", status="pending"),
    ExtractedSegment(segment="05-ui-ux", normalized="ui-ux", status="pending"),
]
```

## Default Configuration

The default configuration provides sensible defaults for most repositories:

| Setting | Value | Rationale |
|---------|-------|-----------|
| `enabled` | `true` | Feature active by default |
| `skip_segments` | `[]` | Don't skip any path segments by default |
| `max_depth` | `3` | Extract up to 3 levels of path segments to prevent tag explosion |
| `normalize_numbers` | `true` | Clean up numbered prefixes like "01-", "05-", etc. for readability |
| `exclude_patterns` | See below | Skip generic directories and pure numbers |

**Default Exclude Patterns:**

```python
[
    r"^\d+$",                                      # Pure numbers: "01", "123"
    r"^(src|lib|test|docs|examples|__pycache__|node_modules)$"  # Common directories
]
```

## API Endpoints

### GET /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags

Retrieve extracted path segments and their approval status for a catalog entry.

**Parameters:**
- `source_id` (path): Marketplace source identifier
- `entry_id` (path): Catalog entry identifier

**Response:** `PathSegmentsResponse`

```typescript
{
  "entry_id": "cat_canvas_design",
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "pending",
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "extracted_at": "2025-01-04T15:30:00Z"
}
```

**Errors:**
- `404 Not Found`: Source or entry not found
- `400 Bad Request`: Entry has no path_segments (not extracted yet)
- `500 Internal Server Error`: Malformed path_segments JSON

**Example:**
```bash
curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/catalog/cat-def456/path-tags" \
  -H "Content-Type: application/json"
```

### PATCH /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags

Update approval status of a path segment.

**Parameters:**
- `source_id` (path): Marketplace source identifier
- `entry_id` (path): Catalog entry identifier

**Request:** `UpdateSegmentStatusRequest`

```typescript
{
  "segment": "ui-ux",           // Original segment value to update
  "status": "approved"          // "approved" or "rejected"
}
```

**Response:** `UpdateSegmentStatusResponse`

```typescript
{
  "entry_id": "cat_canvas_design",
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "approved",      // Updated status
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "updated_at": "2025-01-04T15:35:00Z"
}
```

**Errors:**
- `404 Not Found`: Source, entry, or segment not found
- `409 Conflict`: Segment already approved/rejected or is excluded
- `400 Bad Request`: Entry has no path_segments
- `500 Internal Server Error`: Malformed path_segments JSON

**Status Transition Rules:**
- Only `pending` segments can be updated
- Cannot change `excluded` segments (filtered by rules)
- Cannot double-approve/reject (409 Conflict if already changed)

**Examples:**

Approve a segment:
```bash
curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src-abc123/catalog/cat-def456/path-tags" \
  -H "Content-Type: application/json" \
  -d '{"segment": "ui-ux", "status": "approved"}'
```

Reject a segment:
```bash
curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src-abc123/catalog/cat-def456/path-tags" \
  -H "Content-Type: application/json" \
  -d '{"segment": "canvas-design", "status": "rejected"}'
```

## Design Decisions

### 1. Text Columns for JSON Storage

**Decision**: Store path_segments as TEXT in SQLite rather than native JSONB

**Rationale:**
- SQLite doesn't have native JSONB type (only JSON functions in recent versions)
- Need to support older SQLite versions (3.9+) in existing installations
- TEXT column with JSON validation is more portable
- Query performance is acceptable for small documents

**Implementation:**
- Validate JSON structure in Python before storage
- Store as minified JSON string to save space
- Parse and validate on retrieval

### 2. Pre-Compiled Regex Patterns

**Decision**: Compile exclude_patterns regex once during initialization

**Rationale:**
- Avoid re-compiling regex for every extraction call
- Significant performance improvement for many artifacts
- Trade-off: slightly higher memory usage (acceptable for typical pattern counts)

**Implementation:**
```python
def __init__(self, config: PathTagConfig):
    self._compiled_patterns: list[re.Pattern[str]] = []
    for pattern in config.exclude_patterns:
        try:
            self._compiled_patterns.append(re.compile(pattern))
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
```

### 3. Non-Blocking Extraction

**Decision**: Extract path segments asynchronously; scanner continues if extraction fails

**Rationale:**
- Path extraction is secondary to artifact detection
- Prevents entire scan failure due to malformed JSON or regex errors
- Allows graceful degradation: some artifacts get tags, others don't
- Errors are logged but don't interrupt the scanning process

**Implementation:**
```python
try:
    segments = extractor.extract(artifact.path)
    path_segments_json = json.dumps({...})
except Exception as e:
    logger.error(f"Failed to extract path segments: {e}")
    # Continue without path_segments; extraction is non-blocking
```

### 4. Status Immutability After Approval

**Decision**: Once `pending` → `approved`/`rejected`, cannot revert

**Rationale:**
- Prevents accidental reversion of user decisions
- Maintains audit trail (timestamp of decision)
- Simpler state machine (no undo/redo complexity)
- Users can delete and re-scan source if reversal needed

**Implementation:**
```python
# Cannot double-approve/reject
if seg["status"] in ["approved", "rejected"]:
    raise HTTPException(409, f"Segment already has status '{seg['status']}'")
```

### 5. Excluded Segments Are Immutable

**Decision**: "excluded" segments (filtered by rules) cannot be approved/rejected

**Rationale:**
- Rules exist for good reasons (e.g., excluding "src" directory)
- Prevents users from circumventing configuration
- If user disagrees with rule, they should modify source configuration
- Simplifies state management

**Implementation:**
```python
if seg["status"] == "excluded":
    raise HTTPException(409, f"Cannot change status of excluded segment")
```

## Configuration Examples

### Example 1: Anthropic Skills Repository

```json
{
  "enabled": true,
  "skip_segments": [0],        // Skip "skills" root directory
  "max_depth": 2,
  "normalize_numbers": true,
  "exclude_patterns": [
    "^\\d+$",
    "^(src|lib|test|docs|examples|__pycache__|node_modules)$"
  ]
}
```

**Path:** `skills/05-data-ai/csv-analyzer`
**Result:** `["data-ai", "csv-analyzer"]`

### Example 2: Nested Organization Structure

```json
{
  "enabled": true,
  "skip_segments": [],         // Keep all levels
  "max_depth": 3,
  "normalize_numbers": false,  // Preserve numeric prefixes
  "exclude_patterns": [
    "^\\d+$",
    "^(test|build|dist)$"
  ]
}
```

**Path:** `categories/01-tools/02-data-processing/data-cleaner`
**Result:** `["categories", "01-tools", "02-data-processing"]`

### Example 3: Single-Level Tagging

```json
{
  "enabled": true,
  "skip_segments": [],
  "max_depth": 1,              // Only first level
  "normalize_numbers": true,
  "exclude_patterns": [
    "^\\d+$",
    "^(src|lib|test|docs|examples)$"
  ]
}
```

**Path:** `categories/data-science/ml-models/transformer`
**Result:** `["categories"]`

## Error Handling

### Invalid Regex Pattern

If a exclude_pattern is invalid regex, extraction fails at initialization:

```python
try:
    config = PathTagConfig.from_json('{"exclude_patterns": ["[invalid"]}')
except ValueError as e:
    # ValueError: Invalid regex pattern '[invalid': unterminated character set
```

### Malformed path_segments JSON

If stored JSON is corrupted, API returns 500:

```python
try:
    data = json.loads(entry.path_segments)
except json.JSONDecodeError:
    raise HTTPException(500, "Internal error parsing path_segments")
```

### Empty or No Segments

Returns empty list for single-file artifacts:

```python
# Input: "file.md" (no parent directory)
extractor.extract("file.md")  # Returns []
```

## Performance Considerations

### Extraction Performance

For typical paths (3-5 segments):
- Regex matching: < 1ms per segment
- Normalization: < 0.1ms per segment
- Total per artifact: 1-5ms

For 1000 artifacts:
- Sequential extraction: ~3 seconds total
- Acceptable overhead for scanning process

### Storage Overhead

Typical path_segments JSON:
- Minimal path (2 segments): ~250 bytes
- Complex path (5 segments): ~600 bytes
- Average per artifact: ~400 bytes

For 1000 artifacts: ~400KB total (negligible)

### Query Performance

- Extraction is stored but not queried frequently
- No full-text search on path segments (future enhancement)
- No filtering by path segment status in default queries

## Future Enhancements

### 1. Bulk Status Update

Allow approving/rejecting multiple segments at once:

```
PATCH /marketplace/sources/{source_id}/catalog/{entry_id}/path-tags
{
  "updates": [
    {"segment": "ui-ux", "status": "approved"},
    {"segment": "canvas-design", "status": "approved"}
  ]
}
```

### 2. Global Configuration

Apply path tag config to all sources:

```
PATCH /marketplace/path-tags/config
{
  "enabled": true,
  "max_depth": 3,
  ...
}
```

### 3. Tag Application During Import

Automatically apply approved segments as tags during artifact import.

### 4. Full-Text Search on Tags

Search artifacts by approved path-based tags:

```
GET /marketplace/sources/{source_id}/artifacts?tags=data-ai&tags=python
```

### 5. Regex Testing UI

UI tool for testing custom regex patterns before saving:

```
POST /marketplace/path-tags/test-pattern
{
  "pattern": "^(src|lib)$",
  "test_values": ["src", "lib", "other"]
}
```

## References

- **Core Implementation:** `skillmeat/core/path_tags.py`
- **API Schemas:** `skillmeat/api/schemas/marketplace.py` (ExtractedSegmentResponse, etc.)
- **Router Implementation:** `skillmeat/api/routers/marketplace_sources.py` (endpoints)
- **Database Model:** `skillmeat/cache/models.py` (MarketplaceCatalogEntry.path_segments)
