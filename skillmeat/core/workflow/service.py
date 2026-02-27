"""WorkflowService: CRUD operations for SkillMeat workflow definitions.

Provides business-logic over ``WorkflowRepository`` and ``WorkflowStageRepository``.
All public methods return ``WorkflowDTO`` dataclasses — never raw ORM models.

Typical usage::

    from skillmeat.core.workflow.service import WorkflowService

    svc = WorkflowService()

    # Create from YAML string
    dto = svc.create(yaml_content=yaml_text, project_id="my-project")

    # Retrieve
    dto = svc.get(dto.id)

    # List with optional project filter
    workflows = svc.list(project_id="my-project", skip=0, limit=20)

    # Update definition
    dto = svc.update(dto.id, yaml_content=new_yaml_text)

    # Duplicate
    copy = svc.duplicate(dto.id, new_name="My Workflow (copy)")

    # Delete
    svc.delete(dto.id)
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import ValidationError

from skillmeat.core.workflow.dag import build_dag
from skillmeat.core.workflow.exceptions import (
    WorkflowCycleError,
    WorkflowNotFoundError,
    WorkflowParseError,
    WorkflowValidationError,
)
from skillmeat.core.workflow.models import WorkflowDefinition
from skillmeat.core.workflow.planner import ExecutionPlan, generate_plan
from skillmeat.core.workflow.validator import ValidationResult, validate_expressions

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Object
# =============================================================================


@dataclass
class StageDTO:
    """Lightweight representation of a single workflow stage.

    Attributes:
        id:           DB primary key (uuid hex).
        stage_id_ref: Stage identifier from the SWDL definition (kebab-case).
        name:         Human-readable stage name.
        description:  Optional stage description.
        order_index:  Positional index within the workflow (0-based).
        stage_type:   Stage execution type: "agent" | "gate" | "fan_out".
        condition:    Optional SWDL guard expression.
        depends_on:   List of stage_id_ref values this stage depends on.
        roles:        Roles dict (primary agent, tools) or None.
        inputs:       Input contracts dict or None.
        outputs:      Output contracts dict or None.
        created_at:   Record creation timestamp.
        updated_at:   Record last-update timestamp.
    """

    id: str
    stage_id_ref: str
    name: str
    description: Optional[str]
    order_index: int
    stage_type: str
    condition: Optional[str]
    depends_on: List[str]
    roles: Optional[Dict[str, Any]]
    inputs: Optional[Dict[str, Any]]
    outputs: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


@dataclass
class WorkflowDTO:
    """Lightweight representation of a persisted workflow definition.

    Attributes:
        id:          DB primary key (uuid hex).
        name:        Workflow display name.
        description: Optional workflow description.
        version:     SemVer string (e.g. "1.0.0").
        status:      Lifecycle status: "draft" | "active" | "archived".
        definition:  Raw YAML definition string.
        tags:        Searchable tag list.
        stages:      Decomposed stage DTOs (ordered by order_index).
        project_id:  Optional owning project identifier.
        created_at:  Record creation timestamp.
        updated_at:  Record last-update timestamp.
    """

    id: str
    name: str
    description: Optional[str]
    version: str
    status: str
    definition: str
    tags: List[str]
    stages: List[StageDTO]
    project_id: Optional[str]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Internal helpers
# =============================================================================


def _parse_yaml_string(yaml_content: str) -> WorkflowDefinition:
    """Parse and validate a YAML string into a ``WorkflowDefinition``.

    Args:
        yaml_content: Raw YAML text.

    Returns:
        Validated ``WorkflowDefinition`` instance.

    Raises:
        WorkflowParseError: On YAML syntax errors or type errors.
        WorkflowValidationError: On Pydantic schema validation failures.
    """
    try:
        raw = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        location = ""
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            mark = exc.problem_mark
            location = f" at line {mark.line + 1}, column {mark.column + 1}"
        raise WorkflowParseError(
            f"YAML parse error{location}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise WorkflowParseError(
            f"Expected a YAML mapping at the top level, got {type(raw).__name__!r}."
        )

    try:
        return WorkflowDefinition.model_validate(raw)
    except ValidationError as exc:
        details = [
            f"{' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        raise WorkflowValidationError(
            f"Workflow definition schema validation failed ({exc.error_count()} error(s)).",
            details=details,
        ) from exc


def _sha256(text: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_workflow_orm(
    definition: WorkflowDefinition,
    yaml_content: str,
    project_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> "Workflow":
    """Construct an unsaved ``Workflow`` ORM instance from a parsed definition.

    Args:
        definition:   Validated ``WorkflowDefinition``.
        yaml_content: Raw YAML text (stored verbatim for round-trip fidelity).
        project_id:   Optional project scoping identifier.
        workflow_id:  Optional explicit ID; auto-generated when ``None``.

    Returns:
        Unsaved ``Workflow`` ORM instance.
    """
    from skillmeat.cache.models import Workflow  # noqa: PLC0415 — lazy import avoids circular

    meta = definition.workflow
    now = datetime.utcnow()

    tags_json = json.dumps(meta.tags) if meta.tags else None
    config_json = definition.config.model_dump_json() if definition.config else None
    error_policy_json = (
        definition.error_policy.model_dump_json() if definition.error_policy else None
    )
    hooks_json = definition.hooks.model_dump_json() if definition.hooks else None
    ui_metadata_json = meta.ui.model_dump_json() if meta.ui else None

    # Store global context module IDs
    global_context_module_ids_json = None
    if definition.context and definition.context.global_modules:
        global_context_module_ids_json = json.dumps(definition.context.global_modules)

    return Workflow(
        id=workflow_id or uuid.uuid4().hex,
        name=meta.name,
        description=meta.description,
        version=meta.version,
        status="draft",
        definition_yaml=yaml_content,
        definition_hash=_sha256(yaml_content),
        tags_json=tags_json,
        config_json=config_json,
        error_policy_json=error_policy_json,
        hooks_json=hooks_json,
        ui_metadata_json=ui_metadata_json,
        global_context_module_ids_json=global_context_module_ids_json,
        created_at=now,
        updated_at=now,
    )


def _build_stage_orms(
    definition: WorkflowDefinition, workflow_id: str
) -> "List[WorkflowStage]":
    """Decompose all stages from a definition into ``WorkflowStage`` ORM instances.

    Args:
        definition:  Validated ``WorkflowDefinition``.
        workflow_id: Parent workflow DB primary key.

    Returns:
        Ordered list of unsaved ``WorkflowStage`` instances.
    """
    from skillmeat.cache.models import WorkflowStage  # noqa: PLC0415 — lazy import avoids circular

    stages: List[WorkflowStage] = []
    now = datetime.utcnow()

    for idx, stage in enumerate(definition.stages):
        depends_on_json = json.dumps(stage.depends_on) if stage.depends_on else None
        roles_json = stage.roles.model_dump_json() if stage.roles else None
        inputs_json = (
            json.dumps({k: v.model_dump() for k, v in stage.inputs.items()})
            if stage.inputs
            else None
        )
        outputs_json = (
            json.dumps({k: v.model_dump() for k, v in stage.outputs.items()})
            if stage.outputs
            else None
        )
        context_json = stage.context.model_dump_json() if stage.context else None
        error_policy_json = (
            stage.error_policy.model_dump_json() if stage.error_policy else None
        )
        handoff_json = stage.handoff.model_dump_json() if stage.handoff else None
        gate_json = stage.gate.model_dump_json() if stage.gate else None
        ui_metadata_json = stage.ui.model_dump_json() if stage.ui else None

        stages.append(
            WorkflowStage(
                id=uuid.uuid4().hex,
                workflow_id=workflow_id,
                stage_id_ref=stage.id,
                name=stage.name,
                description=stage.description,
                order_index=idx,
                condition=stage.condition,
                stage_type=stage.type,
                depends_on_json=depends_on_json,
                roles_json=roles_json,
                inputs_json=inputs_json,
                outputs_json=outputs_json,
                context_json=context_json,
                error_policy_json=error_policy_json,
                handoff_json=handoff_json,
                gate_json=gate_json,
                ui_metadata_json=ui_metadata_json,
                created_at=now,
                updated_at=now,
            )
        )
    return stages


def _stage_orm_to_dto(stage: "WorkflowStage") -> StageDTO:
    """Convert a ``WorkflowStage`` ORM instance to a ``StageDTO``.

    Args:
        stage: Populated ``WorkflowStage`` ORM instance.

    Returns:
        Equivalent ``StageDTO``.
    """
    depends_on: List[str] = []
    if stage.depends_on_json:
        try:
            depends_on = json.loads(stage.depends_on_json)
        except (json.JSONDecodeError, TypeError):
            depends_on = []

    roles: Optional[Dict[str, Any]] = None
    if stage.roles_json:
        try:
            roles = json.loads(stage.roles_json)
        except (json.JSONDecodeError, TypeError):
            roles = None

    inputs: Optional[Dict[str, Any]] = None
    if stage.inputs_json:
        try:
            inputs = json.loads(stage.inputs_json)
        except (json.JSONDecodeError, TypeError):
            inputs = None

    outputs: Optional[Dict[str, Any]] = None
    if stage.outputs_json:
        try:
            outputs = json.loads(stage.outputs_json)
        except (json.JSONDecodeError, TypeError):
            outputs = None

    return StageDTO(
        id=stage.id,
        stage_id_ref=stage.stage_id_ref,
        name=stage.name,
        description=stage.description,
        order_index=stage.order_index,
        stage_type=stage.stage_type,
        condition=stage.condition,
        depends_on=depends_on,
        roles=roles,
        inputs=inputs,
        outputs=outputs,
        created_at=stage.created_at,
        updated_at=stage.updated_at,
    )


def _workflow_orm_to_dto(workflow: "Workflow") -> WorkflowDTO:
    """Convert a ``Workflow`` ORM instance (with loaded stages) to a ``WorkflowDTO``.

    Args:
        workflow: ``Workflow`` ORM instance.  The ``stages`` relationship must be
                  loaded (eagerly or via ``selectin``).

    Returns:
        Equivalent ``WorkflowDTO``.
    """
    tags: List[str] = []
    if workflow.tags_json:
        try:
            tags = json.loads(workflow.tags_json)
        except (json.JSONDecodeError, TypeError):
            tags = []

    # project_id is not a first-class column on Workflow; it may be injected
    # via config_json or a future column.  Return None for now.
    project_id: Optional[str] = None
    if workflow.config_json:
        try:
            config = json.loads(workflow.config_json)
            project_id = config.get("project_id")
        except (json.JSONDecodeError, TypeError, AttributeError):
            project_id = None

    stage_dtos: List[StageDTO] = sorted(
        [_stage_orm_to_dto(s) for s in (workflow.stages or [])],
        key=lambda s: s.order_index,
    )

    return WorkflowDTO(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        version=workflow.version,
        status=workflow.status,
        definition=workflow.definition_yaml,
        tags=tags,
        stages=stage_dtos,
        project_id=project_id,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


# =============================================================================
# WorkflowService
# =============================================================================


class WorkflowService:
    """Business-logic service for SkillMeat workflow CRUD operations.

    All public methods return ``WorkflowDTO`` instances — ORM models are never
    exposed to callers.  The service handles parse → validate → persist and
    raises domain exceptions (``WorkflowNotFoundError``, ``WorkflowParseError``,
    ``WorkflowValidationError``) rather than repository-layer errors.

    Attributes:
        repo: Underlying ``WorkflowRepository`` instance.

    Example::

        svc = WorkflowService()

        # Create from YAML string
        dto = svc.create(yaml_content="workflow:\\n  id: my-wf\\n  name: My Wf")

        # Create from file
        dto = svc.create(file_path="/path/to/WORKFLOW.yaml", project_id="proj-1")

        # Retrieve
        dto = svc.get(dto.id)

        # Update
        dto = svc.update(dto.id, new_yaml)

        # Delete
        svc.delete(dto.id)
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialise the service.

        Args:
            db_path: Optional path to the SQLite database file.  Uses the
                default ``~/.skillmeat/cache/cache.db`` when ``None``.
        """
        from skillmeat.cache.workflow_repository import WorkflowRepository  # noqa: PLC0415 — lazy import avoids circular

        self.repo = WorkflowRepository(db_path=db_path)
        logger.info("WorkflowService initialised")

    # =========================================================================
    # CRUD
    # =========================================================================

    def create(
        self,
        yaml_content: Optional[str] = None,
        file_path: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> WorkflowDTO:
        """Parse, validate, and persist a new workflow definition.

        At least one of ``yaml_content`` or ``file_path`` must be provided.
        If both are supplied, ``yaml_content`` takes precedence.

        Args:
            yaml_content: Raw YAML string of the workflow definition.
            file_path:    Path to a ``.yaml``, ``.yml``, or ``.json`` file.
            project_id:   Optional project identifier to scope the workflow.

        Returns:
            ``WorkflowDTO`` for the newly created record.

        Raises:
            ValueError: If neither ``yaml_content`` nor ``file_path`` is given.
            WorkflowParseError: On YAML/JSON syntax errors or file-not-found.
            WorkflowValidationError: On schema validation failures.
        """
        if yaml_content is None and file_path is None:
            raise ValueError(
                "At least one of 'yaml_content' or 'file_path' must be provided."
            )

        # Resolve YAML text
        if yaml_content is None:
            path = Path(file_path)  # type: ignore[arg-type]
            if not path.exists():
                raise WorkflowParseError(
                    f"Workflow definition file not found: {path}", path=path
                )
            try:
                yaml_content = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise WorkflowParseError(
                    f"Could not read workflow file: {exc}", path=path
                ) from exc

        definition = _parse_yaml_string(yaml_content)

        workflow_orm = _build_workflow_orm(definition, yaml_content, project_id)
        stage_orms = _build_stage_orms(definition, workflow_orm.id)

        # Attach stages so repository cascade persists them
        workflow_orm.stages = stage_orms

        created = self.repo.create(workflow_orm)
        logger.info(
            "WorkflowService.create: id=%s name=%r project_id=%r stages=%d",
            created.id,
            created.name,
            project_id,
            len(stage_orms),
        )
        return _workflow_orm_to_dto(created)

    def get(self, workflow_id: str) -> WorkflowDTO:
        """Retrieve a workflow by ID.

        Args:
            workflow_id: Primary key of the workflow.

        Returns:
            ``WorkflowDTO`` for the matching record.

        Raises:
            WorkflowNotFoundError: If no workflow with the given ID exists.
        """
        workflow = self.repo.get_with_stages(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(
                f"Workflow not found: {workflow_id!r}", workflow_id=workflow_id
            )
        return _workflow_orm_to_dto(workflow)

    def list(
        self,
        project_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WorkflowDTO]:
        """Return a paginated list of workflow DTOs.

        The underlying repository uses cursor-based pagination; this method
        adapts that to the simpler ``skip`` / ``limit`` offset interface by
        iterating pages when ``skip > 0``.  For most practical skip values this
        is efficient enough; callers that need pure cursor pagination should use
        the repository directly.

        Args:
            project_id: Optional project filter.  When supplied, only workflows
                        whose ``config_json`` contains a matching ``project_id``
                        field are returned.  Note: this is a client-side filter
                        applied after the repository page is fetched.
            skip:       Number of records to skip (0-based offset).
            limit:      Maximum number of records to return.

        Returns:
            List of ``WorkflowDTO`` instances, ordered by ``created_at DESC``.
        """
        # Fetch enough records to satisfy skip + limit in one repository call.
        fetch_limit = skip + limit
        results, _ = self.repo.list(limit=fetch_limit)

        dtos = [_workflow_orm_to_dto(wf) for wf in results]

        # Client-side project_id filter (project_id is stored inside config_json)
        if project_id is not None:
            dtos = [d for d in dtos if d.project_id == project_id]

        # Apply skip after filtering
        return dtos[skip : skip + limit]  # noqa: E203

    def update(self, workflow_id: str, yaml_content: str) -> WorkflowDTO:
        """Re-parse YAML, re-validate, and update an existing workflow.

        Replaces the definition and all associated stages atomically.

        Args:
            workflow_id:  Primary key of the workflow to update.
            yaml_content: New raw YAML definition string.

        Returns:
            Updated ``WorkflowDTO``.

        Raises:
            WorkflowNotFoundError: If no workflow with the given ID exists.
            WorkflowParseError: On YAML syntax errors.
            WorkflowValidationError: On schema validation failures.
        """
        existing = self.repo.get_with_stages(workflow_id)
        if existing is None:
            raise WorkflowNotFoundError(
                f"Workflow not found: {workflow_id!r}", workflow_id=workflow_id
            )

        definition = _parse_yaml_string(yaml_content)
        meta = definition.workflow

        # Preserve mutable DB state (status, id, created_at)
        existing.name = meta.name
        existing.description = meta.description
        existing.version = meta.version
        existing.definition_yaml = yaml_content
        existing.definition_hash = _sha256(yaml_content)
        existing.tags_json = json.dumps(meta.tags) if meta.tags else None
        existing.config_json = (
            definition.config.model_dump_json() if definition.config else None
        )
        existing.error_policy_json = (
            definition.error_policy.model_dump_json()
            if definition.error_policy
            else None
        )
        existing.hooks_json = (
            definition.hooks.model_dump_json() if definition.hooks else None
        )
        existing.ui_metadata_json = (
            meta.ui.model_dump_json() if meta.ui else None
        )
        existing.global_context_module_ids_json = (
            json.dumps(definition.context.global_modules)
            if definition.context and definition.context.global_modules
            else None
        )

        # Replace stages: clear existing, set new ones
        new_stages = _build_stage_orms(definition, workflow_id)
        existing.stages = new_stages

        updated = self.repo.update(existing)
        logger.info(
            "WorkflowService.update: id=%s name=%r stages=%d",
            updated.id,
            updated.name,
            len(new_stages),
        )
        return _workflow_orm_to_dto(updated)

    def delete(self, workflow_id: str) -> None:
        """Delete a workflow and all its stages.

        Stages are removed automatically via the ``cascade="all, delete-orphan"``
        relationship on the ORM model.

        Args:
            workflow_id: Primary key of the workflow to delete.

        Raises:
            WorkflowNotFoundError: If no workflow with the given ID exists.
        """
        deleted = self.repo.delete(workflow_id)
        if not deleted:
            raise WorkflowNotFoundError(
                f"Workflow not found: {workflow_id!r}", workflow_id=workflow_id
            )
        logger.info("WorkflowService.delete: id=%s", workflow_id)

    def duplicate(
        self,
        workflow_id: str,
        new_name: Optional[str] = None,
    ) -> WorkflowDTO:
        """Create a copy of an existing workflow with a new ID.

        The copy is created as a ``draft``.  If ``new_name`` is not supplied,
        the original name is suffixed with ``" (copy)"``.

        Args:
            workflow_id: Primary key of the source workflow.
            new_name:    Optional name for the duplicate.  Defaults to
                         ``"<original name> (copy)"``.

        Returns:
            ``WorkflowDTO`` for the newly created duplicate.

        Raises:
            WorkflowNotFoundError: If no workflow with ``workflow_id`` exists.
        """
        source = self.repo.get_with_stages(workflow_id)
        if source is None:
            raise WorkflowNotFoundError(
                f"Workflow not found: {workflow_id!r}", workflow_id=workflow_id
            )

        from skillmeat.cache.models import Workflow, WorkflowStage  # noqa: PLC0415 — lazy import avoids circular

        copy_id = uuid.uuid4().hex
        now = datetime.utcnow()

        copy_name = new_name if new_name is not None else f"{source.name} (copy)"

        copy_workflow = Workflow(
            id=copy_id,
            name=copy_name,
            description=source.description,
            version=source.version,
            status="draft",
            definition_yaml=source.definition_yaml,
            definition_hash=source.definition_hash,
            tags_json=source.tags_json,
            config_json=source.config_json,
            error_policy_json=source.error_policy_json,
            hooks_json=source.hooks_json,
            ui_metadata_json=source.ui_metadata_json,
            global_context_module_ids_json=source.global_context_module_ids_json,
            created_by=source.created_by,
            created_at=now,
            updated_at=now,
        )

        # Deep-copy all stages with new IDs pointing to the new workflow
        copied_stages: List[WorkflowStage] = []
        for stage in sorted(source.stages or [], key=lambda s: s.order_index):
            copied_stages.append(
                WorkflowStage(
                    id=uuid.uuid4().hex,
                    workflow_id=copy_id,
                    stage_id_ref=stage.stage_id_ref,
                    name=stage.name,
                    description=stage.description,
                    order_index=stage.order_index,
                    condition=stage.condition,
                    stage_type=stage.stage_type,
                    depends_on_json=stage.depends_on_json,
                    roles_json=stage.roles_json,
                    inputs_json=stage.inputs_json,
                    outputs_json=stage.outputs_json,
                    context_json=stage.context_json,
                    error_policy_json=stage.error_policy_json,
                    handoff_json=stage.handoff_json,
                    gate_json=stage.gate_json,
                    ui_metadata_json=stage.ui_metadata_json,
                    created_at=now,
                    updated_at=now,
                )
            )

        copy_workflow.stages = copied_stages

        created = self.repo.create(copy_workflow)
        logger.info(
            "WorkflowService.duplicate: source_id=%s copy_id=%s name=%r",
            workflow_id,
            copy_id,
            copy_name,
        )
        return _workflow_orm_to_dto(created)

    # =========================================================================
    # Validation & Planning
    # =========================================================================

    def validate(
        self,
        workflow_id_or_yaml: str,
        is_yaml: bool = False,
    ) -> ValidationResult:
        """Validate a workflow definition through all static analysis passes.

        Runs four validation passes in sequence, accumulating all findings into
        a single ``ValidationResult`` so that callers receive a complete picture
        without the process stopping at the first error:

        1. **Schema validation** — Pydantic model parse (catches type errors,
           missing required fields, and enum violations).
        2. **Expression validation** — static ``${{ }}`` reference checks
           (unknown stages, undeclared parameters, missing output keys).
        3. **DAG validation** — unknown ``depends_on`` references and cycle
           detection.
        4. **Artifact resolution** — verifies that every ``roles.primary.artifact``
           and ``roles.tools`` entry follows the ``<type>:<name>`` format expected
           by the execution engine.

        Args:
            workflow_id_or_yaml: When ``is_yaml=False`` (default), the DB primary
                key of a persisted workflow to fetch and validate.  When
                ``is_yaml=True``, a raw YAML string to parse and validate in-memory
                without any DB interaction.
            is_yaml: If ``True``, treat ``workflow_id_or_yaml`` as a YAML string.
                If ``False`` (default), treat it as a workflow ID to look up.

        Returns:
            A ``ValidationResult`` whose ``valid`` flag is ``True`` when no errors
            were found.  ``errors`` and ``warnings`` carry all discovered issues as
            ``ValidationIssue`` instances with ``category``, ``message``,
            ``stage_id``, and ``field`` attributes.

        Raises:
            WorkflowNotFoundError: If ``is_yaml=False`` and no workflow with the
                given ID exists in the database.

        Example::

            svc = WorkflowService()

            # Validate a persisted workflow by ID
            result = svc.validate("abc123")
            if not result.valid:
                for err in result.errors:
                    print(err)

            # Validate a YAML string without persisting
            result = svc.validate(yaml_text, is_yaml=True)
        """
        # ------------------------------------------------------------------
        # Pass 1: Schema validation (parse YAML or fetch from DB).
        # ------------------------------------------------------------------
        result = ValidationResult()
        definition: Optional[WorkflowDefinition] = None

        if is_yaml:
            try:
                definition = _parse_yaml_string(workflow_id_or_yaml)
            except WorkflowParseError as exc:
                result.add_error(
                    category="schema",
                    message=f"YAML parse error: {exc.message}",
                )
                return result  # Cannot proceed without a parseable definition.
            except WorkflowValidationError as exc:
                for detail in exc.details:
                    result.add_error(category="schema", message=detail)
                # Schema errors are blocking — expression/DAG passes require a
                # valid Pydantic model.
                return result
        else:
            workflow_orm = self.repo.get_with_stages(workflow_id_or_yaml)
            if workflow_orm is None:
                raise WorkflowNotFoundError(
                    f"Workflow not found: {workflow_id_or_yaml!r}",
                    workflow_id=workflow_id_or_yaml,
                )
            try:
                definition = _parse_yaml_string(workflow_orm.definition_yaml)
            except WorkflowParseError as exc:
                result.add_error(
                    category="schema",
                    message=f"Stored definition parse error: {exc.message}",
                )
                return result
            except WorkflowValidationError as exc:
                for detail in exc.details:
                    result.add_error(category="schema", message=detail)
                return result

        # ------------------------------------------------------------------
        # Pass 2 + 3: DAG build (validates depends_on refs + cycles) then
        # expression validation (requires a valid DAG).
        # ------------------------------------------------------------------
        dag = None
        try:
            dag = build_dag(definition)
        except WorkflowValidationError as exc:
            result.add_error(category="dag", message=str(exc))
        except WorkflowCycleError as exc:
            result.add_error(category="dag", message=str(exc))

        if dag is not None:
            expr_result = validate_expressions(definition, dag)
            result.errors.extend(expr_result.errors)
            result.warnings.extend(expr_result.warnings)
            if expr_result.errors:
                result.valid = False

        # ------------------------------------------------------------------
        # Pass 4: Artifact reference format validation.
        # ------------------------------------------------------------------
        for stage in definition.stages:
            if stage.roles is not None:
                primary_ref = stage.roles.primary.artifact
                if primary_ref and ":" not in primary_ref:
                    result.add_error(
                        category="artifact",
                        message=(
                            f"roles.primary.artifact {primary_ref!r} must follow "
                            f"the '<type>:<name>' format (e.g. 'agent:researcher-v1')"
                        ),
                        stage_id=stage.id,
                        field="roles.primary.artifact",
                    )
                for tool_ref in stage.roles.tools:
                    if ":" not in tool_ref:
                        result.add_error(
                            category="artifact",
                            message=(
                                f"roles.tools entry {tool_ref!r} must follow "
                                f"the '<type>:<name>' format (e.g. 'skill:web-search')"
                            ),
                            stage_id=stage.id,
                            field="roles.tools",
                        )

        logger.info(
            "WorkflowService.validate: id_or_yaml=%r is_yaml=%s valid=%s "
            "errors=%d warnings=%d",
            workflow_id_or_yaml[:40] if is_yaml else workflow_id_or_yaml,
            is_yaml,
            result.valid,
            len(result.errors),
            len(result.warnings),
        )
        return result

    def plan(
        self,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """Generate a static execution plan for a persisted workflow.

        Validates the workflow first and raises if any blocking errors are found.
        On success, resolves parameters (merging caller values with declared
        defaults), builds the dependency DAG, computes parallel execution batches
        via topological sort, and returns a fully-populated ``ExecutionPlan``.

        Args:
            workflow_id:  DB primary key of the workflow to plan.
            parameters:   Caller-supplied parameter values (merged with workflow
                          defaults).  Missing non-required parameters receive their
                          declared defaults.  ``None`` is treated as an empty dict.

        Returns:
            An ``ExecutionPlan`` containing:

            - ``workflow_id`` / ``workflow_name`` / ``workflow_version``
            - ``parameters`` — fully merged parameter dict
            - ``batches`` — ordered list of ``ExecutionBatch`` objects, each
              containing ``ExecutionPlanStage`` entries that can run concurrently
            - ``estimated_timeout_seconds`` — rough sequential sum of per-batch
              max stage timeouts
            - ``validation`` — the ``ValidationResult`` from the pre-plan
              validation pass (always ``valid=True`` at this point)

        Raises:
            WorkflowNotFoundError: If no workflow with ``workflow_id`` exists.
            WorkflowValidationError: If the workflow definition has blocking
                validation errors (schema, DAG, expression, or artifact issues).

        Example::

            svc = WorkflowService()
            plan = svc.plan("abc123", parameters={"feature_name": "auth-v2"})
            print(plan.format_text())
        """
        # Fetch the stored definition YAML.
        workflow_orm = self.repo.get_with_stages(workflow_id)
        if workflow_orm is None:
            raise WorkflowNotFoundError(
                f"Workflow not found: {workflow_id!r}", workflow_id=workflow_id
            )

        # Pre-plan validation — raise on any blocking errors.
        validation_result = self.validate(workflow_id, is_yaml=False)
        if not validation_result.valid:
            error_summary = "; ".join(
                str(e) for e in validation_result.errors[:5]
            )
            raise WorkflowValidationError(
                f"Workflow '{workflow_id}' failed validation "
                f"({len(validation_result.errors)} error(s)): {error_summary}",
                details=[str(e) for e in validation_result.errors],
            )

        # Parse the stored YAML into a WorkflowDefinition for the planner.
        definition = _parse_yaml_string(workflow_orm.definition_yaml)

        # Delegate to planner — generate_plan handles parameter merging,
        # DAG build, expression validation, batch computation, and timeout
        # estimation internally.
        params: Dict[str, Any] = parameters if parameters is not None else {}
        execution_plan = generate_plan(definition, params)

        logger.info(
            "WorkflowService.plan: id=%s batches=%d stages=%d "
            "estimated_timeout_s=%d",
            workflow_id,
            len(execution_plan.batches),
            sum(len(b.stages) for b in execution_plan.batches),
            execution_plan.estimated_timeout_seconds,
        )
        return execution_plan
