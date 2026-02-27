"""Add workflows, workflow_stages, workflow_executions, and execution_steps tables.

Revision ID: 20260227_0900_add_workflow_tables
Revises: 20260226_1900_fix_artifact_fts_triggers
Create Date: 2026-02-27 09:00:00.000000+00:00

Background
----------
Introduces the workflow orchestration data layer for the SWDL (SkillMeat Workflow
Definition Language) runtime.  Workflows are first-class entities that compose
multiple agent stages into a directed acyclic graph (DAG); each execution is
tracked independently so historical runs are preserved even if the source
workflow is later archived or modified.

The design separates the *definition* layer (workflows + workflow_stages) from
the *execution* layer (workflow_executions + execution_steps).  Execution tables
deliberately snapshot the workflow name, version, and definition hash at launch
time so that records remain self-describing even after the originating workflow
is mutated.

Tables created
--------------
1. ``workflows``
   - Primary key: ``id`` (String, UUID hex, 32 chars)
   - ``name`` (String, non-null) — human-readable workflow name
   - ``description`` (Text, nullable)
   - ``version`` (String, non-null, default ``"1.0.0"``) — semantic version
   - ``status`` (String, non-null, default ``"draft"``) — lifecycle state
   - ``definition_yaml`` (Text, non-null) — raw SWDL YAML source
   - ``definition_hash`` (String, nullable) — content hash for change detection
   - ``tags_json`` (Text, nullable) — JSON array of string tags
   - ``global_context_module_ids_json`` (Text, nullable) — JSON array of module IDs
   - ``config_json`` (Text, nullable) — parameters, timeout, env overrides
   - ``error_policy_json`` (Text, nullable) — top-level error handling config
   - ``hooks_json`` (Text, nullable) — lifecycle hook definitions
   - ``ui_metadata_json`` (Text, nullable) — display/editor metadata
   - ``created_by`` (String, nullable) — originating user/agent identifier
   - ``created_at`` / ``updated_at`` (DateTime, non-null)
   - CheckConstraint: status IN ('draft', 'published', 'archived')
   - Indexes: ``idx_workflows_name``, ``idx_workflows_status``,
             ``idx_workflows_definition_hash``

2. ``workflow_stages``
   - Primary key: ``id`` (String, UUID hex)
   - ``workflow_id`` → ``workflows.id`` ON DELETE CASCADE
   - ``stage_id_ref`` (String, non-null) — the ``id`` field from SWDL YAML
     (e.g., ``"research"``)
   - ``name`` (String, non-null) — display name
   - ``description`` (Text, nullable)
   - ``order_index`` (Integer, non-null) — topological sort position
   - ``depends_on_json`` (Text, nullable) — JSON array of upstream stage_id_refs
   - ``condition`` (String, nullable) — CEL/boolean expression gating execution
   - ``stage_type`` (String, non-null, default ``"agent"``) — agent or gate
   - ``roles_json`` (Text, nullable) — eligible agent role definitions
   - ``inputs_json`` (Text, nullable) — declared input bindings
   - ``outputs_json`` (Text, nullable) — declared output bindings
   - ``context_json`` (Text, nullable) — context module references
   - ``error_policy_json`` (Text, nullable) — per-stage error handling
   - ``handoff_json`` (Text, nullable) — handoff/transition config
   - ``gate_json`` (Text, nullable) — gate-specific config (populated when
     stage_type = 'gate')
   - ``ui_metadata_json`` (Text, nullable)
   - ``created_at`` / ``updated_at`` (DateTime, non-null)
   - CheckConstraint: stage_type IN ('agent', 'gate')
   - Indexes: ``idx_workflow_stages_workflow_id``,
             ``idx_workflow_stages_stage_id_ref``

3. ``workflow_executions``
   - Primary key: ``id`` (String, UUID hex)
   - ``workflow_id`` → ``workflows.id`` (NO CASCADE — executions survive workflow
     archival/deletion for audit purposes)
   - ``workflow_name`` (String, non-null) — denormalised snapshot at launch time
   - ``workflow_version`` (String, non-null) — snapshot
   - ``workflow_definition_hash`` (String, nullable) — snapshot
   - ``status`` (String, non-null, default ``"pending"``) — execution lifecycle
   - ``parameters_json`` (Text, nullable) — runtime parameter overrides
   - ``overrides_json`` (Text, nullable) — stage-level overrides
   - ``trigger`` (String, non-null, default ``"manual"``) — how the run was started
   - ``started_at`` / ``completed_at`` (DateTime, nullable)
   - ``error_message`` (Text, nullable)
   - ``created_at`` / ``updated_at`` (DateTime, non-null)
   - CheckConstraint: status IN ('pending', 'running', 'paused', 'completed',
     'failed', 'cancelled')
   - CheckConstraint: trigger IN ('manual', 'scheduled', 'api')
   - Indexes: ``idx_workflow_executions_workflow_id``,
             ``idx_workflow_executions_status``,
             ``idx_workflow_executions_trigger``

4. ``execution_steps``
   - Primary key: ``id`` (String, UUID hex)
   - ``execution_id`` → ``workflow_executions.id`` ON DELETE CASCADE
   - ``stage_id_ref`` (String, non-null) — matches stage_id_ref in workflow_stages
   - ``stage_name`` (String, non-null) — denormalised display name
   - ``status`` (String, non-null, default ``"pending"``) — step lifecycle
   - ``attempt_number`` (Integer, non-null, default 1) — retry counter
   - ``agent_id`` (String, nullable) — executing agent identifier
   - ``context_consumed_json`` (Text, nullable) — context module data used
   - ``inputs_json`` (Text, nullable) — resolved inputs passed to the agent
   - ``outputs_json`` (Text, nullable) — outputs produced by the agent
   - ``logs_json`` (Text, nullable) — JSON array of log line strings
   - ``error_message`` (Text, nullable)
   - ``started_at`` / ``completed_at`` (DateTime, nullable)
   - ``duration_seconds`` (Float, nullable) — wall-clock duration
   - ``created_at`` / ``updated_at`` (DateTime, non-null)
   - CheckConstraint: status IN ('pending', 'running', 'completed', 'failed',
     'skipped', 'timed_out', 'cancelled')
   - Indexes: ``idx_execution_steps_execution_id``,
             ``idx_execution_steps_stage_id_ref``

Rollback
--------
Drop tables in strict reverse dependency order to satisfy FK constraints:
execution_steps → workflow_executions → workflow_stages → workflows.
No other tables or columns are modified by this migration.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260227_0900_add_workflow_tables"
down_revision: Union[str, None] = "20260226_1900_fix_artifact_fts_triggers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workflows, workflow_stages, workflow_executions, execution_steps.

    Tables are created in FK dependency order: workflows first (no external
    deps), workflow_stages next (references workflows), workflow_executions
    third (references workflows), and execution_steps last (references
    workflow_executions).
    """
    # -------------------------------------------------------------------------
    # 1. workflows
    # -------------------------------------------------------------------------
    op.create_table(
        "workflows",
        # Primary key — UUID hex, 32 chars
        sa.Column("id", sa.String(32), primary_key=True),
        # Identity fields
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Versioning and lifecycle
        sa.Column(
            "version",
            sa.String(),
            nullable=False,
            server_default="1.0.0",
            comment="Semantic version string, e.g. '1.0.0'",
        ),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="draft",
            comment="Lifecycle state: 'draft' | 'published' | 'archived'",
        ),
        # SWDL source
        sa.Column(
            "definition_yaml",
            sa.Text(),
            nullable=False,
            comment="Raw SWDL YAML source document",
        ),
        sa.Column(
            "definition_hash",
            sa.String(),
            nullable=True,
            comment="SHA-256 content hash of definition_yaml for change detection",
        ),
        # JSON payloads stored as Text to avoid schema churn
        sa.Column(
            "tags_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of string tags, e.g. '[\"nlp\", \"research\"]'",
        ),
        sa.Column(
            "global_context_module_ids_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of globally available context module IDs",
        ),
        sa.Column(
            "config_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: parameters, timeout, env overrides",
        ),
        sa.Column(
            "error_policy_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: top-level error handling policy",
        ),
        sa.Column(
            "hooks_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: lifecycle hook definitions",
        ),
        sa.Column(
            "ui_metadata_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: display and editor metadata",
        ),
        # Provenance
        sa.Column(
            "created_by",
            sa.String(),
            nullable=True,
            comment="Identifier of the user or agent that created the workflow",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraint: only recognised status values
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="check_workflow_status",
        ),
    )

    # Indexes on workflows
    op.create_index(
        "idx_workflows_name",
        "workflows",
        ["name"],
    )
    op.create_index(
        "idx_workflows_status",
        "workflows",
        ["status"],
    )
    op.create_index(
        "idx_workflows_definition_hash",
        "workflows",
        ["definition_hash"],
    )

    # -------------------------------------------------------------------------
    # 2. workflow_stages
    # -------------------------------------------------------------------------
    op.create_table(
        "workflow_stages",
        # Primary key — UUID hex
        sa.Column("id", sa.String(32), primary_key=True),
        # Parent workflow — CASCADE so stages are cleaned up with the workflow
        sa.Column(
            "workflow_id",
            sa.String(32),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to workflows.id — CASCADE DELETE",
        ),
        # SWDL stage identity — the 'id' field declared in the YAML
        sa.Column(
            "stage_id_ref",
            sa.String(),
            nullable=False,
            comment="SWDL stage identifier, e.g. 'research'",
        ),
        # Display fields
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # DAG position
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            comment="Topological sort position within the workflow",
        ),
        sa.Column(
            "depends_on_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of upstream stage_id_refs",
        ),
        sa.Column(
            "condition",
            sa.String(),
            nullable=True,
            comment="CEL/boolean expression; stage skipped when this evaluates to false",
        ),
        # Stage type — determines which additional JSON blobs are meaningful
        sa.Column(
            "stage_type",
            sa.String(),
            nullable=False,
            server_default="agent",
            comment="Stage variant: 'agent' | 'gate'",
        ),
        # Agent role and IO config
        sa.Column(
            "roles_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of eligible agent role definitions",
        ),
        sa.Column(
            "inputs_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: declared input bindings",
        ),
        sa.Column(
            "outputs_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: declared output bindings",
        ),
        sa.Column(
            "context_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: context module references",
        ),
        sa.Column(
            "error_policy_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: per-stage error handling policy",
        ),
        sa.Column(
            "handoff_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: handoff/transition configuration",
        ),
        # Gate-specific payload — only populated when stage_type = 'gate'
        sa.Column(
            "gate_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: gate criteria and approval config",
        ),
        sa.Column(
            "ui_metadata_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: display and editor metadata",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraint: only recognised stage types
        sa.CheckConstraint(
            "stage_type IN ('agent', 'gate')",
            name="check_workflow_stage_type",
        ),
    )

    # Indexes on workflow_stages
    op.create_index(
        "idx_workflow_stages_workflow_id",
        "workflow_stages",
        ["workflow_id"],
    )
    op.create_index(
        "idx_workflow_stages_stage_id_ref",
        "workflow_stages",
        ["stage_id_ref"],
    )

    # -------------------------------------------------------------------------
    # 3. workflow_executions
    # -------------------------------------------------------------------------
    # NOTE: No CASCADE on workflow_id FK — execution records must survive workflow
    # archival and deletion so that historical run data is preserved for audit.
    op.create_table(
        "workflow_executions",
        # Primary key — UUID hex
        sa.Column("id", sa.String(32), primary_key=True),
        # Workflow reference — intentionally no CASCADE (see note above)
        sa.Column(
            "workflow_id",
            sa.String(32),
            sa.ForeignKey("workflows.id"),
            nullable=False,
            comment="FK to workflows.id — NO CASCADE; executions outlive workflow changes",
        ),
        # Denormalised snapshot fields — self-describing without the parent row
        sa.Column(
            "workflow_name",
            sa.String(),
            nullable=False,
            comment="Snapshot of workflows.name at execution start",
        ),
        sa.Column(
            "workflow_version",
            sa.String(),
            nullable=False,
            comment="Snapshot of workflows.version at execution start",
        ),
        sa.Column(
            "workflow_definition_hash",
            sa.String(),
            nullable=True,
            comment="Snapshot of workflows.definition_hash at execution start",
        ),
        # Execution lifecycle
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
            comment=(
                "Execution state: 'pending' | 'running' | 'paused' | "
                "'completed' | 'failed' | 'cancelled'"
            ),
        ),
        # Runtime inputs
        sa.Column(
            "parameters_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: runtime parameter values",
        ),
        sa.Column(
            "overrides_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: stage-level configuration overrides",
        ),
        # How the execution was initiated
        sa.Column(
            "trigger",
            sa.String(),
            nullable=False,
            server_default="manual",
            comment="Execution trigger: 'manual' | 'scheduled' | 'api'",
        ),
        # Timing
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=True,
            comment="Wall-clock time when the first stage began",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
            comment="Wall-clock time when the execution reached a terminal state",
        ),
        # Error capture
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Top-level error message when status = 'failed'",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraints
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')",
            name="check_workflow_execution_status",
        ),
        sa.CheckConstraint(
            "trigger IN ('manual', 'scheduled', 'api')",
            name="check_workflow_execution_trigger",
        ),
    )

    # Indexes on workflow_executions
    op.create_index(
        "idx_workflow_executions_workflow_id",
        "workflow_executions",
        ["workflow_id"],
    )
    op.create_index(
        "idx_workflow_executions_status",
        "workflow_executions",
        ["status"],
    )
    op.create_index(
        "idx_workflow_executions_trigger",
        "workflow_executions",
        ["trigger"],
    )

    # -------------------------------------------------------------------------
    # 4. execution_steps
    # -------------------------------------------------------------------------
    op.create_table(
        "execution_steps",
        # Primary key — UUID hex
        sa.Column("id", sa.String(32), primary_key=True),
        # Parent execution — CASCADE so steps are cleaned up with the execution
        sa.Column(
            "execution_id",
            sa.String(32),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to workflow_executions.id — CASCADE DELETE",
        ),
        # Stage reference — correlates back to workflow_stages.stage_id_ref
        sa.Column(
            "stage_id_ref",
            sa.String(),
            nullable=False,
            comment="SWDL stage identifier; matches workflow_stages.stage_id_ref",
        ),
        sa.Column(
            "stage_name",
            sa.String(),
            nullable=False,
            comment="Denormalised stage display name at execution time",
        ),
        # Step lifecycle
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
            comment=(
                "Step state: 'pending' | 'running' | 'completed' | 'failed' | "
                "'skipped' | 'timed_out' | 'cancelled'"
            ),
        ),
        # Retry tracking
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Monotonically increasing retry counter; starts at 1",
        ),
        # Execution context
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=True,
            comment="Identifier of the agent process that handled this step",
        ),
        sa.Column(
            "context_consumed_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: context module data injected into the agent",
        ),
        # IO capture
        sa.Column(
            "inputs_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: resolved inputs passed to the agent",
        ),
        sa.Column(
            "outputs_json",
            sa.Text(),
            nullable=True,
            comment="JSON object: outputs produced by the agent",
        ),
        # Observability
        sa.Column(
            "logs_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of log line strings emitted during this step",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message when status = 'failed' or 'timed_out'",
        ),
        # Timing
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=True,
            comment="Wall-clock time when the step started executing",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
            comment="Wall-clock time when the step reached a terminal state",
        ),
        sa.Column(
            "duration_seconds",
            sa.Float(),
            nullable=True,
            comment="Wall-clock duration in seconds (completed_at - started_at)",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraint: only recognised step status values
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'timed_out', 'cancelled')",
            name="check_execution_step_status",
        ),
    )

    # Indexes on execution_steps
    op.create_index(
        "idx_execution_steps_execution_id",
        "execution_steps",
        ["execution_id"],
    )
    op.create_index(
        "idx_execution_steps_stage_id_ref",
        "execution_steps",
        ["stage_id_ref"],
    )


