---
type: progress
prd: "marketplace-github-ingestion-remediation"
phase: 3
title: "Import Downloads"
status: "completed"
started: "2025-12-26T18:00:00Z"
completed: "2025-12-26T20:30:00Z"

overall_progress: 100
completion_estimate: "complete"

total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "REM-3.1"
    description: "Implement _download_artifact - fetch files from GitHub API"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "60min"
    priority: "high"
    file: "skillmeat/core/marketplace/import_coordinator.py"
    commit: "pending"

  - id: "REM-3.2"
    description: "Implement _update_manifest - update collection manifest.toml"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "30min"
    priority: "high"
    file: "skillmeat/core/marketplace/import_coordinator.py"
    commit: "pending"

  - id: "REM-3.3"
    description: "Wire Downloads - replace stub in import_coordinator.py"
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REM-3.1", "REM-3.2"]
    estimated_effort: "30min"
    priority: "high"
    file: "skillmeat/core/marketplace/import_coordinator.py"
    commit: "pending"

parallelization:
  batch_1: ["REM-3.1", "REM-3.2"]
  batch_2: ["REM-3.3"]
  critical_path: ["REM-3.1", "REM-3.3"]
  estimated_total_time: "2h"

blockers: []

success_criteria:
  - _download_artifact fetches files from GitHub API successfully ✅
  - _update_manifest updates manifest.toml with new artifact entry ✅
  - Import flow completes end-to-end (catalog entry → downloaded files → manifest updated) ✅
  - pytest tests/core/marketplace/test_import_coordinator.py passes ✅ (36/36)

files_modified:
  - "skillmeat/core/marketplace/import_coordinator.py"
  - "tests/core/marketplace/test_import_coordinator.py"
---

# Phase 3: Import Downloads

**Status:** ✅ Completed | **Owner:** python-backend-engineer | **Est. Effort:** 2 hours

## Overview

Implement the download functionality in the import coordinator to complete the marketplace-to-collection import flow. Currently the import coordinator stubs out actual file downloads.

## Rationale

This phase was originally deferred but is now being implemented to complete the full import workflow. Users need to be able to download discovered artifacts from the marketplace into their local collection.

## Orchestration Quick Reference

**Batch Execution:**
- Batch 1: REM-3.1, REM-3.2 (parallel - independent methods)
- Batch 2: REM-3.3 (sequential - requires both methods)

### Task Delegation Commands

```python
Task("python-backend-engineer", """REM-3.1: Implement _download_artifact method.

File: skillmeat/core/marketplace/import_coordinator.py

Implement the _download_artifact method to:
1. Fetch artifact files from GitHub API
2. Create local directory structure in collection
3. Download all files in the artifact directory
4. Handle binary vs text files appropriately

Reference existing GitHub API patterns in:
- skillmeat/core/marketplace/github_scanner.py (GitHubScanner._fetch_tree, _get_file_content)

Expected signature:
async def _download_artifact(
    self,
    catalog_entry: MarketplaceCatalogEntry,
    target_dir: Path,
) -> DownloadResult:
    '''Download artifact files from GitHub to target directory.'''

The method should:
- Parse the upstream_url to get owner/repo/path
- Use GitHub API to get directory tree
- Download each file to target_dir
- Return success/failure status with downloaded file count""")
```

```python
Task("python-backend-engineer", """REM-3.2: Implement _update_manifest method.

File: skillmeat/core/marketplace/import_coordinator.py

Implement the _update_manifest method to:
1. Read existing manifest.toml from collection
2. Add new artifact entry with proper metadata
3. Write updated manifest atomically

Reference manifest patterns in:
- skillmeat/storage/manifest.py (ManifestManager)
- skillmeat/core/artifact.py (ArtifactSpec)

Expected signature:
def _update_manifest(
    self,
    collection_path: Path,
    artifact_spec: ArtifactSpec,
) -> None:
    '''Add artifact to collection manifest.toml.'''

The manifest entry should include:
- name, type, source, version
- scope (user or local)
- aliases (if any)
- installed_at timestamp""")
```

```python
Task("python-backend-engineer", """REM-3.3: Wire download flow in import_coordinator.py.

File: skillmeat/core/marketplace/import_coordinator.py

Find the stub/placeholder in the import flow and wire it to use:
1. _download_artifact to fetch files
2. _update_manifest to update collection manifest

Current stub likely returns early or logs "download not implemented".
Replace with actual download flow:

1. Get catalog entry details
2. Determine target directory based on artifact type and scope
3. Call _download_artifact to fetch files
4. Call _update_manifest to register in collection
5. Update import status to completed

Return proper ImportResult with downloaded file paths.""")
```

## Tasks

| Task ID | Description | Status | Dependencies | Est. |
|---------|-------------|--------|--------------|------|
| REM-3.1 | Implement _download_artifact | Pending | None | 60min |
| REM-3.2 | Implement _update_manifest | Pending | None | 30min |
| REM-3.3 | Wire download flow | Pending | REM-3.1, REM-3.2 | 30min |

## Verification Steps

After completing all tasks:

```bash
# 1. Run unit tests
pytest tests/core/marketplace/test_import_coordinator.py -v

# 2. Integration test - import from marketplace
# First ensure a source is scanned:
curl -X POST http://localhost:8000/api/v1/marketplace/sources/{source_id}/rescan

# Then import an artifact:
curl -X POST http://localhost:8000/api/v1/marketplace/import \
  -H "Content-Type: application/json" \
  -d '{"catalog_entry_id": "<entry_id>", "target_scope": "user"}'

# 3. Verify files downloaded
ls -la ~/.skillmeat/collection/artifacts/

# 4. Verify manifest updated
cat ~/.skillmeat/collection/manifest.toml
```

## Blockers

None identified.

## Work Log

| Timestamp | Action | Details |
|-----------|--------|---------|
| 2025-12-26 18:00 | Phase started | Beginning Phase 3 implementation |
| 2025-12-26 19:00 | REM-3.1 completed | Implemented _download_artifact with GitHub API, rate limiting, retry logic |
| 2025-12-26 19:30 | REM-3.2 completed | Implemented _update_manifest with ManifestManager and Artifact model |
| 2025-12-26 20:00 | REM-3.3 completed | Wired download flow in _process_entry method |
| 2025-12-26 20:30 | Tests fixed | Added mocking for HTTP calls, all 36 tests passing |
| 2025-12-26 20:30 | Phase completed | All success criteria met |
