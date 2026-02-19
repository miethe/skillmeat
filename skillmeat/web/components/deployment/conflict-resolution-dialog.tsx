/**
 * Version Conflict Resolution Dialog
 *
 * Appears during plugin deployment when pinned child artifact versions conflict
 * with currently deployed versions. Presents each conflict with two resolution
 * strategies and an escape hatch to cancel deployment entirely.
 *
 * Platform scope: Claude Code only. Other platforms receive an informational notice.
 */
'use client';

import { useState, useCallback, useId } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
  AlertTriangle,
  ArrowRightLeft,
  GitCommit,
  Info,
  Layers,
  PackageX,
  ShieldAlert,
  Swords,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface VersionConflict {
  artifactName: string;
  artifactType: string;
  pinnedHash: string;
  currentHash: string;
  detectedAt: string; // ISO 8601
}

export type ConflictResolution = 'side-by-side' | 'overwrite';

export interface ConflictResolutionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conflicts: VersionConflict[];
  pluginName: string;
  /** Defaults to "claude-code". Non-claude-code platforms show unsupported notice. */
  platform?: string;
  /** Called with a Map from artifactName → resolution for each conflict. */
  onResolve: (resolutions: Map<string, ConflictResolution>) => void;
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function truncateHash(hash: string, length = 8): string {
  if (hash.length <= length) return hash;
  return hash.slice(0, length);
}

function formatDetectedAt(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function artifactTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    skill: 'Skill',
    command: 'Command',
    agent: 'Agent',
    mcp: 'MCP Server',
    hook: 'Hook',
  };
  return labels[type.toLowerCase()] ?? type;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface HashDisplayProps {
  label: string;
  hash: string;
  variant: 'pinned' | 'current';
}

function HashDisplay({ label, hash, variant }: HashDisplayProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <div
        className={cn(
          'flex items-center gap-1.5 rounded px-2 py-1 font-mono text-xs',
          variant === 'pinned'
            ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
            : 'bg-muted text-muted-foreground'
        )}
      >
        <GitCommit className="h-3 w-3 shrink-0" aria-hidden="true" />
        <span title={hash}>{truncateHash(hash)}</span>
      </div>
    </div>
  );
}

interface ResolutionOptionProps {
  value: ConflictResolution;
  selected: boolean;
  onSelect: () => void;
  radioId: string;
  /** Unique name scoped to the parent ConflictCard's radio group. */
  radioGroupName: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  accentClass: string;
}

function ResolutionOption({
  value,
  selected,
  onSelect,
  radioId,
  radioGroupName,
  title,
  description,
  icon,
  accentClass,
}: ResolutionOptionProps) {
  return (
    <label
      htmlFor={radioId}
      className={cn(
        'group relative flex cursor-pointer gap-3 rounded-lg border p-3 transition-all duration-150',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1',
        selected
          ? cn('border-transparent shadow-sm', accentClass)
          : 'border-border hover:border-border/80 hover:bg-muted/40'
      )}
    >
      {/* Hidden native radio for accessibility */}
      <input
        type="radio"
        id={radioId}
        name={radioGroupName}
        value={value}
        checked={selected}
        onChange={onSelect}
        className="sr-only"
        aria-checked={selected}
      />

      {/* Custom radio indicator */}
      <div
        className={cn(
          'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
          selected ? 'border-current bg-current' : 'border-muted-foreground/50'
        )}
        aria-hidden="true"
      >
        {selected && <div className="h-1.5 w-1.5 rounded-full bg-background" />}
      </div>

      {/* Icon */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-md',
          selected ? 'bg-background/30' : 'bg-muted'
        )}
        aria-hidden="true"
      >
        {icon}
      </div>

      {/* Text */}
      <div className="flex-1 space-y-0.5">
        <p className="text-sm font-semibold leading-snug">{title}</p>
        <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </label>
  );
}

interface ConflictCardProps {
  conflict: VersionConflict;
  resolution: ConflictResolution | undefined;
  onResolutionChange: (resolution: ConflictResolution) => void;
  index: number;
  total: number;
}

