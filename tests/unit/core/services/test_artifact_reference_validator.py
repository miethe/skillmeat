"""Unit tests for ArtifactReferenceValidator.

Tests use mock-based isolation (MagicMock) — no real DB or filesystem access.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.services.artifact_reference_validator import (
    ArtifactReferenceValidator,
    RoleResolutionResult,
)
from skillmeat.core.workflow.models import (
    RoleAssignment,
    StageDefinition,
    StageRoles,
    WorkflowDefinition,
    WorkflowMetadata,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_artifact(artifact_id: str, name: str, artifact_type: str) -> MagicMock:
    """Build a mock Artifact ORM row."""
    a = MagicMock()
    a.id = artifact_id
    a.name = name
    a.type = artifact_type
    return a


def _make_stage(
    stage_id: str,
    primary_artifact: str,
    tools: list[str] | None = None,
) -> StageDefinition:
    """Construct a minimal StageDefinition with roles."""
    return StageDefinition(
        id=stage_id,
        name=stage_id.replace("-", " ").title(),
        roles=StageRoles(
            primary=RoleAssignment(artifact=primary_artifact),
            tools=tools or [],
        ),
    )


def _make_workflow_definition(stages: list[StageDefinition]) -> WorkflowDefinition:
    """Build a minimal WorkflowDefinition with the given stages."""
    return WorkflowDefinition(
        workflow=WorkflowMetadata(id="test-wf", name="Test Workflow"),
        stages=stages,
    )


def _make_workflow_row(yaml_text: str | None) -> MagicMock:
    """Build a mock Workflow ORM row."""
    row = MagicMock()
    row.definition_yaml = yaml_text
    return row


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Return a MagicMock standing in for a SQLAlchemy Session."""
    return MagicMock()


@pytest.fixture
def validator(mock_session):
    """ArtifactReferenceValidator with a mock session."""
    return ArtifactReferenceValidator(mock_session)


# =============================================================================
# RoleResolutionResult data class
# =============================================================================


class TestRoleResolutionResult:
    """Basic smoke tests for the result dataclass."""

    def test_defaults(self):
        result = RoleResolutionResult(workflow_id="wf-1")
        assert result.workflow_id == "wf-1"
        assert result.resolved == []
        assert result.unresolved == []

    def test_with_values(self):
        entry = {
            "role_string": "agent:researcher-v1",
            "artifact_id": "agent:researcher-v1",
            "name": "researcher-v1",
            "artifact_type": "agent",
        }
        result = RoleResolutionResult(
            workflow_id="wf-2",
            resolved=[entry],
            unresolved=["skill:missing"],
        )
        assert len(result.resolved) == 1
        assert result.resolved[0]["artifact_id"] == "agent:researcher-v1"
        assert result.unresolved == ["skill:missing"]


# =============================================================================
# _load_workflow_definition
# =============================================================================


