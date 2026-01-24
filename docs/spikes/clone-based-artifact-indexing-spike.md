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

### Option D: Hybrid API + Clone (Pragmatic)

Use API for small operations, clone for large batches.

**Approach**:
```python
if artifact_count < 3:
    use_api_calls()
elif artifact_count < 20:
    use_sparse_clone()
else:
    use_full_shallow_clone()
```

**Pros**:
- Optimal for each case
- Graceful degradation

**Cons**:
- More complex logic
- Multiple code paths to maintain

## Recommended Design: Option A with Enhancements

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

```python
CLONE_THRESHOLD = 3  # Minimum artifacts to use clone

def select_indexing_strategy(
    source: MarketplaceSource,
    artifacts: List[DetectedArtifact],
) -> Literal["api", "sparse_clone", "full_clone"]:
    """Select optimal indexing strategy."""
    count = len(artifacts)

    if count < CLONE_THRESHOLD:
        return "api"

    # Use pre-computed root if available
    if source.artifacts_root:
        # Single directory - full clone of that path is efficient
        return "full_clone" if count > 20 else "sparse_clone"

    # Scattered artifacts - sparse is more efficient
    return "sparse_clone"
```

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
│     ├─> 3-20 artifacts: Sparse clone                       │
│     └─> >20 artifacts: Full shallow clone of root          │
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

### New Migration: Add Clone Metadata Fields

```python
# Alembic migration
def upgrade():
    op.add_column('marketplace_sources', sa.Column(
        'artifacts_root', sa.String(500), nullable=True,
        comment='Computed common ancestor path of all artifacts'
    ))
    op.add_column('marketplace_sources', sa.Column(
        'artifact_paths_json', sa.Text(), nullable=True,
        comment='JSON array of artifact paths for diff detection'
    ))
    op.add_column('marketplace_sources', sa.Column(
        'sparse_patterns_json', sa.Text(), nullable=True,
        comment='JSON array of sparse-checkout patterns'
    ))
    op.add_column('marketplace_sources', sa.Column(
        'last_tree_sha', sa.String(64), nullable=True,
        comment='SHA of repo tree at last scan for change detection'
    ))
```

## API Changes

### Enhanced Source Response

```python
class MarketplaceSourceResponse(BaseModel):
    # Existing fields...

    # New computed metadata (read-only)
    artifacts_root: str | None
    artifact_count: int
    indexing_strategy: Literal["api", "sparse_clone", "full_clone"] | None
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Git not available | Low | High | Check at startup, warn user |
| Clone timeout | Medium | Medium | Configurable timeout, fallback to API |
| Disk space exhaustion | Low | Medium | Limit temp dir size, cleanup on error |
| Private repo auth failure | Medium | Medium | Validate token before clone |
| Manifest format changes | Low | Low | Flexible parsing with defaults |

## Open Questions

1. **Threshold tuning**: Is 3 artifacts the right threshold for clone mode?
2. **Parallel clones**: Should we support cloning multiple sources simultaneously?
3. **Cache persistence**: Should clones be cached for rapid re-indexing?
4. **Webhook integration**: Auto-reindex on push via GitHub webhooks?

## Implementation Plan

### Phase 1: Foundation (1-2 days)
- [ ] Add database migration for new fields
- [ ] Implement `compute_clone_metadata()` function
- [ ] Update `_perform_scan()` to compute and store metadata

### Phase 2: Universal Clone (2-3 days)
- [ ] Refactor `_clone_repo_sparse()` to accept pattern list
- [ ] Implement `_extract_all_manifests_batch()` for all artifact types
- [ ] Add manifest parsers for command, agent, hook, mcp types
- [ ] Update scan flow to use universal extraction

### Phase 3: Optimization (1-2 days)
- [ ] Implement differential re-indexing
- [ ] Add strategy selection logic
- [ ] Add metrics/logging for indexing performance
- [ ] Expose indexing_strategy in API responses

### Phase 4: Testing (1 day)
- [ ] Unit tests for metadata computation
- [ ] Integration tests for clone strategies
- [ ] Performance benchmarks with large repos

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
