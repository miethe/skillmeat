/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Information about an available marketplace broker.
 *
 * Describes broker capabilities and configuration.
 */
export type BrokerInfo = {
    /**
     * Broker name
     */
    name: string;
    /**
     * Whether the broker is currently enabled
     */
    enabled: boolean;
    /**
     * Base endpoint URL for the broker API
     */
    endpoint: string;
    /**
     * Whether the broker supports publishing
     */
    supports_publish: boolean;
    /**
     * Optional broker description
     */
    description?: (string | null);
};

