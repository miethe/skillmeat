---
title: 'Implementation Plan: Modal Architecture Improvements (R2-R3)'
description: Fix modal navigation handlers in projects pages, create wrapper components,
  and implement app-level data prefetching
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- refactoring
- modal-architecture
created: 2026-01-28
updated: 2026-01-28
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/reports/artifact-modal-architecture-analysis.md
schema_version: 2
doc_type: implementation_plan
feature_slug: modal-architecture-improvements-r2r3
prd_ref: null
---
# Implementation Plan: Modal Architecture Improvements (R2-R3)

**Plan ID**: `IMPL-2026-01-28-MODAL-ARCH-R2R3`
**Date**: 2026-01-28
**Author**: AI Artifacts Engineer (Opus)
**Related Documents**:
- **Report**: `/docs/project_plans/reports/artifact-modal-architecture-analysis.md`

**Complexity**: Small-Medium
**Total Estimated Effort**: 10-14 hours (1-2 days)
**Target Timeline**: 2026-01-28 - 2026-01-29

## Executive Summary

This plan addresses Recommendations 2-3 from the artifact modal architecture analysis, plus newly discovered issues with projects pages. Phase 1 fixes critical bugs where projects pages lack proper navigation handlers, causing broken Source/Deployment links. Phase 2 creates reusable wrapper components to enforce prop contracts and completes the `entity` → `artifact` prop migration. Phase 3 adds app-level data prefetching to eliminate the 2-5 second delay when opening the Sources tab.

## Quick Reference

### Orchestration Commands

```bash
# Execute all phases in sequence
/dev:execute-phase 1  # Fix critical bugs (projects pages)
/dev:execute-phase 2  # Wrapper components + prop migration
/dev:execute-phase 3  # App-level prefetching

# Or run quick feature workflow
/dev:quick-feature "modal-architecture-improvements"
```

### Key Files

| File | Purpose |
|------|---------|
| `skillmeat/web/app/projects/[id]/page.tsx` | Fix missing navigation handlers |
| `skillmeat/web/app/projects/[id]/manage/page.tsx` | Fix incomplete handlers |
| `skillmeat/web/components/shared/CollectionArtifactModal.tsx` | New wrapper for collection pages |
| `skillmeat/web/components/shared/ProjectArtifactModal.tsx` | New wrapper for project pages |
| `skillmeat/web/components/providers.tsx` | Add source data prefetching |
| `skillmeat/web/components/entity/unified-entity-modal.tsx` | Optional: add runtime warnings |

## Implementation Strategy

### Architecture Sequence

Following SkillMeat web frontend patterns:
1. **Bug Fixes** - Fix broken/missing navigation handlers in projects pages
2. **Component Layer** - Create wrapper components with proper contract enforcement
3. **Provider Layer** - Add app-level data prefetching for sources
4. **Testing Layer** - Verify all navigation handlers work across all pages

### Parallel Work Opportunities

- Phase 1 and Phase 2 can partially overlap (wrapper components can be built while fixing bugs)
- Prop migration in Phase 2 can happen independently of wrapper component creation
- Phase 3 is independent and can be done anytime after Phase 1 is validated

### Critical Path

**Phase 1 (Bug Fixes)** → **Phase 2 (Wrapper Components)** → **Phase 3 (Prefetching)**

Phase 1 must complete first to establish baseline functionality. Phase 3 is performance optimization and can be deferred if needed.

## Phase Breakdown

### Phase 1: Fix Critical Bugs - Projects Pages Navigation Handlers

