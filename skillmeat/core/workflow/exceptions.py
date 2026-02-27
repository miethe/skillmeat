"""Workflow-specific exceptions for the SkillMeat Workflow Orchestration Engine.

All exceptions in this module inherit from ``WorkflowError`` so callers can
catch any workflow failure with a single ``except WorkflowError`` clause while
still discriminating on sub-types when needed.

Hierarchy::

    WorkflowError
    ├── WorkflowParseError              -- file load / YAML / JSON parse failures
    ├── WorkflowValidationError         -- Pydantic schema / contract validation failures
    ├── WorkflowCycleError              -- cycle detected in the stage dependency DAG
    ├── WorkflowArtifactError           -- missing or unresolvable artifact reference
    ├── WorkflowNotFoundError           -- workflow record not found in the database
    └── WorkflowExecutionNotFoundError  -- execution record not found in the database
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional


class WorkflowError(Exception):
    """Base exception for all SkillMeat workflow errors.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class WorkflowParseError(WorkflowError):
    """Raised when a workflow definition file cannot be loaded or parsed.

    Covers:
    - File not found
    - Unsupported file extension
    - YAML syntax errors
    - JSON decode errors
    - Pydantic model validation failures (wrapped from ``WorkflowValidationError``)

    Attributes:
        message: Human-readable description of the parse failure.
        path:    Path to the file that triggered the error (may be None when
                 the error is not associated with a specific file).
        details: Optional list of granular validation error strings (populated
                 when the root cause is a Pydantic ``ValidationError``).
    """

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        details: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.details: List[str] = details or []

    def __str__(self) -> str:
        parts = [self.message]
        if self.path is not None:
            parts.append(f"  File: {self.path}")
        if self.details:
            parts.append("  Validation errors:")
            for detail in self.details:
                parts.append(f"    - {detail}")
        return "\n".join(parts)


class WorkflowValidationError(WorkflowError):
    """Raised when a parsed workflow fails schema or contract validation.

    This is distinct from ``WorkflowParseError`` in that the file was
    successfully read and parsed (syntactically valid) but the resulting
    structure does not conform to the SWDL schema or semantic constraints.

    Attributes:
        message: Human-readable description of the validation failure.
        details: Optional list of granular validation error strings.
        field:   Optional dotted field path that triggered the error
                 (e.g. ``"stages[0].roles.primary.artifact"``).
    """

    def __init__(
        self,
        message: str,
        details: Optional[List[str]] = None,
        field: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.details: List[str] = details or []
        self.field = field

    def __str__(self) -> str:
        parts = [self.message]
        if self.field is not None:
            parts.append(f"  Field: {self.field}")
        if self.details:
            parts.append("  Details:")
            for detail in self.details:
                parts.append(f"    - {detail}")
        return "\n".join(parts)


class WorkflowCycleError(WorkflowError):
    """Raised when a cycle is detected in the stage dependency DAG.

    Stage dependencies must form a directed acyclic graph (DAG).  If a cycle
    is found during topological sort, this exception is raised with the
    offending cycle path for diagnostic purposes.

    Attributes:
        message: Human-readable description mentioning the cycle.
        cycle:   Ordered list of stage IDs that form the cycle.
                 E.g. ``["stage-a", "stage-b", "stage-a"]``.
    """

    def __init__(self, message: str, cycle: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.cycle: List[str] = cycle or []

    def __str__(self) -> str:
        parts = [self.message]
        if self.cycle:
            parts.append("  Cycle path: " + " -> ".join(self.cycle))
        return "\n".join(parts)


class WorkflowArtifactError(WorkflowError):
    """Raised when a workflow references an artifact that cannot be resolved.

    Covers missing artifact references in ``roles.primary.artifact``,
    ``roles.tools``, or context module bindings.

    Attributes:
        message:       Human-readable description of the resolution failure.
        artifact_ref:  The unresolvable artifact reference string
                       (e.g. ``"agent:researcher-v1"``).
        stage_id:      Optional stage ID where the reference appears.
    """

    def __init__(
        self,
        message: str,
        artifact_ref: Optional[str] = None,
        stage_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.artifact_ref = artifact_ref
        self.stage_id = stage_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.artifact_ref is not None:
            parts.append(f"  Artifact reference: {self.artifact_ref!r}")
        if self.stage_id is not None:
            parts.append(f"  Stage: {self.stage_id!r}")
        return "\n".join(parts)


class WorkflowNotFoundError(WorkflowError):
    """Raised when a requested workflow does not exist in the database.

    Attributes:
        message:     Human-readable description.
        workflow_id: The identifier that was looked up.
    """

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.workflow_id = workflow_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.workflow_id is not None:
            parts.append(f"  Workflow ID: {self.workflow_id!r}")
        return "\n".join(parts)


class WorkflowExecutionNotFoundError(WorkflowError):
    """Raised when a requested workflow execution does not exist in the database.

    Attributes:
        message:      Human-readable description.
        execution_id: The execution identifier that was looked up.
    """

    def __init__(
        self,
        message: str,
        execution_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.execution_id = execution_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.execution_id is not None:
            parts.append(f"  Execution ID: {self.execution_id!r}")
        return "\n".join(parts)
