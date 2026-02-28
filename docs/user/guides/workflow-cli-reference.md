---
title: Workflow CLI Reference
description: Complete reference for all `skillmeat workflow` CLI commands, options, and examples
audience: [users]
tags: [cli, workflow, reference, commands]
created: 2026-02-27
updated: 2026-02-27
category: cli-reference
status: published
related_documents:
  - docs/user/guides/workflow-authoring.md
  - docs/user/guides/workflow-ui-guide.md
---

# Workflow CLI Reference

Complete reference for the `skillmeat workflow` command group. All workflow management, execution, and monitoring operations are accessed through these subcommands.

## Overview

The `skillmeat workflow` group manages multi-stage, agent-driven pipelines defined in YAML. Commands enable creation, validation, execution planning, runtime management, and execution history inspection.

### Feature Flag

Workflow commands are gated behind the `SKILLMEAT_WORKFLOW_ENGINE_ENABLED` environment variable (default: `true`). Disable with:

```bash
export SKILLMEAT_WORKFLOW_ENGINE_ENABLED=false
```

When disabled, the workflow group remains discoverable via `--help` but subcommands exit gracefully with a feature flag message.

### Global Options

All workflow subcommands support:

- **`--debug`** (hidden flag)
  Enable debug output for troubleshooting. Shows additional metadata (DB IDs, parsing details, etc.).

## Commands

### `skillmeat workflow create`

Import a workflow YAML file into the collection.

**Usage:**

```bash
skillmeat workflow create PATH [--name NAME] [--force]
```

**Arguments:**

- `PATH` (required)
  File path to the workflow YAML file. Must exist and be readable.

**Options:**

- `--name NAME`
  Override the workflow name extracted from the YAML `workflow.name` field. Useful for renaming on import.

- `--force` / `-f`
  Overwrite an existing workflow with the same name. Both filesystem and database entries are replaced.

**What it does:**

1. Reads and validates the YAML file
2. Stores the YAML in the collection directory (`~/.skillmeat/collection/workflows/<name>/`)
3. Updates the collection manifest
4. Persists the workflow definition to the database

**Exit codes:**

- `0` — Success
- `1` — Parse error, validation failure, or file I/O error

**Examples:**

```bash
# Import a workflow from a YAML file
skillmeat workflow create ./deployment-pipeline.yaml

# Import with a custom name
skillmeat workflow create ./my-workflow.yaml --name "custom-pipeline"

# Force overwrite an existing workflow
skillmeat workflow create ./my-workflow.yaml --force
```

**Output:**

On success, displays a table with:
- Workflow name, version, and stage count
- Database ID
- Collection location
- Tags and description (if present)

---

### `skillmeat workflow list`

List all workflows in the collection with optional filtering.

**Usage:**

```bash
skillmeat workflow list [--status STATUS] [--tag TAG] [--format FORMAT]
```

**Options:**

- `--status STATUS`
  Filter by workflow status. Supported values: `draft`, `active`, `archived`.

- `--tag TAG`
  Filter by tag name. Only workflows with the specified tag are shown.

- `--format FORMAT`
  Output format: `table` (default, Rich table) or `json` (JSON array).
  Default: `table`

**Exit codes:**

- `0` — Success (even if no results match filters)
- `1` — Query error

**Examples:**

```bash
# List all workflows
skillmeat workflow list

# List only active workflows
skillmeat workflow list --status active

# Filter by tag
skillmeat workflow list --tag ci

# List all archived workflows in JSON
skillmeat workflow list --status archived --format json

# Combine filters
skillmeat workflow list --tag ci --status active
```

**Output (table mode):**

Rich table with columns:
- **Name** — Workflow name (bold)
- **Version** — Semantic version
- **Stages** — Count of stages in the workflow
- **Status** — Status (green for `active`, yellow for `draft`, dim for `archived`)
- **Tags** — Comma-separated tags, or `-` if none
- **Updated** — Last modification timestamp (YYYY-MM-DD HH:MM)

**Output (JSON mode):**

Array of objects with fields:
```json
[
  {
    "id": "uuid",
    "name": "string",
    "version": "semver",
    "stages": 5,
    "status": "active|draft|archived",
    "tags": ["tag1", "tag2"],
    "description": "string or null",
    "project_id": "string",
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
]
```

---

### `skillmeat workflow show`

Display detailed information about a specific workflow.

**Usage:**

```bash
skillmeat workflow show NAME
```

**Arguments:**

- `NAME` (required)
  Workflow name (case-sensitive).

**Exit codes:**

- `0` — Success
- `1` — Workflow not found or query error

**Examples:**

```bash
# Show a workflow's definition
skillmeat workflow show my-workflow

# Show a code review pipeline
skillmeat workflow show code-review-pipeline
```

