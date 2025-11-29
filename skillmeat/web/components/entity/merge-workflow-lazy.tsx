'use client';

import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

// Lazy load the heavy MergeWorkflow component
const MergeWorkflowDynamic = dynamic(
  () => import('./merge-workflow').then((mod) => ({ default: mod.MergeWorkflow })),
  {
    loading: () => (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Loading merge workflow...</span>
          </div>
        </CardContent>
      </Card>
    ),
    ssr: false, // Disable SSR for this heavy component
  }
);

interface MergeWorkflowLazyProps {
  entityId: string;
  projectPath: string;
  direction: 'upstream' | 'downstream';
  onComplete: () => void;
  onCancel: () => void;
}

export function MergeWorkflowLazy(props: MergeWorkflowLazyProps) {
  return <MergeWorkflowDynamic {...props} />;
}
