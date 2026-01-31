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
from skillmeat.cache.models import Collection, CollectionArtifact

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

        # Query associations for all artifact_ids in a single query
        associations = (
            self.db.query(CollectionArtifact)
            .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
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

        # Batch fetch collection details with artifact counts in a single query
        # Uses subquery for counts to avoid GROUP BY on all collection fields
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

        total_query_time = time.perf_counter() - start_time
        logger.debug(
            f"Collection details query: {len(collections_with_counts)} collections "
            f"with counts in {total_query_time:.3f}s total"
        )

        # Build collection map for fast lookup
        collection_map: Dict[str, ArtifactCollectionInfo] = {
            c.id: ArtifactCollectionInfo(
                id=c.id,
                name=c.name,
                artifact_count=count or 0,
            )
            for c, count in collections_with_counts
        }

        # Build result - ensure all input artifact_ids have entries (even if empty)
        result: Dict[str, List[ArtifactCollectionInfo]] = {
            aid: [] for aid in artifact_ids
        }

        for assoc in associations:
            if assoc.collection_id in collection_map:
                result[assoc.artifact_id].append(
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
