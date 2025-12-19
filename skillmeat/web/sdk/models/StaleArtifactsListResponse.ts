/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StaleArtifactResponse } from './StaleArtifactResponse';
/**
 * List of stale artifacts.
 *
 * Attributes:
 * items: List of stale artifacts
 * total: Total number of stale artifacts
 */
export type StaleArtifactsListResponse = {
    /**
     * List of stale artifacts
     */
    items: Array<StaleArtifactResponse>;
    /**
     * Total number of stale artifacts
     */
    total: number;
};

