/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating a new group in a collection.
 *
 * Groups provide a way to organize artifacts within a collection.
 */
export type GroupCreateRequest = {
  /**
   * ID of the collection this group belongs to
   */
  collection_id: string;
  /**
   * Group name (must be unique within collection)
   */
  name: string;
  /**
   * Optional detailed description of the group
   */
  description?: string | null;
  /**
   * Group-local tags used for categorization and filtering
   */
  tags?: Array<string>;
  /**
   * Visual color token for group card accents
   */
  color?: 'slate' | 'blue' | 'green' | 'amber' | 'rose';
  /**
   * Icon token used for group display
   */
  icon?: 'layers' | 'folder' | 'tag' | 'sparkles' | 'book' | 'wrench';
  /**
   * Display order within collection (0-based)
   */
  position?: number;
};
