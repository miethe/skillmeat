/**
 * Enterprise analytics and observability export widget.
 */

'use client';

import { useMemo, useState, type ComponentType } from 'react';
import { Activity, Download, FolderKanban, Gauge, GitMerge, ShieldCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  downloadAnalyticsExport,
  type AnalyticsExportFormat,
  useEnterpriseAnalyticsSummary,
} from '@/hooks';
import { useToast } from '@/hooks/use-toast';

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatMetric(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  return value.toFixed(digits);
}

export function EnterpriseInsightsWidget() {
  const { data, isLoading, isError } = useEnterpriseAnalyticsSummary();
  const { toast } = useToast();
  const [isExporting, setIsExporting] = useState<AnalyticsExportFormat | null>(null);

  const window7d = useMemo(
    () => data?.windows.find((item) => item.window_days === 7) ?? data?.windows[0],
    [data]
  );

  const onExport = async (format: AnalyticsExportFormat) => {
    setIsExporting(format);
    try {
      const filename = await downloadAnalyticsExport(format);
      toast({
        title: 'Export complete',
        description: `Saved ${filename}`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown export error';
      toast({
        title: 'Export failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsExporting(null);
    }
  };

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Enterprise Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Enterprise metrics are currently unavailable.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Enterprise Insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-20" />
            ))}
          </div>
          <Skeleton className="h-28" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Enterprise Insights</CardTitle>
          <Badge variant="outline">
            {data.total_projects.toLocaleString()} projects, {data.total_events.toLocaleString()} events
          </Badge>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onExport('json')}
            disabled={isExporting !== null}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            {isExporting === 'json' ? 'Exporting JSON...' : 'Export JSON'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onExport('prometheus')}
            disabled={isExporting !== null}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            {isExporting === 'prometheus' ? 'Exporting Prometheus...' : 'Export Prometheus'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onExport('otel')}
            disabled={isExporting !== null}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            {isExporting === 'otel' ? 'Exporting OTel...' : 'Export OTel'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <MetricTile
            icon={Gauge}
            label="Deploy/day (7d)"
            value={formatMetric(data.delivery.deployment_frequency_7d)}
            caption={`${data.delivery.unique_artifacts_deployed_30d} artifacts deployed (30d)`}
          />
          <MetricTile
            icon={ShieldCheck}
            label="Sync Success (7d)"
            value={formatPercent(data.reliability.sync_success_rate_7d)}
            caption={`Failure rate (30d): ${formatPercent(data.reliability.change_failure_rate_30d)}`}
          />
          <MetricTile
            icon={Activity}
            label="Search->Deploy (30d)"
            value={formatPercent(data.adoption.search_to_deploy_conversion_30d)}
            caption={`${data.adoption.active_projects_30d.toLocaleString()} active projects`}
          />
          <MetricTile
            icon={GitMerge}
            label="Merge Events"
            value={data.history_summary.merge_events.toLocaleString()}
            caption={`${data.history_summary.version_events.toLocaleString()} provenance events`}
          />
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Top Projects (30d)</h4>
            {data.top_projects.slice(0, 5).map((project) => (
              <div
                key={project.project_path}
                className="flex items-center justify-between rounded border px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{project.project_path}</p>
                  <p className="text-xs text-muted-foreground">
                    {project.deploy_count} deploys, {project.sync_count} syncs
                  </p>
                </div>
                <Badge variant="secondary">{project.event_count}</Badge>
              </div>
            ))}
            {data.top_projects.length === 0 && (
              <p className="text-sm text-muted-foreground">No project activity detected.</p>
            )}
          </div>
          <div className="space-y-2">
            <h4 className="text-sm font-medium">7 Day Window</h4>
            <div className="rounded border p-3">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <FolderKanban className="h-4 w-4" />
                {window7d ? `${window7d.total_events.toLocaleString()} events` : 'No data'}
              </div>
              {window7d && (
                <div className="space-y-1 text-xs text-muted-foreground">
                  <p>Deploys: {window7d.deploy_events}</p>
                  <p>Syncs: {window7d.sync_events}</p>
                  <p>Updates: {window7d.update_events}</p>
                  <p>Unique artifacts: {window7d.unique_artifacts}</p>
                  <p>Success rate: {formatPercent(window7d.success_rate)}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MetricTile({
  icon: Icon,
  label,
  value,
  caption,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  caption: string;
}) {
  return (
    <div className="rounded border p-3">
      <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        <span>{label}</span>
      </div>
      <p className="text-xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{caption}</p>
    </div>
  );
}
