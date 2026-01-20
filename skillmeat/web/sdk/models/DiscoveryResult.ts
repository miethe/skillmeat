/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DiscoveredArtifact } from './DiscoveredArtifact';
/**
 * Result of artifact discovery scan.
 */
export type DiscoveryResult = {
    /**
     * Total number of artifacts discovered
     */
    discovered_count: number;
    /**
     * Number of artifacts not yet imported (filtered by manifest)
     */
    importable_count: number;
    /**
     * List of discovered artifacts (filtered if manifest provided)
     */
    artifacts?: Array<DiscoveredArtifact>;
    /**
     * Per-artifact errors encountered during scan
     */
    errors?: Array<string>;
    /**
     * Scan duration in milliseconds
     */
    scan_duration_ms: number;
};

