/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to create or update a bundle share link.
 */
export type ShareLinkUpdateRequest = {
  /**
   * Permission level for share link (viewer, importer, editor)
   */
  permission_level?: string;
  /**
   * Hours until share link expires (None for no expiration)
   */
  expiration_hours?: number | null;
  /**
   * Maximum number of downloads allowed (None for unlimited)
   */
  max_downloads?: number | null;
};
