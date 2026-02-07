---
feature: collection-import-symlink-resolution
status: completed
created: 2025-02-06
scope: single-file fix
files_affected:
  - skillmeat/core/marketplace/import_coordinator.py
---

# Fix: Symlink Resolution During Collection Import

## Problem
When importing marketplace artifacts with symlinked directories into a collection,
only SKILL.md is imported. Symlinked dirs (e.g., `data/`, `scripts/`) are silently skipped.

## Root Cause
GitHub Contents API **directory listings** do NOT include the `target` field for symlink entries.
The code at line 667 checks `item.get("target", "")` which returns empty, causing skip.

However, querying the **individual symlink path** via Contents API DOES return `target`.
Also, the `download_url` field in directory listings contains the raw symlink target content.

## Fix
In `_download_directory_recursive()`, when a symlink has no `target` in the directory listing:
1. Fetch the symlink target by calling the Contents API for the individual symlink path
2. OR fetch via `download_url` which returns the raw symlink target string
3. Then continue with existing symlink resolution logic

Option 1 (individual API call) is preferred because:
- Returns structured JSON with `target` field
- Consistent with existing API usage patterns
- No content parsing needed

## Tasks
- [x] TASK-1: Investigate root cause
- [x] TASK-2: Fix `_download_directory_recursive` to resolve symlink targets when `target` field is missing
- [x] TASK-3: Verify module imports, linting passes, existing tests unaffected
