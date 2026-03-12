---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 1-2: Foundation"
description: >
  Universal schema and data models (Phase 1) + BOM generation service (Phase 2).
  Establishes the foundation for all subsequent phases, including future-compatible
  point-in-time environment recovery.
audience:
  - ai-agents
  - developers
  - database-engineers
tags:
  - implementation-plan
  - phases
  - skillbom
  - database
  - backend
created: 2026-03-10
updated: 2026-03-10
phase: 1-2
phase_title: "Foundation: Schema & BOM Generation"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - PRD approved and signed off
  - Team capacity allocated for 2-3 weeks
  - Database schema review completed
exit_criteria:
  - All 6 models implemented and tested in cache/models.py
  - Alembic migrations pass on SQLite and PostgreSQL
  - BomGenerator service produces valid JSON per v1.0 schema
  - All 13+ artifact type adapters implemented
  - BOM generation benchmarks pass (< 2s for 50 artifacts)
feature_slug: skillbom-attestation
effort_estimate: "27-31 story points"
timeline: "2-3 weeks"
---

# SkillBOM & Attestation System - Phases 1-2: Foundation

## Overview

Phases 1-2 establish the core data models and BOM generation engine required by all subsequent phases. Phase 1 defines the database schema (6 new models, migrations for both SQLite and PostgreSQL). Phase 2 implements the `BomGenerator` service with adapters for all 13+ artifact types.

**Critical**: Phase 1 must complete before Phase 2 begins. The models lock the data contract for all downstream services (history, API, web).

---

## Phase 1: Universal Schema & Data Models

**Duration**: 2 weeks | **Effort**: 13-15 story points | **Assigned**: data-layer-expert

### Overview

Create 6 new SQLAlchemy ORM models in `skillmeat/cache/models.py`:
1. `AttestationRecord` — Owner-scoped attestation metadata
2. `ArtifactHistoryEvent` — Immutable audit log entries
3. `BomSnapshot` — Point-in-time BOM snapshots with signatures
4. `AttestationPolicy` — Enterprise policy enforcement (enterprise edition only)
5. `BomMetadata` — BOM version and format metadata
6. `ScopeValidator` — Helper model for RBAC scope validation

Also create corresponding Alembic migrations for both SQLite (local edition) and PostgreSQL (enterprise edition).

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 1.1 | Define `AttestationRecord` model | SQLAlchemy ORM model for owner-scoped attestation metadata. Fields: id (PK), artifact_id (FK), owner_type (ENUM), owner_id (String), roles (JSON), scopes (JSON), visibility (ENUM), created_at, updated_at. Indexes: (owner_type, owner_id), artifact_id. | Model instantiates and maps to DB table correctly; foreign keys enforce referential integrity; indexes created on both SQLite and PostgreSQL | 3 | Pending |
| 1.2 | Define `ArtifactHistoryEvent` model | SQLAlchemy ORM model for immutable event log. Fields: id (PK), artifact_id (FK), event_type (ENUM: create/update/delete/deploy/undeploy/sync), actor_id (String, nullable), owner_type (ENUM), timestamp, diff_json (Text), content_hash (String). Indexes: (artifact_id, timestamp), (event_type, timestamp), actor_id. | Model instantiates; no UPDATE/DELETE allowed (immutable via app logic); timestamps auto-generated; JSON diffs serialize/deserialize correctly | 3 | Pending |
| 1.3 | Define `BomSnapshot` model | SQLAlchemy ORM model for point-in-time snapshots. Fields: id (PK), artifact_id (FK, nullable), project_id (FK), commit_sha (String, nullable), bom_json (Text), signature (Text, nullable), signature_algorithm (String), owner_type (ENUM), created_at. Indexes: (project_id, created_at), commit_sha (UNIQUE if set). | Model instantiates; bom_json stores valid JSON; signature field nullable (for unsigned BOMs); commit_sha UNIQUE constraint works on PostgreSQL | 3 | Pending |
| 1.4 | Define `AttestationPolicy` model | Enterprise-only model for policy enforcement. Fields: id (PK), tenant_id (FK, enterprise only), name (String), required_artifacts (JSON array of artifact names), required_scopes (JSON array of scope strings), compliance_metadata (JSON), created_at, updated_at. **Local edition**: Model stubbed out but not used. | Model exists in both editions; enterprise edition stores full data; local edition has stub with no DB table; policy enforcement can be added later | 2 | Pending |
| 1.5 | Define `BomMetadata` & `ScopeValidator` helpers | BomMetadata: id, schema_version, format_version (e.g., "1.0.0"), generator_version. ScopeValidator: helper model or utility class for RBAC scope validation. | BomMetadata instantiates; schema_version and format_version stored correctly. ScopeValidator utility supports owner-scope filtering logic. | 1 | Pending |
| 1.6 | Create Alembic migration for SQLite | Migration file for local edition: creates all 6 tables with correct schema, indexes, foreign keys. Test with actual SQLite database. | Migration applies cleanly with `alembic upgrade head`; all tables created with correct columns, types, and constraints; rollback works | 2 | Pending |
| 1.7 | Create Alembic migration for PostgreSQL | Migration file for enterprise edition: creates all 6 tables with PostgreSQL-specific syntax (UUID PKs if applicable, specific index types, constraints). Test with actual PostgreSQL database. | Migration applies cleanly to PostgreSQL test database; UUID types used where appropriate; JSONB indexing functional; rollback works | 2 | Pending |
| 1.8 | Unit tests for model relationships | Tests for foreign key constraints, cascade behavior, and relationship loading. Test artifact_id FK → Artifact.id; project_id FK (if used) → Project.id. | All foreign key relationships verified; cascade rules enforced; relationship loading works in both directions | 2 | Pending |

