---
title: "ADR-0001: Repository Metadata Storage Strategy"
status: accepted
date: 2026-01-18
deciders: ["lead-architect", "backend-architect"]
tags: [adr, marketplace, metadata, storage, github]
related:
  - /docs/project_plans/PRDs/enhancements/marketplace-sources-enhancement-v1.md
  - /skillmeat/api/schemas/marketplace.py
  - /skillmeat/core/marketplace/github_scanner.py
---

# ADR-0001 — Repository Metadata Storage Strategy

## Context

The Marketplace Sources Enhancement feature requires exposing repository context (description and README files) directly in the SkillMeat UI to improve source discovery. Users currently must visit GitHub separately to understand what a source contains and whether it's relevant to their needs.

Key constraints:

- **GitHub API Rate Limits**: Fetching README for every source during listing would exhaust API quota quickly
- **Storage Overhead**: README files are often 10-50KB; storing full content for hundreds of sources creates manifest bloat
- **User Metadata Separation**: Sources have both user-provided descriptions (notes) and repository-level descriptions (from GitHub); these must be distinct
- **Offline Access**: Users should be able to browse source details without network access to GitHub
- **Caching**: Repository metadata should be cached to avoid redundant API calls during rescans

## Decision

We adopt a **selective metadata import strategy** with the following principles:

1. **Opt-in Import via Toggles**
   - Add `import_repo_description` and `import_repo_readme` boolean flags to `CreateSourceRequest` and `UpdateSourceRequest`
   - Default both to `false` to avoid automatic API calls and storage overhead
   - Users explicitly choose to import these during source creation or editing

2. **Separate Fields from User Metadata**
   - Store `repo_description` (max 2000 chars) and `repo_readme` (max 50KB) as distinct fields from user `description`
   - Clear UI labels distinguish "Your Description" (user notes) from "Repository Description" (from GitHub)
   - User description remains editable independently

3. **README Truncation Strategy**
   - Fetch full README from GitHub API
   - Truncate to 50KB if larger (pragmatic limit for manifest storage)
   - Store truncation indicator in UI; provide "View Full on GitHub" link for truncated content
   - Rationale: 50KB covers most practical READMEs while keeping manifest size reasonable

4. **Lazy Fetch with Timeout**
   - Fetch repository description and README *during* source creation/rescan (not during list queries)
   - Implement 5-second timeout per source to respect GitHub API budget
   - If timeout occurs, continue with source creation (graceful degradation)
   - Flag failed fetches for retry on next rescan if toggles remain enabled

5. **Caching in Lock File**
   - Store resolved SHA of repository and fetch timestamp in lock file alongside metadata
   - On rescan with toggles enabled, check if cached SHA matches current remote
   - If SHA unchanged, skip fetch and reuse cached content (avoid redundant API calls)
   - If SHA changed or no prior fetch, fetch fresh metadata

6. **Backward Compatibility**
   - Existing sources without metadata fields have `repo_description: null` and `repo_readme: null`
   - These fields are optional in `SourceResponse`; clients check for presence before rendering
   - Clients can migrate old sources by enabling toggles in edit dialog

## Consequences

### Positive

- ✅ **Reduced API Load**: Opt-in approach prevents blanket metadata fetching for all sources
- ✅ **Offline Access**: Cached metadata allows browsing without network for sources that were imported with toggles enabled
- ✅ **Storage Efficiency**: 50KB truncation keeps manifests lean; only sources with toggles enabled consume storage
- ✅ **User Control**: Clear toggle UI gives users agency over what gets fetched
- ✅ **Performance**: Manifest parsing remains fast; large READMEs don't bloat list queries
- ✅ **Graceful Degradation**: Source creation succeeds even if metadata fetch times out

### Negative

- ❌ **Feature Discoverability**: Users may not enable toggles by default; metadata adoption could be slow
- ❌ **Staleness Risk**: Cached content can drift from GitHub if repository is updated frequently
- ❌ **Storage Redundancy**: Same metadata cached in both manifest and lock file increases storage slightly
- ❌ **Truncated Content**: Users see "View Full on GitHub" instead of complete README in UI

### Mitigations

1. **Feature Discoverability**: Default toggles to `true` after v1 stabilization; enable via feature flag
2. **Staleness**: Rescan action always fetches fresh metadata if toggles enabled; document refresh behavior
3. **Storage**: Compress README content in lock file using gzip (future optimization)
4. **Truncation**: Accept 50KB limit as pragmatic trade-off; communicate clearly in UI about truncation

## Alternatives Considered

### Alternative A: Fetch on Demand from GitHub API

**Approach**: Don't store metadata; fetch from GitHub API each time user views source detail page.

**Rejected Because**:
- High latency (100-500ms GitHub API call per detail page load)
- Violates offline-access principle
- Rate limit exhaustion for popular sources viewed by multiple users
- Poor UX during network failures

### Alternative B: Store Full README Always

**Approach**: Automatically fetch and store complete README for all sources without toggles.

**Rejected Because**:
- Massive storage overhead (100+ sources × 50KB average = 5MB+ per collection)
- Slow manifest parsing with large embedded content
- Wasted storage for users who don't need repository details
- Violates principle of user control

### Alternative C: Minimal Metadata (Link Only)

**Approach**: Store only GitHub URL; UI renders link to view on GitHub.

**Rejected Because**:
- Doesn't solve offline-access requirement
- Requires users to leave SkillMeat UI to understand source content
- Doesn't improve source discovery experience

## Follow-Up Actions

1. **Feature Flag**: Add `FEATURE_REPO_DETAILS` flag; default `true` after stabilization
2. **Observability**: Track metadata fetch success rate and timeout frequency; alert if >5% timeout rate
3. **Compression**: Evaluate gzip compression for README in lock file to reduce storage overhead
4. **User Research**: Gather feedback on toggle adoption rates and preferences for auto-fetch vs opt-in
5. **Future Enhancement (v2)**: Implement batch refresh endpoint for bulk metadata updates across sources

## Decision Record

**Decided**: 2026-01-18
**Approved By**: Lead Architect, Backend Architect
**Implementation Status**: Accepted for Phase 2 (Backend Repository Fetching & Scanning)
