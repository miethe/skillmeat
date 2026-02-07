---
title: "Implementation Plan: Workflow Orchestration Engine"
description: "Comprehensive phased implementation plan with task breakdown, subagent assignments, and acceptance criteria for the Workflow Orchestration Engine feature."
audience: [ai-agents, developers, architects]
tags: [implementation, planning, phases, tasks, workflow, orchestration, automation, agents]
created: 2026-02-06
updated: 2026-02-06
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/workflow-orchestration-v1.md
  - /docs/project_plans/specs/workflow-orchestration-schema-spec.md
  - /docs/project_plans/design/workflow-orchestration-ui-spec.md
  - /docs/project_plans/implementation_plans/features/memory-context-system-v1.md
---

# Implementation Plan: Workflow Orchestration Engine

**Plan ID**: `IMPL-2026-02-06-workflow-orchestration-v1`
**Date**: 2026-02-06
**Author**: Implementation Planner Orchestrator (Opus)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/workflow-orchestration-v1.md`
- **Schema Spec**: `/docs/project_plans/specs/workflow-orchestration-schema-spec.md`
- **UI/UX Design Spec**: `/docs/project_plans/design/workflow-orchestration-ui-spec.md`
- **Memory Context System Plan**: `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md`
- **API Reference**: `/skillmeat/api/CLAUDE.md`
- **Frontend Reference**: `/skillmeat/web/CLAUDE.md`
- **Router Patterns**: `.claude/context/key-context/router-patterns.md`
- **Component Patterns**: `.claude/context/key-context/component-patterns.md`

**Complexity**: Extra Large (XL)
**Total Estimated Effort**: 72 story points
**Target Timeline**: 9-10 weeks (Phases 0-7)

---

## Executive Summary

The Workflow Orchestration Engine elevates SkillMeat from managing individual artifacts (skills, agents, commands) to managing multi-stage agentic processes. This plan guides the implementation of a complete workflow system: the SkillMeat Workflow Definition Language (SWDL) for declarative YAML-based workflow authoring, a DAG execution engine with parallel batch computation, a visual Workflow Builder with drag-and-drop stage reordering, and a real-time Execution Dashboard with SSE-powered live updates.

The implementation follows MeatyPrompts layered architecture (Foundation --> Schema/Core --> Database --> Service/API --> CLI --> Frontend Library/Builder --> Frontend Execution --> Integration/Testing) across eight phases. The system integrates with the existing Memory & Context system (v1, fully implemented) for per-stage context injection, the Collection architecture for workflow storage and sync, and the Bundle system for workflow sharing.

**Key Milestones**:
1. Phase 0: Prerequisites, feature branch, dependency install (0.5 weeks)
2. Phase 1: SWDL schema parser, validator, expression language, DAG engine (1 week)
3. Phase 2: Database tables, ORM models, repositories (1 week)
4. Phase 3: Services, API routers, execution engine (1.5 weeks)
5. Phase 4: CLI commands (1 week, parallelizable with Phase 5)
6. Phase 5: Frontend Workflow Library and Builder (2 weeks)
7. Phase 6: Frontend Execution Dashboard (1.5 weeks)
8. Phase 7: Integration testing, bundle support, documentation, deployment (1 week)

**Success Criteria**: All 14 API endpoints operational, SWDL parser handles 100% of schema spec features (v1 scope), workflow execution supports sequential + parallel stages with retry, <300ms list query p95, <1s workflow plan generation p95, WCAG 2.1 AA accessibility on all new UI pages, 80%+ test coverage across backend services.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture, build bottom-up with strategic frontend overlap:

1. **Foundation Layer** -- Add `WORKFLOW` to ArtifactType, install `@dnd-kit`, establish feature branch
2. **Schema/Core Layer** -- SWDL parser, validator, expression engine, DAG builder, topological sort
3. **Database Layer** -- Alembic migration for `workflows`, `workflow_stages`, `workflow_executions`, `execution_steps` tables
4. **Repository Layer** -- WorkflowRepository, WorkflowExecutionRepository with cursor pagination
5. **Service Layer** -- WorkflowService (CRUD, validate, plan), WorkflowExecutionService (run, pause, resume, cancel), WorkflowContextService (memory/context integration)
6. **API Layer** -- FastAPI routers at `/api/v1/workflows` and `/api/v1/workflow-executions`, SSE streaming endpoint
7. **CLI Layer** -- `skillmeat workflow` command group (create, list, plan, run, validate, show, cancel, approve)
8. **UI Layer** -- Workflow Library, Builder (with @dnd-kit), Detail, Execution Dashboard, Execution List
9. **Testing Layer** -- Unit, integration, E2E, component tests (80%+ coverage)
10. **Documentation Layer** -- API docs, user guides, SWDL authoring guide
11. **Deployment Layer** -- Feature flags, monitoring, bundle integration, collection sync

### Parallel Work Opportunities

- **Phase 1 and Phase 2 can overlap**: DAG engine implementation does not block database schema design; core models inform both
- **Phase 4 (CLI) and Phase 5 (Frontend Library/Builder)** are fully independent once Phase 3 API is complete
- **Phase 5 frontend design** can begin during Phase 3 (types, hooks, navigation scaffolding)
- **Phase 6 (Execution Dashboard)** depends on Phase 3 API and Phase 5 component primitives (StageCard, connectors), but the SSE hook can be built in parallel
- **Testing throughout**: Unit tests accompany each phase; integration and E2E tests consolidate in Phase 7

### Critical Path

```
Phase 0 --> Phase 1 (Schema/Core) --> Phase 2 (Database) --> Phase 3 (Service/API) --> Phase 5 (Frontend Builder)
                                                                    |                          |
                                                                    +--> Phase 4 (CLI)         +--> Phase 6 (Execution Dashboard)
                                                                                                          |
                                                                                                          +--> Phase 7 (Integration)
