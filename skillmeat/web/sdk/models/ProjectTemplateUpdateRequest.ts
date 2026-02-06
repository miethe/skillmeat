/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating a project template.
 *
 * All fields are optional - only provided fields will be updated.
 */
export type ProjectTemplateUpdateRequest = {
  /**
   * Updated template name
   */
  name?: string | null;
  /**
   * Updated template description
   */
  description?: string | null;
  /**
   * Updated list of context entity IDs
   */
  entity_ids?: Array<string> | null;
};
