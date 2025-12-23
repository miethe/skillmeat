"""Rating storage manager for user ratings and community scores.

This module provides the RatingManager class for managing user ratings of artifacts
using SQLAlchemy ORM. It follows the existing SkillMeat storage patterns from
ManifestManager and uses get_session() for database access.

Usage:
    >>> from skillmeat.storage.rating_store import RatingManager
    >>> manager = RatingManager()
    >>>
    >>> # Add a rating
    >>> rating = manager.add_rating("skill:canvas-design", 5, "Great skill!", share=True)
    >>>
    >>> # Get ratings for an artifact
    >>> ratings = manager.get_ratings("skill:canvas-design")
    >>>
    >>> # Get average rating
    >>> avg = manager.get_average_rating("skill:canvas-design")
    >>> print(f"Average: {avg:.2f}")
    >>>
    >>> # Export ratings for community sharing
    >>> shared_ratings = manager.export_ratings(shared_only=True)
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from skillmeat.cache.models import UserRating as OrmUserRating
from skillmeat.cache.models import get_session
from skillmeat.core.scoring.models import UserRating


class RatingNotFoundError(Exception):
    """Raised when a rating is not found."""

    pass


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""

    pass


class RatingManager:
    """Manager for user ratings storage and retrieval.

    This class provides methods for adding, retrieving, updating, and exporting
    user ratings for artifacts. It includes rate limiting to prevent abuse.

    Attributes:
        None (uses get_session() for database access)
    """

    def add_rating(
        self,
        artifact_id: str,
        rating: int,
        feedback: str | None = None,
        share: bool = False,
        max_per_day: int = 5,
    ) -> UserRating:
        """Add a new rating for an artifact.

        Args:
            artifact_id: Artifact identifier (non-empty string)
            rating: Rating value (1-5)
            feedback: Optional text feedback
            share: Whether to share rating with community (default: False)
            max_per_day: Maximum ratings per artifact per day (default: 5)

        Returns:
            UserRating domain object with the created rating

        Raises:
            ValueError: If artifact_id is empty or rating is not 1-5
            RateLimitExceededError: If rate limit is exceeded

        Example:
            >>> manager = RatingManager()
            >>> rating = manager.add_rating("skill:canvas", 5, "Excellent!", share=True)
            >>> print(f"Rating ID: {rating.id}")
        """
        # Validate inputs
        if not artifact_id or not artifact_id.strip():
            raise ValueError("artifact_id must be a non-empty string")

        if not 1 <= rating <= 5:
            raise ValueError(f"rating must be 1-5, got {rating}")

        # Check rate limit
        if not self.can_rate(artifact_id, max_per_day):
            raise RateLimitExceededError(
                f"Rate limit exceeded: maximum {max_per_day} ratings per artifact per day"
            )

        # Create ORM object
        session = get_session()
        try:
            orm_rating = OrmUserRating(
                artifact_id=artifact_id.strip(),
                rating=rating,
                feedback=feedback,
                share_with_community=share,
                rated_at=datetime.utcnow(),
            )

            session.add(orm_rating)
            session.commit()
            session.refresh(orm_rating)

            # Convert to domain model
            return UserRating(
                id=orm_rating.id,
                artifact_id=orm_rating.artifact_id,
                rating=orm_rating.rating,
                feedback=orm_rating.feedback,
                share_with_community=orm_rating.share_with_community,
                rated_at=orm_rating.rated_at,
            )
        except IntegrityError as e:
            session.rollback()
            raise ValueError(f"Failed to add rating: {e}")
        finally:
            session.close()

    def get_ratings(self, artifact_id: str) -> list[UserRating]:
        """Get all ratings for an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            List of UserRating domain objects, ordered by most recent first

        Example:
            >>> manager = RatingManager()
            >>> ratings = manager.get_ratings("skill:canvas")
            >>> for rating in ratings:
            ...     print(f"{rating.rating}/5: {rating.feedback}")
        """
        if not artifact_id or not artifact_id.strip():
            return []

        session = get_session()
        try:
            orm_ratings = (
                session.query(OrmUserRating)
                .filter(OrmUserRating.artifact_id == artifact_id.strip())
                .order_by(OrmUserRating.rated_at.desc())
                .all()
            )

            # Convert to domain models
            return [
                UserRating(
                    id=r.id,
                    artifact_id=r.artifact_id,
                    rating=r.rating,
                    feedback=r.feedback,
                    share_with_community=r.share_with_community,
                    rated_at=r.rated_at,
                )
                for r in orm_ratings
            ]
        finally:
            session.close()

    def get_average_rating(self, artifact_id: str) -> float | None:
        """Get average rating for an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Average rating as float, or None if no ratings exist

        Example:
            >>> manager = RatingManager()
            >>> avg = manager.get_average_rating("skill:canvas")
            >>> if avg:
            ...     print(f"Average: {avg:.2f}/5.00")
        """
        if not artifact_id or not artifact_id.strip():
            return None

        session = get_session()
        try:
            from sqlalchemy import func

            result = (
                session.query(func.avg(OrmUserRating.rating))
                .filter(OrmUserRating.artifact_id == artifact_id.strip())
                .scalar()
            )

            # scalar() returns None if no rows, or Decimal if using PostgreSQL
            return float(result) if result is not None else None
        finally:
            session.close()

    def export_ratings(self, shared_only: bool = True) -> list[dict]:
        """Export ratings for community sharing.

        Args:
            shared_only: If True, only export ratings where share_with_community=True
                        If False, export all ratings (default: True)

        Returns:
            List of rating dictionaries suitable for JSON export

        Example:
            >>> manager = RatingManager()
            >>> shared = manager.export_ratings(shared_only=True)
            >>> import json
            >>> print(json.dumps(shared, indent=2))
        """
        session = get_session()
        try:
            query = session.query(OrmUserRating)

            if shared_only:
                query = query.filter(OrmUserRating.share_with_community == True)

            orm_ratings = query.order_by(OrmUserRating.rated_at.desc()).all()

            # Convert to dicts
            return [
                {
                    "artifact_id": r.artifact_id,
                    "rating": r.rating,
                    "feedback": r.feedback,
                    "rated_at": r.rated_at.isoformat() if r.rated_at else None,
                }
                for r in orm_ratings
            ]
        finally:
            session.close()

    def delete_rating(self, rating_id: int) -> bool:
        """Delete a rating by ID.

        Args:
            rating_id: Rating identifier

        Returns:
            True if rating was deleted, False if not found

        Example:
            >>> manager = RatingManager()
            >>> if manager.delete_rating(123):
            ...     print("Rating deleted")
            ... else:
            ...     print("Rating not found")
        """
        session = get_session()
        try:
            orm_rating = session.query(OrmUserRating).filter(OrmUserRating.id == rating_id).first()

            if orm_rating is None:
                return False

            session.delete(orm_rating)
            session.commit()
            return True
        finally:
            session.close()

    def update_rating(
        self,
        rating_id: int,
        rating: int | None = None,
        feedback: str | None = None,
    ) -> UserRating:
        """Update an existing rating.

        Args:
            rating_id: Rating identifier
            rating: New rating value (1-5), or None to keep current
            feedback: New feedback text, or None to keep current

        Returns:
            Updated UserRating domain object

        Raises:
            RatingNotFoundError: If rating_id doesn't exist
            ValueError: If rating is not 1-5

        Example:
            >>> manager = RatingManager()
            >>> updated = manager.update_rating(123, rating=4, feedback="Good!")
            >>> print(f"Updated to {updated.rating}/5")
        """
        # Validate rating if provided
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError(f"rating must be 1-5, got {rating}")

        session = get_session()
        try:
            orm_rating = session.query(OrmUserRating).filter(OrmUserRating.id == rating_id).first()

            if orm_rating is None:
                raise RatingNotFoundError(f"Rating with id {rating_id} not found")

            # Update fields if provided
            if rating is not None:
                orm_rating.rating = rating
            if feedback is not None:
                orm_rating.feedback = feedback

            session.commit()
            session.refresh(orm_rating)

            # Convert to domain model
            return UserRating(
                id=orm_rating.id,
                artifact_id=orm_rating.artifact_id,
                rating=orm_rating.rating,
                feedback=orm_rating.feedback,
                share_with_community=orm_rating.share_with_community,
                rated_at=orm_rating.rated_at,
            )
        finally:
            session.close()

    def can_rate(self, artifact_id: str, max_per_day: int = 5) -> bool:
        """Check if user can rate an artifact (rate limiting).

        Args:
            artifact_id: Artifact identifier
            max_per_day: Maximum ratings per artifact per day (default: 5)

        Returns:
            True if user can add another rating, False if limit reached

        Example:
            >>> manager = RatingManager()
            >>> if manager.can_rate("skill:canvas", max_per_day=5):
            ...     rating = manager.add_rating("skill:canvas", 5)
        """
        if not artifact_id or not artifact_id.strip():
            return False

        # Calculate cutoff time (24 hours ago)
        cutoff = datetime.utcnow() - timedelta(days=1)

        session = get_session()
        try:
            # Count ratings for this artifact in last 24 hours
            count = (
                session.query(OrmUserRating)
                .filter(
                    OrmUserRating.artifact_id == artifact_id.strip(),
                    OrmUserRating.rated_at >= cutoff,
                )
                .count()
            )

            return count < max_per_day
        finally:
            session.close()
