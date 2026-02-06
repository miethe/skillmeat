/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response body for a generated context pack.
 *
 * Extends the preview response with markdown output and a generation
 * timestamp.
 *
 * Attributes:
 * items: List of selected item dicts.
 * total_tokens: Sum of estimated tokens for all selected items.
 * budget_tokens: The token budget that was requested.
 * utilization: Fraction of budget used (0.0-1.0).
 * items_included: Number of items that fit within budget.
 * items_available: Total number of candidate items before budget cut.
 * markdown: Formatted markdown context pack grouped by memory type.
 * generated_at: ISO 8601 timestamp of generation.
 */
export type ContextPackGenerateResponse = {
  items: Array<Record<string, any>>;
  total_tokens: number;
  budget_tokens: number;
  utilization: number;
  items_included: number;
  items_available: number;
  markdown: string;
  generated_at: string;
};
