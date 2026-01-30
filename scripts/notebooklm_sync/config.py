"""Configuration constants for NotebookLM sync scripts."""

from pathlib import Path

# File patterns to track
ROOT_PATTERNS = ["*.md"]
DOCS_PATTERNS = ["docs/**/*.md"]
EXCLUDE_PATTERNS = ["docs/project_plans/**"]

# Mapping file location
MAPPING_PATH = Path.home() / ".notebooklm" / "skillmeat-sources.json"

# Default notebook settings
DEFAULT_NOTEBOOK_TITLE = "SkillMeat"
