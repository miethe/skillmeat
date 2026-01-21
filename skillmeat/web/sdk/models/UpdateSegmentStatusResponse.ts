/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExtractedSegmentResponse } from './ExtractedSegmentResponse';
/**
 * Response after updating segment status.
 *
 * Returns the updated entry with all segments and their new statuses.
 */
export type UpdateSegmentStatusResponse = {
    /**
     * Catalog entry ID
     */
    entry_id: string;
    /**
     * Full artifact path
     */
    raw_path: string;
    /**
     * Updated segments with status
     */
    extracted: Array<ExtractedSegmentResponse>;
    /**
     * Update timestamp
     */
    updated_at: string;
};

