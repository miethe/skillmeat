# Artifact Detection and Indexing System Analysis

**Date**: 2026-01-24
**Status**: Comprehensive analysis of current implementation
**Focus**: Detection flow, metadata capture, database persistence, and indexing mechanisms

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Artifact Detection System](#artifact-detection-system)
3. [Marketplace Source Model](#marketplace-source-model)
4. [Indexing Flow](#indexing-flow)
5. [Database Schema](#database-schema)
6. [Current Limitations & Integration Points](#current-limitations)

---

## System Overview

The artifact detection and indexing system consists of four interconnected layers:

```
GitHub Repository
       ↓
   GitHubScanner (fetch tree, rate limit handling)
       ↓
   HeuristicDetector (8-signal scoring, 0-100 confidence)
       ↓
   Frontmatter Extraction (batch or per-artifact)
       ↓
   MarketplaceCatalogEntry (database persistence)
       ↓
   Cross-Source Search (FTS5 indexing)
```

---

## Artifact Detection System

### 1. Baseline Detection Module (`skillmeat/core/artifact_detection.py`)

**Purpose**: Canonical source of truth for artifact type detection

#### ArtifactType Enum

Located in: `skillmeat/core/artifact_detection.py` (lines 66-126)

```python
class ArtifactType(str, Enum):
    # Primary artifact types (deployable)
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    MCP = "mcp"

    # Context entity types (non-deployable)
    PROJECT_CONFIG = "project_config"
    SPEC_FILE = "spec_file"
    RULE_FILE = "rule_file"
    CONTEXT_FILE = "context_file"
    PROGRESS_TEMPLATE = "progress_template"
```

**Key Features**:
- Extends both `str` and `Enum` for JSON serialization
- Methods: `primary_types()`, `context_types()`
- Used across all detection contexts (local, GitHub, validation)

#### DetectionResult Dataclass

Stores comprehensive detection metadata:

```python
@dataclass
class DetectionResult:
    artifact_type: ArtifactType
    name: str
    path: str
    container_type: str
    detection_mode: Literal["strict", "heuristic"]
    confidence: int (0-100)
    manifest_file: Optional[str]
    metadata: Dict[str, Any]
    detection_reasons: List[str]
    deprecation_warning: Optional[str]

    @property
    def is_confident(self) -> bool:  # confidence >= 80
    @property
    def is_strict(self) -> bool:  # detection_mode == "strict"
```

#### ArtifactSignature Registry

Maps artifact type → detection rules:

```python
ARTIFACT_SIGNATURES: Dict[ArtifactType, ArtifactSignature] = {
    ArtifactType.SKILL: ArtifactSignature(
        artifact_type=ArtifactType.SKILL,
        container_names={"skills", "skill", "claude-skills"},
        is_directory=True,
        requires_manifest=True,
        manifest_names={"SKILL.md", "skill.md"},
        allowed_nesting=False,
    ),
    ArtifactType.COMMAND: ArtifactSignature(
        artifact_type=ArtifactType.COMMAND,
        container_names={"commands", "command", "claude-commands"},
        is_directory=False,
        requires_manifest=False,
        manifest_names={"COMMAND.md", "command.md"},
        allowed_nesting=True,  # Can be nested in subdirs
    ),
    # ... more types
}
```

#### Detection Functions

**`infer_artifact_type(path: Path) → Optional[ArtifactType]`**
- Priority 1: Check for manifest files in directory
- Priority 2: Check ancestor directory names (container hints)
- Priority 3: Check file extension patterns (for .md files)
- Supports nesting for command/agent types

**`detect_artifact(path: Path, container_type: Optional[str], mode: Literal["strict", "heuristic"]) → DetectionResult`**
- Comprehensive detection with confidence scoring
- Strict mode: Requires 70+ confidence or raises DetectionError
- Heuristic mode: Returns best guess with 0-100 confidence
- Builds detection reasons for transparency

#### Confidence Scoring (detect_artifact)

```
Process:
1. Container type hint (+30)          # If provided
2. Path inference (+40)               # From parent dirs/manifest names
3. Manifest file detection (+40)      # Definitive marker
4. Structure validation (+20/-20)     # Is it a dir/file as expected?
5. Manifest requirement check (-30)   # If required but missing

Strict mode: Must achieve 70+ confidence or fail
Heuristic mode: Returns clamped 0-100 score
```

**Example Detection Flow**:
```
Path: "./skills/my-skill"
  → Container matches: +30
  → Parent "skills" in CONTAINER_TO_TYPE: +40
  → SKILL.md found: +40
  → Structure: directory ✓: +20
  → Total: 130 → clamped 100% (strict mode)
```

---

### 2. Marketplace Heuristic Detector (`skillmeat/core/marketplace/heuristic_detector.py`)

**Purpose**: GitHub-specific detection layer on top of baseline detection

#### Two-Layer Architecture

```
Baseline Signals (from artifact_detection module):
  - dir_name: 10 pts           → Container directory matching
  - manifest: 20 pts           → SKILL.md, COMMAND.md presence
  - skill_manifest_bonus: 40   → Extra for SKILL.md

Marketplace Signals (GitHub-specific):
  - extensions: 5 pts          → Expected file types present
  - parent_hint: 15 pts        → Ancestor paths contain "claude", "anthropic"
  - frontmatter: 15 pts        → Documentation file presence
  - container_hint: 25 pts     → Detected type matches parent container
  - frontmatter_type: 30 pts   → Explicit type in YAML frontmatter

MAX_RAW_SCORE = 160
Final confidence = normalize(raw_score) → 0-100 scale
```

#### DetectionConfig

```python
@dataclass
class DetectionConfig:
    dir_patterns: Dict[ArtifactType, Set[str]]
    manifest_files: Dict[ArtifactType, Set[str]]
    expected_extensions: Set[str] = {".md", ".py", ".ts", ".js", ".json", ".yaml", ".yml"}
    min_confidence: int = 30
    max_depth: int = 10
    depth_penalty: int = 1
    # Score weights...
```

#### HeuristicDetector Class

```python
class HeuristicDetector:
    def __init__(
        self,
        config: Optional[DetectionConfig] = None,
        enable_frontmatter_detection: bool = False,
        manual_mappings: Optional[Dict[str, str]] = None,
    ):
```

**Key Methods**:
- `analyze_paths(file_paths, base_url, detected_sha) → List[DetectedArtifact]`
  - Main entry point for scanning file trees
  - Returns list of detected artifacts with confidence scores

- `score_directory_v2(files, artifact_path) → Tuple[ArtifactType, int, Dict]`
  - Two-layer detection: baseline + marketplace signals
  - Returns (type, confidence, score_breakdown)

---

## Marketplace Source Model

**File**: `skillmeat/cache/models.py` (lines 1182-1514)

### MarketplaceSource Fields

```python
class MarketplaceSource(Base):
    # Core identification
    id: str (primary key)
    repo_url: str (unique)
    owner: str
    repo_name: str
    ref: str (default: "main")
    root_hint: Optional[str]  # ← Artifacts root path within repo

    # User-provided metadata
    description: Optional[str] (500 chars)
    notes: Optional[str] (2000 chars)

    # GitHub-fetched metadata
    repo_description: Optional[str] (2000 chars)
    repo_readme: Optional[str] (up to 50KB)

    # Tags and categorization
    tags: Optional[str]  # JSON: ["tag1", "tag2", ...]
    auto_tags: Optional[str]  # JSON: {extracted: [{value, normalized, status, source}]}

    # Artifact mapping
    manual_map: Optional[str]  # JSON: {"path/to/artifact": "skill"}

    # Detection settings
    enable_frontmatter_detection: bool (default: False)
    indexing_enabled: Optional[bool]  # Tri-state:
                                       # None = use global mode
                                       # True = enable regardless
                                       # False = disable regardless

    # Path-based tagging
    path_tag_config: Optional[str]  # JSON: PathTagConfig

    # Single artifact mode
    single_artifact_mode: bool (default: False)
    single_artifact_type: Optional[str]  # "skill", "command", etc.

    # Sync status
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    scan_status: str  # "pending" | "scanning" | "success" | "error"
    artifact_count: int (cached count)
    counts_by_type: Optional[str]  # JSON: {"skill": 5, "command": 3}

    # Relationships
    entries: List[MarketplaceCatalogEntry]
```

### Key Model Methods

**`get_manual_map_dict() → Optional[Dict[str, Any]]`**
- Parse manual_map JSON
- Used during scanning to override artifact types

**`get_counts_by_type_dict() → Dict[str, int]`**
- Returns artifact type distribution
- Updated after each scan

**`set_counts_by_type_dict(counts_dict: Dict[str, int])`**
- Serialize and store type counts

**`get_auto_tags_dict() → Optional[Dict[str, Any]]`**
- Parse auto_tags from GitHub topics
- Structure: `{"extracted": [{"value", "normalized", "status", "source"}]}`

---

## Indexing Flow

### Complete Scan Flow

**Entry Point**: `POST /marketplace/sources/{id}/rescan` or `POST /marketplace/sources` (create + auto-scan)

**Handler**: `_perform_scan()` in `skillmeat/api/routers/marketplace_sources.py` (lines 937-1226)

```
1. Update source.scan_status = "scanning"
   ↓
2. Check single_artifact_mode
   ├─ Yes: Create synthetic DetectedArtifact with 100% confidence
   └─ No: Call scanner.scan_repository()
   ↓
3. GitHubScanner.scan_repository()
   ├─ Fetch repository tree via GitHub API
   ├─ Apply HeuristicDetector to file tree
   ├─ Return ScanResultDTO with detected artifacts
   └─ Handle deduplication (get_existing_collection_hashes)
   ↓
4. Load PathTagConfig for path-based tag extraction
   ↓
5. For each detected artifact:
   ├─ Extract path segments (if extractor enabled)
   ├─ Extract frontmatter (if indexing_enabled):
   │  ├─ Use batch clone for skills >= BATCH_CLONE_THRESHOLD (3+)
   │  └─ Otherwise per-artifact API calls
   ├─ Create MarketplaceCatalogEntry
   └─ Collect into new_entries
   ↓
6. Atomic transaction:
   ├─ Update source status: success/error
   ├─ Update counts_by_type
   ├─ Merge new_entries with existing catalog:
   │  ├─ Preserve import metadata
   │  ├─ Track updated_imports
   │  └─ Track preserved_count
   └─ Commit
   ↓
7. Return ScanResultDTO with statistics
```

### Frontmatter Extraction

Located in: `skillmeat/api/routers/marketplace_sources.py` (lines 550-920)

#### Per-Artifact Extraction: `_extract_frontmatter_for_artifact()`

```python
def _extract_frontmatter_for_artifact(
    scanner: GitHubScanner,
    source: MarketplaceSource,
    artifact: DetectedArtifact,
) -> Dict[str, Any]:
    """Extract frontmatter for single artifact via GitHub API.

    Process:
    1. Build path to manifest file (SKILL.md, COMMAND.md, etc.)
    2. Fetch content via GitHub API
    3. Parse YAML frontmatter
    4. Extract: title, description, tags
    5. Build search_text from combined fields
    """
```

**Extracted Metadata**:
```python
{
    "title": str (max 200 chars),           # From frontmatter.title or .name
    "description": str,                      # From frontmatter.description
    "search_tags": List[str],                # From frontmatter.tags (parsed)
    "search_text": str,                      # Combined: name + title + desc + tags
}
```

#### Batch Extraction: `_extract_frontmatter_batch()`

```python
def _extract_frontmatter_batch(
    source: MarketplaceSource,
    artifacts: List[DetectedArtifact],  # Pre-filtered to skills
) -> Dict[str, Dict[str, Any]]:
    """Extract frontmatter for multiple artifacts using git sparse clone.

    Optimization: Single git clone fetches all SKILL.md files at once.
    Much more efficient than N individual API calls.

    Process:
    1. Check artifact count >= BATCH_CLONE_THRESHOLD (3)
    2. If yes, use sparse clone:
       - git init
       - Configure sparse-checkout for **/SKILL.md
       - git fetch --depth=1 --filter=blob:none
       - git checkout FETCH_HEAD
    3. Read SKILL.md files from disk
    4. Extract frontmatter for each
    5. Return Dict[name → metadata]

    Returns empty results on clone failure; non-blocking.
    """
```

**Threshold**: `BATCH_CLONE_THRESHOLD = 3` (lines 651-652)

### Frontmatter Parsing

Located in: `skillmeat/utils/metadata.py`

Uses YAML frontmatter extraction utility (`extract_frontmatter(content: str) → Dict`).

**Frontmatter Format** (SKILL.md example):

```markdown
---
title: My Skill
description: Does something useful
tags: [ai, claude, automation]
name: my-skill  # Fallback for title
---

# Skill Description

Content here...
```

---

## Database Schema

### MarketplaceCatalogEntry Table

**File**: `skillmeat/cache/models.py` (lines 1516-1728)

```python
class MarketplaceCatalogEntry(Base):
    # Primary key
    id: str (UUID)

    # Source relationship
    source_id: str (FK to marketplace_sources.id)

    # Core detection fields
    artifact_type: str
    name: str
    path: str
    upstream_url: str (full GitHub URL)

    # Version tracking
    detected_version: Optional[str]
    detected_sha: Optional[str] (commit SHA at detection)
    detected_at: datetime (when detected)

    # Confidence scoring
    confidence_score: int (0-100)
    raw_score: Optional[int] (before normalization)
    score_breakdown: Optional[JSON] (signal details)

    # Import tracking
    status: str  # "new" | "updated" | "removed" | "imported" | "excluded"
    import_date: Optional[datetime]
    import_id: Optional[str]

    # Exclusion tracking
    excluded_at: Optional[datetime]
    excluded_reason: Optional[str] (max 500 chars)

    # Path-based tagging
    path_segments: Optional[str]  # JSON: {raw_path, extracted, extracted_at}

    # Cross-source search fields (populated from frontmatter)
    title: Optional[str] (max 200 chars)
    description: Optional[str] (unlimited)
    search_tags: Optional[str]  # JSON: ["tag1", "tag2", ...]
    search_text: Optional[str]  # Concatenated for FTS

    # Additional metadata
    metadata_json: Optional[str]  # JSON: {content_hash, single_artifact_mode, ...}

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Foreign key relationship
    source: MarketplaceSource
```

### Indexes

```python
__table_args__ = (
    CheckConstraint("artifact_type IN (...)"),
    CheckConstraint("status IN ('new', 'updated', 'removed', 'imported', 'excluded')"),
    CheckConstraint("confidence_score >= 0 AND confidence_score <= 100"),
)

# Implicit indexes from relationships:
# - idx_catalog_entries_source_id
# - idx_catalog_entries_status
# - idx_catalog_entries_type
# - idx_catalog_entries_upstream_url (for deduplication)
# - idx_catalog_entries_source_status
```

### FTS5 Integration (Search)

**Migration**: `20260124_1200_add_fts5_catalog_search.py`

Creates virtual FTS5 table for full-text search:

```sql
CREATE VIRTUAL TABLE marketplace_catalog_fts USING fts5(
    id UNINDEXED,
    search_text,
    search_tags,
    artifact_type,
    name,
    -- Indexed by default for efficiency
    content='marketplace_catalog_entries',
    content_rowid='id'
);
```

**Search Fields** (indexed in order of importance):
1. `search_text` - Combined title + description + tags + name
2. `search_tags` - JSON array of tags
3. `artifact_type` - Filter by type
4. `name` - Artifact name

---

## Current Limitations

### 1. No Explicit "Artifacts Root" Field

**Issue**: While `root_hint` exists, there's no formal concept of detecting/storing the "artifacts root" directory.

**Current Behavior**:
- `root_hint`: User-provided subdirectory within repo (optional)
- Single artifact mode: Treats entire repo as one artifact
- Normal mode: Scans all subdirectories, applies heuristics

**Missing**:
- Automatic detection of artifact container root (e.g., "skills/", "components/")
- Metadata about which container types are present
- Confidence that scanning started from the right root

### 2. Metadata Capture

**Currently Captured**:
- From detection: artifact_type, confidence_score, path, name, raw_score, score_breakdown
- From GitHub: repo_description, repo_readme, auto_tags
- From frontmatter: title, description, search_tags, search_text
- Path segments: raw_path, extracted segments, extraction status

**Missing from Detection Phase**:
- Detection reasons (only stored in logging)
- Detection mode (strict vs heuristic)
- Manifest file path (detected but not persisted)
- Alternative artifact names/aliases from frontmatter
- Detection signals breakdown per signal (only stored as score_breakdown JSON)

### 3. Indexing Control

**Current State**:
- Tri-state `indexing_enabled` field (None/True/False)
- Only controls frontmatter extraction
- No control over:
  - Which fields to index
  - Search ranking/weighting
  - FTS5 parameters (BM25 weights, phrase search)

**Gap**:
- No per-source search configuration
- All sources use same FTS5 parameters

### 4. Batch Processing Threshold

**Current**: `BATCH_CLONE_THRESHOLD = 3` (hard-coded)

**Limitation**:
- Not configurable per-source
- Fixed at module level
- No adaptive threshold based on repo size

### 5. Deduplication

**Current**: Content hash-based deduplication via `get_existing_collection_hashes()`

**Method**:
- Query existing catalog entries for content_hash in metadata_json
- Uses SQLite `json_extract()` for performance
- Filters out excluded entries

**Gap**:
- No duplicate detection across sources
- No URL-based deduplication (only content-based)
- No versioning/update tracking across sources

---

## Integration Points

### With GitHubScanner

```python
class GitHubScanner:
    def scan_repository(
        self,
        owner: str,
        repo: str,
        ref: str,
        root_hint: Optional[str],
        session: Optional[Session],
        manual_mappings: Optional[Dict[str, str]],
    ) -> ScanResultDTO:
        """Fetch tree, apply heuristics, return detected artifacts."""
```

**Returns**: `ScanResultDTO` with:
- List of `DetectedArtifact` instances
- Metadata: scan_duration_ms, artifacts_found, errors
- Deduplication metadata (preserved/updated imports)

### With PathSegmentExtractor

```python
class PathSegmentExtractor:
    def extract(self, path: str) -> List[PathSegment]:
        """Extract meaningful segments from artifact path."""
```

**Used for**: Path-based tag extraction and approval workflow

### With MarketplaceTransactionHandler

```python
class MarketplaceTransactionHandler:
    def scan_update_transaction(
        self, source_id: str
    ) -> TransactionContext:
        """Atomic transaction for scan updates."""
```

**Provides**: Atomic source + catalog entry updates

### With FrontmatterExtraction

**Per-artifact**: Uses GitHub API to fetch manifest files

**Batch**: Uses git sparse clone for efficiency

---

## Key Data Flows

### Detection Data Flow

```
GitHub Tree (paths only)
    ↓
HeuristicDetector.analyze_paths()
    ├─ Map each path to DetectedArtifact
    ├─ Score with 8 signals
    ├─ Normalize confidence 0-100
    └─ Return list with reasons
    ↓
GitHubScanner.scan_repository()
    ├─ Handle deduplication
    ├─ Merge results
    └─ Return ScanResultDTO
    ↓
_perform_scan() (router)
    ├─ Extract frontmatter (batch or per-artifact)
    ├─ Extract path segments
    ├─ Create MarketplaceCatalogEntry objects
    └─ Store in database atomically
    ↓
MarketplaceCatalogEntry (persisted)
    ├─ Source + artifacts linked
    ├─ Search fields populated
    └─ Ready for FTS5 indexing
```

### Search Data Flow

```
MarketplaceCatalogEntry (database)
    ├─ title
    ├─ description
    ├─ search_tags (JSON)
    └─ search_text (concatenated)
    ↓
FTS5 Virtual Table (indexed)
    ↓
Search Query → BM25 Ranking
    ↓
Results (ranked by relevance)
```

---

## Summary

The artifact detection and indexing system is well-architected with:

✓ **Strengths**:
- Two-layer detection (baseline + marketplace-specific)
- Comprehensive confidence scoring (8 signals)
- Efficient batch frontmatter extraction
- Atomic transaction handling
- FTS5 integration for search

⚠ **Gaps**:
- No explicit "artifacts root" detection/persistence
- Limited detection metadata capture
- Hard-coded batch thresholds
- No per-source search configuration
- Limited cross-source deduplication

