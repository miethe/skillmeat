/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MemoryItemResponse } from './MemoryItemResponse';
/**
 * Response model for paginated memory item listing.
 */
export type MemoryItemListResponse = {
  items: Array<MemoryItemResponse>;
  next_cursor?: string | null;
  has_more?: boolean;
  total?: number | null;
};
