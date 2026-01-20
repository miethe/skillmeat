/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GroupPositionUpdate } from './GroupPositionUpdate';
/**
 * Request schema for bulk reordering groups within a collection.
 */
export type GroupReorderRequest = {
    /**
     * List of groups with their new positions
     */
    groups: Array<GroupPositionUpdate>;
};

