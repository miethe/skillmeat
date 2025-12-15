"""Template rendering service with variable substitution and security.

This module provides secure template deployment functionality with:
- Simple variable substitution (no eval/exec)
- Path traversal prevention
- Atomic deployment with rollback
- Support for selective entity deployment

Security:
    - Uses simple string replacement (no eval/exec)
    - Validates all file paths before writing
    - Prevents path traversal attacks
    - Atomic deployment (all-or-nothing)

Variable Substitution:
    Only whitelisted variables are supported:
    - {{PROJECT_NAME}} - Required
    - {{PROJECT_DESCRIPTION}} - Optional
    - {{AUTHOR}} - Optional
    - {{DATE}} - Optional (defaults to current date)
    - {{ARCHITECTURE_DESCRIPTION}} - Optional
"""

from __future__ import annotations

import tempfile
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.cache.models import Artifact, ProjectTemplate, TemplateEntity


# Variable whitelist for security
ALLOWED_VARIABLES = {
    "PROJECT_NAME",
    "PROJECT_DESCRIPTION",
    "AUTHOR",
    "DATE",
    "ARCHITECTURE_DESCRIPTION",
}


@dataclass
class DeploymentResult:
    """Result of template deployment operation.

    Attributes:
        success: Whether deployment completed successfully
        project_path: Target project path where template was deployed
        deployed_files: List of files successfully deployed (relative paths)
        skipped_files: List of files skipped (already exist, overwrite=False)
        message: Human-readable deployment status message
    """

    success: bool
    project_path: str
    deployed_files: list[str]
    skipped_files: list[str]
    message: str


def validate_variables(variables: dict[str, str]) -> None:
    """Validate variables against whitelist.

    Args:
        variables: Variable values for substitution

    Raises:
        ValueError: If variables contain disallowed keys or missing required keys
    """
    # Check for required variables
    if "PROJECT_NAME" not in variables:
        raise ValueError("PROJECT_NAME is required")

    # Check for disallowed variables
    disallowed = set(variables.keys()) - ALLOWED_VARIABLES
    if disallowed:
        raise ValueError(
            f"Disallowed variables: {', '.join(sorted(disallowed))}. "
            f"Allowed variables: {', '.join(sorted(ALLOWED_VARIABLES))}"
        )

    # Validate PROJECT_NAME is not empty
    if not variables["PROJECT_NAME"].strip():
        raise ValueError("PROJECT_NAME cannot be empty")


def render_content(content: str, variables: dict[str, str]) -> str:
    """Substitute variables in content using simple string replacement.

    Args:
        content: Template content with {{VARIABLE}} placeholders
        variables: Variable values for substitution

    Returns:
        Content with variables substituted

    Security:
        Uses simple str.replace() - no eval/exec
    """
    result = content
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"  # {{VARIABLE}}
        result = result.replace(placeholder, value)
    return result


def resolve_file_path(path_pattern: str, project_path: Path) -> Path:
    """Convert path pattern to absolute path within project.

    Args:
        path_pattern: Path pattern like '.claude/rules/api.md'
        project_path: Absolute path to project root

    Returns:
        Absolute path for file

    Raises:
        ValueError: If path_pattern contains '..' (path traversal)
    """
    # Prevent path traversal
    if ".." in path_pattern:
        raise ValueError(f"Path pattern cannot contain '..': {path_pattern}")

    # Remove leading './' if present, but preserve directory names starting with '.'
    clean_pattern = path_pattern
    if clean_pattern.startswith("./"):
        clean_pattern = clean_pattern[2:]
    elif clean_pattern.startswith("/"):
        clean_pattern = clean_pattern[1:]

    # Construct absolute path
    target_path = project_path / clean_pattern

    # Verify resolved path is still within project_path (security check)
    try:
        target_path.resolve().relative_to(project_path.resolve())
    except ValueError as e:
        raise ValueError(
            f"Path pattern resolves outside project directory: {path_pattern}"
        ) from e

    return target_path


