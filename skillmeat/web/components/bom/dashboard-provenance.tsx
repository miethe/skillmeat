/**
 * DashboardProvenance — provenance summary card for the project dashboard.
 *
 * Implements WF-6 from the Phase 9 wireframe brief:
 *   - Stats row: artifact count, attestation count, verification status
 *   - Mini activity feed: last 3 events
 *   - "View BOM" and "View all activity" links
 *
 * Uses `useBomSnapshot` and `useArtifactActivityHistory` hooks. Also accepts
 * an optional `attestationCount` override from the parent when the caller
 * already has attestation data, to avoid a redundant extra query.
 *
 * Card styling matches existing dashboard section cards (border, card bg,
 * zinc palette, Inter font weights).
 *
 * @example
 * ```tsx
 * <DashboardProvenance
 *   projectId={project.path}
 *   onViewBom={() => navigateToBom()}
 *   onViewAllActivity={() => navigateToHistory()}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import {
  ShieldCheck,
  ShieldX,
  Shield,
  Package,
  BadgeCheck,
  Clock,
  User,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useBomSnapshot } from '@/hooks';
import { useArtifactActivityHistory } from '@/hooks';
import type { ActivityEvent } from '@/types/bom';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeTime(isoTimestamp: string | null | undefined): string {
  if (!isoTimestamp) return 'Unknown';
  const date = new Date(isoTimestamp);
  if (isNaN(date.getTime())) return 'Unknown';
  const now = Date.now();
  const diffSec = Math.floor((now - date.getTime()) / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

function formatAbsoluteTime(isoTimestamp: string | null | undefined): string {
  if (!isoTimestamp) return '';
  const date = new Date(isoTimestamp);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString();
}

function eventTypeLabel(eventType: string): string {
  const labels: Record<string, string> = {
    created: 'Created',
    updated: 'Updated',
    deployed: 'Deployed',
    deleted: 'Deleted',
    attested: 'Attested',
    bom_generated: 'BOM generated',
  };
  return labels[eventType] ?? eventType.replace(/_/g, ' ');
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface DashboardProvenanceProps {
  /** Optional project path to scope the BOM and activity to a specific project. */
  projectId?: string;
  /** Pre-loaded attestation count. When provided, skips separate fetch. */
  attestationCount?: number;
  /** Called when the "View BOM" button is clicked. */
  onViewBom?: () => void;
  /** Called when the "View all activity" button is clicked. */
  onViewAllActivity?: () => void;
  /** Additional CSS class names. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function DashboardProvenanceSkeleton() {
  return (
    <Card aria-hidden="true">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-8 w-24 rounded-md" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats row skeleton */}
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-md border border-border/60 p-3 space-y-1">
              <Skeleton className="h-6 w-10" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))}
        </div>
        <Separator />
        {/* Activity skeleton */}
        <div className="space-y-2.5">
          <Skeleton className="h-3.5 w-24" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between py-1">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-20 rounded-full" />
                <Skeleton className="h-3.5 w-20" />
              </div>
              <Skeleton className="h-3 w-14" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Stat Cell
// ---------------------------------------------------------------------------

interface StatCellProps {
  value: React.ReactNode;
  label: string;
  tooltip?: string;
  status?: 'positive' | 'warning' | 'neutral';
}

