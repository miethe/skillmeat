/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from clearing skip preferences.
 */
export type SkipClearResponse = {
    /**
     * Whether clear operation succeeded
     */
    success: boolean;
    /**
     * Number of skip preferences that were cleared
     */
    cleared_count: number;
    /**
     * Human-readable result message
     */
    message: string;
};

