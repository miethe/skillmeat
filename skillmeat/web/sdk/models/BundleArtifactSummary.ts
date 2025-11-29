/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Summary of an artifact within a bundle.
 */
export type BundleArtifactSummary = {
  /**
   * Artifact name
   */
  name: string;
  /**
   * Artifact type (skill, command, agent)
   */
  type: string;
  /**
   * Artifact version
   */
  version: string;
  /**
   * Artifact scope (user, local)
   */
  scope: string;
};
