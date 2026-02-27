/**
 * Edit Workflow Page
 *
 * Form to modify an existing workflow's definition and configuration.
 * Placeholder shell — full implementation in Phase 5/6.
 *
 * Next.js 15: params is a Promise — must be awaited.
 */

import { Pencil } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';

interface EditWorkflowPageProps {
  params: Promise<{ id: string }>;
}

export default async function EditWorkflowPage({ params }: EditWorkflowPageProps) {
  const { id } = await params;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Edit Workflow"
        description={`Editing workflow: ${id}`}
        icon={<Pencil className="h-6 w-6" />}
      />
      <div className="flex items-center justify-center rounded-lg border border-dashed py-24 text-center">
        <div className="space-y-2">
          <Pencil className="mx-auto h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Edit Workflow form — coming soon</p>
          <p className="font-mono text-xs text-muted-foreground/60">{id}</p>
        </div>
      </div>
    </div>
  );
}
