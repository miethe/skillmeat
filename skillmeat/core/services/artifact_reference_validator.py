"""Service that resolves artifact role references from workflow definitions.

A workflow's stages reference artifact *roles* — strings in ``<type>:<name>``
format (e.g. ``"agent:researcher-v1"``, ``"skill:web-search"``) — which may or
may not correspond to actual rows in the ``artifacts`` table.

``ArtifactReferenceValidator`` attempts to match every role string found in a
workflow definition against the artifacts table, returning a structured
``RoleResolutionResult`` that separates successfully resolved roles from
unresolved ones.  Missing artifacts cause a WARNING log but never raise an
exception, making the validator safe to call during read-only validation passes.

Design notes:
    - Accepts a SQLAlchemy ``Session`` so tests can inject a mock or in-memory
      session without touching the filesystem.
    - Uses SQLAlchemy 1.x ``session.query()`` style, consistent with other
      local-dialect services in this package.
    - Role strings follow the project-wide ``<type>:<name>`` convention
      (``Artifact.id`` primary key format).  The validator resolves them with
      a two-step strategy:
        1. **Primary fast path**: query ``artifacts.id = "<type>:<name>"``
           (case-insensitive name component).
        2. **Fallback**: if no match is found, query by ``artifacts.name`` alone
           (case-insensitive) regardless of type — useful when the type prefix
           does not match the stored type label.
    - Workflow loading parses the stored YAML definition so that the full
      ``WorkflowDefinition`` Pydantic model is available for role extraction.
      This avoids a second round-trip for workflows already partially loaded.

Usage::

    from sqlalchemy.orm import Session
    from skillmeat.core.services.artifact_reference_validator import (
        ArtifactReferenceValidator,
    )

    validator = ArtifactReferenceValidator(session)
    result = validator.resolve_stage_roles("abc123")

    for resolved in result.resolved:
        print(resolved["role_string"], "->", resolved["artifact_id"])

    for role in result.unresolved:
        print("UNRESOLVED:", role)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from skillmeat.cache.models import Artifact
from skillmeat.core.workflow.models import WorkflowDefinition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RoleResolutionResult:
    """Result of resolving artifact role references from a workflow.

    Attributes:
        workflow_id: The DB primary key of the queried workflow.
        resolved: Roles that matched an artifact in the ``artifacts`` table.
            Each entry is a dict with keys:
            - ``role_string`` (str): The original ``<type>:<name>`` role string.
            - ``artifact_id`` (str): The matched ``Artifact.id``.
            - ``name`` (str): The matched artifact's display name.
            - ``artifact_type`` (str): The matched artifact's type label.
        unresolved: Role strings that did not match any artifact.
    """

    workflow_id: str
    resolved: List[Dict[str, Any]] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ArtifactReferenceValidator:
    """Resolves artifact role references from workflow stage definitions.

    Accepts a SQLAlchemy ``Session`` for dependency injection — the caller
    manages session lifecycle (open, commit/rollback, close).

    Attributes:
        _session: Active SQLAlchemy session used for all DB queries.
    """

    def __init__(self, session: Session) -> None:
        """Initialise the validator with an active SQLAlchemy session.

        Args:
            session: SQLAlchemy session.  The validator never commits or
                closes this session — lifecycle is owned by the caller.
        """
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_stage_roles(self, workflow_id: str) -> RoleResolutionResult:
        """Resolve all artifact role references found in a workflow's stages.

        Loads the workflow definition from the ``workflows`` table, extracts
        every role string from every stage, and attempts to match each one
        against the ``artifacts`` table.

        Resolution strategy per role string (``<type>:<name>`` format):
            1. Primary path: case-insensitive lookup by ``Artifact.id``
               (i.e. the composite ``<type>:<name>`` primary key).
            2. Fallback: if the primary path misses, try case-insensitive
               lookup by ``Artifact.name`` alone — catches cases where the
               type prefix in the role string differs from the stored type label.

        Args:
            workflow_id: DB primary key of the workflow to resolve.

        Returns:
            ``RoleResolutionResult`` with ``resolved`` and ``unresolved``
            lists populated.  Returns an empty result (both lists empty) when
            the workflow is not found or has no stages.

        Raises:
            Nothing — all errors are logged and an empty result is returned.
        """
        result = RoleResolutionResult(workflow_id=workflow_id)

        # -- Load workflow YAML from DB --
        definition = self._load_workflow_definition(workflow_id)
        if definition is None:
            return result

        # -- Extract all unique role strings from stages --
        role_strings = self._extract_role_strings(definition)
        if not role_strings:
            logger.info(
                "ArtifactReferenceValidator: workflow '%s' has no role references",
                workflow_id,
            )
            return result

        logger.info(
            "ArtifactReferenceValidator: resolving %d role string(s) for workflow '%s'",
            len(role_strings),
            workflow_id,
        )

        # -- Resolve each role string against the artifacts table --
        for role_string in role_strings:
            match = self._resolve_role(role_string)
            if match is not None:
                result.resolved.append(match)
                logger.info(
                    "ArtifactReferenceValidator: resolved '%s' -> artifact_id='%s'",
                    role_string,
                    match["artifact_id"],
                )
            else:
                result.unresolved.append(role_string)
                logger.warning(
                    "ArtifactReferenceValidator: role '%s' in workflow '%s' "
                    "did not match any artifact",
                    role_string,
                    workflow_id,
                )

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_workflow_definition(
        self, workflow_id: str
    ) -> Optional[WorkflowDefinition]:
        """Fetch and parse the workflow YAML definition from the DB.

        Args:
            workflow_id: DB primary key of the workflow row.

        Returns:
            Parsed ``WorkflowDefinition`` on success, or ``None`` when the
            workflow is not found or the YAML cannot be parsed.
        """
        # Lazy import avoids circular dependency: cache.models -> this module.
        from skillmeat.cache.models import Workflow  # noqa: PLC0415

        try:
            workflow_row = (
                self._session.query(Workflow)
                .filter_by(id=workflow_id)
                .first()
            )
        except OperationalError as exc:
            logger.warning(
                "ArtifactReferenceValidator: DB error fetching workflow '%s': %s",
                workflow_id,
                exc,
            )
            return None

        if workflow_row is None:
            logger.warning(
                "ArtifactReferenceValidator: workflow '%s' not found",
                workflow_id,
            )
            return None

        if not workflow_row.definition_yaml:
            logger.warning(
                "ArtifactReferenceValidator: workflow '%s' has no definition YAML",
                workflow_id,
            )
            return None

        try:
            import yaml  # noqa: PLC0415 — already a project dependency

            raw = yaml.safe_load(workflow_row.definition_yaml)
            return WorkflowDefinition.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — intentional broad catch for non-blocking path
            logger.warning(
                "ArtifactReferenceValidator: could not parse YAML for workflow '%s': %s",
                workflow_id,
                exc,
            )
            return None

    def _extract_role_strings(self, definition: WorkflowDefinition) -> List[str]:
        """Extract all unique artifact role strings from a workflow definition.

        Collects:
        - ``stage.roles.primary.artifact`` — the primary agent role string.
        - ``stage.roles.tools`` — supporting tool artifact references.

        Args:
            definition: Parsed and validated ``WorkflowDefinition``.

        Returns:
            Deduplicated list of role strings in encounter order.
        """
        seen: set[str] = set()
        ordered: List[str] = []

        for stage in definition.stages:
            if stage.roles is None:
                continue

            primary_ref = stage.roles.primary.artifact
            if primary_ref and primary_ref not in seen:
                seen.add(primary_ref)
                ordered.append(primary_ref)

            for tool_ref in stage.roles.tools:
                if tool_ref and tool_ref not in seen:
                    seen.add(tool_ref)
                    ordered.append(tool_ref)

        return ordered

    def _resolve_role(self, role_string: str) -> Optional[Dict[str, Any]]:
        """Attempt to match a single role string against the artifacts table.

        Applies two resolution passes:
            1. Case-insensitive match on ``Artifact.id`` (``<type>:<name>``).
            2. Fallback case-insensitive match on ``Artifact.name`` alone.

        Args:
            role_string: Artifact role reference (e.g. ``"agent:researcher-v1"``).

        Returns:
            Dict with ``role_string``, ``artifact_id``, ``name``, and
            ``artifact_type`` on a successful match, or ``None``.
        """
        try:
            return self._resolve_by_id(role_string) or self._resolve_by_name(
                role_string
            )
        except OperationalError as exc:
            logger.warning(
                "ArtifactReferenceValidator: DB error resolving role '%s': %s",
                role_string,
                exc,
            )
            return None

    def _resolve_by_id(self, role_string: str) -> Optional[Dict[str, Any]]:
        """Match role string against ``Artifact.id`` (case-insensitive).

        ``Artifact.id`` stores the ``<type>:<name>`` composite primary key.
        A direct match here is the fast path for well-formed role strings.

        Args:
            role_string: Full ``<type>:<name>`` role reference.

        Returns:
            Resolution dict or ``None``.
        """
        artifact: Optional[Artifact] = (
            self._session.query(Artifact)
            .filter(Artifact.id.ilike(role_string))
            .first()
        )
        if artifact is not None:
            return self._build_match(role_string, artifact)
        return None

    def _resolve_by_name(self, role_string: str) -> Optional[Dict[str, Any]]:
        """Match the name component of a role string against ``Artifact.name``.

        Strips the ``<type>:`` prefix (if present) and performs a
        case-insensitive equality match on ``Artifact.name``.  This handles
        cases where the type prefix in the role string does not align with the
        stored ``type`` column value.

        Args:
            role_string: Role reference, optionally prefixed with ``<type>:``.

        Returns:
            Resolution dict for the first matching artifact, or ``None``.
        """
        if ":" in role_string:
            _, name_part = role_string.split(":", 1)
        else:
            name_part = role_string

        if not name_part:
            return None

        artifact: Optional[Artifact] = (
            self._session.query(Artifact)
            .filter(Artifact.name.ilike(name_part))
            .first()
        )
        if artifact is not None:
            return self._build_match(role_string, artifact)
        return None

    @staticmethod
    def _build_match(role_string: str, artifact: Artifact) -> Dict[str, Any]:
        """Build the resolution dict from a matched ``Artifact`` row.

        Args:
            role_string: The original role string from the workflow definition.
            artifact:    Matched ``Artifact`` ORM instance.

        Returns:
            Dict with ``role_string``, ``artifact_id``, ``name``, and
            ``artifact_type``.
        """
        return {
            "role_string": role_string,
            "artifact_id": artifact.id,
            "name": artifact.name,
            "artifact_type": artifact.type,
        }
