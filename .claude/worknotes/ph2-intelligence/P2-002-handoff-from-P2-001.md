# P2-002 Handoff: Cross-Project Indexing

**From**: P2-001 (SearchManager Core)
**To**: P2-002 (Cross-Project Indexing)
**Date**: 2025-11-15
**Status**: P2-001 COMPLETE ✅

---

## What P2-001 Delivers to P2-002

### 1. Core Search Infrastructure

**SearchManager Class** (`skillmeat/core/search.py`, 611 lines):
- Fully functional collection search
- Metadata + content search with ranking
- Ripgrep integration with Python fallback
- Comprehensive error handling
- Performance: <3s for 100+ artifacts

**Data Models** (`skillmeat/models.py`):
```python
@dataclass
class SearchMatch:
    artifact_name: str
    artifact_type: str
    score: float
    match_type: str  # "metadata", "content", or "both"
    context: str
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    query: str
    matches: List[SearchMatch] = field(default_factory=list)
    total_count: int = 0
    search_time: float = 0.0
    used_ripgrep: bool = False
    search_type: str = "both"
```

**Key Methods**:
```python
def search_collection(
    query: str,
    collection_name: Optional[str] = None,
    search_type: str = "both",  # "metadata", "content", or "both"
    artifact_types: Optional[List[ArtifactType]] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50
) -> SearchResult
```

### 2. Reusable Components for P2-002

**Metadata Search Logic** (lines 146-201):
- YAML frontmatter extraction
- Weighted scoring algorithm
- Context generation
- **Ready to reuse** for cross-project search

**Content Search Logic** (lines 203-265):
- Ripgrep integration with JSON output
- Python fallback implementation
- Binary file detection
- **Ready to reuse** for cross-project search

**Ranking Algorithm** (lines 557-585):
- Score calculation and normalization
- Exact match boosting
- Artifact name matching
- **Ready to reuse** for cross-project ranking

**Helper Methods**:
```python
_search_with_ripgrep()   # Lines 267-336
_search_with_python()    # Lines 338-394
_get_searchable_files()  # Lines 396-418
_should_ignore()         # Lines 420-439
_is_binary_file()        # Lines 441-462
_is_path_in_artifact()   # Lines 464-478
_rank_matches()          # Lines 557-585
```

---

## P2-002 Requirements Analysis

### Acceptance Criteria

From implementation plan:
- ✅ Handles >10 projects with caching TTL 60s
- ✅ Config-driven root discovery
- ✅ Returns cross-project SearchResult with project_path field
- ✅ Caching layer for performance

### Technical Specifications

**New Features Needed**:

1. **Multi-Project Scanning**:
   - Extend SearchManager to accept list of project paths
   - Scan `.claude/` directories in each project
   - Aggregate artifacts from all projects
   - Preserve project_path metadata

2. **Caching Layer**:
   - Cache search index with TTL (60s default)
   - Invalidate on file modification (mtime check)
   - In-memory cache for performance
   - Configurable cache size

3. **Config-Driven Discovery**:
   - ConfigManager setting for project roots
   - Auto-discovery of .claude directories
   - Exclusion patterns for ignored paths
   - Recursive vs. shallow search options

4. **Enhanced Data Models**:
   - Add `project_path` field to SearchMatch
   - Track which project each artifact came from
   - Support project-level filtering

---

## Implementation Strategy for P2-002

### Option 1: Extend SearchManager (Recommended)

**Pros**:
- Reuses existing search logic
- Single class for all search operations
- Easier to maintain

**Cons**:
- SearchManager becomes larger
- Collection vs. project search split in one class

**Approach**:
```python
class SearchManager:
    def __init__(self, collection_mgr=None):
        self.collection_mgr = collection_mgr
        self._search_cache = {}  # New: cache layer

    def search_collection(self, ...):
        # Existing implementation (no changes)
        pass

    def search_projects(
        self,
        query: str,
        project_paths: Optional[List[Path]] = None,  # None = use config
        search_type: str = "both",
        artifact_types: Optional[List[ArtifactType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        use_cache: bool = True
    ) -> SearchResult:
        """Search across multiple project directories.

        This method:
        1. Discovers projects (from config or explicit list)
        2. Scans .claude/ directories for artifacts
        3. Builds in-memory index (cached)
        4. Searches index using existing search logic
        5. Returns aggregated results with project_path
        """
        # Implementation details below
        pass

    def _discover_projects(self, roots: List[Path]) -> List[Path]:
        """Find all .claude/ directories under roots."""
        pass

    def _build_project_index(self, projects: List[Path]) -> Dict[str, Any]:
        """Build searchable index from project artifacts."""
        pass

    def _get_cached_index(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached index if valid (TTL check)."""
        pass

    def _cache_index(self, cache_key: str, index: Dict[str, Any]) -> None:
        """Store index in cache with timestamp."""
        pass
```

