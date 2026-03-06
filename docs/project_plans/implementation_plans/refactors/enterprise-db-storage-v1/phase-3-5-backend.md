---
title: "Phases 3-5: Backend Completion (API, CLI, Migration)"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-06
updated: 2026-03-06
feature_slug: "enterprise-db-storage"
phase: "3-5"
phase_title: "Backend Completion: API, CLI, and Migration Tooling"
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
entry_criteria:
  - "Phase 2 (Repositories) 100% complete"
  - "All repository implementations tested and reviewed"
  - "Python-backend-engineer available for all three phases"
  - "**Phase 4 and 5 additionally require PRD 2 (AuthContext/RBAC) to be approved and in-progress**"
exit_criteria:
  - "API content delivery endpoint complete and tested"
  - "CLI enterprise mode fully functional"
  - "Migration tooling working with dry-run and rollback support"
  - "End-to-end integration tests passing"
---

# Phases 3-5: Backend Completion

This consolidated phase document covers the three parallel backend implementation phases: API Content Delivery (Phase 3), CLI Enterprise Mode (Phase 4), and Cloud Migration Tooling (Phase 5).

**Duration:** 1.5-2 weeks per phase (can run in parallel) | **Total Effort:** 30-36 story points | **Subagent:** python-backend-engineer

---

## Phase 3: API Content Delivery Endpoints

### Overview

Phase 3 implements the API endpoints that serve artifact content to CLI users in enterprise mode. The core endpoint `GET /api/v1/artifacts/{id}/download` returns a JSON payload with file tree and content.

> **Single-Tenant Bootstrap Mode**: Phase 3 does NOT require PRD 2 (AuthContext/RBAC). All API endpoints operate using `DEFAULT_TENANT_ID` in bootstrap mode — no authentication middleware is required because single-tenant deployments are trusted-network deployments. After Phase 3 completes, the web app is fully functional with the enterprise DB backend. Authentication middleware (ENT-3.4) is scaffolded in Phase 3 but only enforced once PRD 2 provides the auth infrastructure.

**Duration:** 1.5 weeks | **Effort:** 10-12 story points

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|---|
| ENT-3.1 | Content delivery service | Create enterprise_content.py service for streaming artifact payloads | Service builds file tree + contents JSON, handles versioning, gzip compression | 3 | Phase 2 |
| ENT-3.2 | GET /api/v1/artifacts/{id}/download endpoint | Implement content download router | Returns JSON: {artifact_id, files[], metadata} | 3 | ENT-3.1 |
| ENT-3.3 | Version-aware download (?version query param) | Support pinning to specific content_hash or version_label | ?version=sha256:abc or ?version=v1.0 | 2 | ENT-3.2 |
| ENT-3.4 | Enterprise authentication middleware (scaffold) | Scaffold auth middleware stub; uses DEFAULT_TENANT_ID in bootstrap mode | Stub passes all requests in single-tenant mode; enforces PAT/Clerk JWT when PRD 2 AuthContext is available | 2 | Phase 2 |
| ENT-3.5 | Content delivery tests | Unit + integration tests for download endpoint | Tests verify: file tree structure, versioning, tenant isolation | 2 | ENT-3.1 through ENT-3.4 |

**Total: 10-12 story points**

### Content Delivery Format

```json
{
  "artifact": {
    "id": "skill:frontend-design",
    "name": "frontend-design",
    "type": "skill",
    "version": "v1.2.0",
    "content_hash": "sha256:abc123...",
    "metadata": {
      "created_at": "2026-03-06T12:00:00Z",
      "updated_at": "2026-03-06T13:00:00Z",
      "tags": ["design", "ui"]
    }
  },
  "files": [
    {
      "path": "frontend-design.md",
      "content": "# Frontend Design Skill\n...",
      "is_markdown": true,
      "size_bytes": 5240
    },
    {
      "path": "examples/button.tsx",
      "content": "export const Button = () => { ... }",
      "is_markdown": false,
      "size_bytes": 1024
    }
  ]
}
```

### API Specification

**Endpoint:** `GET /api/v1/artifacts/{id}/download`

**Parameters:**
- `id` (path): Artifact ID (UUID or "type:name")
- `version` (query, optional): Specific version (hash or label)
- `format` (query, optional): "json" (default) or "tar.gz" (future)

**Response:** 200 OK with JSON payload (as shown above)

**Error Responses:**
- 400 Bad Request: Invalid artifact ID
- 401 Unauthorized: Missing/invalid auth token
- 403 Forbidden: Wrong tenant or no access
- 404 Not Found: Artifact not found

**Quality Gates:**
- [ ] Endpoint returns valid JSON matching schema
- [ ] Version-aware downloads return correct content
- [ ] Tenant isolation enforced (403 for wrong tenant)
- [ ] Performance: <200ms response time for typical artifacts
- [ ] Tests pass with docker-compose PostgreSQL
- [ ] **Web app fully functional in single-tenant enterprise mode after Phase 3** (no PRD 2 required)

