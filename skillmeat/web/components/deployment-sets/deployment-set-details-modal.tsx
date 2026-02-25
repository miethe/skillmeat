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
import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import {
  Layers,
  Users,
  AlertCircle,
  Loader2,
  Tag,
  Calendar,
  Hash,
  Info,
  Rocket,
  MoreVertical,
  Pencil,
  Trash2,
  Plus,
  ChevronDown,
  ChevronRight,
  Package,
} from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import { Skeleton } from '@/components/ui/skeleton';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';
import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import {
  useDeploymentSet,
  useResolveSet,
  useDeploymentSetMembers,
  useArtifacts,
  useUpdateDeploymentSet,
  useDeleteDeploymentSet,
  useBatchDeploy,
  useToast,
} from '@/hooks';
import { formatDate } from '@/lib/utils';
import type { DeploymentSet, DeploymentSetMember } from '@/types/deployment-sets';
import type { Artifact } from '@/types/artifact';
import {
  DeploymentSetMemberCard,
  DeploymentSetMemberCardSkeleton,
} from '@/components/deployment-sets/deployment-set-member-card';
import { ArtifactDetailsModal } from '@/components/collection/artifact-details-modal';
import { AddMemberDialog } from '@/components/deployment-sets/add-member-dialog';
import { DeploymentSetTagEditor } from '@/components/deployment-sets/deployment-set-tag-editor';

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
  /** Optional callback triggered when user selects "Edit" from the menu */
  onEdit?: () => void;
  /** Optional callback triggered when user selects "Delete" from the menu */
  onDelete?: () => void;
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
 * name, description, color swatch, icon, tags (editable), resolved member count,
 * and created/updated timestamps.
 *
 * Supports inline editing of name and description via useUpdateDeploymentSet.
 * Uses useResolveSet for the resolved artifact count (30s stale time so it
 * stays fresh after member mutations).
 */
