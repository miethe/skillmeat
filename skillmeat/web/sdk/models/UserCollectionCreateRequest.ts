/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating a new user collection.
 */
export type UserCollectionCreateRequest = {
  /**
   * Collection name (must be unique)
   */
  name: string;
  /**
   * Optional collection description
   */
  description?: string | null;
  /**
   * Collection type (e.g., 'context', 'artifacts')
   */
  collection_type?: string | null;
  /**
   * Category for context collections (e.g., 'rules', 'specs', 'context')
   */
  context_category?: string | null;
};
