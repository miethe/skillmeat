---
title: "Phases 6-7: Testing, Validation & Documentation"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-06
updated: 2026-03-06
feature_slug: "enterprise-db-storage"
phase: "6-7"
phase_title: "Testing, Validation & Documentation"
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
entry_criteria:
  - "Phases 1-5 (schema, repos, API, CLI, migration) 100% complete"
  - "All unit and integration tests from Phases 1-5 passing"
  - "Python-backend-engineer available for Phase 6"
  - "Documentation-writer available for Phase 7"
exit_criteria:
  - "Full test suite passing (unit, integration, E2E)"
  - "Multi-tenant isolation verified with comprehensive security tests"
  - "Performance regression tests baseline established and passing"
  - "Documentation complete: setup guide, migration guide, API docs, ADR"
  - "Production readiness checklist signed off"
---

# Phases 6-7: Testing, Validation & Documentation

This consolidated phase document covers comprehensive testing (Phase 6) and documentation/deployment readiness (Phase 7).

**Phase 6 Duration:** 2 weeks | **Effort:** 14-16 story points
**Phase 7 Duration:** 1 week | **Effort:** 8-10 story points
**Subagents:** python-backend-engineer (Phase 6), documentation-writer + api-documenter (Phase 7)

---

## Phase 6: Testing & Validation

### Overview

Phase 6 executes comprehensive testing across all components, focusing on enterprise-specific concerns: multi-tenant isolation, content delivery, migration data integrity, and performance under load.

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|---|
| ENT-6.1 | End-to-end test: full migrate→deploy→sync cycle | Write E2E test covering entire user journey: local vault → migrate → cloud deploy → sync | Test passes with real PostgreSQL, verifies file integrity throughout | 3 | Phases 1-5 |
| ENT-6.2 | Security test: multi-tenant data isolation | Write security tests for cross-tenant access (negative tests) | Tests verify: tenant A cannot read/write/delete tenant B's artifacts, tenant isolation via API | 3 | Phases 1-5 |
| ENT-6.3 | Migration data integrity tests | Verify migrated artifacts have correct checksums and content | Tests check: every migrated file matches original, no data loss, metadata preserved | 2 | Phase 5 |
| ENT-6.4 | Load test: concurrent deployments and syncs | Simulate 10+ concurrent deploy/sync operations, verify no race conditions | Load test passes, no deadlocks, all operations succeed | 2 | Phases 3-4 |
| ENT-6.5 | Performance regression tests | Establish baseline metrics from Phase 2, verify no regression >10% | Benchmarks: get() <1ms, list(1000) <10ms, search() <5ms, API download <200ms | 2 | Phase 2, Phases 3-5 |
| ENT-6.6 | Backward compatibility tests | Verify local (SQLite) mode unchanged, no breaking changes for existing users | Tests run against both SQLite and PostgreSQL, SQLite behavior identical | 2 | Phases 1-5 |
| ENT-6.7 | Error handling and recovery tests | Test failure scenarios: network errors, database unavailable, partial migrations | Tests verify: graceful errors, helpful messages, ability to retry | 2 | Phases 1-5 |
| ENT-6.8 | CI/CD integration tests | Set up automated test suite in GitHub Actions with docker-compose PostgreSQL | CI runs all tests on every PR, reports coverage and performance benchmarks | 2 | Phases 1-5 |
| ENT-6.9 | Documentation for test running | Document how to run test suites locally and in CI | Runbooks for: `pnpm test`, `pytest`, docker-compose test database setup | 1 | ENT-6.1 through ENT-6.8 |

**Total: 14-16 story points**

### Detailed Testing Strategy

#### E2E Test: Migration → Deploy → Sync Cycle

