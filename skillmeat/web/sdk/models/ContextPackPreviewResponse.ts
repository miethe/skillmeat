/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response body for a context pack preview.
 *
 * Attributes:
 * items: List of selected item dicts with id, type, content,
 * confidence, and tokens fields.
 * total_tokens: Sum of estimated tokens for all selected items.
 * budget_tokens: The token budget that was requested.
 * utilization: Fraction of budget used (0.0-1.0).
 * items_included: Number of items that fit within budget.
 * items_available: Total number of candidate items before budget cut.
 */
export type ContextPackPreviewResponse = {
  items: Array<Record<string, any>>;
  total_tokens: number;
  budget_tokens: number;
  utilization: number;
  items_included: number;
  items_available: number;
};
