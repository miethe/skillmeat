/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextEntityType } from './ContextEntityType';
/**
 * Request schema for updating a context entity.
 *
 * All fields are optional - only provided fields will be updated.
 * Path pattern validation applies when provided.
 */
export type ContextEntityUpdateRequest = {
  /**
   * Updated name
   */
  name?: string | null;
  /**
   * Updated entity type
   */
  entity_type?: ContextEntityType | null;
  /**
   * Updated markdown content
   */
  content?: string | null;
  /**
   * Updated path pattern (must start with '.claude/', no '..')
   */
  path_pattern?: string | null;
  /**
   * Updated description
   */
  description?: string | null;
  /**
   * Updated category
   */
  category?: string | null;
  /**
   * Updated auto-load setting
   */
  auto_load?: boolean | null;
  /**
   * Updated version
   */
  version?: string | null;
};
