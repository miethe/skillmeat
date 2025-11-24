/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Cursor-based pagination information.
 *
 * Provides information about the current page and navigation cursors
 * for efficient pagination of large datasets.
 */
export type PageInfo = {
    /**
     * Whether there are more items after this page
     */
    has_next_page: boolean;
    /**
     * Whether there are items before this page
     */
    has_previous_page: boolean;
    /**
     * Cursor pointing to the first item in this page
     */
    start_cursor?: (string | null);
    /**
     * Cursor pointing to the last item in this page
     */
    end_cursor?: (string | null);
    /**
     * Total number of items (may be expensive to compute)
     */
    total_count?: (number | null);
};

