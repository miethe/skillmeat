# SPIKE: Clone-Based Artifact Indexing Strategy

**Created**: 2026-01-24
**Status**: Draft
**Author**: Claude (Opus)
**Scope**: API Layer, Core Layer

## Executive Summary

Optimize artifact metadata extraction by cloning repositories locally instead of making per-file GitHub API calls. The current implementation makes one API call per skill artifact to fetch SKILL.md for frontmatter extraction. For repositories with 30+ skills, this quickly exhausts rate limits (60/hour unauthenticated, 5000/hour authenticated).

**Goal**: Reduce GitHub API calls during source indexing from O(n) to O(1) while supporting all artifact types and enabling future optimizations through pre-computed metadata.

## Problem Statement

### Current State
1. **Per-file API calls**: Each skill's SKILL.md is fetched individually via GitHub API
2. **Skills-only**: Current batch optimization only handles skill artifacts
3. **No persistence**: Detection metadata (score breakdown, signals) not stored for re-use
4. **Rate limit vulnerability**: Large repos (100+ artifacts) exhaust limits quickly

### Observed Behavior
```
[API] Frontmatter indexing enabled for source 067ae669...
[API] Request GET /repos/.../contents/skills/javascript-expert/SKILL.md failed with 403: rate limit exceeded
[API] Setting next backoff to 3581.43051s
```

## Requirements Analysis

### Functional Requirements
1. Support all artifact types (skills, commands, agents, hooks, MCP servers)
2. Extract metadata from type-specific manifest files
3. Minimize GitHub API calls during indexing
4. Support both new source imports and re-indexing existing sources
5. Graceful fallback when clone fails

### Non-Functional Requirements
1. Complete indexing of 100-artifact repo in <60 seconds
2. No more than 5 API calls per source scan (excluding tree fetch)
3. Temp storage usage <500MB per clone operation
4. Automatic cleanup of temporary files

## Current Architecture

### Data Available at Detection Time
```python
class DetectedArtifact:
    artifact_type: str      # "skill", "command", "agent", "hook", "mcp"
    name: str               # "canvas-design"
    path: str               # "skills/canvas-design"
    upstream_url: str       # Full GitHub URL
    confidence_score: int   # 0-100
    detected_sha: str       # Commit SHA
    metadata: Dict          # Detection signals
    score_breakdown: Dict   # Heuristic scores
```

### Database Model (MarketplaceSource)
```python
class MarketplaceSource:
    owner: str              # "anthropics"
    repo_name: str          # "quickstarts"
    ref: str                # "main"
    root_hint: str | None   # Optional subdirectory path
    single_artifact_mode: bool
```

### Database Model (MarketplaceCatalogEntry)
```python
class MarketplaceCatalogEntry:
    # Core fields
    name: str
    artifact_type: str
    path: str
    source_id: UUID

    # Search fields (currently skills-only)
    title: str | None
    description: str | None
    search_tags: str | None      # JSON array
    search_text: str | None      # Concatenated searchable text

    # Detection metadata
    confidence_score: int
    detected_sha: str | None
```

## Design Options

### Option A: Full Sparse Clone (Recommended)

Clone the repository with sparse-checkout configured to fetch only manifest files.

**Approach**:
1. Compute minimal sparse-checkout patterns from detected artifacts
2. Clone with `--depth 1 --filter=blob:none --sparse`
3. Configure sparse-checkout for manifest files only
4. Read all manifests from local filesystem
5. Clean up temp directory

**Manifest Files by Type**:
| Artifact Type | Manifest File | Metadata Fields |
|--------------|---------------|-----------------|
| skill | SKILL.md | title, description, tags, version |
| command | command.yaml | name, description, tools |
| agent | agent.yaml | name, description, model |
| hook | hook.yaml | name, description, events |
| mcp | mcp.json | name, description, tools |

**Sparse Patterns**:
```
# For artifacts at: skills/foo, commands/bar, agents/baz
skills/foo/SKILL.md
commands/bar/command.yaml
agents/baz/agent.yaml
```

**Pros**:
- Single git operation regardless of artifact count
- Works for all artifact types
- Minimal bandwidth (only fetches needed files)
- Token-authenticated clone for private repos

**Cons**:
- Requires git binary
- Temp disk space (minimal with sparse)
- Clone timeout for very large repos

