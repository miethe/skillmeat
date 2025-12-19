/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ImportStatus } from './ImportStatus';
/**
 * Result for a single imported artifact.
 */
export type ImportResult = {
    /**
     * ID of the artifact (type:name)
     */
    artifact_id: string;
    /**
     * Import status: success, skipped, or failed
     */
    status: ImportStatus;
    /**
     * Human-readable result message
     */
    message: string;
    /**
     * Error message (if status=failed)
     */
    error?: (string | null);
    /**
     * Reason artifact was skipped (if status=skipped)
     */
    skip_reason?: (string | null);
    /**
     * Backward compatibility: returns True if status is SUCCESS.
     */
    readonly success: boolean;
};

