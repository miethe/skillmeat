"""Tests for skillmeat.core.workflow.parser and skillmeat.core.workflow.defaults.

Coverage:
  Parser (parse_workflow):
    - minimal YAML
    - full SDLC YAML
    - JSON format
    - file-not-found error
    - unsupported extension error
    - invalid YAML syntax error
    - invalid JSON syntax error
    - Pydantic validation failure (missing required field)

  Defaults (apply_defaults):
    - workflow config.timeout default ("2h")
    - agent stage gets 30m timeout when error_policy absent
    - gate stage gets 24h timeout when error_policy absent
    - global retry inherited by stage with no error_policy
    - explicit stage timeout is not overwritten
    - stage without handoff gets HandoffConfig(format="structured")
    - roundtrip idempotency: apply_defaults(apply_defaults(wf)) == apply_defaults(wf)
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, Dict

import pytest

from skillmeat.core.workflow.defaults import (
    DEFAULT_AGENT_STAGE_TIMEOUT,
    DEFAULT_GATE_STAGE_TIMEOUT,
    DEFAULT_WORKFLOW_TIMEOUT,
    apply_defaults,
)
from skillmeat.core.workflow.exceptions import WorkflowParseError
from skillmeat.core.workflow.models import (
    ErrorPolicy,
    GlobalErrorPolicy,
    HandoffConfig,
    RetryPolicy,
    StageDefinition,
    StageRoles,
    RoleAssignment,
    WorkflowDefinition,
    WorkflowMetadata,
)
from skillmeat.core.workflow.parser import parse_workflow


# ---------------------------------------------------------------------------
# Shared YAML / dict helpers
# ---------------------------------------------------------------------------

MINIMAL_WORKFLOW_DICT: Dict[str, Any] = {
    "workflow": {
        "id": "test-workflow",
        "name": "Test Workflow",
    },
    "stages": [
        {
            "id": "stage-one",
            "name": "Stage One",
            "roles": {
                "primary": {
                    "artifact": "agent:test-agent",
                },
            },
        },
    ],
}

MINIMAL_WORKFLOW_YAML = textwrap.dedent(
    """\
    workflow:
      id: "test-workflow"
      name: "Test Workflow"

    stages:
      - id: "stage-one"
        name: "Stage One"
        roles:
          primary:
            artifact: "agent:test-agent"
    """
)

FULL_SDLC_YAML = textwrap.dedent(
    """\
    workflow:
      id: "sdlc-feature-ship"
      name: "Ship a Feature (SDLC)"
      version: "1.0.0"
      description: "End-to-end workflow for shipping a feature."
      author: "miethe"
      tags:
        - "sdlc"
        - "feature"
        - "full-stack"
      ui:
        color: "#4A90D9"
        icon: "rocket"

    config:
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
          description: "Skip the review stage"
      timeout: "4h"
      env:
        PROJECT_ROOT: "${{ parameters.feature_name }}"

    context:
      global_modules:
        - "ctx:repo-rules"
        - "ctx:coding-standards"
      memory:
        project_scope: "current"
        min_confidence: 0.7
        categories:
          - "constraint"
          - "decision"
        max_tokens: 2000

    stages:
      - id: "research"
        name: "Research & Discovery"
        description: "Investigate the problem space."
        depends_on: []
        type: "agent"
        roles:
          primary:
            artifact: "agent:researcher-v1"
            model: "opus"
            instructions: "Focus on identifying prior art and risks."
          tools:
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
        error_policy:
          on_failure: "halt"
          timeout: "45m"
          retry:
            max_attempts: 2
            initial_interval: "30s"
            backoff_multiplier: 2.0
            max_interval: "5m"
        handoff:
          format: "structured"
          include_run_log: false

      - id: "approval-gate"
        name: "Review Approval"
        type: "gate"
        depends_on:
          - "research"
        gate:
          kind: "manual_approval"
          approvers:
            - "miethe"
          timeout: "24h"
          on_timeout: "halt"
          message: "Please review the research summary."
        handoff:
          format: "structured"
          include_run_log: false

    error_policy:
      default_retry:
        max_attempts: 2
        initial_interval: "30s"
        backoff_multiplier: 2.0
        max_interval: "5m"
      on_stage_failure: "halt"

    hooks:
      on_start:
        notify: "slack:#deployments"
      on_complete:
        notify: "slack:#deployments"
      on_failure:
        notify: "slack:#alerts"
    """
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_yaml_file(tmp_path: Path) -> Path:
    """Write minimal workflow YAML to a temp file and return its path."""
    f = tmp_path / "minimal.yaml"
    f.write_text(MINIMAL_WORKFLOW_YAML, encoding="utf-8")
    return f


@pytest.fixture()
def full_sdlc_yaml_file(tmp_path: Path) -> Path:
    """Write full SDLC workflow YAML to a temp file and return its path."""
    f = tmp_path / "sdlc.yaml"
    f.write_text(FULL_SDLC_YAML, encoding="utf-8")
    return f


@pytest.fixture()
def minimal_json_file(tmp_path: Path) -> Path:
    """Write minimal workflow as JSON to a temp file and return its path."""
    f = tmp_path / "minimal.json"
    f.write_text(json.dumps(MINIMAL_WORKFLOW_DICT), encoding="utf-8")
    return f


@pytest.fixture()
def minimal_workflow() -> WorkflowDefinition:
    """Return a minimal parsed WorkflowDefinition for defaults tests."""
    return WorkflowDefinition.model_validate(MINIMAL_WORKFLOW_DICT)


@pytest.fixture()
def agent_stage_no_policy() -> StageDefinition:
    """Agent stage with no error_policy and no handoff."""
    return StageDefinition(
        id="agent-stage",
        name="Agent Stage",
        type="agent",
        roles=StageRoles(
            primary=RoleAssignment(artifact="agent:test-agent"),
        ),
    )


@pytest.fixture()
def gate_stage_no_policy() -> StageDefinition:
    """Gate stage with no error_policy and no handoff."""
    return StageDefinition(
        id="gate-stage",
        name="Gate Stage",
        type="gate",
    )


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParseWorkflowYAML:
    """parse_workflow correctly loads valid YAML workflow files."""

    def test_parse_minimal_yaml(self, minimal_yaml_file: Path) -> None:
        """A minimal workflow YAML parses to a WorkflowDefinition."""
        wf = parse_workflow(minimal_yaml_file)

        assert isinstance(wf, WorkflowDefinition)
        assert wf.workflow.id == "test-workflow"
        assert wf.workflow.name == "Test Workflow"
        assert len(wf.stages) == 1
        assert wf.stages[0].id == "stage-one"

    def test_parse_full_sdlc_yaml(self, full_sdlc_yaml_file: Path) -> None:
        """Full SDLC YAML parses and all major fields are populated correctly."""
        wf = parse_workflow(full_sdlc_yaml_file)

        # Workflow metadata
        assert wf.workflow.id == "sdlc-feature-ship"
        assert wf.workflow.name == "Ship a Feature (SDLC)"
        assert wf.workflow.version == "1.0.0"
        assert wf.workflow.author == "miethe"
        assert "sdlc" in wf.workflow.tags
        assert wf.workflow.ui is not None
        assert wf.workflow.ui.color == "#4A90D9"
        assert wf.workflow.ui.icon == "rocket"

        # Config
        assert wf.config.timeout == "4h"
        assert "feature_name" in wf.config.parameters
        assert wf.config.parameters["feature_name"].required is True
        assert wf.config.parameters["target_branch"].default == "main"
        assert wf.config.env["PROJECT_ROOT"] == "${{ parameters.feature_name }}"

        # Context
        assert wf.context is not None
        assert "ctx:repo-rules" in wf.context.global_modules
        assert wf.context.memory is not None
        assert wf.context.memory.min_confidence == 0.7
        assert wf.context.memory.max_tokens == 2000

        # Stages
        assert len(wf.stages) == 2
        research = wf.stages[0]
        assert research.id == "research"
        assert research.type == "agent"
        assert research.roles is not None
        assert research.roles.primary.artifact == "agent:researcher-v1"
        assert research.roles.primary.model == "opus"
        assert "skill:web-search" in research.roles.tools
        assert "feature_name" in research.inputs
        assert "research_summary" in research.outputs
        assert research.error_policy is not None
        assert research.error_policy.timeout == "45m"
        assert research.error_policy.retry is not None
        assert research.error_policy.retry.max_attempts == 2

        gate = wf.stages[1]
        assert gate.id == "approval-gate"
        assert gate.type == "gate"
        assert gate.gate is not None
        assert gate.gate.approvers == ["miethe"]

        # Global error_policy
        assert wf.error_policy is not None
        assert wf.error_policy.on_stage_failure == "halt"
        assert wf.error_policy.default_retry is not None
        assert wf.error_policy.default_retry.max_attempts == 2

        # Hooks
        assert wf.hooks is not None
        assert wf.hooks.on_start == {"notify": "slack:#deployments"}
        assert wf.hooks.on_failure == {"notify": "slack:#alerts"}

    def test_parse_yml_extension(self, tmp_path: Path) -> None:
        """The .yml extension is accepted as an alias for .yaml."""
        f = tmp_path / "workflow.yml"
        f.write_text(MINIMAL_WORKFLOW_YAML, encoding="utf-8")
        wf = parse_workflow(f)
        assert wf.workflow.id == "test-workflow"


class TestParseWorkflowJSON:
    """parse_workflow correctly loads valid JSON workflow files."""

    def test_parse_minimal_json(self, minimal_json_file: Path) -> None:
        """A minimal workflow JSON parses to a WorkflowDefinition."""
        wf = parse_workflow(minimal_json_file)

        assert isinstance(wf, WorkflowDefinition)
        assert wf.workflow.id == "test-workflow"
        assert wf.workflow.name == "Test Workflow"
        assert len(wf.stages) == 1
        assert wf.stages[0].id == "stage-one"


class TestParseWorkflowErrors:
    """parse_workflow raises WorkflowParseError for all error conditions."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """A non-existent path raises WorkflowParseError with 'not found' message."""
        missing = tmp_path / "does_not_exist.yaml"

        with pytest.raises(WorkflowParseError) as exc_info:
            parse_workflow(missing)

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.path == missing

    def test_unsupported_extension_toml(self, tmp_path: Path) -> None:
        """A .toml file raises WorkflowParseError about unsupported extension."""
        f = tmp_path / "workflow.toml"
        f.write_text("[workflow]\nid = 'test'\n", encoding="utf-8")

        with pytest.raises(WorkflowParseError) as exc_info:
            parse_workflow(f)

        error_str = str(exc_info.value)
        assert ".toml" in error_str

    def test_unsupported_extension_txt(self, tmp_path: Path) -> None:
        """A .txt extension raises WorkflowParseError about unsupported extension."""
        f = tmp_path / "workflow.txt"
        f.write_text(MINIMAL_WORKFLOW_YAML, encoding="utf-8")

        with pytest.raises(WorkflowParseError):
            parse_workflow(f)

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Malformed YAML raises WorkflowParseError wrapping the YAML error."""
        f = tmp_path / "bad.yaml"
        f.write_text(
            textwrap.dedent(
                """\
                workflow:
                  id: "test"
                  name: [unclosed bracket
                """
            ),
            encoding="utf-8",
        )

        with pytest.raises(WorkflowParseError) as exc_info:
            parse_workflow(f)

        assert "yaml" in str(exc_info.value).lower()

    def test_invalid_json_syntax(self, tmp_path: Path) -> None:
        """Malformed JSON raises WorkflowParseError wrapping the JSON error."""
        f = tmp_path / "bad.json"
        f.write_text('{"workflow": {"id": "test", INVALID}', encoding="utf-8")

        with pytest.raises(WorkflowParseError) as exc_info:
            parse_workflow(f)

        assert "json" in str(exc_info.value).lower()

    def test_pydantic_validation_failure_missing_name(self, tmp_path: Path) -> None:
        """Valid YAML syntax but missing required 'name' raises WorkflowParseError."""
        # The 'workflow' block requires both 'id' and 'name'; omit 'name'.
        f = tmp_path / "missing_name.yaml"
        f.write_text(
            textwrap.dedent(
                """\
                workflow:
                  id: "test-workflow"
                stages:
                  - id: "stage-one"
                    name: "Stage One"
                """
            ),
            encoding="utf-8",
        )

        with pytest.raises(WorkflowParseError) as exc_info:
            parse_workflow(f)

        err = exc_info.value
        # Should have Pydantic-level details populated
        assert len(err.details) > 0
        # At least one detail references the missing 'name' field
        details_text = " ".join(err.details)
        assert "name" in details_text.lower() or "missing" in details_text.lower()

    def test_pydantic_validation_failure_missing_workflow_block(
        self, tmp_path: Path
    ) -> None:
        """YAML missing the top-level 'workflow' key raises WorkflowParseError."""
        f = tmp_path / "no_workflow_key.yaml"
        f.write_text(
            textwrap.dedent(
                """\
                stages:
                  - id: "stage-one"
                    name: "Stage One"
                """
            ),
            encoding="utf-8",
        )

        with pytest.raises(WorkflowParseError) as exc_info:
            parse_workflow(f)

        assert len(exc_info.value.details) > 0