```

The longest path is: Phase 0 --> 1 --> 2 --> 3 --> 5 --> 6 --> 7 = 8.5 weeks. Phases 1+2 overlap and Phases 4+5 overlap compress this to ~9 weeks.

---

## Phase 0: Prerequisites & Foundation

**Duration**: 0.5 weeks
**Dependencies**: None (blocking)
**Assigned Subagent(s)**: lead-architect, codebase-explorer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PREP-0.1 | Create Feature Branch | Create `feat/workflow-orchestration-v1` branch from main | Branch exists, initial commit with plan reference | 0.5 pt | lead-architect | None |
| PREP-0.2 | Add WORKFLOW ArtifactType | Add `WORKFLOW = "workflow"` to `ArtifactType` enum in `skillmeat/core/artifact_detection.py`; add detection heuristic for `WORKFLOW.yaml` / `WORKFLOW.json` | Enum extended, `detect_artifact_type()` returns `WORKFLOW` for directories containing `WORKFLOW.yaml` | 1 pt | python-backend-engineer | PREP-0.1 |
| PREP-0.3 | Install @dnd-kit Dependency | Run `pnpm add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities` in `skillmeat/web/` | Packages in `package.json`, lockfile updated, builds successfully | 0.5 pt | ui-engineer-enhanced | PREP-0.1 |
| PREP-0.4 | Review Existing Patterns | Review `context_entities.py` router, `BundleBuilder` pattern, collection manifest structure, MemoryService/ContextPackerService integration points | Design notes capturing pagination, DTO, error handling, bundle, and memory integration patterns | 1 pt | lead-architect | None |
| PREP-0.5 | Create Collection Workflow Directory | Add `workflows/` to the collection directory structure at `~/.skillmeat/collection/artifacts/workflows/`; update `collection.toml` schema to accept `type = "workflow"` entries | Directory created, manifest accepts workflow entries, existing collection operations unaffected | 1 pt | python-backend-engineer | PREP-0.2 |

**Phase 0 Quality Gates**:
- [ ] Feature branch created and pushed
- [ ] `ArtifactType.WORKFLOW` in enum, detection working
- [ ] `@dnd-kit` installed and building
- [ ] Pattern review documented
- [ ] Collection directory supports workflows

---

## Phase 1: Schema & Core Logic (SWDL Engine)

**Duration**: 1 week
**Dependencies**: Phase 0 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

This phase implements the heart of the system: the SkillMeat Workflow Definition Language parser, validator, expression engine, and DAG computation. All code lives in `skillmeat/core/workflow/`.

### 1.1 SWDL Schema & Parser

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SCHEMA-1.1 | Pydantic Models for SWDL | Create Pydantic v2 models in `skillmeat/core/workflow/models.py` matching the Schema Spec: `WorkflowDefinition`, `WorkflowConfig`, `WorkflowParameter`, `StageDefinition`, `RoleAssignment`, `InputContract`, `OutputContract`, `ErrorPolicy`, `RetryPolicy`, `HandoffConfig`, `GateConfig`, `ContextBinding`, `UIMetadata` | All models parse the complete example from Schema Spec Section 6; validation errors are descriptive; sensible defaults per Section 8 (Defaults table) | 3 pts | backend-architect | PREP-0.4 |
| SCHEMA-1.2 | YAML/JSON Parser | Implement `parse_workflow(path: Path) -> WorkflowDefinition` in `skillmeat/core/workflow/parser.py` that loads YAML or JSON, validates against Pydantic models, and returns the typed definition | Parses both `.yaml` and `.json`; rejects malformed files with clear error messages; handles the minimal 30-line example (Section 7) and the full 150-line example (Section 6) | 2 pts | python-backend-engineer | SCHEMA-1.1 |
| SCHEMA-1.3 | Schema Defaults Application | Implement default-filling logic per Schema Spec Section 8 (timeout: 2h, retry max_attempts: 2, on_failure: halt, etc.) | Missing fields receive documented defaults; explicit values are never overwritten; roundtrip: parse -> serialize -> parse produces identical output | 1 pt | python-backend-engineer | SCHEMA-1.1 |

### 1.2 Expression Language

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| EXPR-1.4 | Expression Parser | Implement `${{ }}` expression parser in `skillmeat/core/workflow/expressions.py` supporting: property access (`parameters.feature_name`, `stages.research.outputs.summary`), comparisons (`==`, `!=`), boolean operators (`&&`, `\|\|`, `!`), ternary (`a ? b : c`) | All namespaces from Schema Spec Section 3.6 supported: `parameters`, `stages.<id>.outputs`, `stages.<id>.status`, `context`, `env`, `run`, `workflow`; invalid expressions produce clear parse errors | 3 pts | backend-architect | SCHEMA-1.1 |
| EXPR-1.5 | Built-in Functions | Implement `length()`, `contains()`, `toJSON()`, `fromJSON()` functions within the expression evaluator | Functions pass unit tests: `length([1,2,3]) == 3`, `contains("hello", "ell") == true`, `toJSON({a:1}) == '{"a":1}'`, `fromJSON('{"a":1}').a == 1` | 1 pt | python-backend-engineer | EXPR-1.4 |
| EXPR-1.6 | Expression Validation (Static) | Implement static validation: check that all `${{ stages.X.outputs.Y }}` references correspond to declared dependencies and output contracts | Validation errors for: referencing a stage not in `depends_on`, referencing a non-existent output field, type mismatch between input `type` and referenced output `type` | 2 pts | backend-architect | EXPR-1.4, SCHEMA-1.1 |

### 1.3 DAG Engine

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DAG-1.7 | Dependency Graph Builder | Implement `build_dag(workflow: WorkflowDefinition) -> DAG` in `skillmeat/core/workflow/dag.py` that constructs a directed acyclic graph from `depends_on` declarations | DAG correctly represents all stage dependencies; stages with no dependencies are root nodes; all edges are validated | 2 pts | python-backend-engineer | SCHEMA-1.1 |
| DAG-1.8 | Cycle Detection | Implement cycle detection in the DAG builder; raise `WorkflowCycleError` with descriptive message showing the cycle path | Detects direct cycles (`A -> B -> A`), indirect cycles (`A -> B -> C -> A`), and self-references (`A -> A`); error message shows full cycle path | 1 pt | python-backend-engineer | DAG-1.7 |
| DAG-1.9 | Parallel Batch Computation | Implement `compute_execution_batches(dag: DAG) -> list[Batch]` using topological sort; stages in the same batch can execute in parallel | Correct batch ordering for: fully sequential workflows, fully parallel workflows, diamond dependencies (fan-out + fan-in), mixed patterns; conditional stages grouped in the correct batch | 2 pts | backend-architect | DAG-1.7 |
| DAG-1.10 | Execution Plan Generator | Implement `generate_plan(workflow: WorkflowDefinition, parameters: dict) -> ExecutionPlan` that resolves parameters, builds DAG, computes batches, resolves artifact references, and estimates timing | Plan output matches the format in Schema Spec Section 4.2; includes batch grouping, agent assignments, context bindings, timeout estimates; raises errors for unresolved artifact references | 2 pts | backend-architect | DAG-1.9, EXPR-1.4 |

### 1.4 Phase 1 Tests

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TEST-1.11 | Parser Unit Tests | Tests for YAML/JSON parsing, defaults, validation errors, minimal and full examples | 90%+ coverage on parser module; all Schema Spec examples parse correctly; malformed inputs produce descriptive errors | 2 pts | python-backend-engineer | SCHEMA-1.2, SCHEMA-1.3 |
| TEST-1.12 | Expression Unit Tests | Tests for expression parsing, evaluation, static validation, built-in functions, error cases | All operators, namespaces, and functions tested; invalid expressions produce clear errors; edge cases (null values, missing fields) handled | 2 pts | python-backend-engineer | EXPR-1.5, EXPR-1.6 |
| TEST-1.13 | DAG Unit Tests | Tests for graph construction, cycle detection, batch computation, plan generation | All dependency patterns tested (sequential, parallel, diamond, conditional); cycle detection works; batch ordering correct | 2 pts | python-backend-engineer | DAG-1.10 |

**Phase 1 Quality Gates**:
- [ ] Full SWDL schema parsed from YAML and JSON
- [ ] Expression language supports all v1 namespaces and operators
- [ ] Static validation catches reference errors at plan time
- [ ] DAG cycle detection working
- [ ] Parallel batch computation correct for all patterns
- [ ] Execution plan generates readable output
- [ ] Test coverage >85% on `skillmeat/core/workflow/`

---

## Phase 2: Database + Repository Layer

**Duration**: 1 week (can overlap with Phase 1 DAG work)
**Dependencies**: Phase 0 complete, SCHEMA-1.1 (Pydantic models inform ORM design)
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

### 2.1 Database Schema Design

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DB-2.1 | Alembic Migration | Create migration for 4 tables: `workflows`, `workflow_stages`, `workflow_executions`, `execution_steps` with relationships and constraints | Migration file created, FK relationships defined, all columns specified, forward and backward migration tested | 3 pts | data-layer-expert | PREP-0.2 |
| DB-2.2 | ORM Models | Implement SQLAlchemy models in `skillmeat/cache/models/`: `Workflow`, `WorkflowStage`, `WorkflowExecution`, `ExecutionStep` | All fields mapped, relationships configured (cascade deletes), JSON columns for flexible data (parameters, context_policy, outputs) | 2 pts | python-backend-engineer | DB-2.1 |
| DB-2.3 | Indexes & Constraints | Add indexes for query optimization; unique constraints; check constraints | Indexes on (status, updated_at), (workflow_id, status) for executions, (execution_id, stage_id) for steps; UNIQUE on workflow name per user; CHECK on status enums | 1 pt | data-layer-expert | DB-2.2 |

**Tables Created**:

1. **workflows**
   - Columns: id (UUID PK), name (str, NOT NULL), description (text, nullable), version (str, default "1.0.0"), status (str: draft/published/archived), definition_yaml (text, NOT NULL -- stores canonical SWDL YAML), definition_hash (str -- content hash for change detection), tags_json (text -- JSON array), global_context_module_ids_json (text -- JSON array), config_json (text -- parameters, timeout, env), error_policy_json (text), hooks_json (text), ui_metadata_json (text), created_by (str, nullable), created_at (datetime), updated_at (datetime)
   - Constraints: UNIQUE (name, created_by), CHECK status IN ('draft', 'published', 'archived')

2. **workflow_stages**
   - Columns: id (UUID PK), workflow_id (FK workflows.id CASCADE), stage_id_ref (str -- the `id` field from SWDL, e.g., "research"), name (str), description (text, nullable), order_index (int), depends_on_json (text -- JSON array of stage_id_refs), condition (str, nullable), stage_type (str: agent/gate, default "agent"), roles_json (text), inputs_json (text), outputs_json (text), context_json (text), error_policy_json (text), handoff_json (text), gate_json (text, nullable), ui_metadata_json (text, nullable), created_at (datetime), updated_at (datetime)
   - Constraints: FK workflow_id, UNIQUE (workflow_id, stage_id_ref), UNIQUE (workflow_id, order_index)

3. **workflow_executions**
   - Columns: id (UUID PK), workflow_id (FK workflows.id), workflow_name (str -- denormalized), workflow_version (str -- snapshot), workflow_definition_hash (str -- snapshot), status (str: pending/running/paused/completed/failed/cancelled), parameters_json (text), overrides_json (text, nullable), trigger (str: manual/scheduled/api), started_at (datetime, nullable), completed_at (datetime, nullable), error_message (text, nullable), created_at (datetime), updated_at (datetime)
   - Constraints: FK workflow_id, CHECK status enum, CHECK trigger enum

4. **execution_steps**
   - Columns: id (UUID PK), execution_id (FK workflow_executions.id CASCADE), stage_id_ref (str -- references workflow_stages.stage_id_ref), stage_name (str -- denormalized), status (str: pending/running/completed/failed/skipped/timed_out/cancelled), attempt_number (int, default 1), agent_id (str, nullable), context_consumed_json (text, nullable), inputs_json (text, nullable), outputs_json (text, nullable), logs_json (text, nullable -- JSON array of log lines), error_message (text, nullable), started_at (datetime, nullable), completed_at (datetime, nullable), duration_seconds (float, nullable), created_at (datetime), updated_at (datetime)
   - Constraints: FK execution_id CASCADE, CHECK status enum

### 2.2 Repository Layer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| REPO-2.4 | WorkflowRepository | Implement CRUD + list with filters (status, tags, search), cursor pagination, find_by_name | All methods working, cursor pagination implemented, tag search via JSON contains, text search on name/description | 3 pts | python-backend-engineer | DB-2.3 |
| REPO-2.5 | WorkflowExecutionRepository | Implement CRUD + list with filters (workflow_id, status, date range), cursor pagination, active execution queries | CRUD operations complete, filter by workflow and status, list ordered by started_at desc | 2 pts | python-backend-engineer | DB-2.3 |
| REPO-2.6 | ExecutionStepRepository | Implement CRUD + list by execution_id, update status/outputs/logs, bulk status updates | Step operations working, log appending efficient (JSON array append), bulk updates for batch status changes | 1 pt | python-backend-engineer | DB-2.3 |
| REPO-2.7 | Transaction Handling | Add rollback/error handling for all mutations; execution state changes are atomic | Errors trigger automatic rollback, no partial writes, concurrent execution updates handled | 1 pt | data-layer-expert | REPO-2.4 |
| TEST-2.8 | Repository Tests | Unit tests for all repository methods, pagination edge cases, filter combinations | 85%+ coverage, all CRUD ops tested, pagination edge cases, concurrent access scenarios | 2 pts | python-backend-engineer | REPO-2.7 |

**Pagination Pattern** (following existing `context_entities.py`):
- Cursor-based pagination with base64-encoded cursors
- Cursor value: `{id}:{sort_field_value}`
- Response envelope: `items`, `next_cursor`, `prev_cursor`, `has_more`, `total_count`

**Phase 2 Quality Gates**:
- [ ] Alembic migration passes forward/backward tests
- [ ] All 4 ORM models correctly mapped with relationships
- [ ] Indexes created and verified via EXPLAIN QUERY PLAN
- [ ] All 3 repositories implemented with CRUD + pagination
- [ ] Transaction handling prevents partial writes
- [ ] Test coverage >85% on repository layer

---

## Phase 3: Service + API Layer

**Duration**: 1.5 weeks
**Dependencies**: Phase 1 (core engine) and Phase 2 (repositories) complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

### 3.1 Service Layer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SVC-3.1 | WorkflowService -- CRUD | Create `skillmeat/core/workflow/service.py` with create (from YAML string or file path), get, list, update, delete, duplicate methods | All methods return DTOs, create parses YAML and stores definition + decomposed stages, update re-parses and re-validates, delete cascades to stages | 3 pts | backend-architect | REPO-2.4, SCHEMA-1.2 |
| SVC-3.2 | WorkflowService -- Validate | Implement `validate(workflow_id_or_yaml: str) -> ValidationResult` that runs schema validation, expression validation, DAG validation, and artifact resolution | Returns structured result with errors/warnings categorized (schema, expression, dag, artifact); validates the full SWDL spec | 2 pts | backend-architect | SVC-3.1, EXPR-1.6, DAG-1.8 |
| SVC-3.3 | WorkflowService -- Plan | Implement `plan(workflow_id: str, parameters: dict) -> ExecutionPlan` that validates, resolves parameters, builds DAG, computes batches, resolves artifacts, and returns a human-readable plan | Plan includes batch grouping, agent assignments, context modules, timeout estimates; matches Schema Spec Section 4.2 output format | 2 pts | backend-architect | SVC-3.2, DAG-1.10 |
| SVC-3.4 | WorkflowExecutionService -- Run | Implement `start_execution(workflow_id: str, parameters: dict, overrides: dict) -> WorkflowExecution` that creates execution record, snapshots workflow definition, and starts the execution loop | Execution record created with "running" status, workflow version snapshotted, stages initialized as "pending" | 3 pts | python-backend-engineer | SVC-3.3, REPO-2.5 |
| SVC-3.5 | WorkflowExecutionService -- Stage Executor | Implement the stage execution loop: process batches sequentially; within each batch, execute stages in parallel; handle retries, timeouts, error policies, conditional skipping | Sequential batches processed in order; parallel stages within a batch execute concurrently; retry with backoff per error_policy; conditional stages skipped when condition evaluates to false; gate stages pause execution | 5 pts | backend-architect | SVC-3.4, EXPR-1.4 |
| SVC-3.6 | WorkflowExecutionService -- Controls | Implement pause, resume, cancel operations on running executions | Pause stops after current batch completes; resume continues from next batch; cancel terminates all running stages and marks execution as cancelled | 2 pts | python-backend-engineer | SVC-3.5 |
| SVC-3.7 | WorkflowExecutionService -- Handoff | Implement inter-stage data handoff: validate outputs against contracts, serialize per handoff config, optional summary prompt | Outputs validated before handoff; structured JSON format by default; summary prompt triggers a condensation step; outputs stored in execution step record and available to downstream stages via expression resolution | 2 pts | backend-architect | SVC-3.5 |
| SVC-3.8 | WorkflowContextService | Integrate with existing `ContextModuleService` and `ContextPackerService` to inject context per stage: resolve `ctx:*` references, call `pack_context()` with stage-specific memory config | Global context modules applied to all stages; stage-specific modules override or extend; memory injection respects min_confidence and max_tokens; context available to stage executor | 2 pts | python-backend-engineer | SVC-3.5 |

### 3.2 API Layer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| API-3.9 | Workflow CRUD Router | Implement `skillmeat/api/routers/workflows.py` with GET (list), POST (create), GET/{id}, PUT/{id}, DELETE/{id}, POST/{id}/duplicate | All endpoints return DTOs, pagination working, create accepts YAML body, error handling consistent with existing routers | 3 pts | python-backend-engineer | SVC-3.1 |
| API-3.10 | Workflow Operations Router | Implement POST/{id}/validate, POST/{id}/plan endpoints | Validate returns structured errors/warnings; plan returns execution plan with batch grouping; both accept parameters query/body | 2 pts | python-backend-engineer | SVC-3.2, SVC-3.3 |
| API-3.11 | Execution CRUD Router | Implement `skillmeat/api/routers/workflow_executions.py` with POST (run), GET (list all), GET by workflow_id, GET/{run_id} | Run creates execution and returns run_id; list supports filtering by workflow_id and status; detail returns full execution with step statuses | 2 pts | python-backend-engineer | SVC-3.4 |
| API-3.12 | Execution Controls Router | Implement POST/{run_id}/pause, POST/{run_id}/resume, POST/{run_id}/cancel, POST/{run_id}/gates/{stage_id}/approve, POST/{run_id}/gates/{stage_id}/reject | Controls modify execution state correctly; gate approval/rejection advances or halts the workflow; error responses for invalid state transitions | 2 pts | python-backend-engineer | SVC-3.6 |
| API-3.13 | SSE Streaming Endpoint | Implement GET /workflows/{id}/executions/{run_id}/stream as Server-Sent Events endpoint emitting: `stage_started`, `stage_completed`, `stage_failed`, `log_line`, `execution_completed` | SSE connection stays open for active executions; events stream in real-time; connection closes when execution completes; fallback to polling documented | 2 pts | backend-architect | SVC-3.5 |
| API-3.14 | Pydantic Schemas | Create request/response schemas in `skillmeat/api/schemas/workflow.py`: `WorkflowCreateRequest`, `WorkflowResponse`, `WorkflowListResponse`, `ExecutionCreateRequest`, `ExecutionResponse`, `ExecutionListResponse`, `ExecutionStepResponse`, `ValidationResultResponse`, `ExecutionPlanResponse` | All schemas validate inputs, never expose ORM models, match OpenAPI best practices | 2 pts | python-backend-engineer | API-3.9 |
| API-3.15 | OpenAPI Documentation | Update `skillmeat/api/openapi.json` with all new endpoints and schemas; include request/response examples | All 14 endpoints documented, request/response schemas accurate, examples for create, plan, and run | 1 pt | python-backend-engineer | API-3.14 |
| TEST-3.16 | API Integration Tests | Integration tests for all endpoints: CRUD, validate, plan, run, controls, SSE | All endpoints tested with happy path and error cases; 85%+ coverage; pagination verified; SSE events received | 3 pts | python-backend-engineer | API-3.15 |
| TEST-3.17 | E2E Service Test | Full lifecycle: create workflow from YAML --> validate --> plan --> run --> complete (with mock agent dispatch) | Complete workflow from creation to execution completion; all stages transition through correct statuses; outputs propagate via handoff | 2 pts | python-backend-engineer | TEST-3.16 |

**API Endpoints Summary** (14 endpoints):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/workflows` | List workflows (paginated, filterable) |
| `POST` | `/api/v1/workflows` | Create workflow from YAML definition |
| `GET` | `/api/v1/workflows/{id}` | Get workflow detail |
| `PUT` | `/api/v1/workflows/{id}` | Update workflow definition |
| `DELETE` | `/api/v1/workflows/{id}` | Delete workflow |
| `POST` | `/api/v1/workflows/{id}/duplicate` | Duplicate workflow |
| `POST` | `/api/v1/workflows/{id}/validate` | Validate workflow schema |
| `POST` | `/api/v1/workflows/{id}/plan` | Generate execution plan (dry run) |
| `POST` | `/api/v1/workflows/{id}/run` | Start workflow execution |
| `GET` | `/api/v1/workflow-executions` | List all executions |
| `GET` | `/api/v1/workflow-executions/{run_id}` | Get execution detail |
| `POST` | `/api/v1/workflow-executions/{run_id}/pause` | Pause execution |
| `POST` | `/api/v1/workflow-executions/{run_id}/resume` | Resume execution |
| `POST` | `/api/v1/workflow-executions/{run_id}/cancel` | Cancel execution |
| `POST` | `/api/v1/workflow-executions/{run_id}/gates/{stage_id}/approve` | Approve gate |
| `POST` | `/api/v1/workflow-executions/{run_id}/gates/{stage_id}/reject` | Reject gate |
| `GET` | `/api/v1/workflows/{id}/executions/{run_id}/stream` | SSE stream |

