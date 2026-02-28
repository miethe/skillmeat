---
title: SWDL Workflow Authoring Guide
description: Complete guide to writing SkillMeat Workflow Definition Language (SWDL) files with expression syntax, parameters, error policies, and practical examples
audience: developers
tags:
  - swdl
  - workflow-definition
  - orchestration
  - expressions
  - agent-workflows
created: "2026-02-27"
updated: "2026-02-27"
category: user-guides
status: current
related_documents:
  - docs/project_plans/design-specs/workflow-orchestration-schema-spec.md
  - skillmeat/core/workflow/models.py
  - skillmeat/core/workflow/expressions.py
---

# SWDL Workflow Authoring Guide

This guide teaches you how to write SkillMeat Workflow Definition Language (SWDL) files. SWDL is a declarative YAML format for defining multi-stage agent workflows with typed I/O contracts, dependency graphs, error handling, and context binding.

## What is SWDL?

SWDL (SkillMeat Workflow Definition Language) enables you to:

- **Define multi-stage workflows** where agents work in sequence or parallel
- **Type inputs and outputs** for reliable data flow between stages
- **Control execution** with conditions, dependencies, and error policies
- **Bind context** from Context Modules and the Memory system
- **Handle failures gracefully** with retry policies and fallback behavior
- **Pause for human approval** with manual gates

Workflows are defined as YAML files named `WORKFLOW.yaml` in your project's `.claude` directory.

## Your First Workflow: 30 Lines

Here's a minimal, working workflow that researches a feature and generates documentation:

```yaml
workflow:
  id: simple-research
  name: Research and Document Feature
  version: "1.0.0"
  description: Research a feature and generate documentation

config:
  parameters:
    feature_name:
      type: string
      required: true
      description: The feature to research
  timeout: "1h"

stages:
  - id: research
    name: Research Feature
    type: agent
    roles:
      primary:
        artifact: "agent:researcher-v1"
    outputs:
      summary:
        type: string
        description: Research summary
      key_points:
        type: array<string>
        description: Key findings

  - id: document
    name: Generate Documentation
    type: agent
    depends_on: [research]
    roles:
      primary:
        artifact: "agent:doc-writer-v1"
    inputs:
      research_data:
        type: string
        source: "${{ stages.research.outputs.summary }}"
    outputs:
      documentation:
        type: string
        required: true
```

To run this workflow:

```bash
skillmeat workflow execute simple-research --feature-name "authentication-v2"
```

## Full SDLC Example: Complete Feature Workflow

Here's a comprehensive workflow showing all major features:

```yaml
workflow:
  id: sdlc-feature-ship
  name: Ship a Feature (Full SDLC)
  version: "1.0.0"
  description: |
    Complete feature development workflow: specification, implementation,
    testing, code review, approval gate, and deployment.
  author: engineering-team
  tags:
    - sdlc
    - full-stack
    - deployment
  ui:
    color: "#4A90D9"
    icon: "rocket"

config:
  # Runtime parameters supplied by the caller
  parameters:
    feature_name:
      type: string
      required: true
      description: "Name of the feature (e.g., 'auth-v2')"
    target_env:
      type: string
      required: false
      default: staging
      description: "Deployment target: staging or production"
    skip_review:
      type: boolean
      required: false
      default: false
      description: "Skip code review stage (for hotfixes)"
    estimated_effort:
      type: integer
      required: false
      description: "Story points estimate"

  timeout: "6h"
  env:
    LOG_LEVEL: "info"
    GITHUB_REPO: "org/main-repo"

# Global context available to all stages
context:
  global_modules:
    - "ctx:coding-standards"
    - "ctx:architecture-guide"
  memory:
    project_scope: current
    min_confidence: 0.75
    categories: [constraint, decision]
    max_tokens: 3000

# Global error handling defaults
error_policy:
  default_retry:
    max_attempts: 2
    initial_interval: "30s"
    backoff_multiplier: 2.0
    max_interval: "5m"
  on_stage_failure: "halt"

# Lifecycle hooks
hooks:
  on_start:
    notify:
      channel: "#engineering"
      message: "Starting feature workflow for ${{ parameters.feature_name }}"
  on_complete:
    notify:
      channel: "#engineering"
      message: "Feature ${{ parameters.feature_name }} shipped to ${{ parameters.target_env }}"
  on_failure:
    notify:
      channel: "#engineering"
      message: "Feature workflow failed at stage ${{ workflow.current_stage }}"

stages:
  # Stage 1: Specification
  - id: spec
    name: Write Specification
    description: Generate feature specification from requirements
    type: agent
    roles:
      primary:
        artifact: "agent:spec-writer-v1"
        instructions: "Focus on API contracts and data models"
      tools:
        - "skill:web-search"
        - "skill:codebase-explorer"
    inputs:
      feature_description:
        type: string
        source: "${{ parameters.feature_name }}"
    outputs:
      specification:
        type: string
        required: true
        description: Complete feature specification
      api_schema:
        type: string
        required: true
        description: OpenAPI specification
      acceptance_criteria:
        type: array<string>
        required: true
    error_policy:
      on_failure: "halt"
      timeout: "45m"
    handoff:
      format: markdown
      include_run_log: false
    ui:
      position: [100, 50]
      color: "#E8F5E9"
      icon: "file-text"

  # Stage 2: Implementation
  - id: implement
    name: Implement Feature
    description: Write code based on specification
    type: agent
    depends_on: [spec]
    roles:
      primary:
        artifact: "agent:backend-engineer-v1"
        model: "sonnet"  # Override default model
        instructions: "Follow the specification exactly. Use the API schema provided."
      tools:
        - "skill:code-generator"
        - "mcp:github-api"
    inputs:
      spec:
        type: string
        source: "${{ stages.spec.outputs.specification }}"
      api_schema:
        type: string
        source: "${{ stages.spec.outputs.api_schema }}"
    outputs:
      implemented_code:
        type: string
        required: true
      test_cases:
        type: array<string>
        required: true
      pr_url:
        type: string
        required: true
    error_policy:
      retry:
        max_attempts: 2
        initial_interval: "1m"
        non_retryable_errors: [auth_failure]
      on_failure: "halt"
      timeout: "2h"
    context:
      modules:
        - "ctx:code-style-guide"
      memory:
        project_scope: current
        min_confidence: 0.8
    handoff:
      format: markdown
      include_run_log: true
      summary_prompt: "Summarize the implementation, highlighting any deviations from spec"
    ui:
      position: [300, 50]
      color: "#E3F2FD"
      icon: "code"

  # Stage 3: Testing (parallel with implementation)
  - id: test
    name: Run Test Suite
    type: agent
    depends_on: [spec]
    roles:
      primary:
        artifact: "agent:qa-engineer-v1"
    inputs:
      acceptance_criteria:
        type: array<string>
        source: "${{ stages.spec.outputs.acceptance_criteria }}"
    outputs:
      test_results:
        type: string
        required: true
      coverage_report:
        type: string
        required: true
      issues_found:
        type: array<string>
        default: []
    error_policy:
      on_failure: "continue"  # Don't halt on test failures
      timeout: "1h"
    ui:
      position: [500, 50]
      color: "#FFF3E0"
      icon: "check-circle"

  # Stage 4: Code Review (conditional)
  - id: review
    name: Code Review
    description: Human code review of implementation
    type: agent
    depends_on: [implement]
    condition: "${{ parameters.skip_review == false }}"
    roles:
      primary:
        artifact: "agent:senior-code-reviewer-v1"
    inputs:
      pr_url:
        type: string
        source: "${{ stages.implement.outputs.pr_url }}"
      test_results:
        type: string
        source: "${{ stages.test.outputs.test_results }}"
    outputs:
      review_comments:
        type: string
        required: true
      approval:
        type: boolean
        required: true
    error_policy:
      on_failure: "continue"
      timeout: "30m"
    ui:
      position: [700, 50]
      color: "#F3E5F5"
      icon: "eye"

  # Stage 5: Approval Gate
  - id: approval
    name: QA Approval Gate
    description: Manual approval before deployment
    type: gate
    depends_on: [review, test]
    condition: "${{ parameters.target_env == 'production' }}"
    gate:
      kind: manual_approval
      approvers:
        - qa-lead
        - product-manager
      timeout: "24h"
      on_timeout: "reject"
      message: "Please review the feature implementation and approve for production deployment"
    error_policy:
      timeout: "24h"
      on_failure: "halt"
    ui:
      position: [900, 50]
      color: "#FCE4EC"
      icon: "alert-circle"

  # Stage 6: Deploy to Staging
  - id: deploy-staging
    name: Deploy to Staging
    type: agent
    depends_on: [implement]
    condition: "${{ parameters.target_env == 'staging' || parameters.target_env == 'production' }}"
    roles:
      primary:
        artifact: "agent:devops-engineer-v1"
        instructions: "Deploy to staging environment"
    inputs:
      pr_url:
        type: string
        source: "${{ stages.implement.outputs.pr_url }}"
    outputs:
      staging_url:
        type: string
        required: true
      deployment_id:
        type: string
        required: true
    error_policy:
      retry:
        max_attempts: 3
        initial_interval: "1m"
      on_failure: "halt"
      timeout: "30m"
    ui:
      position: [300, 200]
      color: "#E0F2F1"
      icon: "cloud"

  # Stage 7: Deploy to Production (conditional)
  - id: deploy-prod
    name: Deploy to Production
    type: agent
    depends_on: [approval]
    condition: "${{ parameters.target_env == 'production' }}"
    roles:
      primary:
        artifact: "agent:devops-engineer-v1"
        instructions: "Deploy to production with monitoring enabled"
    inputs:
      deployment_id:
        type: string
        source: "${{ stages.deploy-staging.outputs.deployment_id }}"
    outputs:
      prod_url:
        type: string
        required: true
      monitoring_dashboard:
        type: string
        required: true
    error_policy:
      on_failure: "halt"
      timeout: "30m"
    ui:
      position: [500, 200]
      color: "#FFEBEE"
      icon: "send"

  # Stage 8: Smoke Tests
  - id: smoke-tests
    name: Run Smoke Tests
    type: agent
    depends_on: [deploy-staging]
    roles:
      primary:
        artifact: "agent:qa-engineer-v1"
    inputs:
      staging_url:
        type: string
        source: "${{ stages.deploy-staging.outputs.staging_url }}"
    outputs:
      smoke_test_results:
        type: string
        required: true
      passed:
        type: boolean
        required: true
    error_policy:
      on_failure: "continue"
      timeout: "15m"
    ui:
      position: [700, 200]
      color: "#F1F8E9"
      icon: "activity"
```

