/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScoreBreakdown } from './ScoreBreakdown';
/**
 * Single matched artifact with confidence score.
 *
 * Represents an artifact that matched the search query with its
 * relevance score and optional breakdown.
 */
export type MatchedArtifact = {
    /**
     * Artifact composite key (type:name)
     */
    artifact_id: string;
    /**
     * Artifact name
     */
    name: string;
    /**
     * Type of artifact (skill, command, agent, etc.)
     */
    artifact_type: string;
    /**
     * Composite confidence score (0-100)
     */
    confidence: number;
    /**
     * Human-readable title from artifact metadata
     */
    title?: (string | null);
    /**
     * Brief description from artifact metadata
     */
    description?: (string | null);
    /**
     * Detailed score breakdown (only if requested)
     */
    breakdown?: (ScoreBreakdown | null);
};

