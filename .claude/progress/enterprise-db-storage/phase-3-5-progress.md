---
type: progress
schema_version: 2
doc_type: progress
prd: "enterprise-db-storage"
feature_slug: "enterprise-db-storage"
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
phase: 3
title: "API Content Delivery, CLI Enterprise Mode & Migration Tooling"
status: "planning"
started: "2026-03-06"
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 17
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: ["backend-architect"]

tasks:
  # === Phase 3: API Content Delivery Endpoints ===
  - id: "ENT-3.1"
    description: "Create enterprise_content.py service for streaming artifact payloads (file tree + contents JSON, versioning, gzip compression)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "3sp"
    priority: "critical"

  - id: "ENT-3.2"
    description: "Implement GET /api/v1/artifacts/{id}/download router returning JSON: {artifact_id, files[], metadata}"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.1"]
    estimated_effort: "3sp"
    priority: "critical"

  - id: "ENT-3.3"
    description: "Support version-aware download via ?version query param (content_hash or version_label)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.2"]
    estimated_effort: "2sp"
    priority: "high"

  - id: "ENT-3.4"
    description: "Implement enterprise authentication middleware validating PAT or Clerk JWT before artifact access (401/403 responses)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.2"]
    estimated_effort: "2sp"
    priority: "high"

  - id: "ENT-3.5"
    description: "Unit + integration tests for download endpoint (file tree structure, versioning, tenant isolation)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.1", "ENT-3.2", "ENT-3.3", "ENT-3.4"]
    estimated_effort: "2sp"
    priority: "high"

  # === Phase 4: CLI Enterprise Mode ===
  - id: "ENT-4.1"
    description: "Add SKILLMEAT_EDITION, SKILLMEAT_API_URL, SKILLMEAT_PAT env vars with config loading and edition logging at startup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2sp"
    priority: "critical"

  - id: "ENT-4.2"
    description: "Update CLI to detect enterprise mode and route deploy/sync commands to local filesystem or API accordingly"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-4.1"]
    estimated_effort: "2sp"
    priority: "high"

  - id: "ENT-4.3"
    description: "Implement API-based deployment: call GET /api/v1/artifacts/{id}/download, materialize to ./.claude/, update deployed.toml"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.2", "ENT-4.1"]
    estimated_effort: "3sp"
    priority: "high"

  - id: "ENT-4.4"
    description: "Implement API-based sync: poll API for latest content, compare content_hash, update if changed"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.2", "ENT-4.1"]
    estimated_effort: "2sp"
    priority: "high"

  - id: "ENT-4.5"
    description: "Implement --token flag and env var for PAT-based headless auth; store PAT in secure config and send in Authorization header"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-4.1"]
    estimated_effort: "1sp"
    priority: "medium"

  - id: "ENT-4.6"
    description: "Unit + E2E tests for enterprise deploy/sync (API calls made, files materialized, deployed.toml updated)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-4.3", "ENT-4.4"]
    estimated_effort: "2sp"
    priority: "high"

  # === Phase 5: Cloud Migration Tooling ===
  - id: "ENT-5.1"
    description: "Create migration service to read from LocalFileSystemRepository and POST to API (iterates local artifacts, computes checksums)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-3.2"]
    estimated_effort: "3sp"
    priority: "critical"

  - id: "ENT-5.2"
    description: "Implement skillmeat enterprise migrate CLI command with --dry-run and --force flags"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-5.1"]
    estimated_effort: "3sp"
    priority: "high"

  - id: "ENT-5.3"
    description: "Migration checksum validation: SHA256 comparison, abort on mismatch with detailed error reporting"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-5.1"]
    estimated_effort: "2sp"
    priority: "high"

  - id: "ENT-5.4"
    description: "Migration rollback: create .skillmeat-migration-backup.toml during migration, implement rollback command to restore it"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-5.2"]
    estimated_effort: "3sp"
    priority: "high"

  - id: "ENT-5.5"
    description: "Migration progress reporting: console progress bar with count and percentage during long migrations"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-5.2"]
    estimated_effort: "2sp"
    priority: "medium"

  - id: "ENT-5.6"
    description: "Migration error handling: retry logic for transient failures, detailed error logs, graceful partial migration recovery"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT-5.1"]
    estimated_effort: "2sp"
    priority: "high"

