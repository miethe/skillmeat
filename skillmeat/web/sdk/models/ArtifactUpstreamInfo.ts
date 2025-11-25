/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Upstream tracking information for an artifact.
 */
export type ArtifactUpstreamInfo = {
    /**
     * Whether upstream tracking is enabled
     */
    tracking_enabled: boolean;
    /**
     * Current installed version SHA
     */
    current_sha?: (string | null);
    /**
     * Latest upstream version SHA
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
     * Drift status (none, modified, deleted, added)
     */
    drift_status?: (string | null);
};

