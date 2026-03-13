---
schema_version: 2
doc_type: phase_plan
title: 'SkillBOM & Attestation - Phases 7-8: API & CLI'
description: 'REST API layer (Phase 7) + CLI commands (Phase 8). Exposes activity
  history, BOM, and attestation data via HTTP and command-line interfaces.

  '
audience:
- ai-agents
- developers
- backend-engineers
- api-engineers
tags:
- implementation-plan
- phases
- skillbom
- api
- cli
created: 2026-03-10
updated: 2026-03-11
phase: 7-8
phase_title: 'API & CLI: HTTP & Command-Line Surfaces'
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
- Phase 1-6 complete with models, generators, activity history, RBAC, git, and crypto
- Repositories and services stable and tested
- Authentication/authorization middleware available
exit_criteria:
- All planned API endpoints implemented with proper auth
- OpenAPI spec updated and documentation correct
- All CLI commands (`bom`, `history`, `attest`) functional
- Response pagination implemented where required
- Integration tests pass for all endpoints
feature_slug: skillbom-attestation
effort_estimate: 28-32 story points
timeline: 3 weeks
critical_path: Phase 7 gates Phase 9-10 (web/backstage)
status: inferred_complete
---
# SkillBOM & Attestation System - Phases 7-8: API & CLI

## Overview

Phase 7 exposes artifact activity history, BOM, and attestation data via REST APIs. Phase 8 implements CLI command groups for BOM management, history viewing, and attestation creation.

Important API boundary:

- Existing `/api/v1/artifacts/{id}/history` remains the version-lineage / rollback timeline.
- New activity-history APIs expose the audit/provenance stream added in Phase 3.
- BOM APIs package and render provenance-relevant subsets rather than owning the primary event stream.

---

## Phase 7: API Layer

**Duration**: 2 weeks | **Effort**: 16-18 story points | **Assigned**: python-backend-engineer

### Overview

Implement the new HTTP surface in `skillmeat/api/routers/bom.py` plus a dedicated activity-history router. These endpoints become the source of truth for CLI, web provenance UI, and Backstage backend integration.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 7.1 | `GET /api/v1/bom/snapshot` — Current BOM snapshot | Returns the current point-in-time BOM snapshot for the authenticated caller's context. Query params: `project_id`, `include_memory_items`, `include_signatures`. | Endpoint returns 200 with valid BOM schema; auth required; response includes timestamp and hash | 2 | Pending |
| 7.2 | `POST /api/v1/bom/generate` — Trigger BOM generation | Trigger on-demand BOM generation. Response: `BomSnapshot` with generated snapshot + signature (if auto-sign enabled). | Endpoint accepts POST; calls `BomGenerator`; stores snapshot; returns 201 with snapshot ID | 2 | Pending |
| 7.3 | `GET /api/v1/artifacts/activity` — Artifact activity log | List artifact activity events. Query params: `artifact_id` (optional), `project_id` (optional), `event_type`, `time_range`, `actor_id`, `owner_scope`, `limit`, `cursor`. | Endpoint returns 200 with paginated activity events; owner filtering works; events ordered by timestamp DESC | 3 | Pending |
| 7.4 | `GET /api/v1/attestations` — List attestations | List attestation records. Query params: `owner_scope=user|team|enterprise`, `artifact_id`, `date_range`, `limit`, `cursor`. | Endpoint returns 200 with attestations filtered by caller's auth scope; pagination works; no cross-owner leakage | 2 | Pending |
| 7.5 | `POST /api/v1/attestations` — Create attestation | Create manual attestation record for offline workflows. | Endpoint accepts POST; validates artifact IDs; creates `AttestationRecord`; returns 201 with ID | 2 | Pending |
| 7.6 | `GET /api/v1/attestations/{id}` — Get attestation detail | Get single attestation record with full metadata. | Endpoint returns 200 with attestation detail; auth verifies caller can view the record; 404 if not found or unauthorized | 2 | Pending |
| 7.7 | `POST /api/v1/bom/verify` — Verify BOM signature | Verify signature on a BOM snapshot. Optional multipart signature upload supported. | Endpoint accepts POST; verifies signature; returns 200 with verification status; 422 if signature invalid | 2 | Pending |
| 7.8 | `GET /integrations/idp/bom-card/{project_id}` — Backstage backend payload | Returns Backstage-renderable BOM payload for IDP catalog/backend consumers. Extends existing `idp_integration` router. | Endpoint returns 200 with payload contract suitable for backend/scaffolder consumers; load time < 500ms | 2 | Pending |
| 7.9 | Auth middleware for BOM/activity endpoints | Implement auth for all new endpoints. Read endpoints require `artifact:read`; write endpoints require `artifact:write`; ownership checks happen in services. | All endpoints authenticated; correct scope required; owner filtering enforced; 401/403 errors on auth failure | 2 | Pending |
| 7.10 | Cursor-based pagination for list endpoints | Implement cursor-based pagination for activity and attestation lists. | Pagination works; cursors correctly encode position; no duplicate items across pages | 2 | Pending |
| 7.11 | OpenAPI spec and documentation | Update OpenAPI spec and examples for all new endpoints. | OpenAPI spec generated correctly; `/docs` shows all endpoints; schemas match actual responses | 2 | Pending |
| 7.12 | Regenerate web SDK / typed client artifacts | Regenerate or update the web SDK/client artifacts after OpenAPI changes so frontend work uses current contracts. | SDK/client artifacts updated and committed; no manual drift between API spec and frontend client | 1 | Pending |
| 7.13 | Integration tests for all API endpoints | Test each endpoint with various auth contexts (user, team, enterprise), verify filtering and permissions, and cover 404/401/403/422 cases. | All endpoints tested; auth filtering verified; error responses correct; no data leakage across tenants/owners | 3 | Pending |