function ConflictCard({ conflict, resolution, onResolutionChange, index, total }: ConflictCardProps) {
  const uid = useId();
  const sideBySideId = `${uid}-side-by-side`;
  const overwriteId = `${uid}-overwrite`;
  // Unique radio group name scoped to this card — prevents radios across different
  // conflict cards from being mutually exclusive with each other (WCAG 4.1.3).
  const radioGroupName = `${uid}-resolution`;

  return (
    <article
      aria-label={`Conflict ${index + 1} of ${total}: ${conflict.artifactName}`}
      className="rounded-xl border bg-card shadow-sm"
    >
      {/* Card header — artifact identity */}
      <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400"
            aria-hidden="true"
          >
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold text-sm leading-tight">{conflict.artifactName}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                {artifactTypeLabel(conflict.artifactType)}
              </Badge>
            </p>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-1 text-[10px] text-muted-foreground">
          <AlertTriangle className="h-3 w-3 text-amber-500" aria-hidden="true" />
          <time dateTime={conflict.detectedAt}>{formatDetectedAt(conflict.detectedAt)}</time>
        </div>
      </div>

      {/* Hash comparison row */}
      <div className="mx-4 mb-3 flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2.5">
        <HashDisplay label="Plugin pins" hash={conflict.pinnedHash} variant="pinned" />
        <div
          className="flex flex-1 flex-col items-center justify-center"
          aria-label="conflicts with"
        >
          <Swords className="h-4 w-4 text-destructive/60" aria-hidden="true" />
        </div>
        <HashDisplay label="Currently deployed" hash={conflict.currentHash} variant="current" />
      </div>

      <Separator className="mx-4" style={{ width: 'calc(100% - 2rem)' }} />

      {/* Resolution options */}
      <div
        className="space-y-2 p-4"
        role="radiogroup"
        aria-label={`Resolution for ${conflict.artifactName}`}
        aria-required="true"
      >
        <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Resolution strategy
        </p>

        <ResolutionOption
          value="side-by-side"
          selected={resolution === 'side-by-side'}
          onSelect={() => onResolutionChange('side-by-side')}
          radioId={sideBySideId}
          radioGroupName={radioGroupName}
          title="Deploy side-by-side"
          description={`Install the plugin's pinned version under a renamed alias, keeping the current deployment intact.`}
          icon={<ArrowRightLeft className="h-4 w-4" aria-hidden="true" />}
          accentClass="bg-blue-500/8 border-blue-400/30 text-blue-600 dark:text-blue-400"
        />

        <ResolutionOption
          value="overwrite"
          selected={resolution === 'overwrite'}
          onSelect={() => onResolutionChange('overwrite')}
          radioId={overwriteId}
          radioGroupName={radioGroupName}
          title="Overwrite with plugin version"
          description={`Replace the current deployment with the plugin's pinned hash. Existing users of this artifact will see the plugin's version.`}
          icon={<Layers className="h-4 w-4" aria-hidden="true" />}
          accentClass="bg-orange-500/8 border-orange-400/30 text-orange-600 dark:text-orange-400"
        />
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Unsupported platform notice
// ---------------------------------------------------------------------------

interface UnsupportedPlatformNoticeProps {
  platform: string;
  pluginName: string;
  onClose: () => void;
}

function UnsupportedPlatformNotice({
  platform,
  pluginName,
  onClose,
}: UnsupportedPlatformNoticeProps) {
  return (
    <>
      <DialogHeader>
        <div className="flex items-center gap-2">
          <PackageX className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <DialogTitle>Plugin Deployment Unavailable</DialogTitle>
        </div>
        <DialogDescription>
          Plugin deployment for <strong>{pluginName}</strong> is not yet supported on this platform.
        </DialogDescription>
      </DialogHeader>

      <div
        className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-4"
        role="note"
      >
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="space-y-1">
          <p className="text-sm font-medium">Platform: {platform}</p>
          <p className="text-sm text-muted-foreground">
            Plugin deployment with version conflict resolution is currently only available on the
            Claude Code platform. Support for additional platforms is planned.
          </p>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </DialogFooter>
    </>
  );
}

// ---------------------------------------------------------------------------
// Main dialog
// ---------------------------------------------------------------------------

export function ConflictResolutionDialog({
  open,
  onOpenChange,
  conflicts,
  pluginName,
  platform = 'claude-code',
  onResolve,
  onCancel,
}: ConflictResolutionDialogProps) {
  // Track each conflict's chosen resolution independently
  const [resolutions, setResolutions] = useState<Map<string, ConflictResolution>>(() => new Map());

  const handleResolutionChange = useCallback(
    (artifactName: string, resolution: ConflictResolution) => {
      setResolutions((prev) => {
        const next = new Map(prev);
        next.set(artifactName, resolution);
        return next;
      });
    },
    []
  );

  const allResolved = conflicts.length > 0 && conflicts.every((c) => resolutions.has(c.artifactName));

  const handleResolve = () => {
    if (!allResolved) return;
    onResolve(resolutions);
  };

  const handleCancel = () => {
    onCancel();
    onOpenChange(false);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      // Reset state when dialog closes
      setResolutions(new Map());
    }
    onOpenChange(nextOpen);
  };

  const unresolvedCount = conflicts.filter((c) => !resolutions.has(c.artifactName)).length;
  const isUnsupportedPlatform = platform !== 'claude-code';

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className={cn(
          'flex max-h-[88vh] flex-col gap-0 overflow-hidden p-0',
          isUnsupportedPlatform ? 'max-w-md p-6 gap-4' : 'max-w-2xl'
        )}
        aria-modal="true"
      >
        {/* Unsupported platform: compact informational view */}
        {isUnsupportedPlatform ? (
          <UnsupportedPlatformNotice
            platform={platform}
            pluginName={pluginName}
            onClose={handleCancel}
          />
        ) : (
          <>
            {/* ── Header ─────────────────────────────────────────────────── */}
            <div className="border-b px-6 py-5">
              <DialogHeader>
                <div className="flex items-center gap-2.5">
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400"
                    aria-hidden="true"
                  >
                    <AlertTriangle className="h-4.5 w-4.5" />
                  </div>
                  <div>
                    <DialogTitle className="text-base">Version Conflicts Detected</DialogTitle>
                  </div>
                </div>
                <DialogDescription className="mt-1.5">
                  Deploying plugin{' '}
                  <span className="font-semibold text-foreground">{pluginName}</span> requires
                  resolving{' '}
                  {conflicts.length === 1
                    ? 'a version conflict with 1 artifact'
                    : `version conflicts with ${conflicts.length} artifacts`}
                  . Choose how to handle each conflict before proceeding.
                </DialogDescription>
              </DialogHeader>

              {/* Progress indicator */}
              {conflicts.length > 1 && (
                <div className="mt-3 flex items-center gap-2" aria-live="polite" aria-atomic="true">
                  <div
                    className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"
                    role="progressbar"
                    aria-valuenow={conflicts.length - unresolvedCount}
                    aria-valuemin={0}
                    aria-valuemax={conflicts.length}
                    aria-label="Conflicts resolved"
                  >
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{
                        width: `${((conflicts.length - unresolvedCount) / conflicts.length) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                    {conflicts.length - unresolvedCount} / {conflicts.length}
                  </span>
                </div>
              )}
            </div>

            {/* ── Conflict cards ─────────────────────────────────────────── */}
            <ScrollArea className="flex-1">
              <div
                className="space-y-3 px-6 py-4"
                role="list"
                aria-label="Version conflicts requiring resolution"
              >
                {conflicts.map((conflict, index) => (
                  <div key={conflict.artifactName} role="listitem">
                    <ConflictCard
                      conflict={conflict}
                      resolution={resolutions.get(conflict.artifactName)}
                      onResolutionChange={(res) =>
                        handleResolutionChange(conflict.artifactName, res)
                      }
                      index={index}
                      total={conflicts.length}
                    />
                  </div>
                ))}
              </div>
            </ScrollArea>

            {/* ── Footer ─────────────────────────────────────────────────── */}
            <div className="border-t bg-muted/20 px-6 py-4">
              {/* Escape hatch notice */}
              <p className="mb-3 text-xs text-muted-foreground">
                Not sure? You can{' '}
                <button
                  type="button"
                  onClick={handleCancel}
                  className="underline underline-offset-2 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  skip plugin deployment
                </button>{' '}
                to cancel without making any changes.
              </p>

              <DialogFooter className="flex-row items-center justify-between gap-2 sm:justify-between">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  className="shrink-0"
                >
                  Skip deployment
                </Button>

                <Button
                  type="button"
                  onClick={handleResolve}
                  disabled={!allResolved}
                  className="shrink-0"
                  aria-describedby={!allResolved ? 'resolve-hint' : undefined}
                >
                  {allResolved
                    ? 'Proceed with deployment'
                    : `Resolve ${unresolvedCount} remaining`}
                </Button>
              </DialogFooter>

              {!allResolved && (
                <p
                  id="resolve-hint"
                  className="mt-2 text-right text-xs text-muted-foreground"
                  aria-live="polite"
                >
                  Select a resolution strategy for each conflict above.
                </p>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
