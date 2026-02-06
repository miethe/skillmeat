/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for previewing a context pack (read-only).
 *
 * Attributes:
 * module_id: Optional module whose selectors define filter criteria.
 * budget_tokens: Maximum token budget for the pack (100-100000).
 * filters: Optional additional filters dict. Supported keys:
 * type (str), min_confidence (float).
 */
export type ContextPackPreviewRequest = {
  module_id?: string | null;
  budget_tokens?: number;
  filters?: Record<string, any> | null;
};
