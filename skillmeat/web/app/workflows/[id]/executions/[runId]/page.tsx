/**
 * Execution Dashboard Page
 *
 * Real-time dashboard for a single workflow execution run,
 * showing step-by-step progress, logs, and output.
 * Placeholder shell — full implementation in Phase 5/6.
 *
 * Next.js 15: params is a Promise — must be awaited.
 */

import { Activity } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

interface ExecutionDashboardPageProps {
  params: Promise<{ id: string; runId: string }>;
}

export default async function ExecutionDashboardPage({ params }: ExecutionDashboardPageProps) {
  const { id, runId } = await params;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Execution Dashboard"
        description={`Run ${runId} — Workflow ${id}`}
        icon={<Activity className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <Activity className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Execution Dashboard — coming soon</p>
          <p className="font-mono text-xs text-muted-foreground/60">
            workflow: {id} / run: {runId}
          </p>
        </div>
      </div>
    </div>
  );
}
