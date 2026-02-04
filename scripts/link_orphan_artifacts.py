#!/usr/bin/env python3
"""Link orphan collection artifacts to marketplace catalog entries.

Finds collection artifacts that have a source URL but no linked
MarketplaceCatalogEntry, then links them by matching upstream URLs.

Example:
    # Preview changes (default - dry run)
    python scripts/link_orphan_artifacts.py

    # Apply the links
    python scripts/link_orphan_artifacts.py --execute

    # Verbose output with matching details
    python scripts/link_orphan_artifacts.py -v
"""

import argparse
import re
import sys
from dataclasses import dataclass

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from skillmeat.cache.models import (
    CollectionArtifact,
    MarketplaceCatalogEntry,
    MarketplaceSource,
    get_session,
)


@dataclass
class SourceSpec:
    """Parsed source specification."""

    owner: str
    repo: str
    path: str
    version: str | None = None

    @property
    def repo_url(self) -> str:
        """Build the GitHub repo URL."""
        return f"https://github.com/{self.owner}/{self.repo}"

    @property
    def full_source(self) -> str:
        """Reconstruct the full source string."""
        base = f"{self.owner}/{self.repo}/{self.path}"
        if self.version:
            return f"{base}@{self.version}"
        return base


# Regex to parse GitHub tree URLs like:
# https://github.com/owner/repo/tree/branch/path/to/artifact
GITHUB_TREE_URL_PATTERN = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+?)(?:\.md)?$"
)

# Regex to parse GitHub blob URLs like:
# https://github.com/owner/repo/blob/branch/path/to/file.md
GITHUB_BLOB_URL_PATTERN = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+?)(?:\.md)?$"
)


def parse_source_spec(source: str) -> SourceSpec | None:
    """Parse a source spec in various formats.

    Supported formats:
    - owner/repo/path[@version] (e.g., 'anthropics/skills/pdf@latest')
    - https://github.com/owner/repo/tree/branch/path/to/artifact
    - https://github.com/owner/repo/blob/branch/path/to/file.md

    Args:
        source: Source string in any supported format

    Returns:
        SourceSpec if parsed successfully, None otherwise
    """
    if not source:
        return None

    # Try GitHub tree URL format first
    match = GITHUB_TREE_URL_PATTERN.match(source)
    if match:
        owner, repo, _branch, path = match.groups()
        return SourceSpec(owner=owner, repo=repo, path=path)

    # Try GitHub blob URL format
    match = GITHUB_BLOB_URL_PATTERN.match(source)
    if match:
        owner, repo, _branch, path = match.groups()
        # For blob URLs, the path includes the filename - extract directory
        # e.g., "agents/ai-staff.md" -> "agents/ai-staff"
        if "/" in path:
            # Keep the full path without .md extension
            pass
        return SourceSpec(owner=owner, repo=repo, path=path)

    # Try short format: owner/repo/path[@version]
    # Remove version suffix if present
    version = None
    if "@" in source:
        source, version = source.rsplit("@", 1)

    # Split into parts: owner/repo/path[/subpath/...]
    parts = source.split("/")
    if len(parts) < 3:
        return None

    owner = parts[0]
    repo = parts[1]
    path = "/".join(parts[2:])  # Rest is the path

    return SourceSpec(owner=owner, repo=repo, path=path, version=version)


def find_orphan_artifacts(session: Session) -> list[CollectionArtifact]:
    """Find collection artifacts with source but no linked catalog entry.

    Args:
        session: Database session

    Returns:
        List of orphan CollectionArtifact records
    """
    # Subquery to check if an artifact has a linked catalog entry
    has_catalog_entry = (
        select(MarketplaceCatalogEntry.id)
        .where(MarketplaceCatalogEntry.import_id == CollectionArtifact.artifact_id)
        .exists()
    )

    # Query artifacts that have source but no linked catalog entry
    query = (
        select(CollectionArtifact)
        .where(
            and_(
                CollectionArtifact.source.isnot(None),
                CollectionArtifact.source != "",
                or_(
                    CollectionArtifact.origin == "marketplace",
                    CollectionArtifact.origin == "github",
                ),
                ~has_catalog_entry,
            )
        )
        .order_by(CollectionArtifact.artifact_id)
    )

    return list(session.execute(query).scalars().all())


def find_already_linked_count(session: Session) -> int:
    """Count artifacts that already have catalog links.

    Args:
        session: Database session

    Returns:
        Count of linked artifacts
    """
    has_catalog_entry = (
        select(MarketplaceCatalogEntry.id)
        .where(MarketplaceCatalogEntry.import_id == CollectionArtifact.artifact_id)
        .exists()
    )

    query = select(CollectionArtifact).where(
        and_(
            CollectionArtifact.source.isnot(None),
            CollectionArtifact.source != "",
            or_(
                CollectionArtifact.origin == "marketplace",
                CollectionArtifact.origin == "github",
            ),
            has_catalog_entry,
        )
    )

    return len(list(session.execute(query).scalars().all()))


