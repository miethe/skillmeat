/**
 * MemoryDetailsModal Component
 *
 * Full tabbed modal for viewing and managing a memory item. Uses BaseMemoryModal
 * as the structural foundation and provides 5 tabs: Overview, Provenance,
 * Contexts, Anchors, and Activity.
 *
 * Footer actions are persistent across all tabs, matching the patterns from
 * MemoryDetailPanel (edit, status-aware primary action, reject, more menu).
 *
 * @example
 * ```tsx
 * <MemoryDetailsModal
 *   memory={selectedMemory}
 *   open={!!selectedMemory}
 *   onClose={() => setSelected(null)}
 *   projectId={projectId}
 *   onEdit={handleEdit}
 *   onApprove={handleApprove}
 *   onReject={handleReject}
 *   onMerge={handleMerge}
 *   onDeprecate={handleDeprecate}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import {
  Info,
  GitCommit,
  Layers,
  Anchor,
  Activity,
  FileText,
  Hash,
  Pencil,
  Check,
  Ban,
  MoreHorizontal,
  GitMerge,
  Archive,
  ChevronDown,
  ShieldCheck,
  RotateCcw,
  Trash2,
  Globe,
  Lock,
  CalendarDays,
} from 'lucide-react';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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

import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import { BaseMemoryModal } from './base-memory-modal';
import { MemoryTypeBadge } from './memory-type-badge';
import { useContextModules } from '@/hooks';
import {
  getConfidenceTier,
  getConfidenceBarColor,
  getConfidenceColorClasses,
  formatRelativeTime,
  getStatusDotClass,
  STATUS_DOT_CLASSES,
} from './memory-utils';
import type { Tab } from '@/components/shared/tab-navigation';

// ============================================================================
// Types
// ============================================================================

export type MemoryDetailsTab =
  | 'overview'
  | 'provenance'
  | 'contexts'
  | 'anchors'
  | 'activity';

export interface MemoryDetailsModalProps {
  /** The memory item to display. Null when modal should not render content. */
  memory: MemoryItemResponse | null;
  /** Whether the modal is open. */
  open: boolean;
  /** Close handler. */
  onClose: () => void;
  /** Initial tab to display (default: 'overview'). */
  initialTab?: MemoryDetailsTab;
  /** Project ID for context module queries. */
  projectId: string;
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
  /** Delete a memory item permanently. */
  onDelete?: (id: string) => void;
}

// ============================================================================
// Constants
// ============================================================================

/** All possible statuses for the status override dropdown. */
const ALL_STATUSES: MemoryStatus[] = [
  'candidate',
  'active',
  'stable',
  'deprecated',
];

/** Human-readable labels for each status. */
const STATUS_LABELS: Record<MemoryStatus, string> = {
  candidate: 'Candidate',
  active: 'Active',
  stable: 'Stable',
  deprecated: 'Deprecated',
};

/** Tab definitions for the modal. */
const TABS: Tab[] = [
  { value: 'overview', label: 'Overview', icon: Info },
  { value: 'provenance', label: 'Provenance', icon: GitCommit },
  { value: 'contexts', label: 'Contexts', icon: Layers },
  { value: 'anchors', label: 'Anchors', icon: Anchor },
  { value: 'activity', label: 'Activity', icon: Activity },
];

const ANCHOR_TYPE_ORDER: Record<string, number> = {
  code: 0,
  test: 1,
  doc: 2,
  config: 3,
  plan: 4,
};

const ANCHOR_TYPE_BADGE_CLASS: Record<string, string> = {
  code: 'bg-blue-100 text-blue-800 border-blue-200',
  test: 'bg-green-100 text-green-800 border-green-200',
  doc: 'bg-violet-100 text-violet-800 border-violet-200',
  config: 'bg-orange-100 text-orange-800 border-orange-200',
  plan: 'bg-teal-100 text-teal-800 border-teal-200',
};