**Duration**: 2-3 hours
**Dependencies**: None
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BUG-001 | Fix `/projects/[id]/page.tsx` handlers | Add `onNavigateToSource` and `onNavigateToDeployment` handlers to `UnifiedEntityModal` | Navigation handlers defined, clicking Source link navigates to source detail page, clicking deployment link navigates to project | 1.5 hrs | ui-engineer-enhanced | None |
| BUG-002 | Fix `/projects/[id]/manage/page.tsx` handlers | Ensure both navigation handlers are properly wired to `UnifiedEntityModal` | Both handlers present, navigation works for deployed artifacts in manage view | 1 hr | ui-engineer-enhanced | None |
| BUG-003 | Manual verification | Test Source/Deployment navigation from projects pages | All navigation links functional from both `/projects/[id]` and `/projects/[id]/manage` pages | 0.5 hrs | ui-engineer-enhanced | BUG-001, BUG-002 |

**Phase 1 Quality Gates:**
- [ ] `/projects/[id]/page.tsx` has both navigation handlers implemented
- [ ] `/projects/[id]/manage/page.tsx` has both navigation handlers verified
- [ ] Clicking Source link from project modal navigates to correct source detail page
- [ ] Clicking Deployment link from project modal navigates to correct project page
- [ ] No console errors or warnings in browser

---

### Phase 2: Component Props Contract Enforcement + Prop Migration

**Duration**: 4-6 hours
**Dependencies**: Phase 1 complete (optional - can overlap)
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| COMP-001 | Create `CollectionArtifactModal` wrapper | Create page-specific wrapper for `/collection` and `/manage` pages that ensures navigation handlers are always provided | Wrapper component created in `components/shared/`, implements both navigation handlers using `useRouter`, accepts `artifact`, `open`, `onClose` props | 1.5 hrs | ui-engineer-enhanced | None |
| COMP-002 | Create `ProjectArtifactModal` wrapper | Create page-specific wrapper for `/projects/[id]` and `/projects/[id]/manage` pages with project-specific navigation logic | Wrapper component created, handles project context, both navigation handlers implemented | 1.5 hrs | ui-engineer-enhanced | None |
| COMP-003 | Update `/collection/page.tsx` | Replace direct `UnifiedEntityModal` usage with `CollectionArtifactModal` wrapper | Page uses wrapper, navigation still works, code is cleaner | 0.5 hrs | ui-engineer-enhanced | COMP-001 |
| COMP-004 | Update `/manage/page.tsx` | Replace direct `UnifiedEntityModal` usage with `CollectionArtifactModal` wrapper | Page uses wrapper, both navigation handlers functional | 0.5 hrs | ui-engineer-enhanced | COMP-001 |
| COMP-005 | Update `/projects/[id]/page.tsx` | Replace direct `UnifiedEntityModal` usage with `ProjectArtifactModal` wrapper | Page uses wrapper, navigation works for deployed artifacts | 0.5 hrs | ui-engineer-enhanced | COMP-002, BUG-001 |
| COMP-006 | Update `/projects/[id]/manage/page.tsx` | Replace direct `UnifiedEntityModal` usage with `ProjectArtifactModal` wrapper | Page uses wrapper, manage view navigation functional | 0.5 hrs | ui-engineer-enhanced | COMP-002, BUG-002 |
| COMP-007 | Complete `entity` → `artifact` prop migration | Search codebase for remaining `entity` prop usage, migrate to canonical `artifact` prop | All pages and components use `artifact` prop consistently, backward compatibility maintained where needed | 1.5 hrs | ui-engineer-enhanced | None |

**Phase 2 Quality Gates:**
- [ ] `CollectionArtifactModal` wrapper created and exports properly
- [ ] `ProjectArtifactModal` wrapper created with project-specific logic
- [ ] All four pages updated to use appropriate wrapper component
- [ ] Navigation handlers work identically before and after wrapper introduction
- [ ] All components use `artifact` prop (or `entity` as backward-compatible alias)
- [ ] No TypeScript errors or warnings
- [ ] Code is cleaner and more maintainable than before

---

### Phase 3: App-Level Data Prefetching

