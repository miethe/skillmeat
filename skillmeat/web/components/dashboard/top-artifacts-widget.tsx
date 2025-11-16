/**
 * Top Artifacts Widget
 *
 * Displays most used artifacts in a bar chart or ranked list
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { useTopArtifacts } from '@/hooks/useAnalytics';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { calculatePercentage } from '@/lib/utils';
import type { TopArtifact } from '@/types/analytics';

const COLORS = {
  skill: '#3b82f6',    // blue
  command: '#10b981',  // green
  agent: '#8b5cf6',    // purple
  mcp: '#f59e0b',      // amber
  hook: '#ec4899',     // pink
};

interface TopArtifactsWidgetProps {
  limit?: number;
  showChart?: boolean;
}

export function TopArtifactsWidget({ limit = 10, showChart = true }: TopArtifactsWidgetProps) {
  const { data, isLoading, isError } = useTopArtifacts(limit);

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top Artifacts</CardTitle>
          <CardDescription>Most used artifacts by deployment count</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-muted-foreground">
            <p>Failed to load top artifacts data</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return <TopArtifactsWidgetSkeleton />;
  }

  const artifacts = data?.items ?? [];
  const totalUsage = artifacts.reduce((sum, a) => sum + a.usage_count, 0);

  // Prepare data for chart
  const chartData = artifacts.map((artifact) => ({
    name: artifact.artifact_name,
    usage: artifact.usage_count,
    deployments: artifact.deployment_count,
    type: artifact.artifact_type,
    percentage: calculatePercentage(artifact.usage_count, totalUsage),
  }));

  if (artifacts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top Artifacts</CardTitle>
          <CardDescription>Most used artifacts by deployment count</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <p className="text-sm">No artifacts found</p>
            <p className="text-xs mt-2">Add artifacts to your collection to see usage statistics</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Artifacts</CardTitle>
        <CardDescription>Most used artifacts by deployment count</CardDescription>
      </CardHeader>
      <CardContent>
        {showChart && chartData.length > 0 && (
          <div className="h-64 mb-6">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                layout="horizontal"
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  type="number"
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{ fill: 'hsl(var(--muted) / 0.3)' }}
                />
                <Bar dataKey="usage" radius={[0, 4, 4, 0]} label={{ position: 'right' }}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[entry.type as keyof typeof COLORS] || COLORS.skill}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Ranked List */}
        <div className="space-y-3">
          {artifacts.slice(0, 5).map((artifact, index) => (
            <ArtifactRow
              key={artifact.artifact_name}
              artifact={artifact}
              rank={index + 1}
              percentage={calculatePercentage(artifact.usage_count, totalUsage)}
            />
          ))}
        </div>

        {artifacts.length > 5 && (
          <div className="mt-4 text-center">
            <p className="text-xs text-muted-foreground">
              Showing top 5 of {artifacts.length} artifacts
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Individual artifact row in ranked list
 */
function ArtifactRow({
  artifact,
  rank,
  percentage,
}: {
  artifact: TopArtifact;
  rank: number;
  percentage: number;
}) {
  return (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex-shrink-0 w-6 text-center font-semibold text-muted-foreground text-sm">
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-sm truncate">{artifact.artifact_name}</p>
          <Badge variant="outline" className="flex-shrink-0 text-xs">
            {artifact.artifact_type}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          {artifact.deployment_count} deployment{artifact.deployment_count !== 1 ? 's' : ''}
        </p>
      </div>
      <div className="flex-shrink-0 text-right">
        <p className="font-semibold text-sm">{artifact.usage_count}</p>
        <p className="text-xs text-muted-foreground">{percentage.toFixed(1)}%</p>
      </div>
    </div>
  );
}

/**
 * Custom tooltip for chart
 */
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3">
      <div className="space-y-1">
        <p className="font-semibold text-sm">{data.name}</p>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {data.type}
          </Badge>
          <span className="text-xs text-muted-foreground">{data.percentage.toFixed(1)}%</span>
        </div>
        <div className="pt-2 space-y-1">
          <p className="text-xs">
            <span className="text-muted-foreground">Usage:</span>{' '}
            <span className="font-medium">{data.usage}</span>
          </p>
          <p className="text-xs">
            <span className="text-muted-foreground">Deployments:</span>{' '}
            <span className="font-medium">{data.deployments}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Loading skeleton
 */
export function TopArtifactsWidgetSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Artifacts</CardTitle>
        <CardDescription>Most used artifacts by deployment count</CardDescription>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-64 w-full mb-6" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-4 w-6" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-4 w-12" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
