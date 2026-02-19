---
title: 'Implementation Plan: Unify Refresh Metadata Extraction with Import Flow'
description: Fix collection refresh to correctly extract descriptions from single-file
  artifacts by reusing import flow's proven extraction logic
audience:
- ai-agents
- developers
tags:
- bugfix
- refactor
- metadata
- refresh
- collection
created: 2026-02-03
updated: 2026-02-03
category: refactors
status: inferred_complete
related:
- /docs/project_plans/implementation_plans/refactors/tag-storage-consolidation-v1.md
---
# Implementation Plan: Unify Refresh Metadata Extraction with Import Flow

**Plan ID**: `IMPL-2026-02-03-REFRESH-METADATA`
**Date**: 2026-02-03
**Author**: Claude Opus 4.5

**Complexity**: Medium
**Total Estimated Effort**: 13 pts
**Risk**: Low (purely additive core changes, existing interface preserved)

## Executive Summary

The `skillmeat collection refresh --fields description` command fails to extract descriptions from single-file artifacts (agents, commands) because `GitHubMetadataExtractor.fetch_metadata()` assumes all artifact paths are directories. The import flow already handles this correctly via `extract_artifact_metadata()` in `utils/metadata.py`. This plan unifies the refresh flow with the import flow's proven extraction pipeline by creating reusable utility functions and wiring them into the refresher.

## Root Cause

`GitHubMetadataExtractor.fetch_metadata()` (`github_metadata.py:257-270`) looks for `SKILL.md`/`AGENT.md`/`README.md` **inside** the artifact path:

```python
file_path = f"{spec.path}/{filename}"  # e.g., "agents/apple-platform-architect.md/SKILL.md"
```

For single-file artifacts whose upstream URL ends with `.md`, this produces invalid paths like `apple-platform-architect.md/SKILL.md`. The actual file is never read, so description stays `None`. This affects 20+ artifacts in the default collection.

## Implementation Strategy

### Approach: Hybrid (Option D) - Reusable GitHub extraction + defense-in-depth

1. Create new reusable utility functions in `utils/metadata.py` that bridge the GitHub API with the existing frontmatter extraction pipeline
2. Wire the refresher to use these new functions instead of `GitHubMetadataExtractor`
3. Fix `GitHubMetadataExtractor` as defense-in-depth for other callers
4. Ensure cache DB stays in sync after refresh

### Critical Path

Phase 1 (utility functions) -> Phase 2 (wire into refresher) -> Phase 3 (cache sync) -> Phase 4 (defense-in-depth)

### Parallel Work

Phase 4 (defense-in-depth fix) can run in parallel with Phase 3 (cache sync).

## Phase Breakdown

### Phase 1: Reusable Extraction Utilities

**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| UTIL-001 | `extract_metadata_from_content()` | Add function to `utils/metadata.py` that takes raw file content + artifact_type, returns `ArtifactMetadata` using existing `extract_frontmatter()` + `populate_metadata_from_frontmatter()` pipeline | Function extracts description, title, author, tools from content with frontmatter | 2 pts | python-backend-engineer | None |
| UTIL-002 | `fetch_and_extract_github_metadata()` | Add function to `utils/metadata.py` that takes GitHubClient + owner/repo/path/artifact_type, detects file vs directory, fetches correct file via API, calls UTIL-001 | Single-file (.md) paths fetched directly; directory paths look for type-appropriate metadata files (SKILL.md, AGENT.md, etc.) | 3 pts | python-backend-engineer | UTIL-001 |
| UTIL-003 | Unit tests for new utilities | Test both functions with mocked GitHub responses | Tests cover: single-file agent, directory skill, missing frontmatter, fallback description from body | 2 pts | python-backend-engineer | UTIL-002 |

**Key Design Decisions**:

- `extract_metadata_from_content(content, artifact_type)` is deliberately content-source-agnostic. It works with content from GitHub API, local files, or any other source. This makes it reusable for marketplace scanning, local refresh, and future features.
- `fetch_and_extract_github_metadata()` mirrors `find_metadata_file()` logic but for remote GitHub content. File detection: if path ends with `.md`, treat as direct file; otherwise, search for type-specific metadata files in the directory.
- Both functions live in `utils/metadata.py` alongside the existing `extract_artifact_metadata()` they reuse.

**Phase 1 Quality Gates:**
- [ ] `extract_metadata_from_content()` extracts description from frontmatter
- [ ] `fetch_and_extract_github_metadata()` handles both single-file and directory paths
- [ ] All unit tests pass

