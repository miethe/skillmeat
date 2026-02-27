'use client';

/**
 * ExecutionDetail — right-panel detail view for the workflow execution dashboard.
 *
 * Displays all runtime details for the selected StageExecution:
 *   - Stage header (name, status badge, stage-type indicator)
 *   - Agent & tools section
 *   - Timing grid (started, duration/live counter, ended)
 *   - Context consumed section
 *   - Collapsible Inputs / Outputs sections
 *   - Conditional error callout (failed stages)
 *   - Conditional gate approval panel (gate stages awaiting approval)
 *   - Log viewer slot ({children})
 *
 * Empty state renders when no stage is selected.
 *
 * Accessibility:
 *   - Sections use <section> with aria-labelledby headings
 *   - Approve/Reject buttons carry aria-label with stage name
 *   - Status badge carries aria-label
 *   - Collapsible sections toggle aria-expanded
 *   - Live duration ticks are aria-live="off" (non-disruptive)
 */

import * as React from 'react';
import {
  Bot,
  Clock,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  ShieldQuestion,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Cpu,
  GitMerge,
  Loader2,
  Check,
  X,
  Minus,
  Ban,
  Pause,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { rawToStageType } from '@/types/workflow';
import type { StageExecution, ExecutionStatus, StageType } from '@/types/workflow';

// ============================================================================
// Props
// ============================================================================

export interface ExecutionDetailProps {
  /** The selected stage execution, or null when nothing is selected. */
  stage: StageExecution | null;
  /** Called when the user approves a gate stage. */
  onApproveGate?: (stageId: string) => void;
  /** Called when the user rejects a gate stage. */
  onRejectGate?: (stageId: string, reason?: string) => void;
  /** Slot for the LogViewer component (FE-6.5). Rendered at the bottom of the panel. */
  children?: React.ReactNode;
  /** Additional Tailwind class overrides for the root element. */
  className?: string;
}

// ============================================================================
// Status configuration (mirrors stage-timeline.tsx)
// ============================================================================

const STATUS_CONFIG: Record<
  ExecutionStatus,
  {
    icon: React.ElementType;
    iconClass?: string;
    badgeClass: string;
    label: string;
  }
> = {
  pending: {
    icon: Clock,
    badgeClass:
      'border-muted-foreground/30 bg-muted/50 text-muted-foreground',
    label: 'Pending',
  },
  running: {
    icon: Loader2,
    iconClass: 'animate-spin',
    badgeClass:
      'border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-400',
    label: 'Running',
  },
  completed: {
    icon: Check,
    badgeClass:
      'border-green-500/40 bg-green-500/10 text-green-600 dark:text-green-400',
    label: 'Completed',
  },
  failed: {
    icon: X,
    badgeClass:
      'border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400',
    label: 'Failed',
  },
  cancelled: {
    icon: Ban,
    badgeClass:
      'border-gray-400/40 bg-gray-500/10 text-gray-500 dark:text-gray-400',
    label: 'Cancelled',
  },
  paused: {
    icon: Pause,
    badgeClass:
      'border-yellow-500/40 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400',
    label: 'Paused',
  },
  waiting_for_approval: {
    icon: ShieldQuestion,
    badgeClass:
      'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400',
    label: 'Waiting Gate',
  },
};

// ============================================================================
// Stage type configuration
// ============================================================================

const STAGE_TYPE_CONFIG: Record<
  StageType,
  { icon: React.ElementType; label: string; badgeClass: string }
> = {
  standard: {
    icon: Cpu,
    label: 'Standard',
    badgeClass: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
  },
  gate: {
    icon: ShieldQuestion,
    label: 'Gate',
    badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  checkpoint: {
    icon: GitMerge,
    label: 'Checkpoint',
    badgeClass: 'border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400',
  },
};

// ============================================================================
// Helpers
// ============================================================================

/**
 * Format milliseconds to a compact human-readable string.
 * E.g. 45000 → "45s", 83000 → "1:23", 3725000 → "1h 2m"
 */
function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) {
    return seconds === 0 ? `${minutes}m` : `${minutes}:${String(seconds).padStart(2, '0')}`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes === 0 ? `${hours}h` : `${hours}h ${remainingMinutes}m`;
}

/**
 * Format an ISO 8601 timestamp to a compact local time string.
 * Returns an em-dash when timestamp is absent.
 */
function formatTime(iso: string | undefined): string {
  if (!iso) return '\u2014';
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Extract an agent name from a "type:name" artifact reference.
 * E.g. "agent:researcher-v1" → "researcher-v1"
 */
function parseAgentName(ref: string | undefined): string {
  if (!ref) return 'Unknown';
  const parts = ref.split(':');
  return parts.length > 1 ? parts.slice(1).join(':') : ref;
}

// ============================================================================
// Sub-components
// ============================================================================

// --------------------------------------------------------------------------
// Section wrapper
// --------------------------------------------------------------------------

interface SectionProps {
  id: string;
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  className?: string;
}

function Section({ id, title, icon: Icon, children, className }: SectionProps) {
  return (
    <section aria-labelledby={id} className={cn('space-y-2', className)}>
      <h3
        id={id}
        className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
      >
        <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {title}
      </h3>
      {children}
    </section>
  );
}

// --------------------------------------------------------------------------
// Collapsible section (Inputs / Outputs)
// --------------------------------------------------------------------------

interface CollapsibleSectionProps {
  id: string;
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  isEmpty: boolean;
  emptyText: string;
  children: React.ReactNode;
}

function CollapsibleSection({
  id,
  title,
  icon: Icon,
  defaultOpen = false,
  isEmpty,
  emptyText,
  children,
}: CollapsibleSectionProps) {
  const [open, setOpen] = React.useState(defaultOpen);

  return (
    <section aria-labelledby={id} className="space-y-1.5">
      <button
        type="button"
        id={id}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={cn(
          'flex w-full items-center gap-1.5 rounded-sm text-[11px] font-semibold uppercase tracking-wider',
          'text-muted-foreground transition-colors hover:text-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
        )}
      >
        {open ? (
          <ChevronDown className="h-3 w-3 shrink-0" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" aria-hidden="true" />
        )}
        <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {title}
      </button>

      {open && (
        <div className="pl-5">
          {isEmpty ? (
            <p className="text-xs text-muted-foreground/60 italic">{emptyText}</p>
          ) : (
            children
          )}
        </div>
      )}
    </section>
  );
}

// --------------------------------------------------------------------------
// Status badge
// --------------------------------------------------------------------------

function StatusBadge({ status }: { status: ExecutionStatus }) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <Badge
      variant="outline"
      className={cn('gap-1.5 pl-1.5 pr-2 py-0.5 text-xs font-medium', cfg.badgeClass)}
      aria-label={`Stage status: ${cfg.label}`}
    >
      <Icon className={cn('h-3 w-3 shrink-0', cfg.iconClass)} aria-hidden="true" />
      {cfg.label}
    </Badge>
  );
}

