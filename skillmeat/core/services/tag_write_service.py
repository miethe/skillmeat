"""Service for writing tag changes to filesystem sources.

Follows the principle: Web UI -> Filesystem -> DB Cache.
When tags are renamed or deleted via the web UI, this service
updates both collection.toml and artifact frontmatter files
so the changes persist through cache refreshes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.utils.frontmatter_writer import (
    rename_tag_in_frontmatter,
    remove_tag_from_frontmatter,
)

logger = logging.getLogger(__name__)

# Markdown filenames to search for in artifact directories, in priority order.
_ARTIFACT_MD_NAMES = ["SKILL.md", "COMMAND.md", "AGENT.md", "README.md"]


class TagWriteService:
    """Writes tag changes to filesystem (collection.toml + frontmatter).

    This service bridges the gap between web UI tag mutations and
    the filesystem sources that feed the cache. Without this, tag
    renames/deletes would revert on the next cache refresh.
    """

    def _find_artifact_md(self, artifact_path: Path) -> Optional[Path]:
        """Locate the primary markdown file for an artifact.

        Args:
            artifact_path: Resolved path to the artifact on disk.

        Returns:
            Path to the first matching markdown file, or None.
        """
        if artifact_path.is_dir():
            for md_name in _ARTIFACT_MD_NAMES:
                md_path = artifact_path / md_name
                if md_path.exists():
                    return md_path
        elif artifact_path.is_file() and artifact_path.suffix == ".md":
            return artifact_path
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rename_tag(
        self,
        old_name: str,
        new_name: str,
        collection_manager,
        artifact_manager=None,
    ) -> Dict:
        """Rename a tag across all filesystem sources.

        Updates every ``collection.toml`` and artifact frontmatter file
        that contains *old_name*, replacing it with *new_name*.

        Args:
            old_name: Current tag name.
            new_name: New tag name.
            collection_manager: ``CollectionManager`` instance.
            artifact_manager: Optional ``ArtifactManager`` (unused, reserved
                for future path-resolution strategies).

        Returns:
            Dict with ``affected_artifacts`` (list of artifact identifiers)
            and ``files_updated`` (count of files modified on disk).
        """
        affected_artifacts: List[str] = []
        files_updated = 0

        try:
            collection_names = collection_manager.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections for tag rename: {e}")
            return {"affected_artifacts": [], "files_updated": 0}

        for coll_name in collection_names:
            try:
                collection = collection_manager.load_collection(coll_name)
            except Exception as e:
                logger.warning(f"Skipping collection '{coll_name}' (load failed): {e}")
                continue

            collection_path = collection_manager.config.get_collection_path(coll_name)
            modified = False

            for artifact in collection.artifacts:
                if old_name not in (artifact.tags or []):
                    continue

                # Build deduplicated tag list with the rename applied
                new_tags: List[str] = []
                seen: set = set()
                for t in artifact.tags:
                    replacement = new_name if t == old_name else t
                    if replacement not in seen:
                        seen.add(replacement)
                        new_tags.append(replacement)
                artifact.tags = new_tags
                modified = True

                artifact_id = f"{artifact.type.value}:{artifact.name}"
                affected_artifacts.append(artifact_id)

                # Update frontmatter in the artifact's markdown file
                md_path = self._find_artifact_md(collection_path / artifact.path)
                if md_path is not None:
                    if rename_tag_in_frontmatter(md_path, old_name, new_name):
                        files_updated += 1

            if modified:
                try:
                    collection_manager.save_collection(collection)
                    files_updated += 1  # collection.toml counts as one file
                    logger.info(
                        f"Updated collection.toml for '{coll_name}' "
                        f"(renamed tag '{old_name}' -> '{new_name}')"
                    )
                except Exception as e:
                    logger.error(f"Failed to save collection '{coll_name}': {e}")

        logger.info(
            f"Tag rename '{old_name}' -> '{new_name}': "
            f"{len(affected_artifacts)} artifacts, {files_updated} files"
        )
        return {
            "affected_artifacts": affected_artifacts,
            "files_updated": files_updated,
        }

    def delete_tag(
        self,
        tag_name: str,
        collection_manager,
        artifact_manager=None,
    ) -> Dict:
        """Remove a tag from all filesystem sources.

        Strips *tag_name* from every ``collection.toml`` artifact entry
        and from the corresponding frontmatter files.

        Args:
            tag_name: Tag name to remove.
            collection_manager: ``CollectionManager`` instance.
            artifact_manager: Optional ``ArtifactManager`` (reserved).

        Returns:
            Dict with ``affected_artifacts`` and ``files_updated``.
        """
        affected_artifacts: List[str] = []
        files_updated = 0

        try:
            collection_names = collection_manager.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections for tag delete: {e}")
            return {"affected_artifacts": [], "files_updated": 0}

        for coll_name in collection_names:
            try:
                collection = collection_manager.load_collection(coll_name)
            except Exception as e:
                logger.warning(f"Skipping collection '{coll_name}' (load failed): {e}")
                continue

            collection_path = collection_manager.config.get_collection_path(coll_name)
            modified = False

            for artifact in collection.artifacts:
                if tag_name not in (artifact.tags or []):
                    continue

                artifact.tags = [t for t in artifact.tags if t != tag_name]
                modified = True

                artifact_id = f"{artifact.type.value}:{artifact.name}"
                affected_artifacts.append(artifact_id)

                # Update frontmatter in the artifact's markdown file
                md_path = self._find_artifact_md(collection_path / artifact.path)
                if md_path is not None:
                    if remove_tag_from_frontmatter(md_path, tag_name):
                        files_updated += 1

            if modified:
                try:
                    collection_manager.save_collection(collection)
                    files_updated += 1
                    logger.info(
                        f"Updated collection.toml for '{coll_name}' "
                        f"(removed tag '{tag_name}')"
                    )
                except Exception as e:
                    logger.error(f"Failed to save collection '{coll_name}': {e}")

        logger.info(
            f"Tag delete '{tag_name}': "
            f"{len(affected_artifacts)} artifacts, {files_updated} files"
        )
        return {
            "affected_artifacts": affected_artifacts,
            "files_updated": files_updated,
        }

    def update_tags_json_cache(
        self,
        affected_artifact_ids: List[str],
        session_factory=None,
    ) -> int:
        """Update ``tags_json`` on CollectionArtifact rows after filesystem changes.

        This keeps the DB cache in sync without requiring a full cache refresh.

        Args:
            affected_artifact_ids: List of artifact identifiers
                (e.g. ``["skill:my-skill", "command:my-cmd"]``).
            session_factory: Optional callable returning a SQLAlchemy session.
                Falls back to ``cache.models.get_session``.

        Returns:
            Number of ``CollectionArtifact`` rows updated.
        """
        if not affected_artifact_ids:
            return 0

        try:
            from skillmeat.cache.models import (
                CollectionArtifact,
                ArtifactTag,
                Tag,
                get_session,
            )
        except ImportError as e:
            logger.warning(f"Cache models not available: {e}")
            return 0

        session = get_session() if session_factory is None else session_factory()
        updated = 0

        try:
            from skillmeat.cache.models import Artifact  # local import to avoid cycles

            for artifact_id in affected_artifact_ids:
                # Resolve type:name artifact_id → artifacts.uuid
                artifact = (
                    session.query(Artifact)
                    .filter_by(id=artifact_id)
                    .first()
                )
                if not artifact:
                    logger.debug(
                        f"update_tags_json_cache: artifact '{artifact_id}' not in "
                        "cache; skipping"
                    )
                    continue

                artifact_uuid = artifact.uuid

                # Fetch current tag names from the junction table (keyed by uuid)
                tags = (
                    session.query(Tag.name)
                    .join(ArtifactTag, Tag.id == ArtifactTag.tag_id)
                    .filter(ArtifactTag.artifact_uuid == artifact_uuid)
                    .all()
                )
                tag_names = sorted(t[0] for t in tags)

                # Patch tags_json on every CollectionArtifact row for this artifact
                rows = (
                    session.query(CollectionArtifact)
                    .filter_by(artifact_uuid=artifact_uuid)
                    .all()
                )
                for row in rows:
                    row.tags_json = json.dumps(tag_names)
                    updated += 1

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update tags_json cache: {e}")
            raise
        finally:
            session.close()

        return updated