---

### Phase 2: Wire Refresher to Use New Extraction

**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| REF-001 | Update `_fetch_upstream_metadata()` | Modify `refresher.py:_fetch_upstream_metadata()` to accept `artifact_type` parameter and use `fetch_and_extract_github_metadata()` instead of `self.metadata_extractor.fetch_metadata()`. Map result to `GitHubMetadata` structure. Still fetch repo metadata (topics, license) via `GitHubClient.get_repo_metadata()`. | Single-file artifacts get correct descriptions during refresh | 3 pts | python-backend-engineer | UTIL-002 |
| REF-002 | Update `refresh_metadata()` caller | Pass `artifact.type` to `_fetch_upstream_metadata()` at line ~1117 | Type information flows to extraction logic | 1 pt | python-backend-engineer | REF-001 |
| REF-003 | Integration test | Test `collection refresh --fields description` with a collection containing both single-file agents and directory skills | Both artifact types get descriptions refreshed correctly | 1 pts | python-backend-engineer | REF-002 |

**Key Files Modified**:
- `skillmeat/core/refresher.py` lines 670-747 (`_fetch_upstream_metadata`), line ~1117 (caller in `refresh_metadata`)

**Phase 2 Quality Gates:**
- [ ] `apple-platform-architect` (single-file agent) gets description refreshed
- [ ] Existing directory-based skills still refresh correctly (no regression)
- [ ] `skillmeat collection refresh --fields description --dry-run` shows pending changes for previously-missing descriptions

---

### Phase 3: Cache Database Sync

**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| CACHE-001 | CLI cache invalidation | Add `_refresh_api_cache()` call in `cli.py` after successful `collection_refresh` when changes were applied (not dry-run/check) | Web UI reflects refreshed descriptions without manual cache clear | 1 pt | python-backend-engineer | REF-003 |

**Key Files Modified**:
- `skillmeat/cli.py` line ~2938 (after refresh summary display)

**Phase 3 Quality Gates:**
- [ ] After `skillmeat collection refresh --fields description`, API returns updated descriptions
- [ ] Dry-run and check modes do NOT trigger cache invalidation

---

### Phase 4: Defense-in-Depth Fix for GitHubMetadataExtractor

**Dependencies**: None (can run in parallel with Phase 3)
**Assigned Subagent(s)**: python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| GHM-001 | Fix `fetch_metadata()` single-file handling | In `github_metadata.py:fetch_metadata()`, before the metadata_files loop, check if `spec.path` ends with `.md` and if so, fetch the file directly and extract frontmatter from it | `GitHubMetadataExtractor` works correctly for single-file paths even if called directly | 1 pt | python-backend-engineer | None |

**Key Files Modified**:
- `skillmeat/core/github_metadata.py` lines 255-270

**Phase 4 Quality Gates:**
- [ ] `GitHubMetadataExtractor.fetch_metadata()` returns description for single-file artifact paths
- [ ] No regression for directory artifact paths

---

## Files Changed Summary

| File | Change | Phase |
|------|--------|-------|
| `skillmeat/utils/metadata.py` | ADD `extract_metadata_from_content()`, `fetch_and_extract_github_metadata()` | 1 |
| `skillmeat/core/refresher.py` | MODIFY `_fetch_upstream_metadata()` signature + body, update caller | 2 |
| `skillmeat/cli.py` | ADD cache invalidation after refresh | 3 |
| `skillmeat/core/github_metadata.py` | FIX single-file path handling in `fetch_metadata()` | 4 |
| `tests/` | ADD unit + integration tests | 1, 2 |

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| GitHub API rate limit during refresh | Medium | Low | Existing rate limit handling in GitHubClient; no additional API calls vs current flow |
| Regression in directory artifact refresh | High | Low | Phase 2 integration test validates both paths |
| Cache staleness after refresh | Low | Medium | Phase 3 explicitly handles cache invalidation |

## Verification Plan

1. **Manual verification**: Run `skillmeat collection refresh --fields description --dry-run` and confirm `apple-platform-architect` shows as "would update description"
2. **Apply**: Run `skillmeat collection refresh --fields description` and verify description appears in `collection.toml`
3. **Web UI**: Verify description appears in artifact detail modal on `/manage` page
4. **Batch**: Confirm all 20+ single-file artifacts with missing descriptions now get them
5. **No regression**: Existing directory-based skills (e.g., `senior-prompt-engineer`) retain their descriptions

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-03
