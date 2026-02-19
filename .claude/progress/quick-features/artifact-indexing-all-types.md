---
status: completed
feature: artifact-indexing-all-types
created: 2026-01-27
completed: 2026-01-27
type: quick-feature
schema_version: 2
doc_type: quick_feature
feature_slug: artifact-indexing-all-types
---

# Fix Artifact Search Indexing for All Types

## Problem

The artifact search indexing only works for skills. Commands, agents, hooks, and MCP servers are not being indexed despite having manifest files.

**Root Cause**: The indexing code assumes all artifacts are **directories** containing manifest files (e.g., `skills/canvas/SKILL.md`). However, commands, agents, and hooks are often **single files** that ARE the manifest (e.g., `commands/doc-generate.md`).

When the code tries to index `commands/doc-generate.md`, it looks for `commands/doc-generate.md/COMMAND.md` which doesn't exist.

## Evidence

Database query after rescanning shows:
- Skills: 338 total, 324 indexed (96%)
- Agents: 321 total, 0 indexed (0%)
- Commands: 243 total, 0 indexed (0%)

## Solution

Modify `_extract_frontmatter_batch` and `_extract_frontmatter_for_artifact` to:
1. Check if the artifact path itself ends with a manifest file extension (`.md`, `.yaml`, `.yml`)
2. If so, read the artifact path directly as the manifest
3. Otherwise, use existing directory-based lookup logic

## Files to Modify

- `skillmeat/api/routers/marketplace_sources.py`
  - `_extract_frontmatter_for_artifact()` (line ~745)
  - `_extract_frontmatter_batch()` (line ~1116)

## Acceptance Criteria

- [ ] Commands with paths like `commands/foo.md` have search_text populated after rescan
- [ ] Agents with paths like `agents/bar.md` have search_text populated after rescan
- [ ] Hooks with paths like `hooks/baz.yaml` have search_text populated after rescan
- [ ] Existing skill indexing continues to work (directory-based)
- [ ] Tests pass

## Testing

1. Run existing tests
2. Trigger a rescan of a source with mixed artifact types
3. Verify non-skill artifacts have search_text populated in database
