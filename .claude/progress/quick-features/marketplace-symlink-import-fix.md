---
title: "Fix Marketplace Import: Symlinks + Single-Artifact Naming"
type: quick-feature
status: completed
created: 2025-02-05
estimated_effort: 2-3 hours
files_affected:
  - skillmeat/core/marketplace/import_coordinator.py
  - skillmeat/core/marketplace/github_scanner.py
  - skillmeat/core/marketplace/heuristic_detector.py
---

# Fix Marketplace Import: Symlinks + Single-Artifact Naming

## Problem

Two edge cases in marketplace source import:

### Bug 1: Single-artifact source names incorrectly
When adding source `https://github.com/user/repo/tree/main/.claude`:
- `root_hint` is set to `.claude`
- Artifact detected at `.claude/skills/ui-ux-pro-max/`
- But source/artifact name may be derived from root (`.claude`) instead of the actual artifact
- The entire `.claude` tree is imported rather than just the detected artifact

**Expected**: Detect the skill at its actual path and import only that artifact with the correct name (`ui-ux-pro-max`).

### Bug 2: Symlinks silently dropped during import
- GitHub Contents API returns `type: "symlink"` with a `target` field (relative path)
- `_download_directory_recursive()` only handles `"file"` and `"dir"` types
- Symlinked directories (e.g., `data/` -> `../../../src/ui-ux-pro-max/data`) are skipped
- Result: Imported skill only has SKILL.md, missing data/ and scripts/

**Expected**: Detect symlinks, resolve their targets, and download the actual content from the target path.

## Implementation Plan

### Task 1: Handle symlinks in `_download_directory_recursive()` (import_coordinator.py)
- Add `elif item_type == "symlink":` branch
- Read the `target` field from the API response (relative path like `../../../src/ui-ux-pro-max/data`)
- Resolve the relative path against the current remote_path to get an absolute repo path
- Use GitHub Contents API to check if the target is a file or directory
- If directory: recursively download using `_download_directory_recursive()` with the resolved target path but writing to the local symlink location
- If file: download normally using `_download_file()`
- Store symlink metadata (original target) for future sync tracking
- Add logging for symlink resolution

### Task 2: Handle symlinks in `_extract_file_paths()` (github_scanner.py)
- In the tree walking, also process `type: "symlink"` entries (the Git Trees API blob-only filter skips them)
- When a symlink target resolves to a directory, include all files under that directory in the artifact's file list
- This ensures heuristic detection includes symlinked content in artifact scoring

### Task 3: Single-artifact source naming fix
- When `root_hint` is set (e.g., `.claude`) and scanning finds artifacts within it:
  - Each artifact should be named from its own directory (e.g., `ui-ux-pro-max` from `skills/ui-ux-pro-max/`)
  - NOT from the root_hint itself
- The download path should be the artifact's detected boundary, not the full root_hint tree
- Review `_process_entry()` and the import entry creation to ensure names come from detected artifact paths

## Testing Strategy

- Unit test: symlink resolution with relative path traversal
- Unit test: single-artifact naming from nested path
- Integration test: mock GitHub API responses with symlink entries
- Manual test: re-import the `nextlevelbuilder/ui-ux-pro-max-skill` source
