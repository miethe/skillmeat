---
title: 'Implementation Plan: Marketplace Sources Enhancement v1'
description: Detailed phased implementation for rich source details, tags, and advanced
  filtering
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- marketplace
created: 2026-01-18
updated: 2026-01-18
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/enhancements/marketplace-sources-enhancement-v1.md
---
# Implementation Plan: Marketplace Sources Enhancement v1

**Plan ID**: `IMPL-2026-01-18-MARKETPLACE-SOURCES-V1`
**Date**: 2026-01-18
**Author**: Implementation Planner Agent
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/enhancements/marketplace-sources-enhancement-v1.md`
- **GitHub Scanner**: `skillmeat/core/marketplace/github_scanner.py`
- **API Schemas**: `skillmeat/api/schemas/marketplace.py`
- **Frontend Types**: `skillmeat/web/types/marketplace.ts`

**Complexity**: Large (L)
**Total Estimated Effort**: 50-60 story points
**Target Timeline**: 6-8 weeks (single FTE) or 3-4 weeks (parallel backend + frontend)

---

## Executive Summary

This implementation plan breaks down the Marketplace Sources Enhancement v1 feature into 8 sequential phases following MeatyPrompts layered architecture. The feature adds rich repository metadata (description, README), source-level tagging, artifact count breakdown by type, and advanced filtering across the marketplace sources discovery experience.

**Key deliverables**:
- Backend schema extensions with new fields
- Repository detail fetching from GitHub API with graceful degradation
- Source filtering API with composable query parameters
- Redesigned source cards with tags and count badges
- Repo details modal for viewing repository information
- Complete test coverage and documentation

**Critical path**: Database schema -> Repository fetching -> API endpoints -> Frontend integration -> Testing -> Docs.

**Success metrics**: 40%+ filter adoption, 60%+ of sources tagged, <200ms filter response times, >80% test coverage, WCAG 2.1 AA compliance.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture from database to deployment:

| Phase | Name | Duration | Focus |
|-------|------|----------|-------|
| 1 | Database Schema | 3 days | Extend source manifest/storage format |
| 2 | Repository Layer | 3 days | Update repository methods for filtering |
| 3 | Service & API Layer | 3 days | Endpoints, GitHub client integration |
| 4 | Frontend Components | 3 days | SourceCard, FilterBar, Modal |
| 5 | Frontend Pages | 2 days | Marketplace page integration |
| 6 | Frontend Dialogs | 2 days | Import/edit dialogs |
| 7 | Testing & QA | 3 days | Unit, integration, E2E, a11y |
| 8 | Documentation | 1 day | API docs, user guides, ADRs |

### Parallel Work Opportunities

**Track 1 (Backend)**: Phases 1-3 run sequentially; critical path for API contract
**Track 2 (Frontend)**: Can begin design in Phase 3; implement Phases 4-6 in parallel
**Track 3 (Testing)**: Begin test stubs in Phase 3; implement in Phase 7
**Track 4 (Docs)**: Collect during Phases 1-3; document in Phase 8

**Timeline optimization**: Phases 1-3 (backend, 3 weeks) and Phases 4-6 (frontend, 2 weeks starting week 2) overlap, reducing total duration from 8 weeks to 4-5 weeks.

---

## Phase Overview

| Phase | Details | Tasks | Story Points |
|-------|---------|-------|--------------|
| **1-3** | [Backend Implementation](./marketplace-sources-enhancement-v1/phase-1-3-backend.md) | DB-001 to SVC-005 | 30 pts |
| **4-6** | [Frontend Implementation](./marketplace-sources-enhancement-v1/phase-4-6-frontend.md) | UI-001 to DIALOG-006 | 20 pts |
| **7-8** | [Testing & Documentation](./marketplace-sources-enhancement-v1/phase-7-8-validation.md) | TEST-001 to DOC-008 | 20 pts |

---

## Critical Path

```
Phase 1 (DB Schema)
    |
Phase 2 (Repository Layer)
    |
Phase 3 (API Schemas & Endpoints) --> Unblocks Frontend
    |
Phase 4 (Components) --> Phase 5 (Pages) --> Phase 6 (Dialogs)
    |
