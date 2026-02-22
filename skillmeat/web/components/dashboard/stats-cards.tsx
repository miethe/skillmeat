/**
 * Quick Stats Cards
 *
 * Displays high-level statistics in card format
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Package, GitBranch, Activity, Clock } from 'lucide-react';
import { useAnalyticsSummary, useEnterpriseAnalyticsSummary } from '@/hooks';
import { formatDistanceToNow } from '@/lib/utils';

export function StatsCards() {
  const summaryQuery = useAnalyticsSummary();
  const enterpriseQuery = useEnterpriseAnalyticsSummary();

  const summary = summaryQuery.data;
  const enterprise = enterpriseQuery.data;
  const isLoading = summaryQuery.isLoading && enterpriseQuery.isLoading;
  const isError = summaryQuery.isError && enterpriseQuery.isError;

  if (isError) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-destructive">
              Error Loading Stats
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Failed to fetch analytics data</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return <StatsCardsSkeleton />;
  }

  const totalArtifacts = summary?.total_artifacts ?? enterprise?.total_artifacts ?? 0;
  const totalCollections = summary?.total_collections ?? enterprise?.total_collections ?? 0;
  const deploymentsPerDay = enterprise?.delivery.deployment_frequency_7d ?? 0;
  const syncSuccessRate = enterprise?.reliability.sync_success_rate_7d;
  const activeProjects = enterprise?.adoption.active_projects_30d ?? 0;
  const totalEvents = enterprise?.total_events ?? summary?.total_events ?? 0;
  const lastActivity = summary?.last_activity ?? enterprise?.generated_at;

  const stats = [
    {
      title: 'Total Artifacts',
      value: totalArtifacts,
      description: `${totalCollections} collection${totalCollections === 1 ? '' : 's'}`,
      icon: Package,
      color: 'text-brand',
    },
    {
      title: 'Deploy/day (7d)',
      value: deploymentsPerDay.toFixed(2),
      description: enterprise ? `${enterprise.delivery.unique_artifacts_deployed_30d} artifacts deployed (30d)` : 'Awaiting enterprise metrics',
      icon: GitBranch,
      color: 'text-success',
      valueClass: 'text-xl',
    },
    {
      title: 'Sync Success (7d)',
      value: syncSuccessRate !== undefined ? `${(syncSuccessRate * 100).toFixed(1)}%` : 'N/A',
      description: enterprise
        ? `${activeProjects.toLocaleString()} active projects (30d)`
        : 'Awaiting enterprise metrics',
      icon: Activity,
      color: 'text-warning',
      valueClass: 'text-xl',
    },
    {
      title: 'Last Sync',
      value: lastActivity ? formatDistanceToNow(new Date(lastActivity)) : 'Never',
      description: totalEvents ? `${totalEvents.toLocaleString()} total events` : 'No events',
      icon: Clock,
      color: 'text-primary',
      valueClass: 'text-xl',
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <Icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className={`font-bold ${stat.valueClass || 'text-2xl'}`}>
                {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

/**
 * Loading skeleton for stats cards
 */
export function StatsCardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-4 rounded" />
          </CardHeader>
          <CardContent>
            <Skeleton className="mb-2 h-8 w-16" />
            <Skeleton className="h-3 w-32" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
