# P2-003 Handoff: Duplicate Detection

**From**: P2-002 (Cross-Project Indexing)
**To**: P2-003 (Duplicate Detection)
**Date**: 2025-11-15
**Status**: P2-002 COMPLETE ✅

---

## What P2-002 Delivers to P2-003

### 1. Cross-Project Search Infrastructure

**SearchManager Enhancements** (`skillmeat/core/search.py`, 1101 lines):
- Project discovery with configurable roots and exclusions
- Project indexing with artifact validation and metadata extraction
- Cross-project search across multiple .claude/ directories
- Caching layer with TTL and mtime-based invalidation
- Performance: <2s for 15 projects (well under 5s target)

**Data Models** (`skillmeat/models.py`):
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
    project_path: Optional[Path] = None  # NEW in P2-002

@dataclass
class SearchCacheEntry:
    index: List[Dict[str, Any]]
    created_at: float
    ttl: float = 60.0

    def is_expired(self) -> bool
```

**Key Methods**:
```python
def search_projects(
    query: str,
    project_paths: Optional[List[Path]] = None,
    search_type: str = "both",
    artifact_types: Optional[List[ArtifactType]] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    use_cache: bool = True
) -> SearchResult

def _discover_projects(
    roots: Optional[List[Path]] = None
) -> List[Path]

def _build_project_index(
    project_paths: List[Path]
) -> List[Dict[str, any]]
```

### 2. Reusable Components for P2-003

**Project Index Structure** (from `_build_project_index`):
```python
{
    "project_path": Path("/path/to/project/.claude"),
    "artifacts": [
        {
            "name": "skill-name",
            "type": ArtifactType.SKILL,
            "path": Path("/path/to/project/.claude/skills/skill-name"),
            "metadata": ArtifactMetadata(...),
        },
        ...
    ],
    "last_modified": 1699999999.0
}
```

**Artifact Discovery Pattern**:
- P2-002 already discovers all artifacts across projects
- Validates artifacts using `ArtifactValidator.validate_skill()`
- Extracts metadata with fallback to defaults
- **Ready to reuse** for duplicate detection

**Metadata Extraction**:
- Uses `extract_artifact_metadata()` for YAML frontmatter
- Handles missing/invalid metadata gracefully
- Returns `ArtifactMetadata` with title, description, tags, author, license, version
- **Ready to reuse** for similarity comparison

**Helper Methods**:
```python
_discover_projects()       # Lines 735-780
_build_project_index()     # Lines 823-893
_walk_directories()        # Lines 782-821
```

---

## P2-003 Requirements Analysis

### Acceptance Criteria

From implementation plan:
- ✅ find_duplicates reports artifact pairs w/ similarity score
- ✅ Threshold filtering for configurable similarity
- ✅ Hash collision handling
- ✅ Performance: <5s for 100+ artifacts

### Technical Specifications

**1. Similarity Hashing Algorithm**:

Recommended approach: Content-based hashing with multiple features

```python
@dataclass
class ArtifactFingerprint:
    """Fingerprint for duplicate detection."""
    artifact_path: Path
    artifact_name: str
    artifact_type: str

    # Content hashes
    content_hash: str       # SHA256 of all file contents
    metadata_hash: str      # Hash of title/description
    structure_hash: str     # Hash of file tree structure

    # Metadata features
    title: Optional[str]
    description: Optional[str]
    tags: List[str]
    file_count: int
    total_size: int

    def compute_similarity(self, other: 'ArtifactFingerprint') -> float:
        """Calculate similarity score (0.0 to 1.0)."""
        score = 0.0

        # Exact content match (highest weight: 50%)
        if self.content_hash == other.content_hash:
            score += 0.5

        # Structure match (20%)
        if self.structure_hash == other.structure_hash:
            score += 0.2

        # Metadata match (20%)
        metadata_score = self._compare_metadata(other)
        score += metadata_score * 0.2

        # File count similarity (10%)
        if self.file_count > 0 and other.file_count > 0:
            count_similarity = min(self.file_count, other.file_count) / max(self.file_count, other.file_count)
            score += count_similarity * 0.1

        return score

    def _compare_metadata(self, other: 'ArtifactFingerprint') -> float:
        """Compare metadata fields (0.0 to 1.0)."""
        score = 0.0
        count = 0

        # Title similarity (Levenshtein or simple equality)
        if self.title and other.title:
            score += 1.0 if self.title.lower() == other.title.lower() else 0.0
            count += 1

        # Description similarity
        if self.description and other.description:
            score += 1.0 if self.description.lower() == other.description.lower() else 0.0
            count += 1

        # Tag overlap (Jaccard similarity)
        if self.tags and other.tags:
            self_tags = set(t.lower() for t in self.tags)
            other_tags = set(t.lower() for t in other.tags)
            if self_tags or other_tags:
                jaccard = len(self_tags & other_tags) / len(self_tags | other_tags)
                score += jaccard
                count += 1

        return score / count if count > 0 else 0.0
