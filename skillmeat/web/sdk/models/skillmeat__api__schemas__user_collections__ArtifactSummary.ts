/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactGroupMembership } from './ArtifactGroupMembership';
/**
 * Lightweight artifact summary for collection listings.
 *
 * When include_groups=true query parameter is used, the groups field
 * will be populated with group membership information.
 */
export type skillmeat__api__schemas__user_collections__ArtifactSummary = {
    /**
     * Artifact name
     */
    name: string;
    /**
     * Artifact type (skill, command, agent, etc.)
     */
    type: string;
    /**
     * Current version
     */
    version?: (string | null);
    /**
     * Source specification
     */
    source: string;
    /**
     * Groups this artifact belongs to (only populated when include_groups=true)
     */
    groups?: (Array<ArtifactGroupMembership> | null);
};

