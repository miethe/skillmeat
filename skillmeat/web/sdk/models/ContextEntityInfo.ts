/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Information about a discovered context entity in a project.
 *
 * Represents a context file discovered in a project's .claude/ directory
 * with token estimates for progressive disclosure.
 */
export type ContextEntityInfo = {
    /**
     * Type of context entity (spec_file, rule_file, context_file)
     */
    type: string;
    /**
     * Name derived from file path
     */
    name: string;
    /**
     * Relative path from project root
     */
    path: string;
    /**
     * Estimated token count for this entity
     */
    tokens: number;
    /**
     * Whether this entity auto-loads based on path patterns
     */
    auto_load?: boolean;
};

