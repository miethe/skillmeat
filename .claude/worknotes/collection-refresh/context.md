# Collection Artifact Refresh - Context

**Feature**: Collection Artifact Refresh
**Status**: Planning Complete
**Created**: 2025-01-21

## Problem Statement

Existing imported artifacts have stale data:
- `source`: Showing `TYPE:NAME` instead of full GitHub URL (from older imports)
- `tags`: Hardcoded `["marketplace", "imported"]`
- `description`: Hardcoded `"Imported from marketplace"`
- `origin_source`: Missing (field didn't exist before)

Users need a way to refresh this metadata from upstream GitHub sources without re-importing.

## Solution Overview

A `CollectionRefresher` system that:
1. Iterates collection artifacts with GitHub upstream URLs
2. Fetches fresh metadata from GitHub (frontmatter, repo info)
3. Updates artifact fields with new data
4. Tracks changes (old/new values) for transparency
5. Supports dry-run mode for safe preview

## Key Documents

| Document | Path |
|----------|------|
| Implementation Plan | `docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md` |
| Phase 1 Progress | `.claude/progress/collection-refresh/phase-1-progress.md` |
| Phase 2 Progress | `.claude/progress/collection-refresh/phase-2-progress.md` |
| Phase 3 Progress | `.claude/progress/collection-refresh/phase-3-progress.md` |
| Phase 4 Progress | `.claude/progress/collection-refresh/phase-4-progress.md` |

## Existing Infrastructure

The codebase already has these components to leverage:

| Component | File | Purpose |
|-----------|------|---------|
| `SyncManager.check_drift()` | `skillmeat/core/sync.py` | Detects updates via three-way merge |
| `GitHubMetadataExtractor` | `skillmeat/core/github_metadata.py` | Fetches metadata from GitHub URLs |
| `parse_markdown_with_frontmatter()` | `skillmeat/core/parsers/markdown_parser.py` | Extracts YAML frontmatter |
| `GitHubClient` | `skillmeat/core/github_client.py` | Centralized GitHub API wrapper |
| `CollectionManager` | `skillmeat/core/collection.py` | Collection CRUD with caching |

## Phase Summary

| Phase | Title | Effort | Status |
|-------|-------|--------|--------|
| 1 | Core CollectionRefresher Class | 15.5 pts | Pending |
| 2 | CLI Command Implementation | 13.25 pts | Pending |
| 3 | API Endpoint Implementation | 12 pts | Pending |
| 4 | Update Detection & Advanced | 13.25 pts | Pending |

**Total**: ~54 story points over 4-5 weeks

## Critical Path

```
Phase 1 (5 days) → Phase 2/3 in parallel (7 days) → Phase 4 (5 days)
```

Phase 1 is the critical path - all other phases depend on it.

## Key Decisions

1. **Metadata-only by default**: Safer than full sync, won't overwrite source/version
2. **Dry-run support**: Preview changes before applying
3. **Non-blocking errors**: Continue processing if single artifact fails
4. **Leverage existing infra**: Use GitHubMetadataExtractor, SyncManager

## Files to Create

| File | Phase |
|------|-------|
| `skillmeat/core/refresher.py` | 1 |
| `tests/unit/test_refresher.py` | 1 |
| `tests/integration/test_refresh_cli.py` | 2 |
| `tests/integration/test_refresh_api.py` | 3 |
| `docs/guides/artifact-refresh-guide.md` | 4 |

## Files to Modify

| File | Phase |
|------|-------|
| `skillmeat/cli.py` | 2 |
| `skillmeat/api/routers/collections.py` | 3 |
| `skillmeat/api/schemas/collections.py` | 3 |

## Notes

- This feature was prompted by stale data issue discovered 2025-01-21
- Recent commits (78a3619, 4c8751e) fixed the import flow but existing data remains stale
- This refresh feature will fix existing data and provide ongoing maintenance capability