### Option B: Git Archive (Alternative)

Use `git archive` to fetch a tarball of specific paths.

**Approach**:
```bash
git archive --remote=git@github.com:owner/repo.git ref paths... | tar -xf -
```

**Pros**:
- No full clone needed
- Can specify exact paths

**Cons**:
- GitHub doesn't support `git archive --remote` for public repos
- Would need GitHub API to generate archive (still rate-limited)
- Less flexible than sparse-checkout

### Option C: Computed Root with Shallow Clone

Compute the nearest common ancestor directory and clone just that subtree.

**Approach**:
1. From detected artifacts, find common path prefix
2. Clone with sparse-checkout for that directory
3. Read all files within

**Example**:
```
Artifacts: skills/a, skills/b, skills/c/nested
Common root: skills/
Clone: skills/**/*
```

**Pros**:
- Natural fit for repos with dedicated artifact directories
- Captures README, shared assets

**Cons**:
- May clone unnecessary files
- No benefit for scattered artifacts

### Option D: Hybrid API + Clone (Pragmatic) — SELECTED

Use API for small operations, sparse clone for larger batches. **Never clone full repository.**

**Approach**:
```python
if artifact_count < 3:
    use_api_calls()           # Simple, no clone overhead
elif artifact_count < 20:
    use_sparse_manifest()     # Clone only manifest files (SKILL.md, etc.)
else:
    use_sparse_directory()    # Clone artifact root directories (.claude/**)
```

**Critical**: Even `sparse_directory` only clones artifact-containing directories, not the
entire codebase. This handles the common case of normal codebases with `.claude/` or `.codex/`
directories containing artifacts.

**Pros**:
- Optimal for each case
- Never clones unnecessary code
- Handles mixed codebases (app code + artifacts)

**Cons**:
- More complex logic
- Multiple code paths to maintain

## Recommended Design: Hybrid Sparse Clone (Option D + Option A Enhancements)

### 1. Universal Manifest Extraction

```python
MANIFEST_PATTERNS = {
    "skill": ["SKILL.md"],
    "command": ["command.yaml", "command.yml", "COMMAND.md"],
    "agent": ["agent.yaml", "agent.yml", "AGENT.md"],
    "hook": ["hook.yaml", "hook.yml"],
    "mcp": ["mcp.json", "package.json"],
}

def get_sparse_patterns(artifacts: List[DetectedArtifact]) -> List[str]:
    """Generate sparse-checkout patterns for all artifacts."""
    patterns = []
    for artifact in artifacts:
        manifests = MANIFEST_PATTERNS.get(artifact.artifact_type, [])
        for manifest in manifests:
            patterns.append(f"{artifact.path}/{manifest}")
    return patterns
```

### 2. Pre-Computed Clone Metadata

Store computed metadata on MarketplaceSource for faster re-indexing:

```python
# New fields on MarketplaceSource
class MarketplaceSource:
    # Existing fields...

    # New computed fields
    artifacts_root: str | None          # Computed common ancestor path
    artifact_paths_json: str | None     # JSON array of all artifact paths
    sparse_patterns_json: str | None    # JSON array of optimal sparse patterns
    last_tree_sha: str | None           # SHA of repo tree at last scan
```

**Computation on Import**:
```python
def compute_clone_metadata(artifacts: List[DetectedArtifact]) -> dict:
    paths = [a.path for a in artifacts]

    # Find common ancestor
    if paths:
        common = os.path.commonpath(paths) if len(paths) > 1 else os.path.dirname(paths[0])
    else:
        common = ""

    # Generate sparse patterns
    patterns = get_sparse_patterns(artifacts)

    return {
        "artifacts_root": common or None,
        "artifact_paths_json": json.dumps(paths),
        "sparse_patterns_json": json.dumps(patterns),
    }
```

### 3. Differential Re-Indexing

When re-scanning an existing source:

```python
def should_reindex(source: MarketplaceSource, current_tree_sha: str) -> bool:
    """Check if source needs re-indexing."""
    if source.last_tree_sha is None:
        return True  # Never indexed
    if source.last_tree_sha != current_tree_sha:
        return True  # Tree changed
    return False

def get_changed_artifacts(source: MarketplaceSource, new_artifacts: List[DetectedArtifact]) -> List[DetectedArtifact]:
    """Find artifacts that need re-indexing."""
    existing_paths = set(json.loads(source.artifact_paths_json or "[]"))
    new_paths = {a.path for a in new_artifacts}

    # Added or modified paths
    changed = new_paths - existing_paths
    return [a for a in new_artifacts if a.path in changed]
```