# ---------------------------------------------------------------------------
# Defaults tests
# ---------------------------------------------------------------------------


class TestWorkflowTimeoutDefault:
    """WorkflowConfig.timeout is always set after parsing."""

    def test_workflow_timeout_default_is_2h(self, minimal_workflow: WorkflowDefinition) -> None:
        """A workflow without an explicit timeout has config.timeout == '2h'."""
        # The Pydantic default ensures this; apply_defaults documents the invariant.
        assert minimal_workflow.config.timeout == DEFAULT_WORKFLOW_TIMEOUT
        assert minimal_workflow.config.timeout == "2h"

    def test_apply_defaults_preserves_explicit_timeout(self, tmp_path: Path) -> None:
        """Explicit workflow timeout is not overwritten by apply_defaults."""
        wf_data = dict(MINIMAL_WORKFLOW_DICT)
        wf_data["config"] = {"timeout": "6h"}
        wf = WorkflowDefinition.model_validate(wf_data)
        result = apply_defaults(wf)
        assert result.config.timeout == "6h"


class TestStageTimeoutDefaults:
    """apply_defaults assigns type-appropriate timeouts to stages."""

    def _make_workflow_with_stage(self, stage: StageDefinition) -> WorkflowDefinition:
        return WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[stage],
        )

    def test_agent_stage_gets_30m_timeout(
        self, agent_stage_no_policy: StageDefinition
    ) -> None:
        """Agent stage without error_policy gets timeout='30m' after apply_defaults."""
        wf = self._make_workflow_with_stage(agent_stage_no_policy)
        result = apply_defaults(wf)

        stage = result.stages[0]
        assert stage.error_policy is not None
        assert stage.error_policy.timeout == DEFAULT_AGENT_STAGE_TIMEOUT
        assert stage.error_policy.timeout == "30m"

    def test_gate_stage_gets_24h_timeout(
        self, gate_stage_no_policy: StageDefinition
    ) -> None:
        """Gate stage without error_policy gets timeout='24h' after apply_defaults."""
        wf = self._make_workflow_with_stage(gate_stage_no_policy)
        result = apply_defaults(wf)

        stage = result.stages[0]
        assert stage.error_policy is not None
        assert stage.error_policy.timeout == DEFAULT_GATE_STAGE_TIMEOUT
        assert stage.error_policy.timeout == "24h"

    def test_explicit_stage_timeout_not_overwritten(self) -> None:
        """Stage with explicit timeout='1h' keeps that value after apply_defaults."""
        stage = StageDefinition(
            id="explicit-timeout",
            name="Explicit Timeout",
            type="agent",
            error_policy=ErrorPolicy(timeout="1h"),
        )
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[stage],
        )
        result = apply_defaults(wf)

        assert result.stages[0].error_policy is not None
        assert result.stages[0].error_policy.timeout == "1h"


