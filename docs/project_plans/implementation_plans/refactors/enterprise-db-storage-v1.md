---
title: 'Implementation Plan: Enterprise Database Storage'
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-03-06
updated: '2026-03-06'
feature_slug: enterprise-db-storage
feature_version: v1
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: null
scope: Enterprise PostgreSQL storage backend replacing filesystem for SaaS deployments
effort_estimate: TBD (calculated from phase estimates)
architecture_summary: EnterpriseDBRepository implementations fulfilling PRD 1 interfaces,
  PostgreSQL schema with tenant isolation, API content delivery, CLI enterprise mode,
  and local-to-cloud migration tooling
related_documents:
- docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
- docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
- docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
owner: python-backend-engineer
contributors:
- data-layer-expert
- backend-architect
priority: high
risk_level: high
category: product-planning
tags:
- enterprise
- database
- postgresql
- storage
- multi-tenant
- migration
milestone: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Implementation Plan: Enterprise Database Storage

## Executive Summary

This plan orchestrates the migration of SkillMeat from a filesystem-centric personal collection manager to an enterprise-capable, cloud-database-backed SaaS platform. The implementation fulfills the repository interfaces defined in PRD 1 with PostgreSQL-backed `EnterpriseDBRepository` implementations, adds multi-tenant support via `tenant_id` filtering, enables stateless API deployments, and provides automated migration tooling for existing local vault users.

**Key Outcomes:**
- EnterpriseDBRepository implementations fulfilling all PRD 1 interfaces
- PostgreSQL schema with tenant isolation via `tenant_id` columns
- API-driven artifact content delivery (`GET /api/v1/artifacts/{id}/download`)
- CLI enterprise mode (`skillmeat deploy --enterprise`)
- Automated migration tooling (`skillmeat enterprise migrate`)
- Full test coverage and zero breaking changes for local users

**Complexity:** Extra Large (XL) | **Phases:** 7 | **Estimated Timeline:** 8-12 weeks

---

## Implementation Strategy

### Architecture & Sequencing

**Critical Dependencies:**
- **PRD 1 (Repository Pattern Refactor)** MUST be complete first
  - Provides abstract repository interfaces (IArtifactRepository, ICollectionRepository, etc.)
  - Provides DI container setup for repository swapping
  - Provides RequestContext with tenant_id field
- **PRD 2 (AAA & RBAC Foundation)** MUST be complete before Phase 4
  - Provides AuthContext with tenant_id
  - Provides multi-tenant scoping mechanisms

**Layered Sequence (MP Architecture):**
1. **Database Layer** (Phase 1): PostgreSQL schema with enterprise tables and tenant scoping
2. **Repository Layer** (Phase 2): EnterpriseDBRepository implementations with automatic tenant filtering
3. **Service Layer** (Phase 3): Content delivery service for artifact streaming
4. **API Layer** (Phase 3): Content download endpoints, enterprise middleware/guards
5. **CLI Layer** (Phase 4): Enterprise mode detection, API-driven deploy/sync
6. **Migration Layer** (Phase 5): Local→Cloud migration tooling with rollback
7. **Testing & Validation** (Phase 6): Unit, integration, E2E with docker-compose PostgreSQL
8. **Documentation** (Phase 7): Setup guides, migration guides, API docs, ADR

**Parallelization Strategy:**
- Phases 1-2 sequential (schema before repos)
- Phases 3-5 can run in parallel after Phase 2 (independent concerns: API, CLI, migration)
- Phase 6 testing runs alongside implementation (test-alongside pattern)
- Phase 7 documentation runs in parallel with Phase 6

**Critical Path:** Phase 1 → Phase 2 → Phases 3/4/5 (parallel) → Phase 6 → Phase 7

---

## Phase Breakdown

### Phase Summary Table

