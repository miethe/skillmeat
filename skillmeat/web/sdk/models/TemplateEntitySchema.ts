/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Entity information within a project template.
 *
 * Represents a context entity that is part of a template, including
 * deployment order and path pattern information.
 */
export type TemplateEntitySchema = {
    /**
     * Context entity artifact identifier
     */
    artifact_id: string;
    /**
     * Entity name
     */
    name: string;
    /**
     * Entity type (e.g., rule_file, context_file)
     */
    type: string;
    /**
     * Deployment order (lower values deploy first)
     */
    deploy_order: number;
    /**
     * Whether entity is required for template deployment
     */
    required?: boolean;
    /**
     * Path pattern within .claude/ directory
     */
    path_pattern?: (string | null);
};

