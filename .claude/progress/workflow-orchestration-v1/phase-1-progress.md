---
type: progress
prd: workflow-orchestration-v1
phase: 1
title: Schema & Core Logic (SWDL Engine)
status: pending
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 13
completed_tasks: 10
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- backend-architect
contributors: []
tasks:
- id: SCHEMA-1.1
  description: Pydantic v2 models for SWDL in core/workflow/models.py (WorkflowDefinition,
    StageDefinition, RoleAssignment, etc.)
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - PREP-0.4
  estimated_effort: 3 pts
  priority: critical
- id: SCHEMA-1.2
  description: 'YAML/JSON parser: parse_workflow(path) -> WorkflowDefinition'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SCHEMA-1.1
  estimated_effort: 2 pts
  priority: critical
- id: SCHEMA-1.3
  description: Schema defaults application per Schema Spec Section 8
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SCHEMA-1.1
  estimated_effort: 1 pt
  priority: high
- id: EXPR-1.4
  description: Expression parser for ${{ }} syntax in core/workflow/expressions.py
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SCHEMA-1.1
  estimated_effort: 3 pts
  priority: critical
- id: EXPR-1.5
  description: 'Built-in functions: length(), contains(), toJSON(), fromJSON()'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - EXPR-1.4
  estimated_effort: 1 pt
  priority: high
- id: EXPR-1.6
  description: Static expression validation (reference checking against depends_on
    and output contracts)
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - EXPR-1.4
  - SCHEMA-1.1
  estimated_effort: 2 pts
  priority: critical
- id: DAG-1.7
  description: 'Dependency graph builder: build_dag(workflow) -> DAG in core/workflow/dag.py'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SCHEMA-1.1
  estimated_effort: 2 pts
  priority: critical
- id: DAG-1.8
  description: Cycle detection with WorkflowCycleError and descriptive cycle path
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DAG-1.7
  estimated_effort: 1 pt
  priority: critical
- id: DAG-1.9
  description: Parallel batch computation via topological sort
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - DAG-1.7
  estimated_effort: 2 pts
  priority: critical
- id: DAG-1.10
  description: 'Execution plan generator: generate_plan(workflow, parameters) -> ExecutionPlan'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - DAG-1.9
  - EXPR-1.4
  estimated_effort: 2 pts
  priority: critical
- id: TEST-1.11
  description: Parser unit tests (YAML/JSON, defaults, validation errors, all Schema
    Spec examples)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SCHEMA-1.2
  - SCHEMA-1.3
  estimated_effort: 2 pts
  priority: high
- id: TEST-1.12
  description: Expression unit tests (parsing, evaluation, static validation, built-in
    functions)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - EXPR-1.5
  - EXPR-1.6
  estimated_effort: 2 pts
  priority: high
- id: TEST-1.13
  description: DAG unit tests (construction, cycle detection, batch computation, plan
    generation)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DAG-1.10
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - SCHEMA-1.1
  batch_2:
  - SCHEMA-1.2
  - SCHEMA-1.3
  - EXPR-1.4
  - DAG-1.7
  batch_3:
  - EXPR-1.5
  - EXPR-1.6
  - DAG-1.8
  - DAG-1.9
  batch_4:
  - DAG-1.10
  batch_5:
  - TEST-1.11
  - TEST-1.12
  - TEST-1.13
  critical_path:
  - SCHEMA-1.1
  - EXPR-1.4
  - DAG-1.9
  - DAG-1.10
  - TEST-1.13
  estimated_total_time: 5-7 days
blockers: []
success_criteria:
- id: SC-1.1
  description: Full SWDL schema parsed from YAML and JSON
  status: pending
- id: SC-1.2
  description: Expression language supports all v1 namespaces and operators
  status: pending
- id: SC-1.3
  description: Static validation catches reference errors at plan time
  status: pending
- id: SC-1.4
  description: DAG cycle detection working
  status: pending
- id: SC-1.5
  description: Parallel batch computation correct for all patterns
  status: pending
- id: SC-1.6
  description: Test coverage >85% on core/workflow/
  status: pending
files_modified:
- skillmeat/core/workflow/__init__.py
- skillmeat/core/workflow/models.py
- skillmeat/core/workflow/parser.py
- skillmeat/core/workflow/expressions.py
- skillmeat/core/workflow/dag.py
- tests/test_workflow_parser.py
- tests/test_workflow_expressions.py
- tests/test_workflow_dag.py
schema_version: 2
doc_type: progress
feature_slug: workflow-orchestration-v1
progress: 76
updated: '2026-02-27'
---

# workflow-orchestration-v1 - Phase 1: Schema & Core Logic (SWDL Engine)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/workflow-orchestration-v1/phase-1-progress.md \
  --updates "SCHEMA-1.1:completed,SCHEMA-1.2:completed"
```

---

## Objective

Implement the SkillMeat Workflow Definition Language (SWDL) engine: Pydantic models for the schema, YAML/JSON parser, `${{ }}` expression language, and DAG computation with topological sort for parallel batch execution planning.

---

## Implementation Notes

### Key References
- Schema Spec: `docs/project_plans/specs/workflow-orchestration-schema-spec.md`
- Section 3: Top-level schema structure
- Section 3.4: Stage schema
- Section 3.6: Expression language
- Section 6: Full SDLC example (validation target)
- Section 7: Minimal example (validation target)
- Section 8: Default values table

### Expression Language Scope (v1)
- Property access: `parameters.name`, `stages.X.outputs.Y`, `stages.X.status`
- Comparisons: `==`, `!=`
- Boolean: `&&`, `||`, `!`
- Built-in functions: `length()`, `contains()`, `toJSON()`, `fromJSON()`
- NO: Jinja2, arbitrary code, loops, variable assignment
