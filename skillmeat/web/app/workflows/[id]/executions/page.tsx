/**
 * Workflow Executions Page
 *
 * Lists all execution runs for a specific workflow.
 * Placeholder shell — full implementation in Phase 5/6.
 *
 * Next.js 15: params is a Promise — must be awaited.
 */

import { PlayCircle } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

interface WorkflowExecutionsPageProps {
  params: Promise<{ id: string }>;
}

export default async function WorkflowExecutionsPage({ params }: WorkflowExecutionsPageProps) {
  const { id } = await params;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Workflow Executions"
        description={`Run history for workflow: ${id}`}
        icon={<PlayCircle className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <PlayCircle className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Workflow Executions list — coming soon</p>
          <p className="font-mono text-xs text-muted-foreground/60">{id}</p>
        </div>
      </div>
    </div>
  );
}
