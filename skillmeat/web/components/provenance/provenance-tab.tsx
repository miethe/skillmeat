/**
 * ProvenanceTab — BOM snapshot summary, attestation list, and activity preview.
 *
 * This is a purely presentational component. Data fetching is delegated to
 * hooks that will be wired up by the parent (useBomSnapshot, useAttestations,
 * useArtifactActivity). Props follow the API schema shapes in types/bom.ts.
 *
 * Layout (WF-1):
 *   1. BOMSummaryCard  — artifact count, generated-at, export JSON button
 *   2. AttestationSection — list of attestation records, create button
 *   3. RecentActivityPreview — last 5 events, "View all" link
 *
 * Accessibility: WCAG 2.1 AA — all interactive elements have aria-labels,
 * lists use role="list" + role="listitem", skeleton regions are aria-hidden.
 *
 * @example
 * ```tsx
 * <ProvenanceTab
 *   artifactId={artifact.id}
 *   bomData={bomSnapshot}
 *   attestations={attestationList}
 *   recentActivity={activityEvents}
 *   isLoading={isLoading}
 *   onExportBom={handleExport}
 *   onCreateAttestation={handleCreate}
 *   onViewAllActivity={handleViewAll}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import {
  FileCheck,
  BadgeCheck,
  Download,
  Plus,
  ChevronRight,
  Clock,
  User,
  AlertCircle,
  Package,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { BomSnapshot, Attestation, ActivityEvent } from '@/types/bom';

// =============================================================================
// Helpers
// =============================================================================

/**
 * Formats an ISO-8601 timestamp as a human-readable relative string.
 * Falls back to the full locale string if the date is invalid.
 */
