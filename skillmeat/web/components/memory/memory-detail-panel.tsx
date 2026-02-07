/**
 * MemoryDetailPanel Component
 *
 * Right sidebar panel showing full memory item details, provenance, access
 * stats, and action buttons. Slides in from the right when a memory card is
 * selected.
 *
 * Design spec reference: section 3.10
 */

'use client';

import * as React from 'react';
import { useEffect, useCallback } from 'react';
import {
  ArrowLeft,
  X,
  Pencil,
  Check,
  Ban,
  MoreHorizontal,
  GitMerge,
  Archive,
  ChevronDown,
  Clock,
  FileText,
  GitCommit,
  Hash,
  Activity,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { MemoryTypeBadge } from './memory-type-badge';
import {
  getConfidenceTier,
  getConfidenceBarColor,
  getConfidenceColorClasses,
  formatRelativeTime,
  getStatusDotClass,
  STATUS_DOT_CLASSES,
} from './memory-utils';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemoryDetailPanelProps {
  /** The memory item to display. Null when panel is closed. */
  memory: MemoryItemResponse | null;
  /** Whether the panel is currently visible. */
  isOpen: boolean;
  /** Close the detail panel. */
  onClose: () => void;
  /** Open the edit dialog for this memory. */
  onEdit: (id: string) => void;
  /** Approve (promote) this memory item. */
  onApprove: (id: string) => void;
  /** Reject (deprecate) this memory item. */
  onReject: (id: string) => void;
  /** Open merge dialog for this memory. */
  onMerge: (id: string) => void;
  /** Deprecate this memory item. */
  onDeprecate: (id: string) => void;
  /** Reactivate a deprecated memory item (sets status to candidate). */
  onReactivate?: (id: string) => void;
  /** Set a memory item's status directly (bypasses promote/deprecate flow). */
  onSetStatus?: (id: string, status: MemoryStatus) => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * ConfidenceDisplay -- renders confidence percentage with a colored progress
 * bar styled according to the confidence tier.
 */
function ConfidenceDisplay({ confidence }: { confidence: number }) {
  const tier = getConfidenceTier(confidence);
  const percent = Math.round(confidence * 100);
  const colors = getConfidenceColorClasses(tier);
  const barColor = getConfidenceBarColor(tier);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          Confidence
        </span>
        <span className={cn('text-sm font-semibold', colors.text)}>
          {percent}%
        </span>
      </div>
      <div
        className="relative h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence: ${percent}%`}
      >
        <div
          className={cn('h-full rounded-full transition-all duration-300', barColor)}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/**
 * ProvenanceSection -- collapsible section displaying provenance metadata
 * parsed from the memory item's provenance JSON field.
 */
function ProvenanceSection({
  provenance,
}: {
  provenance?: Record<string, any> | null;
}) {
  const [isOpen, setIsOpen] = React.useState(true);

  if (!provenance || typeof provenance !== 'object') {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Provenance</h3>
        <p className="text-xs text-muted-foreground">
          No provenance data available
        </p>
      </div>
    );
  }

  const fields: { key: string; label: string; icon: React.ElementType }[] = [
    { key: 'source_type', label: 'Source', icon: Activity },
    { key: 'session_id', label: 'Session', icon: Hash },
    { key: 'extracted_at', label: 'Extracted', icon: Clock },
    { key: 'files', label: 'Files', icon: FileText },
    { key: 'commit_sha', label: 'Commit', icon: GitCommit },
  ];

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center justify-between py-1 text-sm font-semibold hover:text-foreground transition-colors"
          aria-expanded={isOpen}
          aria-label="Toggle provenance section"
        >
          Provenance
          <ChevronDown
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform duration-200',
              isOpen && 'rotate-180'
            )}
            aria-hidden="true"
          />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <dl className="mt-2 space-y-2">
          {fields.map(({ key, label, icon: Icon }) => {
            const value = provenance[key];
            if (value === undefined || value === null) return null;

            // Format arrays (e.g., files list)
            const displayValue = Array.isArray(value)
              ? value.join(', ')
              : typeof value === 'string' && key === 'extracted_at'
                ? formatDate(value)
                : typeof value === 'string' && key === 'commit_sha'
                  ? value.slice(0, 7)
                  : String(value);

            return (
              <div key={key} className="flex items-start gap-2">
                <Icon className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <dt className="text-xs font-medium text-muted-foreground">
                    {label}
                  </dt>
                  <dd className="text-sm break-all">{displayValue}</dd>
                </div>
              </div>
            );
          })}

          {/* Render any extra keys not in the known fields list */}
          {Object.entries(provenance)
            .filter(
              ([key]) => !fields.some((f) => f.key === key)
            )
            .map(([key, value]) => {
              if (value === undefined || value === null) return null;
              let displayValue: string;
              if (Array.isArray(value)) {
                // Check if array contains objects
                if (value.length > 0 && typeof value[0] === 'object') {
                  displayValue = JSON.stringify(value, null, 2);
                } else {
                  displayValue = value.join(', ');
                }
              } else if (typeof value === 'object') {
                displayValue = JSON.stringify(value, null, 2);
              } else {
                displayValue = String(value);
              }
              return (
                <div key={key} className="flex items-start gap-2">
                  <Hash className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <dt className="text-xs font-medium text-muted-foreground">
                      {key}
                    </dt>
                    <dd className="text-sm break-all">
                      {displayValue.startsWith('[') || displayValue.startsWith('{') ? (
                        <pre className="text-xs font-mono whitespace-pre-wrap">{displayValue}</pre>
                      ) : (
                        displayValue
                      )}
                    </dd>
                  </div>
                </div>
              );
            })}
        </dl>
      </CollapsibleContent>
    </Collapsible>
  );
}

