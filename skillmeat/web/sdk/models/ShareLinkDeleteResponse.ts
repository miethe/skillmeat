/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for share link deletion/revocation.
 */
export type ShareLinkDeleteResponse = {
    /**
     * Whether deletion succeeded
     */
    success: boolean;
    /**
     * Bundle unique identifier
     */
    bundle_id: string;
    /**
     * Status message
     */
    message: string;
};

