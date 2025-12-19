/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for sync operation result.
 *
 * Attributes:
 * entity_id: Entity identifier
 * entity_name: Entity name
 * action: Action performed (pulled, pushed, skipped, conflict, resolved)
 * message: Human-readable status message
 */
export type SyncResultResponse = {
    /**
     * Entity identifier
     */
    entity_id: string;
    /**
     * Entity name
     */
    entity_name: string;
    /**
     * Action performed
     */
    action: string;
    /**
     * Human-readable status message
     */
    message: string;
};