**Error Handling Pattern**:
- Use `ErrorResponse` envelope (consistent with existing API)
- Return appropriate HTTP codes: 400 (validation), 404 (not found), 409 (conflict/invalid state transition), 422 (unprocessable)
- Log all errors with trace ID and context

**Phase 3 Quality Gates**:
- [ ] All services passing unit tests (80%+ coverage)
- [ ] All 14+ API endpoints returning correct responses
- [ ] Cursor pagination working on both workflows and executions
- [ ] DTOs never expose ORM models
- [ ] SSE streaming delivers real-time events
- [ ] Execution engine processes sequential and parallel batches
- [ ] Retry, timeout, and error policies working
- [ ] Gate stages pause and resume correctly
- [ ] Context injection via ContextPackerService working
- [ ] OpenAPI documentation complete
- [ ] Integration tests passing
- [ ] E2E lifecycle test passing

---

## Phase 4: CLI Commands

**Duration**: 1 week (can run in parallel with Phase 5)
**Dependencies**: Phase 3 API complete
**Assigned Subagent(s)**: python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CLI-4.1 | Workflow Command Group | Create `skillmeat workflow` Click command group in `skillmeat/cli.py` or `skillmeat/cli/workflow.py` | Command group registered, `skillmeat workflow --help` shows all subcommands | 1 pt | python-backend-engineer | API-3.9 |
| CLI-4.2 | `workflow create` | Implement `skillmeat workflow create <path>` that reads a YAML file, validates it, and creates the workflow in the collection + DB | Creates workflow from YAML file; validates first; reports errors clearly; stores in collection under `artifacts/workflows/<name>/`; syncs to DB cache | 2 pts | python-backend-engineer | CLI-4.1, SVC-3.1 |
| CLI-4.3 | `workflow list` | Implement `skillmeat workflow list [--status STATUS] [--tag TAG] [--format table\|json]` | Lists workflows in Rich table (name, version, status, stages count, last run); supports JSON output; filters work | 1 pt | python-backend-engineer | CLI-4.1 |
| CLI-4.4 | `workflow show` | Implement `skillmeat workflow show <name>` that displays workflow definition, stages, and last execution info | Shows workflow metadata, stage list with roles and dependencies, last execution status; Rich formatted output | 1 pt | python-backend-engineer | CLI-4.1 |
| CLI-4.5 | `workflow validate` | Implement `skillmeat workflow validate <path>` that validates a YAML file without importing | Reports schema errors, expression errors, DAG errors, artifact resolution warnings; exits 0 on valid, 1 on invalid | 1 pt | python-backend-engineer | CLI-4.1, SVC-3.2 |
| CLI-4.6 | `workflow plan` | Implement `skillmeat workflow plan <name> [--param key=val ...]` that generates and displays the execution plan | Shows batch-grouped plan matching Schema Spec Section 4.2 format; includes agent assignments, context modules, timeouts; Rich formatted | 2 pts | python-backend-engineer | CLI-4.1, SVC-3.3 |
| CLI-4.7 | `workflow run` | Implement `skillmeat workflow run <name> [--param key=val ...] [--dry-run]` that executes the workflow | Starts execution, shows progress with Rich live display, reports stage completions/failures; `--dry-run` calls plan instead; supports Ctrl+C for cancel | 3 pts | python-backend-engineer | CLI-4.1, SVC-3.4 |
| CLI-4.8 | `workflow runs` | Implement `skillmeat workflow runs [<run_id>] [--logs] [--status STATUS]` | Lists recent runs in table; with run_id shows detailed status; `--logs` shows execution logs; `--status` filters | 1 pt | python-backend-engineer | CLI-4.1 |
| CLI-4.9 | `workflow approve/cancel` | Implement `skillmeat workflow approve <run_id> <stage_id>` and `skillmeat workflow cancel <run_id>` | Approve advances past gate; cancel terminates running workflow; both confirm before action | 1 pt | python-backend-engineer | CLI-4.1, SVC-3.6 |
| CLI-4.10 | Collection Manifest Integration | Update collection manifest TOML handling to support `type = "workflow"` entries; ensure `skillmeat list` includes workflows | Manifest round-trips workflow entries; `skillmeat list --type workflow` filters correctly; `skillmeat sync` handles workflows | 1 pt | python-backend-engineer | CLI-4.2, PREP-0.5 |
| TEST-4.11 | CLI Unit Tests | Tests for all CLI commands with mocked services | All commands tested with valid and invalid inputs; error messages verified; output format verified | 2 pts | python-backend-engineer | CLI-4.10 |