```python
def test_e2e_migration_deploy_sync_cycle():
    """Full lifecycle: migrate local vault to cloud, deploy from cloud, sync."""

    # Step 1: Set up local artifacts
    collection_path = temp_dir / ".skillmeat" / "collection"
    artifact1 = collection_path / "skills" / "design.md"
    artifact1.write_text("# Design Skill v1.0")

    # Step 2: Migrate to cloud
    result = cli.run(["enterprise", "migrate", "--force"])
    assert result.exit_code == 0
    assert "42 artifacts migrated" in result.output

    # Step 3: Verify artifacts in PostgreSQL
    artifacts = api_client.list_artifacts()
    assert len(artifacts) == 42

    # Step 4: Deploy from cloud
    os.environ["SKILLMEAT_EDITION"] = "enterprise"
    result = cli.run(["deploy", "skill:design"])
    assert result.exit_code == 0
    assert (project_dir / ".claude" / "skills" / "design.md").exists()

    # Step 5: Verify deployed content matches original
    deployed = (project_dir / ".claude" / "skills" / "design.md").read_text()
    assert deployed == "# Design Skill v1.0"

    # Step 6: Sync (check for updates)
    # Update artifact in cloud
    api_client.update_artifact("skill:design", content="# Design Skill v1.1")

    # Sync should detect update
    result = cli.run(["sync"])
    assert "Updated 1 artifact" in result.output

    # Verify synced content
    synced = (project_dir / ".claude" / "skills" / "design.md").read_text()
    assert synced == "# Design Skill v1.1"
```

#### Security Test: Multi-Tenant Isolation

```python
def test_tenant_isolation_via_api():
    """Verify tenant A cannot access tenant B's artifacts via API."""

    # Setup: Create two tenants with artifacts
    tenant_a = "tenant-a-uuid"
    tenant_b = "tenant-b-uuid"

    # Tenant A creates artifact
    artifact_a = api_client.create_artifact(
        tenant_id=tenant_a,
        name="design",
        content="Secret design system A"
    )

    # Tenant B creates artifact
    artifact_b = api_client.create_artifact(
        tenant_id=tenant_b,
        name="design",
        content="Secret design system B"
    )

    # Tenant B tries to read Tenant A's artifact (should fail)
    token_b = jwt_for_tenant(tenant_b)
    response = api_client.get(
        f"/artifacts/{artifact_a.id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404  # Or 403
    assert artifact_a.id not in response.json()

    # Tenant B queries should only see own artifacts
    response = api_client.list_artifacts(headers={"Authorization": f"Bearer {token_b}"})
    artifacts = response.json()
    assert all(a["tenant_id"] == tenant_b for a in artifacts)
    assert artifact_a.id not in [a["id"] for a in artifacts]
```

#### Load Test: Concurrent Operations

```python
@pytest.mark.load
def test_concurrent_deployments():
    """Verify 10 concurrent deployments don't cause race conditions."""

    import concurrent.futures

    def deploy_one(artifact_id):
        return subprocess.run(
            ["skillmeat", "deploy", artifact_id],
            capture_output=True
        )

    artifact_ids = ["skill:design", "skill:analytics", ...] * 2  # 10 total

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(deploy_one, artifact_ids))

    # All should succeed
    assert all(r.returncode == 0 for r in results)

    # All files should exist and have correct content
    for artifact_id in set(artifact_ids):
        path = project_dir / ".claude" / artifact_id.replace(":", "/")
        assert path.exists()
        assert path.read_bytes()  # Has content
```

#### Performance Regression Test

```python
def test_performance_regression():
    """Verify performance hasn't degraded >10% from baseline."""

    import statistics

    # Baseline (from Phase 2)
    BASELINE = {
        "artifact_repo.get": 1.0,    # ms
        "artifact_repo.list": 8.0,   # ms for 1000 artifacts
        "search_by_tags": 4.0,       # ms
        "api_download": 150.0,       # ms
    }

    # Measure current performance
    measurements = {
        "artifact_repo.get": [],
        "artifact_repo.list": [],
        "search_by_tags": [],
        "api_download": [],
    }

    # Run each operation 10 times
    for _ in range(10):
        measurements["artifact_repo.get"].append(timeit_artifact_get())
        measurements["artifact_repo.list"].append(timeit_artifact_list(1000))
        measurements["search_by_tags"].append(timeit_search())
        measurements["api_download"].append(timeit_api_download())

    # Check for regression
    for operation, baseline_ms in BASELINE.items():
        median_ms = statistics.median(measurements[operation])
        regression = (median_ms - baseline_ms) / baseline_ms

        assert regression < 0.10, \
            f"{operation} regressed {regression*100:.1f}% " \
            f"(baseline: {baseline_ms}ms, current: {median_ms}ms)"
```

### Quality Gates for Phase 6

