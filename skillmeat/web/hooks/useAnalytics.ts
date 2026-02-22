/**
 * React Query hooks for analytics data fetching.
 */

import { useQuery } from '@tanstack/react-query';
import type {
  AnalyticsEventsResponse,
  AnalyticsSummary,
  EnterpriseAnalyticsSummary,
  TimePeriod,
  TopArtifactsResponse,
  TrendsResponse,
} from '@/types/analytics';
import { ApiError, apiConfig, apiRequest, buildApiHeaders } from '@/lib/api';

const USE_MOCKS = apiConfig.useMocks;

export interface AnalyticsEventsQueryOptions {
  limit?: number;
  after?: string;
  eventType?: string;
  artifactName?: string;
  artifactType?: string;
  collectionName?: string;
}

export type AnalyticsExportFormat = 'json' | 'prometheus' | 'otel';

/**
 * Fetch analytics summary.
 */
async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  try {
    return await apiRequest<AnalyticsSummary>('/analytics/summary');
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && (error.status === 404 || error.status === 503)) {
      return {
        total_collections: 1,
        total_artifacts: 15,
        total_deployments: 42,
        total_events: 156,
        artifacts_by_type: {
          skill: 10,
          command: 3,
          agent: 2,
        },
        recent_activity_count: 23,
        most_deployed_artifact: 'canvas-design',
        last_activity: new Date().toISOString(),
      };
    }
    // eslint-disable-next-line no-console
    console.error('[analytics] Failed to fetch summary from API', error);
    throw error;
  }
}

/**
 * Fetch enterprise analytics summary.
 */
async function fetchEnterpriseSummary(): Promise<EnterpriseAnalyticsSummary> {
  try {
    return await apiRequest<EnterpriseAnalyticsSummary>('/analytics/enterprise-summary');
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && (error.status === 404 || error.status === 503)) {
      return {
        generated_at: new Date().toISOString(),
        total_events: 156,
        total_artifacts: 15,
        total_projects: 4,
        total_collections: 1,
        event_type_counts: {
          deploy: 42,
          sync: 51,
          update: 27,
          search: 36,
        },
        windows: [
          {
            window_days: 1,
            total_events: 14,
            deploy_events: 3,
            sync_events: 4,
            update_events: 2,
            remove_events: 1,
            search_events: 4,
            success_count: 11,
            failure_count: 1,
            success_rate: 0.916,
            unique_artifacts: 7,
            unique_projects: 2,
            unique_collections: 1,
            deploy_frequency_per_day: 3,
          },
          {
            window_days: 7,
            total_events: 68,
            deploy_events: 19,
            sync_events: 22,
            update_events: 13,
            remove_events: 4,
            search_events: 10,
            success_count: 52,
            failure_count: 6,
            success_rate: 0.896,
            unique_artifacts: 12,
            unique_projects: 4,
            unique_collections: 1,
            deploy_frequency_per_day: 2.71,
          },
        ],
        delivery: {
          deployment_frequency_7d: 2.71,
          deployment_frequency_30d: 1.4,
          median_deploy_interval_minutes_30d: 118,
          unique_artifacts_deployed_30d: 11,
        },
        reliability: {
          change_failure_rate_30d: 0.12,
          sync_success_rate_7d: 0.91,
          rollback_rate_30d: 0.04,
          mean_time_to_recovery_hours_30d: 2.6,
        },
        adoption: {
          active_projects_7d: 4,
          active_projects_30d: 6,
          active_collections_30d: 1,
          search_to_deploy_conversion_30d: 0.53,
        },
        top_projects: [
          {
            project_path: '/workspace/example-api',
            event_count: 28,
            deploy_count: 10,
            sync_count: 8,
            last_activity: new Date().toISOString(),
          },
          {
            project_path: '/workspace/example-web',
            event_count: 22,
            deploy_count: 6,
            sync_count: 9,
            last_activity: new Date(Date.now() - 3600 * 1000).toISOString(),
          },
        ],
        top_artifacts: [
          {
            artifact_name: 'canvas-design',
            artifact_type: 'skill',
            deployment_count: 25,
            usage_count: 150,
            last_used: new Date(Date.now() - 86400000).toISOString(),
            collections: ['default'],
          },
        ],
        history_summary: {
          version_events: 84,
          merge_events: 7,
          deployment_events: 42,
        },
      };
    }
    throw error;
  }
}

/**
 * Fetch top artifacts.
 */
async function fetchTopArtifacts(limit = 10, artifactType?: string): Promise<TopArtifactsResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    ...(artifactType && { artifact_type: artifactType }),
  });

  try {
    return await apiRequest<TopArtifactsResponse>(`/analytics/top-artifacts?${params.toString()}`);
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && (error.status === 404 || error.status === 503)) {
      return {
        items: [
          {
            artifact_name: 'canvas-design',
            artifact_type: 'skill',
            deployment_count: 25,
            usage_count: 150,
            last_used: new Date(Date.now() - 86400000).toISOString(),
            collections: ['default'],
          },
          {
            artifact_name: 'git-helper',
            artifact_type: 'command',
            deployment_count: 18,
            usage_count: 128,
            last_used: new Date(Date.now() - 3600000).toISOString(),
            collections: ['default'],
          },
          {
            artifact_name: 'database-mcp',
            artifact_type: 'mcp',
            deployment_count: 12,
            usage_count: 67,
            last_used: new Date(Date.now() - 43200000).toISOString(),
            collections: ['default'],
          },
          {
            artifact_name: 'docx-processor',
            artifact_type: 'skill',
            deployment_count: 8,
            usage_count: 45,
            last_used: new Date(Date.now() - 604800000).toISOString(),
            collections: ['default'],
          },
          {
            artifact_name: 'code-reviewer',
            artifact_type: 'agent',
            deployment_count: 5,
            usage_count: 22,
            last_used: new Date(Date.now() - 172800000).toISOString(),
            collections: ['default'],
          },
        ],
        page_info: {
          has_next_page: false,
          has_previous_page: false,
          start_cursor: null,
          end_cursor: null,
          total_count: 5,
        },
      };
    }
    throw error;
  }
}