**CLI Surface Summary**:

```bash
skillmeat workflow create <path>                      # Create from YAML file
skillmeat workflow list [--status S] [--tag T]        # List workflows
skillmeat workflow show <name>                        # Display workflow detail
skillmeat workflow validate <path>                    # Validate YAML file
skillmeat workflow plan <name> [--param key=val]      # Dry run: show execution plan
skillmeat workflow run <name> [--param key=val]       # Execute workflow
skillmeat workflow runs [<run_id>] [--logs]           # List/show runs
skillmeat workflow approve <run_id> <stage_id>        # Approve gate
skillmeat workflow cancel <run_id>                    # Cancel running workflow
```

**Phase 4 Quality Gates**:
- [ ] All 9 CLI subcommands functional
- [ ] `workflow create` validates before storing
- [ ] `workflow plan` output matches Schema Spec format
- [ ] `workflow run` shows live progress
- [ ] Collection manifest supports workflow entries
- [ ] `skillmeat list` includes workflows
- [ ] CLI tests passing
- [ ] Error messages are clear and actionable

---

## Phase 5: Frontend -- Workflow Library & Builder

**Duration**: 2 weeks
**Dependencies**: Phase 3 API complete (can start scaffolding during Phase 3)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

This is the largest frontend phase. It creates the Workflow Library page, the Workflow Builder with @dnd-kit drag-and-drop, and all supporting components. See the UI/UX Design Spec for detailed wireframes, component specs, and interaction patterns.

