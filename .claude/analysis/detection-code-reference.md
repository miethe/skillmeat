# Artifact Detection & Indexing - Code Reference Map

**Quick reference for key implementations and locations**

---

## File Locations

### Core Detection

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `skillmeat/core/artifact_detection.py` | Baseline detection (canonical) | `ArtifactType`, `DetectionResult`, `detect_artifact()`, `infer_artifact_type()`, `ARTIFACT_SIGNATURES` |
| `skillmeat/core/marketplace/heuristic_detector.py` | GitHub-specific heuristics | `HeuristicDetector`, `detect_artifacts_in_tree()`, `normalize_score()` |
| `skillmeat/core/marketplace/github_scanner.py` | GitHub API scanning | `GitHubScanner.scan_repository()`, `compute_artifact_hash_from_tree()` |

### Database

| File | Purpose | Key Classes |
|------|---------|-------------|
| `skillmeat/cache/models.py` | ORM models | `MarketplaceSource`, `MarketplaceCatalogEntry` |
| `skillmeat/cache/repositories.py` | Data access | `MarketplaceSourceRepository`, `MarketplaceCatalogRepository`, `MarketplaceTransactionHandler` |
| `skillmeat/cache/migrations/versions/20260124_1200_add_fts5_catalog_search.py` | FTS5 search table | Virtual table for full-text search |

### API & Routing

| File | Purpose | Key Functions |
|------|---------|----------------|
| `skillmeat/api/routers/marketplace_sources.py` | Scan endpoints | `_perform_scan()`, `_extract_frontmatter_for_artifact()`, `_extract_frontmatter_batch()` |
| `skillmeat/api/schemas/marketplace.py` | Request/response models | `DetectedArtifact`, `ScanResultDTO`, `CatalogEntryResponse` |

### Utilities

| File | Purpose | Key Functions |
|------|---------|----------------|
| `skillmeat/utils/metadata.py` | Frontmatter parsing | `extract_frontmatter()` |
| `skillmeat/core/path_tags.py` | Path-based tagging | `PathSegmentExtractor`, `PathTagConfig` |

---

## Detection Workflow Trace

### 1. Scan Initiation

**Endpoint**: `POST /marketplace/sources/{id}/rescan`

**Handler**: `skillmeat/api/routers/marketplace_sources.py:rescan_source()`

```python
# Line 2191+
async def rescan_source(source_id: str, request: ScanRequest = None) -> ScanResultDTO:
    source = source_repo.get_by_id(source_id)
    return await _perform_scan(source, source_repo, catalog_repo, transaction_handler)
```

### 2. Scan Operation

**Function**: `_perform_scan()` (lines 937-1226)

**Main Steps**:

| Step | Line | Action |
|------|------|--------|
| 1 | 963-964 | Mark source as "scanning" |
| 2 | 968 | Create GitHubScanner instance |
| 3 | 978-1036 | Check single_artifact_mode |
| 4 | 1042-1049 | Call scanner.scan_repository() |
| 5 | 1052-1064 | Load PathTagConfig and create extractor |
| 6 | 1066-1070 | Compute counts_by_type |
| 7 | 1073 | Start atomic transaction |
| 8 | 1075-1086 | Update source status and counts |
| 9 | 1096-1108 | Pre-compute batch frontmatter (if enabled) |
| 10 | 1111-1183 | Convert detected artifacts to catalog entries |
| 11 | 1186 | Merge entries with existing catalog |
| 12 | 1203-1225 | Handle errors gracefully |

### 3. Repository Scanning

**Class**: `GitHubScanner` in `skillmeat/core/marketplace/github_scanner.py`

**Method**: `scan_repository(owner, repo, ref, root_hint, session, manual_mappings)`

**Internal Process**:

```python
# Line 194+
def __init__(self, token: Optional[str] = None, config: Optional[ScanConfig] = None):
    self.client = get_github_client()
    self.detector = HeuristicDetector(enable_frontmatter_detection=enable_frontmatter)
    self.dedup_engine = DeduplicationEngine(session)

def scan_repository(self, owner, repo, ref, root_hint, session, manual_mappings):
    # 1. Fetch repo tree via GitHub API
    tree = self.client.get_repo_tree(owner, repo, ref)

    # 2. Apply manual overrides if provided
    if manual_mappings:
        # Override artifact types for specific paths

    # 3. Detect artifacts using heuristics
    artifacts = self.detector.analyze_paths(
        tree_items,
        base_url=f"https://github.com/{owner}/{repo}",
        detected_sha=resolved_sha
    )

    # 4. Deduplicate against existing catalog
    for artifact in artifacts:
        hash = compute_artifact_hash_from_tree(artifact.path, tree)
        if hash in existing_hashes:
            artifact.status = "existing"  # Mark for preservation

    return ScanResultDTO(artifacts=artifacts, ...)
```

