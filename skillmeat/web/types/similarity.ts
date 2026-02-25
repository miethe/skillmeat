/**
 * Similarity Detection Types for SkillMeat
 *
 * These types mirror the backend DTOs for the similar artifacts feature:
 * - SimilarArtifactDTO
 * - SimilarityBreakdownDTO
 * - SimilarArtifactsResponse
 *
 * Field names use snake_case to match JSON response keys exactly.
 * See: GET /api/v1/artifacts/{id}/similar
 *
 * Note: Named SimilarityMatchType (not MatchType) to avoid collision with
 * the MatchType exported by types/discovery.ts (collection membership matching).
 */

/**
 * Match strength classification for a similarity result.
 *
 * - exact: Near-identical content (score ~1.0)
 * - near_duplicate: Very high similarity, minor differences
 * - similar: Meaningful similarity, same domain/purpose
 * - related: Loose similarity, shared concepts or keywords
 */
export type SimilarityMatchType = 'exact' | 'near_duplicate' | 'similar' | 'related';

/**
 * Search scope for similar artifact queries.
 *
 * - collection: Search only the user's personal collection
 * - marketplace: Search marketplace artifacts only
 * - all: Search across both collection and marketplace
 */
export type SimilaritySource = 'collection' | 'marketplace' | 'all';

/**
 * Individual score components from the similarity analysis pipeline.
 *
 * All required scores are in the range [0.0, 1.0].
 * semantic_score is null when a semantic/embedding model is unavailable.
 */
export interface SimilarityBreakdown {
  /** Content similarity score (file content comparison) */
  content_score: number;
  /** Structure similarity score (artifact structure/schema comparison) */
  structure_score: number;
  /** Metadata similarity score (name, description, tags comparison) */
  metadata_score: number;
  /** Keyword/TF-IDF similarity score */
  keyword_score: number;
  /** Semantic similarity score via embeddings; null if unavailable */
  semantic_score: number | null;
}

/**
 * A similar artifact with its similarity score and detailed breakdown.
 *
 * Mirrors SimilarArtifactDTO from the backend.
 */
export interface SimilarArtifact {
  /** Unique identifier of the similar artifact */
  artifact_id: string;
  /** Display name of the similar artifact */
  name: string;
  /** Type of the artifact (skill, command, agent, mcp, hook) */
  artifact_type: string;
  /** Source repository or path; null for locally-created artifacts */
  source: string | null;
  /** Overall similarity score in the range [0.0, 1.0] */
  composite_score: number;
  /** Match strength classification */
  match_type: SimilarityMatchType;
  /** Individual score components from the similarity analysis */
  breakdown: SimilarityBreakdown;
}

/**
 * Response envelope for the GET /api/v1/artifacts/{id}/similar endpoint.
 *
 * Mirrors SimilarArtifactsResponse from the backend.
 * Items are ordered by composite_score descending.
 */
export interface SimilarArtifactsResponse {
  /** Canonical identifier of the source artifact that was queried */
  artifact_id: string;
  /** Similar artifacts ordered by composite score descending */
  items: SimilarArtifact[];
  /** Total number of similar artifacts returned */
  total: number;
}

/**
 * Options for the useSimilarArtifacts hook.
 *
 * All fields are optional; the hook applies sensible defaults.
 */
export interface SimilarArtifactsOptions {
  /** Maximum number of similar artifacts to return */
  limit?: number;
  /** Minimum composite score threshold (0.0–1.0) */
  minScore?: number;
  /** Search scope: collection, marketplace, or all */
  source?: SimilaritySource;
  /** Whether the query is enabled (default: true) */
  enabled?: boolean;
}