## Schema Reference

### Top-Level Fields

Every SWDL workflow has this structure:

```yaml
workflow:           # Workflow metadata (required)
  id: string        # Unique identifier (kebab-case)
  name: string      # Human-readable name
  version: string   # SemVer version (default: "1.0.0")
  description: string  # Optional description
  author: string    # Optional author
  tags: [string]    # Optional searchable tags
  ui:               # Optional visual metadata
    color: string   # CSS hex color
    icon: string    # Icon name

config:             # Execution configuration (optional, defaults shown)
  parameters: {}    # Workflow parameters
  timeout: "2h"     # Global timeout
  env: {}           # Environment variables

context:            # Global context binding (optional)
  global_modules: [string]  # Context modules for all stages
  memory:           # Memory injection config
    project_scope: "current"
    min_confidence: 0.7
    categories: []  # Memory type filter
    max_tokens: 2000

stages: []          # List of stage definitions (required)

error_policy:       # Global error handling (optional)
  default_retry:    # Default retry policy
    max_attempts: 2
    initial_interval: "30s"
    backoff_multiplier: 2.0
    max_interval: "5m"
  on_stage_failure: "halt"  # "halt" | "continue" | "rollback"

hooks:              # Lifecycle hooks (optional)
  on_start: {}      # Hook executed at workflow start
  on_complete: {}   # Hook executed on success
  on_failure: {}    # Hook executed on failure
```

### Stage Definition

Each stage in the `stages` array defines a unit of work:

```yaml
- id: string              # Unique stage identifier (kebab-case, required)
  name: string            # Human-readable name (required)
  description: string     # Detailed description (optional)
  type: string            # "agent" | "gate" | "fan_out" (default: "agent")

  # Dependencies and conditions
  depends_on: [string]    # IDs of prerequisite stages (default: [])
  condition: string       # SWDL expression; skip if false (optional)

  # For agent and gate stages
  roles:                  # Agent role assignments (required for agent type)
    primary:              # Primary agent
      artifact: string    # "agent:name" or "skill:name" (required)
      model: string       # Model override: "opus", "sonnet", "haiku" (optional)
      instructions: string  # Additional stage-specific instructions (optional)
    tools: [string]       # Supporting artifacts available to primary agent

  # For gate stages
  gate:                   # Gate configuration (required for gate type)
    kind: string          # "manual_approval" (default: "manual_approval")
    approvers: [string]   # List of approver usernames
    timeout: string       # Approval timeout (default: "24h")
    on_timeout: string    # "halt" | "auto_approve" | "reject" (default: "halt")
    message: string       # Message displayed to approvers (optional)

  # Input/output contracts
  inputs:                 # Named input declarations
    name:
      type: string        # SWDL type: "string", "boolean", "integer", "array<string>", etc.
      source: string      # SWDL expression resolving the value
      required: boolean   # Must be provided before execution (default: true)
      description: string # Human-readable description (optional)

  outputs:                # Named output declarations
    name:
      type: string        # SWDL type
      required: boolean   # Must be present after execution (default: true)
      description: string # Human-readable description (optional)
      default: any        # Fallback when absent and required: false (optional)

  # Context and memory
  context:                # Stage-level context binding (optional)
    modules: [string]     # Context modules to inject
    memory:               # Memory injection config
      project_scope: "current"  # "current" or project ID
      min_confidence: 0.7
      categories: []      # Memory type filter
      max_tokens: 2000

  # Error handling
  error_policy:           # Stage-level error policy (optional)
    retry:                # Retry configuration (optional)
      max_attempts: 2
      initial_interval: "30s"
      backoff_multiplier: 2.0
      max_interval: "5m"
      non_retryable_errors: [string]  # Error types to not retry
    on_failure: string     # "halt" | "continue" | "skip_dependents" (default: "halt")
    timeout: string        # Stage timeout (default: "30m" for agent, "24h" for gate)

  # Output handling
  handoff:                # Output packaging (optional)
    format: string        # "structured" | "markdown" | "raw" (default: "structured")
    include_run_log: boolean  # Attach execution log (default: false)
    summary_prompt: string    # Summarization prompt (optional)

  # UI metadata
  ui:                     # Visual composer metadata (ignored by engine)
    position: [number, number]  # Canvas [x, y] coordinates
    color: string         # CSS hex color
    icon: string          # Icon identifier
```

### Parameters

Define workflow parameters that are supplied by the caller at execution time:

```yaml
config:
  parameters:
    feature_name:
      type: string
      required: true
      description: "Name of the feature"

    target_env:
      type: string
      required: false
      default: "staging"
      description: "Deployment environment"

    skip_tests:
      type: boolean
      required: false
      default: false
      description: "Skip test execution"

    effort_points:
      type: integer
      required: false
      description: "Story point estimate"
```

Access parameters in expressions with `${{ parameters.name }}`:

```yaml
condition: "${{ parameters.skip_tests == false }}"
source: "${{ parameters.feature_name }}"
```

## Expression Syntax

Expressions are embedded in YAML fields using `${{ ... }}` syntax. They're evaluated at runtime against the workflow context.

### Property Access

Access values from the runtime context:

```
${{ parameters.feature_name }}      # Workflow parameter
${{ stages.research.outputs.summary }}  # Prior stage output
${{ context.deployment_id }}        # Context variable
${{ env.LOG_LEVEL }}                # Environment variable
${{ run.execution_id }}             # Run metadata
${{ workflow.name }}                # Workflow metadata
```

### Comparisons

```
${{ parameters.env == "production" }}
${{ parameters.skip_review != true }}
${{ effort_points > 5 }}
${{ effort_points <= 3 }}
${{ effort_points < 8 }}
${{ effort_points >= 1 }}
```

### Boolean Operators

```
${{ parameters.skip_review == false && parameters.env == "prod" }}
${{ parameters.env == "staging" || parameters.env == "dev" }}
${{ !parameters.skip_tests }}
```

### Ternary Operator

```
${{ parameters.env == "prod" ? "production" : "staging" }}
${{ stages.tests.outputs.passed ? "Ship it" : "Fix tests" }}
```

### Built-in Functions

#### `length(value)`

Returns the length of a string, array, or object:

```
${{ length(stages.research.outputs.findings) > 0 }}
${{ length(parameters.feature_name) <= 50 }}
```

#### `contains(container, item)`

Checks if a string or array contains an item:

```
${{ contains(parameters.feature_name, "auth") }}
${{ contains(stages.tests.outputs.failed_tests, "integration") }}
```

