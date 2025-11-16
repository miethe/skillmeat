/**
 * Analytics Types for SkillMeat
 *
 * These types represent analytics data from the API endpoints
 */

export interface AnalyticsSummary {
  total_collections: number;
  total_artifacts: number;
  total_deployments: number;
  total_events: number;
  artifacts_by_type: Record<string, number>;
  recent_activity_count: number;
  most_deployed_artifact: string;
  last_activity: string;
}

export interface TopArtifact {
  artifact_name: string;
  artifact_type: string;
  deployment_count: number;
  usage_count: number;
  last_used: string;
  collections: string[];
}

export interface PageInfo {
  has_next_page: boolean;
  has_previous_page: boolean;
  start_cursor: string | null;
  end_cursor: string | null;
  total_count: number;
}

export interface TopArtifactsResponse {
  items: TopArtifact[];
  page_info: PageInfo;
}

export interface TrendDataPoint {
  timestamp: string;
  period: string;
  deployment_count: number;
  usage_count: number;
  unique_artifacts: number;
  top_artifact: string;
}

export interface TrendsResponse {
  period_type: string;
  start_date: string;
  end_date: string;
  data_points: TrendDataPoint[];
  total_periods: number;
}

export type TimePeriod = 'day' | 'week' | 'month';

export interface AnalyticsFilters {
  period?: TimePeriod;
  days?: number;
  artifact_type?: string;
}

/**
 * Analytics event for real-time updates
 */
export interface AnalyticsEvent {
  type: 'summary_update' | 'artifact_update' | 'trend_update';
  data: AnalyticsSummary | TopArtifact | TrendDataPoint;
  timestamp: string;
}