- [ ] E2E test covering full migration → deploy → sync cycle passes
- [ ] Security tests verify multi-tenant isolation (no cross-tenant access)
- [ ] Migration data integrity verified (checksums match)
- [ ] Load tests pass (10+ concurrent operations)
- [ ] Performance regression tests pass (<10% slowdown)
- [ ] Backward compatibility tests pass (SQLite mode unchanged)
- [ ] CI/CD integration complete (automated test runs on every PR)
- [ ] Test coverage >90% for enterprise code paths
- [ ] All manual test scenarios documented

---

## Phase 7: Documentation & Deployment

### Overview

Phase 7 produces all documentation needed for users and operators to understand, set up, and maintain the enterprise edition.

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|---|
| ENT-7.1 | Enterprise setup guide | Write comprehensive setup guide for PostgreSQL + enterprise SkillMeat | Guide covers: PostgreSQL setup, env var configuration, initial data seeding, troubleshooting | 2 | Phases 1-6 |
| ENT-7.2 | Migration guide | Write step-by-step migration guide (local → cloud) | Guide covers: pre-flight checks, dry-run usage, running migration, rollback if needed, post-migration verification | 2 | Phase 5 |
| ENT-7.3 | API documentation | Update/create API docs for enterprise endpoints | Docs include: endpoint specs, request/response schemas, examples, error codes | 2 | Phase 3 |
| ENT-7.4 | Architecture Decision Record (ADR) | Write ADR documenting enterprise architecture choices | ADR covers: Why PostgreSQL, why application-enforced tenancy, performance tradeoffs, future RLS migration | 2 | Phases 1-5 |
| ENT-7.5 | Deployment runbook | Create ops runbook for deploying enterprise SkillMeat in production | Runbook covers: infrastructure setup, database backups, monitoring, scaling, disaster recovery | 1 | Phases 1-6 |
| ENT-7.6 | CHANGELOG and breaking changes | Document any breaking changes (none expected) and new features | CHANGELOG lists all features, improvements, bug fixes organized by phase | 1 | Phases 1-6 |
| ENT-7.7 | Update README with enterprise section | Add enterprise section to main README | README points to setup guide, migration guide, ADR | 0.5 | ENT-7.1 through ENT-7.4 |

**Total: 8-10 story points**

### Documentation Artifacts

#### 1. Enterprise Setup Guide

**File:** `docs/guides/enterprise-setup.md` (or enterprise-db-storage-v1/SETUP.md)

**Sections:**
1. Prerequisites (PostgreSQL 15+, SkillMeat v0.3.0+)
2. PostgreSQL Setup
   - Managed service (AWS RDS, Azure Database, Heroku Postgres)
   - Self-hosted (Docker, systemd, Kubernetes)
   - Connection string format
3. Environment Configuration
   - Required env vars (DATABASE_URL, SKILLMEAT_EDITION, SKILLMEAT_API_URL, SKILLMEAT_PAT)
   - Optional env vars (connection pool settings, logging)
4. Initial Data Setup
   - Running Alembic migrations
   - Creating first tenant
5. Verification
   - Test commands to verify setup
   - Troubleshooting common issues
6. Production Hardening
   - Security best practices
   - Backups and recovery
   - Monitoring setup

#### 2. Migration Guide

**File:** `docs/guides/enterprise-migration.md` (or enterprise-db-storage-v1/MIGRATION.md)

**Sections:**
1. Pre-Migration Checklist
   - Backup local vault
   - Verify API connectivity
   - Understand PAT requirements
2. Dry-Run (Optional but Recommended)
   - Command: `skillmeat enterprise migrate --dry-run`
   - Understanding output
3. Running Migration
   - Command: `skillmeat enterprise migrate --force`
   - Monitoring progress
   - Understanding error messages
4. Post-Migration Verification
   - Querying migrated artifacts via API
   - Verifying checksums
   - Switching to enterprise mode
5. Rollback (If Needed)
   - Command: `skillmeat enterprise migrate --rollback`
   - Restoring from backup manifest
6. Common Issues & Solutions
   - "Migration timed out"
   - "Checksum mismatch"
   - "Network errors during migration"

#### 3. API Documentation

**File:** `docs/api/enterprise-endpoints.md` or OpenAPI spec update

**Content:**
- GET /api/v1/artifacts/{id}/download
  - Parameters, response schema, examples
  - Error responses
