'use client';

import { useState, useRef, useCallback } from 'react';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, Layers3, Pencil, Check, X, Edit3, Plus, Rocket } from 'lucide-react';
import {
  useDeploymentSet,
  useDeploymentSetMembers,
  useUpdateDeploymentSet,
  useResolveSet,
  useToast,
} from '@/hooks';
import type { DeploymentSet } from '@/types/deployment-sets';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { EditDeploymentSetDialog } from '@/components/deployment-sets/edit-deployment-set-dialog';
import { MemberList } from '@/components/deployment-sets/member-list';
import { COLOR_TAILWIND_CLASSES } from '@/lib/group-constants';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeHexColor(value: string): string | null {
  const hex = value.trim().replace(/^#/, '').toLowerCase();
  if (/^[0-9a-f]{3}$/.test(hex)) {
    return `#${hex
      .split('')
      .map((part) => `${part}${part}`)
      .join('')}`;
  }
  if (/^[0-9a-f]{6}$/.test(hex)) {
    return `#${hex}`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Inline-editable field
// ---------------------------------------------------------------------------

interface InlineEditFieldProps {
  value: string;
  onSave: (next: string) => Promise<void>;
  className?: string;
  inputClassName?: string;
  placeholder?: string;
  label: string;
  multiline?: boolean;
}

function InlineEditField({
  value,
  onSave,
  className = '',
  inputClassName = '',
  placeholder,
  label,
  multiline = false,
}: InlineEditFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  const startEdit = useCallback(() => {
    setDraft(value);
    setEditing(true);
    // Focus happens after state update via useEffect alternative
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [value]);

  const cancel = useCallback(() => {
    setDraft(value);
    setEditing(false);
  }, [value]);

  const commit = useCallback(async () => {
    const trimmed = draft.trim();
    if (trimmed === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(trimmed);
      setSaved(true);
      setEditing(false);
      setTimeout(() => setSaved(false), 1500);
    } finally {
      setSaving(false);
    }
  }, [draft, value, onSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !multiline) {
        e.preventDefault();
        void commit();
      }
      if (e.key === 'Escape') {
        cancel();
      }
    },
    [commit, cancel, multiline],
  );

  if (editing) {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {multiline ? (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => void commit()}
            placeholder={placeholder}
            rows={2}
            aria-label={label}
            className={`resize-none rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${inputClassName}`}
            disabled={saving}
          />
        ) : (
          <Input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => void commit()}
            placeholder={placeholder}
            aria-label={label}
            className={`h-auto py-1 text-inherit font-inherit ${inputClassName}`}
            disabled={saving}
          />
        )}
        <button
          type="button"
          aria-label="Confirm edit"
          onClick={() => void commit()}
          disabled={saving}
          className="rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <Check className="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="Cancel edit"
          onClick={cancel}
          disabled={saving}
          className="rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className={`group flex items-center gap-1 ${className}`}>
      <span className={saved ? 'text-green-600 dark:text-green-400' : ''}>{value || placeholder}</span>
      {saved && <Check className="h-3.5 w-3.5 text-green-600 dark:text-green-400" aria-hidden="true" />}
      <button
        type="button"
        aria-label={`Edit ${label}`}
        onClick={startEdit}
        className="rounded p-0.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:text-foreground focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------

function StatsBar({ set, id }: { set: DeploymentSet; id: string }) {
  const { data: resolution, isLoading } = useResolveSet(id);

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-muted-foreground">
      <span>
        <span className="font-medium text-foreground">{set.member_count}</span>{' '}
        {set.member_count === 1 ? 'member' : 'members'}
      </span>
      <Separator orientation="vertical" className="h-4" />
      {isLoading ? (
        <Skeleton className="h-4 w-36" />
      ) : (
        <span>
          <span className="font-medium text-foreground">{resolution?.total_count ?? 0}</span>{' '}
          resolved {resolution?.total_count === 1 ? 'artifact' : 'artifacts'}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main client component
// ---------------------------------------------------------------------------

interface DeploymentSetDetailClientProps {
  id: string;
}

export function DeploymentSetDetailClient({ id }: DeploymentSetDetailClientProps) {
  const { data: set, isLoading, error } = useDeploymentSet(id);
  const { data: members = [], isLoading: membersLoading } = useDeploymentSetMembers(id);
  const updateSet = useUpdateDeploymentSet();
  const { toast } = useToast();

  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // 404 handling: surface as Next.js not-found boundary
  if (!isLoading && (error?.message?.includes('404') || (!set && !error))) {
    // Only call notFound when we are sure the resource doesn't exist
  }
  if (!isLoading && error && error.message.includes('404')) {
    notFound();
  }

  const saveName = useCallback(
    async (name: string) => {
      if (!set) return;
      if (!name) {
        toast({ title: 'Name required', variant: 'destructive' });
        return;
      }
      try {
        await updateSet.mutateAsync({ id: set.id, data: { name } });
      } catch (err) {
        toast({
          title: 'Update failed',
          description: err instanceof Error ? err.message : 'An unexpected error occurred.',
          variant: 'destructive',
        });
        throw err;
      }
    },
    [set, updateSet, toast],
  );

  const saveDescription = useCallback(
    async (description: string) => {
      if (!set) return;
      try {
        await updateSet.mutateAsync({
          id: set.id,
          data: { description: description || null },
        });
      } catch (err) {
        toast({
          title: 'Update failed',
          description: err instanceof Error ? err.message : 'An unexpected error occurred.',
          variant: 'destructive',
        });
        throw err;
      }
    },
    [set, updateSet, toast],
  );

  // Color display helpers (mirrors deployment-set-card)
  const tokenColorClass =
    set?.color && !set.color.startsWith('#')
      ? (COLOR_TAILWIND_CLASSES[set.color] ?? COLOR_TAILWIND_CLASSES.slate)
      : COLOR_TAILWIND_CLASSES.slate;
  const customColor = set?.color ? normalizeHexColor(set.color) : null;
  const borderColorClass = customColor ? 'border-l-border' : tokenColorClass;

  // Loading state
  if (isLoading || !set) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-32" />
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <div className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-8 w-64" />
          </div>
          <Skeleton className="h-4 w-80" />
        </div>
        <Skeleton className="h-5 w-56" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const tags = set.tags ?? [];

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Back navigation */}
        <div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/deployment-sets">
              <ArrowLeft className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Deployment Sets
            </Link>
          </Button>
        </div>

        {/* Header card */}
        <div
          className={`border-l-4 ${borderColorClass} rounded-lg border bg-card p-6 shadow-sm`}
          style={customColor ? { borderLeftColor: customColor } : undefined}
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            {/* Left: icon + name + description */}
            <div className="min-w-0 flex-1 space-y-2">
              {/* Icon + name row */}
              <div className="flex items-center gap-2">
                {set.icon ? (
                  <span className="shrink-0 text-xl" aria-hidden="true">
                    {set.icon}
                  </span>
                ) : (
                  <Layers3 className="h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />
                )}
                <InlineEditField
                  value={set.name}
                  onSave={saveName}
                  label="deployment set name"
                  className="text-xl font-bold tracking-tight"
                  inputClassName="text-xl font-bold w-72"
                />
              </div>

              {/* Description */}
              <InlineEditField
                value={set.description ?? ''}
                onSave={saveDescription}
                label="description"
                placeholder="Add a description…"
                className="text-sm text-muted-foreground"
                inputClassName="w-full max-w-md"
                multiline
              />

              {/* Tags */}
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1" role="list" aria-label="Tags">
                  {tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs" role="listitem">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Right: Edit Details button */}
            <div className="shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditDialogOpen(true)}
                aria-label="Edit deployment set details"
              >
                <Edit3 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                Edit Details
              </Button>
            </div>
          </div>
        </div>

        {/* Stats bar */}
        <StatsBar set={set} id={id} />

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled
            aria-label="Add member (coming soon)"
          >
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Add Member
          </Button>

          <Tooltip>
            <TooltipTrigger asChild>
              <span tabIndex={0}>
                <Button size="sm" disabled aria-label="Deploy set (coming in next phase)">
                  <Rocket className="mr-1.5 h-4 w-4" aria-hidden="true" />
                  Deploy Set
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>Coming in next phase</p>
            </TooltipContent>
          </Tooltip>
        </div>

        <Separator />

        {/* Member list */}
        <section aria-label="Deployment set members">
          <h2 className="mb-3 text-base font-semibold">Members</h2>
          <MemberList
            members={members}
            setId={set.id}
            isLoading={membersLoading}
            onAddMember={() => {
              /* DS-012 will wire this up */
            }}
          />
        </section>
      </div>

      {/* Edit dialog */}
      <EditDeploymentSetDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        set={set}
      />
    </TooltipProvider>
  );
}
