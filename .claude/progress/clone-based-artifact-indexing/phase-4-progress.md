---
type: progress
prd: clone-based-artifact-indexing
phase: 4
title: Deep Indexing
status: completed
started: null
updated: '2026-01-25'
completion: 0
total_tasks: 6
completed_tasks: 6
tasks:
- id: DEEP-101
  title: Implement get_deep_sparse_patterns()
  description: Generate patterns for full artifact directory clone (not just manifest
    files)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 45m
  story_points: 1
  acceptance_criteria:
  - Returns patterns like ['{artifact_path}/**' for each artifact]
  - Tested with large repos (clones only artifact dirs, not codebase)
  - Integrates with existing sparse-checkout infrastructure
- id: DEEP-102
  title: Implement extract_deep_search_text()
  description: Extract searchable text from all files in artifact directory; filter
    by type; skip large files
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 2
  acceptance_criteria:
  - 'Extracts text from: *.md, *.yaml, *.yml, *.json, *.txt, *.py, *.ts, *.js'
  - Skips files >100KB (configurable)
  - Skips binary files
  - Normalizes whitespace and strips code comments
  - Returns concatenated searchable text
  - Returns list of indexed file paths
- id: DEEP-103
  title: Add file size limits and binary filtering
  description: 'Implement safeguards for deep indexing: file size limits, binary detection,
    truncation'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DEEP-102
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - MAX_FILE_SIZE_BYTES configurable (default 100KB)
  - Binary file detection (check for null bytes)
  - Large text files truncated with '...[truncated]' marker
  - Total deep_search_text capped at 1MB per artifact
- id: DEEP-104
  title: Add deep_indexing_enabled to SourceCreateRequest
  description: Update schema to accept deep_indexing_enabled toggle when creating/updating
    sources
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 45m
  story_points: 1
  acceptance_criteria:
  - Field accepted in POST /marketplace/sources
  - Field accepted in PATCH /marketplace/sources/{id}
  - Defaults to false
  - Description explains performance impact
- id: DEEP-105
  title: Add deep_match and matched_file to search response
  description: Update search response schema to indicate deep index matches
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 45m
  story_points: 1
  acceptance_criteria:
  - 'deep_match: bool - whether match came from deep-indexed content'
  - 'matched_file: Optional[str] - file path where match was found'
  - Fields populated in search endpoint logic
  - Documentation updated
- id: DEEP-106
  title: Integrate deep_search_text with FTS5 queries
  description: Update search query to include deep_search_text column; rank deep matches
    appropriately
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DEEP-105
  model: opus
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - FTS5 MATCH queries include deep_search_text
  - Deep matches ranked slightly lower than title/description matches
  - Searches return results from deep_search_text when appropriate
  - Performance acceptable (<500ms for typical queries)
parallelization:
  batch_1:
  - DEEP-101
  - DEEP-102
  - DEEP-104
  - DEEP-105
  batch_2:
  - DEEP-103
  - DEEP-106
  critical_path:
  - DEEP-102
  - DEEP-103
  estimated_total_time: 7h
blockers: []
quality_gates:
- Deep indexing extracts text from all supported file types
- Large files (>100KB) properly skipped
- FTS5 searches include deep_search_text results
- deep_match flag correctly set in responses
- Performance impact of deep indexing measured and acceptable
- Backward compatibility maintained (default deep_indexing_enabled=false)
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 4: Deep Indexing

