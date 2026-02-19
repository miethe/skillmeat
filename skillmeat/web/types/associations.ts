/**
 * TypeScript DTOs for artifact association (composite membership) endpoints.
 *
 * These types mirror the backend Pydantic models in:
 *   skillmeat/api/schemas/associations.py
 *
 * Source of truth: skillmeat/api/openapi.json
 */

/**
 * Single association edge between two artifacts.
 *
 * Represents one row from the composite_memberships table, enriched
 * with basic metadata about the related artifact so callers don't need
 * a second round-trip.
 */
export interface AssociationItemDTO {
  /** type:name identifier of the related artifact (e.g. "composite:my-plugin") */
  artifact_id: string;

  /** Human-readable name component extracted from artifact_id (e.g. "my-plugin") */
  artifact_name: string;

  /** Type component extracted from artifact_id (e.g. "composite", "skill") */
  artifact_type: string;

  /** Semantic edge label for the membership (e.g. "contains") */
  relationship_type: string;

  /**
   * Optional content hash locking the child to a specific snapshot.
   * null means "track latest".
   */
  pinned_version_hash: string | null;

  /** UTC timestamp (ISO 8601) when this membership was created */
  created_at: string;
}

/**
 * All parent and child associations for a single artifact.
 *
 * Returned by GET /api/v1/artifacts/{artifactId}/associations
 */
export interface AssociationsDTO {
  /** type:name identifier of the queried artifact */
  artifact_id: string;

  /**
   * Composite artifacts that contain this artifact as a child (reverse lookup).
   * Empty when the artifact belongs to no composite.
   */
  parents: AssociationItemDTO[];

  /**
   * Child artifacts that this composite contains.
   * Empty when artifact_id is not a composite or has no members.
   */
  children: AssociationItemDTO[];
}
