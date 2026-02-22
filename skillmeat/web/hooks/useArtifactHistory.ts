/**
 * React Query hook for artifact provenance/history timelines.
 */

import { useQuery } from '@tanstack/react-query';
import type {
  ArtifactHistoryEvent,
  ArtifactHistoryResponse,
  ArtifactHistoryTimelineEntry,
} from '@/types/history';
import type { Artifact } from '@/types/artifact';
import { ApiError, apiConfig, apiRequest } from '@/lib/api';

const USE_MOCKS = apiConfig.useMocks;

export interface UseArtifactHistoryOptions {
  enabled?: boolean;
  includeVersions?: boolean;
  includeAnalytics?: boolean;
  includeDeployments?: boolean;
  limit?: number;
}

export interface ArtifactHistoryViewModel extends ArtifactHistoryResponse {
  timelineEntries: ArtifactHistoryTimelineEntry[];
}

export const artifactHistoryKeys = {
  all: ['artifact-history'] as const,
  detail: (
    artifactId: string,
    options: Required<Omit<UseArtifactHistoryOptions, 'enabled'>>
  ) =>
    [
      ...artifactHistoryKeys.all,
      artifactId,
      options.includeVersions,
      options.includeAnalytics,
      options.includeDeployments,
      options.limit,
    ] as const,
};

function toHistoryNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value > 0 ? Math.floor(value) : undefined;
  }

  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }

  return undefined;
}

function resolveHistoryType(event: ArtifactHistoryEvent): ArtifactHistoryTimelineEntry['type'] {
  const normalizedType = event.event_type.toLowerCase();
  const metadata = event.metadata ?? {};

  if (
    metadata.rollback === true ||
    normalizedType.includes('rollback') ||
    normalizedType.includes('revert')
  ) {
    return 'rollback';
  }

  if (event.event_category === 'deployment' || normalizedType.includes('deploy')) {
    return 'deploy';
  }

  if (normalizedType.includes('sync')) {
    return 'sync';
  }

  return 'update';
}

function resolveHistoryDirection(
  type: ArtifactHistoryTimelineEntry['type']
): ArtifactHistoryTimelineEntry['direction'] {
  if (type === 'deploy' || type === 'rollback') {
    return 'downstream';
  }
  return 'upstream';
}

function resolveHistoryUser(event: ArtifactHistoryEvent): string | undefined {
  const metadata = event.metadata ?? {};
  const metadataUser =
    (typeof metadata.user === 'string' && metadata.user) ||
    (typeof metadata.actor === 'string' && metadata.actor) ||
    (typeof metadata.triggered_by === 'string' && metadata.triggered_by) ||
    (typeof metadata.initiator === 'string' && metadata.initiator);

  if (metadataUser) {
    return metadataUser;
  }

  if (event.source === 'artifact_versions') return 'Version Control';
  if (event.source === 'deployment_tracker') return 'Deployment Tracker';
  if (event.source === 'analytics_events') return 'Analytics';
  return undefined;
}

function resolveFilesChanged(event: ArtifactHistoryEvent): number | undefined {
  const metadata = event.metadata ?? {};
  return (
    toHistoryNumber(metadata.files_changed) ||
    toHistoryNumber(metadata.file_count) ||
    toHistoryNumber(metadata.changed_files) ||
    toHistoryNumber(metadata.conflicts_detected)
  );
}

function resolveVersion(event: ArtifactHistoryEvent): string | undefined {
  const metadata = event.metadata ?? {};
  const value =
    event.content_sha ||
    (typeof metadata.sha_after === 'string' ? metadata.sha_after : null) ||
    (typeof metadata.sha === 'string' ? metadata.sha : null) ||
    (typeof metadata.version === 'string' ? metadata.version : null);

  return value || undefined;
}

export function mapHistoryEventToTimelineEntry(
  event: ArtifactHistoryEvent
): ArtifactHistoryTimelineEntry {
  const type = resolveHistoryType(event);
  return {
    id: event.id,
    type,
    direction: resolveHistoryDirection(type),
    timestamp: event.timestamp,
    filesChanged: resolveFilesChanged(event),
    user: resolveHistoryUser(event),
    version: resolveVersion(event),
    eventType: event.event_type,
    eventCategory: event.event_category,
    source: event.source,
    projectPath: event.project_path,
    collectionName: event.collection_name,
    contentSha: event.content_sha,
    parentSha: event.parent_sha,
  };
}

function mapHistoryTimeline(timeline: ArtifactHistoryEvent[]): ArtifactHistoryTimelineEntry[] {
  return timeline.map(mapHistoryEventToTimelineEntry);
}

async function fetchArtifactHistory(
  artifactId: string,
  options: Required<Omit<UseArtifactHistoryOptions, 'enabled'>>
): Promise<ArtifactHistoryViewModel> {
  const params = new URLSearchParams({
    include_versions: String(options.includeVersions),
    include_analytics: String(options.includeAnalytics),
    include_deployments: String(options.includeDeployments),
    limit: String(options.limit),
  });

  try {
    const response = await apiRequest<ArtifactHistoryResponse>(
      `/artifacts/${encodeURIComponent(artifactId)}/history?${params.toString()}`
    );
    return {
      ...response,
      timelineEntries: mapHistoryTimeline(response.timeline),
    };
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && (error.status === 404 || error.status === 503)) {
      return {
        artifact_name: artifactId,
        artifact_type: 'unknown',
        timeline: [],
        statistics: {},
        last_updated: new Date().toISOString(),
        timelineEntries: [],
      };
    }
    throw error;
  }
}

export function getArtifactHistoryId(
  artifact: Pick<Artifact, 'id' | 'type' | 'name'> | null | undefined
): string {
  if (!artifact) return '';
  if (artifact.id && artifact.id.includes(':')) return artifact.id;
  return `${artifact.type}:${artifact.name}`;
}

export function useArtifactHistory(artifactId: string, options: UseArtifactHistoryOptions = {}) {
  const resolved = {
    includeVersions: options.includeVersions ?? true,
    includeAnalytics: options.includeAnalytics ?? true,
    includeDeployments: options.includeDeployments ?? true,
    limit: options.limit ?? 300,
  };

  return useQuery({
    queryKey: artifactHistoryKeys.detail(artifactId, resolved),
    queryFn: () => fetchArtifactHistory(artifactId, resolved),
    enabled: (options.enabled ?? true) && !!artifactId,
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  });
}
