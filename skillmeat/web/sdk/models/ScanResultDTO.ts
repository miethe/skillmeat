/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DetectedArtifact } from './DetectedArtifact';
/**
 * Result of scanning a GitHub repository.
 *
 * Contains scan statistics, duration, and any errors encountered.
 */
export type ScanResultDTO = {
  /**
   * ID of the source that was scanned
   */
  source_id: string;
  /**
   * Scan result status
   */
  status: 'success' | 'error' | 'partial';
  /**
   * Total number of artifacts detected
   */
  artifacts_found: number;
  /**
   * List of detected artifacts
   */
  artifacts?: Array<DetectedArtifact>;
  /**
   * Number of new artifacts detected
   */
  new_count: number;
  /**
   * Number of artifacts with changes detected
   */
  updated_count: number;
  /**
   * Number of artifacts no longer present
   */
  removed_count: number;
  /**
   * Number of artifacts with no changes
   */
  unchanged_count: number;
  /**
   * Scan duration in milliseconds
   */
  scan_duration_ms: number;
  /**
   * Number of duplicate artifacts detected within this source and excluded from catalog. These are artifacts with identical content (same SHA256 hash) found multiple times in the same repository scan.
   */
  duplicates_within_source?: number;
  /**
   * Number of duplicate artifacts detected that already exist in the collection (from other sources or previous scans) and excluded from catalog. These are artifacts matching existing collection entries by content hash.
   */
  duplicates_cross_source?: number;
  /**
   * Total number of artifacts initially detected before deduplication. Equals: total_unique + duplicates_within_source + duplicates_cross_source
   */
  total_detected?: number;
  /**
   * Number of unique artifacts after deduplication that were added to the catalog. These are new artifacts not previously seen in this source or the existing collection.
   */
  total_unique?: number;
  /**
   * List of error messages encountered during scan
   */
  errors?: Array<string>;
  /**
   * Timestamp when scan completed
   */
  scanned_at: string;
  /**
   * Entry IDs of imported artifacts with upstream changes (SHA changed since import)
   */
  updated_imports?: Array<string>;
  /**
   * Number of imported/excluded entries preserved during merge (their status and import metadata retained)
   */
  preserved_count?: number;
};