**Output:**

Displays three Rich panels:

1. **Workflow Definition**
   Table with metadata:
   - Name, version, status (colored)
   - Stage count, description, tags
   - Created and updated timestamps
   - DB ID (shown only with `--debug`)

2. **Stages**
   Table with columns:
   - `#` — Stage index (1-based)
   - **Stage Name** — Stage identifier
   - **Type** — `agent`, `gate`, or `fan_out` (colored)
   - **Depends On** — Comma-separated list of dependencies, or `-` if independent
   - **Timeout** — Timeout duration in seconds, or `-` if not set

3. **Last Execution** (informational)
   Table with:
   - Run ID, status (colored), start time
   - Duration (if completed), or "in progress" (if running)
   - Shows "-" if no executions recorded

---

### `skillmeat workflow validate`

Validate a workflow YAML file without importing it.

**Usage:**

```bash
skillmeat workflow validate PATH [--strict]
```

**Arguments:**

- `PATH` (required)
  File path to the workflow YAML file.

**Options:**

- `--strict`
  Treat warnings as errors. Exit with code 1 if any warnings are present (in addition to errors).

**What it does:**

Runs all static analysis passes:
- YAML parsing
- Schema validation
- Expression syntax checking
- DAG cycle detection
- Artifact format validation

The collection is never modified.

**Exit codes:**

- `0` — Valid (no errors, or only warnings if `--strict` is not used)
- `1` — Parse error, validation error, or warnings with `--strict`

**Examples:**

```bash
# Validate a workflow file
skillmeat workflow validate ./my-workflow.yaml

# Strict validation (warnings = errors)
skillmeat workflow validate ./my-workflow.yaml --strict
```

**Output:**

Displays:
- Validation errors (red, prefixed `[red]Error:[/red]`)
- Validation warnings (yellow, prefixed `[yellow]Warning:[/yellow]`)
- For each issue: category, stage ID (if relevant), field name, and message

On success with no issues:
```
[green]Workflow validation passed.[/green]
```

---

### `skillmeat workflow plan`

Preview the execution plan for a workflow without running it.

**Usage:**

```bash
skillmeat workflow plan NAME [--param KEY=VALUE ...]
```

**Arguments:**

- `NAME` (required)
  Workflow name.

**Options:**

- `--param KEY=VALUE` (repeatable)
  Override a workflow parameter. Repeat to pass multiple parameters.
  Format: `--param key1=value1 --param key2=value2`

**What it does:**

1. Resolves workflow parameters (from YAML defaults + CLI overrides)
2. Computes parallel execution batches via topological sort
3. Displays the execution plan as a Rich tree (no execution occurs)

**Exit codes:**

- `0` — Success
- `1` — Validation error, workflow not found, or plan generation failure

**Examples:**

```bash
# View execution plan
skillmeat workflow plan my-workflow

# Override a parameter
skillmeat workflow plan my-workflow --param environment=production

# Multiple parameter overrides
skillmeat workflow plan my-workflow --param feature=auth-v2 --param env=prod
```

**Output:**

1. **Execution Plan Header**
   Panel with:
   - Workflow name and version
   - Number of batches and total stages
   - Parameter overrides (if any)

2. **Batch Trees**
   For each batch, a Rich tree showing:
   - Batch index and label (e.g., "Batch 1 [dim](parallel)[/dim]")
   - Stages within the batch:
     - Stage name, type (colored: `agent`/`gate`/`fan_out`), and status (`pending`)
     - Stage ID, dependencies, and configuration

   **For agent stages**, additional details:
   - Primary artifact and model
   - Tools, inputs (with sources), and outputs
   - Context modules, conditions, and timeout

   **For gate stages**, additional details:
   - Approvers list
   - Timeout duration

3. **Footer**
   Estimated total execution time (based on timeouts and sequential dependencies)

---

### `skillmeat workflow run`

Execute a workflow with Rich live progress display.

**Usage:**

```bash
skillmeat workflow run NAME [--param KEY=VALUE ...] [--dry-run]
```

**Arguments:**

- `NAME` (required)
  Workflow name.

**Options:**

- `--param KEY=VALUE` (repeatable)
  Override a workflow parameter.

- `--dry-run`
  Show the execution plan without running it. Equivalent to `skillmeat workflow plan NAME --param ...`.

**What it does:**

1. Resolves parameters and generates the execution plan
2. If `--dry-run`: displays the plan and exits
3. Otherwise: executes the workflow with real-time progress tracking

During execution:
- Batches run sequentially
- Stages within a batch run in parallel
- Gate stages pause for approvals
- Progress table updates with stage status, start times, and output summaries

**Exit codes:**

- `0` — Execution completed successfully
- `1` — Validation error, execution failure, or user cancellation

