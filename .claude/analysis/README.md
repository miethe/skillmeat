# Artifact Detection & Indexing Analysis

**Complete analysis of how SkillMeat detects, indexes, and searches for Claude Code artifacts across GitHub repositories.**

## Quick Start

Start here if you're new to understanding the artifact detection system:

1. **Overview**: Read [ANALYSIS-SUMMARY.md](ANALYSIS-SUMMARY.md) (5 min read)
2. **Deep Dive**: Read [artifact-detection-system.md](artifact-detection-system.md) (20 min read)
3. **Code Deep Dive**: Use [detection-code-reference.md](detection-code-reference.md) for line-by-line traces

## Document Guide

### [ANALYSIS-SUMMARY.md](ANALYSIS-SUMMARY.md)
**Purpose**: Executive summary of findings
**Audience**: Project leads, architects, developers planning extensions
**Content**:
- System architecture overview
- Quick reference on all components
- Integration point diagram
- Metadata captured vs persisted
- Current limitations
- Extension opportunities

### [artifact-detection-system.md](artifact-detection-system.md)
**Purpose**: Comprehensive technical reference
**Audience**: Developers implementing detection features
**Content**:
- Baseline detection module (ArtifactType, DetectionResult, signatures)
- Marketplace heuristic detector (2-layer architecture, 8 signals)
- MarketplaceSource model (30+ fields)
- Complete indexing flow (with line numbers)
- Database schema and indexes
- Frontmatter extraction strategies
- FTS5 search integration
- Limitations and gaps

### [detection-code-reference.md](detection-code-reference.md)
**Purpose**: Developer quick reference with code locations
**Audience**: Developers debugging detection, tracing code flow
**Content**:
- File locations and key classes
- Workflow traces with line numbers
- Data structure definitions
- Signal weights and configuration
- Error handling patterns
- Performance notes and bottlenecks

## Key Concepts

### Three Detection Layers

1. **Baseline Detection** (`core/artifact_detection.py`)
   - Universal, works everywhere (local, GitHub, etc.)
   - Type inference from paths and manifests
   - 0-100 confidence scoring

2. **Marketplace Heuristics** (`core/marketplace/heuristic_detector.py`)
   - GitHub-specific signals (8 scoring vectors)
   - Layers on top of baseline
   - Final 0-100 confidence score

3. **Frontmatter Indexing** (`api/routers/marketplace_sources.py`)
   - Extract title, description, tags
   - Build search_text for FTS
   - Two strategies: batch (git clone) or per-artifact (API)

### Metadata Flow

```
GitHub Repository
    ↓ (file tree)
GitHubScanner
    ↓ (detected artifacts)
HeuristicDetector (8-signal scoring)
    ↓ (raw artifacts with confidence)
_perform_scan()
    ├─ Extract frontmatter (batch or per-artifact)
    ├─ Extract path segments
    └─ Create MarketplaceCatalogEntry
    ↓
Database persistence
    ├─ Detection metadata (type, confidence, raw_score)
    ├─ Search metadata (title, description, tags)
    └─ Path metadata (segments with approval status)
    ↓
FTS5 search index
    ├─ search_text (BM25 ranked)
    ├─ search_tags (exact match)
    ├─ artifact_type (filter)
    └─ name (filter)
```

## Finding Information

### "I want to understand..."

| Question | Document | Section |
|----------|----------|---------|
| How does detection work? | artifact-detection-system.md | Section 2 (Artifact Detection System) |
| What's a MarketplaceSource? | artifact-detection-system.md | Section 3 (Marketplace Source Model) |
| How is a scan performed? | artifact-detection-system.md | Section 4 (Indexing Flow) |
| What gets stored in database? | artifact-detection-system.md | Section 5 (Database Schema) |
| Where's the code for X? | detection-code-reference.md | First 3 tables (File Locations) |
| Line-by-line of _perform_scan? | detection-code-reference.md | Section "Scan Operation" |
| How does frontmatter extraction work? | detection-code-reference.md | Sections 7-8 |
| What are the signal weights? | detection-code-reference.md | "Signal Weights Reference" |
| What are the current gaps? | ANALYSIS-SUMMARY.md | "Current Limitations" |
| What can we extend? | ANALYSIS-SUMMARY.md | "Extension Opportunities" |

### File Navigation

**If you're working on...**

- **Detection accuracy**: See `core/artifact_detection.py`, `core/marketplace/heuristic_detector.py`
- **Scanning performance**: See `core/marketplace/github_scanner.py`, `api/routers/marketplace_sources.py` (frontmatter extraction)
- **Search functionality**: See `cache/models.py` (MarketplaceCatalogEntry), FTS5 migration
- **Database layer**: See `cache/models.py` (models), `cache/repositories.py` (data access)
- **API endpoints**: See `api/routers/marketplace_sources.py` (_perform_scan, related endpoints)

## Key Statistics

### Detection System

- **ArtifactType**: 10 types (5 primary, 5 context entities)
- **Detection Signals**: 8 scoring vectors
- **Max Raw Score**: 160 (normalized to 100)
- **Minimum Confidence**: 30 (configurable, default)
- **Manifest Files**: 5+ types (SKILL.md, COMMAND.md, AGENT.md, etc.)

### Database Schema

- **MarketplaceSource**: 30+ fields, 1 relationship
- **MarketplaceCatalogEntry**: 25+ fields, FTS5 indexed
- **Search Fields**: 4 (search_text, search_tags, artifact_type, name)

### Performance

- **Per-artifact extraction**: ~500ms (GitHub API)
- **Batch extraction**: ~5s for 5 artifacts (git clone)
- **Break-even threshold**: 3 artifacts
- **Database commit**: ~100ms (atomic transaction)

## Implementation Readiness

### For Cross-Source Search

- ✓ Database schema designed (MarketplaceCatalogEntry)
- ✓ FTS5 migration ready
- ✓ Search metadata captured (title, description, tags)
- ✓ Frontmatter extraction implemented
- ⚠ Per-source ranking not configurable

### For Enhanced Detection

- ✓ 8-signal scoring implemented
- ✓ Raw scores captured
- ✓ Score breakdown stored
- ⚠ Detection reasons not persisted (logs only)
- ⚠ Individual signal scores not decomposed

### For Artifacts Root Detection

- ✗ Not implemented
- ⚠ Partial support via `root_hint` (user-provided)
- ✗ No automatic detection
- ✗ No confidence/reasoning

---

**Analysis completed**: 2026-01-24

For questions about specific components, see the appropriate document section referenced above.
