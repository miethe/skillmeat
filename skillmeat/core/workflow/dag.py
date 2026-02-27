"""Dependency graph (DAG) builder for SkillMeat Workflow Definition Language (SWDL).

This module constructs a directed acyclic graph representation from a parsed
``WorkflowDefinition``, making stage dependencies explicit and navigable for
the execution engine.

Both edge validation (unknown ``depends_on`` references) and cycle detection
are performed by ``build_dag()``, so callers receive a guaranteed acyclic graph
or a descriptive exception.

Usage::

    from skillmeat.core.workflow import WorkflowDefinition
    from skillmeat.core.workflow.dag import build_dag, DAG, DAGNode

    workflow = WorkflowDefinition.model_validate(data)
    dag = build_dag(workflow)

    roots = dag.get_roots()           # stages with no predecessors
    deps = dag.get_predecessors("b")  # what must run before "b"
    next_ = dag.get_successors("a")   # what runs after "a"

    batches = dag.compute_batches()   # parallel execution groups
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Dict, List

from skillmeat.core.workflow.exceptions import WorkflowCycleError, WorkflowValidationError
from skillmeat.core.workflow.models import StageDefinition, WorkflowDefinition


@dataclass
class DAGNode:
    """A single node in the workflow dependency graph.

    Attributes:
        stage_id:     Unique stage identifier matching ``StageDefinition.id``.
        stage:        The full stage definition this node wraps.
        predecessors: IDs of stages that must complete before this stage runs
                      (i.e. stages listed in this stage's ``depends_on``).
        successors:   IDs of stages that depend on this stage completing first.
    """

    stage_id: str
    stage: StageDefinition
    predecessors: set[str] = field(default_factory=set)
    successors: set[str] = field(default_factory=set)


@dataclass
class Batch:
    """A single parallel execution group produced by ``compute_execution_batches``.

    All stages within one ``Batch`` have no dependency on each other and may
    execute concurrently.  Batches are ordered: batch *N* must complete before
    batch *N+1* may start.

    Attributes:
        index:     0-based position of this batch in the execution plan.
        stage_ids: IDs of stages that belong to this batch.
    """

    index: int
    stage_ids: List[str]


@dataclass
class DAG:
    """Directed acyclic graph of workflow stages.

    Provides efficient lookup and traversal of stage relationships built from
    a ``WorkflowDefinition``.  The nodes dict preserves insertion order
    (Python 3.7+ dict guarantee), which matches the declaration order of
    stages in the WORKFLOW.yaml file.

    Attributes:
        nodes: Mapping of stage_id to its ``DAGNode``.
    """

    nodes: Dict[str, DAGNode]

    def get_roots(self) -> List[str]:
        """Return stage IDs that have no predecessors.

        These stages can begin execution immediately (in parallel) when the
        workflow starts, as they have no dependencies.

        Returns:
            Stage IDs with an empty predecessor set, in declaration order.
        """
        return [
            node.stage_id
            for node in self.nodes.values()
            if not node.predecessors
        ]

    def get_stage(self, stage_id: str) -> StageDefinition:
        """Return the ``StageDefinition`` for the given stage ID.

        Args:
            stage_id: The unique stage identifier to look up.

        Returns:
            The ``StageDefinition`` associated with ``stage_id``.

        Raises:
            KeyError: If ``stage_id`` is not present in this DAG.
        """
        return self.nodes[stage_id].stage

    def get_successors(self, stage_id: str) -> List[str]:
        """Return IDs of stages that depend on ``stage_id``.

        These are stages that list ``stage_id`` in their ``depends_on`` and
        therefore cannot start until this stage completes.

        Args:
            stage_id: The stage whose dependents to return.

        Returns:
            List of successor stage IDs in declaration order.

        Raises:
            KeyError: If ``stage_id`` is not present in this DAG.
        """
        return list(self.nodes[stage_id].successors)

    def get_predecessors(self, stage_id: str) -> List[str]:
        """Return IDs of stages that ``stage_id`` depends on.

        These are the stages that must complete before ``stage_id`` can run.

        Args:
            stage_id: The stage whose dependencies to return.

        Returns:
            List of predecessor stage IDs in declaration order.

        Raises:
            KeyError: If ``stage_id`` is not present in this DAG.
        """
        return list(self.nodes[stage_id].predecessors)

    def all_stage_ids(self) -> List[str]:
        """Return all stage IDs in their original declaration order.

        Returns:
            List of every stage ID contained in this DAG.
        """
        return list(self.nodes.keys())

    def compute_batches(self) -> List[Batch]:
        """Group stages into parallel execution batches using Kahn's algorithm.

        Delegates to :func:`compute_execution_batches`.

        Returns:
            Ordered list of :class:`Batch` objects.  Each batch contains stage
            IDs that may run concurrently.  Batch 0 runs first; batch *N* runs
            only after all stages in batch *N-1* have completed.
        """
        return compute_execution_batches(self)


def detect_cycles(dag: DAG) -> None:
    """Detect cycles in the workflow dependency DAG using DFS node coloring.

    Uses the standard three-color DFS algorithm:

    - WHITE (0): node not yet visited
    - GRAY  (1): node currently on the DFS recursion stack (in-progress)
    - BLACK (2): node and all its successors fully explored (safe)

    If a DFS traversal encounters a GRAY node, a back-edge exists and a cycle
    is present.  The cycle path is reconstructed from the DFS stack and
    included in the raised exception.

    Args:
        dag: A fully built ``DAG`` instance (nodes and edges wired).

    Raises:
        WorkflowCycleError: If any cycle is detected.  The exception's
            ``cycle`` attribute contains the stage IDs forming the cycle,
            e.g. ``["a", "b", "c", "a"]`` for an indirect three-node cycle
            or ``["a", "a"]`` for a self-loop.

    Example::

        dag = build_dag(workflow)   # also calls detect_cycles internally
        detect_cycles(dag)          # safe to call again; raises if cyclic
    """
    WHITE = 0
    GRAY = 1
    BLACK = 2

    color: Dict[str, int] = {node_id: WHITE for node_id in dag.nodes}
    # Tracks the current DFS path for cycle reconstruction.
    stack: List[str] = []

    def _dfs(node_id: str) -> None:
        color[node_id] = GRAY
        stack.append(node_id)

        for successor_id in dag.nodes[node_id].successors:
            if color[successor_id] == GRAY:
                # Back-edge found: reconstruct the cycle segment from the stack.
                cycle_start = stack.index(successor_id)
                cycle_path = stack[cycle_start:] + [successor_id]
                raise WorkflowCycleError(
                    f"Cycle detected in workflow stage dependencies: "
                    f"{' -> '.join(cycle_path)}",
                    cycle=cycle_path,
                )
            if color[successor_id] == WHITE:
                _dfs(successor_id)

        stack.pop()
        color[node_id] = BLACK

    for node_id in dag.nodes:
        if color[node_id] == WHITE:
            _dfs(node_id)


def build_dag(workflow: WorkflowDefinition) -> DAG:
    """Build a ``DAG`` from a parsed ``WorkflowDefinition``.

    Algorithm:

    1. Create one ``DAGNode`` for each stage, keyed by ``stage.id``.
    2. For each stage's ``depends_on`` list, validate that every referenced ID
       is a known stage, then wire predecessor/successor edges bidirectionally.
    3. Run cycle detection via ``detect_cycles()`` and raise immediately if
       any cycle is found.

    Args:
        workflow: A fully parsed and Pydantic-validated ``WorkflowDefinition``.

    Returns:
        A ``DAG`` instance with all nodes and edges populated and verified
        to be acyclic.

    Raises:
        WorkflowValidationError: If any ``depends_on`` entry references a stage
            ID that does not exist in the workflow's stage list.
        WorkflowCycleError: If the dependency graph contains a cycle.

    Example::

        workflow = WorkflowDefinition.model_validate(yaml.safe_load(text))
        dag = build_dag(workflow)
        print(dag.get_roots())        # ["research", "setup"]
        print(dag.all_stage_ids())    # ["research", "setup", "implement", ...]
    """
    # Pass 1: Build nodes indexed by stage ID.
    nodes: Dict[str, DAGNode] = {}
    for stage in workflow.stages:
        nodes[stage.id] = DAGNode(stage_id=stage.id, stage=stage)

    # Pass 2: Wire edges and validate all depends_on references.
    for stage in workflow.stages:
        for dep_id in stage.depends_on:
            if dep_id not in nodes:
                raise WorkflowValidationError(
                    f"Stage '{stage.id}' depends on unknown stage '{dep_id}'"
                )
            # Predecessor of the current stage = the dependency.
            nodes[stage.id].predecessors.add(dep_id)
            # Successor of the dependency = the current stage.
            nodes[dep_id].successors.add(stage.id)

    dag = DAG(nodes=nodes)

    # Pass 3: Detect cycles and raise immediately if any are found.
    detect_cycles(dag)

    return dag


def compute_execution_batches(dag: DAG) -> List[Batch]:
    """Group DAG stages into parallel execution batches using Kahn's algorithm.

    The algorithm performs a BFS-style topological sort that naturally groups
    nodes into *levels* — sets of nodes that have no dependency on one another
    and can therefore execute concurrently.

    Algorithm::

        1. Compute in-degree for every node (number of predecessors).
        2. Batch 0 = all nodes whose in-degree is 0 (no dependencies / roots).
        3. "Process" the current batch:
               for each stage_id in the batch:
                   for each successor of stage_id:
                       decrement successor's in-degree by 1
                       if in-degree reaches 0 → add to next batch
        4. Advance: the next batch becomes the current batch.
        5. Repeat until no nodes remain unprocessed.
        6. If any nodes still have non-zero in-degree after the loop, a cycle
           exists in the graph.  This should not occur if ``build_dag`` already
           ran cycle detection, but the guard is included for safety.

    Handles all common DAG shapes correctly:

    * **Sequential** (A → B → C) → [[A], [B], [C]]
    * **Fully parallel** (A, B, C with no edges) → [[A, B, C]]
    * **Diamond** (A → {B, C} → D) → [[A], [B, C], [D]]
    * **Mixed fan-out/fan-in** → stages are always placed in the earliest
      batch in which all their predecessors have been processed.

    Args:
        dag: A ``DAG`` instance built by ``build_dag()``.  The graph must be
             acyclic; callers should run ``detect_cycles`` beforehand.

    Returns:
        An ordered list of :class:`Batch` objects.  The list is non-empty for
        any non-empty DAG.  Batch indices are 0-based and contiguous.

    Raises:
        RuntimeError: If a cycle is detected during batch computation
            (indicates ``build_dag`` was called without cycle detection).

    Example::

        dag = build_dag(workflow)
        for batch in compute_execution_batches(dag):
            print(f"Batch {batch.index}: {batch.stage_ids}")
        # Batch 0: ['a']
        # Batch 1: ['b', 'c']
        # Batch 2: ['d']
    """
    # Step 1: Compute in-degree for each node.
    in_degree: Dict[str, int] = {
        stage_id: len(node.predecessors)
        for stage_id, node in dag.nodes.items()
    }

    # Step 2: Seed the BFS queue with all root nodes (in-degree == 0).
    # Use a deque for O(1) pops; maintain declaration order within each batch
    # by iterating dag.nodes (insertion-ordered dict) rather than the arbitrary
    # order that a set would give us.
    current_batch_ids: List[str] = [
        stage_id for stage_id, deg in in_degree.items() if deg == 0
    ]

    batches: List[Batch] = []
    processed: int = 0

    while current_batch_ids:
        batch_index = len(batches)
        batches.append(Batch(index=batch_index, stage_ids=list(current_batch_ids)))
        processed += len(current_batch_ids)

        # Step 3: Decrement in-degree of successors; collect the next batch.
        next_batch_ids: List[str] = []
        for stage_id in current_batch_ids:
            for successor_id in dag.nodes[stage_id].successors:
                in_degree[successor_id] -= 1
                if in_degree[successor_id] == 0:
                    next_batch_ids.append(successor_id)

        # Sort next batch to match declaration order (successors come from a set).
        declaration_order = list(dag.nodes.keys())
        next_batch_ids.sort(key=lambda sid: declaration_order.index(sid))

        current_batch_ids = next_batch_ids

    # Step 6: Cycle guard.
    if processed != len(dag.nodes):
        remaining = [sid for sid, deg in in_degree.items() if deg > 0]
        raise RuntimeError(
            f"Cycle detected during batch computation — "
            f"{len(dag.nodes) - processed} stage(s) unreachable: {remaining}"
        )

    return batches
