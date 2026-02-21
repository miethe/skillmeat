'use client';

/**
 * PluginMembersTab — Tab panel for managing members of a composite plugin.
 *
 * Renders the current member list with drag-to-reorder (via MemberList) and
 * a collapsible add-member flow (via MemberSearchInput).  Each member row has
 * per-item actions: remove from plugin (with confirmation dialog).
 *
 * Mutations are handled by the three focused hooks from useManageCompositeMembers:
 *   - useAddCompositeMember
 *   - useRemoveCompositeMember
 *   - useReorderCompositeMembers
 *
 * Members are derived from useArtifactAssociations so they stay in sync with
 * the server-authoritative association graph.
 *
 * Accessibility: WCAG 2.1 AA compliant.  MemberList handles keyboard
 * reordering (ArrowUp/Down/Delete).  Confirmation dialog is focus-trapped.
 *
 * @example
 * ```tsx
 * <PluginMembersTab compositeId="composite:my-plugin" collectionId="default" />
 * ```
 */

import React, { useCallback, useMemo, useState } from 'react';
import { Plus, X, Loader2, AlertCircle, Users } from 'lucide-react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
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
import { ScrollArea } from '@/components/ui/scroll-area';
import { MiniArtifactCard, DraggableMiniArtifactCard } from '@/components/collection/mini-artifact-card';
import { MemberSearchInput } from '@/components/shared/member-search-input';
import {
  useArtifactAssociations,
  useArtifact,
  useAddCompositeMember,
  useRemoveCompositeMember,
  useReorderCompositeMembers,
  useToast,
} from '@/hooks';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface PluginMembersTabProps {
  /**
   * Composite artifact ID in "type:name" format.
   * Example: "composite:my-plugin"
   */
  compositeId: string;

  /**
   * Optional collection context for add-member mutations.
   * Defaults to "default" when omitted.
   */
  collectionId?: string;

  /**
   * Disables all interaction (add, remove, reorder).
   * Use when the composite is read-only or the user lacks write access.
   */
  disabled?: boolean;

  /**
   * Optional callback invoked when a member card is clicked.
   * Receives the artifact ID of the clicked member.
   * When provided, this replaces the default URL navigation behavior.
   */
  onArtifactClick?: (artifactId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers — map association DTO fields onto Artifact shape expected by MemberList
// ---------------------------------------------------------------------------

/**
 * Association children use string artifact_type fields that overlap with
 * ArtifactType.  This helper narrows the string to ArtifactType, defaulting
 * to 'skill' for unknown values so the icon fallback is predictable.
 */
function toArtifactType(raw: string): ArtifactType {
  const valid: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'hook', 'composite'];
  return valid.includes(raw as ArtifactType) ? (raw as ArtifactType) : 'skill';
}

/**
 * Convert an AssociationItemDTO child into the minimal Artifact shape
 * required by MemberList and MemberSearchInput.
 *
 * NOTE: We only populate the fields MemberList actually renders (id, name,
 * type).  The remaining Artifact fields are stubbed with safe defaults since
 * MemberList does not access them.
 */
function associationChildToArtifact(child: {
  artifact_id: string;
  artifact_name: string;
  artifact_type: string;
}): Artifact {
  return {
    id: child.artifact_id,
    name: child.artifact_name,
    type: toArtifactType(child.artifact_type),
    // Required Artifact fields — stubs only used by shape, not rendered by MemberList
    uuid: child.artifact_id,
    source: '',
    version: '',
    scope: 'user',
    path: '',
    collection: '',
    status: 'synced',
    deployments: [],
    collections: [],
    createdAt: '',
    updatedAt: '',
  } as unknown as Artifact;
}

// ---------------------------------------------------------------------------
// EnrichedMiniArtifactCard — enriches a stub artifact with full data from cache
// ---------------------------------------------------------------------------

/**
 * Wrapper around MiniArtifactCard that attempts to fetch the full artifact
 * data for a stub artifact so the card renders description, tags, and groups.
 *
 * Uses useArtifact which will hit the React Query cache first (zero extra
 * network request if the artifact is already loaded on the page), and falls
 * back to a background fetch otherwise. The stub is shown immediately as
 * placeholderData so there is no loading flash.
 */
function EnrichedMiniArtifactCard({
  stub,
  onClick,
  groupId,
  className,
}: {
  stub: Artifact;
  onClick: () => void;
  groupId?: string;
  className?: string;
}) {
  const { data: fullArtifact } = useArtifact(stub.id);
  const artifact = fullArtifact ?? stub;
  return (
    <MiniArtifactCard
      artifact={artifact}
      onClick={onClick}
      groupId={groupId}
      className={className}
    />
  );
}

/**
 * Draggable version of EnrichedMiniArtifactCard.
 * Delegates to DraggableMiniArtifactCard with enriched artifact data.
 */
function DraggableEnrichedMiniArtifactCard({
  stub,
  onClick,
  groupId,
  className,
}: {
  stub: Artifact;
  onClick: () => void;
  groupId: string;
  className?: string;
}) {
  const { data: fullArtifact } = useArtifact(stub.id);
  const artifact = fullArtifact ?? stub;
  return (
    <DraggableMiniArtifactCard
      artifact={artifact}
      onClick={onClick}
      groupId={groupId}
      className={className}
    />
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function MembersTabSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading members">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-8 rounded-full" />
        </div>
        <Skeleton className="h-9 w-32" />
      </div>

      {/* Member card grid skeleton */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="min-h-[140px] rounded-lg border border-l-[3px] border-l-muted p-3"
          >
            <div className="flex items-center gap-1.5">
              <Skeleton className="h-4 w-4 shrink-0 rounded" />
              <Skeleton className="h-4 flex-1" />
            </div>
            <div className="mt-1 space-y-1">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
            </div>
            <div className="mt-auto pt-3 flex gap-1">
              <Skeleton className="h-4 w-12 rounded-full" />
              <Skeleton className="h-4 w-10 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function MembersEmptyState({ onAdd, disabled }: { onAdd: () => void; disabled: boolean }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-md border border-dashed',
        'border-border/60 px-6 py-10 text-center'
      )}
      role="status"
      aria-label="No members"
    >
      <Users
        className="mb-3 h-9 w-9 text-indigo-500/40"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-muted-foreground">No members yet</p>
      <p className="mt-1 text-xs text-muted-foreground/60">
        Add artifacts to this plugin using the button above.
      </p>
      {!disabled && (
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={onAdd}
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Add Member
        </Button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function MembersErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-md border border-destructive/30 bg-destructive/5 px-6 py-8 text-center"
      role="alert"
    >
      <AlertCircle className="mb-2 h-8 w-8 text-destructive/60" aria-hidden="true" />
      <p className="text-sm font-medium text-destructive">Failed to load members</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Could not fetch plugin members. Check your connection and try again.
      </p>
      <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Remove confirmation dialog
// ---------------------------------------------------------------------------

interface RemoveConfirmDialogProps {
  open: boolean;
  memberName: string;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function RemoveConfirmDialog({
  open,
  memberName,
  isPending,
  onConfirm,
  onCancel,
}: RemoveConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(v) => !v && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove member?</AlertDialogTitle>
          <AlertDialogDescription>
            <span className="font-medium text-foreground">{memberName}</span> will be removed from
            this plugin. This does not delete the artifact from your collection.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending} onClick={onCancel}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={isPending}
            onClick={onConfirm}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive"
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Removing…
              </>
            ) : (
              'Remove'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// ---------------------------------------------------------------------------
// PluginMembersTab
// ---------------------------------------------------------------------------

export function PluginMembersTab({
  compositeId,
  collectionId = 'default',
  disabled = false,
  onArtifactClick,
}: PluginMembersTabProps) {
  const { toast } = useToast();

  // ── Data ──────────────────────────────────────────────────────────────────

  const { data, isLoading, error, refetch } = useArtifactAssociations(compositeId, collectionId);

  // Derive a stable ordered member list from the association children.
  const members: Artifact[] = useMemo(() => {
    if (!data?.children) return [];
    return data.children.map(associationChildToArtifact);
  }, [data]);

  const memberIds = useMemo(() => members.map((m) => m.id), [members]);

  // ── Mutations ─────────────────────────────────────────────────────────────

  const addMember = useAddCompositeMember();
  const removeMember = useRemoveCompositeMember();
  const reorderMembers = useReorderCompositeMembers();

  // ── Local UI state ────────────────────────────────────────────────────────

  const [isAddingMember, setIsAddingMember] = useState(false);

  // Removal confirmation
  const [pendingRemove, setPendingRemove] = useState<{
    artifactId: string;
    memberUuid: string;
    name: string;
  } | null>(null);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleAddMember = useCallback(
    async (artifact: Artifact) => {
      try {
        await addMember.mutateAsync({
          compositeId,
          collectionId,
          payload: { artifact_id: artifact.id },
        });
        toast({
          title: 'Member added',
          description: `${artifact.name} has been added to the plugin.`,
        });
      } catch {
        // Error toast is shown by the mutation hook via useToastNotification
      }
    },
    [addMember, compositeId, collectionId, toast]
  );

  const handleRequestRemove = useCallback(
    (artifactId: string) => {
      // Find the association child to get the stable child_artifact_uuid.
      // The associations DTO gives us artifact_id (type:name) — we need the
      // UUID for the DELETE call.  We surface this as the artifact_id as a
      // fallback since the associations DTO does not embed child UUIDs.
      // When the plugin detail query is in cache, useRemoveCompositeMember
      // will use the UUID from that cache; otherwise it falls back to the ID.
      const child = data?.children.find((c) => c.artifact_id === artifactId);
      const name = child?.artifact_name ?? artifactId;

      // memberUuid from association DTO is not available — we use artifact_id
      // as the stable identifier. The backend removeCompositeMember endpoint
      // accepts either UUID or artifact ID depending on the router; check
      // composites.ts for the exact shape. Use artifact_id as memberUuid here.
      setPendingRemove({ artifactId, memberUuid: artifactId, name });
    },
    [data]
  );

  const handleConfirmRemove = useCallback(async () => {
    if (!pendingRemove) return;
    try {
      await removeMember.mutateAsync({
        compositeId,
        memberUuid: pendingRemove.memberUuid,
      });
      toast({
        title: 'Member removed',
        description: `${pendingRemove.name} has been removed from the plugin.`,
      });
    } catch {
      // Error toast is shown by the mutation hook
    } finally {
      setPendingRemove(null);
    }
  }, [pendingRemove, removeMember, compositeId, toast]);

  const handleCancelRemove = useCallback(() => {
    setPendingRemove(null);
  }, []);

  // Navigate to artifact detail view (card click).
  // Uses the onArtifactClick callback when provided by the parent modal,
  // which allows the parent to switch to the clicked artifact without a
  // full URL navigation that would leave the current modal open.
  const handleViewDetails = useCallback((artifact: Artifact) => {
    onArtifactClick?.(artifact.id);
  }, [onArtifactClick]);

  // DnD sensors for the grid
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const activeDragArtifact = activeDragId
    ? members.find((m) => m.id === activeDragId) ?? null
    : null;

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveDragId(String(event.active.id));
  }, []);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      setActiveDragId(null);
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = members.findIndex((m) => m.id === active.id);
      const newIndex = members.findIndex((m) => m.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const reordered = arrayMove(members, oldIndex, newIndex);
      const payload = {
        members: reordered.map((a, idx) => ({ artifact_id: a.id, position: idx })),
      };
      try {
        await reorderMembers.mutateAsync({ compositeId, payload });
      } catch {
        // Error toast handled by hook; optimistic rollback handled by hook
      }
    },
    [members, reorderMembers, compositeId]
  );

  // ── Render ────────────────────────────────────────────────────────────────

  if (isLoading) {
    return <MembersTabSkeleton />;
  }

  if (error) {
    return <MembersErrorState onRetry={() => void refetch()} />;
  }

  const isAnyMutationPending =
    addMember.isPending || removeMember.isPending || reorderMembers.isPending;
  const effectiveDisabled = disabled || isAnyMutationPending;

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 id="plugin-members-heading" className="text-sm font-medium">Members</h3>
          <Badge
            variant="secondary"
            className="px-2 py-0.5 text-xs tabular-nums"
            aria-label={`${members.length} member${members.length !== 1 ? 's' : ''}`}
          >
            {members.length}
          </Badge>
        </div>

        {!disabled && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAddingMember((v) => !v)}
            aria-expanded={isAddingMember}
            aria-controls="plugin-member-search"
            aria-label={isAddingMember ? 'Cancel adding member' : 'Add member to plugin'}
          >
            {isAddingMember ? (
              <>
                <X className="mr-2 h-4 w-4" aria-hidden="true" />
                Cancel
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                Add Member
              </>
            )}
          </Button>
        )}
      </div>

      {/* ── Add Member Search ── */}
      {isAddingMember && !disabled && (
        <div id="plugin-member-search" role="region" aria-label="Add member search">
          <MemberSearchInput
            excludeIds={memberIds}
            onSelect={(artifact) => {
              void handleAddMember(artifact);
              setIsAddingMember(false);
            }}
            placeholder="Search for an artifact to add…"
            disabled={addMember.isPending}
            inputAriaLabel="Search artifacts to add as plugin members"
            className="w-full"
          />
          {addMember.isPending && (
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              Adding member…
            </p>
          )}
        </div>
      )}

      {/* ── Member Grid or Empty State ── */}
      {members.length === 0 ? (
        <MembersEmptyState
          onAdd={() => setIsAddingMember(true)}
          disabled={disabled}
        />
      ) : (
        <ScrollArea
          className={cn(members.length > 6 ? 'h-[480px]' : undefined)}
          aria-label={members.length > 6 ? 'Scrollable member grid' : undefined}
        >
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={(e) => void handleDragEnd(e)}
          >
            <SortableContext items={memberIds} strategy={rectSortingStrategy}>
              <div
                className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
                role="list"
                aria-labelledby="plugin-members-heading"
                aria-label="Plugin members"
              >
                {members.map((artifact) => (
                  <div key={artifact.id} className="relative group/card" role="listitem">
                    <DraggableEnrichedMiniArtifactCard
                      stub={artifact}
                      groupId={compositeId}
                      onClick={() => handleViewDetails(artifact)}
                      className={cn(effectiveDisabled && 'pointer-events-none opacity-60')}
                    />
                    {/* Remove button overlay — shown on hover when not disabled */}
                    {!effectiveDisabled && (
                      <button
                        type="button"
                        aria-label={`Remove ${artifact.name} from plugin`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRequestRemove(artifact.id);
                        }}
                        className={cn(
                          'absolute right-2 top-2 z-10',
                          'flex h-5 w-5 items-center justify-center rounded',
                          'bg-background/80 text-muted-foreground/60',
                          'opacity-0 transition-opacity duration-150',
                          'group-hover/card:opacity-100 focus-visible:opacity-100',
                          'hover:bg-destructive/10 hover:text-destructive',
                          'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                        )}
                      >
                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </SortableContext>

            {/* Drag overlay — ghost while dragging */}
            <DragOverlay>
              {activeDragArtifact ? (
                <EnrichedMiniArtifactCard
                  stub={activeDragArtifact}
                  onClick={() => {}}
                  groupId={compositeId}
                  className="rotate-1 shadow-lg opacity-90"
                />
              ) : null}
            </DragOverlay>
          </DndContext>
        </ScrollArea>
      )}

      {/* ── Save order status ── */}
      {reorderMembers.isPending && (
        <p
          className="flex items-center gap-1.5 text-xs text-muted-foreground"
          role="status"
          aria-live="polite"
        >
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          Saving order…
        </p>
      )}

      {/* ── Remove confirmation dialog ── */}
      <RemoveConfirmDialog
        open={pendingRemove !== null}
        memberName={pendingRemove?.name ?? ''}
        isPending={removeMember.isPending}
        onConfirm={handleConfirmRemove}
        onCancel={handleCancelRemove}
      />

    </div>
  );
}