function DeploymentSetOverviewTab({ deploymentSet }: { deploymentSet: DeploymentSet }) {
  const { data: resolution, isLoading: isResolving } = useResolveSet(deploymentSet.id);
  const updateSet = useUpdateDeploymentSet();

  // ── Editable name ──────────────────────────────────────────────────────────
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(deploymentSet.name);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // ── Editable description ───────────────────────────────────────────────────
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const [descriptionValue, setDescriptionValue] = useState(
    deploymentSet.description ?? ''
  );
  const descriptionRef = useRef<HTMLTextAreaElement>(null);

  // Sync local state when deploymentSet changes (e.g., after a successful mutation)
  useEffect(() => {
    if (!isEditingName) setNameValue(deploymentSet.name);
  }, [deploymentSet.name, isEditingName]);

  useEffect(() => {
    if (!isEditingDescription) setDescriptionValue(deploymentSet.description ?? '');
  }, [deploymentSet.description, isEditingDescription]);

  // Auto-focus inputs when editing starts
  useEffect(() => {
    if (isEditingName) nameInputRef.current?.focus();
  }, [isEditingName]);

  useEffect(() => {
    if (isEditingDescription) descriptionRef.current?.focus();
  }, [isEditingDescription]);

  const saveName = useCallback(async () => {
    const trimmed = nameValue.trim();
    if (!trimmed || trimmed === deploymentSet.name) {
      setIsEditingName(false);
      setNameValue(deploymentSet.name);
      return;
    }
    try {
      await updateSet.mutateAsync({ id: deploymentSet.id, data: { name: trimmed } });
    } catch (err) {
      console.error('Failed to update name:', err);
      setNameValue(deploymentSet.name);
    } finally {
      setIsEditingName(false);
    }
  }, [nameValue, deploymentSet.id, deploymentSet.name, updateSet]);

  const saveDescription = useCallback(async () => {
    const trimmed = descriptionValue.trim();
    const current = deploymentSet.description ?? '';
    if (trimmed === current) {
      setIsEditingDescription(false);
      return;
    }
    try {
      await updateSet.mutateAsync({
        id: deploymentSet.id,
        data: { description: trimmed || null },
      });
    } catch (err) {
      console.error('Failed to update description:', err);
      setDescriptionValue(deploymentSet.description ?? '');
    } finally {
      setIsEditingDescription(false);
    }
  }, [descriptionValue, deploymentSet.id, deploymentSet.description, updateSet]);

  const handleNameKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        saveName();
      } else if (e.key === 'Escape') {
        setIsEditingName(false);
        setNameValue(deploymentSet.name);
      }
    },
    [saveName, deploymentSet.name]
  );

  const handleDescriptionKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        saveDescription();
      } else if (e.key === 'Escape') {
        setIsEditingDescription(false);
        setDescriptionValue(deploymentSet.description ?? '');
      }
    },
    [saveDescription, deploymentSet.description]
  );

  return (
    <div className="space-y-6" role="region" aria-label="Deployment set overview">
      {/* Identity: name, color swatch, icon */}
      <div>
        <div className="mb-1 flex items-start gap-2">
          {/* Editable name */}
          {isEditingName ? (
            <Input
              ref={nameInputRef}
              value={nameValue}
              onChange={(e) => setNameValue(e.target.value)}
              onBlur={saveName}
              onKeyDown={handleNameKeyDown}
              className="h-7 flex-1 py-0 text-base font-semibold leading-tight"
              aria-label="Edit deployment set name"
            />
          ) : (
            <div className="group flex flex-1 items-center gap-1.5">
              <h2 className="text-base font-semibold leading-tight">{deploymentSet.name}</h2>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 w-5 p-0 opacity-0 transition-opacity group-hover:opacity-60 focus-visible:opacity-60"
                onClick={() => setIsEditingName(true)}
                aria-label="Edit name"
              >
                <Pencil className="h-3 w-3" />
              </Button>
            </div>
          )}

          {/* Color swatch + icon (always visible) */}
          <div className="flex shrink-0 items-center gap-1.5 pt-0.5">
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
        </div>

        {/* Editable description */}
        {isEditingDescription ? (
          <Textarea
            ref={descriptionRef}
            value={descriptionValue}
            onChange={(e) => setDescriptionValue(e.target.value)}
            onBlur={saveDescription}
            onKeyDown={handleDescriptionKeyDown}
            className="mt-1 min-h-[60px] resize-none text-sm text-muted-foreground"
            placeholder="Add a description... (Enter to save, Shift+Enter for newline, Escape to cancel)"
            aria-label="Edit deployment set description"
          />
        ) : (
          <div className="group flex items-start gap-1.5">
            {deploymentSet.description ? (
              <p className="text-sm text-muted-foreground">{deploymentSet.description}</p>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditingDescription(true)}
                className="text-sm text-muted-foreground/50 italic transition-colors hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                aria-label="Add description"
              >
                Add description...
              </button>
            )}
            {deploymentSet.description && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-0.5 h-4 w-4 shrink-0 p-0 opacity-0 transition-opacity group-hover:opacity-60 focus-visible:opacity-60"
                onClick={() => setIsEditingDescription(true)}
                aria-label="Edit description"
              >
                <Pencil className="h-3 w-3" />
              </Button>
            )}
          </div>
        )}
      </div>

      <Separator />

      {/* Tags — inline editable */}
      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
          <Tag className="h-4 w-4" aria-hidden="true" />
          Tags
        </h3>
        <DeploymentSetTagEditor deploymentSet={deploymentSet} />
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

// ============================================================================
// Member type section config
// ============================================================================

type MemberTypeKey = 'artifact' | 'group' | 'set';

const MEMBER_TYPE_CONFIG: Record<
  MemberTypeKey,
  { label: string; icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }> }
> = {
  artifact: { label: 'Artifacts', icon: Package },
  group: { label: 'Groups', icon: Users },
  set: { label: 'Sets', icon: Layers },
};

const MEMBER_TYPE_ORDER: MemberTypeKey[] = ['artifact', 'group', 'set'];

// ============================================================================
// Collapsible member section
// ============================================================================

interface MemberSectionProps {
  sectionKey: MemberTypeKey;
  members: DeploymentSetMember[];
  isCollapsed: boolean;
  onToggle: () => void;
  artifactByUuid: Record<string, Artifact>;
  onArtifactClick: (artifact: Artifact) => void;
  onSetClick: (nestedSetId: string) => void;
}