Phase 7 (Testing)
    |
Phase 8 (Documentation)
```

**Total critical path**: 20 days (4 weeks) sequential. Can be reduced to 2.5-3 weeks with parallel tracks.

---

## Risk Mitigation Summary

| Risk | Mitigation |
|------|------------|
| GitHub API rate limits | 5s timeout, cache in lock file, retry on rescan |
| Large README files (>50KB) | Truncate to 50KB, "View Full on GitHub" link |
| Filter performance with 10K+ sources | Database indexes, cursor pagination, query caching |
| Backward compatibility | Keep artifact_count field, compute from counts_by_type |
| Tag validation bypass | Whitelist validation, parameterized queries, sanitize on display |

### Feature Flags

```python
FEATURE_REPO_DETAILS = True          # Enable description/README fetching
FEATURE_SOURCE_TAGS = True           # Enable source-level tagging
FEATURE_SOURCE_FILTERING = True      # Enable advanced filtering
```

---

## Success Metrics Summary

### Delivery Metrics

| Metric | Target |
|--------|--------|
| On-time delivery | Within +/-10% of 50-60 story points |
| Code coverage | >80% across all layers |
| Performance | Source list <200ms, detail fetch <5s |
| Bug resolution | Zero P0/P1 bugs in first week |

### Business Metrics

| Metric | Target |
|--------|--------|
| Filter adoption | >40% of source list users |
| Tag coverage | >60% of imported sources |
| Repo details views | >25% of source detail views |
| User satisfaction | >4/5 stars in feedback |

---

## Resource Requirements

**Optimal parallel setup (4-5 weeks)**:
- Backend Engineer (1 FTE): Phases 1-3, then support Phase 7
- Frontend Engineer (1 FTE): Design Phase 3, implement Phases 4-6, support Phase 7
- QA/Test Specialist (0.5 FTE): Test prep during Phases 1-6, full-time Phase 7
- UI/UX Designer (0.25 FTE): Review Phase 4 components, accessibility consultation

**Alternative sequential setup (8 weeks)**:
- One full-stack engineer through all phases
- QA specialist joining Phase 5, full-time Phase 7

---

## Key Files Summary

### Backend
- `skillmeat/api/schemas/marketplace.py` - Schema extensions
- `skillmeat/api/routers/marketplace_sources.py` - Filtering endpoints
- `skillmeat/core/marketplace/github_scanner.py` - README fetching
- `skillmeat/core/marketplace/source_manager.py` - Tag management

### Frontend
- `skillmeat/web/components/marketplace/source-card.tsx` - Redesigned card
- `skillmeat/web/components/marketplace/source-filter-bar.tsx` - Filter UI
- `skillmeat/web/app/marketplace/sources/page.tsx` - List page integration
- `skillmeat/web/components/dialogs/create-source-dialog.tsx` - Import dialog

---

## Post-Implementation

### Launch Monitoring (Week 1-2)
- Error rates: GitHub API failures, tag validation errors
- Performance: API response times, frontend load times
- Adoption: Filter usage, tag coverage, repo details views

### Iteration Plan
- **v1.1**: Bug fixes, accessibility issues, performance tuning
- **v2.0**: OR logic for tags, tag autocomplete, batch tag operations, advanced search

---

## Version Control

### Branch Strategy
- Feature branch: `feat/marketplace-sources-enhancement-v1`
- Phase branches (if parallel): `feat/marketplace-sources-db`, `feat/marketplace-sources-api`, `feat/marketplace-sources-ui`

### Commit Format
```
[PHASE][TASK-ID]: Brief description

Relates to: IMPL-2026-01-18-MARKETPLACE-SOURCES-V1
```

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-18
**Status**: Ready for execution

**Phase Details**:
- [Phases 1-3: Backend Implementation](./marketplace-sources-enhancement-v1/phase-1-3-backend.md)
- [Phases 4-6: Frontend Implementation](./marketplace-sources-enhancement-v1/phase-4-6-frontend.md)
- [Phases 7-8: Testing & Documentation](./marketplace-sources-enhancement-v1/phase-7-8-validation.md)