function StatCell({ value, label, tooltip, status = 'neutral' }: StatCellProps) {
  const valueClass = cn(
    'text-xl font-semibold tabular-nums',
    status === 'positive' && 'text-green-600 dark:text-green-400',
    status === 'warning' && 'text-yellow-600 dark:text-yellow-400',
    status === 'neutral' && 'text-foreground'
  );

  const cell = (
    <div className="rounded-md border border-border/60 p-3 space-y-0.5">
      <div className={valueClass}>{value}</div>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );

  if (!tooltip) return cell;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{cell}</TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          {tooltip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// Activity Row
// ---------------------------------------------------------------------------

interface ActivityRowProps {
  event: ActivityEvent;
}

function ActivityRow({ event }: ActivityRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-xs font-medium text-foreground truncate">
          {eventTypeLabel(event.event_type)}
        </span>
        {event.actor_id && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
            <User className="h-3 w-3" aria-hidden="true" />
            {event.actor_id}
          </span>
        )}
      </div>
      {event.timestamp && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex items-center gap-1 text-[11px] text-muted-foreground shrink-0 cursor-default ml-2">
                <Clock className="h-3 w-3" aria-hidden="true" />
                {formatRelativeTime(event.timestamp)}
              </span>
            </TooltipTrigger>
            <TooltipContent side="left" className="text-xs">
              {formatAbsoluteTime(event.timestamp)}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DashboardProvenance
// ---------------------------------------------------------------------------

/**
 * Provenance summary card for the project dashboard.
 *
 * Fetches BOM snapshot and recent activity independently; renders a compact
 * 3-stat row plus a mini activity feed with links to full views.
 */
export function DashboardProvenance({
  projectId,
  attestationCount,
  onViewBom,
  onViewAllActivity,
  className,
}: DashboardProvenanceProps) {
  // BOM snapshot
  const {
    data: bomData,
    isLoading: isBomLoading,
    isError: isBomError,
  } = useBomSnapshot({ projectId });

  // Recent activity (last 3 events)
  const {
    data: activityData,
    isLoading: isActivityLoading,
  } = useArtifactActivityHistory({ limit: 3 });

  const recentEvents: ActivityEvent[] =
    activityData?.pages.flatMap((page) => page.items).slice(0, 3) ?? [];

  const isLoading = isBomLoading || isActivityLoading;

  if (isLoading) {
    return <DashboardProvenanceSkeleton />;
  }

  const artifactCount = bomData?.bom.artifact_count ?? 0;
  const attestCount = attestationCount ?? 0;
  const isSigned = !!(bomData?.signature);
  const generatedAt = bomData?.bom.generated_at;

  const verificationStatus: 'positive' | 'warning' | 'neutral' = isSigned
    ? 'positive'
    : 'warning';

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <Shield className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Provenance &amp; BOM
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
            onClick={onViewBom}
            aria-label="View full BOM details"
            disabled={!bomData}
          >
            View BOM
            <ArrowRight className="h-3 w-3" aria-hidden="true" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Stats row */}
        {isBomError && !bomData ? (
          <div className="flex flex-col items-center justify-center gap-2 py-4 text-center rounded-md border border-dashed border-border/60">
            <AlertCircle className="h-6 w-6 text-muted-foreground/40" aria-hidden="true" />
            <p className="text-xs text-muted-foreground">
              No BOM snapshot available.
            </p>
            <p className="text-[11px] text-muted-foreground/70">
              Run{' '}
              <code className="font-mono text-[11px] bg-muted px-1 py-0.5 rounded">
                skillmeat bom generate
              </code>{' '}
              to create one.
            </p>
          </div>
        ) : (
          <div
            className="grid grid-cols-3 gap-3"
            role="list"
            aria-label="Provenance statistics"
          >
            <div role="listitem">
              <StatCell
                value={
                  <span className="flex items-center gap-1">
                    <Package className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    {artifactCount}
                  </span>
                }
                label="Artifacts"
                tooltip={`${artifactCount} artifact${artifactCount !== 1 ? 's' : ''} in the latest BOM snapshot`}
              />
            </div>
            <div role="listitem">
              <StatCell
                value={
                  <span className="flex items-center gap-1">
                    <BadgeCheck className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    {attestCount}
                  </span>
                }
                label="Attestations"
                tooltip={`${attestCount} attestation record${attestCount !== 1 ? 's' : ''}`}
              />
            </div>
            <div role="listitem">
              <StatCell
                value={
                  isSigned ? (
                    <ShieldCheck className="h-5 w-5 text-green-600 dark:text-green-400" aria-hidden="true" />
                  ) : (
                    <ShieldX className="h-5 w-5 text-yellow-600 dark:text-yellow-400" aria-hidden="true" />
                  )
                }
                label={isSigned ? 'Signed' : 'Unsigned'}
                status={verificationStatus}
                tooltip={
                  isSigned
                    ? `BOM signed — last generated ${generatedAt ? formatAbsoluteTime(generatedAt) : 'unknown'}`
                    : 'BOM has not been signed. Run skillmeat bom generate --auto-sign to sign.'
                }
              />
            </div>
          </div>
        )}

        <Separator />

        {/* Recent activity */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Recent Activity</p>

          {recentEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-1.5 py-4 rounded-md border border-dashed border-border/60 text-center">
              <Clock className="h-5 w-5 text-muted-foreground/30" aria-hidden="true" />
              <p className="text-xs text-muted-foreground">No activity recorded yet.</p>
            </div>
          ) : (
            <ul
              role="list"
              aria-label="Recent provenance activity"
              className="divide-y divide-border/40"
            >
              {recentEvents.map((event) => (
                <li key={event.id} role="listitem">
                  <ActivityRow event={event} />
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* View all activity link */}
        {recentEvents.length > 0 && (
          <div className="flex justify-end pt-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={onViewAllActivity}
              aria-label="View all provenance activity"
            >
              View all activity
              <ArrowRight className="h-3 w-3" aria-hidden="true" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
