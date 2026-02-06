---
title: "Workflow Orchestration Engine: Schema Specification"
description: "Detailed schema specification for multi-stage agent workflow definitions, informed by industry standards analysis."
audience: [architects, developers]
tags: [spec, workflow, orchestration, schema, architecture]
created: 2026-02-06
updated: 2026-02-06
category: "architecture"
status: draft
related:
  - /docs/project_plans/PRDs/features/workflow-orchestration-v1.md
  - /docs/project_plans/PRDs/features/memory-context-system-v1.md
  - /skillmeat/core/artifact.py
  - /skillmeat/core/artifact_detection.py
---

# Workflow Orchestration Engine: Schema Specification

**Version:** 1.0
**Date:** 2026-02-06
**Status:** Draft (Research & Design)

---

## 1. Industry Standards Analysis

This section surveys six workflow/pipeline schema standards to extract reusable design patterns for the SkillMeat Workflow Orchestration Engine.

### 1.1 GitHub Actions

**Schema structure:** YAML-based. A workflow file defines `on` (triggers), `env` (global environment), `jobs` (a map of job IDs to job definitions). Each job contains `runs-on`, `needs` (dependencies), `strategy` (matrix), `steps` (ordered list), and `outputs`.

**Key concepts extracted:**

| Concept | GitHub Actions Approach | Relevance to SkillMeat |
|---------|------------------------|----------------------|
| **Stage definition** | `jobs.<id>` with `steps[]` list | Direct analog: stages with ordered steps |
| **Dependencies** | `jobs.<id>.needs: [job_a, job_b]` | Explicit DAG via `depends_on` array |
| **Input/Output flow** | `jobs.<id>.outputs.<name>` + `${{ needs.job_a.outputs.name }}` | Expression-based output references |
| **Parallelism** | Jobs without `needs` run in parallel; `strategy.matrix` for fan-out | Implicit parallel via missing dependencies |
| **Error handling** | `continue-on-error: true`, `if: failure()`, per-step `timeout-minutes` | Per-stage error policies |
| **Environment** | `env` at workflow/job/step level (cascading) | Hierarchical context scoping |
| **Conditionals** | `if: ${{ expression }}` on jobs and steps | Conditional stage execution |

**Strengths:** Human-readable YAML; expression language for inter-job data flow; implicit parallelism through dependency omission; matrix strategy for fan-out.

**Weaknesses:** No built-in retry with backoff (requires marketplace actions); limited error recovery patterns; no native concept of "roles" or agent assignment.

### 1.2 Temporal.io

**Schema structure:** Programmatic (Go/TypeScript/Python SDKs). Workflows are code that calls Activities (units of work). The Temporal server persists workflow state, handles retries, and manages timeouts.

**Key concepts extracted:**

| Concept | Temporal Approach | Relevance to SkillMeat |
|---------|-------------------|----------------------|
| **Stage definition** | Activities (functions) called from workflow code | Stages as declarative activity definitions |
| **Dependencies** | Implicit via code flow (await activity_a; then activity_b) | Sequential by default, parallel via Promise.all |
| **Input/Output flow** | Function arguments and return values, typed | Typed input/output contracts per stage |
| **Parallelism** | `Promise.all([activityA(), activityB()])` | Explicit parallel groups |
| **Error handling** | RetryPolicy per activity: initial_interval, backoff_coefficient, max_attempts, non_retryable_error_types | Rich retry policies with error classification |
| **Timeouts** | schedule_to_close, start_to_close, schedule_to_start, heartbeat | Multiple timeout dimensions |
| **Signals/Queries** | External input to running workflows | Human-in-the-loop approval gates |
| **Saga pattern** | Compensating activities on failure | Rollback/cleanup on stage failure |

**Strengths:** Best-in-class retry and timeout model; durable execution (survives crashes); saga compensation pattern; heartbeating for long-running tasks.

**Weaknesses:** Programmatic (not declarative); steep learning curve; server dependency; no native concept of "roles."

### 1.3 Prefect

**Schema structure:** Python decorators (`@flow`, `@task`). Flows contain tasks with explicit dependency via return value passing. Prefect infers the DAG from data dependencies.

**Key concepts extracted:**

| Concept | Prefect Approach | Relevance to SkillMeat |
|---------|------------------|----------------------|
| **Stage definition** | `@task` decorated functions within `@flow` | Declarative task definitions |
| **Dependencies** | Implicit via data flow (task_b receives output of task_a) | Data-driven dependency inference |
| **Input/Output flow** | Python function args/returns with type hints | Typed contracts, JSON-serializable |
| **Parallelism** | `.submit()` for concurrent tasks, `.map()` for fan-out | Explicit submission model |
| **Error handling** | `retries`, `retry_delay_seconds`, `retry_condition_fn` per task | Per-task retry with conditional logic |
| **Caching** | `cache_key_fn`, `cache_expiration` | Result caching between runs |
| **Parameters** | `Parameter("name", default=value)` | Runtime parameterization |
| **State hooks** | `on_failure`, `on_completion`, `on_cancellation` | Lifecycle callbacks |

**Strengths:** Elegant data-flow-driven dependencies; result caching; clean parameter system; state hooks for observability. The `@task` decorator pattern maps well to declarative stage definitions.

**Weaknesses:** Python-only; DAG inference can be opaque; no built-in concept of roles or agent assignment.

### 1.4 n8n

**Schema structure:** JSON-based workflow definitions. A workflow is an array of `nodes` (each with a type, parameters, position) and `connections` (mapping source node outputs to destination node inputs by index).

**Key concepts extracted:**

| Concept | n8n Approach | Relevance to SkillMeat |
|---------|--------------|----------------------|
| **Stage definition** | `nodes[]` with `type`, `parameters`, `position` | Visual-first node definitions |
| **Dependencies** | `connections` object: `{ "NodeA": { "main": [[{ "node": "NodeB", "type": "main", "index": 0 }]] } }` | Explicit connection graph |
| **Input/Output flow** | Nodes receive items from connected inputs; output items to connected outputs | Item-based data passing |
| **Parallelism** | Fan-out via multiple output connections; SplitInBatches node | Explicit split/merge nodes |
| **Error handling** | Error output (separate output index); onError: "continueRegularOutput" / "continueErrorOutput" / "stopWorkflow" | Per-node error routing |
| **Credentials** | `credentials` object per node, referencing stored credential IDs | Credential binding per node |
| **Visual metadata** | `position: [x, y]`, `notes`, `color` | UI layout metadata alongside logic |

