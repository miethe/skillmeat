"""Unit tests for the SWDL expression engine.

Covers ExpressionParser, ExpressionContext, ExpressionError, and the
static validate_expressions validator from skillmeat.core.workflow.
"""

from __future__ import annotations

import json
import pytest

from skillmeat.core.workflow.expressions import (
    ExpressionContext,
    ExpressionError,
    ExpressionParser,
)
from skillmeat.core.workflow.models import (
    InputContract,
    OutputContract,
    RoleAssignment,
    StageDefinition,
    StageRoles,
    WorkflowConfig,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowParameter,
)
from skillmeat.core.workflow.dag import build_dag
from skillmeat.core.workflow.validator import validate_expressions


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def parser() -> ExpressionParser:
    """Return a reusable ExpressionParser instance."""
    return ExpressionParser()


@pytest.fixture()
def basic_ctx() -> ExpressionContext:
    """Return an ExpressionContext populated with representative test data."""
    return ExpressionContext(
        parameters={
            "feature_name": "auth-v2",
            "x": "hello",
            "a": True,
            "b": False,
            "flag": True,
            "items": [1, 2, 3],
        },
        stages={
            "research": {
                "outputs": {"summary": "done", "report": "full text"},
                "status": "completed",
            }
        },
        env={"PROJECT_ROOT": "/home/user/project"},
        run={"id": "run-abc123", "started_at": "2026-01-01T00:00:00Z"},
        workflow={"version": "1.0.0", "name": "test-workflow"},
    )


# ---------------------------------------------------------------------------
# Helper – build a minimal valid WorkflowDefinition for validator tests
# ---------------------------------------------------------------------------


def _make_workflow(stages: list[StageDefinition], params: dict | None = None) -> WorkflowDefinition:
    """Construct a WorkflowDefinition from a list of StageDefinition objects."""
    parameters: dict = {}
    if params:
        for name, typ in params.items():
            parameters[name] = WorkflowParameter(type=typ)

    return WorkflowDefinition(
        workflow=WorkflowMetadata(id="test-wf", name="Test Workflow"),
        config=WorkflowConfig(parameters=parameters),
        stages=stages,
    )


def _make_agent_stage(
    stage_id: str,
    depends_on: list[str] | None = None,
    inputs: dict | None = None,
    outputs: dict | None = None,
    condition: str | None = None,
) -> StageDefinition:
    """Build a minimal agent StageDefinition for testing."""
    return StageDefinition(
        id=stage_id,
        name=stage_id.replace("-", " ").title(),
        depends_on=depends_on or [],
        inputs=inputs or {},
        outputs=outputs or {},
        condition=condition,
        roles=StageRoles(
            primary=RoleAssignment(artifact="agent:test-agent")
        ),
    )


# ===========================================================================
# Expression parser tests
# ===========================================================================


