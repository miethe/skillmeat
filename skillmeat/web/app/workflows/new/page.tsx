'use client';

/**
 * New Workflow Page
 *
 * Renders the WorkflowBuilderView in create mode (no existing workflow).
 * All builder state starts empty; saving calls useCreateWorkflow.
 */

import { WorkflowBuilderView } from '@/components/workflow/workflow-builder-view';

export default function NewWorkflowPage() {
  return <WorkflowBuilderView />;
}
