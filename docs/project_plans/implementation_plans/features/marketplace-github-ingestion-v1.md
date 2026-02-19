---
title: 'Implementation Plan: GitHub Marketplace Ingestion'
description: Phased implementation plan for GitHub repo ingestion with auto-detection,
  manual overrides, and import status tracking
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- marketplace
- github
- ingestion
- discovery
created: 2025-12-03
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md
- /docs/project_plans/SPIKEs/marketplace-github-ingestion-spike.md
schema_version: 2
doc_type: implementation_plan
feature_slug: marketplace-github-ingestion
prd_ref: null
---

# Implementation Plan: GitHub Marketplace Ingestion

**Plan ID**: `IMPL-2025-12-03-marketplace-github-ingestion`
**Date**: 2025-12-03
**Author**: Implementation Planner Agent
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md`
- **SPIKE**: `/docs/project_plans/SPIKEs/marketplace-github-ingestion-spike.md`

**Complexity**: Large
**Total Estimated Effort**: 109 story points
**Target Timeline**: 5-6 weeks
**Team Size**: 4-5 engineers

## Executive Summary

Implement GitHub-backed marketplace sources that auto-scan repositories for Claude artifacts using heuristic detection, provide manual catalog override capabilities, and expose new/updated/imported state through the marketplace UI. This feature bridges the gap between raw GitHub repositories and the SkillMeat marketplace by enabling one-click ingestion with intelligent fallback mechanisms and comprehensive status tracking.

The implementation follows MeatyPrompts layered architecture (Database → Repository → Service → API → UI → Testing → Docs → Deployment) with parallel work opportunities in phases 2-4 and again in phases 5-6.

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Database Layer** - MarketplaceSource and MarketplaceCatalogEntry tables, indexes, RLS policies
2. **Repository Layer** - Data access patterns, query methods, pagination, transaction handling
3. **Service Layer** - GitHub scanning service, detection heuristics, metadata extraction, sync coordination
4. **API Layer** - REST endpoints for source management, rescanning, artifact listing, imports
5. **UI Layer** - Marketplace cards, add modal with stepper, detail views, import workflows
6. **Testing Layer** - Unit, integration, E2E tests for detection algorithms and API workflows
7. **Documentation Layer** - API docs, user guides, developer guides, ADRs
8. **Deployment Layer** - Feature flags, monitoring, staged rollout

### Parallel Work Opportunities

- **Phase 2 & 3 Parallel**: Repository layer can begin while Service design finalizes (small dependency)
- **Phase 4 & 5 Partial Parallel**: UI design/prototyping can start once API surface is finalized (Phase 3.3)
- **Phase 5 & 6 Parallel**: Component testing can begin while UI development completes

### Critical Path

Database → Repository → Service → API → UI (minimal for Phase 5 completion) → Testing → Docs → Deployment

Estimated critical path: 3 weeks for core functionality (Phases 1-5), +1 week for testing/docs, +3-5 days for deployment.

## Phase Breakdown

### Phase 1: Database Foundation

**Duration**: 3 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DB-001 | Schema: MarketplaceSource | Create table for repo metadata: repo_url, branch/tag/sha, root_hint, manual_map, last_sync, last_error, trust_level, visibility, created_at, updated_at | Schema validates, migrations run cleanly, indexes on repo_url + branch | 3 pts | data-layer-expert | None |
| DB-002 | Schema: MarketplaceCatalogEntry | Create table for detected artifacts: source_id FK, artifact_type, path, upstream_url, detected_version, detected_sha, detected_at, confidence_score, status (new/updated/removed/imported), import_date, import_id | Schema validates, migrations run, FK constraints enforce | 3 pts | data-layer-expert | DB-001 |
| DB-003 | RLS Policies | Implement RLS to enforce user isolation on sources and catalog entries | User can only see/modify own sources, RLS policies pass security review | 2 pts | data-layer-expert | DB-001, DB-002 |
| DB-004 | Indexes & Performance | Add indexes: source_id+status on CatalogEntry, last_sync on MarketplaceSource, upstream_url on CatalogEntry for dedup detection | Queries execute within 200ms for typical source (1000+ artifacts), EXPLAIN ANALYZE confirms index usage | 2 pts | data-layer-expert | DB-002, DB-003 |

**Phase 1 Quality Gates**:
- [ ] Migration files created and tested in isolation
- [ ] RLS policies verified against SQL injection/escalation
- [ ] Index coverage meets performance targets (200ms query)
- [ ] Schema supports soft deletes for audit trail
- [ ] Foreign key constraints prevent orphaned records

---

### Phase 2: Repository Layer

**Duration**: 4 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| REPO-001 | MarketplaceSourceRepository | CRUD operations, get_by_id, list_by_user, upsert, delete (soft), cursor pagination | All CRUD ops tested, pagination handles >10k sources | 3 pts | python-backend-engineer | DB-004 |
| REPO-002 | MarketplaceCatalogRepository | CRUD for entries, bulk_insert, get_by_source, list_by_status, find_duplicates (by upstream_url + type + name) | Bulk insert handles 5k entries in <100ms, dedup queries work | 4 pts | python-backend-engineer | DB-004 |
| REPO-003 | Query Methods | get_source_catalog(source_id, filters=[type, status]), compare_catalogs (old vs new for update tracking), count_by_status, filter_by_confidence_range | All filter combos return correct subsets, sorting works | 2 pts | python-backend-engineer | REPO-001, REPO-002 |
| REPO-004 | Transaction Handling | Transaction wrapper for scan+update workflow, rollback on detection errors, connection pooling config | Exceptions trigger rollback, no orphaned records on failure | 2 pts | data-layer-expert | REPO-002 |

**Phase 2 Quality Gates**:
- [ ] All CRUD operations working with correct RLS
- [ ] Cursor pagination tested with edge cases (empty results, single item)
- [ ] Bulk insert performance meets targets
- [ ] Transaction rollback verified on error injection
- [ ] Repository tests achieve >85% coverage

---

### Phase 3: Service Layer

**Duration**: 5 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: backend-architect, python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SVC-001 | DTOs & Models | Create Pydantic models for: CreateSourceRequest, SourceResponse, CatalogEntryResponse, ScanResultDTO, ImportResultDTO | DTOs validate all required fields, serialization round-trips | 2 pts | python-backend-engineer | REPO-004 |
| SVC-002 | Heuristic Detector | Implement scoring algorithm: dir-name match (10pts), manifest presence (20pts), extension match (5pts), depth penalty (-1pt per level), return confidence 0-100 | Algorithm scores representative repos correctly (test with 5 sample repos: organized/messy/mixed), rules match PRD heuristics | 5 pts | backend-architect | SVC-001 |
| SVC-003 | GitHub Scanning Service | Implement scan(source): fetch tree/contents API, apply heuristics, extract metadata per artifact, cache results, apply rate limiting + timeouts (60s default) | Scans typical repo in <30s, handles large repos (>1000 files) with pagination, rate-limit handling works | 5 pts | backend-architect | SVC-002 |
| SVC-004 | README Link Harvester | Parse README for GitHub links, enqueue secondary scans (depth 1 only), dedup by repo URL, cycle guard | Extracts links correctly, dedup prevents duplicates, no infinite loops on circular refs | 3 pts | python-backend-engineer | SVC-003 |
| SVC-005 | Catalog Diff Engine | Compare previous catalog to new scan: mark new (not in old), updated (commit/sha changed), removed (in old not in new) | Diff correctly identifies all three states, status updates persist | 3 pts | backend-architect | SVC-004 |
| SVC-006 | Import Coordinator | Map upstream artifact (URL+type+name) to local collection, handle conflicts, track import state | Import maps correctly, conflicts detected, import_date recorded | 3 pts | python-backend-engineer | SVC-005 |
| SVC-007 | Error Handling & Observability | Implement service-layer error patterns, OpenTelemetry spans for scan/import, structured logging | Errors use ErrorResponse envelope, spans logged for all operations, JSON logs include source_id | 2 pts | backend-architect | SVC-006 |

**Phase 3 Quality Gates**:
- [ ] Unit tests for heuristic scoring (>90% coverage)
- [ ] Heuristic accuracy validation (test 10+ real repos, measure false positive/negative rates)
- [ ] Scan performance meets targets (<30s typical, <60s max)
- [ ] README harvesting cycle-guard tested
- [ ] Diff engine handles all state transitions correctly
- [ ] Service tests achieve >85% coverage
- [ ] OpenTelemetry instrumentation complete

---

### Phase 4: API Layer

**Duration**: 4 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-001 | Marketplace Sources Router | POST /marketplace/sources (create with repo_url, branch, root_hint, pat, manual_map), GET /marketplace/sources (list owned), GET /marketplace/sources/{id}, PATCH /marketplace/sources/{id} | All endpoints return correct responses, OpenAPI docs generated | 3 pts | python-backend-engineer | SVC-007 |
| API-002 | Marketplace Rescan Endpoint | POST /marketplace/sources/{id}/rescan (async, background job), returns immediate status, stores job_id for polling | Endpoint accepts request, returns 202 Accepted, scan completes in background | 2 pts | python-backend-engineer | API-001 |
| API-003 | Marketplace Artifacts Listing | GET /marketplace/sources/{id}/artifacts (filters: type, status, confidence_min), pagination, sorting (by status, confidence, type) | Filters work correctly, pagination handles large results, sorting persists | 2 pts | python-backend-engineer | API-001 |
| API-004 | Marketplace Import Endpoint | POST /marketplace/sources/{id}/import (single or bulk with artifact_ids), returns import result with conflicts, maps to collection | Single and bulk imports work, conflicts reported, artifacts added to collection | 3 pts | backend-architect | SVC-006 |
| API-005 | Error & Validation | Request validation (repo_url format, PAT validation if provided), response formatting (ErrorResponse envelope), rate limiting | Invalid requests return 400 with clear messages, consistent error responses | 2 pts | python-backend-engineer | API-004 |
| API-006 | Authentication & Security | Clerk integration for user context, encrypt PAT at rest, sanitize inputs (path traversal guard for root_hint) | Auth enforces user isolation, PATs encrypted, path validation works | 2 pts | backend-architect | API-005 |
| API-007 | Background Job Integration | Setup Celery/APScheduler integration for async scans (if not exists), job result tracking, timeout handling | Async scans complete successfully, timeouts trigger gracefully, job status queryable | 2 pts | backend-architect | API-002 |

**Phase 4 Quality Gates**:
- [ ] All endpoints return correct status codes and response shapes
- [ ] OpenAPI documentation complete and accurate
- [ ] Error responses consistent with ErrorResponse envelope
- [ ] Authentication verified (user isolation enforced)
- [ ] Rate limiting functional
- [ ] Background job execution works
- [ ] API tests achieve >80% coverage

---

### Phase 5: UI Layer

**Duration**: 5 days
**Dependencies**: Phase 4 complete (can start design earlier via partial parallel)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, ui-designer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-001 | Marketplace List Page Design | Design /marketplace cards: name, source repo, counts by type, New/Updated badges, last sync, trust badge, error chip, quick actions (Rescan, Open) | Figma mockups approved, all states designed (loading, error, success, empty) | 2 pts | ui-designer | API-007 |
| UI-002 | Add Source Modal (Stepper) | Step 1: Repo (URL + branch/tag/sha + root + PAT), Step 2: Scan Results (preview, skip/rescan), Step 3: Manual Catalog (optional per-type dirs), Step 4: Review + Create | Modal handles all steps, validation at each step, back/next navigation works | 3 pts | frontend-developer | UI-001 |
| UI-003 | Marketplace Detail Page | Header: sync status, last sync, error state; filters by type/status; catalog grid (matching /manage style) with status chips | Page loads source and catalog, filters work, chips display correctly | 3 pts | ui-engineer-enhanced | UI-002 |
| UI-004 | Artifact Cards & Status Chips | Reuse artifact modal, add chips (Imported, New, Update available, Unavailable), disable sync/status controls until imported, show upstream URL + confidence | Card rendering works, chips display correctly, modal integration complete | 3 pts | frontend-developer | UI-003 |
| UI-005 | API Integration | Integrate all endpoints: createSource, listSources, rescanSource, listArtifacts (with filters), importArtifacts | All API calls work, data flows correctly to UI, loading states managed | 4 pts | frontend-developer | UI-004 |
| UI-006 | Loading & Error States | Loading spinners for scan/import, error messages from API, retry logic for failed scans, disabled states for in-progress ops | All states display correctly, users can retry failed scans, clear error messages shown | 2 pts | ui-engineer-enhanced | UI-005 |
| UI-007 | Accessibility & Responsive | WCAG 2.1 AA compliance, keyboard navigation, mobile responsive (test on 3 breakpoints) | Axe audit <2 violations, keyboard nav works, mobile layout tested | 2 pts | ui-engineer-enhanced | UI-006 |

**Phase 5 Quality Gates**:
- [ ] All pages render in all states (loading, success, error, empty)
- [ ] API integration verified (mock and real server)
- [ ] User interactions functional (click, type, submit)
- [ ] Mobile responsiveness validated
- [ ] Accessibility requirements met (Axe scan <2 violations, keyboard nav works)
- [ ] Component library integration complete

---

### Phase 6: Testing Layer

**Duration**: 4 days
**Dependencies**: Phases 5 and 6 parallel (some tests can run concurrently)
**Assigned Subagent(s)**: testing specialist, python-backend-engineer, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Unit Tests (Backend) | Test heuristic scorer, diff engine, catalog builder, DTOs, repository methods | >90% coverage, all edge cases covered (empty repos, no matches, high confidence) | 4 pts | python-backend-engineer | UI-007 |
| TEST-002 | Integration Tests (API) | Test all endpoints: create, list, rescan, artifacts list, import; verify DB state changes | All endpoints tested with valid/invalid inputs, DB state correct after operations | 3 pts | python-backend-engineer | TEST-001 |
| TEST-003 | Service Tests | Test scan pipeline end-to-end with mock GitHub, heuristic accuracy on 10+ sample repos | Scan handles typical/edge cases, heuristics accurate (measure false positive/negative rates) | 3 pts | python-backend-engineer | TEST-002 |
| TEST-004 | Component Tests | Test modal stepper, detail page filters, artifact cards, status chips; verify state management | All interactions tested, prop changes reflected, event handlers work | 3 pts | frontend-developer | TEST-001 |
| TEST-005 | E2E Tests (Playwright) | Critical paths: create source → scan → review → import; handle errors; manual catalog override | Paths execute successfully, errors handled gracefully, import persists | 3 pts | testing specialist | TEST-004 |
| TEST-006 | Performance Tests | Scan <30s for typical repo, API responses <200ms (p95), UI renders in <1s, no memory leaks | Performance benchmarks met, no memory leaks detected | 2 pts | python-backend-engineer | TEST-005 |
| TEST-007 | Security Tests | PAT encryption/decryption, path traversal guard on root_hint, RLS enforcement, rate limiting | All security checks pass, no vulnerabilities detected | 2 pts | backend-architect | TEST-006 |

**Phase 6 Quality Gates**:
- [ ] Code coverage >85% (backend >90%, frontend >80%)
- [ ] All tests passing in CI/CD
- [ ] E2E tests cover critical journeys
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] No critical vulnerabilities detected

---

### Phase 7: Documentation Layer

**Duration**: 3 days
**Dependencies**: Phase 6 complete
**Assigned Subagent(s)**: documentation-writer, api-documenter, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DOC-001 | API Documentation | Endpoint docs (request/response examples), error codes, rate limits, authentication requirements | All 7 endpoints documented with examples, error codes listed | 2 pts | api-documenter | TEST-007 |
| DOC-002 | User Guide | How-to: add source, interpret scan results, override catalog, import artifacts, interpret status chips | Step-by-step guide, screenshots, common issues/FAQ | 2 pts | documentation-writer | TEST-007 |
| DOC-003 | Developer Guide | Architecture overview, heuristic scoring algorithm, service patterns, extending detection rules | Developers can extend heuristics, understand data flow | 2 pts | documentation-writer | DOC-002 |
| DOC-004 | ADR: GitHub Ingestion | Decision records: why heuristic detection, why background jobs, confidence threshold strategy | ADR explains trade-offs, alternatives considered | 1 pt | backend-architect | DOC-003 |
| DOC-005 | Changelog Entry | Document feature in CHANGELOG.md with version and highlights | CHANGELOG updated with feature, version, date | 1 pt | documentation-writer | DOC-004 |

**Phase 7 Quality Gates**:
- [ ] API documentation complete and accurate
- [ ] User guide tested by non-technical reviewer
- [ ] Developer guide allows safe extension
- [ ] ADR explains trade-offs and decisions
- [ ] CHANGELOG updated
- [ ] All docs reviewed and approved

---

### Phase 8: Deployment Layer

**Duration**: 3 days
**Dependencies**: Phase 7 complete
**Assigned Subagent(s)**: DevOps, backend-architect, lead-pm

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DEPLOY-001 | Feature Flags | Implement feature flag for marketplace GitHub ingestion (FF_MARKETPLACE_GITHUB_INGESTION) | Flag can be toggled per environment, feature hidden when disabled | 1 pt | backend-architect | DOC-005 |
| DEPLOY-002 | Monitoring & Alerts | Setup telemetry: scan duration, artifact count by type/status, import success rate, error rates; add alerts for >10% error rate | Dashboards show all metrics, alerts trigger on threshold | 2 pts | backend-architect | DEPLOY-001 |
| DEPLOY-003 | Staging Deployment | Deploy to staging, run smoke tests (create source, scan, verify catalog), verify monitoring | Staging deployment successful, feature functional, monitoring data flowing | 1 pt | DevOps | DEPLOY-002 |
| DEPLOY-004 | Production Rollout | Staged rollout: 10% → 50% → 100% over 3 days, monitor metrics, customer notifications | Rollout completed, no major incidents, customer informed | 2 pts | lead-pm | DEPLOY-003 |
| DEPLOY-005 | Post-Launch Support | Monitor error rates, customer feedback, hotfix critical issues, prepare rollback plan | Feature stable in production, customer satisfaction >4/5, no rollback needed | 1 pt | backend-architect | DEPLOY-004 |

**Phase 8 Quality Gates**:
- [ ] Feature flag working in all environments
- [ ] Monitoring and alerting active
- [ ] Staging deployment successful
- [ ] Production rollout completed
- [ ] Post-launch metrics healthy (<1% error rate)
- [ ] Customer feedback positive (>4/5 satisfaction)

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| GitHub API rate limiting blocks scans | High | Medium | Implement exponential backoff, cache tree results, provide manual PAT override, document rate limits |
| Heuristic detection produces high false positive rate | High | Medium | Validate on 20+ sample repos, allow manual override, set conservative confidence thresholds, A/B test |
| Large repos timeout (>60s) | Medium | Medium | Implement streaming tree API, add timeout configuration, surface timeout errors clearly |
| PAT encryption/decryption failure | High | Low | Use industry-standard encryption (ChaCha20-Poly1305), test encrypt/decrypt in integration tests, audit logging |
| Database performance degrades with 100k+ entries | Medium | Low | Pre-optimize queries, implement archival for old entries, test with large datasets |
| Import conflicts crash or data loss | High | Low | Comprehensive conflict detection, transaction rollback, audit trail of all imports |
| Memory leak in async scan jobs | Medium | Low | Memory profiling in load tests, job cleanup on completion, implement circuit breaker |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Scope creep (README harvesting, multi-depth scans) | Medium | High | Change request process, strictly enforce phase scope, prioritize MVP features |
| Heuristic accuracy requires rework | Medium | Medium | Early validation on sample repos (Phase 3.2), adjust thresholds if needed |
| Integration with existing marketplace broker takes longer than expected | Medium | Medium | Clarify interface during Phase 3, leverage existing broker patterns |
| UI complexity requires design iteration | Low | Medium | Early design review (Phase 5.1), prototype with stakeholders |

### Mitigation Summary

1. **GitHub API**: Implement robust rate limit handling, cache aggressively, provide manual overrides
2. **Detection Accuracy**: Validate early and often, test on diverse repos, allow manual overrides
3. **Performance**: Profile and optimize critical paths (scan, import), implement caching, test at scale
4. **Security**: Use industry-standard encryption, audit all sensitive operations, test threat scenarios
5. **Scope**: Enforce MVP boundaries, manage feature requests through formal change process

---

## Resource Requirements

### Team Composition

- **Backend Architect**: 1.5 FTE (Phases 1-5, 8), part-time (6-7) - Leads service design, API architecture, observability
- **Backend Engineer**: 2 FTE (Phases 2-4, 6-7), part-time (1, 5, 8) - Implements repos, services, API endpoints
- **Frontend Engineer**: 1.5 FTE (Phase 5, 6), part-time (1, 7-8) - UI development, integration testing
- **UI/UX Designer**: 0.5 FTE (Phase 5) - Design systems, component design
- **QA/Testing Specialist**: 0.5 FTE (Phase 6) - E2E testing, security testing
- **DevOps/Platform**: 0.5 FTE (Phase 8, part-time throughout) - Deployment, monitoring, feature flags

### Skill Requirements

- **Backend**: Python, FastAPI, SQLAlchemy, async/await, GitHub API, Celery/APScheduler
- **Frontend**: TypeScript, React, React Query, Tailwind CSS, testing libraries
- **Database**: SQL, query optimization, indexing, RLS policies
- **DevOps**: Feature flags, monitoring (OpenTelemetry), Docker, staging/production deployments
- **Testing**: Unit testing, integration testing, E2E testing, performance profiling

### Development Tools

- PostgreSQL 14+ with RLS support
- Python 3.9+, FastAPI 0.100+, SQLAlchemy 2.0+
- Node.js 18+, React 18+, Next.js 15+
- Testing: pytest, Playwright, Jest/Vitest
- Monitoring: OpenTelemetry, Prometheus, Grafana (optional)
- CI/CD: GitHub Actions (existing)

---

## Success Metrics

### Delivery Metrics

- On-time delivery (±10% of timeline estimate)
- Code coverage: Backend >90%, Frontend >80%
- Zero P0 bugs in first 2 weeks of production
- Performance targets met: scan <30s (typical), API <200ms (p95), UI <1s render

### Business Metrics

- User adoption: >50% of marketplace users add ≥1 GitHub source within 1 month
- Artifact discovery rate: average 50+ artifacts per source scan
- Import success rate: >95%
- Error rate: <1% (scan/import operations)
- User satisfaction: >4/5 for feature quality

### Technical Metrics

- 100% API documentation coverage
- 100% WCAG 2.1 AA compliance
- Security review: zero critical vulnerabilities
- Monitoring: 100% of critical operations instrumented
- Scalability: handles 10k+ sources, 1M+ catalog entries

---

## Communication Plan

- **Daily Standups**: 15 min sync on blockers/progress (Phases 1-3 critical)
- **Weekly Status Reports**: Summary of completed phases/tasks, upcoming milestones
- **Formal Phase Reviews**: Review + sign-off before advancing to next phase (before DB, API, UI, Deployment phases)
- **Stakeholder Updates**: Bi-weekly demos starting Phase 5
- **Slack Channel**: #marketplace-github-ingestion for async updates

---

## Post-Implementation

- **Performance Monitoring**: Dashboard showing scan duration, artifact counts, error rates by source
- **Customer Feedback Loop**: Survey users after 2 weeks, collect feature requests
- **Technical Debt**: Capture refactoring opportunities in GitHub issues
- **Feature Iteration**: Plan Phase 2 features (multi-depth scanning, README-only repos, non-GitHub sources)
- **Usage Analytics**: Track which heuristics are most effective, false positive/negative rates

---

## Critical Dependencies & Assumptions

### External Dependencies

- GitHub API availability (documented rate limits)
- Existing marketplace broker infrastructure available
- Clerk authentication fully functional
- PostgreSQL with RLS support available

### Internal Dependencies

- `skillmeat/core/discovery.py` - Artifact detection service available
- `skillmeat/core/github_metadata.py` - Metadata extraction utilities
- `skillmeat/sources/github.py` - GitHub client with auth/version resolution
- `skillmeat/api/routers/marketplace.py` - Existing marketplace endpoint patterns
- React Query for frontend state management

### Assumptions

- Background job infrastructure (Celery/APScheduler) exists or will be implemented early
- PostgreSQL RLS policies can be applied to marketplace tables
- GitHub free tier rate limits acceptable for MVP (60 requests/hour unauthenticated, 5000/hour with PAT)
- Manual catalog overrides are optional (heuristics work for 80%+ of cases)
- README harvesting limited to depth=1 to keep scope manageable

---

## Implementation Notes

### Database Considerations

- Use UUID for primary keys (consistency with SkillMeat patterns)
- `MarketplaceSource.manual_map` stored as JSONB for flexibility
- `MarketplaceCatalogEntry.status` as enum (new, updated, removed, imported)
- Add `detected_at` and `import_date` for audit trail and sync logic
- Soft deletes via `deleted_at` timestamp for compliance

### Service Layer Patterns

- Heuristic scoring: modular and easily extensible (add new rules without code changes)
- Scan pipeline: async with progress tracking and cancellation support
- Error handling: distinguish between retryable (rate limit, timeout) and fatal (invalid URL) errors
- Caching: cache GitHub tree results with TTL to reduce API calls

### API Patterns

- Use 202 Accepted for long-running operations (scans)
- Provide job status endpoint for polling (or WebSocket in future)
- Cursor-based pagination for large result sets
- Filter by confidence threshold (allow clients to filter low-confidence matches)

### UI Patterns

- Stepper modal for onboarding (Repo info → Scan → Manual Catalog → Review)
- Status chips for quick visual identification (color-coded)
- Reuse artifact modal for detail views (consistency)
- Skeleton loading for async operations

---

## Detailed Task Dependencies

**Phase 1**: No external dependencies (database setup first)

**Phase 2**: Requires Phase 1 complete

**Phase 3**: Requires Phase 2 complete; can start design in parallel with Phase 2

**Phase 4**: Requires Phase 3 complete; API design can be finalized during Phase 3.7

**Phase 5**: Requires Phase 4 complete (but can prototype UI mockups in Phase 3)

**Phase 6**: Requires Phase 5 complete (but some unit tests can run against Phase 2/3 code)

**Phase 7**: Requires Phase 6 complete

**Phase 8**: Requires Phase 7 complete

---

## Progress Tracking

See `.claude/progress/marketplace-github-ingestion/` for detailed phase-by-phase progress files:
- `phase-1-progress.md` - Database foundation
- `phase-2-progress.md` - Repository layer
- `phase-3-progress.md` - Service layer
- `phase-4-progress.md` - API layer
- `phase-5-progress.md` - UI layer
- `phase-6-progress.md` - Testing layer
- `phase-7-progress.md` - Documentation layer
- `phase-8-progress.md` - Deployment layer

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2025-12-03

---

## Appendix: Heuristic Scoring Reference

### Scoring Algorithm (Baseline)

```
score = 0

