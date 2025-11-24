/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for upstream status check.
 *
 * Provides detailed information about available updates and
 * local modifications.
 */
export type ArtifactUpstreamResponse = {
    /**
     * Artifact composite key
     */
    artifact_id: string;
    /**
     * Whether upstream tracking is enabled
     */
    tracking_enabled: boolean;
    /**
     * Current installed version
     */
    current_version: string;
    /**
     * Current version SHA
     */
    current_sha: string;
    /**
     * Latest upstream version
     */
    upstream_version?: (string | null);
    /**
     * Latest upstream SHA
     */
    upstream_sha?: (string | null);
    /**
     * Whether an update is available
     */
    update_available: boolean;
    /**
     * Whether local modifications exist
     */
    has_local_modifications: boolean;
    /**
     * Timestamp of last upstream check
     */
    last_checked: string;
};

