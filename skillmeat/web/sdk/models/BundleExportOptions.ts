/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Options for bundle export.
 */
export type BundleExportOptions = {
    /**
     * Bundle format (zip or tar.gz)
     */
    format?: string;
    /**
     * Generate shareable link for bundle
     */
    generate_share_link?: boolean;
    /**
     * Permission level for share link (view, download)
     */
    permission_level?: string;
    /**
     * Hours until share link expires (None for no expiration)
     */
    link_expiration_hours?: (number | null);
    /**
     * Optional vault storage configuration
     */
    vault_config?: (Record<string, any> | null);
    /**
     * Sign bundle with Ed25519 signature
     */
    sign_bundle?: boolean;
    /**
     * Signing key ID (uses default if None and sign_bundle=True)
     */
    signing_key_id?: (string | null);
};

