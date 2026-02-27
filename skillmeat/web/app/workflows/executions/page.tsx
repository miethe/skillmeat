/**
 * All Executions Page
 *
 * Global list of all workflow execution runs across all workflows.
 * Placeholder shell — full implementation in Phase 5/6.
 */

import { ListChecks } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

export default function AllExecutionsPage() {
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="All Executions"
        description="View and monitor all workflow runs across your collection"
        icon={<ListChecks className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <ListChecks className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">All Executions list — coming soon</p>
        </div>
      </div>
    </div>
  );
}
