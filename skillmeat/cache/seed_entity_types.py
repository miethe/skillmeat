"""Idempotent seeding logic for built-in entity type configurations.

This module seeds the ``entity_type_configs`` table with the five built-in
context entity types that were previously only available as hard-coded
validators in ``skillmeat/core/validators/context_entity.py`` and path
defaults in ``skillmeat/core/platform_defaults.py``.

The five types are:
    1. project_config  — CLAUDE.md files (plain markdown, optional frontmatter)
    2. spec_file       — .claude/specs/ specs (YAML frontmatter + markdown)
    3. rule_file       — .claude/rules/ rules (markdown, optional path scope)
    4. context_file    — .claude/context/ context docs (frontmatter + refs)
    5. progress_template — .claude/progress/ YAML+Markdown hybrid progress files

Usage
-----
Call ``seed_builtin_entity_types(session)`` once at application startup (after
running Alembic migrations).  It is fully idempotent: invoking it multiple
times always results in exactly five rows, never duplicates.

    >>> from skillmeat.cache.models import get_session
    >>> from skillmeat.cache.seed_entity_types import seed_builtin_entity_types
    >>> session = get_session()
    >>> try:
    ...     seed_builtin_entity_types(session)
    ... finally:
    ...     session.close()
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from skillmeat.cache.models import EntityTypeConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Built-in type definitions
# =============================================================================

#: The canonical list of built-in entity type definitions.
#: Each dict maps directly to EntityTypeConfig column values.
#:
#: Validation rule data is extracted from:
#:   - skillmeat/core/validators/context_entity.py  (required/optional keys)
#:   - skillmeat/core/platform_defaults.py           (path prefixes)
BUILTIN_ENTITY_TYPES: List[Dict[str, Any]] = [
    {
        "slug": "project_config",
        "display_name": "Project Config",
        "description": (
            "CLAUDE.md files that configure Claude Code's behaviour for a project. "
            "Markdown content is required; YAML frontmatter is optional."
        ),
        "icon": "file-text",
        "path_prefix": ".claude",
        # No required frontmatter keys — CLAUDE.md has no mandatory fields
        "required_frontmatter_keys": [],
        "optional_frontmatter_keys": [],
        "validation_rules": {
            "min_content_length": 10,
            "frontmatter_required": False,
        },
        "content_template": (
            "# Project Configuration\n\n"
            "## Overview\n\n"
            "Describe the project purpose and context here.\n\n"
            "## Development Commands\n\n"
            "<!-- Add common development commands -->\n\n"
            "## Architecture\n\n"
            "<!-- Describe the project architecture -->\n"
        ),
        "is_builtin": True,
        "sort_order": 0,
    },
    {
        "slug": "spec_file",
        "display_name": "Spec File",
        "description": (
            "Specification documents stored under .claude/specs/. "
            "YAML frontmatter is required and must include a 'title' field, "
            "followed by Markdown content."
        ),
        "icon": "book-open",
        "path_prefix": ".claude/specs",
        # title is the only required frontmatter key (see validate_spec_file)
        "required_frontmatter_keys": ["title"],
        "optional_frontmatter_keys": ["description", "version", "status", "tags"],
        "validation_rules": {
            "min_content_length": 1,
            "frontmatter_required": True,
            "path_prefix_required": True,
        },
        "content_template": (
            "---\n"
            "title: My Specification\n"
            "---\n\n"
            "## Overview\n\n"
            "Describe the specification here.\n\n"
            "## Requirements\n\n"
            "<!-- List the requirements -->\n\n"
            "## Implementation Notes\n\n"
            "<!-- Add implementation notes -->\n"
        ),
        "is_builtin": True,
        "sort_order": 1,
    },
    {
        "slug": "rule_file",
        "display_name": "Rule File",
        "description": (
            "Rule documents stored under .claude/rules/. "
            "Markdown content with an optional "
            "'<!-- Path Scope: ... -->' comment specifying the file scope."
        ),
        "icon": "shield",
        "path_prefix": ".claude/rules",
        # No mandatory frontmatter keys (path scope comment is optional)
        "required_frontmatter_keys": [],
        "optional_frontmatter_keys": [],
        "validation_rules": {
            "min_content_length": 10,
            "frontmatter_required": False,
            "path_prefix_required": True,
            "path_scope_comment_recommended": True,
        },
        "content_template": (
            "# Rule Title\n\n"
            "<!-- Path Scope: path/to/apply/rule -->\n\n"
            "## Rule Description\n\n"
            "Describe what this rule enforces.\n\n"
            "## Examples\n\n"
            "<!-- Provide examples of correct and incorrect usage -->\n"
        ),
        "is_builtin": True,
        "sort_order": 2,
    },
    {
        "slug": "context_file",
        "display_name": "Context File",
        "description": (
            "Context documents stored under .claude/context/. "
            "YAML frontmatter is required and must include a 'references' list, "
            "followed by Markdown content."
        ),
        "icon": "layers",
        "path_prefix": ".claude/context",
        # references is required (see validate_context_file)
        "required_frontmatter_keys": ["references"],
        "optional_frontmatter_keys": ["title", "description", "tags", "version"],
        "validation_rules": {
            "min_content_length": 1,
            "frontmatter_required": True,
            "path_prefix_required": True,
            "references_must_be_list": True,
        },
        "content_template": (
            "---\n"
            "references:\n"
            "  - path/to/referenced/file\n"
            "---\n\n"
            "## Context Overview\n\n"
            "Describe the context and its purpose here.\n\n"
            "## Key Concepts\n\n"
            "<!-- Explain key concepts from the referenced files -->\n"
        ),
        "is_builtin": True,
        "sort_order": 3,
    },
    {
        "slug": "progress_template",
        "display_name": "Progress Template",
        "description": (
            "YAML+Markdown hybrid progress-tracking files stored under "
            ".claude/progress/. "
            "YAML frontmatter is required and must include 'type: progress'."
        ),
        "icon": "check-square",
        "path_prefix": ".claude/progress",
        # type field required and must equal 'progress' (see validate_progress_template)
        "required_frontmatter_keys": ["type"],
        "optional_frontmatter_keys": [
            "title",
            "phase",
            "status",
            "tasks",
            "parallelization",
        ],
        "validation_rules": {
            "min_content_length": 1,
            "frontmatter_required": True,
            "path_prefix_required": True,
            "type_must_equal": "progress",
        },
        "content_template": (
            "---\n"
            "type: progress\n"
            "title: Phase N Progress\n"
            "status: in_progress\n"
            "---\n\n"
            "## Phase Overview\n\n"
            "Describe the phase goals here.\n\n"
            "## Tasks\n\n"
            "- [ ] Task 1\n"
            "- [ ] Task 2\n"
        ),
        "is_builtin": True,
        "sort_order": 4,
    },
]


# =============================================================================
# Public seeding function
# =============================================================================


def seed_builtin_entity_types(session: Session) -> int:
    """Seed the entity_type_configs table with the five built-in types.

    This function is idempotent: it uses an INSERT-if-not-exists strategy
    keyed on ``slug``.  Running it multiple times always results in exactly
    five built-in rows, never duplicates.

    Only the columns that do NOT typically change after seeding are checked for
    presence.  If a row already exists for a given slug, it is left untouched
    so that any admin edits (e.g. custom description, icon overrides) survive
    restarts.

    Args:
        session: An open SQLAlchemy ``Session``.  The caller is responsible for
                 committing or rolling back the transaction.

    Returns:
        The number of rows actually inserted (0 if all five already existed).

    Example:
        >>> from skillmeat.cache.models import get_session
        >>> from skillmeat.cache.seed_entity_types import seed_builtin_entity_types
        >>> session = get_session()
        >>> try:
        ...     inserted = seed_builtin_entity_types(session)
        ...     session.commit()
        ...     print(f"Seeded {inserted} entity type(s)")
        ... except Exception:
        ...     session.rollback()
        ...     raise
        ... finally:
        ...     session.close()
    """
    inserted = 0
    now = datetime.utcnow()

    for defn in BUILTIN_ENTITY_TYPES:
        slug = defn["slug"]

        # Check whether this slug already exists — avoids duplicate key errors
        existing = (
            session.query(EntityTypeConfig)
            .filter(EntityTypeConfig.slug == slug)
            .first()
        )

        if existing is not None:
            logger.debug(
                "seed_builtin_entity_types: slug=%r already exists (id=%r), skipping",
                slug,
                existing.id,
            )
            continue

        entity = EntityTypeConfig(
            slug=slug,
            display_name=defn["display_name"],
            description=defn.get("description"),
            icon=defn.get("icon"),
            path_prefix=defn.get("path_prefix"),
            required_frontmatter_keys=defn.get("required_frontmatter_keys"),
            optional_frontmatter_keys=defn.get("optional_frontmatter_keys"),
            validation_rules=defn.get("validation_rules"),
            content_template=defn.get("content_template"),
            is_builtin=defn.get("is_builtin", True),
            sort_order=defn.get("sort_order", 0),
            created_at=now,
            updated_at=now,
        )
        session.add(entity)
        inserted += 1
        logger.debug(
            "seed_builtin_entity_types: inserting slug=%r sort_order=%d",
            slug,
            entity.sort_order,
        )

    if inserted:
        logger.info(
            "seed_builtin_entity_types: inserted %d built-in entity type(s)",
            inserted,
        )
    else:
        logger.debug(
            "seed_builtin_entity_types: all built-in entity types already present"
        )

    return inserted