**Strengths:** Visual-first design with JSON serialization; error output routing (distinct from success path); credential management; strong UI/JSON round-trip fidelity.

**Weaknesses:** Node type coupling (each node is a specific integration); verbose connection format; limited retry support; no native agent/role concept.

### 1.5 Claude Code Team/Task System

**Schema structure:** Imperative API calls: `TeamCreate` (defines team members with roles and instructions), `TaskCreate` (assigns work to team members), `SendMessage` (inter-agent communication).

**Key concepts extracted:**

| Concept | Claude Code Approach | Relevance to SkillMeat |
|---------|----------------------|----------------------|
| **Stage definition** | Tasks created imperatively, assigned to team members | Direct analog: stages assigned to agents |
| **Role assignment** | `TeamCreate` with `members: [{ role, instructions }]` | First-class role definitions |
| **Dependencies** | Implicit via message ordering and task sequencing | Sequential by default |
| **Input/Output flow** | `SendMessage` passes context between agents | Message-based context handoff |
| **Parallelism** | Multiple `TaskCreate` calls in a single turn | Parallel by launching multiple tasks |
| **Context binding** | `instructions` field per team member; context via messages | Per-agent instruction binding |
| **Agent specialization** | Different models/instructions per role | Model selection per role |

**Strengths:** Native agent/role concept; instruction-based context binding; model selection per agent; aligns perfectly with SkillMeat's agent-centric worldview.

**Weaknesses:** Imperative (not declarative); no retry/error handling semantics; no formal input/output contracts; no persistence or durability.

### 1.6 Dagster

**Schema structure:** Python decorators (`@op`, `@job`, `@graph`). Ops are units of computation with typed `In`/`Out` definitions. Graphs compose ops into DAGs. Jobs are executable instances of graphs with `config` and `resources`.

**Key concepts extracted:**

| Concept | Dagster Approach | Relevance to SkillMeat |
|---------|------------------|----------------------|
| **Stage definition** | `@op` with `ins: {"input_name": In(dagster_type)}` and `out: {"output_name": Out(dagster_type)}` | Explicitly typed I/O contracts |
| **Dependencies** | Graph composition: `op_b(op_a())` | Data-flow DAG |
| **Input/Output flow** | Typed `In`/`Out` with DagsterType validation | Schema-validated I/O |
| **Parallelism** | Dynamic outputs + `DynamicOut` for fan-out/fan-in | Dynamic parallelism |
| **Error handling** | `RetryPolicy(max_retries, delay)`, `@op(retry_policy=...)` | Per-op retry policies |
| **Resources** | `@resource` injected into ops via config | Dependency injection for external services |
| **Config** | `@op(config_schema={"key": Field(str)})` | Typed runtime configuration |
| **IO Managers** | Pluggable I/O serialization (filesystem, S3, database) | Customizable state persistence |
| **Tags/Metadata** | `@op(tags={"priority": "high"})` | Metadata annotations on ops |

**Strengths:** Best-in-class typed I/O contracts; resource injection pattern; IO managers for state persistence; clean separation of graph structure from runtime config; metadata/tags for scheduling.

**Weaknesses:** Python-only; heavy framework; over-engineered for simple workflows; no native agent concept.

---

## 2. Cross-Cutting Pattern Synthesis

From the six systems above, the following universal patterns emerge:

### 2.1 Stage/Step Definition Patterns

| Pattern | Used By | Adoption Decision |
|---------|---------|-------------------|
| Declarative stage list (YAML/JSON) | GitHub Actions, n8n | **Adopt** -- human-readable, serializable |
| Typed input/output contracts | Dagster, Temporal, Prefect | **Adopt** -- prevents runtime mismatches |
| Role/agent assignment per stage | Claude Code Teams | **Adopt** -- core differentiator |
| Visual position metadata | n8n | **Adopt** -- needed for Web UI composer |

### 2.2 Dependency Patterns

| Pattern | Used By | Adoption Decision |
|---------|---------|-------------------|
| Explicit `depends_on` / `needs` array | GitHub Actions | **Adopt** -- clear, unambiguous |
| Implicit via data flow | Prefect, Dagster | **Defer** -- requires runtime inference |
| Connection graph (source -> target) | n8n | **Adapt** -- useful for visual editor serialization |

### 2.3 Parallelism Patterns

| Pattern | Used By | Adoption Decision |
|---------|---------|-------------------|
| Implicit (no dependency = parallel) | GitHub Actions | **Adopt** -- zero-config parallelism |
| Explicit parallel groups | Temporal | **Adopt** -- `parallel_group` for clarity |
| Matrix/fan-out | GitHub Actions, Dagster | **Defer** -- v2 feature |

### 2.4 Error Handling Patterns

| Pattern | Used By | Adoption Decision |
|---------|---------|-------------------|
| RetryPolicy (max_attempts, backoff, interval) | Temporal, Dagster, Prefect | **Adopt** -- essential for flaky agent tasks |
| Error output routing | n8n | **Adapt** -- `on_failure` stage routing |
| Compensating actions (saga) | Temporal | **Defer** -- v2 feature |
| `continue-on-error` flag | GitHub Actions | **Adopt** -- simple and useful |
| Non-retryable error types | Temporal | **Adopt** -- prevent retrying fatal errors |

### 2.5 Context/Environment Patterns

| Pattern | Used By | Adoption Decision |
|---------|---------|-------------------|
| Hierarchical env (workflow > job > step) | GitHub Actions | **Adopt** -- natural scoping |
| Resource injection | Dagster | **Adapt** -- bind as SkillMeat context modules |
| Credential binding | n8n | **Adapt** -- bind as SkillMeat secrets |
| Per-agent instructions | Claude Code Teams | **Adopt** -- core requirement |

---

## 3. Proposed Schema: SkillMeat Workflow Definition Language (SWDL)

### 3.1 Design Principles

