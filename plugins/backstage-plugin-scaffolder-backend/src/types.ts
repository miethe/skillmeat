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

/** SAM Attestation API request — POST /api/v1/attestations */
export interface AttestationRequest {
  /** Artifact identifier in 'type:name' format (e.g. 'skill:canvas-design') */
  artifact_id: string;
  /**
   * Owner scope override: 'user', 'team', or 'enterprise'.
   * When omitted the caller's principal type is used.
   */
  owner_scope?: string;
  /** Optional free-text compliance notes for manual attestation workflows */
  notes?: string;
}

/** SAM Attestation API response */
export interface AttestationResponse {
  /** Attestation record UUID hex */
  id: string;
  /** Artifact identifier in 'type:name' format */
  artifact_id: string;
  /** Owner entity type (e.g. 'user', 'team', 'org') */
  owner_type: string;
  /** Owner entity identifier */
  owner_id: string;
  /** RBAC roles granted to this attestation */
  roles: string[];
  /** Permission scopes covered by this attestation */
  scopes: string[];
  /** Visibility policy: 'private', 'team', or 'public' */
  visibility: string;
  /** ISO 8601 creation timestamp */
  created_at?: string;
  /** Optional free-text compliance notes */
  notes?: string;
}

/** SAM BOM Generate API request — POST /api/v1/bom/generate */
export interface BomGenerateRequest {
  /** Project scope to filter artifacts. Omit for a collection-level BOM. */
  project_id?: string;
  /** Sign the generated BOM with the local Ed25519 signing key. */
  auto_sign?: boolean;
}

/** SAM BOM Generate API response */
export interface BomGenerateResponse {
  /** Auto-incrementing snapshot primary key */
  id: number;
  /** Project scope (null for collection-level) */
  project_id?: string;
  /** Owner context (user / team / enterprise) */
  owner_type: string;
  /** ISO-8601 UTC timestamp */
  created_at: string;
  /** Deserialized BOM document */
  bom: {
    artifact_count: number;
    generated_at: string;
    [key: string]: unknown;
  };
  /** Whether the snapshot was signed */
  signed: boolean;
  /** Hex-encoded signature (present when signed=true) */
  signature?: string;
  /** SHA-256 fingerprint of the signing key (present when signed=true) */
  signing_key_id?: string;
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