- POST /api/v1/artifacts/{id}/upload
  - Parameters, request schema, examples
  - Error responses
- Authentication methods (JWT, PAT)
- Rate limiting (if applicable)
- Tenant filtering behavior

Example:
```markdown
### GET /api/v1/artifacts/{id}/download

Retrieve artifact content for deployment.

**Parameters:**
- `id` (path, required): Artifact ID
- `version` (query, optional): Specific version hash or label

**Response:**
```json
{
  "artifact": {...},
  "files": [...]
}
```

**Errors:**
- 404: Artifact not found (or no access)
- 401: Unauthorized
- 403: Forbidden (wrong tenant)
```

#### 4. Architecture Decision Record (ADR)

**File:** `.claude/adrs/ADR-XXX-enterprise-database-storage.md`

**Sections:**
1. Decision: Adopt PostgreSQL for enterprise edition
2. Context: Local SkillMeat uses SQLite + filesystem; need cloud-scalable backend
3. Options Considered:
   - DocumentDB (MongoDB-compatible)
   - DynamoDB
   - PostgreSQL with JSONB
   - Custom blob storage (S3 + metadata DB)
4. Chosen Option: PostgreSQL with JSONB
5. Rationale:
   - Familiar technology in codebase (Alembic expertise)
   - JSONB provides document flexibility without schema changes
   - Superior transaction support for migrations
   - RLS capability for future multi-tenancy hardening
6. Consequences:
   - Must manage PostgreSQL infrastructure
   - Scaling requires connection pooling and read replicas
   - RLS migration path available for future
7. Alternatives Rejected:
   - DocumentDB: Higher operational complexity, less SQL flexibility
   - DynamoDB: Requires custom migration logic, billing model differs
   - Blob storage: Separate metadata management needed

#### 5. Deployment Runbook

**File:** `docs/ops/enterprise-deployment-runbook.md`

**Sections:**
1. Pre-Deployment
   - Capacity planning
   - Backup strategy
   - Monitoring setup
2. Deployment Steps
   - PostgreSQL provisioning
   - Schema migrations
   - SkillMeat API deployment
   - CLI configuration
3. Verification
   - Health checks
   - Smoke tests
4. Scaling Strategy
   - Connection pooling
   - Read replicas (future)
   - Load balancing
5. Disaster Recovery
   - Backup/restore procedures
   - Data corruption recovery
   - Failover processes
6. Monitoring & Alerting
   - Key metrics (query latency, connection pool usage)
   - Alert thresholds
   - Log aggregation
7. Operational Runbooks
   - Adding new tenant
   - Scaling database
   - Patching PostgreSQL
   - Migration troubleshooting

### Quality Gates for Phase 7

- [ ] Enterprise setup guide complete with examples
- [ ] Migration guide covers all scenarios (dry-run, rollback, errors)
- [ ] API documentation matches implementation
- [ ] ADR documents all major architectural decisions
- [ ] Deployment runbook covers ops concerns (backups, scaling, monitoring)
- [ ] CHANGELOG updated with all features
- [ ] README updated with enterprise section
- [ ] All docs reviewed for clarity and completeness
- [ ] Links between docs correct and navigable

---

## Combined Success Criteria

**Both Phases Complete When:**

- [ ] All test suites passing (unit, integration, E2E, load)
- [ ] Security tests verify multi-tenant isolation ✓
- [ ] Performance baselines established and no regression >10% ✓
- [ ] All documentation artifacts created and reviewed ✓
- [ ] Production deployment ready (runbook complete) ✓
- [ ] Zero breaking changes for existing users ✓
- [ ] Migration path validated end-to-end ✓

---

## Production Readiness Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Security review completed (tenant isolation audit)
- [ ] Performance load tests successful
- [ ] Monitoring/alerting configured
- [ ] Backup/recovery procedures tested
- [ ] Runbook reviewed by ops team
- [ ] Documentation review complete
- [ ] Feature flag ready (SKILLMEAT_EDITION config)
- [ ] Rollback plan documented
- [ ] Launch communications planned

---

## References

- Phase 1: Schema
- Phase 2: Repositories
- Phases 3-5: API, CLI, Migration
- Testing patterns: `.claude/context/key-context/testing-patterns.md`
- API patterns: `.claude/context/key-context/router-patterns.md`