#### `toJSON(value)`

Serializes a value to JSON string:

```
${{ toJSON(stages.research.outputs) }}
```

#### `fromJSON(string)`

Parses a JSON string:

```
${{ fromJSON(stages.data.outputs.json_data).user.id }}
```

### String Literals

Use single or double quotes:

```
${{ "Feature: auth-v2" }}
${{ 'Feature approved' }}
```

### Number and Boolean Literals

```
${{ 42 }}
${{ 3.14 }}
${{ true }}
${{ false }}
${{ null }}
```

### Complete Expression Examples

```yaml
# Stage only runs if feature is auth-related
condition: "${{ contains(parameters.feature_name, 'auth') && parameters.target_env != 'prod' }}"

# Input resolved from prior stage or parameter
source: "${{ parameters.use_previous ? stages.research.outputs.data : parameters.default_data }}"

# Check array length
condition: "${{ length(stages.tests.outputs.failures) == 0 }}"

# Complex logic
condition: |
  ${{
    (parameters.skip_review == false && parameters.env == 'production')
    && stages.tests.outputs.passed == true
  }}
```

## Error Policies

Control how the workflow handles failures at the global and stage levels.

### Retry Behavior

Configure automatic retries with exponential backoff:

```yaml
error_policy:
  default_retry:
    max_attempts: 3
    initial_interval: "30s"
    backoff_multiplier: 2.0       # Delay multiplies each retry
    max_interval: "5m"            # Cap on maximum delay
    non_retryable_errors:         # Don't retry these
      - auth_failure
      - rate_limit_exhausted
```

**Example retry sequence** with the above config:
- Attempt 1: Fails immediately
- Retry 1: Wait 30s, retry
- Retry 2: Wait 60s, retry
- Retry 3: Wait 120s, retry (capped at 5m)
- After 3 attempts, execute `on_failure` action

### Global on_stage_failure

When a stage exhausts its retries, what happens next?

```yaml
error_policy:
  on_stage_failure: "halt"        # Stop the workflow (default)
  on_stage_failure: "continue"    # Continue remaining stages
  on_stage_failure: "rollback"    # Execute compensation (v2 feature)
```

### Stage-Level on_failure

Override for individual stages:

```yaml
- id: non-critical-task
  error_policy:
    on_failure: "continue"        # Fail but don't stop workflow
```

Options:
- `"halt"` - Stop the workflow (default)
- `"continue"` - Mark stage as failed, continue dependents if possible
- `"skip_dependents"` - Skip all downstream stages that depend on this one

### Timeouts

Set per-stage and global timeouts:

```yaml
config:
  timeout: "6h"                    # Entire workflow timeout

stages:
  - id: research
    error_policy:
      timeout: "2h"                # This stage times out after 2h
```

Duration format: `"30s"`, `"5m"`, `"30m"`, `"2h"`, `"6h"`

### Complete Error Policy Example

```yaml
error_policy:
  default_retry:
    max_attempts: 2
    initial_interval: "30s"
    backoff_multiplier: 2.0
    max_interval: "5m"
  on_stage_failure: "continue"

stages:
  - id: critical-step
    error_policy:
      retry:
        max_attempts: 3           # Override global default
        non_retryable_errors: [auth_failure]
      on_failure: "halt"          # This one halts on failure
      timeout: "1h"

  - id: optional-step
    error_policy:
      on_failure: "continue"      # This one continues on failure
      timeout: "30m"
```

## Hooks

Execute actions at workflow lifecycle points:

```yaml
hooks:
  on_start:
    notify:
      channel: "#engineering"
      message: "Starting feature workflow for ${{ parameters.feature_name }}"

  on_complete:
    notify:
      channel: "#engineering"
      message: "Feature shipped!"
    slack:
      webhook: "${{ env.SLACK_WEBHOOK }}"
    analytics:
      event: "workflow_completed"
      duration: "${{ run.duration_seconds }}"

  on_failure:
    notify:
      channel: "#engineering"
    pagerduty:
      severity: "error"
      title: "Feature workflow failed"
```

Hook payloads are arbitrary dicts interpreted by the execution engine.

## Dependencies and Execution Order

### Sequential Execution

