#!/usr/bin/env python3
"""Repair corrupted origin_source values in collection.toml files.

This script fixes origin_source fields that contain full URLs instead of
platform types (github, gitlab, bitbucket).

Example:
    # Preview changes without modifying
    python scripts/repair_origin_source.py --dry-run

    # Apply fixes to default collection
    python scripts/repair_origin_source.py

    # Apply fixes to custom path
    python scripts/repair_origin_source.py /path/to/collection.toml
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

# Python 3.9+ compatibility for tomllib
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

# Platform detection patterns
PLATFORM_PATTERNS = {
    "https://github.com": "github",
    "http://github.com": "github",
    "https://gitlab.com": "gitlab",
    "http://gitlab.com": "gitlab",
    "https://bitbucket.org": "bitbucket",
    "http://bitbucket.org": "bitbucket",
}

# Valid platform types
VALID_PLATFORMS = {"github", "gitlab", "bitbucket", "local", "marketplace"}


def get_default_collection_path() -> Path:
    """Get the default collection.toml path."""
    return Path.home() / ".skillmeat" / "collections" / "default" / "collection.toml"


def detect_platform_from_url(url: str) -> str | None:
    """Detect platform type from a URL.

    Args:
        url: The URL to analyze

    Returns:
        Platform type string or None if not recognized
    """
    url_lower = url.lower()
    for pattern, platform in PLATFORM_PATTERNS.items():
        if url_lower.startswith(pattern):
            return platform
    return None


def is_valid_origin_source(value: str) -> bool:
    """Check if origin_source value is valid (not a URL).

    Args:
        value: The origin_source value to check

    Returns:
        True if valid (platform type), False if invalid (URL)
    """
    return value.lower() in VALID_PLATFORMS


def repair_collection(
    toml_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Repair origin_source values in a collection.toml file.

    Args:
        toml_path: Path to the collection.toml file
        dry_run: If True, don't modify the file, just report changes

    Returns:
        Dictionary with repair results:
            - total_artifacts: Total number of artifacts
            - checked: Number of artifacts with origin_source
            - corrupted: Number of corrupted origin_source values
            - fixed: List of (artifact_name, old_value, new_value) tuples
            - errors: List of (artifact_name, old_value, error_message) tuples
    """
    results = {
        "total_artifacts": 0,
        "checked": 0,
        "corrupted": 0,
        "fixed": [],
        "errors": [],
    }

    # Read the TOML file
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    artifacts = data.get("artifacts", [])
    results["total_artifacts"] = len(artifacts)

    for artifact in artifacts:
        origin_source = artifact.get("origin_source")
        artifact_name = artifact.get("name", "<unnamed>")

        if origin_source is None:
            continue

        results["checked"] += 1

        # Check if it's a valid platform type
        if is_valid_origin_source(origin_source):
            continue

        # It's corrupted (likely a URL)
        results["corrupted"] += 1

        # Try to detect the correct platform
        platform = detect_platform_from_url(origin_source)

        if platform:
            results["fixed"].append((artifact_name, origin_source, platform))
            artifact["origin_source"] = platform
        else:
            results["errors"].append(
                (artifact_name, origin_source, "Could not determine platform from URL")
            )

    # Write the repaired file if not dry run and changes were made
    if not dry_run and results["fixed"]:
        # Create backup
        backup_path = toml_path.with_suffix(".toml.bak")
        shutil.copy2(toml_path, backup_path)
        print(f"Created backup: {backup_path}")

        # Write repaired file
        with open(toml_path, "wb") as f:
            tomli_w.dump(data, f)

    return results


def print_results(results: dict[str, Any], dry_run: bool) -> None:
    """Print the repair results in a readable format."""
    print("\n" + "=" * 60)
    print("REPAIR RESULTS" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 60)

    print(f"\nTotal artifacts: {results['total_artifacts']}")
    print(f"Artifacts with origin_source: {results['checked']}")
    print(f"Corrupted values found: {results['corrupted']}")

    if results["fixed"]:
        print(f"\n{'Fixed' if not dry_run else 'Would fix'}: {len(results['fixed'])}")
        print("-" * 60)
        for name, old_value, new_value in results["fixed"]:
            print(f"\n  Artifact: {name}")
            print(f"    Old: {old_value[:80]}{'...' if len(old_value) > 80 else ''}")
            print(f"    New: {new_value}")

    if results["errors"]:
        print(f"\nErrors (could not repair): {len(results['errors'])}")
        print("-" * 60)
        for name, old_value, error in results["errors"]:
            print(f"\n  Artifact: {name}")
            print(f"    Value: {old_value[:80]}{'...' if len(old_value) > 80 else ''}")
            print(f"    Error: {error}")

    if not results["fixed"] and not results["errors"]:
        print("\nNo corrupted origin_source values found.")

    print("\n" + "=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Repair corrupted origin_source values in collection.toml files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/repair_origin_source.py --dry-run    # Preview changes
  python scripts/repair_origin_source.py              # Apply fixes
  python scripts/repair_origin_source.py /custom/path/collection.toml
        """,
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=None,
        help="Path to collection.toml (default: ~/.skillmeat/collections/default/collection.toml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the file",
    )

    args = parser.parse_args()

    # Determine the path
    toml_path = args.path if args.path else get_default_collection_path()

    # Validate the path
    if not toml_path.exists():
        print(f"Error: File not found: {toml_path}", file=sys.stderr)
        return 1

    if not toml_path.is_file():
        print(f"Error: Not a file: {toml_path}", file=sys.stderr)
        return 1

    print(f"Processing: {toml_path}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")

    try:
        results = repair_collection(toml_path, dry_run=args.dry_run)
        print_results(results, args.dry_run)

        # Return appropriate exit code
        if results["errors"]:
            return 2  # Partial success (some errors)
        return 0

    except tomllib.TOMLDecodeError as e:
        print(f"Error: Invalid TOML file: {e}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"Error: Permission denied: {toml_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
