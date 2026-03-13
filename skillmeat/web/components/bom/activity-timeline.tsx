'use client';

/**
 * ActivityTimeline Component
 *
 * Chronological, date-grouped activity log for BOM provenance/audit events.
 * Shows events such as BOM generated, attestation created, BOM verified,
 * and artifact updated — NOT version history.
 *
 * Accessibility: WCAG 2.1 AA
 *   - Container: role="feed" with aria-label and aria-busy
 *   - Each event: role="article" with aria-label (type + time + actor)
 *   - Arrow keys move focus between events; Enter/Space expands; Escape collapses
 *   - Visible focus ring on all interactive elements
 *   - Screen reader live region for dynamic content (load-more)
 *
 * Layout (WF-4):
 *   DateGroup(date) → DateHeader
 *     TimelineItem(event) → CollapsibleTrigger (time, icon, description, actor)
 *                         → CollapsibleContent (detail card, metadata grid)
 *   LoadMoreButton
 */

import * as React from 'react';
import {
  FileCheck2,
  ShieldCheck,
  ShieldPlus,
  GitCommit,
  RefreshCw,
  Trash2,
  Upload,
  Activity,
  ChevronDown,
  User,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import type { ActivityEvent, ActivityEventType } from '@/types/bom';

// =============================================================================
// Types
// =============================================================================

export interface ActivityTimelineProps {
  events: ActivityEvent[];
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  className?: string;
}

// =============================================================================
// Event type configuration
// =============================================================================

interface EventTypeConfig {
  label: string;
  Icon: React.ElementType;
  /** Tailwind color class for the icon and the timeline dot */
  colorClass: string;
  /** Tailwind class for the dot ring when expanded */
  ringClass: string;
  /** Tailwind class for the badge */
  badgeClass: string;
}

const EVENT_TYPE_CONFIG: Record<string, EventTypeConfig> = {
  bom_generated: {
    label: 'BOM Generated',
    Icon: FileCheck2,
    colorClass: 'text-blue-500 dark:text-blue-400',
    ringClass: 'ring-blue-200 dark:ring-blue-900',
    badgeClass:
      'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300',
  },
  attested: {
    label: 'Attestation Created',
    Icon: ShieldPlus,
    colorClass: 'text-purple-500 dark:text-purple-400',
    ringClass: 'ring-purple-200 dark:ring-purple-900',
    badgeClass:
      'border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-300',
  },
  verified: {
    label: 'BOM Verified',
    Icon: ShieldCheck,
    colorClass: 'text-emerald-500 dark:text-emerald-400',
    ringClass: 'ring-emerald-200 dark:ring-emerald-900',
    badgeClass:
      'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  },
  created: {
    label: 'Created',
    Icon: GitCommit,
    colorClass: 'text-sky-500 dark:text-sky-400',
    ringClass: 'ring-sky-200 dark:ring-sky-900',
    badgeClass:
      'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-300',
  },
  updated: {
    label: 'Updated',
    Icon: RefreshCw,
    colorClass: 'text-amber-500 dark:text-amber-400',
    ringClass: 'ring-amber-200 dark:ring-amber-900',
    badgeClass:
      'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300',
  },
  deployed: {
    label: 'Deployed',
    Icon: Upload,
    colorClass: 'text-teal-500 dark:text-teal-400',
    ringClass: 'ring-teal-200 dark:ring-teal-900',
    badgeClass:
      'border-teal-200 bg-teal-50 text-teal-700 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-300',
  },
  deleted: {
    label: 'Deleted',
    Icon: Trash2,
    colorClass: 'text-rose-500 dark:text-rose-400',
    ringClass: 'ring-rose-200 dark:ring-rose-900',
    badgeClass:
      'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-300',
  },
};

const FALLBACK_CONFIG: EventTypeConfig = {
  label: 'Activity',
  Icon: Activity,
  colorClass: 'text-zinc-500 dark:text-zinc-400',
  ringClass: 'ring-zinc-200 dark:ring-zinc-700',
  badgeClass:
    'border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400',
};

function getEventConfig(eventType: ActivityEventType): EventTypeConfig {
  return EVENT_TYPE_CONFIG[eventType] ?? FALLBACK_CONFIG;
}

// =============================================================================
// Date helpers
// =============================================================================

function formatDateHeader(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const sameDay = (a: Date, b: Date) =>
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();

    if (sameDay(d, today)) return 'Today';
    if (sameDay(d, yesterday)) return 'Yesterday';

    return d.toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return isoDate;
  }
}

function formatTime(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function formatDateKey(iso?: string | null): string {
  if (!iso) return 'unknown';
  try {
    const d = new Date(iso);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return 'unknown';
  }
}

/**
 * Group events by calendar day (descending date order).
 * Events within a day maintain their original order (typically newest-first from API).
 */
function groupEventsByDate(events: ActivityEvent[]): Array<{
  dateKey: string;
  displayDate: string;
  events: ActivityEvent[];
}> {
  const groups = new Map<string, ActivityEvent[]>();

  for (const event of events) {
    const key = formatDateKey(event.timestamp);
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(event);
    } else {
      groups.set(key, [event]);
    }
  }

  // Sort date keys descending
  const sortedKeys = Array.from(groups.keys()).sort((a, b) => b.localeCompare(a));

  return sortedKeys.map((key) => {
    const bucket = groups.get(key)!;
    const representativeTs = bucket[0]?.timestamp ?? key;
    return {
      dateKey: key,
      displayDate: formatDateHeader(representativeTs),
      events: bucket,
    };
  });
}

// =============================================================================
// MetadataGrid — renders diff_json entries as a key/value table
// =============================================================================

function MetadataGrid({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
      {entries.map(([key, value]) => (
        <React.Fragment key={key}>
          <dt className="font-medium text-zinc-500 dark:text-zinc-400 whitespace-nowrap">
            {key.replace(/_/g, ' ')}
          </dt>
          <dd className="text-zinc-700 dark:text-zinc-300 break-words font-mono">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </dd>
        </React.Fragment>
      ))}
    </dl>
  );
}

// =============================================================================
// TimelineItem — single collapsible event row
// =============================================================================

interface TimelineItemProps {
  event: ActivityEvent;
  /** Whether this is the last item in its date group (for connector line logic) */
  isLast: boolean;
  /** Whether this is the very last item in the entire feed (no bottom connector) */
  isFeedLast: boolean;
  /** Callback when this item is focused via keyboard navigation */
  onFocusRequest: (id: string) => void;
  isFocused: boolean;
}

const TimelineItem = React.forwardRef<HTMLDivElement, TimelineItemProps>(
  ({ event, isLast: _isLast, isFeedLast, onFocusRequest, isFocused }, _ref) => {
    const [expanded, setExpanded] = React.useState(false);
    const config = getEventConfig(event.event_type);
    const { Icon } = config;
    const time = formatTime(event.timestamp);
    const actor = event.actor_id ?? 'system';
    const description = event.artifact_id
      ? `${config.label} — ${event.artifact_id}`
      : config.label;
    const ariaLabel = `${config.label} at ${time} by ${actor}`;

    const triggerRef = React.useRef<HTMLButtonElement>(null);

    // Expose focus method for keyboard navigation from parent
    React.useEffect(() => {
      if (isFocused) {
        triggerRef.current?.focus();
      }
    }, [isFocused]);

    function handleKeyDown(e: React.KeyboardEvent) {
      if (e.key === 'Escape' && expanded) {
        e.stopPropagation();
        setExpanded(false);
      }
    }

    function handleTriggerClick() {
      setExpanded((prev) => !prev);
      onFocusRequest(event.id);
    }

    return (
      <div
        role="article"
        aria-label={ariaLabel}
        className="relative flex gap-3"
      >
        {/* Vertical connector line */}
        <div className="flex flex-col items-center" aria-hidden="true">
          {/* Dot */}
          <div
            className={cn(
              'relative z-10 mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full',
              'bg-white dark:bg-zinc-950 ring-2',
              config.ringClass,
              'transition-shadow duration-150',
              expanded && 'ring-offset-2'
            )}
          >
            <Icon className={cn('h-3.5 w-3.5', config.colorClass)} aria-hidden="true" />
          </div>
          {/* Connector line below dot */}
          {!isFeedLast && (
            <div className="mt-1 w-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
          )}
        </div>

        {/* Event content */}
        <div className="min-w-0 flex-1 pb-4">
          <Collapsible open={expanded} onOpenChange={setExpanded}>
            <CollapsibleTrigger asChild>
              <button
                ref={triggerRef}
                className={cn(
                  'group flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left',
                  'transition-colors duration-100',
                  'hover:bg-zinc-50 dark:hover:bg-zinc-900/60',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2',
                  'dark:focus-visible:ring-zinc-600'
                )}
                aria-expanded={expanded}
                aria-controls={`timeline-content-${event.id}`}
                onClick={handleTriggerClick}
                onKeyDown={handleKeyDown}
              >
                {/* Timestamp */}
                <span
                  className="mt-0.5 flex-shrink-0 font-mono text-xs text-zinc-400 dark:text-zinc-500"
                  aria-hidden="true"
                >
                  {time}
                </span>

                {/* Description */}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-zinc-800 dark:text-zinc-200">
                    {description}
                  </span>
                </span>

                {/* Actor badge */}
                <ActorBadge actor={actor} ownerType={event.owner_type ?? undefined} />

                {/* Expand chevron */}
                {(event.diff_json || event.content_hash) && (
                  <ChevronDown
                    className={cn(
                      'mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-zinc-400 transition-transform duration-200',
                      'group-hover:text-zinc-600 dark:group-hover:text-zinc-300',
                      expanded && 'rotate-180'
                    )}
                    aria-hidden="true"
                  />
                )}
              </button>
            </CollapsibleTrigger>

            <CollapsibleContent
              id={`timeline-content-${event.id}`}
              className={cn(
                'overflow-hidden',
                'data-[state=open]:animate-collapsible-down',
                'data-[state=closed]:animate-collapsible-up'
              )}
            >
              <DetailCard event={event} config={config} />
            </CollapsibleContent>
          </Collapsible>
        </div>
      </div>
    );
  }
);
TimelineItem.displayName = 'TimelineItem';

// =============================================================================
// ActorBadge — renders actor id with optional owner type hint
// =============================================================================

function ActorBadge({
  actor,
  ownerType,
}: {
  actor: string;
  ownerType?: string;
}) {
  const label =
    actor === 'system'
      ? 'system'
      : actor.length > 16
        ? `${actor.slice(0, 8)}…${actor.slice(-4)}`
        : actor;

  return (
    <span
      className={cn(
        'inline-flex flex-shrink-0 items-center gap-1 rounded-sm',
        'border border-zinc-200 bg-zinc-100 px-1.5 py-0.5',
        'text-xs text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400'
      )}
      title={actor !== label ? actor : undefined}
      aria-hidden="true"
    >
      <User className="h-2.5 w-2.5 flex-shrink-0" aria-hidden="true" />
      {ownerType && ownerType !== 'user' && (
        <span className="capitalize text-zinc-400 dark:text-zinc-500">{ownerType}/</span>
      )}
      {label}
    </span>
  );
}

// =============================================================================
// DetailCard — expandable detail area
// =============================================================================

function DetailCard({
  event,
  config,
}: {
  event: ActivityEvent;
  config: EventTypeConfig;
}) {
  const hasDiff = event.diff_json && Object.keys(event.diff_json).length > 0;
  const hasHash = !!event.content_hash;

  return (
    <div
      className={cn(
        'ml-2 mt-1 rounded-md border',
        'border-zinc-200 bg-zinc-50/60 dark:border-zinc-800 dark:bg-zinc-900/40',
        'px-3 py-2.5 text-xs'
      )}
    >
      {/* Header row */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <Badge
          variant="outline"
          className={cn('h-5 px-1.5 py-0', config.badgeClass)}
        >
          {config.label}
        </Badge>
        {event.timestamp && (
          <span className="flex items-center gap-1 text-zinc-400 dark:text-zinc-500">
            <Clock className="h-3 w-3" aria-hidden="true" />
            <time dateTime={event.timestamp}>
              {new Date(event.timestamp).toLocaleString(undefined, {
                dateStyle: 'medium',
                timeStyle: 'short',
              })}
            </time>
          </span>
        )}
      </div>

      {/* Artifact id */}
      {event.artifact_id && (
        <p className="mb-2 font-mono text-zinc-600 dark:text-zinc-300">
          {event.artifact_id}
        </p>
      )}

      {/* Content hash */}
      {hasHash && (
        <>
          <Separator className="my-2" />
          <div className="flex items-baseline gap-2">
            <span className="font-medium text-zinc-500 dark:text-zinc-400">
              Content hash
            </span>
            <span className="truncate font-mono text-zinc-600 dark:text-zinc-300">
              {event.content_hash!.slice(0, 12)}…
            </span>
          </div>
        </>
      )}

      {/* Diff / metadata */}
      {hasDiff && (
        <>
          <Separator className="my-2" />
          <p className="mb-1.5 font-medium text-zinc-500 dark:text-zinc-400">Changes</p>
          <MetadataGrid data={event.diff_json!} />
        </>
      )}
    </div>
  );
}

// =============================================================================
// DateGroupHeader
// =============================================================================

function DateGroupHeader({ label }: { label: string }) {
  return (
    <div className="relative z-10 mb-3 flex items-center gap-3">
      {/* Spacer to align with the dot column (7px dot + 12px margin) */}
      <div className="w-7 flex-shrink-0" aria-hidden="true" />
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
          {label}
        </span>
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" aria-hidden="true" />
      </div>
    </div>
  );
}

// =============================================================================
// Skeleton loader
// =============================================================================

function TimelineSkeleton() {
  return (
    <div aria-label="Loading activity timeline" aria-busy="true" className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <Skeleton className="h-7 w-7 rounded-full" />
            {i < 4 && <Skeleton className="mt-1 h-8 w-px" />}
          </div>
          <div className="flex-1 space-y-1.5 py-1">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Empty state
// =============================================================================

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <Activity
        className="h-8 w-8 text-zinc-300 dark:text-zinc-700"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-zinc-400 dark:text-zinc-500">
        No activity yet
      </p>
      <p className="text-xs text-zinc-400 dark:text-zinc-600">
        Events will appear here as BOM operations are performed.
      </p>
    </div>
  );
}

// =============================================================================
// ActivityTimelineFeed — main exported component
// =============================================================================

/**
 * ActivityTimelineFeed renders a chronological, date-grouped list of
 * ActivityEvent records for BOM provenance audit display.
 *
 * @example
 * ```tsx
 * <ActivityTimelineFeed
 *   events={historyEvents}
 *   isLoading={isLoading}
 *   hasMore={hasNextPage}
 *   onLoadMore={fetchNextPage}
 * />
 * ```
 */
export function ActivityTimelineFeed({
  events,
  isLoading = false,
  hasMore = false,
  onLoadMore,
  className,
}: ActivityTimelineProps) {
  const [focusedId, setFocusedId] = React.useState<string | null>(null);

  // Flat ordered list of event ids for keyboard navigation
  const flatEventIds = React.useMemo(() => events.map((e) => e.id), [events]);

  const groupedDates = React.useMemo(() => groupEventsByDate(events), [events]);

  // Arrow-key navigation handler on the feed container
  function handleFeedKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;

    e.preventDefault();
    const currentIndex = focusedId ? flatEventIds.indexOf(focusedId) : -1;

    if (e.key === 'ArrowDown') {
      const next = flatEventIds[currentIndex + 1];
      if (next) setFocusedId(next);
    } else {
      const prev = flatEventIds[currentIndex - 1];
      if (prev) setFocusedId(prev);
    }
  }

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------
  if (isLoading && events.length === 0) {
    return (
      <div className={cn('w-full', className)}>
        <TimelineSkeleton />
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------
  if (!isLoading && events.length === 0) {
    return (
      <div className={cn('w-full', className)}>
        <EmptyState />
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Feed
  // -------------------------------------------------------------------------
  const totalEvents = events.length;
  let globalIndex = 0;

  return (
    <div
      role="feed"
      aria-label="Activity timeline"
      aria-busy={isLoading}
      aria-describedby="activity-timeline-hint"
      className={cn('w-full', className)}
      onKeyDown={handleFeedKeyDown}
    >
      {/* Screen-reader instruction hint (visually hidden) */}
      <p id="activity-timeline-hint" className="sr-only">
        Use Arrow Up and Arrow Down to move between events. Press Enter or Space
        to expand an event for details. Press Escape to collapse.
      </p>

      {groupedDates.map(({ dateKey, displayDate, events: dateEvents }) => (
        <div key={dateKey} className="mb-2" role="group" aria-label={displayDate}>
          <DateGroupHeader label={displayDate} />

          <div className="space-y-0">
            {dateEvents.map((event, idx) => {
              const isLastInGroup = idx === dateEvents.length - 1;
              const isLastInFeed = globalIndex === totalEvents - 1;
              globalIndex += 1;

              return (
                <TimelineItem
                  key={event.id}
                  event={event}
                  isLast={isLastInGroup}
                  isFeedLast={isLastInFeed && !hasMore}
                  onFocusRequest={setFocusedId}
                  isFocused={focusedId === event.id}
                  ref={null}
                />
              );
            })}
          </div>
        </div>
      ))}

      {/* Load more */}
      {(hasMore || isLoading) && (
        <div className="mt-2 flex justify-center" aria-live="polite" aria-atomic="true">
          <Button
            variant="outline"
            size="sm"
            onClick={onLoadMore}
            disabled={isLoading || !onLoadMore}
            className={cn(
              'gap-2 border-zinc-200 text-xs text-zinc-500',
              'hover:border-zinc-300 hover:bg-zinc-50 hover:text-zinc-700',
              'dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-900'
            )}
          >
            {isLoading ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Loading…
              </>
            ) : (
              'Load more'
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Default export alias for convenience
// =============================================================================

export { ActivityTimelineFeed as ActivityTimeline };
