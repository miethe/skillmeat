'use client';

/**
 * ConsolidationClusterDetail
 *
 * Full detail panel for a selected consolidation cluster.
 *
 * For a cluster with two members, renders:
 *   - Side-by-side artifact metadata comparison
 *   - DiffViewer for content diff (primary vs secondary)
 *   - Action bar: Merge / Replace / Skip / Close
 *   - Confirmation dialogs for destructive actions (Merge, Replace)
 *
 * Skip marks the pair ignored via useIgnorePair and removes it from the list.
 * Merge/Replace call placeholder handlers (TODO: wire to SA-P5-009 API).
 */

import { useState } from 'react';
import {
  Package,
  Terminal,
  Bot,
  Server,
  Webhook,
  Blocks,
  Layers,
  X,
  GitMerge,
  Replace,
  SkipForward,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { DiffViewer } from '@/components/entity/diff-viewer';
import { useIgnorePair, useToast } from '@/hooks';
import type { ConsolidationCluster, ConsolidationClusterMember } from '@/types/similarity';
import type { FileDiff } from '@/sdk/models/FileDiff';

// ============================================================================
// Types
// ============================================================================

interface ConsolidationClusterDetailProps {
  cluster: ConsolidationCluster;
  onClose: () => void;
}

type ConfirmAction = 'merge' | 'replace' | null;

// ============================================================================
// Constants
// ============================================================================

const artifactTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  skill: Package,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  hook: Webhook,
  composite: Blocks,
};

const artifactTypeColors: Record<string, string> = {
  skill: 'bg-blue-500/10 text-blue-700 border-blue-500/20 dark:text-blue-400',
  command: 'bg-purple-500/10 text-purple-700 border-purple-500/20 dark:text-purple-400',
  agent: 'bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400',
  mcp: 'bg-orange-500/10 text-orange-700 border-orange-500/20 dark:text-orange-400',
  hook: 'bg-pink-500/10 text-pink-700 border-pink-500/20 dark:text-pink-400',
  composite: 'bg-indigo-500/10 text-indigo-700 border-indigo-500/20 dark:text-indigo-400',
};

const artifactTypeLabels: Record<string, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP Server',
  hook: 'Hook',
  composite: 'Plugin',
};

// ============================================================================
// Helpers
// ============================================================================

