/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Information about a modified artifact in a project.
 */
export type ModifiedArtifactInfo = {
    /**
     * Artifact name
     */
    artifact_name: string;
    /**
     * Artifact type
     */
    artifact_type: string;
    /**
     * SHA-256 hash at deployment time
     */
    deployed_sha: string;
    /**
     * Current SHA-256 hash
     */
    current_sha: string;
    /**
     * Timestamp when modification was first detected
     */
    modification_detected_at?: (string | null);
    /**
     * Origin of the change (deployment/sync/local_modification)
     */
    change_origin?: (string | null);
    /**
     * Hash at deployment time (baseline for three-way merge)
     */
    baseline_hash?: (string | null);
};