// --------------------------------------------------------------------------
// Stage type badge
// --------------------------------------------------------------------------

function StageTypeBadge({ stageType }: { stageType: StageType }) {
  const cfg = STAGE_TYPE_CONFIG[stageType];
  const Icon = cfg.icon;
  return (
    <Badge
      variant="outline"
      className={cn('gap-1 pl-1.5 pr-2 py-0.5 text-[10px] font-medium', cfg.badgeClass)}
      aria-label={`Stage type: ${cfg.label}`}
    >
      <Icon className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
      {cfg.label}
    </Badge>
  );
}

// --------------------------------------------------------------------------
// Live duration counter
// --------------------------------------------------------------------------

function LiveDuration({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = React.useState(() =>
    Math.max(0, Date.now() - new Date(startedAt).getTime())
  );

  React.useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.max(0, Date.now() - new Date(startedAt).getTime()));
    }, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return (
    <span aria-live="off" aria-atomic="true">
      {formatDuration(elapsed)}
    </span>
  );
}

// --------------------------------------------------------------------------
// Definition list row
// --------------------------------------------------------------------------

interface DefRowProps {
  label: string;
  children: React.ReactNode;
}

function DefRow({ label, children }: DefRowProps) {
  return (
    <div className="grid grid-cols-[6rem_1fr] gap-x-2 text-xs">
      <dt className="text-muted-foreground font-medium truncate">{label}</dt>
      <dd className="text-foreground font-mono truncate">{children}</dd>
    </div>
  );
}

// --------------------------------------------------------------------------
// JSON / key-value output renderer
// --------------------------------------------------------------------------

interface DataBlockProps {
  data: Record<string, unknown>;
}

