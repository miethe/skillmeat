"""Project-level workflow override loader and deep-merge engine.

Projects can place a ``.skillmeat-workflow-overrides.yaml`` file in their root
directory to customise workflow bindings — agent assignments, context modules,
and parameter defaults — without modifying the shared workflow definition stored
in the database.

Spec reference: docs/project_plans/design-specs/workflow-orchestration-schema-spec.md
Section 3.7 "Project Overrides".

Override file format::

    overrides:
      "sdlc-feature-ship":
        stages:
          research:
            roles:
              primary:
                artifact: "agent:my-custom-researcher"
                model: "sonnet"
          implement:
            roles:
              primary:
                artifact: "agent:my-fullstack-dev"
              tools:
                - "skill:my-custom-linter"
        context:
          global_modules:
            - "ctx:my-project-rules"
        config:
          parameters:
            target_branch:
              default: "develop"

Deep-merge semantics:
    - Dicts are merged recursively.
    - Non-dict (leaf) values are replaced entirely.
    - Lists are replaced entirely (not appended).
    - Keys present in the override but absent in the base are added.
    - Keys present in the base but absent in the override are preserved.

Structural elements that cannot be overridden (raise ``WorkflowOverrideError``):
    - Stage ordering or stage names (``stages[*].id``)
    - Stage dependencies (``stages[*].depends_on``)
    - Stage type (``stages[*].type``)
    - Workflow identity fields (``workflow.id``, ``workflow.name``, ``workflow.version``)

Usage::

    from pathlib import Path
    from skillmeat.core.workflow.overrides import load_project_overrides, apply_overrides

    overrides = load_project_overrides(Path("/path/to/project"), workflow_id="sdlc-feature-ship")
    if overrides:
        merged_dict = apply_overrides(base_dict, overrides)
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# File name searched in the project root
OVERRIDE_FILENAME = ".skillmeat-workflow-overrides.yaml"

# Structural keys that must NOT be overridden (applied at the stage level)
_PROTECTED_STAGE_KEYS = frozenset({"id", "depends_on", "type"})

# Top-level workflow metadata keys that must NOT be overridden
_PROTECTED_WORKFLOW_KEYS = frozenset({"id", "name", "version"})

# Top-level keys that are allowed to be overridden
_ALLOWED_TOP_LEVEL_KEYS = frozenset({"stages", "context", "config", "error_policy"})


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class WorkflowOverrideError(Exception):
    """Raised when an override file is invalid or attempts a protected change.

    Attributes:
        message: Human-readable description of the problem.
        path:    Path to the override file (may be None).
    """

    def __init__(self, message: str, path: Optional[Path] = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path is not None:
            return f"{self.message}  (file: {self.path})"
        return self.message


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into a deep copy of *base*.

    Rules:
    - If both values are ``dict``, merge recursively.
    - Otherwise (list, scalar, None), the override value replaces the base value.
    - Keys in *base* not present in *override* are kept unchanged.
    - Keys in *override* not present in *base* are added.

    Args:
        base:     The original workflow definition dict (or sub-dict).
        override: The override dict to merge on top.

    Returns:
        A new dict containing the merged result.  The inputs are not mutated.
    """
    result: Dict[str, Any] = copy.deepcopy(base)
    for key, override_value in override.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = _deep_merge(base_value, override_value)
        else:
            result[key] = copy.deepcopy(override_value)
    return result