```yaml
stages:
  - id: stage-1

  - id: stage-2
    depends_on: [stage-1]           # Wait for stage-1

  - id: stage-3
    depends_on: [stage-2]           # Wait for stage-2
```

Executes in order: stage-1 → stage-2 → stage-3

### Parallel Execution

```yaml
stages:
  - id: research

  - id: test
    depends_on: [research]          # Both run after research

  - id: implement
    depends_on: [research]

  - id: deploy
    depends_on: [test, implement]   # Waits for both
```

Executes as: research → (test | implement) in parallel → deploy

### DAG Resolution

The engine performs a topological sort to determine execution batches. Stages with no shared dependencies run in parallel (like GitHub Actions jobs).

## Parameters

### Defining Parameters

```yaml
config:
  parameters:
    feature_name:
      type: string
      required: true
      description: "What feature are we building?"

    target_env:
      type: string
      required: false
      default: "staging"
      description: "Deployment target"

    story_points:
      type: integer
      required: false
      description: "Effort estimate"

    is_hotfix:
      type: boolean
      required: false
      default: false
      description: "Is this a critical hotfix?"
```

### Using Parameters

```yaml
# In conditions
condition: "${{ parameters.is_hotfix == false }}"

# In inputs
inputs:
  feature_description:
    type: string
    source: "${{ parameters.feature_name }}"

# In instructions
roles:
  primary:
    artifact: "agent:researcher-v1"
    instructions: "Research the ${{ parameters.feature_name }} feature"
```

### Calling with Parameters

```bash
skillmeat workflow execute sdlc-feature-ship \
  --feature-name "auth-v2" \
  --target-env "production" \
  --story-points 13 \
  --is-hotfix false
```

## Context Binding

### Global Context Modules

Inject the same Context Modules into all stages:

```yaml
context:
  global_modules:
    - "ctx:coding-standards"
    - "ctx:architecture-patterns"
    - "ctx:api-guidelines"
```

### Per-Stage Context

Override or extend context for specific stages:

```yaml
stages:
  - id: implement
    context:
      modules:
        - "ctx:code-style-guide"      # Stage-specific
        - "ctx:database-patterns"
      memory:
        project_scope: current
        min_confidence: 0.8
        categories: [constraint, decision]
        max_tokens: 4000
```

### Memory Injection

Configure memory system integration:

```yaml
context:
  memory:
    project_scope: "current"          # Query current project's memories
    min_confidence: 0.75              # Only inject high-confidence memories
    categories:                       # Filter by memory type
      - constraint
      - decision
    max_tokens: 3000                  # Token budget for memories
```

## Project Overrides

Create `.skillmeat-workflow-overrides.yaml` in your project to override workflow settings without modifying the workflow file itself:

```yaml
# .skillmeat-workflow-overrides.yaml

sdlc-feature-ship:
  config:
    timeout: "4h"                    # Shorter timeout for this project
  stages:
    implement:
      roles:
        primary:
          model: "opus"              # Use opus instead of default
    approval:
      gate:
        approvers:
          - project-lead
          - qa-team
```

This is useful when you want to use the same workflow across multiple projects with different constraints.

## Troubleshooting

### Common Validation Errors

#### Error: "Unknown context namespace 'param'"

```
Bad:   source: "${{ param.feature_name }}"
Good:  source: "${{ parameters.feature_name }}"
```

Valid namespaces: `parameters`, `stages`, `context`, `env`, `run`, `workflow`

#### Error: "Stage 'implement' depends on unknown stage 'research'"

```
Bad:   depends_on: [research]       # Typo: 'reasearch'
Good:  depends_on: [research]       # Correct stage ID
```

Check that all referenced stage IDs match existing stages.

#### Error: "Property path 'research.outputs.sumary' not found"

```
Bad:   source: "${{ stages.research.outputs.sumary }}"
Good:  source: "${{ stages.research.outputs.summary }}"
```

Verify the exact output name defined in the prior stage's `outputs`.

#### Error: "on_failure must be one of ['halt', 'continue', 'skip_dependents']"

```
Bad:   on_failure: "retry"           # Not a valid option
Good:  on_failure: "continue"        # Valid option
```

Valid values: `"halt"`, `"continue"`, `"skip_dependents"`

#### Error: "Input 'feature_data' (required) not provided"

Make sure required inputs have a `source` that resolves to a value:

```yaml
inputs:
  feature_data:
    type: string
    required: true
    source: "${{ parameters.data }}"  # Must resolve to something
```

#### Error: "Type 'string' not recognized"

```
Bad:   type: "str"                   # Python type name
Good:  type: "string"                # SWDL type name
```

Valid SWDL types:
- `string`
- `boolean`
- `integer`
- `number` (float)
- `array<string>`
- `array<integer>`
- `array<object>`
- `object`

#### Error: "Circular dependency detected"

```yaml
Bad:
  - id: stage-a
    depends_on: [stage-b]
  - id: stage-b
    depends_on: [stage-a]            # Cycle!

Good:
  - id: stage-a
  - id: stage-b
    depends_on: [stage-a]            # One direction
```

Use `depends_on` to form a directed acyclic graph (DAG), not cycles.

#### Error: "Gate stage 'approval' missing required gate config"

```yaml
Bad:
  - id: approval
    type: gate
    # Missing gate config!

Good:
  - id: approval
    type: gate
    gate:
      kind: manual_approval
      approvers: [qa-lead]
      timeout: "24h"
```

Gate-type stages require a `gate` config.

#### Error: "Unknown function 'substr'"

```
Bad:   source: "${{ substr(parameters.name, 0, 3) }}"
Good:  source: "${{ contains(parameters.name, 'auth') }}"
```

Valid built-in functions:
- `length(x)`
- `contains(haystack, needle)`
- `toJSON(x)`
- `fromJSON(x)`

### Expression Debugging

Test expressions in isolation:

```python
from skillmeat.core.workflow.expressions import ExpressionParser, ExpressionContext

parser = ExpressionParser()
ctx = ExpressionContext(
    parameters={"feature_name": "auth-v2"},
    stages={
        "research": {
            "outputs": {"summary": "Found 3 patterns"},
            "status": "completed"
        }
    }
)

result = parser.evaluate("parameters.feature_name == 'auth-v2'", ctx)
print(result)  # True
```

### Validating a Workflow

```bash
# Validate syntax
python -m skillmeat.core.workflow --validate WORKFLOW.yaml

# Check for semantic issues
skillmeat workflow validate sdlc-feature-ship
```

### Testing a Workflow

Start a workflow execution with `--dry-run` to preview without executing:

```bash
skillmeat workflow execute sdlc-feature-ship \
  --feature-name "test-feature" \
  --dry-run
```

This shows the execution plan and expression resolutions without running agents.

## Best Practices

### 1. Use Semantic Stage IDs

```yaml
Good:   id: implement
        id: code-review
        id: deploy-production

Bad:    id: stage1
        id: s2
        id: x
```

### 2. Always Document Your Outputs

```yaml
outputs:
  feature_spec:
    type: string
    required: true
    description: "Complete feature specification including API contracts"

  acceptance_criteria:
    type: array<string>
    required: true
    description: "List of acceptance criteria for testing"
```

### 3. Make Inputs Explicit

```yaml
inputs:
  research_data:
    type: string
    required: true
    source: "${{ stages.research.outputs.summary }}"
    description: "Output from research stage"
```

### 4. Use Conditions for Optional Stages

```yaml
- id: code-review
  condition: "${{ parameters.skip_review == false }}"
  # ...
```

### 5. Set Appropriate Timeouts

```yaml
error_policy:
  timeout: "45m"       # Long-running but not infinite
```

### 6. Provide Context for Complex Workflows

```yaml
context:
  global_modules:
    - "ctx:sdlc-standards"
    - "ctx:architecture-guide"
  memory:
    min_confidence: 0.8
    categories: [decision, constraint]
```

### 7. Use Descriptive Handoff Formats

```yaml
handoff:
  format: markdown
  include_run_log: true
  summary_prompt: "Summarize key findings for the next stage"
```

### 8. Test with Dry-Run

Always dry-run complex workflows:

```bash
skillmeat workflow execute my-workflow --dry-run
```

## Next Steps

- **Run a workflow**: `skillmeat workflow execute WORKFLOW_ID --param-name value`
- **View execution**: Check the web UI at `http://localhost:3000/workflows`
- **Deploy a workflow**: Package it in a SkillMeat artifact
- **Share workflows**: Publish to the SkillMeat Marketplace

For more details, see the [Workflow Orchestration Schema Specification](../project_plans/design-specs/workflow-orchestration-schema-spec.md).