1. **Declarative-first, YAML-native.** Workflows are human-readable YAML files with optional JSON serialization.
2. **Agent-centric.** Stages assign roles to SkillMeat artifacts (agents, skills), not generic compute nodes.
3. **Contract-driven.** Every stage declares typed inputs and outputs. The engine validates the DAG at plan time.
4. **Context-integrated.** Stages bind SkillMeat Context Modules (from the Memory & Context system) directly.
5. **Progressive complexity.** A minimal workflow is 10 lines. Advanced features (retries, conditionals, fan-out) layer on without breaking simple cases.
6. **Round-trip fidelity.** The YAML representation losslessly serializes to/from the Web UI visual composer.

### 3.2 File Convention

Workflow artifacts live in the collection under:
```
~/.skillmeat/collection/artifacts/workflows/<workflow-name>/
  WORKFLOW.yaml       # Canonical workflow definition
  WORKFLOW.md         # Optional: human documentation
  overrides/          # Optional: project-level override templates
```

File extension: `.yaml` (preferred) or `.json`.

### 3.3 Top-Level Schema

```yaml
# ---- Workflow Metadata ----
workflow:
  id: "sdlc-feature-ship"            # Unique identifier (kebab-case)
  name: "Ship a Feature (SDLC)"      # Human-readable display name
  version: "1.0.0"                    # SemVer
  description: >
    End-to-end workflow for shipping a feature: research, plan,
    implement, review, and deploy.
  author: "miethe"
  tags: ["sdlc", "feature", "full-stack"]

  # Optional: metadata for the visual composer
  ui:
    color: "#4A90D9"
    icon: "rocket"

# ---- Global Configuration ----
config:
  # Runtime parameters (overridable at execution time)
  parameters:
    feature_name:
      type: string
      required: true
      description: "Name of the feature to ship"
    target_branch:
      type: string
      default: "main"
      description: "Branch to target for the PR"
    skip_review:
      type: boolean
      default: false
      description: "Skip the review stage (for hotfixes)"

  # Global timeout for the entire workflow
  timeout: "4h"

  # Global environment variables (available to all stages)
  env:
    PROJECT_ROOT: "${{ parameters.feature_name }}"

# ---- Context Binding ----
context:
  # SkillMeat Context Modules injected globally
  global_modules:
    - "ctx:repo-rules"
    - "ctx:coding-standards"

  # Memory query: auto-inject relevant memories from the Memory system
  memory:
    project_scope: "current"          # "current" | specific project ID
    min_confidence: 0.7               # Only inject memories above threshold
    categories: ["constraint", "pattern", "decision"]
    max_tokens: 2000                  # Token budget for memory injection

# ---- Stage Definitions ----
stages:
  - id: "research"
    # ... (see Stage Schema below)
  - id: "plan"
    # ...
  - id: "implement"
    # ...
  - id: "review"
    # ...
  - id: "deploy"
    # ...

# ---- Error Handling (Global Defaults) ----
error_policy:
  default_retry:
    max_attempts: 2
    initial_interval: "30s"
    backoff_multiplier: 2.0
    max_interval: "5m"
  on_stage_failure: "halt"            # "halt" | "continue" | "rollback"

# ---- Hooks (Lifecycle Callbacks) ----
hooks:
  on_start:
    notify: "slack:#deployments"
  on_complete:
    notify: "slack:#deployments"
    run: "skillmeat memory capture --workflow-run ${{ run.id }}"
  on_failure:
    notify: "slack:#alerts"
```

### 3.4 Stage Schema

Each stage is a unit of work assigned to an agent role.

```yaml
stages:
  - id: "research"                    # Unique within this workflow (kebab-case)
    name: "Research & Discovery"      # Human-readable
    description: "Investigate the problem space, existing solutions, and constraints."

    # ---- Dependency Declaration ----
    depends_on: []                    # No dependencies = eligible for parallel execution

    # ---- Conditional Execution ----
    condition: null                   # null = always run
    # Examples:
    #   condition: "${{ parameters.skip_review == false }}"
    #   condition: "${{ stages.research.outputs.needs_review == true }}"

    # ---- Role Assignment ----
    roles:
      primary:                        # The main agent executing this stage
        artifact: "agent:researcher-v1"         # SkillMeat artifact reference
        model: "opus"                           # Model preference (optional)
        instructions: >                         # Stage-specific instructions appended to agent
          Focus on identifying prior art, constraints, and risks.
          Do not write code. Produce a research summary.

      tools:                          # Supporting skills/MCPs available to the primary agent
        - "skill:web-search"
        - "skill:codebase-explorer"
        - "mcp:github-api"

    # ---- Input Contract ----
    inputs:
      feature_name:
        type: string
        source: "${{ parameters.feature_name }}"
        required: true
      codebase_context:
        type: object
        source: "${{ context.repo_structure }}"
        required: false

    # ---- Output Contract ----
    outputs:
      research_summary:
        type: string
        description: "Markdown summary of research findings"
        required: true
      identified_risks:
        type: "array<string>"
        description: "List of identified risks and constraints"
        required: true
      needs_review:
        type: boolean
        description: "Whether the findings warrant external review"
        required: false
        default: true

    # ---- Context Binding (Stage-Specific) ----
    context:
      modules:
        - "ctx:domain-knowledge"
        - "ctx:competitor-analysis"
      memory:
        categories: ["constraint", "decision"]
        max_tokens: 1000

    # ---- Error Policy (Stage-Level Override) ----
    error_policy:
      retry:
        max_attempts: 3
        initial_interval: "1m"
        backoff_multiplier: 2.0
        non_retryable_errors: ["auth_failure", "rate_limit_exhausted"]
      on_failure: "halt"              # "halt" | "continue" | "skip_dependents"
      timeout: "30m"

    # ---- Handoff Configuration ----
    handoff:
      format: "structured"            # "structured" | "markdown" | "raw"
      include_run_log: false           # Whether to pass execution log to next stage
      summary_prompt: >               # Optional: prompt to summarize outputs for next stage
        Summarize the research findings in 3-5 bullet points for the planning stage.

    # ---- Visual Metadata (for Web UI Composer) ----
    ui:
      position: [100, 200]
      color: "#E8F5E9"
      icon: "search"
```

