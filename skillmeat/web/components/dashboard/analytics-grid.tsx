/**
 * Analytics Grid
 *
 * Container component that organizes all analytics widgets
 * with live update indicators
 */

'use client';

import { StatsCards } from './stats-cards';
import { TopArtifactsWidget } from './top-artifacts-widget';
import { UsageTrendsWidget } from './usage-trends-widget';
import { useAnalyticsStream } from '@/hooks/useAnalyticsStream';
import { Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AnalyticsGridProps {
  enableLiveUpdates?: boolean;
}

export function AnalyticsGrid({ enableLiveUpdates = true }: AnalyticsGridProps) {
  const { status } = useAnalyticsStream({
    enabled: enableLiveUpdates,
  });

  return (
    <div className="space-y-6" data-testid="analytics-grid">
      {/* Live update indicator */}
      {enableLiveUpdates && (
        <div className="flex items-center justify-between" data-testid="live-indicator">
          <div className="flex items-center gap-2 text-sm">
            <div
              className={cn(
                'w-2 h-2 rounded-full transition-colors',
                status.isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              )}
              data-testid="status-dot"
              aria-label={status.isConnected ? 'Connected' : 'Disconnected'}
            />
            <span className="text-muted-foreground">
              {status.isConnected ? 'Live updates active' : 'Updates paused'}
            </span>
            {status.lastUpdate && (
              <span className="text-xs text-muted-foreground" data-testid="last-update">
                (Last: {status.lastUpdate.toLocaleTimeString()})
              </span>
            )}
          </div>
          {status.eventCount > 0 && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground" data-testid="event-count">
              <Activity className="h-3 w-3" aria-hidden="true" />
              <span>{status.eventCount} updates</span>
            </div>
          )}
        </div>
      )}

      {/* Quick Stats Cards */}
      <StatsCards />

      {/* Main Analytics Widgets */}
      <div className="grid gap-6 md:grid-cols-2" data-testid="widgets-grid">
        <TopArtifactsWidget limit={10} showChart={true} />
        <UsageTrendsWidget showType="area" />
      </div>
    </div>
  );
}
