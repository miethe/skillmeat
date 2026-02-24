'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Search, X, Package, Layers, Layers3, Users, CheckCircle2 } from 'lucide-react';
import {
  useAddMember,
  useArtifacts,
  useDeploymentSets,
  useToast,
} from '@/hooks';
import type { DeploymentSet } from '@/types/deployment-sets';
import type { Artifact } from '@/types/artifact';
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
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ARTIFACT_TYPE_LABELS: Record<string, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP',
  hook: 'Hook',
};

const ARTIFACT_TYPE_COLORS: Record<string, string> = {
  skill: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  command: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  agent: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  mcp: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  hook: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AddMemberDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The deployment set ID to add members to */
  setId: string;
}

type TabValue = 'artifact' | 'group' | 'set';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Skeleton row for loading states */
function ItemSkeleton() {
  return (
    <div className="flex items-center gap-3 rounded-lg px-3 py-2.5">
      <Skeleton className="h-5 w-12 rounded" />
      <Skeleton className="h-4 w-40" />
    </div>
  );
}

/** Empty state for each tab */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <Package className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

interface SearchInputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}

function SearchInput({ value, onChange, placeholder }: SearchInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

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

// ---------------------------------------------------------------------------
// Keyboard-navigable list item
// ---------------------------------------------------------------------------

interface PickerItemProps {
  onSelect: () => void;
  isAdding?: boolean;
  justAdded?: boolean;
  children: React.ReactNode;
  ariaLabel: string;
}

function PickerItem({ onSelect, isAdding, justAdded, children, ariaLabel }: PickerItemProps) {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === 'Enter' || e.key === ' ') && !isAdding) {
        e.preventDefault();
        onSelect();
      }
    },
    [onSelect, isAdding],
  );

  return (
    <div
      role="listitem"
      tabIndex={0}
      onClick={!isAdding ? onSelect : undefined}
      onKeyDown={handleKeyDown}
      aria-label={ariaLabel}
      aria-disabled={isAdding}
      className={cn(
        'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
        'hover:bg-accent focus-visible:bg-accent focus-visible:outline-none',
        isAdding && 'cursor-wait opacity-60',
        justAdded && 'bg-emerald-50 dark:bg-emerald-950/30',
      )}
    >
      {children}
      {justAdded && (
        <CheckCircle2
          className="ml-auto h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400"
          aria-hidden="true"
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Artifact tab
// ---------------------------------------------------------------------------

interface ArtifactTabProps {
  setId: string;
  onAdded: (uuid: string) => void;
}

function ArtifactTab({ setId, onAdded }: ArtifactTabProps) {
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const addMember = useAddMember();

  const { data: artifactsData, isLoading } = useArtifacts({}, { field: 'name', order: 'asc' });
  const artifacts: Artifact[] = artifactsData?.artifacts ?? [];

  const filtered = artifacts.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  );

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
        // Clear the just-added indicator after 1.5s
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
      <SearchInput value={search} onChange={setSearch} placeholder="Search artifacts…" />

      <ScrollArea className="h-64">
        {isLoading ? (
          <div role="list" aria-label="Loading artifacts">
            {[1, 2, 3, 4].map((i) => (
              <ItemSkeleton key={i} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            message={search ? `No artifacts match "${search}".` : 'No artifacts in your collection.'}
          />
        ) : (
          <div role="list" aria-label="Artifacts">
            {filtered.map((artifact) => (
              <PickerItem
                key={artifact.uuid}
                onSelect={() => void handleAdd(artifact)}
                isAdding={addingId === artifact.uuid}
                justAdded={addedIds.has(artifact.uuid)}
                ariaLabel={`Add ${artifact.name} (${artifact.type})`}
              >
                <span
                  className={cn(
                    'shrink-0 rounded px-1.5 py-0.5 text-xs font-medium',
                    ARTIFACT_TYPE_COLORS[artifact.type] ??
                      'bg-muted text-muted-foreground',
                  )}
                >
                  {ARTIFACT_TYPE_LABELS[artifact.type] ?? artifact.type}
                </span>
                <span className="min-w-0 truncate font-medium">{artifact.name}</span>
                {artifact.description && (
                  <span className="ml-auto shrink-0 max-w-[120px] truncate text-xs text-muted-foreground">
                    {artifact.description}
                  </span>
                )}
              </PickerItem>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group tab
// ---------------------------------------------------------------------------

// Minimal Group shape needed for picker (avoids requiring collection ID in this context)
interface GroupPickerItem {
  id: string;
  name: string;
  artifact_count: number;
  color?: string;
}

interface GroupTabProps {
  setId: string;
  onAdded: (groupId: string) => void;
}

function GroupTab({ setId, onAdded }: GroupTabProps) {
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const addMember = useAddMember();

  // Fetch all groups via the groups endpoint (no collection filter = all groups)
  const [groups, setGroups] = useState<GroupPickerItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    fetch('/api/v1/groups', {
      headers: { 'Content-Type': 'application/json' },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Groups fetch failed: ${res.status}`);
        return res.json() as Promise<{ groups: GroupPickerItem[]; total: number }>;
      })
      .then((data) => {
        if (!cancelled) {
          const sorted = [...(data.groups ?? [])].sort((a, b) =>
            a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }),
          );
          setGroups(sorted);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.warn('[add-member-dialog] Failed to fetch groups:', err);
          setGroups([]);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = groups.filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleAdd = useCallback(
    async (group: GroupPickerItem) => {
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
      <SearchInput value={search} onChange={setSearch} placeholder="Search groups…" />

      <ScrollArea className="h-64">
        {isLoading ? (
          <div role="list" aria-label="Loading groups">
            {[1, 2, 3].map((i) => (
              <ItemSkeleton key={i} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            message={search ? `No groups match "${search}".` : 'No groups found.'}
          />
        ) : (
          <div role="list" aria-label="Groups">
            {filtered.map((group) => (
              <PickerItem
                key={group.id}
                onSelect={() => void handleAdd(group)}
                isAdding={addingId === group.id}
                justAdded={addedIds.has(group.id)}
                ariaLabel={`Add group ${group.name}`}
              >
                <Users
                  className="h-4 w-4 shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <span className="min-w-0 truncate font-medium">{group.name}</span>
                <Badge variant="outline" className="ml-auto shrink-0 text-xs">
                  {group.artifact_count} {group.artifact_count === 1 ? 'artifact' : 'artifacts'}
                </Badge>
              </PickerItem>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Set tab
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
  // Exclude the current set from the picker
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
        // 422 = circular reference
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
      <SearchInput value={search} onChange={setSearch} placeholder="Search deployment sets…" />

      <ScrollArea className="h-64">
        {isLoading ? (
          <div role="list" aria-label="Loading deployment sets">
            {[1, 2, 3].map((i) => (
              <ItemSkeleton key={i} />
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
          <div role="list" aria-label="Deployment sets">
            {filtered.map((depSet) => (
              <PickerItem
                key={depSet.id}
                onSelect={() => void handleAdd(depSet)}
                isAdding={addingId === depSet.id}
                justAdded={addedIds.has(depSet.id)}
                ariaLabel={`Add deployment set ${depSet.name}`}
              >
                {/* Color indicator */}
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
              </PickerItem>
            ))}
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
 * - Artifact tab: search + type badge + click to add
 * - Group tab: search + artifact count + click to add
 * - Set tab: search + color indicator + member count + click to add (circular-ref protected)
 * - Success toast on add, error toast on failure
 * - WCAG 2.1 AA: keyboard navigation, ARIA labels, focus management
 */
export function AddMemberDialog({ open, onOpenChange, setId }: AddMemberDialogProps) {
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
        className="sm:max-w-lg"
        aria-label="Add member to deployment set"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layers3 className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            Add Member
          </DialogTitle>
          <DialogDescription>
            Choose an artifact, group, or deployment set to add to this set. Click any
            item to add it immediately.
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
            <GroupTab setId={setId} onAdded={handleAdded} />
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