### 3.5 Advanced Stage Patterns

#### 3.5.1 Parallel Group

Stages without `depends_on` entries pointing at each other run in parallel automatically (GitHub Actions pattern). For explicit parallel grouping with a shared join point:

```yaml
stages:
  - id: "frontend-impl"
    depends_on: ["plan"]
    roles:
      primary:
        artifact: "agent:ui-engineer-v2"
    # ...

  - id: "backend-impl"
    depends_on: ["plan"]
    roles:
      primary:
        artifact: "agent:python-backend-v2"
    # ...

  - id: "integration-test"
    depends_on: ["frontend-impl", "backend-impl"]   # Fan-in: waits for both
    roles:
      primary:
        artifact: "agent:test-engineer-v1"
    # ...
```

The engine infers that `frontend-impl` and `backend-impl` can run in parallel because they share the same dependency (`plan`) and do not depend on each other.

#### 3.5.2 Conditional Stages

```yaml
  - id: "security-review"
    depends_on: ["implement"]
    condition: "${{ stages.implement.outputs.touches_auth == true }}"
    roles:
      primary:
        artifact: "agent:security-reviewer-v1"
```

#### 3.5.3 Approval Gates (Human-in-the-Loop)

```yaml
  - id: "deploy-approval"
    depends_on: ["review"]
    type: "gate"                      # Special stage type
    gate:
      kind: "manual_approval"
      approvers: ["miethe"]
      timeout: "24h"
      on_timeout: "halt"              # "halt" | "auto_approve" | "reject"
      message: "Review complete. Approve deployment to production?"
```

#### 3.5.4 Dynamic Fan-Out (v2)

Reserved for future implementation. Allows a stage to dynamically spawn N parallel sub-stages based on runtime data.

```yaml
  - id: "test-matrix"
    depends_on: ["implement"]
    type: "fan_out"
    fan_out:
      source: "${{ stages.implement.outputs.test_suites }}"
      stage_template:
        roles:
          primary:
            artifact: "agent:test-runner-v1"
        inputs:
          test_suite:
            type: string
            source: "${{ item }}"
    # Results collected in stages.test-matrix.outputs (array)
```

### 3.6 Expression Language

The schema uses a minimal expression language for inter-stage references and conditionals, inspired by GitHub Actions.

**Syntax:** `${{ <expression> }}`

**Available namespaces:**

| Namespace | Description | Examples |
|-----------|-------------|---------|
| `parameters` | Workflow runtime parameters | `${{ parameters.feature_name }}` |
| `stages.<id>.outputs` | Outputs from a completed stage | `${{ stages.research.outputs.research_summary }}` |
| `stages.<id>.status` | Execution status of a stage | `${{ stages.review.status == 'success' }}` |
| `context` | Global context bindings | `${{ context.repo_structure }}` |
| `env` | Environment variables | `${{ env.PROJECT_ROOT }}` |
| `run` | Current workflow run metadata | `${{ run.id }}`, `${{ run.started_at }}` |
| `workflow` | Workflow definition metadata | `${{ workflow.id }}`, `${{ workflow.version }}` |

**Operators:** `==`, `!=`, `&&`, `||`, `!`, ternary `a ? b : c`

**Built-in functions:**

| Function | Description | Example |
|----------|-------------|---------|
| `length(array)` | Array length | `${{ length(stages.research.outputs.risks) > 3 }}` |
| `contains(str, substr)` | String containment | `${{ contains(parameters.target_branch, 'release') }}` |
| `toJSON(value)` | Serialize to JSON string | `${{ toJSON(stages.plan.outputs) }}` |
| `fromJSON(str)` | Parse JSON string | `${{ fromJSON(stages.plan.outputs.config_json) }}` |

### 3.7 Project Overrides

Projects can override workflow bindings without modifying the shared workflow definition:

**File:** `.skillmeat-workflow-overrides.yaml`

```yaml
overrides:
  # Override for a specific workflow
  "sdlc-feature-ship":
    # Swap agents per role
    stages:
      research:
        roles:
          primary:
            artifact: "agent:my-custom-researcher"
            model: "sonnet"                        # Downgrade model for cost
      implement:
        roles:
          primary:
            artifact: "agent:my-fullstack-dev"
          tools:
            - "skill:my-custom-linter"
            - "skill:git-ops"

    # Override context modules
    context:
      global_modules:
        - "ctx:my-project-rules"
        - "ctx:my-coding-standards"

    # Override parameters defaults
    config:
      parameters:
        target_branch:
          default: "develop"
```

The engine merges overrides with the base workflow definition using a deep-merge strategy: override values replace base values at the leaf level; arrays are replaced entirely (not appended).

### 3.8 Type System

The schema supports a minimal type system for input/output contracts, designed to be JSON Schema-compatible for validation.

**Primitive types:**

| Type | JSON Schema | Description |
|------|-------------|-------------|
| `string` | `{ "type": "string" }` | UTF-8 string |
| `number` | `{ "type": "number" }` | Floating point |
| `integer` | `{ "type": "integer" }` | Integer |
| `boolean` | `{ "type": "boolean" }` | Boolean |

**Compound types:**

| Type | JSON Schema | Description |
|------|-------------|-------------|
| `object` | `{ "type": "object" }` | Arbitrary JSON object |
| `array<T>` | `{ "type": "array", "items": { "type": "T" } }` | Typed array |
| `artifact_ref` | Custom: `{ "type": "string", "pattern": "^(agent|skill|mcp|command):.*$" }` | SkillMeat artifact reference |
| `memory_item` | Custom | Reference to a Memory system item |
| `context_module` | Custom | Reference to a Context Module |

**Validation rules:**
- `required: true` fields must be present in stage outputs before the handoff proceeds.
- Type mismatches at plan time produce warnings; at runtime, they produce errors.
- The `default` field provides a fallback value if the output is not produced.

---

## 4. Execution Model

### 4.1 Lifecycle Phases

```
DEFINE  -->  VALIDATE  -->  PLAN  -->  EXECUTE  -->  COMPLETE
  |            |              |           |             |
  |            |              |           |             +-- on_complete hooks
  |            |              |           +-- Stage execution loop
  |            |              +-- DAG resolution, parallel batch computation
  |            +-- Schema validation, contract checking, artifact resolution
  +-- Author writes YAML or uses visual composer
```