**Duration**: 2-3 hours
**Dependencies**: Phase 1 complete (Phase 2 optional)
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PREF-001 | Add `DataPrefetcher` component | Create component in `components/providers.tsx` that prefetches sources data at app initialization | Component created, calls `useSources(50)` to populate cache, wraps children | 1 hr | ui-engineer-enhanced | None |
| PREF-002 | Integrate prefetcher in provider tree | Add `DataPrefetcher` to the provider chain in `app/providers.tsx` | Prefetcher wraps app, sources data loads on app startup | 0.5 hrs | ui-engineer-enhanced | PREF-001 |
| PREF-003 | Remove eager fetch from modal | Remove the `fetchNextPage()` trigger added in quick fix (artifact-modal-architecture-analysis bug fix) | Modal relies on prefetched data, no longer triggers fetch on open | 0.5 hrs | ui-engineer-enhanced | PREF-002 |
| PREF-004 | Performance verification | Measure time-to-interactive for Sources tab before and after prefetching | Sources tab opens instantly (<200ms) on first access, no visible loading spinner | 1 hr | ui-engineer-enhanced | PREF-003 |

**Phase 3 Quality Gates:**
- [ ] `DataPrefetcher` component created and functioning
- [ ] Sources data prefetches on app initialization
- [ ] Sources tab opens instantly without 2-5 second delay
- [ ] TanStack Query cache properly populated before modal opens
- [ ] No duplicate data fetches or race conditions
- [ ] Performance improvement measurable and consistent

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Wrapper components break existing functionality | High | Low | Thorough manual testing of all four pages before/after, keep wrappers minimal |
| Prefetching impacts initial load performance | Medium | Low | Monitor bundle size, lazy load prefetcher if needed |
| Prop migration breaks backward compatibility | Medium | Low | Use type aliases, gradual migration, test all modal usage points |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Testing reveals additional missing handlers | Medium | Medium | Grep codebase for all `UnifiedEntityModal` usage before starting |
| Prefetching conflicts with TanStack Query patterns | Low | Low | Review TanStack Query docs, use standard prefetch patterns |

---

## Resource Requirements

### Team Composition
- Frontend Developer (ui-engineer-enhanced): 1 FTE for all phases
- QA/Manual Testing: Part-time (Phase 1 and Phase 3 verification)

### Skill Requirements
- React 19, Next.js 15 App Router
- TanStack Query (prefetching, cache management)
- TypeScript (component props, type aliases)
- Radix UI / shadcn component composition patterns

---

## Success Metrics

### Delivery Metrics
- All phases complete within 1-2 days
- Zero regressions in existing navigation functionality
- All TypeScript errors resolved

### Technical Metrics
- Sources tab opens in <200ms (down from 2-5 seconds)
- All pages use wrapper components (consistent contract enforcement)
- 100% prop migration to `artifact` (deprecate `entity`)
- Zero console warnings about missing navigation handlers

### User Experience Metrics
- Navigation links functional across all pages
- Sources tab appears immediately without visible loading delay
- No broken features after refactor

---

## Communication Plan

- Update progress file after each phase completion
- Document any discovered issues in `.claude/worknotes/observations/observation-log-01-26.md`
- Create git commit after each phase with clear message

---

## Post-Implementation

### Monitoring
- Watch for console warnings about missing handlers (if runtime warnings added)
- Monitor TanStack Query DevTools for prefetch behavior
- Track initial page load performance metrics

### Documentation Updates
- Update `/docs/project_plans/reports/artifact-modal-architecture-analysis.md` with "Implemented" status for R2-R3
- Add wrapper component usage examples to component docs (if needed)
- Document prefetching pattern for future similar cases

### Future Improvements
- Evaluate Recommendation 4 (Database-Backed Collections) as separate initiative
- Add unit tests for wrapper components (currently manual testing only)

**Note**: Recommendation 1 (Centralize Entity Mapping) was already implemented as part of the entity-artifact-consolidation refactor. The centralized mapper exists at `lib/api/mappers.ts`.

---

**Progress Tracking:**

`.claude/progress/modal-architecture-improvements/phase-1-progress.md` (created on demand)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-28