### Key Design Notes

- **Activity vs History Naming**: Keep the new audit stream separate from the existing artifact version-history route.
- **Auth Enforcement**: All endpoints require auth (except health/docs). Use the project-standard auth dependencies.
- **Owner-Scoped Filtering**: Service layer filters results by resolved `user|team|enterprise` ownership.
- **Pagination**: Cursor-based for list endpoints only.
- **Response Format**: Follow the existing project response schema (`items` + `pageInfo`).
- **Backstage Auth**: Keep the new IDP payload endpoint aligned with existing IDP auth patterns; exact middleware choice should match the router it extends.

### Deliverables

1. **Code**:
   - `skillmeat/api/routers/bom.py` — BOM and attestation endpoints
   - `skillmeat/api/routers/artifact_activity.py` — Activity-history endpoints
   - Extended `skillmeat/api/routers/idp_integration.py` — Backstage backend payload endpoint
   - `skillmeat/api/schemas/bom.py` — Updated Pydantic schemas for responses

2. **Tests**:
   - `skillmeat/api/tests/test_bom_endpoints.py` — BOM and attestation endpoint tests
   - `skillmeat/api/tests/test_artifact_activity_endpoints.py` — Activity-history endpoint tests
   - `skillmeat/api/tests/test_bom_auth.py` — Auth and permission tests

### Exit Criteria

- [ ] Planned endpoints implemented with correct HTTP methods and status codes
- [ ] Auth middleware enforces scope-based access
- [ ] Owner-scope filtering prevents cross-owner/cross-tenant leakage
- [ ] Cursor-based pagination works for activity and attestation lists
- [ ] OpenAPI spec generated and `/docs` shows correct schemas
- [ ] Web SDK/client artifacts regenerated or updated
- [ ] Integration tests pass (auth, filtering, pagination, error cases)
- [ ] Backstage backend endpoint returns the agreed payload contract
- [ ] Response times meet performance targets (< 200ms p95 for typical activity queries)

---

## Phase 8: CLI Commands

**Duration**: 2 weeks | **Effort**: 12-14 story points | **Assigned**: python-backend-engineer

### Overview

Implement CLI command groups: `bom`, `history`, `attest`. Commands interact with Phase 7 APIs in enterprise/remote mode or directly with repositories/services in local mode.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 8.1 | `skillmeat bom generate` CLI command | Generate BOM and write to `.skillmeat/context.lock`. | Command executes and produces `context.lock`; output path respected; specified artifact types included | 2 | Pending |
| 8.2 | `skillmeat bom verify` CLI command | Verify BOM signature. | Command verifies signature and returns correct status; displays key metadata; handles missing signature gracefully | 2 | Pending |
| 8.3 | `skillmeat bom restore` CLI command | Restore artifact state from commit. Params include `--commit`, `--dry-run`, and `--force`. | Command retrieves BOM from commit; optionally prompts for upstream fetch; rehydrates `.claude/`; dry-run shows changes | 2 | Pending |
| 8.4 | `skillmeat bom install-hook` CLI command | Install the Git hook set. | Command installs hooks with executable permissions; hooks run on next commit; works on supported platforms | 1 | Pending |
| 8.5 | `skillmeat bom` command group and help | Group BOM subcommands and help text. | `skillmeat bom --help` shows subcommands with actionable descriptions | 1 | Pending |
| 8.6 | `skillmeat history <artifact-name>` CLI command | Show artifact activity history. Supports filters such as `--limit`, `--event-type`, `--format`. | Command resolves artifact and shows activity timeline; formatted output works in table or JSON | 2 | Pending |
| 8.7 | `skillmeat history --all` option | Show activity history for all artifacts in project. | Command aggregates activity histories; output includes artifact names and sortable timestamps | 1 | Pending |
| 8.8 | `skillmeat attest create` CLI command | Create manual attestation. Supports `--artifact-ids`, `--owner-scope`, `--notes`, and optional signing. | Command creates `AttestationRecord` via API/service; optional signing works; returns attestation ID | 2 | Pending |
| 8.9 | `skillmeat attest list` CLI command | List attestations with filters and formatting options. | Command returns paginated attestations; filtering by scope/artifact works | 2 | Pending |
| 8.10 | `skillmeat attest show` CLI command | Show single attestation detail. | Command fetches attestation and displays detail, including signature verification status where relevant | 1 | Pending |
| 8.11 | `skillmeat attest` command group and help | Group attestation subcommands and help text. | `skillmeat attest --help` shows subcommands with clear help | 1 | Pending |
| 8.12 | Output formatting (table, JSON, human-readable) | Consistent output formatting across all commands. | All commands support `--format` where appropriate; timestamps ISO 8601; JSON output parseable | 2 | Pending |
| 8.13 | Error handling and messaging | Clear error messages for missing files, auth errors, network errors, and 404s. | Error messages actionable; remediation hints included; no raw stack traces exposed by default | 1 | Pending |
| 8.14 | Integration with local and enterprise editions | Commands work in both local and enterprise modes. | Commands auto-detect edition or use config; connect to correct store/API; enterprise auth works | 2 | Pending |
| 8.15 | Integration tests for all CLI commands | Test each command end-to-end with mock artifacts, DB, and API where needed. | All commands tested; output correct and well-formatted; error cases handled gracefully | 2 | Pending |

