---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 7-8: API & CLI"
description: >
  REST API layer (Phase 7) + CLI commands (Phase 8).
  Exposes BOM, history, and attestation data via HTTP and command-line interfaces.
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
updated: 2026-03-10
phase: 7-8
phase_title: "API & CLI: HTTP & Command-Line Surfaces"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 1-6 complete with models, generators, history, RBAC, git, and crypto
  - Repositories and services stable and tested
  - Authentication/authorization middleware available
exit_criteria:
  - All 8 API endpoints implemented with proper auth
  - OpenAPI spec updated and documentation correct
  - All CLI commands (bom, history, attest) functional
  - Response pagination (cursor-based) implemented
  - Integration tests pass for all endpoints
feature_slug: skillbom-attestation
effort_estimate: "28-32 story points"
timeline: "3 weeks"
critical_path: "Phase 7 gates Phase 9-10 (web/backstage)"
---

# SkillBOM & Attestation System - Phases 7-8: API & CLI

## Overview

Phase 7 exposes BOM, history, and attestation data via 8 REST API endpoints with owner-scoped auth and cursor-based pagination. Phase 8 implements CLI commands for BOM management, history viewing, and attestation creation.

Phase 7 is the gateway for Phases 9-10 (web app and Backstage plugin) — all downstream surfaces consume these APIs.

---

## Phase 7: API Layer

**Duration**: 2 weeks | **Effort**: 16-18 story points | **Assigned**: python-backend-engineer

### Overview

Implement 8 REST API endpoints in `skillmeat/api/routers/bom.py` with auth middleware and cursor-based pagination. Endpoints are the single source of truth for all BOM data across CLI, web, and Backstage surfaces.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 7.1 | `GET /api/v1/bom/snapshot` — Current BOM snapshot | Returns the current point-in-time BOM snapshot for the authenticated caller's context. Query params: (1) project_id (optional), (2) include_memory_items (bool), (3) include_signatures (bool). Response includes BOM JSON + metadata. | Endpoint returns 200 with valid BOM schema; auth required; filters by owner scope; response includes timestamp and hash | 2 | Pending |
| 7.2 | `POST /api/v1/bom/generate` — Trigger BOM generation | Trigger on-demand BOM generation. Request: {} (empty). Response: BomSnapshot with generated snapshot + signature (if auto-sign enabled). Used by agents and CLI. | Endpoint accepts POST; calls BomGenerator; stores snapshot in DB; returns 201 with snapshot ID; idempotent | 2 | Pending |
| 7.3 | `GET /api/v1/bom/history` — Artifact history log | List artifact lifecycle events. Query params: (1) artifact_id (required), (2) event_type (optional: create/update/delete/deploy/sync), (3) time_range (optional: start_date, end_date), (4) actor_id (optional), (5) limit, (6) cursor (pagination). Response: paginated list of HistoryEventDTO. | Endpoint returns 200 with paginated events; auth filters by owner scope; cursor pagination works; events ordered by timestamp DESC | 2 | Pending |
| 7.4 | `GET /api/v1/attestations` — List attestations | List attestation records. Query params: (1) owner_scope (user|team|enterprise), (2) artifact_id (optional), (3) date_range (optional), (4) limit, (5) cursor. Response: paginated attestations. Owner-scoped by default (user sees own, team admin sees team). | Endpoint returns 200 with attestations filtered by caller's auth scope; pagination works; no cross-owner leakage | 2 | Pending |
| 7.5 | `POST /api/v1/attestations` — Create attestation | Create manual attestation record (for offline workflows). Request: { artifact_ids: [str], owner_scope: enum, compliance_notes: str }. Response: { attestation_id, created_at }. | Endpoint accepts POST; validates artifact_ids exist; creates AttestationRecord; returns 201 with ID | 2 | Pending |
| 7.6 | `GET /api/v1/attestations/{id}` — Get attestation detail | Get single attestation record with full metadata (owner_type, roles, scopes, signature, compliance_data). | Endpoint returns 200 with attestation detail; auth verifies caller can view this attestation; 404 if not found or unauthorized | 2 | Pending |
| 7.7 | `POST /api/v1/bom/verify` — Verify BOM signature | Verify signature on a BOM snapshot. Request: { snapshot_id: str, signature_file: bytes (optional, multipart) }. Response: { is_valid: bool, verification_result: str, key_id: str, signed_at: datetime }. | Endpoint accepts POST with optional file upload; verifies signature; returns 200 with verification status; 422 if signature invalid | 2 | Pending |
| 7.8 | `GET /integrations/idp/bom-card/{project_id}` — Backstage BOM card | Returns Backstage-renderable BOM card payload for IDP catalog entries. Response includes current snapshot + recent history delta (last 5 events). Extends existing `idp_integration` router. **Auth**: Enterprise PAT (`verify_enterprise_pat`). | Endpoint returns 200 with Backstage-compatible JSON; no auth required if PAT valid; includes live BOM data; load time < 500ms | 3 | Pending |
| 7.9 | Auth middleware for all BOM endpoints | Implement auth layer for all endpoints. Decorator: `@require_auth(scopes=[artifact:read])` for read endpoints, `@require_auth(scopes=[artifact:write])` for writes. Admin endpoints use `admin:*` scope. Verify owner-scoped access in service layer. | All endpoints authenticated; correct scope required; owner-scope filtering enforced; 401/403 errors on auth failure | 2 | Pending |
| 7.10 | Cursor-based pagination for all list endpoints | Implement cursor-based pagination (not offset-based). Response format: `{ items: [...], pageInfo: { nextCursor: str|null, hasPrevious: bool, total: int } }`. | Pagination works for history, attestations lists; cursors correctly encode position; no duplicate items across pages | 2 | Pending |
| 7.11 | OpenAPI spec and documentation | Update OpenAPI spec (`skillmeat/api/openapi.json`) to include all 8 endpoints. Add examples, response schemas, error codes. Generate Swagger UI documentation. | OpenAPI spec generated correctly; `/docs` Swagger UI shows all endpoints; schemas match actual responses | 2 | Pending |
| 7.12 | Integration tests for all API endpoints | Test each endpoint with various auth contexts (user, team, enterprise), verify correct filtering and permissions. Test error cases (404, 401, 403, 422). | All endpoints tested; auth filtering verified; error responses correct; no data leakage across tenants/owners | 3 | Pending |

