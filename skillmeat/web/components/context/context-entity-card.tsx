/**
 * Context Entity Card Component
 *
 * Displays a context entity with type badge, category, auto-load indicator,
 * path pattern, and action buttons. Follows the unified card style with
 * colored left border accents based on entity type.
 *
 * Type display properties (colours, icons, labels) are driven by
 * `lib/context-entity-config.ts` — edit that file to change per-type styling.
 */

'use client';

import * as React from 'react';
import {
  FileText,
  Settings,
  BookOpen,
  Shield,
  Clock,
  File,
  Rocket,
  Pencil,
  Trash2,
  CheckCircle2,
  Circle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  getEntityTypeConfig,
  type ContextEntityTypeConfig,
} from '@/lib/context-entity-config';
import type { ContextEntity } from '@/types/context-entity';

// ============================================================================
// Icon resolver
// ============================================================================

/** Maps icon name strings from ContextEntityTypeConfig to real Lucide components. */
function resolveIcon(iconName: ContextEntityTypeConfig['icon']): React.ElementType {
  switch (iconName) {
    case 'settings':
      return Settings;
    case 'file-text':
      return FileText;
    case 'shield':
      return Shield;
    case 'book-open':
      return BookOpen;
    case 'clock':
      return Clock;
    case 'file':
    default:
      return File;
  }
}

// ============================================================================
// Sub-components
// ============================================================================

interface TypeBadgeProps {
  config: ContextEntityTypeConfig;
}

