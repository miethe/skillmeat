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

export interface EnterpriseMetricWindow {
  window_days: number;
  total_events: number;
  deploy_events: number;
  sync_events: number;
  update_events: number;
  remove_events: number;
  search_events: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  unique_artifacts: number;
  unique_projects: number;
  unique_collections: number;
  deploy_frequency_per_day: number;
}

export interface ProjectActivityItem {
  project_path: string;
  event_count: number;
  deploy_count: number;
  sync_count: number;
  last_activity: string;
}

export interface ArtifactHistorySummary {
  version_events: number;
  merge_events: number;
  deployment_events: number;
}

export interface EnterpriseDeliveryMetrics {
  deployment_frequency_7d: number;
  deployment_frequency_30d: number;
  median_deploy_interval_minutes_30d: number | null;
  unique_artifacts_deployed_30d: number;
}

export interface EnterpriseReliabilityMetrics {
  change_failure_rate_30d: number;
  sync_success_rate_7d: number;
  rollback_rate_30d: number;
  mean_time_to_recovery_hours_30d: number | null;
}

export interface EnterpriseAdoptionMetrics {
  active_projects_7d: number;
  active_projects_30d: number;
  active_collections_30d: number;
  search_to_deploy_conversion_30d: number;
}

export interface EnterpriseAnalyticsSummary {
  generated_at: string;
  total_events: number;
  total_artifacts: number;
  total_projects: number;
  total_collections: number;
  event_type_counts: Record<string, number>;
  windows: EnterpriseMetricWindow[];
  delivery: EnterpriseDeliveryMetrics;
  reliability: EnterpriseReliabilityMetrics;
  adoption: EnterpriseAdoptionMetrics;
  top_projects: ProjectActivityItem[];
  top_artifacts: TopArtifact[];
  history_summary: ArtifactHistorySummary;
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
  total_count: number | null;
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

export interface AnalyticsEventItem {
  id: number;
  event_type: string;
  artifact_name: string;
  artifact_type: string;
  collection_name: string | null;
  project_path: string | null;
  timestamp: string;
  metadata: Record<string, unknown>;
  outcome: string | null;
}

export interface AnalyticsEventsResponse {
  items: AnalyticsEventItem[];
  page_info: PageInfo;
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
  type: 'summary_update' | 'artifact_update' | 'trend_update' | string;
  data: Record<string, unknown>;
  timestamp: string;
}
