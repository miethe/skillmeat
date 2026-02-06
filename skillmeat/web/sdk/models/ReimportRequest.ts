/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to force re-import an artifact from upstream.
 *
 * Used when an artifact was deleted but the catalog entry still shows 'imported',
 * or when you want to replace an existing artifact with the upstream version.
 */
export type ReimportRequest = {
  /**
   * If True and artifact exists, save deployment records, delete artifact, re-import, and restore deployments. If False, performs a full fresh import.
   */
  keep_deployments?: boolean;
};