### Key Design Notes

- **Owner Type**: `AttestationRecord.owner_type` uses enum (user/team/enterprise) from existing `OwnerType` in `skillmeat/cache/auth_types.py`. Do not create new enums.
- **Visibility**: Re-use existing `Visibility` enum (private/team/public) from auth_types.
- **Primary Key Types**:
  - Local (SQLite): Use `Integer` with auto-increment
  - Enterprise (PostgreSQL): Use `UUID` with uuid.uuid4() default
  - Use helper `_pk_type()` from existing models to switch types conditionally
- **JSON Columns**:
  - SQLite: Use `Text` column with JSON serialization (no JSONB)
  - PostgreSQL: Can use `JSONB` with functional indexes for performance
- **Timestamps**: Use `DateTime` with `datetime.utcnow()` default; create indexes on (artifact_id, timestamp) and (event_type, timestamp) for efficient range queries.
- **Immutability of ArtifactHistoryEvent**: Enforce at application layer (no UPDATE/DELETE allowed); consider adding CHECK constraint or rowid trigger if needed.

### Deliverables

1. **Code**: Updated `skillmeat/cache/models.py` with 6 new models, complete with docstrings and type hints.
2. **Migrations**: Two Alembic migration files (one for SQLite, one for PostgreSQL) in `skillmeat/cache/migrations/versions/`.
3. **Tests**: Unit test file `skillmeat/cache/tests/test_bom_models.py` covering model instantiation, relationships, and constraints.
4. **Documentation**: Docstring examples in models showing usage patterns.

### Exit Criteria

- [ ] All 6 models defined in `cache/models.py`
- [ ] Alembic migrations pass on both SQLite and PostgreSQL test databases
- [ ] Foreign key relationships verified (artifact_id, project_id)
- [ ] Indexes created on high-cardinality columns (artifact_id, event_type, owner_id)
- [ ] Unit tests for model CRUD operations pass
- [ ] Type hints are correct and mypy checks pass
- [ ] No breaking changes to existing models (AttestationRecord/BomSnapshot are pure additions)

---

## Phase 2: BOM Generation Service

**Duration**: 2 weeks | **Effort**: 14-16 story points | **Assigned**: python-backend-engineer

### Overview

Implement the `BomGenerator` service and artifact type adapters to produce valid Software Bill of Materials JSON documents. The generator reads the deployed artifact state from the database, collects metadata and content hashes for all 13+ artifact types, and serializes to a v1.0 BOM schema.

