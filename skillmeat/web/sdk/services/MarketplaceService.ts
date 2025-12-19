/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BrokerListResponse } from '../models/BrokerListResponse';
import type { InstallRequest } from '../models/InstallRequest';
import type { InstallResponse } from '../models/InstallResponse';
import type { ListingDetailResponse } from '../models/ListingDetailResponse';
import type { ListingsPageResponse } from '../models/ListingsPageResponse';
import type { PublishRequest } from '../models/PublishRequest';
import type { PublishResponse } from '../models/PublishResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MarketplaceService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Browse marketplace listings
     * Retrieve paginated marketplace listings with optional filtering
     * @returns ListingsPageResponse Successfully retrieved listings
     * @throws ApiError
     */
    public listListingsApiV1MarketplaceListingsGet({
        broker,
        query,
        tags,
        license,
        publisher,
        cursor,
        limit = 50,
    }: {
        /**
         * Filter by broker name
         */
        broker?: (string | null),
        /**
         * Search term
         */
        query?: (string | null),
        /**
         * Comma-separated tags
         */
        tags?: (string | null),
        /**
         * Filter by license
         */
        license?: (string | null),
        /**
         * Filter by publisher
         */
        publisher?: (string | null),
        /**
         * Pagination cursor
         */
        cursor?: (string | null),
        /**
         * Items per page (max 100)
         */
        limit?: number,
    }): CancelablePromise<ListingsPageResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/listings',
            query: {
                'broker': broker,
                'query': query,
                'tags': tags,
                'license': license,
                'publisher': publisher,
                'cursor': cursor,
                'limit': limit,
            },
            errors: {
                400: `Invalid request parameters`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
                500: `Internal server error`,
                503: `Broker unavailable`,
            },
        });
    }
    /**
     * Get listing details
     * Retrieve detailed information for a specific marketplace listing
     * @returns ListingDetailResponse Successfully retrieved listing
     * @throws ApiError
     */
    public getListingDetailApiV1MarketplaceListingsListingIdGet({
        listingId,
    }: {
        listingId: string,
    }): CancelablePromise<ListingDetailResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/listings/{listing_id}',
            path: {
                'listing_id': listingId,
            },
            errors: {
                404: `Listing not found`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
                500: `Internal server error`,
                503: `Broker unavailable`,
            },
        });
    }
    /**
     * Install marketplace listing
     * Download and install a bundle from the marketplace
     * @returns InstallResponse Successfully installed listing
     * @throws ApiError
     */
    public installListingApiV1MarketplaceInstallPost({
        requestBody,
    }: {
        requestBody: InstallRequest,
    }): CancelablePromise<InstallResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/install',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Listing not found`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Publish bundle to marketplace
     * Publish a signed bundle to the marketplace for distribution
     * @returns PublishResponse Successfully published bundle
     * @throws ApiError
     */
    public publishBundleApiV1MarketplacePublishPost({
        requestBody,
    }: {
        requestBody: PublishRequest,
    }): CancelablePromise<PublishResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/publish',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request or validation failed`,
                401: `Unauthorized`,
                404: `Broker not found`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * List available brokers
     * Retrieve list of all configured marketplace brokers
     * @returns BrokerListResponse Successfully retrieved brokers
     * @throws ApiError
     */
    public listBrokersApiV1MarketplaceBrokersGet(): CancelablePromise<BrokerListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/brokers',
            errors: {
                500: `Internal server error`,
            },
        });
    }
    /**
     * Scan bundle for license compliance
     * Scan all files in bundle for license headers and copyright notices
     * @returns any Scan completed successfully
     * @throws ApiError
     */
    public complianceScanApiV1MarketplaceComplianceScanPost({
        bundlePath,
    }: {
        bundlePath: string,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/compliance/scan',
            query: {
                'bundle_path': bundlePath,
            },
            errors: {
                400: `Invalid bundle path`,
                422: `Validation Error`,
                500: `Scan failed`,
            },
        });
    }
    /**
     * Generate compliance checklist
     * Generate legal compliance checklist for bundle
     * @returns any Checklist generated successfully
     * @throws ApiError
     */
    public complianceChecklistApiV1MarketplaceComplianceChecklistPost({
        bundleId,
        license,
    }: {
        bundleId: string,
        license: string,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/compliance/checklist',
            query: {
                'bundle_id': bundleId,
                'license': license,
            },
            errors: {
                400: `Invalid parameters`,
                422: `Validation Error`,
                500: `Generation failed`,
            },
        });
    }
    /**
     * Record compliance consent
     * Record publisher consent to compliance checklist
     * @returns any Consent recorded successfully
     * @throws ApiError
     */
    public complianceConsentApiV1MarketplaceComplianceConsentPost({
        checklistId,
        bundleId,
        publisherEmail,
        requestBody,
    }: {
        checklistId: string,
        bundleId: string,
        publisherEmail: string,
        requestBody: Record<string, any>,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/compliance/consent',
            query: {
                'checklist_id': checklistId,
                'bundle_id': bundleId,
                'publisher_email': publisherEmail,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid consent data`,
                422: `Validation Error`,
                500: `Recording failed`,
            },
        });
    }
    /**
     * Get consent history
     * Retrieve compliance consent history
     * @returns any History retrieved successfully
     * @throws ApiError
     */
    public complianceHistoryApiV1MarketplaceComplianceHistoryGet({
        publisherEmail,
    }: {
        /**
         * Filter by publisher email
         */
        publisherEmail?: (string | null),
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/compliance/history',
            query: {
                'publisher_email': publisherEmail,
            },
            errors: {
                403: `Unauthorized access`,
                422: `Validation Error`,
                500: `Retrieval failed`,
            },
        });
    }
}