def _validate_override_structure(
    override_block: Dict[str, Any], override_path: Path
) -> None:
    """Validate that an override block does not touch protected fields.

    Args:
        override_block: The per-workflow override dict (value under the workflow
                        ID key inside ``overrides:``).
        override_path:  Path to the override file (for error messages).

    Raises:
        WorkflowOverrideError: If the block attempts to override a protected
            structural field.
    """
    # Check top-level keys are from the allowed set
    unknown_keys = set(override_block.keys()) - _ALLOWED_TOP_LEVEL_KEYS - {"workflow"}
    if unknown_keys:
        raise WorkflowOverrideError(
            f"Override block contains unknown top-level key(s): "
            f"{sorted(unknown_keys)}.  Allowed keys: {sorted(_ALLOWED_TOP_LEVEL_KEYS)}.",
            path=override_path,
        )

    # Reject overrides to workflow identity fields
    if "workflow" in override_block:
        protected_found = set(override_block["workflow"].keys()) & _PROTECTED_WORKFLOW_KEYS
        if protected_found:
            raise WorkflowOverrideError(
                f"Overriding workflow structural fields is not allowed: "
                f"{sorted(protected_found)}.  Use a new workflow definition instead.",
                path=override_path,
            )

    # Reject overrides to stage structural fields
    stages_override = override_block.get("stages")
    if stages_override is not None:
        if not isinstance(stages_override, dict):
            raise WorkflowOverrideError(
                "Override 'stages' must be a mapping of stage_id -> override dict, "
                f"got {type(stages_override).__name__!r}.",
                path=override_path,
            )
        for stage_id, stage_override in stages_override.items():
            if not isinstance(stage_override, dict):
                raise WorkflowOverrideError(
                    f"Stage override for {stage_id!r} must be a mapping, "
                    f"got {type(stage_override).__name__!r}.",
                    path=override_path,
                )
            protected_found = set(stage_override.keys()) & _PROTECTED_STAGE_KEYS
            if protected_found:
                raise WorkflowOverrideError(
                    f"Stage {stage_id!r}: overriding structural field(s) "
                    f"{sorted(protected_found)} is not allowed.  "
                    "Structural changes require a new workflow definition.",
                    path=override_path,
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_project_overrides(
    project_path: Path,
    workflow_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Load and return project-level overrides for the given workflow.

    Looks for ``.skillmeat-workflow-overrides.yaml`` in *project_path*.  If the
    file does not exist, returns ``None`` (no-op).  If ``workflow_id`` is
    supplied, extracts only the block for that specific workflow.  If
    ``workflow_id`` is ``None``, returns the full ``overrides`` mapping.

    Args:
        project_path: Root directory of the project (the directory that should
                      contain ``.skillmeat-workflow-overrides.yaml``).
        workflow_id:  Optional workflow SWDL ``id`` field to filter by.  When
                      ``None`` the full overrides mapping is returned.

    Returns:
        A dict of override values, or ``None`` if:
        - The override file does not exist.
        - The file exists but contains no override for the requested workflow.

    Raises:
        WorkflowOverrideError: If the file exists but cannot be parsed or
            contains an invalid structure.
    """
    override_file = project_path / OVERRIDE_FILENAME

    if not override_file.exists():
        logger.debug(
            "load_project_overrides: no override file found at %s", override_file
        )
        return None

    logger.info("load_project_overrides: loading %s", override_file)

    try:
        raw_text = override_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowOverrideError(
            f"Could not read override file: {exc}", path=override_file
        ) from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        location = ""
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            mark = exc.problem_mark
            location = f" at line {mark.line + 1}, column {mark.column + 1}"
        raise WorkflowOverrideError(
            f"YAML parse error in override file{location}: {exc}",
            path=override_file,
        ) from exc

    if data is None:
        # Empty file — treat as no overrides
        logger.debug("load_project_overrides: override file is empty, skipping")
        return None

    if not isinstance(data, dict):
        raise WorkflowOverrideError(
            f"Override file must be a YAML mapping at the top level, "
            f"got {type(data).__name__!r}.",
            path=override_file,
        )

    if "overrides" not in data:
        raise WorkflowOverrideError(
            "Override file must have a top-level 'overrides' key.",
            path=override_file,
        )

    overrides_map = data["overrides"]
    if not isinstance(overrides_map, dict):
        raise WorkflowOverrideError(
            f"'overrides' must be a mapping of workflow_id -> override block, "
            f"got {type(overrides_map).__name__!r}.",
            path=override_file,
        )

    if workflow_id is None:
        # Return the full map; validate all blocks
        for wf_id, block in overrides_map.items():
            if isinstance(block, dict):
                _validate_override_structure(block, override_file)
        return overrides_map

    block = overrides_map.get(workflow_id)
    if block is None:
        logger.debug(
            "load_project_overrides: no override block for workflow %r", workflow_id
        )
        return None

    if not isinstance(block, dict):
        raise WorkflowOverrideError(
            f"Override block for workflow {workflow_id!r} must be a mapping, "
            f"got {type(block).__name__!r}.",
            path=override_file,
        )

    _validate_override_structure(block, override_file)
    logger.info(
        "load_project_overrides: loaded override block for workflow %r "
        "with keys %s",
        workflow_id,
        sorted(block.keys()),
    )
    return block


def apply_overrides(
    workflow_def: Dict[str, Any],
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply a per-workflow override block onto a workflow definition dict.

    Accepts the raw parsed dict of a workflow definition (i.e. the output of
    ``yaml.safe_load`` on a WORKFLOW.yaml) and merges the override block onto
    it.  The ``stages`` key in the override is treated specially: rather than
    replacing the whole stages list, individual stage entries are found by
    ``id`` and merged individually.

    The base workflow dict is **not mutated**.  A new dict is returned.

    Args:
        workflow_def: Raw workflow definition dict (parsed from YAML / loaded
                      from ``WorkflowDTO.definition``).
        overrides:    Per-workflow override block, as returned by
                      :func:`load_project_overrides`.

    Returns:
        A new dict with overrides applied.

    Raises:
        WorkflowOverrideError: If the override references a stage ID that does
            not exist in the base definition, or references an unknown top-level
            key.
    """
    if not overrides:
        return copy.deepcopy(workflow_def)

    result: Dict[str, Any] = copy.deepcopy(workflow_def)

    for key, override_value in overrides.items():
        if key == "stages":
            # Special handling: stages are a list in the base definition but a
            # dict (stage_id -> override) in the override block.
            result["stages"] = _merge_stages(
                result.get("stages", []),
                override_value,
            )
        elif key in _ALLOWED_TOP_LEVEL_KEYS:
            base_value = result.get(key)
            if isinstance(base_value, dict) and isinstance(override_value, dict):
                result[key] = _deep_merge(base_value, override_value)
            else:
                result[key] = copy.deepcopy(override_value)
        elif key == "workflow":
            # workflow block may be overridden for non-protected sub-keys (e.g. description, tags)
            base_wf = result.get("workflow", {})
            if isinstance(base_wf, dict) and isinstance(override_value, dict):
                result["workflow"] = _deep_merge(base_wf, override_value)
            else:
                result["workflow"] = copy.deepcopy(override_value)
        else:
            logger.warning(
                "apply_overrides: ignoring unknown override key %r", key
            )

    return result


def _merge_stages(
    base_stages: Any,
    stages_override: Dict[str, Any],
) -> Any:
    """Merge a stages override dict onto the base stages list.

    The base definition stores stages as a list of dicts, each with an ``id``
    field.  The override stores them as a mapping of ``stage_id -> override_dict``.
    This function finds each stage by ID and deep-merges the override onto it.

    Args:
        base_stages:    The ``stages`` value from the base workflow definition
                        (expected to be a list of stage dicts).
        stages_override: Mapping of ``stage_id -> override_dict``.

    Returns:
        Updated stages list with overrides applied.

    Raises:
        WorkflowOverrideError: If an override references a stage ID that does
            not appear in the base definition.
    """
    if not isinstance(base_stages, list):
        logger.warning(
            "_merge_stages: base stages is not a list (%s), returning override as-is",
            type(base_stages).__name__,
        )
        return base_stages

    if not isinstance(stages_override, dict):
        # Caller passed a raw list — return it directly (full replacement)
        return copy.deepcopy(stages_override)

    # Index base stages by id for O(1) lookup
    base_index: Dict[str, int] = {}
    for idx, stage in enumerate(base_stages):
        if isinstance(stage, dict) and "id" in stage:
            base_index[stage["id"]] = idx

    # Validate all override stage IDs exist in the base
    unknown_ids = set(stages_override.keys()) - set(base_index.keys())
    if unknown_ids:
        raise WorkflowOverrideError(
            f"Override references stage ID(s) that do not exist in the base "
            f"workflow definition: {sorted(unknown_ids)}.  "
            "Verify the stage IDs in your override file."
        )

    # Apply overrides onto a copy of the base stages list
    result_stages = copy.deepcopy(base_stages)
    for stage_id, stage_override in stages_override.items():
        idx = base_index[stage_id]
        base_stage = result_stages[idx]
        if isinstance(base_stage, dict) and isinstance(stage_override, dict):
            result_stages[idx] = _deep_merge(base_stage, stage_override)
        else:
            result_stages[idx] = copy.deepcopy(stage_override)

    return result_stages