---

## Phase 4: CLI Enterprise Mode

### Overview

Phase 4 updates the SkillMeat CLI to work in enterprise mode, using the API for deployment and sync instead of local filesystem operations.

> **Requires PRD 2 (AuthContext/RBAC)**: Phase 4 depends on PAT-based authentication infrastructure that PRD 2 provides. Tasks ENT-4.3 through ENT-4.5 (enterprise deploy, sync, and PAT auth) are blocked until PRD 2 is approved and its auth infrastructure is available. ENT-4.1 and ENT-4.2 (config/env detection) can proceed independently.

**Duration:** 1.5 weeks | **Effort:** 8-10 story points

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|---|
| ENT-4.1 | Enterprise config and env detection | Add SKILLMEAT_EDITION, SKILLMEAT_API_URL, SKILLMEAT_PAT env vars | Config loads from env, logs edition (local or enterprise) at startup | 2 | Phase 2 |
| ENT-4.2 | Enterprise mode CLI detection | Update CLI to detect enterprise mode and route commands appropriately | `skillmeat deploy` uses LocalFileSystemRepository in local mode, API in enterprise | 2 | ENT-4.1 |
| ENT-4.3 | skillmeat deploy --enterprise | Implement API-based deployment (calls GET /api/v1/artifacts/{id}/download) | Deploy pulls artifact from API, materializes to ./.claude/, updates deployed.toml | 3 | ENT-3.2, ENT-4.1, **PRD 2** |
| ENT-4.4 | skillmeat sync --enterprise | Implement API-based sync (polls API for latest content) | Sync checks for updates via API, compares content_hash, updates if changed | 2 | ENT-3.2, ENT-4.1, **PRD 2** |
| ENT-4.5 | PAT-based authentication | Implement --token flag and env var for headless auth — **Blocked until PRD 2 provides authentication infrastructure** | CLI stores PAT in secure config, sends in Authorization header | 1 | ENT-4.1, **PRD 2** |
| ENT-4.6 | Enterprise mode CLI tests | Unit + E2E tests for enterprise deploy/sync | Tests verify: API calls made, files materialized, deployed.toml updated | 2 | ENT-4.3, ENT-4.4 |

**Total: 8-10 story points**

### Implementation Details

**Enterprise Deploy Flow:**
```python
# 1. Load enterprise config
edition = config.get("SKILLMEAT_EDITION")  # "enterprise" or "local"
if edition == "enterprise":
    # 2. Call API
    response = api_client.get(f"/artifacts/{artifact_id}/download",
                              headers={"Authorization": f"Bearer {pat}"})
    files = response.json()["files"]

    # 3. Materialize to ./.claude/
    for file in files:
        path = Path(".claude") / file["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file["content"])

    # 4. Update deployed.toml
    deployment_manager.record_deployment(...)
```

**Environment Variables:**
```bash
SKILLMEAT_EDITION=enterprise          # or "local"
SKILLMEAT_API_URL=https://api.skillmeat.dev  # Enterprise API endpoint
SKILLMEAT_PAT=sk_live_xxxxx...        # Personal Access Token for auth
SKILLMEAT_GITHUB_TOKEN=ghp_xxxxx...   # Still used for GitHub API
```

**Quality Gates:**
- [ ] `skillmeat deploy --enterprise` pulls from API and materializes files
- [ ] `skillmeat sync --enterprise` checks API for updates
- [ ] PAT authentication works with API calls
- [ ] Fallback to local mode if env vars not set
- [ ] E2E tests pass with mock API server

---

## Phase 5: Cloud Migration Tooling

### Overview

Phase 5 implements the `skillmeat enterprise migrate` command for users to upload their local filesystem vault to the cloud database.

> **PRD 2 dependency**: Migration via the API (`POST /api/v1/artifacts/{id}/upload`) requires authenticated endpoints that PRD 2 provides. If PRD 2 is delayed, migration can alternatively be performed via direct DB connection (bypassing API auth entirely, writing to PostgreSQL directly through `EnterpriseDBRepository`). This direct-DB path is viable as a temporary fallback but is **not recommended for production** — it bypasses tenant validation and audit logging. The default implementation targets API-based migration assuming PRD 2 is available.

