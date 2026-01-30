/**
 * Artifact Type Section Component
 *
 * Groups artifacts by type with collapsible section headers.
 * Each section displays type-specific icons, counts, and a grid of compact artifact cards.
 */

'use client';

import { useState, useCallback, memo } from 'react';
import { ChevronRight, Sparkles, Terminal, Bot, Server, Anchor } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { ArtifactCompactCard } from './artifact-compact-card';
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
  /** Callback when artifact card is clicked (opens modal) */
  onArtifactClick?: (entry: CatalogEntry) => void;
  /** Source ID for exclude operations */
  sourceId: string;
  /** Whether import is in progress */
  isImporting?: boolean;
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
// Main Component
// ============================================================================

/**
 * Displays artifacts of a specific type in a collapsible section.
 *
 * Section header shows type icon, name (plural), count badge, and chevron.
 * Content area displays artifact rows with import/exclude actions.
 * Returns null if no artifacts are provided.
 *
 * PERFORMANCE: Wrapped with React.memo to prevent re-renders when
 * sibling sections or parent state changes without affecting this section.
 */
function ArtifactTypeSectionComponent({
  type,
  artifacts,
  defaultExpanded = false,
  onImport,
  onExclude: _onExclude,
  onArtifactClick,
  sourceId,
  isImporting = false,
}: ArtifactTypeSectionProps) {
  // Hooks must be called unconditionally (Rules of Hooks)
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  // Note: onExclude is handled internally by ArtifactCompactCard via ExcludeArtifactDialog
  void _onExclude;

  // Memoize import handler factory to provide stable callbacks
  const handleImport = useCallback(
    (entry: CatalogEntry) => () => onImport(entry),
    [onImport]
  );

  // Memoize click handler factory to provide stable callbacks
  const handleClick = useCallback(
    (entry: CatalogEntry) => () => onArtifactClick?.(entry),
    [onArtifactClick]
  );

  // Don't render if no artifacts (after hooks)
  if (artifacts.length === 0) {
    return null;
  }

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
          aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${config.pluralLabel} section, ${artifacts.length} ${artifacts.length === 1 ? 'item' : 'items'}`}
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

          {/* Count Badge - aria-hidden since count is in aria-label */}
          <span className="text-sm text-muted-foreground" aria-hidden="true">({artifacts.length})</span>
        </button>
      </CollapsibleTrigger>

      {/* Collapsible Content - Grid of compact cards */}
      <CollapsibleContent>
        <div className="grid grid-cols-2 gap-3 pt-3 md:grid-cols-3 lg:grid-cols-4">
          {artifacts.map((entry) => (
            <ArtifactCompactCard
              key={entry.id}
              entry={entry}
              sourceId={sourceId}
              onClick={handleClick(entry)}
              onImport={handleImport(entry)}
              isImporting={isImporting}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export const ArtifactTypeSection = memo(ArtifactTypeSectionComponent);
