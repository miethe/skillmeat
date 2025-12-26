# Marketplace Gaps - Exact File Locations

## Gap 1: Heuristic Detector Disconnected

### File 1: `skillmeat/core/marketplace/github_scanner.py`

**Location 1 - Missing Import (Lines 30-34)**
```python
# NOTE: This import will be available once SVC-002 (heuristic detector) is implemented
# from skillmeat.core.marketplace.heuristic_detector import (
#     HeuristicDetector,
#     detect_artifacts_in_tree,
# )
```
**Action**: Uncomment lines 30-34

---

**Location 2 - Missing Initialization (Line 101)**
```python
        # Will be initialized once heuristic detector is implemented
        # self.detector = HeuristicDetector()
```
**Action**: Uncomment line 101

---

**Location 3 - Missing Detection Call in scan_repository() (Lines 161-167)**
```python
                # 4. Apply heuristic detection
                ctx.metadata["phase"] = "detect_artifacts"
                # NOTE: This will be uncommented once SVC-002 (heuristic detector) is implemented
                # base_url = f"https://github.com/{owner}/{repo}"
                # artifacts = detect_artifacts_in_tree(
                #     file_paths,
                #     repo_url=base_url,
                #     ref=ref,
                #     root_hint=root_hint,
                #     detected_sha=commit_sha,
                # )

                # Placeholder until heuristic detector is implemented
                artifacts = []
                logger.warning(
                    "Heuristic detector not yet implemented (SVC-002). "
                    "Returning empty artifact list."
                )
```
**Action**: Uncomment lines 161-166, delete lines 170-174

---

**Location 4 - Missing Detection Call in scan_github_source() (Lines 464-471)**
```python
    # NOTE: This will be uncommented once SVC-002 (heuristic detector) is implemented
    # artifacts = detect_artifacts_in_tree(
    #     file_paths,
    #     repo_url=repo_url,
    #     ref=ref,
    #     root_hint=root_hint,
    #     detected_sha=commit_sha,
    # )

    # Placeholder until heuristic detector is implemented
    artifacts = []
    logger.warning(
        "Heuristic detector not yet implemented (SVC-002). "
        "Returning empty artifact list."
    )
```
**Action**: Uncomment lines 464-470, delete lines 474-478

---

## Gap 2: Diff Engine Unused

### File: `skillmeat/api/routers/marketplace_sources.py`

**Location: rescan_source() endpoint (Lines 545-548)**
```python
                # Update source and catalog atomically
                with transaction_handler.scan_update_transaction(source_id) as ctx:
                    # Update source status
                    ctx.update_source_status(
                        status="success",
                        artifact_count=scan_result.artifacts_found,
                        error_message=None,
                    )

                    # For now, replace catalog entries
                    # TODO: Use diff engine for incremental updates
                    # Currently heuristic detector returns empty list, so this is a placeholder
                    new_entries: List[MarketplaceCatalogEntry] = []
                    ctx.replace_catalog_entries(new_entries)
```

**Action**: Replace lines 544-548 with:
```python
                # Fetch existing catalog entries
                existing_entries = catalog_repo.get_source_catalog(source_id=source_id)
                existing_dicts = [
                    {
                        "id": e.id,
                        "upstream_url": e.upstream_url,
                        "detected_sha": e.detected_sha,
                        "artifact_type": e.artifact_type,
                        "name": e.name,
                        "path": e.path,
                        "detected_version": e.detected_version,
                    }
                    for e in existing_entries
                ]

                # Compute diff
                from skillmeat.core.marketplace.diff_engine import CatalogDiffEngine
                diff_engine = CatalogDiffEngine()
                diff_result = diff_engine.compute_diff(
                    existing_dicts,
                    scan_result.artifacts,  # Populated by heuristic detector
                    source_id,
                )

                # Apply diff: create new, update changed, mark removed
                with transaction_handler.scan_update_transaction(source_id) as ctx:
                    # Create new entries
                    new_orm_entries = [
                        MarketplaceCatalogEntry(**e.new_data)
                        for e in diff_result.new_entries
                    ]
                    ctx.replace_catalog_entries(new_orm_entries)  # Or bulk_insert

                    # Update existing entries
                    for diff_entry in diff_result.updated_entries:
                        if diff_entry.existing_entry_id and diff_entry.new_data:
                            catalog_repo.update(
                                diff_entry.existing_entry_id,
                                diff_entry.new_data,
                            )

                    # Mark removed entries
                    for diff_entry in diff_result.removed_entries:
                        if diff_entry.existing_entry_id:
                            ctx.mark_removed([diff_entry.existing_entry_id])
```

