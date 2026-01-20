/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactPositionUpdate } from './ArtifactPositionUpdate';
/**
 * Request schema for bulk reordering artifacts within a group.
 */
export type ReorderArtifactsRequest = {
    /**
     * List of artifacts with their new positions
     */
    artifacts: Array<ArtifactPositionUpdate>;
};