type AnchorEntry = {
  path: string;
  type: 'code' | 'test' | 'doc' | 'config' | 'plan';
  line_start?: number;
  line_end?: number;
  commit_sha?: string;
  description?: string;
};

function normalizeAnchor(raw: unknown): AnchorEntry | null {
  if (typeof raw === 'string') {
    const path = raw.trim();
    if (!path) return null;
    return { path, type: 'code' };
  }

  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const record = raw as Record<string, unknown>;
  const path = typeof record.path === 'string' ? record.path.trim() : '';
  if (!path) return null;

  const rawType = typeof record.type === 'string' ? record.type : 'code';
  const type: AnchorEntry['type'] = (['code', 'test', 'doc', 'config', 'plan'].includes(rawType)
    ? rawType
    : 'code') as AnchorEntry['type'];

  const lineStart =
    typeof record.line_start === 'number' && Number.isInteger(record.line_start)
      ? record.line_start
      : undefined;
  const lineEnd =
    typeof record.line_end === 'number' && Number.isInteger(record.line_end)
      ? record.line_end
      : undefined;
  const commitSha =
    typeof record.commit_sha === 'string' && record.commit_sha.trim()
      ? record.commit_sha.trim()
      : undefined;
  const description =
    typeof record.description === 'string' && record.description.trim()
      ? record.description.trim()
      : undefined;

  return {
    path,
    type,
    line_start: lineStart,
    line_end: lineEnd,
    commit_sha: commitSha,
    description,
  };
}