**Examples:**

```bash
# Execute a workflow
skillmeat workflow run my-workflow

# Preview the execution plan without running
skillmeat workflow run my-workflow --dry-run

# Run with parameter overrides
skillmeat workflow run my-workflow --param env=staging --param feature=v2

# Execute and monitor progress
skillmeat workflow run deploy-pipeline
```

**Output (execution):**

Live-updating Rich progress table:
- **Batch** — Batch index
- **Stage** — Stage name
- **Type** — Stage type (agent/gate/fan_out)
- **Status** — Current status with color coding:
  - `pending` (yellow)
  - `running` (cyan)
  - `waiting_for_approval` (magenta) [gates only]
  - `completed` (green)
  - `failed` (red)
  - `skipped` (dim)
  - `cancelled` (dim)
- **Start Time** — When the stage began
- **Summary** — Brief output or error message

**Output (on completion):**

Summary table with:
- Total execution time
- Success/failure summary
- Stage-by-stage results
- Any error messages or logs (with `--logs` flag in `runs` command)

---

### `skillmeat workflow runs`

List or inspect workflow executions.

**Usage (list mode):**

```bash
skillmeat workflow runs [--workflow NAME] [--status STATUS] [--limit N]
```

**Usage (detail mode):**

```bash
skillmeat workflow runs RUN_ID [--logs]
```

**Arguments:**

- `RUN_ID` (optional)
  Execution UUID. When provided, shows detailed metadata for that execution. When omitted, lists recent executions.

**Options:**

- `--workflow NAME`
  Filter by workflow name (list mode only).

- `--status STATUS`
  Filter by execution status (list mode only).
  Supported values: `pending`, `running`, `completed`, `failed`, `cancelled`.

- `--logs`
  Include error messages and output summaries for each stage (detail mode only).

- `--limit N`
  Maximum number of executions to show in list mode.
  Default: `20`

**Exit codes:**

- `0` — Success
- `1` — Execution in failed/cancelled state (detail mode), or no results found

**Examples:**

```bash
# List recent executions
skillmeat workflow runs

# List executions for a specific workflow
skillmeat workflow runs --workflow my-workflow

# Filter by status
skillmeat workflow runs --status failed

# Show detailed information for an execution
skillmeat workflow runs abc123def456

# Show execution details with stage output
skillmeat workflow runs abc123def456 --logs

# Combine filters
skillmeat workflow runs --workflow deploy-pipeline --status completed --limit 10
```

**Output (list mode):**

Rich table with columns:
- **Run ID** — Execution UUID (first 12 characters)
- **Workflow ID** — Workflow UUID (first 12 characters)
- **Status** — Execution status (colored)
- **Started** — Start timestamp (YYYY-MM-DD HH:MM)
- **Duration** — Elapsed time (e.g., "5m 23s") or "-" if still running

Footer shows count and message to use run ID for details.

**Output (detail mode):**

1. **Execution Metadata Panel**
   Table with:
   - Run ID, workflow ID
   - Status (colored)
   - Started and completed timestamps
   - Total duration
   - Error message (if failed)
   - Parameters (JSON, if any)

2. **Per-Stage Table**
   Columns:
   - **Stage** — Stage name
   - **Type** — Stage type (agent/gate/fan_out)
   - **Status** — Stage status (colored)
   - **Duration** — Elapsed time for stage (e.g., "30s")
   - **Error / Output** — Error message or JSON output (only with `--logs`)

---

### `skillmeat workflow approve`

Approve a gate stage that is waiting for approval.

**Usage:**

```bash
skillmeat workflow approve RUN_ID [--yes]
```

**Arguments:**

- `RUN_ID` (required)
  Execution UUID.

**Options:**

- `--yes` / `-y`
  Skip confirmation prompt and approve immediately.

**What it does:**

1. Fetches the execution metadata
2. Locates the gate stage in `waiting_for_approval` state
3. Prompts for confirmation (unless `--yes`)
4. Marks the stage as approved so execution can continue

**Exit codes:**

- `0` — Approval successful
- `1` — Execution not found, no gate awaiting approval, or user aborted confirmation

**Examples:**

```bash
# Approve a gate stage (with confirmation prompt)
skillmeat workflow approve abc123def456

# Approve without confirmation
skillmeat workflow approve abc123def456 --yes

# Approve with shorthand flag
skillmeat workflow approve abc123def456 -y
```

**Output:**

Confirmation panel showing:
- Run ID (first 12 characters)
- Current execution status
- Number of stages in the execution

After approval:
```
[green]Approved:[/green] Execution abc123def456 — gate stage unlocked.
```

---

### `skillmeat workflow cancel`

Cancel a running or pending workflow execution.

**Usage:**