class TestGlobalRetryInheritance:
    """apply_defaults propagates global error_policy.default_retry to stages."""

    def test_global_retry_inherited_by_stage_without_error_policy(self) -> None:
        """Stage with no error_policy inherits global default_retry."""
        global_retry = RetryPolicy(
            max_attempts=3,
            initial_interval="1m",
            backoff_multiplier=1.5,
        )
        stage = StageDefinition(
            id="inheriting-stage",
            name="Inheriting Stage",
            type="agent",
            # no error_policy
        )
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[stage],
            error_policy=GlobalErrorPolicy(default_retry=global_retry),
        )
        result = apply_defaults(wf)

        ep = result.stages[0].error_policy
        assert ep is not None
        assert ep.retry is not None
        assert ep.retry.max_attempts == 3
        assert ep.retry.initial_interval == "1m"
        assert ep.retry.backoff_multiplier == 1.5

    def test_global_retry_inherited_by_stage_with_error_policy_but_no_retry(self) -> None:
        """Stage that has an error_policy but no retry inherits global default_retry."""
        global_retry = RetryPolicy(max_attempts=4)
        stage = StageDefinition(
            id="no-retry-stage",
            name="No Retry Stage",
            type="agent",
            error_policy=ErrorPolicy(on_failure="continue"),  # no retry
        )
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[stage],
            error_policy=GlobalErrorPolicy(default_retry=global_retry),
        )
        result = apply_defaults(wf)

        ep = result.stages[0].error_policy
        assert ep is not None
        assert ep.retry is not None
        assert ep.retry.max_attempts == 4

    def test_explicit_stage_retry_not_overwritten_by_global(self) -> None:
        """Stage with its own retry keeps it even when global default_retry is set."""
        global_retry = RetryPolicy(max_attempts=5)
        stage_retry = RetryPolicy(max_attempts=1)
        stage = StageDefinition(
            id="explicit-retry-stage",
            name="Explicit Retry Stage",
            type="agent",
            error_policy=ErrorPolicy(retry=stage_retry),
        )
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[stage],
            error_policy=GlobalErrorPolicy(default_retry=global_retry),
        )
        result = apply_defaults(wf)

        ep = result.stages[0].error_policy
        assert ep is not None
        assert ep.retry is not None
        assert ep.retry.max_attempts == 1  # stage value, not global


