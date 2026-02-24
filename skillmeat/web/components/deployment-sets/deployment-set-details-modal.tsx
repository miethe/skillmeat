/**
 * DeploymentSetDetailsModal - Detail view modal for a single deployment set
 *
 * Provides a tabbed dialog for browsing deployment set metadata and members.
 * Follows the same Dialog + Tabs pattern as ArtifactDetailsModal.
 *
 * @example
 * ```tsx
 * <DeploymentSetDetailsModal
 *   setId={selectedSetId}
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { useState } from 'react';
import { Layers, Users, AlertCircle, Loader2 } from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';
import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import { useDeploymentSet } from '@/hooks';

// ============================================================================
// Types
// ============================================================================

export interface DeploymentSetDetailsModalProps {
  /** ID of the deployment set to display, or null when closed */
  setId: string | null;
  /** Whether the dialog is open */
  open: boolean;
  /** Callback to control open state */
  onOpenChange: (open: boolean) => void;
}

// ============================================================================
// Tab config
// ============================================================================

const TABS: Tab[] = [
  { value: 'overview', label: 'Overview', icon: Layers },
  { value: 'members', label: 'Members', icon: Users },
];

// ============================================================================
// Loading skeleton
// ============================================================================

function DeploymentSetDetailsSkeleton() {
  return (
    <div className="space-y-4 px-6 py-4" aria-busy="true" aria-label="Loading deployment set">
      <div className="space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-1/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}

// ============================================================================
// Error state
// ============================================================================

function DeploymentSetDetailsError({ message }: { message: string }) {
  return (
    <div
      className="flex flex-col items-center gap-3 px-6 py-12 text-center"
      role="alert"
      aria-live="assertive"
    >
      <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
      <p className="text-sm font-medium text-destructive">Failed to load deployment set</p>
      <p className="max-w-xs text-xs text-muted-foreground">{message}</p>
    </div>
  );
}

// ============================================================================
// Main component
// ============================================================================

/**
 * DeploymentSetDetailsModal
 *
 * Renders a max-w-2xl Dialog containing tabbed content for a deployment set.
 * Fetches the set via useDeploymentSet — disabled when setId is null.
 * Shows loading skeleton while fetching and an error state on failure.
 */
export function DeploymentSetDetailsModal({
  setId,
  open,
  onOpenChange,
}: DeploymentSetDetailsModalProps) {
  const [activeTab, setActiveTab] = useState<string>('overview');

  const {
    data: deploymentSet,
    isLoading,
    error,
  } = useDeploymentSet(setId ?? '');

  // Reset to overview tab whenever a different set is opened
  React.useEffect(() => {
    if (open) {
      setActiveTab('overview');
    }
  }, [open, setId]);

  // Derive dialog title — shown even during loading
  const title = deploymentSet?.name ?? (isLoading ? 'Loading…' : 'Deployment Set');
  const description = deploymentSet?.description ?? undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[90vh] max-w-2xl flex-col gap-0 overflow-hidden p-0"
        aria-label={`Deployment set details: ${title}`}
      >
        {/* Header */}
        <ModalHeader
          icon={Layers}
          iconClassName="text-primary"
          title={title}
          description={description}
          actions={
            isLoading ? (
              <Loader2
                className="h-4 w-4 animate-spin text-muted-foreground"
                aria-label="Loading"
              />
            ) : undefined
          }
        />

        {/* Body */}
        {error ? (
          <DeploymentSetDetailsError message={error.message} />
        ) : isLoading || !deploymentSet ? (
          <DeploymentSetDetailsSkeleton />
        ) : (
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="flex flex-1 flex-col overflow-hidden"
          >
            <TabNavigation
              tabs={TABS}
              ariaLabel="Deployment set detail tabs"
            />

            {/* Overview tab — placeholder for next batch */}
            <TabContentWrapper value="overview">
              <div
                className="flex flex-col gap-2 rounded-md border border-dashed border-muted-foreground/30 px-4 py-8 text-center"
                role="region"
                aria-label="Overview placeholder"
              >
                <Layers className="mx-auto h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">
                  Overview content will be implemented in the next batch.
                </p>
              </div>
            </TabContentWrapper>

            {/* Members tab — placeholder for later batch */}
            <TabContentWrapper value="members">
              <div
                className="flex flex-col gap-2 rounded-md border border-dashed border-muted-foreground/30 px-4 py-8 text-center"
                role="region"
                aria-label="Members placeholder"
              >
                <Users className="mx-auto h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">
                  Members content will be implemented in a later batch.
                </p>
              </div>
            </TabContentWrapper>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