### Key Design Notes

- **CLI Pattern**: Use the existing Click-based CLI entrypoint and command package structure already in the repo.
- **Local vs Enterprise**: Use repository/service selection in local mode and API clients in enterprise/remote mode.
- **History Command Semantics**: `skillmeat history` should query the new activity-history surface, not the existing version-lineage timeline unless an explicit mode is added later.
- **Output Formatting**: Table format uses Rich; JSON is standard machine-readable output.
- **Pagination in CLI**: Cursor-based under the hood, but presented simply to users.

### Deliverables

1. **Code**:
   - `skillmeat/cli/__init__.py` — Register new command groups
   - `skillmeat/cli/commands/bom.py` — BOM command group
   - `skillmeat/cli/commands/history.py` — Activity-history command group
   - `skillmeat/cli/commands/attest.py` — Attestation command group

2. **Tests**:
   - `skillmeat/cli/tests/test_bom_commands.py` — CLI command tests
   - `skillmeat/cli/tests/test_history_commands.py` — Activity-history command tests
   - `skillmeat/cli/tests/test_attest_commands.py` — Attestation command tests

### Exit Criteria

- [ ] All planned CLI commands functional
- [ ] Commands work in both local and enterprise editions
- [ ] Output formatted correctly (table/JSON)
- [ ] Error messages clear and actionable
- [ ] Help text complete with examples
- [ ] Integration tests pass
- [ ] CLI tests achieve >= 80% code coverage
- [ ] Commands follow project naming conventions and current CLI structure

---

## Integration Points

### Within Phase 7-8
- Phase 7 API endpoints are the data source for Phase 8 CLI in enterprise/remote mode
- Phase 8 CLI uses local repositories/services in local mode

### To Phase 9 (Web)
- Activity-history, BOM snapshot, and attestation endpoints are consumed by React hooks in the web app

### To Phase 10 (Backstage Backend)
- The IDP payload endpoint is consumed by Backstage backend/scaffolder integration

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Activity-history API confused with existing version-history API | Keep route naming and docs explicit; preserve existing artifact-history route unchanged |
| Auth bypass via API | Comprehensive auth tests; code review by security expert |
| CLI breaks existing workflows | Keep behavior behind feature flag during rollout; anchor changes in current CLI structure |
| API/frontend contract drift | Regenerate SDK/client artifacts as part of this phase |

---

## Success Metrics

- **API Performance**: Typical activity query (100 events) < 200ms p95; attestation list < 100ms p95
- **API Test Coverage**: >= 80% endpoint coverage; all auth scenarios tested
- **CLI Usability**: Commands succeed on first try with clear errors
- **CLI Test Coverage**: >= 80% command coverage
- **OpenAPI Spec**: Auto-generated without manual drift

---

## Next Steps (Gate to Phase 9-10)

1. ✅ Phase 7-8 exit criteria verified
2. ✅ API endpoints tested with integration tests
3. ✅ CLI commands tested and documented
4. ✅ OpenAPI spec and typed client artifacts updated
5. ✅ Phase 9 (Web) can begin with stable API contracts

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-04, FR-06, FR-12, FR-15, FR-16, FR-18, FR-20
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **API CLAUDE.md**: `skillmeat/api/CLAUDE.md`
- **Router Patterns**: `.claude/context/key-context/router-patterns.md`
- **Auth Architecture**: `.claude/context/key-context/auth-architecture.md`
