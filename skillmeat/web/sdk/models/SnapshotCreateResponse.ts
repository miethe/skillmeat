/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SnapshotResponse } from './SnapshotResponse';
/**
 * Response after creating a snapshot.
 *
 * Returns the newly created snapshot with confirmation flag.
 */
export type SnapshotCreateResponse = {
    /**
     * Newly created snapshot metadata
     */
    snapshot: SnapshotResponse;
    /**
     * Confirmation that snapshot was created
     */
    created?: boolean;
};

