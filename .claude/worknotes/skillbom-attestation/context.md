---
schema_version: 2
doc_type: context
type: context
prd: "skillbom-attestation"
feature_slug: "skillbom-attestation"
status: active
created: 2026-03-10
updated: 2026-03-10
prd_ref: "docs/project_plans/PRDs/features/skillbom-attestation-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md"
---

# SkillBOM & Attestation System - Context

## Architectural Decisions

### Hexagonal Repository Pattern
All BOM data access goes through `IBomRepository` and `IArtifactHistoryRepository` ABCs in `skillmeat/core/interfaces/repositories.py`. Local (SQLite) uses SQLAlchemy 1.x `session.query()` style; enterprise (PostgreSQL) uses SQLAlchemy 2.x `select()` style. This is **intentional divergence** — do not unify.

Factory: `RepositoryFactory` in `skillmeat/cache/repository_factory.py` selects implementation based on edition. Always use this for DI.

### Fire-and-Forget History Writes
History event recording uses FastAPI `BackgroundTasks` (not sync). Failures are logged, never propagated. Never block mutations for history writes.

### Owner-Scoped RBAC
All attestation and history queries are filtered by `AuthContext`. `AttestationScopeResolver` in `skillmeat/core/bom/scope.py` enforces visibility:
- `user` owner_type: sees only own records
- `team` owner_type: sees all records within team
- `team_admin`: sees all enterprise records
- `system_admin`: sees everything

Use `OwnerType` and `Visibility` enums from `skillmeat/cache/auth_types.py` — do not create new enums.

### Content Hash for Versioning
BOM snapshots use SHA-256 content hashes from existing drift detection utilities (`skillmeat/core/content_hash.py` or `artifact_drift.py`). No sequential version numbers.

### Edition-Based Schema
`AttestationPolicy` model (enterprise-only) exists as a stub in local edition with no DB table. `AttestationRecord` is shared. Local uses Integer PKs; enterprise uses UUID PKs. Use `_pk_type()` helper from existing models to switch conditionally.

### Feature Flags
Three flags in `APISettings`: `skillbom_enabled` (master), `skillbom_auto_sign`, `skillbom_history_capture`. All default `false`. Enable after Phase 7 stabilizes.

## Critical File Paths

### Phase 1-2 (Foundation)
- `skillmeat/cache/models.py` — add 6 new models (AttestationRecord, ArtifactHistoryEvent, BomSnapshot, AttestationPolicy, BomMetadata, ScopeValidator)
- `skillmeat/cache/migrations/versions/` — two Alembic migrations (SQLite + PostgreSQL)
- `skillmeat/core/bom/__init__.py` — new package
- `skillmeat/core/bom/generator.py` — BomGenerator + 13+ artifact adapters + BomSerializer
- `skillmeat/api/schemas/bom.py` — Pydantic schemas (BomSchema, ArtifactEntrySchema, AttestationSchema, HistoryEventSchema)
- `skillmeat/core/tests/test_bom_generator.py` — generator unit tests
- `skillmeat/cache/tests/test_bom_models.py` — model tests

### Phase 3-4 (History & RBAC)
- `skillmeat/core/interfaces/repositories.py` — add IArtifactHistoryRepository ABC
- `skillmeat/core/repositories/local_artifact_history.py` — LocalArtifactHistoryRepository (1.x)
- `skillmeat/cache/enterprise_repositories.py` — add EnterpriseArtifactHistoryRepository (2.x)
- `skillmeat/core/bom/history.py` — ArtifactHistoryService + SQLAlchemy event listeners
- `skillmeat/core/bom/scope.py` — AttestationScopeResolver
- `skillmeat/core/services/bom_service.py` — BOM/attestation service with policy enforcement
- `skillmeat/api/dependencies.py` — add HistoryRepositoryDep, ScopeResolverDep

### Phase 5-6 (Git & Crypto)
- `skillmeat/core/bom/git_integration.py` — hook installer, commit message writer, restore logic
- `skillmeat/core/bom/signing.py` — Ed25519 signing/verification (wraps existing `skillmeat/security/crypto.py`)
- `skillmeat/core/tools/generate_attestation.py` — Claude Code agent tool definition
- `skillmeat/cli.py` — `bom install-hook`, `bom restore` commands

### Phase 7-8 (API & CLI)
- `skillmeat/api/routers/bom.py` — 8 BOM endpoints (new file)
- `skillmeat/api/routers/idp_integration.py` — extend with `/integrations/idp/bom-card/{project_id}`
- `skillmeat/cli/bom_commands.py` — bom command group (new file)
- `skillmeat/cli/history_commands.py` — history command group (new file)
- `skillmeat/cli/attest_commands.py` — attestation command group (new file)
- `skillmeat/api/openapi.json` — update after Phase 7