### 4. Heuristic Detection

**Class**: `HeuristicDetector` in `skillmeat/core/marketplace/heuristic_detector.py`

**Method**: `analyze_paths(file_paths, base_url, detected_sha) → List[DetectedArtifact]`

**Process** (simplified):

```python
# Line 249+
def analyze_paths(self, file_paths: List[str], base_url: str, detected_sha: str):
    results = []

    # Group files by potential artifact directories
    for artifact_path in self._group_by_artifacts(file_paths):
        files_in_artifact = [f for f in file_paths if f.startswith(artifact_path)]

        # Score using two-layer detection
        artifact_type, confidence, breakdown = self.score_directory_v2(
            files_in_artifact,
            artifact_path
        )

        if confidence >= self.config.min_confidence:
            result = DetectedArtifact(
                artifact_type=artifact_type,
                name=Path(artifact_path).name,
                path=artifact_path,
                confidence_score=confidence,
                raw_score=breakdown['raw_score'],
                score_breakdown=breakdown,
                upstream_url=f"{base_url}/tree/{ref}/{artifact_path}",
                detected_sha=detected_sha
            )
            results.append(result)

    return results
```

### 5. Scoring (Two Layers)

**Method**: `score_directory_v2(files, artifact_path) → Tuple[ArtifactType, int, Dict]`

**Layer 1 - Baseline Detection** (from `skillmeat.core.artifact_detection`):

```python
# Apply baseline detection rules
baseline_result = detect_artifact(
    Path(artifact_path),
    container_type=None,
    mode="heuristic"
)
confidence = baseline_result.confidence  # 0-100
artifact_type = baseline_result.artifact_type
```

**Layer 2 - Marketplace Signals** (GitHub-specific):

```python
raw_score = 0

# Signal 1: Directory name matching (10 pts)
if self._matches_dir_pattern(artifact_path):
    raw_score += 10

# Signal 2: Manifest detection (20 pts)
if self._has_manifest(artifact_path, files):
    raw_score += 20

# Signal 3: Skill manifest bonus (40 pts)
if artifact_type == "skill" and self._has_skill_manifest(files):
    raw_score += 40

# Signal 4: Extension matching (5 pts)
if self._has_expected_extensions(files):
    raw_score += 5

# Signal 5: Parent hint (15 pts)
if self._has_parent_hint(artifact_path):
    raw_score += 15

# Signal 6: Frontmatter presence (15 pts)
if self._has_frontmatter_file(files):
    raw_score += 15

# Signal 7: Container hint bonus (25 pts)
if self._container_hint_matches(artifact_path, artifact_type):
    raw_score += 25

# Signal 8: Frontmatter type (30 pts)
if explicit_type := self._parse_frontmatter_type(files):
    raw_score += 30
    artifact_type = explicit_type

# Normalize to 0-100 scale
confidence = normalize_score(raw_score)

return artifact_type, confidence, {
    'raw_score': raw_score,
    'signals': {
        'dir_name': 10 if matched else 0,
        'manifest': 20 if has_manifest else 0,
        # ... all 8 signals
    }
}
```

### 6. Frontmatter Extraction Decision Tree

**In `_perform_scan()` around line 1096-1149**:

```python
if indexing_enabled:
    # Pre-compute batch extraction for efficiency
    skill_artifacts = [a for a in artifacts if a.artifact_type == "skill"]

    if len(skill_artifacts) >= BATCH_CLONE_THRESHOLD:  # 3 or more
        # Use single git clone for all SKILL.md files
        batch_frontmatter = _extract_frontmatter_batch(source, skill_artifacts)
        use_batch_extraction = True
    else:
        use_batch_extraction = False
        batch_frontmatter = {}

# For each artifact:
if use_batch_extraction and artifact.artifact_type == "skill":
    search_metadata = batch_frontmatter[artifact.name]
else:
    # Fall back to per-artifact extraction
    search_metadata = _extract_frontmatter_for_artifact(scanner, source, artifact)
```

### 7. Per-Artifact Frontmatter Extraction

**Function**: `_extract_frontmatter_for_artifact()` (lines 550-644)