### 4. Clone Strategy Selection

**Critical Constraint**: Never clone unnecessary code. Many repositories are normal codebases
that happen to contain artifacts in directories like `.claude/`, `.codex/`, or similar. We must
only clone artifact directories, not the entire codebase.

```python
CLONE_THRESHOLD = 3  # Minimum artifacts to use clone

def select_indexing_strategy(
    source: MarketplaceSource,
    artifacts: List[DetectedArtifact],
) -> Literal["api", "sparse_manifest", "sparse_directory"]:
    """Select optimal indexing strategy.

    Strategies:
    - api: Individual API calls for each manifest file
    - sparse_manifest: Sparse clone fetching only manifest files (e.g., SKILL.md)
    - sparse_directory: Sparse clone of artifact root directories (e.g., .claude/**)

    NOTE: We NEVER do a full repository clone. Even for large repos (>20 artifacts),
    we use sparse checkout targeting only the artifact directories. This is critical
    for repos that are normal codebases with artifacts in .claude/, .codex/, etc.
    """
    count = len(artifacts)

    if count < CLONE_THRESHOLD:
        return "api"

    # For large artifact counts, clone the common ancestor directory
    # This is more efficient than many individual file patterns
    if source.artifacts_root and count > 20:
        # Example: artifacts_root = ".claude/skills" → clone ".claude/skills/**"
        # This avoids cloning the entire codebase
        return "sparse_directory"

    # For moderate counts or scattered artifacts, fetch only manifest files
    return "sparse_manifest"


def get_sparse_checkout_patterns(
    strategy: str,
    artifacts: List[DetectedArtifact],
    artifacts_root: str | None,
) -> List[str]:
    """Generate sparse-checkout patterns based on strategy.

    Examples:
        sparse_manifest with 5 skills:
            [".claude/skills/foo/SKILL.md", ".claude/skills/bar/SKILL.md", ...]

        sparse_directory with artifacts_root=".claude":
            [".claude/**"]

        sparse_directory with multiple roots (.claude/, .codex/):
            [".claude/**", ".codex/**"]
    """
    if strategy == "sparse_directory":
        if artifacts_root:
            return [f"{artifacts_root}/**"]
        # Multiple roots - find unique top-level directories
        roots = set()
        for artifact in artifacts:
            parts = artifact.path.split("/")
            if parts:
                roots.add(parts[0])
        return [f"{root}/**" for root in sorted(roots)]

    # sparse_manifest - individual files only
    patterns = []
    for artifact in artifacts:
        manifests = MANIFEST_PATTERNS.get(artifact.artifact_type, [])
        for manifest in manifests:
            patterns.append(f"{artifact.path}/{manifest}")
    return patterns
```

**Strategy Examples**:

| Scenario | Artifact Count | Strategy | Patterns |
|----------|---------------|----------|----------|
| Small skill repo | 2 | api | N/A (use API) |
| Dedicated artifact repo | 15 | sparse_manifest | `skills/*/SKILL.md` |
| Large artifact repo | 50 | sparse_directory | `.claude/**` |
| Normal codebase + artifacts | 30 | sparse_directory | `.claude/**`, `.codex/**` |
| Scattered artifacts | 10 | sparse_manifest | Individual manifest paths |

### 5. Implementation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Source Scan Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Fetch repo tree (1 API call)                           │
│     └─> DetectedArtifact[] with paths                      │
│                                                             │
│  2. Compute clone metadata                                  │
│     └─> artifacts_root, sparse_patterns                    │
│                                                             │
│  3. Select indexing strategy                                │
│     ├─> <3 artifacts: API calls                            │
│     ├─> 3-20 artifacts: sparse_manifest (individual files) │
│     └─> >20 artifacts: sparse_directory (root dirs only)   │
│                                                             │
│  4. Execute clone (if selected)                             │
│     └─> git clone --depth 1 --sparse ...                   │
│                                                             │
│  5. Extract manifests                                       │
│     └─> Read files from disk or API                        │
│                                                             │
│  6. Parse and store metadata                                │
│     └─> Update MarketplaceCatalogEntry                     │
│                                                             │
│  7. Update source computed fields                           │
│     └─> artifacts_root, last_tree_sha                      │
│                                                             │
│  8. Cleanup temp directory                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema Changes

