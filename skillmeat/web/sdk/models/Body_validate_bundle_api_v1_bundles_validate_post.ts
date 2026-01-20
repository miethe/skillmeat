/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type Body_validate_bundle_api_v1_bundles_validate_post = {
    /**
     * Bundle ZIP file to validate
     */
    bundle_file: Blob;
    /**
     * Expected SHA-256 hash for verification
     */
    expected_hash?: (string | null);
};