### Option 2: Create ProjectSearchManager (Alternative)

**Pros**:
- Separation of concerns
- Smaller, focused classes

**Cons**:
- Code duplication
- More complex integration

**Not recommended** due to code duplication.

---

## Detailed Implementation Plan

### Step 1: Data Model Enhancements

**Update SearchMatch**:
```python
@dataclass
class SearchMatch:
    artifact_name: str
    artifact_type: str
    score: float
    match_type: str
    context: str
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    project_path: Optional[Path] = None  # NEW: source project
```

### Step 2: Cache Structure

**CacheEntry**:
```python
@dataclass
class SearchCacheEntry:
    """In-memory cache entry for project search index."""
    index: Dict[str, Any]  # Artifact metadata + paths
    created_at: float      # time.time() timestamp
    ttl: float = 60.0      # Default 60s TTL

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl
```

**Cache Storage**:
```python
class SearchManager:
    def __init__(self, ...):
        self._project_cache: Dict[str, SearchCacheEntry] = {}
```

### Step 3: Project Discovery

**ConfigManager Integration**:
```python
# In config.toml
[settings]
project-roots = [
    "/home/user/projects",
    "/home/user/work"
]
project-search-depth = 3  # Max recursion depth
exclude-patterns = [
    "node_modules",
    ".venv",
    "venv"
]
```

**Discovery Logic**:
```python
def _discover_projects(
    self,
    roots: Optional[List[Path]] = None
) -> List[Path]:
    """Discover all .claude/ directories under roots.

    Args:
        roots: List of root paths to search (uses config if None)

    Returns:
        List of paths to .claude/ directories
    """
    if roots is None:
        roots = self.collection_mgr.config.get("settings.project-roots", [])
        roots = [Path(r) for r in roots]

    max_depth = self.collection_mgr.config.get("settings.project-search-depth", 3)
    exclude_patterns = self.collection_mgr.config.get(
        "settings.exclude-patterns",
        ["node_modules", ".venv", "venv"]
    )

    projects = []
    for root in roots:
        if not root.exists():
            continue

        # BFS to find .claude/ directories
        for path in self._walk_directories(root, max_depth, exclude_patterns):
            if (path / ".claude").is_dir():
                projects.append(path / ".claude")

    return projects
```

### Step 4: Index Building

**Project Index Structure**:
```python
{
    "project_path": Path("/path/to/project/.claude"),
    "artifacts": [
        {
            "name": "skill-name",
            "type": "skill",
            "path": Path("skills/skill-name"),
            "metadata": ArtifactMetadata(...),
        },
        ...
    ],
    "last_modified": 1699999999.0  # mtime for cache invalidation
}
```

**Build Logic**:
```python
def _build_project_index(self, project_paths: List[Path]) -> List[Dict[str, Any]]:
    """Build searchable index from project .claude/ directories.

    Args:
        project_paths: List of .claude/ directory paths

    Returns:
        List of project index dicts
    """
    indexes = []

    for project_path in project_paths:
        # Check for skills/ directory
        skills_dir = project_path / "skills"
        artifacts = []

        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                # Validate skill
                from skillmeat.utils.validator import ArtifactValidator
                result = ArtifactValidator.validate_skill(skill_dir)
                if not result.is_valid:
                    continue

                # Extract metadata
                try:
                    metadata = extract_artifact_metadata(skill_dir, ArtifactType.SKILL)
                except Exception:
                    metadata = ArtifactMetadata()

                artifacts.append({
                    "name": skill_dir.name,
                    "type": "skill",
                    "path": skill_dir,
                    "metadata": metadata,
                })

        # Get directory mtime for cache invalidation
        mtime = project_path.stat().st_mtime

        indexes.append({
            "project_path": project_path,
            "artifacts": artifacts,
            "last_modified": mtime,
        })

    return indexes
```