| Phase | Title | Dependencies | Duration | Effort | Key Subagents |
|-------|-------|--------------|----------|--------|----------------|
| 1 | Enterprise Schema & Database Foundation | PRD 1 complete | 2-3 weeks | 18-22 pts | data-layer-expert, backend-architect |
| 2 | Enterprise Repository Implementation | Phase 1 complete | 2 weeks | 16-20 pts | python-backend-engineer, data-layer-expert |
| 3 | API Content Delivery Endpoints | Phase 2 complete | 1.5 weeks | 10-12 pts | python-backend-engineer, backend-architect |
| 4 | CLI Enterprise Mode | Phase 2 complete | 1.5 weeks | 8-10 pts | python-backend-engineer |
| 5 | Cloud Migration Tooling | Phase 2, 3, 4 | 1.5 weeks | 12-14 pts | python-backend-engineer |
| 6 | Testing & Validation | Phases 1-5 | 2 weeks | 14-16 pts | python-backend-engineer, data-layer-expert |
| 7 | Documentation & Deployment | Phases 1-6 | 1 week | 8-10 pts | documentation-writer, api-documenter |

**Total Estimated Effort:** 86-104 story points | **Timeline:** 8-12 weeks

---

## Detailed Phase Plans

For detailed task breakdowns, acceptance criteria, and subagent assignments, see:

- [Phase 1: Enterprise Schema & Database Foundation](./enterprise-db-storage-v1/phase-1-schema.md)
- [Phase 2: Enterprise Repository Implementation](./enterprise-db-storage-v1/phase-2-repositories.md)
- [Phase 3: API Content Delivery Endpoints](./enterprise-db-storage-v1/phase-3-api.md)
- [Phase 4: CLI Enterprise Mode](./enterprise-db-storage-v1/phase-4-cli.md)
- [Phase 5: Cloud Migration Tooling](./enterprise-db-storage-v1/phase-5-migration.md)
- [Phase 6: Testing & Validation](./enterprise-db-storage-v1/phase-6-testing.md)
- [Phase 7: Documentation & Deployment](./enterprise-db-storage-v1/phase-7-docs.md)

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| PostgreSQL connection pooling bottleneck | HIGH | MEDIUM | Implement async SQLAlchemy connections, connection pool sizing, monitoring from Day 1 |
| Multi-tenant data leakage via query filters | CRITICAL | LOW | Mandatory WHERE tenant_id filter in all queries, code review checkpoints, integration tests with multiple tenants |
| Breaking changes to existing local deployment | HIGH | MEDIUM | Preserve LocalFileSystemRepository 100%, feature-flag enterprise mode, rollback plan |
| Migration data loss (local→cloud) | CRITICAL | LOW | Transaction-wrapped migrations, checksum validation, dry-run mode, full rollback support |
| Schema versioning mismatch between local/enterprise | HIGH | MEDIUM | Consolidated Alembic migrations, version lock in config, clear upgrade/downgrade paths |
| API performance under high artifact count | MEDIUM | MEDIUM | Pagination mandatory, indexed lookups, caching strategy (30s stale time for content), load testing baseline |

### Schedule Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| PRD 1 completion delays | CRITICAL | MEDIUM | Coordinate with repo-pattern refactor team, identify blocking repositories early |
| PostgreSQL setup/maintenance overhead | MEDIUM | MEDIUM | Provide docker-compose reference, managed PostgreSQL guide, automated backups setup |
| Test environment complexity | MEDIUM | MEDIUM | Automated docker-compose test database, seed data scripts, CI/CD test fixtures |

### Organizational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Knowledge silos (enterprise-specific code) | MEDIUM | MEDIUM | Pair programming on Phases 1-2, documentation during implementation, ADR for major decisions |
| Monitoring/observability gaps | MEDIUM | LOW | Log all repository calls with request_id, trace enterprise vs. local paths, metrics dashboard setup |

---

## Quality Gates

### Per-Phase Quality Gates

**Phase 1 Complete When:**
- All PostgreSQL schema migrations created and tested against Docker container ✓
- Schema supports tenant isolation via WHERE clauses ✓
- artifact_versions table with content_hash and markdown_payload columns ✓
- Alembic migration docs written ✓
- No breaking changes to existing SQLite schema ✓

**Phase 2 Complete When:**
- All IArtifactRepository, ICollectionRepository methods implemented ✓
- 100% of repository methods apply automatic tenant_id filtering ✓
- RequestContext tenant_id properly threaded through DI ✓
- Unit tests cover single-tenant isolation (negative tests) ✓
- Performance benchmarks show <5ms overhead vs direct SQL ✓

**Phase 3 Complete When:**
- GET /api/v1/artifacts/{id}/download returns valid JSON with file tree + contents ✓
- Content streaming properly chunks large files ✓
- Version-aware downloads work (with ?version query param) ✓
- 100% API test coverage with docker-compose PostgreSQL ✓

