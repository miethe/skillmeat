/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Summary of a group within a collection.
 *
 * Lightweight group representation for collection listings.
 */
export type GroupSummary = {
  /**
   * Group unique identifier
   */
  id: string;
  /**
   * Group name
   */
  name: string;
  /**
   * Group description
   */
  description?: string | null;
  /**
   * Display order within collection
   */
  position: number;
  /**
   * Number of artifacts in group
   */
  artifact_count: number;
};
