/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TemplateEntitySchema } from './TemplateEntitySchema';
/**
 * Response schema for a single project template.
 *
 * Provides complete template information including entity list,
 * configuration, and metadata.
 */
export type ProjectTemplateResponse = {
    /**
     * Unique identifier for the template
     */
    id: string;
    /**
     * Template name
     */
    name: string;
    /**
     * Template description
     */
    description?: (string | null);
    /**
     * Source collection ID if template was created from collection
     */
    collection_id?: (string | null);
    /**
     * Default project config entity ID
     */
    default_project_config_id?: (string | null);
    /**
     * List of entities in the template
     */
    entities: Array<TemplateEntitySchema>;
    /**
     * Total number of entities in template
     */
    entity_count: number;
    /**
     * Timestamp when template was created
     */
    created_at: string;
    /**
     * Timestamp when template was last updated
     */
    updated_at: string;
};

