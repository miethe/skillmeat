/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidationIssueResponse } from './ValidationIssueResponse';
/**
 * Response from bundle validation.
 */
export type BundleValidationResponse = {
    /**
     * Whether bundle is valid
     */
    is_valid: boolean;
    /**
     * Validation issues found
     */
    issues?: Array<ValidationIssueResponse>;
    /**
     * SHA-256 hash of bundle
     */
    bundle_hash?: (string | null);
    /**
     * Number of artifacts in bundle
     */
    artifact_count?: number;
    /**
     * Total bundle size in bytes
     */
    total_size_bytes?: number;
    /**
     * Human-readable summary
     */
    summary?: string;
};

