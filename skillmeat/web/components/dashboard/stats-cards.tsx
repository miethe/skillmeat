/**
 * Quick Stats Cards
 *
 * Displays high-level statistics in card format
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Package, GitBranch, Activity, Clock } from 'lucide-react';
import { useAnalyticsSummary } from '@/hooks';
import { formatDistanceToNow } from '@/lib/utils';

export function StatsCards() {
  const { data, isLoading, isError } = useAnalyticsSummary();

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

  const stats = [
    {
      title: 'Total Artifacts',
      value: data?.total_artifacts ?? 0,
      description: `${data?.total_collections ?? 0} collection${data?.total_collections === 1 ? '' : 's'}`,
      icon: Package,
      color: 'text-brand',
    },
    {
      title: 'Active Deployments',
      value: data?.total_deployments ?? 0,
      description: `${data?.most_deployed_artifact ?? 'none'} most deployed`,
      icon: GitBranch,
      color: 'text-success',
    },
    {
      title: 'Recent Activity',
      value: data?.recent_activity_count ?? 0,
      description: 'events in last 24 hours',
      icon: Activity,
      color: 'text-warning',
    },
    {
      title: 'Last Sync',
      value: data?.last_activity ? formatDistanceToNow(new Date(data.last_activity)) : 'Never',
      description: data?.total_events ? `${data.total_events} total events` : 'No events',
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