### 5.1 Foundation (Types, Hooks, Navigation)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-5.1 | TypeScript Types | Create `types/workflow.ts` with all types from UI Spec Section 6.1: `Workflow`, `WorkflowStage`, `WorkflowExecution`, `WorkflowStageExecution`, enums, role/context types | All types match backend schemas; exported from barrel; no `any` types | 1 pt | frontend-developer | API-3.14 |
| FE-5.2 | Workflow Query Hooks | Create `hooks/use-workflows.ts` with `useWorkflows`, `useWorkflow`, `useCreateWorkflow`, `useUpdateWorkflow`, `useDeleteWorkflow`, `useDuplicateWorkflow` per UI Spec Section 6.2 | All hooks connect to correct API endpoints; query keys follow standard pattern; stale time: 5min; invalidation graph correct per UI Spec Section 6.3 | 2 pts | frontend-developer | FE-5.1 |
| FE-5.3 | Execution Query Hooks | Create `hooks/use-workflow-executions.ts` with `useWorkflowExecutions`, `useWorkflowExecution`, `useRunWorkflow`, `usePauseExecution`, `useResumeExecution`, `useCancelExecution`, `useExecutionStream` per UI Spec Section 6.2 | All hooks working; execution hooks use 30s stale time (monitoring); SSE hook for real-time updates; invalidation graph correct | 2 pts | frontend-developer | FE-5.1 |
| FE-5.4 | Hook Barrel Export | Register all new hooks in `hooks/index.ts` barrel export | All hooks importable from `@/hooks` | 0.5 pt | frontend-developer | FE-5.2, FE-5.3 |
| FE-5.5 | Navigation Integration | Add "Workflows" section to sidebar navigation in `components/navigation.tsx` per UI Spec Section 2 with Library and Executions items | Navigation section visible, correct icons (Workflow or GitBranch), routes work, collapsible section | 1 pt | ui-engineer-enhanced | FE-5.1 |
| FE-5.6 | Route Structure | Create all Next.js route pages as empty shells: `/workflows/page.tsx`, `/workflows/new/page.tsx`, `/workflows/[id]/page.tsx`, `/workflows/[id]/edit/page.tsx`, `/workflows/[id]/executions/page.tsx`, `/workflows/[id]/executions/[runId]/page.tsx`, `/workflows/executions/page.tsx` | All routes accessible, render placeholder content, no 404s | 1 pt | frontend-developer | FE-5.5 |

### 5.2 Shared Components

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-5.7 | SlideOverPanel | Create `components/shared/slide-over-panel.tsx` -- reusable right-side slide-over panel with backdrop, title, close button, animated enter/exit per UI Spec Section 3.2 | Opens from right with translate animation; focus trapped inside; closes on backdrop click, Escape key, or close button; supports custom width | 2 pts | ui-engineer-enhanced | FE-5.6 |
| FE-5.8 | ArtifactPicker | Create `components/shared/artifact-picker.tsx` -- Popover-based searchable artifact selector with type filtering per UI Spec Section 5.2 | Search works with 300ms debounce; results grouped by type; single and multi-select modes; selected items shown as removable Badges; sources data from `useArtifacts` hook | 2 pts | ui-engineer-enhanced | FE-5.6 |
| FE-5.9 | ContextModulePicker | Create `components/shared/context-module-picker.tsx` -- Popover-based context module selector per UI Spec Section 5.3 | Multi-select; shows module name, description, memory count; inherited global modules shown separately; sources from `useContextModules` | 2 pts | ui-engineer-enhanced | FE-5.6 |
| FE-5.10 | InlineEdit | Create `components/shared/inline-edit.tsx` -- click-to-edit text field per UI Spec Section 4 | Click to enter edit mode; blur or Enter to save; Escape to cancel; shows current value as text when not editing | 1 pt | frontend-developer | FE-5.6 |
| FE-5.11 | StatusDot | Create `components/shared/status-dot.tsx` -- colored dot indicator with optional pulse animation per UI Spec Section 4 | Supports all ExecutionStatus values; correct colors (green/blue/red/gray/yellow); optional pulse for running state; accessible with aria-label | 0.5 pt | frontend-developer | FE-5.6 |

### 5.3 Workflow Library Page

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-5.12 | WorkflowCard | Create `components/workflow/workflow-card.tsx` per UI Spec Section 3.1 | Shows name, stage count, last run time, tags (max 3 + overflow), created by, action buttons (Run, Edit, menu); hover shadow lift; click navigates to detail | 2 pts | ui-engineer-enhanced | FE-5.2 |
| FE-5.13 | WorkflowListItem | Create `components/workflow/workflow-list-item.tsx` per UI Spec Section 3.1 | Row layout with name, metadata columns, tags, inline actions; truncation on name; hover highlight | 1 pt | frontend-developer | FE-5.12 |
| FE-5.14 | WorkflowToolbar | Create `components/workflow/workflow-toolbar.tsx` per UI Spec Section 3.1 | Search input, tag filter, sort dropdown, grid/list view toggle; URL-driven state per UI Spec Section 6.6 | 1 pt | frontend-developer | FE-5.12 |
| FE-5.15 | Workflow Library Page | Implement `app/workflows/page.tsx` with PageHeader, toolbar, card grid/list, empty state per UI Spec Section 3.1 | PageHeader with title, description, "+ New Workflow" button; grid/list toggle; search/filter/sort working; empty state when no workflows; 3-column grid on desktop, 1-column on mobile | 2 pts | ui-engineer-enhanced | FE-5.12, FE-5.13, FE-5.14 |