parallelization:
  # Phase 3 must lead — its download endpoint gates Phase 4 and 5
  batch_1:
    - "ENT-3.1"  # Phase 3 foundation (no deps)
    - "ENT-4.1"  # Phase 4 config/env detection (no deps, independent of Phase 3)
  batch_2:
    - "ENT-3.2"  # Needs ENT-3.1
    - "ENT-4.2"  # Needs ENT-4.1
    - "ENT-4.5"  # Needs ENT-4.1
  batch_3:
    - "ENT-3.3"  # Needs ENT-3.2
    - "ENT-3.4"  # Needs ENT-3.2
    - "ENT-4.3"  # Needs ENT-3.2 + ENT-4.1
    - "ENT-4.4"  # Needs ENT-3.2 + ENT-4.1
    - "ENT-5.1"  # Needs ENT-3.2 (upload endpoint implied by Phase 3)
  batch_4:
    - "ENT-3.5"  # Needs ENT-3.1 through ENT-3.4
    - "ENT-4.6"  # Needs ENT-4.3 + ENT-4.4
    - "ENT-5.2"  # Needs ENT-5.1
    - "ENT-5.3"  # Needs ENT-5.1
    - "ENT-5.6"  # Needs ENT-5.1
  batch_5:
    - "ENT-5.4"  # Needs ENT-5.2
    - "ENT-5.5"  # Needs ENT-5.2
  critical_path:
    - "ENT-3.1"
    - "ENT-3.2"
    - "ENT-5.1"
    - "ENT-5.2"
    - "ENT-5.4"
  estimated_total_time: "~4-5 weeks (parallel), ~7-8 weeks (sequential)"

blockers: []

success_criteria:
  - id: "SC-3.1"
    description: "GET /api/v1/artifacts/{id}/download returns valid JSON matching content delivery schema"
    status: "pending"
  - id: "SC-3.2"
    description: "Version-aware downloads return correct content for hash and label specifiers"
    status: "pending"
  - id: "SC-3.3"
    description: "Tenant isolation enforced: 403 returned for wrong-tenant access"
    status: "pending"
  - id: "SC-3.4"
    description: "Content delivery performance: <200ms response time for typical artifacts against docker-compose PostgreSQL"
    status: "pending"
  - id: "SC-4.1"
    description: "skillmeat deploy --enterprise pulls from API and materializes files to ./.claude/"
    status: "pending"
  - id: "SC-4.2"
    description: "skillmeat sync --enterprise checks API for updates and applies changes"
    status: "pending"
  - id: "SC-4.3"
    description: "PAT authentication works for all API calls; fallback to local mode when env vars absent"
    status: "pending"
  - id: "SC-4.4"
    description: "E2E CLI tests pass against mock API server"
    status: "pending"
  - id: "SC-5.1"
    description: "skillmeat enterprise migrate --dry-run shows accurate preview of what would migrate"
    status: "pending"
  - id: "SC-5.2"
    description: "Migration with checksum validation succeeds; aborts on mismatch with detailed error"
    status: "pending"
  - id: "SC-5.3"
    description: "Rollback command restores backup manifest from .skillmeat-migration-backup.toml"
    status: "pending"
  - id: "SC-5.4"
    description: "Progress reporting works correctly for large collections"
    status: "pending"
  - id: "SC-5.5"
    description: "Partial migration failures handled gracefully with retry logic for transient errors"
    status: "pending"
  - id: "SC-INT.1"
    description: "End-to-end integration test passes: local migrate -> cloud deploy cycle"
    status: "pending"

files_modified: []
---

# enterprise-db-storage - Phase 3-5: API Content Delivery, CLI Enterprise Mode & Migration Tooling

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-db-storage/phase-3-5-progress.md \
  -t ENT-3.1 -s completed

python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/enterprise-db-storage/phase-3-5-progress.md \
  --updates "ENT-3.1:completed,ENT-4.1:completed"