---

## Gap 3: Import Downloads Missing

### File: `skillmeat/core/marketplace/import_coordinator.py`

**Location: _process_entry() method (Lines 212-221)**
```python
        # Compute local path
        entry.local_path = self._compute_local_path(entry.artifact_type, entry.name)

        # Mark as success (actual file operations would happen here)
        # In a full implementation, this would:
        # 1. Download artifact files from upstream_url
        # 2. Write to local_path
        # 3. Update manifest
        entry.status = ImportStatus.SUCCESS
        logger.debug(f"Imported {entry.name} to {entry.local_path}")
```

**Action**: Replace lines 215-221 with:
```python
        # Compute local path
        entry.local_path = self._compute_local_path(entry.artifact_type, entry.name)

        try:
            # Download artifact from upstream URL
            artifact_content = self._download_artifact(
                entry.upstream_url,
                entry.artifact_type,
                entry.name,
            )

            # Write to local path
            local_path = Path(entry.local_path)
            local_path.mkdir(parents=True, exist_ok=True)

            # Write downloaded files
            for filename, content in artifact_content.items():
                file_path = local_path / filename
                file_path.write_text(content) if isinstance(content, str) else file_path.write_bytes(content)

            # Update manifest
            self._update_manifest(entry.artifact_type, entry.name, entry)

            entry.status = ImportStatus.SUCCESS
            logger.debug(f"Imported {entry.name} to {entry.local_path}")

        except Exception as e:
            entry.status = ImportStatus.ERROR
            entry.error_message = f"Download failed: {str(e)}"
            logger.error(f"Failed to download {entry.upstream_url}: {e}")
            raise
```

**Add new methods to ImportCoordinator class**:
```python
    def _download_artifact(
        self,
        upstream_url: str,
        artifact_type: str,
        name: str,
    ) -> Dict[str, Union[str, bytes]]:
        """Download artifact from upstream URL.

        Args:
            upstream_url: GitHub URL or API endpoint
            artifact_type: Type of artifact (skill, command, etc.)
            name: Artifact name

        Returns:
            Dict of {filename: content} for files to write
        """
        import requests

        # Convert tree URL to API URL if needed
        # Example: https://github.com/user/repo/tree/main/skills/my-skill
        # → https://api.github.com/repos/user/repo/contents/skills/my-skill

        if "github.com" in upstream_url and "/tree/" in upstream_url:
            # Parse GitHub tree URL
            parts = upstream_url.replace("https://github.com/", "").split("/tree/")
            owner_repo = parts[0]
            path = "/".join(parts[1].split("/")[1:])  # Skip branch/tag

            api_url = f"https://api.github.com/repos/{owner_repo}/contents/{path}"

            # Fetch contents recursively
            response = requests.get(
                api_url,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            response.raise_for_status()

            files = {}
            for item in response.json():
                if item["type"] == "file":
                    file_response = requests.get(item["download_url"])
                    file_response.raise_for_status()
                    files[item["name"]] = file_response.content

            return files
        else:
            raise ValueError(f"Unsupported upstream URL format: {upstream_url}")

    def _update_manifest(
        self,
        artifact_type: str,
        name: str,
        entry: ImportEntry,
    ) -> None:
        """Update manifest.toml with imported artifact.

        Args:
            artifact_type: Type of artifact
            name: Artifact name
            entry: Import entry with metadata
        """
        import tomli_w

        manifest_path = self.collection_path / "manifest.toml"

        # Load existing manifest or create new
        if manifest_path.exists():
            import tomllib
            manifest = tomllib.loads(manifest_path.read_text())
        else:
            manifest = {"tool": {"skillmeat": {"artifacts": []}}}

        # Add/update artifact entry
        artifacts = manifest.get("tool", {}).get("skillmeat", {}).get("artifacts", [])

        # Find existing entry
        existing_idx = next(
            (i for i, a in enumerate(artifacts) if a.get("name") == name),
            None
        )

        artifact_entry = {
            "name": name,
            "type": artifact_type,
            "scope": "user",
            "source": entry.upstream_url,
            "version": entry.upstream_url.split("/")[-2],  # From path
        }

        if existing_idx is not None:
            artifacts[existing_idx] = artifact_entry
        else:
            artifacts.append(artifact_entry)

        # Write manifest
        manifest["tool"]["skillmeat"]["artifacts"] = artifacts
        manifest_path.write_text(tomli_w.dumps(manifest))
```