Key deliverable: `.skillmeat/context.lock` file generated by `skillmeat bom generate` command.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 2.1 | Create `BomGenerator` service class | Core service in `skillmeat/core/bom/generator.py`. Responsibilities: (1) Read deployed artifacts from DeploymentTracker, (2) Instantiate type-specific adapters, (3) Collect metadata + hashes, (4) Preserve stable identity/source locator metadata needed for future restore, (5) Serialize to BOM JSON. Constructor takes session + AuthContext. | Class instantiates; generates() method returns BomSchema instance with non-empty artifacts array; idempotent (same input → same output); execution time logged via OpenTelemetry | 4 | Pending |
| 2.2 | Skill artifact adapter | ArtifactAdapter for skill type. Collects: name, source, version, content_hash (from Artifact.content_hash or computed via hash_file), metadata (author, tags, etc). | Adapter extracts correct fields from Skill ORM model; content_hash matches deployment state; metadata serializes to dict without errors | 2 | Pending |
| 2.3 | Command, Agent, MCP artifact adapters | Adapters for command, agent, and mcp/mcp_server types. Follow skill adapter pattern. | All three adapters implemented; each extracts correct fields per artifact type; content hashes computed consistently | 2 | Pending |
| 2.4 | Hook, Workflow, Composite artifact adapters | Adapters for hook, workflow, and composite types. Composite adapter must recursively include member artifacts (via CompositeMembership). | Adapters extract metadata correctly; composite adapter returns nested artifacts array for members; recursion depth limited to prevent cycles | 2 | Pending |
| 2.5 | Config, Spec, Rule, Context file adapters | Adapters for project_config, spec_file, rule_file, context_file types. These read from .claude/ directory structure. | Adapters locate files from project path; compute content_hash via hash_file; include file path and MIME type in BOM entry | 2 | Pending |
| 2.6 | Memory item & Deployment set adapters | Adapters for memory_item and deployment_set types. Memory items read from MemoryItem ORM; deployment sets from DeploymentSet ORM. | Memory adapter returns all project-scoped memory items; deployment_set adapter includes member artifacts; both compute content hashes | 2 | Pending |
| 2.7 | Create `BomSerializer` | Class in `skillmeat/core/bom/generator.py` to serialize BomSchema to JSON per v1.0 spec. Produces `.skillmeat/context.lock` file. Methods: to_json() (string), to_dict() (dict), write_file(path). | Serializer produces valid JSON matching BOM schema; write_file() creates file with correct permissions; to_json() and to_dict() are inverses | 2 | Pending |
| 2.8 | Pydantic schemas in `skillmeat/api/schemas/bom.py` | Define `BomSchema`, `ArtifactEntrySchema`, `BomMetadataSchema`, `AttestationSchema`, `HistoryEventSchema`. All cover all 13+ artifact types and preserve future restore-compatible entry metadata such as stable identity, source class, and source/deployment locators where available. | Schemas validate correct structure; from_orm mode works for all fields; schema version and artifact types validated; no required fields missing; restore-compatible metadata fields specified intentionally | 3 | Pending |
| 2.9 | Integration test for BOM generation | End-to-end test: mock deployed artifacts (5-10 of mixed types), instantiate BomGenerator, call generate(), verify output JSON is valid, contains correct number of artifacts, hashes match input. | Test generates complete BOM JSON without errors; artifact count and types correct; content hashes are valid SHA-256; execution time < 2s for 50 artifacts | 2 | Pending |
| 2.10 | Performance benchmarking | Benchmark BOM generation time with 50+ artifacts across all types. Target: < 2 seconds for 50 artifacts. Identify and optimize hotspots. | Benchmark script runs and logs timing; generation completes in < 2s p95; per-artifact adapter time logged and reasonable (< 20ms each) | 2 | Pending |

### Key Design Notes

