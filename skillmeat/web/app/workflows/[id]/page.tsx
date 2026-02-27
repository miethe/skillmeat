/**
 * Workflow Detail Page
 *
 * Shows the definition, metadata, and run history for a single workflow.
 * Placeholder shell — full implementation in Phase 5/6.
 *
 * Next.js 15: params is a Promise — must be awaited.
 */

import { GitBranch } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

interface WorkflowDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function WorkflowDetailPage({ params }: WorkflowDetailPageProps) {
  const { id } = await params;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Workflow Detail"
        description={`Workflow ID: ${id}`}
        icon={<GitBranch className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <GitBranch className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Workflow Detail — coming soon</p>
          <p className="font-mono text-xs text-muted-foreground/60">{id}</p>
        </div>
      </div>
    </div>
  );
}