### Step 5: Search Implementation

**search_projects Method**:
```python
def search_projects(
    self,
    query: str,
    project_paths: Optional[List[Path]] = None,
    search_type: str = "both",
    artifact_types: Optional[List[ArtifactType]] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    use_cache: bool = True
) -> SearchResult:
    """Search across multiple project directories.

    Args:
        query: Search query string
        project_paths: Explicit project paths (None = discover from config)
        search_type: "metadata", "content", or "both"
        artifact_types: Filter by artifact types
        tags: Filter by tags
        limit: Maximum results
        use_cache: Use cached index if available

    Returns:
        SearchResult with project_path in each match
    """
    start_time = time.time()

    # Step 1: Discover projects
    if project_paths is None:
        project_paths = self._discover_projects()

    # Step 2: Build/retrieve index
    cache_key = self._compute_cache_key(project_paths)

    if use_cache:
        cached_index = self._get_cached_index(cache_key)
        if cached_index:
            project_indexes = cached_index
        else:
            project_indexes = self._build_project_index(project_paths)
            self._cache_index(cache_key, project_indexes)
    else:
        project_indexes = self._build_project_index(project_paths)

    # Step 3: Search across all projects
    all_matches = []
    used_ripgrep = False

    for project_index in project_indexes:
        project_path = project_index["project_path"]
        artifacts = project_index["artifacts"]

        # Search metadata
        if search_type in ("metadata", "both"):
            metadata_matches = self._search_project_metadata(
                query, artifacts, project_path
            )
            all_matches.extend(metadata_matches)

        # Search content
        if search_type in ("content", "both"):
            content_matches, rg_used = self._search_project_content(
                query, artifacts, project_path
            )
            all_matches.extend(content_matches)
            used_ripgrep = used_ripgrep or rg_used

    # Step 4: Rank and filter
    all_matches = self._rank_matches(query, all_matches)

    # Filter by type/tags if specified
    if artifact_types:
        all_matches = [m for m in all_matches if m.artifact_type in [t.value for t in artifact_types]]
    if tags:
        all_matches = [m for m in all_matches if any(tag in m.metadata.get("tags", []) for tag in tags)]

    # Limit results
    if limit > 0:
        all_matches = all_matches[:limit]

    search_time = time.time() - start_time

    return SearchResult(
        query=query,
        matches=all_matches,
        total_count=len(all_matches),
        search_time=search_time,
        used_ripgrep=used_ripgrep,
        search_type=search_type,
    )
```

### Step 6: Cache Management

**Helper Methods**:
```python
def _compute_cache_key(self, project_paths: List[Path]) -> str:
    """Generate cache key from project paths."""
    # Sort for consistent keys
    sorted_paths = sorted([str(p) for p in project_paths])
    return hashlib.md5("".join(sorted_paths).encode()).hexdigest()

def _get_cached_index(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve cached index if valid."""
    entry = self._project_cache.get(cache_key)
    if entry is None:
        return None

    if entry.is_expired():
        del self._project_cache[cache_key]
        return None

    # Check if any project directories were modified
    for project_index in entry.index:
        project_path = project_index["project_path"]
        cached_mtime = project_index["last_modified"]

        try:
            current_mtime = project_path.stat().st_mtime
            if current_mtime > cached_mtime:
                # Directory modified, invalidate cache
                del self._project_cache[cache_key]
                return None
        except (OSError, IOError):
            # Directory no longer exists
            del self._project_cache[cache_key]
            return None

    return entry.index

def _cache_index(self, cache_key: str, index: List[Dict[str, Any]]) -> None:
    """Store index in cache."""
    ttl = self.collection_mgr.config.get("settings.search-cache-ttl", 60.0)
    self._project_cache[cache_key] = SearchCacheEntry(
        index=index,
        created_at=time.time(),
        ttl=ttl
    )
```

---

## Testing Strategy for P2-002

### Test Structure

**File**: `tests/test_search_projects.py`

**Test Classes**:
1. `TestProjectDiscovery` (5 tests)
   - Discover projects from roots
   - Respect max depth
   - Honor exclude patterns
   - Handle missing roots
   - Handle permission errors

2. `TestProjectIndexing` (5 tests)
   - Build index from projects
   - Extract metadata correctly
   - Handle invalid artifacts
   - Track modification times
   - Handle multiple artifact types

