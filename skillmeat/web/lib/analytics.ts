type AnalyticsEvent = {
  discovery_scan: {
    discovered_count: number;
    duration_ms: number;
    has_errors: boolean;
  };
  discovery_banner_view: {
    discovered_count: number;
  };
  discovery_modal_open: {
    discovered_count: number;
  };
  discovery_tab_view: {
    project_id: string;
    artifact_count: number;
  };
  discovery_filter_applied: {
    filter_type: 'status' | 'type' | 'search';
    filter_value: string;
  };
  discovery_sort_applied: {
    sort_field: 'name' | 'type' | 'discovered_at';
    sort_direction: 'asc' | 'desc';
  };
  skip_checkbox_toggle: {
    artifact_key: string;
    skipped: boolean;
  };
  skip_preference_cleared: {
    project_id: string;
    cleared_count: number;
  };
  bulk_import: {
    requested_count: number;
    imported_count: number;
    failed_count: number;
    duration_ms: number;
  };
  auto_population_fetch: {
    source: string;
    success: boolean;
    duration_ms?: number;
    error?: string;
  };
  parameter_edit: {
    artifact_type: string;
    updated_fields: string[];
  };
};

export function trackEvent<K extends keyof AnalyticsEvent>(
  name: K,
  data: AnalyticsEvent[K]
) {
  // Log in development
  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics]', name, data);
  }

  // Send to analytics service if available
  if (typeof window !== 'undefined' && (window as any).analytics?.track) {
    (window as any).analytics.track(name, data);
  }

  // Could also send to internal API endpoint
  // fetch('/api/analytics', { method: 'POST', body: JSON.stringify({ event: name, data }) });
}

// Helper hooks for common tracking patterns
export function useTrackDiscovery() {
  return {
    trackScan: (result: { discovered_count: number; scan_duration_ms: number; errors: string[] }) => {
      trackEvent('discovery_scan', {
        discovered_count: result.discovered_count,
        duration_ms: result.scan_duration_ms,
        has_errors: result.errors.length > 0,
      });
    },
    trackBannerView: (count: number) => {
      trackEvent('discovery_banner_view', { discovered_count: count });
    },
    trackModalOpen: (count: number) => {
      trackEvent('discovery_modal_open', { discovered_count: count });
    },
    trackTabView: (projectId: string, count: number) => {
      trackEvent('discovery_tab_view', { project_id: projectId, artifact_count: count });
    },
    trackFilterApplied: (type: string, value: string) => {
      trackEvent('discovery_filter_applied', {
        filter_type: type as 'status' | 'type' | 'search',
        filter_value: value,
      });
    },
    trackSortApplied: (field: string, direction: string) => {
      trackEvent('discovery_sort_applied', {
        sort_field: field as 'name' | 'type' | 'discovered_at',
        sort_direction: direction as 'asc' | 'desc',
      });
    },
    trackSkipToggle: (artifactKey: string, skipped: boolean) => {
      trackEvent('skip_checkbox_toggle', {
        artifact_key: artifactKey,
        skipped,
      });
    },
    trackSkipCleared: (projectId: string, count: number) => {
      trackEvent('skip_preference_cleared', {
        project_id: projectId,
        cleared_count: count,
      });
    },
    trackImport: (result: { total_requested: number; total_imported: number; total_failed: number; duration_ms: number }) => {
      trackEvent('bulk_import', {
        requested_count: result.total_requested,
        imported_count: result.total_imported,
        failed_count: result.total_failed,
        duration_ms: result.duration_ms,
      });
    },
  };
}
