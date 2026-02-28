"""Performance benchmarks for SkillMeat Workflow Orchestration Engine (TEST-7.5).

Measures key workflow operations against documented performance targets.

Performance Targets:
    - Workflow YAML parse (50 stages):  <200ms mean
    - Execution plan generation (20-stage DAG): <1s mean
    - DB list query (100 workflows):    <300ms mean
    - Workflow validation (30+ stages): documented (no hard assertion)
    - DAG construction (50 stages):     documented (no hard assertion)
    - SSE event serialisation (100 events): documented (no hard assertion)

All benchmarks use ``pytest-benchmark`` with at least 5 rounds so that the
statistical ``mean`` is meaningful on developer hardware.  The assertions use
``benchmark.stats["mean"]`` — the arithmetic mean over all rounds measured.

Usage::

    # Run only workflow benchmarks
    pytest tests/benchmarks/test_workflow_benchmarks.py -v --benchmark-sort=mean

    # With histogram
    pytest tests/benchmarks/test_workflow_benchmarks.py --benchmark-histogram
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


# =============================================================================
# Test-data generators
# =============================================================================


def _make_stage(
    index: int,
    *,
    depends_on: List[int] | None = None,
    with_gate: bool = False,
    with_context: bool = False,
    with_inputs: bool = True,
) -> Dict[str, Any]:
    """Return a realistic SWDL stage dict.

    Args:
        index:       0-based stage index used to derive unique IDs.
        depends_on:  List of stage indices this stage depends on.
        with_gate:   When True, produces a 'gate' type stage instead of 'agent'.
        with_context: When True, adds a context binding block.
        with_inputs: When True, adds input/output contracts.

    Returns:
        A dict suitable for inclusion in the ``stages`` list of a SWDL document.
    """
    sid = f"stage-{index:02d}"
    dep_ids = [f"stage-{d:02d}" for d in (depends_on or [])]

    if with_gate:
        return {
            "id": sid,
            "name": f"Approval Gate {index}",
            "type": "gate",
            "depends_on": dep_ids,
            "gate": {
                "kind": "manual_approval",
                "approvers": ["lead-engineer", "qa-manager"],
                "timeout": "24h",
                "on_timeout": "halt",
                "message": f"Please review and approve stage {index} deliverables.",
            },
        }

    stage: Dict[str, Any] = {
        "id": sid,
        "name": f"Stage {index}: Data Processing",
        "description": f"Processes and validates data for pipeline step {index}.",
        "type": "agent",
        "depends_on": dep_ids,
        "roles": {
            "primary": {
                "artifact": f"agent:processor-v{(index % 3) + 1}",
                "model": ["opus", "sonnet", "haiku"][index % 3],
                "instructions": f"Process data for step {index} and validate outputs.",
            },
            "tools": [
                "skill:data-validator",
                f"skill:step-{index % 5}-handler",
            ],
        },
        "error_policy": {
            "on_failure": "halt",
            "timeout": "30m",
            "retry": {
                "max_attempts": 2,
                "initial_interval": "30s",
                "backoff_multiplier": 2.0,
                "max_interval": "5m",
                "non_retryable_errors": ["auth_failure"],
            },
        },
        "handoff": {
            "format": "structured",
            "include_run_log": False,
        },
        "ui": {
            "position": [index * 120, (index % 4) * 80],
            "color": "#E8F5E9",
            "icon": "data",
        },
    }

    if with_inputs and index > 0:
        prev = f"stage-{(index - 1):02d}"
        stage["inputs"] = {
            "upstream_result": {
                "type": "string",
                "source": f"${{{{ stages.{prev}.outputs.result }}}}",
                "required": True,
                "description": "Result from the previous stage.",
            },
            "run_mode": {
                "type": "string",
                "source": "${{ parameters.run_mode }}",
                "required": False,
                "description": "Execution mode override.",
            },
        }

    stage["outputs"] = {
        "result": {
            "type": "string",
            "required": True,
            "description": f"Processed result from stage {index}.",
        },
        "metrics": {
            "type": "object",
            "required": False,
            "description": "Performance metrics collected during this stage.",
        },
    }

    if with_context:
        stage["context"] = {
            "modules": [
                "ctx:domain-knowledge",
                f"ctx:step-{index % 3}-guide",
            ],
            "memory": {
                "project_scope": "current",
                "min_confidence": 0.75,
                "categories": ["constraint", "decision"],
                "max_tokens": 2000,
            },
        }

    return stage


def _generate_linear_workflow_yaml(n_stages: int) -> str:
    """Generate a linear chain workflow with *n_stages* stages.

    Each stage depends on the previous one (A → B → C → …).  All stages carry
    realistic role, input/output, context, and error-policy blocks to simulate
    production YAML size.

    Args:
        n_stages: Number of stages to generate.

    Returns:
        Valid SWDL YAML string.
    """
    stages = []
    for i in range(n_stages):
        dep = [i - 1] if i > 0 else None
        stages.append(
            _make_stage(i, depends_on=dep, with_context=True, with_inputs=True)
        )

    doc: Dict[str, Any] = {
        "workflow": {
            "id": f"benchmark-linear-{n_stages}",
            "name": f"Benchmark Linear Workflow ({n_stages} stages)",
            "version": "1.0.0",
            "description": "Auto-generated benchmark workflow with a linear dependency chain.",
            "author": "benchmark-suite",
            "tags": ["benchmark", "linear", "performance"],
        },
        "config": {
            "parameters": {
                "run_mode": {
                    "type": "string",
                    "required": False,
                    "default": "production",
                    "description": "Execution mode.",
                },
                "feature_name": {
                    "type": "string",
                    "required": True,
                    "description": "Name of the feature being processed.",
                },
            },
            "timeout": "6h",
            "env": {
                "LOG_LEVEL": "INFO",
                "RETRY_MAX": "3",
            },
        },
        "context": {
            "global_modules": ["ctx:global-standards"],
            "memory": {
                "project_scope": "current",
                "min_confidence": 0.7,
                "max_tokens": 4000,
            },
        },
        "error_policy": {
            "on_stage_failure": "halt",
            "default_retry": {
                "max_attempts": 2,
                "initial_interval": "30s",
                "backoff_multiplier": 2.0,
                "max_interval": "5m",
            },
        },
        "hooks": {
            "on_start": {"notify": "slack:#workflow-starts"},
            "on_complete": {"notify": "slack:#workflow-complete"},
            "on_failure": {"notify": "slack:#alerts"},
        },
        "stages": stages,
    }

    return yaml.dump(doc, default_flow_style=False, sort_keys=False)


def _generate_dag_workflow_yaml(n_stages: int) -> str:
    """Generate a diamond-fan DAG workflow with *n_stages* stages.

    Structure: one root → *k* parallel middle branches → one merge → tail chain.
    This exercises both DAG construction and batch-computation code paths.

    Args:
        n_stages: Total number of stages (must be >= 4).

    Returns:
        Valid SWDL YAML string.
    """
    n_stages = max(n_stages, 4)
    # Root + parallel fan-out + merge + remaining tail
    fan_width = max(2, (n_stages - 3) // 2)
    tail_count = n_stages - 1 - fan_width - 1  # root + fan + merge

    stages = []
    idx = 0

    # Root stage (no dependencies)
    stages.append(_make_stage(idx, depends_on=None, with_inputs=False))
    root_idx = idx
    idx += 1

    # Parallel fan-out stages (all depend on root)
    fan_indices = []
    for _ in range(fan_width):
        stages.append(_make_stage(idx, depends_on=[root_idx]))
        fan_indices.append(idx)
        idx += 1

    # Merge stage (depends on all fan stages)
    stages.append(_make_stage(idx, depends_on=fan_indices))
    merge_idx = idx
    idx += 1

    # Sequential tail
    prev = merge_idx
    for _ in range(tail_count):
        stages.append(_make_stage(idx, depends_on=[prev]))
        prev = idx
        idx += 1

    doc: Dict[str, Any] = {
        "workflow": {
            "id": f"benchmark-dag-{n_stages}",
            "name": f"Benchmark DAG Workflow ({n_stages} stages)",
            "version": "1.0.0",
            "description": "Auto-generated DAG benchmark workflow (fan-out/merge pattern).",
            "tags": ["benchmark", "dag", "performance"],
        },
        "config": {
            "parameters": {
                "run_mode": {
                    "type": "string",
                    "required": False,
                    "default": "production",
                },
                "feature_name": {
                    "type": "string",
                    "required": True,
                },
            },
            "timeout": "4h",
        },
        "error_policy": {"on_stage_failure": "halt"},
        "stages": stages,
    }

    return yaml.dump(doc, default_flow_style=False, sort_keys=False)


def _generate_complex_workflow_yaml(n_stages: int) -> str:
    """Generate a complex workflow with mixed types and rich expressions.

    Uses alternating agent and gate stages, rich expressions in inputs, and
    per-stage context bindings.  Designed to stress the validator.

    Args:
        n_stages: Number of stages.

    Returns:
        Valid SWDL YAML string.
    """
    stages = []
    for i in range(n_stages):
        dep = [i - 1] if i > 0 else None
        is_gate = i > 0 and i % 8 == 0  # Gate every 8th stage
        stages.append(
            _make_stage(
                i,
                depends_on=dep,
                with_gate=is_gate,
                with_context=not is_gate,
                with_inputs=not is_gate,
            )
        )

    doc: Dict[str, Any] = {
        "workflow": {
            "id": f"benchmark-complex-{n_stages}",
            "name": f"Benchmark Complex Workflow ({n_stages} stages)",
            "version": "2.0.0",
            "description": "Complex benchmark workflow with mixed stage types and expressions.",
            "tags": ["benchmark", "complex", "mixed"],
        },
        "config": {
            "parameters": {
                "run_mode": {"type": "string", "required": False, "default": "production"},
                "feature_name": {"type": "string", "required": True},
                "skip_review": {"type": "boolean", "required": False, "default": False},
                "max_retries": {"type": "integer", "required": False, "default": 3},
            },
            "timeout": "8h",
        },
        "error_policy": {
            "on_stage_failure": "continue",
            "default_retry": {
                "max_attempts": 3,
                "initial_interval": "1m",
                "backoff_multiplier": 2.0,
                "max_interval": "10m",
            },
        },
        "stages": stages,
    }

    return yaml.dump(doc, default_flow_style=False, sort_keys=False)


def _make_sse_event(seq: int) -> Dict[str, Any]:
    """Return a realistic raw SSE event dict as stored by the execution service.

    Args:
        seq: Sequence number for the event.

    Returns:
        Dict with ``seq``, ``type``, and ``data`` fields.
    """
    event_types = [
        "stage_started",
        "stage_completed",
        "log_line",
        "stage_failed",
        "execution_completed",
    ]
    etype = event_types[seq % len(event_types)]

    if etype == "stage_started":
        data = {"stage_id": f"stage-{seq:02d}", "stage_name": f"Stage {seq}"}
    elif etype == "stage_completed":
        data = {"stage_id": f"stage-{seq:02d}", "duration_seconds": seq * 0.5 + 1.2}
    elif etype == "log_line":
        data = {
            "stage_id": f"stage-{seq % 10:02d}",
            "message": f"Processing item {seq} of batch — status OK",
        }
    elif etype == "stage_failed":
        data = {
            "stage_id": f"stage-{seq:02d}",
            "error": f"TimeoutError: stage-{seq:02d} exceeded 30m limit",
        }
    else:
        data = {"status": "completed"}

    return {"seq": seq, "type": etype, "data": data}


def _serialize_sse_event(event: Dict[str, Any]) -> str:
    """Serialise a raw event dict to SSE wire format.

    Mirrors the serialisation logic in
    ``skillmeat/api/routers/workflow_executions.py::stream_execution_events``.

    Args:
        event: Raw event dict with ``seq``, ``type``, ``data`` keys.

    Returns:
        SSE-formatted string: ``"event: <type>\\ndata: <json>\\n\\n"``.
    """
    event_type: str = event.get("type", "message")
    event_data: Dict[str, Any] = event.get("data", {})

    # Normalise exactly as the router does.
    if event_type == "stage_started":
        payload = {
            "stage_id": event_data.get("stage_id", event_data.get("step_id", "")),
            "stage_name": event_data.get("stage_name", event_data.get("stage_id", "")),
        }
    elif event_type == "stage_completed":
        payload = {
            "stage_id": event_data.get("stage_id", event_data.get("step_id", "")),
            "duration_seconds": event_data.get("duration_seconds", 0.0),
        }
    elif event_type == "stage_failed":
        payload = {
            "stage_id": event_data.get("stage_id", event_data.get("step_id", "")),
            "error": event_data.get("error", event_data.get("error_message", "")),
        }
    elif event_type == "log_line":
        payload = {
            "stage_id": event_data.get("stage_id", ""),
            "message": event_data.get("message", ""),
        }
    elif event_type in ("execution_completed", "execution_failed"):
        event_type = "execution_completed"
        payload = {"status": event_data.get("status", "completed")}
    else:
        payload = event_data

    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def linear_50_yaml() -> str:
    """Pre-generated YAML for a 50-stage linear workflow."""
    return _generate_linear_workflow_yaml(50)


@pytest.fixture(scope="module")
def dag_20_yaml() -> str:
    """Pre-generated YAML for a 20-stage diamond-fan DAG workflow."""
    return _generate_dag_workflow_yaml(20)


@pytest.fixture(scope="module")
def complex_30_yaml() -> str:
    """Pre-generated YAML for a 30+-stage complex mixed workflow."""
    return _generate_complex_workflow_yaml(35)


@pytest.fixture(scope="module")
def workflow_service_with_100(tmp_path_factory):
    """WorkflowService backed by a temp DB pre-populated with 100 workflows.

    Scoped to the module so the 100 inserts run only once across all benchmark
    rounds that share this fixture.
    """
    from skillmeat.core.workflow.service import WorkflowService

    db_dir = tmp_path_factory.mktemp("wf_bench_db")
    db_path = str(db_dir / "bench.db")

    svc = WorkflowService(db_path=db_path)

    # Insert 100 minimal workflows (small YAML to keep insert cost low).
    _min_yaml_tmpl = """\