3. `TestCacheManagement` (5 tests)
   - Cache index on first search
   - Retrieve from cache on second search
   - Invalidate on TTL expiration
   - Invalidate on directory modification
   - Handle cache key collisions

4. `TestCrossProjectSearch` (5 tests)
   - Search across multiple projects
   - Filter by project path
   - Aggregate results correctly
   - Preserve project_path in matches
   - Handle >10 projects efficiently

5. `TestPerformance` (2 tests)
   - Cache performance (second search faster)
   - Large project set (<5s for 10+ projects)

**Total**: 22 tests

---

## Performance Targets

From PRD:
- **Multi-Project Search**: <5s for 10+ projects (first search)
- **Cached Search**: <1s for repeated searches
- **Cache TTL**: 60s default (configurable)

**Expected Performance**:
- Project discovery: ~0.1-0.5s (depending on depth)
- Index building: ~0.5-2s (10 projects, ~100 artifacts)
- Search: ~0.1-0.5s (using existing search logic)
- **Total first search**: ~1-3s (well under 5s target)
- **Cached search**: ~0.1-0.5s (well under 1s target)

---

## Integration Points

### ConfigManager

**New Settings**:
```toml
[settings]
project-roots = []           # List of root paths
project-search-depth = 3     # Max recursion
exclude-patterns = []        # Directories to skip
search-cache-ttl = 60.0      # Cache TTL in seconds
```

### CLI Integration (for P2-004)

**Command**: `skillmeat search --projects`

```python
@main.command()
@click.argument("query")
@click.option("--projects", is_flag=True, help="Search across projects")
def search_cmd(query: str, projects: bool):
    """Search artifacts in collection or across projects."""
    search_mgr = SearchManager()

    if projects:
        result = search_mgr.search_projects(query)
    else:
        result = search_mgr.search_collection(query)

    # Display results...
```

---

## Files to Create/Modify

### Create:
- `tests/test_search_projects.py` (22 tests)
- `.claude/worknotes/ph2-intelligence/P2-002-implementation-notes.md`

### Modify:
- `skillmeat/core/search.py`:
  - Add `search_projects()` method
  - Add cache management methods
  - Add project discovery methods
  - Add project indexing methods
- `skillmeat/models.py`:
  - Add `project_path: Optional[Path]` to SearchMatch
  - Add `SearchCacheEntry` dataclass
- `skillmeat/config.py` (or config schema):
  - Add project-roots setting
  - Add project-search-depth setting
  - Add exclude-patterns setting
  - Add search-cache-ttl setting

---

## Success Criteria Checklist

- [ ] Handles >10 projects efficiently (<5s first search)
- [ ] Caching works with 60s TTL
- [ ] Cache invalidates on directory modification
- [ ] Config-driven root discovery works
- [ ] Returns SearchResult with project_path field
- [ ] Respects exclude patterns
- [ ] Honors max search depth
- [ ] All 22 tests passing
- [ ] Performance targets met
- [ ] Integration with existing search logic verified

---

## Risk Assessment

**Low Risk**:
- ✅ Core search logic proven (P2-001 complete)
- ✅ Data models well-designed
- ✅ ConfigManager integration straightforward

**Medium Risk**:
- ⚠️ Cache invalidation correctness (requires thorough testing)
- ⚠️ Performance with many projects (>20 projects)
- ⚠️ Cross-platform path handling (Windows vs. Unix)

**Mitigation**:
- Use mtime-based invalidation (simple, reliable)
- Implement cache size limits (prevent memory growth)
- Test on Windows + Unix in CI
- Add performance benchmarks

---

## Estimated Effort

**Original Estimate**: 2 pts (1-2 days)

**Breakdown**:
- Project discovery: 0.5 pts
- Index building: 0.5 pts
- Cache layer: 0.5 pts
- Search integration: 0.25 pts
- Testing: 0.25 pts

**Total**: 2 pts (matches original estimate)

---

## Summary

P2-001 delivers a complete, tested, performant search foundation. P2-002 extends this to cross-project search by adding:

1. **Project discovery** (config-driven, recursive)
2. **Index building** (metadata extraction, validation)
3. **Cache layer** (TTL, mtime invalidation)
4. **Aggregated search** (reuses existing logic)

All core search logic is proven and ready to reuse. The main work is scaffolding the multi-project indexing and caching infrastructure.

**Ready for P2-002 implementation!**