### Key Design Notes

- **Auth Enforcement**: All endpoints require auth (except health/docs). Use `@require_auth()` decorator.
- **Owner-Scoped Filtering**: Service layer filters results by AuthContext.user_id/team_id/tenant_id before returning.
- **Pagination**: Cursor-based (not offset) for consistency with project standards. Cursor encodes last_id + sort direction.
- **Response Format**: Follow existing project response schema (items array + pageInfo).
- **Error Handling**: Use HTTPException with appropriate status codes and logged errors.
- **Enterprise PAT**: Backstage endpoint uses `verify_enterprise_pat` middleware (existing pattern).

### Deliverables

1. **Code**:
   - `skillmeat/api/routers/bom.py` — 8 BOM endpoints
   - Extended `skillmeat/api/routers/idp_integration.py` — Backstage BOM card endpoint
   - `skillmeat/api/schemas/bom.py` — Updated Pydantic schemas for responses

2. **Tests**:
   - `skillmeat/api/tests/test_bom_endpoints.py` — Comprehensive endpoint tests
   - `skillmeat/api/tests/test_bom_auth.py` — Auth and permission tests

### Exit Criteria

- [ ] All 8 endpoints implemented with correct HTTP methods and status codes
- [ ] Auth middleware enforces scope-based access (artifact:read/write, admin:*)
- [ ] Owner-scope filtering prevents cross-owner/cross-tenant data leakage
- [ ] Cursor-based pagination works for all list endpoints
- [ ] OpenAPI spec generated and Swagger UI shows correct schemas
- [ ] Integration tests pass (auth, filtering, pagination, error cases)
- [ ] Backstage endpoint returns Backstage-compatible JSON
- [ ] Response times meet performance targets (< 200ms p95 for history query)

---

## Phase 8: CLI Commands

