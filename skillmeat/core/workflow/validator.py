"""Static expression validator for SkillMeat Workflow Definition Language (SWDL).

Performs compile-time analysis of ``${{ }}`` expressions in a workflow definition,
catching reference errors before execution begins.

Typical usage::

    from skillmeat.core.workflow import build_dag, parse_workflow
    from skillmeat.core.workflow.validator import validate_expressions

    workflow = parse_workflow(path)
    dag = build_dag(workflow)
    result = validate_expressions(workflow, dag)

    if not result.valid:
        for issue in result.errors:
            print(f"[{issue.category}] {issue.message}")

Validation coverage:

    - ``${{ stages.X.outputs.Y }}``:
        - Stage ``X`` must exist in the workflow.
        - Stage ``X`` must appear in the referencing stage's ``depends_on``
          (or be the same stage for a self-reference).
        - Output ``Y`` must be declared in stage ``X``'s ``outputs`` contract.
        - If both sides carry a ``type``, a type-mismatch warning is emitted.

    - ``${{ stages.X.status }}``:
        - Stage ``X`` must exist in the workflow.

    - ``${{ parameters.X }}``:
        - Parameter ``X`` must be declared in ``workflow.config.parameters``.

    Expression fields scanned across all stages:
        - ``inputs[*].source``
        - ``condition``
        - ``error_policy.retry`` (serialised as a string — skipped if not a string)

    Expressions that fail to parse are reported as ``"expression"`` category errors
    so that callers receive a complete picture in a single validation pass rather
    than stopping at the first bad expression.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from skillmeat.core.workflow.dag import DAG
from skillmeat.core.workflow.expressions import ExpressionError, ExpressionParser
from skillmeat.core.workflow.models import WorkflowDefinition

# ---------------------------------------------------------------------------
# Reference patterns
# ---------------------------------------------------------------------------

# Matches: stages.STAGE_ID.outputs.OUTPUT_KEY
_RE_STAGE_OUTPUT = re.compile(
    r"stages\.(?P<stage_id>[\w][\w-]*)\.outputs\.(?P<output_key>\w+)"
)

# Matches: stages.STAGE_ID.status
_RE_STAGE_STATUS = re.compile(r"stages\.(?P<stage_id>[\w][\w-]*)\.status")

# Matches: parameters.PARAM_NAME
_RE_PARAMETER = re.compile(r"parameters\.(?P<param_name>\w+)")

_PARSER = ExpressionParser()

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single validation finding (error or warning).

    Attributes:
        category: Broad classification of the finding.
                  One of ``"schema"``, ``"expression"``, ``"dag"``,
                  ``"artifact"``.
        message:  Human-readable description of the issue.
        stage_id: The stage where the issue was found, if applicable.
        field:    The field within the stage where the issue was found
                  (e.g. ``"inputs.my_input.source"``), if applicable.
    """

    category: str
    message: str
    stage_id: Optional[str] = None
    field: Optional[str] = None

    def __str__(self) -> str:
        parts = [f"[{self.category}]"]
        if self.stage_id:
            parts.append(f"stage={self.stage_id!r}")
        if self.field:
            parts.append(f"field={self.field!r}")
        parts.append(self.message)
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Accumulated result of a static expression validation pass.

    Attributes:
        valid:    ``True`` when no errors were recorded (warnings are allowed).
        errors:   List of blocking validation issues.
        warnings: List of advisory validation issues.
    """

    valid: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    def add_error(
        self,
        category: str,
        message: str,
        stage_id: Optional[str] = None,
        field: Optional[str] = None,
    ) -> None:
        """Record a blocking validation error and mark the result invalid.

        Args:
            category: Issue category (``"schema"``, ``"expression"``,
                      ``"dag"``, ``"artifact"``).
            message:  Human-readable description.
            stage_id: Originating stage ID (optional).
            field:    Originating field path (optional).
        """
        self.errors.append(
            ValidationIssue(
                category=category,
                message=message,
                stage_id=stage_id,
                field=field,
            )
        )
        self.valid = False

    def add_warning(
        self,
        category: str,
        message: str,
        stage_id: Optional[str] = None,
        field: Optional[str] = None,
    ) -> None:
        """Record a non-blocking advisory warning.

        Args:
            category: Issue category.
            message:  Human-readable description.
            stage_id: Originating stage ID (optional).
            field:    Originating field path (optional).
        """
        self.warnings.append(
            ValidationIssue(
                category=category,
                message=message,
                stage_id=stage_id,
                field=field,
            )
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_expression_bodies(text: str) -> List[str]:
    """Return all ``${{ expr }}`` bodies found in *text* (whitespace-stripped).

    Returns an empty list when *text* contains no placeholders.
    """
    return _PARSER.extract_expressions(text)


def _validate_expression_body(
    expr_body: str,
    *,
    stage_id: str,
    field_path: str,
    referencing_stage_depends_on: List[str],
    all_stage_ids: List[str],
    stage_outputs: dict,  # stage_id -> set[str] output keys
    stage_input_type: Optional[str],
    parameters: dict,  # param_name -> WorkflowParameter
    result: ValidationResult,
) -> None:
    """Validate a single parsed expression body against the workflow state.

    Checks stage output references, stage status references, and parameter
    references.  All findings are written into *result* rather than raised.

    Args:
        expr_body:                     The raw expression body (no ``${{ }}``).
        stage_id:                      The stage containing this expression.
        field_path:                    Dotted path of the field (for reporting).
        referencing_stage_depends_on:  ``depends_on`` list of the referencing stage.
        all_stage_ids:                 All stage IDs defined in the workflow.
        stage_outputs:                 Mapping of stage_id to set of output keys.
        stage_input_type:              Type declared on the input field (or ``None``).
        parameters:                    Declared workflow parameters.
        result:                        Accumulates validation findings.
    """
    # --- Stage output references ----------------------------------------
    for m in _RE_STAGE_OUTPUT.finditer(expr_body):
        ref_stage = m.group("stage_id")
        ref_output = m.group("output_key")

        # 1. Referenced stage must exist.
        if ref_stage not in all_stage_ids:
            result.add_error(
                category="expression",
                message=(
                    f"Expression references unknown stage '{ref_stage}' "
                    f"(in '{expr_body}')"
                ),
                stage_id=stage_id,
                field=field_path,
            )
            continue  # No point checking further for this match.

        # 2. Referenced stage must be in depends_on (or be the same stage).
        if ref_stage != stage_id and ref_stage not in referencing_stage_depends_on:
            result.add_error(
                category="dag",
                message=(
                    f"Expression references stage '{ref_stage}' output but "
                    f"'{stage_id}' does not declare it in depends_on"
                ),
                stage_id=stage_id,
                field=field_path,
            )

        # 3. Output key must be declared in the referenced stage's outputs.
        declared_outputs = stage_outputs.get(ref_stage, set())
        if ref_output not in declared_outputs:
            result.add_error(
                category="expression",
                message=(
                    f"Stage '{ref_stage}' does not declare output '{ref_output}'; "
                    f"declared outputs: {sorted(declared_outputs) or '(none)'}"
                ),
                stage_id=stage_id,
                field=field_path,
            )
            continue

        # 4. Type compatibility warning (best-effort).
        if stage_input_type is not None:
            # Retrieve the referenced output's type from the workflow model.
            # (stage_outputs only holds keys; we need the full model here.)
            # _output_types is populated by the caller via the closure-like
            # approach of passing stage_output_types explicitly — see
            # validate_expressions() for the full picture.
            pass  # handled by validate_expressions with full type info

    # --- Stage status references -----------------------------------------
    for m in _RE_STAGE_STATUS.finditer(expr_body):
        ref_stage = m.group("stage_id")
        if ref_stage not in all_stage_ids:
            result.add_error(
                category="expression",
                message=(
                    f"Expression references status of unknown stage '{ref_stage}' "
                    f"(in '{expr_body}')"
                ),
                stage_id=stage_id,
                field=field_path,
            )

    # --- Parameter references --------------------------------------------
    for m in _RE_PARAMETER.finditer(expr_body):
        param_name = m.group("param_name")
        if param_name not in parameters:
            result.add_error(
                category="expression",
                message=(
                    f"Expression references undeclared parameter '{param_name}'; "
                    f"declared parameters: {sorted(parameters.keys()) or '(none)'}"
                ),
                stage_id=stage_id,
                field=field_path,
            )


def _check_parse(
    expr_body: str,
    *,
    stage_id: str,
    field_path: str,
    result: ValidationResult,
) -> bool:
    """Attempt to parse *expr_body*; record an error and return False on failure.

    Returns:
        ``True`` when the expression parses successfully, ``False`` otherwise.
    """
    try:
        _PARSER.parse(expr_body)
        return True
    except ExpressionError as exc:
        result.add_error(
            category="expression",
            message=f"Expression parse error: {exc.message}",
            stage_id=stage_id,
            field=field_path,
        )
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_expressions(workflow: WorkflowDefinition, dag: DAG) -> ValidationResult:
    """Statically validate all ``${{ }}`` expressions in *workflow*.

    Walks every stage's ``inputs[*].source``, ``condition``, and
    ``error_policy.retry`` (when expressed as a string) fields and validates
    each embedded SWDL expression against the workflow's declared parameters,
    stage IDs, and stage output contracts.

    The function does **not** raise exceptions — all findings are returned in
    a ``ValidationResult`` so that the caller receives the full picture in one
    pass rather than stopping at the first error.

    Args:
        workflow: A fully-parsed ``WorkflowDefinition`` (Pydantic-validated).
        dag:      The dependency graph built from *workflow* via ``build_dag()``.
                  Used to look up each stage's declared dependencies.

    Returns:
        A ``ValidationResult`` whose ``valid`` flag is ``True`` when no errors
        were found and whose ``errors`` / ``warnings`` lists contain all
        discovered issues.

    Example::

        from skillmeat.core.workflow import build_dag, parse_workflow
        from skillmeat.core.workflow.validator import validate_expressions

        workflow = parse_workflow(path)
        dag = build_dag(workflow)
        result = validate_expressions(workflow, dag)

        for err in result.errors:
            print(err)
    """
    result = ValidationResult()

    # Precompute lookup tables from the workflow for O(1) checks.
    all_stage_ids: List[str] = dag.all_stage_ids()
    parameters: dict = workflow.config.parameters  # name -> WorkflowParameter

    # stage_outputs: stage_id -> set of declared output keys
    stage_outputs: dict = {
        stage.id: set(stage.outputs.keys()) for stage in workflow.stages
    }

    # stage_output_types: (stage_id, output_key) -> type string | None
    stage_output_types: dict = {}
    for stage in workflow.stages:
        for out_key, out_contract in stage.outputs.items():
            stage_output_types[(stage.id, out_key)] = out_contract.type

    # -----------------------------------------------------------------------
    # Walk all stages
    # -----------------------------------------------------------------------
    for stage in workflow.stages:
        stage_id = stage.id
        depends_on: List[str] = list(stage.depends_on)

        # Collect (text, field_path, input_type) triples to validate.
        # input_type is carried for the type-mismatch warning.
        texts_to_check: List[tuple] = []

        # inputs[*].source
        for inp_name, inp_contract in stage.inputs.items():
            if inp_contract.source:
                texts_to_check.append(
                    (
                        inp_contract.source,
                        f"inputs.{inp_name}.source",
                        inp_contract.type,  # type declared on the input side
                    )
                )

        # condition
        if stage.condition:
            texts_to_check.append((stage.condition, "condition", None))

        # error_policy.retry — RetryPolicy is a Pydantic model; skip non-strings.
        # (The spec says to scan this field, but in the model RetryPolicy is
        # a structured object, not a free-form string.  We scan
        # non_retryable_errors entries as strings since those may carry
        # expressions in future schema revisions, but we gracefully skip
        # structured fields.)
        if stage.error_policy and stage.error_policy.retry:
            retry = stage.error_policy.retry
            # non_retryable_errors: list[str] — scan each entry
            for idx, entry in enumerate(retry.non_retryable_errors):
                if isinstance(entry, str) and "${{" in entry:
                    texts_to_check.append(
                        (entry, f"error_policy.retry.non_retryable_errors[{idx}]", None)
                    )

        # -----------------------------------------------------------------------
        # Validate collected texts
        # -----------------------------------------------------------------------
        for text, field_path, input_type in texts_to_check:
            expr_bodies = _extract_expression_bodies(text)
            for expr_body in expr_bodies:
                # Parse check first — skip reference validation if unparseable.
                if not _check_parse(expr_body, stage_id=stage_id, field_path=field_path, result=result):
                    continue

                # Reference validation
                _validate_expression_body(
                    expr_body,
                    stage_id=stage_id,
                    field_path=field_path,
                    referencing_stage_depends_on=depends_on,
                    all_stage_ids=all_stage_ids,
                    stage_outputs=stage_outputs,
                    stage_input_type=input_type,
                    parameters=parameters,
                    result=result,
                )

                # Type-mismatch warning (done here where we have full type tables).
                if input_type is not None:
                    for m in _RE_STAGE_OUTPUT.finditer(expr_body):
                        ref_stage = m.group("stage_id")
                        ref_output = m.group("output_key")
                        output_type = stage_output_types.get((ref_stage, ref_output))
                        if (
                            output_type is not None
                            and output_type != input_type
                        ):
                            result.add_warning(
                                category="expression",
                                message=(
                                    f"Type mismatch: input '{field_path}' expects "
                                    f"'{input_type}' but stage '{ref_stage}' output "
                                    f"'{ref_output}' is declared as '{output_type}'"
                                ),
                                stage_id=stage_id,
                                field=field_path,
                            )

    return result