function formatRelativeTime(isoTimestamp: string | null | undefined): string {
  if (!isoTimestamp) return 'Unknown';
  const date = new Date(isoTimestamp);
  if (isNaN(date.getTime())) return 'Unknown';

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

/** Formats an ISO-8601 timestamp as a full locale datetime for title/tooltip. */
function formatAbsoluteTime(isoTimestamp: string | null | undefined): string {
  if (!isoTimestamp) return '';
  const date = new Date(isoTimestamp);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString();
}

/** Returns a Tailwind colour class for attestation visibility levels. */
function visibilityVariant(
  visibility: string
): 'default' | 'secondary' | 'outline' {
  switch (visibility) {
    case 'public':
      return 'default';
    case 'org':
      return 'secondary';
    default:
      return 'outline';
  }
}

/** Returns a concise label for a history event_type string. */
function eventTypeLabel(eventType: string): string {
  const labels: Record<string, string> = {
    created: 'Created',
    updated: 'Updated',
    deployed: 'Deployed',
    deleted: 'Deleted',
    attested: 'Attested',
    bom_generated: 'BOM Generated',
  };
  return labels[eventType] ?? eventType.replace(/_/g, ' ');
}

/** Returns a Tailwind colour class for event badge colouring. */
function eventBadgeVariant(
  eventType: string
): 'default' | 'secondary' | 'outline' | 'destructive' {
  switch (eventType) {
    case 'created':
    case 'attested':
    case 'bom_generated':
      return 'default';
    case 'updated':
    case 'deployed':
      return 'secondary';
    case 'deleted':
      return 'destructive';
    default:
      return 'outline';
  }
}

// =============================================================================
// Props Interface
// =============================================================================

export interface ProvenanceTabProps {
  /** Composite ID of the artifact (type:name format). */
  artifactId: string;
  /** BOM snapshot data from useBomSnapshot hook (will be created later). */
  bomData?: BomSnapshot;
  /** List of attestation records from useAttestations hook. */
  attestations?: Attestation[];
  /** Recent activity events from useArtifactActivity hook. */
  recentActivity?: ActivityEvent[];
  /** True while any data is being fetched. */
  isLoading?: boolean;
  /** Called when the user clicks the Export JSON button. */
  onExportBom?: () => void;
  /** Called when the user clicks Create Attestation. */
  onCreateAttestation?: () => void;
  /** Called when the user clicks View All Activity. */
  onViewAllActivity?: () => void;
}

// =============================================================================
// Section Header
// =============================================================================

interface SectionHeaderProps {
  icon: React.ElementType;
  title: string;
  action?: React.ReactNode;
}

function SectionHeader({ icon: Icon, title, action }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// =============================================================================
// BOM Summary Card — Skeleton
// =============================================================================

function BOMSummarySkeleton() {
  return (
    <Card aria-hidden="true">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-36" />
          </div>
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
        <div className="mt-4 space-y-1.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-full rounded-md" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// BOM Summary Card
// =============================================================================

interface BOMSummaryCardProps {
  data: BomSnapshot;
  onExport?: () => void;
}

function BOMSummaryCard({ data, onExport }: BOMSummaryCardProps) {
  const generatorName =
    (data.metadata?.generator as string | undefined) ?? 'skillmeat-bom';
  const elapsedMs = data.metadata?.elapsed_ms as number | undefined;

  // Group artifacts by type for the type breakdown display
  const typeBreakdown = React.useMemo(() => {
    const counts: Record<string, number> = {};
    for (const artifact of data.artifacts) {
      counts[artifact.type] = (counts[artifact.type] ?? 0) + 1;
    }
    return Object.entries(counts).sort(([, a], [, b]) => b - a);
  }, [data.artifacts]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <FileCheck
              className="h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            Bill of Materials
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={onExport}
            aria-label="Export BOM as JSON"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Export JSON
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground mb-0.5">Artifacts</p>
            <p className="text-lg font-semibold tabular-nums">
              {data.artifact_count}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-0.5">Generated</p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <p className="text-sm font-medium cursor-default">
                    {formatRelativeTime(data.generated_at)}
                  </p>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                  {formatAbsoluteTime(data.generated_at)}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          {elapsedMs !== undefined && (
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">
                Generation time
              </p>
              <p className="text-sm font-medium tabular-nums">
                {elapsedMs.toFixed(0)}ms
              </p>
            </div>
          )}
        </div>

        {/* Schema version + generator */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="text-xs font-mono">
            schema v{data.schema_version}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {generatorName}
          </Badge>
          {data.project_path && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge variant="outline" className="text-xs font-mono max-w-[160px] truncate">
                    {data.project_path}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs font-mono">
                  {data.project_path}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Type breakdown */}
        {typeBreakdown.length > 0 && (
          <div
            role="list"
            aria-label="Artifact type breakdown"
            className="space-y-1.5"
          >
            {typeBreakdown.map(([type, count]) => (
              <div
                key={type}
                role="listitem"
                className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5"
              >
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground capitalize">
                  <Package className="h-3 w-3" aria-hidden="true" />
                  {type}
                </span>
                <span className="text-xs font-medium tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        )}

        {data.artifacts.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-3">
            No artifacts in this BOM snapshot.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// BOM Summary — Empty / Not Generated
// =============================================================================

function BOMEmptyState() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <FileCheck
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          Bill of Materials
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center gap-2 py-6 text-center">
          <FileCheck
            className="h-8 w-8 text-muted-foreground/30"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            No BOM snapshot has been generated yet.
          </p>
          <p className="text-xs text-muted-foreground/70">
            Run{' '}
            <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">
              skillmeat bom generate
            </code>{' '}
            to create a snapshot.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Attestation Item
// =============================================================================

interface AttestationItemProps {
  attestation: Attestation;
}

function AttestationItem({ attestation }: AttestationItemProps) {
  return (
    <li
      className="flex items-start justify-between gap-3 rounded-md border border-border/60 bg-card px-3 py-2.5"
      role="listitem"
    >
      <div className="flex flex-col gap-1 min-w-0">
        {/* Owner */}
        <div className="flex items-center gap-1.5">
          <User
            className="h-3.5 w-3.5 text-muted-foreground shrink-0"
            aria-hidden="true"
          />
          <span className="text-xs font-medium truncate">
            {attestation.owner_type}/{attestation.owner_id}
          </span>
        </div>

        {/* Roles */}
        {attestation.roles.length > 0 && (
          <div className="flex flex-wrap gap-1" aria-label="Roles">
            {attestation.roles.map((role) => (
              <Badge
                key={role}
                variant="secondary"
                className="text-[10px] px-1.5 py-0"
              >
                {role}
              </Badge>
            ))}
          </div>
        )}

        {/* Scopes */}
        {attestation.scopes.length > 0 && (
          <div
            className="flex flex-wrap gap-1"
            aria-label="Scopes"
          >
            {attestation.scopes.map((scope) => (
              <Badge
                key={scope}
                variant="outline"
                className="text-[10px] px-1.5 py-0 font-mono"
              >
                {scope}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Right: visibility + date */}
      <div className="flex flex-col items-end gap-1 shrink-0">
        <Badge
          variant={visibilityVariant(attestation.visibility)}
          className="text-[10px] px-1.5 py-0 capitalize"
          aria-label={`Visibility: ${attestation.visibility}`}
        >
          {attestation.visibility}
        </Badge>
        {attestation.created_at && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground cursor-default">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  {formatRelativeTime(attestation.created_at)}
                </span>
              </TooltipTrigger>
              <TooltipContent side="left" className="text-xs">
                {formatAbsoluteTime(attestation.created_at)}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </li>
  );
}

// =============================================================================
// Attestation Section — Skeleton
// =============================================================================

function AttestationSkeleton() {
  return (
    <div aria-hidden="true" className="space-y-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="rounded-md border border-border/60 px-3 py-2.5 space-y-1.5"
        >
          <div className="flex items-center gap-1.5">
            <Skeleton className="h-3.5 w-3.5 rounded" />
            <Skeleton className="h-3.5 w-32" />
          </div>
          <div className="flex gap-1">
            <Skeleton className="h-4 w-14 rounded-full" />
            <Skeleton className="h-4 w-16 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Attestation Section
// =============================================================================

interface AttestationSectionProps {
  attestations: Attestation[];
  isLoading?: boolean;
  onCreateAttestation?: () => void;
}

function AttestationSection({
  attestations,
  isLoading,
  onCreateAttestation,
}: AttestationSectionProps) {
  return (
    <section aria-labelledby="attestation-section-heading">
      <SectionHeader
        icon={BadgeCheck}
        title={`Attestations${attestations.length > 0 ? ` (${attestations.length})` : ''}`}
        action={
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={onCreateAttestation}
            aria-label="Create new attestation"
          >
            <Plus className="h-3 w-3" aria-hidden="true" />
            Attest
          </Button>
        }
      />

      {isLoading ? (
        <AttestationSkeleton />
      ) : attestations.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-6 text-center rounded-md border border-dashed border-border/60">
          <BadgeCheck
            className="h-7 w-7 text-muted-foreground/30"
            aria-hidden="true"
          />
          <p className="text-xs text-muted-foreground">
            No attestations recorded yet.
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onCreateAttestation}
          >
            Create first attestation
          </Button>
        </div>
      ) : (
        <ul
          role="list"
          aria-label={`${attestations.length} attestation${attestations.length === 1 ? '' : 's'}`}
          className="space-y-2"
        >
          {attestations.map((att) => (
            <AttestationItem key={att.id} attestation={att} />
          ))}
        </ul>
      )}
    </section>
  );
}

// =============================================================================
// Activity Event Item
// =============================================================================

interface ActivityEventItemProps {
  event: ActivityEvent;
}

function ActivityEventItem({ event }: ActivityEventItemProps) {
  return (
    <li
      role="listitem"
      className="flex items-center justify-between gap-3 py-2 border-b border-border/40 last:border-0"
    >
      <div className="flex items-center gap-2 min-w-0">
        <Badge
          variant={eventBadgeVariant(event.event_type)}
          className="text-[10px] px-1.5 py-0 shrink-0"
        >
          {eventTypeLabel(event.event_type)}
        </Badge>
        {event.actor_id && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground truncate">
            <User className="h-3 w-3 shrink-0" aria-hidden="true" />
            {event.actor_id}
          </span>
        )}
      </div>
      {event.timestamp && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground shrink-0 cursor-default">
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
    </li>
  );
}

// =============================================================================
// Recent Activity Preview — Skeleton
// =============================================================================

function ActivitySkeleton() {
  return (
    <div aria-hidden="true" className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between py-2 border-b border-border/40 last:border-0"
        >
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-16 rounded-full" />
            <Skeleton className="h-3.5 w-24" />
          </div>
          <Skeleton className="h-3 w-12" />
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Recent Activity Preview
// =============================================================================

interface RecentActivityPreviewProps {
  events: ActivityEvent[];
  isLoading?: boolean;
  onViewAllActivity?: () => void;
}

function RecentActivityPreview({
  events,
  isLoading,
  onViewAllActivity,
}: RecentActivityPreviewProps) {
  const MAX_PREVIEW = 5;
  const previewEvents = events.slice(0, MAX_PREVIEW);

  return (
    <section aria-labelledby="activity-section-heading">
      <SectionHeader
        icon={Clock}
        title="Recent Activity"
        action={
          events.length > 0 ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={onViewAllActivity}
              aria-label="View all activity events"
            >
              View all
              <ChevronRight className="h-3 w-3" aria-hidden="true" />
            </Button>
          ) : undefined
        }
      />

      {isLoading ? (
        <ActivitySkeleton />
      ) : previewEvents.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-6 text-center rounded-md border border-dashed border-border/60">
          <Clock
            className="h-7 w-7 text-muted-foreground/30"
            aria-hidden="true"
          />
          <p className="text-xs text-muted-foreground">
            No activity recorded yet.
          </p>
        </div>
      ) : (
        <ul
          role="list"
          aria-label={`${previewEvents.length} recent activity event${previewEvents.length === 1 ? '' : 's'}`}
        >
          {previewEvents.map((event) => (
            <ActivityEventItem key={event.id} event={event} />
          ))}
        </ul>
      )}
    </section>
  );
}

// =============================================================================
// ProvenanceTabContent (inner, unwrapped)
// =============================================================================

function ProvenanceTabContent({
  bomData,
  attestations = [],
  recentActivity = [],
  isLoading = false,
  onExportBom,
  onCreateAttestation,
  onViewAllActivity,
}: Omit<ProvenanceTabProps, 'artifactId'>) {
  return (
    <ScrollArea className="h-full">
      <div className="space-y-6 p-1 pb-6">
        {/* BOM Summary */}
        <section aria-labelledby="bom-section-heading">
          {isLoading ? (
            <BOMSummarySkeleton />
          ) : bomData ? (
            <BOMSummaryCard data={bomData} onExport={onExportBom} />
          ) : (
            <BOMEmptyState />
          )}
        </section>

        {/* Attestations */}
        <AttestationSection
          attestations={attestations}
          isLoading={isLoading}
          onCreateAttestation={onCreateAttestation}
        />

        {/* Recent Activity */}
        <RecentActivityPreview
          events={recentActivity}
          isLoading={isLoading}
          onViewAllActivity={onViewAllActivity}
        />
      </div>
    </ScrollArea>
  );
}

// =============================================================================
// ProvenanceTab Error Boundary
// =============================================================================

interface ProvenanceErrorBoundaryState {
  hasError: boolean;
}

class ProvenanceErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ProvenanceErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ProvenanceErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    if (process.env.NODE_ENV !== 'production') {
      console.error('[ProvenanceTab] Render error caught by boundary:', error, info);
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex flex-col items-center justify-center gap-3 py-12 text-center"
          role="alert"
          aria-live="assertive"
        >
          <AlertCircle
            className="h-8 w-8 text-destructive/70"
            aria-hidden="true"
          />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              Something went wrong
            </p>
            <p className="text-xs text-muted-foreground">
              The provenance panel encountered an unexpected error.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={this.handleReset}
          >
            Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

// =============================================================================
// ProvenanceTab (public export)
// =============================================================================

/**
 * ProvenanceTab — top-level presentational component for the Provenance tab.
 *
 * Renders three sections: BOM summary card, attestation list, and recent
 * activity preview. All data is passed via props; hooks are wired up by the
 * parent modal.
 *
 * Wrapped in an error boundary so unexpected render failures are isolated
 * to this tab and never propagate to the parent modal.
 */
export function ProvenanceTab(props: ProvenanceTabProps) {
  const { artifactId: _artifactId, ...rest } = props;
  return (
    <ProvenanceErrorBoundary>
      <ProvenanceTabContent {...rest} />
    </ProvenanceErrorBoundary>
  );
}

// Named sub-component exports for consumers that compose at the section level.
export { BOMSummaryCard, AttestationSection, RecentActivityPreview };
export type { BOMSummaryCardProps, AttestationSectionProps, RecentActivityPreviewProps };
