#!/usr/bin/env python3
"""
Backfill tools_json for existing artifacts in the cache database.

This script:
1. Reads all CollectionArtifact rows from SQLite cache
2. For each artifact, finds the SKILL.md file in the collection
3. Extracts tools from frontmatter using the existing parser
4. Updates tools_json in the database

Usage:
    python scripts/backfill_tools_json.py              # Execute backfill
    python scripts/backfill_tools_json.py --dry-run    # Preview without changes
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def setup_path():
    """Add project root to sys.path for imports."""
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


setup_path()

from skillmeat.core.parsers.markdown_parser import extract_metadata


def get_cache_db_path() -> Path:
    """Get path to the cache database."""
    return Path.home() / ".skillmeat" / "cache" / "cache.db"


def get_collection_paths_from_db(cursor) -> dict[str, Path]:
    """
    Get paths to all collection directories using database to map UUIDs.

    The database stores collection_id as UUIDs or "default".
    We need to map these to filesystem paths.

    Returns:
        Dict mapping collection_id to base path
    """
    skillmeat_dir = Path.home() / ".skillmeat"
    paths = {}

    # Query collections table to get id -> name mapping
    cursor.execute("SELECT id, name FROM collections")
    collections = cursor.fetchall()

    for coll_id, coll_name in collections:
        # Special case: "default" collection
        if coll_id == "default":
            # Try new structure first, fall back to old
            new_path = skillmeat_dir / "collections" / "default"
            old_path = skillmeat_dir / "collection"
            if new_path.exists():
                paths[coll_id] = new_path
            elif old_path.exists():
                paths[coll_id] = old_path
        else:
            # UUID collections - look for matching directory by name
            # Convert name to directory-safe format (lowercase, no spaces)
            dir_name = coll_name.lower().replace(" ", "-").replace("_", "-")
            coll_path = skillmeat_dir / "collections" / dir_name
            if coll_path.exists():
                paths[coll_id] = coll_path
            else:
                # Also try original name
                coll_path = skillmeat_dir / "collections" / coll_name
                if coll_path.exists():
                    paths[coll_id] = coll_path

    # Also add any directories not in database (for safety)
    collections_dir = skillmeat_dir / "collections"
    if collections_dir.exists():
        for coll_dir in collections_dir.iterdir():
            if coll_dir.is_dir() and coll_dir.name not in [p.name for p in paths.values()]:
                # Use directory name as key if not already mapped
                if coll_dir.name not in paths:
                    paths[coll_dir.name] = coll_dir

    return paths


def parse_artifact_id(artifact_id: str) -> tuple[str, str] | None:
    """
    Parse artifact_id into type and name.

    Args:
        artifact_id: Format "type:name" (e.g., "skill:aesthetic")

    Returns:
        Tuple of (type, name) or None if invalid format
    """
    parts = artifact_id.split(":", 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def get_artifact_skill_file(
    artifact_id: str,
    collection_id: str,
    collection_paths: dict[str, Path]
) -> Path | None:
    """
    Get path to SKILL.md file for an artifact.

    Args:
        artifact_id: Format "type:name"
        collection_id: Collection ID (e.g., "default", "personal")
        collection_paths: Dict mapping collection_id to base path

    Returns:
        Path to SKILL.md or None if artifact_id format is invalid
    """
    parsed = parse_artifact_id(artifact_id)
    if not parsed:
        return None

    artifact_type, artifact_name = parsed
    # Type needs 's' suffix: skill → skills, command → commands
    type_dir = f"{artifact_type}s"

    # Try to find collection path
    collection_path = collection_paths.get(collection_id)
    if not collection_path:
        # Try default if collection not found
        collection_path = collection_paths.get("default")

    if not collection_path:
        return None

    return collection_path / type_dir / artifact_name / "SKILL.md"


def extract_tools_from_file(skill_file: Path) -> list[str] | None:
    """
    Extract tools from SKILL.md frontmatter.

    Args:
        skill_file: Path to SKILL.md file

    Returns:
        List of tool names, empty list if no tools, or None if file missing/error
    """
    if not skill_file.exists():
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")
        metadata = extract_metadata(content)
        tools = metadata.get("tools", [])
        return tools if isinstance(tools, list) else []
    except Exception as e:
        print(f"  ⚠️  Error reading {skill_file}: {e}")
        return None


def backfill_tools_json(dry_run: bool = False) -> dict[str, int]:
    """
    Backfill tools_json for all artifacts in cache database.

    Args:
        dry_run: If True, preview changes without updating database

    Returns:
        Dict with counts: {"updated": int, "skipped": int, "errors": int}
    """
    cache_db = get_cache_db_path()

    if not cache_db.exists():
        print(f"❌ Cache database not found: {cache_db}")
        sys.exit(1)

    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()

    collection_paths = get_collection_paths_from_db(cursor)

    if not collection_paths:
        print("❌ No collection directories found")
        conn.close()
        sys.exit(1)

    print(f"📦 Cache database: {cache_db}")
    print(f"📁 Collections mapped: {len(collection_paths)}")
    for coll_id, coll_path in list(collection_paths.items())[:5]:
        print(f"   - {coll_id[:20]}... → {coll_path.name}")
    if len(collection_paths) > 5:
        print(f"   ... and {len(collection_paths) - 5} more")
    print(f"{'🔍 DRY RUN MODE' if dry_run else '✅ EXECUTING BACKFILL'}\n")

    # Get all artifacts with collection_id
    cursor.execute(
        "SELECT collection_id, artifact_id, tools_json FROM collection_artifacts"
    )
    rows = cursor.fetchall()

    if not rows:
        print("ℹ️  No artifacts found in database")
        conn.close()
        return {"updated": 0, "skipped": 0, "errors": 0}

    print(f"Found {len(rows)} artifacts\n")

    stats = {"updated": 0, "skipped": 0, "errors": 0, "no_tools": 0}

    for collection_id, artifact_id, existing_tools_json in rows:
        # Only process skills (agents, commands, hooks don't have SKILL.md)
        parsed = parse_artifact_id(artifact_id)
        if parsed and parsed[0] != "skill":
            # Skip non-skills silently
            stats["skipped"] += 1
            continue

        print(f"Processing: {artifact_id}")

        # Skip if tools_json already populated
        if existing_tools_json and existing_tools_json.strip():
            print(f"  ⏭️  Already has tools_json, skipping")
            stats["skipped"] += 1
            continue

        # Get SKILL.md file path
        skill_file = get_artifact_skill_file(artifact_id, collection_id, collection_paths)
        if not skill_file:
            print(f"  ❌ Invalid artifact_id format or collection not found")
            stats["errors"] += 1
            continue

        # Extract tools
        tools = extract_tools_from_file(skill_file)

        if tools is None:
            print(f"  ❌ File not found: {skill_file.name}")
            stats["errors"] += 1
            continue

        # Convert to JSON (null if empty list)
        tools_json = json.dumps(tools) if tools else None

        if tools:
            print(f"  ✅ Found {len(tools)} tool(s): {', '.join(tools[:5])}{'...' if len(tools) > 5 else ''}")
        else:
            print(f"  ℹ️  No tools in frontmatter")
            stats["no_tools"] += 1

        # Update database
        if not dry_run:
            cursor.execute(
                "UPDATE collection_artifacts SET tools_json = ? WHERE collection_id = ? AND artifact_id = ?",
                (tools_json, collection_id, artifact_id)
            )

        stats["updated"] += 1

    if not dry_run:
        conn.commit()

    conn.close()

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill tools_json for existing artifacts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database"
    )
    args = parser.parse_args()

    stats = backfill_tools_json(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Updated:    {stats['updated']}")
    print(f"  └─ With tools: {stats['updated'] - stats.get('no_tools', 0)}")
    print(f"  └─ No tools:   {stats.get('no_tools', 0)}")
    print(f"⏭️  Skipped:    {stats['skipped']}")
    print(f"❌ Errors:      {stats['errors']}")

    if args.dry_run:
        print("\n🔍 This was a dry run. Re-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