### Migration 1: Add Clone Target and Deep Indexing Fields

```python
# Alembic migration: add_clone_target_fields
def upgrade():
    # MarketplaceSource: Clone target (replaces individual fields with structured JSON)
    op.add_column('marketplace_sources', sa.Column(
        'clone_target_json', sa.Text(), nullable=True,
        comment='JSON-serialized CloneTarget for rapid re-indexing'
    ))

    # MarketplaceSource: Deep indexing toggle
    op.add_column('marketplace_sources', sa.Column(
        'deep_indexing_enabled', sa.Boolean(), nullable=False,
        server_default='false',
        comment='Clone entire artifact directories for enhanced search'
    ))

    # MarketplaceSource: Webhook pre-wiring (for future use)
    op.add_column('marketplace_sources', sa.Column(
        'webhook_secret', sa.String(64), nullable=True,
        comment='Secret for GitHub webhook verification (future use)'
    ))
    op.add_column('marketplace_sources', sa.Column(
        'last_webhook_event_at', sa.DateTime(), nullable=True,
        comment='Timestamp of last webhook event received'
    ))

    # MarketplaceCatalogEntry: Deep index fields
    op.add_column('marketplace_catalog_entries', sa.Column(
        'deep_search_text', sa.Text(), nullable=True,
        comment='Full-text content from deep indexing'
    ))
    op.add_column('marketplace_catalog_entries', sa.Column(
        'deep_indexed_at', sa.DateTime(), nullable=True,
        comment='Timestamp of last deep indexing'
    ))
    op.add_column('marketplace_catalog_entries', sa.Column(
        'deep_index_files', sa.Text(), nullable=True,
        comment='JSON array of files included in deep index'
    ))


def downgrade():
    op.drop_column('marketplace_catalog_entries', 'deep_index_files')
    op.drop_column('marketplace_catalog_entries', 'deep_indexed_at')
    op.drop_column('marketplace_catalog_entries', 'deep_search_text')
    op.drop_column('marketplace_sources', 'last_webhook_event_at')
    op.drop_column('marketplace_sources', 'webhook_secret')
    op.drop_column('marketplace_sources', 'deep_indexing_enabled')
    op.drop_column('marketplace_sources', 'clone_target_json')
```

### Migration 2: Update FTS5 Virtual Table

```python
# Alembic migration: add_deep_search_to_fts5
def upgrade():
    # Drop and recreate FTS5 table with new column
    # Note: FTS5 tables cannot be altered, must recreate
    op.execute("DROP TABLE IF EXISTS catalog_fts")
    op.execute("""
        CREATE VIRTUAL TABLE catalog_fts USING fts5(
            name UNINDEXED,
            artifact_type UNINDEXED,
            title,
            description,
            search_text,
            tags,
            deep_search_text,
            content='marketplace_catalog_entries',
            content_rowid='rowid',
            tokenize='porter unicode61 remove_diacritics 2'
        )
    """)
    # Rebuild FTS index
    op.execute("INSERT INTO catalog_fts(catalog_fts) VALUES('rebuild')")
```

## API Changes

### Enhanced Source Response

```python
class MarketplaceSourceResponse(BaseModel):
    # Existing fields...

    # New computed metadata (read-only)
    artifacts_root: str | None
    artifact_count: int
    indexing_strategy: Literal["api", "sparse_manifest", "sparse_directory"] | None
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Git not available | Low | High | Check at startup, warn user |
| Clone timeout | Medium | Medium | Configurable timeout, fallback to API |
| Disk space exhaustion | Low | Medium | Limit temp dir size, cleanup on error |
| Private repo auth failure | Medium | Medium | Validate token before clone |
| Manifest format changes | Low | Low | Flexible parsing with defaults |

## Resolved Decisions

1. **Threshold**: 3 artifacts is the initial threshold. Performance benchmarks during
   implementation will validate or adjust this.

2. **Clone caching**: Do NOT cache the cloned files. DO cache the **clone targets** as a
   structured object with all information needed for rapid re-sync. See Clone Target Structure.

3. **Webhook integration**: Add as future enhancement with pre-wiring during implementation.

## Clone Target Structure

Store a structured object on `MarketplaceSource` containing everything needed for rapid re-indexing:

```python
@dataclass
class CloneTarget:
    """Structured clone configuration for rapid re-sync."""

    # Clone strategy
    strategy: Literal["api", "sparse_manifest", "sparse_directory"]

    # Sparse checkout patterns (computed from artifacts)
    sparse_patterns: List[str]  # e.g., [".claude/**"] or ["skills/foo/SKILL.md", ...]

    # Common ancestor path (if exists)
    artifacts_root: str | None  # e.g., ".claude/skills"

    # All artifact paths for differential detection
    artifact_paths: List[str]  # e.g., [".claude/skills/foo", ".claude/skills/bar"]

    # Tree state for change detection
    tree_sha: str  # SHA of repo tree at computation time

    # Timestamp for staleness checks
    computed_at: datetime


