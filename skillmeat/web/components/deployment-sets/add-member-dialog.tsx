'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  Search,
  X,
  Package,
  Layers,
  Layers3,
  Users,
  CheckCircle2,
  Zap,
  Terminal,
  Bot,
  Server,
  Webhook,
} from 'lucide-react';
import {
  useAddMember,
  useArtifacts,
  useCollections,
  useDeploymentSets,
  useGroups,
  useToast,
} from '@/hooks';
import type { DeploymentSet } from '@/types/deployment-sets';
import type { Artifact, ArtifactType } from '@/types/artifact';
import type { Group } from '@/types/groups';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MiniArtifactCard } from '@/components/collection/mini-artifact-card';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ARTIFACT_TYPES: {
  value: ArtifactType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { value: 'skill', label: 'Skills', icon: Zap },
  { value: 'command', label: 'Commands', icon: Terminal },
  { value: 'agent', label: 'Agents', icon: Bot },
  { value: 'mcp', label: 'MCP Servers', icon: Server },
  { value: 'hook', label: 'Hooks', icon: Webhook },
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AddMemberDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The deployment set ID to add members to */
  setId: string;
  /**
   * Optional collection ID for the Groups tab.
   * When omitted, the first available collection is used automatically.
   * Pass explicitly to support a future collection selector.
   */
  collectionId?: string;
}

type TabValue = 'artifact' | 'group' | 'set';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Grid skeleton cards for loading states */
function GridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex min-w-[180px] flex-col gap-2 rounded-lg border border-l-[3px] p-3 border-l-muted">
          <div className="flex items-center gap-1.5">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 flex-1 rounded" />
          </div>
          <Skeleton className="h-3 w-full rounded" />
          <Skeleton className="h-3 w-2/3 rounded" />
          <div className="mt-auto pt-1">
            <Skeleton className="h-4 w-1/2 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Empty state */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Package className="h-9 w-9 text-muted-foreground/30" aria-hidden="true" />
      <p className="mt-3 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

/** Search input with icon + clear button */
interface SearchInputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  autoFocus?: boolean;
}