class TestHandoffDefault:
    """apply_defaults adds a default HandoffConfig to stages that lack one."""

    def test_stage_without_handoff_gets_structured_handoff(
        self, agent_stage_no_policy: StageDefinition
    ) -> None:
        """Stage without handoff receives HandoffConfig(format='structured') after apply_defaults."""
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[agent_stage_no_policy],
        )
        result = apply_defaults(wf)

        stage = result.stages[0]
        assert stage.handoff is not None
        assert stage.handoff.format == "structured"
        assert stage.handoff.include_run_log is False

    def test_explicit_handoff_not_overwritten(self) -> None:
        """Stage with handoff format='markdown' keeps it after apply_defaults."""
        stage = StageDefinition(
            id="md-handoff",
            name="Markdown Handoff",
            type="agent",
            handoff=HandoffConfig(format="markdown", include_run_log=True),
        )
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=[stage],
        )
        result = apply_defaults(wf)

        assert result.stages[0].handoff is not None
        assert result.stages[0].handoff.format == "markdown"
        assert result.stages[0].handoff.include_run_log is True


class TestApplyDefaultsIdempotency:
    """apply_defaults satisfies the roundtrip idempotency guarantee."""

    def test_roundtrip_idempotency_minimal(
        self, minimal_workflow: WorkflowDefinition
    ) -> None:
        """apply_defaults(apply_defaults(wf)) == apply_defaults(wf) for minimal workflow."""
        once = apply_defaults(minimal_workflow)
        twice = apply_defaults(once)

        # Compare serialised forms for a deep equality check.
        assert once.model_dump() == twice.model_dump()

    def test_roundtrip_idempotency_with_global_error_policy(self) -> None:
        """Idempotency holds when global error_policy and multiple stages are present."""
        global_retry = RetryPolicy(max_attempts=3)
        stages = [
            StageDefinition(
                id=f"stage-{i}",
                name=f"Stage {i}",
                type="agent",
            )
            for i in range(3)
        ]
        stages.append(
            StageDefinition(
                id="gate",
                name="Gate",
                type="gate",
            )
        )
        wf = WorkflowDefinition(
            workflow=WorkflowMetadata(id="wf", name="Workflow"),
            stages=stages,
            error_policy=GlobalErrorPolicy(default_retry=global_retry),
        )

        once = apply_defaults(wf)
        twice = apply_defaults(once)

        assert once.model_dump() == twice.model_dump()