# Serialized as JSON in MarketplaceSource.clone_target_json
```

**Database Field**:
```python
class MarketplaceSource:
    # ... existing fields ...

    clone_target_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized CloneTarget for rapid re-indexing"
    )

    @property
    def clone_target(self) -> Optional[CloneTarget]:
        """Deserialize clone target configuration."""
        if not self.clone_target_json:
            return None
        return CloneTarget(**json.loads(self.clone_target_json))
```

**Re-sync Flow**:
```python
def resync_source(source: MarketplaceSource) -> None:
    """Rapid re-sync using cached clone target."""
    target = source.clone_target
    if not target:
        # No cached target - perform full scan
        return full_scan(source)

    # Check if tree changed
    current_sha = fetch_tree_sha(source)
    if current_sha == target.tree_sha:
        logger.info("Tree unchanged, skipping re-index")
        return

    # Use cached strategy and patterns for clone
    clone_with_patterns(source, target.strategy, target.sparse_patterns)
    extract_manifests(...)
    update_clone_target(source, current_sha)
```

## Full-Artifact Indexing (Enhanced Search)

### Feature Description

Add an optional **deep indexing mode** that clones and indexes the entire artifact directory,
not just the manifest file. This enables full-text search across all artifact content.

**Use Case**: Find skills based on code patterns, examples, or implementation details that
aren't in the SKILL.md frontmatter.

### Configuration

```python
class MarketplaceSource:
    # ... existing fields ...

    # Indexing depth control
    deep_indexing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="Clone entire artifact directories for enhanced search"
    )