function DataBlock({ data }: DataBlockProps) {
  const keys = Object.keys(data);
  if (keys.length === 0) return null;

  return (
    <div className="rounded-md border border-border bg-muted/40 text-xs font-mono overflow-x-auto">
      <pre className="p-3 whitespace-pre-wrap break-words text-[11px] leading-relaxed">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

// ============================================================================
// Empty state
// ============================================================================

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
      <Minus className="h-8 w-8 text-muted-foreground/30" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">Select a stage to view details</p>
    </div>
  );
}

// ============================================================================
// ExecutionDetail — main component
// ============================================================================

/**
 * ExecutionDetail — right-panel detail view for the execution dashboard.
 *
 * Shows all runtime metadata for the selected StageExecution. When no stage
 * is selected, renders a centred empty state.
 *
 * The `children` prop provides a slot for the LogViewer (FE-6.5) which will
 * be integrated after the bottom divider.
 */
export function ExecutionDetail({
  stage,
  onApproveGate,
  onRejectGate,
  children,
  className,
}: ExecutionDetailProps) {
  if (!stage) {
    return (
      <div
        className={cn(
          'flex h-full flex-col rounded-lg border border-border bg-card',
          className
        )}
        aria-label="Stage detail panel"
      >
        <EmptyState />
      </div>
    );
  }

  const stageType = rawToStageType(stage.stageType);
  const agentName = parseAgentName(stage.agentUsed);
  const isRunning = stage.status === 'running';
  const isGateWaiting = stageType === 'gate' && stage.status === 'waiting_for_approval';
  const hasError = stage.status === 'failed' && !!stage.errorMessage;
  const hasOutputs = Object.keys(stage.outputs).length > 0;

  // Determine if durationMs is a final value or if we should use a live counter
  const hasFinalDuration = stage.durationMs != null && stage.durationMs > 0;
  const showLiveDuration = isRunning && !!stage.startedAt && !hasFinalDuration;

  return (
    <div
      className={cn(
        'flex h-full flex-col rounded-lg border border-border bg-card',
        className
      )}
      aria-label={`Stage detail: ${stage.stageName}`}
    >
      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-5 p-4">

          {/* ================================================================ */}
          {/* Stage header                                                     */}
          {/* ================================================================ */}
          <div className="space-y-2">
            {/* Name + type + status */}
            <div className="flex flex-wrap items-start gap-2">
              <h2 className="flex-1 min-w-0 text-base font-semibold leading-tight text-foreground break-words">
                {stage.stageName}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <StatusBadge status={stage.status} />
              <StageTypeBadge stageType={stageType} />
            </div>

            {/* Stage ID — muted mono reference */}
            <p className="font-mono text-[10px] text-muted-foreground/60 truncate">
              {stage.stageId}
            </p>
          </div>

          <Separator />

          {/* ================================================================ */}
          {/* Error callout (conditional — failed stages only)                */}
          {/* ================================================================ */}
          {hasError && (
            <div
              role="alert"
              className={cn(
                'flex gap-2.5 rounded-md border border-red-500/30',
                'bg-red-500/8 dark:bg-red-500/10 p-3'
              )}
            >
              <AlertTriangle
                className="mt-0.5 h-4 w-4 shrink-0 text-red-500 dark:text-red-400"
                aria-hidden="true"
              />
              <div className="space-y-0.5 min-w-0">
                <p className="text-xs font-semibold text-red-600 dark:text-red-400">
                  Stage failed
                </p>
                <p className="text-xs text-red-600/80 dark:text-red-400/80 break-words">
                  {stage.errorMessage}
                </p>
              </div>
            </div>
          )}

          {/* ================================================================ */}
          {/* Gate approval panel (conditional)                               */}
          {/* ================================================================ */}
          {isGateWaiting && (
            <div
              className={cn(
                'flex flex-col gap-3 rounded-md border border-amber-500/30',
                'bg-amber-500/8 dark:bg-amber-500/10 p-3'
              )}
              aria-label="Gate approval required"
            >
              <div className="flex items-start gap-2.5">
                <ShieldQuestion
                  className="mt-0.5 h-4 w-4 shrink-0 text-amber-500 dark:text-amber-400"
                  aria-hidden="true"
                />
                <div className="space-y-0.5">
                  <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                    Awaiting approval
                  </p>
                  <p className="text-xs text-amber-600/80 dark:text-amber-400/80">
                    This gate stage requires human sign-off before the workflow continues.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 pl-6" role="group" aria-label="Gate actions">
                <Button
                  size="sm"
                  className={cn(
                    'h-7 gap-1.5 text-xs',
                    'bg-green-600 hover:bg-green-700 text-white dark:bg-green-700 dark:hover:bg-green-600'
                  )}
                  onClick={() => onApproveGate?.(stage.id)}
                  aria-label={`Approve gate: ${stage.stageName}`}
                >
                  <ThumbsUp className="h-3 w-3 shrink-0" aria-hidden="true" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className={cn(
                    'h-7 gap-1.5 text-xs',
                    'border-red-500/40 text-red-600 hover:bg-red-500/10',
                    'dark:text-red-400 dark:border-red-500/30 dark:hover:bg-red-500/10'
                  )}
                  onClick={() => onRejectGate?.(stage.id)}
                  aria-label={`Reject gate: ${stage.stageName}`}
                >
                  <ThumbsDown className="h-3 w-3 shrink-0" aria-hidden="true" />
                  Reject
                </Button>
              </div>
            </div>
          )}

          {/* ================================================================ */}
          {/* Agent & tools                                                    */}
          {/* ================================================================ */}
          <Section id="detail-agent" title="Agent & Tools" icon={Bot}>
            <div className="space-y-2">
              {/* Agent */}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-muted-foreground font-medium shrink-0">Agent:</span>
                {stage.agentUsed ? (
                  <Badge
                    variant="secondary"
                    className="gap-1 text-xs bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950 dark:text-indigo-300 dark:border-indigo-800"
                  >
                    <Bot className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
                    {agentName}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground/60 italic">No agent assigned</span>
                )}
              </div>

              {/* Tools — tools are not directly on StageExecution; render placeholder note */}
              <div className="flex items-start gap-1.5 text-xs">
                <span className="text-muted-foreground font-medium shrink-0 mt-0.5">Tools:</span>
                <span className="text-muted-foreground/60 italic">
                  Tool info not available at runtime
                </span>
              </div>
            </div>
          </Section>

          <Separator />

          {/* ================================================================ */}
          {/* Timing                                                           */}
          {/* ================================================================ */}
          <Section id="detail-timing" title="Timing" icon={Clock}>
            <dl className="space-y-1.5">
              <DefRow label="Started">
                {stage.startedAt ? (
                  <time dateTime={stage.startedAt}>{formatTime(stage.startedAt)}</time>
                ) : (
                  <span className="text-muted-foreground/60">—</span>
                )}
              </DefRow>

              <DefRow label="Duration">
                {hasFinalDuration ? (
                  formatDuration(stage.durationMs!)
                ) : showLiveDuration ? (
                  <LiveDuration startedAt={stage.startedAt!} />
                ) : (
                  <span className="text-muted-foreground/60">—</span>
                )}
              </DefRow>

              <DefRow label="Ended">
                {stage.completedAt ? (
                  <time dateTime={stage.completedAt}>{formatTime(stage.completedAt)}</time>
                ) : (
                  <span className="text-muted-foreground/60">
                    {isRunning ? 'In progress…' : '—'}
                  </span>
                )}
              </DefRow>
            </dl>
          </Section>

          <Separator />

          {/* ================================================================ */}
          {/* Context consumed                                                 */}
          {/* ================================================================ */}
          <Section id="detail-context" title="Context Consumed" icon={BookOpen}>
            {/* StageExecution doesn't carry context module data at runtime.
                This section provides a meaningful empty state with a hint
                that context info will be available once the backend exposes it. */}
            <p className="text-xs text-muted-foreground/60 italic">
              No context information available
            </p>
          </Section>

          <Separator />

          {/* ================================================================ */}
          {/* Inputs                                                           */}
          {/* ================================================================ */}
          <CollapsibleSection
            id="detail-inputs"
            title="Inputs"
            icon={Calendar}
            defaultOpen={false}
            isEmpty={true}
            emptyText="No input data captured"
          >
            {/* Inputs are not in StageExecution; reserved for future backend field */}
            <></>
          </CollapsibleSection>

          {/* ================================================================ */}
          {/* Outputs                                                          */}
          {/* ================================================================ */}
          <CollapsibleSection
            id="detail-outputs"
            title="Outputs"
            icon={CheckCircle2}
            defaultOpen={hasOutputs}
            isEmpty={!hasOutputs}
            emptyText="No outputs produced"
          >
            <DataBlock data={stage.outputs} />
          </CollapsibleSection>

          {/* ================================================================ */}
          {/* Log viewer slot                                                  */}
          {/* ================================================================ */}
          {children && (
            <>
              <Separator />
              <section aria-label="Stage logs">
                {children}
              </section>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
