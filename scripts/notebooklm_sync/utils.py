"""Shared utilities for NotebookLM sync scripts.

Provides functions to manage notebook mappings, discover target files,
and execute notebooklm CLI commands.
"""

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .config import DEFAULT_NOTEBOOK_TITLE, EXCLUDE_PATTERNS, MAPPING_PATH


def load_mapping(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the notebook ID mapping from disk.

    Args:
        path: Path to mapping file. Defaults to ~/.notebooklm/skillmeat-sources.json

    Returns:
        Dictionary containing notebook metadata. Empty dict if file doesn't exist.
    """
    target_path = path or MAPPING_PATH

    if not target_path.exists():
        return {}

    try:
        with open(target_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load mapping from {target_path}: {e}")
        return {}


def save_mapping(data: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Atomically save the notebook ID mapping to disk.

    Creates parent directory if needed. Uses atomic write (write to temp, then rename)
    to prevent corruption.

    Args:
        data: Dictionary to save
        path: Path to mapping file. Defaults to ~/.notebooklm/skillmeat-sources.json
    """
    target_path = path or MAPPING_PATH

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file first, then rename
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        dir=target_path.parent,
        delete=False,
    ) as tmp_file:
        json.dump(data, tmp_file, indent=2)
        tmp_path = Path(tmp_file.name)

    try:
        tmp_path.replace(target_path)
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to save mapping to {target_path}: {e}")


def get_target_files(
    base_dir: Path = Path("."),
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[Path]:
    """Discover all markdown files in scope for NotebookLM sync.

    Default scope:
    - Root-level .md files (not in subdirectories)
    - Files under docs/ (recursively, excluding docs/project_plans/)

    Args:
        base_dir: Base directory to search from. Defaults to current directory.
        include_patterns: Additional glob patterns to include (e.g., ["docs/project_plans/PRDs/**/*.md"]).
                         Patterns are relative to base_dir and support ** for recursive matching.
        exclude_patterns: Glob patterns to exclude (e.g., ["docs/user/beta/**"]).
                         Applied AFTER includes. Patterns are relative to base_dir.

    Returns:
        Sorted list of relative paths to markdown files.

    Examples:
        # Default scope
        >>> files = get_target_files()

        # Include project_plans PRDs too
        >>> files = get_target_files(include_patterns=["docs/project_plans/PRDs/**/*.md"])

        # Exclude beta docs
        >>> files = get_target_files(exclude_patterns=["docs/user/beta/**"])
    """
    base_dir = Path(base_dir).resolve()
    target_files: List[Path] = []

    # Find root-level .md files
    for md_file in base_dir.glob("*.md"):
        if md_file.is_file():
            target_files.append(md_file.relative_to(base_dir))

    # Find docs/**/*.md files (recursively)
    docs_dir = base_dir / "docs"
    if docs_dir.exists():
        for md_file in docs_dir.rglob("*.md"):
            if md_file.is_file():
                relative_path = md_file.relative_to(base_dir)

                # Check if it matches any default exclude pattern
                excluded = False
                for pattern in EXCLUDE_PATTERNS:
                    # Convert glob pattern to path check
                    pattern_prefix = pattern.rstrip("/**").rstrip("/*").rstrip("*")
                    if str(relative_path).startswith(pattern_prefix):
                        excluded = True
                        break

                if not excluded:
                    target_files.append(relative_path)

    # Add files matching include_patterns
    if include_patterns:
        for pattern in include_patterns:
            # Use glob or rglob depending on whether pattern contains **
            if "**" in pattern:
                # For recursive patterns, extract the base directory and use rglob
                pattern_parts = pattern.split("**", 1)
                base_pattern = pattern_parts[0].rstrip("/")
                suffix_pattern = pattern_parts[1].lstrip("/")

                search_base = base_dir / base_pattern if base_pattern else base_dir

                if search_base.exists():
                    for match in search_base.rglob(suffix_pattern):
                        if match.is_file():
                            relative_path = match.relative_to(base_dir)
                            if relative_path not in target_files:
                                target_files.append(relative_path)
            else:
                # Non-recursive pattern
                for match in base_dir.glob(pattern):
                    if match.is_file():
                        relative_path = match.relative_to(base_dir)
                        if relative_path not in target_files:
                            target_files.append(relative_path)

    # Apply exclude_patterns
    if exclude_patterns:
        filtered_files = []
        for filepath in target_files:
            excluded = False
            for pattern in exclude_patterns:
                # Use match() for glob-style pattern matching
                if filepath.match(pattern):
                    excluded = True
                    break

            if not excluded:
                filtered_files.append(filepath)

        target_files = filtered_files

    return sorted(target_files)


def is_in_scope(filepath: Union[str, Path]) -> bool:
    """Check if a file is in scope for NotebookLM sync.

    A file is in scope if:
    - It's a root-level .md file (not in subdirectories)
    - It's under docs/ (but not docs/project_plans/)

    Args:
        filepath: Path to check (relative or absolute)

    Returns:
        True if file is in scope, False otherwise.
    """
    path = Path(filepath)
    parts = path.parts

    # Check if it's a root-level .md file
    if len(parts) == 1 and path.suffix == ".md":
        return True

    # Check if it's under docs/ but not docs/project_plans/
    if len(parts) >= 2 and parts[0] == "docs":
        # Excluded if under project_plans
        if len(parts) >= 2 and parts[1] == "project_plans":
            return False
        return True

    return False


def run_notebooklm_cmd(
    args: List[str],
    capture_json: bool = False,
) -> Tuple[int, Union[str, Dict[str, Any]]]:
    """Execute a notebooklm CLI command.

    Args:
        args: Command arguments (without 'notebooklm' prefix)
        capture_json: If True, parse and return JSON output instead of raw string

    Returns:
        Tuple of (return_code, output_or_parsed_json).
        - return_code: Exit code from subprocess
        - output: Raw string output (if capture_json=False) or parsed dict (if True)
                 Empty string or empty dict on error.
    """
    cmd = ["notebooklm"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if capture_json:
            # Try to parse JSON output
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return result.returncode, json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse JSON output: {e}")
                    return result.returncode, {}
            return result.returncode, {}
        else:
            return result.returncode, result.stdout

    except FileNotFoundError:
        print("Error: 'notebooklm' command not found. Is it installed?")
        return 1, "" if not capture_json else {}
    except Exception as e:
        print(f"Error executing notebooklm command: {e}")
        return 1, "" if not capture_json else {}


def get_notebook_id() -> Optional[str]:
    """Get the initialized notebook ID from the mapping file.

    Returns:
        Notebook ID string, or None if not initialized.
    """
    mapping = load_mapping()
    return mapping.get("notebook_id")


def get_file_mtime(filepath: Path) -> Optional[str]:
    """Get file modification time as ISO timestamp.

    Args:
        filepath: Path to the file to check

    Returns:
        ISO 8601 formatted timestamp string (e.g., "2024-01-30T14:23:45"),
        or None if file doesn't exist.

    Examples:
        >>> mtime = get_file_mtime(Path("README.md"))
        >>> print(mtime)
        2024-01-30T14:23:45
    """
    if not filepath.exists():
        return None

    try:
        mtime_timestamp = filepath.stat().st_mtime
        mtime_dt = datetime.fromtimestamp(mtime_timestamp)
        return mtime_dt.isoformat(timespec="seconds")
    except (OSError, ValueError) as e:
        print(f"Warning: Could not get mtime for {filepath}: {e}")
        return None
