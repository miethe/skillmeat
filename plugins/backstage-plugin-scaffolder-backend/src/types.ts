/**
 * Shared TypeScript interfaces for SAM (SkillMeat API) request/response shapes
 * and Backstage plugin configuration.
 *
 * These types mirror the OpenAPI contract defined in skillmeat/api/openapi.json
 * under the /api/v1/integrations/idp/* endpoints.
 */

/** SAM IDP Scaffold API request — POST /api/v1/integrations/idp/scaffold */
export interface ScaffoldRequest {
  /** The IDP target identifier (e.g. backstage template entity ref) */
  target_id: string;
  /** Template variable substitutions to apply during rendering */
  variables: Record<string, string>;
}

/** A single rendered file from scaffold response */
export interface RenderedFile {
  /** Relative path of the file within the scaffolder workspace */
  path: string;
  /** Base64-encoded file content */
  content_base64: string;
}

/** SAM IDP Scaffold API response */
export interface ScaffoldResponse {
  /** Rendered files to be written into the scaffolder workspace */
  files: RenderedFile[];
}

/** SAM IDP Register Deployment request — POST /api/v1/integrations/idp/register-deployment */
export interface RegisterDeploymentRequest {
  /** The GitHub repository URL created by publish:github */
  repo_url: string;
  /** The IDP target identifier used during scaffold */
  target_id: string;
  /** Arbitrary key-value metadata to associate with the deployment */
  metadata: Record<string, string>;
}

/** SAM IDP Register Deployment response */
export interface RegisterDeploymentResponse {
  /** Unique identifier for the created or matched deployment set */
  deployment_set_id: string;
  /** Whether a new deployment set was created (false = matched existing) */
  created: boolean;
}

/** Plugin configuration sourced from Backstage app-config.yaml */
export interface SkillMeatConfig {
  /** Base URL of the SAM API, e.g. https://sam.internal or http://localhost:8080 */
  baseUrl: string;
  /**
   * Optional bearer token for SAM API authentication.
   * When omitted, requests are sent unauthenticated (suitable for internal networks).
   */
  token?: string;
}
