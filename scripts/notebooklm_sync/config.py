"""Configuration constants for NotebookLM sync scripts."""

from pathlib import Path

# Root-level .md files to include (by exact filename, not all root *.md)
ROOT_INCLUDE_FILES = ["README.md", "CHANGELOG.md"]

# Directories to include recursively (all .md files within each dir)
INCLUDE_DIRS = [
    "docs/project_plans/PRDs",
    "docs/project_plans/SPIKEs",
    "docs/project_plans/design-specs",
    "docs/dev",
    ".claude/progress/quick-features",
]

# Fine-grained exclusion patterns applied on top of INCLUDE_DIRS (glob patterns relative to project root)
EXCLUDE_PATTERNS: list[str] = []

# Mapping file location
MAPPING_PATH = Path.home() / ".notebooklm" / "skillmeat-sources.json"

# Default notebook settings
DEFAULT_NOTEBOOK_TITLE = "SkillMeat"
