'use client';

import { useState, useMemo } from 'react';
import { Layers3, PackageSearch, Plus, Search } from 'lucide-react';
import {
  useDeploymentSets,
  useDeleteDeploymentSet,
  useCloneDeploymentSet,
  useToast,
} from '@/hooks';
import type { DeploymentSet } from '@/types/deployment-sets';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { BatchDeployModal } from './batch-deploy-modal';
import { DeploymentSetCard } from './deployment-set-card';
import { CreateDeploymentSetDialog } from './create-deployment-set-dialog';
import { EditDeploymentSetDialog } from './edit-deployment-set-dialog';

// ============================================================================
// Empty state helper
// ============================================================================

function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 py-12 text-center">
      <Icon className="h-12 w-12 text-muted-foreground/50" aria-hidden />
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// ============================================================================
// Main component
// ============================================================================

/**
 * DeploymentSetList — client component rendered inside the deployment-sets page.
 *
 * Provides:
 * - Live search (client-side name filter)
 * - Card grid with per-card Edit / Clone / Delete actions
 * - Create dialog triggered from toolbar button or empty-state CTA
 * - Inline delete confirmation via AlertDialog
 */
export function DeploymentSetList() {
  const { toast } = useToast();

  // --- data ---
  const { data, isLoading } = useDeploymentSets();
  const sets = data?.items ?? [];

  // --- mutations ---
  const deleteSet = useDeleteDeploymentSet();
  const cloneSet = useCloneDeploymentSet();

  // --- UI state ---
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editingSet, setEditingSet] = useState<DeploymentSet | null>(null);
  const [deletingSet, setDeletingSet] = useState<DeploymentSet | null>(null);
  const [deployingSet, setDeployingSet] = useState<DeploymentSet | null>(null);

  // --- filtered sets ---
  const filteredSets = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) {
      return sets;
    }
    return sets.filter((s) => {
      const haystack = [s.name, s.description ?? '', ...(s.tags ?? [])].join(' ').toLowerCase();
      return haystack.includes(q);
    });
  }, [sets, search]);

  // --- handlers ---
  const handleDelete = async () => {
    if (!deletingSet) {
      return;
    }
    try {
      await deleteSet.mutateAsync(deletingSet.id);
      toast({
        title: 'Deployment set deleted',
        description: `"${deletingSet.name}" was deleted.`,
      });
      setDeletingSet(null);
    } catch (err) {
      toast({
        title: 'Delete failed',
        description: err instanceof Error ? err.message : 'Unexpected error.',
        variant: 'destructive',
      });
    }
  };

  const handleClone = async (set: DeploymentSet) => {
    try {
      await cloneSet.mutateAsync(set.id);
      toast({
        title: 'Deployment set cloned',
        description: `A copy of "${set.name}" was created.`,
      });
    } catch (err) {
      toast({
        title: 'Clone failed',
        description: err instanceof Error ? err.message : 'Unexpected error.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Toolbar */}
      <div
        className="flex flex-wrap items-center gap-3 rounded-lg border bg-card p-4"
        role="region"
        aria-label="Deployment sets toolbar"
      >
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            className="pl-9"
            placeholder="Search by name, description, or tag…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search deployment sets"
          />
        </div>
        <Button onClick={() => setCreateOpen(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          New Deployment Set
        </Button>
      </div>

      {/* Content area */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-52 w-full rounded-lg" />
          ))}
        </div>
      ) : filteredSets.length === 0 ? (
        sets.length === 0 ? (
          <EmptyState
            icon={Layers3}
            title="No deployment sets yet"
            description="Create your first deployment set to batch-deploy artifacts to a project in one click."
            action={
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                Create Deployment Set
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={PackageSearch}
            title="No matching deployment sets"
            description="Try adjusting your search query."
          />
        )
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredSets.map((set) => (
            <DeploymentSetCard
              key={set.id}
              set={set}
              onEdit={setEditingSet}
              onDelete={setDeletingSet}
              onClone={handleClone}
              onDeploy={setDeployingSet}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <CreateDeploymentSetDialog open={createOpen} onOpenChange={setCreateOpen} />

      <EditDeploymentSetDialog
        open={!!editingSet}
        onOpenChange={(open) => !open && setEditingSet(null)}
        set={editingSet}
      />

      {deployingSet && (
        <BatchDeployModal
          setId={deployingSet.id}
          setName={deployingSet.name}
          open={!!deployingSet}
          onOpenChange={(open) => !open && setDeployingSet(null)}
        />
      )}

      <AlertDialog open={!!deletingSet} onOpenChange={(open) => !open && setDeletingSet(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete deployment set?</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingSet
                ? `This permanently deletes "${deletingSet.name}" and all its members. Artifacts themselves are not deleted.`
                : 'This permanently deletes the deployment set and all its members.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteSet.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleteSet.isPending}>
              {deleteSet.isPending ? 'Deleting…' : 'Delete Set'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
