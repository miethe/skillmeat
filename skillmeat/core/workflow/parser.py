"""SWDL workflow definition parser.

Reads a workflow definition file from disk, parses it (YAML or JSON), validates
the result against the ``WorkflowDefinition`` Pydantic model, and returns a
fully-typed ``WorkflowDefinition`` instance.

Supported file extensions:
    ``.yaml``, ``.yml`` -- parsed with PyYAML (``yaml.safe_load``)
    ``.json``            -- parsed with the standard ``json`` module

Errors are surfaced as ``WorkflowParseError`` with a human-readable message,
the offending file path, and (for Pydantic failures) a list of field-level
error strings.

Typical usage::

    from pathlib import Path
    from skillmeat.core.workflow.parser import parse_workflow
    from skillmeat.core.workflow.exceptions import WorkflowParseError

    try:
        workflow = parse_workflow(Path("WORKFLOW.yaml"))
    except WorkflowParseError as exc:
        print(exc)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import ValidationError

from skillmeat.core.workflow.exceptions import WorkflowParseError
from skillmeat.core.workflow.models import WorkflowDefinition

# Supported file extension → loader mapping.
_SUPPORTED_EXTENSIONS = frozenset({".yaml", ".yml", ".json"})


def _load_yaml(path: Path) -> Any:
    """Read and parse a YAML file using PyYAML safe_load.

    Args:
        path: Absolute or relative path to the ``.yaml`` / ``.yml`` file.

    Returns:
        The deserialized Python object (typically a ``dict``).

    Raises:
        WorkflowParseError: On any YAML syntax / scanner error.
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        # Provide the mark (line/column) when available for better diagnostics.
        location = ""
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            mark = exc.problem_mark
            location = f" at line {mark.line + 1}, column {mark.column + 1}"
        raise WorkflowParseError(
            f"YAML parse error{location}: {exc}",
            path=path,
        ) from exc


def _load_json(path: Path) -> Any:
    """Read and parse a JSON file using the standard ``json`` module.

    Args:
        path: Absolute or relative path to the ``.json`` file.

    Returns:
        The deserialized Python object (typically a ``dict``).

    Raises:
        WorkflowParseError: On any JSON decode error.
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise WorkflowParseError(
            f"JSON parse error at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            path=path,
        ) from exc


def _validate(raw: Any, path: Path) -> WorkflowDefinition:
    """Validate a raw parsed dict against the ``WorkflowDefinition`` schema.

    Args:
        raw:  The deserialized data (expected to be a ``dict``).
        path: Source file path (used for error context only).

    Returns:
        A validated ``WorkflowDefinition`` instance.

    Raises:
        WorkflowParseError: When the raw data is not a mapping or fails
                            Pydantic model validation.
    """
    if not isinstance(raw, dict):
        raise WorkflowParseError(
            f"Expected a YAML/JSON mapping at the top level, "
            f"got {type(raw).__name__!r}.",
            path=path,
        )

    try:
        return WorkflowDefinition.model_validate(raw)
    except ValidationError as exc:
        # Flatten Pydantic v2 error list into readable strings.
        details = [
            f"{' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        raise WorkflowParseError(
            f"Workflow definition schema validation failed "
            f"({exc.error_count()} error(s)).",
            path=path,
            details=details,
        ) from exc


def parse_workflow(path: Path) -> WorkflowDefinition:
    """Parse and validate a SWDL workflow definition file.

    Reads the file at ``path``, selects the appropriate deserializer based on
    the file extension, validates the result against the ``WorkflowDefinition``
    Pydantic schema, and returns a fully-typed model instance.

    Args:
        path: Path to the workflow definition file.  Must have a ``.yaml``,
              ``.yml``, or ``.json`` extension.

    Returns:
        A validated :class:`~skillmeat.core.workflow.models.WorkflowDefinition`
        instance.

    Raises:
        WorkflowParseError: For any of the following conditions:

            - The file does not exist (wraps ``FileNotFoundError``).
            - The file extension is not supported (not ``.yaml``, ``.yml``,
              or ``.json``).
            - The YAML/JSON content cannot be parsed (syntax error).
            - The parsed data does not conform to the ``WorkflowDefinition``
              schema (Pydantic ``ValidationError`` wrapped with field details).

    Example::

        from pathlib import Path
        from skillmeat.core.workflow.parser import parse_workflow

        workflow = parse_workflow(Path("my-workflow.yaml"))
        print(workflow.workflow.name)
    """
    # --- 1. File existence check -----------------------------------------
    if not path.exists():
        raise WorkflowParseError(
            f"Workflow definition file not found: {path}",
            path=path,
        )

    # --- 2. Extension guard -----------------------------------------------
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        raise WorkflowParseError(
            f"Unsupported workflow file extension {suffix!r}. "
            f"Supported extensions: {supported}.",
            path=path,
        )

    # --- 3. Deserialize ---------------------------------------------------
    if suffix in {".yaml", ".yml"}:
        raw = _load_yaml(path)
    else:
        # suffix == ".json"
        raw = _load_json(path)

    # --- 4. Validate against Pydantic schema ------------------------------
    return _validate(raw, path)