function TypeBadge({ config }: TypeBadgeProps) {
  const Icon = resolveIcon(config.icon);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn(
              'gap-1 rounded-full text-xs font-medium border-transparent',
              config.bgClass,
              config.textClass
            )}
          >
            <Icon className="h-3 w-3" aria-hidden="true" />
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>Entity type: {config.label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface AutoLoadIndicatorProps {
  autoLoad: boolean;
}

function AutoLoadIndicator({ autoLoad }: AutoLoadIndicatorProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn(
              'gap-1 text-xs',
              autoLoad
                ? 'border-green-500 bg-green-50 text-green-700 dark:bg-green-950'
                : 'border-gray-300 bg-gray-50 text-gray-600 dark:bg-gray-900'
            )}
          >
            {autoLoad ? <CheckCircle2 className="h-3 w-3" /> : <Circle className="h-3 w-3" />}
            {autoLoad ? 'Auto-load' : 'Manual'}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            {autoLoad ? 'Automatically loads when path pattern matches' : 'Requires manual loading'}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export interface ContextEntityCardProps {
  /** The context entity to display */
  entity: ContextEntity;
  /** Callback when preview button is clicked */
  onPreview?: (entity: ContextEntity) => void;
  /** Callback when deploy button is clicked */
  onDeploy?: (entity: ContextEntity) => void;
  /** Callback when edit button is clicked */
  onEdit?: (entity: ContextEntity) => void;
  /** Callback when delete button is clicked */
  onDelete?: (entity: ContextEntity) => void;
  /** Show token count badge */
  showTokenCount?: boolean;
  /** Estimated token count for this entity */
  tokenCount?: number;
  /** Callback when auto-load toggle is changed */
  onAutoLoadToggle?: (enabled: boolean) => void;
}

/**
 * ContextEntityCard - Card for displaying a context entity
 *
 * Shows entity information including name, type, category, auto-load setting,
 * and path pattern. Provides action buttons for preview, deploy, edit, and delete.
 *
 * Visual design follows the unified card style with colored left borders based
 * on entity type (config=blue, spec=purple, rule=orange, context=green, progress=yellow).
 *
 * @example
 * ```tsx
 * <ContextEntityCard
 *   entity={contextEntity}
 *   onPreview={(entity) => showPreview(entity)}
 *   onDeploy={(entity) => deployToProject(entity)}
 *   onEdit={(entity) => openEditor(entity)}
 *   onDelete={(entity) => confirmDelete(entity)}
 * />
 * ```
 *
 * @param props - ContextEntityCardProps configuration
 * @returns Card component with entity information and actions
 */
export function ContextEntityCard({
  entity,
  onPreview,
  onDeploy,
  onEdit,
  onDelete,
  showTokenCount = false,
  tokenCount,
  onAutoLoadToggle,
}: ContextEntityCardProps) {
  // Look up display config from the central map (handles null/casing internally).
  const config = getEntityTypeConfig(entity.entity_type);

  const Icon = resolveIcon(config.icon);

  const handleDeploy = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDeploy?.(entity);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(entity);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(entity);
  };

  const handleAutoLoadToggle = (checked: boolean) => {
    onAutoLoadToggle?.(checked);
  };

  // Truncate path pattern if too long
  const truncatedPath =
    entity.path_pattern.length > 40 ? `...${entity.path_pattern.slice(-37)}` : entity.path_pattern;

  return (
    <Card
      className={cn(
        'group relative flex min-h-[220px] cursor-pointer flex-col border-l-4',
        config.borderClass,
        config.cardBgClass,
        'transition-shadow duration-200 hover:shadow-md hover:ring-1 hover:ring-border'
      )}
      role="article"
      aria-label={`Context entity: ${entity.name}. Click to preview.`}
      onClick={() => onPreview?.(entity)}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onPreview?.(entity);
        }
      }}
    >
      {/* Card content */}
      <div className="flex-1 space-y-3 p-4">
        {/* Header: Name + Type Badge + Auto-load */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Icon className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{entity.name}</h3>
              {entity.category && (
                <p className="text-xs text-muted-foreground">Category: {entity.category}</p>
              )}
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center gap-1">
            <TypeBadge config={config} />
            <AutoLoadIndicator autoLoad={entity.auto_load} />
          </div>
        </div>

        {/* Description */}
        {entity.description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">{entity.description}</p>
        )}

        {/* Path Pattern and Token Count */}
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded bg-muted px-2 py-1 font-mono text-xs text-muted-foreground"
            title={entity.path_pattern}
            aria-label={`Path pattern: ${entity.path_pattern}`}
          >
            {truncatedPath}
          </span>
          {entity.version && (
            <Badge variant="outline" className="text-xs">
              v{entity.version}
            </Badge>
          )}
          {showTokenCount && tokenCount !== undefined && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge variant="secondary" className="gap-1 text-xs">
                    ~{tokenCount} tokens
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Estimated token usage when loaded</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Auto-load Toggle */}
        {onAutoLoadToggle && (
          <div
            className="flex items-center justify-between border-t pt-2"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2">
              <label
                htmlFor={`auto-load-${entity.id}`}
                className="cursor-pointer text-sm font-medium"
              >
                Auto-load
              </label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="text-xs text-muted-foreground" aria-label="Help">
                      ⓘ
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Automatically load this entity when path pattern matches</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Switch
              id={`auto-load-${entity.id}`}
              checked={entity.auto_load}
              onCheckedChange={handleAutoLoadToggle}
              aria-describedby={`auto-load-help-${entity.id}`}
              aria-label={`Auto-load ${entity.name} when path pattern matches`}
            />
            <span id={`auto-load-help-${entity.id}`} className="sr-only">
              Automatically load this entity when path pattern matches edited files
            </span>
          </div>
        )}
      </div>

      {/* Footer: Action Bar — pinned to bottom */}
      <div
        className="flex items-center justify-between gap-2 border-t p-2"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Left: Edit/Delete (visible on hover) */}
        <div className="flex gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          {onEdit && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleEdit}
              aria-label={`Edit ${entity.name}`}
            >
              <Pencil className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive hover:text-destructive"
              onClick={handleDelete}
              aria-label={`Delete ${entity.name}`}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        </div>

        {/* Right: Deploy */}
        <div className="flex gap-2">
          {onDeploy && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeploy}
              aria-label={`Deploy ${entity.name} to project`}
            >
              <Rocket className="mr-1 h-4 w-4" aria-hidden="true" />
              Deploy
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