```

**2. Duplicate Detection Method**:

```python
@dataclass
class DuplicatePair:
    """Pair of potentially duplicate artifacts."""
    artifact1_path: Path
    artifact1_name: str
    artifact2_path: Path
    artifact2_name: str
    similarity_score: float
    match_reasons: List[str]  # ["exact_content", "same_structure", "similar_metadata"]

class SearchManager:
    def find_duplicates(
        self,
        threshold: float = 0.7,
        project_paths: Optional[List[Path]] = None,
        use_cache: bool = True
    ) -> List[DuplicatePair]:
        """Find duplicate artifacts across projects.

        Args:
            threshold: Minimum similarity score (0.0 to 1.0)
            project_paths: Explicit project paths (None = discover from config)
            use_cache: Use cached index if available

        Returns:
            List of DuplicatePair objects sorted by similarity (descending)
        """
        # Step 1: Discover projects (reuse from P2-002)
        if project_paths is None:
            project_paths = self._discover_projects()

        # Step 2: Build/retrieve index (reuse from P2-002)
        cache_key = self._compute_cache_key(project_paths)
        if use_cache:
            cached_index = self._get_cached_index(cache_key, project_paths)
            if cached_index:
                project_indexes = cached_index
            else:
                project_indexes = self._build_project_index(project_paths)
                self._cache_index(cache_key, project_indexes)
        else:
            project_indexes = self._build_project_index(project_paths)

        # Step 3: Extract all artifacts
        all_artifacts = []
        for project_index in project_indexes:
            all_artifacts.extend(project_index["artifacts"])

        # Step 4: Compute fingerprints
        fingerprints = []
        for artifact in all_artifacts:
            fp = self._compute_fingerprint(artifact)
            fingerprints.append(fp)

        # Step 5: Compare all pairs
        duplicates = []
        for i in range(len(fingerprints)):
            for j in range(i + 1, len(fingerprints)):
                fp1 = fingerprints[i]
                fp2 = fingerprints[j]

                # Skip same artifact (by path)
                if fp1.artifact_path == fp2.artifact_path:
                    continue

                # Compute similarity
                similarity = fp1.compute_similarity(fp2)

                if similarity >= threshold:
                    match_reasons = self._get_match_reasons(fp1, fp2)
                    duplicates.append(DuplicatePair(
                        artifact1_path=fp1.artifact_path,
                        artifact1_name=fp1.artifact_name,
                        artifact2_path=fp2.artifact_path,
                        artifact2_name=fp2.artifact_name,
                        similarity_score=similarity,
                        match_reasons=match_reasons
                    ))

        # Step 6: Sort by similarity (descending)
        duplicates.sort(key=lambda d: d.similarity_score, reverse=True)

        return duplicates
