"""Template fixtures for database seeding.

This module provides predefined templates that can be used to seed the database
with structured .claude/ context files and documentation patterns.

Template Types:
  - fullstack-fastapi-nextjs: FastAPI + Next.js full-stack application
  - python-cli: Python command-line application using Click
  - minimal: Bare minimum template with core directives only

Usage:
  from skillmeat.data.fixtures.templates import load_template

  template = load_template('fullstack-fastapi-nextjs')
  # template.entities -> List of context entities to deploy
"""

import json
from pathlib import Path
from typing import Any, Optional

__all__ = ["load_template", "list_templates", "Template"]


class Template:
    """Represents a template fixture with metadata and entities."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize template from fixture data.

        Args:
            data: Dictionary loaded from JSON fixture file
        """
        self.metadata = data.get("template", {})
        self.entities = data.get("entities", [])

    @property
    def name(self) -> str:
        """Template name."""
        return self.metadata.get("name", "Unknown")

    @property
    def description(self) -> str:
        """Template description."""
        return self.metadata.get("description", "")

    @property
    def version(self) -> str:
        """Template version."""
        return self.metadata.get("version", "1.0.0")

    def to_dict(self) -> dict[str, Any]:
        """Convert template to dictionary representation.

        Returns:
            Dictionary with metadata and entities
        """
        return {
            "template": self.metadata,
            "entities": self.entities,
        }


def get_fixtures_dir() -> Path:
    """Get the fixtures directory path.

    Returns:
        Path to the templates fixtures directory
    """
    return Path(__file__).parent


def load_template(template_name: str) -> Optional[Template]:
    """Load a template fixture by name.

    Args:
        template_name: Name of the template (without .json extension)
                      e.g., 'fullstack-fastapi-nextjs', 'python-cli', 'minimal'

    Returns:
        Template object if found, None otherwise

    Raises:
        json.JSONDecodeError: If fixture file is invalid JSON
        IOError: If fixture file cannot be read
    """
    fixture_path = get_fixtures_dir() / f"{template_name}.json"

    if not fixture_path.exists():
        return None

    try:
        with open(fixture_path, "r") as f:
            data = json.load(f)
        return Template(data)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in template fixture {template_name}",
            e.doc,
            e.pos,
        ) from e
    except IOError as e:
        raise IOError(f"Cannot read template fixture {template_name}") from e


def list_templates() -> list[str]:
    """List all available template names.

    Returns:
        List of template names (without .json extension)
    """
    fixtures_dir = get_fixtures_dir()
    templates = []

    for fixture_file in fixtures_dir.glob("*.json"):
        template_name = fixture_file.stem
        templates.append(template_name)

    return sorted(templates)


def get_template_info(template_name: str) -> Optional[dict[str, str]]:
    """Get metadata for a template without loading all entities.

    Args:
        template_name: Name of the template

    Returns:
        Dictionary with name and description, or None if not found
    """
    template = load_template(template_name)
    if not template:
        return None

    return {
        "name": template.name,
        "description": template.description,
        "version": template.version,
    }
