"""Context entity validation module.

Provides validators for all 5 context entity types with security considerations
for path traversal prevention and content validation.

Entity Types:
- ProjectConfig: CLAUDE.md files (markdown with optional frontmatter)
- SpecFile: .claude/specs/ files (YAML frontmatter + markdown)
- RuleFile: .claude/rules/ files (markdown with path scope comments)
- ContextFile: .claude/context/ files (YAML frontmatter with references + markdown)
- ProgressTemplate: .claude/progress/ files (YAML frontmatter + markdown hybrid)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class ValidationError:
    """Represents a validation error.

    Attributes:
        field: Field or section that failed validation
        message: Human-readable error message
        severity: Error severity ("error" or "warning")
    """

    field: str
    message: str
    severity: str = "error"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


def _validate_path_security(path: str) -> List[str]:
    """Validate path for security issues.

    Prevents path traversal attacks by checking for:
    - Parent directory references (..)
    - Absolute paths
    - Paths that escape .claude directory

    Args:
        path: File path to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Normalize path for checking
    normalized = Path(path).as_posix()

    # Check for parent directory references
    if ".." in normalized.split("/"):
        errors.append("Path contains parent directory reference (..) - security risk")

    # Check for absolute paths (Unix-style)
    if normalized.startswith("/"):
        errors.append("Absolute path detected - must be relative")

    # Check for absolute paths (Windows-style)
    if len(normalized) > 1 and normalized[1] == ":":
        errors.append("Absolute path detected - must be relative")

    # For .claude/* paths, verify they don't escape the directory
    if path.startswith(".claude/"):
        try:
            # Resolve would fail on invalid paths
            resolved = Path(".claude") / Path(path.replace(".claude/", ""))
            if not str(resolved).startswith(".claude"):
                errors.append("Path attempts to escape .claude directory")
        except (ValueError, OSError):
            errors.append("Invalid path format")

    return errors


def _extract_frontmatter(content: str) -> tuple[Optional[Dict], str]:
    """Extract YAML frontmatter from markdown content.

    Looks for YAML frontmatter delimited by --- at the start of the file:
    ---
    title: My Document
    key: value
    ---

    Args:
        content: Markdown file content

    Returns:
        Tuple of (frontmatter_dict, remaining_content)
        Returns (None, content) if no frontmatter found
    """
    if not content or not content.strip():
        return None, content

    # Match YAML frontmatter: --- ... ---
    # Must be at start of file
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return None, content

    yaml_content = match.group(1)
    remaining_content = content[match.end() :]

    try:
        frontmatter = yaml.safe_load(yaml_content)
        if not isinstance(frontmatter, dict):
            return None, content
        return frontmatter, remaining_content
    except yaml.YAMLError:
        return None, content


def validate_project_config(content: str, path: str) -> List[str]:
    """Validate ProjectConfig entity (CLAUDE.md).

    Requirements:
    - Must be valid markdown
    - Optional frontmatter (not required)
    - Must not be empty
    - No path traversal

    Args:
        content: File content
        path: File path (for path validation)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path)
    errors.extend(path_errors)

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (optional, just validate if present)
    frontmatter, _ = _extract_frontmatter(content)
    if frontmatter is not None:
        # Frontmatter exists and was parsed successfully
        # No specific required fields for CLAUDE.md
        pass

    # Basic markdown validation: should have some text
    if len(content.strip()) < 10:
        errors.append("Content too short to be valid markdown")

    return errors


def validate_spec_file(content: str, path: str) -> List[str]:
    """Validate SpecFile entity (.claude/specs/).

    Requirements:
    - YAML frontmatter is REQUIRED
    - Must have 'title' field in frontmatter
    - Path must start with .claude/specs/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path)
    errors.extend(path_errors)

    # Path must start with .claude/specs/
    if not path.startswith(".claude/specs/"):
        errors.append("Path must start with .claude/specs/")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (REQUIRED)
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Must have 'title' field
    if "title" not in frontmatter:
        errors.append("Frontmatter must include 'title' field")

    # Validate remaining content is not empty
    if not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    return errors


def validate_rule_file(content: str, path: str) -> List[str]:
    """Validate RuleFile entity (.claude/rules/).

    Requirements:
    - Should have <!-- Path Scope: ... --> comment
    - Path must start with .claude/rules/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path)
    errors.extend(path_errors)

    # Path must start with .claude/rules/
    if not path.startswith(".claude/rules/"):
        errors.append("Path must start with .claude/rules/")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Check for path scope comment (optional but recommended)
    path_scope_pattern = r"<!--\s*Path Scope:\s*.+?\s*-->"
    if not re.search(path_scope_pattern, content):
        # This is a warning, not an error
        # We'll add it but with lower severity
        # For now, just skip - can be added to ValidationError if needed
        pass

    # Basic markdown validation
    if len(content.strip()) < 10:
        errors.append("Content too short to be valid markdown")

    return errors


def validate_context_file(content: str, path: str) -> List[str]:
    """Validate ContextFile entity (.claude/context/).

    Requirements:
    - YAML frontmatter required with 'references:' list
    - Path must start with .claude/context/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path)
    errors.extend(path_errors)

    # Path must start with .claude/context/
    if not path.startswith(".claude/context/"):
        errors.append("Path must start with .claude/context/")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (REQUIRED)
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Must have 'references' field as a list
    if "references" not in frontmatter:
        errors.append("Frontmatter must include 'references' field")
    elif not isinstance(frontmatter.get("references"), list):
        errors.append("'references' field must be a list")

    # Validate remaining content is not empty
    if not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    return errors


def validate_progress_template(content: str, path: str) -> List[str]:
    """Validate ProgressTemplate entity (.claude/progress/).

    Requirements:
    - Must be valid YAML+Markdown hybrid
    - YAML frontmatter with 'type: progress' field
    - Path must start with .claude/progress/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path)
    errors.extend(path_errors)

    # Path must start with .claude/progress/
    if not path.startswith(".claude/progress/"):
        errors.append("Path must start with .claude/progress/")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (REQUIRED)
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Must have 'type: progress' field
    if "type" not in frontmatter:
        errors.append("Frontmatter must include 'type' field")
    elif frontmatter.get("type") != "progress":
        errors.append("Frontmatter 'type' field must be 'progress'")

    # Validate remaining content is not empty
    if not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    return errors


def validate_context_entity(entity_type: str, content: str, path: str) -> List[str]:
    """Unified validation function for all context entity types.

    Args:
        entity_type: Type of entity ("project_config", "spec_file", "rule_file",
                     "context_file", "progress_template")
        content: File content to validate
        path: File path (for path validation and type checking)

    Returns:
        List of error messages (empty if valid)

    Raises:
        ValueError: If entity_type is not recognized
    """
    validators = {
        "project_config": validate_project_config,
        "spec_file": validate_spec_file,
        "rule_file": validate_rule_file,
        "context_file": validate_context_file,
        "progress_template": validate_progress_template,
    }

    validator = validators.get(entity_type)
    if validator is None:
        raise ValueError(
            f"Unknown entity type: {entity_type}. "
            f"Must be one of: {', '.join(validators.keys())}"
        )

    return validator(content, path)
