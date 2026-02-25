---
# === CONTEXT WORKNOTES: SIMILAR ARTIFACTS ===
# PRD-level sticky pad for agent notes and observations during development
# This file grows as agents add notes during Phase 1-6 implementation

# Metadata: Identification and Scope
type: context
prd: "similar-artifacts"
title: "Similar Artifacts — Development Context"
status: "active"
created: "2026-02-25"
updated: "2026-02-25"

# Quick Reference (for fast agent queries)
critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []

# Agent Communication Index (for efficient lookups)
# Format: { agent: "agent-name", note_count: N, last_contribution: "YYYY-MM-DD" }
agents: []
---

# Similar Artifacts — Development Context

**Status**: Active Development
**Created**: 2026-02-25
**Last Updated**: 2026-02-25

> **Purpose**: This is a shared worknotes file for all AI agents working on the Similar Artifacts feature. Add brief observations, decisions, gotchas, and implementation notes that future agents should know. Think of this as a sticky-note pad for the development team.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: None yet

---

## Key Decisions

> Architectural and technical decisions made during development

### Phase 1 Architecture: Similarity Engine Design Approach

**Status**: Pending Phase 1 implementation

Key architectural decisions to be made:

- SemanticScorer integration strategy (stateless per-query vs. caching)
- Scoring weighting: ArtifactFingerprint vs. MatchAnalyzer vs. SemanticScorer
- Pagination strategy for large collection results
- Timeout and fallback behavior for slow/failing scorers
- Cache invalidation strategy for similarity queries (suggested: 5-min staleTime per PRD)

---

## Implementation Notes

> Things that tripped us up or patterns discovered during implementation

### Pre-Implementation Observations

**Architecture Overview**:
- New `SimilarityService` will be located at `skillmeat/core/similarity.py`
- Orchestrates three existing components: ArtifactFingerprint (models.py:458-570), MatchAnalyzer (core/scoring/match_analyzer.py), SemanticScorer (core/scoring/semantic_scorer.py)
- All existing components are stable per PRD; no breaking changes needed

**Performance Considerations**:
- SemanticScorer (HaikuEmbedder/cosine similarity) must be hard-capped at 800 ms per requirement
- Keyword-only fallback (MatchAnalyzer + fingerprint) should complete in <300 ms for typical collections
- Large collection (500 artifacts) fingerprint comparison may exceed 2 s SLA; mitigation: limit full comparison to top-N candidates by keyword score first
- Frontend marketplace badge batching will be critical to avoid N+1 API calls on SourceCard lists

**Existing Code Patterns to Reuse**:
- DiffViewer component for consolidation comparison (already handles diff parsing)
- VersionMergeService for merge/replace/skip logic with auto-snapshot (already exists)
- DuplicateReviewModal UX patterns for consolidation UI
- MiniArtifactCard for similarity results grid display
- Custom colors API (/api/v1/colors) for threshold color configuration
- React Query hooks pattern from existing codebase (useSync, useDeploy, etc.)

---

## Dependencies & Integration Points

> How components interact and connect

### Backend Layer

**Core Service Dependencies**:
- **ArtifactFingerprint** (`skillmeat/models.py:458-570`)
  - Usage: Weighted hash comparison (content, structure, metadata)
  - Interface: Static/class methods for fingerprint computation and comparison
  - Status: Stable, no changes required

- **MatchAnalyzer** (`skillmeat/core/scoring/match_analyzer.py`)
  - Usage: TF-IDF keyword scoring across name, title, tags, description, aliases
  - New method needed: `compare(artifact_a: Artifact, artifact_b: Artifact) -> SimilarityResult`
  - Status: Stable; minimal addition of comparison helper method

- **SemanticScorer** (`skillmeat/core/scoring/semantic_scorer.py`)
  - Usage: Cosine similarity via HaikuEmbedder for semantic matching
  - Timeout requirement: Hard 800 ms cap with keyword-only fallback
  - Status: Stable, optional graceful failure
  - Note: Remains stateless per-query; no embedding persistence

**Database & Repository Layer**:
- **DuplicatePair** model (`skillmeat/models.py`)
  - Extension: Add `ignored` boolean column (default `false`)
  - Migration: Additive Alembic migration, backward-compatible
  - Usage: Mark/unmark skipped pairs in consolidation workflow

- **Artifact Repository** (`skillmeat/cache/repositories.py`)
  - New method needed: `mark_pair_ignored(artifact_id_a, artifact_id_b, ignored: bool)`
  - New method needed: `get_consolidation_clusters(min_score: float, limit: int, cursor: str)`
  - Cursor pagination for cluster list

**API Layer**:
- **New endpoint**: `GET /api/v1/artifacts/{id}/similar`
  - Query params: `limit` (1-50, default 10), `min_score` (0-1, default 0.3), `source` ('collection'|'marketplace'|'all')
  - Response: List of `SimilarArtifactDTO` with score breakdown
  - Error handling: 404 on unknown artifact, validation errors on invalid params

