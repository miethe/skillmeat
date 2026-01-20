/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextEntityType } from './ContextEntityType';
/**
 * Response schema for a single context entity.
 *
 * Provides complete context entity information including metadata,
 * path pattern, and auto-load settings.
 */
export type ContextEntityResponse = {
    /**
     * Unique identifier for the context entity
     */
    id: string;
    /**
     * Human-readable name
     */
    name: string;
    /**
     * Type of context entity
     */
    type: ContextEntityType;
    /**
     * Path pattern within .claude/ directory
     */
    path_pattern: string;
    /**
     * Detailed description
     */
    description?: (string | null);
    /**
     * Category for progressive disclosure
     */
    category?: (string | null);
    /**
     * Whether to auto-load when path pattern matches
     */
    auto_load: boolean;
    /**
     * Version identifier
     */
    version?: (string | null);
    /**
     * SHA-256 hash of content (for change detection)
     */
    content_hash?: (string | null);
    /**
     * Timestamp when entity was created
     */
    created_at: string;
    /**
     * Timestamp when entity was last updated
     */
    updated_at: string;
};