- **Content Hashing**: Use SHA-256 from existing drift detection utilities (`skillmeat/core/content_hash.py` or similar). Do not re-implement crypto.
- **DeploymentTracker**: Query deployed artifacts via existing `DeploymentTracker` API — read-only access, no modifications.
- **Type-Specific Adapters**: Each artifact type has a dedicated adapter class (SkillAdapter, CommandAdapter, etc.) inheriting from `BaseArtifactAdapter`. Pattern allows future extensibility.
- **Metadata Extraction**: Use existing ORM models and filesystem queries; no new data sources introduced.
- **File-Based Artifacts** (.claude/ directory): Use project path from AuthContext to locate files; compute hashes dynamically.
- **Memory Items**: Query MemoryItem ORM with project scope filter; include content hash of item.text.
- **Error Handling**: If an artifact adapter fails (missing file, bad hash), log warning but continue generating BOM without that artifact (partial BOM is better than complete failure).
- **Idempotency**: Same input artifact state always produces identical BOM JSON (timestamps, ordering must be deterministic).
- **Future Restore Compatibility**: BOM entries should preserve stable artifact identity and source/deployment locator metadata where available so a later restore architecture can resolve exact historical content without breaking the manifest format.

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/generator.py` — BomGenerator class + 13+ artifact adapters
   - `skillmeat/api/schemas/bom.py` — Pydantic schemas for BOM, attestation, history
2. **Tests**:
   - `skillmeat/core/tests/test_bom_generator.py` — Unit tests for each adapter and serializer
   - `skillmeat/core/tests/test_bom_performance.py` — Benchmark tests for generation time
3. **Configuration**:
   - Feature flag `skillbom_enabled: false` in `APISettings` (enable after Phase 7)
   - Configuration option `bom_artifact_limit: 50` (max artifacts to include)

### Exit Criteria

- [ ] BomGenerator service instantiates and generates valid JSON
- [ ] All 13+ artifact type adapters implemented and tested
- [ ] `context.lock` file produced with correct format and content hashes
- [ ] BOM schema preserves stable identity/source locator metadata required for future point-in-time recovery
- [ ] Performance benchmark: 50 artifacts in < 2 seconds
- [ ] Pydantic schemas validate all artifact types
- [ ] Error handling: partial BOM on adapter failures, not hard failure
- [ ] Integration test passes with mock deployed artifacts
- [ ] Idempotency test: same input always produces same JSON output

---

## Key Files Modified

### New Files
- `skillmeat/cache/models.py` (add 6 models)
- `skillmeat/core/bom/generator.py` (new file)
- `skillmeat/core/bom/__init__.py` (new package)
- `skillmeat/api/schemas/bom.py` (new file)
- `skillmeat/cache/migrations/versions/20260310_*.py` (SQLite migration)
- `skillmeat/cache/migrations/versions/20260310_*.py` (PostgreSQL migration)

### Modified Files
- `skillmeat/cache/models.py` (Base class imports)
- `.claude/config/multi-model.toml` (feature flag)

---

## Database Migration Strategy

Both local (SQLite) and enterprise (PostgreSQL) editions need migrations.

### SQLite Migration
Use SQLAlchemy dialect-agnostic approach:
- Integer PKs with autoincrement
- Text columns for JSON
- Simple foreign keys
- Standard index syntax

### PostgreSQL Migration
Optimize for enterprise scale:
- UUID PKs
- JSONB columns with functional indexes
- Advanced constraint types
- Partitioning hints for large tables (future)

### Testing
Run both migrations on test databases to ensure:
1. Schema applies cleanly (no syntax errors)
2. Foreign key constraints enforced
3. Indexes created and functional
4. Rollback works (down revision)
5. Data integrity preserved (cascade, nullability)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Schema conflicts with existing models | Review existing models first; add new models only, no modifications to existing tables |
| Migration breaks existing deployments | Test on both SQLite and PostgreSQL; provide rollback plan; run dry-run before deployment |
| Performance regression on large artifact lists | Benchmark early; add indexes on high-cardinality columns; profile adapter execution time |
| Content hash mismatches | Use existing hash utilities; validate hashes with known-good test data |
| Adapter extensibility gaps | Design BaseArtifactAdapter ABC upfront; allow future adapters without modifying core logic |

---

## Success Metrics

- **Model Tests**: 100% of model unit tests pass
- **Migration Tests**: Both SQLite and PostgreSQL migrations apply and rollback cleanly
- **BOM Generation**: 50-artifact BOM generates in < 2 seconds
- **Schema Validation**: All 13+ artifact types validate against Pydantic schemas
- **Code Coverage**: >= 80% coverage for generator and adapter code

---

## Next Steps (Gate to Phase 3)

1. ✅ Phase 1 & 2 exit criteria verified
2. ✅ Models locked (no further changes without explicit approval)
3. ✅ BomGenerator service tested and performance validated
4. ✅ Phase 3 (History Capture) can begin with models + generator as foundation

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § Functional Requirements (FR-01, FR-02)
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **Cache Layer Guide**: `skillmeat/cache/CLAUDE.md`
- **Existing Drift Detection**: `skillmeat/core/artifact_drift.py` (reference for content_hash utilities)
- **DeploymentTracker**: `skillmeat/core/deployment.py` (reference for deployed artifacts API)