class TestLoadWorkflowDefinition:
    """Tests for the private YAML-loading helper."""

    def test_returns_none_when_workflow_not_found(self, validator, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        result = validator._load_workflow_definition("missing-wf")
        assert result is None

    def test_returns_none_when_definition_yaml_is_empty(self, validator, mock_session):
        row = _make_workflow_row(yaml_text=None)
        mock_session.query.return_value.filter_by.return_value.first.return_value = row
        result = validator._load_workflow_definition("wf-001")
        assert result is None

    def test_returns_none_when_yaml_is_unparseable(self, validator, mock_session):
        row = _make_workflow_row(yaml_text="{{{{invalid yaml{{{{")
        mock_session.query.return_value.filter_by.return_value.first.return_value = row
        result = validator._load_workflow_definition("wf-002")
        assert result is None

    def test_returns_none_on_db_operational_error(self, validator, mock_session):
        from sqlalchemy.exc import OperationalError

        mock_session.query.return_value.filter_by.return_value.first.side_effect = (
            OperationalError("query failed", params=None, orig=Exception("disk I/O error"))
        )
        result = validator._load_workflow_definition("wf-003")
        assert result is None

    def test_returns_parsed_definition_for_valid_yaml(self, validator, mock_session):
        yaml_text = """
workflow:
  id: test-pipeline
  name: Test Pipeline
stages:
  - id: stage-a
    name: Stage A
    roles:
      primary:
        artifact: "agent:researcher-v1"
"""
        row = _make_workflow_row(yaml_text=yaml_text)
        mock_session.query.return_value.filter_by.return_value.first.return_value = row
        definition = validator._load_workflow_definition("wf-004")
        assert definition is not None
        assert definition.workflow.id == "test-pipeline"
        assert len(definition.stages) == 1


# =============================================================================
# _extract_role_strings
# =============================================================================


class TestExtractRoleStrings:
    """Tests for the role-string extraction helper."""

    def test_returns_empty_for_no_stages(self, validator):
        defn = _make_workflow_definition(stages=[])
        assert validator._extract_role_strings(defn) == []

    def test_returns_empty_when_stage_has_no_roles(self, validator):
        stage = StageDefinition(id="s1", name="S1", roles=None)
        defn = _make_workflow_definition(stages=[stage])
        assert validator._extract_role_strings(defn) == []

    def test_extracts_primary_artifact(self, validator):
        stage = _make_stage("s1", "agent:researcher-v1")
        defn = _make_workflow_definition(stages=[stage])
        roles = validator._extract_role_strings(defn)
        assert roles == ["agent:researcher-v1"]

    def test_extracts_tools(self, validator):
        stage = _make_stage(
            "s1",
            "agent:researcher-v1",
            tools=["skill:web-search", "mcp:github-api"],
        )
        defn = _make_workflow_definition(stages=[stage])
        roles = validator._extract_role_strings(defn)
        assert roles == ["agent:researcher-v1", "skill:web-search", "mcp:github-api"]

    def test_deduplicates_across_stages(self, validator):
        """Same role referenced in two stages should appear only once."""
        stage1 = _make_stage("s1", "agent:researcher-v1")
        stage2 = _make_stage(
            "s2", "agent:writer-v1", tools=["agent:researcher-v1"]
        )
        defn = _make_workflow_definition(stages=[stage1, stage2])
        roles = validator._extract_role_strings(defn)
        assert roles.count("agent:researcher-v1") == 1
        assert "agent:writer-v1" in roles

    def test_preserves_encounter_order(self, validator):
        """Role strings appear in the order they were first encountered."""
        stage1 = _make_stage("s1", "agent:first")
        stage2 = _make_stage("s2", "agent:second")
        defn = _make_workflow_definition(stages=[stage1, stage2])
        roles = validator._extract_role_strings(defn)
        assert roles == ["agent:first", "agent:second"]


# =============================================================================
# _resolve_role / _resolve_by_id / _resolve_by_name
# =============================================================================


class TestResolveByIdAndName:
    """Unit tests for the two-pass resolution strategy."""

    def _setup_query_chain(self, mock_session, return_value):
        """Wire mock_session.query(...).filter(...).first() -> return_value."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            return_value
        )

    def test_resolve_by_id_returns_match_dict(self, validator, mock_session):
        artifact = _make_artifact("agent:researcher-v1", "researcher-v1", "agent")
        self._setup_query_chain(mock_session, artifact)

        result = validator._resolve_by_id("agent:researcher-v1")
        assert result is not None
        assert result["role_string"] == "agent:researcher-v1"
        assert result["artifact_id"] == "agent:researcher-v1"
        assert result["name"] == "researcher-v1"
        assert result["artifact_type"] == "agent"

    def test_resolve_by_id_returns_none_when_no_match(self, validator, mock_session):
        self._setup_query_chain(mock_session, None)
        result = validator._resolve_by_id("agent:does-not-exist")
        assert result is None

    def test_resolve_by_name_strips_type_prefix(self, validator, mock_session):
        artifact = _make_artifact("skill:web-search", "web-search", "skill")
        self._setup_query_chain(mock_session, artifact)

        result = validator._resolve_by_name("wrong-type:web-search")
        assert result is not None
        assert result["artifact_id"] == "skill:web-search"

    def test_resolve_by_name_with_no_colon(self, validator, mock_session):
        artifact = _make_artifact("skill:plain-name", "plain-name", "skill")
        self._setup_query_chain(mock_session, artifact)

        result = validator._resolve_by_name("plain-name")
        assert result is not None
        assert result["artifact_id"] == "skill:plain-name"

    def test_resolve_by_name_returns_none_for_empty_name_part(
        self, validator, mock_session
    ):
        # e.g. "agent:" has empty name part after the colon
        result = validator._resolve_by_name("agent:")
        assert result is None
        mock_session.query.assert_not_called()

    def test_resolve_role_falls_through_to_name_when_id_misses(
        self, validator, mock_session
    ):
        """Primary id-lookup miss -> fallback name lookup succeeds."""
        artifact = _make_artifact("skill:web-search", "web-search", "skill")

        # First query (by id) returns None; second (by name) returns artifact.
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            None,
            artifact,
        ]

        result = validator._resolve_role("wrong-type:web-search")
        assert result is not None
        assert result["artifact_id"] == "skill:web-search"

    def test_resolve_role_returns_none_when_both_passes_miss(
        self, validator, mock_session
    ):
        mock_session.query.return_value.filter.return_value.first.return_value = None
        result = validator._resolve_role("agent:ghost")
        assert result is None

    def test_resolve_role_returns_none_on_db_operational_error(
        self, validator, mock_session
    ):
        from sqlalchemy.exc import OperationalError

        mock_session.query.return_value.filter.return_value.first.side_effect = (
            OperationalError("DB error", params=None, orig=Exception("lock timeout"))
        )
        result = validator._resolve_role("agent:locked-role")
        assert result is None


# =============================================================================
# resolve_stage_roles — integration scenarios
# =============================================================================


class TestResolveStageRoles:
    """End-to-end tests for the public resolve_stage_roles() method.

    All DB interactions are mocked.  WorkflowDefinition objects are injected
    directly into _load_workflow_definition via patch.
    """

    def _patch_load(self, validator, definition_or_none):
        """Patch _load_workflow_definition to return a fixed value."""
        return patch.object(
            validator,
            "_load_workflow_definition",
            return_value=definition_or_none,
        )

    def _patch_resolve(self, validator, side_effect_fn):
        """Patch _resolve_role with a custom side_effect function."""
        return patch.object(validator, "_resolve_role", side_effect=side_effect_fn)

    # -- Empty / missing workflows --

    def test_returns_empty_result_when_workflow_not_found(self, validator):
        with self._patch_load(validator, None):
            result = validator.resolve_stage_roles("missing-wf")

        assert result.workflow_id == "missing-wf"
        assert result.resolved == []
        assert result.unresolved == []

    def test_returns_empty_result_for_workflow_with_no_stages(self, validator):
        defn = _make_workflow_definition(stages=[])
        with self._patch_load(validator, defn):
            result = validator.resolve_stage_roles("empty-wf")

        assert result.resolved == []
        assert result.unresolved == []

    def test_returns_empty_result_when_stages_have_no_roles(self, validator):
        stage = StageDefinition(id="gate-1", name="Gate", type="gate", roles=None)
        defn = _make_workflow_definition(stages=[stage])
        with self._patch_load(validator, defn):
            result = validator.resolve_stage_roles("gate-only-wf")

        assert result.resolved == []
        assert result.unresolved == []

    # -- All roles resolved --

    def test_all_roles_resolved(self, validator):
        stage = _make_stage(
            "s1",
            "agent:researcher-v1",
            tools=["skill:web-search"],
        )
        defn = _make_workflow_definition(stages=[stage])

        def mock_resolve(role_string):
            return {
                "role_string": role_string,
                "artifact_id": role_string,
                "name": role_string.split(":")[1],
                "artifact_type": role_string.split(":")[0],
            }

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, mock_resolve):
                result = validator.resolve_stage_roles("wf-all-resolved")

        assert len(result.resolved) == 2
        assert result.unresolved == []
        resolved_ids = [r["artifact_id"] for r in result.resolved]
        assert "agent:researcher-v1" in resolved_ids
        assert "skill:web-search" in resolved_ids

    # -- Some roles unresolved --

    def test_unresolved_roles_appear_in_unresolved_list(self, validator, caplog):
        stage = _make_stage(
            "s1",
            "agent:researcher-v1",
            tools=["skill:missing-skill"],
        )
        defn = _make_workflow_definition(stages=[stage])

        def mock_resolve(role_string):
            if role_string == "agent:researcher-v1":
                return {
                    "role_string": role_string,
                    "artifact_id": role_string,
                    "name": "researcher-v1",
                    "artifact_type": "agent",
                }
            return None  # skill:missing-skill not found

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, mock_resolve):
                with caplog.at_level(logging.WARNING):
                    result = validator.resolve_stage_roles("wf-partial")

        assert len(result.resolved) == 1
        assert result.resolved[0]["artifact_id"] == "agent:researcher-v1"
        assert result.unresolved == ["skill:missing-skill"]

    # -- All roles unresolved --

    def test_all_roles_unresolved(self, validator, caplog):
        stage = _make_stage("s1", "agent:ghost-agent")
        defn = _make_workflow_definition(stages=[stage])

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, lambda _: None):
                with caplog.at_level(logging.WARNING):
                    result = validator.resolve_stage_roles("wf-all-unresolved")

        assert result.resolved == []
        assert result.unresolved == ["agent:ghost-agent"]

    # -- Warning logs for unresolved roles --

    def test_unresolved_roles_log_warning(self, validator, caplog):
        stage = _make_stage("s1", "agent:ghost-agent")
        defn = _make_workflow_definition(stages=[stage])

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, lambda _: None):
                with caplog.at_level(logging.WARNING):
                    validator.resolve_stage_roles("wf-warning-test")

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("agent:ghost-agent" in m for m in warning_msgs)
        assert any("wf-warning-test" in m for m in warning_msgs)

    def test_unresolved_roles_do_not_raise(self, validator, caplog):
        """Missing artifacts must never cause an exception."""
        stage = _make_stage("s1", "agent:ghost-agent")
        defn = _make_workflow_definition(stages=[stage])

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, lambda _: None):
                with caplog.at_level(logging.WARNING):
                    # Must NOT raise
                    result = validator.resolve_stage_roles("wf-no-raise")

        assert isinstance(result, RoleResolutionResult)

    # -- Mixed resolved / unresolved --

    def test_mixed_resolution(self, validator, caplog):
        stage1 = _make_stage("s1", "agent:good-agent")
        stage2 = _make_stage("s2", "agent:missing-agent")
        defn = _make_workflow_definition(stages=[stage1, stage2])

        def mock_resolve(role_string):
            if "good" in role_string:
                return {
                    "role_string": role_string,
                    "artifact_id": role_string,
                    "name": "good-agent",
                    "artifact_type": "agent",
                }
            return None

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, mock_resolve):
                with caplog.at_level(logging.WARNING):
                    result = validator.resolve_stage_roles("wf-mixed")

        assert len(result.resolved) == 1
        assert result.resolved[0]["artifact_id"] == "agent:good-agent"
        assert result.unresolved == ["agent:missing-agent"]

    # -- Deduplication --

    def test_same_role_in_multiple_stages_resolved_once(self, validator):
        stage1 = _make_stage("s1", "agent:shared-agent")
        stage2 = _make_stage("s2", "agent:other-agent", tools=["agent:shared-agent"])
        defn = _make_workflow_definition(stages=[stage1, stage2])

        resolve_call_count = {"n": 0}

        def mock_resolve(role_string):
            resolve_call_count["n"] += 1
            return {
                "role_string": role_string,
                "artifact_id": role_string,
                "name": role_string.split(":")[1],
                "artifact_type": "agent",
            }

        with self._patch_load(validator, defn):
            with self._patch_resolve(validator, mock_resolve):
                result = validator.resolve_stage_roles("wf-dedup")

        # "agent:shared-agent" should only be resolved once
        resolved_ids = [r["artifact_id"] for r in result.resolved]
        assert resolved_ids.count("agent:shared-agent") == 1
        assert resolve_call_count["n"] == 2  # shared-agent + other-agent

    # -- workflow_id in result --

    def test_result_contains_correct_workflow_id(self, validator):
        defn = _make_workflow_definition(stages=[])
        with self._patch_load(validator, defn):
            result = validator.resolve_stage_roles("my-specific-wf-id")

        assert result.workflow_id == "my-specific-wf-id"


# =============================================================================
# _build_match static method
# =============================================================================


class TestBuildMatch:
    """Tests for the static match-dict builder."""

    def test_builds_correct_dict(self):
        artifact = _make_artifact("agent:researcher-v1", "researcher-v1", "agent")
        match = ArtifactReferenceValidator._build_match("agent:researcher-v1", artifact)

        assert match["role_string"] == "agent:researcher-v1"
        assert match["artifact_id"] == "agent:researcher-v1"
        assert match["name"] == "researcher-v1"
        assert match["artifact_type"] == "agent"

    def test_role_string_differs_from_artifact_id(self):
        """Fallback path: role string type prefix may differ from stored id."""
        artifact = _make_artifact("skill:web-search", "web-search", "skill")
        match = ArtifactReferenceValidator._build_match("agent:web-search", artifact)

        assert match["role_string"] == "agent:web-search"
        assert match["artifact_id"] == "skill:web-search"  # uses the DB value
        assert match["artifact_type"] == "skill"