def downgrade() -> None:
    """Drop execution_steps, workflow_executions, workflow_stages, workflows.

    Tables are dropped in strict reverse dependency order to satisfy FK
    constraints.  All workflow definitions, stage records, execution history,
    and step detail will be permanently lost.
    """
    # Drop leaf table first (FK references workflow_executions)
    op.drop_index("idx_execution_steps_stage_id_ref", "execution_steps")
    op.drop_index("idx_execution_steps_execution_id", "execution_steps")
    op.drop_table("execution_steps")

    # Drop execution table (FK references workflows)
    op.drop_index("idx_workflow_executions_trigger", "workflow_executions")
    op.drop_index("idx_workflow_executions_status", "workflow_executions")
    op.drop_index("idx_workflow_executions_workflow_id", "workflow_executions")
    op.drop_table("workflow_executions")

    # Drop stage table (FK references workflows)
    op.drop_index("idx_workflow_stages_stage_id_ref", "workflow_stages")
    op.drop_index("idx_workflow_stages_workflow_id", "workflow_stages")
    op.drop_table("workflow_stages")

    # Drop root table last
    op.drop_index("idx_workflows_definition_hash", "workflows")
    op.drop_index("idx_workflows_status", "workflows")
    op.drop_index("idx_workflows_name", "workflows")
    op.drop_table("workflows")