### 4.2 Plan Phase (Dry Run)

`skillmeat workflow plan <name>` performs:

1. **Parse** the YAML into the internal workflow model.
2. **Validate** schema structure, type contracts, expression references.
3. **Resolve artifacts** -- verify all referenced agents/skills/MCPs exist in the collection.
4. **Build DAG** -- compute dependency graph from `depends_on` declarations.
5. **Compute batches** -- group stages into parallel execution batches (topological sort).
6. **Estimate cost** -- based on model assignments and estimated token usage per stage.
7. **Output** an execution plan:

```
Workflow: Ship a Feature (SDLC) v1.0.0
Parameters: feature_name=auth-redesign, target_branch=main

Execution Plan:
  Batch 1 (parallel):
    [research] Research & Discovery
      Agent: agent:researcher-v1 (opus)
      Context: ctx:repo-rules, ctx:domain-knowledge + 2000 tokens memory
      Timeout: 30m

  Batch 2 (sequential after Batch 1):
    [plan] Architecture Planning
      Agent: agent:architect-v1 (opus)
      Inputs: research.research_summary, research.identified_risks
      Context: ctx:repo-rules, ctx:coding-standards
      Timeout: 20m

  Batch 3 (parallel after Batch 2):
    [frontend-impl] Frontend Implementation
      Agent: agent:ui-engineer-v2 (opus)
      Inputs: plan.implementation_plan, plan.component_spec
      Tools: skill:git-ops, mcp:github-api
      Timeout: 1h

    [backend-impl] Backend Implementation
      Agent: agent:python-backend-v2 (opus)
      Inputs: plan.implementation_plan, plan.api_spec
      Tools: skill:git-ops, mcp:github-api
      Timeout: 1h

  Batch 4 (sequential after Batch 3):
    [integration-test] Integration Testing
      Agent: agent:test-engineer-v1 (sonnet)
      Inputs: frontend-impl.changes, backend-impl.changes
      Timeout: 30m

  Batch 5 (conditional):
    [security-review] Security Review
      Condition: stages.implement.outputs.touches_auth == true
      Agent: agent:security-reviewer-v1 (opus)
      Timeout: 20m

  Batch 6 (gate):
    [deploy-approval] Deployment Approval
      Type: manual_approval
      Approvers: miethe
      Timeout: 24h

  Batch 7 (sequential after Batch 6):
    [deploy] Production Deployment
      Agent: agent:deployer-v1 (sonnet)
      Tools: skill:git-ops, mcp:github-api
      Timeout: 15m

Estimated total time: 3h 15m (excluding approval gate)
Estimated token cost: ~85K tokens
```

### 4.3 Execution Phase

The execution engine processes batches sequentially. Within each batch, stages run in parallel.

**Stage execution lifecycle:**

```
PENDING --> RUNNING --> SUCCESS
                   \-> FAILED --> (retry?) --> RUNNING
                   \-> SKIPPED (condition false)
                   \-> TIMED_OUT --> (retry?) --> RUNNING
                   \-> CANCELLED
```

**Handoff protocol:**

After a stage completes successfully:
1. The engine validates outputs against the output contract.
2. If `handoff.format` is "structured", outputs are serialized as JSON.
3. If `handoff.summary_prompt` is provided, a summarization pass condenses outputs.
4. The outputs are stored in the run state under `stages.<id>.outputs`.
5. Dependent stages that reference these outputs via `${{ stages.<id>.outputs.* }}` are unblocked.

### 4.4 Run State Persistence

Each workflow execution creates a run record:

```yaml
run:
  id: "run-2026-02-06-001"
  workflow_id: "sdlc-feature-ship"
  workflow_version: "1.0.0"
  status: "running"                   # pending | running | success | failed | cancelled
  started_at: "2026-02-06T10:00:00Z"
  completed_at: null
  parameters:
    feature_name: "auth-redesign"
    target_branch: "main"
  stages:
    research:
      status: "success"
      started_at: "2026-02-06T10:00:05Z"
      completed_at: "2026-02-06T10:12:30Z"
      attempt: 1
      outputs:
        research_summary: "..."
        identified_risks: ["rate-limit concerns", "breaking API change"]
        needs_review: true
      agent_run_id: "agent-run-abc123"
    plan:
      status: "running"
      started_at: "2026-02-06T10:12:35Z"
      attempt: 1
```