```python
def _extract_frontmatter_for_artifact(
    scanner: GitHubScanner,
    source: MarketplaceSource,
    artifact: DetectedArtifact,
) -> Dict[str, Any]:
    result = {"title": None, "description": None, "search_tags": None, "search_text": None}

    try:
        # Build path to manifest (SKILL.md, COMMAND.md, etc.)
        artifact_path = artifact.path.rstrip("/")
        if artifact.artifact_type == "skill":
            skill_md_path = f"{artifact_path}/SKILL.md"
        elif artifact.artifact_type == "command":
            skill_md_path = f"{artifact_path}.md"
        # ... etc

        # Fetch content from GitHub API
        content = scanner.client.get_file_content(
            source.owner, source.repo_name, skill_md_path, source.ref
        )

        # Extract YAML frontmatter
        frontmatter = extract_frontmatter(content)
        if not frontmatter:
            return result

        # Extract fields
        result["title"] = (frontmatter.get("title") or frontmatter.get("name"))[:200]
        result["description"] = frontmatter.get("description")

        # Parse tags (handle list or comma-separated string)
        tags = frontmatter.get("tags", [])
        if isinstance(tags, list):
            result["search_tags"] = tags
        elif isinstance(tags, str):
            result["search_tags"] = [t.strip() for t in tags.split(",")]

        # Build combined search text
        search_parts = [artifact.name]
        if result["title"]:
            search_parts.append(result["title"])
        if result["description"]:
            search_parts.append(result["description"])
        if result["search_tags"]:
            search_parts.extend(result["search_tags"])
        result["search_text"] = " ".join(search_parts)

    except Exception as e:
        logger.warning(f"Failed to extract frontmatter: {e}")
        # Non-blocking - continue with empty result

    return result
```

### 8. Batch Frontmatter Extraction

**Function**: `_extract_frontmatter_batch()` (lines 790-920)

**Key Steps**:

| Step | Lines | Action |
|------|-------|--------|
| 1 | 834-840 | Call `_clone_repo_sparse()` with patterns `["**/SKILL.md", "SKILL.md"]` |
| 2 | 842-847 | Return empty if clone fails (non-blocking) |
| 3 | 849-860 | For each artifact, read SKILL.md from cloned disk |
| 4 | 862-880 | Extract frontmatter and parse fields |
| 5 | 881-899 | Handle tags (list or comma-separated) |
| 6 | 894-910 | Build search_text from combined fields |

**Sparse Clone Helper** (lines 655-787):

```python
def _clone_repo_sparse(owner, repo, ref, patterns, timeout=60):
    """Use git sparse-checkout + partial clone to minimize data transfer."""
    temp_dir = tempfile.mkdtemp(prefix="skillmeat-sparse-")

    subprocess.run(["git", "init"], cwd=temp_dir)
    subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=temp_dir)
    subprocess.run(["git", "config", "extensions.partialClone", "origin"], cwd=temp_dir)

    # Write sparse-checkout patterns to .git/info/sparse-checkout
    patterns_file = Path(temp_dir) / ".git" / "info" / "sparse-checkout"
    patterns_file.write_text("\n".join(patterns) + "\n")

    subprocess.run(
        ["git", "fetch", "--depth=1", "--filter=blob:none", "origin", ref],
        cwd=temp_dir
    )
    subprocess.run(["git", "checkout", "FETCH_HEAD"], cwd=temp_dir)

    return Path(temp_dir)
```

### 9. Database Persistence

**In atomic transaction** (lines 1073-1186):

```python
with transaction_handler.scan_update_transaction(source_id) as ctx:
    # Update source
    ctx.update_source_status(status="success", artifact_count=len(artifacts))

    # Create catalog entries
    for artifact in artifacts:
        entry = MarketplaceCatalogEntry(
            id=str(uuid.uuid4()),
            source_id=source_id,
            artifact_type=artifact.artifact_type,
            name=artifact.name,
            path=artifact.path,
            upstream_url=artifact.upstream_url,
            confidence_score=artifact.confidence_score,
            raw_score=artifact.raw_score,
            score_breakdown=artifact.score_breakdown,
            detected_sha=artifact.detected_sha,
            status="new" or "existing" (from dedup),
            # Frontmatter fields
            title=search_metadata["title"],
            description=search_metadata["description"],
            search_tags=json.dumps(search_metadata["search_tags"]),
            search_text=search_metadata["search_text"],
            # Path segments (if extracted)
            path_segments=path_segments_json,
        )
        new_entries.append(entry)

    # Merge with existing (preserves imports)
    merge_result = ctx.merge_catalog_entries(new_entries)
    ctx.commit()
```

---

## Key Data Structures

### DetectedArtifact (schema)

