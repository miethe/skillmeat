"""Unit tests for the DAG engine and execution planner (SWDL workflow module).

Covers:
- DAG construction (single stage, sequential, fan-out, fan-in/diamond)
- Edge validation (unknown depends_on references)
- DAG navigation helpers (get_roots, get_successors, get_predecessors, all_stage_ids)
- Cycle detection (direct, indirect, self-loop, cycle attribute)
- Parallel batch computation (sequential, fully-parallel, diamond, mixed)
- Execution plan generation (parameters, batches, gate stages, format_plan_text)
"""
from __future__ import annotations

import pytest

from skillmeat.core.workflow.dag import (
    DAG,
    Batch,
    DAGNode,
    build_dag,
    compute_execution_batches,
    detect_cycles,
)
from skillmeat.core.workflow.exceptions import WorkflowCycleError, WorkflowValidationError
from skillmeat.core.workflow.models import (
    GateConfig,
    RoleAssignment,
    StageDefinition,
    StageRoles,
    WorkflowConfig,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowParameter,
)
from skillmeat.core.workflow.planner import ExecutionPlan, format_plan_text, generate_plan


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_workflow(stages_data, params=None):
    """Build a minimal WorkflowDefinition from a list of stage dicts.

    Each dict must have an 'id' key and may have an optional 'deps' key
    containing a list of stage IDs.  An optional 'type' key ('agent'|'gate')
    defaults to 'agent'.  Gate stages automatically receive a minimal GateConfig.

    Args:
        stages_data: List of dicts with 'id', optionally 'deps', 'type'.
        params:      Optional dict of WorkflowParameter instances keyed by name.

    Returns:
        A fully Pydantic-validated WorkflowDefinition.
    """
    stages = []
    for s in stages_data:
        stage_type = s.get("type", "agent")
        roles = None
        gate = None
        if stage_type == "agent":
            roles = StageRoles(
                primary=RoleAssignment(artifact="agent:test-agent"),
            )
        elif stage_type == "gate":
            gate = GateConfig(approvers=s.get("approvers", ["reviewer"]))

        stages.append(
            StageDefinition(
                id=s["id"],
                name=s["id"].upper(),
                depends_on=s.get("deps", []),
                type=stage_type,
                roles=roles,
                gate=gate,
            )
        )

    config = WorkflowConfig(parameters=params or {})
    return WorkflowDefinition(
        workflow=WorkflowMetadata(id="test", name="Test Workflow"),
        config=config,
        stages=stages,
    )


def _stage_ids_in_batches(batches):
    """Extract a list-of-lists of stage IDs from Batch objects."""
    return [b.stage_ids for b in batches]


# ===========================================================================
# DAG BUILD TESTS
# ===========================================================================