# Directory hints (case-insensitive)
if artifact_dir in ['.claude/skills', '.claude/agents', '.claude/commands', 'skills', 'agents', 'commands', 'tools', 'plugins', 'mcp', 'mcp-servers', 'hooks', 'bundles']:
    score += 10

# Manifest presence
if manifest_file_exists (manifest.json, manifest.yaml, manifest.toml, skills.toml):
    score += 20

# File hints
if filename matches: skill*.md, skill*.yaml, agent*.md, command*.md:
    score += 5

# Depth penalty (penalize deeply nested artifacts)
score -= (depth_level - 1)

# Confidence = min(max(score, 0), 100)
```

### Example Scores

- `.claude/skills/my-skill/skill.yaml` → 10 (dir) + 5 (filename) + 0 (depth) = 15 → Confidence: 15%
- `.claude/skills/manifest.toml` → 10 (dir) + 20 (manifest) + 0 (depth) = 30 → Confidence: 30%
- `skills/my-skill/skill.md` → 10 (dir) + 5 (filename) + 0 (depth) = 15 → Confidence: 15%
- `skills/manifest.yaml` → 10 (dir) + 20 (manifest) + 0 (depth) = 30 → Confidence: 30%
- `src/tools/my-agent/agent.yaml` → 0 (dir no match) + 5 (filename) + (-1) (depth) = 4 → Confidence: 4%

### README Link Harvesting Pattern

```
# Regex to extract GitHub links
pattern = r'https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)'

# For each unique repo found:
# 1. Dedup by repo URL
# 2. Check for cycles (don't scan if already in this source's link tree)
# 3. Enqueue single-depth scan
# 4. Cap total linked repos at 5 per source
```

