"""WorkflowContextService: inject context per stage using context modules and packer.

This service acts as a thin integration layer between the workflow execution
engine and the Memory & Context Intelligence System (ContextModuleService /
ContextPackerService).  It is intentionally kept simple — context injection is
optional and the service degrades gracefully when the underlying services are
unavailable or when the workflow/stage declares no context bindings.

Typical usage::

    from skillmeat.core.workflow.context_service import WorkflowContextService

    svc = WorkflowContextService(db_path="/path/to/cache.db")

    context = svc.prepare_stage_context(
        execution_id="exec-abc",
        stage_id="research",
        stage_config={
            "context": {
                "modules": ["ctx:domain-knowledge"],
                "memory": {"min_confidence": 0.8, "max_tokens": 2000},
            }
        },
        parameters={"project_id": "proj-123"},
    )
    # context["packed_context"] → markdown string or "" on degradation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowContextService:
    """Inject context per stage using ContextModuleService and ContextPackerService.

    Resolves context module references (``"ctx:<name>"`` syntax) declared in
    the workflow definition, merges global and stage-level bindings, and uses
    ``ContextPackerService.generate_pack()`` to produce a packed context string
    ready for injection into the stage's agent prompt.

    Graceful degradation is a first-class requirement: if either
    ``ContextModuleService`` or ``ContextPackerService`` cannot be imported or
    initialized (e.g. missing DB tables, import error), ``prepare_stage_context``
    returns an empty dict rather than raising.

    Attributes:
        _db_path: SQLite database path forwarded to the context services.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize WorkflowContextService.

        Args:
            db_path: Optional path to the SQLite database file.  Uses the
                default ``~/.skillmeat/cache/cache.db`` (resolved by the
                underlying repositories) when ``None``.
        """
        self._db_path = db_path

    # =========================================================================
    # Public API
    # =========================================================================

    def prepare_stage_context(
        self,
        execution_id: str,
        stage_id: str,
        stage_config: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build context for a stage and return it as a plain dict.

        Resolution order:
        1. Collect ``global_modules`` from the workflow-level ``context`` block
           (passed in via ``stage_config["global_modules"]`` if present).
        2. Merge stage-level ``context.modules`` (override / extend).
        3. For each ``"ctx:<name>"`` reference, look up the module by name
           via ``ContextModuleService`` and call ``ContextPackerService.generate_pack()``
           with the memory config from the stage (or global) binding.
        4. Combine packed content and return.

        If no context bindings are declared, or if any service call fails, an
        empty dict is returned so execution continues unimpeded.

        Args:
            execution_id: Running execution identifier (used for logging only).
            stage_id:     Stage identifier within the workflow.
            stage_config: Dict representing the stage definition.  Expected keys:
                          - ``"context"`` (optional): stage-level ContextBinding dict
                            with optional ``"modules"`` (list) and ``"memory"`` (dict).
                          - ``"global_modules"`` (optional): list of module references
                            inherited from the workflow-level context block.
                          - ``"global_memory"`` (optional): workflow-level MemoryConfig
                            dict used as fallback when stage has no memory config.
            parameters:   Resolved workflow parameters dict.  Expected to contain
                          ``"project_id"`` when memory injection is needed.

        Returns:
            Dict with zero or more of the following keys on success:
            - ``"packed_context"``: str — markdown-formatted context pack.
            - ``"modules_resolved"``: list[str] — module names that were packed.
            - ``"tokens_estimated"``: int — token estimate for the packed context.

            Empty dict ``{}`` on graceful degradation (no bindings or service error).
        """
        # ------------------------------------------------------------------
        # Step 1: Resolve module reference list (global + stage-level merge)
        # ------------------------------------------------------------------
        global_modules: List[str] = stage_config.get("global_modules") or []
        stage_context: Dict[str, Any] = stage_config.get("context") or {}
        stage_modules: List[str] = stage_context.get("modules") or []

        # Stage modules override global modules where names collide; otherwise
        # extend.  Use an ordered dict-like approach preserving insertion order.
        combined: Dict[str, str] = {}
        for ref in global_modules:
            combined[ref] = ref
        for ref in stage_modules:
            combined[ref] = ref  # stage entry wins on collision (same key)

        module_refs: List[str] = list(combined.values())

        if not module_refs:
            # No context bindings declared — skip gracefully.
            logger.debug(
                "prepare_stage_context: execution=%s stage=%s — no module refs, skipping",
                execution_id,
                stage_id,
            )
            return {}

        # ------------------------------------------------------------------
        # Step 2: Resolve memory config (stage overrides global fallback)
        # ------------------------------------------------------------------
        global_memory: Dict[str, Any] = stage_config.get("global_memory") or {}
        stage_memory: Dict[str, Any] = stage_context.get("memory") or {}
        # Merge: stage_memory keys take precedence over global_memory.
        effective_memory: Dict[str, Any] = {**global_memory, **stage_memory}

        min_confidence: float = float(effective_memory.get("min_confidence", 0.7))
        max_tokens: int = int(effective_memory.get("max_tokens", 2000))
        project_id: Optional[str] = parameters.get("project_id")

        # ------------------------------------------------------------------
        # Step 3: Lazy-import context services (graceful degradation on error)
        # ------------------------------------------------------------------
        try:
            from skillmeat.core.services.context_module_service import (  # noqa: PLC0415
                ContextModuleService,
            )
            from skillmeat.core.services.context_packer_service import (  # noqa: PLC0415
                ContextPackerService,
            )
        except ImportError as exc:
            logger.warning(
                "prepare_stage_context: context services unavailable (import error) — "
                "skipping context injection for execution=%s stage=%s. Error: %s",
                execution_id,
                stage_id,
                exc,
            )
            return {}

        try:
            module_svc = ContextModuleService(db_path=self._db_path)
            packer_svc = ContextPackerService(db_path=self._db_path)
        except Exception as exc:
            logger.warning(
                "prepare_stage_context: failed to initialize context services — "
                "skipping context injection for execution=%s stage=%s. Error: %s",
                execution_id,
                stage_id,
                exc,
            )
            return {}

        # ------------------------------------------------------------------
        # Step 4: Resolve each "ctx:<name>" reference → module_id
        # ------------------------------------------------------------------
        resolved_module_ids: List[str] = []
        resolved_module_names: List[str] = []

        for ref in module_refs:
            if not ref.startswith("ctx:"):
                logger.debug(
                    "prepare_stage_context: skipping non-ctx ref %r for stage=%s",
                    ref,
                    stage_id,
                )
                continue

            module_name = ref[len("ctx:"):]
            if not module_name:
                continue

            # Look up module by name within the project scope.
            # ContextModuleService.list() supports name-based filtering via the
            # underlying repository.  We iterate to find a match by name.
            try:
                # list_by_project() returns a paginated dict with an "items" key.
                # NOTE: If ContextModuleService gains a get_by_name() method in the
                # future, replace this lookup with that call for efficiency.
                page = module_svc.list_by_project(
                    project_id=project_id or "",
                    limit=200,
                )
                modules_list: List[Dict[str, Any]] = page.get("items", [])
                match = next(
                    (m for m in modules_list if m.get("name") == module_name),
                    None,
                )
                if match:
                    resolved_module_ids.append(match["id"])
                    resolved_module_names.append(module_name)
                    logger.debug(
                        "prepare_stage_context: resolved %r → module_id=%s",
                        ref,
                        match["id"],
                    )
                else:
                    logger.warning(
                        "prepare_stage_context: module %r not found for "
                        "execution=%s stage=%s — skipping",
                        ref,
                        execution_id,
                        stage_id,
                    )
            except Exception as exc:
                logger.warning(
                    "prepare_stage_context: error looking up module %r — "
                    "skipping. execution=%s stage=%s. Error: %s",
                    ref,
                    execution_id,
                    stage_id,
                    exc,
                )

        if not resolved_module_ids:
            logger.debug(
                "prepare_stage_context: no modules resolved for execution=%s stage=%s",
                execution_id,
                stage_id,
            )
            return {}

        # ------------------------------------------------------------------
        # Step 5: Pack context using ContextPackerService
        # ------------------------------------------------------------------
        packed_parts: List[str] = []
        tokens_total: int = 0

        for module_id, module_name in zip(resolved_module_ids, resolved_module_names):
            try:
                # generate_pack returns a dict with at minimum a "markdown" key.
                pack_result: Dict[str, Any] = packer_svc.generate_pack(
                    project_id=project_id or "",
                    module_id=module_id,
                    budget_tokens=max_tokens,
                    filters={"min_confidence": min_confidence} if min_confidence else None,
                )
                markdown: str = pack_result.get("markdown") or ""
                if markdown:
                    packed_parts.append(markdown)
                    tokens_total += pack_result.get("total_tokens", 0) or ContextPackerService.estimate_tokens(markdown)
                    logger.debug(
                        "prepare_stage_context: packed module=%r tokens=%d for stage=%s",
                        module_name,
                        tokens_total,
                        stage_id,
                    )
            except Exception as exc:
                logger.warning(
                    "prepare_stage_context: error packing module=%r — "
                    "skipping. execution=%s stage=%s. Error: %s",
                    module_name,
                    execution_id,
                    stage_id,
                    exc,
                )

        if not packed_parts:
            return {}

        packed_context = "\n\n".join(packed_parts)

        logger.info(
            "prepare_stage_context: execution=%s stage=%s — packed %d module(s), "
            "~%d tokens",
            execution_id,
            stage_id,
            len(packed_parts),
            tokens_total,
        )

        return {
            "packed_context": packed_context,
            "modules_resolved": resolved_module_names,
            "tokens_estimated": tokens_total,
        }
