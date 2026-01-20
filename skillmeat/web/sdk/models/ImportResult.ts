/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ErrorReasonCode } from './ErrorReasonCode';
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
     * Path to the artifact (for local imports)
     */
    path?: (string | null);
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
     * Machine-readable reason code for failures/skips. Use this for programmatic error handling.
     */
    reason_code?: (ErrorReasonCode | null);
    /**
     * Reason artifact was skipped (if status=skipped)
     */
    skip_reason?: (string | null);
    /**
     * Additional details about the error, such as line numbers for YAML parse errors or specific validation failures.
     */
    details?: (string | null);
    /**
     * Number of path-based tags applied to this artifact during import. Only non-zero when apply_path_tags=True and approved segments exist.
     */
    tags_applied?: number;
    /**
     * Backward compatibility: returns True if status is SUCCESS.
     */
    readonly success: boolean;
};

