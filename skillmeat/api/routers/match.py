"""Match API router for artifact search/discovery endpoints.

This module provides endpoints for searching and matching artifacts using
the confidence scoring system with semantic + keyword matching.
"""

import logging
from datetime import datetime, timezone
from typing import List, Tuple

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.dependencies import ArtifactManagerDep, CollectionManagerDep
from skillmeat.api.schemas.match import (
    MatchedArtifact,
    MatchResponse,
    ScoreBreakdown,
)
from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.service import ScoringService
from skillmeat.observability.tracing import trace_operation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/match",
    tags=["match"],
)


@router.get(
    "/",
    response_model=MatchResponse,
    summary="Match artifacts against query",
    description="""
    Search for artifacts matching a query using confidence scoring.

    This endpoint uses semantic embeddings when available, with graceful
    degradation to keyword-only matching. Results are sorted by confidence
    score (descending).

    The confidence score combines:
    - Trust score: Source reputation/verification
    - Quality score: Community ratings and metrics
    - Match score: Semantic + keyword relevance to query

    Semantic matching provides better results but requires API key.
    Keyword-only mode works without configuration.
    """,
    responses={
        200: {"description": "Matches found (may be empty list)"},
        400: {"description": "Invalid query (empty or too short)"},
        500: {"description": "Scoring service error"},
    },
)
async def match_artifacts(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    q: str = Query(
        ...,
        min_length=1,
        description="Search query",
        examples=["pdf tool"],
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum results to return",
    ),
    min_confidence: float = Query(
        0.0,
        ge=0.0,
        le=100.0,
        description="Minimum confidence score threshold",
    ),
    include_breakdown: bool = Query(
        False,
        description="Include detailed score breakdown for each match",
    ),
) -> MatchResponse:
    """Match artifacts against search query.

    Args:
        q: Search query string
        limit: Maximum number of results to return
        min_confidence: Minimum confidence threshold (0-100)
        include_breakdown: Whether to include score breakdown
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency

    Returns:
        MatchResponse with matched artifacts sorted by confidence

    Raises:
        HTTPException 400: Empty or invalid query
        HTTPException 500: Scoring service error
    """
    # Validate query
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    with trace_operation(
        "match.search",
        query=q,
        limit=limit,
        min_confidence=min_confidence,
        include_breakdown=include_breakdown,
    ) as span:
        try:
            # Get all artifacts from collection
            # TODO: This loads all artifacts - optimize for large collections
            artifacts = artifact_mgr.list_artifacts()
            span.set_attribute("total_artifacts", len(artifacts))
            span.add_event("artifacts_loaded")

            # Convert to format expected by ScoringService
            artifact_tuples: List[Tuple[str, ArtifactMetadata]] = [
                (
                    artifact.name,
                    artifact.metadata if artifact.metadata else ArtifactMetadata(),
                )
                for artifact in artifacts
            ]

            # Initialize scoring service
            scoring_service = ScoringService(
                enable_semantic=True,  # Try semantic, fall back if unavailable
                fallback_to_keyword=True,
            )

            # Score artifacts
            result = await scoring_service.score_artifacts(
                query=q,
                artifacts=artifact_tuples,
            )

            span.set_attribute("used_semantic", result.used_semantic)
            span.set_attribute("degraded", result.degraded)
            if result.degradation_reason:
                span.set_attribute("degradation_reason", result.degradation_reason)
            span.add_event("scoring_complete")

            # Filter by min_confidence
            filtered_scores = [
                score for score in result.scores if score.confidence >= min_confidence
            ]
            span.set_attribute("matches_after_filter", len(filtered_scores))

            # Sort by confidence descending
            sorted_scores = sorted(
                filtered_scores,
                key=lambda s: s.confidence,
                reverse=True,
            )

            # Build matched artifacts
            matches: List[MatchedArtifact] = []
            for score in sorted_scores[:limit]:
                # Find original artifact for metadata
                artifact = next(
                    (a for a in artifacts if a.name == score.artifact_id),
                    None,
                )

                # Build matched artifact
                matched = MatchedArtifact(
                    artifact_id=f"{artifact.type.value}:{score.artifact_id}"
                    if artifact
                    else score.artifact_id,
                    name=score.artifact_id,
                    artifact_type=artifact.type.value if artifact else "unknown",
                    confidence=score.confidence,
                    title=artifact.metadata.title if artifact and artifact.metadata else None,
                    description=artifact.metadata.description if artifact and artifact.metadata else None,
                )

                # Add breakdown if requested
                if include_breakdown:
                    matched.breakdown = ScoreBreakdown(
                        trust_score=score.trust_score,
                        quality_score=score.quality_score,
                        match_score=score.match_score,
                        semantic_used=result.used_semantic,
                        context_boost_applied=False,  # TODO: Track context boost
                    )

                matches.append(matched)

            span.set_attribute("matches_returned", len(matches))
            span.add_event("matches_prepared")

            return MatchResponse(
                query=q,
                matches=matches,
                total=len(filtered_scores),
                limit=limit,
                min_confidence=min_confidence,
                schema_version="1.0.0",
                scored_at=datetime.now(timezone.utc),
                degraded=result.degraded,
                degradation_reason=result.degradation_reason,
            )

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.exception(f"Failed to match artifacts for query '{q}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to match artifacts: {str(e)}",
            )