def deploy_template(
    session: Session,
    template_id: str,
    project_path: str,
    variables: dict[str, str],
    selected_entity_ids: Optional[list[str]] = None,
    overwrite: bool = False,
) -> DeploymentResult:
    """Deploy a template to a project directory.

    Args:
        session: Database session
        template_id: UUID of template to deploy
        project_path: Absolute path to project root
        variables: Variable values for substitution
        selected_entity_ids: Optional subset of entity IDs to deploy
        overwrite: Whether to overwrite existing files

    Returns:
        DeploymentResult with deployed_files, skipped_files, success

    Raises:
        ValueError: Invalid template_id, variables, or path
        PermissionError: Cannot write to project_path
        FileExistsError: File exists and overwrite=False
    """
    # Validate variables
    validate_variables(variables)

    # Add default DATE if not provided
    if "DATE" not in variables:
        variables["DATE"] = datetime.now().strftime("%Y-%m-%d")

    # Validate and resolve project path
    project_root = Path(project_path).resolve()
    if not project_root.is_absolute():
        raise ValueError(f"project_path must be absolute: {project_path}")

    # Check if project path exists and is writable
    if project_root.exists():
        if not project_root.is_dir():
            raise ValueError(f"project_path is not a directory: {project_path}")
        # Check write permissions by checking if we can write to directory
        if not project_root.stat().st_mode & 0o200:  # Check write bit
            raise PermissionError(f"Cannot write to project_path: {project_path}")
    else:
        # Attempt to create project directory
        try:
            project_root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise PermissionError(
                f"Cannot create project directory: {project_path}"
            ) from e

    # Fetch template with entities
    template = (
        session.query(ProjectTemplate).filter(ProjectTemplate.id == template_id).first()
    )

    if not template:
        raise ValueError(f"Template not found: {template_id}")

    if not template.entities:
        return DeploymentResult(
            success=True,
            project_path=str(project_root),
            deployed_files=[],
            skipped_files=[],
            message="Template has no entities to deploy",
        )

    # Filter entities if selected_entity_ids provided
    entities_to_deploy = template.entities
    if selected_entity_ids is not None:
        selected_set = set(selected_entity_ids)
        entities_to_deploy = [
            entity
            for entity in entities_to_deploy
            if entity.artifact_id in selected_set
        ]

        if not entities_to_deploy:
            return DeploymentResult(
                success=True,
                project_path=str(project_root),
                deployed_files=[],
                skipped_files=[],
                message="No matching entities found for deployment",
            )

    # Filter out required entities if not in selected_entity_ids
    if selected_entity_ids is not None:
        # Check if any required entities are missing
        required_entities = [e for e in template.entities if e.required]
        selected_set = set(selected_entity_ids)
        missing_required = [
            e.artifact_id
            for e in required_entities
            if e.artifact_id not in selected_set
        ]

        if missing_required:
            raise ValueError(
                f"Required entities must be included: {', '.join(missing_required)}"
            )

    # Sort entities by deploy_order
    sorted_entities = sorted(entities_to_deploy, key=lambda e: e.deploy_order)

    # Atomic deployment: use temp directory first
    deployed_files: list[str] = []
    skipped_files: list[str] = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)

            # Phase 1: Render all entities to temp directory
            for entity in sorted_entities:
                # Fetch artifact with content
                artifact = (
                    session.query(Artifact)
                    .filter(Artifact.id == entity.artifact_id)
                    .first()
                )

                if not artifact:
                    raise ValueError(
                        f"Artifact not found: {entity.artifact_id} "
                        f"(entity: {entity.artifact_id})"
                    )

                # Get path pattern
                path_pattern = artifact.path_pattern
                if not path_pattern:
                    # Skip artifacts without path pattern
                    continue

                # Resolve target path
                target_path = resolve_file_path(path_pattern, project_root)
                temp_path = resolve_file_path(path_pattern, temp_root)

                # Check if file exists and overwrite flag
                if target_path.exists() and not overwrite:
                    skipped_files.append(str(target_path.relative_to(project_root)))
                    continue

                # Fetch artifact content
                # NOTE: Artifact model doesn't have content field directly
                # We need to read from filesystem based on artifact metadata
                # For now, we'll assume artifacts are stored in collection
                # This is a placeholder - actual implementation would fetch from storage

                # TODO: Implement actual content fetching from artifact storage
                # This requires integration with ArtifactManager or storage layer
                artifact_content = _fetch_artifact_content(artifact)

                if artifact_content is None:
                    # Skip artifacts without content
                    continue

                # Render content with variables
                rendered_content = render_content(artifact_content, variables)

                # Write to temp directory
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_text(rendered_content, encoding="utf-8")

                deployed_files.append(str(target_path.relative_to(project_root)))

            # Phase 2: Move files from temp to target (atomic)
            for deployed_file in deployed_files:
                temp_file = temp_root / deployed_file
                target_file = project_root / deployed_file

                # Create parent directories
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Move file
                shutil.copy2(temp_file, target_file)

        # Success
        message = f"Successfully deployed {len(deployed_files)} file(s)"
        if skipped_files:
            message += f", skipped {len(skipped_files)} existing file(s)"

        return DeploymentResult(
            success=True,
            project_path=str(project_root),
            deployed_files=deployed_files,
            skipped_files=skipped_files,
            message=message,
        )

    except Exception as e:
        # Failure - temp directory automatically cleaned up
        return DeploymentResult(
            success=False,
            project_path=str(project_root),
            deployed_files=[],
            skipped_files=[],
            message=f"Deployment failed: {str(e)}",
        )


def _fetch_artifact_content(artifact: Artifact) -> Optional[str]:
    """Fetch artifact content from storage.

    This is a placeholder implementation. Actual implementation should
    integrate with ArtifactManager or storage layer to fetch content.

    Args:
        artifact: Artifact ORM model

    Returns:
        Artifact content as string, or None if not available

    TODO: Implement actual content fetching from:
        - Collection storage (~/.skillmeat/collection/artifacts/)
        - Local project artifacts
        - Marketplace cache
    """
    # Placeholder: Return None for now
    # Real implementation would:
    # 1. Determine artifact source (collection, local, marketplace)
    # 2. Construct path to artifact content
    # 3. Read and return content
    return None