/**
 * Fetch usage trends.
 */
async function fetchUsageTrends(period: TimePeriod, days: number): Promise<TrendsResponse> {
  const params = new URLSearchParams({
    period,
    days: days.toString(),
  });

  try {
    return await apiRequest<TrendsResponse>(`/analytics/trends?${params.toString()}`);
  } catch (error) {
    if (USE_MOCKS && error instanceof ApiError && (error.status === 404 || error.status === 503)) {
      const dataPoints = [];
      const now = new Date();
      const topArtifacts = ['canvas-design', 'git-helper', 'database-mcp'];

      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        date.setHours(0, 0, 0, 0);
        const randomIndex = Math.floor(Math.random() * topArtifacts.length);

        dataPoints.push({
          timestamp: date.toISOString(),
          period,
          deployment_count: Math.floor(Math.random() * 10) + 1,
          usage_count: Math.floor(Math.random() * 50) + 10,
          unique_artifacts: Math.floor(Math.random() * 5) + 2,
          top_artifact: topArtifacts[randomIndex] || 'canvas-design',
        });
      }

      return {
        period_type: period,
        start_date: dataPoints[0]?.timestamp || now.toISOString(),
        end_date: now.toISOString(),
        data_points: dataPoints,
        total_periods: dataPoints.length,
      };
    }
    throw error;
  }
}

/**
 * Fetch analytics events.
 */
async function fetchAnalyticsEvents(
  options: AnalyticsEventsQueryOptions = {}
): Promise<AnalyticsEventsResponse> {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 100),
    ...(options.after ? { after: options.after } : {}),
    ...(options.eventType ? { event_type: options.eventType } : {}),
    ...(options.artifactName ? { artifact_name: options.artifactName } : {}),
    ...(options.artifactType ? { artifact_type: options.artifactType } : {}),
    ...(options.collectionName ? { collection_name: options.collectionName } : {}),
  });

  return apiRequest<AnalyticsEventsResponse>(`/analytics/events?${params.toString()}`);
}

async function fetchAnalyticsExportPayload(format: AnalyticsExportFormat): Promise<{
  ext: 'json' | 'prom';
  mimeType: string;
  content: string;
}> {
  const response = await fetch(
    `${apiConfig.baseUrl}/api/${apiConfig.version}/analytics/export?format=${format}`,
    {
      headers: buildApiHeaders({
        Accept: format === 'prometheus' ? 'text/plain' : 'application/json',
      }),
    }
  );

  if (!response.ok) {
    let body: unknown = undefined;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw new ApiError('Request failed', response.status, body);
  }

  if (format === 'prometheus') {
    return {
      ext: 'prom',
      mimeType: 'text/plain;charset=utf-8',
      content: await response.text(),
    };
  }

  const payload = await response.json();
  return {
    ext: 'json',
    mimeType: 'application/json;charset=utf-8',
    content: JSON.stringify(payload, null, 2),
  };
}

export async function downloadAnalyticsExport(format: AnalyticsExportFormat): Promise<string> {
  const payload = await fetchAnalyticsExportPayload(format);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `skillmeat-analytics-${format}-${timestamp}.${payload.ext}`;

  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return filename;
  }

  const blob = new Blob([payload.content], { type: payload.mimeType });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(href);
  return filename;
}

// Query keys
const analyticsKeys = {
  all: ['analytics'] as const,
  summary: () => [...analyticsKeys.all, 'summary'] as const,
  enterpriseSummary: () => [...analyticsKeys.all, 'enterprise-summary'] as const,
  topArtifacts: (limit: number, artifactType?: string) =>
    [...analyticsKeys.all, 'top-artifacts', limit, artifactType] as const,
  trends: (period: TimePeriod, days: number) =>
    [...analyticsKeys.all, 'trends', period, days] as const,
  events: (options: AnalyticsEventsQueryOptions) =>
    [...analyticsKeys.all, 'events', JSON.stringify(options)] as const,
};

/**
 * Hook to fetch analytics summary.
 */
export function useAnalyticsSummary() {
  return useQuery({
    queryKey: analyticsKeys.summary(),
    queryFn: fetchAnalyticsSummary,
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

/**
 * Hook to fetch enterprise analytics summary.
 */
export function useEnterpriseAnalyticsSummary() {
  return useQuery({
    queryKey: analyticsKeys.enterpriseSummary(),
    queryFn: fetchEnterpriseSummary,
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

/**
 * Hook to fetch top artifacts.
 */
export function useTopArtifacts(limit = 10, artifactType?: string) {
  return useQuery({
    queryKey: analyticsKeys.topArtifacts(limit, artifactType),
    queryFn: () => fetchTopArtifacts(limit, artifactType),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

/**
 * Hook to fetch usage trends.
 */
export function useUsageTrends(period: TimePeriod = 'day', days = 30) {
  return useQuery({
    queryKey: analyticsKeys.trends(period, days),
    queryFn: () => fetchUsageTrends(period, days),
    staleTime: 300000,
    refetchInterval: 600000,
  });
}

/**
 * Hook to fetch normalized analytics events.
 */
export function useAnalyticsEvents(options: AnalyticsEventsQueryOptions = {}) {
  return useQuery({
    queryKey: analyticsKeys.events(options),
    queryFn: () => fetchAnalyticsEvents(options),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}
