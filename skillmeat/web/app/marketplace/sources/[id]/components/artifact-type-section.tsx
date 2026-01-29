/**
 * Artifact Type Section Component
 *
 * Groups artifacts by type with collapsible section headers.
 * Each section displays type-specific icons, counts, and artifact rows with actions.
 */

'use client';

import * as React from 'react';
import { ChevronRight, Sparkles, Terminal, Bot, Server, Anchor, Download, EyeOff } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { CatalogEntry, ArtifactType } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

export interface ArtifactTypeSectionProps {
  /** Artifact type (skill, command, agent, mcp, hook) */
  type: ArtifactType;
  /** Artifacts of this type */
  artifacts: CatalogEntry[];
  /** Whether section starts expanded */
  defaultExpanded?: boolean;
  /** Callback when import is requested */
  onImport: (entry: CatalogEntry) => void;
  /** Callback when exclude is requested */
  onExclude: (entry: CatalogEntry) => void;
}

// ============================================================================
// Type Configuration
// ============================================================================

/**
 * Icon and label configuration for each artifact type.
 */
const typeConfig: Record<ArtifactType, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  pluralLabel: string;
}> = {
  skill: { icon: Sparkles, label: 'Skill', pluralLabel: 'Skills' },
  command: { icon: Terminal, label: 'Command', pluralLabel: 'Commands' },
  agent: { icon: Bot, label: 'Agent', pluralLabel: 'Agents' },
  mcp: { icon: Server, label: 'MCP', pluralLabel: 'MCP Servers' },
  mcp_server: { icon: Server, label: 'MCP Server', pluralLabel: 'MCP Servers' },
  hook: { icon: Anchor, label: 'Hook', pluralLabel: 'Hooks' },
};

// ============================================================================
// Sub-components
// ============================================================================

interface ArtifactRowProps {
  entry: CatalogEntry;
  onImport: () => void;
  onExclude: () => void;
}

/**
 * Individual artifact row with name, description, and action buttons.
 */
function ArtifactRow({ entry, onImport, onExclude }: ArtifactRowProps) {
  // Determine if actions should be disabled based on status
  const isImported = entry.status === 'imported';
  const isExcluded = entry.status === 'excluded';

  return (
    <div className="flex items-center justify-between gap-4 border-b py-3 last:border-b-0">
      {/* Name and description */}
      <div className="min-w-0 flex-1">
        <h4 className="truncate text-sm font-medium">{entry.name}</h4>
        {/* Only show description if it exists and is different from name */}
        {entry.path && (
          <p className="max-w-[200px] truncate text-xs text-muted-foreground" title={entry.path}>
            {entry.path}
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex flex-shrink-0 items-center gap-1">
        {/* Status badges */}
        {isImported && (
          <Badge variant="secondary" className="text-xs">
            Imported
          </Badge>
        )}
        {isExcluded && (
          <Badge variant="outline" className="text-xs text-muted-foreground">
            Excluded
          </Badge>
        )}

        {/* Import button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onImport}
          disabled={isImported}
          aria-label={`Import ${entry.name}`}
          className="h-8 w-8"
        >
          <Download className="h-4 w-4" />
        </Button>

        {/* Exclude button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onExclude}
          disabled={isExcluded}
          aria-label={`Exclude ${entry.name}`}
          className="h-8 w-8"
        >
          <EyeOff className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Displays artifacts of a specific type in a collapsible section.
 *
 * Section header shows type icon, name (plural), count badge, and chevron.
 * Content area displays artifact rows with import/exclude actions.
 * Returns null if no artifacts are provided.
 */
export function ArtifactTypeSection({
  type,
  artifacts,
  defaultExpanded = false,
  onImport,
  onExclude,
}: ArtifactTypeSectionProps) {
  // Don't render if no artifacts
  if (artifacts.length === 0) {
    return null;
  }

  const [isOpen, setIsOpen] = React.useState(defaultExpanded);
  const config = typeConfig[type];
  const TypeIcon = config.icon;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      {/* Section Header */}
      <CollapsibleTrigger asChild>
        <button
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-3 py-2',
            'cursor-pointer transition-colors duration-200 hover:bg-muted/50',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
          )}
          aria-expanded={isOpen}
          aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${config.pluralLabel} section`}
        >
          {/* Chevron */}
          <ChevronRight
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform duration-200',
              isOpen && 'rotate-90'
            )}
            aria-hidden="true"
          />

          {/* Type Icon */}
          <TypeIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />

          {/* Type Name (Plural) */}
          <span className="text-sm font-medium">{config.pluralLabel}</span>

          {/* Count Badge */}
          <span className="text-sm text-muted-foreground">({artifacts.length})</span>
        </button>
      </CollapsibleTrigger>

      {/* Collapsible Content */}
      <CollapsibleContent>
        <div className="pl-6">
          {artifacts.map((entry) => (
            <ArtifactRow
              key={entry.id}
              entry={entry}
              onImport={() => onImport(entry)}
              onExclude={() => onExclude(entry)}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
