/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Search result for a single artifact.
 *
 * Attributes:
 * id: Artifact ID
 * name: Artifact name
 * type: Artifact type
 * project_id: Project ID
 * project_name: Project name
 * score: Relevance score (100=exact, 80=prefix, 60=contains)
 */
export type SearchResult = {
  /**
   * Artifact ID
   */
  id: string;
  /**
   * Artifact name
   */
  name: string;
  /**
   * Artifact type
   */
  type: string;
  /**
   * Project ID
   */
  project_id: string;
  /**
   * Project name
   */
  project_name: string;
  /**
   * Relevance score (100=exact match, 80=prefix, 60=contains)
   */
  score: number;
};
