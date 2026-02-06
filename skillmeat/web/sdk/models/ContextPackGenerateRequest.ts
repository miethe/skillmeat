/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for generating a full context pack with markdown.
 *
 * Attributes:
 * module_id: Optional module whose selectors define filter criteria.
 * budget_tokens: Maximum token budget for the pack (100-100000).
 * filters: Optional additional filters dict. Supported keys:
 * type (str), min_confidence (float).
 */
export type ContextPackGenerateRequest = {
  module_id?: string | null;
  budget_tokens?: number;
  filters?: Record<string, any> | null;
};
