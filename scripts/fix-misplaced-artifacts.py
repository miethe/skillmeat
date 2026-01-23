#!/usr/bin/env python3
"""Fix misplaced artifacts that were imported to the wrong collection.

Due to a bug in the import process, some artifacts were:
1. Downloaded to the active collection (e.g., "personal")
2. But database records point to "default" collection

This causes 404 errors when viewing artifact files because the API looks
in "default" but files are in "personal".

This script scans for misplaced artifacts and moves them to the correct
collection directory.

Example:
    # Preview what would be fixed (dry-run mode, default)
    python scripts/fix-misplaced-artifacts.py

    # Actually fix the artifacts
    python scripts/fix-misplaced-artifacts.py --execute

    # Verbose output
    python scripts/fix-misplaced-artifacts.py --execute --verbose
"""

import argparse
import logging
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Python 3.9+ compatibility for tomllib
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        print(
            "Error: tomli package required for Python < 3.11. "
            "Install with: pip install tomli",
            file=sys.stderr,
        )
        sys.exit(1)

try:
    import tomli_w
except ImportError:
    print(
        "Error: tomli_w package required. Install with: pip install tomli_w",
        file=sys.stderr,
    )
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Mapping from artifact type to directory name
TYPE_TO_DIR = {
    "skill": "skills",
    "command": "commands",
    "agent": "agents",
    "mcp": "mcp",
    "mcp_server": "mcp",
    "hook": "hooks",
    # Context entity types
    "project_config": "project_configs",
    "spec_file": "specs",
    "rule_file": "rules",
    "context_file": "context",
    "progress_template": "progress_templates",
}

# Default collection ID in database
DEFAULT_COLLECTION_ID = "default"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MisplacedArtifact:
    """Represents a misplaced artifact that needs to be fixed."""

    artifact_id: str
    artifact_name: str
    artifact_type: str
    db_collection_id: str  # Collection ID in database (e.g., "default")
    actual_collection: str  # Collection where files actually exist
    source_path: Path  # Current (wrong) location
    dest_path: Path  # Correct location
    manifest_entry: Optional[Dict[str, Any]] = None


@dataclass
class FixResult:
    """Result of fixing a misplaced artifact."""

    artifact_id: str
    artifact_name: str
    success: bool
    action: str  # "moved", "skipped", "error"
    message: str
    source_path: Optional[Path] = None
    dest_path: Optional[Path] = None


# =============================================================================
# Path Helpers
# =============================================================================


def get_skillmeat_root() -> Path:
    """Get the SkillMeat root directory (~/.skillmeat)."""
    return Path.home() / ".skillmeat"


def get_collections_dir() -> Path:
    """Get the collections directory."""
    return get_skillmeat_root() / "collections"


def get_db_path() -> Path:
    """Get the cache database path."""
    return get_skillmeat_root() / "cache" / "cache.db"


def get_collection_path(collection_name: str) -> Path:
    """Get path to a specific collection."""
    return get_collections_dir() / collection_name


def get_manifest_path(collection_name: str) -> Path:
    """Get path to collection.toml for a collection."""
    return get_collection_path(collection_name) / "collection.toml"


def get_artifact_dir(collection_name: str, artifact_type: str, artifact_name: str) -> Path:
    """Get the expected directory path for an artifact."""
    type_dir = TYPE_TO_DIR.get(artifact_type, f"{artifact_type}s")
    return get_collection_path(collection_name) / type_dir / artifact_name


# =============================================================================
# Database Operations
# =============================================================================


def parse_artifact_id(artifact_id: str) -> Tuple[str, str]:
    """Parse artifact_id in format 'type:name' into (type, name).

    The artifact_id in collection_artifacts table uses the format:
    - 'skill:artifact-name'
    - 'agent:agent-name'
    - 'command:command-name'
    etc.

    Args:
        artifact_id: The artifact_id string

    Returns:
        Tuple of (artifact_type, artifact_name)
    """
    if ":" in artifact_id:
        parts = artifact_id.split(":", 1)
        return parts[0], parts[1]
    else:
        # Fallback: assume it's a skill if no type prefix
        return "skill", artifact_id


