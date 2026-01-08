"""Ratings API router for artifact scoring endpoints.

This module provides endpoints for submitting and retrieving artifact ratings,
as well as calculating confidence scores.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.schemas.scoring import (
    ArtifactScoreResponse,
    UserRatingRequest,
    UserRatingResponse,
)
from skillmeat.core.scoring import QualityScorer
from skillmeat.observability.tracing import trace_operation
from skillmeat.storage.rating_store import (
    RatingManager,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ratings",
    tags=["ratings"],
)


@router.post(
    "/artifacts/{artifact_id}/ratings",
    response_model=UserRatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit artifact rating",
    description="""
    Submit a rating for an artifact (1-5 scale).

    Rate limits apply: maximum 5 ratings per artifact per user per day.
    Ratings can optionally be shared with the community for aggregate scoring.
    """,
    responses={
        201: {"description": "Rating submitted successfully"},
        400: {"description": "Invalid rating value"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def submit_rating(
    artifact_id: str,
    request: UserRatingRequest,
) -> UserRatingResponse:
    """Submit a rating for an artifact.

    Args:
        artifact_id: Artifact identifier (e.g., "skill:canvas-design")
        request: Rating request with rating value and optional feedback

    Returns:
        UserRatingResponse with rating confirmation

    Raises:
        HTTPException 400: Invalid rating value
        HTTPException 429: Rate limit exceeded
    """
    with trace_operation(
        "rating.submit",
        artifact_id=artifact_id,
        rating=request.rating,
        shared=request.share_with_community,
    ) as span:
        try:
            manager = RatingManager()

            user_rating = manager.add_rating(
                artifact_id=artifact_id,
                rating=request.rating,
                feedback=request.feedback,
                share=request.share_with_community,
            )

            span.set_attribute("rating_id", user_rating.id)
            span.add_event("rating_stored")

            return UserRatingResponse(
                id=user_rating.id,
                artifact_id=user_rating.artifact_id,
                rating=user_rating.rating,
                feedback=user_rating.feedback,
                share_with_community=user_rating.share_with_community,
                rated_at=user_rating.rated_at or datetime.utcnow(),
                schema_version="1.0.0",
            )

        except RateLimitExceededError as e:
            span.add_event("rate_limit_exceeded")
            logger.warning(f"Rate limit exceeded for artifact {artifact_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
            )
        except ValueError as e:
            span.add_event("validation_error", {"error": str(e)})
            logger.warning(f"Invalid rating for artifact {artifact_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            logger.exception(f"Failed to submit rating for artifact {artifact_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit rating",
            )


@router.get(
    "/artifacts/{artifact_id}/scores",
    response_model=ArtifactScoreResponse,
    summary="Get artifact scores",
    description="""
    Get confidence scores for an artifact.

    Returns trust score, quality score, and composite confidence.
    Match score is only included when querying with a search context.
    """,
    responses={
        200: {"description": "Scores retrieved successfully"},
        404: {"description": "Artifact not found"},
    },
)
async def get_artifact_scores(
    artifact_id: str,
    source_type: Optional[str] = Query(
        default="unknown",
        description="Source type for trust scoring (official, verified, github, local, unknown)",
    ),
    match_score: Optional[float] = Query(
        default=None,
        ge=0,
        le=100,
        description="Query match score from search context (0-100)",
    ),
) -> ArtifactScoreResponse:
    """Get confidence scores for an artifact.

    Args:
        artifact_id: Artifact identifier
        source_type: Source type for trust scoring
        match_score: Optional match score from search context

    Returns:
        ArtifactScoreResponse with all score components
    """
    with trace_operation(
        "score.fetch",
        artifact_id=artifact_id,
        source_type=source_type,
        has_match_score=match_score is not None,
    ) as span:
        try:
            scorer = QualityScorer()

            result = scorer.calculate_confidence_score(
                artifact_id=artifact_id,
                source_type=source_type,
                match_score=match_score,
            )

            span.set_attribute("confidence", result["confidence"])
            span.set_attribute("quality_score", result["quality_score"])
            span.add_event("scores_calculated")

            return ArtifactScoreResponse(
                artifact_id=result["artifact_id"],
                trust_score=result["trust_score"],
                quality_score=result["quality_score"],
                match_score=result["match_score"],
                confidence=result["confidence"],
                schema_version=result["schema_version"],
                last_updated=datetime.utcnow(),
            )

        except Exception as e:
            logger.exception(f"Failed to get scores for artifact {artifact_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve artifact scores",
            )


@router.get(
    "/artifacts/{artifact_id}/ratings",
    summary="List artifact ratings",
    description="Get all ratings for an artifact, ordered by most recent first.",
    responses={
        200: {"description": "Ratings retrieved successfully"},
    },
)
async def list_artifact_ratings(
    artifact_id: str,
    limit: int = Query(
        default=50, ge=1, le=100, description="Maximum ratings to return"
    ),
):
    """List all ratings for an artifact.

    Args:
        artifact_id: Artifact identifier
        limit: Maximum number of ratings to return

    Returns:
        List of ratings with average
    """
    with trace_operation(
        "rating.list",
        artifact_id=artifact_id,
        limit=limit,
    ) as span:
        try:
            manager = RatingManager()

            ratings = manager.get_ratings(artifact_id)
            avg_rating = manager.get_average_rating(artifact_id)

            span.set_attribute("rating_count", len(ratings))
            span.set_attribute("average_rating", avg_rating)
            span.add_event("ratings_fetched")

            # Convert to response format
            rating_list = [
                {
                    "id": r.id,
                    "rating": r.rating,
                    "feedback": r.feedback,
                    "shared": r.share_with_community,
                    "rated_at": r.rated_at.isoformat() if r.rated_at else None,
                }
                for r in ratings[:limit]
            ]

            return {
                "artifact_id": artifact_id,
                "ratings": rating_list,
                "total": len(ratings),
                "average_rating": round(avg_rating, 2) if avg_rating else None,
                "schema_version": "1.0.0",
            }

        except Exception as e:
            logger.exception(f"Failed to list ratings for artifact {artifact_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve ratings",
            )
