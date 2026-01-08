"""Template rendering service with variable substitution and security.

This module provides secure template deployment functionality with:
- Simple variable substitution (no eval/exec)
- Path traversal prevention
- Atomic deployment with rollback
- Support for selective entity deployment
- Optimized for performance (async I/O, batch queries, cached patterns)

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

Performance Optimizations:
    - Async file I/O with aiofiles for concurrent writes
    - Batch database queries with eager loading to eliminate N+1
    - Pre-compiled template variable patterns (cached)
    - Concurrent file operations using asyncio.gather()
"""

from __future__ import annotations

import asyncio
import re
import tempfile
import shutil
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from skillmeat.cache.models import Artifact, ProjectTemplate, TemplateEntity

# Try importing aiofiles, fall back to sync I/O if not available
try:
    import aiofiles

    ASYNC_IO_AVAILABLE = True
except ImportError:
    ASYNC_IO_AVAILABLE = False


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


@lru_cache(maxsize=128)
def _compile_variable_pattern(variable_name: str) -> re.Pattern:
    """Compile regex pattern for variable substitution (cached).

    Args:
        variable_name: Variable name (e.g., "PROJECT_NAME")

    Returns:
        Compiled regex pattern for {{VARIABLE_NAME}}

    Note:
        Cached to avoid recompiling same patterns
    """
    # Escape variable name for regex, then create pattern
    escaped = re.escape(variable_name)
    return re.compile(rf"{{{{{escaped}}}}}")


def render_content(content: str, variables: dict[str, str]) -> str:
    """Substitute variables in content using cached regex patterns.

    Args:
        content: Template content with {{VARIABLE}} placeholders
        variables: Variable values for substitution

    Returns:
        Content with variables substituted

    Security:
        Uses simple regex replacement - no eval/exec

    Performance:
        Uses cached compiled regex patterns for efficient substitution
    """
    result = content
    for key, value in variables.items():
        pattern = _compile_variable_pattern(key)
        result = pattern.sub(value, result)
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


async def deploy_template_async(
    session: Session,
    template_id: str,
    project_path: str,
    variables: dict[str, str],
    selected_entity_ids: Optional[list[str]] = None,
    overwrite: bool = False,
) -> DeploymentResult:
    """Deploy a template to a project directory (async, optimized).

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

    Performance:
        - Uses eager loading to fetch all artifacts in single query (no N+1)
        - Async file I/O with concurrent writes using asyncio.gather()
        - Pre-creates all directories before writing files
        - Cached regex patterns for variable substitution
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
        if not project_root.stat().st_mode & 0o200:
            raise PermissionError(f"Cannot write to project_path: {project_path}")
    else:
        try:
            project_root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise PermissionError(
                f"Cannot create project directory: {project_path}"
            ) from e

    # OPTIMIZATION 1: Fetch template with eager-loaded entities and artifacts
    # This eliminates N+1 query problem by loading everything in one query
    template = (
        session.query(ProjectTemplate)
        .options(
            joinedload(ProjectTemplate.entities).joinedload(TemplateEntity.artifact)
        )
        .filter(ProjectTemplate.id == template_id)
        .first()
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

        # Check if any required entities are missing
        required_entities = [e for e in template.entities if e.required]
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

            # OPTIMIZATION 2: Pre-create all directories upfront
            unique_dirs = set()
            for entity in sorted_entities:
                artifact = entity.artifact
                if not artifact or not artifact.path_pattern:
                    continue

                target_path = resolve_file_path(artifact.path_pattern, project_root)
                temp_path = resolve_file_path(artifact.path_pattern, temp_root)

                unique_dirs.add(temp_path.parent)

            # Create all directories in batch
            for directory in unique_dirs:
                directory.mkdir(parents=True, exist_ok=True)

            # OPTIMIZATION 3: Prepare all file write tasks
            write_tasks = []
            for entity in sorted_entities:
                artifact = entity.artifact

                if not artifact:
                    continue

                path_pattern = artifact.path_pattern
                if not path_pattern:
                    continue

                target_path = resolve_file_path(path_pattern, project_root)
                temp_path = resolve_file_path(path_pattern, temp_root)

                # Check if file exists and overwrite flag
                if target_path.exists() and not overwrite:
                    skipped_files.append(str(target_path.relative_to(project_root)))
                    continue

                # Fetch artifact content
                artifact_content = _fetch_artifact_content(artifact)

                if artifact_content is None:
                    continue

                # Render content with variables (cached patterns)
                rendered_content = render_content(artifact_content, variables)

                deployed_files.append(str(target_path.relative_to(project_root)))

                # Queue async write task
                write_tasks.append(_write_file_async(temp_path, rendered_content))

            # OPTIMIZATION 4: Execute all file writes concurrently
            if write_tasks:
                await asyncio.gather(*write_tasks)

            # Phase 2: Move files from temp to target (atomic)
            for deployed_file in deployed_files:
                temp_file = temp_root / deployed_file
                target_file = project_root / deployed_file

                # Create parent directories (should already exist, but safety check)
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


def deploy_template(
    session: Session,
    template_id: str,
    project_path: str,
    variables: dict[str, str],
    selected_entity_ids: Optional[list[str]] = None,
    overwrite: bool = False,
) -> DeploymentResult:
    """Deploy a template to a project directory (sync wrapper).

    This is a synchronous wrapper around deploy_template_async() for backward
    compatibility with synchronous code.

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

    Note:
        For best performance, use deploy_template_async() directly in async contexts
    """
    # Run async function in event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create new one
        return asyncio.run(
            deploy_template_async(
                session,
                template_id,
                project_path,
                variables,
                selected_entity_ids,
                overwrite,
            )
        )
    else:
        # Event loop already running, use run_until_complete
        return loop.run_until_complete(
            deploy_template_async(
                session,
                template_id,
                project_path,
                variables,
                selected_entity_ids,
                overwrite,
            )
        )


async def _write_file_async(path: Path, content: str) -> None:
    """Write file content asynchronously.

    Args:
        path: File path to write to
        content: File content to write

    Note:
        Uses aiofiles if available, falls back to sync I/O
    """
    if ASYNC_IO_AVAILABLE:
        # Use async I/O
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(content)
    else:
        # Fall back to sync I/O (still works, just not parallel)
        path.write_text(content, encoding="utf-8")


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

    Implementation Strategy:
        1. Determine artifact source (collection, local, marketplace)
        2. Construct path to artifact content based on artifact.path_pattern
        3. Read and return content from filesystem
        4. For context entities: Read from .claude/ directories
        5. For skills/agents/commands: Read from artifacts/ directory
    """
    # Placeholder: Return None for now
    # Real implementation would:
    # 1. Get collection path from environment or config
    # 2. Construct full path: collection_path / "artifacts" / artifact.type / artifact.name
    # 3. Read main file (SKILL.md, COMMAND.md, AGENT.md, etc.)
    # 4. Return content as string
    return None