/** Format an ISO date string into a readable local date/time. */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

/**
 * MemoryDetailPanel -- right sidebar showing full details of a selected
 * memory item.
 *
 * Features:
 * - Slide animation (translate-x) when opening/closing
 * - Escape key closes the panel
 * - Full content display, confidence bar, provenance, access stats
 * - Action buttons: Edit, Approve, Reject, and More menu (Merge, Deprecate)
 *
 * @example
 * ```tsx
 * <MemoryDetailPanel
 *   memory={selectedMemory}
 *   isOpen={!!selectedMemory}
 *   onClose={() => setSelectedMemoryId(null)}
 *   onEdit={handleEdit}
 *   onApprove={handleApprove}
 *   onReject={handleReject}
 *   onMerge={handleMerge}
 *   onDeprecate={handleDeprecate}
 * />
 * ```
 */
/** All possible statuses for the status override dropdown. */
const ALL_STATUSES: MemoryStatus[] = ['candidate', 'active', 'stable', 'deprecated'];

/** Human-readable labels for each status. */
const STATUS_LABELS: Record<MemoryStatus, string> = {
  candidate: 'Candidate',
  active: 'Active',
  stable: 'Stable',
  deprecated: 'Deprecated',
};

export function MemoryDetailPanel({
  memory,
  isOpen,
  onClose,
  onEdit,
  onApprove,
  onReject,
  onMerge,
  onDeprecate,
  onReactivate,
  onSetStatus,
}: MemoryDetailPanelProps) {
  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <aside
      role="complementary"
      aria-label="Memory detail panel"
      className={cn(
        'fixed top-14 right-0 bottom-0 z-30 w-[420px] border-l bg-background',
        'flex flex-col shadow-lg',
        'transform transition-transform duration-200 ease-out',
        isOpen ? 'translate-x-0' : 'translate-x-full'
      )}
    >
      {/* --------------------------------------------------------------- */}
      {/* Header                                                          */}
      {/* --------------------------------------------------------------- */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClose}
            aria-label="Back to list"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </Button>
          <h2 className="text-sm font-semibold">Memory Detail</h2>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onClose}
          aria-label="Close detail panel"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      {/* --------------------------------------------------------------- */}
      {/* Scrollable Content                                              */}
      {/* --------------------------------------------------------------- */}
      {memory ? (
        <>
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-6 px-4 py-4">
              {/* Type + Status badges */}
              <div className="flex items-center gap-2">
                <MemoryTypeBadge type={memory.type} />
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5',
                    'text-[10px] font-medium uppercase tracking-wider',
                    'border bg-background'
                  )}
                >
                  <span
                    className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      getStatusDotClass(memory.status)
                    )}
                    aria-hidden="true"
                  />
                  {memory.status}
                </span>
              </div>

              {/* Content */}
              <div>
                <h3 className="mb-2 text-sm font-semibold">Content</h3>
                <div className="rounded-md border bg-muted/30 p-3">
                  <p className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed">
                    {memory.content}
                  </p>
                </div>
              </div>

              {/* Confidence */}
              <ConfidenceDisplay confidence={memory.confidence} />

              {/* Provenance */}
              <div className="border-t pt-4">
                <ProvenanceSection provenance={memory.provenance} />
              </div>

              {/* Access Stats */}
              <div className="border-t pt-4">
                <h3 className="mb-2 text-sm font-semibold">Access Stats</h3>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>
                    Used{' '}
                    <span className="font-medium text-foreground">
                      {memory.access_count ?? 0}
                    </span>{' '}
                    {(memory.access_count ?? 0) === 1 ? 'time' : 'times'}
                  </span>
                  {memory.updated_at && (
                    <>
                      <span className="text-border">|</span>
                      <span>
                        Last:{' '}
                        <span className="font-medium text-foreground">
                          {formatRelativeTime(memory.updated_at)}
                        </span>
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Timestamps */}
              <div className="border-t pt-4">
                <h3 className="mb-2 text-sm font-semibold">Timestamps</h3>
                <div className="space-y-1 text-xs text-muted-foreground">
                  {memory.created_at && (
                    <p>
                      Created:{' '}
                      <span className="text-foreground">
                        {formatDate(memory.created_at)}
                      </span>
                    </p>
                  )}
                  {memory.updated_at && (
                    <p>
                      Updated:{' '}
                      <span className="text-foreground">
                        {formatDate(memory.updated_at)}
                      </span>
                    </p>
                  )}
                  {memory.deprecated_at && (
                    <p>
                      Deprecated:{' '}
                      <span className="text-foreground">
                        {formatDate(memory.deprecated_at)}
                      </span>
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* --------------------------------------------------------------- */}
          {/* Footer Actions                                                  */}
          {/* --------------------------------------------------------------- */}
          <div className="border-t px-4 py-3">
            <TooltipProvider delayDuration={300}>
              <div className="flex items-center gap-2">
                {/* Edit -- always visible */}
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => onEdit(memory.id)}
                >
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                  Edit
                </Button>

                {/* --------------------------------------------------------- */}
                {/* Status-aware primary action with split-button dropdown     */}
                {/* --------------------------------------------------------- */}
                {memory.status === 'candidate' && (
                  <div className="flex items-center">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          className="gap-1.5 rounded-r-none border-r border-r-primary-foreground/30"
                          onClick={() => onApprove(memory.id)}
                        >
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                          Approve
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Promote to active</TooltipContent>
                    </Tooltip>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          size="sm"
                          className="rounded-l-none px-1.5"
                          aria-label="Set status directly"
                        >
                          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                          Set status directly
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {ALL_STATUSES.map((s) => (
                          <DropdownMenuItem
                            key={s}
                            disabled={s === memory.status}
                            onClick={() => onSetStatus?.(memory.id, s)}
                          >
                            <span
                              className={cn('mr-2 h-2 w-2 rounded-full', STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400')}
                              aria-hidden="true"
                            />
                            {STATUS_LABELS[s]}
                            {s === memory.status && (
                              <Check className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                            )}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                )}

                {memory.status === 'active' && (
                  <div className="flex items-center">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          className="gap-1.5 rounded-r-none border-r border-r-primary-foreground/30 bg-blue-600 hover:bg-blue-700 text-white"
                          onClick={() => onApprove(memory.id)}
                        >
                          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                          Mark Stable
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Promote to stable</TooltipContent>
                    </Tooltip>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          size="sm"
                          className="rounded-l-none px-1.5 bg-blue-600 hover:bg-blue-700 text-white"
                          aria-label="Set status directly"
                        >
                          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                          Set status directly
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {ALL_STATUSES.map((s) => (
                          <DropdownMenuItem
                            key={s}
                            disabled={s === memory.status}
                            onClick={() => onSetStatus?.(memory.id, s)}
                          >
                            <span
                              className={cn('mr-2 h-2 w-2 rounded-full', STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400')}
                              aria-hidden="true"
                            />
                            {STATUS_LABELS[s]}
                            {s === memory.status && (
                              <Check className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                            )}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                )}

                {memory.status === 'deprecated' && onReactivate && (
                  <div className="flex items-center">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          className="gap-1.5 rounded-r-none border-r border-r-amber-700/30 bg-amber-600 hover:bg-amber-700 text-white"
                          onClick={() => onReactivate(memory.id)}
                        >
                          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                          Reactivate
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Reactivate as candidate</TooltipContent>
                    </Tooltip>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          size="sm"
                          className="rounded-l-none px-1.5 bg-amber-600 hover:bg-amber-700 text-white"
                          aria-label="Set status directly"
                        >
                          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                          Set status directly
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {ALL_STATUSES.map((s) => (
                          <DropdownMenuItem
                            key={s}
                            disabled={s === memory.status}
                            onClick={() => onSetStatus?.(memory.id, s)}
                          >
                            <span
                              className={cn('mr-2 h-2 w-2 rounded-full', STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400')}
                              aria-hidden="true"
                            />
                            {STATUS_LABELS[s]}
                            {s === memory.status && (
                              <Check className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                            )}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                )}

                {/* stable: no primary action, only split-button for override */}
                {memory.status === 'stable' && onSetStatus && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5"
                        aria-label="Set status directly"
                      >
                        <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                        Set Status
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                        Set status directly
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {ALL_STATUSES.map((s) => (
                        <DropdownMenuItem
                          key={s}
                          disabled={s === memory.status}
                          onClick={() => onSetStatus(memory.id, s)}
                        >
                          <span
                            className={cn('mr-2 h-2 w-2 rounded-full', STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400')}
                            aria-hidden="true"
                          />
                          {STATUS_LABELS[s]}
                          {s === memory.status && (
                            <Check className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                          )}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}

                {/* --------------------------------------------------------- */}
                {/* Secondary actions: Reject (candidate only)                */}
                {/* --------------------------------------------------------- */}
                {memory.status === 'candidate' && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5 text-destructive hover:text-destructive"
                        onClick={() => onReject(memory.id)}
                      >
                        <Ban className="h-3.5 w-3.5" aria-hidden="true" />
                        Reject
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Deprecate this candidate</TooltipContent>
                  </Tooltip>
                )}

                {/* More menu (Merge + Deprecate, when applicable) */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="ml-auto h-8 w-8"
                      aria-label="More actions"
                    >
                      <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {memory.status !== 'deprecated' && (
                      <DropdownMenuItem onClick={() => onMerge(memory.id)}>
                        <GitMerge className="mr-2 h-4 w-4" aria-hidden="true" />
                        Merge
                      </DropdownMenuItem>
                    )}
                    {memory.status !== 'deprecated' && (
                      <DropdownMenuItem onClick={() => onDeprecate(memory.id)}>
                        <Archive className="mr-2 h-4 w-4" aria-hidden="true" />
                        Deprecate
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </TooltipProvider>
          </div>
        </>
      ) : (
        /* Empty state when panel is open but no memory loaded */
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            Select a memory to view details
          </p>
        </div>
      )}
    </aside>
  );
}
