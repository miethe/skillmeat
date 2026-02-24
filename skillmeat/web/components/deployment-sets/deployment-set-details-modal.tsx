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
import { useState, useMemo } from 'react';
import { Layers, Users, AlertCircle, Loader2, Tag, Calendar, Hash, Info } from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';
import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import { useDeploymentSet, useResolveSet, useDeploymentSetMembers, useArtifacts } from '@/hooks';
import { formatDate } from '@/lib/utils';
import type { DeploymentSet, DeploymentSetMember } from '@/types/deployment-sets';
import type { Artifact } from '@/types/artifact';
import {
  DeploymentSetMemberCard,
  DeploymentSetMemberCardSkeleton,
} from '@/components/deployment-sets/deployment-set-member-card';
import { ArtifactDetailsModal } from '@/components/collection/artifact-details-modal';

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
// Overview tab
// ============================================================================

/**
 * DeploymentSetOverviewTab
 *
 * Displays the full metadata for a deployment set:
 * name, description, color swatch, icon, tags, resolved member count,
 * and created/updated timestamps.
 *
 * Uses useResolveSet for the resolved artifact count (30s stale time so it
 * stays fresh after member mutations).
 */
function DeploymentSetOverviewTab({ deploymentSet }: { deploymentSet: DeploymentSet }) {
  const { data: resolution, isLoading: isResolving } = useResolveSet(deploymentSet.id);

  return (
    <div className="space-y-6" role="region" aria-label="Deployment set overview">
      {/* Identity: name, color swatch, icon */}
      <div>
        <div className="mb-1 flex items-center gap-2">
          <h2 className="text-base font-semibold leading-tight">{deploymentSet.name}</h2>
          {deploymentSet.color && (
            <span
              className="inline-block h-4 w-4 shrink-0 rounded-full border border-border"
              style={{ backgroundColor: deploymentSet.color }}
              aria-label={`Color: ${deploymentSet.color}`}
              title={deploymentSet.color}
            />
          )}
          {deploymentSet.icon && (
            <span
              className="text-base leading-none"
              aria-label={`Icon: ${deploymentSet.icon}`}
              role="img"
            >
              {deploymentSet.icon}
            </span>
          )}
        </div>
        {deploymentSet.description && (
          <p className="text-sm text-muted-foreground">{deploymentSet.description}</p>
        )}
      </div>

      <Separator />

      {/* Tags */}
      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
          <Tag className="h-4 w-4" aria-hidden="true" />
          Tags
        </h3>
        {deploymentSet.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1.5" role="list" aria-label="Tags">
            {[...deploymentSet.tags].sort((a, b) => a.localeCompare(b)).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs" role="listitem">
                {tag}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No tags</p>
        )}
      </div>

      <Separator />

      {/* Member count */}
      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
          <Hash className="h-4 w-4" aria-hidden="true" />
          Members
        </h3>
        <div className="space-y-1.5 text-sm text-muted-foreground">
          <div className="flex items-center justify-between">
            <span>Direct members</span>
            <span className="tabular-nums font-medium text-foreground">
              {deploymentSet.member_count}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Resolved artifacts</span>
            {isResolving ? (
              <Skeleton className="h-4 w-8" aria-label="Loading resolved count" />
            ) : (
              <span className="tabular-nums font-medium text-foreground">
                {resolution?.total_count ?? '—'}
              </span>
            )}
          </div>
        </div>
      </div>

      <Separator />

      {/* Timestamps */}
      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
          <Calendar className="h-4 w-4" aria-hidden="true" />
          Timestamps
        </h3>
        <div className="space-y-1.5 text-sm text-muted-foreground">
          <div className="flex items-center justify-between">
            <span>Created</span>
            <time dateTime={deploymentSet.created_at} className="tabular-nums">
              {formatDate(deploymentSet.created_at)}
            </time>
          </div>
          <div className="flex items-center justify-between">
            <span>Updated</span>
            <time dateTime={deploymentSet.updated_at} className="tabular-nums">
              {formatDate(deploymentSet.updated_at)}
            </time>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Members tab
// ============================================================================

/**
 * GroupMemberPopover
 *
 * Displays a simple info popover for group-type members, showing the group ID
 * since there is no dedicated group detail modal.
 */
function GroupMemberPopover({
  member,
  children,
}: {
  member: DeploymentSetMember;
  children: React.ReactNode;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="w-72 p-4" side="top" align="center">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <h4 className="text-sm font-semibold">Group Member</h4>
          </div>
          <Separator />
          <div className="space-y-1 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Group ID</span>
              <span className="font-mono text-xs break-all text-right">
                {member.group_id ?? member.id}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Position</span>
              <span className="tabular-nums">{member.position ?? '—'}</span>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

/**
 * DeploymentSetMembersTab
 *
 * Renders the Members tab content for a deployment set. Fetches members via
 * useDeploymentSetMembers and resolves artifact data for artifact-type members
 * by building a UUID → Artifact map from useArtifacts.
 *
 * Click behaviour:
 *   - artifact member → opens ArtifactDetailsModal
 *   - set member → opens a nested DeploymentSetDetailsModal
 *   - group member → shows a GroupMemberPopover with group info
 */
function DeploymentSetMembersTab({ setId }: { setId: string }) {
  // Members list for this deployment set
  const {
    data: members,
    isLoading: isMembersLoading,
  } = useDeploymentSetMembers(setId);

  // Fetch all artifacts to build a UUID lookup map for artifact-type members.
  // useArtifacts() is already cached at 5min stale time — no extra cost when
  // the collection page has already loaded this data.
  const { data: artifactsResponse, isLoading: isArtifactsLoading } = useArtifacts();

  // State for the artifact details modal (artifact-type member clicks)
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [artifactModalOpen, setArtifactModalOpen] = useState(false);

  // State for the nested deployment set modal (set-type member clicks)
  const [nestedSetId, setNestedSetId] = useState<string | null>(null);
  const [nestedSetModalOpen, setNestedSetModalOpen] = useState(false);

  // Build uuid → Artifact map for O(1) lookups
  const artifactByUuid = useMemo<Record<string, Artifact>>(() => {
    const artifacts = artifactsResponse?.artifacts ?? [];
    return Object.fromEntries(artifacts.map((a) => [a.uuid, a]));
  }, [artifactsResponse]);

  const isLoading = isMembersLoading || isArtifactsLoading;

  // Sort members by position ascending (null positions go last)
  const sortedMembers = useMemo(() => {
    if (!members) return [];
    return [...members].sort((a, b) => {
      if (a.position === null && b.position === null) return 0;
      if (a.position === null) return 1;
      if (b.position === null) return -1;
      return a.position - b.position;
    });
  }, [members]);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        aria-busy="true"
        aria-label="Loading members"
      >
        {[1, 2, 3].map((i) => (
          <DeploymentSetMemberCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────────
  if (sortedMembers.length === 0) {
    return (
      <div
        className="flex flex-col items-center gap-3 rounded-md border border-dashed border-muted-foreground/30 px-4 py-12 text-center"
        role="status"
        aria-label="No members"
      >
        <Users className="h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
        <p className="text-sm font-medium text-muted-foreground">No members yet</p>
        <p className="text-xs text-muted-foreground/70">
          Add artifacts, groups, or nested sets to this deployment set.
        </p>
      </div>
    );
  }

  // ── Member grid ────────────────────────────────────────────────────────────
  return (
    <>
      <div
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        role="list"
        aria-label="Deployment set members"
      >
        {sortedMembers.map((member, index) => {
          const position = member.position ?? index + 1;
          const resolvedArtifact =
            member.member_type === 'artifact' && member.artifact_uuid
              ? artifactByUuid[member.artifact_uuid]
              : undefined;

          // ── Artifact member ──────────────────────────────────────────────
          if (member.member_type === 'artifact') {
            return (
              <div key={member.id} role="listitem">
                <DeploymentSetMemberCard
                  member={member}
                  resolvedArtifact={resolvedArtifact}
                  position={position}
                  onClick={
                    resolvedArtifact
                      ? () => {
                          setSelectedArtifact(resolvedArtifact);
                          setArtifactModalOpen(true);
                        }
                      : undefined
                  }
                />
              </div>
            );
          }

          // ── Set member ───────────────────────────────────────────────────
          if (member.member_type === 'set') {
            return (
              <div key={member.id} role="listitem">
                <DeploymentSetMemberCard
                  member={member}
                  position={position}
                  onClick={() => {
                    if (member.nested_set_id) {
                      setNestedSetId(member.nested_set_id);
                      setNestedSetModalOpen(true);
                    }
                  }}
                />
              </div>
            );
          }

          // ── Group member ─────────────────────────────────────────────────
          return (
            <div key={member.id} role="listitem">
              <GroupMemberPopover member={member}>
                <span className="block w-full">
                  <DeploymentSetMemberCard
                    member={member}
                    position={position}
                    onClick={() => {
                      /* handled by popover trigger */
                    }}
                  />
                </span>
              </GroupMemberPopover>
            </div>
          );
        })}
      </div>

      {/* Artifact details modal (artifact-type member navigation) */}
      <ArtifactDetailsModal
        artifact={selectedArtifact}
        open={artifactModalOpen}
        onClose={() => {
          setArtifactModalOpen(false);
          setSelectedArtifact(null);
        }}
      />

      {/* Nested deployment set modal (set-type member navigation) */}
      <DeploymentSetDetailsModal
        setId={nestedSetId}
        open={nestedSetModalOpen}
        onOpenChange={(open) => {
          setNestedSetModalOpen(open);
          if (!open) setNestedSetId(null);
        }}
      />
    </>
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

            {/* Overview tab */}
            <TabContentWrapper value="overview">
              <DeploymentSetOverviewTab deploymentSet={deploymentSet} />
            </TabContentWrapper>

            {/* Members tab */}
            <TabContentWrapper value="members">
              <DeploymentSetMembersTab setId={deploymentSet.id} />
            </TabContentWrapper>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