```

**3. Fingerprint Computation**:

```python
def _compute_fingerprint(self, artifact: Dict) -> ArtifactFingerprint:
    """Compute fingerprint for duplicate detection.

    Args:
        artifact: Artifact dict from project index

    Returns:
        ArtifactFingerprint with computed hashes
    """
    artifact_path = artifact["path"]
    metadata = artifact["metadata"]

    # Compute content hash (SHA256 of all files)
    content_hash = self._hash_artifact_contents(artifact_path)

    # Compute structure hash (file tree structure)
    structure_hash = self._hash_artifact_structure(artifact_path)

    # Compute metadata hash
    metadata_str = f"{metadata.title or ''}{metadata.description or ''}"
    metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()

    # Get file stats
    file_count = sum(1 for _ in artifact_path.rglob("*") if _.is_file())
    total_size = sum(f.stat().st_size for f in artifact_path.rglob("*") if f.is_file())

    return ArtifactFingerprint(
        artifact_path=artifact_path,
        artifact_name=artifact["name"],
        artifact_type=artifact["type"].value,
        content_hash=content_hash,
        metadata_hash=metadata_hash,
        structure_hash=structure_hash,
        title=metadata.title,
        description=metadata.description,
        tags=metadata.tags or [],
        file_count=file_count,
        total_size=total_size
    )

def _hash_artifact_contents(self, artifact_path: Path) -> str:
    """Hash all file contents in artifact.

    Args:
        artifact_path: Path to artifact directory

    Returns:
        SHA256 hash of concatenated file contents
    """
    hasher = hashlib.sha256()

    # Get all files, sorted for consistency
    files = sorted(artifact_path.rglob("*"))

    for file_path in files:
        if not file_path.is_file():
            continue

        # Skip ignored files
        if self._should_ignore(file_path):
            continue

        # Skip binary files
        if self._is_binary_file(file_path):
            continue

        try:
            with open(file_path, "rb") as f:
                hasher.update(f.read())
        except (OSError, IOError):
            # Skip unreadable files
            continue

    return hasher.hexdigest()

def _hash_artifact_structure(self, artifact_path: Path) -> str:
    """Hash artifact file tree structure.

    Args:
        artifact_path: Path to artifact directory

    Returns:
        SHA256 hash of file tree (paths only, not contents)
    """
    hasher = hashlib.sha256()

    # Get all files, sorted for consistency
    files = sorted(artifact_path.rglob("*"))

    for file_path in files:
        if self._should_ignore(file_path):
            continue

        # Use relative path for consistency
        rel_path = file_path.relative_to(artifact_path)
        hasher.update(str(rel_path).encode())

    return hasher.hexdigest()

def _get_match_reasons(
    self, fp1: ArtifactFingerprint, fp2: ArtifactFingerprint
) -> List[str]:
    """Determine why two fingerprints are similar.

    Args:
        fp1: First fingerprint
        fp2: Second fingerprint

    Returns:
        List of match reasons
    """
    reasons = []

    if fp1.content_hash == fp2.content_hash:
        reasons.append("exact_content")

    if fp1.structure_hash == fp2.structure_hash:
        reasons.append("same_structure")

    if fp1.metadata_hash == fp2.metadata_hash:
        reasons.append("exact_metadata")

    # Check tag overlap
    if fp1.tags and fp2.tags:
        self_tags = set(t.lower() for t in fp1.tags)
        other_tags = set(t.lower() for t in fp2.tags)
        jaccard = len(self_tags & other_tags) / len(self_tags | other_tags)
        if jaccard > 0.5:
            reasons.append("similar_tags")

    # Check title similarity
    if fp1.title and fp2.title and fp1.title.lower() == fp2.title.lower():
        reasons.append("same_title")

    return reasons
```

**4. Data Models**:

Add to `skillmeat/models.py`:

```python
@dataclass
class ArtifactFingerprint:
    """Fingerprint for duplicate detection."""
    artifact_path: Path
    artifact_name: str
    artifact_type: str
    content_hash: str
    metadata_hash: str
    structure_hash: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    file_count: int = 0
    total_size: int = 0

    def compute_similarity(self, other: 'ArtifactFingerprint') -> float:
        """Calculate similarity score (0.0 to 1.0)."""
        # Implementation as above

