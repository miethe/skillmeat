/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to update a segment's approval status.
 *
 * Used to approve or reject a path segment for tag creation.
 */
export type UpdateSegmentStatusRequest = {
    /**
     * Original segment value to update
     */
    segment: string;
    /**
     * New status (approved or rejected)
     */
    status: 'approved' | 'rejected';
};

