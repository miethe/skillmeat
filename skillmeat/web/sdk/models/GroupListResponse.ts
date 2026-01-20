/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GroupResponse } from './GroupResponse';
/**
 * Response schema for listing groups.
 */
export type GroupListResponse = {
  /**
   * List of groups
   */
  groups?: Array<GroupResponse>;
  /**
   * Total number of groups
   */
  total: number;
};
