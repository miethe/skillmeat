/**
 * Dashboard Page
 *
 * Main dashboard with analytics widgets and quick stats
 */

import { AnalyticsGrid } from '@/components/dashboard/analytics-grid';
import { SyncToolsCard } from '@/components/dashboard/sync-tools-card';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to SkillMeat - Your personal collection manager for Claude Code artifacts
        </p>
      </div>

      <AnalyticsGrid enableLiveUpdates={true} />
      <SyncToolsCard />
    </div>
  );
}
