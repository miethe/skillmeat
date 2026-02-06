/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextModuleResponse } from './ContextModuleResponse';
/**
 * Paginated list response for context modules.
 *
 * Attributes:
 * items: List of context module responses.
 * next_cursor: Cursor for fetching the next page (None if no more).
 * has_more: Whether more pages are available.
 * total: Total count (None if not computed for performance).
 */
export type ContextModuleListResponse = {
  items: Array<ContextModuleResponse>;
  next_cursor?: string | null;
  has_more?: boolean;
  total?: number | null;
};
