"""Collection service for centralized collection membership queries.

This service provides efficient batch queries for artifact-collection
membership, eliminating N+1 query patterns across the API layer.
"""

import logging
import time
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from skillmeat.api.schemas.artifacts import ArtifactCollectionInfo
from skillmeat.cache.collection_cache import get_collection_count_cache
from skillmeat.cache.models import Artifact, Collection, CollectionArtifact

logger = logging.getLogger(__name__)


class CollectionService:
    """Centralized service for collection membership queries.

    Provides batch and single-artifact methods for fetching collection
    memberships with optimized queries to avoid N+1 patterns.

    Attributes:
        db: SQLAlchemy database session

    Example:
        >>> service = CollectionService(db_session)
        >>> memberships = service.get_collection_membership_batch(["artifact:1", "artifact:2"])
        >>> for artifact_id, collections in memberships.items():
        ...     print(f"{artifact_id}: {[c.name for c in collections]}")
    """

    def __init__(self, db_session: Session):
        """Initialize the CollectionService.

        Args:
            db_session: SQLAlchemy database session for queries
        """
        self.db = db_session

    def get_collection_membership_batch(
        self,
        artifact_ids: List[str],
    ) -> Dict[str, List[ArtifactCollectionInfo]]:
        """Fetch collection memberships for multiple artifacts in a single query.

        Uses optimized batch queries with in_() clauses and GROUP BY for counts
        to avoid N+1 query patterns. All collection details and artifact counts
        are fetched in a maximum of 2 queries regardless of input size.

        Args:
            artifact_ids: List of artifact IDs to query memberships for

        Returns:
            Dict mapping each artifact_id to a list of ArtifactCollectionInfo.
            Every input artifact_id will have an entry (empty list if no memberships).

        Example:
            >>> service = CollectionService(db_session)
            >>> result = service.get_collection_membership_batch(["skill:canvas"])
            >>> result["skill:canvas"]
            [ArtifactCollectionInfo(id="abc123", name="Design Tools", artifact_count=5)]
        """
        if not artifact_ids:
            return {}

        start_time = time.perf_counter()

        # Step 1: Resolve type:name artifact IDs to their UUIDs.
        # Since CAI-P5-01, CollectionArtifact stores artifact_uuid (FK to
        # artifacts.uuid) rather than the type:name artifact_id string.
        # We resolve the external type:name IDs to UUIDs in a single query,
        # then use those UUIDs to query CollectionArtifact.
        uuid_rows = (
            self.db.query(Artifact.id, Artifact.uuid)
            .filter(Artifact.id.in_(artifact_ids))
            .all()
        )
        # Build bidirectional maps
        artifact_id_to_uuid: dict = {row[0]: row[1] for row in uuid_rows}
        uuid_to_artifact_id: dict = {row[1]: row[0] for row in uuid_rows}
        known_uuids = list(artifact_id_to_uuid.values())

        if not known_uuids:
            return {aid: [] for aid in artifact_ids}

        # Step 2: Query associations by artifact_uuid
        associations = (
            self.db.query(CollectionArtifact)
            .filter(CollectionArtifact.artifact_uuid.in_(known_uuids))
            .all()
        )

        query_time = time.perf_counter() - start_time
        logger.debug(
            f"Collection associations query: {len(associations)} results "
            f"for {len(artifact_ids)} artifacts in {query_time:.3f}s"
        )

        if not associations:
            return {aid: [] for aid in artifact_ids}

        # Get unique collection IDs from associations
        collection_ids = {a.collection_id for a in associations}

        # Check cache for counts first
        cache = get_collection_count_cache()
        cached_counts: Dict[str, int] = {}
        missing_ids = collection_ids

        try:
            cached_counts, missing_ids = cache.get_counts(collection_ids)
            logger.debug(
                f"Collection count cache: {len(cached_counts)} hits, "
                f"{len(missing_ids)} misses"
            )
        except Exception as e:
            # Cache failure shouldn't break the service - fall back to DB
            logger.warning(f"Cache lookup failed, falling back to DB: {e}")
            missing_ids = collection_ids

        # Query DB for collection details and counts
        # Strategy: Always fetch collection details for ALL collections.
        # For counts: use cache when available, query DB only for missing counts.
        if missing_ids:
            # Some counts are missing - need to query DB for those
            count_subquery = (
                self.db.query(
                    CollectionArtifact.collection_id,
                    func.count("*").label("count"),
                )
                .group_by(CollectionArtifact.collection_id)
                .subquery()
            )

            collections_with_counts = (
                self.db.query(Collection, count_subquery.c.count)
                .outerjoin(
                    count_subquery,
                    Collection.id == count_subquery.c.collection_id,
                )
                .filter(Collection.id.in_(collection_ids))
                .all()
            )

            # Store fetched counts in cache for future requests (only missing ones)
            fetched_counts = {
                c.id: count or 0
                for c, count in collections_with_counts
                if c.id in missing_ids
            }
            try:
                cache.set_counts(fetched_counts)
            except Exception as e:
                # Cache write failure shouldn't break the service
                logger.warning(f"Cache write failed: {e}")
        else:
            # All counts in cache - only need collection details
            collections_with_counts = (
                self.db.query(Collection)
                .filter(Collection.id.in_(collection_ids))
                .all()
            )
            # Convert to same format as query with counts
            collections_with_counts = [(c, None) for c in collections_with_counts]

        total_query_time = time.perf_counter() - start_time
        logger.debug(
            f"Collection details query: {len(collections_with_counts)} collections "
            f"in {total_query_time:.3f}s total"
        )

        # Build collection map for fast lookup, combining cached and fetched counts
        collection_map: Dict[str, ArtifactCollectionInfo] = {}
        for c, count in collections_with_counts:
            # Use cached count if available, otherwise use DB count
            artifact_count = cached_counts.get(c.id, count or 0)
            collection_map[c.id] = ArtifactCollectionInfo(
                id=c.id,
                name=c.name,
                artifact_count=artifact_count,
            )

        # Build result - ensure all input artifact_ids have entries (even if empty)
        result: Dict[str, List[ArtifactCollectionInfo]] = {
            aid: [] for aid in artifact_ids
        }

        for assoc in associations:
            artifact_type_name = uuid_to_artifact_id.get(assoc.artifact_uuid)
            if artifact_type_name and assoc.collection_id in collection_map:
                result[artifact_type_name].append(
                    collection_map[assoc.collection_id]
                )

        return result

    def get_collection_membership_single(
        self,
        artifact_id: str,
    ) -> List[ArtifactCollectionInfo]:
        """Convenience method for single artifact collection lookup.

        Delegates to get_collection_membership_batch for consistent behavior.
        Use this method when querying a single artifact; use the batch method
        when querying multiple artifacts to avoid repeated queries.

        Args:
            artifact_id: Single artifact ID to query memberships for

        Returns:
            List of ArtifactCollectionInfo for the artifact (empty if none)

        Example:
            >>> service = CollectionService(db_session)
            >>> collections = service.get_collection_membership_single("skill:canvas")
            >>> for c in collections:
            ...     print(f"{c.name}: {c.artifact_count} artifacts")
        """
        result = self.get_collection_membership_batch([artifact_id])
        return result.get(artifact_id, [])
