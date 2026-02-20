'use client';

/**
 * CompositePreview
 *
 * Renders a preview breakdown for composite (plugin) artifact imports.
 * Splits child artifacts into three buckets:
 *   - New (Will Import)      — not already in the collection
 *   - Existing (Will Link)   — matched by content hash
 *   - Conflict (Needs Resolution) — same name, different hash
 *
 * Bucket sections are individually collapsible.
 * An ARIA live region announces the summary when the component mounts / data
 * changes (import modal use-case: announced on open).
 *
 * WCAG 2.1 AA: aria-live summary, semantic lists, keyboard-navigable
 * disclosure buttons (Space / Enter), visible focus rings.
 */

import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  Loader2,
  PlusCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ArtifactCompactCard } from '@/app/marketplace/sources/[id]/components/artifact-compact-card';
import type { CatalogEntry } from '@/types/marketplace';

// ---------------------------------------------------------------------------
// Data shape
// ---------------------------------------------------------------------------

export interface CompositePreviewData {
  pluginName: string;
  totalChildren: number;
  newArtifacts: CatalogEntry[];
  existingArtifacts: CatalogEntry[];
  conflictArtifacts: CatalogEntry[];
}

/**
 * @deprecated Use CompositePreviewData instead.
 * Kept for backward compatibility with CatalogEntryModal during migration.
 */
export interface CompositeArtifactEntry {
  name: string;
  type: string;
}

/**
 * @deprecated Use CompositePreviewData instead.
 * Kept for backward compatibility with CatalogEntryModal during migration.
 */
export interface CompositeConflictEntry {
  name: string;
  type: string;
  currentHash: string;
  newHash: string;
}

/**
 * @deprecated Use CompositePreviewData instead.
 */
export interface CompositePreview {
  pluginName: string;
  totalChildren: number;
  newArtifacts: CompositeArtifactEntry[];
  existingArtifacts: (CompositeArtifactEntry & { hash: string })[];
  conflictArtifacts: CompositeConflictEntry[];
}

// ---------------------------------------------------------------------------
// Bucket header (collapsible trigger)
// ---------------------------------------------------------------------------

interface BucketHeaderProps {
  label: string;
  count: number;
  isOpen: boolean;
  onToggle: () => void;
  intent: 'new' | 'existing' | 'conflict';
}

const INTENT_STYLES = {
  new: {
    icon: PlusCircle,
    iconCls: 'text-green-600 dark:text-green-400',
    countCls: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  },
  existing: {
    icon: CheckCircle2,
    iconCls: 'text-blue-600 dark:text-blue-400',
    countCls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  },
  conflict: {
    icon: AlertTriangle,
    iconCls: 'text-amber-600 dark:text-amber-400',
    countCls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  },
} as const;

