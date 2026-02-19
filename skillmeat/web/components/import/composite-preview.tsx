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
  PlusCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Data shape
// ---------------------------------------------------------------------------

export interface CompositeArtifactEntry {
  name: string;
  type: string;
}

export interface CompositeConflictEntry {
  name: string;
  type: string;
  currentHash: string;
  newHash: string;
}

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

  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center gap-2 rounded-md px-1 py-1.5 text-sm font-medium transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      aria-expanded={isOpen}
      aria-controls={`bucket-${intent}`}
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
// Simple artifact row
// ---------------------------------------------------------------------------

function ArtifactRow({ name, type }: { name: string; type: string }) {
  const typeLabel = type.charAt(0).toUpperCase() + type.slice(1);
  return (
    <li className="flex items-center justify-between py-1 pl-6 text-sm">
      <span className="truncate font-medium">{name}</span>
      <span className="ml-2 shrink-0 text-xs text-muted-foreground">{typeLabel}</span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Conflict row — shows hash comparison
// ---------------------------------------------------------------------------

function ConflictRow({ entry }: { entry: CompositeConflictEntry }) {
  const typeLabel = entry.type.charAt(0).toUpperCase() + entry.type.slice(1);
  return (
    <li className="space-y-0.5 py-1.5 pl-6">
      <div className="flex items-center justify-between text-sm">
        <span className="truncate font-medium">{entry.name}</span>
        <span className="ml-2 shrink-0 text-xs text-muted-foreground">{typeLabel}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-2 text-xs text-muted-foreground">
        <span className="truncate font-mono">
          <span className="text-muted-foreground/60">current: </span>
          {entry.currentHash.slice(0, 8)}
        </span>
        <span className="truncate font-mono">
          <span className="text-amber-600 dark:text-amber-400">incoming: </span>
          {entry.newHash.slice(0, 8)}
        </span>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Collapsible bucket section
// ---------------------------------------------------------------------------

interface BucketSectionProps {
  intent: 'new' | 'existing' | 'conflict';
  label: string;
  entries: CompositeArtifactEntry[] | (CompositeArtifactEntry & { hash: string })[] | CompositeConflictEntry[];
  defaultOpen?: boolean;
}

function BucketSection({ intent, label, entries, defaultOpen = false }: BucketSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (entries.length === 0) return null;

  return (
    <div className="space-y-1">
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
          className="divide-y divide-border rounded-md border bg-muted/30"
        >
          {intent === 'conflict'
            ? (entries as CompositeConflictEntry[]).map((e) => (
                <ConflictRow key={e.name} entry={e} />
              ))
            : (entries as CompositeArtifactEntry[]).map((e) => (
                <ArtifactRow key={e.name} name={e.name} type={e.type} />
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
  preview: CompositePreview;
  className?: string;
}

export function CompositePreview({ preview, className }: CompositePreviewProps) {
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

  return (
    <div className={cn('space-y-4', className)}>
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
        />
        <BucketSection
          intent="existing"
          label="Existing (Will Link)"
          entries={existingArtifacts}
          defaultOpen={false}
        />
        <BucketSection
          intent="conflict"
          label="Conflict (Needs Resolution)"
          entries={conflictArtifacts}
          defaultOpen={conflictArtifacts.length > 0}
        />
      </div>
    </div>
  );
}
