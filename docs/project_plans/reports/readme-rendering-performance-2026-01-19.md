# README Rendering Performance Analysis

**Date**: 2026-01-19
**Component**: Marketplace Sources → RepoDetailsModal
**Status**: Investigation Complete

## Summary

Users experience visible lag when scrolling through README content in the Repo Details modal. Investigation reveals this is a **rendering issue**, not a data fetching issue.

## Findings

### Data Flow (Current Architecture)

| Stage | Timing | Details |
|-------|--------|---------|
| Fetch | Source creation | README fetched when "Import Repository README" checked |
| Storage | Database | `MarketplaceSource.repo_readme` (Text, 50KB max) |
| API | Always returned | Included in all source GET responses |
| Display | Modal open | Full content passed to ReactMarkdown |

### Root Cause

README content is **already loaded** when modal opens. The lag occurs because:

1. **ReactMarkdown renders entire document at once** - up to 50KB of markdown
2. **Browser paint on scroll** - newly visible content requires layout/paint work
3. **Complex markdown** - links, code blocks, tables cause layout thrashing

### Relevant Files

- `skillmeat/cache/models.py` - `MarketplaceSource.repo_readme` storage
- `skillmeat/web/components/marketplace/repo-details-modal.tsx` - ReactMarkdown rendering
- `skillmeat/web/hooks/useMarketplaceSources.ts` - `useSource()` data fetching

## Recommendations

| Option | Effort | Impact | Trade-offs |
|--------|--------|--------|------------|
| **Virtualized rendering** | Medium | High | Adds dependency (react-window), complex for variable-height markdown |
| **Chunked/lazy sections** | Medium | Medium | Render above-fold first, defer rest with IntersectionObserver |
| **Lighter markdown renderer** | Low | Low-Medium | Trade features for speed (e.g., marked.js) |
| **Pre-rendered HTML** | High | High | Store HTML at creation; increases storage, adds migration |

### Recommended Approach

**Chunked rendering with IntersectionObserver** - best balance of effort vs impact:
- Split README into chunks (~5KB each)
- Render first chunk immediately
- Use IntersectionObserver to render subsequent chunks as user scrolls
- No external dependencies, moderate implementation effort

## Next Steps

Enhancement request logged: Track implementation priority based on user feedback frequency.