### 5.4 Workflow Builder Page

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-5.16 | StageCard | Create `components/workflow/stage-card.tsx` with edit and readonly modes per UI Spec Section 3.2 | Edit mode: drag handle, stage number badge, inline-editable title, agent/tools/context summary rows, edit and delete buttons; Readonly mode: no drag/edit/delete; both modes use correct styling | 2 pts | ui-engineer-enhanced | FE-5.10 |
| FE-5.17 | StageConnector | Create `components/workflow/stage-connector.tsx` per UI Spec Section 3.2 | Sequential connector: vertical line between stages; hover reveals "+" add button; parallel branch connector: split/merge visual with dashed lines | 1 pt | frontend-developer | FE-5.16 |
| FE-5.18 | StageEditor | Create `components/workflow/stage-editor.tsx` as a SlideOverPanel form per UI Spec Section 3.2 | Four sections: Basic Info (name, description, execution mode), Roles (ArtifactPicker for agent + tools), Context Policy (ContextModulePicker, inherit toggle), Advanced (timeout, retry, failure action); saves stage on Save button | 3 pts | ui-engineer-enhanced | FE-5.7, FE-5.8, FE-5.9 |
| FE-5.19 | Builder State Management | Implement `useReducer`-based builder state per UI Spec Section 6.4 with all BuilderAction types | All actions work: SET_NAME, SET_DESCRIPTION, ADD_STAGE, UPDATE_STAGE, REMOVE_STAGE, REORDER_STAGES, SELECT_STAGE, TOGGLE_EDITOR, MARK_SAVED, LOAD_WORKFLOW; isDirty tracking accurate | 2 pts | frontend-developer | FE-5.16 |
| FE-5.20 | Drag-and-Drop Integration | Integrate @dnd-kit with stage list: DndContext, SortableContext, useSortable on each StageCard per UI Spec Section 5.1 | Drag via handle lifts card with shadow; drop indicators between stages; keyboard DnD (Space to pick up, arrows to move, Space to drop); stage numbers recalculate after reorder; ARIA announcements for screen readers | 3 pts | ui-engineer-enhanced | FE-5.16, FE-5.19 |
| FE-5.21 | Builder Top Bar | Implement sticky builder header per UI Spec Section 3.2 with back button, editable workflow name, unsaved indicator, Save Draft and Save & Close buttons | Sticky below global header; inline-editable name; amber dot when dirty; Save Draft calls mutation and marks saved; Save & Close saves then navigates to detail | 1 pt | frontend-developer | FE-5.19 |
| FE-5.22 | Builder Sidebar | Implement workflow metadata panel per UI Spec Section 3.2 with name, description, tags, version, global context, execution settings | All fields editable; global context uses ContextModulePicker; settings toggles for stop-on-failure and allow-runtime-overrides; collapses on mobile | 1 pt | frontend-developer | FE-5.9, FE-5.19 |
| FE-5.23 | Builder Page Assembly | Assemble `app/workflows/new/page.tsx` and `app/workflows/[id]/edit/page.tsx` combining top bar, sidebar, canvas with stage list, connectors, and add stage button | Create page starts with empty workflow; edit page loads existing workflow; sidebar + canvas layout; add stage at bottom and between stages; unsaved changes guard (beforeunload + router intercept) | 3 pts | ui-engineer-enhanced | FE-5.16 through FE-5.22 |

### 5.5 Workflow Detail Page

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-5.24 | Workflow Detail Page | Implement `app/workflows/[id]/page.tsx` with tabs: Stages (read-only timeline), Executions (filtered list), Settings (metadata) per UI Spec Section 3.3 | PageHeader with Run/Edit/menu actions; Stages tab shows read-only stage cards in vertical timeline; Executions tab shows filtered execution list; Settings tab shows workflow metadata; artifact badges link to detail pages | 3 pts | ui-engineer-enhanced | FE-5.16, FE-5.2 |
| FE-5.25 | RunWorkflowDialog | Create `components/workflow/run-workflow-dialog.tsx` per UI Spec Section 3.3 | Dialog shows workflow name, parameter inputs (if any), optional override sections (context modules, agent overrides); Run button starts execution and navigates to dashboard | 2 pts | ui-engineer-enhanced | FE-5.3 |
| TEST-5.26 | Library & Builder Component Tests | React Testing Library tests for WorkflowCard, StageCard, StageEditor, builder state reducer, DnD interaction | All components render correctly; reducer handles all action types; DnD reorders stages; form validation works; 80%+ component test coverage | 3 pts | frontend-developer | FE-5.23 |

**Phase 5 Quality Gates**:
- [ ] Workflow Library page renders with grid/list toggle
- [ ] Search, filter, sort working via URL state
- [ ] Builder creates and saves workflows via API
- [ ] Drag-and-drop reorders stages with keyboard support
- [ ] Stage editor slide-over edits all stage properties
- [ ] ArtifactPicker and ContextModulePicker working
- [ ] Unsaved changes guard prevents accidental navigation
- [ ] Detail page shows read-only workflow with tabs
- [ ] Run dialog starts execution
- [ ] Mobile responsive (single column, collapsible sidebar)
- [ ] Component test coverage >80%
- [ ] WCAG 2.1 AA: all ARIA roles, focus management, keyboard navigation

---

## Phase 6: Frontend -- Execution Dashboard

**Duration**: 1.5 weeks
**Dependencies**: Phase 3 API (SSE endpoint), Phase 5 shared components
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

### 6.1 Execution Components

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-6.1 | StageTimeline | Create `components/workflow/stage-timeline.tsx` -- vertical timeline column per UI Spec Section 3.4 with selectable nodes | Each node shows: status circle (color + icon), stage name, status text + duration; click selects node and highlights; running stage has spinning icon; `aria-current="step"` on active stage; J/K keyboard navigation | 2 pts | ui-engineer-enhanced | FE-5.11 |
| FE-6.2 | ExecutionHeader | Create `components/workflow/execution-header.tsx` per UI Spec Section 3.4 | Shows workflow name (link), run ID, started timestamp, status badge; action buttons change by state: Running (Pause, Cancel), Paused (Resume, Cancel), Completed/Failed (Re-run) | 1 pt | frontend-developer | FE-5.11 |
| FE-6.3 | ExecutionProgress | Create `components/workflow/execution-progress.tsx` per UI Spec Section 3.4 | Progress bar using shadcn Progress; shows "N of M stages complete"; animated fill; indeterminate state when initializing | 1 pt | frontend-developer | FE-6.2 |
| FE-6.4 | ExecutionDetail | Create `components/workflow/execution-detail.tsx` -- right panel per UI Spec Section 3.4 | Shows: stage name + status badge, agent & tools (artifact badges), timing (started, duration with live counter, ended), context consumed (module list with sizes), log viewer | 2 pts | ui-engineer-enhanced | FE-6.1 |
| FE-6.5 | LogViewer | Create `components/workflow/log-viewer.tsx` per UI Spec Section 3.4 | Monospace font; auto-scrolls to bottom when live; "scroll to bottom" button when user scrolls up; error lines highlighted in red; empty state: "Waiting for logs..."; max-height with scroll; `role="log"` with `aria-live="polite"` | 2 pts | ui-engineer-enhanced | FE-6.4 |

### 6.2 Execution Pages

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-6.6 | Execution Dashboard Page | Assemble `app/workflows/[id]/executions/[runId]/page.tsx` with header, progress bar, split layout (timeline + detail) per UI Spec Section 3.4 | Split layout: timeline column (w-72) + detail panel; selecting timeline node shows detail; SSE events update timeline and detail in real-time; pause/resume/cancel controls work; mobile: stacked layout | 3 pts | ui-engineer-enhanced | FE-6.1 through FE-6.5, FE-5.3 |
| FE-6.7 | SSE Integration | Integrate `useExecutionStream` hook with dashboard state: update stage statuses, append logs, trigger completion | SSE events update UI in real-time; connection reopens on drop; falls back to 30s polling if SSE unavailable; status transitions trigger toast notifications | 2 pts | frontend-developer | FE-6.6, API-3.13 |
| FE-6.8 | Execution List Pages | Implement `/workflows/executions/page.tsx` (all executions) and `/workflows/[id]/executions/page.tsx` (filtered by workflow) | Table with columns: run ID, workflow name, status badge, started, duration, trigger; filter by status; sort by date; click navigates to dashboard | 2 pts | frontend-developer | FE-5.3 |
| FE-6.9 | Optimistic Updates | Implement optimistic UI updates per UI Spec Section 6.5: pause/resume/cancel update immediately, roll back on error | Status badge updates instantly on control actions; error triggers rollback + error toast; run button navigates immediately with "Initializing..." status | 1 pt | frontend-developer | FE-6.6 |
| TEST-6.10 | Execution Dashboard Tests | Component tests for timeline, log viewer, SSE integration, execution controls | Timeline renders all statuses correctly; log viewer auto-scrolls; SSE updates reflected in UI; controls trigger correct mutations; 80%+ coverage | 2 pts | frontend-developer | FE-6.9 |

**Phase 6 Quality Gates**:
- [ ] Execution dashboard renders with split layout
- [ ] Timeline correctly shows all stage statuses
- [ ] Clicking timeline node shows stage detail
- [ ] SSE events update dashboard in real-time
- [ ] Log viewer auto-scrolls and shows error highlights
- [ ] Pause/Resume/Cancel controls work with optimistic updates
- [ ] Execution list pages with filtering and sorting
- [ ] Mobile responsive (stacked layout)
- [ ] Component test coverage >80%
- [ ] WCAG 2.1 AA: timeline keyboard navigation, log viewer aria-live

---

## Phase 7: Integration, Testing & Documentation

**Duration**: 1 week
**Dependencies**: All previous phases complete
**Assigned Subagent(s)**: python-backend-engineer, ui-engineer-enhanced, documentation-writer

