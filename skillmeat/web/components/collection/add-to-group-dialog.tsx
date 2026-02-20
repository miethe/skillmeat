'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { Layers, Plus, Loader2, ChevronLeft, FolderOpen, X, Settings } from 'lucide-react';
import { resolveColorHex, ICON_MAP, COLOR_HEX_BY_TOKEN } from '@/lib/group-constants';
import type { GroupIcon } from '@/lib/group-constants';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Input } from '@/components/ui/input';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  useGroups,
  useAddArtifactToGroup,
  useRemoveArtifactFromGroup,
  useCreateGroup,
  useToast,
  useCollections,
  useArtifactGroups,
} from '@/hooks';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';

type DialogStep = 'collection' | 'group';

export interface AddToGroupDialogProps {
  /** Control dialog open state */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** The artifact to add to group(s) */
  artifact: Artifact;
  /** Collection ID to fetch groups from (optional - if not provided, shows collection picker) */
  collectionId?: string;
  /** Callback invoked on successful addition */
  onSuccess?: () => void;
}

/**
 * Add to Group Dialog
 *
 * Allows users to add an artifact to one or more groups within a collection.
 * When collectionId is not provided, shows a collection picker step first.
 *
 * Features:
 * - Collection picker when collectionId not provided
 * - Checkbox list of available groups
 * - Multi-select support for adding to multiple groups
 * - Loading states during fetching and submission
 * - Empty state with action to create a group
 * - Error handling with toast notifications
 *
 * @example
 * ```tsx
 * // With collection ID (direct to groups)
 * <AddToGroupDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   artifact={artifact}
 *   collectionId="default"
 *   onSuccess={() => console.log('Added!')}
 * />
 *
 * // Without collection ID (shows collection picker first)
 * <AddToGroupDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   artifact={artifact}
 *   onSuccess={() => console.log('Added!')}
 * />
 * ```
 */
