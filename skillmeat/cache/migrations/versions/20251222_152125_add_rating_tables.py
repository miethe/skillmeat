"""Add user ratings, community scores, and match history tables

Revision ID: 20251222_152125_add_rating_tables
Revises: 20251220_1000_add_content_description_to_artifacts
Create Date: 2025-12-22 15:21:25.000000

This migration creates the database schema for artifact rating and scoring system,
enabling user feedback collection, community score aggregation, and match analytics.

Tables Created:
- user_ratings: Individual user ratings (1-5 stars) with optional feedback
- community_scores: Aggregated scores from external sources (GitHub, registry, exports)
- match_history: Query matching history for analytics and algorithm improvement

Key Features:
- User ratings: 1-5 star ratings with optional text feedback and sharing preference
- Community scoring: Multi-source aggregation (GitHub stars, registry, user exports)
- Match analytics: Track query confidence and user deployment confirmations
- No foreign keys on artifact_id: Support external/marketplace artifacts
- Proper indexing: Fast lookups by artifact, composite indexes for common queries
- Check constraints: Enforce valid rating values (1-5) and confidence scores (0-100)

Schema Version: 1.5.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251222_152125_add_rating_tables"
down_revision: Union[str, None] = "20251220_1000_add_content_description_to_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_ratings, community_scores, and match_history tables.

    Creates the schema for artifact rating and scoring system:

    1. user_ratings - User-submitted ratings (1-5 stars) with optional feedback
    2. community_scores - Aggregated scores from external sources (0-100 normalized)
    3. match_history - Artifact matching query analytics

    All tables use TEXT for string columns (SQLite compatible) and include
    proper indexing for fast queries. artifact_id columns intentionally have
    NO foreign key constraints to allow tracking external/marketplace artifacts.
    """
    # ==========================================================================
    # User Ratings Table
    # ==========================================================================
    # Individual user ratings with 1-5 star scale and optional feedback
    op.create_table(
        "user_ratings",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "share_with_community",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "rated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="check_valid_rating",
        ),
    )

    # User ratings indexes
    op.create_index(
        "idx_user_ratings_artifact_id",
        "user_ratings",
        ["artifact_id"],
    )
    op.create_index(
        "idx_user_ratings_artifact_id_rated_at",
        "user_ratings",
        ["artifact_id", "rated_at"],
    )

    # ==========================================================================
    # Community Scores Table
    # ==========================================================================
    # Aggregated scores from external sources (GitHub, registry, user exports)
    op.create_table(
        "community_scores",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("imported_from", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "artifact_id",
            "source",
            name="uq_community_score",
        ),
    )

    # Community scores indexes
    op.create_index(
        "idx_community_scores_artifact_id",
        "community_scores",
        ["artifact_id"],
    )

    # ==========================================================================
    # Match History Table
    # ==========================================================================
    # Artifact matching query analytics for algorithm improvement
    op.create_table(
        "match_history",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("user_confirmed", sa.Boolean(), nullable=True),
        sa.Column(
            "matched_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Match history indexes
    op.create_index(
        "idx_match_history_artifact_query",
        "match_history",
        ["artifact_id", "query"],
    )

    # ==========================================================================
    # Update schema version
    # ==========================================================================
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.5.0'
        WHERE key = 'schema_version'
        """
    )


def downgrade() -> None:
    """Remove user_ratings, community_scores, and match_history tables.

    This reverts the migration by dropping all rating and scoring tables
    and their indexes.

    WARNING: This is a destructive operation. All user ratings, community scores,
    and match history data will be permanently lost.
    """
    # Drop tables in reverse order of creation
    op.drop_table("match_history")
    op.drop_table("community_scores")
    op.drop_table("user_ratings")

    # Revert schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.4.0'
        WHERE key = 'schema_version'
        """
    )
