#!/usr/bin/env python3
"""Initialize NotebookLM notebook with SkillMeat documentation.

One-time setup that creates a NotebookLM notebook and uploads all target
documentation files.

Usage:
    python scripts/notebooklm_sync/init.py                          # Basic usage
    python scripts/notebooklm_sync/init.py --notebook-title "Foo"   # Custom title
    python scripts/notebooklm_sync/init.py --dry-run                # Show what would be done
    python scripts/notebooklm_sync/init.py --force                  # Reinitialize
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from scripts.notebooklm_sync.config import DEFAULT_NOTEBOOK_TITLE, MAPPING_PATH
from scripts.notebooklm_sync.utils import (
    get_notebook_id,
    get_target_files,
    load_mapping,
    run_notebooklm_cmd,
    save_mapping,
)


def check_existing_initialization() -> bool:
    """Check if notebook is already initialized.

    Returns:
        True if initialized (mapping file exists with notebook_id), False otherwise.
    """
    mapping = load_mapping()
    return bool(mapping.get("notebook_id"))


def verify_authentication() -> bool:
    """Verify user is authenticated with NotebookLM.

    Returns:
        True if authenticated, False otherwise.
    """
    returncode, _ = run_notebooklm_cmd(["auth", "check"])
    return returncode == 0


def create_notebook(title: str, dry_run: bool = False) -> str | None:
    """Create a new NotebookLM notebook.

    Args:
        title: Notebook title
        dry_run: If True, simulate without creating

    Returns:
        Notebook ID string, or None on failure.
    """
    if dry_run:
        print(f"[DRY RUN] Would create notebook: '{title}'")
        return "dry-run-notebook-id"

    print(f"Creating notebook: '{title}'...")
    returncode, output = run_notebooklm_cmd(["create", title, "--json"], capture_json=True)

    if returncode != 0 or not output:
        print(f"Error: Failed to create notebook")
        return None

    # Handle both response formats: {"id": "..."} or {"notebook": {"id": "..."}}
    notebook_id = output.get("id") or output.get("notebook", {}).get("id")
    if not notebook_id:
        print(f"Error: No notebook ID in response: {output}")
        return None

    print(f"Created notebook: {notebook_id}")
    return notebook_id


def set_active_notebook(notebook_id: str, dry_run: bool = False) -> bool:
    """Set the active notebook.

    Args:
        notebook_id: Notebook ID to activate
        dry_run: If True, simulate without setting

    Returns:
        True on success, False on failure.
    """
    if dry_run:
        print(f"[DRY RUN] Would set active notebook: {notebook_id}")
        return True

    print(f"Setting active notebook: {notebook_id}...")
    returncode, _ = run_notebooklm_cmd(["use", notebook_id])

    if returncode != 0:
        print(f"Error: Failed to set active notebook")
        return False

    return True


def upload_file(filepath: Path, dry_run: bool = False) -> str | None:
    """Upload a file to the active notebook.

    Args:
        filepath: Path to file to upload
        dry_run: If True, simulate without uploading

    Returns:
        Source ID string, or None on failure.
    """
    if dry_run:
        return f"dry-run-source-{filepath.name}"

    returncode, output = run_notebooklm_cmd(
        ["source", "add", str(filepath), "--json"],
        capture_json=True,
    )

    if returncode != 0 or not output:
        return None

    # Handle both response formats: {"id": "..."} or {"source": {"id": "..."}}
    source_id = output.get("id") or output.get("source", {}).get("id")
    return source_id


def delete_existing_notebook(notebook_id: str, dry_run: bool = False) -> bool:
    """Delete an existing notebook.

    Args:
        notebook_id: Notebook ID to delete
        dry_run: If True, simulate without deleting

    Returns:
        True on success, False on failure.
    """
    if dry_run:
        print(f"[DRY RUN] Would delete notebook: {notebook_id}")
        return True

    print(f"Deleting existing notebook: {notebook_id}...")
    returncode, _ = run_notebooklm_cmd(["delete", notebook_id, "--force"])

    if returncode != 0:
        print(f"Warning: Failed to delete existing notebook (may not exist)")
        return False

    return True


def init_notebook(
    title: str = DEFAULT_NOTEBOOK_TITLE,
    dry_run: bool = False,
    force: bool = False,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    notebook_id: str | None = None,
    verbose: bool = False,
) -> int:
    """Initialize NotebookLM notebook with documentation.

    Args:
        title: Notebook title
        dry_run: If True, show what would be done without executing
        force: If True, reinitialize even if already initialized
        include_patterns: Additional glob patterns to include
        exclude_patterns: Additional glob patterns to exclude
        notebook_id: Use existing notebook instead of creating new one
        verbose: Enable verbose output

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Check if already initialized
    if check_existing_initialization():
        if not force and not notebook_id:
            print(f"Error: Notebook already initialized.")
            print(f"  Mapping file: {MAPPING_PATH}")
            print(f"  Notebook ID: {get_notebook_id()}")
            print()
            print("Use --force to reinitialize (will delete existing notebook).")
            return 1

        # Force reinitialize - delete existing
        if force:
            existing_id = get_notebook_id()
            if existing_id:
                delete_existing_notebook(existing_id, dry_run=dry_run)

    # Verify authentication
    if not dry_run and not verify_authentication():
        print("Error: Not authenticated with NotebookLM.")
        print()
        print("Run: notebooklm auth login")
        return 1

    # Use existing notebook or create new one
    if notebook_id:
        if verbose:
            print(f"Using existing notebook: {notebook_id}")
    else:
        # Create notebook
        notebook_id = create_notebook(title, dry_run=dry_run)
        if not notebook_id:
            return 1

    # Set as active
    if not set_active_notebook(notebook_id, dry_run=dry_run):
        return 1

    # Discover target files
    print()
    print("Discovering documentation files...")
    if verbose and (include_patterns or exclude_patterns):
        print(f"  Include patterns: {include_patterns or 'default'}")
        print(f"  Exclude patterns: {exclude_patterns or 'default'}")
    target_files = get_target_files(
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    print(f"Found {len(target_files)} files to upload")

    # Upload files
    print()
    print("Uploading files...")
    sources: Dict[str, Dict] = {}
    failed: List[Path] = []
    current_time = datetime.now(timezone.utc).isoformat()

    for i, filepath in enumerate(target_files, 1):
        if verbose:
            print(f"  [{i}/{len(target_files)}] {filepath}...", end=" ")
        else:
            print(f"  [{i}/{len(target_files)}] {filepath.name}...", end=" ")

        source_id = upload_file(filepath, dry_run=dry_run)

        if source_id:
            print("OK")
            if verbose:
                print(f"    Source ID: {source_id}")
            sources[str(filepath)] = {
                "source_id": source_id,
                "title": filepath.name,
                "added_at": current_time,
                "last_synced": current_time,
            }
        else:
            print("FAILED")
            failed.append(filepath)

    # Build and save mapping
    if not dry_run:
        mapping = {
            "notebook_id": notebook_id,
            "notebook_title": title,
            "created_at": current_time,
            "sources": sources,
        }
        save_mapping(mapping)

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Notebook ID: {notebook_id}")
    print(f"Notebook Title: {title}")
    print(f"Total files found: {len(target_files)}")
    print(f"Successfully uploaded: {len(sources)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print()
        print("Failed files:")
        for filepath in failed:
            print(f"  - {filepath}")

    if not dry_run:
        print()
        print(f"Mapping saved to: {MAPPING_PATH}")

    if dry_run:
        print()
        print("[DRY RUN] No changes were made.")

    return 1 if failed else 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize NotebookLM notebook with SkillMeat documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Basic usage
  %(prog)s --notebook-title "Foo"   # Custom title
  %(prog)s --dry-run                # Show what would be done
  %(prog)s --force                  # Reinitialize (delete existing)
  %(prog)s --include "docs/project_plans/PRDs/**" --include "docs/archive/*.md"
  %(prog)s --exclude "docs/user/beta/**"
  %(prog)s --notebook-id abc123     # Use existing notebook
  %(prog)s --verbose                # Detailed output
        """,
    )
    parser.add_argument(
        "--notebook-title",
        default=DEFAULT_NOTEBOOK_TITLE,
        help=f"Notebook title (default: {DEFAULT_NOTEBOOK_TITLE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reinitialize even if already initialized (deletes existing notebook)",
    )
    parser.add_argument(
        "--include",
        action="append",
        metavar="PATTERN",
        help="Add glob pattern to include (repeatable, added to defaults)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help="Add glob pattern to exclude (repeatable)",
    )
    parser.add_argument(
        "--notebook-id",
        metavar="ID",
        help="Use existing notebook instead of creating new one",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="More detailed output during upload",
    )

    args = parser.parse_args()

    return init_notebook(
        title=args.notebook_title,
        dry_run=args.dry_run,
        force=args.force,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        notebook_id=args.notebook_id,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