export function AddToGroupDialog({
  open,
  onOpenChange,
  artifact,
  collectionId,
  onSuccess,
}: AddToGroupDialogProps) {
  const [selectedGroupIds, setSelectedGroupIds] = useState<Set<string>>(new Set());
  const [step, setStep] = useState<DialogStep>('collection');
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [removingGroupId, setRemovingGroupId] = useState<string | null>(null);

  // Determine effective collection ID (prop takes precedence over selection)
  const effectiveCollectionId = collectionId ?? selectedCollectionId;

  // Fetch all collections when artifact has no collection membership
  const { data: allCollectionsData, isLoading: isLoadingAllCollections } = useCollections(
    // Only fetch when we need it (artifact has no collections)
    artifact.collections?.length === 0 && !artifact.collection ? {} : undefined
  );

  // Build effective collections array - prefer artifact.collections, fallback to artifact.collection
  // When artifact has no collections, use all available collections
  const artifactCollections = useMemo(() => {
    if (artifact.collections && artifact.collections.length > 0) {
      return artifact.collections;
    }
    // Fallback to single collection if available (artifact.collection is a string identifier)
    if (artifact.collection) {
      return [
        {
          id: artifact.collection,
          name: artifact.collection,
          artifact_count: undefined, // Not available on single collection reference
        },
      ];
    }
    // No collections on artifact - use all available collections if fetched
    if (allCollectionsData?.items) {
      return allCollectionsData.items.map((collection) => ({
        id: collection.id,
        name: collection.name,
        artifact_count: collection.artifact_count,
      }));
    }
    // Fallback to empty array while loading or if no collections exist
    return [];
  }, [artifact.collections, artifact.collection, allCollectionsData]);

  const {
    data: groupsData,
    isLoading,
    refetch: refetchGroups,
  } = useGroups(effectiveCollectionId ?? '');

  // Fetch groups the artifact already belongs to
  const { data: existingGroups } = useArtifactGroups(
    open && effectiveCollectionId ? artifact.id : undefined,
    effectiveCollectionId ?? undefined
  );

  const addArtifactToGroup = useAddArtifactToGroup();
  const removeArtifactFromGroup = useRemoveArtifactFromGroup();
  const createGroup = useCreateGroup();
  const { toast } = useToast();

  const groups = groupsData?.groups || [];

  // Determine if we should show collection picker
  const showCollectionPicker = !collectionId && step === 'collection';

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedGroupIds(new Set());
      setStep('collection');
      setSelectedCollectionId(null);
      setIsCreatingGroup(false);
      setNewGroupName('');
      setRemovingGroupId(null);
    }
  }, [open]);

  // Auto-select collection and skip to group step when appropriate
  useEffect(() => {
    if (!open) return;

    if (collectionId) {
      // Collection ID provided via prop - skip to group step
      setStep('group');
    } else if (artifactCollections.length === 1 && artifactCollections[0]) {
      // Only one collection available - auto-select and skip to group step
      setSelectedCollectionId(artifactCollections[0].id);
      setStep('group');
    } else if (artifactCollections.length === 0 && !isLoadingAllCollections) {
      // No collections available and not loading - stay on collection step to show empty state
      setStep('collection');
    }
  }, [open, collectionId, artifactCollections]);

  const handleCollectionSelect = (id: string) => {
    setSelectedCollectionId(id);
  };

  const handleNextStep = () => {
    if (selectedCollectionId) {
      setStep('group');
    }
  };

  const handleBackToCollections = () => {
    setStep('collection');
    setSelectedCollectionId(null);
    setSelectedGroupIds(new Set());
  };

  // Get selected collection name for display
  const selectedCollectionName = artifactCollections.find(
    (c) => c.id === selectedCollectionId
  )?.name;

  const handleCheckboxChange = (groupId: string, checked: boolean) => {
    setSelectedGroupIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(groupId);
      } else {
        next.delete(groupId);
      }
      return next;
    });
  };

  const handleRemoveFromGroup = async (groupId: string) => {
    setRemovingGroupId(groupId);
    try {
      await removeArtifactFromGroup.mutateAsync({
        groupId,
        artifactId: artifact.id,
      });

      toast({
        title: 'Removed from group',
        description: `"${artifact.name}" has been removed from the group.`,
      });
      // Dialog stays open - cache invalidation will auto-refetch existingGroups
    } catch (error) {
      console.error('Failed to remove artifact from group:', error);
      toast({
        title: 'Failed to remove from group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    } finally {
      setRemovingGroupId(null);
    }
  };

  const handleCreateGroup = async () => {
    if (!newGroupName.trim() || !effectiveCollectionId) return;

    try {
      const newGroup = await createGroup.mutateAsync({
        collection_id: effectiveCollectionId,
        name: newGroupName.trim(),
      });

      // Auto-select the newly created group
      setSelectedGroupIds((prev) => new Set([...prev, newGroup.id]));

      // Reset create group state
      setIsCreatingGroup(false);
      setNewGroupName('');

      // Refetch groups to ensure the new group appears in the list
      await refetchGroups();

      toast({
        title: 'Group created',
        description: `"${newGroup.name}" has been created.`,
      });
    } catch (error) {
      console.error('Failed to create group:', error);
      toast({
        title: 'Failed to create group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleSubmit = async () => {
    if (selectedGroupIds.size === 0) return;

    try {
      // Add artifact to each selected group
      for (const groupId of selectedGroupIds) {
        await addArtifactToGroup.mutateAsync({
          groupId,
          artifactId: artifact.id,
        });
      }

      // Success toast
      const groupCount = selectedGroupIds.size;
      toast({
        title: 'Added to group' + (groupCount > 1 ? 's' : ''),
        description:
          groupCount === 1
            ? `"${artifact.name}" has been added to the group.`
            : `"${artifact.name}" has been added to ${groupCount} groups.`,
      });

      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error('Failed to add artifact to group:', error);
      toast({
        title: 'Failed to add to group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    if (
      !addArtifactToGroup.isPending &&
      !createGroup.isPending &&
      !removeArtifactFromGroup.isPending
    ) {
      onOpenChange(false);
    }
  };

  const isPending = addArtifactToGroup.isPending;
  const isCreatingGroupPending = createGroup.isPending;
  const isRemovePending = removeArtifactFromGroup.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[640px]">
        <DialogHeader>
          <DialogTitle>Add to Group</DialogTitle>
          <DialogDescription>
            {showCollectionPicker
              ? `Select a collection to add "${artifact.name}" to one of its groups.`
              : `Add "${artifact.name}" to one or more groups${selectedCollectionName ? ` in ${selectedCollectionName}` : ''}.`}
          </DialogDescription>
        </DialogHeader>

        {/* Collection picker step */}
        {showCollectionPicker && (
          <div className="py-4">
            <Label className="text-sm font-medium">Select a collection</Label>
            {isLoadingAllCollections ? (
              <div className="mt-2 space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : artifactCollections.length === 0 ? (
              <div className="mt-2 rounded-lg border border-dashed border-muted-foreground/25 p-6 text-center">
                <FolderOpen
                  className="mx-auto h-8 w-8 text-muted-foreground/50"
                  aria-hidden="true"
                />
                <p className="mt-2 text-sm text-muted-foreground">No collections available.</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Create a collection first to organize artifacts into groups.
                </p>
              </div>
            ) : (
              <ScrollArea className="mt-2 h-[200px] rounded-md border">
                <RadioGroup
                  value={selectedCollectionId ?? ''}
                  onValueChange={handleCollectionSelect}
                  className="p-2"
                  aria-label="Collection selection"
                >
                  {artifactCollections.map((collection) => (
                    <div
                      key={collection.id}
                      className="flex items-center space-x-2 rounded-md px-2 py-2 hover:bg-accent"
                    >
                      <RadioGroupItem
                        value={collection.id}
                        id={`collection-${collection.id}`}
                        aria-label={`Select ${collection.name}`}
                      />
                      <Label
                        htmlFor={`collection-${collection.id}`}
                        className="flex flex-1 cursor-pointer items-center gap-2"
                      >
                        <FolderOpen className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                        <span>{collection.name}</span>
                        {collection.artifact_count !== undefined && (
                          <span className="ml-auto text-xs text-muted-foreground">
                            {collection.artifact_count} artifact
                            {collection.artifact_count !== 1 ? 's' : ''}
                          </span>
                        )}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              </ScrollArea>
            )}
          </div>
        )}

        {/* Groups selection step */}
        {!showCollectionPicker && (
          <div className="py-4">
            {/* Back button (only show when we came from collection picker with multiple options) */}
            {!collectionId && selectedCollectionId && artifactCollections.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBackToCollections}
                className="-ml-2 mb-3 text-muted-foreground hover:text-foreground"
                disabled={isPending}
                aria-label={`Go back to collection selection, currently in ${selectedCollectionName || 'selected collection'}`}
              >
                <ChevronLeft className="mr-1 h-4 w-4" aria-hidden="true" />
                {selectedCollectionName || 'Back'}
              </Button>
            )}

            <div className="flex items-center justify-end mb-3">
              <Link href="/groups">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground hover:text-foreground"
                >
                  <Settings className="mr-1.5 h-4 w-4" aria-hidden="true" />
                  Manage Groups
                </Button>
              </Link>
            </div>

            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : groups.length === 0 ? (
              <div className="rounded-lg border border-dashed border-muted-foreground/25 p-6 text-center">
                <Layers className="mx-auto h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
                <p className="mt-2 text-sm text-muted-foreground">
                  No groups in this collection yet.
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Create a group to organize your artifacts.
                </p>
                {isCreatingGroup ? (
                  <div className="mt-3 flex items-center justify-center gap-2">
                    <Input
                      placeholder="Group name"
                      value={newGroupName}
                      onChange={(e) => setNewGroupName(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === 'Enter' && !isCreatingGroupPending && handleCreateGroup()
                      }
                      autoFocus
                      className="max-w-[180px]"
                      disabled={isCreatingGroupPending}
                      aria-label="New group name"
                    />
                    <Button
                      size="sm"
                      onClick={handleCreateGroup}
                      disabled={!newGroupName.trim() || isCreatingGroupPending}
                      aria-label="Create group"
                    >
                      {isCreatingGroupPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      ) : (
                        'Create'
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setIsCreatingGroup(false);
                        setNewGroupName('');
                      }}
                      disabled={isCreatingGroupPending}
                      aria-label="Cancel creating group"
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-3 text-primary hover:text-primary/90"
                    onClick={() => setIsCreatingGroup(true)}
                    aria-label="Create a new group"
                  >
                    <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                    Create a group
                  </Button>
                )}
              </div>
            ) : (
              <ScrollArea className="max-h-[60vh] min-h-[200px] rounded-md border">
                {/* Create new group section */}
                <div className="border-b p-2">
                  {isCreatingGroup ? (
                    <div className="flex items-center gap-2">
                      <Input
                        placeholder="Group name"
                        value={newGroupName}
                        onChange={(e) => setNewGroupName(e.target.value)}
                        onKeyDown={(e) =>
                          e.key === 'Enter' && !isCreatingGroupPending && handleCreateGroup()
                        }
                        autoFocus
                        disabled={isCreatingGroupPending}
                        aria-label="New group name"
                      />
                      <Button
                        size="sm"
                        onClick={handleCreateGroup}
                        disabled={!newGroupName.trim() || isCreatingGroupPending}
                        aria-label="Create group"
                      >
                        {isCreatingGroupPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        ) : (
                          'Create'
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setIsCreatingGroup(false);
                          setNewGroupName('');
                        }}
                        disabled={isCreatingGroupPending}
                        aria-label="Cancel creating group"
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start"
                      onClick={() => setIsCreatingGroup(true)}
                      disabled={isPending}
                      aria-label="Create a new group"
                    >
                      <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                      Create new group
                    </Button>
                  )}
                </div>
                <div
                  className="grid gap-y-1 p-2"
                  style={{ gridTemplateColumns: 'auto auto 1fr auto' }}
                >
                  {groups.map((group) => {
                    const isAlreadyInGroup =
                      existingGroups?.some((g) => g.id === group.id) ?? false;
                    const isRemoving = isRemovePending && removingGroupId === group.id;

                    return (
                      <div
                        key={group.id}
                        className={cn(
                          'col-span-4 grid grid-cols-subgrid items-start gap-x-3 rounded-md px-2 py-2',
                          isAlreadyInGroup ? 'opacity-60' : 'hover:bg-accent'
                        )}
                      >
                        {/* Col 1: Checkbox */}
                        <Checkbox
                          id={`group-${group.id}`}
                          checked={selectedGroupIds.has(group.id)}
                          onCheckedChange={(checked) =>
                            handleCheckboxChange(group.id, checked === true)
                          }
                          disabled={isPending || isAlreadyInGroup}
                          className="mt-0.5"
                        />

                        {/* Col 2: Name column - auto-sized to widest name across all rows */}
                        <div>
                          <Label
                            htmlFor={`group-${group.id}`}
                            className={cn(
                              'flex items-center gap-2 text-sm font-medium',
                              isAlreadyInGroup ? 'cursor-default' : 'cursor-pointer'
                            )}
                          >
                            {(() => {
                              const colorHex = group.color
                                ? resolveColorHex(group.color)
                                : COLOR_HEX_BY_TOKEN.slate;
                              const IconComponent = group.icon
                                ? ICON_MAP[group.icon as GroupIcon]
                                : null;
                              return (
                                <span
                                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
                                  style={{ backgroundColor: colorHex }}
                                  aria-hidden="true"
                                >
                                  {IconComponent && (
                                    <IconComponent className="h-3 w-3 text-white" />
                                  )}
                                </span>
                              );
                            })()}
                            <span className="whitespace-nowrap">{group.name}</span>
                          </Label>
                          <div className="mt-0.5 flex items-center gap-2 pl-7">
                            {isAlreadyInGroup && (
                              <span className="text-xs text-amber-600">Already in Group</span>
                            )}
                            <span className="shrink-0 text-xs text-muted-foreground">
                              {group.artifact_count} artifact{group.artifact_count !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>

                        {/* Col 3: Description - fills remaining width, aligned across all rows */}
                        <div className="min-w-0 pt-0.5">
                          {group.description && (
                            <p className="line-clamp-2 text-xs text-muted-foreground">
                              {group.description}
                            </p>
                          )}
                        </div>

                        {/* Col 4: Remove button (only for already-in-group items) */}
                        <div>
                          {isAlreadyInGroup && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 shrink-0"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRemoveFromGroup(group.id);
                                    }}
                                    disabled={isRemoving}
                                    aria-label="Remove from group"
                                  >
                                    {isRemoving ? (
                                      <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                                    ) : (
                                      <X className="h-3 w-3" aria-hidden="true" />
                                    )}
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Remove from Group</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            )}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isPending || isCreatingGroupPending || isRemovePending}
          >
            Cancel
          </Button>
          {showCollectionPicker ? (
            <Button
              onClick={handleNextStep}
              disabled={
                !selectedCollectionId ||
                (artifactCollections.length === 0 && !isLoadingAllCollections) ||
                isLoadingAllCollections
              }
            >
              {isLoadingAllCollections ? 'Loading...' : 'Next'}
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={selectedGroupIds.size === 0 || isPending || groups.length === 0}
            >
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  <span>Adding...</span>
                </>
              ) : (
                <>
                  <Layers className="mr-2 h-4 w-4" aria-hidden="true" />
                  Add to Group{selectedGroupIds.size > 1 ? 's' : ''}
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
