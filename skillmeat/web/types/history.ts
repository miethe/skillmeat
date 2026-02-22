/**
 * Artifact history and provenance types.
 *
 * Mirrors /api/v1/artifacts/{artifact_id}/history response contracts.
 */

export type ArtifactHistoryEventCategory = 'version' | 'analytics' | 'deployment' | 'snapshot';

export type ArtifactHistoryEventSource =
  | 'artifact_versions'
  | 'analytics_events'
  | 'deployment_tracker';

export interface ArtifactHistoryEvent {
  id: string;
  timestamp: string;
  event_category: ArtifactHistoryEventCategory;
  event_type: string;
  source: ArtifactHistoryEventSource;
  artifact_name: string;
  artifact_type: string;
  collection_name: string | null;
  project_path: string | null;
  content_sha: string | null;
  parent_sha: string | null;
  version_lineage: string[] | null;
  metadata: Record<string, unknown>;
}

export interface ArtifactHistoryResponse {
  artifact_name: string;
  artifact_type: string;
  timeline: ArtifactHistoryEvent[];
  statistics: Record<string, number>;
  last_updated: string;
}

export interface ArtifactHistoryTimelineEntry {
  id: string;
  type: 'deploy' | 'sync' | 'rollback' | 'update';
  direction: 'upstream' | 'downstream';
  timestamp: string;
  filesChanged?: number;
  user?: string;
  version?: string;
  eventType: string;
  eventCategory: ArtifactHistoryEventCategory;
  source: ArtifactHistoryEventSource;
  projectPath?: string | null;
  collectionName?: string | null;
  contentSha?: string | null;
  parentSha?: string | null;
}