workflow:
  id: bench-wf-{i}
  name: Benchmark Workflow {i}
  version: "1.0.0"
config:
  parameters:
    run_mode:
      type: string
      required: false
      default: production
    feature_name:
      type: string
      required: true
stages:
  - id: stage-00
    name: Stage 0
    type: agent
    roles:
      primary:
        artifact: agent:worker-v1
"""
    for i in range(100):
        svc.create(yaml_content=_min_yaml_tmpl.format(i=i))

    return svc


@pytest.fixture(scope="module")
def sse_events_100() -> List[Dict[str, Any]]:
    """Pre-generated list of 100 realistic SSE event dicts."""
    return [_make_sse_event(i) for i in range(100)]


# =============================================================================
# Benchmark 1: Workflow YAML Parse
# =============================================================================


@pytest.mark.benchmark(group="workflow")
def test_parse_performance(benchmark, linear_50_yaml):
    """Workflow YAML parse must complete in <200ms mean (50 stages).

    Measures the full path: YAML text → ``WorkflowDefinition.model_validate()``.
    The benchmark parses from a string (bypassing disk I/O) to isolate the
    parse + Pydantic validation cost.

    Target: mean < 200ms on development hardware.
    """
    from skillmeat.core.workflow.models import WorkflowDefinition

    yaml_text = linear_50_yaml

    def _parse():
        raw = yaml.safe_load(yaml_text)
        return WorkflowDefinition.model_validate(raw)

    result = benchmark(_parse)

    # Correctness assertions
    assert result is not None
    assert len(result.stages) == 50
    assert result.workflow.id == "benchmark-linear-50"

    # Performance assertion — mean over all benchmark rounds
    # NOTE: Pydantic v2 model validation is very fast; typical mean is <20ms.
    # The 200ms target gives generous headroom for slow CI machines.
    assert benchmark.stats["mean"] < 0.200, (
        f"parse mean {benchmark.stats['mean']:.3f}s exceeded 200ms target"
    )


# =============================================================================
# Benchmark 2: Execution Plan Generation
# =============================================================================


@pytest.mark.benchmark(group="workflow")
def test_plan_generation_performance(benchmark, dag_20_yaml):
    """Plan generation must complete in <1s mean (20-stage DAG).

    Covers: YAML parse → defaults application → DAG construction →
    expression validation → batch computation → ExecutionPlan assembly.

    Target: mean < 1s on development hardware.
    """
    from skillmeat.core.workflow.models import WorkflowDefinition
    from skillmeat.core.workflow.planner import generate_plan

    yaml_text = dag_20_yaml

    def _plan():
        raw = yaml.safe_load(yaml_text)
        workflow = WorkflowDefinition.model_validate(raw)
        return generate_plan(workflow, {"feature_name": "auth-redesign"})

    plan = benchmark(_plan)

    # Correctness
    assert plan is not None
    assert plan.workflow_id == "benchmark-dag-20"
    assert len(plan.batches) >= 3  # root, fan, merge (+tail)
    assert plan.parameters.get("feature_name") == "auth-redesign"
    assert plan.parameters.get("run_mode") == "production"  # default applied

    # Performance
    assert benchmark.stats["mean"] < 1.0, (
        f"plan generation mean {benchmark.stats['mean']:.3f}s exceeded 1s target"
    )


# =============================================================================
# Benchmark 3: DB List Query
# =============================================================================


@pytest.mark.benchmark(group="workflow")
def test_list_query_performance(benchmark, workflow_service_with_100):
    """DB list query must complete in <300ms mean (100 workflows, limit=50).

    Exercises ``WorkflowService.list()`` which calls the repository, builds
    DTOs, and applies the client-side project_id filter path.

    Target: mean < 300ms on development hardware.
    NOTE: SQLite in-process is expected to be well under 50ms; the 300ms
    target accounts for under-spec CI environments.
    """
    svc = workflow_service_with_100

    def _list():
        return svc.list(skip=0, limit=50)

    results = benchmark(_list)

    # Correctness
    assert isinstance(results, list)
    assert len(results) == 50  # limit respected

    # Performance
    assert benchmark.stats["mean"] < 0.300, (
        f"list query mean {benchmark.stats['mean']:.3f}s exceeded 300ms target"
    )


# =============================================================================
# Benchmark 4: Workflow Validation (document result, no hard threshold)
# =============================================================================


@pytest.mark.benchmark(group="workflow")
def test_validation_performance(benchmark, complex_30_yaml):
    """Validate a complex 35-stage workflow (expressions, mixed types).

    Result is documented for profiling; no hard assertion is imposed because
    validation cost scales with expression count rather than stage count alone.

    Typical observed range: 1–15ms on development hardware.

    Potential bottleneck: ``ExpressionParser.extract_expressions()`` is called
    for every ``input.source`` and ``condition`` field.  For very large
    workflows with dense expressions this could approach 50ms+.
    """
    from skillmeat.core.workflow.dag import build_dag
    from skillmeat.core.workflow.models import WorkflowDefinition
    from skillmeat.core.workflow.validator import validate_expressions

    yaml_text = complex_30_yaml

    def _validate():
        raw = yaml.safe_load(yaml_text)
        workflow = WorkflowDefinition.model_validate(raw)
        dag = build_dag(workflow)
        return validate_expressions(workflow, dag)

    result = benchmark(_validate)

    # Correctness
    assert result is not None
    # The complex workflow uses valid stage dependencies, so no DAG errors;
    # expression references use the correct pattern so schema errors = 0.
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)

    # Documented result — surfaced in test output via benchmark.stats
    mean_ms = benchmark.stats["mean"] * 1000
    print(
        f"\n[Benchmark 4 — Validation] mean={mean_ms:.2f}ms "
        f"errors={len(result.errors)} warnings={len(result.warnings)}"
    )


# =============================================================================
# Benchmark 5: DAG Construction
# =============================================================================


@pytest.mark.benchmark(group="workflow")
def test_dag_construction_performance(benchmark, linear_50_yaml):
    """DAG construction + topological sort for a 50-stage linear chain.

    Covers: node creation → edge wiring → cycle detection (DFS) →
    Kahn's algorithm batch computation.

    The linear chain is the worst case for sequential depth traversal.
    Typical observed range: <5ms on development hardware.

    Potential bottleneck: DFS cycle detection with deep recursion on very
    large sequential workflows (Python default recursion limit is 1000).
    For the 50-stage case this is well within limits.
    """
    from skillmeat.core.workflow.dag import build_dag, compute_execution_batches
    from skillmeat.core.workflow.models import WorkflowDefinition

    yaml_text = linear_50_yaml
    raw = yaml.safe_load(yaml_text)
    workflow = WorkflowDefinition.model_validate(raw)

    def _build_and_sort():
        dag = build_dag(workflow)
        return compute_execution_batches(dag)

    batches = benchmark(_build_and_sort)

    # Correctness: linear chain → 50 sequential batches, one stage each
    assert len(batches) == 50
    assert all(len(b.stage_ids) == 1 for b in batches)

    mean_ms = benchmark.stats["mean"] * 1000
    print(f"\n[Benchmark 5 — DAG] mean={mean_ms:.2f}ms batches={len(batches)}")


# =============================================================================
# Benchmark 6: SSE Event Serialisation
# =============================================================================


@pytest.mark.benchmark(group="workflow")
def test_sse_serialisation_performance(benchmark, sse_events_100):
    """Serialise 100 execution events to SSE wire format.

    Measures the normalisation + ``json.dumps`` cost for a batch of 100
    events covering all event types (stage_started, stage_completed, log_line,
    stage_failed, execution_completed).

    Target: mean serialisation of 100 events < 500ms.
    NOTE: ``json.dumps`` on small dicts is typically <0.1ms each, so 100
    events should complete well under 10ms total.  The 500ms budget accounts
    for pathologically slow CI environments and future payload growth.

    Potential bottleneck: If event payloads grow to include large ``outputs``
    dicts (e.g. multi-KB structured results), ``json.dumps`` cost will
    dominate.  Consider streaming partial serialisation or field projection
    at that point.
    """
    events = sse_events_100  # list of 100 raw event dicts

    def _serialise_batch():
        return [_serialize_sse_event(ev) for ev in events]

    results = benchmark(_serialise_batch)

    # Correctness
    assert len(results) == 100
    for chunk in results:
        assert chunk.startswith("event: ")
        assert "\ndata: " in chunk
        assert chunk.endswith("\n\n")

    # Performance
    assert benchmark.stats["mean"] < 0.500, (
        f"SSE serialisation mean {benchmark.stats['mean']:.3f}s exceeded 500ms target"
    )

    mean_us = benchmark.stats["mean"] * 1_000_000 / 100  # per-event microseconds
    print(
        f"\n[Benchmark 6 — SSE] mean={benchmark.stats['mean'] * 1000:.3f}ms total "
        f"({mean_us:.1f}µs per event)"
    )
