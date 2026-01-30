"""View NotebookLM sync status and manage tracked files.

Displays notebook information, lists tracked sources, and identifies untracked
or orphaned files.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import MAPPING_PATH
from .utils import get_notebook_id, get_target_files, is_in_scope, load_mapping


def format_relative_time(iso_timestamp: str) -> str:
    """Format ISO timestamp as relative time (e.g., '2h ago', '1d ago').

    Args:
        iso_timestamp: ISO format timestamp string

    Returns:
        Human-readable relative time string
    """
    try:
        parsed = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(parsed.tzinfo)
        delta = now - parsed

        # Calculate relative time
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except (ValueError, AttributeError):
        return "unknown"


def get_status_summary(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Generate sync status summary.

    Args:
        mapping: Loaded mapping dictionary

    Returns:
        Dictionary with status information
    """
    if not mapping:
        return {
            "initialized": False,
            "notebook_id": None,
            "notebook_title": None,
            "created_at": None,
            "sources_tracked": 0,
            "files_in_scope": 0,
            "files_tracked": 0,
            "files_untracked": 0,
            "files_orphaned": 0,
        }

    sources = mapping.get("sources", {})
    tracked_files = set(sources.keys())
    in_scope_files = set(str(f) for f in get_target_files())
    orphaned = tracked_files - in_scope_files
    untracked = in_scope_files - tracked_files

    return {
        "initialized": True,
        "notebook_id": mapping.get("notebook_id"),
        "notebook_title": mapping.get("notebook_title"),
        "created_at": mapping.get("created_at"),
        "sources_tracked": len(tracked_files),
        "files_in_scope": len(in_scope_files),
        "files_tracked": len(tracked_files),
        "files_untracked": len(untracked),
        "files_orphaned": len(orphaned),
    }


def print_status_summary(mapping: Dict[str, Any]) -> None:
    """Print sync status summary to stdout.

    Args:
        mapping: Loaded mapping dictionary
    """
    status = get_status_summary(mapping)

    if not status["initialized"]:
        print("NotebookLM Sync Status")
        print("=" * 22)
        print("\nNot initialized. Run init.py to set up sync.")
        return

    print("NotebookLM Sync Status")
    print("=" * 22)
    print(f"Notebook: {status['notebook_title']} ({status['notebook_id'][:8]}...)")
    print(f"Created: {status['created_at']}")
    print()
    print(f"Sources: {status['sources_tracked']} tracked")

    # Count files by category (root vs docs/)
    sources = mapping.get("sources", {})
    root_count = sum(1 for f in sources.keys() if "/" not in f)
    docs_count = len(sources) - root_count

    if root_count > 0:
        print(f"  - Root markdown: {root_count}")
    if docs_count > 0:
        print(f"  - docs/: {docs_count}")

    print()
    print(f"Files in scope: {status['files_in_scope']}")
    print(f"  - Tracked: {status['files_tracked']}")
    if status['files_untracked'] > 0:
        print(f"  - Untracked: {status['files_untracked']}")
    if status['files_orphaned'] > 0:
        print(f"  - Orphaned: {status['files_orphaned']}")

    print()
    print("Use --list, --untracked, or --orphaned for details.")


def print_tracked_files(mapping: Dict[str, Any]) -> None:
    """Print all tracked files with sync timestamps.

    Args:
        mapping: Loaded mapping dictionary
    """
    sources = mapping.get("sources", {})

    if not sources:
        print("No tracked sources.")
        return

    print("Tracked Sources ({})".format(len(sources)))
    print("-" * 60)

    for filepath in sorted(sources.keys()):
        source_info = sources[filepath]
        last_synced = source_info.get("last_synced", "unknown")
        relative_time = format_relative_time(last_synced)

        # Format: "path/to/file.md   synced 2h ago"
        print(f"{filepath:<40} synced {relative_time}")


def print_untracked_files(mapping: Dict[str, Any]) -> None:
    """Print files in scope but not tracked.

    Args:
        mapping: Loaded mapping dictionary
    """
    sources = mapping.get("sources", {})
    tracked_files = set(sources.keys())
    in_scope_files = set(str(f) for f in get_target_files())
    untracked = sorted(in_scope_files - tracked_files)

    if not untracked:
        print("No untracked files.")
        return

    print("Untracked Files ({})".format(len(untracked)))
    print("-" * 60)

    for filepath in untracked:
        print(filepath)


def print_orphaned_files(mapping: Dict[str, Any]) -> None:
    """Print tracked files that have been deleted locally.

    Args:
        mapping: Loaded mapping dictionary
    """
    sources = mapping.get("sources", {})
    tracked_files = set(sources.keys())
    in_scope_files = set(str(f) for f in get_target_files())
    orphaned = sorted(tracked_files - in_scope_files)

    if not orphaned:
        print("No orphaned sources.")
        return

    print("Orphaned Sources ({})".format(len(orphaned)))
    print("-" * 60)

    for filepath in orphaned:
        source_info = sources[filepath]
        source_id = source_info.get("source_id", "unknown")
        print(f"{filepath} (source_id: {source_id})")


def output_json(mapping: Dict[str, Any], output_type: str) -> None:
    """Output status as JSON.

    Args:
        mapping: Loaded mapping dictionary
        output_type: Type of output ('summary', 'tracked', 'untracked', 'orphaned')
    """
    sources = mapping.get("sources", {})
    tracked_files = set(sources.keys())
    in_scope_files = set(str(f) for f in get_target_files())
    untracked = in_scope_files - tracked_files
    orphaned = tracked_files - in_scope_files

    if output_type == "summary":
        status = get_status_summary(mapping)
        print(json.dumps(status, indent=2))
    elif output_type == "tracked":
        output = {
            "type": "tracked",
            "count": len(tracked_files),
            "files": {
                filepath: {
                    "source_id": sources[filepath].get("source_id"),
                    "added_at": sources[filepath].get("added_at"),
                    "last_synced": sources[filepath].get("last_synced"),
                }
                for filepath in sorted(tracked_files)
            },
        }
        print(json.dumps(output, indent=2))
    elif output_type == "untracked":
        output = {
            "type": "untracked",
            "count": len(untracked),
            "files": sorted(untracked),
        }
        print(json.dumps(output, indent=2))
    elif output_type == "orphaned":
        output = {
            "type": "orphaned",
            "count": len(orphaned),
            "files": {
                filepath: sources[filepath].get("source_id")
                for filepath in sorted(orphaned)
            },
        }
        print(json.dumps(output, indent=2))


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="View NotebookLM sync status and manage tracked files."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all tracked files",
    )
    parser.add_argument(
        "--untracked",
        action="store_true",
        help="Show files in scope but not tracked",
    )
    parser.add_argument(
        "--orphaned",
        action="store_true",
        help="Show tracked files that have been deleted locally",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    # Load mapping
    mapping = load_mapping()

    # Determine output type and print accordingly
    if args.list:
        output_type = "tracked"
        if args.json:
            output_json(mapping, output_type)
        else:
            print_tracked_files(mapping)
    elif args.untracked:
        output_type = "untracked"
        if args.json:
            output_json(mapping, output_type)
        else:
            print_untracked_files(mapping)
    elif args.orphaned:
        output_type = "orphaned"
        if args.json:
            output_json(mapping, output_type)
        else:
            print_orphaned_files(mapping)
    else:
        # Default: summary
        if args.json:
            output_json(mapping, "summary")
        else:
            print_status_summary(mapping)

    return 0


if __name__ == "__main__":
    sys.exit(main())
