/**
 * Group type definitions for organizing artifacts within collections
 */

/** Represents a group within a collection */
export interface Group {
  /** Group unique identifier (UUID-like) */
  id: string;
  /** Collection this group belongs to */
  collection_id: string;
  /** Group name */
  name: string;
  /** Optional detailed description of the group */
  description?: string;
  /** Group-local tags used for categorization and filtering */
  tags?: string[];
  /** Visual accent token for group cards */
  color?: 'slate' | 'blue' | 'green' | 'amber' | 'rose';
  /** Icon token for group cards */
  icon?: 'layers' | 'folder' | 'tag' | 'sparkles' | 'book' | 'wrench';
  /** Display order within collection (0-based) */
  position: number;
  /** Number of artifacts in this group */
  artifact_count: number;
  /** Group creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at: string;
}

/** Request to create a new group */
export interface CreateGroupRequest {
  /** ID of the collection this group belongs to */
  collection_id: string;
  /** Group name (1-255 characters, unique within collection) */
  name: string;
  /** Optional detailed description */
  description?: string;
  /** Group-local tags */
  tags?: string[];
  /** Visual accent token */
  color?: 'slate' | 'blue' | 'green' | 'amber' | 'rose';
  /** Icon token */
  icon?: 'layers' | 'folder' | 'tag' | 'sparkles' | 'book' | 'wrench';
  /** Display order within collection (default: 0) */
  position?: number;
}

/** Request to update an existing group */
export interface UpdateGroupRequest {
  /** New group name (1-255 characters if provided) */
  name?: string;
  /** New description */
  description?: string;
  /** Updated group-local tags */
  tags?: string[];
  /** Updated visual accent token */
  color?: 'slate' | 'blue' | 'green' | 'amber' | 'rose';
  /** Updated icon token */
  icon?: 'layers' | 'folder' | 'tag' | 'sparkles' | 'book' | 'wrench';
  /** New position in collection */
  position?: number;
}

/** Position update for bulk reorder operations */
export interface GroupPositionUpdate {
  /** Group ID */
  id: string;
  /** New position */
  position: number;
}

/** Request to reorder groups within a collection */
export interface GroupReorderRequest {
  /** List of groups with their new positions */
  groups: GroupPositionUpdate[];
}

/** Request to add artifacts to a group */
export interface AddGroupArtifactsRequest {
  /** List of artifact IDs to add to the group */
  artifact_ids: string[];
  /** Position to insert artifacts at (default: append) */
  position?: number;
}

/** Position update for artifact reorder operations */
export interface ArtifactPositionUpdate {
  /** Artifact ID */
  artifact_id: string;
  /** New position */
  position: number;
}

/** Request to reorder artifacts within a group */
export interface ReorderArtifactsRequest {
  /** List of artifacts with their new positions */
  artifacts: ArtifactPositionUpdate[];
}

/** Artifact in a group with position information */
export interface GroupArtifact {
  /** Artifact ID */
  artifact_id: string;
  /** Position in group (0-based) */
  position: number;
  /** When artifact was added to group (ISO 8601) */
  added_at: string;
}

/** Group with its artifacts list */
export interface GroupWithArtifacts extends Group {
  /** List of artifacts in this group (ordered by position) */
  artifacts: GroupArtifact[];
}

/** Group list response */
export interface GroupListResponse {
  /** List of groups */
  groups: Group[];
  /** Total number of groups */
  total: number;
}
