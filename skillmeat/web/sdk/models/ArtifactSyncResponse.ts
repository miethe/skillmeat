/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConflictInfo } from './ConflictInfo';
/**
 * Response schema for artifact sync operation.
 */
export type ArtifactSyncResponse = {
    /**
     * Whether sync operation succeeded
     */
    success: boolean;
    /**
     * Human-readable result message
     */
    message: string;
    /**
     * Name of synced artifact
     */
    artifact_name: string;
    /**
     * Type of artifact (skill/command/agent)
     */
    artifact_type: string;
    /**
     * List of conflicts detected during sync (if any)
     */
    conflicts?: (Array<ConflictInfo> | null);
    /**
     * New version after sync (if applicable)
     */
    updated_version?: (string | null);
    /**
     * Number of files synced
     */
    synced_files_count?: (number | null);
};