function getArtifactTypeLabel(type: string): string {
  return artifactTypeLabels[type] ?? type;
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

// ============================================================================
// Sub-components
// ============================================================================

interface ArtifactMemberCardProps {
  member: ConsolidationClusterMember;
  label: 'Primary' | 'Secondary';
}

function ArtifactMemberCard({ member, label }: ArtifactMemberCardProps) {
  const Icon = artifactTypeIcons[member.artifact_type] ?? Layers;
  const colorClass =
    artifactTypeColors[member.artifact_type] ??
    'bg-gray-500/10 text-gray-700 border-gray-500/20 dark:text-gray-400';
  const typeLabel = getArtifactTypeLabel(member.artifact_type);
  const isPrimary = label === 'Primary';

  return (
    <div
      className={`flex flex-col gap-2 rounded-lg border p-4 ${
        isPrimary
          ? 'border-primary/30 bg-primary/5'
          : 'border-muted bg-muted/20'
      }`}
      role="article"
      aria-label={`${label} artifact: ${member.name}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="truncate text-sm font-semibold leading-tight" title={member.name}>
            {member.name}
          </span>
        </div>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${
            isPrimary
              ? 'border-primary/40 bg-primary/10 text-primary'
              : 'border-muted-foreground/30 bg-muted text-muted-foreground'
          }`}
          aria-label={`Role: ${label}`}
        >
          {label}
        </span>
      </div>

      <Badge
        variant="outline"
        className={`w-fit inline-flex items-center gap-1.5 text-xs ${colorClass}`}
        aria-label={`Artifact type: ${typeLabel}`}
      >
        <Icon className="h-3 w-3" aria-hidden="true" />
        {typeLabel}
      </Badge>

      {member.source && (
        <p
          className="truncate text-xs text-muted-foreground font-mono"
          title={member.source}
          aria-label={`Source: ${member.source}`}
        >
          {member.source}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Confirmation dialog
// ============================================================================

interface ConfirmActionDialogProps {
  action: ConfirmAction;
  primaryName: string;
  secondaryName: string;
  isExecuting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmActionDialog({
  action,
  primaryName,
  secondaryName,
  isExecuting,
  onConfirm,
  onCancel,
}: ConfirmActionDialogProps) {
  const isMerge = action === 'merge';

  const title = isMerge
    ? 'Merge artifacts?'
    : 'Replace with primary?';

  const description = isMerge
    ? `Keep "${primaryName}" and apply changes from "${secondaryName}" into it. The secondary artifact will be removed.`
    : `Keep "${primaryName}" and permanently discard "${secondaryName}". This action cannot be undone.`;

  return (
    <AlertDialog open={action !== null} onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle
              className="h-5 w-5 text-destructive"
              aria-hidden="true"
            />
            {title}
          </AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel} disabled={isExecuting}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isExecuting}
            className={
              isMerge
                ? 'bg-primary hover:bg-primary/90'
                : 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
            }
            aria-label={isExecuting ? `${isMerge ? 'Merging' : 'Replacing'} in progress` : undefined}
          >
            {isExecuting ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                {isMerge ? 'Merging…' : 'Replacing…'}
              </span>
            ) : (
              isMerge ? 'Merge' : 'Replace'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// ============================================================================
// Main component
// ============================================================================

export function ConsolidationClusterDetail({ cluster, onClose }: ConsolidationClusterDetailProps) {
  const { toast } = useToast();

  // Dialog and action state
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [isExecutingAction, setIsExecutingAction] = useState(false);

  // Ignore pair mutation (used by Skip action)
  const ignorePairMutation = useIgnorePair();

  // Resolve primary/secondary members (use first two members)
  const primaryMember: ConsolidationClusterMember | undefined = cluster.members[0];
  const secondaryMember: ConsolidationClusterMember | undefined = cluster.members[1];

  // Resolve the pairwise record for the primary/secondary pair (if applicable)
  const activePair =
    primaryMember && secondaryMember
      ? cluster.pairs.find(
          (p) =>
            (p.artifact_id_a === primaryMember.artifact_id &&
              p.artifact_id_b === secondaryMember.artifact_id) ||
            (p.artifact_id_a === secondaryMember.artifact_id &&
              p.artifact_id_b === primaryMember.artifact_id)
        )
      : undefined;

  // Pairwise score display
  const pairScore = activePair?.score ?? cluster.max_score;

  // ---- Action handlers ----

  /** Skip: mark the pair as ignored and close the detail panel. */
  async function handleSkip() {
    if (!activePair) {
      onClose();
      return;
    }

    try {
      await ignorePairMutation.mutateAsync({ pairId: activePair.pair_id });
      toast({
        title: 'Pair ignored',
        description: `The pair "${primaryMember?.name}" / "${secondaryMember?.name}" has been marked as ignored.`,
      });
      onClose();
    } catch {
      toast({
        title: 'Failed to ignore pair',
        description: 'Could not mark this pair as ignored. Please try again.',
        variant: 'destructive',
      });
    }
  }

  /** Confirm button in the dialog — executes merge or replace. */
  async function handleConfirmedAction() {
    if (!confirmAction) return;

    setIsExecutingAction(true);

    try {
      // TODO (SA-P5-009): Wire to real merge/replace API endpoints once implemented.
      // For merge:   POST /api/v1/artifacts/consolidation/pairs/{pairId}/merge
      // For replace: POST /api/v1/artifacts/consolidation/pairs/{pairId}/replace
      await new Promise<void>((resolve) => setTimeout(resolve, 500)); // placeholder

      const actionLabel = confirmAction === 'merge' ? 'Merge complete' : 'Replace complete';
      const actionDesc =
        confirmAction === 'merge'
          ? `"${secondaryMember?.name}" was merged into "${primaryMember?.name}".`
          : `"${secondaryMember?.name}" was replaced by "${primaryMember?.name}".`;

      toast({ title: actionLabel, description: actionDesc });
      setConfirmAction(null);
      onClose();
    } catch {
      toast({
        title: `${confirmAction === 'merge' ? 'Merge' : 'Replace'} failed`,
        description: 'The operation could not be completed. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsExecutingAction(false);
    }
  }

  // ---- Diff data ----
  // No real diff data available at this stage (SA-P5-009 will provide it).
  // Render DiffViewer with an empty file list to show the "no changes" state.
  const diffFiles: FileDiff[] = [];

  // ---- Guard: cluster must have at least two members ----
  if (!primaryMember || !secondaryMember) {
    return (
      <div
        className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground"
        role="region"
        aria-label="Cluster detail"
      >
        <p>This cluster does not have enough members to compare.</p>
        <Button
          variant="ghost"
          size="sm"
          className="mt-3"
          onClick={onClose}
          aria-label="Close cluster detail"
        >
          Close
        </Button>
      </div>
    );
  }

  return (
    <section
      className="rounded-lg border bg-background shadow-sm"
      aria-label={`Detail for cluster ${cluster.cluster_id}`}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center justify-between border-b px-5 py-3">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold leading-tight">Artifact Comparison</h3>
          <Badge
            variant="secondary"
            className="text-xs tabular-nums"
            aria-label={`Similarity score: ${formatScore(pairScore)}`}
          >
            {formatScore(pairScore)} similar
          </Badge>
          {cluster.members.length > 2 && (
            <span className="text-xs text-muted-foreground">
              +{cluster.members.length - 2} more in cluster
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={onClose}
          aria-label="Close cluster detail"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Side-by-side member cards                                           */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 gap-4 p-5" aria-label="Artifact comparison">
        <ArtifactMemberCard member={primaryMember} label="Primary" />
        <ArtifactMemberCard member={secondaryMember} label="Secondary" />
      </div>

      <Separator />

      {/* ------------------------------------------------------------------ */}
      {/* Diff viewer                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="px-5 py-4"
        aria-label="Content diff between primary and secondary artifacts"
      >
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Content Diff
        </h4>
        <div className="h-72 overflow-hidden rounded-md border">
          <DiffViewer
            files={diffFiles}
            leftLabel={primaryMember.name}
            rightLabel={secondaryMember.name}
          />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Full diff will be available once the merge API is implemented (SA-P5-009).
        </p>
      </div>

      <Separator />

      {/* ------------------------------------------------------------------ */}
      {/* Action bar                                                           */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
        role="group"
        aria-label="Cluster actions"
      >
        <div className="flex flex-wrap items-center gap-2">
          {/* Merge */}
          <Button
            variant="default"
            size="sm"
            onClick={() => setConfirmAction('merge')}
            disabled={ignorePairMutation.isPending || isExecutingAction}
            aria-label={`Merge: keep "${primaryMember.name}", apply changes from "${secondaryMember.name}"`}
            title="Keep primary artifact and apply changes from the secondary"
          >
            <GitMerge className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Merge
          </Button>

          {/* Replace */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setConfirmAction('replace')}
            disabled={ignorePairMutation.isPending || isExecutingAction}
            aria-label={`Replace: keep "${primaryMember.name}", discard "${secondaryMember.name}"`}
            title="Keep primary artifact and permanently discard the secondary"
            className="text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/30"
          >
            <Replace className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Replace
          </Button>

          {/* Skip */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSkip}
            disabled={ignorePairMutation.isPending || isExecutingAction}
            aria-label="Skip: mark this pair as ignored and remove from list"
            title="Mark this pair as ignored and remove it from the consolidation list"
          >
            {ignorePairMutation.isPending ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <SkipForward className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            )}
            Skip
          </Button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          disabled={ignorePairMutation.isPending || isExecutingAction}
          aria-label="Close detail panel"
        >
          Close
        </Button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Confirmation dialogs                                                 */}
      {/* ------------------------------------------------------------------ */}
      <ConfirmActionDialog
        action={confirmAction}
        primaryName={primaryMember.name}
        secondaryName={secondaryMember.name}
        isExecuting={isExecutingAction}
        onConfirm={handleConfirmedAction}
        onCancel={() => {
          if (!isExecutingAction) setConfirmAction(null);
        }}
      />
    </section>
  );
}