**Duration**: 2 weeks | **Effort**: 12-14 story points | **Assigned**: python-backend-engineer

### Overview

Implement CLI command groups: `bom`, `history`, `attest`. Commands interact with the Phase 7 API endpoints (for remote/enterprise mode) or directly with repositories (for local mode).

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 8.1 | `skillmeat bom generate` CLI command | Generate BOM and write to .skillmeat/context.lock. Params: (1) --project-id (optional, inferred if in project), (2) --output (default: .skillmeat/context.lock), (3) --include-memory (bool), (4) --include-signatures (bool). | Command executes and produces context.lock file; output path respected; includes specified artifact types; idempotent | 2 | Pending |
| 8.2 | `skillmeat bom verify` CLI command | Verify BOM signature. Params: (1) --file (default: .skillmeat/context.lock), (2) --signature (default: context.lock.sig). Returns: VALID / INVALID with details. | Command verifies signature and returns correct status; displays key metadata; handles missing signature gracefully | 2 | Pending |
| 8.3 | `skillmeat bom restore` CLI command | Restore artifact state from commit. Params: (1) --commit <hash> (required), (2) --dry-run (bool, preview only), (3) --force (bool, skip confirmation). | Command retrieves BOM from commit; optionally prompts for upstream fetch; rehydrates .claude/ to target state; dry-run shows changes | 2 | Pending |
| 8.4 | `skillmeat bom install-hook` CLI command | Install pre-commit hook. Params: (1) --force (overwrite existing). Creates .git/hooks/pre-commit script. | Command installs hook with executable permissions; hook runs on next commit; works on all platforms | 1 | Pending |
| 8.5 | `skillmeat bom` command group and help | Group 4 subcommands under `bom` group. Help text explains BOM concept and each command. | `skillmeat bom --help` shows all subcommands with descriptions; subcommand help is clear and actionable | 1 | Pending |
| 8.6 | `skillmeat history <artifact-name>` CLI command | Show artifact lifecycle history. Params: (1) artifact-name (positional), (2) --limit (default: 50), (3) --event-type (optional filter), (4) --format (table|json, default: table). Output: formatted timeline of events. | Command looks up artifact and shows history; formatted output (table or JSON); timestamps human-readable; event types clear | 2 | Pending |
| 8.7 | `skillmeat history --all` option | Show history for all artifacts in project. Params: (1) --limit (events per artifact), (2) --format (table|json). Output: combined timeline. | Command aggregates all artifact histories; output includes artifact names; timestamps sortable; limit applies per artifact | 1 | Pending |
| 8.8 | `skillmeat attest create` CLI command | Create manual attestation. Params: (1) --artifact-ids <list>, (2) --owner-scope (user|team|enterprise), (3) --notes (optional compliance notes), (4) --sign (optional, sign with key). Returns: attestation_id. | Command creates AttestationRecord via API; accepts artifact list; optional signing; returns ID of created record | 2 | Pending |
| 8.9 | `skillmeat attest list` CLI command | List attestations. Params: (1) --owner-scope (optional), (2) --artifact-id (optional filter), (3) --format (table|json), (4) --limit. Output: paginated list of attestations. | Command calls attestation API; formats output; pagination via cursors; filtering by scope/artifact works | 2 | Pending |
| 8.10 | `skillmeat attest show` CLI command | Show single attestation detail. Params: (1) attestation_id (positional). Output: formatted attestation with all metadata (owner, roles, scopes, signature). | Command fetches attestation and displays detail; includes signature verification status; readable format | 1 | Pending |
| 8.11 | `skillmeat attest` command group and help | Group 3 subcommands under `attest` group. Help text explains attestation workflow. | `skillmeat attest --help` shows subcommands; each subcommand has clear help text | 1 | Pending |
| 8.12 | Output formatting (table, JSON, human-readable) | Consistent output formatting across all commands. Table format for CLI interactivity, JSON for scripting. Timestamps in ISO 8601. | All commands support --format (table|json); timestamps ISO 8601; JSON output valid and parseable | 2 | Pending |
| 8.13 | Error handling and messaging | Clear error messages for all failure cases (missing files, auth errors, network errors, 404s). Suggest remediation steps. | Error messages actionable; suggest next steps; no cryptic exceptions shown to user | 1 | Pending |
| 8.14 | Integration with local and enterprise editions | CLI commands work in both local (SQLite) and enterprise (PostgreSQL) modes. Feature flags control behavior. | Commands auto-detect edition; connect to correct DB; enterprise PAT auth used in enterprise mode | 2 | Pending |
| 8.15 | Integration tests for all CLI commands | Test each command end-to-end with mock artifacts, DB, and API (for enterprise mode). Verify output format and error handling. | All commands tested; output correct and formatted well; error cases handled gracefully | 2 | Pending |

