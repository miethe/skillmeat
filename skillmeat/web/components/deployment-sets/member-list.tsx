'use client';

import { useState } from 'react';
import { Trash2, Box, Users, Layers3 } from 'lucide-react';
import type { DeploymentSetMember, DeploymentSetMemberType } from '@/types/deployment-sets';
import { useRemoveMember, useToast } from '@/hooks';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

// ---------------------------------------------------------------------------
// Type badge configuration
// ---------------------------------------------------------------------------

interface MemberTypeMeta {
  label: string;
  icon: React.ElementType;
  badgeClass: string;
}

const MEMBER_TYPE_META: Record<DeploymentSetMemberType, MemberTypeMeta> = {
  artifact: {
    label: 'Artifact',
    icon: Box,
    badgeClass:
      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800',
  },
  group: {
    label: 'Group',
    icon: Users,
    badgeClass:
      'bg-green-100 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800',
  },
  set: {
    label: 'Set',
    icon: Layers3,
    badgeClass:
      'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-800',
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive a human-readable display name for a member row. */
function getMemberDisplayName(member: DeploymentSetMember): string {
  if (member.member_type === 'artifact' && member.artifact_uuid) {
    return member.artifact_uuid;
  }
  if (member.member_type === 'group' && member.group_id) {
    return `Group ${member.group_id}`;
  }
  if (member.member_type === 'set' && member.nested_set_id) {
    return `Set ${member.nested_set_id}`;
  }
  return member.id;
}

// ---------------------------------------------------------------------------
// Individual member row
// ---------------------------------------------------------------------------

interface MemberRowProps {
  member: DeploymentSetMember;
  setId: string;
  position: number;
}

function MemberRow({ member, setId, position }: MemberRowProps) {
  const [confirming, setConfirming] = useState(false);
  const removeMember = useRemoveMember();
  const { toast } = useToast();

  const meta = MEMBER_TYPE_META[member.member_type];
  const Icon = meta.icon;
  const displayName = getMemberDisplayName(member);

  const handleRemoveClick = () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    // Confirmed — fire the mutation
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

  const handleCancelConfirm = () => setConfirming(false);

  return (
    <li
      role="listitem"
      className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3 text-sm transition-colors hover:bg-accent/40"
    >
      {/* Position badge */}
      <span
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground"
        aria-label={`Position ${position}`}
      >
        {position}
      </span>

      {/* Type icon */}
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />

      {/* Type badge */}
      <Badge
        variant="outline"
        className={`shrink-0 text-xs font-medium ${meta.badgeClass}`}
      >
        {meta.label}
      </Badge>

      {/* Name / identifier */}
      <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground" title={displayName}>
        {displayName}
      </span>

      {/* Remove / Confirm */}
      {confirming ? (
        <div className="flex shrink-0 items-center gap-1">
          <span className="text-xs text-destructive">Remove?</span>
          <Button
            size="sm"
            variant="destructive"
            className="h-7 px-2 text-xs"
            onClick={handleRemoveClick}
            disabled={removeMember.isPending}
            aria-label="Confirm remove member"
          >
            Yes
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-2 text-xs"
            onClick={handleCancelConfirm}
            disabled={removeMember.isPending}
            aria-label="Cancel remove"
          >
            No
          </Button>
        </div>
      ) : (
        <Button
          size="sm"
          variant="ghost"
          className="h-7 w-7 shrink-0 p-0 text-muted-foreground hover:text-destructive"
          onClick={handleRemoveClick}
          disabled={removeMember.isPending}
          aria-label={`Remove ${meta.label} member ${displayName}`}
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Skeleton rows shown while loading
// ---------------------------------------------------------------------------

function MemberListSkeleton() {
  return (
    <ul role="list" aria-label="Loading members" className="space-y-2">
      {[1, 2, 3].map((i) => (
        <li key={i} className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3">
          <Skeleton className="h-6 w-6 rounded-full" />
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-7 w-7 rounded" />
        </li>
      ))}
    </ul>
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
  /** Called when the user clicks "Add Member" — wired up by DS-012 */
  onAddMember: () => void;
  /** Show skeleton loading state */
  isLoading?: boolean;
}

export function MemberList({ members, setId, onAddMember, isLoading }: MemberListProps) {
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
    <ul role="list" aria-label="Deployment set members" className="space-y-2">
      {sorted.map((member, index) => (
        <MemberRow
          key={member.id}
          member={member}
          setId={setId}
          position={member.position ?? index + 1}
        />
      ))}
    </ul>
  );
}