**File**: `skillmeat/api/schemas/marketplace.py`

```python
@dataclass
class DetectedArtifact:
    artifact_type: str
    name: str
    path: str
    upstream_url: str
    confidence_score: int  # 0-100
    detected_version: Optional[str]
    detected_sha: Optional[str]
    raw_score: Optional[int]
    score_breakdown: Optional[Dict[str, Any]]
    status: Optional[str]  # "new", "updated", "removed", "imported"
    excluded_at: Optional[str]  # ISO format timestamp
    excluded_reason: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

### ScanResultDTO

**File**: `skillmeat/api/schemas/marketplace.py`

```python
@dataclass
class ScanResultDTO:
    source_id: str
    status: str  # "success" or "error"
    artifacts_found: int
    new_count: int
    updated_count: int
    removed_count: int
    unchanged_count: int
    scan_duration_ms: int
    errors: List[str]
    scanned_at: datetime
    artifacts: List[DetectedArtifact]
    # Added after scan
    updated_imports: List[str]
    preserved_count: int
```

### MarketplaceCatalogEntry (ORM)

**File**: `skillmeat/cache/models.py` (lines 1516+)

Key search fields:
- `title`: str (200 chars max)
- `description`: str (unlimited)
- `search_tags`: JSON array
- `search_text`: concatenated text for FTS

---

## Signal Weights Reference

**From** `skillmeat/core/marketplace/heuristic_detector.py` (lines 202-212):

```python
dir_name_weight = 10
manifest_weight = 20
extension_weight = 5
parent_hint_weight = 15
frontmatter_weight = 15
container_hint_weight = 25
frontmatter_type_weight = 30
skill_manifest_bonus = 40

# Total possible: 160 (normalized to 100)
# Minimum threshold: 30 (configurable)
```

---

## Configuration Points

### MarketplaceSource Config Fields

| Field | Type | Purpose | Default |
|-------|------|---------|---------|
| `enable_frontmatter_detection` | bool | Parse YAML for type hints | False |
| `indexing_enabled` | Optional[bool] | Extract search metadata | None (use global) |
| `path_tag_config` | JSON str | Path-based tag rules | None (defaults) |
| `single_artifact_mode` | bool | Treat repo as one artifact | False |
| `single_artifact_type` | str | Type when single mode | None |

### DetectionConfig

**In `heuristic_detector.py`** (lines 163-212):

| Parameter | Type | Default |
|-----------|------|---------|
| `min_confidence` | int | 30 |
| `max_depth` | int | 10 |
| `depth_penalty` | int | 1 |

### Thresholds

| Name | Location | Value | Purpose |
|------|----------|-------|---------|
| `BATCH_CLONE_THRESHOLD` | marketplace_sources.py:652 | 3 | Min artifacts for batch extraction |
| `CONFIDENCE_THRESHOLD` | marketplace_sources.py:118 | 30 | Hide low-quality entries |

---

## Error Handling Patterns

### Detection Errors

```python
try:
    result = detect_artifact(path, mode="strict")
except DetectionError as e:
    # In strict mode - artifact couldn't be detected
    logger.error(f"Detection failed: {e}")

# Heuristic mode - always returns result
result = detect_artifact(path, mode="heuristic")
# result.confidence may be 0-100
```

### Scan Errors

```python
try:
    scan_result = scanner.scan_repository(...)
except GitHubClientError:
    # Network/API error - caught and returned in ScanResultDTO
except RateLimitError:
    # Rate limited - check reset time
```

### Frontmatter Extraction

```python
try:
    frontmatter = extract_frontmatter(content)
except Exception as e:
    logger.warning(f"Frontmatter parse failed: {e}")
    # Return empty result - non-blocking
    frontmatter = {}
```

---

## Performance Notes

### Optimizations

1. **SQLite JSON Extraction** (github_scanner.py:114-132)
   - Use `json_extract()` for hash queries vs full parse
   - ~10x improvement for large catalogs

2. **Batch Frontmatter Extraction** (lines 1096-1108)
   - Single git clone vs N API calls
   - Threshold: 3+ artifacts

3. **Sparse Checkout** (_clone_repo_sparse)
   - `--filter=blob:none` + `--depth=1`
   - Only fetch SKILL.md files

4. **Atomic Transactions** (scan_update_transaction)
   - Group source + catalog updates
   - Single commit vs multiple

### Bottlenecks

1. GitHub API rate limits (60 req/hr unauthenticated)
2. Network latency for per-artifact extraction
3. Frontmatter parsing for large manifests
4. SQLite writes for large catalogs (not batched)

