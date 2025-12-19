/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for share link creation/update.
 */
export type ShareLinkResponse = {
    /**
     * Whether operation succeeded
     */
    success: boolean;
    /**
     * Bundle unique identifier
     */
    bundle_id: string;
    /**
     * Full shareable URL
     */
    url: string;
    /**
     * Short URL for easier sharing
     */
    short_url: string;
    /**
     * QR code as data URL (optional)
     */
    qr_code?: (string | null);
    /**
     * Permission level for this link
     */
    permission_level: string;
    /**
     * ISO 8601 timestamp when link expires (None if no expiration)
     */
    expires_at?: (string | null);
    /**
     * Maximum downloads allowed (None if unlimited)
     */
    max_downloads?: (number | null);
    /**
     * Current number of downloads
     */
    download_count?: number;
    /**
     * ISO 8601 timestamp when link was created
     */
    created_at: string;
};