### 7.1 Bundle & Collection Integration

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| INT-7.1 | Bundle System Integration | Add workflow support to `BundleBuilder` and `BundleImporter` in `skillmeat/core/sharing/`: include WORKFLOW.yaml in bundles, import workflows from bundles | Workflows export as part of bundles; bundles import workflows and create in collection + DB; version conflict resolution follows existing patterns | 2 pts | python-backend-engineer | SVC-3.1 |
| INT-7.2 | Collection Sync | Ensure `skillmeat sync` handles workflows: detect upstream changes, pull updates, update DB cache | Sync detects new/updated/deleted workflows from upstream; DB cache refreshed after sync; no data loss on sync conflicts | 2 pts | python-backend-engineer | CLI-4.10 |
| INT-7.3 | Project Overrides | Implement `.skillmeat-workflow-overrides.yaml` file loading per Schema Spec Section 3.7; deep-merge with base workflow at plan/run time | Override file in project root detected; agents/context/parameters overridden per spec; base workflow unchanged; plan output reflects overrides | 2 pts | python-backend-engineer | SVC-3.3 |

### 7.2 Comprehensive Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TEST-7.4 | Integration Test Suite | Cross-layer integration tests: CLI create --> API validate --> API plan --> API run --> SSE events --> API cancel | All integration paths tested; data flows correctly through all layers; error scenarios tested (invalid YAML, missing artifacts, cycle detection) | 3 pts | python-backend-engineer | INT-7.3 |
| TEST-7.5 | Performance Benchmarks | Measure: list query (<300ms p95), plan generation (<1s p95), workflow parse (<200ms), SSE event latency (<500ms) | All benchmarks met on development hardware; results documented; bottlenecks identified and noted for optimization | 1 pt | python-backend-engineer | TEST-7.4 |
| TEST-7.6 | E2E Frontend Tests | Playwright tests for: Library page navigation, Builder create workflow, Builder DnD reorder, Run workflow, Execution dashboard monitoring | All user journeys pass in Playwright; screenshots captured for visual regression; mobile viewport tested | 2 pts | frontend-developer | FE-6.9 |
| TEST-7.7 | Accessibility Audit | Full WCAG 2.1 AA audit of all new pages: Library, Builder, Detail, Execution Dashboard | All pages pass automated accessibility checks (axe-core); focus management verified; screen reader tested on key flows; color independence verified | 1 pt | ui-engineer-enhanced | TEST-7.6 |

### 7.3 Documentation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DOC-7.8 | API Documentation | Verify `openapi.json` is complete and accurate for all 14+ endpoints; add usage examples | All endpoints documented with request/response examples; error responses documented; pagination examples included | 1 pt | python-backend-engineer | API-3.15 |
| DOC-7.9 | SWDL Authoring Guide | User guide: how to write workflow YAML, expression syntax, minimal and advanced examples, parameter usage, error policies | Covers all SWDL features; includes the minimal 30-line example and full SDLC example; troubleshooting section for common validation errors | 2 pts | documentation-writer | SCHEMA-1.2 |
| DOC-7.10 | CLI Command Reference | Document all `skillmeat workflow` commands with usage, options, and examples | All 9 subcommands documented; examples for each; linked from main CLI docs | 1 pt | documentation-writer | CLI-4.10 |
| DOC-7.11 | Web UI User Guide | Guide for: creating workflows in the Builder, running workflows, monitoring executions, using the Execution Dashboard | Screenshots/wireframes included; keyboard shortcuts documented; covers empty state to full workflow lifecycle | 1 pt | documentation-writer | FE-6.9 |

### 7.4 Deployment & Observability

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DEPLOY-7.12 | Feature Flag | Implement `WORKFLOW_ENGINE_ENABLED` feature flag; when disabled, workflow routes return 404 and CLI commands show "coming soon" | Feature toggleable via config; UI hides navigation section when disabled; API returns 404; CLI shows message | 1 pt | python-backend-engineer | API-3.9 |
| DEPLOY-7.13 | Observability | Add structured logging for workflow lifecycle events: created, validated, planned, started, stage_started, stage_completed, stage_failed, completed, cancelled | All lifecycle events logged with workflow_id, execution_id, stage_id; log level appropriate (INFO for lifecycle, ERROR for failures); correlatable via run_id | 1 pt | python-backend-engineer | SVC-3.5 |
| DEPLOY-7.14 | README Update | Rebuild README to include workflow features if applicable per doc policy | README reflects new workflow commands and web UI features | 0.5 pt | documentation-writer | DOC-7.10 |

**Phase 7 Quality Gates**:
- [ ] Bundle import/export works for workflows
- [ ] Collection sync handles workflows
- [ ] Project overrides deep-merge correctly
- [ ] Integration test suite passing
- [ ] Performance benchmarks met
- [ ] E2E Playwright tests passing
- [ ] WCAG 2.1 AA audit passing
- [ ] All documentation published
- [ ] Feature flag working
- [ ] Observability logging in place
- [ ] README updated

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Expression language complexity creep | High | Medium | Limit v1 to property access, comparisons, boolean operators, and 4 built-in functions. No Jinja2, no arbitrary code. Defer complex expressions to v2. |
| Agent dispatch mechanism undefined | High | High | For v1, implement a mock/pluggable dispatch interface. Actual agent invocation (via Claude CLI, SDK, or API) is a separate integration concern. The execution engine calls a `StageDispatcher` interface that can be swapped. |
| @dnd-kit learning curve delays Builder | Medium | Medium | Start with simple sortable list (no parallel branches in v1 DnD). Parallel visual is display-only based on `depends_on` analysis, not manual drag into branches. |
| SSE reliability in production | Medium | Medium | Implement polling fallback (30s interval) alongside SSE. SSE reconnects automatically with exponential backoff. Dashboard functional with polling alone. |
| Parallel execution resource exhaustion | High | Medium | v1 limits max concurrent stages to 3 (configurable). Execution engine queues excess stages. Document limitation. |
| SWDL schema changes during implementation | Medium | Low | Schema Spec is draft; freeze schema at Phase 1 completion. Any post-freeze changes require migration plan. |
| Database migration conflicts with memory system | Medium | Low | Memory system migration chain is established. New migration extends the chain. Test forward/backward migration before merging. |
| Frontend page count (7 new routes) | High | Medium | Reuse existing patterns aggressively (PageHeader, TabNavigation, card grid, URL state). Shared components (SlideOverPanel, ArtifactPicker) amortize across pages. |
| Workflow execution state consistency | High | Medium | Use database transactions for all state changes. Execution engine uses optimistic locking. Crash recovery: resume from last committed batch on restart. |
| Gate approval UX unclear | Medium | Low | v1: gates pause execution and require explicit API/CLI call to approve. Web UI shows prominent "Approve" button on gate stages in Execution Dashboard. Email/Slack notifications deferred to v2. |

---

## Resource Requirements

### Team Composition (Subagent Allocation)

- **Backend Architect (Opus)**: Phases 1, 3 -- schema design, expression engine, execution engine, context integration
- **Python Backend Engineer (Opus)**: Phases 0-4, 7 -- repositories, services, API routers, CLI, tests, integration
- **Data Layer Expert (Opus)**: Phase 2 -- migration, ORM models, indexes, transaction handling
- **UI Engineer Enhanced (Opus)**: Phases 5-6 -- Builder, Dashboard, shared components, accessibility
- **Frontend Developer (Opus/Sonnet)**: Phases 5-6 -- types, hooks, library page, list items, tests, SSE integration
- **Documentation Writer (Sonnet)**: Phase 7 -- user guides, CLI reference, SWDL authoring guide
- **Lead Architect (Opus)**: Phase 0 -- pattern review, feature branch setup, collection integration

### Skill Requirements

- Python/FastAPI, SQLAlchemy, Alembic, Click CLI, Pydantic v2
- TypeScript/React, Next.js 15 App Router, TanStack React Query, @dnd-kit
- Radix UI, shadcn/ui, Tailwind CSS
- Server-Sent Events (SSE), Rich (Python terminal formatting)
- DAG algorithms (topological sort, cycle detection)
- Expression parsing (recursive descent or PEG)
- YAML parsing (PyYAML/ruamel.yaml)
- Testing: pytest, Jest, React Testing Library, Playwright

---

