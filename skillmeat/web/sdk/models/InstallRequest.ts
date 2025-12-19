/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for installing a marketplace listing.
 *
 * Specifies the listing to install and conflict resolution strategy.
 */
export type InstallRequest = {
    /**
     * Listing ID to install
     */
    listing_id: string;
    /**
     * Broker name (auto-detect if not provided)
     */
    broker?: (string | null);
    /**
     * Conflict resolution strategy
     */
    strategy?: 'merge' | 'fork' | 'skip';
};