**Phase 4 Complete When:**
- `skillmeat deploy --enterprise` calls API instead of copying files ✓
- `skillmeat sync --enterprise` polls API for latest content ✓
- Enterprise auth (PAT) properly configured and validated ✓
- CLI fallback to local mode if env var not set ✓
- E2E test covers full deploy→project flow ✓

**Phase 5 Complete When:**
- `skillmeat enterprise migrate` reads local vault correctly ✓
- All artifacts migrated with checksum validation ✓
- Rollback creates backup manifest ✓
- Progress reporting shows migration status ✓
- Dry-run mode prevents accidental mutations ✓

**Phase 6 Complete When:**
- Unit test coverage >90% for enterprise repos ✓
- Integration tests with docker-compose PostgreSQL ✓
- E2E tests cover deploy→sync→download cycle ✓
- Multi-tenant isolation tests pass (negative cases) ✓
- Performance regression tests pass (benchmarks established in Phase 2) ✓

**Phase 7 Complete When:**
- Enterprise setup guide complete with docker-compose examples ✓
- Migration guide covers all edge cases (no artifacts, large collections, etc.) ✓
- API documentation updated with enterprise endpoints ✓
- ADR written for architecture decisions ✓
- CHANGELOG entries for breaking changes (none expected) ✓

---

## Success Metrics

**Delivery Metrics:**
- All 7 phases delivered on schedule ✓
- Zero PRs blocked on PRD 1 completion ✓
- 100% of acceptance criteria met ✓

**Quality Metrics:**
- Zero multi-tenant data leakage incidents (test coverage >95%) ✓
- 100% of enterprise repository methods have automatic tenant filtering ✓
- API response times <200ms for artifact downloads (benchmarked) ✓
- Migration success rate 100% (dry-run validation + checksums) ✓

**Operational Metrics:**
- PostgreSQL connection pool operates at <80% utilization under load ✓
- Local (filesystem) deployment unchanged performance ✓
- Migration downtime <5 minutes for typical collections ✓

---

## Pre-Implementation Checklist

Before Phase 1 begins:

- [ ] Confirm PRD 1 (Repository Pattern) is >90% complete
- [ ] Confirm PRD 2 (AAA & RBAC) is planned and scheduled
- [ ] Allocate PostgreSQL instance for production (managed service or self-hosted)
- [ ] Set up docker-compose PostgreSQL for development/testing
- [ ] Review CLAUDE.md for architecture patterns (hexagonal, write-through, data flow)
- [ ] Schedule kickoff meeting with subagent teams (Phase 1: data-layer-expert + backend-architect)
- [ ] Create GitHub milestones for all 7 phases
- [ ] Set up monitoring/observability baseline for enterprise queries

---

## Integration Points

### Upstream Integrations (PRD 1 & 2)

- **PRD 1 Output Used:** IArtifactRepository, ICollectionRepository, RequestContext, DI container setup
- **PRD 2 Output Used:** AuthContext with tenant_id, multi-tenant scoping mechanisms
- **This Plan Output Used By:** PRD 2 needs `tenant_id` tracking in artifacts/collections; future SaaS platform uses EnterpriseDBRepository

### Downstream Integrations

- Frontend web UI: No changes required (API-compatible)
- CLI users (local mode): No changes required (LocalFileSystemRepository unchanged)
- SaaS deployment platform: Uses EnterpriseDBRepository + PostgreSQL, adds deployment tracking
- Marketplace/plugin system: Can integrate with EnterpriseDBRepository for shared artifact discovery

---

## File Organization