function SearchInput({ value, onChange, placeholder, autoFocus }: SearchInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  return (
    <div className="relative">
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-9 pr-9"
        aria-label={placeholder}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

/** Type filter pills — multi-select, shown only on artifact tab */
interface TypeFilterProps {
  selected: Set<ArtifactType>;
  onToggle: (type: ArtifactType) => void;
}

function TypeFilter({ selected, onToggle }: TypeFilterProps) {
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by artifact type">
      {ARTIFACT_TYPES.map(({ value, label, icon: Icon }) => {
        const active = selected.has(value);
        return (
          <button
            key={value}
            type="button"
            onClick={() => onToggle(value)}
            aria-pressed={active}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              active
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-transparent text-muted-foreground hover:border-foreground/40 hover:text-foreground',
            )}
          >
            <Icon className="h-3 w-3" aria-hidden="true" />
            {label}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Artifact tab — grid of MiniArtifactCards with selection overlay
// ---------------------------------------------------------------------------

interface ArtifactTabProps {
  setId: string;
  onAdded: (uuid: string) => void;
}

function ArtifactTab({ setId, onAdded }: ArtifactTabProps) {
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Set<ArtifactType>>(new Set());
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const addMember = useAddMember();

  const { data: artifactsData, isLoading } = useArtifacts({}, { field: 'name', order: 'asc' });
  const artifacts: Artifact[] = artifactsData?.artifacts ?? [];

  const filtered = useMemo(() => {
    return artifacts.filter((a) => {
      const matchesSearch = a.name.toLowerCase().includes(search.toLowerCase());
      const matchesType = selectedTypes.size === 0 || selectedTypes.has(a.type as ArtifactType);
      return matchesSearch && matchesType;
    });
  }, [artifacts, search, selectedTypes]);

  const toggleType = useCallback((type: ArtifactType) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const handleAdd = useCallback(
    async (artifact: Artifact) => {
      if (addingId) return;
      setAddingId(artifact.uuid);
      try {
        await addMember.mutateAsync({
          setId,
          data: { artifact_uuid: artifact.uuid },
        });
        setAddedIds((prev) => new Set([...prev, artifact.uuid]));
        onAdded(artifact.uuid);
        toast({ title: 'Member added', description: `"${artifact.name}" added to set.` });
        setTimeout(() => {
          setAddedIds((prev) => {
            const next = new Set(prev);
            next.delete(artifact.uuid);
            return next;
          });
        }, 1500);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred.';
        const isCircular =
          message.toLowerCase().includes('circular') ||
          (err as { status?: number })?.status === 422;
        toast({
          title: isCircular ? 'Circular reference' : 'Failed to add member',
          description: isCircular
            ? 'This would create a circular reference.'
            : message,
          variant: 'destructive',
        });
      } finally {
        setAddingId(null);
      }
    },
    [addingId, addMember, setId, onAdded, toast],
  );

  return (
    <div className="flex flex-col gap-3">
      <SearchInput value={search} onChange={setSearch} placeholder="Search artifacts…" autoFocus />
      <TypeFilter selected={selectedTypes} onToggle={toggleType} />

      <ScrollArea className="h-[340px]">
        {isLoading ? (
          <GridSkeleton count={8} />
        ) : filtered.length === 0 ? (
          <EmptyState
            message={
              search || selectedTypes.size > 0
                ? 'No artifacts match your filters.'
                : 'No artifacts in your collection.'
            }
          />
        ) : (
          <div
            className="grid grid-cols-2 gap-2 sm:grid-cols-3"
            role="list"
            aria-label="Artifacts"
          >
            {filtered.map((artifact) => {
              const isAdding = addingId === artifact.uuid;
              const isAdded = addedIds.has(artifact.uuid);
              return (
                <div
                  key={artifact.uuid}
                  role="listitem"
                  className="relative min-w-[180px]"
                >
                  <MiniArtifactCard
                    artifact={artifact}
                    onClick={() => void handleAdd(artifact)}
                    className={cn(
                      'cursor-pointer transition-all',
                      isAdding && 'cursor-wait opacity-60',
                      isAdded && 'ring-2 ring-emerald-500 ring-offset-1',
                    )}
                    aria-label={`Add ${artifact.name} (${artifact.type})`}
                    aria-disabled={isAdding}
                  />
                  {/* Selection checkmark overlay */}
                  {isAdded && (
                    <div
                      className="pointer-events-none absolute inset-0 flex items-start justify-end rounded-lg bg-emerald-500/10 p-1.5"
                      aria-hidden="true"
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 shadow">
                        <CheckCircle2 className="h-3.5 w-3.5 text-white" />
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group tab — list view (groups don't map to MiniArtifactCard)
// ---------------------------------------------------------------------------

interface GroupTabProps {
  setId: string;
  onAdded: (groupId: string) => void;
  /** Collection ID to load groups from. Falls back to the first available collection. */
  collectionId?: string;
}

function GroupTab({ setId, onAdded, collectionId }: GroupTabProps) {
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const addMember = useAddMember();

  // Resolve collection ID: use prop if provided, otherwise fall back to the first collection
  const { data: collectionsData } = useCollections({ limit: 1 });
  const resolvedCollectionId = collectionId ?? collectionsData?.items[0]?.id;

  const { data: groupsData, isLoading } = useGroups(resolvedCollectionId);
  const groups = groupsData?.groups ?? [];

  const filtered = groups.filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleAdd = useCallback(
    async (group: Group) => {
      if (addingId) return;
      setAddingId(group.id);
      try {
        await addMember.mutateAsync({
          setId,
          data: { group_id: group.id },
        });
        setAddedIds((prev) => new Set([...prev, group.id]));
        onAdded(group.id);
        toast({ title: 'Member added', description: `Group "${group.name}" added to set.` });
        setTimeout(() => {
          setAddedIds((prev) => {
            const next = new Set(prev);
            next.delete(group.id);
            return next;
          });
        }, 1500);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred.';
        toast({
          title: 'Failed to add member',
          description: message,
          variant: 'destructive',
        });
      } finally {
        setAddingId(null);
      }
    },
    [addingId, addMember, setId, onAdded, toast],
  );

  return (
    <div className="flex flex-col gap-3">
      <SearchInput value={search} onChange={setSearch} placeholder="Search groups…" autoFocus />

      <ScrollArea className="h-[340px]">
        {isLoading ? (
          <div className="flex flex-col gap-1" role="list" aria-label="Loading groups">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2.5">
                <Skeleton className="h-4 w-4 rounded-full" />
                <Skeleton className="h-4 w-40" />
                <Skeleton className="ml-auto h-5 w-20 rounded-full" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            message={search ? `No groups match "${search}".` : 'No groups found.'}
          />
        ) : (
          <div className="flex flex-col gap-0.5" role="list" aria-label="Groups">
            {filtered.map((group) => {
              const isAdding = addingId === group.id;
              const isAdded = addedIds.has(group.id);
              return (
                <div
                  key={group.id}
                  role="listitem"
                  tabIndex={0}
                  onClick={!isAdding ? () => void handleAdd(group) : undefined}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && !isAdding) {
                      e.preventDefault();
                      void handleAdd(group);
                    }
                  }}
                  aria-label={`Add group ${group.name}`}
                  aria-disabled={isAdding}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                    'hover:bg-accent focus-visible:bg-accent focus-visible:outline-none',
                    isAdding && 'cursor-wait opacity-60',
                    isAdded && 'bg-emerald-50 dark:bg-emerald-950/30',
                  )}
                >
                  <Users className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0 truncate font-medium">{group.name}</span>
                  <Badge variant="outline" className="ml-auto shrink-0 text-xs">
                    {group.artifact_count} {group.artifact_count === 1 ? 'artifact' : 'artifacts'}
                  </Badge>
                  {isAdded && (
                    <CheckCircle2
                      className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400"
                      aria-hidden="true"
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Set tab — list view (deployment sets are not artifacts)
// ---------------------------------------------------------------------------

interface SetTabProps {
  setId: string;
  onAdded: (nestedSetId: string) => void;
}

function SetTab({ setId, onAdded }: SetTabProps) {
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const addMember = useAddMember();

  const { data: setsData, isLoading } = useDeploymentSets({ limit: 200 });
  const otherSets: DeploymentSet[] = (setsData?.items ?? []).filter((s) => s.id !== setId);

  const filtered = otherSets.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleAdd = useCallback(
    async (set: DeploymentSet) => {
      if (addingId) return;
      setAddingId(set.id);
      try {
        await addMember.mutateAsync({
          setId,
          data: { nested_set_id: set.id },
        });
        setAddedIds((prev) => new Set([...prev, set.id]));
        onAdded(set.id);
        toast({ title: 'Member added', description: `Set "${set.name}" added as nested member.` });
        setTimeout(() => {
          setAddedIds((prev) => {
            const next = new Set(prev);
            next.delete(set.id);
            return next;
          });
        }, 1500);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred.';
        const isCircular =
          message.toLowerCase().includes('circular') ||
          (err as { status?: number })?.status === 422;
        toast({
          title: isCircular ? 'Circular reference' : 'Failed to add member',
          description: isCircular
            ? 'This would create a circular reference.'
            : message,
          variant: 'destructive',
        });
      } finally {
        setAddingId(null);
      }
    },
    [addingId, addMember, setId, onAdded, toast],
  );

  return (
    <div className="flex flex-col gap-3">
      <SearchInput value={search} onChange={setSearch} placeholder="Search deployment sets…" autoFocus />

      <ScrollArea className="h-[340px]">
        {isLoading ? (
          <div className="flex flex-col gap-1" role="list" aria-label="Loading deployment sets">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2.5">
                <Skeleton className="h-3 w-3 rounded-full" />
                <Skeleton className="h-4 w-44" />
                <Skeleton className="ml-auto h-5 w-20 rounded-full" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            message={
              search
                ? `No deployment sets match "${search}".`
                : otherSets.length === 0
                  ? 'No other deployment sets exist.'
                  : `No sets match "${search}".`
            }
          />
        ) : (
          <div className="flex flex-col gap-0.5" role="list" aria-label="Deployment sets">
            {filtered.map((depSet) => {
              const isAdding = addingId === depSet.id;
              const isAdded = addedIds.has(depSet.id);
              return (
                <div
                  key={depSet.id}
                  role="listitem"
                  tabIndex={0}
                  onClick={!isAdding ? () => void handleAdd(depSet) : undefined}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && !isAdding) {
                      e.preventDefault();
                      void handleAdd(depSet);
                    }
                  }}
                  aria-label={`Add deployment set ${depSet.name}`}
                  aria-disabled={isAdding}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                    'hover:bg-accent focus-visible:bg-accent focus-visible:outline-none',
                    isAdding && 'cursor-wait opacity-60',
                    isAdded && 'bg-emerald-50 dark:bg-emerald-950/30',
                  )}
                >
                  <span
                    className="h-3 w-3 shrink-0 rounded-full border border-border"
                    style={{
                      backgroundColor: depSet.color?.startsWith('#')
                        ? depSet.color
                        : 'hsl(var(--muted-foreground))',
                    }}
                    aria-hidden="true"
                  />
                  {depSet.icon && (
                    <span className="shrink-0 text-base leading-none" aria-hidden="true">
                      {depSet.icon}
                    </span>
                  )}
                  <span className="min-w-0 truncate font-medium">{depSet.name}</span>
                  <Badge variant="outline" className="ml-auto shrink-0 text-xs">
                    {depSet.member_count} {depSet.member_count === 1 ? 'member' : 'members'}
                  </Badge>
                  {isAdded && (
                    <CheckCircle2
                      className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400"
                      aria-hidden="true"
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main dialog
// ---------------------------------------------------------------------------

/**
 * Add Member Dialog
 *
 * Three-tab picker for adding Artifacts, Groups, or other Deployment Sets
 * as members of the given deployment set.
 *
 * Features:
 * - Artifact tab: responsive grid of MiniArtifactCards with search + type filter pills
 * - Group tab: list view with search
 * - Set tab: list view with search + color indicator + member count (circular-ref protected)
 * - Selection checkmark overlay on added cards
 * - Success toast on add, error toast on failure
 * - WCAG 2.1 AA: keyboard navigation, ARIA labels, focus management
 */
export function AddMemberDialog({ open, onOpenChange, setId, collectionId }: AddMemberDialogProps) {
  const [activeTab, setActiveTab] = useState<TabValue>('artifact');

  // Reset tab when dialog opens
  useEffect(() => {
    if (open) setActiveTab('artifact');
  }, [open]);

  // noop — cache invalidation from useAddMember handles list refresh automatically
  const handleAdded = useCallback(() => {}, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-3xl"
        aria-label="Add member to deployment set"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layers3 className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            Add Member
          </DialogTitle>
          <DialogDescription>
            Choose an artifact, group, or deployment set to add to this set.
            Click any item to add it immediately.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as TabValue)}
          className="mt-1"
        >
          <TabsList className="grid w-full grid-cols-3" aria-label="Member type">
            <TabsTrigger value="artifact" className="gap-1.5">
              <Package className="h-3.5 w-3.5" aria-hidden="true" />
              Artifacts
            </TabsTrigger>
            <TabsTrigger value="group" className="gap-1.5">
              <Users className="h-3.5 w-3.5" aria-hidden="true" />
              Groups
            </TabsTrigger>
            <TabsTrigger value="set" className="gap-1.5">
              <Layers className="h-3.5 w-3.5" aria-hidden="true" />
              Sets
            </TabsTrigger>
          </TabsList>

          <TabsContent value="artifact" className="mt-3 focus-visible:outline-none">
            <ArtifactTab setId={setId} onAdded={handleAdded} />
          </TabsContent>

          <TabsContent value="group" className="mt-3 focus-visible:outline-none">
            <GroupTab setId={setId} onAdded={handleAdded} collectionId={collectionId} />
          </TabsContent>

          <TabsContent value="set" className="mt-3 focus-visible:outline-none">
            <SetTab setId={setId} onAdded={handleAdded} />
          </TabsContent>
        </Tabs>

        <div className="flex justify-end pt-1">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