**Duration:** 1.5 weeks | **Effort:** 12-14 story points

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|---|
| ENT-5.1 | Migration service | Create service to read from LocalFileSystemRepository and write to API — requires authenticated upload endpoint (**PRD 2**); direct-DB fallback available if PRD 2 delayed (not for production) | Service iterates local artifacts, computes checksums, posts to API | 3 | Phase 2, Phase 3, **PRD 2** |
| ENT-5.2 | skillmeat enterprise migrate command | Implement CLI command with --dry-run and --force | Shows what would migrate, asks confirmation, executes migration | 3 | ENT-5.1 |
| ENT-5.3 | Migration checksum validation | Verify uploaded artifacts match local originals (SHA256 comparison) | Migration aborts if checksum mismatch, detailed error reporting | 2 | ENT-5.1 |
| ENT-5.4 | Migration rollback support | Create backup manifest and rollback command | Migration creates .skillmeat-migration-backup.toml, rollback restores it | 3 | ENT-5.2 |
| ENT-5.5 | Migration progress reporting | Show progress bar and detailed status during migration | Console output: "Migrating 42 artifacts... [====>   ] 65% (27 done, 15 remaining)" | 2 | ENT-5.2 |
| ENT-5.6 | Migration error handling | Graceful handling of partial migrations and recoverable errors | Retry logic for transient failures, detailed error logs | 2 | ENT-5.1 |

**Total: 12-14 story points**

### Migration Process

```
1. Pre-flight checks
   - Authenticate with API (verify PAT valid)
   - Check local vault for artifacts
   - Estimate migration size/time

2. Dry-run (optional)
   - Show artifacts that would migrate
   - Show which already exist in cloud
   - Estimate time

3. Confirm with user
   - "Ready to migrate 42 artifacts (~5 MB). Continue? [y/n]"

4. Execute migration
   - Read each artifact from local filesystem
   - Compute content_hash (SHA256)
   - POST to /api/v1/artifacts/{id}/upload with file contents
   - Verify checksum on cloud
   - Show progress

5. Post-migration
   - Create backup manifest at ./.skillmeat-migration-backup.toml
   - Output summary: "42 artifacts migrated successfully"
   - Show next steps: "Use SKILLMEAT_EDITION=enterprise to deploy from cloud"
```

### Migration API Endpoint (Phase 3 + 5)

**Endpoint:** `POST /api/v1/artifacts/{id}/upload`

**Request:**
```json
{
  "artifact_id": "skill:frontend-design",
  "name": "frontend-design",
  "type": "skill",
  "content_hash": "sha256:abc123...",
  "files": [
    {
      "path": "frontend-design.md",
      "content": "# Frontend Design\n...",
      "is_markdown": true
    }
  ],
  "metadata": {
    "source_url": "https://github.com/anthropics/skills/...",
    "tags": ["design", "ui"]
  }
}
```

**Response:** 201 Created with uploaded artifact

**Quality Gates:**
- [ ] `skillmeat enterprise migrate --dry-run` shows what would migrate
- [ ] Migration with checksum validation succeeds
- [ ] Rollback command restores backup manifest
- [ ] Progress reporting works for large collections
- [ ] Partial migrations handle transient failures gracefully

---

## Integration Across Phases 3-5

### Order of Implementation

Since these phases can run in parallel:

1. **Phase 3 starts first:** API endpoint needed by Phases 4 and 5
2. **Phase 4 can start:** Once Phase 3 has the basic download endpoint
3. **Phase 5 can start:** Once Phase 3 has both download and upload endpoints

### Testing Strategy

**Unit Tests:** Each phase has independent unit tests
**Integration Tests:** Combined tests verify all three working together:

```python
def test_migration_then_deploy_cycle():
    """Full cycle: migrate local → deploy from cloud."""
    # 1. Set up local artifacts
    # 2. Run skillmeat enterprise migrate --dry-run
    # 3. Verify preview output
    # 4. Run skillmeat enterprise migrate
    # 5. Set SKILLMEAT_EDITION=enterprise
    # 6. Run skillmeat deploy
    # 7. Verify files materialized from API
```

### End-to-End Flow

```
Local User
  ↓
[skillmeat enterprise migrate]
  ↓
LocalFileSystemRepository ← reads ~.skillmeat/collection/
  ↓
[POST /api/v1/artifacts/{id}/upload]
  ↓
EnterpriseDBRepository → writes to PostgreSQL
  ↓
User confirms migration complete
  ↓
Set SKILLMEAT_EDITION=enterprise
  ↓
[skillmeat deploy]
  ↓
[GET /api/v1/artifacts/{id}/download]
  ↓
Files materialized to ./.claude/
  ↓
Done: Now deploying from cloud DB
```

---

## Combined Quality Gates

**Phases 3-5 Complete When:**

- [ ] API content delivery endpoint implemented and tested
- [ ] CLI enterprise deploy/sync working against API
- [ ] Migration tooling supports dry-run, checksum validation, rollback
- [ ] End-to-end integration tests pass (migration → deploy cycle)
- [ ] PAT authentication works for all API calls
- [ ] Error handling for partial migrations and network failures
- [ ] Progress reporting during long operations
- [ ] All three phases integrated and tested together

---

## References

- Phase 2: Enterprise repositories
- PRD 3: Enterprise database storage
- API patterns: `.claude/context/key-context/router-patterns.md`
- CLI patterns: Existing `skillmeat/cli/__init__.py`
