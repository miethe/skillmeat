/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating a group.
 *
 * All fields are optional. Only provided fields will be updated.
 */
export type GroupUpdateRequest = {
  /**
   * New group name
   */
  name?: string | null;
  /**
   * New description
   */
  description?: string | null;
  /**
   * Updated group-local tags
   */
  tags?: Array<string> | null;
  /**
   * Updated visual color token
   */
  color?: 'slate' | 'blue' | 'green' | 'amber' | 'rose' | null;
  /**
   * Updated icon token
   */
  icon?: 'layers' | 'folder' | 'tag' | 'sparkles' | 'book' | 'wrench' | null;
  /**
   * New position in collection
   */
  position?: number | null;
};