- **Existing endpoint**: `GET /api/v1/match/?q=...` (NOT modified; new endpoint is supplementary)

### Frontend Layer

**React Query Hooks** (`skillmeat/web/hooks/similarity.ts`):
- `useSimilarArtifacts(artifactId, options?)` — main hook for Similar tab and marketplace queries
  - staleTime: 5 minutes (per PRD data-flow-patterns)
  - gcTime: Not explicitly mentioned; use React Query default (5 min)
  - Supports `source` option for filtering scope

**Components**:
- **SimilarArtifactsTab** (`skillmeat/web/components/collection/similar-artifacts-tab.tsx`)
  - Renders MiniArtifactCard grid: `grid grid-cols-2 gap-3 pb-1 pr-1 sm:grid-cols-3`
  - Uses existing MiniArtifactCard component with optional `showScore` prop
  - Empty state messaging when no results
  - Loading skeleton during fetch

- **SimilarityBadge** (`skillmeat/web/components/marketplace/similarity-badge.tsx`)
  - Color-coded: green (high ≥0.80), yellow (partial ≥0.55), orange (low ≥0.35), hidden (floor <0.20)
  - Includes `aria-label` with score percentage and match level
  - Integrated into SourceCard via viewport-aware lazy loading

- **SimilaritySettings** (`skillmeat/web/app/settings/components/similarity-settings.tsx`)
  - Sub-tab in Settings > Appearance (alongside Colors | Icons)
  - Threshold sliders: high/partial/low/floor with visual labels
  - Color pickers for each threshold using `useCustomColors()` hook
  - Persist via existing settings API

**ArtifactDetailsModal Integration**:
- Extends `BASE_TABS` pattern to add "Similar" tab
- Icon: GitCompare (Lucide icon)
- Reusable SimilarArtifactsTab component for both collection and marketplace artifact contexts

### Consolidation View Integration

**Page Route**: `/collection/consolidate` (`skillmeat/web/app/collection/consolidate/page.tsx`)
- Accessible from Collection page toolbar button
- Shows cluster list with artifact count, highest score, type
- Pagination: cursor-based, 20 clusters per page

**Cluster Detail Component**:
- Uses existing DiffViewer for side-by-side comparison
- Uses existing VersionMergeService for merge/replace logic
- Auto-snapshot gate (must succeed before merge/replace)
- Actions: merge, replace, skip (mark ignored)

### CLI Integration

**Command 1**: `skillmeat similar <artifact> [--limit 10] [--min-score 0.3] [--source collection|marketplace|all]`
- Rich table output with columns: Name | Type | Score | Breakdown
- Calls SimilarityService directly (no HTTP)

**Command 2**: `skillmeat consolidate [--non-interactive] [--output json|text]`
- TTY: Interactive wizard with menu prompts
- Non-TTY: `--non-interactive --output json` mode with cluster list
- Calls SimilarityService and VersionMergeService directly

---

## Blockers & Risks

> Issues requiring attention or potential problems

### Pre-Implementation Identified Risks

| Risk | Impact | Mitigation | Status |
|------|--------|-----------|--------|
| SemanticScorer latency exceeds 800 ms | High | Hard timeout + keyword-only fallback | Documented in Phase 1 tasks |
| Marketplace N+1 badge queries degrade performance | High | IntersectionObserver batch + deduplicate | Documented in Phase 4 tasks |
| Similarity thresholds default settings miss duplicates or surface noise | Medium | Conservative defaults (floor ≥0.20); settings UI for tuning | Requires post-launch monitoring |
| DuplicatePair migration causes backward compatibility issues | Low | Additive migration only (new column, default false) | Low risk; standard Alembic pattern |
| Large collections (>500 artifacts) exceed 2 s latency SLA | Medium | Limit full fingerprint to top-N candidates by keyword; cache 5 min | Backlog optimization if needed |
| Consolidation merge snapshot fails mid-action | Critical | Abort merge if snapshot fails; never proceed silently | Must enforce in VersionMergeService gate |

### Pre-Implementation Technical Assumptions

- SemanticScorer failure is a graceful fallback (no user error modal); keyword scoring stands alone
- Marketplace artifact similarity always queries against user's collection (not other marketplace artifacts)
- Floor threshold is a single global setting (not per-source)
- Ignored pairs persist indefinitely until explicitly un-ignored
- Cursor pagination on clusters endpoint uses cursor-based strategy (consistent with collection patterns)

---

## Cross-Phase Notes

> Observations spanning multiple phases or high-level learnings

### Phase Sequence Notes

**Phase 1 Completion Gate**:
- SimilarityService must pass unit tests (scorer fallback, filtering, empty results)
- API endpoint must pass integration tests (happy path, 404, filter params, pagination)
- DuplicatePair.ignored migration must be backward-compatible and tested
- Once Phase 1 merges, Phase 2, 4, 5, and 6 can proceed in parallel

