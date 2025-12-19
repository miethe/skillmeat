/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Cache metadata for cached responses.
 */
export type CacheInfo = {
    /**
     * Whether this response was served from cache
     */
    cache_hit: boolean;
    /**
     * When this data was last fetched/refreshed
     */
    last_fetched?: (string | null);
    /**
     * Whether the cached data is considered stale (past TTL)
     */
    is_stale?: boolean;
};

