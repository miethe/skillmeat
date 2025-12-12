"""Catalog diff engine for detecting artifact changes.

Compares previous catalog state with new scan results to identify
new, updated, removed, and unchanged entries.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.cache.repositories import CatalogDiff

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of changes detected in catalog."""

    NEW = "new"
    UPDATED = "updated"
    REMOVED = "removed"
    UNCHANGED = "unchanged"


@dataclass
class DiffEntry:
    """A single diff entry representing a change."""

    change_type: ChangeType
    upstream_url: str
    artifact_type: str
    name: str
    path: str

    # For updates, track what changed
    old_sha: Optional[str] = None
    new_sha: Optional[str] = None
    old_version: Optional[str] = None
    new_version: Optional[str] = None

    # For existing entries
    existing_entry_id: Optional[str] = None

    # New data for creates/updates
    new_data: Optional[Dict] = None


@dataclass
class DiffResult:
    """Result of comparing old and new catalog states."""

    new_entries: List[DiffEntry] = field(default_factory=list)
    updated_entries: List[DiffEntry] = field(default_factory=list)
    removed_entries: List[DiffEntry] = field(default_factory=list)
    unchanged_entries: List[DiffEntry] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        """Total number of changed entries (new + updated + removed)."""
        return (
            len(self.new_entries)
            + len(self.updated_entries)
            + len(self.removed_entries)
        )

    @property
    def summary(self) -> Dict[str, int]:
        """Summary counts for each change type."""
        return {
            "new": len(self.new_entries),
            "updated": len(self.updated_entries),
            "removed": len(self.removed_entries),
            "unchanged": len(self.unchanged_entries),
            "total": len(self.new_entries)
            + len(self.updated_entries)
            + len(self.removed_entries)
            + len(self.unchanged_entries),
        }

    def to_catalog_diff(self) -> CatalogDiff:
        """Convert to CatalogDiff for repository operations."""
        return CatalogDiff(
            new=[e.new_data for e in self.new_entries if e.new_data],
            updated=[
                (e.existing_entry_id, e.new_data)
                for e in self.updated_entries
                if e.existing_entry_id and e.new_data
            ],
            removed=[
                e.existing_entry_id for e in self.removed_entries if e.existing_entry_id
            ],
            unchanged=[
                e.existing_entry_id
                for e in self.unchanged_entries
                if e.existing_entry_id
            ],
        )


class CatalogDiffEngine:
    """Compares catalog states to identify changes.

    Uses upstream_url as the primary key for matching entries,
    and detected_sha for determining if content changed.

    Example:
        >>> engine = CatalogDiffEngine()
        >>> result = engine.compute_diff(old_entries, new_artifacts)
        >>> print(f"New: {len(result.new_entries)}, Updated: {len(result.updated_entries)}")
    """

    def compute_diff(
        self,
        existing_entries: List[Dict],
        new_artifacts: List[DetectedArtifact],
        source_id: str,
    ) -> DiffResult:
        """Compute diff between existing entries and new scan results.

        Args:
            existing_entries: List of existing catalog entry dicts (from DB)
                Each should have: id, upstream_url, detected_sha, artifact_type, name, path
            new_artifacts: List of DetectedArtifact from new scan
            source_id: ID of the marketplace source

        Returns:
            DiffResult with categorized changes
        """
        result = DiffResult()

        # Index existing entries by upstream_url
        existing_by_url: Dict[str, Dict] = {}
        for entry in existing_entries:
            url = entry.get("upstream_url", "")
            if url:
                existing_by_url[url] = entry

        # Index new artifacts by upstream_url
        new_by_url: Dict[str, DetectedArtifact] = {}
        for artifact in new_artifacts:
            if artifact.upstream_url:
                new_by_url[artifact.upstream_url] = artifact

        existing_urls = set(existing_by_url.keys())
        new_urls = set(new_by_url.keys())

        # Find new entries (in new but not in existing)
        for url in new_urls - existing_urls:
            artifact = new_by_url[url]
            result.new_entries.append(
                DiffEntry(
                    change_type=ChangeType.NEW,
                    upstream_url=url,
                    artifact_type=artifact.artifact_type,
                    name=artifact.name,
                    path=artifact.path,
                    new_sha=artifact.detected_sha,
                    new_version=artifact.detected_version,
                    new_data=self._artifact_to_dict(artifact, source_id),
                )
            )

        # Find removed entries (in existing but not in new)
        for url in existing_urls - new_urls:
            entry = existing_by_url[url]
            result.removed_entries.append(
                DiffEntry(
                    change_type=ChangeType.REMOVED,
                    upstream_url=url,
                    artifact_type=entry.get("artifact_type", ""),
                    name=entry.get("name", ""),
                    path=entry.get("path", ""),
                    old_sha=entry.get("detected_sha"),
                    old_version=entry.get("detected_version"),
                    existing_entry_id=entry.get("id"),
                )
            )

        # Find updated/unchanged entries (in both)
        for url in existing_urls & new_urls:
            entry = existing_by_url[url]
            artifact = new_by_url[url]

            # Check if SHA changed (indicates content update)
            old_sha = entry.get("detected_sha", "")
            new_sha = artifact.detected_sha or ""

            if old_sha != new_sha and new_sha:
                result.updated_entries.append(
                    DiffEntry(
                        change_type=ChangeType.UPDATED,
                        upstream_url=url,
                        artifact_type=artifact.artifact_type,
                        name=artifact.name,
                        path=artifact.path,
                        old_sha=old_sha,
                        new_sha=new_sha,
                        old_version=entry.get("detected_version"),
                        new_version=artifact.detected_version,
                        existing_entry_id=entry.get("id"),
                        new_data=self._artifact_to_dict(artifact, source_id),
                    )
                )
            else:
                result.unchanged_entries.append(
                    DiffEntry(
                        change_type=ChangeType.UNCHANGED,
                        upstream_url=url,
                        artifact_type=artifact.artifact_type,
                        name=artifact.name,
                        path=artifact.path,
                        old_sha=old_sha,
                        existing_entry_id=entry.get("id"),
                    )
                )

        logger.info(
            f"Diff computed for source {source_id}: "
            f"{len(result.new_entries)} new, {len(result.updated_entries)} updated, "
            f"{len(result.removed_entries)} removed, {len(result.unchanged_entries)} unchanged"
        )

        return result

    def _artifact_to_dict(
        self,
        artifact: DetectedArtifact,
        source_id: str,
    ) -> Dict:
        """Convert DetectedArtifact to dict for database insertion."""
        return {
            "source_id": source_id,
            "artifact_type": artifact.artifact_type,
            "name": artifact.name,
            "path": artifact.path,
            "upstream_url": artifact.upstream_url,
            "detected_version": artifact.detected_version,
            "detected_sha": artifact.detected_sha,
            "confidence_score": artifact.confidence_score,
            "metadata": artifact.metadata,
        }