class TestPropertyAccess:
    """Tests for dot-path property resolution."""

    def test_simple_property_access(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.feature_name resolves to its value."""
        assert parser.evaluate("parameters.feature_name", basic_ctx) == "auth-v2"

    def test_nested_property_access(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """stages.research.outputs.summary resolves through nested dicts."""
        assert parser.evaluate("stages.research.outputs.summary", basic_ctx) == "done"


class TestComparisonOperators:
    """Tests for ==, !=, >, <, >=, <=."""

    def test_equality_true(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.x == 'hello' is True when values match."""
        assert parser.evaluate("parameters.x == 'hello'", basic_ctx) is True

    def test_equality_false(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.x == 'world' is False when values differ."""
        assert parser.evaluate("parameters.x == 'world'", basic_ctx) is False

    def test_not_equal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.x != 'world' is True when values differ."""
        assert parser.evaluate("parameters.x != 'world'", basic_ctx) is True

    def test_greater_than_with_length(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """length(parameters.items) > 2 is True when list has 3 items."""
        assert parser.evaluate("length(parameters.items) > 2", basic_ctx) is True

    def test_greater_than_false(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """length(parameters.items) > 5 is False when list has only 3 items."""
        assert parser.evaluate("length(parameters.items) > 5", basic_ctx) is False


class TestBooleanOperators:
    """Tests for &&, ||, !."""

    def test_boolean_and_true(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.a && parameters.a is True when both operands are truthy."""
        assert parser.evaluate("parameters.a && parameters.a", basic_ctx) is True

    def test_boolean_and_false(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.a && parameters.b is False when one operand is falsy."""
        result = parser.evaluate("parameters.a && parameters.b", basic_ctx)
        assert not result

    def test_boolean_or_true(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """parameters.a || parameters.b is truthy when at least one is truthy."""
        result = parser.evaluate("parameters.a || parameters.b", basic_ctx)
        assert result

    def test_boolean_or_false(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """False || false is falsy."""
        ctx = ExpressionContext(parameters={"a": False, "b": False})
        result = parser.evaluate("parameters.a || parameters.b", ctx)
        assert not result

    def test_not_operator_negates_true(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """!parameters.flag is False when flag is True."""
        assert parser.evaluate("!parameters.flag", basic_ctx) is False

    def test_not_operator_negates_false(self, parser: ExpressionParser) -> None:
        """!parameters.flag is True when flag is False."""
        ctx = ExpressionContext(parameters={"flag": False})
        assert parser.evaluate("!parameters.flag", ctx) is True


class TestTernary:
    """Tests for the ternary operator ``a ? b : c``."""

    def test_ternary_true_branch(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Ternary selects the then-branch when condition is truthy."""
        result = parser.evaluate("parameters.x ? 'yes' : 'no'", basic_ctx)
        assert result == "yes"

    def test_ternary_false_branch(self, parser: ExpressionParser) -> None:
        """Ternary selects the else-branch when condition is falsy."""
        ctx = ExpressionContext(parameters={"x": False})
        result = parser.evaluate("parameters.x ? 'yes' : 'no'", ctx)
        assert result == "no"

    def test_ternary_null_condition(self, parser: ExpressionParser) -> None:
        """Ternary treats null as falsy, selecting else-branch."""
        ctx = ExpressionContext(parameters={"x": None})
        result = parser.evaluate("parameters.x ? 'yes' : 'no'", ctx)
        assert result == "no"


class TestLiterals:
    """Tests for string, number, boolean, and null literals."""

    def test_string_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """A single-quoted string literal evaluates to a Python str."""
        result = parser.evaluate("'hello'", basic_ctx)
        assert result == "hello"

    def test_double_quoted_string_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """A double-quoted string literal evaluates to a Python str."""
        result = parser.evaluate('"world"', basic_ctx)
        assert result == "world"

    def test_integer_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """An integer literal evaluates to a Python int."""
        result = parser.evaluate("42", basic_ctx)
        assert result == 42
        assert isinstance(result, int)

    def test_float_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """A float literal evaluates to a Python float."""
        result = parser.evaluate("3.14", basic_ctx)
        assert abs(result - 3.14) < 1e-9

    def test_true_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Boolean literal 'true' evaluates to Python True."""
        assert parser.evaluate("true", basic_ctx) is True

    def test_false_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Boolean literal 'false' evaluates to Python False."""
        assert parser.evaluate("false", basic_ctx) is False

    def test_null_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Keyword 'null' evaluates to Python None."""
        assert parser.evaluate("null", basic_ctx) is None


# ===========================================================================
# Built-in function tests
# ===========================================================================


class TestBuiltinLength:
    """Tests for the length() built-in."""

    def test_length_of_list(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """length() on a list returns the element count."""
        result = parser.evaluate("length(parameters.items)", basic_ctx)
        assert result == 3

    def test_length_of_string(self, parser: ExpressionParser) -> None:
        """length() on a string returns the character count."""
        ctx = ExpressionContext(parameters={"word": "hello"})
        result = parser.evaluate("length(parameters.word)", ctx)
        assert result == 5

    def test_length_of_string_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """length() on a string literal returns character count."""
        result = parser.evaluate("length('hello')", basic_ctx)
        assert result == 5


class TestBuiltinContains:
    """Tests for the contains() built-in."""

    def test_contains_substring_true(self, parser: ExpressionParser) -> None:
        """contains() on a string returns True when the substring is present."""
        ctx = ExpressionContext(parameters={"msg": "hello world"})
        result = parser.evaluate("contains(parameters.msg, 'ell')", ctx)
        assert result is True

    def test_contains_substring_false(self, parser: ExpressionParser) -> None:
        """contains() on a string returns False when the substring is absent."""
        ctx = ExpressionContext(parameters={"msg": "hello world"})
        result = parser.evaluate("contains(parameters.msg, 'xyz')", ctx)
        assert result is False

    def test_contains_list_member_true(self, parser: ExpressionParser) -> None:
        """contains() on a list returns True when the item is present."""
        ctx = ExpressionContext(parameters={"tags": ["alpha", "beta", "gamma"]})
        result = parser.evaluate("contains(parameters.tags, 'beta')", ctx)
        assert result is True

    def test_contains_list_member_false(self, parser: ExpressionParser) -> None:
        """contains() on a list returns False when the item is absent."""
        ctx = ExpressionContext(parameters={"tags": ["alpha", "beta"]})
        result = parser.evaluate("contains(parameters.tags, 'delta')", ctx)
        assert result is False


class TestBuiltinToJSON:
    """Tests for the toJSON() built-in."""

    def test_to_json_list(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """toJSON() serializes a list to a JSON string."""
        result = parser.evaluate("toJSON(parameters.items)", basic_ctx)
        assert isinstance(result, str)
        assert json.loads(result) == [1, 2, 3]

    def test_to_json_string_literal(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """toJSON() serializes a string to a JSON string (with quotes)."""
        result = parser.evaluate("toJSON('hello')", basic_ctx)
        assert result == '"hello"'


class TestBuiltinFromJSON:
    """Tests for the fromJSON() built-in."""

    def test_from_json_object(self, parser: ExpressionParser) -> None:
        """fromJSON() parses a JSON object string to a dict."""
        ctx = ExpressionContext(parameters={"raw": '{"a": 1}'})
        result = parser.evaluate("fromJSON(parameters.raw)", ctx)
        assert isinstance(result, dict)
        assert result["a"] == 1

    def test_from_json_array(self, parser: ExpressionParser) -> None:
        """fromJSON() parses a JSON array string to a list."""
        ctx = ExpressionContext(parameters={"raw": "[1, 2, 3]"})
        result = parser.evaluate("fromJSON(parameters.raw)", ctx)
        assert result == [1, 2, 3]


# ===========================================================================
# Namespace tests
# ===========================================================================


class TestNamespaceResolution:
    """Tests that all supported top-level namespaces resolve correctly."""

    def test_stages_namespace_status(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """stages.<id>.status resolves to the stage status string."""
        result = parser.evaluate("stages.research.status", basic_ctx)
        assert result == "completed"

    def test_env_namespace(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """env.<name> resolves from the env dict."""
        result = parser.evaluate("env.PROJECT_ROOT", basic_ctx)
        assert result == "/home/user/project"

    def test_run_namespace(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """run.<key> resolves from the run dict."""
        result = parser.evaluate("run.id", basic_ctx)
        assert result == "run-abc123"

    def test_workflow_namespace(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """workflow.<key> resolves from the workflow dict."""
        result = parser.evaluate("workflow.version", basic_ctx)
        assert result == "1.0.0"


# ===========================================================================
# Error cases
# ===========================================================================


class TestErrorCases:
    """Tests for ExpressionError on invalid inputs."""

    def test_unclosed_string_literal_raises(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """An unclosed string literal causes ExpressionError."""
        with pytest.raises(ExpressionError):
            parser.evaluate("'unclosed", basic_ctx)

    def test_unknown_function_raises(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Calling an unknown function raises ExpressionError."""
        with pytest.raises(ExpressionError, match="Unknown function"):
            parser.evaluate("unknown(parameters.x)", basic_ctx)

    def test_missing_property_returns_none(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Accessing a non-existent property returns None (graceful miss)."""
        result = parser.evaluate("parameters.nonexistent", basic_ctx)
        assert result is None

    def test_missing_nested_property_returns_none(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Accessing a deeply-nested non-existent key returns None."""
        result = parser.evaluate("stages.research.outputs.nonexistent", basic_ctx)
        assert result is None

    def test_unknown_namespace_raises(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Accessing an unknown top-level namespace raises ExpressionError."""
        with pytest.raises(ExpressionError, match="Unknown context namespace"):
            parser.evaluate("secrets.MY_TOKEN", basic_ctx)


# ===========================================================================
# resolve_string tests
# ===========================================================================


class TestResolveString:
    """Tests for ExpressionParser.resolve_string() template substitution."""

    def test_single_expression(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """A single ${{ }} placeholder is replaced with the resolved value."""
        result = parser.resolve_string("Hello ${{ parameters.feature_name }}", basic_ctx)
        assert result == "Hello auth-v2"

    def test_multiple_expressions(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Multiple ${{ }} placeholders are each replaced independently."""
        ctx = ExpressionContext(parameters={"a": "foo", "b": "bar"})
        result = parser.resolve_string("${{ parameters.a }}-${{ parameters.b }}", ctx)
        assert result == "foo-bar"

    def test_no_expressions_unchanged(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """Strings without ${{ }} placeholders are returned unchanged."""
        plain = "just a plain string"
        assert parser.resolve_string(plain, basic_ctx) == plain

    def test_missing_property_renders_empty(self, parser: ExpressionParser, basic_ctx: ExpressionContext) -> None:
        """A ${{ }} placeholder resolving to None renders as an empty string."""
        result = parser.resolve_string("prefix-${{ parameters.missing }}-suffix", basic_ctx)
        assert result == "prefix--suffix"

    def test_boolean_renders_lowercase(self, parser: ExpressionParser) -> None:
        """Boolean values are rendered as lowercase 'true'/'false'."""
        ctx = ExpressionContext(parameters={"flag": True})
        result = parser.resolve_string("enabled=${{ parameters.flag }}", ctx)
        assert result == "enabled=true"

    def test_number_renders_as_string(self, parser: ExpressionParser) -> None:
        """Numeric values are rendered as their string representation."""
        ctx = ExpressionContext(parameters={"count": 42})
        result = parser.resolve_string("count=${{ parameters.count }}", ctx)
        assert result == "count=42"

    def test_resolve_with_name_parameter(self, parser: ExpressionParser) -> None:
        """Classic name-greeting example from the docstring."""
        ctx = ExpressionContext(parameters={"name": "Alice"})
        result = parser.resolve_string("Hello ${{ parameters.name }}", ctx)
        assert result == "Hello Alice"


# ===========================================================================
# Static validation tests (validate_expressions)
# ===========================================================================


class TestValidateExpressions:
    """Tests for the static validate_expressions validator."""

    def test_valid_references_pass(self) -> None:
        """A workflow with correct stage output references produces no errors."""
        research = _make_agent_stage(
            "research",
            outputs={"summary": OutputContract(type="string")},
        )
        synthesis = _make_agent_stage(
            "synthesis",
            depends_on=["research"],
            inputs={
                "research_summary": InputContract(
                    type="string",
                    source="${{ stages.research.outputs.summary }}",
                )
            },
        )
        workflow = _make_workflow([research, synthesis])
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        assert result.valid, [str(e) for e in result.errors]

    def test_unknown_stage_reference_fails(self) -> None:
        """Referencing a nonexistent stage produces an expression error."""
        synthesis = _make_agent_stage(
            "synthesis",
            inputs={
                "data": InputContract(
                    type="string",
                    source="${{ stages.nonexistent.outputs.summary }}",
                )
            },
        )
        workflow = _make_workflow([synthesis])
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        assert not result.valid
        assert any("nonexistent" in e.message for e in result.errors)

    def test_missing_depends_on_fails(self) -> None:
        """Referencing a stage output without declaring it in depends_on is a DAG error."""
        research = _make_agent_stage(
            "research",
            outputs={"summary": OutputContract(type="string")},
        )
        # synthesis does NOT list research in depends_on
        synthesis = _make_agent_stage(
            "synthesis",
            depends_on=[],  # missing dependency
            inputs={
                "data": InputContract(
                    type="string",
                    source="${{ stages.research.outputs.summary }}",
                )
            },
        )
        workflow = _make_workflow([research, synthesis])
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        assert not result.valid
        dag_errors = [e for e in result.errors if e.category == "dag"]
        assert dag_errors, "Expected a DAG-category error for missing depends_on"

    def test_unknown_output_key_fails(self) -> None:
        """Referencing an undeclared output key produces an expression error."""
        research = _make_agent_stage(
            "research",
            outputs={"summary": OutputContract(type="string")},
        )
        synthesis = _make_agent_stage(
            "synthesis",
            depends_on=["research"],
            inputs={
                "data": InputContract(
                    type="string",
                    source="${{ stages.research.outputs.nonexistent_output }}",
                )
            },
        )
        workflow = _make_workflow([research, synthesis])
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        assert not result.valid
        assert any("nonexistent_output" in e.message for e in result.errors)

    def test_unknown_parameter_fails(self) -> None:
        """Referencing an undeclared parameter produces an expression error."""
        stage = _make_agent_stage(
            "build",
            condition="${{ parameters.undeclared }}",
        )
        # No parameters declared in the workflow
        workflow = _make_workflow([stage])
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        assert not result.valid
        assert any("undeclared" in e.message for e in result.errors)

    def test_declared_parameter_passes(self) -> None:
        """Referencing a declared parameter produces no errors."""
        stage = _make_agent_stage(
            "build",
            condition="${{ parameters.skip_tests }}",
        )
        workflow = _make_workflow([stage], params={"skip_tests": "boolean"})
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        assert result.valid, [str(e) for e in result.errors]

    def test_type_mismatch_produces_warning(self) -> None:
        """Mismatched input/output types produce a warning, not an error."""
        research = _make_agent_stage(
            "research",
            outputs={"count": OutputContract(type="integer")},
        )
        synthesis = _make_agent_stage(
            "synthesis",
            depends_on=["research"],
            inputs={
                "count": InputContract(
                    type="string",  # expects string but research produces integer
                    source="${{ stages.research.outputs.count }}",
                )
            },
        )
        workflow = _make_workflow([research, synthesis])
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)
        # Type mismatches are warnings, not errors; workflow is still valid.
        assert result.valid, [str(e) for e in result.errors]
        assert result.warnings, "Expected a type-mismatch warning"
