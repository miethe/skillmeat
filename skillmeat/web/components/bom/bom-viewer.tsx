'use client';

import { useState, useMemo, useCallback } from 'react';
import {
  Search,
  Download,
  ShieldCheck,
  ShieldX,
  Shield,
  BookOpen,
  Terminal,
  Bot,
  Webhook,
  Server,
  Package,
  Workflow,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ArtifactEntry {
  name: string;
  type: string; // skill | command | agent | hook | mcp | composite | workflow
  version: string;
  scope: string; // user | local
  content_hash?: string;
}

export interface BomMetadata {
  owner?: string;
  scope?: string;
  artifactCount?: number;
}

export interface BomViewerProps {
  artifacts: ArtifactEntry[];
  metadata?: BomMetadata;
  signatureStatus?: 'verified' | 'invalid' | 'unsigned';
  signerEmail?: string;
  generatedAt?: string;
  isLoading?: boolean;
  onExportJson?: () => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Display label and icon for each artifact type */
const ARTIFACT_TYPE_CONFIG: Record<
  string,
  { label: string; Icon: React.ElementType; colorClass: string }
> = {
  skill: { label: 'Skills', Icon: BookOpen, colorClass: 'text-blue-500' },
  command: { label: 'Commands', Icon: Terminal, colorClass: 'text-violet-500' },
  agent: { label: 'Agents', Icon: Bot, colorClass: 'text-emerald-500' },
  hook: { label: 'Hooks', Icon: Webhook, colorClass: 'text-amber-500' },
  mcp: { label: 'MCP Servers', Icon: Server, colorClass: 'text-rose-500' },
  composite: { label: 'Composites', Icon: Package, colorClass: 'text-cyan-500' },
  workflow: { label: 'Workflows', Icon: Workflow, colorClass: 'text-fuchsia-500' },
};

const KNOWN_TYPES = Object.keys(ARTIFACT_TYPE_CONFIG);

function getTypeConfig(type: string) {
  return (
    ARTIFACT_TYPE_CONFIG[type] ?? {
      label: type.charAt(0).toUpperCase() + type.slice(1),
      Icon: Package,
      colorClass: 'text-zinc-400',
    }
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Scope badge: user = global, local = project */
function ScopeBadge({ scope }: { scope: string }) {
  const isLocal = scope === 'local';
  return (
    <Badge
      variant="outline"
      className={cn(
        'shrink-0 text-xs font-normal',
        isLocal
          ? 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-400'
          : 'border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400'
      )}
    >
      {isLocal ? 'local' : 'user'}
    </Badge>
  );
}

/** Single artifact row */
function ArtifactBomEntry({ entry }: { entry: ArtifactEntry }) {
  const { Icon, colorClass } = getTypeConfig(entry.type);
  return (
    <div
      className="flex items-center gap-3 px-3 py-2 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 rounded-sm transition-colors"
      role="listitem"
    >
      <Icon
        className={cn('h-3.5 w-3.5 shrink-0', colorClass)}
        aria-hidden="true"
      />
      <span className="flex-1 truncate font-mono text-sm text-zinc-800 dark:text-zinc-200">
        {entry.name}
      </span>
      <span className="shrink-0 font-mono text-xs text-zinc-400 dark:text-zinc-500">
        {entry.version}
      </span>
      <ScopeBadge scope={entry.scope} />
    </div>
  );
}

/** Group header + artifact list for one artifact type */
function ArtifactGroup({
  type,
  entries,
}: {
  type: string;
  entries: ArtifactEntry[];
}) {
  const { label, Icon, colorClass } = getTypeConfig(type);
  return (
    <section aria-label={`${label} — ${entries.length} item${entries.length !== 1 ? 's' : ''}`}>
      {/* Group header */}
      <div className="flex items-center gap-2 px-3 py-1.5 sticky top-0 bg-white dark:bg-zinc-950 z-10">
        <Icon className={cn('h-3.5 w-3.5 shrink-0', colorClass)} aria-hidden="true" />
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {label}
        </span>
        <span className="ml-auto text-xs tabular-nums text-zinc-400 dark:text-zinc-500">
          {entries.length}
        </span>
      </div>
      <Separator className="mx-3 w-auto" />
      {/* Artifact rows */}
      <div role="list" className="pb-2">
        {entries.map((entry) => (
          <ArtifactBomEntry key={`${entry.type}:${entry.name}`} entry={entry} />
        ))}
      </div>
    </section>
  );
}

/** Signature status indicator */
function SignatureBadge({
  status,
  signerEmail,
}: {
  status: 'verified' | 'invalid' | 'unsigned';
  signerEmail?: string;
}) {
  if (status === 'verified') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
        <span>
          Signature verified
          {signerEmail && (
            <> &mdash; <span className="font-mono">{signerEmail}</span></>
          )}
        </span>
      </div>
    );
  }
  if (status === 'invalid') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
        <ShieldX className="h-3.5 w-3.5" aria-hidden="true" />
        <span>Signature invalid</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500">
      <Shield className="h-3.5 w-3.5" aria-hidden="true" />
      <span>Unsigned</span>
    </div>
  );
}

/** Loading skeleton for the BOM viewer */
function BomViewerSkeleton() {
  return (
    <div
      className="flex h-full flex-col"
      aria-label="Loading BOM viewer"
      aria-busy="true"
    >
      {/* Header skeleton */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <div className="space-y-1.5">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3.5 w-48" />
        </div>
        <Skeleton className="h-8 w-28" />
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar skeleton */}
        <div className="w-44 shrink-0 border-r border-zinc-200 dark:border-zinc-800 p-3 space-y-3">
          <Skeleton className="h-4 w-16" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-3.5 w-20" />
            </div>
          ))}
          <Skeleton className="h-4 w-12 mt-4" />
          <Skeleton className="h-8 w-full" />
        </div>

        {/* Content skeleton */}
        <div className="flex-1 p-3 space-y-4">
          {[...Array(3)].map((_, gi) => (
            <div key={gi} className="space-y-1">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-px w-full" />
              {[...Array(gi === 0 ? 4 : 2)].map((_, ri) => (
                <div key={ri} className="flex items-center gap-3 py-1.5 px-3">
                  <Skeleton className="h-3.5 w-3.5 rounded" />
                  <Skeleton className="h-3.5 flex-1" />
                  <Skeleton className="h-3.5 w-14" />
                  <Skeleton className="h-5 w-10 rounded" />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Footer skeleton */}
      <div className="border-t border-zinc-200 dark:border-zinc-800 px-4 py-2 flex items-center justify-between">
        <Skeleton className="h-3.5 w-48" />
        <Skeleton className="h-3.5 w-36" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar: type filter + search
// ---------------------------------------------------------------------------

interface BomSidebarProps {
  allTypes: string[];
  selectedTypes: Set<string>;
  search: string;
  onTypeToggle: (type: string) => void;
  onSearchChange: (value: string) => void;
}

function BomSidebar({
  allTypes,
  selectedTypes,
  search,
  onTypeToggle,
  onSearchChange,
}: BomSidebarProps) {
  const allSelected = allTypes.every((t) => selectedTypes.has(t));

  function handleSelectAll() {
    if (allSelected) {
      // Deselect all → keep at least one type selected (noop deselect-all)
      return;
    }
    allTypes.forEach((t) => {
      if (!selectedTypes.has(t)) onTypeToggle(t);
    });
  }

  return (
    <aside
      className="w-44 shrink-0 border-r border-zinc-200 dark:border-zinc-800 flex flex-col"
      aria-label="Filter artifacts"
    >
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Type filter group */}
          <fieldset>
            <legend className="mb-2 text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
              Type
            </legend>
            <div className="space-y-1.5">
              {/* Select all checkbox */}
              <div className="flex items-center gap-2">
                <Checkbox
                  id="filter-type-all"
                  checked={allSelected}
                  onCheckedChange={handleSelectAll}
                  aria-label="Show all types"
                />
                <Label
                  htmlFor="filter-type-all"
                  className="text-xs font-medium text-zinc-600 dark:text-zinc-300 cursor-pointer select-none"
                >
                  All types
                </Label>
              </div>

              <Separator className="my-1" />

              {allTypes.map((type) => {
                const { label, Icon, colorClass } = getTypeConfig(type);
                const checkboxId = `filter-type-${type}`;
                return (
                  <div key={type} className="flex items-center gap-2">
                    <Checkbox
                      id={checkboxId}
                      checked={selectedTypes.has(type)}
                      onCheckedChange={() => onTypeToggle(type)}
                      aria-label={`Show ${label}`}
                    />
                    <Label
                      htmlFor={checkboxId}
                      className="flex items-center gap-1.5 cursor-pointer select-none"
                    >
                      <Icon
                        className={cn('h-3 w-3 shrink-0', colorClass)}
                        aria-hidden="true"
                      />
                      <span className="text-xs text-zinc-600 dark:text-zinc-300">{label}</span>
                    </Label>
                  </div>
                );
              })}
            </div>
          </fieldset>

          <Separator />

          {/* Search */}
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
              Search
            </p>
            <div className="relative">
              <Search
                className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-zinc-400"
                aria-hidden="true"
              />
              <Input
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder="Filter by name…"
                className="pl-6 h-7 text-xs"
                aria-label="Search artifacts by name"
              />
            </div>
          </div>
        </div>
      </ScrollArea>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Main content area
// ---------------------------------------------------------------------------

interface BomContentProps {
  groupedEntries: [string, ArtifactEntry[]][];
  totalFiltered: number;
  totalAll: number;
}

function BomContent({ groupedEntries, totalFiltered, totalAll }: BomContentProps) {
  if (groupedEntries.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-400 dark:text-zinc-600 text-sm">
        {totalAll === 0 ? 'No artifacts in this BOM.' : 'No artifacts match the current filters.'}
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1" aria-label={`${totalFiltered} of ${totalAll} artifacts`}>
      <div className="py-2">
        {groupedEntries.map(([type, entries]) => (
          <ArtifactGroup key={type} type={type} entries={entries} />
        ))}
      </div>
    </ScrollArea>
  );
}

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

interface BomFooterProps {
  signatureStatus?: 'verified' | 'invalid' | 'unsigned';
  signerEmail?: string;
  generatedAt?: string;
}

function BomFooter({ signatureStatus, signerEmail, generatedAt }: BomFooterProps) {
  const formattedDate = generatedAt
    ? new Date(generatedAt).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      })
    : null;

  return (
    <footer
      className="border-t border-zinc-200 dark:border-zinc-800 px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1"
      aria-label="BOM footer"
    >
      {signatureStatus && (
        <SignatureBadge status={signatureStatus} signerEmail={signerEmail} />
      )}
      {formattedDate && (
        <p className="text-xs text-zinc-400 dark:text-zinc-500 ml-auto">
          Generated{' '}
          <time dateTime={generatedAt}>{formattedDate}</time>
        </p>
      )}
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Root: BomViewerLayout
// ---------------------------------------------------------------------------

function BomViewerLayout({
  artifacts,
  metadata,
  signatureStatus,
  signerEmail,
  generatedAt,
  onExportJson,
}: Omit<BomViewerProps, 'isLoading' | 'className'>) {
  // Derive all unique types present in the BOM, sorted deterministically
  const allTypes = useMemo(() => {
    const typeSet = new Set(artifacts.map((a) => a.type));
    // Preferred order first, then any unknowns alphabetically
    return [
      ...KNOWN_TYPES.filter((t) => typeSet.has(t)),
      ...[...typeSet].filter((t) => !KNOWN_TYPES.includes(t)).sort(),
    ];
  }, [artifacts]);

  // Filter state
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(() => new Set(allTypes));
  const [search, setSearch] = useState('');

  // Keep selectedTypes in sync when allTypes changes (e.g., on new BOM prop)
  // Using a ref to detect first render vs. prop changes would be over-engineering here;
  // the effect is intentionally gated on allTypes identity.
  const handleTypeToggle = useCallback((type: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        // Don't allow deselecting the last type
        if (next.size <= 1) return prev;
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  // Filtered + grouped entries
  const groupedEntries = useMemo<[string, ArtifactEntry[]][]>(() => {
    const lowerSearch = search.toLowerCase().trim();
    const filtered = artifacts.filter((a) => {
      if (!selectedTypes.has(a.type)) return false;
      if (lowerSearch && !a.name.toLowerCase().includes(lowerSearch)) return false;
      return true;
    });

    // Group by type, preserving allTypes order
    const grouped = new Map<string, ArtifactEntry[]>();
    for (const type of allTypes) {
      grouped.set(type, []);
    }
    for (const entry of filtered) {
      const group = grouped.get(entry.type);
      if (group) {
        group.push(entry);
      } else {
        grouped.set(entry.type, [entry]);
      }
    }

    return [...grouped.entries()].filter(([, entries]) => entries.length > 0);
  }, [artifacts, allTypes, selectedTypes, search]);

  const totalFiltered = groupedEntries.reduce((sum, [, entries]) => sum + entries.length, 0);

  return (
    <div className="flex h-full flex-col" role="region" aria-label="Bill of Materials viewer">
      {/* Header */}
      <header className="flex items-start justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 gap-4">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            BOM Viewer
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            context.lock &mdash;{' '}
            <span className="tabular-nums">{artifacts.length}</span>{' '}
            artifact{artifacts.length !== 1 ? 's' : ''}
            {metadata?.scope && (
              <> &middot; scope: {metadata.scope}</>
            )}
            {metadata?.owner && (
              <> &middot; owner: {metadata.owner}</>
            )}
          </p>
        </div>
        {onExportJson && (
          <Button
            variant="outline"
            size="sm"
            onClick={onExportJson}
            className="shrink-0 gap-1.5 text-xs"
            aria-label="Export BOM as JSON file"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Export JSON
          </Button>
        )}
      </header>

      {/* Body: sidebar + content */}
      <div className="flex flex-1 overflow-hidden">
        <BomSidebar
          allTypes={allTypes}
          selectedTypes={selectedTypes}
          search={search}
          onTypeToggle={handleTypeToggle}
          onSearchChange={setSearch}
        />
        <BomContent
          groupedEntries={groupedEntries}
          totalFiltered={totalFiltered}
          totalAll={artifacts.length}
        />
      </div>

      {/* Footer */}
      {(signatureStatus || generatedAt) && (
        <BomFooter
          signatureStatus={signatureStatus}
          signerEmail={signerEmail}
          generatedAt={generatedAt}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export: BomViewer (handles loading state)
// ---------------------------------------------------------------------------

export function BomViewer({
  artifacts,
  metadata,
  signatureStatus,
  signerEmail,
  generatedAt,
  isLoading = false,
  onExportJson,
  className,
}: BomViewerProps) {
  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950 overflow-hidden',
        className
      )}
    >
      {isLoading ? (
        <BomViewerSkeleton />
      ) : (
        <BomViewerLayout
          artifacts={artifacts}
          metadata={metadata}
          signatureStatus={signatureStatus}
          signerEmail={signerEmail}
          generatedAt={generatedAt}
          onExportJson={onExportJson}
        />
      )}
    </div>
  );
}