**Plan:** `docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md`
**SPIKE:** `docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
**Status:** Pending
**Story Points:** 9 total
**Duration:** 1-2 days
**Dependencies:** Phase 3 complete

## Orchestration Quick Reference

**Batch 1** (Parallel - 4h estimated):
- DEEP-101 -> `python-backend-engineer` (sonnet) - get_deep_sparse_patterns()
- DEEP-102 -> `python-backend-engineer` (opus) - extract_deep_search_text()
- DEEP-104 -> `python-backend-engineer` (sonnet) - Schema update for deep_indexing_enabled
- DEEP-105 -> `python-backend-engineer` (sonnet) - Search response schema update

**Batch 2** (After Batch 1 - 2.5h estimated):
- DEEP-103 -> `python-backend-engineer` (sonnet) - File size limits and binary filtering
- DEEP-106 -> `python-backend-engineer` (opus) - FTS5 query integration

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "DEEP-101: Implement get_deep_sparse_patterns()

Add to skillmeat/core/clone_target.py:

def get_deep_sparse_patterns(artifacts: List[DetectedArtifact]) -> List[str]:
    '''Generate patterns for full artifact directory clone.'''
    return [f'{artifact.path}/**' for artifact in artifacts]

This is used when deep_indexing_enabled=True to clone entire artifact
directories instead of just manifest files.

Contrast with get_sparse_checkout_patterns() which clones only manifests.", model="sonnet")

Task("python-backend-engineer", "DEEP-102: Implement extract_deep_search_text()

Create function in skillmeat/core/manifest_extractors.py.

Signature:
def extract_deep_search_text(artifact_dir: Path) -> Tuple[str, List[str]]:
    '''Extract searchable text from all files in artifact directory.

    Returns:
        Tuple of (concatenated_text, list_of_indexed_files)
    '''

Indexable patterns: ['*.md', '*.yaml', '*.yml', '*.json', '*.txt', '*.py', '*.ts', '*.js']

Logic:
1. Glob for each pattern recursively
2. For each file:
   - Check size < MAX_FILE_SIZE_BYTES (100KB default)
   - Check not binary (no null bytes in first 1KB)
   - Read content, normalize whitespace
   - Optionally strip code comments (// and #)
3. Concatenate all text with spaces
4. Return (full_text, [file_paths])

Keep total text under 1MB per artifact (truncate if needed).")

Task("python-backend-engineer", "DEEP-104: Add deep_indexing_enabled to SourceCreateRequest

Update skillmeat/api/schemas/marketplace.py.

Add to SourceCreateRequest and SourceUpdateRequest:
deep_indexing_enabled: bool = Field(
    default=False,
    description='Enable deep indexing for enhanced full-text search. '
                'Clones entire artifact directories. May increase scan time.'
)

Router should pass this through to source creation/update.", model="sonnet")

Task("python-backend-engineer", "DEEP-105: Add deep_match and matched_file to search response

Update skillmeat/api/schemas/marketplace.py search response.

Add to ArtifactSearchResult or CatalogEntryResponse:
deep_match: bool = Field(
    default=False,
    description='True if match came from deep-indexed content rather than metadata'
)
matched_file: Optional[str] = Field(
    default=None,
    description='File path where match was found (deep index matches only)'
)

These help users understand why a result matched their query.", model="sonnet")
```

**Batch 2:**
```
Task("python-backend-engineer", "DEEP-103: Add file size limits and binary filtering

Enhance extract_deep_search_text() with safeguards.

Add constants at module level:
MAX_FILE_SIZE_BYTES = int(os.getenv('DEEP_INDEX_MAX_FILE_SIZE', 100_000))  # 100KB
MAX_TOTAL_TEXT_BYTES = int(os.getenv('DEEP_INDEX_MAX_TOTAL', 1_000_000))  # 1MB

Add helper:
def _is_binary_file(file_path: Path) -> bool:
    '''Check if file appears to be binary by looking for null bytes.'''
    with open(file_path, 'rb') as f:
        chunk = f.read(1024)
        return b'\\x00' in chunk

Add truncation:
- If file > MAX_FILE_SIZE_BYTES: skip and log
- If total text > MAX_TOTAL_TEXT_BYTES: truncate and append '...[truncated]'

Log skipped files at DEBUG level.", model="sonnet")

Task("python-backend-engineer", "DEEP-106: Integrate deep_search_text with FTS5 queries

Update search logic in skillmeat/api/routers/marketplace_sources.py.

Current query likely uses:
SELECT ... FROM catalog_fts WHERE catalog_fts MATCH ?

Update to include deep_search_text in ranking:
- Matches in title/description should rank higher
- Matches in deep_search_text should rank lower but still appear
- Use FTS5 bm25() or similar for ranking

When a match is from deep_search_text:
- Set deep_match=True in response
- Optionally extract matched_file from deep_index_files JSON

Test with various queries to ensure ranking is sensible.")
```

---

## Success Criteria

- [ ] Deep indexing extracts text from all supported file types
- [ ] Large files (>100KB) properly skipped
- [ ] FTS5 searches include deep_search_text results
- [ ] deep_match flag correctly set in responses
- [ ] Performance impact of deep indexing measured and acceptable
- [ ] Backward compatibility maintained (default deep_indexing_enabled=false)

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