@dataclass
class DuplicatePair:
    """Pair of potentially duplicate artifacts."""
    artifact1_path: Path
    artifact1_name: str
    artifact2_path: Path
    artifact2_name: str
    similarity_score: float
    match_reasons: List[str] = field(default_factory=list)
```

**5. Config Settings**:

Add to `~/.skillmeat/config.toml`:

```toml
[duplicates]
# Minimum similarity threshold for duplicate detection (0.0 to 1.0)
threshold = 0.7

# Skip duplicate detection for artifacts with these tags
skip-tags = ["test", "example", "template"]

# Maximum file size for content hashing (bytes)
max-file-size = 10485760  # 10MB
```

---

## Performance Considerations

**For 100 Artifacts**:
- Fingerprint computation: ~0.5s (read all files, compute hashes)
- Pairwise comparison: ~0.1s (100 * 99 / 2 = 4950 comparisons)
- Total: ~0.6s ✅ (well under 5s target)

**Optimization Ideas**:
- **Early rejection**: Compare content hashes first (cheap), skip similarity if different
- **Bloom filters**: Quick rejection of non-duplicates before full comparison
- **Parallel fingerprinting**: Use ThreadPoolExecutor for I/O-bound fingerprint computation
- **Cache fingerprints**: Store fingerprints in cache alongside project index

```python
# Optimization: Cache fingerprints alongside project index
def _build_project_index(self, project_paths: List[Path]) -> List[Dict[str, any]]:
    indexes = []
    for project_path in project_paths:
        # ... existing code ...

        # NEW: Pre-compute fingerprints
        fingerprints = []
        for artifact in artifacts:
            fp = self._compute_fingerprint(artifact)
            fingerprints.append(fp)

        indexes.append({
            "project_path": project_path,
            "artifacts": artifacts,
            "fingerprints": fingerprints,  # NEW: cached fingerprints
            "last_modified": mtime,
        })

    return indexes
```

---

## Error Handling

**Hash Collisions**:
- SHA256 collisions are extremely rare (2^256 space)
- If content hashes match, verify structure and metadata
- Log warning if suspicious collision detected

**Large Files**:
- Skip files larger than `max-file-size` config
- Log warning for skipped files
- Continue with remaining files

**Permission Errors**:
- Skip unreadable files (same as content search)
- Log debug message
- Continue with remaining files

**Binary Files**:
- Skip binary files for content hashing (same logic as search)
- Include in structure hash only

---

## Testing Strategy for P2-003

### Test Structure

**File**: `tests/test_duplicate_detection.py`

**Test Classes**:
1. `TestFingerprintComputation` (5 tests)
   - Compute content hash
   - Compute structure hash
   - Compute metadata hash
   - Handle binary files
   - Handle large files

2. `TestSimilarityCalculation` (5 tests)
   - Exact content match (1.0 score)
   - Partial metadata match
   - Tag overlap (Jaccard similarity)
   - Structure match only
   - No similarity (0.0 score)

3. `TestDuplicateDetection` (5 tests)
   - Find exact duplicates
   - Find similar artifacts (above threshold)
   - Skip below threshold
   - Handle no duplicates
   - Handle single artifact

4. `TestMatchReasons` (3 tests)
   - Identify exact content match
   - Identify structure match
   - Identify metadata match

5. `TestPerformance` (2 tests)
   - 100 artifacts < 5s
   - Cached fingerprints faster

**Total**: 20 tests

---

## Integration Points

### Reuse from P2-002

**Project Discovery**:
```python
# Already implemented in P2-002
project_paths = self._discover_projects()
```

**Project Indexing**:
```python
# Already implemented in P2-002
project_indexes = self._build_project_index(project_paths)
```

**Caching**:
```python
# Already implemented in P2-002
# Can extend to cache fingerprints alongside index
cache_key = self._compute_cache_key(project_paths)
cached_index = self._get_cached_index(cache_key, project_paths)
```

### CLI Integration (for P2-004)

**Command**: `skillmeat find-duplicates`

```python
@main.command()
@click.option("--threshold", type=float, default=0.7, help="Similarity threshold (0.0-1.0)")
@click.option("--json", is_flag=True, help="Output JSON format")
def find_duplicates_cmd(threshold: float, json: bool):
    """Find duplicate artifacts across projects."""
    search_mgr = SearchManager()

    duplicates = search_mgr.find_duplicates(threshold=threshold)

    if json:
        # JSON output
        import json as json_lib
        output = [
            {
                "artifact1": str(d.artifact1_path),
                "artifact2": str(d.artifact2_path),
                "similarity": d.similarity_score,
                "reasons": d.match_reasons
            }
            for d in duplicates
        ]
        click.echo(json_lib.dumps(output, indent=2))
    else:
        # Rich formatted output
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"Duplicate Artifacts (threshold: {threshold})")
        table.add_column("Artifact 1")
        table.add_column("Artifact 2")
        table.add_column("Similarity", justify="right")
        table.add_column("Reasons")

        for dup in duplicates:
            table.add_row(
                dup.artifact1_name,
                dup.artifact2_name,
                f"{dup.similarity_score:.2%}",
                ", ".join(dup.match_reasons)
            )

        console.print(table)