```

### Behavior Comparison

| Mode | What's Cloned | What's Indexed | Search Coverage |
|------|--------------|----------------|-----------------|
| Standard | `skills/foo/SKILL.md` | Frontmatter only | Title, description, tags |
| Deep | `skills/foo/**` | All text files | Full content, examples, code |

### Deep Indexing Implementation

```python
def get_deep_sparse_patterns(artifacts: List[DetectedArtifact]) -> List[str]:
    """Generate patterns for full artifact directory clone."""
    return [f"{artifact.path}/**" for artifact in artifacts]


def extract_deep_search_text(artifact_dir: Path) -> str:
    """Extract searchable text from all files in artifact directory."""
    text_parts = []

    # Define indexable file patterns
    indexable = ["*.md", "*.yaml", "*.yml", "*.json", "*.txt", "*.py", "*.ts", "*.js"]

    for pattern in indexable:
        for file_path in artifact_dir.glob(pattern):
            if file_path.stat().st_size < 100_000:  # Skip large files
                content = file_path.read_text(errors="ignore")
                # Strip code comments and normalize whitespace
                text_parts.append(normalize_for_search(content))

    return " ".join(text_parts)
```

### Database Schema for Deep Index

```python
class MarketplaceCatalogEntry:
    # ... existing fields ...

    # Enhanced search fields
    deep_search_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full-text content from deep indexing"
    )
    deep_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last deep indexing"
    )
    deep_index_files: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of files included in deep index"
    )
```

### FTS5 Integration

Update the FTS5 virtual table to include deep search text:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(
    name UNINDEXED,
    artifact_type UNINDEXED,
    title,
    description,
    search_text,
    tags,
    deep_search_text,  -- NEW: Full content from deep indexing
    content='marketplace_catalog_entries',
    content_rowid='rowid',
    tokenize='porter unicode61 remove_diacritics 2'
);
```

### API Exposure

```python
class SourceCreateRequest(BaseModel):
    # ... existing fields ...
    deep_indexing_enabled: bool = Field(
        default=False,
        description="Enable deep indexing for enhanced full-text search"
    )

class ArtifactSearchResponse(BaseModel):
    # ... existing fields ...
    deep_match: bool = Field(
        default=False,
        description="Whether match came from deep-indexed content"
    )
    matched_file: Optional[str] = Field(
        default=None,
        description="File path where match was found (deep index only)"
    )
```

## Future Enhancements

### GitHub Webhook Integration

**Goal**: Auto-reindex sources when commits are pushed to the repository.

**Pre-wiring during implementation**:
1. Add `webhook_secret` field to `MarketplaceSource` (nullable, for future use)
2. Add `last_webhook_event_at` timestamp field
3. Design webhook endpoint structure (not implemented yet)

```python
class MarketplaceSource:
    # Pre-wired for future webhook support
    webhook_secret: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Secret for GitHub webhook verification (future use)"
    )
    last_webhook_event_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last webhook event received"
    )
```

**Future webhook endpoint** (not in current scope):
```python
@router.post("/sources/{source_id}/webhook")
async def handle_github_webhook(
    source_id: UUID,
    request: Request,
    x_hub_signature_256: str = Header(...),
):
    """Handle GitHub push webhook for auto-reindex."""
    # Verify signature using webhook_secret
    # Queue re-index job
    pass
```

## Open Questions

1. **Deep indexing file size limits**: What's the max file size to include? (Proposed: 100KB)
2. **Deep indexing file types**: Should we include more than text files? (e.g., Jupyter notebooks)
3. **Parallel clones**: Should we support cloning multiple sources simultaneously?

## Implementation Plan

### Phase 1: Foundation (1-2 days)
- [ ] Add database migration for new fields:
  - `clone_target_json` on MarketplaceSource
  - `deep_indexing_enabled` on MarketplaceSource
  - `deep_search_text`, `deep_indexed_at`, `deep_index_files` on MarketplaceCatalogEntry
  - Pre-wire: `webhook_secret`, `last_webhook_event_at` on MarketplaceSource
- [ ] Implement `CloneTarget` dataclass and serialization
- [ ] Implement `compute_clone_metadata()` function
- [ ] Update `_perform_scan()` to compute and store clone target

### Phase 2: Universal Clone (2-3 days)
- [ ] Refactor `_clone_repo_sparse()` to accept pattern list
- [ ] Implement `get_sparse_checkout_patterns()` with strategy selection
- [ ] Implement `_extract_all_manifests_batch()` for all artifact types
- [ ] Add manifest parsers for command, agent, hook, mcp types
- [ ] Update scan flow to use universal extraction

### Phase 3: Optimization (1-2 days)
- [ ] Implement differential re-indexing using `CloneTarget.tree_sha`
- [ ] Add strategy selection logic (`sparse_manifest` vs `sparse_directory`)
- [ ] Add metrics/logging for indexing performance
- [ ] Expose `clone_target` summary in API responses

### Phase 4: Deep Indexing (1-2 days)
- [ ] Implement `get_deep_sparse_patterns()` for full artifact cloning
- [ ] Implement `extract_deep_search_text()` with file type filtering
- [ ] Update FTS5 virtual table to include `deep_search_text`
- [ ] Add `deep_indexing_enabled` toggle to source create/update API
- [ ] Add `deep_match` and `matched_file` to search responses

### Phase 5: Testing & Benchmarks (1 day)
- [ ] Unit tests for CloneTarget serialization
- [ ] Unit tests for metadata computation
- [ ] Integration tests for clone strategies
- [ ] Performance benchmarks with large repos (validate 3-artifact threshold)
- [ ] Deep indexing integration tests

## Success Criteria

1. **Rate limit safety**: Indexing 100-artifact repo uses <10 API calls
2. **Speed**: 100-artifact repo indexes in <60 seconds
3. **Coverage**: All 5 artifact types supported
4. **Reliability**: 99%+ success rate for public repos
5. **Observability**: Clear logging of strategy selection and timing

## References

- Current implementation: `skillmeat/api/routers/marketplace_sources.py:655-929`
- Git sparse-checkout docs: https://git-scm.com/docs/git-sparse-checkout
- GitHub rate limits: https://docs.github.com/en/rest/rate-limit