def compute_catalog_diff(
    existing_entries: List[Dict],
    new_artifacts: List[DetectedArtifact],
    source_id: str,
) -> DiffResult:
    """Convenience function to compute catalog diff.

    Args:
        existing_entries: Existing catalog entries from database
        new_artifacts: Newly detected artifacts from scan
        source_id: Marketplace source ID

    Returns:
        DiffResult with categorized changes
    """
    engine = CatalogDiffEngine()
    return engine.compute_diff(existing_entries, new_artifacts, source_id)


if __name__ == "__main__":
    from skillmeat.api.schemas.marketplace import DetectedArtifact

    # Existing entries (simulating DB records)
    existing = [
        {
            "id": "e1",
            "upstream_url": "https://github.com/user/repo/skills/a",
            "detected_sha": "sha1",
            "artifact_type": "skill",
            "name": "a",
            "path": "skills/a",
        },
        {
            "id": "e2",
            "upstream_url": "https://github.com/user/repo/skills/b",
            "detected_sha": "sha2",
            "artifact_type": "skill",
            "name": "b",
            "path": "skills/b",
        },
        {
            "id": "e3",
            "upstream_url": "https://github.com/user/repo/skills/c",
            "detected_sha": "sha3",
            "artifact_type": "skill",
            "name": "c",
            "path": "skills/c",
        },
    ]

    # New scan results
    new_artifacts = [
        DetectedArtifact(
            artifact_type="skill",
            name="a",
            path="skills/a",
            upstream_url="https://github.com/user/repo/skills/a",
            confidence_score=80,
            detected_sha="sha1",
        ),  # Unchanged
        DetectedArtifact(
            artifact_type="skill",
            name="b",
            path="skills/b",
            upstream_url="https://github.com/user/repo/skills/b",
            confidence_score=80,
            detected_sha="sha2-new",
        ),  # Updated
        DetectedArtifact(
            artifact_type="skill",
            name="d",
            path="skills/d",
            upstream_url="https://github.com/user/repo/skills/d",
            confidence_score=80,
            detected_sha="sha4",
        ),  # New
        # Note: "c" is missing = removed
    ]

    result = compute_catalog_diff(existing, new_artifacts, "source-123")

    print("Diff Results:")
    print(f"  New: {len(result.new_entries)}")
    print(f"  Updated: {len(result.updated_entries)}")
    print(f"  Removed: {len(result.removed_entries)}")
    print(f"  Unchanged: {len(result.unchanged_entries)}")
    print(f"  Summary: {result.summary}")