class TestBuildDag:
    """Tests for build_dag() — node creation and edge wiring."""

    def test_single_stage_no_deps(self):
        """Single stage → one root node, no predecessors, no successors."""
        workflow = make_workflow([{"id": "a"}])
        dag = build_dag(workflow)

        assert list(dag.nodes.keys()) == ["a"]
        node = dag.nodes["a"]
        assert node.predecessors == set()
        assert node.successors == set()

    def test_sequential_chain(self):
        """A→B→C: roots=[A], edges wired correctly."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]}]
        )
        dag = build_dag(workflow)

        assert dag.get_roots() == ["a"]
        # A feeds B
        assert "b" in dag.nodes["a"].successors
        assert "a" in dag.nodes["b"].predecessors
        # B feeds C
        assert "c" in dag.nodes["b"].successors
        assert "b" in dag.nodes["c"].predecessors
        # A has no predecessors; C has no successors
        assert dag.nodes["a"].predecessors == set()
        assert dag.nodes["c"].successors == set()

    def test_fan_out(self):
        """A→{B,C}: A is root, B and C both have A as predecessor."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["a"]}]
        )
        dag = build_dag(workflow)

        assert dag.get_roots() == ["a"]
        assert "b" in dag.nodes["a"].successors
        assert "c" in dag.nodes["a"].successors
        assert dag.nodes["b"].predecessors == {"a"}
        assert dag.nodes["c"].predecessors == {"a"}

    def test_fan_in_diamond(self):
        """A→{B,C}→D: D has two predecessors (B and C)."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
            ]
        )
        dag = build_dag(workflow)

        assert dag.nodes["d"].predecessors == {"b", "c"}
        assert "d" in dag.nodes["b"].successors
        assert "d" in dag.nodes["c"].successors

    def test_unknown_depends_on_raises_validation_error(self):
        """Stage depending on a non-existent stage → WorkflowValidationError."""
        workflow = make_workflow([{"id": "a", "deps": ["nonexistent"]}])
        with pytest.raises(WorkflowValidationError) as exc_info:
            build_dag(workflow)
        assert "nonexistent" in str(exc_info.value)
        assert "a" in str(exc_info.value)

    def test_get_roots_multiple(self):
        """get_roots() returns all stages with no predecessors."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b"}, {"id": "c", "deps": ["a"]}]
        )
        dag = build_dag(workflow)
        roots = dag.get_roots()
        assert "a" in roots
        assert "b" in roots
        assert "c" not in roots

    def test_get_roots_single(self):
        """get_roots() returns exactly one stage for a sequential chain."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]}]
        )
        dag = build_dag(workflow)
        assert dag.get_roots() == ["a"]

    def test_get_successors(self):
        """get_successors() returns correct IDs for a fan-out."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["a"]}]
        )
        dag = build_dag(workflow)
        successors = dag.get_successors("a")
        assert set(successors) == {"b", "c"}

    def test_get_predecessors(self):
        """get_predecessors() returns the IDs this stage depends on."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b"},
                {"id": "c", "deps": ["a", "b"]},
            ]
        )
        dag = build_dag(workflow)
        preds = dag.get_predecessors("c")
        assert set(preds) == {"a", "b"}

    def test_get_successors_empty_for_leaf(self):
        """Leaf stage (no dependents) has empty successors list."""
        workflow = make_workflow([{"id": "a"}, {"id": "b", "deps": ["a"]}])
        dag = build_dag(workflow)
        assert dag.get_successors("b") == []

    def test_get_predecessors_empty_for_root(self):
        """Root stage has empty predecessors list."""
        workflow = make_workflow([{"id": "a"}, {"id": "b", "deps": ["a"]}])
        dag = build_dag(workflow)
        assert dag.get_predecessors("a") == []

    def test_all_stage_ids_declaration_order(self):
        """all_stage_ids() returns IDs in the order stages were declared."""
        stages_data = [
            {"id": "a"},
            {"id": "b", "deps": ["a"]},
            {"id": "c", "deps": ["a"]},
            {"id": "d", "deps": ["b", "c"]},
        ]
        workflow = make_workflow(stages_data)
        dag = build_dag(workflow)
        assert dag.all_stage_ids() == ["a", "b", "c", "d"]

    def test_bidirectional_edges_consistent(self):
        """Predecessor/successor sets are always consistent with each other."""
        workflow = make_workflow(
            [
                {"id": "p"},
                {"id": "q"},
                {"id": "r", "deps": ["p", "q"]},
            ]
        )
        dag = build_dag(workflow)
        # Every predecessor of r must list r as a successor.
        for pred_id in dag.nodes["r"].predecessors:
            assert "r" in dag.nodes[pred_id].successors
        # Every successor of p must list p as a predecessor.
        for succ_id in dag.nodes["p"].successors:
            assert "p" in dag.nodes[succ_id].predecessors


# ===========================================================================
# CYCLE DETECTION TESTS
# ===========================================================================


class TestCycleDetection:
    """Tests for detect_cycles() and build_dag() cycle checking."""

    def _build_cyclic_dag(self, stage_ids, edges):
        """Helper: manually wire a DAG with cycles (bypasses build_dag validation)."""
        nodes = {sid: DAGNode(stage_id=sid, stage=None) for sid in stage_ids}
        for src, dst in edges:
            nodes[src].successors.add(dst)
            nodes[dst].predecessors.add(src)
        return DAG(nodes=nodes)

    def test_direct_cycle_raises(self):
        """A→B→A raises WorkflowCycleError via build_dag."""
        workflow = make_workflow(
            [{"id": "a", "deps": ["b"]}, {"id": "b", "deps": ["a"]}]
        )
        with pytest.raises(WorkflowCycleError):
            build_dag(workflow)

    def test_indirect_cycle_raises(self):
        """A→B→C→A raises WorkflowCycleError."""
        workflow = make_workflow(
            [
                {"id": "a", "deps": ["c"]},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["b"]},
            ]
        )
        with pytest.raises(WorkflowCycleError):
            build_dag(workflow)

    def test_self_reference_raises(self):
        """A stage that depends on itself raises WorkflowCycleError."""
        workflow = make_workflow([{"id": "a", "deps": ["a"]}])
        with pytest.raises(WorkflowCycleError):
            build_dag(workflow)

    def test_cycle_attribute_populated_direct(self):
        """WorkflowCycleError.cycle contains the cycle path for a direct cycle."""
        # Manually build the DAG nodes to bypass unknown-dep validation.
        nodes = {
            "a": DAGNode(stage_id="a", stage=None),
            "b": DAGNode(stage_id="b", stage=None),
        }
        nodes["a"].successors.add("b")
        nodes["b"].predecessors.add("a")
        nodes["b"].successors.add("a")
        nodes["a"].predecessors.add("b")
        dag = DAG(nodes=nodes)

        with pytest.raises(WorkflowCycleError) as exc_info:
            detect_cycles(dag)
        cycle = exc_info.value.cycle
        assert isinstance(cycle, list)
        assert len(cycle) >= 2
        # The first and last element are the same (cycle closes).
        assert cycle[0] == cycle[-1]

    def test_cycle_attribute_populated_self_loop(self):
        """WorkflowCycleError.cycle is populated for a self-loop."""
        nodes = {"a": DAGNode(stage_id="a", stage=None)}
        nodes["a"].successors.add("a")
        nodes["a"].predecessors.add("a")
        dag = DAG(nodes=nodes)

        with pytest.raises(WorkflowCycleError) as exc_info:
            detect_cycles(dag)
        cycle = exc_info.value.cycle
        assert "a" in cycle

    def test_valid_linear_dag_no_error(self):
        """A linear chain does not raise any error."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]}]
        )
        dag = build_dag(workflow)  # must not raise
        assert dag is not None

    def test_valid_diamond_dag_no_error(self):
        """A diamond DAG does not raise any error."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
            ]
        )
        dag = build_dag(workflow)  # must not raise
        assert dag is not None

    def test_detect_cycles_safe_on_acyclic(self):
        """detect_cycles() is safe to call on a known-acyclic DAG."""
        workflow = make_workflow([{"id": "a"}, {"id": "b", "deps": ["a"]}])
        dag = build_dag(workflow)
        detect_cycles(dag)  # must not raise


# ===========================================================================
# PARALLEL BATCH COMPUTATION TESTS
# ===========================================================================


class TestComputeExecutionBatches:
    """Tests for compute_execution_batches() batch grouping."""

    def test_sequential_chain(self):
        """A→B→C produces 3 sequential batches."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]}]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)

        ids = _stage_ids_in_batches(batches)
        assert ids == [["a"], ["b"], ["c"]]

    def test_fully_parallel(self):
        """Three independent stages → one batch with all three."""
        workflow = make_workflow([{"id": "a"}, {"id": "b"}, {"id": "c"}])
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)

        assert len(batches) == 1
        assert set(batches[0].stage_ids) == {"a", "b", "c"}

    def test_diamond_batches(self):
        """A→{B,C}→D produces 3 batches: [A], [B,C], [D]."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
            ]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)

        ids = _stage_ids_in_batches(batches)
        assert ids[0] == ["a"]
        assert set(ids[1]) == {"b", "c"}
        assert ids[2] == ["d"]
        assert len(batches) == 3

    def test_mixed_fan_out_fan_in(self):
        """A→{B,C}→D→E produces 4 batches."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
                {"id": "e", "deps": ["d"]},
            ]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)

        ids = _stage_ids_in_batches(batches)
        assert ids[0] == ["a"]
        assert set(ids[1]) == {"b", "c"}
        assert ids[2] == ["d"]
        assert ids[3] == ["e"]
        assert len(batches) == 4

    def test_single_node(self):
        """A single stage produces exactly one batch."""
        workflow = make_workflow([{"id": "a"}])
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)

        assert len(batches) == 1
        assert batches[0].stage_ids == ["a"]

    def test_batch_count_sequential(self):
        """Batch count equals stage count for a fully sequential chain."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["b"]},
                {"id": "d", "deps": ["c"]},
            ]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)
        assert len(batches) == 4

    def test_batch_count_diamond(self):
        """Diamond graph has exactly 3 batches."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
            ]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)
        assert len(batches) == 3

    def test_stage_order_within_batch_matches_declaration(self):
        """Stages within a batch appear in their original declaration order."""
        # Declare b before c; both depend on a; they should appear b, c in batch 1.
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
            ]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)
        # Batch 1 contains b and c — b was declared first.
        assert batches[1].stage_ids == ["b", "c"]

    def test_batch_indices_contiguous(self):
        """Batch.index values are 0-based and contiguous."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}, {"id": "c", "deps": ["b"]}]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)
        for i, batch in enumerate(batches):
            assert batch.index == i

    def test_compute_batches_method_on_dag(self):
        """DAG.compute_batches() delegates to compute_execution_batches correctly."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}]
        )
        dag = build_dag(workflow)
        via_method = dag.compute_batches()
        via_function = compute_execution_batches(dag)
        assert _stage_ids_in_batches(via_method) == _stage_ids_in_batches(via_function)

    def test_two_independent_chains(self):
        """Two independent A→B and C→D chains produce 2 batches each."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c"},
                {"id": "d", "deps": ["c"]},
            ]
        )
        dag = build_dag(workflow)
        batches = compute_execution_batches(dag)
        ids = _stage_ids_in_batches(batches)
        # Batch 0: a and c (both roots)
        assert set(ids[0]) == {"a", "c"}
        # Batch 1: b and d (both unblocked after batch 0)
        assert set(ids[1]) == {"b", "d"}
        assert len(batches) == 2


# ===========================================================================
# EXECUTION PLAN GENERATOR TESTS
# ===========================================================================


class TestGeneratePlan:
    """Tests for generate_plan() and format_plan_text()."""

    def test_basic_plan_generation(self):
        """Workflow with 2 stages and a required parameter produces an ExecutionPlan."""
        params = {
            "feature_name": WorkflowParameter(type="string", required=True),
        }
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}],
            params=params,
        )
        plan = generate_plan(workflow, {"feature_name": "auth-redesign"})

        assert isinstance(plan, ExecutionPlan)
        assert plan.workflow_id == "test"
        assert plan.workflow_name == "Test Workflow"

    def test_missing_required_parameter_raises(self):
        """Missing required parameter raises WorkflowValidationError."""
        params = {
            "feature_name": WorkflowParameter(type="string", required=True),
        }
        workflow = make_workflow([{"id": "a"}], params=params)

        with pytest.raises(WorkflowValidationError) as exc_info:
            generate_plan(workflow, {})
        assert "feature_name" in str(exc_info.value)

    def test_parameter_default_applied(self):
        """Optional parameter with a default is included in plan.parameters."""
        params = {
            "env": WorkflowParameter(type="string", required=False, default="staging"),
        }
        workflow = make_workflow([{"id": "a"}], params=params)

        plan = generate_plan(workflow, {})
        assert plan.parameters["env"] == "staging"

    def test_caller_value_overrides_default(self):
        """Caller-supplied value overrides the declared default."""
        params = {
            "env": WorkflowParameter(type="string", required=False, default="staging"),
        }
        workflow = make_workflow([{"id": "a"}], params=params)

        plan = generate_plan(workflow, {"env": "production"})
        assert plan.parameters["env"] == "production"

    def test_batch_structure_in_plan(self):
        """Plan batches match the expected topological grouping."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
            ]
        )
        plan = generate_plan(workflow, {})

        assert len(plan.batches) == 3
        stage_ids_0 = [ps.stage_id for ps in plan.batches[0].stages]
        stage_ids_1 = {ps.stage_id for ps in plan.batches[1].stages}
        stage_ids_2 = [ps.stage_id for ps in plan.batches[2].stages]

        assert stage_ids_0 == ["a"]
        assert stage_ids_1 == {"b", "c"}
        assert stage_ids_2 == ["d"]

    def test_stage_primary_artifact_in_plan(self):
        """ExecutionPlanStage.primary_artifact matches the stage's roles.primary.artifact."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})

        plan_stage = plan.batches[0].stages[0]
        assert plan_stage.primary_artifact == "agent:test-agent"

    def test_gate_stage_has_approvers(self):
        """Gate stage in plan has gate_approvers populated."""
        workflow = make_workflow(
            [
                {"id": "build"},
                {"id": "review-gate", "deps": ["build"], "type": "gate", "approvers": ["alice", "bob"]},
                {"id": "deploy", "deps": ["review-gate"]},
            ]
        )
        plan = generate_plan(workflow, {})

        # Gate is in batch 1.
        gate_stage = plan.batches[1].stages[0]
        assert gate_stage.stage_id == "review-gate"
        assert gate_stage.stage_type == "gate"
        assert set(gate_stage.gate_approvers) == {"alice", "bob"}

    def test_gate_timeout_in_plan(self):
        """Gate stage has gate_timeout populated from GateConfig."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "gate", "deps": ["a"], "type": "gate", "approvers": ["mgr"]},
            ]
        )
        plan = generate_plan(workflow, {})

        gate_stage = plan.batches[1].stages[0]
        # Default GateConfig timeout is "24h".
        assert gate_stage.gate_timeout == "24h"

    def test_non_required_parameter_without_default_omitted(self):
        """Non-required parameter without a default and not supplied is omitted from plan."""
        params = {
            "optional_flag": WorkflowParameter(type="boolean", required=False),
        }
        workflow = make_workflow([{"id": "a"}], params=params)

        plan = generate_plan(workflow, {})
        assert "optional_flag" not in plan.parameters

    def test_extra_caller_params_passed_through(self):
        """Undeclared caller-supplied parameters are included in plan.parameters."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {"undeclared_key": "value"})
        assert plan.parameters["undeclared_key"] == "value"

    def test_plan_has_validation_result(self):
        """ExecutionPlan.validation is always populated."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})
        assert plan.validation is not None

    def test_estimated_timeout_non_negative(self):
        """Estimated timeout is always >= 0."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})
        assert plan.estimated_timeout_seconds >= 0


# ===========================================================================
# FORMAT PLAN TEXT TESTS
# ===========================================================================


class TestFormatPlanText:
    """Tests for format_plan_text() output structure."""

    def test_output_contains_workflow_name(self):
        """format_plan_text output includes the workflow name."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "Test Workflow" in text

    def test_output_contains_batch_labels(self):
        """format_plan_text output contains Batch labels."""
        workflow = make_workflow(
            [{"id": "a"}, {"id": "b", "deps": ["a"]}]
        )
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "Batch 1" in text
        assert "Batch 2" in text

    def test_output_contains_stage_ids(self):
        """format_plan_text output contains all stage IDs."""
        workflow = make_workflow(
            [{"id": "alpha"}, {"id": "beta", "deps": ["alpha"]}]
        )
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "alpha" in text
        assert "beta" in text

    def test_output_contains_estimated_time(self):
        """format_plan_text output contains an estimated time line."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "Estimated total time" in text

    def test_output_contains_parameters_section(self):
        """format_plan_text output includes parameters when provided."""
        params = {
            "feature_name": WorkflowParameter(type="string", required=True),
        }
        workflow = make_workflow([{"id": "a"}], params=params)
        plan = generate_plan(workflow, {"feature_name": "my-feature"})
        text = format_plan_text(plan)
        assert "feature_name" in text
        assert "my-feature" in text

    def test_format_method_on_plan_equals_function(self):
        """ExecutionPlan.format_text() returns same result as format_plan_text()."""
        workflow = make_workflow([{"id": "a"}, {"id": "b", "deps": ["a"]}])
        plan = generate_plan(workflow, {})
        assert plan.format_text() == format_plan_text(plan)

    def test_output_gate_stage_shows_type(self):
        """Gate stage in format_plan_text output shows type and approvers."""
        workflow = make_workflow(
            [
                {"id": "build"},
                {"id": "approve", "deps": ["build"], "type": "gate", "approvers": ["lead"]},
            ]
        )
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "approve" in text
        assert "manual_approval" in text
        assert "lead" in text

    def test_parallel_label_in_diamond_batch(self):
        """Batch with multiple stages is labelled as parallel."""
        workflow = make_workflow(
            [
                {"id": "a"},
                {"id": "b", "deps": ["a"]},
                {"id": "c", "deps": ["a"]},
                {"id": "d", "deps": ["b", "c"]},
            ]
        )
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "parallel" in text

    def test_sequential_label_for_single_stage_batch(self):
        """Batch with one stage is labelled as sequential."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "sequential" in text

    def test_none_parameters_shows_none_label(self):
        """Workflow with no parameters shows '(none)' in the parameters line."""
        workflow = make_workflow([{"id": "a"}])
        plan = generate_plan(workflow, {})
        text = format_plan_text(plan)
        assert "Parameters: (none)" in text