### Key Design Notes

- **CLI Pattern**: Use Click framework (already in skillmeat). Commands follow project naming conventions.
- **Local vs Enterprise**: Use `RepositoryFactory` to determine edition; connect to local DB or make API calls based on edition.
- **Output Formatting**: Table format uses Rich library (no Unicode box drawing); JSON is standard.
- **Pagination in CLI**: Cursor-based pagination (like API) but present to user as simple pagination (page size, next page option).
- **Error Messages**: Include trace_id for API errors; suggest remediation (e.g., "try --force to override").
- **Help Text**: Include examples in help (use Click examples).

### Deliverables

1. **Code**:
   - `skillmeat/cli.py` — Update with new command groups
   - `skillmeat/cli/bom_commands.py` — BOM command group
   - `skillmeat/cli/history_commands.py` — History command group
   - `skillmeat/cli/attest_commands.py` — Attestation command group

2. **Tests**:
   - `skillmeat/cli/tests/test_bom_commands.py` — CLI command tests
   - `skillmeat/cli/tests/test_history_commands.py` — History command tests
   - `skillmeat/cli/tests/test_attest_commands.py` — Attestation command tests

### Exit Criteria

- [ ] All 11 CLI commands (4 bom + 3 history + 3 attest) functional
- [ ] Commands work in both local and enterprise editions
- [ ] Output formatted correctly (table/JSON)
- [ ] Error messages clear and actionable
- [ ] Help text complete with examples
- [ ] Integration tests pass
- [ ] CLI tests achieve >= 80% code coverage
- [ ] All commands follow project naming conventions

---

## Integration Points

### Within Phase 7-8
- Phase 7 API endpoints are data source for Phase 8 CLI
- Phase 8 CLI uses Phase 7 APIs (remote mode) or repos directly (local mode)

### To Phase 9 (Web)
- Phase 7 API endpoints called by React hooks in web app

### To Phase 10 (Backstage)
- Phase 7 `/integrations/idp/bom-card` endpoint called by Backstage plugin

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| API response time exceeds targets | Optimize queries; add DB indexes; lazy-load history data |
| Auth bypass via API | Comprehensive auth tests; code review by security expert |
| CLI breaks existing workflows | Backward-compatible; feature flag to enable (default: off until stable) |
| Pagination cursor corruption | Unit tests for cursor encoding/decoding; validate cursors before use |

---

## Success Metrics

- **API Performance**: History query (100 events) < 200ms p95; attestation list < 100ms p95
- **API Test Coverage**: >= 80% endpoint coverage; all auth scenarios tested
- **CLI Usability**: All commands succeed on first try (no confusing errors)
- **CLI Test Coverage**: >= 80% command coverage
- **OpenAPI Spec**: Auto-generated without manual edits

---

## Next Steps (Gate to Phase 9-10)

1. ✅ Phase 7-8 exit criteria verified
2. ✅ API endpoints tested with integration tests
3. ✅ CLI commands tested and documented
4. ✅ OpenAPI spec generated and verified
5. ✅ Phase 9 (Web) can begin with stable API in place

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-04, FR-06, FR-12, FR-15, FR-16, FR-18, FR-20
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **API CLAUDE.md**: `skillmeat/api/CLAUDE.md`
- **Router Patterns**: `.claude/context/key-context/router-patterns.md`
- **Auth Architecture**: `.claude/context/key-context/auth-architecture.md`
