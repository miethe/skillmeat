"""Dependency graph (DAG) builder for SkillMeat Workflow Definition Language (SWDL).

This module constructs a directed acyclic graph representation from a parsed
``WorkflowDefinition``, making stage dependencies explicit and navigable for
the execution engine.

Cycle detection is intentionally excluded here (see DAG-1.8 for that concern).
This module only builds the graph structure and validates that all ``depends_on``
references point to known stages.

Usage::

    from skillmeat.core.workflow import WorkflowDefinition
    from skillmeat.core.workflow.dag import build_dag, DAG, DAGNode

    workflow = WorkflowDefinition.model_validate(data)
    dag = build_dag(workflow)

    roots = dag.get_roots()           # stages with no predecessors
    deps = dag.get_predecessors("b")  # what must run before "b"
    next_ = dag.get_successors("a")   # what runs after "a"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from skillmeat.core.workflow.exceptions import WorkflowValidationError
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


def build_dag(workflow: WorkflowDefinition) -> DAG:
    """Build a ``DAG`` from a parsed ``WorkflowDefinition``.

    Algorithm:

    1. Create one ``DAGNode`` for each stage, keyed by ``stage.id``.
    2. For each stage's ``depends_on`` list, validate that every referenced ID
       is a known stage, then wire predecessor/successor edges bidirectionally.

    Cycle detection is deliberately not performed here; that is the
    responsibility of the DAG-1.8 validator.

    Args:
        workflow: A fully parsed and Pydantic-validated ``WorkflowDefinition``.

    Returns:
        A ``DAG`` instance with all nodes and edges populated.

    Raises:
        WorkflowValidationError: If any ``depends_on`` entry references a stage
            ID that does not exist in the workflow's stage list.

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

    return DAG(nodes=nodes)
