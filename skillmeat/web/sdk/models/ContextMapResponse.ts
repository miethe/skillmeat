/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextEntityInfo } from './ContextEntityInfo';
/**
 * Response for project context map discovery.
 *
 * Provides a categorized map of context entities in a project,
 * separated by auto-loading behavior for progressive disclosure.
 */
export type ContextMapResponse = {
    /**
     * Entities that auto-load based on path patterns
     */
    auto_loaded?: Array<ContextEntityInfo>;
    /**
     * Entities that load on-demand (context files)
     */
    on_demand?: Array<ContextEntityInfo>;
    /**
     * Total estimated tokens for all auto-loaded entities
     */
    total_auto_load_tokens: number;
};