```bash
skillmeat workflow cancel RUN_ID [--yes]
```

**Arguments:**

- `RUN_ID` (required)
  Execution UUID.

**Options:**

- `--yes` / `-y`
  Skip confirmation prompt and cancel immediately.

**What it does:**

1. Fetches the execution metadata
2. Confirms with the user (unless `--yes`)
3. Marks all active stages as `cancelled`
4. Sets the execution status to `cancelled`

If the execution is already in a terminal state (`completed`, `failed`, `cancelled`), the command exits with a message and no changes are made.

**Exit codes:**

- `0` — Cancellation successful, or execution already in terminal state
- `1` — Execution not found or error during cancellation

**Examples:**

```bash
# Cancel an execution (with confirmation)
skillmeat workflow cancel abc123def456

# Cancel without confirmation
skillmeat workflow cancel abc123def456 --yes

# Cancel with shorthand flag
skillmeat workflow cancel abc123def456 -y
```

**Output:**

Confirmation panel showing:
- Run ID
- Current status
- Number of stages

After cancellation:
```
[green]Cancelled:[/green] Execution abc123def456 — 3 stage(s) marked cancelled.
```

---

## Command Workflow Examples

### Example 1: Create, Validate, Plan, and Run

```bash
# Validate the YAML first (optional but recommended)
skillmeat workflow validate ./my-deployment.yaml

# Create the workflow in the collection
skillmeat workflow create ./my-deployment.yaml --name "deployment-v2"

# Preview the execution plan
skillmeat workflow plan deployment-v2

# Run the workflow
skillmeat workflow run deployment-v2

# Check execution status
skillmeat workflow runs deployment-v2
```

### Example 2: Run with Parameters

```bash
# List workflows to find the right one
skillmeat workflow list --tag ci

# Show the workflow to understand parameters
skillmeat workflow show ci-pipeline

# Plan with production environment override
skillmeat workflow plan ci-pipeline --param env=production

# Run with parameters
skillmeat workflow run ci-pipeline --param env=production --param skip_tests=false
```

### Example 3: Monitor and Manage Execution

```bash
# Start an execution
skillmeat workflow run my-workflow

# In another terminal, watch recent executions
skillmeat workflow runs

# When a gate is waiting, approve it
skillmeat workflow approve abc123def456

# If something goes wrong, cancel
skillmeat workflow cancel abc123def456 --yes

# View detailed execution history with logs
skillmeat workflow runs abc123def456 --logs
```

### Example 4: Batch Operations

```bash
# List all active workflows
skillmeat workflow list --status active

# Update a workflow definition
skillmeat workflow create ./updated.yaml --force

# Check recent executions across all workflows
skillmeat workflow runs --limit 50

# Find failed executions
skillmeat workflow runs --status failed
```

---

## Error Handling

### Common Errors

**`Workflow engine is coming soon.`**
The workflow feature flag is disabled.
**Fix:** Set `SKILLMEAT_WORKFLOW_ENGINE_ENABLED=true` in your environment.

**`Workflow '[name]' not found.`**
The specified workflow name doesn't exist.
**Fix:** Use `skillmeat workflow list` to see available workflows, or check the spelling.

**`[red]Workflow validation failed:[/red]`**
The YAML file has syntax or schema errors.
**Fix:** Review the error messages and correct the YAML, then use `skillmeat workflow validate` to test.

**`Error: Cannot read file: [error]`**
The specified file path doesn't exist or is unreadable.
**Fix:** Verify the file path and permissions.

**`Error: Failed to generate plan`**
The plan generation failed due to invalid parameters or DAG issues.
**Fix:** Check parameter values and workflow dependencies with `skillmeat workflow show`.

### Debug Output

For more detailed troubleshooting information, use the `--debug` flag:

```bash
skillmeat workflow --debug plan my-workflow
skillmeat workflow --debug run my-workflow
```

Debug output includes:
- File paths (for `create`, `validate`)
- DB IDs (for `show`)
- Full tracebacks (for errors)
- Parsing and validation details

---

## Integration with Other Commands

The workflow CLI integrates with other SkillMeat features:

- **Syncing workflows**: Use `skillmeat sync` to synchronize workflow artifacts between projects and upstream sources
- **Bundling workflows**: Include workflows in artifact bundles with `skillmeat bundle`
- **Listing artifacts**: Find workflows alongside other artifacts with `skillmeat list`
- **Searching**: Search workflows by name or tag with `skillmeat search`

---

## See Also

- [Workflow Authoring Guide](workflow-authoring.md) — Learn how to write YAML workflow definitions
- [Workflow Web UI Guide](workflow-ui-guide.md) — Using the web interface for workflow management
- [Workflow Execution API](../../api/workflow-execution.md) — Programmatic workflow control via REST API