function BucketHeader({ label, count, isOpen, onToggle, intent }: BucketHeaderProps) {
  const { icon: Icon, iconCls, countCls } = INTENT_STYLES[intent];
  // Only set aria-controls when the panel is actually rendered in the DOM
  const controlsId = isOpen ? `bucket-${intent}` : undefined;

  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center gap-2 rounded-md px-1 py-1.5 text-sm font-medium transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      aria-expanded={isOpen}
      aria-controls={controlsId}
      aria-label={`${label}: ${count} ${count !== 1 ? 'artifacts' : 'artifact'}. ${isOpen ? 'Collapse' : 'Expand'} section`}
      data-testid={`bucket-toggle-${intent}`}
    >
      {isOpen ? (
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      ) : (
        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      )}
      <Icon className={cn('h-4 w-4 shrink-0', iconCls)} aria-hidden="true" />
      <span className="flex-1 text-left">{label}</span>
      <span
        className={cn(
          'rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums',
          countCls,
        )}
        aria-label={`${count} artifact${count !== 1 ? 's' : ''}`}
      >
        {count}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Collapsible bucket section using ArtifactCompactCard
// ---------------------------------------------------------------------------

interface BucketSectionProps {
  intent: 'new' | 'existing' | 'conflict';
  label: string;
  entries: CatalogEntry[];
  defaultOpen?: boolean;
  sourceId: string;
  onImport?: (entry: CatalogEntry) => void;
  onEntryClick?: (entry: CatalogEntry) => void;
  importingEntryIds?: Set<string>;
}

function BucketSection({
  intent,
  label,
  entries,
  defaultOpen = false,
  sourceId,
  onImport,
  onEntryClick,
  importingEntryIds,
}: BucketSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (entries.length === 0) return null;

  return (
    <div className="space-y-1" data-testid={`bucket-section-${intent}`}>
      <BucketHeader
        label={label}
        count={entries.length}
        isOpen={isOpen}
        onToggle={() => setIsOpen((v) => !v)}
        intent={intent}
      />
      {isOpen && (
        <ul
          id={`bucket-${intent}`}
          role="list"
          aria-label={`${label} artifacts`}
          className="grid grid-cols-1 gap-2 sm:grid-cols-2"
        >
          {entries.map((entry) => (
            <li key={entry.id} role="listitem">
              <ArtifactCompactCard
                entry={entry}
                sourceId={sourceId}
                onClick={onEntryClick ? () => onEntryClick(entry) : undefined}
                onImport={() => onImport?.(entry)}
                isImporting={importingEntryIds?.has(entry.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export interface CompositePreviewProps {
  preview: CompositePreviewData;
  className?: string;
  /** Source ID passed through to ArtifactCompactCard for exclude mutations */
  sourceId: string;
  /** Called when the user clicks Import on an individual child artifact card */
  onImport?: (entry: CatalogEntry) => void;
  /** Called when the user wants to import all new artifacts at once */
  onImportAll?: () => void;
  /** Called when the user clicks a card to view the entry detail */
  onEntryClick?: (entry: CatalogEntry) => void;
  /** Set of entry IDs currently being imported (shows spinner on their cards) */
  importingEntryIds?: Set<string>;
}

export function CompositePreview({
  preview,
  className,
  sourceId,
  onImport,
  onImportAll,
  onEntryClick,
  importingEntryIds,
}: CompositePreviewProps) {
  const { pluginName, totalChildren, newArtifacts, existingArtifacts, conflictArtifacts } =
    preview;

  // Human-readable summary for ARIA live region
  const summaryParts: string[] = [];
  if (newArtifacts.length > 0) summaryParts.push(`${newArtifacts.length} new`);
  if (existingArtifacts.length > 0) summaryParts.push(`${existingArtifacts.length} existing`);
  if (conflictArtifacts.length > 0) summaryParts.push(`${conflictArtifacts.length} conflicts`);

  const summaryText = `Plugin "${pluginName}": ${totalChildren} ${
    totalChildren === 1 ? 'child' : 'children'
  } — ${summaryParts.join(', ') || 'none'}.`;

  const isAnyImporting = importingEntryIds && importingEntryIds.size > 0;

  return (
    <div className={cn('space-y-4', className)} data-testid="composite-preview">
      {/* ARIA live region — announces summary when opened */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {summaryText}
      </div>

      {/* Visible summary card */}
      <div className="rounded-lg border bg-card px-4 py-3">
        <p className="text-sm font-medium">
          <span className="font-semibold">{pluginName}</span>
          {': '}
          <span className="text-muted-foreground">{summaryText.split('—')[1]?.trim()}</span>
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {totalChildren} total {totalChildren === 1 ? 'child artifact' : 'child artifacts'}
        </p>
      </div>

      {/* Import All New button — only when there are new artifacts and a handler */}
      {newArtifacts.length > 0 && onImportAll && (
        <div className="flex justify-end">
          <Button
            size="sm"
            variant="default"
            onClick={onImportAll}
            disabled={isAnyImporting}
            aria-label={`Import all ${newArtifacts.length} new artifact${newArtifacts.length !== 1 ? 's' : ''} from this plugin`}
          >
            {isAnyImporting ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Importing...
              </>
            ) : (
              <>
                <Download className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                Import All New ({newArtifacts.length})
              </>
            )}
          </Button>
        </div>
      )}

      {/* Conflict warning banner (only when there are conflicts) */}
      {conflictArtifacts.length > 0 && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-sm"
        >
          <AlertTriangle
            className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400"
            aria-hidden="true"
          />
          <p className="text-amber-900 dark:text-amber-100">
            <span className="font-medium">
              {conflictArtifacts.length} version{' '}
              {conflictArtifacts.length === 1 ? 'conflict' : 'conflicts'} detected.
            </span>{' '}
            Review below and choose a resolution strategy before importing.
          </p>
        </div>
      )}

      {/* Bucket sections */}
      <div className="space-y-2">
        <BucketSection
          intent="new"
          label="New (Will Import)"
          entries={newArtifacts}
          defaultOpen={newArtifacts.length > 0}
          sourceId={sourceId}
          onImport={onImport}
          onEntryClick={onEntryClick}
          importingEntryIds={importingEntryIds}
        />
        <BucketSection
          intent="existing"
          label="Existing (Will Link)"
          entries={existingArtifacts}
          defaultOpen={false}
          sourceId={sourceId}
          onImport={onImport}
          onEntryClick={onEntryClick}
          importingEntryIds={importingEntryIds}
        />
        <BucketSection
          intent="conflict"
          label="Conflict (Needs Resolution)"
          entries={conflictArtifacts}
          defaultOpen={conflictArtifacts.length > 0}
          sourceId={sourceId}
          onImport={onImport}
          onEntryClick={onEntryClick}
          importingEntryIds={importingEntryIds}
        />
      </div>
    </div>
  );
}