def find_matching_catalog_entry(
    session: Session,
    spec: SourceSpec,
    verbose: bool = False,
) -> MarketplaceCatalogEntry | None:
    """Find a catalog entry matching the source spec.

    Matching algorithm:
    1. Look for catalog entry where upstream_url contains owner/repo and path
    2. Or where name matches and source's repo_url matches

    Args:
        session: Database session
        spec: Parsed source specification
        verbose: Print detailed matching info

    Returns:
        Matching catalog entry or None
    """
    # Build URL patterns for matching
    # Pattern: https://github.com/owner/repo/tree/[branch]/path
    url_pattern = f"%github.com/{spec.owner}/{spec.repo}%/{spec.path}%"

    if verbose:
        print(f"    Looking for upstream_url LIKE: {url_pattern}")

    # First try: match by upstream_url pattern
    query = (
        select(MarketplaceCatalogEntry)
        .where(
            and_(
                MarketplaceCatalogEntry.upstream_url.like(url_pattern),
                MarketplaceCatalogEntry.import_id.is_(None),  # Not already linked
            )
        )
        .limit(1)
    )

    entry = session.execute(query).scalar_one_or_none()
    if entry:
        if verbose:
            print(f"    Matched via upstream_url: {entry.upstream_url}")
        return entry

    # Second try: match by name and source repo_url
    # Find sources that match the repo
    source_query = select(MarketplaceSource).where(
        or_(
            MarketplaceSource.repo_url == spec.repo_url,
            MarketplaceSource.repo_url == f"{spec.repo_url}.git",
        )
    )

    sources = list(session.execute(source_query).scalars().all())

    if verbose and sources:
        print(f"    Found {len(sources)} matching sources for repo {spec.repo_url}")

    for source in sources:
        # Look for catalog entry with matching name and source
        # Extract just the artifact name (last part of path)
        artifact_name = spec.path.split("/")[-1]

        entry_query = (
            select(MarketplaceCatalogEntry)
            .where(
                and_(
                    MarketplaceCatalogEntry.source_id == source.id,
                    or_(
                        MarketplaceCatalogEntry.name == artifact_name,
                        MarketplaceCatalogEntry.path == spec.path,
                        MarketplaceCatalogEntry.path.like(f"%{spec.path}"),
                    ),
                    MarketplaceCatalogEntry.import_id.is_(None),
                )
            )
            .limit(1)
        )

        entry = session.execute(entry_query).scalar_one_or_none()
        if entry:
            if verbose:
                print(
                    f"    Matched via source+name: source={source.repo_url}, "
                    f"name={entry.name}, path={entry.path}"
                )
            return entry

    if verbose:
        print("    No match found")

    return None


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Link orphan collection artifacts to marketplace catalog entries"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without applying (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually apply the links",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed matching info",
    )
    args = parser.parse_args()

    # dry_run unless --execute explicitly passed
    dry_run = not args.execute

    print("Scanning for orphan artifacts...")

    session = get_session()
    try:
        # Find orphan artifacts
        orphans = find_orphan_artifacts(session)
        already_linked = find_already_linked_count(session)

        if not orphans:
            print("No orphan artifacts found (all have catalog links or no source)")
            print(f"\nSummary:")
            print(f"  Already linked: {already_linked}")
            return 0

        print(f"Found {len(orphans)} orphan artifacts with source but no catalog link")
        print()
        print("Matching artifacts to catalog entries:")

        matched: list[tuple[CollectionArtifact, MarketplaceCatalogEntry]] = []
        no_match: list[CollectionArtifact] = []
        parse_errors: list[tuple[CollectionArtifact, str]] = []

        for artifact in orphans:
            # Parse the source spec
            spec = parse_source_spec(artifact.source)

            if not spec:
                parse_errors.append((artifact, artifact.source or "(empty)"))
                if args.verbose:
                    print(
                        f"  ! {artifact.artifact_id} -> parse error: {artifact.source}"
                    )
                continue

            if args.verbose:
                print(f"  Processing: {artifact.artifact_id}")
                print(f"    Source: {artifact.source}")
                print(
                    f"    Parsed: owner={spec.owner}, repo={spec.repo}, path={spec.path}"
                )

            # Find matching catalog entry
            entry = find_matching_catalog_entry(session, spec, verbose=args.verbose)

            if entry:
                matched.append((artifact, entry))
                print(f"  + {artifact.artifact_id} -> matched to {entry.id[:8]}...")
                print(f"      ({entry.upstream_url})")
            else:
                no_match.append(artifact)
                print(f"  x {artifact.artifact_id} -> no matching catalog entry found")

        print()
        print("Summary:")
        print(f"  Matched: {len(matched)}")
        print(f"  No match: {len(no_match)}")
        print(f"  Parse errors: {len(parse_errors)}")
        print(f"  Already linked: {already_linked}")

        if parse_errors and args.verbose:
            print()
            print("Parse errors:")
            for artifact, source in parse_errors:
                print(f"  - {artifact.artifact_id}: {source}")

        if not matched:
            print()
            print("No artifacts to link.")
            return 0

        print()
        if dry_run:
            print(
                f"[DRY RUN] Would link {len(matched)} artifacts. Run with --execute to apply."
            )
        else:
            print(f"Linking {len(matched)} artifacts...")

            for artifact, entry in matched:
                entry.import_id = artifact.artifact_id
                entry.status = "imported"

            session.commit()
            print("Done. Links applied successfully.")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        session.rollback()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
