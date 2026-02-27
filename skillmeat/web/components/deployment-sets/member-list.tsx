'use client';

import { useState, useMemo } from 'react';
import { Trash2, Layers3 } from 'lucide-react';
import type { DeploymentSetMember } from '@/types/deployment-sets';
import { useRemoveMember, useToast, useArtifacts, useGroup, useDeploymentSet } from '@/hooks';
import { Button } from '@/components/ui/button';
import { MiniArtifactCard } from '@/components/collection/mini-artifact-card';
import { MiniGroupCard, MiniGroupCardSkeleton } from '@/components/deployment-sets/mini-group-card';
import {
  MiniDeploymentSetCard,
  MiniDeploymentSetCardSkeleton,
} from '@/components/deployment-sets/mini-deployment-set-card';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';

// ---------------------------------------------------------------------------
// Remove overlay
// ---------------------------------------------------------------------------

interface RemoveOverlayProps {
  member: DeploymentSetMember;
  setId: string;
  displayName: string;
}

function RemoveOverlay({ member, setId, displayName }: RemoveOverlayProps) {
  const [confirming, setConfirming] = useState(false);
  const removeMember = useRemoveMember();
  const { toast } = useToast();

  const handleRemoveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirming) {
      setConfirming(true);
      return;
    }
    removeMember.mutate(
      { setId, memberId: member.id },
      {
        onError: (err) => {
          toast({
            title: 'Remove failed',
            description: err instanceof Error ? err.message : 'An unexpected error occurred.',
            variant: 'destructive',
          });
          setConfirming(false);
        },
      },
    );
  };

  const handleCancelConfirm = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirming(false);
  };

  if (confirming) {
    return (
      <div
        className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-lg bg-background/85 backdrop-blur-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-xs font-medium text-destructive">Remove member?</p>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="destructive"
            className="h-7 px-3 text-xs"
            onClick={handleRemoveClick}
            disabled={removeMember.isPending}
            aria-label="Confirm remove member"
          >
            Yes
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-3 text-xs"
            onClick={handleCancelConfirm}
            disabled={removeMember.isPending}
            aria-label="Cancel remove"
          >
            No
          </Button>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      className={cn(
        'absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full',
        'bg-background/70 text-muted-foreground opacity-0 shadow-sm transition-all',
        'hover:bg-destructive hover:text-destructive-foreground hover:opacity-100',
        'group-hover:opacity-60 focus-visible:opacity-100',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      )}
      onClick={handleRemoveClick}
      aria-label={`Remove ${displayName}`}
    >
      <Trash2 className="h-3 w-3" aria-hidden="true" />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Card wrappers with remove overlay
// ---------------------------------------------------------------------------

interface ArtifactMemberCardProps {
  member: DeploymentSetMember;
  setId: string;
  position: number;
  artifact: Artifact;
  onClick?: () => void;
}

function ArtifactMemberCard({ member, setId, position, artifact, onClick }: ArtifactMemberCardProps) {
  return (
    <div className="group relative" role="listitem">
      {/* Position badge — absolute top-left over the card */}
      <span
        className="absolute left-1.5 top-1.5 z-10 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-muted/90 px-1.5 text-[10px] font-semibold tabular-nums text-muted-foreground shadow-sm"
        aria-label={`Position ${position}`}
      >
        #{position}
      </span>

      <MiniArtifactCard
        artifact={artifact}
        onClick={onClick ?? (() => {})}
        className="cursor-pointer"
      />

      <RemoveOverlay member={member} setId={setId} displayName={artifact.name} />
    </div>
  );
}

interface GroupMemberCardProps {
  member: DeploymentSetMember;
  setId: string;
  position: number;
  onClick?: () => void;
}

function GroupMemberCard({ member, setId, position, onClick }: GroupMemberCardProps) {
  const { data: group, isLoading } = useGroup(member.group_id ?? undefined);

  if (isLoading) {
    return (
      <div role="listitem">
        <MiniGroupCardSkeleton />
      </div>
    );
  }

  if (!group) {
    // Fallback skeleton-like placeholder when group can't be resolved
    return (
      <div
        role="listitem"
        className="flex min-h-[140px] items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground"
      >
        Group not found
      </div>
    );
  }

  return (
    <div className="group relative" role="listitem">
      <MiniGroupCard
        group={group}
        onClick={onClick}
        position={position}
      />
      <RemoveOverlay member={member} setId={setId} displayName={group.name} />
    </div>
  );
}

interface SetMemberCardProps {
  member: DeploymentSetMember;
  setId: string;
  position: number;
  onClick?: () => void;
}

function SetMemberCard({ member, setId, position, onClick }: SetMemberCardProps) {
  const { data: nestedSet, isLoading } = useDeploymentSet(member.nested_set_id ?? '');

  if (isLoading) {
    return (
      <div role="listitem">
        <MiniDeploymentSetCardSkeleton />
      </div>
    );
  }

  if (!nestedSet) {
    return (
      <div
        role="listitem"
        className="flex min-h-[140px] items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground"
      >
        Set not found
      </div>
    );
  }

  return (
    <div className="group relative" role="listitem">
      <MiniDeploymentSetCard
        set={nestedSet}
        onClick={onClick}
        position={position}
      />
      <RemoveOverlay member={member} setId={setId} displayName={nestedSet.name} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton grid shown while loading
// ---------------------------------------------------------------------------

function MemberListSkeleton() {
  return (
    <div
      className="grid grid-cols-2 gap-3 sm:grid-cols-3"
      role="list"
      aria-label="Loading members"
      aria-busy="true"
    >
      {[1, 2, 3].map((i) => (
        <div key={i} role="listitem">
          <MiniDeploymentSetCardSkeleton />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inner member grid (fetches artifacts itself)
// ---------------------------------------------------------------------------

interface MemberGridProps {
  members: DeploymentSetMember[];
  setId: string;
  onArtifactClick?: (artifactUuid: string) => void;
  onSetClick?: (nestedSetId: string) => void;
  onGroupClick?: (groupId: string) => void;
}

function MemberGrid({ members, setId, onArtifactClick, onSetClick, onGroupClick }: MemberGridProps) {
  // Fetch all artifacts to build a UUID lookup map — already cached by the collection page
  const { data: artifactsResponse } = useArtifacts({ limit: 500 });

  const artifactByUuid = useMemo<Record<string, Artifact>>(() => {
    const artifacts = artifactsResponse?.artifacts ?? [];
    return Object.fromEntries(artifacts.map((a) => [a.uuid, a]));
  }, [artifactsResponse]);

  return (
    <div
      className="grid grid-cols-2 gap-3 sm:grid-cols-3"
      role="list"
      aria-label="Deployment set members"
    >
      {members.map((member, index) => {
        const position = member.position ?? index + 1;

        if (member.member_type === 'artifact') {
          const artifact = member.artifact_uuid ? artifactByUuid[member.artifact_uuid] : undefined;

          if (!artifact) {
            // Still loading or unresolved — show a skeleton placeholder
            return (
              <div key={member.id} role="listitem">
                <MiniDeploymentSetCardSkeleton />
              </div>
            );
          }

          return (
            <ArtifactMemberCard
              key={member.id}
              member={member}
              setId={setId}
              position={position}
              artifact={artifact}
              onClick={
                onArtifactClick && member.artifact_uuid
                  ? () => onArtifactClick(member.artifact_uuid!)
                  : undefined
              }
            />
          );
        }

        if (member.member_type === 'group') {
          return (
            <GroupMemberCard
              key={member.id}
              member={member}
              setId={setId}
              position={position}
              onClick={
                onGroupClick && member.group_id
                  ? () => onGroupClick(member.group_id!)
                  : undefined
              }
            />
          );
        }

        // set
        return (
          <SetMemberCard
            key={member.id}
            member={member}
            setId={setId}
            position={position}
            onClick={
              onSetClick && member.nested_set_id
                ? () => onSetClick(member.nested_set_id!)
                : undefined
            }
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export interface MemberListProps {
  /** Members to display — pass empty array when still loading */
  members: DeploymentSetMember[];
  /** ID of the parent deployment set (needed for remove mutations) */
  setId: string;
  /** Called when the user clicks "Add Member" */
  onAddMember: () => void;
  /** Show skeleton loading state */
  isLoading?: boolean;
  /** Optional click handlers for opening member detail views */
  onArtifactClick?: (artifactUuid: string) => void;
  onSetClick?: (nestedSetId: string) => void;
  onGroupClick?: (groupId: string) => void;
}

export function MemberList({
  members,
  setId,
  onAddMember,
  isLoading,
  onArtifactClick,
  onSetClick,
  onGroupClick,
}: MemberListProps) {
  if (isLoading) {
    return <MemberListSkeleton />;
  }

  if (members.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-lg border border-dashed bg-card px-6 py-10 text-center"
        role="status"
        aria-label="No members"
      >
        <Layers3 className="mb-3 h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
        <p className="text-sm font-medium text-muted-foreground">No members yet.</p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          Add artifacts, groups, or other sets.
        </p>
        <Button
          size="sm"
          variant="outline"
          className="mt-4"
          onClick={onAddMember}
          aria-label="Add first member"
        >
          Add Member
        </Button>
      </div>
    );
  }

  // Sort by position ascending (null positions go last)
  const sorted = [...members].sort((a, b) => {
    if (a.position === null && b.position === null) return 0;
    if (a.position === null) return 1;
    if (b.position === null) return -1;
    return a.position - b.position;
  });

  return (
    <MemberGrid
      members={sorted}
      setId={setId}
      onArtifactClick={onArtifactClick}
      onSetClick={onSetClick}
      onGroupClick={onGroupClick}
    />
  );
}