```

---

## Files to Create/Modify

### Create:
- `tests/test_duplicate_detection.py` (20 tests)
- `.claude/worknotes/ph2-intelligence/P2-003-implementation-notes.md`

### Modify:
- `skillmeat/core/search.py`:
  - Add `find_duplicates()` method
  - Add `_compute_fingerprint()` method
  - Add `_hash_artifact_contents()` method
  - Add `_hash_artifact_structure()` method
  - Add `_get_match_reasons()` method
- `skillmeat/models.py`:
  - Add `ArtifactFingerprint` dataclass
  - Add `DuplicatePair` dataclass

---

## Success Criteria Checklist

- [ ] find_duplicates() returns DuplicatePair list
- [ ] Similarity scores calculated correctly (0.0 to 1.0)
- [ ] Threshold filtering works
- [ ] Match reasons populated accurately
- [ ] Handles hash collisions gracefully
- [ ] Performance <5s for 100 artifacts
- [ ] All 20 tests passing
- [ ] Integration with P2-002 project discovery verified

---

## Risk Assessment

**Low Risk**:
- ✅ Project discovery proven (P2-002 complete)
- ✅ SHA256 hashing well-established
- ✅ Data models straightforward

**Medium Risk**:
- ⚠️ Similarity scoring algorithm tuning (weights may need adjustment)
- ⚠️ Performance with large artifacts (>10MB files)
- ⚠️ Binary file handling (skip vs include in structure hash)

**Mitigation**:
- Make similarity weights configurable
- Implement file size limits (skip large files)
- Test with various artifact sizes
- Add performance benchmarks

---

## Estimated Effort

**Original Estimate**: 2 pts

**Breakdown**:
- Fingerprint computation: 0.5 pts
- Similarity algorithm: 0.5 pts
- Duplicate detection: 0.5 pts
- Testing: 0.5 pts

**Total**: 2 pts (matches original estimate)

---

## Summary

P2-002 delivers a complete, tested, performant cross-project search foundation. P2-003 extends this by adding duplicate detection:

1. **Fingerprint computation** (content, structure, metadata hashes)
2. **Similarity scoring** (weighted multi-factor comparison)
3. **Duplicate detection** (pairwise comparison with threshold)
4. **Match reasons** (explain why artifacts are similar)

All project discovery and indexing logic is proven and ready to reuse. The main work is implementing the fingerprinting and similarity algorithms.

**Ready for P2-003 implementation!**