function MemberSection({
  sectionKey,
  members,
  isCollapsed,
  onToggle,
  artifactByUuid,
  onArtifactClick,
  onSetClick,
}: MemberSectionProps) {
  const config = MEMBER_TYPE_CONFIG[sectionKey];
  const Icon = config.icon;
  const ChevronIcon = isCollapsed ? ChevronRight : ChevronDown;

  return (
    <Collapsible open={!isCollapsed} onOpenChange={() => onToggle()}>
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md px-1 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-expanded={!isCollapsed}
          aria-label={`${isCollapsed ? 'Expand' : 'Collapse'} ${config.label} section`}
        >
          <ChevronIcon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span>
            {config.label}{' '}
            <span className="font-normal text-muted-foreground">({members.length})</span>
          </span>
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div
          className="mt-2 max-h-[300px] overflow-y-auto"
          aria-label={`${config.label} members`}
        >
          <div
            className="grid grid-cols-1 gap-3 pb-1 pr-1 sm:grid-cols-2 lg:grid-cols-3"
            role="list"
            aria-label={`${config.label} member cards`}
          >
            {members.map((member, index) => {
              const position = member.position ?? index + 1;

              if (sectionKey === 'artifact') {
                const resolvedArtifact =
                  member.artifact_uuid ? artifactByUuid[member.artifact_uuid] : undefined;
                return (
                  <div key={member.id} role="listitem">
                    <DeploymentSetMemberCard
                      member={member}
                      resolvedArtifact={resolvedArtifact}
                      position={position}
                      onClick={
                        resolvedArtifact
                          ? () => onArtifactClick(resolvedArtifact)
                          : undefined
                      }
                    />
                  </div>
                );
              }

              if (sectionKey === 'set') {
                return (
                  <div key={member.id} role="listitem">
                    <DeploymentSetMemberCard
                      member={member}
                      position={position}
                      onClick={() => {
                        if (member.nested_set_id) {
                          onSetClick(member.nested_set_id);
                        }
                      }}
                    />
                  </div>
                );
              }

              // group
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
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

/**
 * DeploymentSetMembersTab
 *
 * Renders the Members tab content for a deployment set. Fetches members via
 * useDeploymentSetMembers and resolves artifact data for artifact-type members
 * by building a UUID → Artifact map from useArtifacts.
 *
 * Layout:
 *   - Header row: "Members (N)" title + "Add Members" button
 *   - Collapsible sections grouped by member type (artifact, group, set)
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

  // State for the Add Members dialog
  const [addMemberOpen, setAddMemberOpen] = useState(false);

  // Collapsed sections — tracked by member type key
  const [collapsedSections, setCollapsedSections] = useState<Set<MemberTypeKey>>(new Set());

  const toggleSection = useCallback((key: MemberTypeKey) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

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

  // Group members by type
  const membersByType = useMemo(() => {
    const groups: Record<MemberTypeKey, DeploymentSetMember[]> = {
      artifact: [],
      group: [],
      set: [],
    };
    for (const member of sortedMembers) {
      const key = member.member_type as MemberTypeKey;
      if (key in groups) {
        groups[key].push(member);
      }
    }
    return groups;
  }, [sortedMembers]);

  const totalCount = sortedMembers.length;

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-28" aria-label="Loading members count" />
          <Skeleton className="h-8 w-32" aria-label="Loading add button" />
        </div>
        <div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
          aria-busy="true"
          aria-label="Loading members"
        >
          {[1, 2, 3].map((i) => (
            <DeploymentSetMemberCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Header row */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">
          Members
          {totalCount > 0 && (
            <span className="ml-1 font-normal text-muted-foreground">({totalCount})</span>
          )}
        </h3>
        <Button
          variant="outline"
          size="sm"
          className="h-8 gap-1.5 px-3 text-xs"
          onClick={() => setAddMemberOpen(true)}
          aria-label="Add members to this deployment set"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          Add Members
        </Button>
      </div>

      {/* Empty state — shown when there are no members across all types */}
      {totalCount === 0 ? (
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
      ) : (
        /* Collapsible sections grouped by type */
        <div className="space-y-1" role="region" aria-label="Members by type">
          {MEMBER_TYPE_ORDER.map((typeKey) => {
            const sectionMembers = membersByType[typeKey];
            if (sectionMembers.length === 0) return null;
            return (
              <MemberSection
                key={typeKey}
                sectionKey={typeKey}
                members={sectionMembers}
                isCollapsed={collapsedSections.has(typeKey)}
                onToggle={() => toggleSection(typeKey)}
                artifactByUuid={artifactByUuid}
                onArtifactClick={(artifact) => {
                  setSelectedArtifact(artifact);
                  setArtifactModalOpen(true);
                }}
                onSetClick={(nestedId) => {
                  setNestedSetId(nestedId);
                  setNestedSetModalOpen(true);
                }}
              />
            );
          })}
        </div>
      )}

      {/* Add Members dialog */}
      <AddMemberDialog
        open={addMemberOpen}
        onOpenChange={setAddMemberOpen}
        setId={setId}
      />

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
 * Renders a max-w-5xl Dialog containing tabbed content for a deployment set.
 * Fetches the set via useDeploymentSet — disabled when setId is null.
 * Shows loading skeleton while fetching and an error state on failure.
 *
 * Header actions:
 *   - Deploy button: batch-deploys the set to the current directory
 *   - Kebab menu: Edit (calls onEdit prop) and Delete (calls onDelete prop or
 *     executes deletion directly via useDeleteDeploymentSet)
 */
export function DeploymentSetDetailsModal({
  setId,
  open,
  onOpenChange,
  onEdit,
  onDelete,
}: DeploymentSetDetailsModalProps) {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const { toast } = useToast();

  const {
    data: deploymentSet,
    isLoading,
    error,
  } = useDeploymentSet(setId ?? '');

  const batchDeploy = useBatchDeploy();
  const deleteSet = useDeleteDeploymentSet();

  // Reset to overview tab whenever a different set is opened
  React.useEffect(() => {
    if (open) {
      setActiveTab('overview');
    }
  }, [open, setId]);

  // Derive dialog title — shown even during loading
  const title = deploymentSet?.name ?? (isLoading ? 'Loading…' : 'Deployment Set');
  const description = deploymentSet?.description ?? undefined;

  const handleDeploy = useCallback(async () => {
    if (!deploymentSet) return;
    try {
      const result = await batchDeploy.mutateAsync({
        id: deploymentSet.id,
        data: { project_path: '.' },
      });
      const successCount = result.results.filter((r) => r.status === 'success').length;
      const failedCount = result.results.filter((r) => r.status === 'failed').length;
      toast({
        title: 'Deployment complete',
        description:
          failedCount > 0
            ? `${successCount} deployed, ${failedCount} failed`
            : `${successCount} artifact${successCount !== 1 ? 's' : ''} deployed successfully`,
      });
    } catch (err) {
      toast({
        title: 'Deployment failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [deploymentSet, batchDeploy, toast]);

  const handleDelete = useCallback(async () => {
    if (!deploymentSet) return;
    if (onDelete) {
      onDelete();
      return;
    }
    try {
      await deleteSet.mutateAsync(deploymentSet.id);
      onOpenChange(false);
      toast({ title: 'Deployment set deleted' });
    } catch (err) {
      toast({
        title: 'Failed to delete',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [deploymentSet, deleteSet, onDelete, onOpenChange, toast]);

  // Header actions — Deploy button + kebab menu
  const headerActions = deploymentSet ? (
    <>
      <Button
        variant="default"
        size="sm"
        className="h-7 gap-1.5 px-3 text-xs"
        onClick={handleDeploy}
        disabled={batchDeploy.isPending}
        aria-label="Deploy this deployment set"
      >
        {batchDeploy.isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        ) : (
          <Rocket className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        Deploy
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            aria-label="More options"
          >
            <MoreVertical className="h-4 w-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {onEdit && (
            <DropdownMenuItem onClick={onEdit}>
              <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
              Edit
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onClick={handleDelete}
            className="text-destructive focus:text-destructive"
            disabled={deleteSet.isPending}
          >
            <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  ) : isLoading ? (
    <Loader2
      className="h-4 w-4 animate-spin text-muted-foreground"
      aria-label="Loading"
    />
  ) : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[90vh] max-w-5xl flex-col gap-0 overflow-hidden p-0"
        aria-label={`Deployment set details: ${title}`}
      >
        {/* Header */}
        <ModalHeader
          icon={Layers}
          iconClassName="text-primary"
          title={title}
          description={description}
          actions={headerActions}
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