def get_collection_artifacts_from_db(
    db_path: Path,
    collection_id: str = DEFAULT_COLLECTION_ID,
) -> List[Tuple[str, str, str]]:
    """Query artifacts assigned to a collection in the database.

    Args:
        db_path: Path to SQLite database
        collection_id: Collection ID to query

    Returns:
        List of (artifact_id, artifact_name, artifact_type) tuples
    """
    if not db_path.exists():
        logger.warning(f"Database not found: {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Query collection_artifacts - artifact_id format is "type:name"
        query = """
            SELECT ca.artifact_id
            FROM collection_artifacts ca
            WHERE ca.collection_id = ?
        """
        cursor.execute(query, (collection_id,))
        results = cursor.fetchall()

        # Parse artifact_id format "type:name"
        processed = []
        for (artifact_id,) in results:
            artifact_type, artifact_name = parse_artifact_id(artifact_id)
            processed.append((artifact_id, artifact_name, artifact_type))

        return processed

    finally:
        conn.close()


# =============================================================================
# Manifest Operations
# =============================================================================


def read_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Read and parse a collection.toml manifest.

    Args:
        manifest_path: Path to collection.toml

    Returns:
        Parsed TOML data as dictionary
    """
    with open(manifest_path, "rb") as f:
        return tomllib.load(f)


def write_manifest(manifest_path: Path, data: Dict[str, Any]) -> None:
    """Write data to a collection.toml manifest.

    Args:
        manifest_path: Path to collection.toml
        data: Dictionary to serialize as TOML
    """
    with open(manifest_path, "wb") as f:
        tomli_w.dump(data, f)


def backup_manifest(manifest_path: Path) -> Path:
    """Create a backup of a manifest file.

    Args:
        manifest_path: Path to collection.toml

    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = manifest_path.with_suffix(f".toml.bak.{timestamp}")
    shutil.copy2(manifest_path, backup_path)
    return backup_path


def find_artifact_in_manifest(
    manifest_data: Dict[str, Any],
    artifact_name: str,
    artifact_type: str,
) -> Optional[Dict[str, Any]]:
    """Find an artifact entry in manifest data.

    Args:
        manifest_data: Parsed manifest TOML
        artifact_name: Artifact name to find
        artifact_type: Artifact type to match

    Returns:
        Artifact entry dict if found, None otherwise
    """
    artifacts = manifest_data.get("artifacts", [])
    for artifact in artifacts:
        if artifact.get("name") == artifact_name and artifact.get("type") == artifact_type:
            return artifact
    return None


def remove_artifact_from_manifest(
    manifest_data: Dict[str, Any],
    artifact_name: str,
    artifact_type: str,
) -> bool:
    """Remove an artifact entry from manifest data (in-place).

    Args:
        manifest_data: Parsed manifest TOML (modified in-place)
        artifact_name: Artifact name to remove
        artifact_type: Artifact type to match

    Returns:
        True if removed, False if not found
    """
    artifacts = manifest_data.get("artifacts", [])
    for i, artifact in enumerate(artifacts):
        if artifact.get("name") == artifact_name and artifact.get("type") == artifact_type:
            artifacts.pop(i)
            manifest_data["updated"] = datetime.utcnow().isoformat()
            return True
    return False


def add_artifact_to_manifest(
    manifest_data: Dict[str, Any],
    artifact_entry: Dict[str, Any],
) -> None:
    """Add an artifact entry to manifest data (in-place).

    Args:
        manifest_data: Parsed manifest TOML (modified in-place)
        artifact_entry: Artifact entry to add
    """
    if "artifacts" not in manifest_data:
        manifest_data["artifacts"] = []
    manifest_data["artifacts"].append(artifact_entry)
    manifest_data["updated"] = datetime.utcnow().isoformat()


# =============================================================================
# Artifact Discovery
# =============================================================================


def find_misplaced_artifacts(
    db_path: Path,
    target_collection: str = DEFAULT_COLLECTION_ID,
    verbose: bool = False,
) -> List[MisplacedArtifact]:
    """Find artifacts that are in the database but files are in wrong collection.

    Args:
        db_path: Path to SQLite database
        target_collection: The collection ID to check (where DB says artifacts should be)
        verbose: Enable verbose logging

    Returns:
        List of MisplacedArtifact objects
    """
    misplaced = []

    # Get artifacts from database for the target collection
    db_artifacts = get_collection_artifacts_from_db(db_path, target_collection)
    if verbose:
        logger.info(f"Found {len(db_artifacts)} artifacts in database for collection '{target_collection}'")

    # Get list of all collections on disk
    collections_dir = get_collections_dir()
    if not collections_dir.exists():
        logger.warning(f"Collections directory not found: {collections_dir}")
        return []

    all_collections = [
        d.name for d in collections_dir.iterdir()
        if d.is_dir() and (d / "collection.toml").exists()
    ]
    if verbose:
        logger.info(f"Found collections on disk: {all_collections}")

    # Check each artifact
    for artifact_id, artifact_name, artifact_type in db_artifacts:
        expected_path = get_artifact_dir(target_collection, artifact_type, artifact_name)

        if expected_path.exists():
            # Artifact is in the correct place
            if verbose:
                logger.debug(f"OK: {artifact_name} ({artifact_type}) in correct location")
            continue

        # Search for the artifact in other collections
        found_in = None
        found_path = None
        manifest_entry = None

        for collection_name in all_collections:
            if collection_name == target_collection:
                continue

            candidate_path = get_artifact_dir(collection_name, artifact_type, artifact_name)
            if candidate_path.exists():
                found_in = collection_name
                found_path = candidate_path

                # Try to get manifest entry from source collection
                source_manifest_path = get_manifest_path(collection_name)
                if source_manifest_path.exists():
                    try:
                        source_manifest = read_manifest(source_manifest_path)
                        manifest_entry = find_artifact_in_manifest(
                            source_manifest, artifact_name, artifact_type
                        )
                    except Exception as e:
                        if verbose:
                            logger.warning(f"Failed to read manifest from {collection_name}: {e}")

                break

        if found_in:
            misplaced.append(
                MisplacedArtifact(
                    artifact_id=artifact_id,
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    db_collection_id=target_collection,
                    actual_collection=found_in,
                    source_path=found_path,
                    dest_path=expected_path,
                    manifest_entry=manifest_entry,
                )
            )
            if verbose:
                logger.info(
                    f"MISPLACED: {artifact_name} ({artifact_type}) - "
                    f"DB says '{target_collection}', found in '{found_in}'"
                )
        else:
            if verbose:
                logger.warning(
                    f"MISSING: {artifact_name} ({artifact_type}) - "
                    f"not found in any collection"
                )

    return misplaced


# =============================================================================
# Fix Operations
# =============================================================================


def fix_misplaced_artifact(
    artifact: MisplacedArtifact,
    dry_run: bool = True,
    verbose: bool = False,
) -> FixResult:
    """Fix a single misplaced artifact by moving files and updating manifests.

    Args:
        artifact: MisplacedArtifact to fix
        dry_run: If True, only report what would be done
        verbose: Enable verbose logging

    Returns:
        FixResult with outcome details
    """
    # Check if destination already exists
    if artifact.dest_path.exists():
        return FixResult(
            artifact_id=artifact.artifact_id,
            artifact_name=artifact.artifact_name,
            success=False,
            action="skipped",
            message=f"Destination already exists: {artifact.dest_path}",
            source_path=artifact.source_path,
            dest_path=artifact.dest_path,
        )

    if dry_run:
        return FixResult(
            artifact_id=artifact.artifact_id,
            artifact_name=artifact.artifact_name,
            success=True,
            action="would_move",
            message=f"Would move from {artifact.source_path} to {artifact.dest_path}",
            source_path=artifact.source_path,
            dest_path=artifact.dest_path,
        )

    try:
        # 1. Backup source collection manifest
        source_manifest_path = get_manifest_path(artifact.actual_collection)
        if source_manifest_path.exists():
            backup_path = backup_manifest(source_manifest_path)
            if verbose:
                logger.info(f"  Backed up source manifest: {backup_path}")

        # 2. Backup destination collection manifest
        dest_manifest_path = get_manifest_path(artifact.db_collection_id)
        if dest_manifest_path.exists():
            backup_path = backup_manifest(dest_manifest_path)
            if verbose:
                logger.info(f"  Backed up destination manifest: {backup_path}")

        # 3. Create destination directory structure
        artifact.dest_path.parent.mkdir(parents=True, exist_ok=True)

        # 4. Move the artifact directory
        shutil.move(str(artifact.source_path), str(artifact.dest_path))
        if verbose:
            logger.info(f"  Moved: {artifact.source_path} -> {artifact.dest_path}")

        # 5. Update source collection manifest (remove artifact)
        if source_manifest_path.exists():
            source_manifest = read_manifest(source_manifest_path)
            removed = remove_artifact_from_manifest(
                source_manifest,
                artifact.artifact_name,
                artifact.artifact_type,
            )
            if removed:
                write_manifest(source_manifest_path, source_manifest)
                if verbose:
                    logger.info(f"  Removed from source manifest: {artifact.actual_collection}")

        # 6. Update destination collection manifest (add artifact if not present)
        if dest_manifest_path.exists():
            dest_manifest = read_manifest(dest_manifest_path)

            # Check if already in destination manifest
            existing = find_artifact_in_manifest(
                dest_manifest,
                artifact.artifact_name,
                artifact.artifact_type,
            )

            if not existing:
                # Create manifest entry for destination
                if artifact.manifest_entry:
                    # Use existing manifest entry but update path
                    new_entry = artifact.manifest_entry.copy()
                    new_entry["path"] = str(artifact.dest_path)
                else:
                    # Create minimal entry
                    new_entry = {
                        "name": artifact.artifact_name,
                        "type": artifact.artifact_type,
                        "path": str(artifact.dest_path),
                        "added": datetime.utcnow().isoformat(),
                    }

                add_artifact_to_manifest(dest_manifest, new_entry)
                write_manifest(dest_manifest_path, dest_manifest)
                if verbose:
                    logger.info(f"  Added to destination manifest: {artifact.db_collection_id}")

        return FixResult(
            artifact_id=artifact.artifact_id,
            artifact_name=artifact.artifact_name,
            success=True,
            action="moved",
            message=f"Moved to {artifact.dest_path}",
            source_path=artifact.source_path,
            dest_path=artifact.dest_path,
        )

    except PermissionError as e:
        return FixResult(
            artifact_id=artifact.artifact_id,
            artifact_name=artifact.artifact_name,
            success=False,
            action="error",
            message=f"Permission denied: {e}",
            source_path=artifact.source_path,
            dest_path=artifact.dest_path,
        )
    except Exception as e:
        return FixResult(
            artifact_id=artifact.artifact_id,
            artifact_name=artifact.artifact_name,
            success=False,
            action="error",
            message=f"Error: {e}",
            source_path=artifact.source_path,
            dest_path=artifact.dest_path,
        )


# =============================================================================
# Output Formatting
# =============================================================================


def print_summary(
    misplaced: List[MisplacedArtifact],
    results: List[FixResult],
    dry_run: bool,
) -> None:
    """Print a summary of the migration results."""
    print("\n" + "=" * 70)
    print("MISPLACED ARTIFACTS FIX" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 70)

    if not misplaced:
        print("\nNo misplaced artifacts found. All artifacts are in the correct location.")
        return

    print(f"\nFound {len(misplaced)} misplaced artifact(s):")
    print("-" * 70)

    for artifact in misplaced:
        print(f"\n  Name: {artifact.artifact_name}")
        print(f"  Type: {artifact.artifact_type}")
        print(f"  Database collection: {artifact.db_collection_id}")
        print(f"  Actual location: {artifact.actual_collection}")
        print(f"  Source: {artifact.source_path}")
        print(f"  Destination: {artifact.dest_path}")

    if results:
        print("\n" + "-" * 70)
        print("RESULTS:")
        print("-" * 70)

        moved = [r for r in results if r.action in ("moved", "would_move")]
        skipped = [r for r in results if r.action == "skipped"]
        errors = [r for r in results if r.action == "error"]

        if moved:
            verb = "Would move" if dry_run else "Moved"
            print(f"\n{verb}: {len(moved)}")
            for r in moved:
                print(f"  - {r.artifact_name}: {r.message}")

        if skipped:
            print(f"\nSkipped: {len(skipped)}")
            for r in skipped:
                print(f"  - {r.artifact_name}: {r.message}")

        if errors:
            print(f"\nErrors: {len(errors)}")
            for r in errors:
                print(f"  - {r.artifact_name}: {r.message}")

    print("\n" + "=" * 70)

    if dry_run and misplaced:
        print("\nTo apply these fixes, run with --execute flag:")
        print("  python scripts/fix-misplaced-artifacts.py --execute")


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix misplaced artifacts that were imported to the wrong collection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fix-misplaced-artifacts.py                # Preview (dry-run)
  python scripts/fix-misplaced-artifacts.py --execute      # Apply fixes
  python scripts/fix-misplaced-artifacts.py --execute -v   # Verbose output

Notes:
  - By default, runs in dry-run mode (preview only)
  - Use --execute to actually move files and update manifests
  - Manifests are backed up before modification
  - Artifacts that already exist in destination are skipped
        """,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the fixes (default is dry-run)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to cache.db (default: ~/.skillmeat/cache/cache.db)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=DEFAULT_COLLECTION_ID,
        help=f"Target collection ID (default: {DEFAULT_COLLECTION_ID})",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine dry-run mode
    dry_run = not args.execute

    # Get database path
    db_path = args.db or get_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        print("Run the SkillMeat API server first to initialize the database.", file=sys.stderr)
        return 1

    # Validate collections directory exists
    collections_dir = get_collections_dir()
    if not collections_dir.exists():
        print(f"Error: Collections directory not found: {collections_dir}", file=sys.stderr)
        return 1

    print(f"Database: {db_path}")
    print(f"Collections: {collections_dir}")
    print(f"Target collection: {args.collection}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'EXECUTE'}")

    # Find misplaced artifacts
    try:
        misplaced = find_misplaced_artifacts(
            db_path=db_path,
            target_collection=args.collection,
            verbose=args.verbose,
        )
    except sqlite3.Error as e:
        print(f"Error reading database: {e}", file=sys.stderr)
        return 1

    # Fix misplaced artifacts
    results = []
    for artifact in misplaced:
        result = fix_misplaced_artifact(
            artifact=artifact,
            dry_run=dry_run,
            verbose=args.verbose,
        )
        results.append(result)

    # Print summary
    print_summary(misplaced, results, dry_run)

    # Return appropriate exit code
    errors = [r for r in results if r.action == "error"]
    if errors:
        return 2  # Partial success
    return 0


if __name__ == "__main__":
    sys.exit(main())