// ============================================================================
// Sub-components
// ============================================================================

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
          className={cn(
            'h-full rounded-full transition-all duration-300',
            barColor
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
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

/**
 * ProvenanceContent -- full-width provenance display for the Provenance tab.
 * Unlike the detail panel variant, this does not use a Collapsible wrapper
 * since it occupies its own dedicated tab.
 */
function ProvenanceContent({
  memory,
  provenance,
}: {
  memory: MemoryItemResponse;
  provenance?: Record<string, any> | null;
}) {
  const provenanceObject =
    provenance && typeof provenance === 'object' ? provenance : {};
  const promotedFields: { key: string; label: string; icon: React.ElementType; value: unknown }[] = [
    {
      key: 'source_type',
      label: 'Source Type',
      icon: Activity,
      value: memory.source_type ?? provenanceObject.source_type,
    },
    {
      key: 'git_branch',
      label: 'Git Branch',
      icon: GitCommit,
      value: memory.git_branch ?? provenanceObject.git_branch,
    },
    {
      key: 'git_commit',
      label: 'Git Commit',
      icon: GitCommit,
      value: memory.git_commit ?? provenanceObject.git_commit ?? provenanceObject.commit_sha,
    },
    {
      key: 'session_id',
      label: 'Session ID',
      icon: Hash,
      value: memory.session_id ?? provenanceObject.session_id,
    },
    {
      key: 'agent_type',
      label: 'Agent Type',
      icon: Activity,
      value: memory.agent_type ?? provenanceObject.agent_type,
    },
    {
      key: 'model',
      label: 'Model',
      icon: Layers,
      value: memory.model ?? provenanceObject.model,
    },
  ];
  const visiblePromoted = promotedFields.filter(
    (field) => field.value !== undefined && field.value !== null && String(field.value).trim() !== ''
  );

  if (!visiblePromoted.length && Object.keys(provenanceObject).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Hash className="mb-2 h-8 w-8 opacity-40" aria-hidden="true" />
        <p className="text-sm">No provenance data available</p>
      </div>
    );
  }
  const promotedKeys = new Set([
    'source_type',
    'git_branch',
    'git_commit',
    'commit_sha',
    'session_id',
    'agent_type',
    'model',
  ]);

  return (
    <div className="space-y-6">
      {!!visiblePromoted.length && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {visiblePromoted.map(({ key, label, icon: Icon, value }) => {
            const displayValue =
              Array.isArray(value)
                ? value.join(', ')
                : typeof value === 'string' && (key === 'git_commit' || key === 'commit_sha')
                  ? value.slice(0, 7)
                  : String(value);

            return (
              <div key={key} className="rounded-md border bg-muted/30 p-3">
                <div className="mb-1 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {label}
                </div>
                <div className="break-all text-sm">{displayValue}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Extra keys not in known fields list */}
      {Object.entries(provenanceObject).filter(
        ([key]) => !promotedKeys.has(key) && key !== 'llm_reasoning'
      ).length > 0 && (
        <details className="rounded-md border p-3">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Additional Data
          </summary>
          <dl className="mt-3 space-y-3">
            {Object.entries(provenanceObject)
              .filter(([key]) => !promotedKeys.has(key) && key !== 'llm_reasoning')
              .map(([key, value]) => {
                if (value === undefined || value === null) return null;
                const displayValue =
                  typeof value === 'object'
                    ? JSON.stringify(value, null, 2)
                    : String(value);
                return (
                  <div key={key} className="flex items-start gap-3">
                    <Hash
                      className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <dt className="text-xs font-medium text-muted-foreground">
                        {key}
                      </dt>
                      <dd className="text-sm break-all">
                        {displayValue.startsWith('[') || displayValue.startsWith('{') ? (
                          <pre className="whitespace-pre-wrap font-mono text-xs">
                            {displayValue}
                          </pre>
                        ) : (
                          displayValue
                        )}
                      </dd>
                    </div>
                  </div>
                );
              })}
          </dl>
        </details>
      )}

      {/* LLM Reasoning */}
      {provenanceObject.llm_reasoning && (
        <div className="border-t pt-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            LLM Reasoning
          </h4>
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
              {String(provenanceObject.llm_reasoning)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * MemoryDetailsModal -- full tabbed modal for viewing and managing a memory
 * item with 5 tabs: Overview, Provenance, Contexts, Anchors, and Activity.
 *
 * Uses BaseMemoryModal for structural foundation. Footer actions persist
 * across all tabs via the `footer` prop on BaseMemoryModal.
 */
export function MemoryDetailsModal({
  memory,
  open,
  onClose,
  initialTab = 'overview',
  projectId,
  onEdit,
  onApprove,
  onReject,
  onMerge,
  onDeprecate,
  onReactivate,
  onSetStatus,
  onDelete,
}: MemoryDetailsModalProps) {
  const [activeTab, setActiveTab] = React.useState<string>(initialTab);

  // Reset tab when a different memory is selected
  const memoryId = memory?.id;
  React.useEffect(() => {
    if (memoryId) {
      setActiveTab(initialTab);
    }
  }, [memoryId, initialTab]);

  // Fetch context modules for the Contexts tab
  const { data: modulesData, isLoading: modulesLoading } = useContextModules(
    projectId
  );

  // Don't render the modal internals if no memory is provided
  if (!memory) {
    return null;
  }

  const normalizedAnchors = (memory.anchors ?? [])
    .map((anchor) => normalizeAnchor(anchor))
    .filter((anchor): anchor is AnchorEntry => anchor !== null)
    .sort((a, b) => {
      const left = ANCHOR_TYPE_ORDER[a.type] ?? 99;
      const right = ANCHOR_TYPE_ORDER[b.type] ?? 99;
      if (left !== right) return left - right;
      return a.path.localeCompare(b.path);
    });
  const anchorCount = normalizedAnchors.length;

  const tabs = React.useMemo(
    () =>
      TABS.map((tab) =>
        tab.value === 'anchors'
          ? { ...tab, label: `Anchors (${anchorCount})` }
          : tab
      ),
    [anchorCount]
  );

  // Header actions: MemoryTypeBadge + status badge
  const headerActions = (
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
  );

  // -----------------------------------------------------------------------
  // Footer actions (persistent across all tabs)
  // -----------------------------------------------------------------------
  const footer = (
    <div className="border-t px-6 py-3">
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
                    <ChevronDown
                      className="h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    disabled
                    className="text-xs text-muted-foreground"
                  >
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
                        className={cn(
                          'mr-2 h-2 w-2 rounded-full',
                          STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400'
                        )}
                        aria-hidden="true"
                      />
                      {STATUS_LABELS[s]}
                      {s === memory.status && (
                        <Check
                          className="ml-auto h-3.5 w-3.5 text-muted-foreground"
                          aria-hidden="true"
                        />
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
                    className="gap-1.5 rounded-r-none border-r border-r-primary-foreground/30 bg-blue-600 text-white hover:bg-blue-700"
                    onClick={() => onApprove(memory.id)}
                  >
                    <ShieldCheck
                      className="h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                    Mark Stable
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Promote to stable</TooltipContent>
              </Tooltip>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    size="sm"
                    className="rounded-l-none px-1.5 bg-blue-600 text-white hover:bg-blue-700"
                    aria-label="Set status directly"
                  >
                    <ChevronDown
                      className="h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    disabled
                    className="text-xs text-muted-foreground"
                  >
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
                        className={cn(
                          'mr-2 h-2 w-2 rounded-full',
                          STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400'
                        )}
                        aria-hidden="true"
                      />
                      {STATUS_LABELS[s]}
                      {s === memory.status && (
                        <Check
                          className="ml-auto h-3.5 w-3.5 text-muted-foreground"
                          aria-hidden="true"
                        />
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
                    className="gap-1.5 rounded-r-none border-r border-r-amber-700/30 bg-amber-600 text-white hover:bg-amber-700"
                    onClick={() => onReactivate(memory.id)}
                  >
                    <RotateCcw
                      className="h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                    Reactivate
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reactivate as candidate</TooltipContent>
              </Tooltip>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    size="sm"
                    className="rounded-l-none px-1.5 bg-amber-600 text-white hover:bg-amber-700"
                    aria-label="Set status directly"
                  >
                    <ChevronDown
                      className="h-3.5 w-3.5"
                      aria-hidden="true"
                    />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    disabled
                    className="text-xs text-muted-foreground"
                  >
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
                        className={cn(
                          'mr-2 h-2 w-2 rounded-full',
                          STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400'
                        )}
                        aria-hidden="true"
                      />
                      {STATUS_LABELS[s]}
                      {s === memory.status && (
                        <Check
                          className="ml-auto h-3.5 w-3.5 text-muted-foreground"
                          aria-hidden="true"
                        />
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
                <DropdownMenuItem
                  disabled
                  className="text-xs text-muted-foreground"
                >
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
                      className={cn(
                        'mr-2 h-2 w-2 rounded-full',
                        STATUS_DOT_CLASSES[s] ?? 'bg-zinc-400'
                      )}
                      aria-hidden="true"
                    />
                    {STATUS_LABELS[s]}
                    {s === memory.status && (
                      <Check
                        className="ml-auto h-3.5 w-3.5 text-muted-foreground"
                        aria-hidden="true"
                      />
                    )}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {/* Reject (candidate only) */}
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

          {/* More menu (Merge + Deprecate + Delete, when applicable) */}
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
              {onDelete && (
                <>
                  {memory.status !== 'deprecated' && <DropdownMenuSeparator />}
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => onDelete(memory.id)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </TooltipProvider>
    </div>
  );

  // -----------------------------------------------------------------------
  // Tab: Overview
  // -----------------------------------------------------------------------
  const overviewTab = (
    <TabContentWrapper value="overview">
      <div className="space-y-6">
        {/* Full content */}
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

        {/* Status */}
        <div>
          <h3 className="mb-2 text-sm font-semibold">Status</h3>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1',
                'text-xs font-medium capitalize',
                'border bg-background'
              )}
            >
              <span
                className={cn(
                  'h-2 w-2 rounded-full',
                  getStatusDotClass(memory.status)
                )}
                aria-hidden="true"
              />
              {memory.status}
            </span>
          </div>
        </div>

        {/* Share Scope */}
        <div>
          <h3 className="mb-2 text-sm font-semibold">Share Scope</h3>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {memory.share_scope === 'global' ? (
              <Globe className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Lock className="h-4 w-4" aria-hidden="true" />
            )}
            <span className="capitalize">{memory.share_scope}</span>
          </div>
        </div>

        {/* Memory Type */}
        <div>
          <h3 className="mb-2 text-sm font-semibold">Type</h3>
          <MemoryTypeBadge type={memory.type} />
        </div>

        {/* TTL Policy */}
        {memory.ttl_policy && (
          <div>
            <h3 className="mb-2 text-sm font-semibold">TTL Policy</h3>
            <div className="space-y-1 text-sm text-muted-foreground">
              {memory.ttl_policy.revalidate_days != null && (
                <div className="flex items-center gap-2">
                  <CalendarDays
                    className="h-3.5 w-3.5"
                    aria-hidden="true"
                  />
                  <span>
                    Revalidate every{' '}
                    <span className="font-medium text-foreground">
                      {memory.ttl_policy.revalidate_days}
                    </span>{' '}
                    days
                  </span>
                </div>
              )}
              {memory.ttl_policy.deprecate_days != null && (
                <div className="flex items-center gap-2">
                  <Archive className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>
                    Deprecate after{' '}
                    <span className="font-medium text-foreground">
                      {memory.ttl_policy.deprecate_days}
                    </span>{' '}
                    days
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Content Hash */}
        {memory.content_hash && (
          <div>
            <h3 className="mb-2 text-sm font-semibold">Content Hash</h3>
            <code className="rounded bg-muted px-2 py-1 font-mono text-xs">
              {memory.content_hash.slice(0, 12)}
            </code>
          </div>
        )}
      </div>
    </TabContentWrapper>
  );

  // -----------------------------------------------------------------------
  // Tab: Provenance
  // -----------------------------------------------------------------------
  const provenanceTab = (
    <TabContentWrapper value="provenance">
      <ProvenanceContent memory={memory} provenance={memory.provenance} />
    </TabContentWrapper>
  );

  // -----------------------------------------------------------------------
  // Tab: Contexts
  // -----------------------------------------------------------------------
  const modules = modulesData?.items ?? [];
  const contextsTab = (
    <TabContentWrapper value="contexts">
      {modulesLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-sm text-muted-foreground">
            Loading context modules...
          </p>
        </div>
      ) : modules.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Layers className="mb-2 h-8 w-8 opacity-40" aria-hidden="true" />
          <p className="text-sm">No context modules in this project</p>
          <p className="mt-1 text-xs">
            Context modules group related memories for assembly into knowledge
            packs.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {modules.map((mod) => (
            <div
              key={mod.id}
              className="rounded-lg border p-4 transition-colors hover:bg-muted/50"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-medium">{mod.name}</h4>
                  {mod.description && (
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                      {mod.description}
                    </p>
                  )}
                </div>
                {mod.priority != null && (
                  <Badge variant="secondary" className="flex-shrink-0 text-xs">
                    P{mod.priority}
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </TabContentWrapper>
  );

  // -----------------------------------------------------------------------
  // Tab: Anchors
  // -----------------------------------------------------------------------
  const anchorsTab = (
    <TabContentWrapper value="anchors">
      {anchorCount === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Anchor className="mb-2 h-8 w-8 opacity-40" aria-hidden="true" />
          <p className="text-sm">No anchors</p>
          <p className="mt-1 text-xs">
            File anchors link this memory to specific source files.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {normalizedAnchors.map((anchor, idx) => {
            const lineRange =
              anchor.line_start != null
                ? anchor.line_end != null
                  ? `L${anchor.line_start}-${anchor.line_end}`
                  : `L${anchor.line_start}`
                : null;
            return (
            <div
              key={idx}
              className="space-y-2 rounded-md border px-3 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant="outline"
                  className={cn(
                    'capitalize',
                    ANCHOR_TYPE_BADGE_CLASS[anchor.type] ?? ANCHOR_TYPE_BADGE_CLASS.code
                  )}
                >
                  {anchor.type}
                </Badge>
                {lineRange && (
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    {lineRange}
                  </Badge>
                )}
                {anchor.commit_sha && (
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    {anchor.commit_sha.slice(0, 7)}
                  </Badge>
                )}
              </div>
              <div className="flex items-start gap-2">
                <FileText
                  className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1 break-all font-mono text-sm">
                  {anchor.path}
                </span>
              </div>
              {anchor.description && (
                <p className="text-sm text-muted-foreground">{anchor.description}</p>
              )}
            </div>
            );
          })}
        </div>
      )}
    </TabContentWrapper>
  );

  // -----------------------------------------------------------------------
  // Tab: Activity
  // -----------------------------------------------------------------------
  const activityTab = (
    <TabContentWrapper value="activity">
      <div className="space-y-6">
        {/* Access Stats */}
        <div>
          <h3 className="mb-3 text-sm font-semibold">Access Stats</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-md border p-3">
              <p className="text-xs text-muted-foreground">Access Count</p>
              <p className="mt-1 text-2xl font-semibold">
                {memory.access_count ?? 0}
              </p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs text-muted-foreground">Last Accessed</p>
              <p className="mt-1 text-sm font-medium">
                {memory.updated_at
                  ? formatRelativeTime(memory.updated_at)
                  : 'Never'}
              </p>
            </div>
          </div>
        </div>

        {/* Timestamps */}
        <div>
          <h3 className="mb-3 text-sm font-semibold">Timestamps</h3>
          <div className="space-y-2 text-sm">
            {memory.created_at && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDate(memory.created_at)}</span>
              </div>
            )}
            {memory.updated_at && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Updated</span>
                <span>{formatDate(memory.updated_at)}</span>
              </div>
            )}
            {memory.deprecated_at && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Deprecated</span>
                <span>{formatDate(memory.deprecated_at)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Lifecycle Timeline */}
        <div>
          <h3 className="mb-3 text-sm font-semibold">Lifecycle</h3>
          <div className="relative ml-3 space-y-0">
            {/* Vertical line */}
            <div className="absolute left-[5px] top-2 bottom-2 w-px bg-border" />

            {/* Created */}
            {memory.created_at && (
              <div className="relative flex items-start gap-4 pb-6">
                <div
                  className={cn(
                    'relative z-10 mt-1 h-3 w-3 rounded-full border-2 border-background',
                    STATUS_DOT_CLASSES['candidate'] ?? 'bg-zinc-400'
                  )}
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">Created</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(memory.created_at)}
                  </p>
                </div>
              </div>
            )}

            {/* Deprecated (if applicable) */}
            {memory.deprecated_at && (
              <div className="relative flex items-start gap-4 pb-6">
                <div
                  className={cn(
                    'relative z-10 mt-1 h-3 w-3 rounded-full border-2 border-background',
                    STATUS_DOT_CLASSES['deprecated'] ?? 'bg-zinc-400'
                  )}
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">Deprecated</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(memory.deprecated_at)}
                  </p>
                </div>
              </div>
            )}

            {/* Current Status */}
            <div className="relative flex items-start gap-4">
              <div
                className={cn(
                  'relative z-10 mt-1 h-3 w-3 rounded-full border-2 border-background',
                  getStatusDotClass(memory.status)
                )}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium capitalize">
                  {memory.status}
                </p>
                <p className="text-xs text-muted-foreground">Current status</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </TabContentWrapper>
  );

  return (
    <BaseMemoryModal
      memory={memory}
      open={open}
      onClose={onClose}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      tabs={tabs}
      headerActions={headerActions}
      footer={footer}
    >
      {overviewTab}
      {provenanceTab}
      {contextsTab}
      {anchorsTab}
      {activityTab}
    </BaseMemoryModal>
  );
}
