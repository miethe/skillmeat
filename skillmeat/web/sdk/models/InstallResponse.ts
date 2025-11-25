/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for installation operations.
 *
 * Indicates success status and lists imported artifacts.
 */
export type InstallResponse = {
    /**
     * Whether installation succeeded
     */
    success: boolean;
    /**
     * List of artifact names that were imported
     */
    artifacts_imported: Array<string>;
    /**
     * Status message
     */
    message: string;
    /**
     * The listing ID that was installed
     */
    listing_id: string;
    /**
     * The broker used for installation
     */
    broker: string;
};

