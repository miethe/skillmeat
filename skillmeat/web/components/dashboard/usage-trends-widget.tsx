/**
 * Usage Trends Widget
 *
 * Displays time-series usage data with interactive charts
 */

'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useUsageTrends } from '@/hooks/useAnalytics';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { formatDate } from '@/lib/utils';
import type { TimePeriod } from '@/types/analytics';

const PERIOD_OPTIONS: { value: TimePeriod; label: string; days: number }[] = [
  { value: 'day', label: 'Last 7 Days', days: 7 },
  { value: 'day', label: 'Last 30 Days', days: 30 },
  { value: 'week', label: 'Last 12 Weeks', days: 84 },
  { value: 'month', label: 'Last 12 Months', days: 365 },
];

interface UsageTrendsWidgetProps {
  showType?: 'line' | 'area';
}

export function UsageTrendsWidget({ showType = 'area' }: UsageTrendsWidgetProps) {
  const [selectedPeriodIndex, setSelectedPeriodIndex] = useState(1); // 30 days default
  const selectedPeriod = PERIOD_OPTIONS[selectedPeriodIndex]!;

  const { data, isLoading, isError } = useUsageTrends(selectedPeriod.value, selectedPeriod.days);

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Usage Trends</CardTitle>
          <CardDescription>Activity over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80 text-muted-foreground">
            <p>Failed to load usage trends data</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return <UsageTrendsWidgetSkeleton />;
  }

  const trends = data?.data_points ?? [];

  // Prepare data for chart
  const chartData = trends.map((point) => ({
    date: new Date(point.timestamp).getTime(),
    dateLabel: formatDate(point.timestamp),
    deployments: point.deployment_count,
    usage: point.usage_count,
    artifacts: point.unique_artifacts,
    topArtifact: point.top_artifact,
  }));

  if (trends.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Usage Trends</CardTitle>
            <CardDescription>Activity over time</CardDescription>
          </div>
          <PeriodSelector
            options={PERIOD_OPTIONS}
            selectedIndex={selectedPeriodIndex}
            onChange={setSelectedPeriodIndex}
          />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-80 text-muted-foreground">
            <p className="text-sm">No usage data available</p>
            <p className="text-xs mt-2">Deploy artifacts to start tracking usage trends</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle>Usage Trends</CardTitle>
          <CardDescription>Activity over time</CardDescription>
        </div>
        <PeriodSelector
          options={PERIOD_OPTIONS}
          selectedIndex={selectedPeriodIndex}
          onChange={setSelectedPeriodIndex}
        />
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            {showType === 'area' ? (
              <AreaChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorDeployments" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return selectedPeriod.value === 'day'
                      ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      : date.toLocaleDateString('en-US', { month: 'short' });
                  }}
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                  iconType="circle"
                />
                <Area
                  type="monotone"
                  dataKey="usage"
                  name="Usage Events"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#colorUsage)"
                />
                <Area
                  type="monotone"
                  dataKey="deployments"
                  name="Deployments"
                  stroke="#10b981"
                  strokeWidth={2}
                  fill="url(#colorDeployments)"
                />
              </AreaChart>
            ) : (
              <LineChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return selectedPeriod.value === 'day'
                      ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      : date.toLocaleDateString('en-US', { month: 'short' });
                  }}
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                  iconType="circle"
                />
                <Line
                  type="monotone"
                  dataKey="usage"
                  name="Usage Events"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="deployments"
                  name="Deployments"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>

        {/* Summary stats below chart */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t">
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {trends.reduce((sum, t) => sum + t.usage_count, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Total Usage</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">
              {trends.reduce((sum, t) => sum + t.deployment_count, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Total Deployments</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-600">
              {Math.max(...trends.map((t) => t.unique_artifacts), 0)}
            </p>
            <p className="text-xs text-muted-foreground">Peak Artifacts</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Period selector component
 */
function PeriodSelector({
  options,
  selectedIndex,
  onChange,
}: {
  options: typeof PERIOD_OPTIONS;
  selectedIndex: number;
  onChange: (index: number) => void;
}) {
  return (
    <select
      value={selectedIndex}
      onChange={(e) => onChange(parseInt(e.target.value))}
      className="text-sm border border-input bg-background px-3 py-1.5 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
      aria-label="Select time period"
    >
      {options.map((option, index) => (
        <option key={index} value={index}>
          {option.label}
        </option>
      ))}
    </select>
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
      <div className="space-y-2">
        <p className="font-semibold text-sm">{data.dateLabel}</p>
        <div className="space-y-1">
          {payload.map((entry: any) => (
            <div key={entry.name} className="flex items-center justify-between gap-4">
              <span className="text-xs flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                {entry.name}:
              </span>
              <span className="text-xs font-medium">{entry.value}</span>
            </div>
          ))}
          <div className="pt-1 mt-1 border-t text-xs text-muted-foreground">
            Top: {data.topArtifact}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Loading skeleton
 */
export function UsageTrendsWidgetSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Usage Trends</CardTitle>
          <CardDescription>Activity over time</CardDescription>
        </div>
        <Skeleton className="h-9 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-80 w-full" />
        <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="text-center space-y-2">
              <Skeleton className="h-8 w-16 mx-auto" />
              <Skeleton className="h-3 w-24 mx-auto" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
