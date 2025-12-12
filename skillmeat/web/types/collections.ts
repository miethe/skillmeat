/**
 * Collection type definitions for artifact organization
 */

/** Represents a user-defined collection of artifacts */
export interface Collection {
  /** Collection unique identifier (collection name, e.g., "default") */
  id: string;
  /** Collection display name */
  name: string;
  /** Collection format version */
  version: string;
  /** Number of artifacts in the collection */
  artifact_count: number;
  /** Collection creation timestamp (ISO 8601) */
  created: string;
  /** Last update timestamp (ISO 8601) */
  updated: string;
}

/** Request to create a new collection */
export interface CreateCollectionRequest {
  /** Collection name (1-100 characters, must be unique) */
  name: string;
}

/** Request to update an existing collection */
export interface UpdateCollectionRequest {
  /** New collection name (1-100 characters if provided) */
  name?: string;
}

/** Lightweight artifact summary in collection listings */
export interface ArtifactSummary {
  /** Artifact name */
  name: string;
  /** Artifact type (skill, command, agent, etc.) */
  type: string;
  /** Current version */
  version?: string;
  /** Source specification (e.g., "anthropics/skills/pdf") */
  source: string;
}

/** Paginated collection list response */
export interface CollectionListResponse {
  /** List of collections */
  items: Collection[];
  /** Total number of collections */
  total: number;
  /** Current page number */
  page: number;
  /** Number of items per page */
  page_size: number;
}

/** Paginated artifacts in collection response */
export interface CollectionArtifactsResponse {
  /** List of artifact summaries */
  items: ArtifactSummary[];
  /** Total number of artifacts */
  total: number;
  /** Current page number */
  page: number;
  /** Number of items per page */
  page_size: number;
}