Run state is persisted to SQLite (DB-native, following SkillMeat's dual-stack pattern). The filesystem representation is optional (for export/audit).

---

## 5. Integration Points

### 5.1 SkillMeat Collection System

Workflows are a new `ArtifactType.WORKFLOW` in the collection:

```python
# In artifact_detection.py
class ArtifactType(str, Enum):
    # ... existing types ...
    WORKFLOW = "workflow"
```

Detection heuristic: directory contains `WORKFLOW.yaml` or `WORKFLOW.json`.

Manifest entry:
```toml
[[artifacts]]
name = "sdlc-feature-ship"
type = "workflow"
source = "miethe/workflows/sdlc-feature-ship"
version = "1.0.0"
```

### 5.2 Memory & Context System

The `context` block in the workflow schema directly references the Memory & Context PRD's constructs:

- **Context Modules** (`ctx:*` references) map to Context Module entities with their governed token budgets and composition rules.
- **Memory injection** (`memory` block) queries the Memory system's `pack_context()` API with the specified filters (project scope, confidence threshold, categories, token budget).
- **Post-run capture** (`hooks.on_complete`) can trigger memory extraction from the workflow run log.

### 5.3 API Surface

New endpoints (added to FastAPI backend):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/workflows` | List workflow artifacts |
| `GET` | `/api/v1/workflows/{id}` | Get workflow definition |
| `POST` | `/api/v1/workflows/{id}/validate` | Validate workflow schema |
| `POST` | `/api/v1/workflows/{id}/plan` | Generate execution plan (dry run) |
| `POST` | `/api/v1/workflows/{id}/run` | Execute workflow |
| `GET` | `/api/v1/workflow-runs` | List workflow runs |
| `GET` | `/api/v1/workflow-runs/{run_id}` | Get run status and outputs |
| `POST` | `/api/v1/workflow-runs/{run_id}/cancel` | Cancel a running workflow |
| `POST` | `/api/v1/workflow-runs/{run_id}/gates/{stage_id}/approve` | Approve a gate |
| `POST` | `/api/v1/workflow-runs/{run_id}/gates/{stage_id}/reject` | Reject a gate |

### 5.4 CLI Surface

```bash
# Workflow management
skillmeat workflow list                            # List available workflows
skillmeat workflow show <name>                     # Display workflow definition
skillmeat workflow validate <path>                 # Validate a workflow YAML file
skillmeat workflow plan <name> [--param key=val]   # Dry run: show execution plan
skillmeat workflow run <name> [--param key=val]    # Execute workflow

# Run management
skillmeat workflow runs                            # List recent runs
skillmeat workflow runs <run_id>                   # Show run status
skillmeat workflow runs <run_id> --logs            # Show execution logs
skillmeat workflow approve <run_id> <stage_id>     # Approve a gate
skillmeat workflow cancel <run_id>                 # Cancel a running workflow
```

### 5.5 Web UI Composer

The visual composer reads/writes the same YAML schema. The `ui` metadata fields (`position`, `color`, `icon`) are maintained by the composer and ignored by the execution engine.

**Round-trip contract:** Any YAML file produced by the composer must be valid when loaded by the CLI. Any YAML file produced by hand must render correctly in the composer (missing `ui` fields use sensible defaults).

---

## 6. Complete Example: SDLC Feature Ship Workflow

```yaml
workflow:
  id: "sdlc-feature-ship"
  name: "Ship a Feature (SDLC)"
  version: "1.0.0"
  description: >
    Complete software development lifecycle for shipping a feature:
    research the problem, plan the architecture, implement frontend
    and backend in parallel, test, review, and deploy.
  author: "miethe"
  tags: ["sdlc", "feature", "full-stack"]

config:
  parameters:
    feature_name:
      type: string
      required: true
      description: "Name of the feature to implement"
    target_branch:
      type: string
      default: "main"
    priority:
      type: string
      default: "normal"
      description: "Execution priority: normal | high | low"
  timeout: "6h"

context:
  global_modules:
    - "ctx:repo-rules"
    - "ctx:coding-standards"
  memory:
    project_scope: "current"
    min_confidence: 0.7
    categories: ["constraint", "pattern", "decision"]
    max_tokens: 2000

stages:
  # ---- Stage 1: Research ----
  - id: "research"
    name: "Research & Discovery"
    depends_on: []
    roles:
      primary:
        artifact: "agent:researcher-v1"
        model: "opus"
        instructions: >
          Investigate the problem space for the feature. Identify existing
          implementations, constraints, and risks. Do not write code.
      tools:
        - "skill:codebase-explorer"
        - "skill:web-search"
    inputs:
      feature_name:
        type: string
        source: "${{ parameters.feature_name }}"
        required: true
    outputs:
      research_summary:
        type: string
        required: true
      identified_risks:
        type: "array<string>"
        required: true
      relevant_files:
        type: "array<string>"
        required: false
    context:
      modules:
        - "ctx:domain-knowledge"
    error_policy:
      retry:
        max_attempts: 2
      timeout: "30m"
    handoff:
      format: "structured"
      summary_prompt: "Summarize findings in 5 bullet points for the architect."

  # ---- Stage 2: Plan ----
  - id: "plan"
    name: "Architecture Planning"
    depends_on: ["research"]
    roles:
      primary:
        artifact: "agent:architect-v1"
        model: "opus"
        instructions: >
          Design the implementation plan based on research findings.
          Produce a component spec, API spec, and implementation tasks.
      tools:
        - "skill:codebase-explorer"
    inputs:
      research_summary:
        type: string
        source: "${{ stages.research.outputs.research_summary }}"
        required: true
      identified_risks:
        type: "array<string>"
        source: "${{ stages.research.outputs.identified_risks }}"
        required: true
    outputs:
      implementation_plan:
        type: object
        required: true
      component_spec:
        type: object
        required: true
      api_spec:
        type: object
        required: false
      touches_auth:
        type: boolean
        required: false
        default: false
    error_policy:
      timeout: "20m"
    handoff:
      format: "structured"

  # ---- Stage 3a: Frontend (parallel with 3b) ----
  - id: "frontend-impl"
    name: "Frontend Implementation"
    depends_on: ["plan"]
    roles:
      primary:
        artifact: "agent:ui-engineer-v2"
        model: "opus"
      tools:
        - "skill:git-ops"
        - "skill:component-patterns"
    inputs:
      implementation_plan:
        type: object
        source: "${{ stages.plan.outputs.implementation_plan }}"
        required: true
      component_spec:
        type: object
        source: "${{ stages.plan.outputs.component_spec }}"
        required: true
    outputs:
      changes:
        type: object
        description: "Git diff summary of frontend changes"
        required: true
      components_created:
        type: "array<string>"
        required: false
    context:
      modules:
        - "ctx:component-patterns"
        - "ctx:accessibility-guidelines"
    error_policy:
      retry:
        max_attempts: 2
        initial_interval: "1m"
      timeout: "1h"

  # ---- Stage 3b: Backend (parallel with 3a) ----
  - id: "backend-impl"
    name: "Backend Implementation"
    depends_on: ["plan"]
    roles:
      primary:
        artifact: "agent:python-backend-v2"
        model: "opus"
      tools:
        - "skill:git-ops"
        - "skill:router-patterns"
    inputs:
      implementation_plan:
        type: object
        source: "${{ stages.plan.outputs.implementation_plan }}"
        required: true
      api_spec:
        type: object
        source: "${{ stages.plan.outputs.api_spec }}"
        required: false
    outputs:
      changes:
        type: object
        description: "Git diff summary of backend changes"
        required: true
      endpoints_created:
        type: "array<string>"
        required: false
    context:
      modules:
        - "ctx:router-patterns"
        - "ctx:data-flow-patterns"
    error_policy:
      retry:
        max_attempts: 2
      timeout: "1h"

  # ---- Stage 4: Integration Test ----
  - id: "test"
    name: "Integration Testing"
    depends_on: ["frontend-impl", "backend-impl"]
    roles:
      primary:
        artifact: "agent:test-engineer-v1"
        model: "sonnet"
      tools:
        - "skill:testing-patterns"
    inputs:
      frontend_changes:
        type: object
        source: "${{ stages.frontend-impl.outputs.changes }}"
        required: true
      backend_changes:
        type: object
        source: "${{ stages.backend-impl.outputs.changes }}"
        required: true
    outputs:
      test_results:
        type: object
        required: true
      coverage_report:
        type: string
        required: false
      all_passing:
        type: boolean
        required: true
    error_policy:
      retry:
        max_attempts: 3
        initial_interval: "30s"
        backoff_multiplier: 2.0
      timeout: "30m"

  # ---- Stage 5: Security Review (conditional) ----
  - id: "security-review"
    name: "Security Review"
    depends_on: ["test"]
    condition: "${{ stages.plan.outputs.touches_auth == true }}"
    roles:
      primary:
        artifact: "agent:security-reviewer-v1"
        model: "opus"
    inputs:
      frontend_changes:
        type: object
        source: "${{ stages.frontend-impl.outputs.changes }}"
      backend_changes:
        type: object
        source: "${{ stages.backend-impl.outputs.changes }}"
    outputs:
      security_findings:
        type: "array<string>"
        required: true
      approved:
        type: boolean
        required: true
    error_policy:
      timeout: "20m"
      on_failure: "halt"

  # ---- Stage 6: Code Review ----
  - id: "review"
    name: "Code Review"
    depends_on: ["test", "security-review"]
    roles:
      primary:
        artifact: "agent:code-reviewer-v1"
        model: "opus"
        instructions: >
          Review all changes for code quality, consistency with project
          standards, and correctness. Approve or request changes.
    inputs:
      test_results:
        type: object
        source: "${{ stages.test.outputs.test_results }}"
        required: true
      security_findings:
        type: "array<string>"
        source: "${{ stages.security-review.outputs.security_findings }}"
        required: false
    outputs:
      review_verdict:
        type: string
        description: "'approved' | 'changes_requested'"
        required: true
      review_comments:
        type: "array<string>"
        required: false
    error_policy:
      timeout: "30m"

  # ---- Stage 7: Deploy Approval (gate) ----
  - id: "deploy-approval"
    name: "Deployment Approval"
    depends_on: ["review"]
    condition: "${{ stages.review.outputs.review_verdict == 'approved' }}"
    type: "gate"
    gate:
      kind: "manual_approval"
      approvers: ["miethe"]
      timeout: "24h"
      on_timeout: "halt"
      message: >
        Feature '${{ parameters.feature_name }}' has passed review.
        Approve deployment to ${{ parameters.target_branch }}?

  # ---- Stage 8: Deploy ----
  - id: "deploy"
    name: "Production Deployment"
    depends_on: ["deploy-approval"]
    roles:
      primary:
        artifact: "agent:deployer-v1"
        model: "sonnet"
      tools:
        - "skill:git-ops"
    inputs:
      target_branch:
        type: string
        source: "${{ parameters.target_branch }}"
        required: true
      feature_name:
        type: string
        source: "${{ parameters.feature_name }}"
        required: true
    outputs:
      deploy_status:
        type: string
        required: true
      pr_url:
        type: string
        required: false
    error_policy:
      retry:
        max_attempts: 1
        non_retryable_errors: ["merge_conflict"]
      timeout: "15m"
      on_failure: "halt"

error_policy:
  default_retry:
    max_attempts: 2
    initial_interval: "30s"
    backoff_multiplier: 2.0
  on_stage_failure: "halt"

hooks:
  on_complete:
    run: "skillmeat memory capture --workflow-run ${{ run.id }}"
```

---

## 7. Minimal Example: Two-Stage Code Review

Demonstrating progressive complexity -- a simple workflow that is only 30 lines:

```yaml
workflow:
  id: "quick-review"
  name: "Quick Code Review"
  version: "1.0.0"

config:
  parameters:
    pr_url:
      type: string
      required: true

stages:
  - id: "analyze"
    name: "Analyze Changes"
    depends_on: []
    roles:
      primary:
        artifact: "agent:code-analyzer-v1"
    inputs:
      pr_url:
        type: string
        source: "${{ parameters.pr_url }}"
    outputs:
      analysis:
        type: string
        required: true

  - id: "review"
    name: "Write Review"
    depends_on: ["analyze"]
    roles:
      primary:
        artifact: "agent:code-reviewer-v1"
    inputs:
      analysis:
        type: string
        source: "${{ stages.analyze.outputs.analysis }}"
    outputs:
      review:
        type: string
        required: true
```

No error policies, no context binding, no gates. The engine applies sensible defaults (1 retry, 30m timeout, halt on failure).

---

## 8. Schema Defaults

When optional fields are omitted, the engine applies these defaults:

| Field | Default Value | Rationale |
|-------|---------------|-----------|
| `config.timeout` | `"2h"` | Reasonable upper bound for agent workflows |
| `stage.depends_on` | `[]` | No dependencies = eligible for first batch |
| `stage.condition` | `null` (always run) | Unconditional by default |
| `stage.type` | `"agent"` | Most stages are agent-executed |
| `stage.roles.primary.model` | `"opus"` | Best quality by default |
| `stage.error_policy.retry.max_attempts` | `2` | One retry is almost always worth it |
| `stage.error_policy.retry.initial_interval` | `"30s"` | Brief pause before retry |
| `stage.error_policy.retry.backoff_multiplier` | `2.0` | Exponential backoff |
| `stage.error_policy.on_failure` | `"halt"` | Fail-safe default |
| `stage.error_policy.timeout` | `"30m"` | Reasonable per-stage limit |
| `stage.handoff.format` | `"structured"` | JSON for machine consumption |
| `stage.handoff.include_run_log` | `false` | Token-efficient default |
| `context.memory.min_confidence` | `0.7` | Only high-confidence memories |
| `context.memory.max_tokens` | `2000` | Reasonable token budget |

---

## 9. Comparison: PRD Schema vs. Proposed Schema

The original PRD (workflow-orchestration-v1) defined a minimal schema:

```json
{
  "workflow_id": "sdlc-feature-ship",
  "stages": [
    {
      "id": "research",
      "roles": { "primary": "agent:researcher-v1" },
      "context_policy": { "modules": ["ctx:repo-rules"] }
    }
  ]
}
```

The proposed schema extends this in the following dimensions:

| Dimension | PRD Schema | Proposed Schema |
|-----------|-----------|-----------------|
| **Metadata** | `workflow_id` only | Full metadata block (name, version, author, tags, description) |
| **Parameters** | Not defined | Typed parameters with defaults and runtime override |
| **Dependencies** | Not defined | `depends_on` array with automatic parallel batch computation |
| **Input/Output contracts** | Not defined | Typed `inputs`/`outputs` per stage with source expressions |
| **Error handling** | Not defined | Hierarchical retry policies, timeout, `on_failure` actions |
| **Conditionals** | Not defined | `condition` expressions for conditional stage execution |
| **Approval gates** | Not defined | `type: "gate"` stages with approval semantics |
| **Context binding** | `context_policy.modules` | Hierarchical context (global + per-stage) with memory integration |
| **Handoff** | Not defined | `handoff` block controlling output format and summarization |
| **Expression language** | Not defined | `${{ }}` expressions for inter-stage data references |
| **Project overrides** | Mentioned (`.skillmeat-workflow-overrides.toml`) | Detailed override schema with deep-merge semantics |
| **Visual metadata** | Not defined | `ui` blocks for composer round-trip fidelity |
| **Lifecycle hooks** | Not defined | `hooks` block for on_start, on_complete, on_failure |
| **Type system** | Not defined | JSON Schema-compatible types for contract validation |

---

## 10. Trade-Off Analysis

### 10.1 YAML vs. JSON vs. Programmatic

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **YAML** | Human-readable, widely understood, comment support | Whitespace-sensitive, harder to validate | **Primary format** |
| **JSON** | Machine-readable, strict parsing, schema validation | Verbose, no comments | **Supported alternative** |
| **Programmatic (Python)** | Full expressiveness, IDE support, type checking | Not serializable for visual editor, non-portable | **Not adopted** |

Decision: YAML as primary authoring format, JSON as machine interchange format. Both are losslessly convertible. The visual composer writes YAML.

### 10.2 Explicit vs. Implicit Dependencies

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Explicit `depends_on`** | Unambiguous, easy to validate, clear DAG | Slightly more verbose | **Adopted** |
| **Implicit (data flow)** | Less boilerplate, auto-inferred | Harder to debug, requires runtime analysis | **Not adopted** |

Decision: Explicit `depends_on` only. Data references via `${{ stages.X.outputs.Y }}` are validated to match declared dependencies at plan time (if stage A references stage B's outputs, stage A must have B in its `depends_on`).

### 10.3 Expression Language Complexity

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Full templating (Jinja2)** | Maximum flexibility | Security risks, hard to validate, overkill | **Not adopted** |
| **GitHub Actions style** | Familiar, scoped, safe | Limited but sufficient | **Adopted** |
| **No expressions** | Simplest, safest | Cannot reference inter-stage outputs | **Insufficient** |

Decision: GitHub Actions-style `${{ }}` expressions. Limited to property access, comparisons, and a small set of built-in functions. No arbitrary code execution.

### 10.4 Role Model: Fixed vs. Dynamic

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Fixed roles per stage** | Predictable, easy to validate | Less flexible | **Adopted (v1)** |
| **Dynamic role selection** | Runtime optimization | Harder to plan, debug | **Deferred (v2)** |

Decision: v1 uses fixed role assignments per stage. The project override mechanism allows swapping agents without modifying the workflow definition.

---

## 11. Implementation Roadmap (Phases)

### Phase 1: Schema & Validation (Core)
- Define YAML/JSON schema (JSON Schema definition for validation)
- Implement `WorkflowDefinition` dataclass in `skillmeat/core/workflow.py`
- Add `ArtifactType.WORKFLOW` to artifact detection
- Implement schema parser and validator
- `skillmeat workflow validate <path>` CLI command
- Unit tests for schema parsing and validation

### Phase 2: DAG Engine & Plan
- Implement dependency graph builder (topological sort)
- Implement parallel batch computation
- Expression language parser (property access + comparisons)
- `skillmeat workflow plan <name>` CLI command (dry run)
- Contract validation (input/output type checking)

### Phase 3: Sequential Execution
- Implement stage executor (invokes agents via SkillMeat's existing dispatch)
- Implement handoff protocol (output serialization, summary prompts)
- Run state persistence (SQLite)
- `skillmeat workflow run <name>` CLI command
- Basic error handling (retry, timeout, halt-on-failure)

### Phase 4: Parallel Execution & Gates
- Implement parallel batch execution (concurrent agent dispatch)
- Implement approval gates (manual approval via CLI/API)
- Conditional stage execution
- API endpoints for run management

### Phase 5: Visual Composer (Web UI)
- Drag-and-drop stage editor
- Artifact picker sidebar
- Context module binding UI
- Execution dashboard with timeline view
- YAML round-trip fidelity

---

## 12. Open Questions

1. **Agent dispatch mechanism:** How does the engine actually invoke an agent? Does it shell out to `claude` CLI, use the Claude Code SDK, or call the SkillMeat API? This depends on the runtime environment (local CLI vs. web server).

2. **Concurrency limits:** Should there be a global max-parallel-stages limit? Running 5+ agent sessions simultaneously could be resource-intensive and expensive.

3. **State persistence granularity:** Should intermediate outputs be stored in the filesystem (for audit/export) or only in SQLite? The dual-stack pattern suggests both, but that adds complexity.

4. **Workflow versioning:** When a workflow is updated while a run is in progress, should the run use the version at start time (snapshot) or the current version? Recommendation: snapshot semantics (lock version at run start).

5. **Cross-workflow composition:** Should one workflow be able to call another as a "sub-workflow"? This is common in GitHub Actions (`workflow_call`) but adds significant complexity. Recommendation: defer to v2.

6. **Cost controls:** Should the engine enforce token budget caps per stage or per workflow? If an agent stage consumes more than N tokens, should it be terminated? This interacts with model selection and timeout policies.
