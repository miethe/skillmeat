/**
 * New Workflow Page
 *
 * Form to create a new workflow.
 * Placeholder shell — full implementation in Phase 5/6.
 */

import { PlusCircle } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

export default function NewWorkflowPage() {
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="New Workflow"
        description="Define a new orchestration workflow"
        icon={<PlusCircle className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <PlusCircle className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Create Workflow form — coming soon</p>
        </div>
      </div>
    </div>
  );
}
