/**
 * Dashboard Page
 *
 * Main dashboard with analytics widgets and quick stats
 */

import { AnalyticsGrid } from '@/components/dashboard/analytics-grid';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Enterprise analytics for artifact delivery, reliability, provenance, and agent operations
        </p>
      </div>

      <AnalyticsGrid enableLiveUpdates={true} />
    </div>
  );
}
