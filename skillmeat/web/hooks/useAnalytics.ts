/**
 * React Query hooks for analytics data fetching
 *
 * These hooks provide data fetching, caching, and state management for analytics.
 */

import { useQuery } from '@tanstack/react-query';
import type {
  AnalyticsSummary,
  TopArtifactsResponse,
  TrendsResponse,
  TimePeriod,
} from '@/types/analytics';

// Environment configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

// Mock API key for development (should be replaced with proper auth)
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-key-12345';

/**
 * Fetch analytics summary
 */
async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/analytics/summary`, {
    headers: {
      'X-API-Key': API_KEY,
    },
  });

  if (!response.ok) {
    // Return mock data if API is not available
    if (response.status === 404 || response.status === 503) {
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
    throw new Error('Failed to fetch analytics summary');
  }

  return response.json();
}

/**
 * Fetch top artifacts
 */
async function fetchTopArtifacts(
  limit = 10,
  artifactType?: string
): Promise<TopArtifactsResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    ...(artifactType && { artifact_type: artifactType }),
  });

  const response = await fetch(
    `${API_BASE_URL}/api/${API_VERSION}/analytics/top-artifacts?${params}`,
    {
      headers: {
        'X-API-Key': API_KEY,
      },
    }
  );

  if (!response.ok) {
    // Return mock data if API is not available
    if (response.status === 404 || response.status === 503) {
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
    throw new Error('Failed to fetch top artifacts');
  }

  return response.json();
}

/**
 * Fetch usage trends
 */
async function fetchUsageTrends(period: TimePeriod, days: number): Promise<TrendsResponse> {
  const params = new URLSearchParams({
    period,
    days: days.toString(),
  });

  const response = await fetch(
    `${API_BASE_URL}/api/${API_VERSION}/analytics/trends?${params}`,
    {
      headers: {
        'X-API-Key': API_KEY,
      },
    }
  );

  if (!response.ok) {
    // Return mock data if API is not available
    if (response.status === 404 || response.status === 503) {
      // Generate mock trend data
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
    throw new Error('Failed to fetch usage trends');
  }

  return response.json();
}

// Query keys
const analyticsKeys = {
  all: ['analytics'] as const,
  summary: () => [...analyticsKeys.all, 'summary'] as const,
  topArtifacts: (limit: number, artifactType?: string) =>
    [...analyticsKeys.all, 'top-artifacts', limit, artifactType] as const,
  trends: (period: TimePeriod, days: number) =>
    [...analyticsKeys.all, 'trends', period, days] as const,
};

/**
 * Hook to fetch analytics summary
 */
export function useAnalyticsSummary() {
  return useQuery({
    queryKey: analyticsKeys.summary(),
    queryFn: fetchAnalyticsSummary,
    staleTime: 30000, // Consider data fresh for 30 seconds
    refetchInterval: 60000, // Refetch every minute for live updates
  });
}

/**
 * Hook to fetch top artifacts
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
 * Hook to fetch usage trends
 */
export function useUsageTrends(period: TimePeriod = 'day', days = 30) {
  return useQuery({
    queryKey: analyticsKeys.trends(period, days),
    queryFn: () => fetchUsageTrends(period, days),
    staleTime: 60000, // Consider data fresh for 1 minute
    refetchInterval: 120000, // Refetch every 2 minutes
  });
}
