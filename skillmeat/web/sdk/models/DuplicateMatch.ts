/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DuplicateDecisionAction } from './DuplicateDecisionAction';
/**
 * A single duplicate match decision from the user.
 *
 * Represents the user's decision to link a discovered artifact
 * to an existing artifact in their collection.
 */
export type DuplicateMatch = {
  /**
   * Full filesystem path to the discovered artifact
   */
  discovered_path: string;
  /**
   * ID of the matching collection artifact (format: type:name)
   */
  collection_artifact_id: string;
  /**
   * Action to take: 'link' to create association, 'skip' to ignore
   */
  action?: DuplicateDecisionAction;
};