## Parallel Work Tracks

### Track A: Core Engine (Phases 1-2, partial overlap)

```
PREP-0.1..0.5 --> SCHEMA-1.1 --> SCHEMA-1.2,1.3 (parallel) --> EXPR-1.4,1.5,1.6 (parallel) --> DAG-1.7..1.10
                                      |
                                      +--> DB-2.1 --> DB-2.2 --> DB-2.3 --> REPO-2.4..2.7 --> TEST-2.8
```

### Track B: Service + API (Phase 3, after A completes)

```
SVC-3.1 --> SVC-3.2,3.3 (parallel) --> SVC-3.4 --> SVC-3.5 --> SVC-3.6,3.7,3.8 (parallel)
                                                                       |
API-3.9 --> API-3.10 --> API-3.11 --> API-3.12 --> API-3.13 --> API-3.14,3.15 --> TEST-3.16,3.17
```

### Track C: CLI (Phase 4, after Phase 3 API)

```
CLI-4.1 --> CLI-4.2..4.10 (partially parallel: create/list/show independent, run depends on plan) --> TEST-4.11
```

### Track D: Frontend Library + Builder (Phase 5, after Phase 3 API)

```
FE-5.1..5.6 (foundation, parallel) --> FE-5.7..5.11 (shared components, parallel) -->
  FE-5.12..5.15 (library, parallel) || FE-5.16..5.23 (builder, sequential with dependencies) -->
  FE-5.24,5.25 (detail page) --> TEST-5.26
```

### Track E: Frontend Execution (Phase 6, after Phase 5 + Phase 3 SSE)

```
FE-6.1..6.5 (components, parallel) --> FE-6.6 (dashboard) --> FE-6.7,6.8,6.9 (integration) --> TEST-6.10
```

### Track F: Integration + Docs (Phase 7, after all)

```
INT-7.1,7.2,7.3 (parallel) --> TEST-7.4,7.5,7.6,7.7 (parallel) --> DOC-7.8..7.11 (parallel) --> DEPLOY-7.12..7.14
```

Tracks C and D run in parallel. Tracks D and E have a dependency (shared components).

---

## Story Point Summary

| Phase | Phase Name | Tasks | Story Points |
|-------|-----------|-------|-------------|
| 0 | Prerequisites & Foundation | 5 | 4 pts |
| 1 | Schema & Core Logic (SWDL Engine) | 13 | 23 pts |
| 2 | Database + Repository Layer | 8 | 15 pts |
| 3 | Service + API Layer | 17 | 36 pts |
| 4 | CLI Commands | 11 | 16 pts |
| 5 | Frontend -- Workflow Library & Builder | 26 | 40.5 pts |
| 6 | Frontend -- Execution Dashboard | 10 | 18 pts |
| 7 | Integration, Testing & Documentation | 14 | 18.5 pts |
| **Total** | | **104 tasks** | **171 pts** |

**Adjusted Estimate** (accounting for parallel execution and overlap):
- Phases 1+2 overlap: ~1.5 weeks effective (not 2 weeks)
- Phases 4+5 overlap: ~2 weeks effective (not 3 weeks)
- Effective timeline: **~9-10 weeks**
- Effective story points on critical path: **~72 pts** (excluding tasks that run in parallel off the critical path)

---

## Definition of Done (Phase-by-Phase)

### Phase 0 Done
- Feature branch created and pushed
- `ArtifactType.WORKFLOW` in enum with detection
- `@dnd-kit` installed, building
- Collection supports workflow directories
- Pattern review complete

### Phase 1 Done
- SWDL Pydantic models parse all Schema Spec examples
- Expression parser handles all v1 namespaces and operators
- Static validation catches invalid references
- DAG builds correctly, detects cycles
- Parallel batch computation correct
- Execution plan generator produces readable output
- Test coverage >85% on core/workflow/

### Phase 2 Done
- Migration tested forward and backward
- All 4 ORM models with relationships
- All 3 repositories with CRUD + pagination
- Transaction handling prevents partial writes
- Test coverage >85% on repository layer

### Phase 3 Done
- All services tested (80%+ coverage)
- All 14+ API endpoints working
- SSE streaming functional
- Execution engine processes sequential + parallel
- Retry, timeout, error policies working
- Gate stages pause/resume correctly
- Context injection working via ContextPackerService
- OpenAPI documentation complete
- Integration + E2E tests passing

### Phase 4 Done
- All 9 CLI subcommands functional
- Live progress display during `workflow run`
- Collection manifest supports workflows
- CLI tests passing

### Phase 5 Done
- Library page with grid/list, search/filter/sort
- Builder creates and saves workflows
- DnD reorders stages with keyboard support
- Stage editor edits all properties
- Detail page with tabs
- Run dialog functional
- Mobile responsive
- Component tests >80%
- WCAG 2.1 AA

### Phase 6 Done
- Execution dashboard with split layout
- Timeline + detail panel working
- SSE real-time updates
- Log viewer with auto-scroll
- Controls with optimistic updates
- Execution list pages
- Mobile responsive
- Component tests >80%
- WCAG 2.1 AA

### Phase 7 Done
- Bundle and collection sync working
- Project overrides functional
- Integration test suite passing
- Performance benchmarks met
- E2E Playwright tests passing
- Accessibility audit passing
- All documentation published
- Feature flag working
- Observability logging active

---

## Critical Success Metrics

### Delivery Metrics
- On-time delivery (within 10% of 9-10 weeks)
- Backend service code coverage >80%
- Frontend component test coverage >80%
- Zero P0/P1 bugs in first week post-launch

### Technical Metrics
- API list query <300ms p95
- Workflow plan generation <1s p95
- SWDL parse + validate <200ms
- SSE event latency <500ms
- 100% API documentation
- 100% WCAG 2.1 AA compliance
- Zero SQL injection vulnerabilities
- Alembic migrations tested forward/backward

### Functional Metrics
- SWDL parser handles 100% of v1 schema features
- Expression engine evaluates all v1 namespaces and operators
- DAG correctly handles sequential, parallel, diamond, and conditional patterns
- Execution engine supports retry, timeout, error policies, and gates
- Builder supports create, edit, DnD reorder, and all stage properties
- Execution Dashboard shows real-time updates via SSE

---

## Open Questions (Resolved and Deferred)

### Resolved for v1

| Question | Resolution |
|----------|-----------|
| Agent dispatch mechanism | Pluggable `StageDispatcher` interface. v1 uses mock dispatcher for development; real dispatch (Claude CLI/SDK) is a separate integration task. |
| Concurrency limits | v1: max 3 concurrent stages (configurable). Excess stages queued. |
| State persistence granularity | DB-native (SQLite). No filesystem run state in v1. Export to YAML/JSON is a CLI command. |
| Workflow versioning | Snapshot semantics: execution locks workflow version at start time. |

### Deferred to v2

| Question | Rationale |
|----------|-----------|
| Cross-workflow composition | Significant complexity; not needed for v1 value proposition. |
| Cost controls (token budgets) | Requires integration with billing/metering; defer until dispatch is real. |
| Dynamic fan-out stages | Schema reserved (`type: "fan_out"`); engine support deferred. |
| Dynamic role selection | Fixed roles in v1; project overrides cover most use cases. |
| Saga/compensating actions | Complex rollback logic; `on_failure: halt` sufficient for v1. |
| Matrix strategy | Fan-out/fan-in sufficient via explicit parallel stages in v1. |

---

## Post-Implementation Roadmap

### v1.1 (4-6 weeks after v1)
- Real agent dispatch integration (Claude CLI/SDK)
- Email/Slack notifications for gate approvals and failures
- Workflow template marketplace (curated starter workflows)
- Run history analytics (success rate, avg duration, cost tracking)

### v2.0 (8-12 weeks after v1)
- Dynamic fan-out stages
- Cross-workflow composition (sub-workflows)
- Saga/compensating actions for rollback
- Cost controls and token budget enforcement
- Advanced expression functions
- Workflow diff viewer (version comparison)

---

**Progress Tracking:**

See `.claude/progress/workflow-orchestration-v1/` for real-time phase-by-phase task status.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-06
**Total Story Points**: 72 pts (critical path) / 171 pts (all tasks including parallel)
**Target Velocity**: ~8 pts/week on critical path --> 9-10 weeks
