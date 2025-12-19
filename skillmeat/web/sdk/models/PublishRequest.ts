/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for publishing a bundle to marketplace.
 *
 * Specifies the bundle path and additional metadata for the listing.
 */
export type PublishRequest = {
    /**
     * Path to the bundle file to publish
     */
    bundle_path: string;
    /**
     * Broker to publish to
     */
    broker?: string;
    /**
     * Additional metadata (description, tags, etc.)
     */
    metadata?: Record<string, any>;
};

