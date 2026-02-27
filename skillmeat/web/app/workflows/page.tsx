/**
 * Workflow Library Page
 *
 * Lists all workflows in the user's collection.
 * Placeholder shell — full implementation in Phase 5/6.
 */

import { GitBranch } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

export default function WorkflowsPage() {
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Workflow Library"
        description="Browse and manage your orchestration workflows"
        icon={<GitBranch className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <GitBranch className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Workflow Library — coming soon</p>
        </div>
      </div>
    </div>
  );
}