---

## Supporting Imports Needed

### In `skillmeat/api/routers/marketplace_sources.py`, add import at top:
```python
from skillmeat.cache.models import MarketplaceCatalogEntry
from skillmeat.core.marketplace.diff_engine import CatalogDiffEngine
```

### In `skillmeat/core/marketplace/import_coordinator.py`, add imports:
```python
import requests
from pathlib import Path
from typing import Union
```

---

## Testing the Fixes

### Test Gap 1: Heuristic Detector
```python
# After uncommenting imports, run:
python -m skillmeat.core.marketplace.heuristic_detector
# Should show: "Detected 5 artifacts:" with scores
```

### Test Gap 2: Diff Engine
```python
# After implementing diff call, trigger a rescan:
curl -X POST http://localhost:8000/api/v1/marketplace/sources/{source_id}/rescan
# Should return artifacts_found > 0
```

### Test Gap 3: Import Downloads
```python
# After implementing downloads, import an artifact:
curl -X POST http://localhost:8000/api/v1/marketplace/sources/{source_id}/import \
  -H "Content-Type: application/json" \
  -d '{"entry_ids": ["entry-id"], "conflict_strategy": "skip"}'
# Should see files written to ~/.skillmeat/collection/artifacts/
```

---

## Summary Table

| Gap | File | Lines | Action | Impact |
|-----|------|-------|--------|--------|
| 1 | `github_scanner.py` | 30-34 | Uncomment import | Enables detection |
| 1 | `github_scanner.py` | 101 | Uncomment init | Initializes detector |
| 1 | `github_scanner.py` | 161-167 | Uncomment call | Detects in scan |
| 1 | `github_scanner.py` | 464-471 | Uncomment call | Detects in convenience func |
| 2 | `marketplace_sources.py` | 545-548 | Implement diff | Enables incremental updates |
| 3 | `import_coordinator.py` | 212-221 | Implement downloads | Persists artifacts |

---

## Checklist Format

```
Heuristic Detector Gap:
[ ] Uncomment github_scanner.py:30-34
[ ] Uncomment github_scanner.py:101
[ ] Uncomment github_scanner.py:161-167
[ ] Uncomment github_scanner.py:464-471
[ ] Test: python -m skillmeat.core.marketplace.heuristic_detector

Diff Engine Gap:
[ ] Fetch existing entries in marketplace_sources.py:rescan_source()
[ ] Create CatalogDiffEngine instance
[ ] Call compute_diff()
[ ] Apply diff results
[ ] Test: POST /marketplace/sources/{id}/rescan → artifacts_found > 0

Import Downloads Gap:
[ ] Implement _download_artifact() in ImportCoordinator
[ ] Implement _update_manifest() in ImportCoordinator
[ ] Replace lines 215-221 in import_coordinator.py
[ ] Add imports (requests, Path, Union)
[ ] Test: POST /marketplace/sources/{id}/import → files written

```

