/**
 * BOM (Bill of Materials) and attestation type definitions.
 *
 * Mirrors the API schemas in skillmeat/api/schemas/bom.py:
 *   - BomSchema → BomSnapshot
 *   - ArtifactEntrySchema → ArtifactEntry
 *   - AttestationSchema → Attestation
 *   - HistoryEventSchema → ActivityEvent
 */

// =============================================================================
// BOM Types
// =============================================================================

/** A single artifact entry within a BOM snapshot. */
export interface ArtifactEntry {
  /** Artifact name (unique within type). */
  name: string;
  /** Artifact type string (e.g. 'skill', 'command'). */
  type: string;
  /** Source identifier (GitHub path or local path). */
  source?: string | null;
  /** Deployed or upstream version string. */
  version?: string | null;
  /** SHA-256 hex digest of artifact content, or '' if unavailable. */
  content_hash: string;
  /** Per-type metadata dict (author, description, tags, mime_type, etc.). */
  metadata: Record<string, unknown>;
  /** Child member list for composite/deployment_set types. */
  members?: Array<Record<string, unknown>> | null;
}

/** Full Bill of Materials snapshot document. */
export interface BomSnapshot {
  /** BOM schema version (semver, e.g. '1.0.0'). */
  schema_version: string;
  /** ISO-8601 UTC timestamp when the BOM was generated. */
  generated_at: string;
  /** Resolved project root path, if provided at generation time. */
  project_path?: string | null;
  /** Total number of artifact entries. */
  artifact_count: number;
  /** Artifact entries sorted by (type, name). */
  artifacts: ArtifactEntry[];
  /** Generator metadata (generator name, elapsed_ms, etc.). */
  metadata: Record<string, unknown>;
}

// =============================================================================
// Attestation Types
// =============================================================================

/** Visibility policy for an attestation. */
export type AttestationVisibility = 'private' | 'org' | 'public';

/** Attestation record linking an artifact to an owner with RBAC metadata. */
export interface Attestation {
  /** Attestation record UUID hex. */
  id: string;
  /** Artifact identifier in 'type:name' format. */
  artifact_id: string;
  /** Owner entity type (e.g. 'user', 'team', 'org'). */
  owner_type: string;
  /** Owner entity identifier. */
  owner_id: string;
  /** RBAC roles granted to this attestation. */
  roles: string[];
  /** Permission scopes covered by this attestation. */
  scopes: string[];
  /** Visibility policy. */
  visibility: AttestationVisibility;
  /** ISO-8601 UTC timestamp when attestation was created. */
  created_at?: string | null;
}

// =============================================================================
// Activity Event Types
// =============================================================================

/** Known event type strings from the artifact history events table. */
export type ActivityEventType =
  | 'created'
  | 'updated'
  | 'deployed'
  | 'deleted'
  | 'attested'
  | 'bom_generated'
  | string;

/** A single artifact history/activity event. */
export interface ActivityEvent {
  /** History event UUID hex. */
  id: string;
  /** Artifact identifier in 'type:name' format. */
  artifact_id: string;
  /** Event type string (e.g. 'created', 'updated', 'deployed'). */
  event_type: ActivityEventType;
  /** Identifier of the actor who triggered the event. */
  actor_id?: string | null;
  /** Owner entity type context for this event. */
  owner_type?: string | null;
  /** ISO-8601 UTC timestamp of the event. */
  timestamp?: string | null;
  /** JSON representation of changes made in this event. */
  diff_json?: Record<string, unknown> | null;
  /** SHA-256 content hash of the artifact after this event. */
  content_hash?: string | null;
}