### Phase 9-10 (Web & Backstage)
- `skillmeat/web/components/provenance/provenance-tab.tsx` — artifact detail provenance tab
- `skillmeat/web/components/bom/bom-viewer.tsx` — context.lock viewer
- `skillmeat/web/components/bom/attestation-badge.tsx` — inline attestation badge
- `skillmeat/web/components/bom/history-timeline.tsx` — event timeline (WCAG 2.1 AA)
- `skillmeat/web/hooks/useBom.ts` — useArtifactHistory, useBomSnapshot, useAttestations hooks
- `skillmeat/web/lib/bom-utils.ts` — BOM/history utility functions
- `plugins/backstage-plugin-scaffolder-backend/src/components/SkillBOMCard.tsx` — Backstage card
- `plugins/backstage-plugin-scaffolder-backend/src/actions/skillmeat-attest.ts` — scaffolder action
- `plugins/backstage-plugin-scaffolder-backend/src/actions/skillmeat-bom-generate.ts` — scaffolder action

### Phase 11 (Validation)
- `tests/integration/test_bom_workflow.py` — end-to-end workflow test
- `tests/load/test_bom_performance.py` — performance benchmarks
- `tests/migration/test_alembic_bom.py` — migration tests
- `.github/workflows/test-bom.yaml` — CI/CD workflow
- `docs/guides/skillbom-workflow.md` — user guide
- `docs/api/bom-api.md` — API docs

## Gotchas

### UUID vs Integer PKs
Local edition (SQLite): Integer PKs with autoincrement. Enterprise (PostgreSQL): UUID PKs with uuid.uuid4() default. The plan docs reference `int` PKs but the implementation uses `uuid.UUID` for enterprise. Always use `_pk_type()` helper from existing models.

### SQLAlchemy 1.x vs 2.x Style
- Local repos: `session.query(Model).filter(...)` (1.x style)
- Enterprise repos: `select(Model).where(...)` (2.x style)
Do NOT unify. This is intentional per codebase architecture. See `skillmeat/cache/tests/CLAUDE.md`.

### JSON Columns — Use `sa.Text()` Not JSONB for Cross-DB Compatibility
SQLite does not support JSONB. Use `Text` columns with JSON serialization for any field that must work on both SQLite and PostgreSQL. Enterprise-only models (AttestationPolicy) can use JSONB with functional indexes. Fields like `diff_json`, `bom_json`, `roles`, `scopes` in shared models must use `Text`.

### SQLAlchemy Comparator Cache Poisoning
When patching `column.type` for SQLite compatibility in tests, the change does not propagate to `comparator.__dict__['type']`. Must manually refresh after patching. See existing test patterns in `skillmeat/cache/tests/test_enterprise_collection_repository.py:90-169`.

### History Event Immutability
`ArtifactHistoryEvent` is immutable by application logic — no UPDATE/DELETE exposed via repositories. SQLAlchemy event listeners on `after_insert` only. Consider adding CHECK constraints or row triggers for extra safety.

### Backstage Auth
The `/integrations/idp/bom-card/{project_id}` endpoint uses `verify_enterprise_pat` (not standard `require_auth`). This is consistent with existing IDP endpoints. Do not use regular user auth here.

### JSONB Tests Must Be Integration-Marked
Any test exercising JSONB `@>` operator or PostgreSQL-specific operators must be `@pytest.mark.integration`. These cannot run on SQLite.

### BOM Generation Idempotency
BOM generation must be deterministic: same artifact state always produces identical JSON. Ensure artifact ordering is deterministic (sort by name or ID), and timestamps in metadata are excluded from the hash computation.

## Phase Dependencies

```
Phase 1 (Models) → Phase 2 (BOM Generator)
                 ↓
Phase 3 (History Capture) ─ [parallel] ─ Phase 4 (RBAC)
                 ↓
Phase 5 (Git Integration) ─ [parallel] ─ Phase 6 (Crypto Signing)
                 ↓
                Phase 7 (API Layer) ← GATEWAY for phases 9-10
               /           \
Phase 8 (CLI) [parallel]   Phase 9 (Web) ─ [parallel] ─ Phase 10 (Backstage)
                                 ↓
                           Phase 11 (Validation & Deployment)
```

- Phase 4 depends on Phase 1 models (AttestationRecord with owner fields)
- Phase 7 depends on Phases 3 and 4 (history and RBAC data ready)
- Phases 9 and 10 depend on Phase 7 API being stable and tested
- Phase 11 depends on Phases 1-10 all merged

## API Endpoints Summary (Phase 7)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/bom/snapshot` | artifact:read | Current BOM snapshot |
| POST | `/api/v1/bom/generate` | artifact:write | Trigger BOM generation |
| GET | `/api/v1/bom/history` | artifact:read | Artifact history log |
| GET | `/api/v1/attestations` | artifact:read | List attestations (owner-scoped) |
| POST | `/api/v1/attestations` | artifact:write | Create attestation |
| GET | `/api/v1/attestations/{id}` | artifact:read | Attestation detail |
| POST | `/api/v1/bom/verify` | artifact:read | Verify BOM signature |
| GET | `/integrations/idp/bom-card/{project_id}` | enterprise PAT | Backstage BOM card |

## Performance Targets

| Operation | Target |
|-----------|--------|
| BOM generation (50 artifacts) | < 2s p95 |
| History query (100 events) | < 200ms p95 |
| History write latency | < 50ms p95 |
| API endpoint response | < 200ms p95 |
| Backstage card load | < 500ms |
| Ed25519 sign | < 500ms |
| Ed25519 verify | < 100ms |
