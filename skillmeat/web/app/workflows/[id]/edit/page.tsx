'use client';

/**
 * Edit Workflow Page
 *
 * Fetches an existing workflow by id and renders WorkflowBuilderView in edit
 * mode. Shows a loading skeleton while the query is in-flight and an inline
 * error message if the workflow cannot be loaded.
 *
 * Next.js 15 note: params is a Promise in Server Components, but this file is
 * 'use client' so we unwrap it via useParams() instead of awaiting props.
 */

import { useParams } from 'next/navigation';
import { AlertCircle } from 'lucide-react';
import {
  WorkflowBuilderView,
  WorkflowBuilderSkeleton,
} from '@/components/workflow/workflow-builder-view';
import { useWorkflow } from '@/hooks';
import { cn } from '@/lib/utils';

// ============================================================================
// Error state
// ============================================================================

interface ErrorStateProps {
  message?: string;
}

function ErrorState({ message }: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex h-screen flex-col items-center justify-center gap-4',
        'bg-background text-center px-6',
      )}
      role="alert"
    >
      <AlertCircle
        className="h-10 w-10 text-destructive/70"
        aria-hidden="true"
      />
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">
          Failed to load workflow
        </p>
        {message && (
          <p className="text-xs text-muted-foreground">{message}</p>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Page component
// ============================================================================

export default function EditWorkflowPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? '';

  const { data: workflow, isLoading, isError, error } = useWorkflow(id);

  if (isLoading) {
    return <WorkflowBuilderSkeleton />;
  }

  if (isError || !workflow) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : undefined}
      />
    );
  }

  return <WorkflowBuilderView existingWorkflow={workflow} />;
}