```

---

## Objective

Phases 3-5 complete the backend surface of the Enterprise DB Storage feature. Phase 3 implements the API content delivery endpoints (`GET /download`, `POST /upload`) that form the hub for all enterprise operations. Phase 4 updates the CLI to detect and operate in enterprise mode using those API endpoints for deploy and sync. Phase 5 delivers the `skillmeat enterprise migrate` command with dry-run, checksum validation, rollback, and progress reporting so existing local-vault users can move their artifacts to the cloud.

Phases 4 and 5 share a hard dependency on Phase 3's download endpoint (ENT-3.2); env-detection work in Phase 4 (ENT-4.1) and upload-service work in Phase 5 can begin independently of Phase 3, enabling early parallelism.

**Entry criteria**: Phase 2 (Repositories) 100% complete; all repository implementations tested and reviewed.

---

## Orchestration Quick Reference

Delegate each batch as a single parallel `Task()` call. Wait for a batch to complete before launching the next.

### Batch 1 — Foundation (parallel, no dependencies)

```text
Task("python-backend-engineer",
  "Implement ENT-3.1: Create skillmeat/api/services/enterprise_content.py.
   Service must build file-tree + contents JSON payload, handle versioning,
   and support gzip compression. See phase plan:
   docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md
   Follow router patterns in .claude/context/key-context/router-patterns.md")

Task("python-backend-engineer",
  "Implement ENT-4.1: Add SKILLMEAT_EDITION, SKILLMEAT_API_URL, SKILLMEAT_PAT
   env var support to ConfigManager. Log detected edition at startup (local/enterprise).
   See phase plan:
   docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")
```

### Batch 2 — Core routing (parallel, after Batch 1)

```text
Task("python-backend-engineer",
  "Implement ENT-3.2: Add GET /api/v1/artifacts/{id}/download router.
   Depends on ENT-3.1 (enterprise_content.py). Returns JSON matching content
   delivery schema in phase plan section 'Content Delivery Format'.
   File: skillmeat/api/routers/artifacts.py or new enterprise router.
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")

Task("python-backend-engineer",
  "Implement ENT-4.2 + ENT-4.5: Update CLI to detect enterprise mode from
   ENT-4.1 env vars and route deploy/sync commands accordingly. Also implement
   --token flag and SKILLMEAT_PAT env var for PAT-based headless auth.
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md
   Existing CLI: skillmeat/cli/__init__.py")
```

### Batch 3 — Feature completions (parallel, after Batch 2)

```text
Task("python-backend-engineer",
  "Implement ENT-3.3 + ENT-3.4: (1) Version-aware ?version query param support
   on download endpoint. (2) Enterprise auth middleware validating PAT or Clerk JWT
   with 401/403 responses. Depends on ENT-3.2.
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")

Task("python-backend-engineer",
  "Implement ENT-4.3 + ENT-4.4: API-based deploy (calls download endpoint,
   materializes to ./.claude/, updates deployed.toml) and API-based sync
   (polls for latest, compares content_hash, updates). Depends on ENT-3.2 + ENT-4.1.
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")

Task("python-backend-engineer",
  "Implement ENT-5.1: Migration service reading from LocalFileSystemRepository
   and POSTing to POST /api/v1/artifacts/{id}/upload. Include checksum computation.
   Depends on ENT-3.2 (upload endpoint). Also implement the upload endpoint if not
   yet present (see 'Migration API Endpoint' section in phase plan).
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")
```

### Batch 4 — Tests and migration CLI (parallel, after Batch 3)

```text
Task("python-backend-engineer",
  "Implement ENT-3.5: Unit + integration tests for download endpoint.
   Cover: file tree structure, versioning, tenant isolation (403), <200ms perf.
   Use docker-compose PostgreSQL per phase plan quality gates.
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")

Task("python-backend-engineer",
  "Implement ENT-4.6: Unit + E2E tests for enterprise deploy/sync CLI.
   Verify API calls, file materialization to ./.claude/, deployed.toml updates.
   Use mock API server. Depends on ENT-4.3 + ENT-4.4.
   Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")

Task("python-backend-engineer",
  "Implement ENT-5.2 + ENT-5.3 + ENT-5.6: (1) skillmeat enterprise migrate CLI
   with --dry-run and --force. (2) SHA256 checksum validation with abort-on-mismatch.
   (3) Retry logic and graceful partial-migration error handling.
   Depends on ENT-5.1. Phase plan:
   docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")
```

### Batch 5 — Migration UX (parallel, after Batch 4)

```text
Task("python-backend-engineer",
  "Implement ENT-5.4 + ENT-5.5: (1) Migration rollback: write
   .skillmeat-migration-backup.toml during migration, implement rollback command.
   (2) Progress bar reporting with count and percentage for large collections.
   Depends on ENT-5.2. Phase plan:
   docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-3-5-backend.md")
```

---

## Implementation Notes

### Phase Dependency Graph

Phase 3 (API) is the critical dependency hub. Phase 4 env-config (ENT-4.1/4.2/4.5) and Phase 5's upload service (ENT-5.1) can begin concurrently with Phase 3 API work once ENT-3.2 (download endpoint) is available.

```
Phase 2 (Repositories) ──► ENT-3.1 ──► ENT-3.2 ──┬──► ENT-3.3
                        │                           ├──► ENT-3.4 ──► ENT-3.5
                        │                           ├──► ENT-4.3 ──► ENT-4.6
                        │                           ├──► ENT-4.4 ──► ENT-4.6
                        │                           └──► ENT-5.1 ──► ENT-5.2 ──► ENT-5.4
                        │                                           ├──► ENT-5.3    └──► ENT-5.5
                        │                                           └──► ENT-5.6
                        └──► ENT-4.1 ──► ENT-4.2
                                     ├──► ENT-4.5
                                     ├──► ENT-4.3 (also needs ENT-3.2)
                                     └──► ENT-4.4 (also needs ENT-3.2)
```

### Patterns and Best Practices

- Router patterns: `.claude/context/key-context/router-patterns.md`
- Existing CLI entry: `skillmeat/cli/__init__.py`
- Repository pattern for storage access: `.claude/context/key-context/repository-architecture.md`
- Auth middleware should follow patterns in `skillmeat/api/` — check for existing middleware before creating new

### Known Gotchas

- The upload endpoint (`POST /api/v1/artifacts/{id}/upload`) is specified in Phase 5 but required by ENT-5.1; confirm it is implemented as part of Phase 3 or early Phase 5 before ENT-5.1 starts.
- `SKILLMEAT_EDITION` env var detection must not break existing local-mode flows; always fall back gracefully.
- PAT storage must be secure (not plaintext in config files readable by other users).
- Tenant isolation in the auth middleware is critical: wrong-tenant access must return 403, not 404 (avoid leaking artifact existence).
- Migration checksum must be computed client-side before upload and re-verified server-side after write — two separate checks.

---

## Completion Notes

*(Fill in when phases complete)*

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for Phase 6 (frontend integration)