**Frontend Dependency Chain**:
- Phase 2 (Similar tab) requires Phase 1 API merged + hook contract agreed
- Phase 3 (Marketplace tab) requires Phase 2 SimilarArtifactsTab stable (light lift; reuse tab)
- Phase 4 (Badges + Settings) requires Phase 1 API merged (no frontend blocker from Phase 2)
- Phase 5 (Consolidation) requires Phase 1 service + clusters endpoint (no Phase 2-4 dependency)

**Documentation Integration**:
- OpenAPI spec must be updated before Phase 1 merge
- CLI `--help` strings are generated from Click docstrings (not separate docs)
- Settings UI inline help text is component-embedded (not separate docs)

### Cross-Component Patterns to Watch

**React Query Stale Times**:
- All similarity queries must use 5-min staleTime per data-flow-patterns context
- Badge queries should use 30 s staleTime for interactive freshness (consider revisit)
- Consolidation cluster list should use 5-min staleTime (read-heavy view)

**Error Handling Patterns**:
- Non-blocking error state in Similar tab (no modal crash if API fails)
- Blocking error in consolidation merge if snapshot fails (abort action)
- SemanticScorer timeout is transparent (falls back to keyword; no error shown)

**Accessibility Requirements**:
- All badge variants must meet WCAG 2.1 AA contrast
- Similar tab is keyboard-navigable (MiniArtifactCard focusable with Enter/Space)
- Consolidation view meets contrast requirements for all threshold colors

---

## References

**Related Files**:
- PRD: `docs/project_plans/PRDs/features/similar-artifacts-v1.md`
- Implementation Plan: `docs/project_plans/implementation_plans/features/similar-artifacts-v1.md`
- Phase 1-2 Plan: `docs/project_plans/implementation_plans/features/similar-artifacts-v1/phase-1-2-backend-and-collection-tab.md`
- Phase 3-4 Plan: `docs/project_plans/implementation_plans/features/similar-artifacts-v1/phase-3-4-marketplace.md`
- Phase 5-6 Plan: `docs/project_plans/implementation_plans/features/similar-artifacts-v1/phase-5-6-consolidation-and-cli.md`
- Progress Tracking: `.claude/progress/similar-artifacts/all-phases-progress.md`

**Key Codebase Locations**:
- Scoring: `skillmeat/core/scoring/{match_analyzer.py, semantic_scorer.py}`
- Models: `skillmeat/models.py` (ArtifactFingerprint, DuplicatePair)
- Existing API patterns: `skillmeat/api/routers/match.py`, `skillmeat/api/routers/artifacts.py`
- Existing UI patterns: `skillmeat/web/components/collection/`, `skillmeat/web/components/marketplace/`, `skillmeat/web/components/discovery/`

---

## Template Examples for Agent Contributions

<details>
<summary>Example: Implementation Decision</summary>

### 2026-02-25 - python-backend-engineer - SemanticScorer Timeout Strategy

**Decision**: SemanticScorer will use a hard 800 ms timeout with keyword-only fallback in SimilarityService.find_similar()

**Rationale**: Prevents Similar tab from feeling slow on p95 collections; graceful fallback ensures feature ships without embedder dependency

**Location**: `skillmeat/core/similarity.py:SimilarityService.find_similar()`

**Impact**: No user-facing errors; similarity results degrade to keyword scoring if embedder is slow/unavailable

</details>

<details>
<summary>Example: Gotcha/Observation</summary>

### 2026-02-25 - ui-engineer-enhanced - MiniArtifactCard Score Overlay

**What**: MiniArtifactCard does not have a built-in score badge prop; will need to add `showScore` and `scorePercentage` props

**Why**: Existing component designed for gallery display without similarity context

**Solution**: Add optional props with sensible defaults (false/undefined); score badge renders as overlay only when props are provided

**Affects**: Phase 2 component implementation; Phase 3 marketplace tab reuse

</details>

<details>
<summary>Example: Integration Note</summary>

### 2026-02-25 - ui-engineer - SimilarityBadge ↔ SourceCard Integration

**From**: SimilarityBadge component
**To**: SourceCard (marketplace source list card)
**Method**: Lazy-loaded via IntersectionObserver on card viewport entry; batched API calls for visible cards

**Notes**: SourceCard renders multiple cards per page; N+1 queries would degrade performance. IntersectionObserver batching + deduplicate by artifact ID will prevent API overload.

</details>

<details>
<summary>Example: Agent Handoff</summary>

### [TBD] - python-backend-engineer → ui-engineer-enhanced

**Completed**: Phase 1 complete — SimilarityService, API endpoint, DuplicatePair.ignored migration all tested and merged

**Next**: Phase 2 frontend — build SimilarArtifactsTab component and integrate into ArtifactDetailsModal. Hook contract in `skillmeat/web/hooks/similarity.ts` is ready.

**Watch Out For**: DuplicatePair.ignored is a new column; make sure repository queries include it in the SELECT list if filtering on ignored pairs later.

</details>

---

**Last Updated**: 2026-02-25
**Document Status**: Active (grows during development)
