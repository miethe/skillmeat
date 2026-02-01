"""Configuration constants for NotebookLM sync scripts."""

from pathlib import Path

# File patterns to track
ROOT_PATTERNS = ["*.md"]
DOCS_PATTERNS = ["docs/**/*.md"]

# Exclude most of project_plans except specific subdirectories we want to track
EXCLUDE_PATTERNS = [
    "docs/project_plans/**",
]

# Include patterns override exclusions for specific directories
INCLUDE_PATTERNS = [
    "docs/project_plans/PRDs/**/*.md",
    "docs/project_plans/reports/**/*.md",
    "docs/project_plans/SPIKEs/**/*.md",
    "docs/project_plans/design-specs/**/*.md",
    "docs/project_plans/ideas/**/*.md",
]

# Mapping file location
MAPPING_PATH = Path.home() / ".notebooklm" / "skillmeat-sources.json"

# Default notebook settings
DEFAULT_NOTEBOOK_TITLE = "SkillMeat"