```
skillmeat/
├── cache/
│   ├── models/
│   │   ├── enterprise_artifacts.py      [Phase 1] Enterprise artifact tables
│   │   ├── enterprise_collections.py    [Phase 1] Enterprise collection tables
│   │   └── enterprise_schema.py         [Phase 1] Shared schema utilities
│   ├── repositories/
│   │   ├── enterprise_base.py           [Phase 2] Base for enterprise repos
│   │   ├── enterprise_artifact.py       [Phase 2] EnterpriseArtifactRepository
│   │   ├── enterprise_collection.py     [Phase 2] EnterpriseCollectionRepository
│   │   └── enterprise_factory.py        [Phase 2] DI factory for repo switching
│   ├── migrations/
│   │   └── versions/
│   │       ├── 20260306_*_enterprise_schema.py [Phase 1] Schema creation
│   │       └── 20260306_*_tenant_columns.py    [Phase 1] Tenant isolation
├── api/
│   └── routers/
│       └── enterprise_download.py       [Phase 3] Content delivery endpoints
├── core/
│   ├── services/
│   │   └── enterprise_content.py        [Phase 3] Content streaming service
│   └── enterprise_config.py             [Phase 4] Enterprise mode config
├── cli/
│   └── commands/
│       ├── enterprise_deploy.py         [Phase 4] Enterprise deploy logic
│       ├── enterprise_sync.py           [Phase 4] Enterprise sync logic
│       └── enterprise_migrate.py        [Phase 5] Migration tooling
└── tests/
    ├── unit/
    │   └── test_enterprise_repos.py     [Phase 6] Repository tests
    ├── integration/
    │   └── test_enterprise_integration.py [Phase 6] API + Repo tests
    └── e2e/
        └── test_enterprise_e2e.py       [Phase 6] Full cycle tests
```

---

## Key Architecture Decisions

### Decision 1: PostgreSQL vs DocumentDB

**Choice:** PostgreSQL with JSONB columns for tags/metadata

**Rationale:**
- JSONB allows flexibility without schema changes
- Superior transaction support for migrations
- Alembic expertise already in codebase
- Better tooling and multi-tenant examples in ecosystem
- Lower operational overhead vs DocumentDB

**Trade-off:** Less document-native than Mongo, but relational structure fits artifact model

### Decision 2: Tenant Scoping Strategy

**Choice:** WHERE tenant_id = ? in all queries (application-enforced)

**Rationale:**
- PostgreSQL RLS requires additional setup and may impact performance
- Application-enforced allows feature-flagging (local mode has no tenant scoping)
- Easier to test and debug
- Aligns with existing RequestContext threading

**Future:** Can migrate to RLS once PostgreSQL 15+ becomes baseline

### Decision 3: Content Versioning

**Choice:** artifact_versions table with content_hash + markdown_payload

**Rationale:**
- Allows history without duplication
- content_hash enables deduplication across collections
- Enables version-aware downloads for CI/CD (pin to content_hash)
- Aligns with existing ArtifactVersion model

### Decision 4: API Content Delivery Format

**Choice:** JSON payload with file tree + contents (not streaming binary)

**Rationale:**
- Easier to implement version tracking
- Simpler to parse in CLI (no streaming protocol)
- Aligns with artifact model (Markdown files, JSON metadata)
- Can add binary streaming in future phase if needed

**Format Example:**
```json
{
  "artifact_id": "skill:frontend-design",
  "version": "v1.2.0",
  "content_hash": "sha256...",
  "files": [
    {
      "path": "frontend-design.md",
      "content": "# Skill...",
      "is_markdown": true
    },
    {
      "path": "examples/button.tsx",
      "content": "export const Button...",
      "is_markdown": false
    }
  ],
  "metadata": {
    "created_at": "2026-03-06T12:00:00Z",
    "author": "skillmeat"
  }
}
```

### Decision 5: Migration Strategy (Local to Cloud)

**Choice:** Read-while-running migration with checksum validation + rollback

**Rationale:**
- Zero downtime for local development
- Atomic transaction per artifact prevents partial migrations
- Checksum validation prevents data corruption
- Rollback capability (create backup manifest) provides safety
- Preserves local vault for recovery

---

## Next Steps After Approval

1. **Week 1:** Confirm PRD 1 completion, finalize PostgreSQL infrastructure, schedule kickoff
2. **Week 2:** Phase 1 kickoff with data-layer-expert and backend-architect
3. **Week 3-4:** Phase 1 delivery, Phase 2 planning with python-backend-engineer
4. **Week 5-6:** Phase 2 delivery, Phase 3/4/5 teams begin parallel work
5. **Week 7-8:** Phase 3/4/5 delivery, Phase 6 (testing) escalation
6. **Week 9-10:** Phase 6 delivery with quality gates
7. **Week 11:** Phase 7 documentation and final validation
8. **Week 12:** Deployment readiness review and SaaS platform integration
